# -*- coding: utf-8 -*-
"""通用掷骰函数：d100 与骰式解析。"""
import random
import re


def roll(max_value: int = 100, cheat: int = 0) -> int:
    """掷一颗 ``max_value`` 面骰，返回 1 到 ``max_value``（含）的整数。

    ``cheat`` 大于 0 时直接返回该值，便于测试或指定结果。
    """
    if cheat > 0:
        return cheat
    if max_value < 1:
        raise ValueError("max_value must be >= 1")
    return random.randint(1, max_value)


def roll_ndm(expr: str, cheat: int = 0) -> int:
    """解析并计算 ``nDm`` 骰式，例如 ``6D10 + 1D4``、``3D6+4``。

    支持大小写、省略骰子数量（``D6`` 等价于 ``1D6``）以及正负常数项。
    ``cheat`` 大于 0 时直接返回该值，不进行随机掷骰。
    """
    if cheat > 0:
        return cheat

    normalized = re.sub(r"\s+", "", expr)
    normalized = normalized.replace("+-", "-")
    if not normalized:
        return 0

    total = 0
    for term in re.split(r"(?=[+-])", normalized):
        if not term:
            continue

        sign = -1 if term.startswith("-") else 1
        body = term.lstrip("+-")

        match = re.fullmatch(r"(\d*)d(\d+)", body, flags=re.IGNORECASE)
        if match:
            times = int(match.group(1)) if match.group(1) else 1
            sides = int(match.group(2))
            total += sign * sum(roll(sides) for _ in range(times))
        else:
            total += sign * (int(body) if body else 0)

    return total
