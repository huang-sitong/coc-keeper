# -*- coding: utf-8 -*-
"""COC7 技能：Skill。"""
import math
import random
from typing import Callable

from pydantic import BaseModel, ConfigDict

from keeper.base.investigator.dice import resolve_check, roll_d100
from keeper.base.investigator.model import CheckResult, Difficulty


class Skill(BaseModel):
    """技能条目。

    占位技能（如“科学:”“外语:”）靠 ``id`` 区分；
    总值与各级成功率均为派生值，不入库。
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

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
