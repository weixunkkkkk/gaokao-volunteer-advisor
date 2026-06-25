#!/usr/bin/env python3
"""Import GPNU official Guangdong major-level admission scores."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from urllib.request import Request, urlopen

try:
    import pandas as pd
except ImportError:
    print(
        "This importer needs pandas. Run it with the bundled Python: "
        "python3",
        file=sys.stderr,
    )
    raise


SOURCE_NAME = "广东技术师范大学本科招生网"
SCHOOL_NAME = "广东技术师范大学"
BASE_URL = "https://bkzs.gpnu.edu.cn"
LIST_PAGE = f"{BASE_URL}/recruit?menuId=42&parentId=40"
DETAIL_API = f"{BASE_URL}/api/admission/api/distributionInfo"
DETAIL_PAGE = f"{BASE_URL}/listInfo?menuId=42&parentId=40&id={{article_id}}"


@dataclass(frozen=True)
class ArticleSpec:
    year: int
    article_id: int
    plan_type: str


ARTICLES = [
    ArticleSpec(2025, 4715, "普通类"),
    ArticleSpec(2025, 4713, "国际班"),
    ArticleSpec(2025, 4712, "地方专项"),
    ArticleSpec(2025, 4711, "少数民族"),
    ArticleSpec(2025, 4710, "教师专项"),
    ArticleSpec(2024, 4573, "普通类"),
    ArticleSpec(2024, 4572, "国际班"),
    ArticleSpec(2024, 4571, "地方专项"),
    ArticleSpec(2024, 4570, "少数民族"),
    ArticleSpec(2024, 4569, "教师专项"),
    ArticleSpec(2023, 3604, "普通类"),
    ArticleSpec(2023, 3602, "河源校区"),
    ArticleSpec(2023, 3598, "国际班"),
    ArticleSpec(2023, 3593, "协同培养"),
    ArticleSpec(2023, 3590, "少数民族"),
    ArticleSpec(2023, 3587, "农村教师专项"),
]

ART_EXCLUDE_KEYWORDS = ("美术", "音乐", "体育", "舞蹈", "艺术", "书法", "播音")

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


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return "" if text.lower() == "nan" else text.strip()


def digits(value: object) -> str:
    return re.sub(r"\D", "", clean(value))


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
    text = clean(value)
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        return ""
    number = float(text)
    return text if 300 <= number <= 750 else ""


def track_matches(args: argparse.Namespace, group_label: str, elective: str) -> bool:
    text = f"{group_label} {elective}"
    if any(keyword in text for keyword in ART_EXCLUDE_KEYWORDS):
        return False
    if args.track == "物理类":
        return "物理" in text
    return "历史" in text


def group_code(group_label: str) -> str:
    match = re.search(r"(\d{3})", group_label)
    return match.group(1) if match else ""


def first(row: pd.Series, names: tuple[str, ...]) -> str:
    for name in names:
        if name in row:
            value = clean(row[name])
            if value:
                return value
    return ""


def fetch_article(article_id: int) -> dict:
    url = f"{DETAIL_API}/{article_id}"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": LIST_PAGE})
    payload = json.loads(urlopen(request, timeout=60).read().decode("utf-8"))
    if payload.get("code") != 200:
        raise RuntimeError(f"GPNU API returned {payload.get('code')}: {payload.get('msg')}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise RuntimeError(f"GPNU API returned unexpected data for article {article_id}: {type(data)!r}")
    return data


def article_url(article_id: int) -> str:
    return DETAIL_PAGE.format(article_id=article_id)


def make_row(
    args: argparse.Namespace,
    spec: ArticleSpec,
    title: str,
    record: pd.Series,
) -> dict[str, str] | None:
    group_label = first(record, ("专业组名称", "院校专业组名称", "专业组"))
    elective = first(record, ("选考科目",))
    if not track_matches(args, group_label, elective):
        return None

    major_name = first(record, ("专业名称",)).replace(" ", "")
    major_code = digits(first(record, ("专业代码", "专业代号")))
    min_score = score_text(first(record, ("最低分",)))
    min_rank = rank_text(first(record, ("最低排位",)))
    if not major_name or major_name == "合计" or not min_score or not min_rank:
        return None

    source_url = article_url(spec.article_id)
    high_score = score_text(first(record, ("最高分",)))
    average = average_text(first(record, ("平均分",)))
    remark = first(record, ("备注",))
    notes = [
        "学校官网招生专业录取情况统计表导入",
        f"官网文章={title}",
        f"文章ID={spec.article_id}",
        f"专业组={group_label}" if group_label else "",
        f"选考科目={elective}" if elective else "",
        f"专业代码={major_code}" if major_code else "",
        f"最高分={high_score}" if high_score else "",
        f"平均分={average}" if average else "",
        remark,
        "只导入物理/历史本科专业行；艺体类行已排除",
    ]
    return {
        "year": str(spec.year),
        "province": args.province,
        "track": args.track,
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": group_code(group_label),
        "major_name": major_name,
        "plan_type": spec.plan_type,
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": digits(first(record, ("录取数",))),
        "source_url": source_url,
        "source_name": SOURCE_NAME,
        "notes": "；".join(part for part in notes if part),
    }


def parse_article(args: argparse.Namespace, spec: ArticleSpec) -> list[dict[str, str]]:
    data = fetch_article(spec.article_id)
    title = clean(data.get("title"))
    content = clean(data.get("content"))
    if not content:
        raise RuntimeError(f"GPNU article {spec.article_id} has no content")
    rows: list[dict[str, str]] = []
    for frame in pd.read_html(StringIO(content), header=0):
        frame.columns = [clean(column) for column in frame.columns]
        for _, record in frame.fillna("").iterrows():
            row = make_row(args, spec, title, record)
            if row:
                rows.append(row)
    return rows


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    selected_years = set(args.years)
    for spec in ARTICLES:
        if spec.year not in selected_years:
            continue
        rows.extend(parse_article(args, spec))
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (
            row["year"],
            row["track"],
            row["major_group"],
            row["major_name"],
            row["plan_type"],
            row["min_score"],
            row["min_rank"],
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
                clean(row.get("source_name")) == SOURCE_NAME
                and clean(row.get("school_name")) == SCHOOL_NAME
                and clean(row.get("province")) == args.province
                and clean(row.get("track")) == args.track
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"GPNU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GPNU official Guangdong major-level scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="10588")
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
    print("# 广东技术师范大学专业录取分数导入\n")
    print(f"- 来源：{LIST_PAGE}")
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
