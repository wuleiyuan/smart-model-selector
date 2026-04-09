#!/usr/bin/env python3
"""
Smart Model Dispatcher - 智能模型调度器 (Skills 解耦版)
==================================================
V6.0 - 肌肉层完全解耦，通过 Skills 系统实现"热插拔"

核心变更：
- 移除了硬编码的 _stream_google / _stream_minimax
- 改为通过 SkillRegistry 动态调用
- 新增模型只需添加到 skills/ 目录，无需修改此文件
"""

import json
import os
import logging
import requests
from pathlib import Path
from typing import Generator, Dict, List

# 尝试挂载大脑和技能系统
try:
    from selector_core import SelectorCore
    HAS_CORE = True
except ImportError:
    HAS_CORE = False

try:
    from skills import auto_register_skills, SkillRegistry
    auto_register_skills()
    HAS_SKILLS = True
except ImportError as e:
    HAS_SKILLS = False
    print(f"[Dispatcher] ⚠️ Skills 系统加载失败: {e}")

logger = logging.getLogger("SmartDispatcher")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('\033[36m%(levelname)s - %(message)s\033[0m'))
    logger.addHandler(ch)


class SmartModelDispatcher:
    """
    智能模型调度器 (Skills 解耦版)
    =================================
    
    工作流程：
    1. 🧠 脑机协同分析 - selector_core 决策用哪个模型
    2. 🎯 Skills 路由 - 根据模型找到对应的技能
    3. 🛡️ 故障转移 - 如果 Key 失效，自动切换下一个
    """
    
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.USER_HOME = Path.home()
        self.AUTH_PATH = self.USER_HOME / ".local" / "share" / "opencode" / "auth.json"
        self.KEYS_PATH = self.BASE_DIR / "keys.json"
        
        self.api_keys: List[Dict] = []
        self.session = requests.Session()
        
        # 初始化大脑
        self.core = SelectorCore() if HAS_CORE else None
        
        # 初始化技能系统
        self._init_skills()
        
        # 初始化系统
        self.initialize_system()
    
    def _init_skills(self):
        """初始化技能系统"""
        if HAS_SKILLS:
            skills = SkillRegistry.list_skills()
            logger.info(f"🧩 Skills 系统已就绪: {skills}")
        else:
            logger.warning("🧩 Skills 系统未加载，使用传统模式")
    
    def initialize_system(self):
        """扫描并加载所有可用的 API Keys"""
        logger.info("🔍 正在扫描本机配置文件...")
        
        # 扫描 keys.json
        if self.KEYS_PATH.exists():
            try:
                with open(self.KEYS_PATH, encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # MiniMax Keys
                    for k in data.get("minimax_paid", []):
                        if k:
                            self.api_keys.append({"provider": "minimax", "key": k})
                    
                    # Google Keys
                    for k in data.get("google_paid", []) + data.get("google_free", []):
                        if k:
                            self.api_keys.append({"provider": "google", "key": k})
                    
                    # DeepSeek Keys
                    for k in data.get("deepseek", []):
                        if isinstance(k, dict):
                            key = k.get("k", "")
                        else:
                            key = k
                        if key:
                            self.api_keys.append({"provider": "deepseek", "key": key})
                            
            except Exception as e:
                logger.error(f"❌ keys.json 读取失败: {e}")
        
        # 扫描 auth.json 作为备选
        if self.AUTH_PATH.exists():
            try:
                with open(self.AUTH_PATH, encoding='utf-8') as f:
                    auth = json.load(f)
                    
                    # MiniMax from auth
                    if not any(k['provider'] == 'minimax' for k in self.api_keys):
                        if auth.get("minimax_api_key"):
                            self.api_keys.append({"provider": "minimax", "key": auth["minimax_api_key"]})
                        elif auth.get("minimax-coding-plan", {}).get("key"):
                            self.api_keys.append({"provider": "minimax", "key": auth["minimax-coding-plan"]["key"]})
                    
                    # Google from auth
                    if not any(k['provider'] == 'google' for k in self.api_keys):
                        if auth.get("api_key"):
                            self.api_keys.append({"provider": "google", "key": auth["api_key"]})
                            
            except Exception as e:
                logger.warning(f"⚠️ auth.json 读取失败: {e}")
        
        # 去重
        seen = set()
        self.api_keys = [x for x in self.api_keys if not (x["key"] in seen or seen.add(x["key"]))]
        
        if not self.api_keys:
            logger.error("🚨 致命错误：未找到任何有效的 API Key！")
        else:
            logger.info(f"✅ 混动引擎点火完毕: 共挂载 {len(self.api_keys)} 个可用 Key")
    
    def dispatch_stream(self, messages, requested_model="auto") -> Generator[str, None, None]:
        """
        核心调度方法 (Skills 解耦版)
        ==============================
        
        工作流程：
        1. 🧠 脑机协同分析 - 决定用哪个模型
        2. 🎯 Skills 路由 - 找到对应的技能
        3. 🛡️ 故障转移 - 自动切换失效的 Key
        """
        preferred_provider = None
        preferred_skill = None
        
        # ===== 阶段 1: 脑机协同分析 =====
        if self.core and (("auto" in requested_model.lower() or not requested_model)):
            try:
                task_text = messages[-1]["content"] if messages else ""
                model_id, reason = self.core.select(task_text)
                logger.info(f"🧠 [大脑分析] {reason} -> 决定使用 {model_id}")
                
                # 向前端流式输出思考过程
                notify = {
                    "id": "brain",
                    "object": "chat.completion.chunk",
                    "choices": [{"delta": {"content": f"> 🧠 **智能调度系统**: {reason} -> 已为您切换至 `{model_id}`\n\n"}, "index": 0}]
                }
                yield f"data: {json.dumps(notify)}\n\n"
                
                # 提取首选供应商
                if "minimax" in model_id.lower():
                    preferred_provider = "minimax"
                elif "deepseek" in model_id.lower():
                    preferred_provider = "deepseek"
                elif "gemini" in model_id.lower() or "google" in model_id.lower():
                    preferred_provider = "google"
                
            except Exception as e:
                logger.warning(f"🧠 大脑分析失败: {e}")
        
        # ===== 阶段 2: Skills 动态路由 =====
        if HAS_SKILLS and preferred_provider:
            preferred_skill = SkillRegistry.get(preferred_provider)
            logger.info(f"🎯 Skills 路由: {preferred_provider} -> {preferred_skill}")
        
        # ===== 阶段 3: 执行与故障转移 =====
        sorted_keys = list(self.api_keys)
        if preferred_provider:
            # 将被大脑选中的提供商 Key 强制排在第一位
            sorted_keys.sort(key=lambda x: x["provider"] != preferred_provider)
        
        last_err = "未知错误"
        for i, api in enumerate(sorted_keys):
            provider = api["provider"]
            api_key = api["key"]
            logger.info(f"🎯 调度引擎 #{i+1} [{provider.upper()}] ...")
            
            # 如果是故障回退触发的，再通知一次前端
            if i > 0:
                notify = {
                    "id": "fallback",
                    "object": "chat.completion.chunk",
                    "choices": [{"delta": {"content": f"\n\n> 🔄 **故障转移**: 检测到限流或超时，已无缝自动切至 `{provider.upper()}` 备用引擎...\n\n"}, "index": 0}]
                }
                yield f"data: {json.dumps(notify)}\n\n"
            
            try:
                # ===== 使用 Skills 系统执行 =====
                if HAS_SKILLS:
                    skill = SkillRegistry.get(provider)
                    if skill:
                        logger.info(f"🧩 使用技能执行: {skill.name}")
                        yield from skill.stream(api_key, messages, model=requested_model)
                        return
                
                # ===== 回退到传统模式（如果 Skills 不可用）=====
                if provider == "minimax":
                    yield from self._stream_minimax(api_key, messages)
                elif provider == "google":
                    yield from self._stream_google(api_key, messages)
                elif provider == "deepseek":
                    yield from self._stream_deepseek(api_key, messages)
                else:
                    raise Exception(f"未知提供商: {provider}")
                
                return
                
            except Exception as e:
                last_err = str(e)
                logger.warning(f"⚠️ [{provider}] 节点熔断: {last_err[:50]}...")
                continue
        
        # ===== 全部失败 =====
        chunk = {
            "id": "error",
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": f"\n\n> 🚨 **系统崩溃**: 全部引擎失效 ({last_err})"}, "index": 0}]
        }
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    # ===== 传统模式回退方法 =====
    
    def _stream_minimax(self, api_key: str, messages: List[Dict]):
        """MiniMax 流式调用（传统回退）"""
        url = "https://api.minimax.chat/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "MiniMax-M2.7", "messages": messages, "stream": True}
        
        resp = self.session.post(url, headers=headers, json=payload, stream=True, timeout=(10, 60))
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data:"):
                    yield decoded + "\n\n"
        
        yield "data: [DONE]\n\n"
    
    def _stream_google(self, api_key: str, messages: List[Dict]):
        """Google Gemini 流式调用（传统回退）"""
        gemini_msgs = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            gemini_msgs.append({"role": role, "parts": [{"text": m["content"]}]})
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:streamGenerateContent?alt=sse&key={api_key}"
        
        proxies = {"http": os.environ.get("HTTP_PROXY", ""), "https": os.environ.get("HTTPS_PROXY", "")}
        if not proxies.get("http"):
            proxies = None
        
        resp = self.session.post(url, json={"contents": gemini_msgs}, timeout=(10, 60), proxies=proxies, stream=True)
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        chunk = {"id": "gemini", "object": "chat.completion.chunk", "choices": [{"delta": {"content": text}, "index": 0}]}
                        yield f"data: {json.dumps(chunk)}\n\n"
                    except:
                        pass
        
        yield "data: [DONE]\n\n"
    
    def _stream_deepseek(self, api_key: str, messages: List[Dict]):
        """DeepSeek 流式调用（传统回退）"""
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": "deepseek-chat", "messages": messages, "stream": True}
        
        resp = self.session.post(url, headers=headers, json=payload, stream=True, timeout=(10, 60))
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data:"):
                    yield decoded + "\n\n"
        
        yield "data: [DONE]\n\n"
