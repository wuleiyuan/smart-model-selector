"""
OpenCode Smart Model Selector 版本管理模块

版本号格式: MAJOR.MINOR.PATCH
- MAJOR: 不兼容的 API 变更
- MINOR: 向后兼容的新功能
- PATCH: 向后兼容的 bug 修复
"""

__version__ = "4.2.0"
__author__ = "OpenCode Team"
__description__ = "智能模型调度系统"

# 版本历史
VERSION_HISTORY = {
    "1.0.0": {
        "date": "2025-01-01",
        "description": "初始版本 - 智能模型选择 + 故障转移"
    },
    "2.0.0": {
        "date": "2025-02-25", 
        "description": "重大更新: 手动指定模型 > 自动推荐优先级, 24h TTL, 连续3次失败自动切换, op auto/reset 命令, 长文本降级策略, 测速记忆持久化"
    },
    "2.1.0": {
        "date": "2026-02-26",
        "description": "新增功能: API Server 模块 (OpenAI 兼容接口), op api 命令"
    },
    "2.2.0": {
        "date": "2026-02-27",
        "description": "新增功能: 双引擎架构, 熔断降级, 并发优化, 测速缓存4h过期, op engine 命令"
    },
    "3.0.0": {
        "date": "2026-03-01",
        "description": "架构升级: 通用核心 + 适配器模式, 六边形架构"
    },
    "3.1.0": {
        "date": "2026-03-02",
        "description": "配置驱动: models_config.json, 零代码添加模型"
    },
    "4.0.0": {
        "date": "2026-03-02",
        "description": "V2.0增强期: YAML配置+性能埋点+动态降级"
    },
    "4.0.1": {
        "date": "2026-03-02",
        "description": "Bug 修复: 代码重构优化"
    },
    "4.1.0": {
        "date": "2026-04-02",
        "description": "架构重构: 物理级双引擎分配与意图直达"
    },
    "4.1.1": {
        "date": "2026-04-06",
        "description": "修复: OpenCode 集成问题修复，模型智能切换优化"
    },
    "4.1.2": {
        "date": "2026-04-06",
        "description": "修复: CLI输出纯模型ID，兼容OpenCode解析"
    },
    "4.1.3": {
        "date": "2026-04-06",
        "description": "精简: smart_model_dispatcher.py 代码重构，移除冗余逻辑"
    },
    "4.2.0": {
        "date": "2026-04-08",
        "description": "功能增强: 添加 gemini-2.5-pro/flash 模型支持，配置回退机制"
    }
}

def get_version():
    """获取当前版本号"""
    return __version__

def get_version_info():
    """获取详细版本信息"""
    return {
        "version": __version__,
        "author": __author__,
        "description": __description__,
        "history": VERSION_HISTORY
    }

def print_version():
    """打印版本信息"""
    print(f"OpenCode Smart Model Selector v{__version__}")
    print(f"Author: {__author__}")
    print()
    print("版本历史:")
    for ver, info in VERSION_HISTORY.items():
        print(f"  v{ver} ({info['date']}) - {info['description']}")

if __name__ == "__main__":
    print_version()