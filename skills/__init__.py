#!/usr/bin/env python3
"""
Skills - 模型技能插件系统
=========================
实现"热插拔"：新增模型只需添加新的 skill，无需修改核心逻辑。

使用方式:
    from skills import auto_register_skills, SkillRegistry
    
    auto_register_skills()  # 自动注册所有技能
    skills = SkillRegistry.get_all()  # 获取所有技能
"""

from skills.base import SkillRegistry, BaseModelSkill, auto_register_skills

__all__ = ["SkillRegistry", "BaseModelSkill", "auto_register_skills"]
