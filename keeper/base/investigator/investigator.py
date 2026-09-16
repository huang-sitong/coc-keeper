# -*- coding: utf-8 -*-
"""COC7 完整调查员：Investigator。"""
import math
import random
import re
from typing import Callable, Optional

from pydantic import BaseModel, Field

from keeper.base.investigator.attributes import Attributes
from keeper.base.investigator.character_status import CharacterStatus
from keeper.base.investigator.dice import roll_d100, roll_dice
from keeper.base.investigator.model import (
    Assets,
    AttributeName,
    AttackBySkillResult,
    AttackResult,
    BattleAttributes,
    CheckResult,
    DamageResult,
    DeriveAttributes,
    Difficulty,
    ExperiencedModule,
    Friend,
    Stories,
    Weapon,
)
from keeper.base.investigator.skill import Skill
from keeper.base.investigator.skill_groups import SkillGroups
from keeper.base.investigator.weapon_list import WeaponList

class Investigator(BaseModel):
    """完整调查员角色卡，对应 nouxiaxia.json 根对象。"""

    # ---- 基本信息 ----
    name: str = ""
    player_name: str = ""
    time: str = ""
    job: str = ""
    age: str = ""
    gender: str = ""
    location: str = ""
    hometown: str = ""
    era: str = ""
    is_editable: bool = True

    # ---- 属性 ----
    attributes: Attributes = Field(default_factory=Attributes)
    derive_attributes: DeriveAttributes = Field(default_factory=DeriveAttributes)
    battle_attributes: BattleAttributes = Field(default_factory=BattleAttributes)

    # ---- 状态 ----
    character_status: CharacterStatus = Field(default_factory=CharacterStatus)

    # ---- 点数 ----
    point_values: dict[str, int] = Field(default_factory=dict)
    pro_skills: list[str] = Field(default_factory=list)
    skill_points: list[int] = Field(default_factory=list)

    # ---- 战斗 / 背景 / 技能 ----
    weapons: WeaponList = Field(default_factory=WeaponList)
    stories: Stories = Field(default_factory=Stories)
    assets: Assets = Field(default_factory=Assets)
    experienced_modules: list[ExperiencedModule] = Field(default_factory=list)
    friends: list[Friend] = Field(default_factory=list)
    skill_groups: SkillGroups = Field(default_factory=SkillGroups)

    # ============ 委托访问 ============

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self.skill_groups.get_skill_by_id(skill_id)

    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        return self.skill_groups.get_skill_by_name(name)

    def get_skills_by_name(self, name: str) -> list[Skill]:
        return self.skill_groups.get_skills_by_name(name)

    def get_attribute(self, name: AttributeName | str) -> int:
        return self.attributes.get(name)

    def get_weapons_by_skill(self, skill_id: str) -> list[Weapon]:
        return self.weapons.get_weapons_by_skill_id(skill_id)

    # ============ 检定 ============

    def check_skill(
        self,
        skill_id: str,
        difficulty: Difficulty = Difficulty.NORMAL,
        rng: Optional[Callable[[], float]] = None,
    ) -> Optional[CheckResult]:
        skill = self.get_skill(skill_id)
        if skill is None:
            return None
        return skill.check(difficulty, rng or random.random)

    def check_attribute(
        self,
        name: AttributeName | str,
        difficulty: Difficulty = Difficulty.NORMAL,
        rng: Optional[Callable[[], float]] = None,
    ) -> CheckResult:
        return self.attributes.check(name, difficulty, rng or random.random)

    # ============ 攻击 ============

    def attack(
        self,
        weapon_id: str,
        check_result: Optional[CheckResult] = None,
        rng: Callable[[], float] = random.random,
    ) -> Optional[AttackResult]:
        weapon = self.weapons.get_weapon_by_id(weapon_id)
        if weapon is None:
            return None

        ammo_left: int | str = weapon.num
        if weapon.num != "":
            try:
                ammo_value = int(weapon.num)
            except ValueError:
                ammo_left = weapon.num
            else:
                ammo_left = ammo_value - 1
                weapon.num = str(ammo_left)

        jammed = False
        if check_result is not None and check_result.level == "fumble" and weapon.err != "":
            try:
                err_value = int(weapon.err)
            except ValueError:
                err_value = None
            jammed = err_value is not None and roll_d100(rng) >= err_value

        return AttackResult(
            weapon_id=weapon.id,
            weapon_name=weapon.name,
            damage=re.sub(r"DB", self.battle_attributes.db, weapon.damage, flags=re.IGNORECASE),
            attacks=weapon.tho,
            range=weapon.range,
            ammo_left=ammo_left,
            jammed=jammed,
        )

    def roll_weapon_damage(
        self,
        weapon_id: str,
        rng: Callable[[], float] = random.random,
    ) -> Optional[int]:
        weapon = self.weapons.get_weapon_by_id(weapon_id)
        if weapon is None or weapon.damage == "":
            return None
        return roll_dice(weapon.damage, self.battle_attributes.db, rng)

    def attack_by_skill(
        self,
        skill_id: str,
        weapon_id: Optional[str] = None,
        difficulty: Difficulty = Difficulty.NORMAL,
        rng: Callable[[], float] = random.random,
    ) -> Optional[AttackBySkillResult]:
        skill = self.get_skill(skill_id)
        if skill is None:
            return None

        check = skill.check(difficulty, rng)
        weapons_by_skill = self.weapons.get_weapons_by_skill_id(skill_id)
        weapon = (
            self.weapons.get_weapon_by_id(weapon_id)
            if weapon_id
            else weapons_by_skill[0]
            if weapons_by_skill
            else None
        )

        attack = (
            self.attack(weapon.id, check, rng)
            if weapon is not None and (check.success or check.level == "fumble")
            else None
        )
        hit = check.success and attack is not None

        return AttackBySkillResult(
            skill_id=skill_id,
            skill_name=skill.name,
            weapon_id=weapon.id if weapon else None,
            check=check,
            attack=attack,
            hit=hit,
            damage_roll=self.roll_weapon_damage(weapon.id, rng) if hit and weapon else None,
        )

    # ============ 伤害 ============

    def take_damage(
        self,
        amount: int,
        rng: Callable[[], float] = random.random,
    ) -> DamageResult:
        hp = self.derive_attributes.hp
        body = self.character_status.body_states

        hp.current = max(hp.current - amount, -hp.max)

        major_wound = amount > 0 and amount * 2 >= hp.max and hp.max > 0
        con_check: Optional[CheckResult] = None
        unconscious = False
        if major_wound:
            con_check = self.check_attribute(AttributeName.CON, Difficulty.NORMAL, rng)
            unconscious = not con_check.success
            if unconscious:
                body.unconscious = True

        dying = hp.current <= 0 and hp.current > -hp.max
        dead = hp.current <= -hp.max
        if dead:
            body.dead = True
            body.unconscious = True
        elif dying:
            body.injured = True
            body.unconscious = True

        return DamageResult(
            amount=amount,
            current=hp.current,
            major_wound=major_wound,
            con_check=con_check,
            unconscious=unconscious,
            dying=dying,
            dead=dead,
        )

    def resolve_dying(self, rng: Callable[[], float] = random.random) -> bool:
        """濒死轮检定：每轮 CON 检定失败则 HP -1 恶化，直至死亡或获救。"""
        hp = self.derive_attributes.hp
        if hp.current > 0 or hp.current <= -hp.max:
            return False

        c = self.check_attribute(AttributeName.CON, Difficulty.NORMAL, rng)
        if not c.success:
            hp.current -= 1
            if hp.current <= -hp.max:
                self.character_status.body_states.dead = True
        return c.success

    # ============ COC7 派生计算 ============

    def get_cthulhu_mythos(self) -> int:
        skill = self.get_skill_by_name("克苏鲁神话")
        return skill.total if skill else 0

    def derive_hp_max(self) -> int:
        return math.floor((self.attributes.con + self.attributes.siz) / 10)

    def derive_mp_max(self) -> int:
        return math.floor(self.attributes.pow / 5)

    def derive_sanity_max(self) -> int:
        return 99 - self.get_cthulhu_mythos()

    def derive_damage_bonus(self) -> str:
        s = self.attributes.str + self.attributes.siz
        if s <= 64:
            return "-2"
        if s <= 84:
            return "-1"
        if s <= 124:
            return "0"
        if s <= 164:
            return "+1d4"
        if s <= 204:
            return "+1d6"
        if s <= 284:
            return "+2d6"
        if s <= 364:
            return "+3d6"
        return "+4d6"

    def derive_build(self) -> int:
        s = self.attributes.str + self.attributes.siz
        if s <= 64:
            return -2
        if s <= 84:
            return -1
        if s <= 124:
            return 0
        if s <= 164:
            return 1
        if s <= 204:
            return 2
        if s <= 284:
            return 3
        if s <= 364:
            return 4
        return 5

    def derive_mov(self) -> int:
        str_, siz = self.attributes.str, self.attributes.siz
        if str_ < 8 and siz < 8:
            return 9
        if str_ < 12 and siz < 12:
            return 8
        return 7

    def sync_derived(self) -> None:
        """同步全部派生值（创建/洗点时调用）。"""
        self.derive_attributes.hp.max = self.derive_hp_max()
        self.derive_attributes.mp.max = self.derive_mp_max()
        self.derive_attributes.sanity.max = self.derive_sanity_max()
        self.battle_attributes.db = self.derive_damage_bonus()
        self.battle_attributes.build = self.derive_build()
        self.battle_attributes.mov = self.derive_mov()
