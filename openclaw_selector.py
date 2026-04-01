#!/usr/bin/env python3
"""
OpenClaw Auto Model Selector - OpenClaw 自动模型选择器

功能：
- 根据任务类型自动选择最优模型
- 混合策略：任务匹配 + 性能驱动自动切换
- 支持 OpenClaw Gateway API
- 支持流式响应

用法：
    python3 openclaw_selector.py "帮我写一个排序算法"
    python3 openclaw_selector.py --json "分析这段代码"
"""

import json
import sys
import os
import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("openclaw_selector")

# ============ 模型定义 ============

class ModelInfo:
    """模型信息"""
    def __init__(self, id: str, name: str, provider: str, 
                 strengths: List[str], context_window: int = 200000,
                 cost_per_1k: float = 0.0, latency_tier: str = "fast"):
        self.id = id
        self.name = name
        self.provider = provider
        self.strengths = strengths  # 强项: coding, research, writing, fast, cheap
        self.context_window = context_window
        self.cost_per_1k = cost_per_1k
        self.latency_tier = latency_tier  # fast, medium, slow

# 支持的模型列表
MODELS = {
    # Anthropic (Claude)
    "claude-opus-4-6": ModelInfo(
        id="claude-opus-4-6",
        name="Claude Opus 4.6",
        provider="anthropic",
        strengths=["research", "writing", "complex_reasoning"],
        context_window=200000,
        cost_per_1k=15.0,
        latency_tier="medium"
    ),
    "claude-sonnet-4-5": ModelInfo(
        id="claude-sonnet-4-5",
        name="Claude Sonnet 4.5",
        provider="anthropic",
        strengths=["coding", "balanced"],
        context_window=200000,
        cost_per_1k=3.0,
        latency_tier="fast"
    ),
    "claude-haiku-3-5": ModelInfo(
        id="claude-haiku-3-5",
        name="Claude Haiku 3.5",
        provider="anthropic",
        strengths=["fast", "cheap"],
        context_window=200000,
        cost_per_1k=0.8,
        latency_tier="fast"
    ),
    
    # Google Gemini
    "gemini-2-0-pro": ModelInfo(
        id="gemini-2-0-pro",
        name="Gemini 2.0 Pro",
        provider="google",
        strengths=["research", "multimodal"],
        context_window=2000000,
        cost_per_1k=1.25,
        latency_tier="medium"
    ),
    "gemini-2-0-flash": ModelInfo(
        id="gemini-2-0-flash",
        name="Gemini 2.0 Flash",
        provider="google",
        strengths=["fast", "coding"],
        context_window=1000000,
        cost_per_1k=0.0,
        latency_tier="fast"
    ),
    
    # OpenAI
    "gpt-4o": ModelInfo(
        id="gpt-4o",
        name="GPT-4o",
        provider="openai",
        strengths=["coding", "balanced"],
        context_window=128000,
        cost_per_1k=2.5,
        latency_tier="fast"
    ),
    "gpt-4o-mini": ModelInfo(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="openai",
        strengths=["fast", "cheap"],
        context_window=128000,
        cost_per_1k=0.15,
        latency_tier="fast"
    ),
    
    # DeepSeek
    "deepseek-chat": ModelInfo(
        id="deepseek-chat",
        name="DeepSeek Chat",
        provider="deepseek",
        strengths=["coding", "cheap"],
        context_window=64000,
        cost_per_1k=0.14,
        latency_tier="fast"
    ),
    
    # Qwen
    "qwen-2-5-coder-32b": ModelInfo(
        id="qwen-2-5-coder-32b",
        name="Qwen 2.5 Coder 32B",
        provider="qwen",
        strengths=["coding"],
        context_window=32000,
        cost_per_1k=0.0,
        latency_tier="fast"
    ),
    
    # OpenCode (免费)
    "minimax-2.5-free": ModelInfo(
        id="minimax-2.5-free",
        name="MiniMax 2.5 (Free)",
        provider="opencode",
        strengths=["fast", "cheap"],
        context_window=128000,
        cost_per_1k=0.0,
        latency_tier="fast"
    ),
}

# 任务类型关键词映射
TASK_PATTERNS = {
    "coding": [
        r"\b(code|编程|写代码|debug|bug|修复|函数|class|def|import|算法)\b",
        r"\b(写一个|实现|创建|开发|编写)\b.*\b(程序|代码|函数|类)\b",
    ],
    "research": [
        r"\b(分析|研究|调研|比较|评估|总结|解释)\b",
        r"\b(是什么|为什么|如何|原理|机制)\b",
    ],
    "writing": [
        r"\b(写|创作|编辑|修改|润色|翻译|总结)\b",
        r"\b(文章|文档|报告|邮件|文案)\b",
    ],
    "fast": [
        r"\b(快速|简单|短|立即)\b",
        r"^[^a-zA-Z]*$",  # 纯中文/符号
    ],
    "multimodal": [
        r"\b(图片|图像|图表|截图|照片)\b",
        r"\b(看图|识别|分析图)\b",
    ],
}

# ============ 性能监控 ============

