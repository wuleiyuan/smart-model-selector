from flask import Flask, request, jsonify, Response
from smart_model_dispatcher import SmartModelDispatcher

app = Flask(__name__)
dispatcher = SmartModelDispatcher()

@app.route('/v1/models', methods=['GET'])
def list_models():
    """提供 OpenAI 兼容的模型列表接口，供 OMO 插件加载"""
    models = [
        {"id": "auto", "object": "model", "owned_by": "smart-selector"},
        {"id": "smart-select", "object": "model", "owned_by": "smart-selector"},
        {"id": "gemini-3.1-pro-preview", "object": "model", "owned_by": "google"},
        {"id": "gemini-2.5-pro", "object": "model", "owned_by": "google"},
        {"id": "gemini-2.5-flash", "object": "model", "owned_by": "google"},
        {"id": "deepseek-coder", "object": "model", "owned_by": "deepseek"},
        {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
        {"id": "minimax-m2.7", "object": "model", "owned_by": "minimax"},
        {"id": "gpt-4o", "object": "model", "owned_by": "openai"},
        {"id": "claude-3-5-sonnet", "object": "model", "owned_by": "anthropic"}
    ]
    return jsonify({"object": "list", "data": models})

@app.route('/v1/chat/completions', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    is_stream = data.get('stream', False)
    
    requested_model = data.get('model', 'auto') 
    
    headers = {
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
        'Cache-Control': 'no-cache',
        'Content-Type': 'text/event-stream; charset=utf-8'
    }
    
    if is_stream:
        return Response(
            dispatcher.dispatch_stream(messages, requested_model), 
            headers=headers
        )
    else:
        # 🩹 兼容非流式请求：收集所有 chunk 后一次性返回
        full_content = ""
        for chunk in dispatcher.dispatch_stream(messages, requested_model):
            if chunk.startswith("data: "):
                import json as _json
                try:
                    chunk_data = _json.loads(chunk[6:])
                    delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        full_content += delta["content"]
                except:
                    pass
        
        return jsonify({
            "id": "chatcmpl",
            "object": "chat.completion",
            "created": 1234567890,
            "model": requested_model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": full_content},
                "finish_reason": "stop"
            }]
        })

if __name__ == '__main__':
    print("🦞 龙虾混动网关 V8.1 (全协议兼容版) 启动中...")
    app.run(host='127.0.0.1', port=8080)