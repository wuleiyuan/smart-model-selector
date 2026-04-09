#!/usr/bin/env python3
"""
P0 输出避让协议 - Smart Model Selector
======================================

当输出超过 4KB 时，强制执行分流协议：
- 将完整内容保存至 /tmp/smart_selector_outputs/
- 仅在对话中回传"文件路径"和"内容摘要"

遵循 OpenClaw 工业级上下文管理协议 (P0/P1/P3)
"""

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 日志输出色彩
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'

class OutputProtocol:
    """
    P0 协议：大输出避让
    ====================
    
    触发条件：任何工具执行输出 > 4KB (约 2000 tokens)
    
    动作：
    1. 将完整输出保存至 /tmp/smart_selector_outputs/{task_id}_{timestamp}.log
    2. 仅返回"【内容摘要（< 50字）+ 绝对路径】"
    3. 严禁在回复中粘贴原始大段日志
    
    物理路径：/tmp/smart_selector_outputs/
    """

    THRESHOLD_BYTES = 4096  # 4KB 阈值
    OUTPUT_DIR = Path("/tmp/smart_selector_outputs")
    
    def __init__(self):
        self.output_dir = self.OUTPUT_DIR
        self._ensure_output_dir()

    def _ensure_output_dir(self):
        """确保输出目录存在"""
        if not self.output_dir.exists():
            self.output_dir.mkdir(parents=True, exist_ok=True)
            print(f"{Colors.BLUE}[P0] 输出目录已创建: {self.output_dir}{Colors.RESET}")

    def _generate_task_id(self, content: str) -> str:
        """生成唯一的任务 ID"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{timestamp}_{content_hash}"

    def _summarize(self, content: str, max_chars: int = 50) -> str:
        """生成内容摘要"""
        content = content.strip()
        if len(content) <= max_chars:
            return content
        
        lines = content.split('\n')
        first_line = lines[0] if lines else ""
        
        if len(first_line) <= max_chars:
            return first_line
        
        return content[:max_chars].rsplit(' ', 1)[0] + "..."

    def handle(self, content: str, task_type: str = "output") -> Dict[str, Any]:
        """
        P0 协议处理入口
        ================
        
        Args:
            content: 待处理的内容
            task_type: 任务类型标识
            
        Returns:
            {
                "evaded": bool,       # 是否执行了分流
                "summary": str,        # 内容摘要（用于对话展示）
                "save_path": str,      # 文件保存路径（如果执行了分流）
                "char_count": int,     # 原始字符数
                "is_truncated": bool  # 是否被截断
            }
        """
        char_count = len(content.encode('utf-8'))
        is_large = char_count > self.THRESHOLD_BYTES
        
        result = {
            "evaded": False,
            "summary": content,
            "save_path": None,
            "char_count": char_count,
            "is_truncated": False
        }
        
        if not is_large:
            return result
        
        # 🚨 触发 P0 协议
        task_id = self._generate_task_id(content)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{task_type}_{task_id}.log"
        save_path = self.output_dir / filename
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(f"# P0 Output Protocol\n")
                f.write(f"# Task ID: {task_id}\n")
                f.write(f"# Timestamp: {timestamp}\n")
                f.write(f"# Character Count: {char_count}\n")
                f.write(f"# Threshold: {self.THRESHOLD_BYTES} bytes\n")
                f.write(f"{'='*60}\n\n")
                f.write(content)
            
            summary = self._summarize(content)
            
            result["evaded"] = True
            result["summary"] = summary
            result["save_path"] = str(save_path)
            result["is_truncated"] = True
            
            print(f"{Colors.YELLOW}[P0] 大输出分流已触发!")
            print(f"     原始大小: {char_count} bytes ({char_count/1024:.1f} KB)")
            print(f"     保存路径: {save_path}")
            print(f"     内容摘要: {summary}{Colors.RESET}")
            
        except Exception as e:
            print(f"{Colors.RED}[P0 ERROR] 分流失败: {e}{Colors.RESET}")
        
        return result

    def format_p0_message(self, result: Dict[str, Any]) -> str:
        """
        格式化 P0 避让消息，用于在对话中展示
        ================================
        """
        if not result["evaded"]:
            return ""
        
        return (
            f"\n\n"
            f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}\n"
            f"{Colors.YELLOW}📁 [P0 Output Evasion] 内容过长，已自动分流\n\n"
            f"{Colors.BLUE}📊 统计信息:{Colors.RESET}\n"
            f"   • 原始大小: {result['char_count']} bytes ({result['char_count']/1024:.1f} KB)\n"
            f"   • 保存路径: `{result['save_path']}`\n\n"
            f"{Colors.BLUE}📝 内容摘要:{Colors.RESET}\n"
            f"   {result['summary']}\n"
            f"{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.RESET}\n"
            f"\n"
        )

    def get_file_content(self, save_path: str) -> Optional[str]:
        """
        根据保存路径读取已分流的内容
        ==============================
        """
        try:
            path = Path(save_path)
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content
        except Exception as e:
            print(f"{Colors.RED}[P0 ERROR] 读取失败: {e}{Colors.RESET}")
        return None

    def cleanup_old_files(self, days: int = 7):
        """
        清理超过指定天数的旧文件
        =========================
        """
        if not self.output_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (days * 86400)
        cleaned = 0
        
        for file in self.output_dir.glob("*.log"):
            if file.stat().st_mtime < cutoff_time:
                try:
                    file.unlink()
                    cleaned += 1
                except Exception:
                    pass
        
        if cleaned > 0:
            print(f"{Colors.BLUE}[P0 Cleanup] 已清理 {cleaned} 个过期文件{Colors.RESET}")


# ===== CLI 工具入口 =====
if __name__ == "__main__":
    import argparse
    import sys
    
    print(f"{Colors.CYAN}")
    print("=" * 50)
    print("🧠 Smart Model Selector - P0 Output Protocol")
    print("=" * 50)
    print(f"{Colors.RESET}")
    
    parser = argparse.ArgumentParser(
        description="P0 输出避让协议工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # handle 命令：处理大输出
    handle_parser = subparsers.add_parser("handle", help="执行 P0 分流处理")
    handle_parser.add_argument("content", help="待处理的内容")
    handle_parser.add_argument("--type", default="output", help="任务类型")
    
    # read 命令：读取已分流文件
    read_parser = subparsers.add_parser("read", help="读取分流文件")
    read_parser.add_argument("path", help="文件路径")
    
    # cleanup 命令：清理旧文件
    cleanup_parser = subparsers.add_parser("cleanup", help="清理过期文件")
    cleanup_parser.add_argument("--days", type=int, default=7, help="保留天数")
    
    args = parser.parse_args()
    
    protocol = OutputProtocol()
    
    if args.command == "handle":
        result = protocol.handle(args.content, args.type)
        message = protocol.format_p0_message(result)
        if message:
            print(message)
        else:
            print(f"{Colors.GREEN}[OK] 内容未超过阈值，无需分流{Colors.RESET}")
    
    elif args.command == "read":
        content = protocol.get_file_content(args.path)
        if content:
            print(content)
        else:
            print(f"{Colors.RED}[ERROR] 文件读取失败{Colors.RESET}")
            sys.exit(1)
    
    elif args.command == "cleanup":
        protocol.cleanup_old_files(args.days)
    
    else:
        parser.print_help()
