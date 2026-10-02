from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

class Position(Enum):
    """NPC的立场: 友好/中立/敌对"""
    FRIENDLY = 0
    NEUTRAL = 1
    HOSTILE = 2


class CombatSkill(BaseModel):
    """战技"""

    name: str = ""
    skill: str = ""
    range: str = ""
    round: str = "1"
    description: str = ""
    success: str = "100"