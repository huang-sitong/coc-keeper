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
    Weapon
)

class BaseCreature(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        serialize_by_alias=True,
    )

    describe: str = ""

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
    # TODO 为武器创建索引
    weapons: list[Weapon] = Field(default_factory=list)

    
