#!/usr/bin/env python3
"""
Smart Model Selector Core - 智能模型选择器核心

V3.0.0 - 通用核心架构

功能：
- 任务分析 (Task Analyzer)
- 模型路由 (Model Router)
- 性能监控 (Performance Tracker)

设计原则：
- 核心层绝对不包含任何特定平台的业务逻辑
- 只做纯粹的模型评估与路由
"""

import json
import re
import time
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("selector_core")


# ============ 数据结构 ============

class TaskType(Enum):
    """任务类型"""
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"
    FAST = "fast"
    MULTIMODAL = "multimodal"
    BALANCED = "balanced"


class ModelCapability(Enum):
    """模型能力标签"""
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"
    FAST = "fast"
    CHEAP = "cheap"
    MULTIMODAL = "multimodal"
    BALANCED = "balanced"
    LONG_CONTEXT = "long_context"
    PREMIUM = "premium"


@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    provider: str
    capabilities: List[ModelCapability]
    context_window: int = 200000
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    latency_tier: str = "fast"


@dataclass
class TaskRequest:
    """标准任务请求"""
    description: str
    task_type: Optional[TaskType] = None
    estimated_tokens: int = 0
    require_vision: bool = False
    budget_constraint: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelScore:
    """模型评分"""
    model_id: str
    score: float
    reason: str
    latency_estimate: float = 0.0
    cost_estimate: float = 0.0


# ============ 模型注册表 ============

class ModelRegistry:
    """模型注册表 - 支持从配置文件加载"""
    
    # 配置文件路径
    CONFIG_FILE = Path(__file__).parent / "models_config.json"
    
    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        self._settings: Dict[str, Any] = {}
        self._load_from_config()
    
    def _load_from_config(self):
        """从配置文件加载模型"""
        try:
            if self.CONFIG_FILE.exists():
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._settings = config.get("settings", {})
                models_data = config.get("models", {})
                
                for model_id, model_data in models_data.items():
                    if not model_data.get("enabled", True):
                        continue
                    
                    # 解析 capabilities
                    capabilities = []
                    for cap_str in model_data.get("capabilities", []):
                        try:
                            capabilities.append(ModelCapability(cap_str))
                        except ValueError:
                            logger.warning(f"[ModelRegistry] 未知能力标签: {cap_str}")
                    
                    model_info = ModelInfo(
                        id=model_data.get("id", model_id),
                        name=model_data.get("name", model_id),
                        provider=model_data.get("provider", "unknown"),
                        capabilities=capabilities,
                        context_window=model_data.get("context_window", 128000),
                        cost_per_1k_input=model_data.get("cost_per_1k_input", 0.0),
                        cost_per_1k_output=model_data.get("cost_per_1k_output", 0.0),
                        latency_tier=model_data.get("latency_tier", "fast"),
                    )
                    self._models[model_id] = model_info
                
                logger.info(f"[ModelRegistry] 从配置文件加载了 {len(self._models)} 个模型")
                return
        except Exception as e:
            logger.warning(f"[ModelRegistry] 加载配置文件失败: {e}")
        
        # 配置文件加载失败时使用默认模型
        self._register_default_models()
    
    def _register_default_models(self):
        """注册默认模型（配置文件加载失败时的后备）"""
        models = [
            ModelInfo("claude-opus-4-6", "Claude Opus 4.6", "anthropic",
                     [ModelCapability.RESEARCH, ModelCapability.WRITING, ModelCapability.LONG_CONTEXT],
                     200000, 15.0, 75.0, "medium"),
            ModelInfo("claude-sonnet-4-5", "Claude Sonnet 4.5", "anthropic",
                     [ModelCapability.CODING, ModelCapability.BALANCED],
                     200000, 3.0, 15.0, "fast"),
            ModelInfo("claude-haiku-3-5", "Claude Haiku 3.5", "anthropic",
                     [ModelCapability.FAST, ModelCapability.CHEAP],
                     200000, 0.8, 4.0, "fast"),
            ModelInfo("gemini-2-0-pro", "Gemini 2.0 Pro", "google",
                     [ModelCapability.RESEARCH, ModelCapability.MULTIMODAL, ModelCapability.LONG_CONTEXT],
                     2000000, 1.25, 5.0, "medium"),
            ModelInfo("gemini-2-0-flash", "Gemini 2.0 Flash", "google",
                     [ModelCapability.FAST, ModelCapability.CODING, ModelCapability.CHEAP],
                     1000000, 0.0, 0.0, "fast"),
            ModelInfo("gpt-4o", "GPT-4o", "openai",
                     [ModelCapability.CODING, ModelCapability.BALANCED],
                     128000, 2.5, 10.0, "fast"),
            ModelInfo("gpt-4o-mini", "GPT-4o Mini", "openai",
                     [ModelCapability.FAST, ModelCapability.CHEAP],
                     128000, 0.15, 0.6, "fast"),
            ModelInfo("deepseek-chat", "DeepSeek Chat", "deepseek",
                     [ModelCapability.CODING, ModelCapability.CHEAP],
                     64000, 0.14, 0.28, "fast"),
            ModelInfo("qwen-2-5-coder-32b", "Qwen 2.5 Coder 32B", "qwen",
                     [ModelCapability.CODING, ModelCapability.CHEAP],
                     32000, 0.0, 0.0, "fast"),
            ModelInfo("minimax-2.5-free", "MiniMax 2.5 (Free)", "opencode",
                     [ModelCapability.FAST, ModelCapability.CHEAP],
                     128000, 0.0, 0.0, "fast"),
        ]
        for m in models:
            self._models[m.id] = m
        logger.info(f"[ModelRegistry] 使用默认模型列表 ({len(self._models)} 个)")
    
    def get_model(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)
    
    def list_models(self) -> Dict[str, ModelInfo]:
        return self._models.copy()
    
    def get_models_by_capability(self, cap: ModelCapability) -> List[ModelInfo]:
        return [m for m in self._models.values() if cap in m.capabilities]


