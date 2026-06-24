#!/usr/bin/env python3
"""Export Gaokao.cn school IDs for later province-level score imports."""

from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHOOL_CODE_URL = "https://static-data.gaokao.cn/www/2.0/school/school_code.json?a=www.gaokao.cn"
DEFAULT_OUTPUT = ROOT / "assets" / "source-discovery" / "national" / "gaokao_cn_school_ids.csv"


def fetch_school_ids() -> list[dict[str, str]]:
    request = urllib.request.Request(
        SCHOOL_CODE_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.gaokao.cn/",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        raise SystemExit("掌上高考学校ID接口返回格式异常")

    rows: list[dict[str, str]] = []
    for source_code, item in data.items():
        if not isinstance(item, dict):
            continue
        school_id = str(item.get("school_id") or "").strip()
        school_name = str(item.get("name") or "").strip()
        if school_id and school_name:
            rows.append(
                {
                    "source_code": str(source_code).strip(),
                    "school_id": school_id,
                    "school_name": school_name,
                    "source_url": SCHOOL_CODE_URL,
                }
            )
    rows.sort(key=lambda row: (row["school_name"], row["school_id"], row["source_code"]))
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Gaokao.cn school IDs to CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = fetch_school_ids()
    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["source_code", "school_id", "school_name", "source_url"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Exported {len(rows)} school IDs to {output}")


if __name__ == "__main__":
    main()
