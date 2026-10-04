# -*- coding: utf-8 -*-
"""COC7 人物卡（CY23 模板）Excel 解析器。

输入一份 ``.xlsx`` 车卡，输出符合 :class:`Investigator` 结构的实例 / JSON。
模板参照 ``.docs/COC7CardExample_nouxiaxia.xlsx``（示例卡）与
``.docs/COC7EmptyCardCY23Final.xlsx``（空白卡），两者的「人物卡」工作表布局一致。

用法::

    from keeper.base.data_parse import parse_card_excel, parse_card_excel_json

    investigator = parse_card_excel("card.xlsx")     # Investigator 实例
    json_text = parse_card_excel_json("card.xlsx")   # Investigator 结构的 JSON

注意：
    解析读取的是 Excel 里公式的**缓存值**（``data_only=True``），
    车卡需要用 Excel / WPS 打开并保存过一次，否则公式格会拿到 ``None``。

解析策略：模板大量使用合并单元格，所以先用「标签文本」定位（归一化掉空白和
换行，例如 ``"生命值\\nHit  Points"`` → ``生命值HitPoints``），再按模板固定的
列偏移或「标签右侧第一个非空格」取值；技能表、武器表、经历/伙伴/法术等区块
则以区块标题行推导表头列号。

取值口径是「一格对一格」：模板自带的示例行（``例：【毒汤】``）与占位提示
（``请务必在此填写背景故事！``）都原样进结果，不做任何内容过滤；只有整行
没有任何内容的空行才跳过。
"""
from __future__ import annotations

import json
import re
import typing
import warnings
from pathlib import Path

import openpyxl

from keeper.base.coc_world.model import (
    Attributes,
    BattleAttributes,
    DeriveAttributes,
    HitPoints,
    Magic,
    MagicPoints,
    Sanity,
    Skill,
    SkillGroups,
    Weapon,
)
from keeper.base.data_parse.excel.skill_groups import skill_group
from keeper.base.investigator.investigator import Investigator
from keeper.base.investigator.model import (
    Assets,
    BodyStates,
    CharacterStatus,
    ExperiencedModule,
    Friend,
    MentalStates,
    Stories,
    Touch,
)

__all__ = ["DEFAULT_SHEET", "parse_card_excel", "parse_card_excel_json"]

DEFAULT_SHEET = "人物卡"
"""默认解析的工作表名。"""

# 表示“无/空”的符号
_EMPTY_SYMBOLS = ("——", "—", "-", "×")

_WHITESPACE_RE = re.compile(r"\s+")
_CIRCLED_INDEX_RE = re.compile(r"[①②③④⑤⑥⑦⑧⑨⑩]")


# --------------------------------------------------------------------------- #
# 基础转换
# --------------------------------------------------------------------------- #
def _norm(value: typing.Any) -> str:
    """标签归一化：去掉所有空白（含换行），用于匹配合并单元格里的多行标签。"""
    if value is None:
        return ""
    return _WHITESPACE_RE.sub("", str(value))


def _clean(value: typing.Any) -> str:
    """把单元格值转成去空白的字符串（浮点整数去掉小数点）。"""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def _to_int(value: typing.Any, default: int = 0) -> int:
    """尽力把单元格值转成 int；`——`、`独立装弹` 这类文本回退到 default。"""
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text or text in _EMPTY_SYMBOLS:
        return default
    try:
        return int(float(text))
    except ValueError:
        match = re.search(r"-?\d+", text)
        return int(match.group()) if match else default


