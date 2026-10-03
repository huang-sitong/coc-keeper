import math
import random
import re
from typing import Callable, Optional

from pydantic import BaseModel, Field, PrivateAttr

from keeper.base.coc_world.base_creature import BaseCreature
from npc import NPC
from model import(
    Content,
    Chapter,
    Ending
)

class Module(BaseModel):
    model_config = ConfigDict(
            populate_by_name=True,
            serialize_by_alias=True,
        )

    title: str = ""
    location: str = ""
    keeper_info: list[Content] = Field(default_factory=list, alias="keeperInfo") # 给keepr的信息/秘密，不需要玩家知道
    information: list[Content] = Field(default_factory=list) # 玩家可以从游玩过程中获取的信息
    backgroud: list[Content] = Field(default_factory=list) # 可以向玩家公布的世界观背景
    summary: str = ""

    opening: str = "" # 开场白，将玩家引入到世界观中，但是注意不要暴露秘密
    chapter: list[Chapter] = Field(default_factory=list)
    ending: list[Ending] = Field(default_factory=list)

    npc: list[NPC] = Field(default_factory=NPC)