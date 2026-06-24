#!/usr/bin/env python3
"""Import GDUPT official Guangdong major scores from the school admission site."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SOURCE_NAME = "广东石油化工学院招生网"
SCHOOL_NAME = "广东石油化工学院"
RECRUIT_LINE_URL = "https://zs.gdupt.edu.cn/module/recruit_line.html"
API_URL = "https://zs.gdupt.edu.cn/zhaosheng_web/web_module/get_recruit_line_list"
ARTICLE_URLS = {
    2025: "https://zs.gdupt.edu.cn/module/news_info.html?article_id=19438",
    2024: "https://zs.gdupt.edu.cn/module/news_info.html?article_id=19399",
}
QUERY_TRACKS = {
    "物理类": {
        2025: "物理类",
        2024: "物理",
        2023: "理工",
    },
    "历史类": {
        2025: "历史类",
        2024: "历史",
        2023: "文史",
    },
}

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


def digits(value: object) -> str:
    return re.sub(r"\D", "", norm(value))


def score_text(value: object) -> str:
    text = digits(value)
    if not text:
        return ""
    number = int(text)
    return text if 300 <= number <= 750 else ""


def rank_text(value: object) -> str:
    text = digits(value)
    if not text:
        return ""
    number = int(text)
    return text if 1 <= number <= 500000 else ""


def average_text(value: object) -> str:
    text = norm(value)
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return ""
    number = float(text)
    return text if 300 <= number <= 750 else ""


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": RECRUIT_LINE_URL})
    return json.loads(urlopen(request, timeout=60).read().decode("utf-8"))


def fetch_rows(year: int, query_track: str, batch: str) -> list[dict]:
    params = {
        "year": str(year),
        "city": "广东",
        "type": query_track,
        "batch": batch,
    }
    payload = fetch_json(f"{API_URL}?{urlencode(params)}")
    if payload.get("code") != 1:
        raise RuntimeError(f"GDUPT API returned {payload.get('code')}: {payload.get('msg')}")
    data = payload.get("data")
    if not isinstance(data, list):
        raise RuntimeError(f"GDUPT API returned unexpected data for {params}: {type(data)!r}")
    return data


def make_row(args: argparse.Namespace, item: dict, year: int, query_track: str) -> dict[str, str] | None:
    major_name = norm(item.get("group")).replace(" ", "")
    min_score = score_text(item.get("line_min"))
    min_rank = rank_text(item.get("min_ranking"))
    if not major_name or not min_score or not min_rank:
        return None
    high_score = score_text(item.get("line_max"))
    average = average_text(item.get("line_c"))
    source_url = ARTICLE_URLS.get(year, RECRUIT_LINE_URL)
    notes = [
        "学校招生网历年录取分数线接口导入",
        f"接口科类={query_track}",
        f"录取最高分={high_score}" if high_score else "",
        f"平均分={average}" if average else "",
        f"line_id={norm(item.get('line_id'))}" if norm(item.get("line_id")) else "",
        "2025/2024官网详情页登记官微原文，recruit_line接口提供结构化表格"
        if year in ARTICLE_URLS
        else "官网历年录取分数线模块提供结构化表格",
    ]
    return {
        "year": str(year),
        "province": args.province,
        "track": args.track,
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": "",
        "major_name": major_name,
        "plan_type": "普通类",
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": digits(item.get("line")),
        "source_url": source_url,
        "source_name": SOURCE_NAME,
        "notes": "；".join(part for part in notes if part),
    }


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    track_map = QUERY_TRACKS[args.track]
    for year in args.years:
        query_track = track_map[year]
        for item in fetch_rows(year, query_track, args.batch):
            row = make_row(args, item, year, query_track)
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
                norm(row.get("source_name")) == SOURCE_NAME
                and norm(row.get("school_name")) == SCHOOL_NAME
                and norm(row.get("province")) == args.province
                and norm(row.get("track")) == args.track
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"GDUPT importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GDUPT official Guangdong major-level scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="11656")
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
    print("# 广东石油化工学院专业录取分数导入\n")
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
