"""
OpenCode Smart Model Selector 版本管理模块

版本号格式: MAJOR.MINOR.PATCH
- MAJOR: 不兼容的 API 变更
- MINOR: 向后兼容的新功能
- PATCH: 向后兼容的 bug 修复
"""

__version__ = "4.0.0"
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
        "description": """重大更新:
        - 手动指定模型 > 自动推荐优先级 (24h TTL, 连续3次失败自动切换)
        - 添加 op auto/reset 命令恢复智能模式
        - 长文本降级策略 (>8000 tokens 自动用免费模型)
        - 测速记忆持久化 (latency_cache.json 热启动)
        - JSON 配置容错机制 (自动备份回退)
        - Bash 兼容 (auto_start.sh 支持 PROMPT_COMMAND)
        - 版本管理模块 (version.py)
        """
    },
    "2.1.0": {
        "date": "2026-02-26",
        "description": """新增功能:
        - API Server 模块 (api_server.py) - OpenAI 兼容接口
        - 新增 op api start/stop/restart 命令
        - 支持作为 Openclaw 模型供应商
        - 支持 /v1/chat/completions 和 /v1/models 端点
        """
    },
    "2.2.0": {
        "date": "2026-02-27",
        "description": """新增功能:
        - 双引擎架构 (dual_engine.py) - 自定义 + 原生冗余
        - 熔断降级机制 - 连续3次失败自动切换
        - API Server 并发优化 - gunicorn 支持
        - 测速缓存生命周期 - 4小时后自动刷新
        - op engine 命令 - 手动切换引擎
        """
    },
    "3.1.0": {
        "date": "2026-03-02",
        "description": """配置驱动架构升级:
        - models_config.json - 模型配置文件 (JSON)
        - selector_core.py - 支持从配置文件动态加载模型
        - 零代码添加模型 - 只需编辑 JSON 配置文件
        - 向后兼容 - 配置文件加载失败时自动回退
        - 新增 PREMIUM 能力标签
    "3.1.0": {
        "date": "2026-03-02",
        "description": """配置驱动架构升级:
        - models_config.json - 模型配置文件 (JSON)
        - selector_core.py - 支持从配置文件动态加载模型
        - 零代码添加模型 - 只需编辑 JSON 配置文件
        - 向后兼容 - 配置文件加载失败时自动回退
        - 新增 PREMIUM 能力标签
        """
    },
    "4.0.0": {
        "date": "2026-03-02",
        "description": """V2.0 增强期 - YAML配置+埋点+动态降级:
        - config.yaml - YAML 配置文件
        - config_loader.py - 配置加载器
        - telemetry.py - 性能埋点收集
        - fallback_strategy.py - 动态降级策略
        - 7天性能数据保留
        """
    }
}
    }
}
        "date": "2026-03-01",
        "description": """架构升级 - 通用核心 + 适配器模式:
        - selector_core.py - 核心逻辑 (任务分析 + 模型路由 + 性能监控)
        - base_adapter.py - 抽象基类 (定义标准接口)
        - adapter_opencode.py - OpenCode 适配器
        - adapter_openclaw.py - OpenClaw 适配器
        - selector_factory.py - 工厂类 (动态实例化)
        - 六边形架构 - 核心与平台解耦
        - 支持扩展新平台
        """
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
        print(f"  v{ver} ({info['date']})")
        for line in info['description'].strip().split('\n'):
            print(f"    {line.strip()}")

if __name__ == "__main__":
    print_version()
