#!/usr/bin/env python3
"""Import GDUFE official major-level admission scores for Guangdong."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OCR_SCRIPT = ROOT / "scripts" / "vision_ocr_image_zh.swift"
SOURCE_NAME = "广东财经大学本科招生办公室"
SCHOOL_NAME = "广东财经大学"
LIST_URL = "https://zsb.gdufe.edu.cn/11400/list.htm"
PYTHON_HINT = "/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"

PDF_PAGES = {
    2025: {
        "物理类": (
            "https://zsb.gdufe.edu.cn/2026/0530/c11400a239654/page.htm",
            "https://zsb.gdufe.edu.cn/_upload/article/files/94/b2/ed28551a41dd9a23c1f56ab68757/f536d1a9-7075-46ca-badc-a68f691d98d5.pdf",
        ),
        "历史类": (
            "https://zsb.gdufe.edu.cn/2026/0530/c11400a239653/page.htm",
            "https://zsb.gdufe.edu.cn/_upload/article/files/a8/29/cd9087f8484194a3c983a92a7c6c/93a40a29-3e2e-451a-937c-77933b0d0320.pdf",
        ),
    },
    2024: {
        "物理类": (
            "https://zsb.gdufe.edu.cn/2025/0103/c11400a215359/page.htm",
            "https://zsb.gdufe.edu.cn/_upload/article/files/e8/35/68b02b1a4affb75280ce60ec7491/2fbc205e-a9d7-4b2d-baf6-9c8622ceb07f.pdf",
        ),
        "历史类": (
            "https://zsb.gdufe.edu.cn/2025/0103/c11400a215358/page.htm",
            "https://zsb.gdufe.edu.cn/_upload/article/files/12/f5/7c2a40f748619c6e74cec684869c/ec800c59-8224-4ac1-a952-e3e442e1eac8.pdf",
        ),
    },
}

IMAGE_PAGES = {
    2023: {
        "物理类": (
            "https://zsb.gdufe.edu.cn/2023/1124/c11400a184244/page.htm",
            "https://zsb.gdufe.edu.cn/_upload/article/images/ff/e8/639a15854f229195c499d41f5b1f/ef64c2b4-f7e6-43ee-b42e-821b33a2e87b_d.jpg",
        ),
        "历史类": (
            "https://zsb.gdufe.edu.cn/2023/1124/c11400a184243/page.htm",
            "https://zsb.gdufe.edu.cn/_upload/article/images/6e/1c/314842144b43bdcfa0a0d2bf3d8a/eaf364c9-e682-4262-8402-7c745fb05d3c_d.jpg",
        ),
    }
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

WATERMARK_CHARS = set("广东财经大学招生办公室")


@dataclass
class OcrItem:
    path: str
    x: float
    y: float
    w: float
    h: float
    text: str


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def download(url: str, path: Path) -> None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    path.write_bytes(urlopen(request, timeout=60).read())


def clean_pdf_cell(value: object) -> str:
    lines = []
    for line in norm(value).splitlines():
        text = line.strip()
        if len(text) == 1 and text in WATERMARK_CHARS:
            continue
        lines.append(text)
    return " ".join(line for line in lines if line).strip()


def clean_int_text(value: object) -> str:
    text = norm(value).replace("O", "0").replace("o", "0").replace("S", "5")
    text = text.replace("Z", "2").replace("z", "2")
    return re.sub(r"\D", "", text)


def clean_number_text(value: object) -> str:
    text = norm(value).replace("O", "0").replace("o", "0").replace("S", "5")
    match = re.search(r"\d+(?:\.\d+)?", text)
    return match.group(0) if match else ""


def normalize_major(value: str) -> str:
    text = norm(value).replace(" ", "")
    text = text.replace("\u3000", "")
    fixes = {
        "（佛山校": "（佛山校区）",
        "（佛": "（佛山校区）",
        "山校区）": "",
        "区）": "",
    }
    for old, new in fixes.items():
        if text.endswith(old):
            text = text[: -len(old)] + new
    return text.strip("，,、")


def infer_plan_type(major: str, group: str, title: str = "") -> str:
    text = f"{major} {group} {title}"
    if "地方专项" in text:
        return "地方专项"
    if "中外" in text or "联合培养" in text:
        return "中外联合培养项目"
    return "普通类"


def parse_pdf_rows(
    *,
    pdf_path: Path,
    year: int,
    track: str,
    article_url: str,
    pdf_url: str,
    batch: str,
    school_code: str,
) -> list[dict[str, str]]:
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise SystemExit(f"读取广东财经大学PDF需要pdfplumber；请用 {PYTHON_HINT} 运行本脚本。") from exc

    rows: list[dict[str, str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                for raw in table:
                    cells = [clean_pdf_cell(cell) for cell in raw]
                    if len(cells) < 9:
                        continue
                    code = clean_int_text(cells[0])
                    if len(code) != 3:
                        continue
                    major_name = normalize_major(cells[1])
                    if not major_name or major_name in {"招生专业", "合计"}:
                        continue
                    group_text = clean_pdf_cell(cells[2])
                    major_group = re.search(r"(\d{3})", group_text)
                    admit_count = clean_int_text(cells[3])
                    max_score = clean_int_text(cells[4])
                    min_score = clean_int_text(cells[5])
                    avg_score = clean_number_text(cells[6])
                    high_rank = clean_int_text(cells[7])
                    min_rank = clean_int_text(cells[8])
                    if not (admit_count and max_score and min_score and min_rank):
                        continue
                    plan_type = infer_plan_type(major_name, group_text)
                    rows.append(
                        {
                            "year": str(year),
                            "province": "广东",
                            "track": track,
                            "batch": batch,
                            "school_name": SCHOOL_NAME,
                            "school_code": school_code,
                            "major_group": major_group.group(1) if major_group else "",
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
                                    "学校官网PDF专业录取分数",
                                    f"PDF={pdf_url}",
                                    f"专业组={group_text}" if group_text else "",
                                    f"最高分={max_score}",
                                    f"平均分={avg_score}" if avg_score else "",
                                    f"最高排位={high_rank}" if high_rank else "",
                                ]
                                if part
                            ),
                        }
                    )
    return rows


def run_ocr(paths: list[Path]) -> list[OcrItem]:
    result = subprocess.run(
        ["swift", str(OCR_SCRIPT), *[str(path) for path in paths]],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    items = []
    for line in result.stdout.splitlines():
        parts = line.split("\t", 5)
        if len(parts) != 6:
            continue
        path, x, y, w, h, text = parts
        items.append(OcrItem(path, float(x), float(y), float(w), float(h), text.strip()))
    return items


def crop_image_for_ocr(path: Path, work_dir: Path) -> list[Path]:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise SystemExit(f"读取广东财经大学2023图片需要Pillow；请用 {PYTHON_HINT} 运行本脚本。") from exc

    image = Image.open(path)
    width, height = image.size
    chunk_height = 1700
    overlap = 180
    output = []
    top = 0
    index = 0
    while top < height:
        bottom = min(height, top + chunk_height)
        crop = image.crop((0, top, width, bottom))
        out = work_dir / f"{path.stem}_crop_{index}.jpg"
        crop.save(out, quality=95)
        output.append(out)
        if bottom == height:
            break
        top = bottom - overlap
        index += 1
    return output


def group_items_by_row(items: list[OcrItem]) -> list[list[OcrItem]]:
    rows: list[list[OcrItem]] = []
    for item in sorted(items, key=lambda value: (-value.y, value.x)):
        if not item.text:
            continue
        for row in rows:
            row_y = sum(entry.y for entry in row) / len(row)
            if abs(row_y - item.y) <= 0.012:
                row.append(item)
                break
        else:
            rows.append([item])
    for row in rows:
        row.sort(key=lambda value: value.x)
    return rows


def text_in(row: list[OcrItem], min_x: float, max_x: float) -> str:
    return "".join(item.text for item in row if min_x <= item.x <= max_x).strip()


def first_int(row: list[OcrItem], min_x: float, max_x: float) -> str:
    for item in row:
        if min_x <= item.x <= max_x:
            value = clean_int_text(item.text)
            if value:
                return value
    return ""


def first_number(row: list[OcrItem], min_x: float, max_x: float) -> str:
    for item in row:
        if min_x <= item.x <= max_x:
            value = clean_number_text(item.text)
            if value:
                return value
    return ""


def plan_type_for_row(row_y: float, titles: list[tuple[float, str]]) -> str:
    candidates = [(title_y - row_y, title) for title_y, title in titles if title_y >= row_y]
    if not candidates:
        return "普通类"
    _, title = min(candidates, key=lambda pair: pair[0])
    return infer_plan_type("", "", title)


def parse_image_rows(
    *,
    items: list[OcrItem],
    year: int,
    track: str,
    article_url: str,
    image_url: str,
    batch: str,
    school_code: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    by_path: dict[str, list[OcrItem]] = defaultdict(list)
    for item in items:
        by_path[item.path].append(item)

    for image_items in by_path.values():
        titles = sorted(
            [(item.y, item.text) for item in image_items if "分专业录取情况统计" in item.text],
            reverse=True,
        )
        for row in group_items_by_row(image_items):
            code = first_int(row, 0.03, 0.17)
            if len(code) != 3:
                continue
            row_y = sum(item.y for item in row) / len(row)
            major_name = normalize_major(text_in(row, 0.10, 0.38))
            if not major_name or major_name in {"专业名称", "合计", "合计："}:
                continue
            admit_count = first_int(row, 0.38, 0.46)
            max_score = first_int(row, 0.46, 0.55)
            min_score = first_int(row, 0.55, 0.64)
            avg_score = first_number(row, 0.63, 0.72)
            high_rank = first_int(row, 0.72, 0.82)
            min_rank = first_int(row, 0.82, 0.94)
            if not (admit_count and max_score and min_score and min_rank):
                continue
            rows.append(
                {
                    "year": str(year),
                    "province": "广东",
                    "track": track,
                    "batch": batch,
                    "school_name": SCHOOL_NAME,
                    "school_code": school_code,
                    "major_group": "",
                    "major_name": major_name,
                    "plan_type": plan_type_for_row(row_y, titles),
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
                            f"最高分={max_score}",
                            f"平均分={avg_score}" if avg_score else "",
                            f"最高排位={high_rank}" if high_rank else "",
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
            row["admit_count"],
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        for year in args.years:
            if year in PDF_PAGES and args.track in PDF_PAGES[year]:
                article_url, pdf_url = PDF_PAGES[year][args.track]
                pdf_path = work_dir / f"gdufe_{year}_{args.track}.pdf"
                download(pdf_url, pdf_path)
                rows.extend(
                    parse_pdf_rows(
                        pdf_path=pdf_path,
                        year=year,
                        track=args.track,
                        article_url=article_url,
                        pdf_url=pdf_url,
                        batch=args.batch,
                        school_code=args.school_code,
                    )
                )
            if year in IMAGE_PAGES and args.track in IMAGE_PAGES[year]:
                article_url, image_url = IMAGE_PAGES[year][args.track]
                image_path = work_dir / f"gdufe_{year}_{args.track}.jpg"
                download(image_url, image_path)
                crops = crop_image_for_ocr(image_path, work_dir)
                rows.extend(
                    parse_image_rows(
                        items=run_ocr(crops),
                        year=year,
                        track=args.track,
                        article_url=article_url,
                        image_url=image_url,
                        batch=args.batch,
                        school_code=args.school_code,
                    )
                )
    return rows


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
    unsupported = sorted(set(years) - (set(PDF_PAGES) | set(IMAGE_PAGES)))
    if unsupported:
        raise argparse.ArgumentTypeError(f"GDUFE importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GDUFE official Guangdong major-level admission scores.")
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
    print("# 广东财经大学专业录取分数导入\n")
    print(f"- 来源：{LIST_URL}")
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
