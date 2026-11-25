"""Convert the two local screening workbooks into a single read-only snapshot."""

import argparse
import json
import math
import os
import re
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

from openpyxl import load_workbook

from app.research_cross_asset_screening import WORKBOOK_SNAPSHOT

METRICS = (
    ("今日异动", "activity", str),
    ("异动排名", "activityRank", int),
    ("连续关注持续时间", "attentionAge", int),
    ("日级别趋势", "day", str),
    ("日级别趋势持续时间", "dayAge", int),
    ("周级别趋势", "week", str),
    ("周级别趋势持续时间", "weekAge", int),
    ("月级别趋势", "month", str),
    ("月级别趋势持续时间", "monthAge", int),
    ("收盘价对比60日位置", "position", float),
    ("选美强度", "relativeStrength", float),
    ("选美动量", "relativeMomentum", float),
    ("选美转向", "relativeTurn", float),
    ("当前选美状态持续时间", "relativeAge", int),
    ("当前选美状态", "relativeState", str),
    ("当前选美状态涨幅", "relativeReturn", float),
    ("此前选美状态", "previousRelativeState", str),
    ("此前选美状态涨幅", "previousRelativeReturn", float),
    ("此前选美状态持续时间", "previousRelativeAge", int),
    ("当前主力资金状态持续时间", "flowAge", int),
    ("当前主力资金状态", "flowState", str),
    ("当前主力资金状态涨幅", "flowReturn", float),
    ("此前主力资金状态", "previousFlowState", str),
    ("此前主力资金状态涨幅", "previousFlowReturn", float),
    ("主力资金数值", "flowValue", float),
    ("主力资金相比前日变动", "flowChange", float),
    ("当前动能状态持续时间", "momentumAge", int),
    ("当前动能状态", "momentumState", str),
    ("当前动能状态累积涨跌幅", "momentumReturn", float),
    ("此前动能状态", "previousMomentumState", str),
    ("此前动能状态累积涨跌幅", "previousMomentumReturn", float),
    ("动能数值", "momentumValue", float),
    ("动能数值相比前日变动", "momentumChange", float),
)
GROUP = re.compile(r"(.+)[（(](\d+)[）)]$")


def workbook_date(path: Path) -> str:
    match = re.match(r"(\d{2}|\d{4})-(\d{2})-(\d{2})(?=\s)", path.stem)
    if not match:
        raise ValueError(f"{path.name} 缺少文件名日期")
    year, month, day = match.groups()
    return date(int(year) + (2000 if len(year) == 2 else 0), int(month), int(day)).isoformat()


def metric_value(value, kind):
    if value in (None, "", "—"):
        return None
    if kind is str and isinstance(value, str):
        return value.strip()
    if kind is int and type(value) is int and value > 0:
        return value
    if kind is float and type(value) in (int, float) and math.isfinite(value):
        return value
    raise ValueError("单元格类型不符合列定义")


def read_pool(path: Path, *, tools: bool) -> dict:
    sheet_name = "押注工具" if tools else "核心数据"
    leading = (
        ("二级分类", "标的代码", "标的名称", "标的代理资产")
        if tools else ("二级分类", "代码", "标的名称")
    )
    header = leading + tuple(title for title, _, _ in METRICS)
    groups, rows, identifiers = {}, [], set()
    group = None
    needs_header = False
    book = load_workbook(path, read_only=True, data_only=True, keep_links=False)
    try:
        for index, cells in enumerate(book[sheet_name].values, 1):
            if not any(cell is not None for cell in cells):
                continue
            cells = tuple(cells)
            if cells[0] is not None and all(cell is None for cell in cells[1:]):
                match = GROUP.fullmatch(str(cells[0]))
                if not match or needs_header or match[1] in groups:
                    raise ValueError(f"{sheet_name}第{index}行的一级分类无效")
                group = match[1]
                groups[group] = [int(match[2]), 0]
                needs_header = True
                continue
            if needs_header:
                if cells[:len(header)] != header or any(
                    v is not None for v in cells[len(header):]
                ):
                    raise ValueError(f"{sheet_name}第{index}行的表头与快照格式不匹配")
                needs_header = False
                continue
            if not group or not all(
                isinstance(v, (int, str)) and str(v).strip() for v in cells[:3]
            ):
                raise ValueError(f"{sheet_name}第{index}行缺少分类、代码或名称")
            category, code, name = (str(v).strip() for v in cells[:3])
            key = (group, category, code, name)
            if key in identifiers:
                raise ValueError(f"{sheet_name}第{index}行的标的重复")
            try:
                metrics = {
                    field: metric_value(cells[offset], kind)
                    for offset, (_, field, kind) in enumerate(METRICS, len(leading))
                }
            except (IndexError, ValueError) as exc:
                raise ValueError(f"{sheet_name}第{index}行的数据无效") from exc
            position = metrics["position"]
            if position is not None and not 0 <= position <= 1:
                raise ValueError(f"{sheet_name}第{index}行的60日位置超出范围")
            identifiers.add(key)
            groups[group][1] += 1
            rows.append({
                "group": group, "category": category, "code": code, "name": name,
                "proxy": metric_value(cells[3], str) if tools else None,
                **metrics,
            })
    finally:
        book.close()
    if not rows or needs_header or any(expected != count for expected, count in groups.values()):
        raise ValueError(f"{sheet_name}的分类标的数与表内统计不符")
    return {"file": path.name, "sheet": sheet_name, "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("core", type=Path)
    parser.add_argument("tools", type=Path)
    args = parser.parse_args()
    as_of = workbook_date(args.core)
    if workbook_date(args.tools) != as_of:
        parser.error("两份工作簿的文件名日期必须一致")
    pools = {"core": read_pool(args.core, tools=False), "tools": read_pool(args.tools, tools=True)}
    WORKBOOK_SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=WORKBOOK_SNAPSHOT.parent, suffix=".tmp", delete=False,
    ) as target:
        json.dump({"version": 1, "date": as_of, "pools": pools}, target, ensure_ascii=False,
                  separators=(",", ":"), allow_nan=False)
    os.replace(target.name, WORKBOOK_SNAPSHOT)
    for pool in pools.values():
        print(f"{as_of} {pool['sheet']} {len(pool['rows'])}")


if __name__ == "__main__":
    main()
