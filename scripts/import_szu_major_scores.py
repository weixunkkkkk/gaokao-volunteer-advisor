#!/usr/bin/env python3
"""Import SZU official major-level admission scores for Guangdong.

Source: 深圳大学本科招生网广东录取数据 page. The current official page
publishes Guangdong major-level rows for 2024 and 2025, including ordinary
and local-special-plan sections.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://zs.szu.edu.cn/info/1153/2985.htm"
SOURCE_NAME = "深圳大学本科招生网"
SCHOOL_NAME = "深圳大学"
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


@dataclass
class RowContext:
    section_track: str = ""
    plan_type: str = ""
    group: str = ""
    college: str = ""


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def normalize_track(value: str) -> str:
    if "物理" in value:
        return "物理类"
    if "历史" in value:
        return "历史类"
    return value


def normalize_plan_type(section_plan_type: str, major_name: str, college: str) -> str:
    text = f"{major_name} {college}"
    if "中外合作" in text or "南特金融科技学院" in text:
        return "中外合作办学"
    return section_plan_type or "普通类"


def fetch_rows() -> list[list[str]]:
    request = Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(request, timeout=30).read().decode("utf-8", "replace")
    parser = TableParser()
    parser.feed(html)
    return parser.rows


def is_digits(value: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", norm(value)))


def is_metrics(values: list[str]) -> bool:
    return len(values) == 6 and is_digits(values[0]) and is_digits(values[3])


def split_row(row: list[str], context: RowContext) -> tuple[str, str, str, list[str], list[str]] | None:
    cells = [norm(cell) for cell in row]
    if not any(cells):
        return None
    if len(cells) == 15 and cells[0].isdigit():
        context.group = cells[0]
        context.college = cells[1]
        return context.group, context.college, cells[2], cells[3:9], cells[9:15]
    if len(cells) == 14 and cells[2].isdigit():
        context.college = cells[0]
        return context.group, context.college, cells[1], cells[2:8], cells[8:14]
    if len(cells) == 13 and cells[1].isdigit():
        return context.group, context.college, cells[0], cells[1:7], cells[7:13]
    return None


def output_row(
    *,
    year: int,
    target_track: str,
    batch: str,
    school_code: str,
    context: RowContext,
    group: str,
    college: str,
    major_name: str,
    metrics: list[str],
) -> dict[str, str] | None:
    if normalize_track(context.section_track) != target_track:
        return None
    if not is_metrics(metrics):
        return None
    admit_count, max_score, avg_score, min_score, avg_rank, min_rank = metrics
    plan_type = normalize_plan_type(context.plan_type, major_name, college)
    notes = [
        "学校官网专业录取分数",
        f"学院={college}" if college else "",
        f"最高分={max_score}" if max_score else "",
        f"平均分={avg_score}" if avg_score else "",
        f"平均排位={avg_rank}" if avg_rank else "",
    ]
    return {
        "year": str(year),
        "province": "广东",
        "track": target_track,
        "batch": batch,
        "school_name": SCHOOL_NAME,
        "school_code": school_code,
        "major_group": group,
        "major_name": major_name,
        "plan_type": plan_type,
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": admit_count,
        "source_url": SOURCE_URL,
        "source_name": SOURCE_NAME,
        "notes": "；".join(part for part in notes if part),
    }


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows = fetch_rows()
    context = RowContext()
    output: list[dict[str, str]] = []
    for row in rows:
        heading = row[0] if len(row) == 1 else ""
        if "深圳大学2024年-2025年广东省录取情况" in heading:
            context = RowContext(
                section_track=heading,
                plan_type="普通类",
            )
            continue
        if "深圳大学2025年广东省地方专项录取情况" in heading:
            context = RowContext(
                section_track=heading,
                plan_type="地方专项",
            )
            continue
        if not context.section_track:
            continue
        parsed = split_row(row, context)
        if not parsed:
            continue
        group, college, major_name, metrics_2025, metrics_2024 = parsed
        for year, metrics in ((2025, metrics_2025), (2024, metrics_2024)):
            if year not in args.years:
                continue
            normalized = output_row(
                year=year,
                target_track=args.track,
                batch=args.batch,
                school_code=args.school_code,
                context=context,
                group=group,
                college=college,
                major_name=major_name,
                metrics=metrics,
            )
            if normalized:
                output.append(normalized)
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
                and norm(row.get("province")) == "广东"
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
    unsupported = sorted(set(years) - {2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"SZU official page only has major-level 2024/2025 data, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SZU official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--track", required=True, help="Normalized target track, e.g. 物理类")
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="")
    parser.add_argument("--years", type=parse_years, default=[2024, 2025])
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
    print("# 深圳大学专业录取分数导入\n")
    print(f"- 来源：{SOURCE_URL}")
    print(f"- 范围：广东 / {args.track} / {', '.join(str(y) for y in args.years)}")
    print(f"- 获取专业记录：{len(rows)}；分年：{by_year}；类型：{by_plan}")
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