# --------------------------------------------------------------------------- #
# 工作表封装
# --------------------------------------------------------------------------- #
class _Sheet:
    """对 openpyxl 工作表做「按标签找单元格」的薄封装。"""

    def __init__(self, worksheet: typing.Any) -> None:
        self._ws = worksheet
        # (归一化文本, 行, 列)，按行优先顺序，find 时取第一个命中
        self._labels: list[tuple[str, int, int]] = []
        for row in worksheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.strip():
                    self._labels.append((_norm(cell.value), cell.row, cell.column))

    # -- 底层读取 -------------------------------------------------------- #
    @property
    def max_column(self) -> int:
        return int(self._ws.max_column or 1)

    def value(self, row: int, col: int) -> typing.Any:
        if row < 1 or col < 1:
            return None
        return self._ws.cell(row=row, column=col).value

    # -- 标签定位 -------------------------------------------------------- #
    def find(
        self, label: str, rows: tuple[int, int] | None = None
    ) -> tuple[int, int] | None:
        """返回标签所在 (行, 列)；rows 限定扫描的行区间。"""
        key = _norm(label)
        for text, row, col in self._labels:
            if text == key and (rows is None or rows[0] <= row <= rows[1]):
                return row, col
        return None

    def find_all(
        self, label: str, rows: tuple[int, int] | None = None
    ) -> list[tuple[int, int]]:
        key = _norm(label)
        return [
            (row, col)
            for text, row, col in self._labels
            if text == key and (rows is None or rows[0] <= row <= rows[1])
        ]

    def find_prefix(
        self, prefix: str, rows: tuple[int, int] | None = None, max_len: int = 16
    ) -> tuple[int, int] | None:
        """匹配 `力量\\nSTR` 这类「中文名+英文码」标签。"""
        key = _norm(prefix)
        for text, row, col in self._labels:
            if (
                text.startswith(key)
                and len(text) <= max_len
                and (rows is None or rows[0] <= row <= rows[1])
            ):
                return row, col
        return None

    # -- 取值 ------------------------------------------------------------ #
    def first_right(
        self, pos: tuple[int, int] | None, gap: int
    ) -> typing.Any:
        if pos is None:
            return None
        row, col = pos
        for offset in range(1, gap + 1):
            value = self.value(row, col + offset)
            if value is not None and _clean(value):
                return value
        return None

    def text_after(
        self, label: str, rows: tuple[int, int] | None = None, gap: int = 6
    ) -> str:
        """标签右侧第一个非空单元格的文本。"""
        return _clean(self.first_right(self.find(label, rows), gap))

    def list_after(
        self,
        label: str,
        rows: tuple[int, int] | None = None,
        count: int = 5,
        gap: int = 14,
    ) -> list[str]:
        """标签右侧的一串非空单元格（用于「现时间」这种多列拼接的字段）。"""
        pos = self.find(label, rows)
        if pos is None:
            return []
        row, col = pos
        values: list[str] = []
        for offset in range(1, gap + 1):
            text = _clean(self.value(row, col + offset))
            if text:
                values.append(text)
                if len(values) >= count:
                    break
        return values

    def pair_after(
        self, label: str, rows: tuple[int, int] | None = None
    ) -> tuple[typing.Any, typing.Any]:
        """取标签右侧第 +3 / +5 列的值。

        CY23 模板里 `生命值` / `理智` / `魔法` 的标签都占 3 列，
        后面依次是「当前值」「上限值」两格（各占 2 列）。
        """
        pos = self.find(label, rows)
        if pos is None:
            return None, None
        row, col = pos
        return self.value(row, col + 3), self.value(row, col + 5)

    def header_columns(self, row: int, labels: typing.Sequence[str]) -> dict[str, list[int]]:
        """扫描表头行，返回每个标签出现的所有列号（技能表左右两栏各出现一次）。"""
        wanted = {_norm(label): label for label in labels}
        found: dict[str, list[int]] = {label: [] for label in labels}
        for col in range(1, self.max_column + 1):
            label = wanted.get(_norm(self.value(row, col)))
            if label is not None:
                found[label].append(col)
        return found


def _nearest(columns: list[int], target: int) -> int | None:
    """在表头列里挑离目标列最近的一个（用于把左右两栏的列配对）。"""
    if not columns:
        return None
    return min(columns, key=lambda col: abs(col - target))


