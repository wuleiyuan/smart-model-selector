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
        {"id": "deepseek-coder", "object": "model", "owned_by": "deepseek"},
        {"id": "minimax-m2.7", "object": "model", "owned_by": "minimax"}
    ]
    return jsonify({"object": "list", "data": models})

@app.route('/v1/chat/completions', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    is_stream = data.get('stream', False)
    
    # 🩹 P1 修复：恢复民主！摘除强行注入的 'auto'
    requested_model = data.get('model', 'auto') 
    
    # 🩹 P0 修复：挂载 OMO / OpenClaw 必须的流式保活头部
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
        # 非流式暂不支持，抛出标准的 OpenAI 格式错误
        return jsonify({
            "error": {
                "message": "网关当前强制要求使用流式输出 (Stream = True)",
                "type": "invalid_request_error",
                "code": "stream_required"
            }
        }), 400

if __name__ == '__main__':
    print("🦞 龙虾混动网关 V8.0 (OMO保活 + 路由修复版) 启动中...")
    app.run(host='127.0.0.1', port=8080)