#!/usr/bin/env python3
"""
OpenCode Platform Adapter - OpenCode 平台适配器

V3.0.0 - 通用架构

负责解析 OpenCode 终端指令，转换为 Core 能理解的标准格式。
"""

import sys
import json
import logging
from typing import Dict, Any, Optional

from base_adapter import BaseCLIAdapter, build_task_from_messages, create_error_response

logger = logging.getLogger("adapter_opencode")


class OpenCodeAdapter(BaseCLIAdapter):
    """OpenCode 命令行适配器"""
    
    def __init__(self):
        super().__init__("opencode")
    
    def parse_request(self, raw_input: Any) -> Dict[str, Any]:
        """
        解析 OpenCode 请求
        
        OpenCode 支持的输入格式：
        - 直接任务描述: "帮我写一个排序算法"
        - JSON 格式: {"task": "...", "model": "auto"}
        - 消息列表: [{"role": "user", "content": "..."}]
        
        Args:
            raw_input: 原始输入
        
        Returns:
            标准请求格式
        """
        if isinstance(raw_input, str):
            # 字符串输入 - 直接作为任务描述
            return {
                "task_description": raw_input,
                "metadata": {"source": "cli_string"}
            }
        
        elif isinstance(raw_input, dict):
            # 字典输入
            if "task" in raw_input:
                return {
                    "task_description": raw_input.get("task", ""),
                    "model": raw_input.get("model", "auto"),
                    "metadata": {"source": "cli_dict"}
                }
            elif "messages" in raw_input:
                task_desc = build_task_from_messages(raw_input.get("messages", []))
                return {
                    "task_description": task_desc,
                    "model": raw_input.get("model", "auto"),
                    "metadata": {"source": "cli_messages"}
                }
        
        # 默认返回
        return {
            "task_description": str(raw_input),
            "metadata": {"source": "unknown"}
        }
    
    def format_response(self, core_output: Dict[str, Any]) -> Any:
        """
        格式化响应
        
        Args:
            core_output: Core 返回的结果
        
        Returns:
            格式化后的响应
        """
        # OpenCode 只需要模型 ID 和原因
        return {
            "model": core_output.get("model_id"),
            "reason": core_output.get("reason"),
            "success": True
        }
    
    def format_error(self, error: Exception) -> Any:
        """
        格式化错误
        
        Args:
            error: 异常对象
        
        Returns:
            错误响应
        """
        return {
            "model": "minimax-2.5-free",  # 错误时使用默认模型
            "reason": f"选择失败: {str(error)}",
            "success": False,
            "error": str(error)
        }
    
    def parse_cli_args(self, args: list) -> Dict[str, Any]:
        """
        解析命令行参数
        
        Args:
            args: 命令行参数列表
        
        Returns:
            标准请求格式
        """
        if not args:
            return {"task_description": "", "metadata": {}}
        
        # 解析参数
        task_parts = []
        model = "auto"
        
        i = 0
        while i < len(args):
            arg = args[i]
            if arg in ["-m", "--model"]:
                if i + 1 < len(args):
                    model = args[i + 1]
                    i += 2
                    continue
            elif arg in ["-j", "--json"]:
                # JSON 输出模式，在 format_cli_output 中处理
                pass
            elif arg.startswith("-"):
                # 跳过其他参数
                i += 1
                continue
            task_parts.append(arg)
            i += 1
        
        task_description = " ".join(task_parts)
        
        return {
            "task_description": task_description,
            "model": model,
            "metadata": {"source": "cli_args"}
        }
    
    def format_cli_output(self, model: str, reason: str, 
                         verbose: bool = False) -> str:
        """
        格式化命令行输出
        
        Args:
            model: 选择的模型
            reason: 选择原因
            verbose: 是否详细输出
        
        Returns:
            命令行输出
        """
        if verbose:
            return f"模型: {model}\n原因: {reason}"
        return model
    
    def format_json_output(self, model: str, reason: str, 
                          metadata: Optional[Dict] = None) -> str:
        """
        格式化 JSON 输出
        
        Args:
            model: 选择的模型
            reason: 选择原因
            metadata: 元数据
        
        Returns:
            JSON 字符串
        """
        output = {
            "model": model,
            "reason": reason,
            "platform": self.platform_name
        }
        
        if metadata:
            output["metadata"] = metadata
        
        return json.dumps(output, ensure_ascii=False, indent=2)


# ============ 主函数 ============

def main():
    """测试入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenCode Adapter Test")
    parser.add_argument("task", nargs="?", help="任务描述")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    # 导入核心模块
    sys.path.insert(0, "/Users/leiyuanwu/GitHub/opencode-smart-model-selector")
    from selector_core import SelectorCore
    
    # 初始化
    adapter = OpenCodeAdapter()
    core = SelectorCore()
    
    if args.task:
        # 解析请求
        request = adapter.parse_request(args.task)
        
        # 选择模型
        model_id, reason = core.select(request["task_description"])
        
        # 输出结果
        if args.json:
            print(adapter.format_json_output(model_id, reason))
        else:
            print(adapter.format_cli_output(model_id, reason, args.verbose))
    else:
        # 列出所有模型
        models = core.get_models()
        print(json.dumps(models, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