def _compose_skill_name(base: str, sub: str) -> str:
    """拼接技能名与它的子技能名：`格斗：`+`斗殴` → `格斗：斗殴`，`科学①`+`物理学` → `科学：物理学`。

    没有子技能时去掉悬空的冒号（`生存：` → `生存`）。
    """
    if not sub:
        return base.rstrip("：:").strip() or base
    if base.endswith(("：", ":")):
        return base + sub
    match = _CIRCLED_INDEX_RE.search(base)
    if match:
        return base[: match.start()] + "：" + sub
    return base + sub


# --------------------------------------------------------------------------- #
# 各区块解析
# --------------------------------------------------------------------------- #
_INFO_ROWS = (1, 12)


def _parse_info(sheet: _Sheet) -> dict[str, str]:
    def text(label: str, gap: int = 6) -> str:
        return sheet.text_after(label, rows=_INFO_ROWS, gap=gap)

    info = {
        "name": text("姓名"),
        "player_name": text("玩家"),
        "job": text("职业"),
        "age": text("年龄"),
        "gender": text("性别"),
        "location": text("住地"),
        "hometown": text("故乡"),
        "era": text("时代"),
        "time": _compose_time(sheet.list_after("现时间", rows=_INFO_ROWS)),
    }
    return info


def _compose_time(parts: list[str]) -> str:
    """"现时间" 由 公元/公元前 + 年 + 月 + 日 (+ 时刻) 几格拼成。"""
    if not parts:
        return ""
    if len(parts) >= 4 and parts[0] in ("公元", "公元前") and parts[1].isdigit():
        text = f"{parts[0]}{int(parts[1])}年{parts[2]}{parts[3]}"
        if len(parts) > 4:
            text += f" {parts[4]}"
        return text
    return "".join(parts)


_ATTRIBUTE_ROWS = (3, 8)
_ATTRIBUTE_FIELDS: tuple[tuple[str, str], ...] = (
    ("力量", "str_"),
    ("敏捷", "dex_"),
    ("体质", "con_"),
    ("外貌", "app_"),
    ("意志", "pow_"),
    ("体型", "siz_"),
    ("教育", "edu_"),
    ("智力", "int_"),
    ("幸运", "luc_"),
)


def _parse_attributes(sheet: _Sheet) -> Attributes:
    values: dict[str, int] = {}
    for label, field in _ATTRIBUTE_FIELDS:
        pos = sheet.find_prefix(label, rows=_ATTRIBUTE_ROWS)
        values[field] = _to_int(sheet.first_right(pos, 4))
    return Attributes(**values)


_DERIVED_ROWS = (9, 12)


def _parse_derived(sheet: _Sheet) -> DeriveAttributes:
    hp_now, hp_max = sheet.pair_after("生命值HitPoints", rows=_DERIVED_ROWS)
    san_now, san_max = sheet.pair_after("理智Sanity", rows=_DERIVED_ROWS)
    mp_now, mp_max = sheet.pair_after("魔法MagicPoints", rows=_DERIVED_ROWS)

    hp_cur, hp_top = _to_int(hp_now), _to_int(hp_max)
    san_cur, san_top = _to_int(san_now), _to_int(san_max)
    mp_top = _to_int(mp_max)
    # 模板里魔法当前值经常留空：留空按“未消耗”处理，即当前=上限
    mp_cur = _to_int(mp_now, default=mp_top)

    return DeriveAttributes(
        sanity=Sanity(current=san_cur, max=san_top),
        hp=HitPoints(current=hp_cur, max=hp_top),
        mp=MagicPoints(current=mp_cur, max=mp_top),
    )


