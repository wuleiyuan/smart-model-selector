from flask import Flask, request, jsonify, Response
from smart_model_dispatcher import SmartModelDispatcher

app = Flask(__name__)
dispatcher = SmartModelDispatcher()

@app.route('/v1/chat/completions', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    is_stream = data.get('stream', False)
    
    if is_stream:
        # 直接把 Generator 甩给 Flask，实现真·流式管道直连
        return Response(dispatcher.dispatch_stream(messages), mimetype='text/event-stream')
    else:
        return jsonify({"error": "请确保 OpenCode 开启了流式输出模式 (Stream)"})

if __name__ == '__main__':
    print("🦞 龙虾混动网关 V5 (真·流式直连 + 前端保活版) 启动中...")
    app.run(host='127.0.0.1', port=8080)
