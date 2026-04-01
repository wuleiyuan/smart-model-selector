#!/usr/bin/env python3
"""
Selector Factory - 选择器工厂类

V3.0.0 - 通用架构

根据平台类型动态实例化对应的适配器。
支持扩展新平台，只需注册即可。
"""

import logging
from typing import Dict, Optional, Any

logger = logging.getLogger("selector_factory")

# 导入所有适配器
from base_adapter import BasePlatformAdapter, BaseAPIServerAdapter, BaseCLIAdapter
from selector_core import SelectorCore


class SelectorFactory:
    """
    选择器工厂类
    
    根据平台名称返回对应的适配器实例。
    支持注册新的平台适配器。
    """
    
    # 注册表
    _adapters: Dict[str, type] = {}
    
    # 核心实例缓存
    _core_instance: Optional[SelectorCore] = None
    
    @classmethod
    def register(cls, platform_name: str, adapter_class: type):
        """
        注册平台适配器
        
        Args:
            platform_name: 平台名称
            adapter_class: 适配器类
        """
        cls._adapters[platform_name] = adapter_class
        logger.info(f"[Factory] 注册适配器: {platform_name} -> {adapter_class.__name__}")
    
    @classmethod
    def get_core(cls) -> SelectorCore:
        """
        获取核心实例 (单例)
        
        Returns:
            SelectorCore 实例
        """
        if cls._core_instance is None:
            cls._core_instance = SelectorCore()
        return cls._core_instance
    
    @classmethod
    def get_adapter(cls, platform_name: str) -> BasePlatformAdapter:
        """
        获取平台适配器
        
        Args:
            platform_name: 平台名称
        
        Returns:
            适配器实例
        
        Raises:
            ValueError: 未知的平台
        """
        if platform_name not in cls._adapters:
            raise ValueError(f"未知平台: {platform_name}. 可用平台: {list(cls._adapters.keys())}")
        
        adapter_class = cls._adapters[platform_name]
        return adapter_class()
    
    @classmethod
    def create(cls, platform_name: str) -> BasePlatformAdapter:
        """
        创建适配器 (别名)
        
        Args:
            platform_name: 平台名称
        
        Returns:
            适配器实例
        """
        return cls.get_adapter(platform_name)
    
    @classmethod
    def list_platforms(cls) -> list:
        """
        列出所有已注册的平台
        
        Returns:
            平台名称列表
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def auto_detect(cls, request_data: Any) -> str:
        """
        自动检测平台类型
        
        Args:
            request_data: 请求数据
        
        Returns:
            平台名称
        """
        # 根据请求数据自动推断平台
        if isinstance(request_data, dict):
            # OpenClaw / OpenAI 格式
            if "messages" in request_data:
                return "openclaw"
            if "task" in request_data:
                return "opencode"
        
        # 字符串输入 -> OpenCode
        if isinstance(request_data, str):
            return "opencode"
        
        # 默认返回 openclaw
        return "openclaw"


# ============ 初始化注册 ============

def _register_default_adapters():
    """注册默认适配器"""
    from adapter_opencode import OpenCodeAdapter
    from adapter_openclaw import OpenClawAdapter
    
    SelectorFactory.register("opencode", OpenCodeAdapter)
    SelectorFactory.register("openclaw", OpenClawAdapter)
    
    logger.info("[Factory] 默认适配器注册完成")


# 初始化
_register_default_adapters()


# ============ 便捷函数 ============

def get_selector(platform: str = "auto", **kwargs) -> tuple:
    """
    获取选择器 (便捷函数)
    
    Args:
        platform: 平台名称，"auto" 自动检测
        **kwargs: 传递给适配器的额外参数
    
    Returns:
        (adapter, core) 元组
    """
    # 自动检测
    if platform == "auto":
        platform = SelectorFactory.list_platforms()[0]
    
    # 获取适配器和核心
    adapter = SelectorFactory.get_adapter(platform)
    core = SelectorFactory.get_core()
    
    return adapter, core


def select_model(task_description: str, platform: str = "auto") -> tuple:
    """
    选择模型 (最简用法)
    
    Args:
        task_description: 任务描述
        platform: 平台名称
    
    Returns:
        (model_id, reason) 元组
    """
    adapter, core = get_selector(platform)
    
    # 解析请求
    request = adapter.parse_request(task_description)
    
    # 选择模型
    model_id, reason = core.select(request["task_description"])
    
    return model_id, reason


# ============ 主函数 ============

def main():
    """测试入口"""
    import json
    
    # 列出所有平台
    print("已注册的平台:")
    for platform in SelectorFactory.list_platforms():
        print(f"  - {platform}")
    
    print("\n测试自动选择:")
    
    # 测试 OpenCode
    print("\n1. OpenCode 适配器:")
    adapter, core = get_selector("opencode")
    model, reason = adapter.parse_request("帮我写一个排序算法") | {} | {"task_description": "帮我写一个排序算法"}
    model_id, reason = core.select("帮我写一个排序算法")
    print(f"   模型: {model_id}")
    print(f"   原因: {reason}")
    
    # 测试 OpenClaw
    print("\n2. OpenClaw 适配器:")
    adapter, core = get_selector("openclaw")
    request = adapter.parse_chat_request({
        "model": "auto",
        "messages": [{"role": "user", "content": "分析这段代码"}]
    })
    model_id, reason = core.select(request["task_description"])
    print(f"   模型: {model_id}")
    print(f"   原因: {reason}")
    
    # 测试便捷函数
    print("\n3. 便捷函数:")
    model_id, reason = select_model("翻译这段话")
    print(f"   模型: {model_id}")
    print(f"   原因: {reason}")


if __name__ == "__main__":
    main()
