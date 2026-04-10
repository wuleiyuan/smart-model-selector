from flask import Flask, request, jsonify, Response
from smart_model_dispatcher import SmartModelDispatcher

app = Flask(__name__)
dispatcher = SmartModelDispatcher()

@app.route('/v1/chat/completions', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    is_stream = data.get('stream', False)
    
    # 🔪 霸王硬上弓：强行拦截 TUI 传来的模型名称，强制注入 'auto'
    # 这样就能 100% 唤醒咱们的 SelectorCore 大脑进行智能路由！
    requested_model = 'auto' 
    
    if is_stream:
        # 把强制修改后的 'auto' 传递给调度器
        return Response(dispatcher.dispatch_stream(messages, requested_model), mimetype='text/event-stream')
    else:
        return jsonify({"error": "请确保 OpenCode 开启了流式输出模式 (Stream)"})

if __name__ == '__main__':
    print("🦞 龙虾混动网关 V7.1 (TUI 强制接管版) 启动中...")
    app.run(host='127.0.0.1', port=8080)