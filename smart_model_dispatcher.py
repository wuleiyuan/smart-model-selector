import json, os, logging, requests
from pathlib import Path

logger = logging.getLogger("SmartDispatcher")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('\033[36m%(levelname)s - %(message)s\033[0m'))
    logger.addHandler(ch)

class SmartModelDispatcher:
    def __init__(self):
        self.KEYS_PATH = Path("/Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector/keys.json")
        self.api_keys = []
        self.session = requests.Session()
        self.initialize_system()

    def initialize_system(self):
        if self.KEYS_PATH.exists():
            try:
                with open(self.KEYS_PATH) as f:
                    data = json.load(f)
                    # 优先挂载 MiniMax
                    for k in data.get("minimax_paid", []):
                        if k: self.api_keys.append({"provider": "minimax", "key": k})
                    # 挂载 Google 备用
                    for k in data.get("google_paid", []) + data.get("google_free", []):
                        if k: self.api_keys.append({"provider": "google", "key": k})
            except Exception as e:
                logger.error(f"读取密钥失败: {e}")
        logger.info(f"⛽ 混动引擎就绪: 共 {len(self.api_keys)} 个 Key 在线")

    def dispatch_stream(self, messages):
        last_err = "未知错误"
        for i, api in enumerate(self.api_keys):
            provider = api["provider"]
            logger.info(f"🎯 启动引擎 #{i+1} [{provider.upper()}] ...")
            try:
                if provider == "minimax":
                    yield from self._stream_minimax(api, messages)
                else:
                    yield from self._stream_google(api, messages)
                return  # 只要某一个 Key 成功跑完流，就直接退出循环！
            except Exception as e:
                last_err = str(e)
                logger.warning(f"⚠️ 引擎 [{provider}] 熄火: {last_err}")
                continue # 失败则无缝换下一个 Key
        
        # 如果把所有的 Key 都试光了还是不行
        chunk = {"id": "error", "object": "chat.completion.chunk", "choices": [{"delta": {"content": f"\n\n🚨 全部引擎失效: {last_err}"}, "index": 0}]}
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    def _stream_minimax(self, api_item, messages):
        url = "https://api.minimax.chat/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_item['key']}", "Content-Type": "application/json"}
        # 【关键】开启 MiniMax 的官方原生流式输出
        payload = {"model": "MiniMax-M2.7", "messages": messages, "stream": True}
        
        # timeout=(10, 120) 代表：10秒连不上就报错，但是允许模型花 120 秒慢慢推理和回传数据
        resp = self.session.post(url, headers=headers, json=payload, stream=True, timeout=(10, 120))
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                # OpenCode 只认 data: 开头的标准协议
                if decoded.startswith("data:"):
                    yield decoded + "\n\n"

    def _stream_google(self, api_item, messages):
        # 【关键保活机制】瞬间吐出占位符，立刻喂饱 OpenCode 前端，让它无限期等下去
        think_msg = {"id": "gemini", "object": "chat.completion.chunk", "choices": [{"delta": {"content": "\n\n🔄 [MiniMax限流，已无缝切换至 Gemini 备用引擎，深度思考中...]\n\n"}, "index": 0}]}
        yield f"data: {json.dumps(think_msg)}\n\n"
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:generateContent?key={api_item['key']}"
        prompt = messages[-1]["content"] if messages else "你好"
        proxies = {"http": os.environ.get("HTTP_PROXY", ""), "https": os.environ.get("HTTPS_PROXY", "")}
        if not proxies.get("http"): proxies = None
        
        resp = self.session.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=(10, 120), proxies=proxies)
        resp.raise_for_status()
        
        text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        final_msg = {"id": "gemini", "object": "chat.completion.chunk", "choices": [{"delta": {"content": text}, "index": 0}]}
        yield f"data: {json.dumps(final_msg)}\n\n"
        yield "data: [DONE]\n\n"
