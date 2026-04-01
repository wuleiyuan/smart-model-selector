#!/usr/bin/env python3
import json
import os
import sys

# 路径
BASE_DIR = "/Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector"
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
STATE_FILE = os.path.join(BASE_DIR, ".selector_state.json")

def load_data(file):
    if os.path.exists(file):
        with open(file, 'r') as f: return json.load(f)
    return {}

def save_data(file, data):
    with open(file, 'w') as f: json.dump(data, f)

def get_next_resource():
    keys = load_data(KEYS_FILE)
    state = load_data(STATE_FILE)
    if not state: state = {"g_paid": 0, "g_free": 0, "other_free": 0}

    # --- 调度逻辑：优先消耗付费 Google Key 进行高难度监工 ---
    if keys.get("google_paid"):
        idx = state["g_paid"] % len(keys["google_paid"])
        key = keys["google_paid"][idx]
        state["g_paid"] = idx + 1
        save_data(STATE_FILE, state)
        return {
            "model": "google/gemini-3-pro-preview",
            "provider": "openai", # 走龙虾隧道
            "name": f"Gemini 3 Pro (Paid-Slot-{idx+1})",
            "reason": "🎯 旗舰算力：已启用付费通道，规避并发限制。"
        }

    # --- 备选：付费 MiniMax ---
    if keys.get("minimax_paid"):
        return {
            "model": "minimax/m2.7",
            "provider": "openai",
            "name": "MiniMax 2.7 (Paid)",
            "reason": "🧠 逻辑备援：调用付费 MiniMax 旗舰模型。"
        }

    # --- 降级：轮询 17 个免费 Key ---
    # 这里合并了 Google Free 和 Other Free
    free_pool = keys.get("google_free", []) + keys.get("other_free", [])
    idx = state["other_free"] % len(free_pool)
    item = free_pool[idx]
    state["other_free"] = idx + 1
    save_data(STATE_FILE, state)
    
    # 动态映射模型名
    model_name = "google/gemini-1.5-flash" if isinstance(item, str) else f"{item['p']}/auto"
    display_name = f"Free-Agent-{idx+1}"

    return {
        "model": model_id,
        "provider": "openai",
        "name": display_name,
        "reason": "🛡️ 避险模式：付费额度异常，已启动无限免费轮换集群。"
    }

def main():
    res = get_next_resource()
    if "--json" in sys.argv:
        print(json.dumps(res))
    else:
        print(f"\n🚀 [INF-WAR] 资产调度完毕")
        print(f"✅ 当前模型: {res['name']}")

if __name__ == "__main__":
    main()
