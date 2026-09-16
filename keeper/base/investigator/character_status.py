# -*- coding: utf-8 -*-
"""COC7 角色状态：CharacterStatus。"""
from pydantic import BaseModel, Field

from keeper.base.investigator.model import BodyStates, MentalStates

class CharacterStatus(BaseModel):
    """角色状态。"""

    body_states: BodyStates = Field(default_factory=BodyStates)
    mental_states: MentalStates = Field(default_factory=MentalStates)

    def get_active_body_states(self) -> list[str]:
        return [k for k, v in self.body_states.model_dump().items() if v]

    def get_active_mental_states(self) -> list[str]:
        return [k for k, v in self.mental_states.model_dump().items() if v]

    def is_incapacitated(self) -> bool:
        return self.body_states.unconscious or self.body_states.dead

    def is_mad(self) -> bool:
        return (
            self.mental_states.permanently_insane
            or self.mental_states.temporarily_insane
            or self.mental_states.indefinitely_insane
        )
