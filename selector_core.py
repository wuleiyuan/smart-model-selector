#!/usr/bin/env python3
import json
import logging
from pathlib import Path

logger = logging.getLogger("SelectorCore")
logger.setLevel(logging.INFO)

class SelectorCore:
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.KEYS_PATH = self.BASE_DIR / "keys.json"
        
        # 🔫 武器库清单 (动态扩展版)
        self.inventory = {
            "google": 0, 
            "minimax": 0,
            "deepseek": 0
        }
        
        # 🚀 模型火力底座
        self.models = {
            "gemini": "gemini-3.1-pro-preview",
            "minimax": "minimax-m2.7",
            "deepseek": "deepseek-coder"
        }
        self._scan_armory()

    def _scan_armory(self):
        """开机扫描弹夹，确认可用火力"""
        if self.KEYS_PATH.exists():
            try:
                with open(self.KEYS_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    google_paid = len(data.get("google_paid", []))
                    google_free = len(data.get("google_free", []))
                    minimax_paid = len(data.get("minimax_paid", []))
                    deepseek_paid = len(data.get("deepseek", []))
                    
                    self.inventory["google"] = google_paid + google_free
                    self.inventory["minimax"] = minimax_paid
                    self.inventory["deepseek"] = deepseek_paid
                    
                    logger.info(f"🧠 大脑接管弹夹: Google x{self.inventory['google']}, MiniMax x{self.inventory['minimax']}, DeepSeek x{self.inventory['deepseek']}")
            except Exception as e:
                logger.warning(f"大脑无法读取弹夹库存: {e}")

    def get_models(self):
        """兼容原有架构的探测接口"""
        return {
            self.models["gemini"]: {"name": "Gemini 3.1 Pro", "inventory": self.inventory["google"]},
            self.models["minimax"]: {"name": "MiniMax M2.7", "inventory": self.inventory["minimax"]},
            self.models["deepseek"]: {"name": "DeepSeek Coder", "inventory": self.inventory["deepseek"]}
        }

    def select(self, task_text: str):
        """核心路由逻辑：根据提示词分发给最合适的模型"""
        task_text = str(task_text).lower()
        
        # 0. 绝境断水逻辑 (如果首选引擎断水，强行降级)
        total_keys = sum(self.inventory.values())
        if total_keys == 0:
            return "auto", "全军覆没 -> 弹夹为空，等待奇迹"
            
        # 1. 编程 / 算法 / Bug 排查场景 -> 优先 DeepSeek Coder (若有弹药)，否则 Gemini
        coding_kw = ['代码', 'python', 'java', 'bug', '报错', '重构', '算法', 'html', '正则', '排序', '写个脚本']
        if any(k in task_text for k in coding_kw):
            if self.inventory["deepseek"] > 0:
                return self.models["deepseek"], "硬核代码场景 -> 呼叫 DeepSeek Coder 特种部队"
            elif self.inventory["google"] > 0:
                return self.models["gemini"], "深度代码重构 -> 呼叫 Gemini 3.1 Pro 主力"

        # 2. 中文创作/文案润色场景 -> 最懂中文特性的 MiniMax
        writing_kw = ['润色', '写封信', '文章', '语气', '小说', '剧本', '公文', '写总结', '翻译成中文']
        if any(k in task_text for k in writing_kw):
            if self.inventory["minimax"] > 0:
                return self.models["minimax"], "中文创作场景 -> 调度 MiniMax M2.7"

        # 3. 默认主线防线
        if self.inventory["google"] > 0:
            return self.models["gemini"], "默认主战序列 -> 调度 Gemini 3.1 Pro"
        elif self.inventory["deepseek"] > 0:
            return self.models["deepseek"], "备用火力 -> 调度 DeepSeek"
        else:
            return self.models["minimax"], "仅存火力 -> 强制切至 MiniMax"

if __name__ == "__main__":
    import argparse
    import sys

    # 禁用默认的啰嗦日志，保持 CLI 界面清爽
    logger.setLevel(logging.ERROR) 

    # 创建专业的命令行解析器
    parser = argparse.ArgumentParser(
        description="🦞 Smart Model Selector - 智能模型路由核心",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="示例:\n  python3 selector_core.py \"帮我写一个 python 爬虫\"\n  python3 selector_core.py --status"
    )
    
    parser.add_argument("prompt", nargs="?", type=str, help="输入需要大脑分析的任务提示词")
    parser.add_argument("-s", "--status", action="store_true", help="查看当前系统武器库(弹夹)状态")
    
    args = parser.parse_args()
    core = SelectorCore()

    # 路由 1：查看状态 (--status)
    if args.status:
        print("\n📊 [系统状态] 武器库清点完毕:")
        print(f"  🟢 Google 引擎 (Gemini 3.1 Pro): \033[32m{core.inventory['google']} 把\033[0m 可用密钥")
        print(f"  🔵 DeepSeek 引擎 (Coder V3): \033[36m{core.inventory['deepseek']} 把\033[0m 可用密钥")
        print(f"  🟡 MiniMax 引擎 (M2.7 Pro): \033[33m{core.inventory['minimax']} 把\033[0m 可用密钥\n")
        sys.exit(0)

    # 路由 2：分析提示词 (prompt)
    elif args.prompt:
        print(f"\n📥 任务输入: \033[36m'{args.prompt}'\033[0m")
        model, reason = core.select(args.prompt)
        print(f"🎯 路由结果: 分配至引擎 \033[1;32m[{model}]\033[0m")
        print(f"💡 决策逻辑: {reason}\n")
    
    # 路由 3：什么都没输，打印友好的帮助文档
    else:
        parser.print_help()