class PerformanceTracker:
    """性能跟踪器 - 记录模型响应时间和成功率"""
    
    CACHE_FILE = Path.home() / ".config" / "openclaw" / "model_performance.json"
    
    def __init__(self):
        self._performance: Dict[str, Dict] = {}  # model_id -> {latency, success, fail, last_used}
        self._load_cache()
    
    def _load_cache(self):
        """加载性能缓存"""
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    self._performance = data.get("performance", {})
                    logger.info(f"[OK] 加载性能缓存: {len(self._performance)} 个模型")
        except Exception as e:
            logger.debug(f"性能缓存加载失败: {e}")
    
    def _save_cache(self):
        """保存性能缓存"""
        try:
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"performance": self._performance, "updated_at": int(time.time())}
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.debug(f"性能缓存保存失败: {e}")
    
    def record_request(self, model_id: str, latency: float, success: bool):
        """记录请求结果"""
        if model_id not in self._performance:
            self._performance[model_id] = {
                "latency_sum": 0.0,
                "success_count": 0,
                "fail_count": 0,
                "last_used": 0,
            }
        
        stats = self._performance[model_id]
        stats["latency_sum"] += latency
        stats["success_count"] += 1 if success else 0
        stats["fail_count"] += 0 if success else 1
        stats["last_used"] = int(time.time())
        
        self._save_cache()
    
    def get_stats(self, model_id: str) -> Optional[Dict]:
        """获取模型性能统计"""
        return self._performance.get(model_id)
    
    def get_average_latency(self, model_id: str) -> float:
        """获取平均延迟"""
        stats = self._performance.get(model_id)
        if not stats or stats["success_count"] == 0:
            return 0.0
        return stats["latency_sum"] / stats["success_count"]
    
    def get_success_rate(self, model_id: str) -> float:
        """获取成功率"""
        stats = self._performance.get(model_id)
        if not stats:
            return 1.0
        total = stats["success_count"] + stats["fail_count"]
        if total == 0:
            return 1.0
        return stats["success_count"] / total
    
    def is_in_cooldown(self, model_id: str) -> bool:
        """检查模型是否在冷却期"""
        # 简单实现：如果失败率过高，认为在冷却期
        rate = self.get_success_rate(model_id)
        return rate < 0.5

# ============ 模型选择器 ============

class OpenClawModelSelector:
    """OpenClaw 自动模型选择器 - 混合策略"""
    
    def __init__(self):
        self.tracker = PerformanceTracker()
    
    def analyze_task(self, task_description: str) -> str:
        """分析任务类型"""
        task_lower = task_description.lower()
        
        # 按优先级匹配
        for task_type, patterns in TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, task_lower, re.IGNORECASE):
                    logger.info(f"任务类型识别: {task_type}")
                    return task_type
        
        return "balanced"  # 默认均衡型
    
    def select(self, task_description: str) -> Tuple[str, str]:
        """
        选择最优模型
        
        Returns:
            (model_id, reason)
        """
        # 1. 分析任务类型
        task_type = self.analyze_task(task_description)
        
        # 2. 获取候选模型列表
        candidates = self._get_candidates_by_task(task_type)
        
        # 3. 按性能排序 (性能驱动)
        candidates = self._sort_by_performance(candidates)
        
        # 4. 选择最佳模型
        if not candidates:
            # 没有可用模型，使用默认
            return "minimax-2.5-free", "[Default] 无可用模型，使用免费模型"
        
        selected_model = candidates[0]
        reason = f"[{task_type}] 任务匹配 + 性能优化"
        
        return selected_model, reason
    
    def _get_candidates_by_task(self, task_type: str) -> List[str]:
        """根据任务类型获取候选模型"""
        candidates = []
        
        for model_id, model in MODELS.items():
            if task_type in model.strengths:
                candidates.append(model_id)
        
        # 如果没有匹配的，返回所有模型
        if not candidates:
            candidates = list(MODELS.keys())
        
        return candidates
    
    def _sort_by_performance(self, model_ids: List[str]) -> List[str]:
        """按性能排序"""
        def sort_key(model_id: str) -> float:
            # 综合评分：低延迟 + 高成功率
            latency = self.tracker.get_average_latency(model_id)
            success_rate = self.tracker.get_success_rate(model_id)
            in_cooldown = self.tracker.is_in_cooldown(model_id)
            
            # 在冷却期的模型惩罚
            cooldown_penalty = 1000 if in_cooldown else 0
            
            return latency + cooldown_penalty - (success_rate * 10)
        
        return sorted(model_ids, key=sort_key)
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """获取模型信息"""
        return MODELS.get(model_id)
    
    def list_models(self) -> Dict:
        """列出所有模型"""
        return {
            model_id: {
                "name": model.name,
                "provider": model.provider,
                "strengths": model.strengths,
                "context_window": model.context_window,
                "cost_per_1k": model.cost_per_1k,
                "latency_tier": model.latency_tier,
                "avg_latency": self.tracker.get_average_latency(model_id),
                "success_rate": self.tracker.get_success_rate(model_id),
            }
            for model_id, model in MODELS.items()
        }

# ============ 主函数 ============

def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="OpenClaw Auto Model Selector - 自动模型选择器"
    )
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--json", action="store_true", help="JSON 输出格式")
    parser.add_argument("--list", action="store_true", help="列出所有模型")
    parser.add_argument("--stats", action="store_true", help="显示性能统计")
    
    args = parser.parse_args()
    
    selector = OpenClawModelSelector()
    
    # 列出所有模型
    if args.list:
        models = selector.list_models()
        print(json.dumps(models, ensure_ascii=False, indent=2))
        return
    
    # 显示性能统计
    if args.stats:
        tracker = PerformanceTracker()
        for model_id in MODELS.keys():
            stats = tracker.get_stats(model_id)
            if stats:
                print(f"{model_id}:")
                print(f"  平均延迟: {tracker.get_average_latency(model_id):.2f}ms")
                print(f"  成功率: {tracker.get_success_rate(model_id)*100:.1f}%")
        return
    
    # 选择模型
    if args.task:
        model_id, reason = selector.select(args.task)
        
        if args.json:
            result = {
                "model": model_id,
                "reason": reason,
                "model_info": {
                    "name": MODELS[model_id].name,
                    "provider": MODELS[model_id].provider,
                    "strengths": MODELS[model_id].strengths,
                }
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(model_id)
            print(reason)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
