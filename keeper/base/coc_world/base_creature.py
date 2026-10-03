# -*- coding: utf-8 -*-
"""COC7 基本生物类：BaseCreature"""
import math
import random
import re
from typing import Callable, Optional

from pydantic import BaseModel, Field, PrivateAttr

from .model import (
    Attributes,
    DeriveAttributes,
    BattleAttributes,
    SkillGroups,
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
    skill_groups: SkillGroups = Field(
        default_factory=SkillGroups,
        alias="skillGroups"
    )

    # ----武器----
    weapons: list[Weapon] = Field(default_factory=list)

    # ----魔法----
    magic: list[Magic] = Field(default_factory=list)
    
    # name -> index
    _weapon_index: dict[str, int] = PrivateAttr(default_factory=dict)


    # ----武器相关func----

    def model_post_init(self, __context: Any) -> None:
        super().model_post_init(__context)
        self.update_index()

    # ---------------- 索引维护 ----------------

    def update_index(self) -> None:
        """全量重建武器索引。直接改动 weapons 列表后需手动调用。"""
        idx: dict[str, int] = {}
        for i, w in enumerate(self.weapons):
            if w.name in idx:
                raise ValueError(f"武器名重复: {w.name!r}")
            idx[w.name] = i
        self._weapon_index = idx

    # ---------------- 读写 ----------------

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
        self.update_index()

    
