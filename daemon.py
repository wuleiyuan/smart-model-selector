#!/usr/bin/env python3
"""
OpenCode 运行时监控守护进程
功能：
1. 启动时自动选择最优模型
2. 后台监控 API 健康状态
3. 故障时自动切换到备用模型

支持两种运行模式：
- 前台模式: python3 daemon.py start (调试用)
- 后台模式: python3 daemon.py daemon (真正的守护进程)
"""

import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from typing import Dict, Optional
import requests
from threading import Thread, Event
import argparse
import fcntl
from logging.handlers import RotatingFileHandler

sys.path.insert(0, str(Path(__file__).parent))
from smart_model_dispatcher import SmartModelDispatcher

LOG_DIR = Path.home() / ".config" / "opencode"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "daemon.log"

handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,
    backupCount=3
)
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler, logging.StreamHandler()]
)
logger = logging.getLogger("OpenCodeDaemon")

PID_FILE = Path.home() / ".config" / "opencode" / "daemon.pid"
AUTH_CONFIG = Path.home() / ".local" / "share" / "opencode" / "auth.json"
CHECK_INTERVAL = 30  # 每30秒检查一次
HEALTH_CHECK_TIMEOUT = 5


# Provider 配置常量
PROVIDER_CONFIGS = {
    "google": ("google_api_key", "https://generativelanguage.googleapis.com"),
    "deepseek": ("deepseek_api_key", "https://api.deepseek.com"),
    "anthropic": ("anthropic_api_key", "https://api.anthropic.com/v1"),
    "siliconflow": ("siliconflow_api_key", "https://api.siliconflow.cn/v1"),
    "minimax": ("minimax_api_key", "https://api.minimax.chat/v1"),
    "kimi": ("kimi_api_key", "https://api.moonshot.cn/v1"),
    "doubao": ("doubao_api_key", "https://ark.cn-beijing.volces.com/api/v1"),
    "groq": ("groq_api_key", "https://api.groq.com/openai/v1"),
    "openrouter": ("openrouter_api_key", "https://openrouter.ai/api/v1"),
    "zhipuai": ("zhipuai_api_key", "https://open.bigmodel.cn/api/paas/v4"),
}

# Provider 到 Profile 的映射
PROVIDER_TO_PROFILE = {
    "google": "research",
    "deepseek": "crawler",
    "anthropic": "coding",
    "siliconflow": "fast",
    "minimax": "cn",
    "kimi": "cn",
    "doubao": "crawler",
    "groq": "fast",
    "openrouter": "fast",
    "zhipuai": "cn",
}


