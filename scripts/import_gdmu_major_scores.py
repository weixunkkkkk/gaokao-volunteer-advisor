#!/usr/bin/env python3
"""Import GDMU official major-level admission scores for Guangdong."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OCR_SCRIPT = ROOT / "scripts" / "vision_ocr_image_zh.swift"
SOURCE_NAME = "广东医科大学招生网"
SCHOOL_NAME = "广东医科大学"
ARTICLE_URL = "https://zs.gdmu.edu.cn/info/1036/2717.htm"
IMAGE_URL = "https://zs.gdmu.edu.cn/__local/8/45/80/42645F3312A6E6DD1ACAB4EADD5_37075660_19C57.png"

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

YEAR_FIELDS = {
    2023: {
        "avg_score": (0.285, 0.335),
        "max_score": (0.424, 0.470),
        "min_score": (0.560, 0.604),
        "min_rank": (0.690, 0.748),
    },
    2024: {
        "avg_score": (0.335, 0.378),
        "max_score": (0.470, 0.516),
        "min_score": (0.604, 0.650),
        "min_rank": (0.748, 0.804),
    },
    2025: {
        "avg_score": (0.378, 0.424),
        "max_score": (0.516, 0.560),
        "min_score": (0.650, 0.690),
        "min_rank": (0.804, 0.858),
    },
}


@dataclass
class OcrItem:
    x: float
    y: float
    w: float
    h: float
    text: str


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def download(url: str, path: Path) -> None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": ARTICLE_URL})
    path.write_bytes(urlopen(request, timeout=60).read())


def run_ocr(path: Path) -> list[OcrItem]:
    result = subprocess.run(
        ["swift", str(OCR_SCRIPT), str(path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    items: list[OcrItem] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t", 5)
        if len(parts) != 6:
            continue
        _, x, y, w, h, text = parts
        items.append(OcrItem(float(x), float(y), float(w), float(h), text.strip()))
    return items


def clean_int_text(value: object) -> str:
    text = norm(value)
    text = text.replace("O", "0").replace("o", "0").replace("S", "5").replace("l", "1")
    return re.sub(r"\D", "", text)


def text_in(row: list[OcrItem], min_x: float, max_x: float) -> str:
    return "".join(item.text for item in row if min_x <= item.x <= max_x).strip()


def first_int(row: list[OcrItem], min_x: float, max_x: float, low: int = 0, high: int = 999999) -> str:
    for item in sorted(row, key=lambda value: value.x):
        if min_x <= item.x <= max_x:
            value = clean_int_text(item.text)
            if value and low <= int(value) <= high:
                return value
    return ""


def normalize_major(value: str) -> str:
    text = value.replace(" ", "").replace("\u3000", "")
    text = text.replace("檢", "检").replace("敏低", "最低")
    text = text.replace('"', "”")
    text = re.sub(r"^[0-9]+", "", text)
    text = re.sub(r"[A-Za-z0-9口OAa.。]+$", "", text)
    if "联合学士学位项目" in text and not text.endswith("联合学士学位项目"):
        before, _, _ = text.partition("联合学士学位项目")
        text = before + "联合学士学位项目"
    return text.strip("，,、")


def candidate_row_centers(items: list[OcrItem]) -> list[float]:
    raw: list[float] = []
    for item in items:
        value = clean_int_text(item.text)
        if not value:
            continue
        number = int(value)
        if 0.560 <= item.x <= 0.690 and 400 <= number <= 650:
            raw.append(item.y)
        elif 0.690 <= item.x <= 0.858 and 1000 <= number <= 200000:
            raw.append(item.y)

    centers: list[float] = []
    for y in sorted(raw, reverse=True):
        for index, center in enumerate(centers):
            if abs(center - y) <= 0.006:
                centers[index] = (center + y) / 2
                break
        else:
            centers.append(y)
    return centers


def row_items(items: list[OcrItem], center_y: float) -> list[OcrItem]:
    return sorted((item for item in items if abs(item.y - center_y) <= 0.010), key=lambda value: value.x)


def physics_boundary(items: list[OcrItem]) -> float:
    for item in items:
        if "普通类物理" in item.text and "控制分数线" in item.text:
            return item.y
    return 0.113


def parse_rows(args: argparse.Namespace, items: list[OcrItem]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    boundary = physics_boundary(items)
    target_years = set(args.years)

    for center in candidate_row_centers(items):
        row = row_items(items, center)
        major_name = normalize_major(text_in(row, 0.10, 0.28))
        if not major_name or major_name in {"专业名称", "普通类物理最低控制分数线", "普通类历史最低控制分数线"}:
            continue
        if "控制分数线" in major_name:
            continue
        track = "物理类" if center > boundary else "历史类"
        if track != args.track:
            continue
        exact_group = first_int(row, 0.050, 0.105, 200, 299)

        for year in sorted(target_years):
            fields = YEAR_FIELDS[year]
            min_score = first_int(row, *fields["min_score"], 400, 650)
            min_rank = first_int(row, *fields["min_rank"], 1000, 200000)
            if not (min_score and min_rank):
                continue
            max_score = first_int(row, *fields["max_score"], 400, 700)
            avg_score = first_int(row, *fields["avg_score"], 400, 700)
            rows.append(
                {
                    "year": str(year),
                    "province": args.province,
                    "track": track,
                    "batch": args.batch,
                    "school_name": SCHOOL_NAME,
                    "school_code": args.school_code,
                    "major_group": exact_group,
                    "major_name": major_name,
                    "plan_type": "普通类",
                    "min_score": min_score,
                    "min_rank": min_rank,
                    "admit_count": "",
                    "source_url": ARTICLE_URL,
                    "source_name": SOURCE_NAME,
                    "notes": "；".join(
                        part
                        for part in [
                            "学校官网图片OCR专业录取分数",
                            f"图片={IMAGE_URL}",
                            f"最高分={max_score}" if max_score else "",
                            f"平均分={avg_score}" if avg_score else "",
                            f"分组代号OCR={exact_group}" if exact_group else "",
                        ]
                        if part
                    ),
                }
            )
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output = []
    for row in rows:
        key = (
            row["year"],
            row["track"],
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


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    with tempfile.TemporaryDirectory() as tmp:
        image_path = Path(tmp) / "gdmu_2023_2025_major.png"
        download(IMAGE_URL, image_path)
        return parse_rows(args, run_ocr(image_path))


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
    unsupported = sorted(set(years) - set(YEAR_FIELDS))
    if unsupported:
        raise argparse.ArgumentTypeError(f"GDMU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GDMU official Guangdong major-level admission scores.")
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

    print("# 广东医科大学专业录取分数导入\n")
    print(f"- 来源：{ARTICLE_URL}")
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
