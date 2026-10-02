import math
import random
import re
from typing import Callable, Optional

from pydantic import BaseModel, Field, PrivateAttr

from keeper.base.coc_world.base_creature import BaseCreature
from model import Position, CombatSkill

class NPC(BaseCreature):

    position: int = Position.NEUTRAL

    combat_skill: list[CombatSkill] = Field(default_factory=list)