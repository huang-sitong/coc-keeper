# -*- coding: utf-8 -*-
"""COC7 属性：Attributes。"""
import random
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field

from keeper.base.investigator.dice import resolve_check, roll_d100
from keeper.base.investigator.model import AttributeName, CheckResult, Difficulty

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