def _parse_battle(sheet: _Sheet) -> BattleAttributes:
    armor = sheet.text_after("护甲Armor", rows=_DERIVED_ROWS)
    db = sheet.text_after("伤害加值DamageBonus", rows=(51, 57))
    build = sheet.text_after("体格Build", rows=(51, 57))
    mov = sheet.text_after("移动力MOV", rows=_DERIVED_ROWS)
    return BattleAttributes(
        db=db or "0",
        build=_to_int(build),
        mov=_to_int(mov, default=8),
        armor=armor or "0",
    )


_SKILL_ROWS = (14, 50)
_SKILL_LABELS = ("本职", "技能名称", "初始", "成长", "职业", "兴趣")


def _parse_skills(sheet: _Sheet) -> list[Skill]:
    anchor = sheet.find("技能表", rows=_SKILL_ROWS)
    if anchor is None:
        return []
    header_row = anchor[0] + 1
    columns = sheet.header_columns(header_row, _SKILL_LABELS)
    name_columns = columns["技能名称"]

    skills: list[Skill] = []
    for name_col in name_columns:
        pro_col = _nearest(columns["本职"], name_col)
        base_col = _nearest(columns["初始"], name_col)
        growth_col = _nearest(columns["成长"], name_col)
        job_col = _nearest(columns["职业"], name_col)
        interest_col = _nearest(columns["兴趣"], name_col)
        sub_col = name_col + 2  # 子技能名（`格斗：`后面的`斗殴`）

        for row in range(header_row + 1, header_row + 41):
            name = _clean(sheet.value(row, name_col))
            if not name:
                break  # 该栏技能列到头了
            sub = _clean(sheet.value(row, sub_col))
            skills.append(
                Skill(
                    name=_compose_skill_name(name, sub),
                    base=_to_int(sheet.value(row, base_col) if base_col else None),
                    growth=_to_int(sheet.value(row, growth_col) if growth_col else None),
                    job=_to_int(sheet.value(row, job_col) if job_col else None),
                    interest=_to_int(
                        sheet.value(row, interest_col) if interest_col else None
                    ),
                    is_professional=_clean(sheet.value(row, pro_col) if pro_col else None)
                    == "★",
                )
            )
    return skills


def _parse_skill_groups(skills: list[Skill]) -> SkillGroups:
    groups = SkillGroups()
    for skill in skills:
        groups.set(skill_group(skill.name), skill)
    return groups


_WEAPON_ROWS = (51, 57)
_WEAPON_LABELS = (
    "武器名称",
    "类型",
    "使用技能",
    "成功率",
    "伤害",
    "基础射程",
    "贯穿",
    "次数",
    "装弹量",
    "故障值",
)


def _parse_weapons(sheet: _Sheet) -> list[Weapon]:
    anchor = sheet.find("武器表", rows=_WEAPON_ROWS)
    if anchor is None:
        return []
    header_row = anchor[0] + 1
    columns = sheet.header_columns(header_row, _WEAPON_LABELS)
    if not all(columns[label] for label in ("武器名称", "类型")):
        return []

    def col(label: str) -> int:
        return columns[label][0]

    name_col, type_col = col("武器名称"), col("类型")
    weapons: list[Weapon] = []
    for row in range(header_row + 1, header_row + 21):
        custom = _clean(sheet.value(row, name_col))
        selected = _clean(sheet.value(row, type_col))
        if custom == "无":
            custom = ""  # 模板里 `无` 表示没起自定义名
        name = custom or selected
        if not name:
            break

        weapon_range = _clean(
            sheet.value(row, col("基础射程")) if columns["基础射程"] else None
        )
        if weapon_range in _EMPTY_SYMBOLS:
            weapon_range = "接触"
        rounds = _clean(sheet.value(row, col("次数")) if columns["次数"] else None)

        weapons.append(
            Weapon(
                name=name,
                skill=_clean(
                    sheet.value(row, col("使用技能")) if columns["使用技能"] else None
                ),
                damage=_clean(sheet.value(row, col("伤害")) if columns["伤害"] else None),
                range=weapon_range,
                through=_clean(
                    sheet.value(row, col("贯穿")) if columns["贯穿"] else None
                )
                in ("√", "✓", "v", "V", "是", "1", "true", "TRUE"),
                round=rounds if rounds not in _EMPTY_SYMBOLS else "1",
                num=_to_int(
                    sheet.value(row, col("装弹量")) if columns["装弹量"] else None
                ),
                err=_to_int(
                    sheet.value(row, col("故障值")) if columns["故障值"] else None
                ),
                weight="",
                note=selected if custom and selected != custom else "",
                success=_to_int(
                    sheet.value(row, col("成功率")) if columns["成功率"] else None
                ),
            )
        )
    return weapons


