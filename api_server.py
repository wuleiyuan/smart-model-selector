#!/usr/bin/env python3
"""
OpenCode Smart Model Selector - API Server
提供 OpenAI 兼容的 HTTP API 接口，可作为 Openclaw 的模型供应商

支持端点:
- POST /v1/chat/completions - 聊天完成
- GET  /v1/models - 获取可用模型列表
- GET  /health - 健康检查
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from typing import Dict, Any, Optional

# 添加项目根目录到 Python 路径
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from smart_model_dispatcher import SmartModelDispatcher
from model_selector import SmartModelSelector

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_server")

# 尝试导入 Flask
try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    logger.warning("Flask not installed. Install with: pip install flask")


class APIServer:
    """OpenCode API Server - OpenAI 兼容接口"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080):
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        
        # 初始化调度器
        self.dispatcher = SmartModelDispatcher()
        self.model_selector = SmartModelSelector()
        
        # 注册路由
        self._register_routes()
        
        logger.info(f"API Server 初始化完成: {host}:{port}")
    
    def _register_routes(self):
        """注册 API 路由"""
        
        @self.app.route("/health", methods=["GET"])
        def health():
            """健康检查"""
            return jsonify({"status": "ok", "service": "opencode-api-server"})
        
        @self.app.route("/v1/models", methods=["GET"])
        def list_models():
            """获取可用模型列表"""
            models = []
            for model_id, model in self.model_selector.MODELS.items():
                if model.available:
                    models.append({
                        "id": model_id,
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": model.provider,
                        "provider": model.provider
                    })
            
            return jsonify({
                "object": "list",
                "data": models
            })
        
        @self.app.route("/v1/chat/completions", methods=["POST"])
        def chat_completions():
            """聊天完成 - 核心接口"""
            try:
                data = request.get_json()
                
                if not data:
                    return jsonify({
                        "error": {
                            "message": "Request body is required",
                            "type": "invalid_request_error",
                            "code": "missing_request_body"
                        }
                    }), 400
                
                # 提取消息
                messages = data.get("messages", [])
                if not messages:
                    return jsonify({
                        "error": {
                            "message": "messages is required",
                            "type": "invalid_request_error",
                            "code": "missing_messages"
                        }
                    }), 400
                
                # 提取模型
                model = data.get("model", "gemini-1.5-pro")
                
                # 提取其他参数
                temperature = data.get("temperature", 0.7)
                max_tokens = data.get("max_tokens", 4096)
                stream = data.get("stream", False)
                
                # 构建任务描述
                task_description = self._build_task_description(messages)
                
                # 选择模型
                if model == "auto" or model == "smart-select":
                    # 智能选择
                    selected_model, reason = self.model_selector.select(task_description)
                    model_id = selected_model.id
                    provider = selected_model.provider
                    logger.info(f"智能选择: {model_id} ({provider}) - {reason}")
                else:
                    # 指定模型
                    model_id = model
                    provider = self._get_provider_from_model(model)
                
                # 调用 API
                response = self._call_api(
                    provider=provider,
                    model=model_id,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                if stream:
                    return self._stream_response(response, model_id)
                
                # 构建响应
                return self._build_response(response, model_id, messages)
                
            except Exception as e:
                logger.error(f"Chat completions error: {e}")
                return jsonify({
                    "error": {
                        "message": str(e),
                        "type": "internal_error",
                        "code": "internal_error"
                    }
                }), 500
        
        @self.app.route("/", methods=["GET"])
        def root():
            """根路径"""
            return jsonify({
                "name": "OpenCode API Server",
                "version": "1.0.0",
                "description": "OpenAI compatible API for OpenCode Smart Model Selector"
            })
    
    def _build_task_description(self, messages: list) -> str:
        """从消息构建任务描述"""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"[{role}]: {content}")
        return "\n".join(parts)
    
    def _get_provider_from_model(self, model: str) -> str:
        """从模型名推断提供商"""
        model_lower = model.lower()
        
        if "claude" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower:
            return "google"
        elif "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "deepseek" in model_lower:
            return "deepseek"
        elif "qwen" in model_lower or "silicon" in model_lower:
            return "siliconflow"
        elif "minimax" in model_lower:
            return "minimax"
        else:
            return "google"  # 默认
    
    def _call_api(self, provider: str, model: str, messages: list, 
                  temperature: float, max_tokens: int) -> Dict[str, Any]:
        """调用 API"""
        
        # 使用调度器的预检逻辑
        self.dispatcher.initialize_system()
        
        # 构建请求格式
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 根据提供商构建请求
        if provider == "anthropic":
            return self._call_anthropic(model, messages, temperature, max_tokens)
        elif provider == "google":
            return self._call_google(model, messages, temperature, max_tokens)
        elif provider == "openai":
            return self._call_openai(model, messages, temperature, max_tokens)
        elif provider == "deepseek":
            return self._call_deepseek(model, messages, temperature, max_tokens)
            return self._call_google(model, messages, temperature, max_tokens)
    
    def _find_valid_key(self, provider: str) -> Optional[str]:
        """查找指定提供商的有效 API Key"""
        # 初始化系统
        self.dispatcher.initialize_system()
        
        # 查找该 provider 的 key
        for api in self.dispatcher.api_keys:
            if api.provider == provider:
                return api.key
        
        return None

    def _call_anthropic(self, model: str, messages: list, 
                        temperature: float, max_tokens: int) -> Dict[str, Any]:
        """调用 Anthropic API"""
        api_key = self._find_valid_key("anthropic")
        if not api_key:
            raise Exception("No valid Anthropic API key available")
        
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # 转换消息格式
        anthropic_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue  # Anthropic 不支持 system 角色
            anthropic_messages.append({
                "role": role,
                "content": msg.get("content", "")
            })
        
        payload = {
            "model": model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        url = "https://api.anthropic.com/v1/messages"
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            return {
                "id": f"chatcmpl-{data.get('id', 'unknown')}",
                "object": "chat.completion",
                "created": data.get("created_time", int(__import__("time").time())),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": data.get("content", [{}])[0].get("text", "")
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": data.get("usage", {}).get("input_tokens", 0),
                    "completion_tokens": data.get("usage", {}).get("output_tokens", 0),
                    "total_tokens": sum(data.get("usage", {}).values())
                }
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Anthropic API error: {e}")
    
    def _call_google(self, model: str, messages: list,
                     temperature: float, max_tokens: int) -> Dict[str, Any]:
        api_key = self._find_valid_key("google")
        if not api_key:
            raise Exception("No valid Google API key available")
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        # 转换消息格式
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            # Google 使用 user/model 而不是 user/assistant
            google_role = "user" if role == "user" else "model"
            contents.append({
                "role": google_role,
                "parts": [{"text": msg.get("content", "")}]
            })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            
            if "candidates" not in data:
                raise Exception(f"Google API error: {data}")
            
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            return {
                "id": f"chatcmpl-google-{int(__import__("time").time())}",
                "object": "chat.completion",
                "created": int(__import__("time").time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": data.get("usageMetadata", {}).get("promptTokenCount", 0),
                    "completion_tokens": data.get("usageMetadata", {}).get("candidatesTokenCount", 0),
                    "total_tokens": data.get("usageMetadata", {}).get("totalTokenCount", 0)
                }
            }
        except requests.exceptions.RequestException as e:
            raise Exception(f"Google API error: {e}")
    
    def _call_openai(self, model: str, messages: list,
                     temperature: float, max_tokens: int) -> Dict[str, Any]:
        api_key = self._find_valid_key("openai")
        if not api_key:
            raise Exception("No valid OpenAI API key available")
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenAI API error: {e}")
    
    def _call_deepseek(self, model: str, messages: list,
                       temperature: float, max_tokens: int) -> Dict[str, Any]:
        api_key = self._find_valid_key("deepseek")
        if not api_key:
            raise Exception("No valid DeepSeek API key available")
        
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"DeepSeek API error: {e}")
    
    def _build_response(self, response: Dict[str, Any], model: str, 
                        messages: list) -> Dict[str, Any]:
        """构建响应"""
        return jsonify(response)
    
    def _stream_response(self, response: Dict[str, Any], model: str):
        """流式响应（暂不支持）"""
        return jsonify({
            "error": {
                "message": "Streaming not supported yet",
                "type": "invalid_request_error",
                "code": "streaming_not_supported"
            }
        }), 400
    
        logger.info(f"启动 API Server: http://{self.host}:{self.port}")
        # 尝试使用 gunicorn 提高并发性能
        try:
            import gunicorn
            # gunicorn 方式启动
            from gunicorn.app.wsgiapp import WSGIApplication
            logger.info("使用 gunicorn 并发服务器")
            WSGIApplication("__main__:app").run()
        except ImportError:
            # 降级到 Flask 内置服务器
            logger.warning("gunicorn 未安装，使用 Flask 内置服务器")
            self.app.run(host=self.host, port=self.port, debug=False, threaded=True)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="OpenCode Smart Model Selector - API Server"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0",
        help="监听地址 (默认: 0.0.0.0)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8080,
        help="监听端口 (默认: 8080)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="调试模式"
    )
    
    args = parser.parse_args()
    
    if not FLASK_AVAILABLE:
        print("错误: 请先安装 Flask")
        print("  pip install flask")
        sys.exit(1)
    
    server = APIServer(host=args.host, port=args.port)
    server.run()


if __name__ == "__main__":
    main()
