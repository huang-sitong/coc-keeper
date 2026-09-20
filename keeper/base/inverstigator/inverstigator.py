import math
import random
import re
from typing import Callable, Optional

from pydantic import BaseModel, Field, PrivateAttr

from keeper.base.coc_world.base_creature import BaseCreature
from .model import (
    CharacterStatus,
    Stories,
    Assets,
    ExperiencedModule,
    Friend
)

class Investigator(BaseCreature):

    player_name: str = ""
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
