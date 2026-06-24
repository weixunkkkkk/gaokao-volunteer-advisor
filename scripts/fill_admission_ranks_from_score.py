#!/usr/bin/env python3
"""Fill missing admission min_rank values by matching min_score to rank_table bands."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "assets" / "data"


def norm(value: str | None) -> str:
    return (value or "").strip()


def as_int(value: str | None) -> int | None:
    value = norm(value).replace(",", "")
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_score_bands(data_dir: Path, province: str, track: str) -> dict[tuple[int, int], int]:
    _, rows = read_csv(data_dir / "rank_table.csv")
    bands: dict[tuple[int, int], int] = {}
    for row in rows:
        if norm(row.get("province")) != province or norm(row.get("track")) != track:
            continue
        year = as_int(row.get("year"))
        score = as_int(row.get("score"))
        max_rank = as_int(row.get("max_rank"))
        if year is None or score is None or max_rank is None:
            continue
        bands[(year, score)] = max_rank
    return bands


def fill_ranks(data_dir: Path, province: str, track: str) -> dict[str, object]:
    path = data_dir / "admission_records.csv"
    fieldnames, rows = read_csv(path)
    bands = build_score_bands(data_dir, province, track)
    filled = 0
    unmatched = 0
    skipped_existing = 0
    selected = 0
    for row in rows:
        if norm(row.get("province")) != province or norm(row.get("track")) != track:
            continue
        selected += 1
        if norm(row.get("min_rank")):
            skipped_existing += 1
            continue
        year = as_int(row.get("year"))
        score = as_int(row.get("min_score"))
        if year is None or score is None:
            unmatched += 1
            continue
        rank = bands.get((year, score))
        if rank is None:
            unmatched += 1
            continue
        row["min_rank"] = str(rank)
        filled += 1
    return {
        "path": str(path),
        "province": province,
        "track": track,
        "selected_rows": selected,
        "filled_rows": filled,
        "skipped_existing_rank_rows": skipped_existing,
        "unmatched_rows": unmatched,
        "rows": rows,
        "fieldnames": fieldnames,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill missing admission min_rank values from rank_table.csv bands.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing admission_records.csv and rank_table.csv")
    parser.add_argument("--province", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dir = Path(args.data_dir).expanduser().resolve()
    result = fill_ranks(data_dir, args.province, args.track)
    rows = result.pop("rows")
    fieldnames = result.pop("fieldnames")
    result["dry_run"] = args.dry_run
    if not args.dry_run:
        write_csv(Path(result["path"]), fieldnames, rows)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("# 分数反推位次补全")
        print(f"- 文件：{result['path']}")
        print(f"- 范围：{result['province']} / {result['track']}")
        print(f"- 命中记录：{result['selected_rows']}")
        print(f"- 已补位次：{result['filled_rows']}")
        print(f"- 原本已有位次：{result['skipped_existing_rank_rows']}")
        print(f"- 未匹配分数：{result['unmatched_rows']}")
        print(f"- 模式：{'预览，不写入' if args.dry_run else '已写入'}")


if __name__ == "__main__":
    main()
