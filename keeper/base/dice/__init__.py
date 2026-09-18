# -*- coding: utf-8 -*-
"""通用掷骰与检定包。

- ``roll`` / ``roll_d100`` / ``roll_dice``：与规则无关的骰子函数。
- ``Difficulty`` / ``CheckResult`` / ``CheckLevel``：检定结果类型。
- ``resolve_check``：COC7 检定裁决。
"""
from keeper.base.dice.model import CheckLevel, CheckResult, Difficulty
from keeper.base.dice.roll import roll, roll_d100, roll_dice
from keeper.base.dice.check import resolve_check

__all__ = [
    "CheckLevel",
    "CheckResult",
    "Difficulty",
    "resolve_check",
    "roll",
    "roll_d100",
    "roll_dice",
]
