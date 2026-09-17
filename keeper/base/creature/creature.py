# -*- coding: utf-8 -*-
"""敌人/怪物核心类：Creature。"""
from __future__ import annotations

import random
import re
from typing import Callable, Optional

from pydantic import Field

from keeper.base.investigator import (
    AttributeName,
    AttackBySkillResult,
    AttackResult,
    Attributes,
    CheckResult,
    DamageResult,
    Difficulty,
    Skill,
    SkillGroups,
    Weapon,
    WeaponList,
    roll_d100,
    roll_dice,
)
from keeper.base.module_base import ModuleBaseModel
from keeper.base.creature.model import ArmorRollResult, SanityLossResult

class Creature(ModuleBaseModel):
    """敌人/怪物：叙述字段与详细战斗数据合并为单个数据类。

    属性复用 ``Attributes``，技能复用 ``SkillGroups``，武器复用 ``WeaponList``；
    HP/MP/SAN/DB/Build/Move/Armor 直接以模组给出的数值记录。

    该类同时提供与调查员 ``Investigator`` 相近的运行时接口：技能/属性访问、
    检定、攻击、受伤结算、理智损失与护甲掷骰，方便战斗轮直接调用。
    """

    id: str
    name: str
    appearance: Optional[str] = None
    appears_in: list[str] = Field(default_factory=list, alias="appearsIn")

    # 详细战斗数据（类似简化版调查员）
    attributes: Attributes = Field(default_factory=Attributes)
    hp: int = 0
    # 最大 HP 不入模组 JSON；未提供时默认等于初始 hp。
    max_hp: int = Field(default=0, alias="maxHp", exclude=True)
    mp: int = 0
    sanity: int = 0
    db: str = "0"
    build: int = 0
    move: int = 8
    armor: str = "0"
    skills: SkillGroups = Field(default_factory=SkillGroups)
    weapons: WeaponList = Field(default_factory=WeaponList)
    spells: list[str] = Field(default_factory=list)
    attacks: list[str] = Field(default_factory=list)
    sanity_loss: Optional[str] = Field(default=None, alias="sanityLoss")
    tactics: Optional[str] = None

    def model_post_init(self, __context: object) -> None:
        """确保有可用的最大 HP，供受伤/死亡接口计算。"""
        if self.max_hp <= 0:
            self.max_hp = max(self.hp, 0)

    # ============ 委托访问 ============

    def get_attribute(self, name: AttributeName | str) -> int:
        """读取一项基础属性。"""
        return self.attributes.get(name)

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """按 id 获取技能。"""
        return self.skills.get_skill_by_id(skill_id)

    def get_skill_by_name(self, name: str) -> Optional[Skill]:
        """按名称获取技能。"""
        return self.skills.get_skill_by_name(name)

    def get_skills_by_name(self, name: str) -> list[Skill]:
        """按名称获取所有同名技能。"""
        return self.skills.get_skills_by_name(name)

    def get_weapons_by_skill(self, skill_id: str) -> list[Weapon]:
        """获取与指定技能关联的武器列表。"""
        return self.weapons.get_weapons_by_skill_id(skill_id)

    # ============ 检定 ============

    def check_skill(
        self,
        skill_id: str,
        difficulty: Difficulty = Difficulty.NORMAL,
        rng: Optional[Callable[[], float]] = None,
    ) -> Optional[CheckResult]:
        """对指定技能发起一次 d100 检定。"""
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
        """对指定属性发起一次 d100 检定。"""
        return self.attributes.check(name, difficulty, rng or random.random)

    # ============ 攻击 ============

    def attack(
        self,
        weapon_id: str,
        check_result: Optional[CheckResult] = None,
        rng: Callable[[], float] = random.random,
    ) -> Optional[AttackResult]:
        """按武器结算一次攻击；``check_result`` 用于判断是否卡壳。"""
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
                err_value: Optional[int] = int(weapon.err)
            except ValueError:
                err_value = None
            jammed = err_value is not None and roll_d100(rng) >= err_value

        return AttackResult(
            weapon_id=weapon.id,
            weapon_name=weapon.name,
            damage=re.sub(r"DB", self.db, weapon.damage, flags=re.IGNORECASE),
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
        """掷指定武器的伤害；复杂描述会截取斜线前的标准骰式。"""
        weapon = self.weapons.get_weapon_by_id(weapon_id)
        if weapon is None or weapon.damage == "":
            return None
        expression = weapon.damage.split("/", 1)[0].strip()
        if not expression:
            return None
        try:
            return roll_dice(expression, self.db, rng)
        except (ValueError, IndexError):
            return None

    def attack_by_skill(
        self,
        skill_id: str,
        weapon_id: Optional[str] = None,
        difficulty: Difficulty = Difficulty.NORMAL,
        rng: Callable[[], float] = random.random,
    ) -> Optional[AttackBySkillResult]:
        """完整攻击流程：技能检定 + 武器结算 + 伤害掷骰。"""
        skill = self.get_skill(skill_id)
        if skill is None:
            return None

        check = skill.check(difficulty, rng)
        weapons_by_skill = self.weapons.get_weapons_by_skill_id(skill_id)
        if weapon_id:
            weapon = self.weapons.get_weapon_by_id(weapon_id)
        elif weapons_by_skill:
            weapon = weapons_by_skill[0]
        else:
            # 模组 AI 常用简写：武器未绑定 skillId 时，退回第一件武器。
            weapon = self.weapons.items[0] if self.weapons.items else None

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

    # ============ 伤害与状态 ============

    def get_hp_max(self) -> int:
        """返回本次创角/载入时确定的最大 HP。"""
        return self.max_hp if self.max_hp > 0 else max(self.hp, 0)

    def is_alive(self) -> bool:
        """当前 HP 大于 0。"""
        return self.hp > 0

    def is_dying(self) -> bool:
        """进入濒死区间（<=0 但未低于负最大 HP）。"""
        max_hp = self.get_hp_max()
        return max_hp > 0 and 0 >= self.hp > -max_hp

    def is_dead(self) -> bool:
        """HP 已降至负最大 HP 或更低。"""
        max_hp = self.get_hp_max()
        return max_hp > 0 and self.hp <= -max_hp

    def take_damage(
        self,
        amount: int,
        rng: Callable[[], float] = random.random,
    ) -> DamageResult:
        """承受伤害并返回与调查员一致的结算结果。"""
        max_hp = self.get_hp_max()
        self.hp = max(self.hp - amount, -max_hp) if max_hp > 0 else self.hp - amount

        major_wound = amount > 0 and max_hp > 0 and amount * 2 >= max_hp
        con_check: Optional[CheckResult] = None
        unconscious = False
        if major_wound:
            con_check = self.check_attribute(AttributeName.CON, Difficulty.NORMAL, rng)
            unconscious = not con_check.success

        dying = max_hp > 0 and 0 >= self.hp > -max_hp
        dead = max_hp > 0 and self.hp <= -max_hp

        return DamageResult(
            amount=amount,
            current=self.hp,
            major_wound=major_wound,
            con_check=con_check,
            unconscious=unconscious,
            dying=dying,
            dead=dead,
        )

    def resolve_dying(self, rng: Callable[[], float] = random.random) -> bool:
        """濒死轮检定：CON 失败则 HP -1 继续恶化。"""
        max_hp = self.get_hp_max()
        if max_hp <= 0 or self.hp > 0 or self.hp <= -max_hp:
            return False
        check = self.check_attribute(AttributeName.CON, Difficulty.NORMAL, rng)
        if not check.success:
            self.hp -= 1
        return check.success

    # ============ 理智损失 ============

    def get_sanity_loss_expression(self, success: bool = False) -> str:
        """解析 ``sanityLoss``："1/1D4" 分别代表成功/失败损失。"""
        expression = (self.sanity_loss or "").strip()
        if not expression:
            return "0"
        # 去掉“（见到他移动时）”等说明文字。
        expression = re.sub(r"[（(].*?[）)]", "", expression).strip()
        parts = [part.strip() for part in expression.split("/", 1)]
        if len(parts) == 2:
            return parts[0] if success else parts[1]
        return parts[0]

    def roll_sanity_loss(
        self,
        success: bool = False,
        rng: Callable[[], float] = random.random,
    ) -> int:
        """掷理智损失；``success`` 为 True 时使用成功项，否则使用失败项。"""
        expression = self.get_sanity_loss_expression(success)
        if not expression or expression in {"0", "-", "无"}:
            return 0
        try:
            return max(roll_dice(expression, "0", rng), 0)
        except (ValueError, IndexError):
            return 0

    def resolve_sanity_loss(
        self,
        success: bool = False,
        rng: Callable[[], float] = random.random,
    ) -> SanityLossResult:
        """返回包含表达式与骰值的理智损失结构化结果。"""
        expression = self.get_sanity_loss_expression(success)
        return SanityLossResult(
            expression=expression,
            success=success,
            loss=self.roll_sanity_loss(success, rng),
        )

    # ============ 护甲 ============

    def get_armor_expression(self) -> str:
        """从叙述性护甲字段中提取可掷骰的表达式。"""
        text = (self.armor or "").strip()
        if not text:
            return "0"
        text = re.sub(r"[（(].*?[）)]", "", text).strip()
        match = re.search(r"(\d+d\d+(?:[+-]\d+)*|\d+)", text, flags=re.IGNORECASE)
        return match.group(1) if match else "0"

    def roll_armor(
        self,
        rng: Callable[[], float] = random.random,
    ) -> int:
        """按护甲描述掷减伤值，无法解析时返回 0。"""
        expression = self.get_armor_expression()
        if not expression or expression == "0":
            return 0
        if "d" in expression.lower():
            value = roll_dice(expression, "0", rng)
        else:
            value = int(expression)
        return max(value, 0)

    def resolve_armor(
        self,
        rng: Callable[[], float] = random.random,
    ) -> ArmorRollResult:
        """返回包含表达式与减伤骰值的结构化护甲结果。"""
        expression = self.get_armor_expression()
        return ArmorRollResult(
            expression=expression,
            value=self.roll_armor(rng),
        )

    # ============ 展示 ============

    def info(self, include_keeper_info: bool = False) -> str:
        """生成便于注入 LLM 的敌人卡片文本。"""
        attrs = self.attributes.model_dump(by_alias=True)
        skill_lines = [
            f"{skill.name} {skill.total}%"
            for group in self.skills.all_group_lists()
            for skill in group
        ]
        weapon_lines = [f"{weapon.name} {weapon.damage}" for weapon in self.weapons.items]
        lines = [
            f"【敌人】{self.name}",
            f"外貌：{self.appearance or ''}",
            f"属性：{attrs}",
            f"HP：{self.hp} MP：{self.mp} SAN：{self.sanity}",
            f"DB：{self.db} Build：{self.build} Move：{self.move}",
            f"护甲：{self.armor or ''}",
            f"技能：{'；'.join(skill_lines) or '无'}",
            f"武器：{'；'.join(weapon_lines) or '无'}",
            f"攻击：{'；'.join(self.attacks) or '无'}",
            f"法术：{'；'.join(self.spells) or '无'}",
        ]
        if include_keeper_info:
            if self.tactics:
                lines.append(f"战术：{self.tactics}")
            if self.sanity_loss:
                lines.append(f"理智损失：{self.sanity_loss}")
        return "\n".join(lines)

    def describe(self, include_keeper_info: bool = False) -> str:
        """``info`` 的语义化别名。"""
        return self.info(include_keeper_info)

    def to_prompt(self, include_keeper_info: bool = False) -> str:
        """``info`` 的别名，便于 Agent 上下文调用。"""
        return self.info(include_keeper_info)

    def format_card(self, include_keeper_info: bool = False) -> str:
        """``info`` 的卡片格式化别名。"""
        return self.info(include_keeper_info)
