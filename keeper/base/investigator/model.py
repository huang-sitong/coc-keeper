# -*- coding: utf-8 -*-
"""COC7 调查员数据模型：纯数据类。"""
from enum import Enum, IntEnum
from typing import Literal, Optional

from pydantic import BaseModel, Field

CheckLevel = Literal["critical", "extreme", "hard", "success", "fail", "fumble"]

class Difficulty(IntEnum):
    """检定难度。"""

    NORMAL = 0
    HARD = 1
    EXTREME = 2

class CheckResult(BaseModel):
    """一次 d100 检定的结果。"""

    roll: int
    target: int
    success: bool
    level: CheckLevel

class AttackResult(BaseModel):
    """攻击命中后的结算结果。"""

    weapon_id: str
    weapon_name: str
    damage: str
    attacks: str
    range: str
    ammo_left: int | str
    jammed: bool

class AttackBySkillResult(BaseModel):
    """完整攻击流程结果：检定 + 结算 + 伤害掷骰。"""

    skill_id: str
    skill_name: str
    weapon_id: Optional[str] = None
    check: CheckResult
    attack: Optional[AttackResult] = None
    hit: bool
    damage_roll: Optional[int] = None

class DamageResult(BaseModel):
    """受到伤害结算结果。"""

    amount: int
    current: int
    major_wound: bool
    con_check: Optional[CheckResult] = None
    unconscious: bool
    dying: bool
    dead: bool

class SkillGroup(str, Enum):
    """技能所属类目（与 JSON skillGroups 键一一对应）。"""

    SPECIAL = "special"
    EXPLORE = "explore"
    SOCIAL = "social"
    COMBAT = "combat"
    MEDICAL = "medical"
    MOVE = "move"
    KNOWLEDGE = "knowledge"
    TECH = "tech"
    DRIVE = "drive"
    OTHER = "other"

class AttributeName(str, Enum):
    """八项基础属性 + 幸运（字符串值与 JSON attributes 键一致）。"""

    STR = "str"
    DEX = "dex"
    CON = "con"
    APP = "app"
    POW = "pow"
    SIZ = "siz"
    EDU = "edu"
    INT = "int"
    LUC = "luc"

class Sanity(BaseModel):
    """理智值。"""

    current: int = 0
    start: int = 0
    max: int = 99

class HitPoints(BaseModel):
    """生命值。"""

    current: int = 0
    max: int = 0

class MagicPoints(BaseModel):
    """魔法值。"""

    current: int = 0
    max: int = 0

class DeriveAttributes(BaseModel):
    """派生属性：理智 / 生命 / 魔法。"""

    sanity: Sanity = Field(default_factory=Sanity)
    hp: HitPoints = Field(default_factory=HitPoints)
    mp: MagicPoints = Field(default_factory=MagicPoints)

class BattleAttributes(BaseModel):
    """战斗属性。"""

    db: str = "0"
    build: int = 0
    mov: int = 8
    mov_note: str = ""
    armor: str = "0"

class BodyStates(BaseModel):
    """身体状态。"""

    injured: bool = False
    dead: bool = False
    unconscious: bool = False

class MentalStates(BaseModel):
    """精神状态。"""

    permanently_insane: bool = False
    temporarily_insane: bool = False
    indefinitely_insane: bool = False

class Weapon(BaseModel):
    """武器条目。"""

    id: str
    name: str
    skill: str = ""
    skill_id: str = ""
    damage: str = ""
    range: str = ""
    tho: str = "1"
    round: str = ""
    num: str = ""
    err: str = ""
    weight: str = ""
    note: str = ""
    success: str = ""

class Stories(BaseModel):
    """个人故事与描述。"""

    app: str = ""
    belief: str = ""
    i_person: str = ""
    i_place: str = ""
    i_item: str = ""
    trait: str = ""
    scar: str = ""
    mad: str = ""
    desc: str = ""

class Assets(BaseModel):
    """资产与随身物品。"""

    cash: str = "0"
    consumption: str = "0"
    assets: str = ""
    items: str = ""
    magic_items: str = ""
    magics: str = ""
    touches: str = ""

class ExperiencedModule(BaseModel):
    """经历过的模组。"""

    name: str = ""
    experience: str = ""

class Friend(BaseModel):
    """盟友/好友。"""

    character: str = ""
    relationship: str = ""
    player: str = ""
