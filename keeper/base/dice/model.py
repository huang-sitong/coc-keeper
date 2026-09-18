# -*- coding: utf-8 -*-
"""通用检定结果类型：骰值、目标值与成功等级。"""
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel

CheckLevel = Literal["critical", "extreme", "hard", "success", "fail", "fumble"]


class Difficulty(IntEnum):
    """检定难度：普通 / 困难（1/2） / 极难（1/5）。"""

    NORMAL = 0
    HARD = 1
    EXTREME = 2


class CheckResult(BaseModel):
    """一次 d100 检定的结果。"""

    roll: int
    target: int
    success: bool
    level: CheckLevel
