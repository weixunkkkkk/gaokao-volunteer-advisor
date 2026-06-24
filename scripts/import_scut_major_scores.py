#!/usr/bin/env python3
"""Import SCUT official major-level admission scores.

Source: 华南理工大学本科招生网 “历年录取分数线” commonquery endpoint.
The official query returns year, province, category, track, major, max score,
min score, and average score. This importer writes normalized
admission_records.csv rows and keeps max/average scores in notes.
"""

from __future__ import annotations

import argparse
import csv
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PHYSICS_DIR = ROOT / "assets" / "pilot-data" / "guangdong-physics"
DEFAULT_HISTORY_DIR = ROOT / "assets" / "pilot-data" / "guangdong-history"
QUERY_URL = (
    "https://admission.scut.edu.cn/_web/_apps/commonquery/commonquery/api/"
    "commonqueryCacheResult/16.rst?_p=YXM9MzQ4JnQ9MTcyMyZwPTEmbT1OJg__&mobileTemplate=false"
)
ENTRY_URL = "https://admission.scut.edu.cn/30821/list.htm"
SOURCE_NAME = "华南理工大学本科招生网"
SCHOOL_NAME = "华南理工大学"
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


class ResultTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
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
            text = re.sub(r"\s+", " ", "".join(self.current_cell)).strip()
            self.current_row.append(text)
            self.in_cell = False
        if tag == "tr" and self.current_row:
            self.rows.append(self.current_row)


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def fetch_rows(year: int, province: str, category: str, source_track: str) -> list[list[str]]:
    body = urlencode(
        {
            "cq16s188": str(year),
            "cq16s189": province,
            "cq16s190": category,
            "cq16s191": source_track,
        }
    ).encode()
    request = Request(
        QUERY_URL,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": ENTRY_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    html = urlopen(request, timeout=30).read().decode("utf-8", "replace")
    parser = ResultTableParser()
    parser.feed(html)
    return [row for row in parser.rows if len(row) >= 8 and row[0].isdigit()]


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for year in args.years:
        for row in fetch_rows(year, args.province, args.category, args.source_track):
            row_year, row_province, category, source_track, major_name, max_score, min_score, avg_score = row[:8]
            output.append(
                {
                    "year": row_year,
                    "province": row_province,
                    "track": args.track,
                    "batch": args.batch,
                    "school_name": SCHOOL_NAME,
                    "school_code": args.school_code,
                    "major_group": "",
                    "major_name": major_name,
                    "plan_type": category,
                    "min_score": min_score,
                    "min_rank": "",
                    "admit_count": "",
                    "source_url": ENTRY_URL,
                    "source_name": SOURCE_NAME,
                    "notes": f"学校官网专业录取分数；官网科类={source_track}；最高分={max_score}；平均分={avg_score}",
                }
            )
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
    years = []
    for chunk in raw.replace("，", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            years.append(int(chunk))
    if not years:
        raise argparse.ArgumentTypeError("years cannot be empty")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SCUT official major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, help="Normalized target track, e.g. 物理类")
    parser.add_argument("--source-track", required=True, help="SCUT query track, e.g. 理工/物理类")
    parser.add_argument("--category", default="普通类")
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="")
    parser.add_argument("--years", type=parse_years, default=[2023, 2024, 2025])
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = normalized_rows(args)
    print("# 华南理工大学专业录取分数导入\n")
    print(f"- 来源：{ENTRY_URL}")
    print(f"- 范围：{args.province} / {args.track} / {args.category} / {', '.join(str(y) for y in args.years)}")
    print(f"- 获取专业记录：{len(rows)}")
    print(f"- 输出目录：{Path(args.data_dir).expanduser().resolve()}")
    if rows:
        print(f"- 预览：{rows[:3]}")
    if args.dry_run:
        print("- 模式：预览，不写入")
        return
    before, after = import_rows(args, rows)
    print(f"- 模式：写入；原记录 {before}，写入后 {after}")


if __name__ == "__main__":
    main()
