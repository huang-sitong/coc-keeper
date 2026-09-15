"""COC7 调查员数据模型基础自检。"""
from keeper.base.investigator import (
    AttributeName,
    Attributes,
    Difficulty,
    Investigator,
    Skill,
    SkillGroup,
    SkillGroups,
    Weapon,
    WeaponList,
    resolve_check,
    roll_dice,
)


def test_roll_dice_and_resolve_check():
    assert roll_dice("2D6+1", "0", lambda: 0.5) == 9
    assert roll_dice("1D3+DB", "-2", lambda: 0.5) == 0

    fumble = resolve_check(100, 80)
    assert fumble.success is False and fumble.level == "fumble"

    critical = resolve_check(1, 80)
    assert critical.success is True and critical.level == "critical"

    hard = resolve_check(30, 80, Difficulty.HARD)
    assert hard.success is True and hard.level == "hard"


def test_skill_and_groups():
    skill = Skill(id="s1", name="侦查", base=50)
    assert skill.total == 50
    assert skill.hard_success == 25
    assert skill.extreme_success == 10

    groups = SkillGroups()
    assert groups.add_skill(SkillGroup.EXPLORE, skill) is True
    assert groups.add_skill(SkillGroup.EXPLORE, skill) is False
    assert groups.get_skill_by_id("s1") is skill
    assert groups.get_skill_by_name("侦查") is skill
    assert groups.remove_skill("s1") is True
    assert groups.get_skill_by_id("s1") is None


def test_weapon_list_index():
    weapon = Weapon(id="w1", name="手枪", skill_id="firearm", damage="1D10", num="12")
    weapons = WeaponList()
    assert weapons.add_weapon(weapon) is True
    assert weapons.get_weapons_by_skill_id("firearm") == [weapon]
    assert weapons.update_weapon("w1", {"skill_id": "other"}) is True
    assert weapons.get_weapons_by_skill_id("firearm") == []
    assert weapons.get_weapons_by_skill_id("other") == [weapon]
    assert weapons.remove_weapon("w1") is True
    assert weapons.get_weapon_by_id("w1") is None


def test_investigator_derived_and_attack():
    inv = Investigator(name="测试员")
    inv.attributes.str = 50
    inv.attributes.con = 50
    inv.attributes.siz = 60
    inv.attributes.pow = 50
    inv.sync_derived()

    assert inv.derive_attributes.hp.max == 11
    assert inv.derive_attributes.mp.max == 10
    assert inv.battle_attributes.db == "0"
    assert inv.battle_attributes.mov == 7

    inv.skill_groups.add_skill(SkillGroup.COMBAT, Skill(id="fight", name="格斗", base=60))
    inv.weapons.add_weapon(Weapon(id="fist", name="拳头", skill_id="fight", damage="1D3+DB", num=""))
    result = inv.attack_by_skill("fight", rng=lambda: 0.01)
    assert result is not None
    assert result.hit is True
    assert result.check.success is True
    assert result.attack is not None
    assert result.attack.damage == "1D3+0"


def test_investigator_damage():
    inv = Investigator()
    inv.attributes.con = 50
    inv.attributes.siz = 60
    inv.sync_derived()
    inv.derive_attributes.hp.current = 11

    result = inv.take_damage(6, rng=lambda: 0.01)
    assert result.current == 5
    assert result.major_wound is True
    assert result.dying is False

    result = inv.take_damage(20, rng=lambda: 0.01)
    assert result.current == -11
    assert result.dead is True


def test_attributes_alias_roundtrip():
    attributes = Attributes(**{"str": 10, "int": 12})
    assert attributes.str == 10
    assert attributes.int == 12
    dumped = attributes.model_dump()
    assert dumped["str"] == 10
    assert dumped["int"] == 12


if __name__ == "__main__":
    test_roll_dice_and_resolve_check()
    test_skill_and_groups()
    test_weapon_list_index()
    test_investigator_derived_and_attack()
    test_investigator_damage()
    test_attributes_alias_roundtrip()
    print("all investigator tests passed")
