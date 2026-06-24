#!/usr/bin/env python3
"""Import SZTU official Guangdong major-level admission scores."""

from __future__ import annotations

import argparse
import csv
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SOURCE_NAME = "深圳技术大学本科招生网"
SCHOOL_NAME = "深圳技术大学"
SOURCE_URL = "https://zs.sztu.edu.cn/bkzn/lnlq1.htm"
QUERY_URL = "https://zs.sztu.edu.cn/lnlqcxjgy_new.jsp?wbtreeid=1015"

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
        self.in_cell = False
        self.current_row: list[str] = []
        self.current_cell: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.current_row = []
        if tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_cell:
            self.current_row.append(clean("".join(self.current_cell)))
            self.in_cell = False
        if tag == "tr" and any(self.current_row):
            self.rows.append(self.current_row)


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def digits(value: object) -> str:
    return re.sub(r"\D", "", clean(value))


def valid_score(value: object) -> str:
    text = digits(value)
    if not text:
        return ""
    number = int(text)
    return text if 300 <= number <= 750 else ""


def valid_rank(value: object) -> str:
    text = digits(value)
    if not text:
        return ""
    number = int(text)
    return text if 1 <= number <= 500000 else ""


def fetch_rows(year: int, province: str) -> list[list[str]]:
    body = urlencode({"nf": str(year), "sf": province}).encode("utf-8")
    request = Request(
        QUERY_URL,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": SOURCE_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    text = urlopen(request, timeout=60).read().decode("utf-8", "ignore")
    parser = TableParser()
    parser.feed(text)
    return parser.rows


def make_row(args: argparse.Namespace, year: int, values: list[str]) -> dict[str, str] | None:
    if len(values) < 6 or values[0] == "专业名称":
        return None
    major_name, source_track, admit_count, min_score, min_rank, remark = values[:6]
    if source_track != args.track:
        return None
    min_score = valid_score(min_score)
    min_rank = valid_rank(min_rank)
    if not major_name or not min_score or not min_rank:
        return None
    return {
        "year": str(year),
        "province": args.province,
        "track": args.track,
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": "",
        "major_name": clean(major_name).replace(" ", ""),
        "plan_type": "普通类",
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": digits(admit_count),
        "source_url": SOURCE_URL,
        "source_name": SOURCE_NAME,
        "notes": "；".join(
            part
            for part in [
                "学校官网历年录取查询接口导入",
                f"接口={QUERY_URL}",
                f"官网科类={source_track}",
                clean(remark),
                "只导入物理类/历史类本科专业行；艺术类、音乐类、美术类已排除",
            ]
            if part
        ),
    }


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in args.years:
        for values in fetch_rows(year, args.province):
            row = make_row(args, year, values)
            if row:
                rows.append(row)
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["major_name"], row["min_score"], row["min_rank"])
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
                clean(row.get("source_name")) == SOURCE_NAME
                and clean(row.get("school_name")) == SCHOOL_NAME
                and clean(row.get("province")) == args.province
                and clean(row.get("track")) == args.track
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"SZTU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SZTU official Guangdong major-level scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="14655")
    parser.add_argument("--years", type=parse_years, default=[2023, 2024, 2025])
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = normalized_rows(args)
    by_year: dict[str, int] = {}
    for row in rows:
        by_year[row["year"]] = by_year.get(row["year"], 0) + 1
    print("# 深圳技术大学专业录取分数导入\n")
    print(f"- 来源：{SOURCE_URL}")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(year) for year in args.years)}")
    print(f"- 获取专业记录：{len(rows)}；分年：{by_year}")
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
