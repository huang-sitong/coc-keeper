import math
import random
import re
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from keeper.base.coc_world.base_creature import BaseCreature
from model import Position, CombatSkill

class NPC(BaseCreature):

    position: int = Position.NEUTRAL
    description: str = "" # NPC的基本信息，包含年龄、身份、个人描述，关系等信息
    keeper_info: str = Field(default = "", alias="keeperInfo") # 给keepr的信息，包含NPC的性格、特性、扮演要点等信息
    combat_skill: list[CombatSkill] = Field(default_factory=list, alias="combatSkill")