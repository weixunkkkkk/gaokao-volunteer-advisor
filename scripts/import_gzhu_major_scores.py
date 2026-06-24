#!/usr/bin/env python3
"""Import GZHU official major-level admission scores for Guangdong.

Source: 广州大学本科招生网 “历年分数” openapp query component.
The official query returns province, year, track, category, major, minimum
score, and minimum rank.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_URL = "https://zsjy.gzhu.edu.cn/bkzn/lnfs2.htm"
QUERY_URL = "https://zsjy.gzhu.edu.cn/aop_component//webber/formquery//data/get/info"
SOURCE_NAME = "广州大学本科招生网"
SCHOOL_NAME = "广州大学"
OWNER = "1438330108"
TEMPLATE_CODE = "Form-1746001468578-9846"
FIELD_PROVINCE = "Item-1746001468596-3612"
FIELD_YEAR = "Item-1746001468596-3907"
FIELD_TRACK = "Item-1746001468596-6833"
FIELD_TYPE = "Item-1746001468596-5295"
FIELD_MAJOR = "Item-1746001468596-573"
FIELD_MIN = "Item-1746001468596-6985"
FIELD_RANK = "Item-1746001468596-8359"
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


def field(row: dict[str, object], key: str) -> str:
    return norm(row.get(f"{key}-value"))


def normalize_plan_type(value: str) -> str:
    mapping = {
        "普通文理": "普通类",
        "国际班": "国际班",
        "地方专项": "地方专项",
        "教师专项": "教师专项",
        "中外合作办学": "中外合作办学",
    }
    return mapping.get(value, value or "普通类")


def fetch_year(year: int, province: str) -> list[dict[str, object]]:
    year_value = f"{year}年"
    body = {
        "owner": OWNER,
        "randomCode": "",
        "randomKey": "",
        "datas": {
            FIELD_PROVINCE: province,
            FIELD_YEAR: year_value,
            FIELD_TRACK: "",
            FIELD_TYPE: "",
        },
        "templateCode": TEMPLATE_CODE,
        "current": 1,
        "size": 10000,
        "pageCode": "",
        "ifRandomCode": True,
    }
    request = Request(
        QUERY_URL,
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/json",
            "Authorization": "tourist",
            "owner": OWNER,
            "Referer": SOURCE_URL,
        },
    )
    raw = urlopen(request, timeout=30).read().decode("utf-8", "replace")
    payload = json.loads(raw)
    if payload.get("code") != "0000":
        raise RuntimeError(f"GZHU query failed for {year}: {payload}")
    return payload.get("data", {}).get("dataList", [])


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for year in args.years:
        for raw in fetch_year(year, args.province):
            province = field(raw, FIELD_PROVINCE)
            row_year = field(raw, FIELD_YEAR).replace("年", "")
            track = field(raw, FIELD_TRACK)
            source_type = field(raw, FIELD_TYPE)
            major_name = field(raw, FIELD_MAJOR)
            min_score = field(raw, FIELD_MIN)
            min_rank = field(raw, FIELD_RANK)
            if province != args.province or row_year != str(year) or track != args.track:
                continue
            if not major_name or not re.fullmatch(r"\d+", min_score):
                continue
            output.append(
                {
                    "year": row_year,
                    "province": province,
                    "track": track,
                    "batch": args.batch,
                    "school_name": SCHOOL_NAME,
                    "school_code": args.school_code,
                    "major_group": "",
                    "major_name": major_name,
                    "plan_type": normalize_plan_type(source_type),
                    "min_score": min_score,
                    "min_rank": min_rank,
                    "admit_count": "",
                    "source_url": SOURCE_URL,
                    "source_name": SOURCE_NAME,
                    "notes": f"学校官网专业录取分数；官网类别={source_type}",
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
    parser = argparse.ArgumentParser(description="Import GZHU official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True)
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
    print("# 广州大学专业录取分数导入\n")
    print(f"- 来源：{SOURCE_URL}")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(y) for y in args.years)}")
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
