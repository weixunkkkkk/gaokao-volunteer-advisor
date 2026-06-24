#!/usr/bin/env python3
"""Import GDUF official major-level admission scores for Guangdong.

Source: 广东金融学院信息公开网录取结果 image tables. The official pages publish
2023 and 2024 Guangdong major-level admission score images. This importer uses
macOS Vision OCR through `vision_ocr_image_zh.swift`; run in dry-run mode first.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OCR_SCRIPT = ROOT / "scripts" / "vision_ocr_image_zh.swift"
SOURCE_NAME = "广东金融学院信息公开网"
SCHOOL_NAME = "广东金融学院"
LIST_URL = "https://xxgk.gduf.edu.cn/xxgklm/zsksxx/lqjg.htm"
PAGES = {
    2024: {
        ("历史类", "普通类"): "https://xxgk.gduf.edu.cn/info/1024/2147.htm",
        ("历史类", "国际班"): "https://xxgk.gduf.edu.cn/info/1024/2148.htm",
        ("历史类", "地方专项"): "https://xxgk.gduf.edu.cn/info/1024/2149.htm",
        ("物理类", "普通类"): "https://xxgk.gduf.edu.cn/info/1024/2150.htm",
        ("物理类", "国际班"): "https://xxgk.gduf.edu.cn/info/1024/2151.htm",
        ("物理类", "地方专项"): "https://xxgk.gduf.edu.cn/info/1024/2152.htm",
    },
    2023: {
        ("历史类", "普通类"): "https://xxgk.gduf.edu.cn/info/1024/2139.htm",
        ("历史类", "国际班"): "https://xxgk.gduf.edu.cn/info/1024/2140.htm",
        ("历史类", "地方专项"): "https://xxgk.gduf.edu.cn/info/1024/2141.htm",
        ("物理类", "普通类"): "https://xxgk.gduf.edu.cn/info/1024/2142.htm",
        ("物理类", "国际班"): "https://xxgk.gduf.edu.cn/info/1024/2143.htm",
        ("物理类", "地方专项"): "https://xxgk.gduf.edu.cn/info/1024/2144.htm",
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
    path: str
    x: float
    y: float
    w: float
    h: float
    text: str


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def fetch_html(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urlopen(request, timeout=30).read().decode("utf-8", "replace")


def content_image_urls(page_url: str) -> list[str]:
    html = fetch_html(page_url)
    urls: list[str] = []
    for tag in re.findall(r"<img[^>]+>", html, flags=re.I):
        if "img_vsb_content" not in tag and "__local" not in tag:
            continue
        match = re.search(r"src=[\"']([^\"']+)", tag, flags=re.I)
        if match and "__local" in match.group(1):
            urls.append(urljoin(page_url, match.group(1)))
    return urls


def download_images(urls: list[str], work_dir: Path, prefix: str) -> list[Path]:
    output: list[Path] = []
    for index, url in enumerate(urls, start=1):
        ext = ".png" if ".png" in url.lower() else ".jpg"
        path = work_dir / f"{prefix}_{index}{ext}"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        path.write_bytes(urlopen(request, timeout=30).read())
        output.append(path)
    return output


def run_ocr(paths: list[Path]) -> list[OcrItem]:
    if not paths:
        return []
    result = subprocess.run(
        ["swift", str(OCR_SCRIPT), *[str(path) for path in paths]],
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
        items.append(OcrItem(path, float(x), float(y), float(w), float(h), text.strip()))
    return items


def is_int(text: str) -> bool:
    return bool(re.fullmatch(r"\d+", text))


def is_number(text: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:\.\d+)?", text))


def clean_int_text(text: str) -> str:
    cleaned = text.replace("O", "0").replace("o", "0").replace("S", "5")
    cleaned = re.sub(r"\D", "", cleaned)
    return cleaned


def clean_number_text(text: str) -> str:
    cleaned = text.replace("O", "0").replace("o", "0").replace("S", "5")
    match = re.search(r"\d+(?:\.\d+)?", cleaned)
    return match.group(0) if match else ""


def group_items_by_row(items: list[OcrItem]) -> list[list[OcrItem]]:
    rows: list[list[OcrItem]] = []
    for item in sorted(items, key=lambda value: (-value.y, value.x)):
        if not item.text:
            continue
        for row in rows:
            row_y = sum(entry.y for entry in row) / len(row)
            if abs(row_y - item.y) <= 0.018:
                row.append(item)
                break
        else:
            rows.append([item])
    for row in rows:
        row.sort(key=lambda value: value.x)
    return rows


def nearest_group(items: list[OcrItem], row_y: float) -> str:
    candidates = []
    for item in items:
        if item.x > 0.16:
            continue
        if "组" not in item.text:
            continue
        match = re.search(r"(\d{3})", item.text)
        if not match:
            continue
        candidates.append((abs(item.y - row_y), match.group(1)))
    candidates.sort(key=lambda pair: pair[0])
    if candidates and candidates[0][0] < 0.12:
        return candidates[0][1]
    return ""


def text_in(row: list[OcrItem], min_x: float, max_x: float) -> str:
    return "".join(item.text for item in row if min_x <= item.x <= max_x).strip()


def first_text(row: list[OcrItem], min_x: float, max_x: float, pattern) -> str:
    values = [item.text for item in row if min_x <= item.x <= max_x and pattern(item.text)]
    return values[0] if values else ""


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


def clean_major_name(value: str, plan_type: str) -> str:
    text = value.replace(" ", "")
    text = text.replace("（地方专项）", "").replace("(地方专项)", "")
    text = text.replace("（国际班）", "").replace("(国际班)", "")
    text = text.replace("信思与计算科学", "信息与计算科学")
    text = text.replace("3+x", "3+X")
    text = text.strip("、，,")
    return text


def group_from_row(row: list[OcrItem], min_x: float, max_x: float) -> str:
    text = text_in(row, min_x, max_x)
    match = re.search(r"(\d{3})", text)
    return match.group(1) if match else ""


def parse_ocr_items(
    *,
    items: list[OcrItem],
    year: int,
    track: str,
    plan_type: str,
    page_url: str,
    batch: str,
    school_code: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    by_path: dict[str, list[OcrItem]] = defaultdict(list)
    for item in items:
        by_path[item.path].append(item)
    for image_items in by_path.values():
        code_layout = any("专业代号" in item.text for item in image_items)
        for row in group_items_by_row(image_items):
            row_y = sum(item.y for item in row) / len(row)
            if code_layout:
                major_name = clean_major_name(text_in(row, 0.08, 0.25), plan_type)
                major_group = group_from_row(row, 0.25, 0.43)
                admit_count = first_int(row, 0.38, 0.49)
                max_score = first_int(row, 0.49, 0.58)
                min_score = first_int(row, 0.58, 0.67)
                avg_score = first_number(row, 0.68, 0.77)
                high_rank = first_int(row, 0.79, 0.88)
                min_rank = first_int(row, 0.90, 0.99)
            else:
                major_name = clean_major_name(text_in(row, 0.15, 0.44), plan_type)
                major_group = nearest_group(image_items, row_y)
                admit_count = first_int(row, 0.44, 0.52)
                max_score = first_int(row, 0.52, 0.60)
                min_score = first_int(row, 0.60, 0.68)
                avg_score = first_number(row, 0.68, 0.78)
                high_rank = first_int(row, 0.78, 0.88)
                min_rank = first_int(row, 0.88, 0.99)
            if not (major_name and admit_count and max_score and min_score and min_rank):
                continue
            if any(word in major_name for word in ["专业名称", "录取人数", "广东金融学院"]):
                continue
            rows.append(
                {
                    "year": str(year),
                    "province": "广东",
                    "track": track,
                    "batch": batch,
                    "school_name": SCHOOL_NAME,
                    "school_code": school_code,
                    "major_group": major_group,
                    "major_name": major_name,
                    "plan_type": plan_type,
                    "min_score": min_score,
                    "min_rank": min_rank,
                    "admit_count": admit_count,
                    "source_url": page_url,
                    "source_name": SOURCE_NAME,
                    "notes": "；".join(
                        part
                        for part in [
                            "学校官网图片OCR专业录取分数",
                            f"最高分={max_score}",
                            f"平均分={avg_score}" if avg_score else "",
                            f"最高排位={high_rank}" if high_rank else "",
                        ]
                        if part
                    ),
                }
            )
    return rows


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        for year in args.years:
            pages = PAGES.get(year, {})
            for (track, plan_type), page_url in pages.items():
                if track != args.track:
                    continue
                image_urls = content_image_urls(page_url)
                image_paths = download_images(image_urls, work_dir, f"{year}_{track}_{plan_type}")
                ocr_items = run_ocr(image_paths)
                output.extend(
                    parse_ocr_items(
                        items=ocr_items,
                        year=year,
                        track=track,
                        plan_type=plan_type,
                        page_url=page_url,
                        batch=args.batch,
                        school_code=args.school_code,
                    )
                )
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
        raise argparse.ArgumentTypeError(f"official GDUF major-score pages are currently mapped for 2023/2024 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GDUF official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True)
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="")
    parser.add_argument("--years", type=parse_years, default=[2023, 2024])
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
    print("# 广东金融学院专业录取分数导入\n")
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
