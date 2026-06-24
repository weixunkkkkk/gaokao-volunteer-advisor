#!/usr/bin/env python3
"""Import SMU official major-level admission scores for Guangdong.

Source: 南方医科大学本科招生网 “往年分数” openapp query component.
The official query returns province, year, track, plan type, major, subject
requirements, minimum score, average score, highest score, and control line.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = "https://portal.smu.edu.cn/bkzs/bkzn/wnfs.htm"
QUERY_URL = "https://portal.smu.edu.cn/aop_component//webber/formquery//data/get/info"
SOURCE_NAME = "南方医科大学本科招生网"
SCHOOL_NAME = "南方医科大学"
OWNER = "1322328145"
TEMPLATE_CODE = "Form-1682646893042-8980"
FIELD_PROVINCE = "Item-1682646893546-4802"
FIELD_YEAR = "Item-1682646893546-4308"
FIELD_TRACK = "Item-1682646893546-6882"
FIELD_TYPE = "Item-1682646893546-9988"
FIELD_MAJOR = "Item-1682646893546-3863"
FIELD_SUBJECTS = "Item-1682646893546-5310"
FIELD_MIN = "Item-1682646893546-8946"
FIELD_AVG = "Item-1682646893546-9018"
FIELD_MAX = "Item-1682646893546-169"
FIELD_CONTROL = "Item-1682646893546-5394"
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


def fetch_year(year: int, province: str) -> list[dict[str, object]]:
    body = {
        "owner": OWNER,
        "randomCode": "",
        "randomKey": "",
        "datas": {
            FIELD_PROVINCE: province,
            FIELD_YEAR: str(year),
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
        raise RuntimeError(f"SMU query failed for {year}: {payload}")
    return payload.get("data", {}).get("dataList", [])


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for year in args.years:
        for raw in fetch_year(year, args.province):
            province = field(raw, FIELD_PROVINCE)
            row_year = field(raw, FIELD_YEAR)
            track = field(raw, FIELD_TRACK)
            plan_type = field(raw, FIELD_TYPE)
            major_name = field(raw, FIELD_MAJOR)
            subjects = field(raw, FIELD_SUBJECTS)
            min_score = field(raw, FIELD_MIN)
            avg_score = field(raw, FIELD_AVG)
            max_score = field(raw, FIELD_MAX)
            control_line = field(raw, FIELD_CONTROL)
            if province != args.province or track != args.track:
                continue
            if row_year != str(year) or not major_name or not re.fullmatch(r"\d+", min_score):
                continue
            notes = [
                "学校官网专业录取分数",
                f"选考科目={subjects}" if subjects else "",
                f"最高分={max_score}" if max_score else "",
                f"平均分={avg_score}" if avg_score else "",
                f"控制线={control_line}" if control_line else "",
            ]
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
                    "plan_type": plan_type,
                    "min_score": min_score,
                    "min_rank": "",
                    "admit_count": "",
                    "source_url": SOURCE_URL,
                    "source_name": SOURCE_NAME,
                    "notes": "；".join(part for part in notes if part),
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
    parser = argparse.ArgumentParser(description="Import SMU official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, help="Normalized target track, e.g. 物理类")
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
    print("# 南方医科大学专业录取分数导入\n")
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
