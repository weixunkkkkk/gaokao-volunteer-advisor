#!/usr/bin/env python3
"""Import Hanshan Normal University official Guangdong major scores."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from io import StringIO
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print(
        "This importer needs pandas. Run it with the bundled Python: "
        "/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
        file=sys.stderr,
    )
    raise


SOURCE_NAME = "韩山师范学院招生办"
SCHOOL_NAME = "韩山师范学院"
SCHOOL_CODE = "10578"
CACHE_DIR = Path("assets/raw-cache/hstc")
SOURCES = {
    (2025, "undergrad"): {
        "cache": "2025_undergrad.html",
        "url": "https://zsb.hstc.edu.cn/info/1023/2690.htm",
        "title": "韩山师范学院2025年夏季高考本科批次各专业录取分数统计表",
        "notes": "学校官网HTML表格导入；本科批",
    },
    (2025, "teacher"): {
        "cache": "2025_teacher.html",
        "url": "https://zsb.hstc.edu.cn/info/1023/2687.htm",
        "title": "韩山师范学院2025年提前批次教师专项各专业录取分数线统计表",
        "notes": "学校官网HTML表格导入；提前批次教师专项",
    },
    (2024, "undergrad"): {
        "cache": "2024_undergrad.html",
        "url": "https://zsb.hstc.edu.cn/info/1023/2647.htm",
        "title": "韩山师范学院2024年夏季高考本科批次各专业录取分数统计表",
        "notes": "学校官网HTML表格导入；本科批；官网列表未定位到2024教师专项统计表",
    },
    (2023, "undergrad"): {
        "cache": "2023_undergrad.html",
        "url": "https://zsb.hstc.edu.cn/info/1023/2292.htm",
        "title": "韩山师范学院2023年夏季高考本科批次各专业录取分数统计表",
        "notes": "学校官网HTML表格导入；本科批",
    },
    (2023, "teacher"): {
        "cache": "2023_teacher.html",
        "url": "https://zsb.hstc.edu.cn/info/1023/2297.htm",
        "title": "韩山师范学院2023年提前批次教师专项各专业录取分数线统计表",
        "notes": "学校官网HTML表格导入；提前批次教师专项",
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
    if pd.isna(value):
        return ""
    return str(value).strip()


def clean_text(value: object) -> str:
    text = norm(value).replace("\u3000", " ")
    text = re.sub(r"\s+", "", text)
    text = text.replace("(", "（").replace(")", "）")
    if text.count("（") > text.count("）"):
        text += "）"
    return text


def int_text(value: object) -> str:
    return re.sub(r"\D", "", norm(value).replace(",", ""))


def score_text(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 100 <= number <= 750 else ""


def rank_text(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 1 <= number <= 500000 else ""


def avg_text(value: object) -> str:
    text = norm(value)
    match = re.search(r"\d+(?:\.\d+)?", text)
    return match.group(0) if match else ""


def target_track(category: str) -> str:
    text = clean_text(category)
    if "历史" in text:
        return "历史类"
    if "物理" in text:
        return "物理类"
    return ""


def plan_type(source_kind: str, major_name: str) -> str:
    if source_kind == "teacher":
        return "教师专项"
    if "协同培养" in major_name or "4+0" in major_name:
        return "协同培养"
    if "中外" in major_name or "联合培养" in major_name:
        return "中外合作"
    return "普通类"


def read_source_table(cache_path: Path) -> pd.DataFrame:
    if not cache_path.exists():
        raise FileNotFoundError(f"Missing cached official page: {cache_path}")
    html = cache_path.read_text(encoding="utf-8")
    tables = pd.read_html(StringIO(html))
    if len(tables) < 2:
        raise RuntimeError(f"No admission table found in {cache_path}")
    table = tables[1].copy()
    if table.empty:
        raise RuntimeError(f"Empty admission table in {cache_path}")
    table.columns = [clean_text(column) for column in table.iloc[0]]
    table = table.iloc[1:].copy()
    first_col = table.columns[0]
    table[first_col] = table[first_col].ffill()
    return table


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for (year, kind), meta in SOURCES.items():
        if year not in args.years:
            continue
        cache_path = CACHE_DIR / str(meta["cache"])
        table = read_source_table(cache_path)
        category_col = table.columns[0]
        major_col = table.columns[1]
        for _, item in table.iterrows():
            track = target_track(norm(item.get(category_col)))
            if track != args.track:
                continue
            major_name = clean_text(item.get(major_col))
            if not major_name:
                continue
            if any(word in major_name for word in ["体育", "美术", "音乐", "书法", "舞蹈"]):
                continue
            min_score = score_text(item.get("最低分"))
            min_rank = rank_text(item.get("最低排位"))
            if not min_score:
                continue
            rows.append(
                {
                    "year": str(year),
                    "province": args.province,
                    "track": args.track,
                    "batch": args.batch,
                    "school_name": SCHOOL_NAME,
                    "school_code": args.school_code,
                    "major_group": "",
                    "major_name": major_name,
                    "plan_type": plan_type(kind, major_name),
                    "min_score": min_score,
                    "min_rank": min_rank,
                    "admit_count": "",
                    "source_url": str(meta["url"]),
                    "source_name": SOURCE_NAME,
                    "notes": "；".join(
                        part
                        for part in [
                            str(meta["notes"]),
                            f"最高分={score_text(item.get('最高分'))}" if score_text(item.get("最高分")) else "",
                            f"平均分={avg_text(item.get('平均分'))}" if avg_text(item.get("平均分")) else "",
                            f"缓存原文={cache_path}",
                        ]
                        if part
                    ),
                }
            )
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["major_name"], row["plan_type"], row["min_score"], row["min_rank"])
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
        raise argparse.ArgumentTypeError(f"HSTC importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Hanshan Normal University official Guangdong major scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default=SCHOOL_CODE)
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
    print("# 韩山师范学院专业录取分数导入\n")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(year) for year in args.years)}")
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
