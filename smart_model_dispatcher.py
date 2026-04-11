import json, os, logging, requests
from pathlib import Path

try:
    from selector_core import SelectorCore
    HAS_CORE = True
except ImportError:
    HAS_CORE = False

logger = logging.getLogger("SmartDispatcher")

class SmartModelDispatcher:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.KEYS_PATH = self.BASE_DIR / "keys.json"
        self.api_keys = []
        self.session = requests.Session()
        self.core = SelectorCore() if HAS_CORE else None
        
        # 定义哪些名字属于“日常基座”。
        # 当客户端传来这些名字时，意味着“随便用个通用的就行”，此时直接唤醒大脑智能接管！
        self.auto_trigger_models = ["auto", "gemini-3.1-pro-preview", "minimax-m2.7"]
        
        self.initialize_system()

    def initialize_system(self):
        if self.KEYS_PATH.exists():
            with open(self.KEYS_PATH, encoding='utf-8') as f:
                data = json.load(f)
                for k in data.get("google_paid", []) + data.get("google_free", []):
                    if k: self.api_keys.append({"provider": "google", "key": k})
                for k in data.get("minimax_paid", []):
                    if k: self.api_keys.append({"provider": "minimax", "key": k})
                for item in data.get("other_free", []):
                    if item.get("p") and item.get("k"):
                        self.api_keys.append({"provider": item["p"], "key": item["k"]})

    def dispatch_stream(self, messages, requested_model="auto"):
        target_provider = "google" # 绝对底座
        
        # ============================================================
        # 🌟 终极逻辑：区分【智能接管】与【手动强制】
        # ============================================================
        req_model_lower = requested_model.lower()
        
        # 模式 1：智能接管 (客户端传来了 auto 或者通用基座名字)
        if self.core and any(trigger in req_model_lower for trigger in self.auto_trigger_models):
            task_text = messages[-1]["content"] if messages else ""
            target_provider, reason = self.core.select(task_text)
            logger.info(f"🧠 [智能接管] {reason}")
            
            brain_msg = f"> 🧠 **智能调度**: {reason}\n\n"
            chunk = {"id": "brain", "choices": [{"delta": {"content": brain_msg}}]}
            yield f"data: {json.dumps(chunk)}\n\n"
            
        # 模式 2：手动强制 (客户端传了一个极其明确的名字，比如 deepseek-coder)
        else:
            logger.info(f"🎯 [手动强制] 主治医师明确指定模型: {requested_model}")
            # 尝试根据传来的名字推断提供商 (例如传了 deepseek-coder，我们就去核武库里找 deepseek)
            for api in self.api_keys:
                if api["provider"] in req_model_lower:
                    target_provider = api["provider"]
                    break
            # 如果没找到匹配的，默认回退给 Google 兜底
        
        # ============================================================

        # 排序：把选中的 provider 排到最前面
        sorted_keys = sorted(self.api_keys, key=lambda x: x["provider"] != target_provider)
        last_err = "未知错误"
        
        for i, api in enumerate(sorted_keys):
            provider = api["provider"]
            
            if i > 0:
                fb_msg = f"\n\n> 🔄 **故障转移**: 切至 `{provider.upper()}` 备用引擎...\n\n"
                chunk = {"id": "fallback", "choices": [{"delta": {"content": fb_msg}}]}
                yield f"data: {json.dumps(chunk)}\n\n"

            try:
                if provider == "google":
                    yield from self._stream_google(api, messages)
                elif provider == "minimax":
                    yield from self._stream_minimax(api, messages)
                elif provider == "claude":
                    raise Exception("Claude 专用协议待接入")
                else:
                    yield from self._stream_openai_compat(api, messages)
                return 
            except Exception as e:
                last_err = str(e)
                logger.warning(f"⚠️ [{provider}] 节点熔断: {last_err[:50]}")
                continue 
                
        err_msg = f"\n\n> 🚨 **系统崩溃**: 全部引擎失效 ({last_err})"
        chunk = {"id": "error", "choices": [{"delta": {"content": err_msg}}]}
        yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"

    # ... 以下为原有的 _stream_openai_compat, _stream_google, _stream_minimax 函数，保持不变 ...
    def _stream_openai_compat(self, api_item, messages):
        provider = api_item["provider"]
        registry = {
            "deepseek": {"url": "https://api.deepseek.com/chat/completions", "model": "deepseek-coder"},
            "openai": {"url": "https://api.openai.com/v1/chat/completions", "model": "gpt-4o"},
            "kimi": {"url": "https://api.moonshot.cn/v1/chat/completions", "model": "moonshot-v1-8k"},
            "zhipu": {"url": "https://open.bigmodel.cn/api/paas/v4/chat/completions", "model": "glm-4"},
            "qwen": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "model": "qwen-max"},
            "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "model": "llama3-70b-8192"},
            "openrouter": {"url": "https://openrouter.ai/api/v1/chat/completions", "model": "auto"},
            "doubao": {"url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions", "model": "doubao-pro-32k"},
            "siliconflow": {"url": "https://api.siliconflow.cn/v1/chat/completions", "model": "deepseek-ai/DeepSeek-V2-Chat"}
        }
        
        if provider not in registry:
            raise Exception(f"未配置服务商路由: {provider}")
            
        url = registry[provider]["url"]
        model = registry[provider]["model"]
        
        headers = {"Authorization": f"Bearer {api_item['key']}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "stream": True}
        
        resp = self.session.post(url, headers=headers, json=payload, stream=True, timeout=(10, 60))
        resp.raise_for_status()
        
        for line in resp.iter_lines():
            if not line: continue
            decoded = line.decode('utf-8')
            if "data: [DONE]" in decoded: continue 
            if decoded.startswith("data:"):
                yield decoded + "\n\n"

    def _stream_google(self, api_item, messages):
        gemini_msgs = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-pro-preview:streamGenerateContent?alt=sse&key={api_item['key']}"
        proxies = {"http": os.environ.get("HTTP_PROXY", ""), "https": os.environ.get("HTTPS_PROXY", "")}
        resp = self.session.post(url, json={"contents": gemini_msgs}, timeout=(10, 60), proxies=proxies if proxies.get("http") else None, stream=True)
        resp.raise_for_status() 
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if decoded.startswith("data: "):
                    try:
                        text = json.loads(decoded[6:])["candidates"][0]["content"]["parts"][0]["text"]
                        chunk = {"id": "gemini", "choices": [{"delta": {"content": text}}]}
                        yield f"data: {json.dumps(chunk)}\n\n"
                    except: pass
                    
    def _stream_minimax(self, api_item, messages):
        url, headers = "https://api.minimax.chat/v1/chat/completions", {"Authorization": f"Bearer {api_item['key']}", "Content-Type": "application/json"}
        resp = self.session.post(url, headers=headers, json={"model": "MiniMax-M2.7", "messages": messages, "stream": True}, stream=True, timeout=(10, 60))
        resp.raise_for_status()
        for line in resp.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                if "data: [DONE]" in decoded: continue
                if decoded.startswith("data:"): yield decoded + "\n\n"