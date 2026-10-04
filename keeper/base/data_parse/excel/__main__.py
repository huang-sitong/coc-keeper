# -*- coding: utf-8 -*-
"""命令行入口：把车卡 Excel 打印成 Investigator JSON。

示例：
    python -m keeper.base.data_parse.excel card.xlsx
    python -m keeper.base.data_parse.excel card.xlsx --sheet 人物卡 --indent 4
"""
from __future__ import annotations

import argparse
import sys

from keeper.base.data_parse.excel.card import DEFAULT_SHEET, parse_card_excel_json


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="解析 COC7 人物卡 Excel，输出 Investigator 结构的 JSON"
    )
    parser.add_argument("path", help="车卡 .xlsx 文件路径")
    parser.add_argument("--sheet", default=DEFAULT_SHEET, help="工作表名，默认：人物卡")
    parser.add_argument("--indent", type=int, default=2, help="JSON 缩进，默认 2")
    parser.add_argument("-o", "--output", help="输出文件路径，默认打印到 stdout")
    args = parser.parse_args(argv)

    try:
        text = parse_card_excel_json(args.path, sheet_name=args.sheet, indent=args.indent)
    except (FileNotFoundError, ValueError) as exc:
        print(f"解析失败: {exc}", file=sys.stderr)
        return 1

    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            file.write(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
