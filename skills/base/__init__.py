#!/usr/bin/env python3
"""
Skills Base - 模型提供者基类
===========================
所有模型提供商（Google/MiniMax/DeepSeek）都必须继承此基类。
实现"热插拔"：新增模型只需添加新的 skill，无需修改核心逻辑。
"""

from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, List
import logging

logger = logging.getLogger("SkillsBase")

class BaseModelSkill(ABC):
    """模型技能基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """技能名称，如 'google', 'minimax', 'deepseek'"""
        pass
    
    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """该技能支持的模型列表"""
        pass
    
    @property
    def priority(self) -> int:
        """优先级，数字越小优先级越高"""
        return 100
    
    @abstractmethod
    def stream(self, api_key: str, messages: List[Dict], **kwargs) -> Generator[str, None, None]:
        """
        流式调用接口
        
        Args:
            api_key: API 密钥
            messages: 消息列表
            **kwargs: 其他参数
            
        Yields:
            SSE 格式的数据块
        """
        pass
    
    @abstractmethod
    def health_check(self, api_key: str) -> bool:
        """
        健康检查
        
        Args:
            api_key: API 密钥
            
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    def is_model_supported(self, model_id: str) -> bool:
        """检查模型是否支持"""
        return any(m.lower() in model_id.lower() for m in self.supported_models)
    
    def get_error_info(self, exception: Exception) -> Dict[str, Any]:
        """解析异常信息"""
        error_msg = str(exception)
        error_type = type(exception).__name__
        
        # 常见错误码
        if "401" in error_msg or "Unauthorized" in error_msg:
            cause = "INVALID_KEY"
            suggestion = "检查 API Key 是否有效"
        elif "429" in error_msg or "Rate Limit" in error_msg:
            cause = "RATE_LIMIT"
            suggestion = "触发冷却期或切换备用 Key"
        elif "timeout" in error_msg.lower():
            cause = "TIMEOUT"
            suggestion = "检查网络连接或降低超时阈值"
        elif "connection" in error_msg.lower():
            cause = "CONNECTION_ERROR"
            suggestion = "检查代理设置和网络连通性"
        else:
            cause = error_type
            suggestion = "查看完整错误日志"
        
        return {
            "type": cause,
            "message": error_msg[:100],
            "suggestion": suggestion
        }


class SkillRegistry:
    """技能注册表 - 管理所有模型技能"""
    
    _skills: Dict[str, BaseModelSkill] = {}
    
    @classmethod
    def register(cls, skill: BaseModelSkill):
        """注册技能"""
        cls._skills[skill.name] = skill
        logger.info(f"🧩 技能注册: {skill.name} (priority={skill.priority})")
    
    @classmethod
    def get(cls, name: str) -> BaseModelSkill:
        """获取技能"""
        return cls._skills.get(name)
    
    @classmethod
    def get_all(cls) -> List[BaseModelSkill]:
        """获取所有技能（按优先级排序）"""
        skills = list(cls._skills.values())
        skills.sort(key=lambda s: s.priority)
        return skills
    
    @classmethod
    def find_for_model(cls, model_id: str) -> BaseModelSkill:
        """根据模型 ID 找到对应的技能"""
        for skill in cls.get_all():
            if skill.is_model_supported(model_id):
                return skill
        return None
    
    @classmethod
    def list_skills(cls) -> List[str]:
        """列出所有已注册的技能"""
        return list(cls._skills.keys())


def auto_register_skills():
    """自动导入并注册所有技能"""
    try:
        from skills.google import GoogleSkill
        from skills.minimax import MiniMaxSkill
        from skills.deepseek import DeepSeekSkill
        
        SkillRegistry.register(GoogleSkill())
        SkillRegistry.register(MiniMaxSkill())
        SkillRegistry.register(DeepSeekSkill())
        
        logger.info(f"✅ 自动注册完成，共 {len(SkillRegistry.list_skills())} 个技能")
    except ImportError as e:
        logger.warning(f"⚠️ 部分技能导入失败: {e}")
