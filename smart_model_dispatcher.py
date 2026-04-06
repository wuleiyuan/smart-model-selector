#!/usr/bin/env python3
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

# 保持原有的配置参数
HEALTH_CHECK_TIMEOUT = 5.0
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3

# 彩色日志
class ColoredFormatter(logging.Formatter):
    COLORS = {'DEBUG': '\033[36m', 'INFO': '\033[32m', 'WARNING': '\033[33m', 'ERROR': '\033[31m', 'CRITICAL': '\033[35m'}
    RESET = '\033[0m'
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)

logger = logging.getLogger("SmartDispatcher")
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter('%(levelname)s - %(message)s'))
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

@dataclass
class APIKey:
    provider: str
    model: str
    key: str
    base_url: str
    tier: str
    def __post_init__(self): self.key = self.key.strip()

class SmartModelDispatcher:
    def __init__(self, config_file_path: Optional[Path] = None):
        self.base_dir = Path(__file__).parent
        self.config_source = config_file_path or (self.base_dir / "api_config.json")
        self.auth_config = Path.home() / ".local" / "share" / "opencode" / "auth.json"
        self.api_keys: List[APIKey] = []
        
        # 代理设置 (保持你的逻辑)
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        self.proxy_sandbox = {"http": http_proxy, "https": http_proxy} if http_proxy else None
        self.session = requests.Session()
        self.initialize_system()

    def initialize_system(self):
        # [核心对齐] 默认 Google 模型升级到 3.1 Pro
        self._load_keys_from_auth()
        logger.info(f"[OK] 调度引擎初始化完成: {len(self.api_keys)} 个 Key 在线")

    def _load_keys_from_auth(self):
        if not self.auth_config.exists(): return
        try:
            with open(self.auth_config, 'r') as f:
                data = json.load(f)
            
            # 加载 Google Pro Keys
            for key in data.get("google_pro_api_keys", []):
                if key: self.api_keys.append(APIKey("google", "gemini-3.1-pro-preview", key, "https://generativelanguage.googleapis.com", "pro"))
            
            # 加载 Google Free Keys
            for key in data.get("google_free_api_keys", []):
                if key: self.api_keys.append(APIKey("google", "gemini-3.1-flash-lite-preview", key, "https://generativelanguage.googleapis.com", "free"))
            
            # 其他 Provider (保持你的映射)
            if data.get("minimax_api_key"):
                self.api_keys.append(APIKey("minimax", "minimax-2.7-pro", data["minimax_api_key"], "https://api.minimax.chat/v1", "auth"))
        except Exception as e:
            logger.error(f"加载 Key 失败: {e}")

    def runtime_request_with_failover(self, messages, model_id="auto", max_retries=5):
        """运行时自动故障转移逻辑"""
        # 简单轮询逻辑，优先使用选定的模型
        target_keys = [k for k in self.api_keys if model_id in k.model or model_id == "auto"]
        if not target_keys: target_keys = self.api_keys # 保底

        for i in range(max_retries):
            api = target_keys[i % len(target_keys)]
            try:
                res = self._make_api_request(api, messages)
                if res: return {"success": True, "response": res, "model": api.model}
            except Exception as e:
                logger.warning(f"🔄 尝试失败 ({api.provider}): {str(e)[:50]}")
                continue
        return {"success": False, "error": "所有重试均已失败"}

    def _make_api_request(self, api: APIKey, messages: List[Dict]):
        # [核心修复] Google API 专用协议转换
        if api.provider == "google":
            # 必须使用 v1beta 且 Key 放在 URL 后面
            url = f"{api.base_url}/v1beta/models/{api.model.split('/')[-1]}:generateContent?key={api.key}"
            headers = {"Content-Type": "application/json"}
            # Google 专用消息格式
            prompt = messages[-1]["content"] if messages else ""
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
        else:
            # OpenAI 标准协议 (MiniMax 等)
            url = f"{api.base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {api.key}", "Content-Type": "application/json"}
            payload = {"model": api.model, "messages": messages}

        # 执行请求
        response = self.session.post(url, headers=headers, json=payload, timeout=30, proxies=self.proxy_sandbox)
        
        if response.status_code == 200:
            data = response.json()
            if api.provider == "google":
                return {"content": data["candidates"][0]["content"]["parts"][0]["text"]}
            else:
                return {"content": data["choices"][0]["message"]["content"]}
        
        raise Exception(f"HTTP {response.status_code}: {response.text[:100]}")

if __name__ == "__main__":
    dispatcher = SmartModelDispatcher()
    print("Dispatcher Ready.")
