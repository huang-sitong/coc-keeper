# -*- coding: utf-8 -*-
"""COC7 基本生物类：BaseCreature"""
import math
import random
import re
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from .model import (
    Attributes,
    DeriveAttributes,
    BattleAttributes,
    Skill,
    Weapon,
    Magic
)

class BaseCreature(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )

    name: str = "null"

    # ---- 属性 ----
    attributes: Attributes = Field(default_factory=Attributes)
    derive_attributes: DeriveAttributes = Field(
        default_factory=DeriveAttributes,
        alias="deriveAttributes",
    )
    battle_attributes: BattleAttributes = Field(
        default_factory=BattleAttributes,
        alias="battleAttributes",
    )

    # ----技能----
    skills: list[Skill] = Field(default_factory=list)

    # ----武器----
    weapons: list[Weapon] = Field(default_factory=list)

    # ----魔法----
    magic: list[Magic] = Field(default_factory=list)

    # name -> index
    _skill_index: dict[str, int] = PrivateAttr(default_factory=dict)
    _weapon_index: dict[str, int] = PrivateAttr(default_factory=dict)


    # ----索引相关func----

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        self.update_skill_index()
        self.update_weapon_index()

    # ---------------- 索引维护 ----------------

    def update_skill_index(self) -> None:
        """全量重建技能索引。直接改动 skills 列表后需手动调用。"""
        idx: dict[str, int] = {}
        for i, skill in enumerate(self.skills):
            if skill.name in idx:
                raise ValueError(f"技能名重复: {skill.name!r}")
            idx[skill.name] = i
        self._skill_index = idx

    def update_weapon_index(self) -> None:
        """全量重建武器索引。直接改动 weapons 列表后需手动调用。"""
        idx: dict[str, int] = {}
        for i, w in enumerate(self.weapons):
            if w.name in idx:
                raise ValueError(f"武器名重复: {w.name!r}")
            idx[w.name] = i
        self._weapon_index = idx

    # ---------------- 技能读写 ----------------

    def get_skill(self, name: str) -> Skill | None:
        """按名称取技能，不存在返回 None。"""
        i = self._skill_index.get(name)
        if i is None:
            return None
        return self.skills[i]

    def set_skill(self, skill: Skill) -> None:
        """
        写入一个技能：
          - 同名已存在 → 原地替换（保持位置不变）；
          - 不存在 → 追加到末尾。
        """
        i = self._skill_index.get(skill.name)
        if i is None:
            self.skills.append(skill)
        else:
            self.skills[i] = skill
        self.update_skill_index()

    # ---------------- 武器读写 ----------------

    def get_weapon(self, name: str) -> Weapon | None:
        """按名称取武器，不存在返回 None。"""
        i = self._weapon_index.get(name)
        if i is None:
            return None
        return self.weapons[i]

    def set_weapon(self, weapon: Weapon) -> None:
        """
        写入一把武器：
          - 同名已存在 → 原地替换（保持位置不变）；
          - 不存在 → 追加到末尾。
        """
        i = self._weapon_index.get(weapon.name)
        if i is None:
            self.weapons.append(weapon)
        else:
            self.weapons[i] = weapon
        self.update_weapon_index()

    