class OpenCodeDaemon:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.running = False
        self.stop_event = Event()
        self.proxy = self._get_proxy()
        self.dispatcher = None
        
    def _get_proxy(self) -> Optional[Dict[str, str]]:
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        
        proxy_dict = {}
        if http_proxy:
            proxy_dict["http"] = http_proxy
        if https_proxy:
            proxy_dict["https"] = https_proxy
        
        return proxy_dict if proxy_dict else None
    
    def load_api_keys(self) -> Dict:
        """加载 API Keys"""
        try:
            if AUTH_CONFIG.exists():
                with open(AUTH_CONFIG, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载 API keys 失败: {e}")
        return {}
    
    def get_current_provider(self) -> Optional[str]:
        """获取当前使用的 provider"""
        try:
            if AUTH_CONFIG.exists():
                with open(AUTH_CONFIG, 'r') as f:
                    data = json.load(f)
                    return data.get("api_provider", "")
        except Exception:
            pass
        return None
    
    def get_provider_key_name(self, provider: str) -> tuple:
        """获取 provider 对应的 key 名称和 base URL"""
        return PROVIDER_CONFIGS.get(provider, ("", ""))
    
    def check_api_health(self, api_key: str, base_url: str, provider: str) -> bool:
        """检查单个 API 是否健康"""
        is_healthy, _ = self.check_api_health_detailed(api_key, base_url, provider)
        return is_healthy
    
    def check_api_health_detailed(self, api_key: str, base_url: str, provider: str) -> tuple:
        """检查 API 健康状态，返回 (是否健康, 是否余额不足)"""
        headers = {"Authorization": f"Bearer {api_key}"}
        
        if provider == "google":
            url = f"{base_url}/v1beta/models?key={api_key}"
        elif provider == "deepseek":
            url = f"{base_url}/v1/models"
        else:
            url = f"{base_url}/models"
        
        try:
            with requests.get(url, headers=headers, timeout=HEALTH_CHECK_TIMEOUT, proxies=self.proxy) as response:
                # 只认可 200 为健康状态
                if response.status_code == 200:
                    return True, False
                
                # 402 表示余额不足
                if response.status_code == 402:
                    return False, True
                    
                # 其他错误码视为不健康
                logger.warning(f"{provider} 健康检查返回 HTTP {response.status_code}")
                    
        except requests.exceptions.Timeout:
            logger.warning(f"{provider} 健康检查超时")
        except Exception as e:
            logger.warning(f"{provider} 健康检查失败: {e}")
        
        return False, False
    
    def auto_startup(self):
        logger.info("🚀 执行启动时模型选择...")
        
        try:
            if not self.dispatcher:
                self.dispatcher = SmartModelDispatcher()
            
            success = self.dispatcher.activate_profile("research")
            if success:
                logger.info("✅ 启动模型加载成功")
            else:
                logger.warning("⚠️ 启动模型加载失败")
                
        except Exception as e:
            logger.error(f"❌ 启动模型加载失败: {e}")
    
    def get_all_providers_health(self) -> Dict[str, bool]:
        """获取所有可用 Provider 的健康状态"""
        health_status = {}
        auth_data = self.load_api_keys()
        
        for provider, (key_name, base_url) in PROVIDER_CONFIGS.items():
            api_key = auth_data.get(key_name, "")
            if api_key:
                is_healthy = self.check_api_health(api_key, base_url, provider)
                health_status[provider] = is_healthy
                logger.info(f"  {provider}: {'✅ 健康' if is_healthy else '❌ 不可用'}")
        
        return health_status
    
    def switch_to_backup(self, current_provider: str, reason: str = "不健康"):
        """切换到备用模型 (基于健康状态)
        
        Args:
            current_provider: 当前provider
            reason: 切换原因 (不健康/余额不足)
        """
        logger.info(f"🔄 正在切换备用模型 (当前: {current_provider}, 原因: {reason})...")
        
        # 先检查所有 provider 的健康状态
        logger.info("📊 检查所有 Provider 健康状态...")
        health_status = self.get_all_providers_health()
        
        # 按健康状态排序: 健康的优先
        healthy_providers = [p for p, is_healthy in health_status.items() if is_healthy]
        
        if not healthy_providers:
            logger.error("❌ 所有 Provider 都不可用")
            return False
        
        logger.info(f"✅ 可用 Provider: {healthy_providers}")
        
        # 切换到第一个健康的 provider
        target_provider = healthy_providers[0]
        
        profile = PROVIDER_TO_PROFILE.get(target_provider, "fast")
        
        try:
            if not self.dispatcher:
                self.dispatcher = SmartModelDispatcher()
            
            success = self.dispatcher.activate_profile(profile)
            if success:
                new_provider = self.get_current_provider()
                logger.info(f"✅ 已切换到备用模型: {new_provider}")
                return True
                
        except Exception as e:
            logger.warning(f"切换失败: {e}")
        
        logger.error("❌ 所有备用模型切换失败")
        return False
    
    def health_check_loop(self):
        """健康检查循环 - 带退避机制"""
        last_known_provider = None
        consecutive_failures = 0  # 连续失败计数
        max_backoff = 300  # 最大退避间隔 5 分钟
        last_startup_time = 0  # 上次 auto_startup 时间，避免频繁触发
        
        while not self.stop_event.is_set():
            try:
                current_provider = self.get_current_provider()
                
                # 如果 provider 变化了，重置失败计数
                if current_provider != last_known_provider:
                    last_known_provider = current_provider
                    consecutive_failures = 0
                
                if not current_provider:
                    if time.time() - last_startup_time > 60:
                        logger.info("当前无固定 provider，使用智能路由模式")
                        last_startup_time = time.time()
                
                # 如果没有固定 provider，就跳过健康检查，直接等待
                if not current_provider:
                    time.sleep(CHECK_INTERVAL)
                    continue
                
                # 加载 keys，使用当前 provider 的特定 key
                auth_data = self.load_api_keys()
                key_name, base_url = self.get_provider_key_name(current_provider)
                api_key = auth_data.get(key_name, "")
                
                if not api_key:
                    logger.warning(f"未找到 {current_provider} 的 API key，执行启动加载...")
                    self.auto_startup()
                    time.sleep(CHECK_INTERVAL)
                    continue
                
                # 检查当前 API 是否健康 (区分余额不足)
                is_healthy, is_balance_insufficient = self.check_api_health_detailed(api_key, base_url, current_provider)
                
                # 余额不足或 API 不健康都需要切换
                if is_balance_insufficient:
                    logger.warning(f"⚠️ {current_provider} 余额不足 (402)，切换到备用模型...")
                    self.switch_to_backup(current_provider, reason="余额不足")
                    consecutive_failures = 0
                elif not is_healthy:
                    consecutive_failures += 1
                    logger.warning(f"⚠️ 当前模型不健康: {current_provider} (连续失败: {consecutive_failures})")
                    self.switch_to_backup(current_provider, reason="不健康")
                else:
                    # 健康检查成功，重置失败计数
                    if consecutive_failures > 0:
                        logger.info(f"✅ 健康检查恢复，连续失败计数已重置")
                    consecutive_failures = 0
                
            except Exception as e:
                logger.error(f"健康检查循环异常: {e}")
                consecutive_failures += 1
            
            # 退避机制: 连续失败时增加间隔
            if consecutive_failures > 2:
                backoff_time = min(CHECK_INTERVAL * (2 ** (consecutive_failures - 2)), max_backoff)
                logger.info(f"⏳ 连续失败 {consecutive_failures} 次，使用退避间隔 {backoff_time}秒")
                time.sleep(backoff_time)
            else:
                time.sleep(CHECK_INTERVAL)
    
    def _signal_handler(self, signum, frame):
        """优雅处理退出信号"""
        logger.info(f"收到信号 {signum}，准备退出...")
        self.stop()
        sys.exit(0)
    
    def start(self, daemon_mode: bool = False):
        """启动守护进程
        
        Args:
            daemon_mode: True 表示真正的后台守护进程，False 表示前台运行(调试用)
        """
        # 注册信号处理器 - 优雅退出
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        if self.is_running():
            logger.warning("守护进程已在运行中")
            return False
        
        if daemon_mode:
            self._daemonize()
        else:
            self._run_foreground()
    
    def _daemonize(self):
        """实现真正的 Unix daemon"""
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"第一次 fork 失败: {e}")
            sys.exit(1)
        
        os.setsid()
        
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"第二次 fork 失败: {e}")
            sys.exit(1)
        
        sys.stdout.flush()
        sys.stderr.flush()
        
        with open('/dev/null', 'r') as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open('/dev/null', 'a+') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())
        
        self.save_pid()
        
        # 设置运行标志 - 修复: 守护进程启动后立即退出的bug
        self.running = True
        
        logger.info("🟢 OpenCode 守护进程已启动 (后台模式)")
        logger.info(f"📁 PID 文件: {PID_FILE}")
        
        self.auto_startup()
        
        health_thread = Thread(target=self.health_check_loop, daemon=True)
        health_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def _run_foreground(self):
        """前台运行模式 (调试用)"""
        self.running = True
        
        self.save_pid()
        
        logger.info("🟢 OpenCode 守护进程启动 (前台模式)")
        logger.info(f"📁 PID 文件: {PID_FILE}")
        
        self.auto_startup()
        
        health_thread = Thread(target=self.health_check_loop, daemon=True)
        health_thread.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到停止信号")
            self.stop()
        
        return True
    
    def stop(self):
        """停止守护进程"""
        self.running = False
        self.stop_event.set()
        
        if PID_FILE.exists():
            PID_FILE.unlink()
        
        logger.info("🔴 OpenCode 守护进程已停止")
    
    def acquire_lock(self) -> Optional[int]:
        """获取排他性文件锁，返回文件描述符"""
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        lock_file = PID_FILE.parent / "daemon.lock"
        try:
            fd = os.open(str(lock_file), os.O_RDWR | os.O_CREAT, 0o666)
            # 非阻塞模式获取排他锁
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except (IOError, OSError):
            # 锁已被占用，获取锁的进程正在运行
            return None
    
    def release_lock(self, fd: int):
        """释放文件锁"""
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        except Exception:
            pass
    
    def save_pid(self):
        """保存 PID (带文件锁)"""
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    
    def is_running(self) -> bool:
        """检查是否已运行 (使用文件锁)"""
        # 先尝试获取锁，如果成功说明没有其他实例
        lock_fd = self.acquire_lock()
        if lock_fd is not None:
            # 获取到锁，说明没有其他实例在运行
            self.release_lock(lock_fd)
            # 清理可能存在的 stale PID 文件
            if PID_FILE.exists():
                PID_FILE.unlink()
            return False
        
        # 未能获取锁，检查PID文件确认进程是否真的在运行
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (FileNotFoundError, ProcessLookupError, ValueError, PermissionError):
            # PID文件不存在或进程已死，清理后认为未运行
            return False
        except Exception:
            return False


