# -*- coding: utf-8 -*-
"""通用掷骰函数：d100 与骰式解析。"""
import random
import re


def roll_dn(max_value: int = 100, cheat: int = 0) -> int:
    if cheat > 0:
        return cheat
    if max_value < 1:
        raise ValueError("max_value must be >= 1")
    return random.randint(1, max_value)


def roll_ndice(expr: str, cheat: int = 0) -> int:
    # 作弊：直接返回指定值
    if cheat > 0:
        return cheat

    # 去掉空格并统一大写，支持 6d10、6D10、D20 等写法
    s = expr.replace(" ", "").upper()
    if not s:
        raise ValueError("骰子表达式不能为空")

    # 合法项：可选正负号 + nDm 或 常数
    token_re = re.compile(r'[+-]?(?:\d*D\d+|\d+)')
    tokens = token_re.findall(s)

    # 如果拼接后和原表达式不一致，说明有非法字符
    if ''.join(tokens) != s:
        raise ValueError(f"非法骰子表达式: {expr}")

    total = 0

    for token in tokens:
        sign = 1

        if token.startswith('+'):
            token = token[1:]
        elif token.startswith('-'):
            sign = -1
            token = token[1:]

        if 'D' in token:
            n_str, m_str = token.split('D', 1)
            n = int(n_str) if n_str else 1
            m = int(m_str)

            if n <= 0 or m <= 0:
                raise ValueError(f"骰子数量和面数必须为正数: {token}")

            total += sign * sum(random.randint(1, m) for _ in range(n))
        else:
            total += sign * int(token)

    return total
