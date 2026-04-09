import json, os, logging, requests
from pathlib import Path

# 尝试挂载大脑
try:
    from selector_core import SelectorCore
    HAS_CORE = True
except ImportError:
    HAS_CORE = False

logger = logging.getLogger("SmartDispatcher")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('\033[36m%(levelname)s - %(message)s\033[0m'))
    logger.addHandler(ch)

class SmartModelDispatcher:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.USER_HOME = Path.home()
        self.AUTH_PATH = self.USER_HOME / ".local" / "share" / "opencode" / "auth.json"
        self.KEYS_PATH = self.BASE_DIR / "keys.json"
        
        self.api_keys = []
        self.session = requests.Session()
        # 初始化大脑
        self.core = SelectorCore() if HAS_CORE else None
        self.initialize_system()

    def initialize_system(self):
        logger.info("🔍 正在扫描本机配置文件...")
        if self.KEYS_PATH.exists():
            try:
                with open(self.KEYS_PATH, encoding='utf-8') as f:
                    data = json.load(f)
                    for k in data.get("minimax_paid", []):
                        if k: self.api_keys.append({"provider": "minimax", "key": k})
                    for k in data.get("google_paid", []) + data.get("google_free", []):
                        if k: self.api_keys.append({"provider": "google", "key": k})
            except Exception as e:
                logger.error(f"❌ keys.json 读取失败: {e}")

        if self.AUTH_PATH.exists() and not any(k['provider'] == 'minimax' for k in self.api_keys):
            try:
                with open(self.AUTH_PATH, encoding='utf-8') as f:
                    auth = json.load(f)
                    if auth.get("minimax_api_key"): 
                        self.api_keys.append({"provider": "minimax", "key": auth["minimax_api_key"]})
            except Exception as e:
                pass
                
        seen = set()
        self.api_keys = [x for x in self.api_keys if not (x["key"] in seen or seen.add(x["key"]))]
        
        if not self.api_keys:
            logger.error("🚨 致命错误：未找到任何有效的 API Key！")
        else:
            logger.info(f"✅ 混动引擎点火完毕: 共挂载 {len(self.api_keys)} 个可用 Key")

    def dispatch_stream(self, messages, requested_model="auto"):
        preferred_provider = None
        
        # 🧠 阶段 1: 脑机协同分析
        # 只有当用户选择 auto 或者默认配置时，才触发智能分析
        if self.core and ("auto" in requested_model.lower() or not requested_model):
            try:
                task_text = messages[-1]["content"] if messages else ""
                model_id, reason = self.core.select(task_text)
                logger.info(f"🧠 [大脑分析] {reason} -> 决定使用 {model_id}")
                
                # 向前端流式输出思考过程 (极其优雅的 UI 体验)
                notify = {"id": "brain", "object": "chat.completion.chunk", "choices": [{"delta": {"content": f"> 🧠 **智能调度系统**: {reason} -> 已为您切换至 `{model_id}`\n\n"}, "index": 0}]}
                yield f"data: {json.dumps(notify)}\n\n"
                
                # 提取首选供应商
                if "minimax" in model_id.lower() or "claude" in model_id.lower():
                    preferred_provider = "minimax"
                elif "gemini" in model_id.lower() or "google" in model_id.lower():
                    preferred_provider = "google"
            except Exception as e:
                logger.warning(f"🧠 大脑分析失败: {e}")

        # ⚡ 阶段 2: 动态重排流水线
        sorted_keys = list(self.api_keys)
        if preferred_provider:
            # 将被大脑选中的提供商 Key 强制排在第一位
            sorted_keys.sort(key=lambda x: x["provider"] != preferred_provider)

        # 🛡️ 阶段 3: 执行与故障转移
        last_err = "未知错误"
        for i, api in enumerate(sorted_keys):
            provider = api["provider"]
            logger.info(f"🎯 调度引擎 #{i+1} [{provider.upper()}] ...")
            
            # 如果是故障回退触发的，再通知一次前端
            if i > 0:
                notify = {"id": "fallback", "object": "chat.completion.chunk", "choices": [{"delta": {"content": f"\n\n> 🔄 **故障转移**: 检测到限流或超时，已无缝自动切至 `{provider.upper()}` 备用引擎...\n\n"}, "index": 0}]}
                yield f"data: {json.dumps(notify)}\n\n"

            try:
                if provider == "minimax":
                    yield from self._stream_minimax(api, messages)
                else:
                    yield from self._stream_google(api, messages)
                return 
            except Exception as e:
                last_err = str(e)
                logger.warning(f"⚠️ [{provider}] 节点熔断: {last_err[:50]}...")
                continue 
        
        chunk = {"id": "error", "object": "chat.completion.chunk", "choices": [{"delta": {"content": f"\n\n> 🚨 **系统崩溃**: 全部引擎失效 ({last_err})"}, "index": 0}]}
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    def _stream_minimax(self, api_item, messages):
        url = "https://api.minimax.chat/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_item['key']}", "Content-Type": "application/json"}
        payload = {"model": "MiniMax-M2.7", "messages": messages, "stream": True}
        resp = self.session.post(url, headers=headers, json=payload, stream=True, timeout=(10, 60))
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data:"): yield decoded + "\n\n"

    def _stream_google(self, api_item, messages):
        gemini_msgs = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            gemini_msgs.append({"role": role, "parts": [{"text": m["content"]}]})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:streamGenerateContent?alt=sse&key={api_item['key']}"
        proxies = {"http": os.environ.get("HTTP_PROXY", ""), "https": os.environ.get("HTTPS_PROXY", "")}
        if not proxies.get("http"): proxies = None
        resp = self.session.post(url, json={"contents": gemini_msgs}, timeout=(10, 60), proxies=proxies, stream=True)
        resp.raise_for_status() 
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    try:
                        data = json.loads(decoded[6:])
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        chunk = {"id": "gemini", "object": "chat.completion.chunk", "choices": [{"delta": {"content": text}, "index": 0}]}
                        yield f"data: {json.dumps(chunk)}\n\n"
                    except: pass
        yield "data: [DONE]\n\n"
