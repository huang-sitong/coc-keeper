# -*- coding: utf-8 -*-
"""COC7 检定裁决：根据骰值与难度计算成功等级。"""
import math

from keeper.base.dice.model import CheckLevel, CheckResult, Difficulty


def resolve_check(
    roll: int, # 骰子随机数
    value: int, # 成功率，在车卡时限制成功率上限
    difficulty: Difficulty = Difficulty.NORMAL,
) -> CheckResult:
    """COC7 检定裁决（技能/属性共用）。"""
    if difficulty == Difficulty.HARD:
        target = math.floor(value / 2)
    elif difficulty == Difficulty.EXTREME:
        target = math.floor(value / 5)
    else:
        target = value

    if roll == 100 or (roll >= 96 and value < 50):
        return CheckResult(roll=roll, target=target, success=False, level="fumble")
    if roll <= 5 and roll <= value:
        return CheckResult(roll=roll, target=target, success=True, level="critical")
    if roll <= target:
        if difficulty == Difficulty.EXTREME:
            level: CheckLevel = "extreme"
        elif difficulty == Difficulty.HARD:
            level = "hard"
        else:
            level = "success"
        return CheckResult(roll=roll, target=target, success=True, level=level)
    return CheckResult(roll=roll, target=target, success=False, level="fail")
