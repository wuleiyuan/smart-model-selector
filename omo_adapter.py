#!/usr/bin/env python3
"""
OMO (oh-my-openagent) Platform Adapter

V5.1.0 - 修复流式输出 "Unexpected EOF" 错误

问题根因:
1. Stream 输出 chunk 终止符不匹配
2. 缺少必要的响应头 (Content-Type, X-Request-Id)
3. JSON 未正确关闭就发送

解决方案:
1. 使用正确的 SSE (Server-Sent Events) 格式
2. 确保所有响应头正确设置
3. JSON 完全序列化和关闭后再传输
"""

import json
import time
import uuid
import logging
from typing import Dict, Any, Optional

from base_adapter import (
    BaseAPIServerAdapter,
    build_task_from_messages,
    create_error_response,
    create_success_response
)

logger = logging.getLogger("omo_adapter")


class OMOAdapter(BaseAPIServerAdapter):
    """OMO (oh-my-openagent) API 适配器"""

    STREAM_CHUNK_DELIMITER = "\n\n"

    def __init__(self):
        super().__init__("omo")

    def parse_request(self, raw_input: Any) -> Dict[str, Any]:
        if isinstance(raw_input, dict):
            messages = raw_input.get("messages", [])
            model = raw_input.get("model", "auto")
            task_description = build_task_from_messages(messages)

            return {
                "task_description": task_description,
                "model": model,
                "temperature": raw_input.get("temperature", 0.7),
                "max_tokens": raw_input.get("max_tokens", 4096),
                "stream": raw_input.get("stream", False),
                "metadata": {
                    "source": "omo_api",
                    "provider": "omo"
                }
            }
        return {"task_description": str(raw_input), "metadata": {}}

    def format_response(self, core_output: Dict[str, Any]) -> Any:
        return core_output

    def format_error(self, error: Exception) -> Any:
        return create_error_response(str(error), "omo_selection_error")

    def parse_chat_request(self, request_data: Dict) -> Dict[str, Any]:
        if not request_data:
            raise ValueError("Request body is required")

        messages = request_data.get("messages", [])
        if not messages:
            raise ValueError("messages is required")

        model = request_data.get("model", "auto")
        temperature = request_data.get("temperature", 0.7)
        max_tokens = request_data.get("max_tokens", 4096)
        stream = request_data.get("stream", False)

        task_description = build_task_from_messages(messages)

        return {
            "task_description": task_description,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "metadata": {
                "source": "omo_chat",
                "provider": "omo"
            }
        }

    def format_chat_response(self, model: str, content: str,
                            metadata: Optional[Dict] = None) -> Dict:
        response = create_success_response(model, content, metadata)
        response["provider"] = "omo"
        return response

    def format_stream_chunk(self, model: str, content: str,
                           chunk_index: int = 0) -> str:
        request_id = f"omo-{uuid.uuid4().hex[:8]}"
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
        chunk = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
        logger.debug(f"[OMO] Stream chunk: {chunk[:100]}...")
        return chunk

    def format_stream_end(self) -> str:
        return "data: [DONE]\n\n"

    def format_stream_error(self, error_message: str, request_id: str = None) -> str:
        if request_id is None:
            request_id = f"omo-{uuid.uuid4().hex[:8]}"
        error_data = {
            "error": {
                "message": error_message,
                "type": "streaming_error",
                "code": "stream_error"
            }
        }
        return f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    def validate_response_headers(self, headers: Dict) -> Dict:
        required_headers = {
            "Content-Type": "application/json",
            "X-Request-Id": f"omo-{uuid.uuid4().hex[:8]}",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
        for key, value in required_headers.items():
            if key not in headers:
                headers[key] = value
        return headers

    def format_model_list(self, models: Dict[str, Dict]) -> Dict:
        data = []
        for model_id, info in models.items():
            data.append({
                "id": model_id,
                "object": "model",
                "created": 1700000000,
                "owned_by": info.get("provider", "smart-selector"),
                "provider": info.get("provider", "omo")
            })
        return {
            "object": "list",
            "data": data
        }

    def health_response(self) -> Dict:
        return {
            "status": "ok",
            "service": "Smart Model Selector",
            "platform": "omo",
            "version": "5.1.0"
        }


def create_chat_completion(adapter: OMOAdapter, core,
                          request_data: Dict) -> Dict:
    try:
        parsed = adapter.parse_chat_request(request_data)

        if parsed["model"] == "auto" or parsed["model"] == "smart-select":
            model_id, reason = core.select(parsed["task_description"])
        else:
            model_id = parsed["model"]
            reason = "用户指定"

        model_info = core.registry.get_model(model_id)
        provider = model_info.provider if model_info else "unknown"

        logger.info(f"[OMO] 选择模型: {model_id} ({provider}) - {reason}")

        return {
            "model": model_id,
            "provider": provider,
            "reason": reason
        }

    except Exception as e:
        logger.error(f"OMO 选择失败: {e}")
        return adapter.format_error(e)


def main():
    from pathlib import Path
    SCRIPT_DIR = Path(__file__).parent
    import sys
    sys.path.insert(0, str(SCRIPT_DIR))

    from selector_core import SelectorCore

    adapter = OMOAdapter()
    core = SelectorCore()

    test_request = {
        "model": "auto",
        "messages": [
            {"role": "user", "content": "帮我写一个排序算法"}
        ]
    }

    result = create_chat_completion(adapter, core, test_request)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()