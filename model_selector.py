#!/usr/bin/env python3
import json
import os
import sys

BASE_DIR = "/Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector"
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
STATE_FILE = os.path.join(BASE_DIR, ".selector_state.json")

def main():
    try:
        # 1. 读取状态
        state = {"p_idx": 0}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
            except:
                pass
                
        # 2. 读取 Keys
        with open(KEYS_FILE, 'r') as f:
            keys = json.load(f)
            
        # 3. 核心轮询逻辑：优先用 3 个付费 Google
        paid_google_keys = keys.get("google_paid", [])
        if paid_google_keys:
            idx = state.get("p_idx", 0) % len(paid_google_keys)
            
            # 保存下次的索引
            state["p_idx"] = idx + 1
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f)
                
            # 组装返回给 OpenCode 的 JSON
            res = {
                "model": "google/gemini-3-pro-preview", 
                "provider": "openai", # 依然走龙虾隧道
                "name": f"Gemini 3 Pro (Paid-Slot-{idx+1})",
                "reason": "🎯 旗舰算力调度成功"
            }
        else:
            # 兜底
            res = {
                "model": "gemini-1.5-flash", 
                "provider": "google", 
                "name": "Fallback Free"
            }
            
    except Exception as e:
        # 终极兜底：即便出错也不能让 OpenCode 崩溃
        res = {
            "model": "gemini-1.5-flash", 
            "provider": "google", 
            "name": f"Error: {str(e)}"
        }

    # 4. 输出给 OpenCode
    if "--json" in sys.argv:
        print(json.dumps(res))
    else:
        print(f"\n🚀 当前挂载: {res.get('name')}")

if __name__ == "__main__":
    main()
