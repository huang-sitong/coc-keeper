# -*- coding: utf-8 -*-
"""COC7 技能组：SkillGroups。"""
import random
from typing import Callable, Optional

from pydantic import BaseModel, Field, PrivateAttr

from keeper.base.investigator.model import SkillGroup
from keeper.base.investigator.skill import Skill

class SkillGroups(BaseModel):
    """技能组：十个类目各持一个列表；id 索引惰性构建，增删时同步维护。"""

    special: list[Skill] = Field(default_factory=list)
    explore: list[Skill] = Field(default_factory=list)
    social: list[Skill] = Field(default_factory=list)
    combat: list[Skill] = Field(default_factory=list)
    medical: list[Skill] = Field(default_factory=list)
    move: list[Skill] = Field(default_factory=list)
    knowledge: list[Skill] = Field(default_factory=list)
    tech: list[Skill] = Field(default_factory=list)
    drive: list[Skill] = Field(default_factory=list)
    other: list[Skill] = Field(default_factory=list)

    _index: Optional[dict[str, Skill]] = PrivateAttr(default=None)

    def all_group_lists(self) -> list[list[Skill]]:
        return [
            self.special,
            self.explore,
            self.social,
            self.combat,
            self.medical,
            self.move,
            self.knowledge,
            self.tech,
            self.drive,
            self.other,
        ]

    def get_all_skills(self) -> list[Skill]:
        return [s for group in self.all_group_lists() for s in group]

    def get_skills_by_group(self, group: SkillGroup) -> list[Skill]:
        return getattr(self, group.value)

    def get_skill_by_id(self, skill_id: str) -> Optional[Skill]:
        if self._index is None:
            self._index = {s.id: s for s in self.get_all_skills()}
        return self._index.get(skill_id)

    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        matched = self.get_skills_by_name(name)
        return matched[0] if matched else None

    def get_skills_by_name(self, name: str) -> list[Skill]:
        return [s for s in self.get_all_skills() if s.name == name]

    def add_skill(self, group: SkillGroup, skill: Skill) -> bool:
        if self.get_skill_by_id(skill.id):
            return False
        getattr(self, group.value).append(skill)
        if self._index is not None:
            self._index[skill.id] = skill
        return True

    def remove_skill(self, skill_id: str) -> bool:
        for group in self.all_group_lists():
            for i, skill in enumerate(group):
                if skill.id == skill_id:
                    del group[i]
                    if self._index is not None:
                        self._index.pop(skill_id, None)
                    return True
        return False

    def update_skill(self, skill_id: str, patch: dict) -> bool:
        skill = self.get_skill_by_id(skill_id)
        if skill is None:
            return False
        for key, value in patch.items():
            if key != "id":
                setattr(skill, key, value)
        return True

    def apply_growth(self, rng: Callable[[], float] = random.random) -> list[Skill]:
        return [s for s in self.get_all_skills() if s.grow(rng)]
