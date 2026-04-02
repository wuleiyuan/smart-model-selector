#!/usr/bin/env python3
"""
智能模型调度引擎 V1.0
核心功能：对接 api_config.json，自动清洗脏Key，实现动态路由
Author: OpenCode Smart Model Dispatcher
"""

import json
import logging
import requests
import sys
import fcntl
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import os
from typing import List, Dict, Any, Optional, Union
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from logging.handlers import RotatingFileHandler

# 可配置参数
HEALTH_CHECK_TIMEOUT = float(os.environ.get("OPENCODE_HEALTH_TIMEOUT", "3.0"))
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# 动态超时配置
MIN_TIMEOUT = 2.0
MAX_TIMEOUT = 10.0
TIMEOUT_SAMPLE_SIZE = 10
TIMEOUT_WEIGHT = 0.7

class TimeoutTracker:
    """动态超时追踪器 - 基于历史响应时间调整超时 (使用中位数算法)
    
    支持测速记忆持久化 - 重启后热启动
    """
    
    CACHE_FILE = Path.home() / ".local" / "share" / "opencode" / "latency_cache.json"
    
    def __init__(self):
        self._history: Dict[str, List[float]] = {}
        self._load_cache()  # 热启动：加载历史测速数据
    
    def _load_cache(self):
        """从磁盘加载历史测速数据"""
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    # 检查缓存是否过期（超过4小时）
                    cache_time = data.get("updated_at", 0)
                    current_time = int(time.time())
                    cache_age = current_time - cache_time
                    
                    if cache_age > 4 * 3600:  # 4小时 = 14400秒
                        logger.info(f"⏰ 测速缓存已过期 ({cache_age // 3600}h)，重新探测")
                        self._history = {}
                        return
                    
                    # [核心修复] 真正将磁盘数据加载到内存中，激活热启动
                    self._history = data.get("history", {})
                    
                    logger.info(f"[OK] 加载测速缓存: {len(self._history)} 个 provider (缓存 {cache_age // 60} 分钟有效)")
        except Exception as e:
            logger.debug(f"测速缓存加载失败: {e}")
        """从磁盘加载历史测速数据"""
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    # 检查缓存是否过期（超过4小时）
                    cache_time = data.get("updated_at", 0)
                    current_time = int(time.time())
                    cache_age = current_time - cache_time
                    
                    if cache_age > 4 * 3600:  # 4小时 = 14400秒
                        logger.info(f"⏰ 测速缓存已过期 ({cache_age // 3600}h)，重新探测")
                        self._history = {}
                        return
                    
                    logger.info(f"[OK] 加载测速缓存: {len(self._history)} 个 provider (缓存 {cache_age // 60} 分钟有效)")
                cache_time = data.get("updated_at", 0)
                current_time = int(time.time())
                cache_age = current_time - cache_time
                
                if cache_age > 4 * 3600:  # 4小时 = 14400秒
                    logger.info(f"⏰ 测速缓存已过期 ({cache_age // 3600}h)，重新探测")
                    self._history = {}
                    return
                
                logger.info(f"[OK] 加载测速缓存: {len(self._history)} 个 provider (缓存 {cache_age // 60} 分钟有效)")
        except Exception as e:
            logger.debug(f"测速缓存加载失败: {e}")
    
    def save_cache(self):
        """保存测速数据到磁盘"""
        try:
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"history": self._history, "updated_at": int(time.time())}
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.debug(f"测速缓存保存失败: {e}")
    
    def record(self, provider: str, response_time: float):
        if provider not in self._history:
            self._history[provider] = []
        self._history[provider].append(response_time)
        if len(self._history[provider]) > TIMEOUT_SAMPLE_SIZE:
            self._history[provider].pop(0)
        # 自动保存缓存 (每 10 次记录)
        if sum(len(v) for v in self._history.values()) % 10 == 0:
            self.save_cache()
    
    def _get_median(self, values: List[float]) -> float:
        """计算中位数，过滤离群值"""
        if not values:
            return HEALTH_CHECK_TIMEOUT
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        return sorted_values[n // 2]
    
    def get_timeout(self, provider: str) -> float:
        if provider not in self._history or not self._history[provider]:
            return HEALTH_CHECK_TIMEOUT
        
        median_time = self._get_median(self._history[provider])
        dynamic_timeout = median_time * TIMEOUT_WEIGHT * 2
        
        return max(MIN_TIMEOUT, min(MAX_TIMEOUT, dynamic_timeout))

timeout_tracker = TimeoutTracker()

# ═════════════════════════════════════════════════════════════
# JSON 配置容错机制
# ═════════════════════════════════════════════════════════════

def safe_json_load(file_path: Path, default: dict = None) -> dict:
    """安全加载 JSON 文件，带自动回退机制
    
    Args:
        file_path: JSON 文件路径
        default: 加载失败时返回的默认值
        
    Returns:
        解析后的字典，加载失败返回 default
    """
    if default is None:
        default = {}
    
    backup_path = file_path.with_suffix(file_path.suffix + ".backup")
    
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ JSON 解析失败 {file_path}: {e}")
        # 尝试加载备份
        try:
            if backup_path.exists():
                with open(backup_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.info(f"[OK] 已从备份恢复: {backup_path}")
                return data
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"⚠️ JSON 加载失败 {file_path}: {e}")
    
    return default

def safe_json_save(file_path: Path, data: dict) -> bool:
    """安全保存 JSON 文件，自动创建备份
    
    Args:
        file_path: JSON 文件路径
        data: 要保存的数据
        
    Returns:
        是否保存成功
    """
    try:
        # 先创建备份
        if file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + ".backup")
            import shutil
            shutil.copy2(file_path, backup_path)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"❌ JSON 保存失败 {file_path}: {e}")
        return False

# 彩色日志Formatter
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)

