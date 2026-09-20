from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

class Attributes(BaseModel):
    """八项基础属性与幸运。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    _str: int = Field(default=0, alias="str")
    _dex: int = Field(default=0, alias="dex")
    _con: int = Field(default=0, alias="con")
    _app: int = Field(default=0, alias="app")
    _pow: int = Field(default=0, alias="pow")
    _siz: int = Field(default=0, alias="siz")
    _edu: int = Field(default=0, alias="edu")
    _int: int = Field(default=0, alias="int")

    _luc: int = Field(default=0, alias="luc")

# DeriveAttributes

class Sanity(BaseModel):
    """理智值。"""

    current: int = 1
    max: int = 99

class HitPoints(BaseModel):
    """生命值。"""

    current: int = 1
    max: int = 1

class MagicPoints(BaseModel):
    """魔法值。"""

    current: int = 0
    max: int = 0

class DeriveAttributes(BaseModel):
    """派生属性：理智 / 生命 / 魔法。"""

    sanity: Sanity = Field(default_factory=Sanity)
    hp: HitPoints = Field(default_factory=HitPoints)
    mp: MagicPoints = Field(default_factory=MagicPoints)

# end

class BattleAttributes(BaseModel):
    """战斗属性。"""

    db: str = "0"
    build: int = 0
    mov: int = 8
    armor: str = "0"

# skills

class Skill(BaseModel):

    name: str = ""
    base: int = 0
    job: int = 0
    interest: int = 0
    growth: int = 0
    is_professional: bool = False

class SkillGroups(BaseModel):
    #TODO 为SkillGroups添加索引_index

    special: list[Skill] = Field(default_factory=list)
    explore: list[Skill] = Field(default_factory=list)
    social: list[Skill] = Field(default_factory=list)
    combat: list[Skill] = Field(default_factory=list)
    medical: list[Skill] = Field(default_factory=list)
    move: list[Skill] = Field(default_factory=list)
    knowledge: list[Skill] = Field(default_factory=list)
    tech: list[Skill] = Field(default_factory=list)
    drive: list[Skill] = Field(default_factory=list)
    other: list[Skill] = Field(default_factory=list)

# end

class Weapon(BaseModel):
    """武器条目"""

    name: str = ""
    skill: str = ""
    skill_id: str = ""
    damage: str = ""
    range: str = ""
    tho: str = "0"
    round: str = "1"
    num: str = ""
    err: str = ""
    weight: str = ""
    note: str = ""
    success: str = ""