_ASSET_ROWS = (60, 67)
_ITEM_ROWS = (76, 95)
_ITEM_SEPARATOR = ";"


def _parse_assets(sheet: _Sheet) -> Assets:
    """资产：现金、消费水平取表头正下方的数值格；``assets`` 只放
    「其他资产」下方那格自由描述（模板占位为「请在这里详述你的资产」）；
    ``items`` 是随身物品表的物品名，用 ``;`` 连接。"""
    # 资产区是「表头行 + 数值行」的结构，值在标签的正下方
    def below(label: str, offset: int = 1) -> str:
        pos = sheet.find(label, rows=_ASSET_ROWS)
        if pos is None:
            return ""
        return _clean(sheet.value(pos[0] + offset, pos[1]))

    consumption = below("消费水平")
    cash = below("当前现金($)")
    unit = below("单位")
    # 「其他资产」标签下方两行是自由描述栏
    detail = below("其他资产", offset=2)

    # 随身物品表（状态 / 部位 / 物品名称 …）
    item_pos = sheet.find("物品名称", rows=_ITEM_ROWS)
    items: list[str] = []
    if item_pos is not None:
        for offset in range(1, 16):
            text = _clean(sheet.value(item_pos[0] + offset, item_pos[1]))
            if text:
                items.append(text)

    return Assets(
        cash=f"{cash}{unit}" if cash else "0",
        consumption=consumption or "0",
        assets=detail,
        items=_ITEM_SEPARATOR.join(items),
    )


_STORY_ROWS = (55, 95)
_STORY_FIELDS: tuple[tuple[str, str], ...] = (
    ("形象描述", "app"),
    ("思想与信念", "belief"),
    ("重要之人", "i_person"),
    ("意义非凡之地", "i_place"),
    ("宝贵之物", "i_item"),
    ("特质", "trait"),
    ("伤口和疤痕", "scar"),
    ("恐惧症和躁狂症", "mad"),
)


def _parse_stories(sheet: _Sheet) -> Stories:
    values: dict[str, str] = {}
    for label, field in _STORY_FIELDS:
        values[field] = sheet.text_after(label, rows=_STORY_ROWS)

    # 自由背景故事：最后一个标签（恐惧症和躁狂症）下面一格开始
    desc = ""
    section = sheet.find("背景故事", rows=_STORY_ROWS)
    last_label = sheet.find("恐惧症和躁狂症", rows=_STORY_ROWS)
    if section is not None:
        start_row = (last_label[0] + 2) if last_label else section[0] + 17
        for row in range(start_row, start_row + 25):
            text = _clean(sheet.value(row, section[1]))
            if text:
                desc = text
                break
    values["desc"] = desc
    return Stories(**values)


_BODY_STATUS_ROWS = (9, 13)
_SKILL_SECTION_END = 112  # 「法术一览」所在的行
_FRIEND_SECTION_ROWS = (126, 145)
_SPELL_SECTION_ROWS = (110, 128)


