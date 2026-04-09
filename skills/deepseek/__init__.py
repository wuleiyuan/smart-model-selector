#!/usr/bin/env python3
"""
DeepSeek Skill - DeepSeek 模型技能
===================================
支持 DeepSeek V3 / Coder 等模型
"""

import os
import json
import requests
from typing import Generator, Dict, List
from skills.base import BaseModelSkill, SkillRegistry

class DeepSeekSkill(BaseModelSkill):
    """DeepSeek 模型技能"""
    
    @property
    def name(self) -> str:
        return "deepseek"
    
    @property
    def supported_models(self) -> List[str]:
        return ["deepseek", "deepseek-chat", "deepseek-coder", "deepseek-v3"]
    
    @property
    def priority(self) -> int:
        return 30  # 第三优先级
    
    def stream(self, api_key: str, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """
        DeepSeek 流式调用
        """
        model = kwargs.get("model", "deepseek-chat")
        timeout = kwargs.get("timeout", 60)
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }
        
        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(10, timeout),
                stream=True
            )
            resp.raise_for_status()
            
            for line in resp.iter_lines():
                if line:
                    decoded = line.decode("utf-8")
                    if decoded.startswith("data:"):
                        # DeepSeek 直接返回 SSE 格式，原样转发
                        yield decoded + "\n\n"
                    elif decoded == "data: [DONE]":
                        yield "data: [DONE]\n\n"
            
            # 确保结束
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            error_chunk = {
                "id": "error",
                "object": "chat.completion.chunk",
                "choices": [{"delta": {"content": f"[DeepSeek Error] {str(e)[:100]}"}, "index": 0}]
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"
    
    def health_check(self, api_key: str) -> bool:
        """检查 DeepSeek API 是否可用"""
        try:
            url = "https://api.deepseek.com/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            return resp.status_code == 200
        except:
            return False


# 自动注册
SkillRegistry.register(DeepSeekSkill())
