# -*- coding: utf-8 -*-
"""COC7 检定与掷骰函数。"""
import math
import random
import re
from typing import Callable

from keeper.base.investigator.model import CheckLevel, CheckResult, Difficulty

def roll(max_value: int = 100, rng: Callable[[], float] = random.random) -> int:
    """掷一颗 ``max_value`` 面骰，返回 1 到 ``max_value``（含）的整数。

    默认为 d100，因此 ``roll()`` 等价于掷 d100。
    """
    if max_value < 1:
        raise ValueError("max_value must be >= 1")
    return math.floor(rng() * max_value) + 1

def roll_d100(rng: Callable[[], float] = random.random) -> int:
    """掷 d100，返回 1-100。"""
    return roll(100, rng)

def roll_dice(expr: str, db: str = "0", rng: Callable[[], float] = random.random) -> int:
    """解析掷骰表达式（``2D6+1``、``1D3+DB``）。

    ``DB`` 会先替换为角色伤害加值，再按常规骰子表达式计算。
    """
    normalized = re.sub(r"DB", db or "0", expr, flags=re.IGNORECASE)
    normalized = normalized.replace("+-", "-")
    total = 0
    for term in re.split(r"(?=[+-])", normalized):
        if not term:
            continue
        sign = -1 if term.startswith("-") else 1
        t = term.lstrip("+-")
        m = re.fullmatch(r"(\d*)d(\d+)", t, flags=re.IGNORECASE)
        if m:
            times = int(m.group(1)) if m.group(1) else 1
            die = int(m.group(2))
            s = sum(roll(die, rng) for _ in range(times))
            total += sign * s
        else:
            total += sign * (int(t) if t else 0)
    return total

def resolve_check(
    roll: int,
    value: int,
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
