#!/usr/bin/env python3
"""Import SZPU official Guangdong undergraduate major-level scores."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAME = "深圳职业技术大学招生信息网"
SCHOOL_NAME = "深圳职业技术大学"
SCHOOL_CODE = "11113"
AGGREGATOR_SOURCE = "掌上高考（聚合补充）"

SOURCE_PAGES = {
    2023: {
        "url": "https://zhaosheng.szpu.edu.cn/info/1016/2953.htm",
        "path": ROOT / "assets" / "raw-cache" / "szpu" / "2023-undergraduate-admission-guangdong.html",
        "title": "深圳职业技术大学2023年夏季普通高考录取情况一览表（本科，广东省内）",
    },
    2024: {
        "url": "https://zhaosheng.szpu.edu.cn/info/1016/3112.htm",
        "path": ROOT / "assets" / "raw-cache" / "szpu" / "2024-undergraduate-admission.html",
        "title": "深圳职业技术大学2024年夏季普通高考录取情况一览表（本科）",
    },
    2025: {
        "url": "https://zhaosheng.szpu.edu.cn/info/1016/3263.htm",
        "path": ROOT / "assets" / "raw-cache" / "szpu" / "2025-undergraduate-admission.html",
        "title": "深圳职业技术大学2025年夏季普通高考录取情况一览表（本科）",
    },
}

TRACK_MAP = {
    "物理": "物理类",
    "物理类": "物理类",
    "历史": "历史类",
    "历史类": "历史类",
    "美术": "美术类",
}

GROUP_OVERRIDES = {
    (2023, "物理类", "电子信息工程技术（实验班）"): "201",
    (2024, "物理类", "电子信息工程技术（实验班）"): "201",
    (2025, "物理类", "电子信息工程技术（实验班）"): "201",
    (2023, "物理类", "电子信息工程技术"): "202",
    (2024, "物理类", "电子信息工程技术"): "202",
    (2025, "物理类", "电子信息工程技术"): "202",
    (2024, "物理类", "大数据技术"): "202",
}

ADMISSION_COLUMNS = [
    "year",
    "province",
    "track",
    "batch",
    "school_name",
    "school_code",
    "major_group",
    "major_name",
    "plan_type",
    "min_score",
    "min_rank",
    "admit_count",
    "source_url",
    "source_name",
    "notes",
]


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_cell = False
        self._cell_text = ""
        self._row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        if tag in {"td", "th"}:
            self._in_cell = True
            self._cell_text = ""

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_text += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            self._row.append(" ".join(self._cell_text.split()))
            self._in_cell = False
        if tag == "tr" and self._row:
            self.rows.append(self._row)


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def clean_major_name(value: object) -> str:
    text = norm(value).replace("\u3000", "")
    text = re.sub(r"\s+", "", text)
    text = text.replace("(", "（").replace(")", "）")
    return text


def numeric_text(value: object) -> str:
    text = norm(value).replace(",", "")
    if not text or text in {"-", "--"}:
        return ""
    try:
        number = float(text)
    except ValueError:
        return ""
    if number.is_integer():
        return str(int(number))
    return f"{number:.6f}".rstrip("0").rstrip(".")


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ADMISSION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_tables(path: Path) -> list[list[str]]:
    parser = TableParser()
    parser.feed(path.read_text(encoding="utf-8-sig", errors="ignore"))
    return parser.rows


def parse_page(year: int) -> list[dict[str, str]]:
    page = SOURCE_PAGES[year]
    rows = parse_tables(page["path"])
    professional_table = False
    current_province = ""
    current_track = ""
    output: list[dict[str, str]] = []

    for cells in rows:
        if "专业名称" in cells:
            professional_table = True
            continue
        if not professional_table:
            continue
        if not cells or "咨询电话" in "".join(cells):
            continue

        offset = 0
        if cells[0] == "广东":
            current_province = "广东"
            current_track = TRACK_MAP.get(cells[1], cells[1]) if len(cells) > 1 else ""
            offset = 2
        elif cells[0] in TRACK_MAP:
            current_track = TRACK_MAP[cells[0]]
            offset = 1
        elif cells[0] and cells[0] not in {"", "广东"} and len(cells) >= 2 and cells[1] in TRACK_MAP:
            current_province = cells[0]
            current_track = TRACK_MAP[cells[1]]
            offset = 2

        if current_province != "广东" or current_track not in {"物理类", "历史类"}:
            continue
        values = cells[offset:]
        if len(values) < 4:
            continue

        major_name = clean_major_name(values[0])
        if not major_name or major_name in {"物理", "历史", "美术"}:
            continue
        admit_count = numeric_text(values[1])
        if year == 2025:
            if len(values) < 6:
                continue
            high_score = numeric_text(values[2])
            min_score = numeric_text(values[3])
            avg_score = numeric_text(values[4])
            min_rank = numeric_text(values[5])
        else:
            high_score = numeric_text(values[2]) if len(values) >= 5 else ""
            min_score = numeric_text(values[-2])
            avg_score = ""
            min_rank = numeric_text(values[-1])
        if not (admit_count and min_score and min_rank):
            continue

        output.append(
            {
                "year": str(year),
                "province": "广东",
                "track": current_track,
                "batch": "本科批",
                "school_name": SCHOOL_NAME,
                "school_code": SCHOOL_CODE,
                "major_group": "",
                "major_name": major_name,
                "plan_type": "普通类",
                "min_score": min_score,
                "min_rank": min_rank,
                "admit_count": admit_count,
                "source_url": page["url"],
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        page["title"],
                        f"最高分={high_score}" if high_score else "",
                        f"平均分={avg_score}" if avg_score else "",
                    ]
                    if part
                ),
            }
        )
    return output


def build_group_lookup(existing: list[dict[str, str]]) -> dict[tuple[int, str, str], str]:
    candidates: dict[tuple[int, str, str], set[str]] = defaultdict(set)
    for row in existing:
        if row.get("school_name") != SCHOOL_NAME or not row.get("major_name"):
            continue
        group = norm(row.get("major_group"))
        if not group:
            continue
        key = (int(row["year"]), row.get("track", ""), clean_major_name(row.get("major_name", "")))
        candidates[key].add(group)

    lookup = {key: next(iter(groups)) for key, groups in candidates.items() if len(groups) == 1}
    lookup.update(GROUP_OVERRIDES)
    return lookup


def normalized_rows(args: argparse.Namespace, existing: list[dict[str, str]]) -> list[dict[str, str]]:
    group_lookup = build_group_lookup(existing)
    rows: list[dict[str, str]] = []
    for year in args.years:
        for row in parse_page(year):
            if row["track"] != args.track:
                continue
            key = (int(row["year"]), row["track"], row["major_name"])
            row["major_group"] = group_lookup.get(key, "")
            if not row["major_group"]:
                row["notes"] += "；专业组未从既有投档/聚合行匹配，需人工复核"
            rows.append(row)
    return rows


def row_should_replace(row: dict[str, str], args: argparse.Namespace) -> bool:
    return (
        row.get("province") == args.province
        and row.get("track") == args.track
        and row.get("batch") == args.batch
        and row.get("school_name") == SCHOOL_NAME
        and bool(row.get("major_name"))
        and row.get("source_name") in {SOURCE_NAME, AGGREGATOR_SOURCE}
        and int(row.get("year", "0") or "0") in args.years
    )


def import_rows(args: argparse.Namespace, rows: list[dict[str, str]]) -> tuple[int, int, int]:
    path = Path(args.data_dir).expanduser().resolve() / "admission_records.csv"
    existing = read_existing(path)
    before = len(existing)
    removed = 0
    if args.replace_existing:
        kept = []
        for row in existing:
            if row_should_replace(row, args):
                removed += 1
            else:
                kept.append(row)
        existing = kept
    write_rows(path, existing + rows)
    return before, removed, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - set(SOURCE_PAGES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"Unsupported years: {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SZPU official Guangdong undergraduate major scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--years", type=parse_years, default=[2023, 2024, 2025])
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_path = Path(args.data_dir).expanduser().resolve() / "admission_records.csv"
    existing = read_existing(data_path)
    rows = normalized_rows(args, existing)
    by_year = Counter(row["year"] for row in rows)
    missing_groups = [row for row in rows if not row["major_group"]]

    print("# 深圳职业技术大学本科专业录取分数导入\n")
    print(f"- 来源：{SOURCE_NAME}")
    print(f"- 范围：{args.province} / {args.track} / {','.join(map(str, args.years))}")
    print(f"- 获取专业记录：{len(rows)}；年份分布：{dict(sorted(by_year.items()))}")
    print(f"- 专业组未匹配：{len(missing_groups)}")
    if rows:
        print(f"- 预览：{rows[:5]}")
    if args.dry_run:
        print("- 模式：预览，不写入")
        return
    before, removed, after = import_rows(args, rows)
    print(f"- 模式：写入；原记录 {before}，替换聚合/旧官网专业行 {removed}，写入后 {after}")


if __name__ == "__main__":
    main()
