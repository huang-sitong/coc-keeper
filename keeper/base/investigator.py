# -*- coding: utf-8 -*-
"""COC7 调查员数据模型。

依据 :doc:`/cocKeeperDesignSpec` 中“调查员相关类”设计，使用 Pydantic 建模。
"""
import math
import random
import re
from enum import Enum, IntEnum
from typing import Callable, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

__all__ = [
    "Difficulty",
    "CheckLevel",
    "CheckResult",
    "roll_d100",
    "roll_dice",
    "resolve_check",
    "AttackResult",
    "AttackBySkillResult",
    "DamageResult",
    "SkillGroup",
    "Skill",
    "SkillGroups",
    "AttributeName",
    "Attributes",
    "Sanity",
    "HitPoints",
    "MagicPoints",
    "DeriveAttributes",
    "BattleAttributes",
    "BodyStates",
    "MentalStates",
    "CharacterStatus",
    "Weapon",
    "WeaponList",
    "Stories",
    "Assets",
    "ExperiencedModule",
    "Friend",
    "Investigator",
]

# ==================== 通用：检定系统 ====================


class Difficulty(IntEnum):
    """检定难度。"""

    NORMAL = 0
    HARD = 1
    EXTREME = 2


CheckLevel = Literal["critical", "extreme", "hard", "success", "fail", "fumble"]


class CheckResult(BaseModel):
    """一次 d100 检定的结果。"""

    roll: int
    target: int
    success: bool
    level: CheckLevel


def roll_d100(rng: Callable[[], float] = random.random) -> int:
    """掷 d100，返回 1-100。"""
    return math.floor(rng() * 100) + 1


def roll_dice(expr: str, db: str = "0", rng: Callable[[], float] = random.random) -> int:
    """解析掷骰表达式（``2D6+1``、``1D3+DB``）。

    ``DB`` 会先替换为角色伤害加值，再按常规骰子表达式计算。
    """
    normalized = re.sub(r"DB", db or "0", expr, flags=re.IGNORECASE)
    normalized = normalized.replace("+-", "-")
    total = 0
    for term in re.split(r"(?=[+-])", normalized):
        if not term:
            continue
        sign = -1 if term.startswith("-") else 1
        t = term.lstrip("+-")
        m = re.fullmatch(r"(\d*)d(\d+)", t, flags=re.IGNORECASE)
        if m:
            times = int(m.group(1)) if m.group(1) else 1
            die = int(m.group(2))
            s = 0
            for _ in range(times):
                s += math.floor(rng() * die) + 1
            total += sign * s
        else:
            total += sign * (int(t) if t else 0)
    return total


def resolve_check(
    roll: int,
    value: int,
    difficulty: Difficulty = Difficulty.NORMAL,
) -> CheckResult:
    """COC7 检定裁决（技能/属性共用）。"""
    if difficulty == Difficulty.HARD:
        target = math.floor(value / 2)
    elif difficulty == Difficulty.EXTREME:
        target = math.floor(value / 5)
    else:
        target = value

    if roll == 100 or (roll >= 96 and value < 50):
        return CheckResult(roll=roll, target=target, success=False, level="fumble")
    if roll <= 5 and roll <= value:
        return CheckResult(roll=roll, target=target, success=True, level="critical")
    if roll <= target:
        if difficulty == Difficulty.EXTREME:
            level: CheckLevel = "extreme"
        elif difficulty == Difficulty.HARD:
            level = "hard"
        else:
            level = "success"
        return CheckResult(roll=roll, target=target, success=True, level=level)
    return CheckResult(roll=roll, target=target, success=False, level="fail")


class AttackResult(BaseModel):
    """攻击命中后的结算结果。"""

    weapon_id: str
    weapon_name: str
    damage: str
    attacks: str
    range: str
    ammo_left: int | str
    jammed: bool


class AttackBySkillResult(BaseModel):
    """完整攻击流程结果：检定 + 结算 + 伤害掷骰。"""

    skill_id: str
    skill_name: str
    weapon_id: Optional[str] = None
    check: CheckResult
    attack: Optional[AttackResult] = None
    hit: bool
    damage_roll: Optional[int] = None


class DamageResult(BaseModel):
    """受到伤害结算结果。"""

    amount: int
    current: int
    major_wound: bool
    con_check: Optional[CheckResult] = None
    unconscious: bool
    dying: bool
    dead: bool


# ==================== 技能 ====================


class SkillGroup(str, Enum):
    """技能所属类目（与 JSON skillGroups 键一一对应）。"""

    SPECIAL = "special"
    EXPLORE = "explore"
    SOCIAL = "social"
    COMBAT = "combat"
    MEDICAL = "medical"
    MOVE = "move"
    KNOWLEDGE = "knowledge"
    TECH = "tech"
    DRIVE = "drive"
    OTHER = "other"


