from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

class BodyStates(BaseModel):
    """身体状态。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    injured: bool = Field(default=False)
    dead: bool = Field(default=False)
    unconscious: bool = Field(default=False)

class MentalStates(BaseModel):
    """精神状态。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    permanently_insane: bool = Field(default=False, alias="permanentlyInsane") # 永久疯狂
    temporarily_insane: bool = Field(default=False, alias="temporarilyInsane") # 临时疯狂
    irregular_insane: bool = Field(default=False, alias="irregularInsane") # 不定期疯狂

class CharacterStatus(BaseModel):
    """角色状态。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    body_states: BodyStates = Field(default_factory=BodyStates, alias="bodyStates")
    mental_states: MentalStates = Field(default_factory=MentalStates, alias="mentalStates")

    
class Stories(BaseModel):
    """个人故事与描述。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    app: str = "" # 形象描述
    belief: str = "" # 思想与信念
    i_person: str = Field(default="", alias="IPerson") # 重要之人
    i_place: str = Field(default="", alias="IPlace") # 重要之地
    i_item: str = Field(default="", alias="IItem") # 重要物品
    trait: str = "" # 特质
    scar: str = "" # 伤口与疤痕
    mad: str = "" # 精神状态
    desc: str = "" # 个人介绍

class Assets(BaseModel):
    """资产、随身物品与第三类接触。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    cash: str = "0" # 资产值
    consumption: str = "0" # 消费水平
    assets: str = "" # 描述拥有的资产
    items: str = "" # 随身物品

class ExperiencedModule(BaseModel):
    """经历过的模组/调查员经历"""

    module: str = ""
    describetion: str = ""

class Friend(BaseModel):
    """盟友/好友。"""

    name: str = ""
    relationship: str = ""

class Touch(BaseModel):
    """第三类接触"""
    describetion: str = ""
    result: str = ""