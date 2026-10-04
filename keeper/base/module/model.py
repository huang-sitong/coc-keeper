from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

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

class PossibleCombat(BaseModel):
    when: str = ""
    npc: list[str] = Field(default_factory=list)
    result: str = "" # 包涵成功和失败的结果

class KeyItem(BaseModel):
    name: str = ""
    description: str = ""

class Chapter(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    title: str = ""
    location: str = ""
    overview: str = ""

    keeper_info: str = Field(default = "", alias="keeperInfo") # 在本章节中给keeper的信息，玩家不需要知道
    appear_npc: list[str] = Field(default_factory=list, alias="appearNPC")

    possible_dialogue: list[PossibleDialogue] = Field(default_factory=list, alias="possibleDialogue") # 通过对话就能获取的信息，回答不能包含秘密
    possible_check: list[PossibleCheck] = Field(default_factory=list, alias="possibleCheck") # 包括属性和技能检定
    possible_combat: list[PossibleCombat] = Field(default_factory=list, alias="possibleCombat")
    key_item: list[KeyItem] = Field(default_factory=list, alias="keyItem")

    content: list[Content] = Field(default_factory=list) # 文本内容入口，存储模组文本

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
    success: int = 100 # 成功率默认为100