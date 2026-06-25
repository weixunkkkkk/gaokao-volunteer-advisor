#!/usr/bin/env python3
"""Import Guangzhou Maritime University official Guangdong major scores."""

from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

try:
    import pandas as pd
    import pdfplumber
except ImportError:
    print(
        "This importer needs pandas and pdfplumber. Run it with the bundled Python: "
        "python3",
        file=sys.stderr,
    )
    raise


SOURCE_NAME = "广州航海学院招生办"
SCHOOL_NAME = "广州航海学院"
PAGES = {
    2025: "https://zsb.gzmtu.edu.cn/info/1169/2164.htm",
    2024: "https://zsb.gzmtu.edu.cn/info/1169/2011.htm",
    2023: "https://zsb.gzmtu.edu.cn/info/1094/1871.htm",
}
PDF_2023 = "https://zsb.gzmtu.edu.cn/__local/D/9B/72/182705CB253E27234D05498EB0F_F106E5EB_367DA.pdf"

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


def clean(value: object) -> str:
    text = norm(value).replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def digits(value: object) -> str:
    return re.sub(r"\D", "", clean(value))


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


def track_group(group_label: str, track: str) -> bool:
    return ("物理" in group_label) if track == "物理类" else ("历史" in group_label)


def group_code(group_label: str) -> str:
    match = re.match(r"^(\d{3})", group_label)
    return match.group(1) if match else ""


def plan_type(major_name: str) -> str:
    if "中外合作" in major_name:
        return "中外合作"
    if "中外联合培养" in major_name:
        return "中外联合培养"
    if major_name in {"航海技术", "轮机工程", "船舶电子电气工程"}:
        return "航海类"
    return "普通类"


def make_row(
    args: argparse.Namespace,
    *,
    year: int,
    source_url: str,
    group_label: str,
    major_code: str,
    major_name: str,
    admit_count: str,
    high_score: str,
    min_score: str,
    min_rank: str,
    average_score: str = "",
    attachment_url: str = "",
) -> dict[str, str] | None:
    group_label = clean(group_label).replace(" ", "")
    major_code = digits(major_code)
    major_name = clean(major_name).replace(" ", "")
    if not group_label or not track_group(group_label, args.track):
        return None
    if not re.fullmatch(r"\d{3}", major_code):
        return None
    min_score = valid_score(min_score)
    min_rank = valid_rank(min_rank)
    if not major_name or not min_score or not min_rank:
        return None
    return {
        "year": str(year),
        "province": args.province,
        "track": args.track,
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": group_code(group_label),
        "major_name": major_name,
        "plan_type": plan_type(major_name),
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": digits(admit_count),
        "source_url": source_url,
        "source_name": SOURCE_NAME,
        "notes": "；".join(
            part
            for part in [
                f"专业组={group_label}",
                f"专业代码={major_code}",
                "学校官网分科类分专业录取情况表导入；只导入普通物理/历史本科专业组，不含美术类",
                f"最高分={valid_score(high_score)}" if valid_score(high_score) else "",
                f"平均分={clean(average_score)}" if clean(average_score) else "",
                f"附件={attachment_url}" if attachment_url else "",
            ]
            if part
        ),
    }


def parse_html_year(args: argparse.Namespace, year: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table in pd.read_html(PAGES[year]):
        if table.shape[1] != 7:
            continue
        for values in table.fillna("").astype(str).values.tolist():
            group_label, major_code, major_name, admit_count, high_score, min_score, min_rank = values
            if not re.fullmatch(r"\d{3}", digits(major_code)):
                continue
            row = make_row(
                args,
                year=year,
                source_url=PAGES[year],
                group_label=group_label,
                major_code=major_code,
                major_name=major_name,
                admit_count=admit_count,
                high_score=high_score,
                min_score=min_score,
                min_rank=min_rank,
            )
            if row:
                rows.append(row)
    return dedupe_rows(rows)


def fetch_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": PAGES[2023]})
    return urlopen(request, timeout=60).read()


def parse_pdf_2023(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="gzmtu_major_") as tmp_raw:
        path = Path(tmp_raw) / "gzmtu_2023.pdf"
        path.write_bytes(fetch_bytes(PDF_2023))
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    current_group = ""
                    for values in table[1:]:
                        if not values or len(values) < 8:
                            continue
                        group_label, major_code, major_name, admit_count, high_score, min_score, average_score, min_rank = [
                            clean(value).replace("\n", "") for value in values[:8]
                        ]
                        if group_label:
                            current_group = group_label.replace(" ", "")
                        row = make_row(
                            args,
                            year=2023,
                            source_url=PAGES[2023],
                            group_label=current_group,
                            major_code=major_code,
                            major_name=major_name,
                            admit_count=admit_count,
                            high_score=high_score,
                            min_score=min_score,
                            min_rank=min_rank,
                            average_score=average_score,
                            attachment_url=PDF_2023,
                        )
                        if row:
                            rows.append(row)
    return dedupe_rows(rows)


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in args.years:
        if year == 2023:
            rows.extend(parse_pdf_2023(args))
        else:
            rows.extend(parse_html_year(args, year))
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["major_group"], row["major_name"], row["plan_type"], row["min_score"], row["min_rank"])
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
    unsupported = sorted(set(years) - set(PAGES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"GZMTU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Guangzhou Maritime University official Guangdong major-level scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
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
    print("# 广州航海学院专业录取分数导入\n")
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
