from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

class Content(BaseModel):
    title: str = ""
    text: str = ""

class PossibleDialogue(BaseModel):
    sentence: str = ""
    answer: str = ""

class PossibleCheck(BaseModel):
    when: str = ""
    check: str = ""
    result: str = "" # 包涵成功和失败的结果

class Chapter(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    title: str = ""
    location: str = ""
    overview: str = ""
    appear_npc: str = Field(default = "", alias="keeperInfo")

    possible_dialogue: list[PossibleDialogue] = Field(default_factory=PossibleDialogue, alias="possibleDialogue")
    possible_check: list[PossibleCheck] = Field(default_factory=PossibleCheck, alias="possibleCheck")

    raw: str = ""

class Ending(BaseModel):
    condition: str = "" # 触发条件
    text: str = ""

class Position(Enum):
    """NPC的立场: 友好/中立/敌对"""
    FRIENDLY = 0
    NEUTRAL = 1
    HOSTILE = 2


class CombatSkill(BaseModel):
    """战技"""

    name: str = ""
    skill: str = "" # 相关联的技能，默认为无，直接根据成功率做判断
    range: str = "" # 作用范围，默认为接触
    round: str = "1" # 每回合使用次数，默认为1/回合
    description: str = ""
    success: str = "100" # 成功率默认为100