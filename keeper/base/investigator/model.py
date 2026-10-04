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
    """资产与随身物品：人物卡「资产」表。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    cash: str = "0" # 资产值：当前现金 + 单位
    consumption: str = "0" # 消费水平
    assets: str = "" # 资产描述：「其他资产」下方的自由详述格
    items: str = "" # 随身物品：多件以 ; 分隔

class ExperiencedModule(BaseModel):
    """经历过的模组/调查员经历"""

    module: str = ""
    describetion: str = ""

class Friend(BaseModel):
    """调查员伙伴：人物卡「调查员伙伴」表的一行。

    表头：姓名 / 玩家 / 注释 / 造成改变 / 相遇模组。
    """

    name: str = "" # 姓名：伙伴（NPC/PC）在游戏中的名字
    player: str = "" # 玩家：谁扮演这位伙伴
    note: str = "" # 注释：对关系的一句话描述
    change: str = "" # 造成改变：这段关系对调查员造成的变化
    module: str = "" # 相遇模组：在哪里认识的

class Touch(BaseModel):
    """第三类接触：人物卡「第三类接触（古籍、咒文、神话知识等）」表的一行。

    表头：遇到了 / 获得的结果 / 备注 / 累计。
    """

    describetion: str = "" # 遇到了：接触到的存在/古籍/咒文
    result: str = "" # 获得的结果：技能/理智等变化
    note: str = "" # 备注
    total: int = 0 # 累计：该次接触累计消耗的 SAN