# -*- coding: utf-8 -*-
"""``keeper.base.coc_world.base_creature`` 技能/武器索引方法的测试。"""
from __future__ import annotations

import pytest

from keeper.base.coc_world.base_creature import BaseCreature
from keeper.base.coc_world.model import Skill, Weapon


def test_get_skill_by_name() -> None:
    creature = BaseCreature(skills=[Skill(name="侦查", base=25), Skill(name="聆听")])
    skill = creature.get_skill("侦查")
    assert skill is not None and skill.base == 25
    assert creature.get_skill("不存在") is None


def test_set_skill_append_and_replace() -> None:
    creature = BaseCreature(skills=[Skill(name="侦查", base=25)])
    # 不存在 → 追加
    creature.set_skill(Skill(name="聆听", base=30))
    assert [item.name for item in creature.skills] == ["侦查", "聆听"]
    # 同名 → 原地替换，位置不变
    creature.set_skill(Skill(name="侦查", base=40))
    assert [item.name for item in creature.skills] == ["侦查", "聆听"]
    assert creature.get_skill("侦查") is not None
    assert creature.get_skill("侦查").base == 40


def test_weapon_index_methods() -> None:
    creature = BaseCreature(weapons=[Weapon(name="徒手格斗")])
    assert creature.get_weapon("徒手格斗") is not None
    assert creature.get_weapon("不存在") is None
    creature.set_weapon(Weapon(name="左轮手枪"))
    creature.set_weapon(Weapon(name="徒手格斗", damage="1D4+DB"))
    assert [item.name for item in creature.weapons] == ["徒手格斗", "左轮手枪"]
    assert creature.get_weapon("徒手格斗").damage == "1D4+DB"


def test_update_skill_index_rejects_duplicates() -> None:
    creature = BaseCreature(skills=[Skill(name="侦查")])
    creature.skills.append(Skill(name="侦查"))
    with pytest.raises(ValueError, match="技能名重复"):
        creature.update_skill_index()


def test_update_weapon_index_rejects_duplicates() -> None:
    creature = BaseCreature(weapons=[Weapon(name="小刀")])
    creature.weapons.append(Weapon(name="小刀"))
    with pytest.raises(ValueError, match="武器名重复"):
        creature.update_weapon_index()
