#!/usr/bin/env python3
"""
Dynamic Fallback Strategy - 动态降级策略

V2.0 - 动态降级
根据性能数据和配置自动选择降级模型
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("fallback")


class FallbackTrigger(Enum):
    """降级触发条件"""
    ERROR = "error"           # 错误触发
    LATENCY = "latency"       # 延迟过高
    COST = "cost"             # 成本过高
    MANUAL = "manual"         # 手动触发


@dataclass
class FallbackRule:
    """降级规则"""
    trigger: FallbackTrigger
    threshold: float
    fallback_model: str
    cooldown_seconds: int = 60


class DynamicFallback:
    """动态降级策略"""
    
    def __init__(self, 
                 fallback_order: Dict[str, List[str]],
                 settings: Dict[str, Any],
                 telemetry=None):
        self.fallback_order = fallback_order
        self.settings = settings
        self.telemetry = telemetry
        
        # 降级状态
        self._cooldowns: Dict[str, int] = {}  # model_id -> unlock_timestamp
        self._current_fallback: Dict[str, str] = {}  # task_type -> fallback_model
        
        # 配置
        self.enable_fallback = settings.get("enable_fallback", True)
        self.cooldown_threshold = settings.get("cooldown_threshold", 3)
    
    def get_fallback(self, 
                     task_type: str, 
                     preferred_model: str,
                     error_count: int = 0,
                     avg_latency: float = 0.0) -> str:
        """
        获取降级模型
        
        Args:
            task_type: 任务类型
            preferred_model: 首选模型
            error_count: 连续错误次数
            avg_latency: 平均延迟
        
        Returns:
            降级后的模型 ID
        """
        if not self.enable_fallback:
            return preferred_model
        
        # 检查冷却
        if self._is_in_cooldown(preferred_model):
            logger.info(f"[Fallback] {preferred_model} 在冷却中，尝试降级")
            return self._get_fallback_for_task(task_type, preferred_model)
        
        # 检查是否需要降级
        if error_count >= self.cooldown_threshold:
            logger.warning(f"[Fallback] {preferred_model} 连续错误 {error_count} 次，触发降级")
            self._trigger_fallback(task_type, preferred_model, FallbackTrigger.ERROR)
            return self._get_fallback_for_task(task_type, preferred_model)
        
        # 检查延迟
        if avg_latency > 5000:  # 5秒
            logger.warning(f"[Fallback] {preferred_model} 延迟过高 ({avg_latency}ms)，触发降级")
            self._trigger_fallback(task_type, preferred_model, FallbackTrigger.LATENCY)
            return self._get_fallback_for_task(task_type, preferred_model)
        
        return preferred_model
    
    def _is_in_cooldown(self, model_id: str) -> bool:
        """检查模型是否在冷却中"""
        import time
        unlock_time = self._cooldowns.get(model_id, 0)
        return unlock_time > time.time()
    
    def _trigger_fallback(self, 
                          task_type: str, 
                          model_id: str, 
                          trigger: FallbackTrigger):
        """触发降级"""
        import time
        
        # 设置冷却时间 (默认 5 分钟)
        cooldown = 300
        self._cooldowns[model_id] = int(time.time()) + cooldown
        
        # 记录当前降级
        fallback_model = self._get_fallback_for_task(task_type, model_id)
        if fallback_model:
            self._current_fallback[task_type] = fallback_model
            logger.info(f"[Fallback] {task_type} 降级到: {fallback_model} (触发: {trigger.value})")
    
    def _get_fallback_for_task(self, task_type: str, original_model: str) -> str:
        """获取任务的降级模型"""
        # 获取该任务类型的降级顺序
        fallback_list = self.fallback_order.get(
            task_type, 
            self.fallback_order.get("default", [])
        )
        
        if not fallback_list:
            return "minimax-2.5-free"  # 默认降级到免费模型
        
        # 选择第一个可用的降级模型
        for model in fallback_list:
            if model != original_model and not self._is_in_cooldown(model):
                return model
        
        # 如果所有降级模型都在冷却中，返回默认免费模型
        return "minimax-2.5-free"
    
    def clear_cooldown(self, model_id: str):
        """清除冷却"""
        if model_id in self._cooldowns:
            del self._cooldowns[model_id]
            logger.info(f"[Fallback] 清除 {model_id} 的冷却")
    
    def clear_all_cooldowns(self):
        """清除所有冷却"""
        self._cooldowns.clear()
        self._current_fallback.clear()
        logger.info("[Fallback] 已清除所有冷却")
    
    def get_status(self) -> Dict[str, Any]:
        """获取降级状态"""
        import time
        return {
            "cooldowns": {
                model: ts - int(time.time()) 
                for model, ts in self._cooldowns.items()
                if ts > time.time()
            },
            "current_fallback": self._current_fallback,
            "enabled": self.enable_fallback,
        }


# 便捷函数
def create_fallback(fallback_config: Dict, settings: Dict, telemetry=None) -> DynamicFallback:
    """创建动态降级实例"""
    return DynamicFallback(fallback_config, settings, telemetry)


if __name__ == "__main__":
    # 测试
    fallback_config = {
        "default": ["minimax-2.5-free", "gemini-2-0-flash", "deepseek-chat"],
        "coding": ["deepseek-chat", "qwen-2-5-coder-32b", "gemini-2-0-flash"],
    }
    
    settings = {
        "enable_fallback": True,
        "cooldown_threshold": 3,
    }
    
    fb = create_fallback(fallback_config, settings)
    
    # 测试降级
    print("=== 正常情况 ===")
    print(f"选择: {fb.get_fallback('coding', 'claude-sonnet-4-5', error_count=0)}")
    
    print("\n=== 错误降级 ===")
    print(f"选择: {fb.get_fallback('coding', 'claude-sonnet-4-5', error_count=5)}")
    
    print("\n=== 状态 ===")
    print(fb.get_status())
