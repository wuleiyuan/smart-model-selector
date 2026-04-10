#!/usr/bin/env python3
"""
MiniMax Skill - MiniMax 模型技能
================================
支持 MiniMax M2.7 / M2.5 等模型
"""

import os
import json
import requests
from typing import Generator, Dict, List
from skills.base import BaseModelSkill, SkillRegistry

class MiniMaxSkill(BaseModelSkill):
    """MiniMax 模型技能"""
    
    @property
    def name(self) -> str:
        return "minimax"
    
    @property
    def supported_models(self) -> List[str]:
        return ["minimax", "minimax-m2.7", "minimax-m2.5", "minimax-2.7-pro"]
    
    @property
    def priority(self) -> int:
        return 20  # 次优先级
    
    def stream(self, api_key: str, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """
        MiniMax 流式调用
        """
        model = kwargs.get("model", "MiniMax-M2.7")
        timeout = kwargs.get("timeout", 60)
        
        url = "https://api.minimax.chat/v1/chat/completions"
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
                    # 🩹 P1 修复：拦截底层 [DONE]，防止三重 DONE 冗余
                    if "data: [DONE]" in decoded:
                        continue
                    if decoded.startswith("data:"):
                        # MiniMax 直接返回 SSE 格式，原样转发
                        yield decoded + "\n\n"
            
            # 已经去除了内置的 DONE 返回，由 dispatcher 统一处理
            
        except Exception as e:
            error_chunk = {
                "id": "error",
                "object": "chat.completion.chunk",
                "choices": [{"delta": {"content": f"\n\n> ⚠️ **[MiniMax 引擎异常]**: {str(e)}\n\n"}, "index": 0}]
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            # 🩹 P0 修复：必须抛出异常！激活 dispatcher 故障轮询
            raise e
    
    def health_check(self, api_key: str) -> bool:
        """检查 MiniMax API 是否可用"""
        try:
            url = "https://api.minimax.chat/v1/models"
            headers = {"Authorization": f"Bearer {api_key}"}
            resp = requests.get(url, headers=headers, timeout=10)
            return resp.status_code == 200
        except:
            return False


# 自动注册
SkillRegistry.register(MiniMaxSkill())
