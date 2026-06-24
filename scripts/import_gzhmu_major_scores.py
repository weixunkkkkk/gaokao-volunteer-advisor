#!/usr/bin/env python3
"""Import GZHMU official major-level admission scores for Guangdong."""

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
SOURCE_NAME = "广州医科大学本科招生网"
SCHOOL_NAME = "广州医科大学"
LIST_URL = "https://zs.gzhmu.edu.cn/wnlqfs/lnfs_gd_/a2025n.htm"

PAGES = {
    2025: (
        "https://zs.gzhmu.edu.cn/wnlqfs/lnfs_gd_/a2025n.htm",
        "https://zs.gzhmu.edu.cn/__local/9/06/DD/BB1DC70A4D27421D0F404E95F9C_F4411889_54516.jpg",
    ),
    2024: (
        "https://zs.gzhmu.edu.cn/wnlqfs/lnfs_gd_/a2024n.htm",
        "https://zs.gzhmu.edu.cn/__local/8/FB/0D/22D8B86B24AD52295E37535839D_2DD3AD1B_7D48.png",
    ),
    2023: (
        "https://zs.gzhmu.edu.cn/wnlqfs/lnfs_gd_/a2023n_.htm",
        "https://zs.gzhmu.edu.cn/__local/A/AA/72/C2E2A43CB50CD6C0D037BF1EEFF_430DF1CE_27595.png",
    ),
}

YEAR_CONFIG = {
    2025: {
        "major": (0.16, 0.45),
        "admit_count": (0.51, 0.61),
        "min_score": (0.67, 0.77),
        "min_rank": (0.83, 0.95),
        "major_group": None,
        "sections": [
            (0.385, "物理类", "普通类"),
            (0.285, "历史类", "普通类"),
            (0.045, "物理类", "地方专项"),
            (-1.0, "历史类", "地方专项"),
        ],
    },
    2024: {
        "major": (0.34, 0.57),
        "admit_count": None,
        "min_score": (0.60, 0.68),
        "min_rank": (0.69, 0.78),
        "major_group": (0.18, 0.28),
        "sections": [
            (0.415, "物理类", "普通类"),
            (0.300, "历史类", "普通类"),
            (0.060, "物理类", "地方专项"),
            (-1.0, "历史类", "地方专项"),
        ],
    },
    2023: {
        "major": (0.22, 0.39),
        "admit_count": None,
        "min_score": (0.44, 0.51),
        "min_rank": (0.58, 0.67),
        "major_group": (0.12, 0.20),
        "sections": [
            (0.470, "物理类", "普通类"),
            (0.205, "历史类", "普通类"),
            (0.065, "物理类", "地方专项"),
            (-1.0, "历史类", "地方专项"),
        ],
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


@dataclass
class OcrItem:
    x: float
    y: float
    w: float
    h: float
    text: str


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def download(url: str, path: Path, referer: str) -> None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": referer})
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
    text = text.replace(".", "").replace("，", "")
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
    text = text.replace("〉", "）").replace("(", "（").replace(")", "）")
    text = text.replace('"', "”")
    text = re.sub(r"^[0-9]+", "", text)
    text = re.sub(r"[A-Za-z0-9口OAa.。]+$", "", text)
    return text.strip("，,、")


def infer_section(year: int, center_y: float) -> tuple[str, str]:
    for min_y, track, plan_type in YEAR_CONFIG[year]["sections"]:
        if center_y >= min_y:
            return track, plan_type
    return "", ""


def candidate_row_centers(year: int, items: list[OcrItem]) -> list[float]:
    config = YEAR_CONFIG[year]
    score_x = config["min_score"]
    rank_x = config["min_rank"]
    raw: list[float] = []
    for item in items:
        value = clean_int_text(item.text)
        if not value:
            continue
        number = int(value)
        if score_x[0] <= item.x <= score_x[1] and 400 <= number <= 700:
            raw.append(item.y)
        elif rank_x[0] <= item.x <= rank_x[1] and 1000 <= number <= 200000:
            raw.append(item.y)

    centers: list[float] = []
    for y in sorted(raw, reverse=True):
        for index, center in enumerate(centers):
            if abs(center - y) <= 0.008:
                centers[index] = (center + y) / 2
                break
        else:
            centers.append(y)
    return centers


def row_items(items: list[OcrItem], center_y: float) -> list[OcrItem]:
    return sorted((item for item in items if abs(item.y - center_y) <= 0.013), key=lambda value: value.x)


def parse_year_rows(args: argparse.Namespace, year: int, items: list[OcrItem]) -> list[dict[str, str]]:
    article_url, image_url = PAGES[year]
    config = YEAR_CONFIG[year]
    rows: list[dict[str, str]] = []
    for center in candidate_row_centers(year, items):
        row = row_items(items, center)
        major_name = normalize_major(text_in(row, *config["major"]))
        if not major_name or major_name in {"专业", "类型", "组别"}:
            continue
        track, plan_type = infer_section(year, center)
        if track != args.track:
            continue
        min_score = first_int(row, *config["min_score"], 400, 700)
        min_rank = first_int(row, *config["min_rank"], 1000, 200000)
        if not (min_score and min_rank):
            continue
        admit_count = ""
        if config["admit_count"]:
            admit_count = first_int(row, *config["admit_count"], 1, 9999)
        major_group = ""
        if config["major_group"]:
            raw_group = text_in(row, *config["major_group"])
            group_match = re.search(r"\d{3}", raw_group)
            major_group = group_match.group(0) if group_match else ""
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": major_group,
                "major_name": major_name,
                "plan_type": plan_type,
                "min_score": min_score,
                "min_rank": min_rank,
                "admit_count": admit_count,
                "source_url": article_url,
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        "学校官网图片OCR专业录取分数",
                        f"图片={image_url}",
                        f"专业组={major_group}" if major_group else "",
                    ]
                    if part
                ),
            }
        )
    return rows


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        for year in args.years:
            article_url, image_url = PAGES[year]
            suffix = Path(image_url).suffix or ".png"
            image_path = work_dir / f"gzhmu_{year}{suffix}"
            download(image_url, image_path, article_url)
            rows.extend(parse_year_rows(args, year, run_ocr(image_path)))
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
    unsupported = sorted(set(years) - set(PAGES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"GZHMU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GZHMU official Guangdong major-level admission scores.")
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

    print("# 广州医科大学专业录取分数导入\n")
    print(f"- 来源：{LIST_URL}")
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
