from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

class Attributes(BaseModel):
    """八项基础属性与幸运。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    str_: int = Field(default=25, alias="str")
    dex_: int = Field(default=25, alias="dex")
    con_: int = Field(default=25, alias="con")
    app_: int = Field(default=25, alias="app")
    pow_: int = Field(default=25, alias="pow")
    siz_: int = Field(default=25, alias="siz")
    edu_: int = Field(default=25, alias="edu")
    int_: int = Field(default=25, alias="int")

    luc_: int = Field(default=25, alias="luc")
    # ---- 通用读写 ----

    @classmethod
    def _resolve(cls, attr: str) -> str:
        """把别名（'str'）或字段名（'str_'）统一解析成字段名。"""
        # 先按字段名匹配
        if attr in cls.model_fields:
            return attr
        # 再按 alias 匹配
        for name, f in cls.model_fields.items():
            if f.alias == attr:
                return name
        raise KeyError(f"未知属性: {attr!r}")

    def get(self, attr: str) -> int:
        return getattr(self, self._resolve(attr))

    def set(self, attr: str, value: int) -> None:
        setattr(self, self._resolve(attr), value)

# DeriveAttributes

class Sanity(BaseModel):
    """理智值。"""

    current: int = 1
    max: int = 99

class HitPoints(BaseModel):
    """生命值。"""

    current: int = 1
    max: int = 1

class MagicPoints(BaseModel):
    """魔法值。"""

    current: int = 0
    max: int = 0

class DeriveAttributes(BaseModel):
    """派生属性：理智 / 生命 / 魔法。"""

    sanity: Sanity = Field(default_factory=Sanity)
    hp: HitPoints = Field(default_factory=HitPoints)
    mp: MagicPoints = Field(default_factory=MagicPoints)

# end

class BattleAttributes(BaseModel):
    """战斗属性。"""

    db: str = "0"
    build: int = 0
    mov: int = 8
    armor: str = "0"

# skills

_GROUP_NAMES = (
    "special", "explore", "social", "combat", "medical",
    "move", "knowledge", "tech", "drive", "other",
)

class Skill(BaseModel):
    # NPC属性只包含name, base
    name: str = ""
    base: int = 25
    job: int = 0
    interest: int = 0
    growth: int = 0
    is_professional: bool = False

class SkillGroups(BaseModel):

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
    # name -> (group, index)
    _index: dict[str, tuple[str, int]] = PrivateAttr(default_factory=dict)

    def model_post_init(self, context: Any, /) -> None:
        super().model_post_init(context)
        self.update_index()

    # ---------------- 索引维护 ----------------

    def update_index(self) -> None:
        """全量重建索引。任何直接改动分组列表后都应调用。"""
        idx: dict[str, tuple[str, int]] = {}
        for group in _GROUP_NAMES:
            for i, skill in enumerate(getattr(self, group)):
                if skill.name in idx:
                    raise ValueError(f"技能名重复: {skill.name!r}")
                idx[skill.name] = (group, i)
        self._index = idx

    # ---------------- 读写 ----------------

    def get(self, name: str) -> Skill | None:
        """按名称取技能。不存在返回 None。"""
        loc = self._index.get(name)
        if loc is None:
            return None
        group, i = loc
        return getattr(self, group)[i]

    def set(self, group: str, skill: Skill) -> None:
        """
        在指定分组中写入技能：
          - 若同名技能已存在（可能在别的分组），先移除旧的；
          - 再把新的追加到目标分组末尾；
          - 最后重建索引。
        """
        if group not in _GROUP_NAMES:
            raise KeyError(f"未知分组: {group!r}")

        loc = self._index.get(skill.name)
        if loc is not None:
            old_group, old_i = loc
            getattr(self, old_group).pop(old_i)

        getattr(self, group).append(skill)
        self.update_index()
# end

class Weapon(BaseModel):
    """武器条目"""

    name: str = "徒手格斗"
    skill: str = "格斗(斗殴)"
    damage: str = "1D3+DB"
    range: str = "接触" # 基础射程
    through: bool = False # 是否贯穿
    round: str = "1"
    num: int = 0 # 装弹数
    err: int = 0
    weight: str = ""
    note: str = ""
    success: int = 25

class Magic(BaseModel):

    name: str = ""
    cost: str = "0"
    description: str = ""