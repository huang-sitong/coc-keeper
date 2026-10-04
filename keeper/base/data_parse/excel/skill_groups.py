# -*- coding: utf-8 -*-
"""技能名 → ``SkillGroups`` 分组的映射。

``SkillGroups`` 固定十个分组（special / explore / social / combat / medical /
move / knowledge / tech / drive / other），而车卡里的技能名既有标准名
（`侦查`、`格斗：斗殴`），也有带占位序号的自由名（`技艺①`、`科学①物理学`），
所以这里先做一次归一化（去空白、`Ω`、全/半角冒号），再查精确表，
查不到时按前缀规则兜底，最后落到 ``other``。

映射规则是本项目的约定，可按团的口径直接修改这两张表。
"""
from __future__ import annotations

import re

__all__ = ["SKILL_GROUP_BY_NAME", "SKILL_GROUP_PREFIX_RULES", "skill_group"]

# 归一化后的技能名 -> 分组
SKILL_GROUP_BY_NAME: dict[str, str] = {
    # 社交 / 识人
    "话术": "social",
    "说服": "social",
    "取悦": "social",
    "恐吓": "social",
    "乔装": "social",
    "信用评级": "social",
    "心理学": "social",
    "魅惑": "social",
    "欺骗": "social",
    "引诱": "social",
    # 探索 / 侦查
    "侦查": "explore",
    "聆听": "explore",
    "追踪": "explore",
    "读唇": "explore",
    "导航": "explore",
    "图书馆使用": "explore",
    "生存": "explore",
    "潜行": "explore",
    "妙手": "explore",
    "锁匠": "explore",
    "撬锁": "explore",
    "开锁": "explore",
    "察觉": "explore",
    "方位": "explore",
    "动物驯养": "explore",
    # 格斗（无前缀的散项）
    "闪避": "combat",
    "投掷": "combat",
    "炮术": "combat",
    # 医疗 / 心理
    "急救": "medical",
    "医学": "medical",
    "精神分析": "medical",
    "催眠": "medical",
    # 移动
    "攀爬": "move",
    "游泳": "move",
    "跳跃": "move",
    "潜水": "move",
    # 知识
    "历史": "knowledge",
    "考古学": "knowledge",
    "人类学": "knowledge",
    "博物学": "knowledge",
    "自然学": "knowledge",
    "神秘学": "knowledge",
    "母语": "knowledge",
    "学识": "knowledge",
    "克苏鲁神话": "knowledge",
    "法律": "knowledge",
    "政治": "knowledge",
    "商业": "knowledge",
    "地域": "knowledge",
    "会计": "knowledge",
    "估价": "knowledge",
    # 科技
    "计算机使用": "tech",
    "电气维修": "tech",
    "电子学": "tech",
    "机械维修": "tech",
    "操作重型机械": "tech",
    "爆破": "tech",
    "密码学": "tech",
    # 驾驶
    "汽车驾驶": "drive",
    "驾驶": "drive",
    "舟艇驾驶": "drive",
    "飞机驾驶": "drive",
    "骑术": "drive",
    # 特长 / 自定义
    "技艺": "special",
    "自定义技能": "special",
    "任意特长": "special",
}

# 前缀规则（按顺序匹配，命中即返回），用于 `格斗①链枷`、`科学①物理学` 这类名字
SKILL_GROUP_PREFIX_RULES: tuple[tuple[str, str], ...] = (
    ("格斗", "combat"),
    ("射击", "combat"),
    ("技艺", "special"),
    ("外语", "knowledge"),
    ("科学", "knowledge"),
    ("学识", "knowledge"),
    ("驾驶", "drive"),
)

_WHITESPACE_RE = re.compile(r"\s+")
_STRIP_CHARS = "ΩΩΩ：:：、,，.。()（）[]【】"


def _normalize(name: str) -> str:
    """归一化技能名：去掉空白、Ω 标记与各种括号/冒号。"""
    text = _WHITESPACE_RE.sub("", str(name or ""))
    return text.strip(_STRIP_CHARS)


def skill_group(name: str) -> str:
    """返回技能应归属的 ``SkillGroups`` 分组名（未知技能归入 other）。"""
    key = _normalize(name)
    group = SKILL_GROUP_BY_NAME.get(key)
    if group is not None:
        return group
    for prefix, group in SKILL_GROUP_PREFIX_RULES:
        if key.startswith(prefix):
            return group
    return "other"