# ============ 任务分析器 ============

class TaskAnalyzer:
    """任务分析器"""
    
    TASK_PATTERNS = {
        TaskType.CODING: [r"(code|编程|写代码|debug|bug|修复|函数|算法)"],
        TaskType.RESEARCH: [r"(分析|研究|调研|比较|评估|总结|解释)"],
        TaskType.WRITING: [r"(写|创作|编辑|修改|润色|翻译|总结)"],
        TaskType.FAST: [r"(快速|简单|短|立即)"],
        TaskType.MULTIMODAL: [r"(图片|图像|图表|截图|照片)"],
    }
    
    def analyze(self, description: str) -> TaskType:
        desc_lower = description.lower()
        for task_type, patterns in self.TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, desc_lower, re.IGNORECASE):
                    return task_type
        return TaskType.BALANCED
    
    def estimate_complexity(self, description: str) -> str:
        length = len(description)
        if length < 50:
            return "simple"
        elif length > 500:
            return "complex"
        return "medium"


# ============ 性能监控 ============

class PerformanceMonitor:
    """性能监控"""
    
    CACHE_FILE = Path.home() / ".config" / "smart_selector" / "performance.json"
    
    def __init__(self):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._load_cache()
    
    def _load_cache(self):
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    self._data = data.get("performance", {})
        except Exception:
            pass
    
    def _save_cache(self):
        try:
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"performance": self._data, "updated_at": int(time.time())}
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(data, f)
        except Exception:
            pass
    
    def record(self, model_id: str, latency: float, success: bool):
        if model_id not in self._data:
            self._data[model_id] = {"latency_sum": 0.0, "success_count": 0, "fail_count": 0, "last_used": 0}
        stats = self._data[model_id]
        stats["latency_sum"] += latency
        stats["success_count"] += 1 if success else 0
        stats["fail_count"] += 0 if success else 1
        stats["last_used"] = int(time.time())
        self._save_cache()
    
    def get_average_latency(self, model_id: str) -> float:
        stats = self._data.get(model_id)
        if not stats or stats["success_count"] == 0:
            return 0.0
        return stats["latency_sum"] / stats["success_count"]
    
    def get_success_rate(self, model_id: str) -> float:
        stats = self._data.get(model_id)
        if not stats:
            return 1.0
        total = stats["success_count"] + stats["fail_count"]
        if total == 0:
            return 1.0
        return stats["success_count"] / total
    
    def is_in_cooldown(self, model_id: str) -> bool:
        return self.get_success_rate(model_id) < 0.5


# ============ 模型路由器 ============

