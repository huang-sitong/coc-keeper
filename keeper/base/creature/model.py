# -*- coding: utf-8 -*-
"""敌人/怪物接口层使用的结构化结果类型。"""
from __future__ import annotations

from keeper.base.module_base import ModuleBaseModel

class SanityLossResult(ModuleBaseModel):
    """一次理智损失掷骰的结果。"""

    expression: str = ""
    success: bool = False
    loss: int = 0


class ArmorRollResult(ModuleBaseModel):
    """一次护甲减伤掷骰的结果。"""

    expression: str = ""
    value: int = 0


__all__ = ["ArmorRollResult", "SanityLossResult"]
