#!/usr/bin/env python3
"""Import STU official major-level admission scores for Guangdong."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_NAME = "汕头大学本科招生网"
SCHOOL_NAME = "汕头大学"
PAGE_URL = "https://zs.stu.edu.cn/bkzn/lnfs.htm"
JSON_URL = "https://zs.stu.edu.cn/json/{year}.txt"

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


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def score_text(value: object) -> str:
    if value is None or value == "":
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return str(int(number)) if number.is_integer() else str(number)


def year_text(value: object) -> str:
    match = re.search(r"\d{4}", norm(value))
    return match.group(0) if match else ""


def plan_type(value: object) -> str:
    text = norm(value)
    if "地方专项" in text:
        return "地方专项"
    if "卫生专项" in text:
        return "卫生专项"
    if text:
        return text
    return "普通类"


def fetch_year(year: int) -> list[dict[str, object]]:
    url = JSON_URL.format(year=year)
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": PAGE_URL})
    text = urlopen(request, timeout=60).read().decode("utf-8-sig", "replace")
    data = json.loads(text)
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected STU JSON payload for {year}: {type(data)!r}")
    return [row for row in data if isinstance(row, dict)]


def row_to_admission(args: argparse.Namespace, row: dict[str, object], year: int) -> dict[str, str] | None:
    if norm(row.get("省份")) != args.province:
        return None
    if norm(row.get("科类")) != args.track:
        return None
    major_name = norm(row.get("专业"))
    min_score = score_text(row.get("最低分"))
    if not (major_name and min_score):
        return None
    max_score = score_text(row.get("最高分"))
    avg_score = score_text(row.get("平均分"))
    remark = norm(row.get("备注"))
    json_url = JSON_URL.format(year=year)
    return {
        "year": year_text(row.get("年份")) or str(year),
        "province": args.province,
        "track": args.track,
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": "",
        "major_name": major_name,
        "plan_type": plan_type(remark),
        "min_score": min_score,
        "min_rank": "",
        "admit_count": score_text(row.get("录取人数")),
        "source_url": PAGE_URL,
        "source_name": SOURCE_NAME,
        "notes": "；".join(
            part
            for part in [
                "学校官网JSON专业录取分数",
                f"JSON={json_url}",
                f"最高分={max_score}" if max_score else "",
                f"平均分={avg_score}" if avg_score else "",
                f"备注={remark}" if remark else "",
                "min_rank由同年广东一分一段表按最低分补齐",
            ]
            if part
        ),
    }


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in args.years:
        for item in fetch_year(year):
            row = row_to_admission(args, item, year)
            if row:
                rows.append(row)
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output = []
    for row in rows:
        key = (
            row["year"],
            row["track"],
            row["major_name"],
            row["plan_type"],
            row["min_score"],
            row["admit_count"],
        )
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
    years = []
    for chunk in raw.replace("，", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            years.append(int(chunk))
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"STU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import STU official Guangdong major-level admission scores.")
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

    print("# 汕头大学专业录取分数导入\n")
    print(f"- 来源：{PAGE_URL}")
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
