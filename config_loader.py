#!/usr/bin/env python3
"""
Config Loader - 配置文件加载器

V2.0 - YAML 配置驱动
支持从 YAML 文件加载配置，与 JSON 配置共存
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("config_loader")

# 尝试导入 YAML
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logger.warning("PyYAML not installed. Run: pip install pyyaml")


@dataclass
class TelemetryConfig:
    """埋点配置"""
    enabled: bool = True
    endpoint: Optional[str] = None
    log_level: str = "INFO"
    record: list = field(default_factory=lambda: ["model_selection", "latency", "errors"])


@dataclass
class SettingsConfig:
    """全局设置"""
    cooldown_threshold: int = 3
    cache_ttl_seconds: int = 14400
    enable_fallback: bool = True
    prefer_free: bool = True
    default_task_type: str = "balanced"
    enable_performance_tracking: bool = True
    performance_retention_days: int = 7


@dataclass
class Config:
    """配置对象"""
    version: str = "2.0.0"
    models: Dict[str, Dict] = field(default_factory=dict)
    task_mappings: Dict[str, list] = field(default_factory=dict)
    fallback: Dict[str, list] = field(default_factory=dict)
    settings: SettingsConfig = field(default_factory=SettingsConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)
    adapters: Dict[str, Dict] = field(default_factory=dict)


class ConfigLoader:
    """配置加载器"""
    
    # 配置文件路径
    CONFIG_DIR = Path(__file__).parent
    YAML_CONFIG = CONFIG_DIR / "config.yaml"
    JSON_CONFIG = CONFIG_DIR / "models_config.json"
    
    def __init__(self):
        self._config: Optional[Config] = None
        self._load_config()
    
    def _load_config(self):
        """加载配置"""
        # 优先加载 YAML
        if YAML_AVAILABLE and self.YAML_CONFIG.exists():
            self._load_yaml()
        elif self.JSON_CONFIG.exists():
            self._load_json()
        else:
            logger.warning("No config file found, using defaults")
            self._config = Config()
    
    def _load_yaml(self):
        """从 YAML 加载配置"""
        try:
            with open(self.YAML_CONFIG, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 解析设置
            settings_data = data.get("settings", {})
            settings = SettingsConfig(
                cooldown_threshold=settings_data.get("cooldown_threshold", 3),
                cache_ttl_seconds=settings_data.get("cache_tl_seconds", 14400),
                enable_fallback=settings_data.get("enable_fallback", True),
                prefer_free=settings_data.get("prefer_free", True),
                default_task_type=settings_data.get("default_task_type", "balanced"),
                enable_performance_tracking=settings_data.get("enable_performance_tracking", True),
                performance_retention_days=settings_data.get("performance_retention_days", 7),
            )
            
            # 解析埋点
            telemetry_data = data.get("telemetry", {})
            telemetry = TelemetryConfig(
                enabled=telemetry_data.get("enabled", True),
                endpoint=telemetry_data.get("endpoint"),
                log_level=telemetry_data.get("log_level", "INFO"),
                record=telemetry_data.get("record", ["model_selection", "latency", "errors"]),
            )
            
            # 构建配置对象
            self._config = Config(
                version=data.get("version", "2.0.0"),
                models=data.get("models", {}),
                task_mappings=data.get("task_mappings", {}),
                fallback=data.get("fallback", {}),
                settings=settings,
                telemetry=telemetry,
                adapters=data.get("adapters", {}),
            )
            
            logger.info(f"[ConfigLoader] 从 YAML 加载配置: {len(self._config.models)} 个模型")
            
        except Exception as e:
            logger.error(f"[ConfigLoader] YAML 加载失败: {e}")
            self._load_json()
    
    def _load_json(self):
        """从 JSON 加载配置 (后备)"""
        try:
            if self.JSON_CONFIG.exists():
                with open(self.JSON_CONFIG, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._config = Config(
                    version=data.get("version", "1.0.0"),
                    models=data.get("models", {}),
                    task_mappings=data.get("task_mappings", {}),
                    fallback=data.get("fallback", {}),
                )
                
                logger.info(f"[ConfigLoader] 从 JSON 加载配置: {len(self._config.models)} 个模型")
        except Exception as e:
            logger.error(f"[ConfigLoader] JSON 加载失败: {e}")
            self._config = Config()
    
    @property
    def config(self) -> Config:
        """获取配置对象"""
        return self._config
    
    def get_models(self) -> Dict[str, Dict]:
        """获取模型配置"""
        return self._config.models if self._config else {}
    
    def get_task_mapping(self, task_type: str) -> list:
        """获取任务类型映射"""
        return self._config.task_mappings.get(task_type, [])
    
    def get_fallback_order(self, task_type: str = "default") -> list:
        """获取降级顺序"""
        return self._config.fallback.get(task_type, self._config.fallback.get("default", []))
    
    def get_settings(self) -> SettingsConfig:
        """获取设置"""
        return self._config.settings
    
    def get_telemetry(self) -> TelemetryConfig:
        """获取埋点配置"""
        return self._config.telemetry
    
    def is_enabled(self, model_id: str) -> bool:
        """检查模型是否启用"""
        model = self._config.models.get(model_id, {})
        return model.get("enabled", True)


# 全局配置实例
_config_loader: Optional[ConfigLoader] = None


def get_config() -> Config:
    """获取全局配置"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.config


def reload_config():
    """重新加载配置"""
    global _config_loader
    _config_loader = ConfigLoader()
    return _config_loader.config


if __name__ == "__main__":
    # 测试
    config = get_config()
    print(f"Version: {config.version}")
    print(f"Models: {len(config.models)}")
    print(f"Settings: {config.settings.prefer_free}")
    print(f"Telemetry: {config.telemetry.enabled}")
