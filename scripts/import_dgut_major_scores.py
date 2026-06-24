#!/usr/bin/env python3
"""Import DGUT official major-level admission scores for Guangdong."""

from __future__ import annotations

import argparse
import csv
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_NAME = "东莞理工学院招生信息网"
SCHOOL_NAME = "东莞理工学院"
PAGES = {
    2025: "https://zsb.dgut.edu.cn/zsdt/1jk1slslcpoj1.xhtml",
    2024: "https://zsb.dgut.edu.cn/bkszs/lnlq/1ie8bhcep8bul.xhtml",
    2023: "https://zsb.dgut.edu.cn/bkszs/lnlq/1hhbe20ji56vd.xhtml",
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
        self.in_table = False
        self.in_cell = False
        self.tables: list[list[list[str]]] = []
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.in_table = True
            self.rows = []
        if self.in_table and tag == "tr":
            self.row = []
        if self.in_table and tag in {"td", "th"}:
            self.in_cell = True
            self.buf = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.in_table and tag in {"td", "th"} and self.in_cell:
            self.row.append(" ".join("".join(self.buf).split()))
            self.in_cell = False
        if self.in_table and tag == "tr":
            if any(self.row):
                self.rows.append(self.row)
        if tag == "table" and self.in_table:
            self.tables.append(self.rows)
            self.in_table = False


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def int_text(value: object) -> str:
    text = norm(value).replace(",", "")
    return re.sub(r"\D", "", text)


def score_text(value: object) -> str:
    text = norm(value)
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return ""
    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else str(number)


def fetch_tables(year: int) -> list[list[list[str]]]:
    url = PAGES[year]
    text = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "ignore")
    parser = TableParser()
    parser.feed(text)
    return parser.tables


def track_from_text(text: str) -> str:
    if "物理" in text:
        return "物理类"
    if "历史" in text:
        return "历史类"
    return ""


def plan_type_from_text(text: str) -> str:
    if "地方专项" in text:
        return "地方专项"
    if "粤台" in text:
        return "粤台联合培养"
    if "中外" in text:
        return "中外合作"
    return "普通类"


def admission_row(
    args: argparse.Namespace,
    *,
    year: int,
    track: str,
    major_group: str,
    major_name: str,
    plan_type: str,
    admit_count: str,
    min_score: str,
    min_rank: str,
    max_score: str,
    avg_score: str,
    section_note: str,
) -> dict[str, str] | None:
    if track != args.track:
        return None
    if not major_name or major_name == "合计" or not min_score:
        return None
    return {
        "year": str(year),
        "province": args.province,
        "track": track,
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": major_group,
        "major_name": major_name,
        "plan_type": plan_type,
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": admit_count,
        "source_url": PAGES[year],
        "source_name": SOURCE_NAME,
        "notes": "；".join(
            part
            for part in [
                "学校官网HTML专业录取分数",
                f"专业组={major_group}" if major_group else "",
                f"最高分={max_score}" if max_score else "",
                f"平均分={avg_score}" if avg_score else "",
                section_note,
            ]
            if part
        ),
    }


def parse_2025(args: argparse.Namespace, table: list[list[str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    track = ""
    major_group = ""
    plan_type = "普通类"
    section_note = ""
    for raw in table:
        cells = [cell for cell in raw if cell]
        if not cells:
            continue
        joined = cells[0]
        if "东莞理工学院" in joined and "专业组" in joined:
            group_match = re.search(r"(\d{3})", joined)
            major_group = group_match.group(1) if group_match else ""
            track = track_from_text(joined)
            plan_type = plan_type_from_text(joined)
            section_note = joined
            continue
        if cells[0] in {"录取专业", "专业名称"} or len(cells) < 6:
            continue
        row = admission_row(
            args,
            year=2025,
            track=track,
            major_group=major_group,
            major_name=cells[0],
            plan_type=plan_type,
            admit_count=int_text(cells[1]),
            min_score=score_text(cells[2]),
            min_rank=int_text(cells[3]),
            max_score=score_text(cells[4]),
            avg_score=score_text(cells[6]) if len(cells) > 6 else "",
            section_note=section_note,
        )
        if row:
            rows.append(row)
    return rows


def parse_older(args: argparse.Namespace, year: int, tables: list[list[list[str]]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table_index, table in enumerate(tables[:2]):
        track = "物理类" if table_index == 0 else "历史类"
        major_group = ""
        section_note = ""
        for cells in table:
            cells = [cell for cell in cells if cell]
            if not cells or cells[0] == "专业组代码":
                continue
            if re.fullmatch(r"\d{3}", cells[0]) and len(cells) >= 8:
                major_group = cells[0]
                major_name = cells[1]
                admit_count, min_score, max_score, avg_score, min_rank = cells[2], cells[3], cells[4], cells[5], cells[6]
                section_note = cells[7] if len(cells) > 7 else section_note
            elif len(cells) >= 6:
                major_name = cells[0]
                admit_count, min_score, max_score, avg_score, min_rank = cells[1], cells[2], cells[3], cells[4], cells[5]
            else:
                continue
            row = admission_row(
                args,
                year=year,
                track=track,
                major_group=major_group,
                major_name=major_name,
                plan_type=plan_type_from_text(section_note),
                admit_count=int_text(admit_count),
                min_score=score_text(min_score),
                min_rank=int_text(min_rank),
                max_score=score_text(max_score),
                avg_score=score_text(avg_score),
                section_note=section_note,
            )
            if row:
                rows.append(row)
    return rows


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in args.years:
        tables = fetch_tables(year)
        if year == 2025:
            rows.extend(parse_2025(args, tables[0]))
        else:
            rows.extend(parse_older(args, year, tables))
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output = []
    for row in rows:
        key = (row["year"], row["track"], row["major_group"], row["major_name"], row["plan_type"], row["min_score"], row["min_rank"])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ADMISSION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def import_rows(args: argparse.Namespace, rows: list[dict[str, str]]) -> tuple[int, int]:
    path = Path(args.data_dir).expanduser().resolve() / "admission_records.csv"
    existing = read_existing(path)
    before = len(existing)
    if args.replace_existing:
        existing = [
            row
            for row in existing
            if not (
                norm(row.get("source_name")) == SOURCE_NAME
                and norm(row.get("school_name")) == SCHOOL_NAME
                and norm(row.get("province")) == args.province
                and norm(row.get("track")) == args.track
                and norm(row.get("batch")) == args.batch
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - set(PAGES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"DGUT importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import DGUT official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="")
    parser.add_argument("--years", type=parse_years, default=[2023, 2024, 2025])
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = normalized_rows(args)
    by_year: dict[str, int] = {}
    by_plan: dict[str, int] = {}
    for row in rows:
        by_year[row["year"]] = by_year.get(row["year"], 0) + 1
        by_plan[row["plan_type"]] = by_plan.get(row["plan_type"], 0) + 1
    print("# 东莞理工学院专业录取分数导入\n")
    print(f"- 来源：{PAGES[2025]}")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(year) for year in args.years)}")
    print(f"- 获取专业记录：{len(rows)}；分年：{by_year}；类型：{by_plan}")
    print(f"- 输出目录：{Path(args.data_dir).expanduser().resolve()}")
    if rows:
        print(f"- 预览：{rows[:5]}")
    if args.dry_run:
        print("- 模式：预览，不写入")
        return
    before, after = import_rows(args, rows)
    print(f"- 模式：写入；原记录 {before}，写入后 {after}")


if __name__ == "__main__":
    main()
