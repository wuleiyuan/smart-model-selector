#!/usr/bin/env python3
"""
OpenCode Smart Model Selector - Dual Engine Manager
双引擎冗余调度系统：自定义引擎 + OpenCode 原生引擎

特性:
- 双引擎冗余：自定义调度为主，原生为备
- 熔断降级：连续失败自动切换到原生引擎
- 状态持久化：记录当前使用的引擎
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum

# 添加项目根目录
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from model_selector import SmartModelSelector

logger = logging.getLogger("dual_engine")


class EngineType(Enum):
    """引擎类型"""
    CUSTOM = "custom"   # 自定义智能调度引擎
    NATIVE = "native"   # OpenCode 原生引擎


class DualEngineManager:
    """双引擎冗余调度管理器"""
    
    # 引擎状态文件
    ENGINE_STATE_FILE = Path.home() / ".config" / "opencode" / "engine_state.json"
    
    # 熔断阈值
    CIRCUIT_BREAK_THRESHOLD = 3  # 连续失败3次触发熔断
    
    def __init__(self):
        self.current_engine = self._load_engine_state()
        self.custom_selector = SmartModelSelector()
        self.failure_count = 0
        
    def _load_engine_state(self) -> EngineType:
        """加载引擎状态"""
        try:
            if self.ENGINE_STATE_FILE.exists():
                with open(self.ENGINE_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    engine = data.get("engine", "custom")
                    return EngineType.CUSTOM if engine == "custom" else EngineType.NATIVE
        except Exception:
            pass
        return EngineType.CUSTOM
    
    def _save_engine_state(self):
        """保存引擎状态"""
        try:
            self.ENGINE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ENGINE_STATE_FILE, 'w') as f:
                json.dump({
                    "engine": self.current_engine.value,
                    "failure_count": self.failure_count
                }, f)
        except Exception as e:
            logger.warning(f"无法保存引擎状态: {e}")
    
    def set_engine(self, engine: EngineType):
        """手动切换引擎"""
        self.current_engine = engine
        self.failure_count = 0
        self._save_engine_state()
        logger.info(f"🔄 引擎切换至: {engine.value}")
    
    def get_current_engine(self) -> EngineType:
        """获取当前引擎"""
        return self.current_engine
    
    def get_status(self) -> dict:
        """获取引擎状态"""
        return {
            "current_engine": self.current_engine.value,
            "failure_count": self.failure_count,
            "circuit_breaker_active": self.failure_count >= self.CIRCUIT_BREAK_THRESHOLD
        }
    
    def record_failure(self):
        """记录失败次数"""
        self.failure_count += 1
        self._save_engine_state()
        
        if self.failure_count >= self.CIRCUIT_BREAK_THRESHOLD:
            logger.warning(f"⚠️ 熔断触发！连续失败 {self.failure_count} 次，切换到原生引擎")
            self.current_engine = EngineType.NATIVE
    
    def record_success(self):
        """记录成功，清零失败计数"""
        if self.failure_count > 0:
            self.failure_count = 0
            self._save_engine_state()
    
    def select(self, task_description: str) -> Tuple[str, str]:
        """
        带冗余的模型选择：自定义引擎为主，原生引擎为备
        
        带冗余的模型选择
        
        Returns:
            (model_id, engine_info)
        """
        
        # 优先使用自定义引擎
        if self.current_engine == EngineType.NATIVE:
            native_model = self._get_native_model()
            return native_model, "[Engine: Native]"
        
        # 尝试使用自定义引擎
        try:
            model, reason = self.custom_selector.select(task_description)
            
            # 检查模型是否可用
            if self._is_model_available(model.id):
                self.record_success()
                return model.id, f"[Engine: Custom] {reason}"
            else:
                raise Exception(f"模型 {model.id} 不可用")
                
        except Exception as e:
            logger.warning(f"⚠️ 自定义引擎失败: {e}，记录失败")
            self.record_failure()
            
            # 熔断后返回原生
            if self.current_engine == EngineType.NATIVE:
                native_model = self._get_native_model()
                return native_model, "[Engine: Native-Fallback]"
            
            # 否则使用原生作为 fallback
            native_model = self._get_native_model()
            return native_model, "[Engine: Native-Fallback]"
    
    def _is_model_available(self, model_id: str) -> bool:
        """检查模型是否可用"""
        # 简单检查：模型 ID 不为空
        return bool(model_id)
    
    def _get_native_model(self) -> str:
        """获取 OpenCode 原生免费模型"""
        # 优先使用 minimax-2.5-free（用户首选）
        return "minimax-2.5-free"


# 全局单例
_manager: Optional[DualEngineManager] = None


def get_manager() -> DualEngineManager:
    """获取全局管理器单例"""
    global _manager
    if _manager is None:
        _manager = DualEngineManager()
    return _manager


def main():
    """CLI 入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="双引擎管理器")
    parser.add_argument("--status", action="store_true", help="查看引擎状态")
    parser.add_argument("--engine", choices=["custom", "native"], help="切换引擎")
    parser.add_argument("--select", type=str, help="选择模型")
    
    args = parser.parse_args()
    
    manager = get_manager()
    
    if args.status:
        status = manager.get_status()
        print(f"当前引擎: {status['current_engine']}")
        print(f"失败次数: {status['failure_count']}")
        print(f"熔断状态: {'激活' if status['circuit_breaker_active'] else '正常'}")
    
    elif args.engine:
        engine = EngineType.CUSTOM if args.engine == "custom" else EngineType.NATIVE
        manager.set_engine(engine)
        print(f"✅ 已切换至: {args.engine}")
    
    elif args.select:
        model, info = manager.select(args.select)
        print(f"选择模型: {model}")
        print(info)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
