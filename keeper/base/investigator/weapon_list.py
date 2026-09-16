# -*- coding: utf-8 -*-
"""COC7 武器表：WeaponList。"""
from typing import Optional

from pydantic import BaseModel, Field, PrivateAttr

from keeper.base.investigator.model import Weapon

class WeaponList(BaseModel):
    """武器表：list 存储，skillId 反向索引惰性构建、增删改时同步维护。"""

    items: list[Weapon] = Field(default_factory=list)

    _index_by_skill: Optional[dict[str, list[Weapon]]] = PrivateAttr(default=None)

    def get_weapons_by_skill_id(self, skill_id: str) -> list[Weapon]:
        if self._index_by_skill is None:
            self._index_by_skill = {}
            for w in self.items:
                if not w.skill_id:
                    continue
                self._index_by_skill.setdefault(w.skill_id, []).append(w)
        return self._index_by_skill.get(skill_id, [])

    def get_weapon_by_id(self, weapon_id: str) -> Optional[Weapon]:
        return next((w for w in self.items if w.id == weapon_id), None)

    def add_weapon(self, weapon: Weapon) -> bool:
        if self.get_weapon_by_id(weapon.id):
            return False
        self.items.append(weapon)
        if self._index_by_skill is not None:
            self._add_to_index(weapon)
        return True

    def remove_weapon(self, weapon_id: str) -> bool:
        for i, weapon in enumerate(self.items):
            if weapon.id == weapon_id:
                del self.items[i]
                if self._index_by_skill is not None and weapon.skill_id:
                    self._remove_from_index(weapon.id, weapon.skill_id)
                return True
        return False

    def update_weapon(self, weapon_id: str, patch: dict) -> bool:
        weapon = self.get_weapon_by_id(weapon_id)
        if weapon is None:
            return False
        old_skill_id = weapon.skill_id
        for key, value in patch.items():
            if key != "id":
                setattr(weapon, key, value)
        if self._index_by_skill is not None and old_skill_id != weapon.skill_id:
            if old_skill_id:
                self._remove_from_index(weapon.id, old_skill_id)
            self._add_to_index(weapon)
        return True

    def _add_to_index(self, weapon: Weapon) -> None:
        if not weapon.skill_id:
            return
        assert self._index_by_skill is not None
        self._index_by_skill.setdefault(weapon.skill_id, []).append(weapon)

    def _remove_from_index(self, weapon_id: str, skill_id: str) -> None:
        assert self._index_by_skill is not None
        weapons = self._index_by_skill.get(skill_id)
        if weapons is None:
            return
        for i, weapon in enumerate(weapons):
            if weapon.id == weapon_id:
                del weapons[i]
                break
        if not weapons:
            self._index_by_skill.pop(skill_id, None)
