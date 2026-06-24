#!/usr/bin/env python3
"""Import SYSU official major-level admission scores for Guangdong."""

from __future__ import annotations

import argparse
import csv
import json
import time
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener


BASE_URL = "https://admission.sysu.edu.cn/"
PAGE_URL = "https://admission.sysu.edu.cn/zsw/lnfs.html"
API_URL = "https://admission.sysu.edu.cn/f/ajax_lnfs"
SOURCE_NAME = "中山大学本科招生网"
SCHOOL_NAME = "中山大学"
PLAN_TYPES = ["普通录取", "高校专项"]

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


@dataclass
class SysuClient:
    tokens: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self.opener.open(Request(PAGE_URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read()

    def request_json(self, path: str, data: dict[str, object], token: str | None = None) -> tuple[dict[str, object], str]:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": PAGE_URL,
            "X-Requested-With": "XMLHttpRequest",
            "X-Requested-Time": str(int(time.time() * 1000)),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        if token:
            headers["Csrf-Token"] = token
        response = self.opener.open(
            Request(
                BASE_URL + path + "?ts=" + str(int(time.time() * 1000)),
                data=urlencode(data).encode(),
                headers=headers,
                method="POST",
            ),
            timeout=30,
        )
        return json.loads(response.read().decode("utf-8", "replace")), response.headers.get("Csrf-Token") or ""

    def ensure_tokens(self) -> None:
        if self.tokens:
            return
        payload, _ = self.request_json("f/ajax_get_csrfToken", {"n": 3})
        if payload.get("state") != 1:
            raise RuntimeError(f"failed to get SYSU CSRF token: {payload}")
        self.tokens.extend(str(payload.get("data", "")).split(","))

    def post(self, path: str, data: dict[str, object]) -> dict[str, object]:
        last_error: Exception | None = None
        for _ in range(4):
            try:
                self.ensure_tokens()
                payload, next_token = self.request_json(path, data, self.tokens.pop(0))
                if next_token:
                    self.tokens.append(next_token)
                if payload.get("state") == 1:
                    return payload
                last_error = RuntimeError(str(payload))
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
                last_error = exc
                self.tokens.clear()
                time.sleep(1.2)
        raise RuntimeError(f"SYSU request failed after retries: {last_error}")


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


def plan_type(raw: str) -> str:
    if raw == "普通录取":
        return "普通类"
    if raw == "高校专项":
        return "高校专项"
    return raw


def row_to_admission(row: dict[str, object], *, batch: str, school_code: str, query_plan_type: str) -> dict[str, str] | None:
    major_name = norm(row.get("zymc"))
    year = norm(row.get("nf"))
    track = norm(row.get("klmc"))
    min_score = score_text(row.get("minScore"))
    min_rank = score_text(row.get("minRank") or row.get("minOrder"))
    max_score = score_text(row.get("maxScore"))
    if not (major_name and year and track and min_score and min_rank):
        return None
    return {
        "year": year,
        "province": "广东",
        "track": track,
        "batch": batch,
        "school_name": SCHOOL_NAME,
        "school_code": norm(row.get("schcode")) or school_code,
        "major_group": "",
        "major_name": major_name,
        "plan_type": plan_type(query_plan_type),
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": score_text(row.get("rs")),
        "source_url": PAGE_URL,
        "source_name": SOURCE_NAME,
        "notes": "；".join(
            part
            for part in [
                "学校官网招生系统专业录取分数",
                f"接口={API_URL}",
                f"招生类型={query_plan_type}",
                f"最高分={max_score}" if max_score else "",
                f"平均分={score_text(row.get('avgScore'))}" if score_text(row.get("avgScore")) else "",
            ]
            if part
        ),
    }


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output = []
    for row in rows:
        key = (row["year"], row["track"], row["major_name"], row["plan_type"], row["min_score"], row["min_rank"])
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    client = SysuClient()
    rows: list[dict[str, str]] = []
    target_years = {str(year) for year in args.years}
    query_year = max(args.years)
    for query_plan_type in args.plan_types:
        payload = client.post(
            "f/ajax_lnfs",
            {"ssmc": args.province, "nf": str(query_year), "klmc": args.track, "zslx": query_plan_type},
        )
        for item in ((payload.get("data") or {}).get("sszygradeList") or []):
            if not isinstance(item, dict):
                continue
            if norm(item.get("nf")) not in target_years:
                continue
            if norm(item.get("ssmc")) != args.province or norm(item.get("klmc")) != args.track:
                continue
            row = row_to_admission(item, batch=args.batch, school_code=args.school_code, query_plan_type=query_plan_type)
            if row:
                rows.append(row)
    return dedupe_rows(rows)


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
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"SYSU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_plan_types(raw: str) -> list[str]:
    values = [chunk.strip() for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(values) - set(PLAN_TYPES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"unsupported SYSU plan types: {unsupported}")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import SYSU official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="10558")
    parser.add_argument("--years", type=parse_years, default=[2023, 2024, 2025])
    parser.add_argument("--plan-types", type=parse_plan_types, default=PLAN_TYPES)
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
    print("# 中山大学专业录取分数导入\n")
    print(f"- 来源：{PAGE_URL}")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(y) for y in args.years)}")
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