def _parse_status(sheet: _Sheet) -> CharacterStatus:
    """两个 `状态:` 分别是生命状态（健康/重伤/昏迷/濒死）与精神状态（清醒/各类疯狂）。"""
    positions = sheet.find_all("状态:", rows=_BODY_STATUS_ROWS)
    body_text = ""
    mental_text = ""
    if positions:
        body_text = _clean(sheet.value(positions[0][0] + 1, positions[0][1]))
    if len(positions) > 1:
        mental_text = _clean(sheet.value(positions[1][0] + 1, positions[1][1]))

    body_states = BodyStates()
    if "濒" in body_text:
        body_states.injured = True
        body_states.unconscious = True
    if "死" in body_text and "濒" not in body_text:
        body_states.dead = True
    if "重伤" in body_text:
        body_states.injured = True
    if "昏迷" in body_text or "失去意识" in body_text:
        body_states.unconscious = True

    mental_states = MentalStates()
    if "永久" in mental_text:
        mental_states.permanently_insane = True
    elif "不定" in mental_text:
        mental_states.irregular_insane = True
    elif "临时" in mental_text:
        mental_states.temporarily_insane = True

    return CharacterStatus(body_states=body_states, mental_states=mental_states)


def _parse_experiences(sheet: _Sheet) -> list[ExperiencedModule]:
    anchor = sheet.find("经历模组")
    if anchor is None:
        return []
    header_row, module_col = anchor
    desc_col = (sheet.find("人物变化描述", rows=(header_row, header_row)) or (0, 0))[1]

    result: list[ExperiencedModule] = []
    for row in range(header_row + 1, header_row + 16):
        module = _clean(sheet.value(row, module_col))
        desc = _clean(sheet.value(row, desc_col)) if desc_col else ""
        if not module and not desc:
            continue
        result.append(ExperiencedModule(module=module, describetion=desc))
    return result


def _parse_touchs(sheet: _Sheet) -> list[Touch]:
    """「第三类接触」表：遇到了 / 获得的结果 / 备注 / 累计 → Touch 四个字段。"""
    anchor = sheet.find("遇到了", rows=(90, _SKILL_SECTION_END))
    if anchor is None:
        return []
    header_row, touch_col = anchor

    def column(label: str) -> int:
        return (sheet.find(label, rows=(header_row, header_row)) or (0, 0))[1]

    result_col = column("获得的结果")
    note_col = column("备注")
    total_col = column("累计")

    touches: list[Touch] = []
    for row in range(header_row + 1, header_row + 15):
        description = _clean(sheet.value(row, touch_col))
        result = _clean(sheet.value(row, result_col)) if result_col else ""
        note = _clean(sheet.value(row, note_col)) if note_col else ""
        total = _to_int(sheet.value(row, total_col)) if total_col else 0
        if not (description or result or note or total):
            continue
        touches.append(
            Touch(
                describetion=description,
                result=result,
                note=note,
                total=total,
            )
        )
    return touches


def _parse_friends(sheet: _Sheet) -> list[Friend]:
    """「调查员伙伴」表：姓名 / 玩家 / 注释 / 造成改变 / 相遇模组 → Friend 五个字段。"""
    section = sheet.find("调查员伙伴", rows=_FRIEND_SECTION_ROWS)
    if section is None:
        return []
    # 区块标题行下面一行才是表头行
    header = sheet.find("姓名", rows=(section[0], section[0] + 2))
    if header is None:
        return []
    header_row, name_col = header

    def column(label: str) -> int:
        return (sheet.find(label, rows=(header_row, header_row)) or (0, 0))[1]

    player_col = column("玩家")
    note_col = column("注释")
    change_col = column("造成改变")
    module_col = column("相遇模组")

    friends: list[Friend] = []
    for row in range(header_row + 1, header_row + 13):
        values = {
            "name": _clean(sheet.value(row, name_col)),
            "player": _clean(sheet.value(row, player_col)) if player_col else "",
            "note": _clean(sheet.value(row, note_col)) if note_col else "",
            "change": _clean(sheet.value(row, change_col)) if change_col else "",
            "module": _clean(sheet.value(row, module_col)) if module_col else "",
        }
        if not any(values.values()):
            continue
        friends.append(Friend(**values))
    return friends


