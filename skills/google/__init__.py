#!/usr/bin/env python3
"""
Google Skill - Gemini 模型技能
==============================
支持 Gemini 3.1 Pro / 2.5 Pro / 2.5 Flash 等模型
"""

import os
import json
import requests
from typing import Generator, Dict, List
from skills.base import BaseModelSkill, SkillRegistry

class GoogleSkill(BaseModelSkill):
    """Google Gemini 模型技能"""
    
    @property
    def name(self) -> str:
        return "google"
    
    @property
    def supported_models(self) -> List[str]:
        return ["gemini", "gemini-3.1-pro-preview", "gemini-2.5-pro", "gemini-2.5-flash"]
    
    @property
    def priority(self) -> int:
        return 10  # 高优先级
    
    def stream(self, api_key: str, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """
        Google Gemini 流式调用
        """
        model = kwargs.get("model", "gemini-2.5-pro")
        timeout = kwargs.get("timeout", 60)
        
        # 转换消息格式
        gemini_msgs = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            content = m.get("content", "")
            if isinstance(content, str):
                gemini_msgs.append({"role": role, "parts": [{"text": content}]})
            elif isinstance(content, list):
                parts = []
                for part in content:
                    if part.get("type") == "text":
                        parts.append({"text": part["text"]})
                gemini_msgs.append({"role": role, "parts": parts})
            else:
                gemini_msgs.append({"role": role, "parts": [{"text": str(content)}]})
        
        # 构建 URL（使用 v1beta 端点）
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={api_key}"
        
        # 处理代理
        proxies = {
            "http": os.environ.get("HTTP_PROXY", ""),
            "https": os.environ.get("HTTPS_PROXY", "")
        }
        if not proxies.get("http"):
            proxies = None
        
        try:
            resp = requests.post(
                url,
                json={"contents": gemini_msgs},
                timeout=(10, timeout),
                proxies=proxies,
                stream=True
            )
            resp.raise_for_status()
            
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    # 🩹 P1 修复：拦截底层 [DONE]，防止三重 DONE 冗余
                    if "data: [DONE]" in decoded:
                        continue
                    if decoded.startswith("data: "):
                        try:
                            data = json.loads(decoded[6:])
                            # 提取文本内容
                            if "candidates" in data and len(data["candidates"]) > 0:
                                candidate = data["candidates"][0]
                                if "content" in candidate and "parts" in candidate["content"]:
                                    for part in candidate["content"]["parts"]:
                                        if "text" in part:
                                            text = part["text"]
                                            chunk = {
                                                "id": "gemini",
                                                "object": "chat.completion.chunk",
                                                "choices": [{"delta": {"content": text}, "index": 0}]
                                            }
                                            yield f"data: {json.dumps(chunk)}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
            
            # 已经去除了内置的 DONE 返回，由 dispatcher 统一处理
            
        except Exception as e:
            error_chunk = {
                "id": "error",
                "object": "chat.completion.chunk",
                "choices": [{"delta": {"content": f"\n\n> ⚠️ **[Google 引擎异常]**: {str(e)}\n\n"}, "index": 0}]
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            # 🩹 P0 修复：必须抛出异常！激活 dispatcher 故障轮询
            raise e
    
    def health_check(self, api_key: str) -> bool:
        """检查 Google API 是否可用"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            resp = requests.get(url, timeout=10)
            return resp.status_code == 200
        except:
            return False


# 自动注册
SkillRegistry.register(GoogleSkill())