def daemon_start():
    """启动守护进程 (后台模式)"""
    daemon = OpenCodeDaemon()
    daemon.start(daemon_mode=True)


def daemon_stop():
    """停止守护进程"""
    try:
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # 先发送 SIGTERM (优雅退出)
            os.kill(pid, signal.SIGTERM)
            print(f"✅ 已发送 SIGTERM 信号到进程 {pid}")
            
            # 等待进程停止 (最多3秒)
            for _ in range(6):
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
            else:
                # 如果进程仍在运行，发送 SIGKILL 强制终止
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"⚠️ 进程未响应，已强制终止")
                except ProcessLookupError:
                    pass
            
            if PID_FILE.exists():
                PID_FILE.unlink()
                
    except FileNotFoundError:
        print("守护进程未运行")
    except ProcessLookupError:
        print("进程不存在，已清理")
    except Exception as e:
        print(f"停止失败: {e}")


def daemon_status():
    """查看状态"""
    daemon = OpenCodeDaemon()
    if daemon.is_running():
        print("🟢 守护进程正在运行")
        
        # 显示当前模型
        current = daemon.get_current_provider()
        if current:
            print(f"📌 当前模型: {current}")
    else:
        print("🔴 守护进程未运行")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCode 守护进程")
    parser.add_argument("command", choices=["start", "stop", "status", "daemon"], 
                        help="命令: start(前台), daemon(后台), stop, status")
    args = parser.parse_args()
    
    if args.command == "daemon":
        daemon_start()
    elif args.command == "start":
        daemon = OpenCodeDaemon()
        daemon.start(daemon_mode=False)
    elif args.command == "stop":
        daemon_stop()
    elif args.command == "status":
        daemon_status()
