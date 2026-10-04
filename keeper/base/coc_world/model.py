from pydantic import BaseModel, ConfigDict, Field

class Attributes(BaseModel):
    """八项基础属性与幸运。"""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    str_: int = Field(default=40, alias="str")
    dex_: int = Field(default=40, alias="dex")
    con_: int = Field(default=40, alias="con")
    app_: int = Field(default=40, alias="app")
    pow_: int = Field(default=40, alias="pow")
    siz_: int = Field(default=40, alias="siz")
    edu_: int = Field(default=40, alias="edu")
    int_: int = Field(default=40, alias="int")

    luc_: int = Field(default=40, alias="luc")
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

    current: int = 98
    max: int = 99

class HitPoints(BaseModel):
    """生命值。"""

    current: int = 10
    max: int = 10

class MagicPoints(BaseModel):
    """魔法值。"""

    current: int = 1
    max: int = 1

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

class Skill(BaseModel):
    # NPC属性只包含name, base
    name: str = ""
    base: int = 25
    job: int = 0
    interest: int = 0
    growth: int = 0
    is_professional: bool = False
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
    success: int = 40

class Magic(BaseModel):

    name: str = ""
    cost: str = "0"
    description: str = ""