# 配置日志 (带滚动)
log_dir = Path.home() / ".config" / "opencode"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "dispatcher.log"

file_handler = RotatingFileHandler(
    log_file, 
    maxBytes=LOG_MAX_BYTES, 
    backupCount=LOG_BACKUP_COUNT
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'))

console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter('%(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger("SmartDispatcher")

class ModelProfile(Enum):
    RESEARCH = "research"    # 主力 (Gemini 3 Pro)
    CRAWLER = "crawler"     # 吞吐 (DeepSeek/Doubao)
    CODING = "coding"      # 专家 (Claude/Qwen)
    FAST = "fast"          # 极速 (Groq/Flash)
    CN = "cn"              # 中文 (MinMax)

@dataclass
class APIKey:
    """API key configuration with validation metadata"""
    provider: str
    model: str
    key: str
    base_url: str
    tier: str  # primary, secondary, backup, expert
    
    def __post_init__(self) -> None:
        """Strip whitespace from API key after initialization"""
        self.key = self.key.strip()
    
    def __str__(self) -> str:
        """Safe string representation (hides sensitive key)"""
        return f"APIKey(provider={self.provider}, model={self.model}, key=...{self.key[-4:] if len(self.key) > 4 else '****'})"

class SmartModelDispatcher:
    """Intelligent model dispatcher with automatic failover and load balancing"""
    
    def __init__(self, config_file_path: Optional[Path] = None) -> None:
        """Initialize the dispatcher with optional custom config path
        
        Args:
            config_file_path: Optional path to custom configuration file
        """
        # 1. 定位配置文件
        self.base_dir = Path(__file__).parent
        self.config_source: Path = config_file_path or (self.base_dir / "api_config.json")
        self.opencode_config: Path = Path.home() / ".config" / "opencode" / "opencode.json"
        self.auth_config: Path = Path.home() / ".local" / "share" / "opencode" / "auth.json"
        
        self.api_keys: List[APIKey] = []
        self._routing_config: Dict[ModelProfile, List[str]] = {
            ModelProfile.RESEARCH: ["google"],
            ModelProfile.CODING: ["anthropic", "siliconflow", "google"],
            ModelProfile.CRAWLER: ["deepseek", "minimax"],
            ModelProfile.FAST: ["siliconflow", "deepseek", "google"],  # 多个免费 provider
            ModelProfile.CN: ["siliconflow", "minimax"]
        }
        
        # [修复] 网络层强制隔离：定义代理沙箱
        # 从环境变量读取代理配置，若未设置则不使用代理
        import os as _os
        
        http_proxy = _os.environ.get('HTTP_PROXY') or _os.environ.get('http_proxy') or _os.environ.get('HTTPS_PROXY')
        https_proxy = _os.environ.get('HTTPS_PROXY') or _os.environ.get('https_proxy') or _os.environ.get('HTTP_PROXY')
        
        # 使用 None 表示无代理（requests 库标准做法）
        proxy_dict: dict[str, str] = {}
        if http_proxy:
            proxy_dict["http"] = http_proxy
        if https_proxy:
            proxy_dict["https"] = https_proxy
        self.proxy_sandbox = proxy_dict if proxy_dict else None
        
        # 创建 requests.Session 连接池 (复用 TCP 连接)
        self.session = requests.Session()
        
        # 清理命名空间
        del _os
        
        self.initialize_system()

    # ═════════════════════════════════════════════════════════════
    # 用户显式指定模型检测 (优先级最高)
    # ═════════════════════════════════════════════════════════════
    
    def is_user_specified_model(self) -> bool:
        """检查用户是否显式指定了模型（优先级最高，同时检查过期）"""
        # 先检查是否过期
        if self.is_user_specified_expired():
            return False
        try:
            if self.auth_config.exists():
                with open(self.auth_config, 'r') as f:
                    auth_data = json.load(f)
                return auth_data.get("user_specified_model", False) is True
        except Exception:
            pass
        return False
    
    def clear_user_specified_model(self) -> None:
        """清除用户显式指定标记，允许自动切换"""
        try:
            if self.auth_config.exists():
                with open(self.auth_config, 'r') as f:
                    auth_data = json.load(f)
            else:
                auth_data = {}
            
            if "user_specified_model" in auth_data:
                del auth_data["user_specified_model"]
            if "specified_model" in auth_data:
                del auth_data["specified_model"]
            
            self.auth_config.parent.mkdir(parents=True, exist_ok=True)
            with open(self.auth_config, 'w') as f:
                json.dump(auth_data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ 清除用户指定标记失败: {e}")
    
    def _set_user_specified_flag(self, provider: str, model: str, ttl_hours: int = 24) -> None:
        """设置用户显式指定模型标记（带TTL有效期）
        
        Args:
            provider: 模型提供商
            model: 模型名称
            ttl_hours: 有效期（小时），默认 24 小时
        """
        import time
        try:
            if self.auth_config.exists():
                with open(self.auth_config, 'r') as f:
                    auth_data = json.load(f)
            else:
                auth_data = {}
            
            auth_data["user_specified_model"] = True
            auth_data["specified_model"] = f"{provider}/{model}"
            auth_data["specified_at"] = int(time.time())  # 设置时间戳
            auth_data["specified_ttl"] = ttl_hours * 3600  # 转换为秒
            auth_data["consecutive_failures"] = 0  # 重置连续失败计数
            
            self.auth_config.parent.mkdir(parents=True, exist_ok=True)
            with open(self.auth_config, 'w') as f:
                json.dump(auth_data, f, indent=2)
            logger.info(f"[OK] 用户指定模型标记已设置: {provider}/{model} (有效期 {ttl_hours} 小时)")
        except Exception as e:
            logger.warning(f"⚠️ 设置用户指定标记失败: {e}")
    
    def is_user_specified_expired(self) -> bool:
        """检查用户指定模型是否过期"""
        import time
        try:
            if self.auth_config.exists():
                with open(self.auth_config, 'r') as f:
                    auth_data = json.load(f)
                specified_at = auth_data.get("specified_at", 0)
                ttl = auth_data.get("specified_ttl", 24 * 3600)  # 默认 24 小时
                if time.time() - specified_at > ttl:
                    logger.info("⏰ 用户指定模型已过期，恢复智能模式")
                    self.clear_user_specified_model()
                    return True
        except Exception:
            pass
        return False
    
    def record_failure(self) -> bool:
        """记录连续失败次数，超过阈值后自动切换智能模式
        
        Returns:
            True if should switch to smart mode
        """
        MAX_FAILURES = 3  # 连续失败 3 次后切换
        try:
            if self.auth_config.exists():
                with open(self.auth_config, 'r') as f:
                    auth_data = json.load(f)
                
                failures = auth_data.get("consecutive_failures", 0) + 1
                auth_data["consecutive_failures"] = failures
                
                with open(self.auth_config, 'w') as f:
                    json.dump(auth_data, f, indent=2)
                
                if failures >= MAX_FAILURES:
                    logger.warning(f"⚠️ 指定模型连续失败 {failures} 次，自动切换智能模式")
                    self.clear_user_specified_model()
                    return True
                else:
                    logger.info(f"⚠️ 指定模型调用失败 ({failures}/{MAX_FAILURES})")
        except Exception:
            pass
        return False
    
    def record_success(self) -> bool:
        """成功后重置失败计数"""
        try:
            if self.auth_config.exists():
                with open(self.auth_config, 'r') as f:
                    auth_data = json.load(f)
                if auth_data.get("consecutive_failures", 0) > 0:
                    auth_data["consecutive_failures"] = 0
                    with open(self.auth_config, 'w') as f:
                        json.dump(auth_data, f, indent=2)
        except Exception:
            pass

    def _validate_google_key(self, key: str) -> bool:
        """Validate Google API key format
        
        Args:
            key: API key to validate
            
        Returns:
            True if key matches Google format, False otherwise
        """
        if not key or len(key) < 20:
            return False
        
        # Google Gemini API keys must start with "AIzaSy" (standard API key format)
        # OAuth client IDs (AQ.Ab...) are NOT valid for Gemini API
        if key.startswith("AQ.Ab"):
            logger.debug(f"⏭️ 跳过 OAuth Client ID (非 Gemini API Key): {key[:15]}...")
            return False
        
        return (
            key.startswith("AIzaSyDum") or  # AI Studio keys
            key.startswith("AIzaSy") and len(key) >= 35  # Standard keys
        )
    
    def _validate_anthropic_key(self, key: str) -> bool:
        """Validate Anthropic API key format
        
        Args:
            key: API key to validate
            
        Returns:
            True if key matches Anthropic format, False otherwise
        """
        return bool(key and key.startswith("sk-ant") and len(key) >= 40)
    
    def _validate_deepseek_key(self, key: str) -> bool:
        """Validate DeepSeek API key format
        
        Args:
            key: API key to validate
            
        Returns:
            True if key matches DeepSeek format, False otherwise
        """
        return bool(key and key.startswith("sk-de2bd") and len(key) == 32)
    
    def _validate_siliconflow_key(self, key: str) -> bool:
        """Validate SiliconFlow API key format
        
        Args:
            key: API key to validate
            
        Returns:
            True if key matches SiliconFlow format, False otherwise
        """
        return bool(key and key.startswith("sk-yyeh") and len(key) >= 40)
    
    def _load_provider_keys(self, raw_keys: Dict[str, Any], provider: str, config_key: str, 
                           validator_func, model: str, base_url: str, tier: str) -> None:
        """Load and validate keys for a specific provider
        
        Args:
            raw_keys: Raw configuration dictionary
            provider: Provider name (e.g., "google", "anthropic")
            config_key: Key in config file for this provider
            validator_func: Function to validate API key format
            model: Model identifier for this provider
            base_url: Base URL for API requests
            tier: Provider tier (primary, secondary, etc.)
        """
        try:
            for key in raw_keys.get(config_key, []):
                # Skip comment lines and empty strings
                if isinstance(key, str) and (key.strip().startswith('#') or not key.strip()):
                    continue
                    
                if validator_func(key):
                    self.api_keys.append(APIKey(
                        provider=provider,
                        model=model,
                        key=key,
                        base_url=base_url,
                        tier=tier
                    ))
        except Exception as e:
            logger.warning(f"⚠️ Failed to load {provider} keys: {str(e)}")

    def initialize_system(self) -> None:
        """Initialize the smart dispatcher by loading and validating API keys
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        if not self.config_source.exists():
            logger.error(f"❌ 找不到配置文件: {self.config_source}")
            raise FileNotFoundError(f"配置文件不存在: {self.config_source}")

        try:
            with open(self.config_source, 'r', encoding='utf-8') as f:
                data = json.load(f)
            raw_keys = data.get("api_keys", {})
            
            # Load provider-specific keys with validation
            self._load_provider_keys(
                raw_keys, "google", "gemini_pro_paid", self._validate_google_key,
                "google/gemini-2.0-pro-exp", "https://generativelanguage.googleapis.com", "primary"
            )
            
            self._load_provider_keys(
                raw_keys, "anthropic", "openai_claude", self._validate_anthropic_key,
                "anthropic/claude-3.5-sonnet", "https://api.anthropic.com/v1", "expert"
            )
            
            self._load_provider_keys(
                raw_keys, "deepseek", "deepseek", self._validate_deepseek_key,
                "deepseek-chat", "https://api.deepseek.com", "secondary"
            )
            
            self._load_provider_keys(
                raw_keys, "siliconflow", "siliconflow", self._validate_siliconflow_key,
                "Qwen/Qwen2.5-72B-Instruct", "https://api.siliconflow.cn/v1", "secondary"
            )
            
            # Load other models with custom logic
            self._load_other_models(raw_keys.get("other_models", []))
            
            # [新增] 从 auth.json 加载真实密钥
            self._load_keys_from_auth()
            
            logger.info(f"[OK] System initialized: {len(self.api_keys)} valid keys loaded")
            
        except json.JSONDecodeError as e:
            logger.error(f"[FAIL] Config JSON error: {str(e)}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"[FAIL] Init failed: {str(e)}")
            sys.exit(1)
    
    def _load_keys_from_auth(self) -> None:
        """Load API keys from secure auth.json and environment variables"""
        
        # Step 1: Load from environment variables (优先级高)
        env_loaded = self._load_keys_from_env()
        
        # Step 2: Load from auth.json (补充)
        json_loaded = self._load_keys_from_auth_json() or 0
        
        total = (env_loaded or 0) + (json_loaded or 0)
        if total > 0:
            logger.info(f"[OK] Loaded {total} keys from auth sources")
        else:
            logger.warning("[!] No valid API keys found")
    
    def _load_keys_from_env(self) -> int:
        """Load API keys from environment variables"""
        loaded_count = 0
        
        # Google API Keys (支持数组格式)
        google_keys = os.environ.get("GOOGLE_API_KEYS", "")
        if google_keys:
            # 解析数组格式: ("key1" "key2" ...)
            import re
            keys = re.findall(r'"([^"]+)"', google_keys) or google_keys.split()
            for key in keys:
                key = key.strip()
                if key and self._validate_google_key(key):
                    exists = any(k.key == key for k in self.api_keys)
                    if not exists:
                        self.api_keys.append(APIKey(
                            provider="google",
                            model="google/gemini-1.5-flash",
                            base_url="https://generativelanguage.googleapis.com",
                            key=key,
                            tier="env"
                        ))
                        loaded_count += 1
        
        # OpenAI API Keys
        openai_keys = os.environ.get("OPENAI_API_KEYS", "")
        if openai_keys:
            import re
            keys = re.findall(r'"([^"]+)"', openai_keys) or openai_keys.split()
            for key in keys:
                key = key.strip()
                if key and len(key) > 10:
                    exists = any(k.key == key for k in self.api_keys)
                    if not exists:
                        self.api_keys.append(APIKey(
                            provider="openai",
                            model="gpt-4o",
                            base_url="https://api.openai.com/v1",
                            key=key,
                            tier="env"
                        ))
                        loaded_count += 1
        
        # Single API Key 环境变量
        single_key_map = {
            "ANTHROPIC_API_KEY": ("anthropic", "anthropic/claude-3.5-sonnet", "https://api.anthropic.com/v1"),
            "DEEPSEEK_API_KEY": ("deepseek", "deepseek-chat", "https://api.deepseek.com"),
            "SILICONFLOW_API_KEY": ("siliconflow", "Qwen/Qwen2.5-72B-Instruct", "https://api.siliconflow.cn/v1"),
            "MINIMAX_API_KEY": ("minimax", "MiniMax-M2.1-lightning", "https://api.minimax.chat/v1"),
            "KIMI_API_KEY": ("kimi", "moonshot-v1-8k", "https://api.moonshot.cn/v1"),
            "DOUBAO_API_KEY": ("doubao", "doubao-pro-32k", "https://ark.cn-beijing.volces.com/api/v1"),
            "GROQ_API_KEY": ("groq", "llama-3.1-70b", "https://api.groq.com/openai/v1"),
            "OPENROUTER_API_KEY": ("openrouter", "openrouter/auto", "https://openrouter.ai/api/v1"),
            "OPENAI_API_KEY": ("openai", "gpt-4o", "https://api.openai.com/v1"),
            "ZHIPU_API_KEY": ("zhipuai", "glm-4", "https://open.bigmodel.cn/api/paas/v4"),
            "MODELSCOPE_API_KEY": ("modelscope", "modelscope/qwen2.5-72b-instruct", "https://api.modelscope.cn/v1"),
        }
        
        for env_name, (provider, model, base_url) in single_key_map.items():
            key = os.environ.get(env_name, "")
            if key and len(key) > 10:
                exists = any(k.key == key for k in self.api_keys)
                if not exists:
                    self.api_keys.append(APIKey(
                        provider=provider,
                        model=model,
                        base_url=base_url,
                        key=key,
                        tier="env"
                    ))
                    loaded_count += 1
        
        if loaded_count > 0:
            logger.info(f"[OK] Loaded {loaded_count} keys from environment variables")
        
        return loaded_count
    
    def _load_keys_from_auth_json(self) -> int:
        try:
            if not self.auth_config.exists():
                logger.warning("[!] auth.json not found")
                return
            
            with open(self.auth_config, 'r', encoding='utf-8') as f:
                auth_data = json.load(f)
            
            # Map auth keys to dispatcher providers (flat format: google_api_key -> google)
            provider_map = {
                "anthropic_api_key": ("anthropic", "anthropic/claude-3.5-sonnet", "https://api.anthropic.com/v1"),
                "deepseek_api_key": ("deepseek", "deepseek-chat", "https://api.deepseek.com"),
                "siliconflow_api_key": ("siliconflow", "Qwen/Qwen2.5-72B-Instruct", "https://api.siliconflow.cn/v1"),
                "minimax_api_key": ("minimax", "MiniMax-M2.1-lightning", "https://api.minimax.chat/v1"),
                "zhipuai_api_key": ("zhipuai", "glm-4", "https://open.bigmodel.cn/api/paas/v4"),
                "kimi_api_key": ("kimi", "moonshot-v1-8k", "https://api.moonshot.cn/v1"),
                "doubao_api_key": ("doubao", "doubao-pro-32k", "https://ark.cn-beijing.volces.com/api/v1"),
                "groq_api_key": ("groq", "llama-3.1-70b", "https://api.groq.com/openai/v1"),
                "qiniuyun_api_key": ("qiniuyun", "qwen-turbo", "https://openai.qiniu.com"),
                "openrouter_api_key": ("openrouter", "openrouter/auto", "https://openrouter.ai/api/v1"),
                "opencode_api_key": ("opencode", "opencode/gpt-4o", "https://api.opencode.ai/v1"),
            }
            
            loaded_count = 0
            
            # Load Google Pro API Keys (array format)
            if "google_pro_api_keys" in auth_data:
                pro_keys = auth_data["google_pro_api_keys"]
                if isinstance(pro_keys, list):
                    for i, key in enumerate(pro_keys):
                        if key and len(key) > 10 and self._validate_google_key(key):
                            exists = any(k.key == key for k in self.api_keys)
                            if not exists:
                                self.api_keys.append(APIKey(
                                    provider="google",
                                    model="google/gemini-1.5-pro",
                                    base_url="https://generativelanguage.googleapis.com",
                                    key=key,
                                    tier="pro"
                                ))
                                loaded_count += 1
            
            # Load Google Free API Keys (array format)
            if "google_free_api_keys" in auth_data:
                free_keys = auth_data["google_free_api_keys"]
                if isinstance(free_keys, list):
                    for key in free_keys:
                        if key and len(key) > 10 and self._validate_google_key(key):
                            exists = any(k.key == key for k in self.api_keys)
                            if not exists:
                                self.api_keys.append(APIKey(
                                    provider="google",
                                    model="google/gemini-1.5-flash",
                                    base_url="https://generativelanguage.googleapis.com",
                                    key=key,
                                    tier="free"
                                ))
                                loaded_count += 1
            
            # Load legacy single Google API key (backward compatibility)
            if "google_api_key" in auth_data:
                key = auth_data["google_api_key"]
                if key and len(key) > 10 and self._validate_google_key(key):
                    exists = any(k.key == key for k in self.api_keys)
                    if not exists:
                        self.api_keys.append(APIKey(
                            provider="google",
                            model="google/gemini-1.5-flash",
                            base_url="https://generativelanguage.googleapis.com",
                            key=key,
                            tier="auth"
                        ))
                        loaded_count += 1
            
            # Load other providers
            for auth_key, (provider, model, base_url) in provider_map.items():
                if auth_key in auth_data:
                    key = auth_data[auth_key]
                    if key and len(key) > 10:
                        # 检查是否已存在
                        exists = any(k.key == key for k in self.api_keys)
                        if not exists:
                            self.api_keys.append(APIKey(
                                provider=provider,
                                model=model,
                                key=key,
                                base_url=base_url,
                                tier="auth"
                            ))
                            loaded_count += 1
            
            if loaded_count > 0:
                logger.info(f"[OK] Loaded {loaded_count} keys from auth.json")
            else:
                logger.warning("[!] No valid keys found in auth.json")
                
        except Exception as e:
            logger.warning(f"[!] Failed to load from auth.json: {str(e)}")
    
    def _load_other_models(self, other_keys: List[str]) -> None:
        """Load and validate other model keys
        
        Args:
            other_keys: List of keys from "other_models" config section
        """
        for key in other_keys:
            # Skip comment lines and invalid entries
            if not isinstance(key, str) or key.strip().startswith('#') or len(key.strip()) < 20:
                continue
                
            key = key.strip()
            
            try:
                # 根据key特征自动识别provider
                # 注意：不要硬编码具体key值，而是通过API验证来判断
                if self._validate_google_key(key):
                    # Google备用 (Flash model)
                    self.api_keys.append(APIKey(
                        provider="google",
                        model="google/gemini-1.5-flash",
                        key=key,
                        base_url="https://generativelanguage.googleapis.com",
                        tier="backup"
                    ))
                # 其他未知key，跳过
            except Exception as e:
                logger.warning(f"⚠️ Failed to load other model key {key[:10]}...: {str(e)}")

    def _build_request_headers(self, api: APIKey) -> dict[str, str]:
        """Build appropriate headers for different providers"""
        if api.provider == "google":
            return {}
        elif api.provider == "anthropic":
            return {"x-api-key": api.key}
        else:
            return {"Authorization": f"Bearer {api.key}"}
    
    def _build_test_url(self, api: APIKey) -> str:
        """Build test URL for different providers"""
        if api.provider == "google":
            return f"{api.base_url}/v1beta/models?key={api.key}"
        elif api.provider == "anthropic":
            return f"{api.base_url}/messages"
        else:
            return f"{api.base_url}/models"
    
    def _get_proxies(self, provider: str) -> Optional[Dict[str, str]]:
        """获取代理配置 - 国产模型强制直连（物理级流量绕行）"""
        # 国内模型列表 - 这些域名在国内，直接连接无代理
        domestic_providers = {"deepseek", "minimax", "kimi", "doubao", "zhipuai", "siliconflow", "qiniuyun", "modelscope"}
        
        if provider in domestic_providers:
            # 显式注入空代理，实现物理级的流量绕行
            # 这样即使环境变量设置了代理，也会强制直连
            return {"http": "", "https": ""}
        
        return self.proxy_sandbox
    
    def pre_flight_check(self, api: APIKey) -> bool:
        """Perform connectivity test with dynamic timeout"""
        start_time = time.time()
        
        dynamic_timeout = timeout_tracker.get_timeout(api.provider)
        
        headers = self._build_request_headers(api)
        url = self._build_test_url(api)
        
        if api.provider == "anthropic":
            headers["anthropic-version"] = "2023-06-01"
        
        proxies = self._get_proxies(api.provider)
        
        try:
            with self.session.get(url, headers=headers, timeout=dynamic_timeout, proxies=proxies) as response:
                response_time = time.time() - start_time
                timeout_tracker.record(api.provider, response_time)
                
                if response.status_code in [200, 404]:
                    logger.info(f"✅ {api.provider} 连接成功 ({response_time:.2f}s)")
                    return True
                elif response.status_code == 401:
                    logger.error(f"🔑 {api.provider} 认证失败 (401)")
                elif response.status_code == 403:
                    logger.error(f"🚫 {api.provider} 访问被拒绝 (403)")
                elif response.status_code == 429:
                    logger.warning(f"⏱️ {api.provider} 触发频率限制 (429)")
                elif response.status_code >= 500:
                    logger.error(f"🖥️ {api.provider} 服务器错误 ({response.status_code})")
                else:
                    logger.warning(f"⚡ {api.provider} 连接异常 (Status: {response.status_code})")
                
                return False
        except requests.exceptions.Timeout:
            logger.warning(f"⏰ {api.provider} 连接超时 (>{dynamic_timeout:.1f}秒)")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"🔌 {api.provider} 网络连接错误: {str(e)[:80]}")
            return False
        except Exception as e:
            logger.warning(f"❓ {api.provider} 未知错误: {str(e)[:80]}")
            return False

    # 用户显式指定模型 > profile 命令，但 profile 命令可以清除它
    def _clear_user_specified_for_profile(self) -> None:
        """profile 命令清除用户指定标记"""
        if self.is_user_specified_model():
            specified = ""
            try:
                with open(self.auth_config, 'r') as f:
                    specified = json.load(f).get("specified_model", "")
            except:
                pass
            logger.info(f"ℹ️ 检测到用户切换 profile，清除指定模型: {specified}")
            self.clear_user_specified_model()

    def activate_profile(self, profile_name: str) -> bool:
        # profile 命令清除用户指定标记，允许自动切换
        self._clear_user_specified_for_profile()

        try:
            profile = ModelProfile(profile_name)
        except ValueError:
            logger.error(f"❌ 未知模式: {profile_name}")
            logger.info(f"📋 可用模式: {[p.value for p in ModelProfile]}")
            return False

        target_providers = self._routing_config.get(profile, [])
        logger.info(f"🚀 [{profile.value}] 模式并发检测中...")

        candidates = []
        for provider in target_providers:
            provider_candidates = [api for api in self.api_keys if api.provider == provider]
            if provider_candidates:
                candidates.extend(provider_candidates)
            else:
                logger.warning(f"⚠️ 没有找到 {provider} 的API密钥")
        
        if not candidates:
            logger.error("❌ 无可用 API 密钥")
            return False

        max_workers = min(32, len(candidates))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_api = {executor.submit(self.pre_flight_check, api): api for api in candidates}
            
            for future in as_completed(future_to_api):
                api = future_to_api[future]
                try:
                    is_healthy = future.result()
                    if is_healthy:
                        self._write_config(api)
                        logger.info(f"🎉 竞速胜出: {api.provider} | Model: {api.model}")
                        return True
                except Exception as e:
                    logger.debug(f"API {api.provider} check error: {e}")
                    continue
        
        logger.error("❌ 所有候选大脑均无法连接!")
        return False
    
    def set_specific_model(self, full_model_string: str, skip_health_check: bool = False) -> bool:
        """直接设置指定的模型，可选健康检测
        
        Args:
            full_model_string: 模型字符串 (provider/model)
            skip_health_check: 是否跳过健康检测（默认 False，执行检测）
        """
        try:
            if "/" not in full_model_string:
                logger.error(f"❌ 模型格式错误: {full_model_string} (应为 provider/model)")
                return False
            
            provider, model_name = full_model_string.split("/", 1)
            
            # 从已加载的 keys 中查找对应 provider 的 key
            api_key = ""
            base_url = ""
            for k in self.api_keys:
                if k.provider == provider and k.key:
                    api_key = k.key
                    base_url = k.base_url
                    break
            
            # 如果没找到，从 auth.json 查找
            if not api_key and self.auth_config.exists():
                try:
                    with open(self.auth_config, 'r') as f:
                        auth_data = json.load(f)
                    key_name = f"{provider}_api_key"
                    api_key = auth_data.get(key_name, "")
                    # 获取对应的 base_url
                    provider_map = {
                        "google": "https://generativelanguage.googleapis.com",
                        "anthropic": "https://api.anthropic.com/v1",
                        "deepseek": "https://api.deepseek.com",
                        "siliconflow": "https://api.siliconflow.cn/v1",
                        "minimax": "https://api.minimax.chat/v1",
                    }
                    base_url = provider_map.get(provider, "")
                except Exception:
                    pass
            
            # 如果仍然没有 key，报错
            if not api_key:
                logger.error(f"❌ 未找到 {provider} 的 API Key，请确保已配置")
                return False
            
            api = APIKey(
                provider=provider,
                model=model_name,
                key=api_key,
                base_url=base_url,
                tier="specific"
            )
            
            # [改进] 健康检测 - 如果模型不可用则报错
            if not skip_health_check:
                logger.info(f"🔍 正在检测模型可用性: {provider}/{model_name}...")
                if not self.pre_flight_check(api):
                    logger.error(f"❌ 模型不可用: {provider}/{model_name}，请检查 API 或选择其他模型")
                    return False
                logger.info(f"✅ 模型可用性检测通过")
            
            self._write_config(api)
            # [优先级修复] 显式指定模型时设置标记（带 24 小时有效期）
            self._set_user_specified_flag(provider, model_name, ttl_hours=24)
            logger.info(f"🎯 精确锁定模型: {provider}/{model_name} (有效期 24 小时)")
            return True
            
        except Exception as e:
            logger.error(f"❌ 设置特定模型失败: {e}")
            return False
    
    def _write_config(self, api: APIKey) -> None:
        lock_file = Path("/tmp/opencode_dispatcher.lock")
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        lock_fd = open(lock_file, 'w')
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            try:
                self._write_config_unlocked(api)
            finally:
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            lock_fd.close()
    
    def _write_config_unlocked(self, api: APIKey) -> None:
        try:
            if self.opencode_config.exists():
                with open(self.opencode_config, 'r', encoding='utf-8') as f:
                    main_config = json.load(f)
            else:
                main_config = {}

            # [安全修复] 强制清洗可能潜伏在任何地方的 apiKey
            if "provider" in main_config:
                for p in list(main_config.get("provider", {}).keys()):
                    if isinstance(main_config["provider"].get(p), dict) and "apiKey" in main_config["provider"][p]:
                        del main_config["provider"][p]["apiKey"]
            # 清洗顶层非法字段
            for illegal_key in ["keys", "apiKey", "google_api_key"]:
                if illegal_key in main_config:
                    del main_config[illegal_key]

            main_config["$schema"] = "https://opencode.ai/config.json"
            main_config["model"] = f"{api.provider}/{api.model}"
            if "plugin" not in main_config:
                main_config["plugin"] = ["oh-my-opencode@latest"]
            
            self.opencode_config.parent.mkdir(parents=True, exist_ok=True)
            temp_file = self.opencode_config.with_suffix(".tmp")
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(main_config, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.opencode_config)
            os.chmod(self.opencode_config, 0o600)
            
            self.auth_config.parent.mkdir(parents=True, exist_ok=True)
            
            auth_data = {}
            if self.auth_config.exists():
                try:
                    with open(self.auth_config, 'r') as f:
                        auth_data = json.load(f)
                except Exception:
                    pass
            
            # 只更新当前 provider 的 key，保留其他 provider 的 keys
            if api.key:  # 只有非空 key 才更新
                auth_data[f"{api.provider}_api_key"] = api.key
            auth_data["api_key"] = api.key if api.key else auth_data.get(f"{api.provider}_api_key", "")
            auth_data["api_base_url"] = api.base_url
            auth_data["api_provider"] = api.provider
            
            temp_auth = self.auth_config.with_suffix(".auth.tmp")
            with open(temp_auth, 'w') as f:
                json.dump(auth_data, f, indent=2)
            temp_auth.replace(self.auth_config)
            os.chmod(self.auth_config, 0o600)

            logger.info(f"[OK] Config updated: Model -> {api.model}")
            logger.info(f"[OK] Credentials injected: {api.provider} -> auth.json")
            
        except IOError as e:
            logger.error(f"[FAIL] Config write failed (IO): {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[FAIL] Config write failed: {str(e)}")
            raise

    # ═════════════════════════════════════════════════════════════
    # 运行时故障转移 (Runtime Failover)
    # ═════════════════════════════════════════════════════════════
    
    def get_current_api_key(self) -> Optional[APIKey]:
        try:
            if self.auth_config.exists():
                with open(self.auth_config, 'r') as f:
                    auth_data = json.load(f)
                
                key = auth_data.get("api_key", "")
                
                for api in self.api_keys:
                    if api.key == key:
                        return api
                return None
        except Exception:
            pass
        return None
    
    def get_fallback_keys(self, current_key: str, max_count: int = 3) -> List[APIKey]:
        """获取备用 API Keys 列表
        
        Args:
            current_key: 当前使用的 key
            max_count: 返回的最大备用数量
            
        Returns:
            备用 API Keys 列表
        """
        # 按优先级排序: pro > secondary > backup > expert > free
        priority_order = {"pro": 0, "primary": 1, "secondary": 2, "backup": 3, "expert": 4, "free": 5, "env": 1, "specific": 2}
        
        available_keys = [k for k in self.api_keys if k.key != current_key]
        available_keys.sort(key=lambda x: priority_order.get(x.tier, 99))
        
        return available_keys[:max_count]
    
    def runtime_request_with_failover(
        self, 
        messages: List[Dict[str, str]],
        max_retries: int = 3,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """运行时请求 with 自动故障转移
        
        当遇到以下错误时自动切换到备用模型:
        - 502 Bad Gateway
        - 504 Gateway Timeout
        - 429 Too Many Requests (限流)
        - Connection Error (连接失败)
        - Timeout (超时)
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            max_retries: 最大重试次数
            timeout: 请求超时时间(秒)
            
        Returns:
            {
                "success": bool,
                "response": Response data or None,
                "error": Error message or None,
                "fallback_used": 是否使用了备用模型,
                "attempts": 尝试次数
            }
        """
        # 获取当前配置的 key
        current_api = self.get_current_api_key()
        
        if not current_api:
            logger.error("❌ 无法获取当前 API 配置")
            return {
                "success": False,
                "response": None,
                "error": "No API key configured",
                "fallback_used": False,
                "attempts": 0
            }
        
        # 获取备用 keys
        fallback_keys = self.get_fallback_keys(current_api.key, max_retries)
        
        all_keys_to_try = [current_api] + fallback_keys
        
        logger.info(f"🚀 开始请求 (共 {len(all_keys_to_try)} 个候选)")
        
        last_error = None
        for attempt_idx, api in enumerate(all_keys_to_try):
            try:
                is_fallback = attempt_idx > 0
                if is_fallback:
                    logger.warning(f"🔄 尝试备用模型 {attempt_idx + 1}/{len(all_keys_to_try)}: {api.provider}/{api.model}")
                
                # 构建请求
                response = self._make_api_request(api, messages, timeout)
                
                if response:
                    if is_fallback:
                        logger.info(f"✅ 备用模型成功! Provider: {api.provider}")
                    return {
                        "success": True,
                        "response": response,
                        "error": None,
                        "fallback_used": is_fallback,
                        "attempts": attempt_idx + 1,
                        "provider": api.provider,
                        "model": api.model
                    }
                    
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                
                # 判断错误类型
                if "502" in error_msg or "Bad Gateway" in error_msg:
                    logger.warning(f"❌ {api.provider} 返回 502 Bad Gateway")
                elif "504" in error_msg or "Gateway Timeout" in error_msg:
                    logger.warning(f"❌ {api.provider} 返回 504 Gateway Timeout")
                elif "429" in error_msg or "Too Many Requests" in error_msg:
                    logger.warning(f"❌ {api.provider} 触发限流 (429)")
                elif "timeout" in error_msg.lower():
                    logger.warning(f"⏰ {api.provider} 请求超时")
                elif "connection" in error_msg.lower():
                    logger.warning(f"🔌 {api.provider} 连接失败")
                else:
                    logger.warning(f"❓ {api.provider} 未知错误: {error_msg[:50]}")
                
                # 继续尝试下一个
                continue
        
        # 所有 key 都失败
        logger.error("❌ 所有模型均失败，无法完成请求")
        return {
            "success": False,
            "response": None,
            "error": last_error or "All models failed",
            "fallback_used": True,
            "attempts": len(all_keys_to_try)
        }
    
    def _make_api_request(
        self, 
        api: APIKey, 
        messages: List[Dict[str, str]],
        timeout: int = 60
    ) -> Optional[Dict[str, Any]]:
        headers = {
            "Content-Type": "application/json"
        }
        
        if api.provider == "anthropic":
            headers["x-api-key"] = api.key
            headers["anthropic-version"] = "2023-06-01"
        elif api.provider in ["openai", "deepseek", "siliconflow", "minimax", "kimi", "doubao", "groq", "qiniuyun", "openrouter"]:
            headers["Authorization"] = f"Bearer {api.key}"
        elif api.provider == "google":
            headers["Authorization"] = f"Bearer {api.key}"
        elif api.provider == "zhipuai":
            headers["Authorization"] = f"Bearer {api.key}"
        
        payload: Dict[str, Any] = {
            "messages": messages
        }
        
        if api.provider == "anthropic":
            payload["model"] = api.model.replace("anthropic/", "")
            payload["max_tokens"] = 4096
        elif api.provider == "google":
            payload["model"] = api.model
            payload["generationConfig"] = {
                "temperature": 0.9,
                "maxOutputTokens": 8192,
                "topP": 0.95,
                "topK": 40
            }
        else:
            payload["model"] = api.model
        
        if api.provider == "google":
            url = f"{api.base_url}/v1beta/models/{api.model.replace('google/', '')}:generateContent"
        else:
            url = f"{api.base_url}/chat/completions"
        
        # 统一代理策略：所有请求使用相同代理配置
        proxies = self.proxy_sandbox
        
        try:
            with self.session.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=timeout,
                proxies=proxies
            ) as response:
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                    except ValueError:
                        raise Exception(f"Invalid JSON response: {response.text[:100]}")
                    
                    if api.provider == "google":
                        candidates = data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts:
                                return {"content": parts[0].get("text", ""), "raw": data}
                    else:
                        choices = data.get("choices", [])
                        if choices:
                            return {"content": choices[0].get("message", {}).get("content", ""), "raw": data}
                    
                    return {"content": "", "raw": data}
                    
                elif response.status_code == 401:
                    raise Exception("401 Unauthorized - API Key invalid")
                elif response.status_code == 402:
                    raise Exception("402 Payment Required - Insufficient balance")
                elif response.status_code == 403:
                    raise Exception("403 Forbidden - Access denied")
                elif response.status_code == 429:
                    raise Exception("429 Too Many Requests - Rate limited")
                elif response.status_code == 502:
                    raise Exception("502 Bad Gateway")
                elif response.status_code == 504:
                    raise Exception("504 Gateway Timeout")
                elif response.status_code >= 500:
                    raise Exception(f"{response.status_code} Server Error")
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:100]}")
        except requests.exceptions.Timeout:
            raise Exception("Request timeout")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Connection error: {str(e)}")
        except Exception as e:
            raise

def export_env():
    """导出环境变量供 Shell 脚本使用
    
    使用方式:
        # 方式1: eval (推荐)
        eval $(python3 smart_model_dispatcher.py --export-env)
        
        # 方式2: source (需要管道)
        source <(python3 smart_model_dispatcher.py --export-env)
        
        # 方式3: 直接运行后手动 export
        python3 smart_model_dispatcher.py --export-env
    """
    import json
    import shlex
    auth_config = Path.home() / ".local" / "share" / "opencode" / "auth.json"
    
    auth_data = {}
    if auth_config.exists():
        try:
            with open(auth_config, 'r') as f:
                auth_data = json.load(f)
        except Exception:
            pass
    
    # 导出有效的环境变量 - 使用 shlex.quote 确保安全的 shell 转义
    for key in ["google_api_key", "openai_api_key", "anthropic_api_key", 
                 "deepseek_api_key", "siliconflow_api_key", "minimax_api_key",
                 "zhipuai_api_key", "kimi_api_key", "doubao_api_key"]:
        value = auth_data.get(key, "")
        if value:
            # 转换为大写并输出 export 命令
            env_name = key.upper()
            # 使用 shlex.quote 进行安全的 shell 转义
            safe_value = shlex.quote(value)
            print(f"export {env_name}={safe_value}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 smart_model_dispatcher.py [profile]       (e.g., research, fast, coding)")
        print("  python3 smart_model_dispatcher.py --set [model]   (e.g., google/gemini-1.5-flash)")
        print("  python3 smart_model_dispatcher.py --export-env     (导出环境变量供 Shell 使用)")
        sys.exit(1)
    
    if sys.argv[1] == "--export-env":
        export_env()
        sys.exit(0)
    
    dispatcher = SmartModelDispatcher()
    
    if sys.argv[1] == "--set" and len(sys.argv) > 2:
        success = dispatcher.set_specific_model(sys.argv[2])
    else:
        success = dispatcher.activate_profile(sys.argv[1])
    
    sys.exit(0 if success else 1)