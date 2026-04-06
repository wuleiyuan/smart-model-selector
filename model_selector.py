#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

class SmartModelSelector:
    def __init__(self):
        self.BASE_DIR = "/Users/leiyuanwu/LocalProjects/OpenCode/smart-model-selector"
        self.CONFIG_FILE = os.path.join(self.BASE_DIR, "models_config.json")
        self.KEYS_FILE = os.path.join(self.BASE_DIR, "keys.json")
        self.STATE_FILE = os.path.join(self.BASE_DIR, ".selector_state.json")
        self.AUTH_FILE = Path.home() / ".local/share/opencode/auth.json"

    def select(self, task_desc: str):
        """核心选择逻辑：供 api_server.py 调用"""
        try:
            # 1. 意图识别
            task_type = "coding"
            if any(w in task_desc for w in ["写文章", "文案", "推文", "创作"]): task_type = "writing"
            elif any(w in task_desc for w in ["分析", "研究", "调研", "总结"]): task_type = "research"
            elif any(w in task_desc for w in ["快速", "简单", "短"]): task_type = "fast"
            
            # 2. 读取配置基因库
            with open(self.CONFIG_FILE, 'r') as f:
                config = json.load(f)
            model_id = config.get("task_mappings", {}).get(task_type, ["gemini-3.1-pro-preview"])[0]

            # 3. 决定 Provider 和 Key (只有在需要打印 JSON 时才有用)
            reason = f"识别为 {task_type} 任务"
            return model_id, reason

        except Exception as e:
            return "gemini-3.1-pro-preview", str(e)

# 兼容原有的脚本运行模式
def main():
    selector = SmartModelSelector()
    task_desc = sys.argv[1] if len(sys.argv) > 1 else "coding"
    model_id, reason = selector.select(task_desc)
    
    # 【关键修复】如果是 CLI 调用，直接输出模型 ID，防止 OpenCode 无法解析 JSON
    print(model_id)

if __name__ == "__main__":
    main()