class Skill(BaseModel):
    """技能条目。

    占位技能（如“科学:”“外语:”）靠 ``id`` 区分；
    总值与各级成功率均为派生值，不入库。
    """

    id: str
    name: str
    base: int = 0
    job: int = 0
    interest: int = 0
    growth: int = 0
    is_professional: bool = False

    @property
    def total(self) -> int:
        return self.base + self.job + self.interest + self.growth

    @property
    def success(self) -> int:
        return self.total

    @property
    def hard_success(self) -> int:
        return math.floor(self.total / 2)

    @property
    def extreme_success(self) -> int:
        return math.floor(self.total / 5)

    def check(
        self,
        difficulty: Difficulty = Difficulty.NORMAL,
        rng: Callable[[], float] = random.random,
    ) -> CheckResult:
        return resolve_check(roll_d100(rng), self.total, difficulty)

    def grow(self, rng: Callable[[], float] = random.random) -> bool:
        """成长检定：检定成功且骰值 > 当前值，则 growth += 1d10。"""
        c = self.check(Difficulty.NORMAL, rng)
        if not c.success or c.roll <= self.total:
            return False
        self.growth += math.floor(rng() * 10) + 1
        return True


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


# ==================== 属性 ====================


class AttributeName(str, Enum):
    """八项基础属性 + 幸运（字符串值与 JSON attributes 键一致）。"""

    STR = "str"
    DEX = "dex"
    CON = "con"
    APP = "app"
    POW = "pow"
    SIZ = "siz"
    EDU = "edu"
    INT = "int"
    LUC = "luc"


class Attributes(BaseModel):
    """八项基础属性与幸运。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    str_: int = Field(default=0, alias="str")
    dex: int = 0
    con: int = 0
    app: int = 0
    pow: int = 0
    siz: int = 0
    edu: int = 0
    int_: int = Field(default=0, alias="int")
    luc: int = 0

    def get(self, name: AttributeName | str) -> int:
        key = name.value if isinstance(name, AttributeName) else name
        return getattr(self, key)

    def check(
        self,
        name: AttributeName | str,
        difficulty: Difficulty = Difficulty.NORMAL,
        rng: Callable[[], float] = random.random,
    ) -> CheckResult:
        return resolve_check(roll_d100(rng), self.get(name), difficulty)

    @property
    def str(self) -> int:
        return self.str_

    @str.setter
    def str(self, value: int) -> None:
        self.str_ = value

    @property
    def int(self) -> int:
        return self.int_

    @int.setter
    def int(self, value: int) -> None:
        self.int_ = value


class Sanity(BaseModel):
    """理智值。"""

    current: int = 0
    start: int = 0
    max: int = 99


class HitPoints(BaseModel):
    """生命值。"""

    current: int = 0
    max: int = 0


class MagicPoints(BaseModel):
    """魔法值。"""

    current: int = 0
    max: int = 0


class DeriveAttributes(BaseModel):
    """派生属性：理智 / 生命 / 魔法。"""

    sanity: Sanity = Field(default_factory=Sanity)
    hp: HitPoints = Field(default_factory=HitPoints)
    mp: MagicPoints = Field(default_factory=MagicPoints)


class BattleAttributes(BaseModel):
    """战斗属性。"""

    db: str = "0"
    build: int = 0
    mov: int = 8
    mov_note: str = ""
    armor: str = "0"


# ==================== 状态 ====================


class BodyStates(BaseModel):
    """身体状态。"""

    injured: bool = False
    dead: bool = False
    unconscious: bool = False


class MentalStates(BaseModel):
    """精神状态。"""

    permanently_insane: bool = False
    temporarily_insane: bool = False
    indefinitely_insane: bool = False


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


# ==================== 武器 ====================


class Weapon(BaseModel):
    """武器条目。"""

    id: str
    name: str
    skill: str = ""
    skill_id: str = ""
    damage: str = ""
    range: str = ""
    tho: str = "1"
    round: str = ""
    num: str = ""
    err: str = ""
    weight: str = ""
    note: str = ""
    success: str = ""


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


# ==================== 背景 ====================


class Stories(BaseModel):
    """个人故事与描述。"""

    app: str = ""
    belief: str = ""
    i_person: str = ""
    i_place: str = ""
    i_item: str = ""
    trait: str = ""
    scar: str = ""
    mad: str = ""
    desc: str = ""


class Assets(BaseModel):
    """资产与随身物品。"""

    cash: str = "0"
    consumption: str = "0"
    assets: str = ""
    items: str = ""
    magic_items: str = ""
    magics: str = ""
    touches: str = ""


class ExperiencedModule(BaseModel):
    """经历过的模组。"""

    name: str = ""
    experience: str = ""


class Friend(BaseModel):
    """盟友/好友。"""

    character: str = ""
    relationship: str = ""
    player: str = ""


# ==================== 调查员（根对象） ====================


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
