#!/usr/bin/env python3
"""Import GDUT official major-level admission scores for Guangdong."""

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
SOURCE_NAME = "广东工业大学招生办公室"
SCHOOL_NAME = "广东工业大学"
LIST_URL = "https://zsb.gdut.edu.cn/xxcx/lqsj.htm"
PYTHON_HINT = "python3"

PAGES = {
    2025: (
        "https://zsb.gdut.edu.cn/xxcx/lqsj/n2025/gd.htm",
        "https://zsb.gdut.edu.cn/__local/1/80/65/150DBF2C78758B86B16AFC92039_A570209E_22799C.png",
    ),
    2024: (
        "https://zsb.gdut.edu.cn/xxcx/lqsj/a2024nlqqk/gd.htm",
        "https://zsb.gdut.edu.cn/__local/6/49/A0/1F5AE2F460E6C0CC242105866F7_5F231CA1_120743.png",
    ),
    2023: (
        "https://zsb.gdut.edu.cn/xxcx/lqsj/a2023nlqqk/gd.htm",
        "https://zsb.gdut.edu.cn/__local/8/47/63/45B803059691DD189795FE10B83_CCB90453_124F11.png",
    ),
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
class CropInfo:
    path: Path
    top: int
    height: int
    full_width: int
    full_height: int


@dataclass
class OcrItem:
    x: float
    y: float
    w: float
    h: float
    text: str


@dataclass
class Section:
    y: float
    title: str
    track: str
    plan_type: str
    excluded: bool


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def download(url: str, path: Path) -> None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    path.write_bytes(urlopen(request, timeout=60).read())


def crop_image_for_ocr(path: Path, work_dir: Path) -> list[CropInfo]:
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise SystemExit(f"读取广东工业大学图片需要Pillow；请用 {PYTHON_HINT} 运行本脚本。") from exc

    image = Image.open(path)
    width, height = image.size
    chunk_height = 2200 if height > 12000 else 1800
    overlap = 260
    output: list[CropInfo] = []
    top = 0
    index = 0
    while top < height:
        bottom = min(height, top + chunk_height)
        crop = image.crop((0, top, width, bottom))
        out = work_dir / f"{path.stem}_crop_{index:02d}.png"
        crop.save(out)
        output.append(CropInfo(out, top, bottom - top, width, height))
        if bottom == height:
            break
        top = bottom - overlap
        index += 1
    return output


def run_ocr(crops: list[CropInfo]) -> list[OcrItem]:
    if not crops:
        return []
    crop_by_path = {str(crop.path): crop for crop in crops}
    result = subprocess.run(
        ["swift", str(OCR_SCRIPT), *[str(crop.path) for crop in crops]],
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
        path, x, y, w, h, text = parts
        crop = crop_by_path.get(path)
        if crop is None:
            continue
        x_f = float(x)
        y_f = float(y)
        w_f = float(w)
        h_f = float(h)
        top_px = crop.top + crop.height * (1 - y_f - h_f)
        mid_px = top_px + crop.height * h_f / 2
        items.append(OcrItem(x_f, mid_px, w_f, crop.height * h_f, text.strip()))
    return dedupe_items(items)


def dedupe_items(items: list[OcrItem]) -> list[OcrItem]:
    seen = set()
    output = []
    for item in sorted(items, key=lambda value: (value.y, value.x, value.text)):
        key = (round(item.x, 3), round(item.y / 8), item.text)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def group_items_by_row(items: list[OcrItem]) -> list[list[OcrItem]]:
    rows: list[list[OcrItem]] = []
    for item in sorted(items, key=lambda value: (value.y, value.x)):
        if not item.text:
            continue
        for row in rows:
            row_y = sum(entry.y for entry in row) / len(row)
            if abs(row_y - item.y) <= 18:
                row.append(item)
                break
        else:
            rows.append([item])
    for row in rows:
        row.sort(key=lambda value: value.x)
    return rows


def clean_int_text(value: object) -> str:
    text = norm(value)
    text = text.replace("O", "0").replace("o", "0").replace("S", "5").replace("l", "1")
    return re.sub(r"\D", "", text)


def clean_number_text(value: object) -> str:
    text = norm(value)
    text = text.replace("O", "0").replace("o", "0").replace("S", "5").replace("l", "1")
    match = re.search(r"\d+(?:\.\d+)?", text)
    return match.group(0) if match else ""


def text_in(row: list[OcrItem], min_x: float, max_x: float) -> str:
    return "".join(item.text for item in row if min_x <= item.x <= max_x).strip()


def major_text_in(row: list[OcrItem], min_x: float, max_x: float) -> str:
    fragments = []
    for item in row:
        if not (min_x <= item.x <= max_x):
            continue
        text = item.text.strip()
        if re.fullmatch(r"[A-Za-z0-9口OAa.。 ]+", text):
            continue
        fragments.append(text)
    return "".join(fragments).strip()


def first_int(row: list[OcrItem], min_x: float, max_x: float) -> str:
    for item in row:
        if min_x <= item.x <= max_x:
            value = clean_int_text(item.text)
            if value:
                return value
    return ""


def first_int_between(row: list[OcrItem], min_x: float, max_x: float, low: int, high: int) -> str:
    for item in row:
        if min_x <= item.x <= max_x:
            value = clean_int_text(item.text)
            if value and low <= int(value) <= high:
                return value
    return ""


def first_number(row: list[OcrItem], min_x: float, max_x: float) -> str:
    for item in row:
        if min_x <= item.x <= max_x:
            value = clean_number_text(item.text)
            if value:
                return value
    return ""


def first_number_between(row: list[OcrItem], min_x: float, max_x: float, low: int, high: int) -> str:
    for item in row:
        if min_x <= item.x <= max_x:
            value = clean_number_text(item.text)
            if value and low <= float(value) <= high:
                return value
    return ""


def normalize_major(value: str) -> str:
    text = value.replace(" ", "").replace("\u3000", "")
    text = text.replace("（", "（").replace("）", "）")
    text = text.replace("家取", "录取")
    text = re.sub(r"[口OAa.。]+$", "", text)
    if len(text) % 2 == 0 and text[: len(text) // 2] == text[len(text) // 2 :]:
        text = text[: len(text) // 2]
    return text.strip("，,、")


def classify_heading(text: str) -> Section | None:
    if "广东工业大学" not in text or "录取情" not in text:
        return None
    excluded = any(word in text for word in ["艺术", "美术", "统考"])
    if "物理" in text:
        track = "物理类"
    elif "历史" in text:
        track = "历史类"
    else:
        track = ""
    if "地方专项" in text:
        plan_type = "地方专项"
    elif "国际班" in text or "中外" in text or "中英" in text or "中德" in text or "中澳" in text:
        plan_type = "国际班"
    else:
        plan_type = "普通类"
    return Section(0, text, track, plan_type, excluded)


def sections_from_items(items: list[OcrItem]) -> list[Section]:
    sections: list[Section] = []
    for item in items:
        section = classify_heading(item.text)
        if section is None:
            continue
        section.y = item.y
        sections.append(section)
    sections.sort(key=lambda value: value.y)
    return sections


def section_for_y(sections: list[Section], y: float) -> Section | None:
    current = None
    for section in sections:
        if section.y <= y:
            current = section
        else:
            break
    return current


def nearest_group(items: list[OcrItem], row_y: float) -> str:
    candidates = []
    for item in items:
        if item.x > 0.09:
            continue
        value = clean_int_text(item.text)
        if len(value) != 3:
            continue
        candidates.append((abs(item.y - row_y), value))
    candidates.sort(key=lambda pair: pair[0])
    if candidates and candidates[0][0] <= 420:
        return candidates[0][1]
    return ""


def valid_row(row: dict[str, str]) -> bool:
    try:
        admit_count = int(row["admit_count"])
        min_score = int(row["min_score"])
        min_rank = int(row["min_rank"])
        max_score = int(row["notes"].split("最高分=", 1)[1].split("；", 1)[0])
    except (ValueError, IndexError):
        return False
    if not (1 <= admit_count <= 5000):
        return False
    if not (350 <= min_score <= 700):
        return False
    if not (1 <= min_rank <= 300000):
        return False
    return min_score <= max_score


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
    sections = sections_from_items(items)
    all_rows = group_items_by_row(items)

    for row in all_rows:
        row_y = sum(item.y for item in row) / len(row)
        section = section_for_y(sections, row_y)
        if section is None or section.excluded or section.track != track:
            continue
        raw_text = "".join(item.text for item in row)
        if any(word in raw_text for word in ["专业组", "专业名称", "录取数", "最高分", "最低分"]):
            continue

        major_name = normalize_major(major_text_in(row, 0.23, 0.56))
        continuation = bool(major_name.startswith(("（", "(")))
        admit_count = first_int(row, 0.54, 0.62)
        max_score = first_int_between(row, 0.61, 0.69, 350, 700)
        avg_score = first_number_between(row, 0.68, 0.76, 350, 700)
        min_score = first_int_between(row, 0.74, 0.82, 350, 700)
        high_rank = first_int(row, 0.81, 0.90)
        min_rank = first_int(row, 0.89, 0.99)

        if continuation and rows:
            previous = rows[-1]
            if previous["track"] == section.track and previous["year"] == str(year):
                previous["major_name"] = f"{previous['major_name']}{major_name}"
            continue

        if not (major_name and admit_count and max_score and min_score and min_rank):
            continue
        if any(word in major_name for word in ["学院", "专业名称", "广东工业大学"]):
            continue

        row_record = {
            "year": str(year),
            "province": "广东",
            "track": section.track,
            "batch": batch,
            "school_name": SCHOOL_NAME,
            "school_code": school_code,
            "major_group": first_int(row, 0.00, 0.09) or nearest_group(items, row_y),
            "major_name": major_name,
            "plan_type": section.plan_type,
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
                    f"栏目={section.title}",
                    f"最高分={max_score}",
                    f"平均分={avg_score}" if avg_score else "",
                    f"最高排位={high_rank}" if high_rank else "",
                ]
                if part
            ),
        }
        if valid_row(row_record):
            rows.append(row_record)
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output = []
    for row in rows:
        key = (
            row["year"],
            row["track"],
            row["major_group"],
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
            article_url, image_url = PAGES[year]
            image_path = work_dir / f"gdut_{year}.png"
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
    unsupported = sorted(set(years) - set(PAGES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"GDUT importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GDUT official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="11845")
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
    print("# 广东工业大学专业录取分数导入\n")
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