class ModelRouter:
    """模型路由器"""
    
    def __init__(self, registry: ModelRegistry, monitor: PerformanceMonitor):
        self.registry = registry
        self.monitor = monitor
    
    def select(self, task_type: TaskType, complexity: str = "medium") -> Tuple[str, str]:
        candidates = self._get_candidates(task_type)
        if not candidates:
            return "minimax-2.5-free", "[Default] 无候选模型"
        
        scored = self._score_models(candidates, task_type, complexity)
        return scored[0].model_id, scored[0].reason
    
    def _get_candidates(self, task_type: TaskType) -> List[ModelInfo]:
        cap_map = {
            TaskType.CODING: ModelCapability.CODING,
            TaskType.RESEARCH: ModelCapability.RESEARCH,
            TaskType.WRITING: ModelCapability.WRITING,
            TaskType.FAST: ModelCapability.FAST,
            TaskType.MULTIMODAL: ModelCapability.MULTIMODAL,
            TaskType.BALANCED: ModelCapability.BALANCED,
        }
        cap = cap_map.get(task_type)
        if cap:
            return self.registry.get_models_by_capability(cap)
        return list(self.registry.list_models().values())
    
    def _score_models(self, models: List[ModelInfo], task_type: TaskType, 
                     complexity: str) -> List[ModelScore]:
        results = []
        for m in models:
            if self.monitor.is_in_cooldown(m.id):
                continue
            score = self._calculate_score(m, task_type, complexity)
            results.append(score)
        return sorted(results, key=lambda x: x.score, reverse=True)
    
    def _calculate_score(self, model: ModelInfo, task_type: TaskType, 
                       complexity: str) -> ModelScore:
        score = 100.0
        reasons = []
        
        cap_map = {
            TaskType.CODING: ModelCapability.CODING,
            TaskType.RESEARCH: ModelCapability.RESEARCH,
            TaskType.WRITING: ModelCapability.WRITING,
            TaskType.FAST: ModelCapability.FAST,
            TaskType.MULTIMODAL: ModelCapability.MULTIMODAL,
        }
        
        required = cap_map.get(task_type)
        if required and required in model.capabilities:
            score += 20
            reasons.append(f"能力匹配:{required.value}")
        
        latency = self.monitor.get_average_latency(model.id)
        if model.latency_tier == "fast":
            score += 10
        
        total_cost = model.cost_per_1k_input + model.cost_per_1k_output
        if total_cost == 0:
            score += 15
            reasons.append("免费模型")
        
        if complexity == "simple" and model.latency_tier == "fast":
            score += 10
        
        reason = ", ".join(reasons) if reasons else "默认选择"
        return ModelScore(model.id, score, reason, latency, total_cost)


# ============ 核心调度器 ============

class SelectorCore:
    """智能选择器核心"""
    
    def __init__(self):
        self.registry = ModelRegistry()
        self.monitor = PerformanceMonitor()
        self.analyzer = TaskAnalyzer()
        self.router = ModelRouter(self.registry, self.monitor)
    
    def select(self, task_description: str) -> Tuple[str, str]:
        task_type = self.analyzer.analyze(task_description)
        complexity = self.analyzer.estimate_complexity(task_description)
        model_id, reason = self.router.select(task_type, complexity)
        logger.info(f"[SelectorCore] 选择: {model_id} - {reason}")
        return model_id, reason
    
    def record_result(self, model_id: str, latency: float, success: bool):
        self.monitor.record(model_id, latency, success)
    
    def get_models(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for mid, m in self.registry.list_models().items():
            result[mid] = {
                "name": m.name,
                "provider": m.provider,
                "capabilities": [c.value for c in m.capabilities],
                "context_window": m.context_window,
                "cost_per_1k_input": m.cost_per_1k_input,
                "cost_per_1k_output": m.cost_per_1k_output,
                "latency_tier": m.latency_tier,
                "avg_latency": self.monitor.get_average_latency(mid),
                "success_rate": self.monitor.get_success_rate(mid),
            }
        return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Smart Model Selector Core V3.0.0")
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--list", action="store_true", help="列出所有模型")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()
    
    core = SelectorCore()
    
    if args.list:
        print(json.dumps(core.get_models(), ensure_ascii=False, indent=2))
        return
    
    if args.task:
        model_id, reason = core.select(args.task)
        if args.json:
            print(json.dumps({"model": model_id, "reason": reason}, ensure_ascii=False, indent=2))
        else:
            print(model_id)
            print(reason)


if __name__ == "__main__":
    main()
