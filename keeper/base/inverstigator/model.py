from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

class BodyStates(BaseModel):
    """身体状态。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    injured: bool = Field(default=False, alias="重伤")
    dead: bool = Field(default=False, alias="死亡")
    unconscious: bool = Field(default=False, alias="昏迷")

class MentalStates(BaseModel):
    """精神状态。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    permanently_insane: bool = Field(default=False, alias="永久疯狂")
    temporarily_insane: bool = Field(default=False, alias="临时疯狂")
    irregular_insane: bool = Field(default=False, alias="不定期疯狂")

class CharacterStatus(BaseModel):
    """角色状态。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    body_states: BodyStates = Field(default_factory=BodyStates, alias="bodyStates")
    mental_states: MentalStates = Field(default_factory=MentalStates, alias="mentalStates")

    
class Stories(BaseModel):
    """个人故事与描述。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    app: str = ""
    belief: str = ""
    i_person: str = Field(default="", alias="IPerson")
    i_place: str = Field(default="", alias="IPlace")
    i_item: str = Field(default="", alias="IItem")
    trait: str = ""
    scar: str = ""
    mad: str = ""
    desc: str = ""

class Assets(BaseModel):
    """资产与随身物品。"""
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)
    cash: str = "0"
    consumption: str = "0"
    assets: str = ""
    items: str = ""
    magic_items: str = Field(default="", alias="magicItems")
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
