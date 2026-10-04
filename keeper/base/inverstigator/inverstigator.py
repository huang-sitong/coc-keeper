import math
import random
import re
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from keeper.base.coc_world.base_creature import BaseCreature
from .model import (
    CharacterStatus,
    Stories,
    Assets,
    ExperiencedModule,
    Friend,
    Touch
)

class Investigator(BaseCreature):

    player_name: str = Field(default="", alias="playerName") # 姓名/昵称，与游戏中的角色无关
    time: str = ""
    job: str = ""
    age: str = ""
    gender: str = ""
    location: str = ""
    hometown: str = ""
    era: str = ""

    character_status: CharacterStatus = Field(default_factory=CharacterStatus, alias="characterStatus")
    stories: Stories = Field(default_factory=Stories)
    assets: Assets = Field(default_factory=Assets)
    experienced_modules: list[ExperiencedModule] = Field(default_factory=list, alias="experiencedModules")
    friends: list[Friend] = Field(default_factory=list)
    touchs: list[Touch] = Field(default_factory=list)
