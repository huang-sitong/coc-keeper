# -*- coding: utf-8 -*-
"""``keeper.base.data_parse.excel`` 车卡解析接口的测试。

样例卡放在 ``.docs/`` 下（示例卡不入库），两者缺一时自动跳过相应用例。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from keeper.base.data_parse import parse_card_excel, parse_card_excel_json
from keeper.base.investigator.investigator import Investigator

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / ".docs"
EXAMPLE_CARD = DOCS / "COC7CardExample_nouxiaxia.xlsx"
EMPTY_CARD = DOCS / "COC7EmptyCardCY23Final.xlsx"


def _available_cards() -> list[Path]:
    return [path for path in (EXAMPLE_CARD, EMPTY_CARD) if path.exists()]


def test_parse_any_available_card_roundtrip() -> None:
    cards = _available_cards()
    if not cards:
        pytest.skip(".docs/ 下没有可用车卡样例")

    for path in cards:
        investigator = parse_card_excel(path)
        # JSON 结构能原样回填 Investigator
        payload = json.loads(parse_card_excel_json(path))
        assert Investigator.model_validate(payload).name == investigator.name

        skills = investigator.skills
        assert len(skills) > 0, f"{path.name}: 技能数为 0"
        # 技能不能有重名（BaseCreature 技能索引依赖唯一技能名）
        names = [skill.name for skill in skills]
        assert len(names) == len(set(names)), f"{path.name}: 存在重名技能"

        # 派生属性自洽
        derived = investigator.derive_attributes
        assert derived.hp.max >= derived.hp.current >= 0
        assert derived.sanity.max >= derived.sanity.current >= 0
        assert derived.mp.max >= derived.mp.current >= 0


@pytest.mark.skipif(not EXAMPLE_CARD.exists(), reason="示例卡未随仓库提供")
def test_parse_example_card_values() -> None:
    investigator = parse_card_excel(EXAMPLE_CARD)

    # 基本信息
    assert investigator.name == "nouxiaxia"
    assert investigator.player_name == "nouxia"
    assert investigator.job == "会计师"
    assert investigator.age == "22"
    assert investigator.gender == "男"
    assert investigator.era == "1920s"
    assert investigator.location == "火星"
    assert investigator.hometown == "地球"
    assert investigator.time == "公元2023年1月1日 0：00"

    # 属性与派生值
    attributes = investigator.attributes
    assert (
        attributes.str_,
        attributes.dex_,
        attributes.con_,
        attributes.edu_,
        attributes.luc_,
    ) == (80, 80, 80, 80, 80)
    derived = investigator.derive_attributes
    assert (derived.hp.current, derived.hp.max) == (12, 16)
    assert (derived.sanity.current, derived.sanity.max) == (98, 99)
    assert (derived.mp.current, derived.mp.max) == (16, 16)

    # 战斗属性
    battle = investigator.battle_attributes
    assert battle.db == "+1D4"
    assert battle.build == 1
    assert battle.mov == 8
    assert battle.armor == "2"

    # 本职技能（会计师）
    professional = {
        skill.name for skill in investigator.skills if skill.is_professional
    }
    assert professional == {
        "会计",
        "法律",
        "图书馆使用",
        "聆听",
        "说服",
        "侦查",
        "信用评级",
    }

    # 技能点拆分
    skill = investigator.get_skill("会计")
    assert skill is not None and (skill.base, skill.growth) == (5, 23)
    anthropology = investigator.get_skill("人类学")
    assert (
        anthropology is not None
        and (anthropology.base, anthropology.job) == (1, 34)
        and anthropology.is_professional is False
    )

    # 武器表
    weapons = {weapon.name: weapon for weapon in investigator.weapons}
    assert set(weapons) == {"肉搏", "黄铜指虎", "-巴雷特M82", "-81mm迫击炮"}
    assert weapons["黄铜指虎"].skill == "斗殴"
    assert weapons["黄铜指虎"].damage == "1D3+1+DB"
    assert weapons["黄铜指虎"].through is False
    assert weapons["-巴雷特M82"].through is True
    assert weapons["-巴雷特M82"].num == 11
    assert weapons["-巴雷特M82"].err == 96

    # 资产与随身物品
    assets = investigator.assets
    assert assets.cash == "300美元"
    assert assets.consumption == "50"
    assert assets.assets == "请在这里详述你的资产"
    assert assets.items == "一本书;一支笔"

    # 背景故事
    stories = investigator.stories
    assert stories.app == "一个普通人"
    assert stories.belief == "马克思主义"
    assert stories.trait == "喜欢睡觉"
    assert stories.mad == "焦虑症"

    # 状态：健康 / 清醒
    status = investigator.character_status
    assert status.body_states.injured is False
    assert status.mental_states.temporarily_insane is False


@pytest.mark.skipif(not EXAMPLE_CARD.exists(), reason="示例卡未随仓库提供")
def test_example_rows_are_parsed_one_to_one() -> None:
    """一格对一格：模板自带的示例行 / 占位提示不做过滤，原样进结果。"""
    investigator = parse_card_excel(EXAMPLE_CARD)

    assert [item.module for item in investigator.experienced_modules] == [
        "例：【毒汤】",
        "例：如果此处空间不够",
    ]
    assert investigator.experienced_modules[0].describetion == "SAN-6,HP-2,侦查+2"

    assert [item.describetion for item in investigator.touchs] == [
        "例：米-戈",
        "例：修格斯",
    ]
    first_touch = investigator.touchs[0]
    assert first_touch.result == "克苏鲁+3，克苏鲁(疯)+5，SAN-6，SAN(信)-8"
    assert first_touch.note == "第一次神话疯狂，相信者规则激活"
    assert first_touch.total == 6

    friend = investigator.friends[0]
    assert [item.name for item in investigator.friends] == ["例：丛雨"]
    assert friend.player == "神乐"
    assert friend.note == "一起出生入死的医生小姐"
    assert friend.change == "成为了挚友"
    assert friend.module == "卡森德拉..."

    assert [item.name for item in investigator.magic] == ["灰色束缚"]
    assert investigator.magic[0].cost == "8mp 1d6san 1h"

    # 占位提示文本同样原样保留
    assert investigator.stories.desc == "请务必在此填写背景故事！\n使用Alt+Enter换行"
    assert investigator.assets.assets == "请在这里详述你的资产"


@pytest.mark.skipif(not EXAMPLE_CARD.exists(), reason="示例卡未随仓库提供")
def test_skill_name_normalization() -> None:
    """技能名取原文拼接、冒号归一；末尾为 `:` 的技能跳过。"""
    investigator = parse_card_excel(EXAMPLE_CARD)
    names = {skill.name for skill in investigator.skills}

    # `：` 与占位序号①-⑩ 统一替换成半角 `:`
    assert {"格斗:斗殴", "格斗:链枷", "格斗:斧"} <= names
    assert {"射击:手枪", "射击:弓术", "射击:冲锋枪"} <= names
    assert {"科学:物理学", "科学:植物学"} <= names
    assert not any("：" in name for name in names)
    assert not any(set(name) & set("①②③④⑤⑥⑦⑧⑨⑩") for name in names)
    # 末尾是 `:`（专长格没填）的技能整个跳过
    assert not any(name.endswith(":") for name in names)
    assert names.isdisjoint({"格斗", "射击", "科学", "技艺", "外语", "生存", "驾驶", "学识"})
    # 不带冒号的技能原样保留（包括初始值为 0 的克苏鲁神话）
    assert {"克苏鲁神话", "闪避", "母语", "自定义技能"} <= names


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_card_excel(tmp_path / "不存在.xlsx")


def test_unknown_sheet() -> None:
    cards = _available_cards()
    if not cards:
        pytest.skip(".docs/ 下没有可用车卡样例")
    with pytest.raises(ValueError, match="工作表"):
        parse_card_excel(cards[0], sheet_name="没有这张表")
