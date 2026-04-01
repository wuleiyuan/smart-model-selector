#!/usr/bin/env python3
"""
Performance Telemetry - 性能埋点收集

V2.0 - 性能数据埋点收集
记录模型选择决策、延迟、错误等信息
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger("telemetry")


@dataclass
class ModelSelectionEvent:
    """模型选择事件"""
    timestamp: int
    task_description: str
    task_type: str
    selected_model: str
    reason: str
    candidates: List[str]
    latency_ms: float
    cost_estimate: float


@dataclass
class ErrorEvent:
    """错误事件"""
    timestamp: int
    model_id: str
    error_type: str
    error_message: str
    task_description: str


class PerformanceTelemetry:
    """性能埋点收集器"""
    
    CACHE_DIR = Path.home() / ".config" / "smart_selector"
    TELEMETRY_FILE = CACHE_DIR / "telemetry.json"
    
    def __init__(self, enabled: bool = True, retention_days: int = 7):
        self.enabled = enabled
        self.retention_days = retention_days
        self._data: Dict[str, List] = {
            "selections": [],
            "errors": [],
            "latency": defaultdict(list),
        }
        self._load_cache()
    
    def _load_cache(self):
        """加载缓存"""
        try:
            if self.TELEMETRY_FILE.exists():
                with open(self.TELEMETRY_FILE, 'r') as f:
                    self._data = json.load(f)
                    # 清理过期数据
                    self._cleanup_old_data()
        except Exception:
            pass
    
    def _save_cache(self):
        """保存缓存"""
        try:
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.TELEMETRY_FILE, 'w') as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            logger.warning(f"[Telemetry] 保存失败: {e}")
    
    def _cleanup_old_data(self):
        """清理过期数据"""
        cutoff = int((datetime.now() - timedelta(days=self.retention_days)).timestamp())
        
        # 清理选择记录
        self._data["selections"] = [
            e for e in self._data.get("selections", [])
            if e.get("timestamp", 0) > cutoff
        ]
        
        # 清理错误记录
        self._data["errors"] = [
            e for e in self._data.get("errors", [])
            if e.get("timestamp", 0) > cutoff
        ]
    
    def record_selection(self, 
                        task_description: str,
                        task_type: str,
                        selected_model: str,
                        reason: str,
                        candidates: List[str],
                        latency_ms: float = 0.0,
                        cost_estimate: float = 0.0):
        """记录模型选择"""
        if not self.enabled:
            return
        
        event = {
            "timestamp": int(time.time()),
            "task_description": task_description[:200],  # 截断长文本
            "task_type": task_type,
            "selected_model": selected_model,
            "reason": reason,
            "candidates": candidates,
            "latency_ms": latency_ms,
            "cost_estimate": cost_estimate,
        }
        
        self._data.setdefault("selections", []).append(event)
        
        # 记录延迟
        if latency_ms > 0:
            self._data["latency"].setdefault(selected_model, []).append({
                "timestamp": int(time.time()),
                "latency_ms": latency_ms,
            })
        
        self._save_cache()
        logger.debug(f"[Telemetry] 记录选择: {selected_model}")
    
    def record_error(self,
                     model_id: str,
                     error_type: str,
                     error_message: str,
                     task_description: str = ""):
        """记录错误"""
        if not self.enabled:
            return
        
        event = {
            "timestamp": int(time.time()),
            "model_id": model_id,
            "error_type": error_type,
            "error_message": error_message[:500],
            "task_description": task_description[:200],
        }
        
        self._data.setdefault("errors", []).append(event)
        self._save_cache()
        logger.debug(f"[Telemetry] 记录错误: {model_id} - {error_type}")
    
    def get_model_stats(self, model_id: str) -> Dict[str, Any]:
        """获取模型统计"""
        selections = self._data.get("selections", [])
        errors = self._data.get("errors", [])
        
        model_selections = [s for s in selections if s.get("selected_model") == model_id]
        model_errors = [e for e in errors if e.get("model_id") == model_id]
        
        latencies = self._data.get("latency", {}).get(model_id, [])
        
        return {
            "total_selections": len(model_selections),
            "total_errors": len(model_errors),
            "error_rate": len(model_errors) / max(len(model_selections), 1),
            "avg_latency": sum(l.get("latency_ms", 0) for l in latencies) / max(len(latencies), 1),
            "last_used": model_selections[-1].get("timestamp") if model_selections else None,
        }
    
    def get_top_models(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最常用模型"""
        selections = self._data.get("selections", [])
        
        # 统计模型使用次数
        model_counts = defaultdict(int)
        for s in selections:
            model_counts[s.get("selected_model", "")] += 1
        
        # 排序
        sorted_models = sorted(
            model_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        result = []
        for model_id, count in sorted_models[:limit]:
            stats = self.get_model_stats(model_id)
            result.append({
                "model_id": model_id,
                "selection_count": count,
                **stats,
            })
        
        return result
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        errors = self._data.get("errors", [])
        
        # 按错误类型统计
        error_types = defaultdict(int)
        for e in errors:
            error_types[e.get("error_type", "unknown")] += 1
        
        # 按模型统计
        model_errors = defaultdict(int)
        for e in errors:
            model_errors[e.get("model_id", "unknown")] += 1
        
        return {
            "total_errors": len(errors),
            "by_type": dict(error_types),
            "by_model": dict(model_errors),
            "recent_errors": errors[-10:] if errors else [],
        }
    
    def export(self) -> Dict:
        """导出所有数据"""
        return {
            "exported_at": int(time.time()),
            "selections": self._data.get("selections", []),
            "errors": self._data.get("errors", []),
            "latency": dict(self._data.get("latency", {})),
        }
    
    def clear(self):
        """清除所有数据"""
        self._data = {"selections": [], "errors": [], "latency": defaultdict(list)}
        self._save_cache()
        logger.info("[Telemetry] 数据已清除")


# 全局实例
_telemetry: Optional[PerformanceTelemetry] = None


def get_telemetry(enabled: bool = True, retention_days: int = 7) -> PerformanceTelemetry:
    """获取埋点实例"""
    global _telemetry
    if _telemetry is None:
        _telemetry = PerformanceTelemetry(enabled, retention_days)
    return _telemetry


if __name__ == "__main__":
    # 测试
    tele = get_telemetry()
    
    # 记录测试数据
    tele.record_selection(
        task_description="写一个排序算法",
        task_type="coding",
        selected_model="claude-sonnet-4-5",
        reason="能力匹配",
        candidates=["claude-sonnet-4-5", "gpt-4o"],
        latency_ms=125.5,
        cost_estimate=0.0
    )
    
    tele.record_error(
        model_id="claude-opus-4-6",
        error_type="timeout",
        error_message="Request timeout after 30s",
        task_description="分析这段代码"
    )
    
    # 获取统计
    print("=== 模型统计 ===")
    print(tele.get_model_stats("claude-sonnet-4-5"))
    
    print("\n=== Top 模型 ===")
    print(tele.get_top_models())
    
    print("\n=== 错误摘要 ===")
    print(tele.get_error_summary())
