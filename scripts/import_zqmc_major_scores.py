#!/usr/bin/env python3
"""Import Zhaoqing Medical College official Guangdong undergraduate scores."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAME = "肇庆医学院招生信息网"
SCHOOL_NAME = "肇庆医学院"
SCHOOL_CODE = "13810"
AGGREGATOR_SOURCE = "掌上高考（聚合补充）"

SOURCE_PAGES = {
    2024: {
        "url": "https://zhaosheng.zqmc.edu.cn/info/1213/1864.htm",
        "title": "肇庆医学院2024年普通本科批投档录取情况",
        "artifact": "assets/raw-cache/zqmc/2024-admission-final.png",
    },
    2025: {
        "url": "https://zhaosheng.zqmc.edu.cn/info/1223/1933.htm",
        "title": "2025年广东省本科批录取情况",
        "artifact": "assets/raw-cache/zqmc/2025-admission-final.png",
    },
}

RAW_ROWS = [
    # year, track, group, major_code, major, plan_count, admit_count, high, min, avg, min_rank
    (2024, "物理类", "201", "001", "药学", 375, 410, 533, 490, "495.7", 165245),
    (2024, "物理类", "201", "002", "护理学", 275, 240, 527, 490, "496.2", 165744),
    (2024, "历史类", "202", "003", "护理学", 100, 100, 511, 447, "472.3", 78371),
    (2025, "物理类", "201", "003", "临床医学", 210, 210, 561, 530, "537.6", 111609),
    (2025, "物理类", "202", "001", "药学", 237, 237, 530, 499, "504.8", 166558),
    (2025, "物理类", "202", "005", "食品卫生与营养学", 124, 123, 529, 497, "498.8", 169391),
    (2025, "物理类", "202", "008", "中药学", 124, 124, 522, 497, "502.1", 169384),
    (2025, "物理类", "203", "004", "康复治疗学", 123, 123, 528, 499, "505.2", 165668),
    (2025, "物理类", "203", "006", "医学影像技术", 124, 124, 530, 499, "505.2", 165670),
    (2025, "物理类", "203", "007", "口腔医学技术", 123, 123, 530, 501, "507", 162099),
    (2025, "物理类", "204", "002", "护理学", 307, 307, 532, 496, "501.8", 172953),
    (2025, "历史类", "205", "009", "护理学", 20, 20, 520, 507, "514", 52014),
]

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


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year, track, group, code, major, plan, count, high, score, avg, rank in RAW_ROWS:
        if year not in args.years or track != args.track:
            continue
        page = SOURCE_PAGES[year]
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": SCHOOL_CODE,
                "major_group": group,
                "major_name": major,
                "plan_type": "普通类",
                "min_score": str(score),
                "min_rank": str(rank),
                "admit_count": str(count),
                "source_url": page["url"],
                "source_name": SOURCE_NAME,
                "notes": (
                    f"{page['title']}官网图片表；专业代码={code}；计划数={plan}；"
                    f"最高分={high}；平均分={avg}；原始缓存={page['artifact']}"
                ),
            }
        )
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
    parser = argparse.ArgumentParser(description="Import Zhaoqing Medical College official Guangdong major scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--years", type=parse_years, default=[2024, 2025])
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = normalized_rows(args)
    by_year = Counter(row["year"] for row in rows)
    print("# 肇庆医学院本科专业录取分数导入\n")
    print(f"- 来源：{SOURCE_NAME}")
    print(f"- 范围：{args.province} / {args.track} / {','.join(map(str, args.years))}")
    print(f"- 获取专业记录：{len(rows)}；年份分布：{dict(sorted(by_year.items()))}")
    if rows:
        print(f"- 预览：{rows[:5]}")
    if args.dry_run:
        print("- 模式：预览，不写入")
        return
    before, removed, after = import_rows(args, rows)
    print(f"- 模式：写入；原记录 {before}，替换聚合/旧官网专业行 {removed}，写入后 {after}")


if __name__ == "__main__":
    main()
