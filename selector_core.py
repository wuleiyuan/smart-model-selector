#!/usr/bin/env python3
import json
import logging
from pathlib import Path

logger = logging.getLogger("SelectorCore")

class SelectorCore:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.KEYS_PATH = self.BASE_DIR / "keys.json"
        
        # 🔫 动态武器库清单
        self.inventory = {"google": 0, "minimax": 0}
        self._scan_armory()

    def _scan_armory(self):
        """开机全面扫描弹夹，包括 other_free 里的核武库"""
        if self.KEYS_PATH.exists():
            try:
                with open(self.KEYS_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.inventory["google"] = len(data.get("google_paid", [])) + len(data.get("google_free", []))
                    self.inventory["minimax"] = len(data.get("minimax_paid", []))
                    
                    # 🚀 扫描 other_free 里的隐藏弹药
                    for item in data.get("other_free", []):
                        provider = item.get("p")
                        if provider:
                            self.inventory[provider] = self.inventory.get(provider, 0) + 1
                            
                # 打印火力配置
                active_providers = [f"{k}({v}把)" for k, v in self.inventory.items() if v > 0]
                logger.info(f"🧠 大脑已接管核武库: {', '.join(active_providers)}")
            except Exception as e:
                logger.warning(f"大脑无法读取弹夹库存: {e}")

    def select(self, task_text: str):
        """🌟 终极路由逻辑：根据提示词分发给最合适的模型"""
        task_text = str(task_text).lower()

        # 1. 深度 Coding 场景 -> 优先 DeepSeek，备用 Claude/Google
        coding_kw = ['代码', 'python', 'java', 'bug', '报错', '重构', '算法', '正则', '排序']
        if any(k in task_text for k in coding_kw):
            if self.inventory.get("deepseek", 0) > 0:
                return "deepseek", "深度代码重构 -> 极速调度 DeepSeek Coder"
            return "google", "代码重构 -> 调度 Gemini 3.1 Pro"

        # 2. 中文长文本/润色 -> 优先 Kimi/智谱/千问
        writing_kw = ['润色', '写封信', '文章', '小说', '总结', '翻译']
        if any(k in task_text for k in writing_kw):
            for p in ["kimi", "zhipu", "qwen", "minimax"]:
                if self.inventory.get(p, 0) > 0:
                    return p, f"中文创作场景 -> 调度特化引擎 {p.capitalize()}"

        # 3. 复杂逻辑推演 -> 优先 OpenAI (GPT-4o)
        logic_kw = ['原理', '为什么', '分析', '规划', '架构']
        if any(k in task_text for k in logic_kw) and self.inventory.get("openai", 0) > 0:
            return "openai", "高难度逻辑推演 -> 调度 OpenAI GPT-4o"

        # 4. 默认主线兜底
        if self.inventory.get("google", 0) > 0:
            return "google", "默认主战序列 -> 调度 Gemini 3.1 Pro"
        
        # 绝境逢生：随便找一个有钥匙的 provider
        for p, count in self.inventory.items():
            if count > 0: return p, f"默认兜底 -> 调度 {p}"
        
        return "error", "弹药库彻底枯竭！"

if __name__ == "__main__":
    import argparse, sys
    logger.setLevel(logging.ERROR) 
    parser = argparse.ArgumentParser(description="🦞 混动大脑测试")
    parser.add_argument("prompt", nargs="?", type=str)
    args = parser.parse_args()
    
    core = SelectorCore()
    if args.prompt:
        model, reason = core.select(args.prompt)
        print(f"\n📥 输入: {args.prompt}\n🎯 路由: [{model}]\n💡 逻辑: {reason}\n")
    else:
        print("\n📊 武器库清单:", core.inventory)
