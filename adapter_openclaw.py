#!/usr/bin/env python3
"""
OpenClaw Platform Adapter - OpenClaw 平台适配器

V3.0.0 - 通用架构

负责处理 OpenClaw API 请求，解析 JSON 格式，与 Core 交互。
"""

import json
import time
import logging
from typing import Dict, Any, Optional

from base_adapter import (
    BaseAPIServerAdapter, 
    build_task_from_messages, 
    create_error_response,
    create_success_response
)

logger = logging.getLogger("adapter_openclaw")


class OpenClawAdapter(BaseAPIServerAdapter):
    """OpenClaw API 适配器"""
    
    def __init__(self):
        super().__init__("openclaw")
    
    def parse_request(self, raw_input: Any) -> Dict[str, Any]:
        """
        解析 OpenClaw 请求
        
        Args:
            raw_input: 原始请求
        
        Returns:
            标准请求格式
        """
        if isinstance(raw_input, dict):
            # 提取消息
            messages = raw_input.get("messages", [])
            model = raw_input.get("model", "auto")
            
            # 构建任务描述
            task_description = build_task_from_messages(messages)
            
            return {
                "task_description": task_description,
                "model": model,
                "temperature": raw_input.get("temperature", 0.7),
                "max_tokens": raw_input.get("max_tokens", 4096),
                "stream": raw_input.get("stream", False),
                "metadata": {
                    "source": "openclaw_api",
                    "provider": "openclaw"
                }
            }
        
        return {"task_description": str(raw_input), "metadata": {}}
    
    def format_response(self, core_output: Dict[str, Any]) -> Any:
        """
        格式化响应
        
        Args:
            core_output: Core 返回的结果
        
        Returns:
            格式化后的响应
        """
        return core_output
    
    def format_error(self, error: Exception) -> Any:
        """
        格式化错误
        
        Args:
            error: 异常对象
        
        Returns:
            错误响应
        """
        return create_error_response(str(error), "openclaw_selection_error")
    
    def parse_chat_request(self, request_data: Dict) -> Dict[str, Any]:
        """
        解析聊天完成请求
        
        OpenAI 兼容格式:
        {
            "model": "auto",
            "messages": [{"role": "user", "content": "..."}],
            "temperature": 0.7,
            "max_tokens": 4096,
            "stream": false
        }
        
        Args:
            request_data: API 请求体
        
        Returns:
            标准请求格式
        """
        # 验证必要字段
        if not request_data:
            raise ValueError("Request body is required")
        
        messages = request_data.get("messages", [])
        if not messages:
            raise ValueError("messages is required")
        
        # 提取参数
        model = request_data.get("model", "auto")
        temperature = request_data.get("temperature", 0.7)
        max_tokens = request_data.get("max_tokens", 4096)
        stream = request_data.get("stream", False)
        
        # 构建任务描述
        task_description = build_task_from_messages(messages)
        
        return {
            "task_description": task_description,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "metadata": {
                "source": "openclaw_chat",
                "provider": "openclaw"
            }
        }
    
    def format_chat_response(self, model: str, content: str, 
                            metadata: Optional[Dict] = None) -> Dict:
        """
        格式化聊天响应
        
        OpenAI 兼容格式
        
        Args:
            model: 模型 ID
            content: 响应内容
            metadata: 元数据
        
        Returns:
            OpenAI 兼容的响应
        """
        return create_success_response(model, content, metadata)
    
    def format_stream_chunk(self, model: str, content: str, 
                           chunk_index: int = 0) -> str:
        """
        格式化流式响应块
        
        SSE (Server-Sent Events) 格式
        
        Args:
            model: 模型 ID
            content: 内容块
            chunk_index: 块索引
        
        Returns:
            SSE 格式的数据块
        """
        import time
        
        data = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": chunk_index,
                "delta": {
                    "content": content
                },
                "finish_reason": None
            }]
        }
        
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    
    def format_stream_end(self) -> str:
        """
        格式化流式响应结束
        
        Returns:
            结束标记
        """
        return "data: [DONE]\n\n"
    
    def list_models_response(self, models: Dict[str, Dict]) -> Dict:
        """
        格式化模型列表响应
        
        Args:
            models: 模型字典
        
        Returns:
            OpenAI 兼容的模型列表
        """
        data = []
        
        for model_id, info in models.items():
            data.append({
                "id": model_id,
                "object": "model",
                "created": 1700000000,
                "owned_by": info.get("provider", "smart-selector"),
                "provider": info.get("provider", "smart-selector")
            })
        
        return {
            "object": "list",
            "data": data
        }
    
    def health_response(self) -> Dict:
        """
        健康检查响应
        
        Returns:
            健康状态
        """
        return {
            "status": "ok",
            "service": "Smart Model Selector",
            "platform": "openclaw",
            "version": "4.0.0"
        }


# ============ 辅助函数 ============

def create_chat_completion(adapter: OpenClawAdapter, core, 
                          request_data: Dict) -> Dict:
    """
    创建聊天完成响应
    
    Args:
        adapter: OpenClaw 适配器
        core: 选择器核心
        request_data: 请求数据
    
    Returns:
        响应字典
    """
    try:
        # 解析请求
        parsed = adapter.parse_chat_request(request_data)
        
        # 选择模型
        if parsed["model"] == "auto" or parsed["model"] == "smart-select":
            model_id, reason = core.select(parsed["task_description"])
        else:
            model_id = parsed["model"]
            reason = "用户指定"
        
        # 获取模型信息
        model_info = core.registry.get_model(model_id)
        provider = model_info.provider if model_info else "unknown"
        
        logger.info(f"[OpenClaw] 选择模型: {model_id} ({provider}) - {reason}")
        
        # 返回选择结果
        return {
            "model": model_id,
            "provider": provider,
            "reason": reason
        }
        
    except Exception as e:
        logger.error(f"OpenClaw 选择失败: {e}")
        return adapter.format_error(e)


# ============ 主函数 ============

def main():
    """测试入口"""
    import sys
    sys.path.insert(0, "/Users/leiyuanwu/GitHub/opencode-smart-model-selector")
    
    from selector_core import SelectorCore
    
    adapter = OpenClawAdapter()
    core = SelectorCore()
    
    # 测试请求
    test_request = {
        "model": "auto",
        "messages": [
            {"role": "user", "content": "帮我写一个排序算法"}
        ]
    }
    
    # 解析并选择
    result = create_chat_completion(adapter, core, test_request)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
