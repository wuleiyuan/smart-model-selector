#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

BASE_DIR = "/Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector"
CONFIG_FILE = os.path.join(BASE_DIR, "models_config.json")
KEYS_FILE = os.path.join(BASE_DIR, "keys.json")
STATE_FILE = os.path.join(BASE_DIR, ".selector_state.json")
AUTH_FILE = Path.home() / ".local/share/opencode/auth.json"

def main():
    try:
        task_desc = sys.argv[1] if len(sys.argv) > 1 else "coding"
        
        task_type = "coding"
        
        writing_keywords = ["写文章", "写文案", "写博客", "写公众号", "写小说", "写剧本", "编剧", "创作", "推文", "文章", "文案"]
        if any(w in task_desc for w in writing_keywords):
            task_type = "writing"
        
        research_keywords = ["分析", "研究", "调研", "对比", "评估", "总结", "解释", "调查"]
        if any(w in task_desc for w in research_keywords):
            task_type = "research"
            
        fast_keywords = ["快速", "简单", "短", "立即", "轻微", "小修"]
        if any(w in task_desc for w in fast_keywords):
            task_type = "fast"
            
        # 2. 强行读取配置基因库 (拿走对应任务的第一顺位)
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        
        model_id = config.get("task_mappings", {}).get(task_type, ["gemini-3.1-pro-preview"])[0]

        # 3. 双引擎物理级分配
        current_key = ""
        provider = "google"
        
        if "minimax" in model_id.lower():
            provider = "minimax"
            if os.path.exists(AUTH_FILE):
                with open(AUTH_FILE, 'r') as f:
                    current_key = json.load(f).get("minimax_api_key", "")
            reason = "2号编剧接管"
        else:
            model_id = "gemini-3.1-pro-preview" 
            if os.path.exists(KEYS_FILE):
                with open(KEYS_FILE, 'r') as f:
                    data = json.load(f)
                local_keys = data.get("google_paid", []) + data.get("google_free", [])
                
                state = {"idx": 0}
                if os.path.exists(STATE_FILE):
                    try:
                        with open(STATE_FILE, 'r') as f: state = json.load(f)
                    except: pass
                if local_keys:
                    current_idx = state.get("idx", 0) % len(local_keys)
                    current_key = local_keys[current_idx]
                    state["idx"] = current_idx + 1
                    with open(STATE_FILE, 'w') as f: json.dump(state, f)
            reason = "3.1 Pro 护航"

        res = {
            "api_key": current_key,
            "model": model_id,
            "provider": provider,
            "name": f"🛡️ 赛博工厂 ({reason})"
        }
        print(json.dumps(res, ensure_ascii=False))
        
    except Exception as e:
        res = {
            "api_key": "YOUR_BACKUP_KEY",
            "model": "gemini-3.1-pro-preview",
            "provider": "google",
            "name": f"⚠️ 紧急降级: {str(e)}"
        }
        print(json.dumps(res, ensure_ascii=False))

if __name__ == "__main__":
    main()
