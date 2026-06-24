#!/usr/bin/env python3
"""Import Jiaying University official Guangdong major scores from Excel attachments."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
from pathlib import Path

import pandas as pd


SOURCE_NAME = "嘉应学院招生信息网"
SCHOOL_NAME = "嘉应学院"
SCHOOL_CODE = "10582"
SOURCES = {
    2025: {
        "article_url": "https://zs.jyu.edu.cn/portal/detail_dsnc.action?channel.id=2295767126766008&domain.id=4230570967593800",
        "attachment_url": "https://zs.jyu.edu.cn/attached/file/20251111/20251111162601_618.xls",
        "xls": "assets/raw-cache/jyu/2025_guangdong_major_scores.xls",
        "xlsx": "assets/raw-cache/jyu/converted/2025_guangdong_major_scores.xlsx",
        "title": "嘉应学院2025年各专业录取情况统计表（广东省）",
    },
    2024: {
        "article_url": "https://zs.jyu.edu.cn/portal/detail_dsnc.action?channel.id=2295767126766008&domain.id=4159977452156400",
        "attachment_url": "https://zs.jyu.edu.cn/attached/file/20250610/20250610094004_244.xls",
        "xls": "assets/raw-cache/jyu/2024_guangdong_major_scores.xls",
        "xlsx": "assets/raw-cache/jyu/converted/2024_guangdong_major_scores.xlsx",
        "title": "嘉应学院2024年各专业录取情况统计表（广东省）",
    },
    2023: {
        "article_url": "https://zs.jyu.edu.cn/portal/detail_dsnc.action?channel.id=2295767126766008&domain.id=7820627160110100",
        "attachment_url": "https://zs.jyu.edu.cn/attached/file/20231116/20231116090724_886.xls",
        "xls": "assets/raw-cache/jyu/2023_guangdong_major_scores.xls",
        "xlsx": "assets/raw-cache/jyu/converted/2023_guangdong_major_scores.xlsx",
        "title": "嘉应学院2023年各专业录取情况统计表（广东省）",
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


def int_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = norm(value).replace(",", "")
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


def decimal_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else f"{value:.1f}".rstrip("0").rstrip(".")
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    return match.group(0) if match else ""


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


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {col: norm(col).replace("\\n", "") for col in df.columns}
    df = df.rename(columns=renamed)
    unnamed = [col for col in df.columns if str(col).startswith("Unnamed")]
    return df.drop(columns=unnamed, errors="ignore")


def ensure_xlsx(meta: dict[str, str]) -> Path:
    xlsx = Path(meta["xlsx"])
    if xlsx.exists():
        return xlsx
    xls = Path(meta["xls"])
    if not xls.exists():
        raise FileNotFoundError(f"Missing official Excel attachment cache: {xls}")
    soffice = shutil.which("soffice") or ("/opt/homebrew/bin/soffice" if Path("/opt/homebrew/bin/soffice").exists() else "")
    if not soffice:
        raise RuntimeError(f"{xls} is .xls and needs soffice conversion; cached xlsx not found")
    xlsx.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([soffice, "--headless", "--convert-to", "xlsx", "--outdir", str(xlsx.parent), str(xls)], check=True)
    return xlsx


def track_name(value: object) -> str:
    text = norm(value)
    if text == "物理":
        return "物理类"
    if text == "历史":
        return "历史类"
    return ""


def major_group(value: object, track: str) -> str:
    number = int_text(value)
    return f"{number}.{track.replace('类', '组')}" if number else ""


def plan_type(major_name: str, notes: str) -> str:
    text = f"{major_name}{notes}"
    if "中外" in text or "联合培养" in text:
        return "中外合作"
    if "协同" in text:
        return "协同培养"
    if "临床医学" in text and "定向" in text:
        return "卫生专项"
    if "定向" in text:
        return "教师专项"
    return "普通类"


def parse_year(args: argparse.Namespace, year: int, meta: dict[str, str]) -> list[dict[str, str]]:
    path = ensure_xlsx(meta)
    df = pd.read_excel(path)
    df = clean_columns(df)
    if "专业组" in df.columns:
        df["专业组"] = df["专业组"].ffill()
    rows: list[dict[str, str]] = []
    for _, raw in df.iterrows():
        if norm(raw.get("层次")) != "本科":
            continue
        track = track_name(raw.get("首选科目"))
        if track != args.track:
            continue
        major_name = norm(raw.get("专业名称"))
        min_score = score_text(raw.get("最低分"))
        min_rank = rank_text(raw.get("最低排位"))
        if not major_name or not min_score or not min_rank:
            continue
        group = major_group(raw.get("专业组"), track)
        notes_parts = [
            meta["title"],
            f"学院={norm(raw.get('学院'))}" if norm(raw.get("学院")) else "",
            f"专业号={int_text(raw.get('专业号'))}" if int_text(raw.get("专业号")) else "",
            f"再选科目={norm(raw.get('再选科目')) or '不限'}",
            f"招生计划={int_text(raw.get('招生计划'))}" if int_text(raw.get("招生计划")) else "",
            f"最高分={score_text(raw.get('最高分'))}" if score_text(raw.get("最高分")) else "",
            f"最高排位={rank_text(raw.get('最高排位'))}" if rank_text(raw.get("最高排位")) else "",
            f"平均分={decimal_text(raw.get('平均分'))}" if decimal_text(raw.get("平均分")) else "",
            f"备注={norm(raw.get('备注'))}" if norm(raw.get("备注")) else "",
            f"附件缓存={meta['xls']}",
        ]
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": group,
                "major_name": major_name,
                "plan_type": plan_type(major_name, norm(raw.get("备注"))),
                "min_score": min_score,
                "min_rank": min_rank,
                "admit_count": int_text(raw.get("录取数")),
                "source_url": meta["article_url"],
                "source_name": SOURCE_NAME,
                "notes": "；".join(part for part in notes_parts if part),
            }
        )
    return dedupe_rows(rows)


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in args.years:
        rows.extend(parse_year(args, year, SOURCES[year]))
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["major_group"], row["major_name"], row["min_score"], row["min_rank"])
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
    unsupported = sorted(set(years) - set(SOURCES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"Unsupported years: {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Jiaying University official Guangdong major scores.")
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
    print("# 嘉应学院专业录取分数导入\n")
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
