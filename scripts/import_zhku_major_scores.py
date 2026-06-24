#!/usr/bin/env python3
"""Import ZHKU official Guangdong major scores from the school-site Excel table."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd


SOURCE_NAME = "仲恺农业工程学院本科招生网"
SCHOOL_NAME = "仲恺农业工程学院"
SCHOOL_CODE = "11347"
SOURCE_URL = "https://zsb-portal.zhku.edu.cn/details/article?id=675793"
ATTACHMENT_URL = "https://study-cdn-img.jobpi.cn/upload/cc10d94812d8d2c9c656c30fea0cf347/2026-05-20/17792615198147.xls"
SOURCE_TITLE = "仲恺农业工程学院2023-2025年本科招生录取情况（广东省）"
RAW_XLS = "assets/raw-cache/zhku/2023_2025_guangdong_major_scores.xls"
XLSX = "assets/raw-cache/zhku/converted/2023_2025_guangdong_major_scores.xlsx"
SHEET_NAME = "2023-2025"

TRACK_COLUMNS = {
    "物理类": {
        2023: (2, 3, 4),
        2024: (8, 9, 10),
        2025: (14, 15, 16),
    },
    "历史类": {
        2023: (5, 6, 7),
        2024: (11, 12, 13),
        2025: (17, 18, 19),
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
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip().replace("\u3000", "")
    text = text.replace("(", "（").replace(")", "）")
    text = re.sub(r"\s+", "", text)
    return "" if text.lower() == "nan" else text


def numeric_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else ""
    text = norm(value).replace(",", "")
    if re.fullmatch(r"\d+(?:\.0+)?", text):
        return str(int(float(text)))
    return ""


def score_text(value: object) -> str:
    text = numeric_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 100 <= number <= 750 else ""


def rank_text(value: object) -> str:
    text = numeric_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 1 <= number <= 500000 else ""


def plan_type(major_name: str) -> str:
    if "国际班" in major_name:
        return "国际班"
    if "中外" in major_name or "联合培养" in major_name:
        return "中外合作"
    return "普通类"


def ensure_xlsx() -> Path:
    xlsx = Path(XLSX)
    if xlsx.exists():
        return xlsx
    xls = Path(RAW_XLS)
    if not xls.exists():
        raise FileNotFoundError(f"Missing official Excel attachment cache: {xls}")
    soffice = shutil.which("soffice") or ("/opt/homebrew/bin/soffice" if Path("/opt/homebrew/bin/soffice").exists() else "")
    if not soffice:
        raise RuntimeError(f"{xls} is .xls and needs soffice conversion; cached xlsx not found")
    xlsx.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([soffice, "--headless", "--convert-to", "xlsx", "--outdir", str(xlsx.parent), str(xls)], check=True)
    return xlsx


def get_cell(row: pd.Series, index: int) -> object:
    return row.iloc[index] if index < len(row) else ""


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    path = ensure_xlsx()
    df = pd.read_excel(path, sheet_name=SHEET_NAME, header=None)
    rows: list[dict[str, str]] = []
    for _, raw in df.iloc[4:].iterrows():
        college = norm(get_cell(raw, 0))
        major_name = norm(get_cell(raw, 1))
        if not major_name or "备注" in major_name:
            continue
        for year in args.years:
            admit_col, score_col, rank_col = TRACK_COLUMNS[args.track][year]
            min_score = score_text(get_cell(raw, score_col))
            min_rank = rank_text(get_cell(raw, rank_col))
            if not min_score or not min_rank:
                continue
            admit_count = numeric_text(get_cell(raw, admit_col))
            notes_parts = [
                SOURCE_TITLE,
                f"学院={college}" if college else "",
                "普通本科专业级三年汇总表",
                f"附件缓存={RAW_XLS}",
                f"附件URL={ATTACHMENT_URL}",
            ]
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
                    "plan_type": plan_type(major_name),
                    "min_score": min_score,
                    "min_rank": min_rank,
                    "admit_count": admit_count,
                    "source_url": SOURCE_URL,
                    "source_name": SOURCE_NAME,
                    "notes": "；".join(part for part in notes_parts if part),
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
        raise argparse.ArgumentTypeError(f"Unsupported years: {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import ZHKU official Guangdong major scores.")
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
    print("# 仲恺农业工程学院专业录取分数导入\n")
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
