#!/usr/bin/env python3
"""
Base Platform Adapter - 平台适配器抽象基类

V3.0.0 - 通用架构

定义所有平台适配器必须实现的接口规范。
任何接入的平台都必须继承并实现这些方法。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("base_adapter")


class BasePlatformAdapter(ABC):
    """平台适配器抽象基类"""
    
    def __init__(self, platform_name: str):
        """
        初始化适配器
        
        Args:
            platform_name: 平台名称
        """
        self.platform_name = platform_name
    
    @abstractmethod
    def parse_request(self, raw_input: Any) -> Dict[str, Any]:
        """
        将特定平台的请求格式转化为 Core 能理解的标准格式
        
        Args:
            raw_input: 平台原始请求
        
        Returns:
            标准化的请求字典 {
                "task_description": str,
                "task_type": Optional[str],
                "metadata": Dict
            }
        """
        pass
    
    @abstractmethod
    def format_response(self, core_output: Dict[str, Any]) -> Any:
        """
        将 Core 返回的结果转化为特定平台需要的格式
        
        Args:
            core_output: Core 返回的结果
        
        Returns:
            平台特定的响应格式
        """
        pass
    
    @abstractmethod
    def format_error(self, error: Exception) -> Any:
        """
        格式化错误响应
        
        Args:
            error: 异常对象
        
        Returns:
            平台特定的错误格式
        """
        pass
    
    def get_platform_name(self) -> str:
        """获取平台名称"""
        return self.platform_name


class BaseAPIServerAdapter(BasePlatformAdapter):
    """API 服务器适配器基类"""
    
    @abstractmethod
    def parse_chat_request(self, request_data: Dict) -> Dict[str, Any]:
        """
        解析聊天完成请求
        
        Args:
            request_data: API 请求体
        
        Returns:
            标准请求格式
        """
        pass
    
    @abstractmethod
    def format_chat_response(self, model: str, content: str, 
                            metadata: Optional[Dict] = None) -> Dict:
        """
        格式化聊天响应
        
        Args:
            model: 模型 ID
            content: 响应内容
            metadata: 元数据
        
        Returns:
            OpenAI 兼容的响应格式
        """
        pass
    
    @abstractmethod
    def format_stream_chunk(self, model: str, content: str, 
                           chunk_index: int = 0) -> str:
        """
        格式化流式响应块
        
        Args:
            model: 模型 ID
            content: 内容块
            chunk_index: 块索引
        
        Returns:
            SSE 格式的数据块
        """
        pass


class BaseCLIAdapter(BasePlatformAdapter):
    """命令行适配器基类"""
    
    @abstractmethod
    def parse_cli_args(self, args: list) -> Dict[str, Any]:
        """
        解析命令行参数
        
        Args:
            args: 命令行参数列表
        
        Returns:
            标准请求格式
        """
        pass
    
    @abstractmethod
    def format_cli_output(self, model: str, reason: str, 
                          verbose: bool = False) -> str:
        """
        格式化命令行输出
        
        Args:
            model: 选择的模型
            reason: 选择原因
            verbose: 是否详细输出
        
        Returns:
            命令行输出字符串
        """
        pass


# ============ 工具函数 ============

def validate_model_id(model_id: str, valid_models: list) -> bool:
    """
    验证模型 ID 是否有效
    
    Args:
        model_id: 模型 ID
        valid_models: 有效模型列表
    
    Returns:
        是否有效
    """
    return model_id in valid_models


def extract_messages(request_data: Dict) -> list:
    """
    从请求中提取消息列表
    
    Args:
        request_data: 请求数据
    
    Returns:
        消息列表
    """
    if isinstance(request_data, dict):
        return request_data.get("messages", [])
    return []


def build_task_from_messages(messages: list) -> str:
    """
    从消息列表构建任务描述
    
    Args:
        messages: 消息列表
    
    Returns:
        任务描述字符串
    """
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        parts.append(f"[{role}]: {content}")
    return "\n".join(parts)


def create_error_response(message: str, code: str = "internal_error") -> Dict:
    """
    创建标准错误响应
    
    Args:
        message: 错误消息
        code: 错误代码
    
    Returns:
        错误响应字典
    """
    return {
        "error": {
            "message": message,
            "type": "invalid_request_error",
            "code": code
        }
    }


def create_success_response(model: str, content: str, 
                           metadata: Optional[Dict] = None) -> Dict:
    """
    创建成功响应
    
    Args:
        model: 模型 ID
        content: 响应内容
        metadata: 元数据
    
    Returns:
        成功响应字典
    """
    import time
    
    response = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "finish_reason": "stop"
        }]
    }
    
    if metadata:
        response["metadata"] = metadata
    
    return response