def _parse_magic(sheet: _Sheet) -> list[Magic]:
    anchor = sheet.find("法术一览", rows=_SPELL_SECTION_ROWS)
    if anchor is None:
        return []
    header_row, _ = anchor
    columns = sheet.header_columns(header_row + 1, ("法术名称", "使用代价", "作用"))
    if not columns["法术名称"]:
        return []
    name_col = columns["法术名称"][0]
    cost_col = columns["使用代价"][0] if columns["使用代价"] else 0
    desc_col = columns["作用"][0] if columns["作用"] else 0

    spells: list[Magic] = []
    for row in range(header_row + 2, header_row + 16):
        name = _clean(sheet.value(row, name_col))
        if not name:
            continue
        spells.append(
            Magic(
                name=name,
                cost=_clean(sheet.value(row, cost_col)) if cost_col else "",
                description=_clean(sheet.value(row, desc_col)) if desc_col else "",
            )
        )
    return spells


# --------------------------------------------------------------------------- #
# 对外接口
# --------------------------------------------------------------------------- #
def _load_sheet(path: str | Path, sheet_name: str) -> _Sheet:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"车卡文件不存在: {path}")
    with warnings.catch_warnings():
        # 车卡用了 openpyxl 不支持的“数据验证扩展”，与取值无关，静音以免刷屏
        warnings.filterwarnings(
            "ignore", message="Data Validation extension is not supported"
        )
        workbook = openpyxl.load_workbook(path, data_only=True)
    try:
        if sheet_name not in workbook.sheetnames:
            raise ValueError(
                f"车卡里没有工作表 {sheet_name!r}，可用: {workbook.sheetnames}"
            )
        sheet = _Sheet(workbook[sheet_name])
        if sheet.find("调查员信息") is None and sheet.find("技能表") is None:
            raise ValueError(
                f"工作表 {sheet_name!r} 不像 CY23 模板的人物卡（找不到「调查员信息」/「技能表」）"
            )
        return sheet
    except Exception:
        workbook.close()
        raise


def parse_card_excel(
    path: str | Path,
    sheet_name: str = DEFAULT_SHEET,
) -> Investigator:
    """解析车卡 Excel，返回 :class:`Investigator` 实例。

    Args:
        path: 车卡文件路径（``.xlsx``）。
        sheet_name: 要解析的工作表名，默认「人物卡」。
    """
    sheet = _load_sheet(path, sheet_name)
    info = _parse_info(sheet)
    skills = _parse_skills(sheet)

    investigator = Investigator(
        name=info["name"],
        player_name=info["player_name"],
        job=info["job"],
        age=info["age"],
        gender=info["gender"],
        location=info["location"],
        hometown=info["hometown"],
        era=info["era"],
        time=info["time"],
        attributes=_parse_attributes(sheet),
        derive_attributes=_parse_derived(sheet),
        battle_attributes=_parse_battle(sheet),
        skill_groups=_parse_skill_groups(skills),
        weapons=_parse_weapons(sheet),
        magic=_parse_magic(sheet),
        character_status=_parse_status(sheet),
        stories=_parse_stories(sheet),
        assets=_parse_assets(sheet),
        experienced_modules=_parse_experiences(sheet),
        friends=_parse_friends(sheet),
        touchs=_parse_touchs(sheet),
    )
    return investigator


def parse_card_excel_json(
    path: str | Path,
    sheet_name: str = DEFAULT_SHEET,
    indent: int | None = 2,
) -> str:
    """解析车卡 Excel，返回符合 ``Investigator`` 结构的 JSON 字符串。"""
    investigator = parse_card_excel(path, sheet_name=sheet_name)
    payload = investigator.model_dump(by_alias=True)
    return json.dumps(payload, ensure_ascii=False, indent=indent)
