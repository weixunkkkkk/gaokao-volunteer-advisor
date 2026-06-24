#!/usr/bin/env python3
"""Import GDPU official Guangdong major-level admission scores from cached official attachments."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "assets" / "raw-cache" / "gdpu"
SOURCE_NAME = "广东药科大学招生办"
SCHOOL_NAME = "广东药科大学"
LIST_URL = "https://zsb.gdpu.edu.cn/"
PYTHON_HINT = "/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"

GENERAL_SOURCES = {
    2025: {
        "article_url": "https://zsb.gdpu.edu.cn/info/1080/1518.htm",
        "attachment_name": "2025_guangdong_scores.pdf",
        "attachment_url": "https://zsb.gdpu.edu.cn/system/_content/download.jsp?urltype=news.DownloadAttachUrl&owner=1460905134&wbfileid=16629148",
        "file_type": "pdf",
    },
    2024: {
        "article_url": "https://zsb.gdpu.edu.cn/info/1080/1489.htm",
        "attachment_name": "2024_guangdong_scores.xlsx",
        "attachment_url": "https://zsb.gdpu.edu.cn/system/_content/download.jsp?urltype=news.DownloadAttachUrl&owner=1460905134&wbfileid=11524071",
        "file_type": "xlsx",
    },
    2023: {
        "article_url": "https://zsb.gdpu.edu.cn/info/1080/1459.htm",
        "attachment_name": "2023_guangdong_scores.xlsx",
        "attachment_url": "https://zsb.gdpu.edu.cn/system/_content/download.jsp?urltype=news.DownloadAttachUrl&owner=1460905134&wbfileid=11499522",
        "file_type": "xlsx",
    },
}

HEALTH_SOURCES = {
    2025: {
        "article_url": "https://zsb.gdpu.edu.cn/info/1080/1529.htm",
        "attachment_name": "2025_health_special.xlsx",
        "attachment_url": "https://zsb.gdpu.edu.cn/system/_content/download.jsp?urltype=news.DownloadAttachUrl&owner=1460905134&wbfileid=16632449",
        "file_type": "xlsx",
    },
    2024: {
        "article_url": "https://zsb.gdpu.edu.cn/info/1080/1491.htm",
        "attachment_name": "2024_health_special.pdf",
        "attachment_url": "https://zsb.gdpu.edu.cn/system/_content/download.jsp?urltype=news.DownloadAttachUrl&owner=1460905134&wbfileid=11524073",
        "file_type": "pdf",
    },
    2023: {
        "article_url": "https://zsb.gdpu.edu.cn/info/1080/1454.htm",
        "attachment_name": "2023_health_special.xlsx",
        "attachment_url": "https://zsb.gdpu.edu.cn/system/_content/download.jsp?urltype=news.DownloadAttachUrl&owner=1460905134&wbfileid=11495665",
        "file_type": "xlsx",
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
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def digits(value: object) -> str:
    text = norm(value).replace(",", "")
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return re.sub(r"\D", "", text)


def valid_score(value: object) -> str:
    text = digits(value)
    if not text:
        return ""
    number = int(text)
    return text if 300 <= number <= 750 else ""


def valid_rank(value: object) -> str:
    text = digits(value)
    if not text:
        return ""
    number = int(text)
    return text if 1 <= number <= 500000 else ""


def valid_count(value: object) -> str:
    text = digits(value)
    if not text:
        return ""
    number = int(text)
    return text if 1 <= number <= 10000 else ""


def normalize_major(value: object) -> str:
    text = norm(value).replace(" ", "")
    text = text.replace("\n", "").replace("（外包特色班）", "（外包特色班）")
    text = text.replace("英语(国际班）", "英语（国际班）").replace("(", "（").replace(")", "）")
    return text.strip("，,、")


def track_from_group(group: str) -> str:
    if "历史" in group:
        return "历史类"
    if "物理" in group:
        return "物理类"
    return ""


def group_code(group: str) -> str:
    match = re.search(r"(\d{3})", group)
    return match.group(1) if match else ""


def plan_type_from_group(group: str, major_name: str) -> str:
    text = f"{group} {major_name}"
    if "国际班" in text:
        return "国际班"
    return "普通类"


def clean_excel_value(value: object) -> str:
    text = norm(value)
    return "" if text.lower() == "nan" else text


def parse_excel_general(args: argparse.Namespace, year: int, path: Path) -> list[dict[str, str]]:
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise SystemExit(f"读取广东药科大学Excel需要pandas/openpyxl；请用 {PYTHON_HINT} 运行本脚本。") from exc

    source = GENERAL_SOURCES[year]
    df = pd.read_excel(path, sheet_name=0, header=None)
    rows: list[dict[str, str]] = []
    for values in df.fillna("").values.tolist():
        if len(values) < 9:
            continue
        code = digits(values[0])
        major_name = normalize_major(values[1])
        group = clean_excel_value(values[2])
        if not (code and major_name and group):
            continue
        track = track_from_group(group)
        if track != args.track:
            continue
        min_score = valid_score(values[5])
        min_rank = valid_rank(values[7])
        if not min_score or not min_rank:
            continue
        high_score = valid_score(values[4])
        average = clean_excel_value(values[6])
        group_rank = valid_rank(values[8])
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": group_code(group),
                "major_name": major_name,
                "plan_type": plan_type_from_group(group, major_name),
                "min_score": min_score,
                "min_rank": min_rank,
                "admit_count": "",
                "source_url": source["article_url"],
                "source_name": SOURCE_NAME,
                "notes": notes(
                    source,
                    "学校官网Excel专业录取分数",
                    group,
                    clean_excel_value(values[3]),
                    high_score,
                    average,
                    group_rank,
                    "",
                ),
            }
        )
    return rows


def parse_pdf_general(args: argparse.Namespace, year: int, path: Path) -> list[dict[str, str]]:
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise SystemExit(f"读取广东药科大学PDF需要pdfplumber；请用 {PYTHON_HINT} 运行本脚本。") from exc

    source = GENERAL_SOURCES[year]
    rows: list[dict[str, str]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for values in table:
                    if len(values) < 9:
                        continue
                    code = digits(values[0])
                    major_name = normalize_major(values[1])
                    group = norm(values[2])
                    if not (code and major_name and group):
                        continue
                    track = track_from_group(group)
                    if track != args.track:
                        continue
                    min_score = valid_score(values[5])
                    min_rank = valid_rank(values[7])
                    if not min_score or not min_rank:
                        continue
                    high_score = valid_score(values[4])
                    average = norm(values[6])
                    group_rank = valid_rank(values[8])
                    rows.append(
                        {
                            "year": str(year),
                            "province": args.province,
                            "track": track,
                            "batch": args.batch,
                            "school_name": SCHOOL_NAME,
                            "school_code": args.school_code,
                            "major_group": group_code(group),
                            "major_name": major_name,
                            "plan_type": plan_type_from_group(group, major_name),
                            "min_score": min_score,
                            "min_rank": min_rank,
                            "admit_count": "",
                            "source_url": source["article_url"],
                            "source_name": SOURCE_NAME,
                            "notes": notes(
                                source,
                                "学校官网PDF专业录取分数",
                                group,
                                norm(values[3]),
                                high_score,
                                average,
                                group_rank,
                                "",
                            ),
                        }
                    )
    return rows


def parse_excel_health(args: argparse.Namespace, year: int, path: Path) -> list[dict[str, str]]:
    if args.track != "物理类":
        return []
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise SystemExit(f"读取广东药科大学Excel需要pandas/openpyxl；请用 {PYTHON_HINT} 运行本脚本。") from exc

    source = HEALTH_SOURCES[year]
    df = pd.read_excel(path, sheet_name=0, header=None)
    rows: list[dict[str, str]] = []
    current_city = ""
    for values in df.fillna("").values.tolist():
        if len(values) < 10:
            continue
        city = clean_excel_value(values[0]) or current_city
        county = clean_excel_value(values[1])
        major_name = normalize_major(values[2])
        group = clean_excel_value(values[4])
        min_score = valid_score(values[6])
        min_rank = valid_rank(values[9])
        if clean_excel_value(values[0]):
            current_city = clean_excel_value(values[0])
        if not (major_name and group and min_score and min_rank):
            continue
        high_score = valid_score(values[5])
        average = clean_excel_value(values[7])
        admit_count = valid_count(values[8])
        rows.append(health_row(args, year, source, city, county, major_name, group, high_score, min_score, average, admit_count, min_rank, "学校官网Excel卫生专项录取分数"))
    return rows


def parse_pdf_health(args: argparse.Namespace, year: int, path: Path) -> list[dict[str, str]]:
    if args.track != "物理类":
        return []
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise SystemExit(f"读取广东药科大学PDF需要pdfplumber；请用 {PYTHON_HINT} 运行本脚本。") from exc

    source = HEALTH_SOURCES[year]
    rows: list[dict[str, str]] = []
    current_city = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for values in table:
                    if len(values) < 10:
                        continue
                    city = norm(values[0]) or current_city
                    county = norm(values[1])
                    major_name = normalize_major(values[2])
                    group = norm(values[4])
                    min_score = valid_score(values[6])
                    min_rank = valid_rank(values[9])
                    if norm(values[0]) and norm(values[0]) not in {"定向地区", "地市"}:
                        current_city = norm(values[0])
                    if not (major_name and group and min_score and min_rank):
                        continue
                    high_score = valid_score(values[5])
                    average = norm(values[7])
                    admit_count = valid_count(values[8])
                    rows.append(health_row(args, year, source, city, county, major_name, group, high_score, min_score, average, admit_count, min_rank, "学校官网PDF卫生专项录取分数"))
    return rows


def notes(
    source: dict[str, str],
    prefix: str,
    group: str,
    duration: str,
    high_score: str,
    average: str,
    group_rank: str,
    extra: str,
) -> str:
    return "；".join(
        part
        for part in [
            prefix,
            f"官方附件={source['attachment_url']}",
            f"专业组={group}" if group else "",
            f"学制={duration}" if duration else "",
            f"最高分={high_score}" if high_score else "",
            f"平均分={average}" if average else "",
            f"专业组最低排位={group_rank}" if group_rank else "",
            extra,
            "只导入本科层次普通物理/历史或卫生专项，不含专科",
        ]
        if part
    )


def health_row(
    args: argparse.Namespace,
    year: int,
    source: dict[str, str],
    city: str,
    county: str,
    major_name: str,
    group: str,
    high_score: str,
    min_score: str,
    average: str,
    admit_count: str,
    min_rank: str,
    prefix: str,
) -> dict[str, str]:
    area = f"{city}{county}".strip()
    return {
        "year": str(year),
        "province": args.province,
        "track": "物理类",
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": group_code(group),
        "major_name": major_name,
        "plan_type": "卫生专项",
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": admit_count,
        "source_url": source["article_url"],
        "source_name": SOURCE_NAME,
        "notes": notes(
            source,
            prefix,
            group,
            "",
            high_score,
            average,
            "",
            f"定向地区={area}" if area else "",
        ),
    }


def parse_year(args: argparse.Namespace, year: int) -> list[dict[str, str]]:
    raw_dir = Path(args.raw_dir).expanduser().resolve()
    rows: list[dict[str, str]] = []
    general = GENERAL_SOURCES[year]
    general_path = raw_dir / general["attachment_name"]
    if not general_path.exists():
        raise FileNotFoundError(f"missing official cached attachment: {general_path}")
    if general["file_type"] == "pdf":
        rows.extend(parse_pdf_general(args, year, general_path))
    else:
        rows.extend(parse_excel_general(args, year, general_path))

    health = HEALTH_SOURCES[year]
    health_path = raw_dir / health["attachment_name"]
    if health_path.exists():
        if health["file_type"] == "pdf":
            rows.extend(parse_pdf_health(args, year, health_path))
        else:
            rows.extend(parse_excel_health(args, year, health_path))
    return rows


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in args.years:
        rows.extend(parse_year(args, year))
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["major_group"], row["major_name"], row["plan_type"], row["min_score"], row["min_rank"], row["notes"])
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
        raise argparse.ArgumentTypeError(f"GDPU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GDPU official Guangdong major-level scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="10573")
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
    print("# 广东药科大学专业录取分数导入\n")
    print(f"- 来源：{LIST_URL}")
    print(f"- 原始附件目录：{Path(args.raw_dir).expanduser().resolve()}")
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
