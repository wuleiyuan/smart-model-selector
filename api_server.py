#!/usr/bin/env python3
import json
import logging
import sys
import time
from pathlib import Path
from flask import Flask, request, jsonify, Response, stream_with_context

# 导入你的核心调度器
from smart_model_dispatcher import SmartModelDispatcher

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SmartGateway")

app = Flask(__name__)
dispatcher = SmartModelDispatcher()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "engine": "OpenCode-Smart-Failover"})

@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    data = request.get_json()
    if not data or "messages" not in data:
        return jsonify({"error": "Missing messages"}), 400

    messages = data.get("messages", [])
    model = data.get("model", "auto")
    temperature = data.get("temperature", 0.7)
    max_tokens = data.get("max_tokens", 4096)

    logger.info(f"📥 收到请求: Model={model}, Messages={len(messages)}")

    # 🚀 核心根治逻辑：调用带自动故障转移的请求
    # 它会自动尝试当前 Key，失败则自动切下一张 Key，直到成功或 Key 耗尽
    result = dispatcher.runtime_request_with_failover(
        messages=messages,
        max_retries=5, # 给你 5 次机会，把 7 个 Key 轮一遍
        timeout=60
    )

    if result["success"]:
        content = result["response"]["content"]
        provider = result.get("provider", "unknown")
        actual_model = result.get("model", "unknown")
        
        # 构建 OpenAI 兼容响应
        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": actual_model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop"
            }],
            "usage": {"total_tokens": 0},
            "system_fingerprint": f"opencode-{provider}-failover"
        }
        logger.info(f"✅ 请求成功 (尝试次数: {result['attempts']})")
        return jsonify(response)
    else:
        logger.error(f"❌ 所有 Key 均已失效: {result['error']}")
        return jsonify({"error": {"message": result["error"], "type": "insufficient_quota"}}), 429

if __name__ == "__main__":
    dispatcher.initialize_system()
    app.run(host="0.0.0.0", port=8080, threaded=True)
