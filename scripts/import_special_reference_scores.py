#!/usr/bin/env python3
"""Import Workbuddy supplemental special-school major rows.

These rows are supplemental records from the Workbuddy special-school reference.
Official sources remain preferred; aggregator fallback rows are explicitly marked
as pending official re-check in `notes`.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


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

IMPORTER_SOURCE = "references/special-schools-inventory.md"
SUPPLEMENTAL_NOTE = f"Workbuddy补充清单={IMPORTER_SOURCE}；聚合站/官网汇总来源，待官方复核"

GDPPLA_URLS = {
    2025: ("广东警官学院招生网（Workbuddy补充）", "https://zsb.gdppla.edu.cn/info/1002/1839.htm"),
    2024: ("广东警官学院招生网（Workbuddy补充）", "https://zsb.gdppla.edu.cn/info/1005/1579.htm"),
    2023: ("聚合站dxsbb（Workbuddy补充）", "https://www.dxsbb.com/"),
}

XHCOM_SOURCE = ("星海音乐学院招生网（Workbuddy补充）", "https://zs.xhcom.edu.cn/index/lnfsx.htm")

RAW_ROWS = [
    ("广东警官学院", "11110", 2025, "物理类", "201", "法学", 548, 83635),
    ("广东警官学院", "11110", 2025, "物理类", "201", "社会工作", 545, 88034),
    ("广东警官学院", "11110", 2025, "物理类", "201", "行政管理", 545, 88040),
    ("广东警官学院", "11110", 2025, "历史类", "202", "法学", 558, 19864),
    ("广东警官学院", "11110", 2025, "历史类", "202", "社会工作", 556, 20914),
    ("广东警官学院", "11110", 2025, "历史类", "202", "行政管理", 556, 20953),
    ("广东警官学院", "11110", 2024, "物理类", "201", "法学", 548, 72888),
    ("广东警官学院", "11110", 2024, "物理类", "201", "社会工作", 544, 86985),
    ("广东警官学院", "11110", 2024, "物理类", "201", "行政管理", 544, 87275),
    ("广东警官学院", "11110", 2024, "历史类", "202", "法学", 538, 19359),
    ("广东警官学院", "11110", 2024, "历史类", "202", "社会工作", 531, 22294),
    ("广东警官学院", "11110", 2024, "历史类", "202", "行政管理", 531, 22374),
    ("广东警官学院", "11110", 2023, "物理类", "201", "法学", 554, 84097),
    ("广东警官学院", "11110", 2023, "物理类", "201", "社会工作", 536, 91585),
    ("广东警官学院", "11110", 2023, "物理类", "203", "行政管理", 540, 87411),
    ("广东警官学院", "11110", 2023, "历史类", "202", "法学", 535, 21170),
    ("广东警官学院", "11110", 2023, "历史类", "202", "社会工作", 533, 22195),
    ("广东警官学院", "11110", 2023, "历史类", "204", "行政管理", 524, 26090),
    ("星海音乐学院", "10587", 2025, "历史类", "201", "艺术管理", 547, 25922),
    ("星海音乐学院", "10587", 2025, "物理类", "202", "艺术管理", 542, 92498),
    ("星海音乐学院", "10587", 2024, "历史类", "202", "艺术管理", 519, 28228),
    ("星海音乐学院", "10587", 2024, "物理类", "203", "艺术管理", 524, 108278),
    ("星海音乐学院", "10587", 2023, "历史类", "202", "艺术管理", 527, 24887),
    ("星海音乐学院", "10587", 2023, "物理类", "203", "艺术管理", 550, 75130),
]


def source_for(school: str, year: int) -> tuple[str, str]:
    if school == "广东警官学院":
        return GDPPLA_URLS[year]
    return XHCOM_SOURCE


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for school, code, year, track, group, major, score, rank in RAW_ROWS:
        if track != args.track or year not in args.years:
            continue
        source_name, source_url = source_for(school, year)
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": track,
                "batch": args.batch,
                "school_name": school,
                "school_code": code,
                "major_group": group,
                "major_name": major,
                "plan_type": "普通类",
                "min_score": str(score),
                "min_rank": str(rank),
                "admit_count": "",
                "source_url": source_url,
                "source_name": source_name,
                "notes": f"{SUPPLEMENTAL_NOTE}；普通本科批可比专业；公安提前批/术科/校考需单独采集",
            }
        )
    return rows


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ADMISSION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def same_scope(row: dict[str, str], args: argparse.Namespace) -> bool:
    return (
        row.get("province") == args.province
        and row.get("track") == args.track
        and row.get("source_name", "").endswith("（Workbuddy补充）")
        and row.get("school_name") in {"广东警官学院", "星海音乐学院"}
    )


def import_rows(args: argparse.Namespace, rows: list[dict[str, str]]) -> tuple[int, int]:
    path = Path(args.data_dir).expanduser().resolve() / "admission_records.csv"
    existing = read_existing(path)
    before = len(existing)
    if args.replace_existing:
        existing = [row for row in existing if not same_scope(row, args)]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"Unsupported years: {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Workbuddy supplemental special-school rows.")
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
    rows = normalized_rows(args)
    by_school: dict[str, int] = {}
    for row in rows:
        by_school[row["school_name"]] = by_school.get(row["school_name"], 0) + 1
    print(f"Prepared {len(rows)} {args.track} supplemental rows: {by_school}")
    if args.dry_run:
        for row in rows[:10]:
            print(row)
        return
    before, after = import_rows(args, rows)
    print(f"Imported {len(rows)} rows into {args.data_dir}/admission_records.csv ({before} -> {after})")


if __name__ == "__main__":
    main()
