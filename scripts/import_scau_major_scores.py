#!/usr/bin/env python3
"""Import South China Agricultural University official Guangdong major scores."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

try:
    from PIL import Image
except ImportError:  # pragma: no cover - environment hint
    print(
        "This importer needs Pillow. Run it with the bundled Python: "
        "/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
        file=sys.stderr,
    )
    raise


SOURCE_NAME = "华南农业大学本科招生网"
SCHOOL_NAME = "华南农业大学"
PAGES = {
    "物理类": "https://zsb.scau.edu.cn/_s112/2025/1030/c8596a420950/page.psp",
    "历史类": "https://zsb.scau.edu.cn/_s112/2025/1030/c8596a420943/page.psp",
}

IMAGE_COLUMN_EDGES = [0, 140, 376, 431, 486, 557, 627, 697, 767]
NUMERIC_COLUMNS = [2, 3, 4, 5, 6, 7]

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


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        attr_map = dict(attrs)
        src = attr_map.get("original-src") or attr_map.get("src")
        if src and "_upload/article/images" in src:
            self.images.append(src)


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def int_text(value: object) -> str:
    return re.sub(r"\D", "", norm(value).replace(",", ""))


def valid_rank(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    return text if number >= 1000 else ""


def valid_score(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 300 <= number <= 750 else ""


def clean_major_name(value: str) -> str:
    text = value.replace(" ", "").replace("|", "")
    if text.count("（") > text.count("）"):
        text += "）"
    return text


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urlopen(request, timeout=60).read().decode("utf-8", "ignore")


def page_images(url: str) -> list[str]:
    parser = ImageParser()
    parser.feed(fetch_text(url))
    return [urljoin(url, src) for src in parser.images]


def download(url: str, dest: Path, referer: str) -> None:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": referer})
    dest.write_bytes(urlopen(request, timeout=60).read())


def run_ocr(script: Path, images: list[Path]) -> list[dict[str, object]]:
    cmd = ["swift", str(script), *[str(path) for path in images]]
    proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    rows: list[dict[str, object]] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 6:
            continue
        path, x, y, w, h, text = parts
        rows.append(
            {
                "path": path,
                "x": float(x),
                "y": float(y),
                "w": float(w),
                "h": float(h),
                "cx": float(x) + float(w) / 2,
                "cy": float(y) + float(h) / 2,
                "text": text.strip(),
            }
        )
    return rows


def dark_lines(image_path: Path, x0: int, x1: int, min_count: int) -> tuple[list[int], int, int]:
    image = Image.open(image_path).convert("L")
    width, height = image.size
    pixels = image.load()
    hits: list[int] = []
    for y in range(height):
        count = sum(1 for x in range(max(0, x0), min(width, x1)) if pixels[x, y] < 80)
        if count >= min_count:
            hits.append(y)
    groups: list[list[int]] = []
    for y in hits:
        if not groups or y - groups[-1][-1] > 1:
            groups.append([y])
        else:
            groups[-1].append(y)
    return [(group[0] + group[-1]) // 2 for group in groups], width, height


def top_y(item: dict[str, object], image_height: int) -> float:
    return (1.0 - float(item["cy"])) * image_height


def assign_numeric(row_items: list[dict[str, object]], image_width: int) -> dict[int, str]:
    values: dict[int, list[str]] = {column: [] for column in NUMERIC_COLUMNS}
    centers = {column: (IMAGE_COLUMN_EDGES[column] + IMAGE_COLUMN_EDGES[column + 1]) / 2 for column in NUMERIC_COLUMNS}
    for item in row_items:
        text = str(item["text"]).replace("|", "")
        if not re.search(r"\d|/", text):
            continue
        if any(header in text for header in ["2025", "2024", "2023", "录取数", "最低"]):
            continue
        tokens = re.findall(r"\d+|/", text)
        if not tokens:
            continue
        x0 = float(item["x"]) * image_width
        x1 = (float(item["x"]) + float(item["w"])) * image_width
        center = float(item["cx"]) * image_width
        if len(tokens) > 1:
            for index, token in enumerate(tokens):
                estimate = x0 + (x1 - x0) * (index + 0.5) / len(tokens)
                column = min(NUMERIC_COLUMNS, key=lambda col: abs(centers[col] - estimate))
                values[column].append(token)
        else:
            column = min(NUMERIC_COLUMNS, key=lambda col: abs(centers[col] - center))
            values[column].append(tokens[0])
    output: dict[int, str] = {}
    for column, tokens in values.items():
        if not tokens:
            output[column] = ""
        elif len(tokens) > 1 and all(len(token) <= 3 for token in tokens):
            output[column] = "".join(tokens)
        else:
            output[column] = tokens[0]
    return output


def group_text_for_row(
    items: list[dict[str, object]],
    *,
    image_width: int,
    image_height: int,
    group_bounds: list[int],
    row_mid: float,
) -> str:
    previous_bounds = [bound for bound in group_bounds if bound <= row_mid]
    next_bounds = [bound for bound in group_bounds if bound > row_mid]
    y0 = previous_bounds[-1] if previous_bounds else 0
    y1 = next_bounds[0] if next_bounds else image_height
    pieces: list[tuple[float, float, str]] = []
    for item in items:
        center_x = float(item["cx"]) * image_width
        y = top_y(item, image_height)
        text = str(item["text"])
        if 0 <= center_x < IMAGE_COLUMN_EDGES[1] and y0 <= y < y1 and re.search(r"[\u4e00-\u9fff]", text):
            if "专业组" not in text:
                pieces.append((y, center_x, text))
    return "".join(text for _, _, text in sorted(pieces)).replace(" ", "")


def plan_type(group: str, major_name: str) -> str:
    text = f"{group} {major_name}"
    if "地方专项" in text:
        return "地方专项"
    if "国际班" in text:
        return "国际班"
    if "提前" in text:
        return "提前批"
    return "普通类"


def batch_for_group(group: str) -> str:
    return "提前批本科" if "提前" in group else "本科批"


def row_notes(year: int, avg_rank: str, image_url: str, score_from_source: bool) -> str:
    parts = ["学校官网近三年图片表经OCR导入"]
    if avg_rank:
        parts.append(f"平均排位={avg_rank}")
    if not score_from_source:
        parts.append("官网表仅发布最低排位，最低分需由同年广东一分一段表补齐")
    parts.append(f"图片源={image_url}")
    return "；".join(parts)


def parse_image(
    args: argparse.Namespace,
    *,
    image_path: Path,
    image_url: str,
    source_url: str,
    items: list[dict[str, object]],
) -> list[dict[str, str]]:
    row_lines, image_width, image_height = dark_lines(image_path, 0, 767, int(767 * 0.35))
    group_bounds, _, _ = dark_lines(image_path, 0, 141, 80)
    image_items = [item for item in items if Path(str(item["path"])).name == image_path.name]
    rows: list[dict[str, str]] = []
    for y0, y1 in zip(row_lines, row_lines[1:]):
        if y1 - y0 < 8:
            continue
        row_mid = (y0 + y1) / 2
        row_items = [item for item in image_items if y0 <= top_y(item, image_height) < y1]
        name_pieces: list[tuple[float, float, str]] = []
        for item in row_items:
            center_x = float(item["cx"]) * image_width
            text = str(item["text"])
            if IMAGE_COLUMN_EDGES[1] <= center_x < IMAGE_COLUMN_EDGES[2] and re.search(r"[\u4e00-\u9fffA-Za-z]", text):
                if not any(skip in text for skip in ["专业名称", "广东省", "备注"]):
                    name_pieces.append((top_y(item, image_height), center_x, text))
        numeric = assign_numeric(row_items, image_width)
        if not name_pieces:
            continue
        major_name = clean_major_name("".join(text for _, _, text in sorted(name_pieces)))
        if not major_name or "录取情况" in major_name:
            continue
        group = group_text_for_row(
            image_items,
            image_width=image_width,
            image_height=image_height,
            group_bounds=group_bounds,
            row_mid=row_mid,
        )
        if not group:
            continue
        admit_count = int_text(numeric.get(2))
        min_score_2025 = valid_score(numeric.get(3))
        avg_rank_2025 = valid_rank(numeric.get(4))
        min_rank_2025 = valid_rank(numeric.get(5))
        rank_2024 = valid_rank(numeric.get(6))
        rank_2023 = valid_rank(numeric.get(7))
        if min_score_2025 or min_rank_2025:
            rows.append(
                {
                    "year": "2025",
                    "province": args.province,
                    "track": args.track,
                    "batch": batch_for_group(group),
                    "school_name": SCHOOL_NAME,
                    "school_code": args.school_code,
                    "major_group": group,
                    "major_name": major_name,
                    "plan_type": plan_type(group, major_name),
                    "min_score": min_score_2025,
                    "min_rank": min_rank_2025,
                    "admit_count": admit_count,
                    "source_url": source_url,
                    "source_name": SOURCE_NAME,
                    "notes": row_notes(2025, avg_rank_2025, image_url, bool(min_score_2025)),
                }
            )
        for year, rank in [(2024, rank_2024), (2023, rank_2023)]:
            if not rank:
                continue
            rows.append(
                {
                    "year": str(year),
                    "province": args.province,
                    "track": args.track,
                    "batch": batch_for_group(group),
                    "school_name": SCHOOL_NAME,
                    "school_code": args.school_code,
                    "major_group": group,
                    "major_name": major_name,
                    "plan_type": plan_type(group, major_name),
                    "min_score": "",
                    "min_rank": rank,
                    "admit_count": "",
                    "source_url": source_url,
                    "source_name": SOURCE_NAME,
                    "notes": row_notes(year, "", image_url, False),
                }
            )
    return dedupe_rows(rows)


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    script = Path(__file__).resolve().parent / "vision_ocr_image_zh.swift"
    source_url = PAGES[args.track]
    image_urls = page_images(source_url)
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="scau_major_") as tmp_raw:
        tmp = Path(tmp_raw)
        image_paths: list[Path] = []
        for index, image_url in enumerate(image_urls):
            ext = image_url.rsplit(".", 1)[-1].split("?", 1)[0] or "jpg"
            image_path = tmp / f"scau_{args.track}_{index}.{ext}"
            download(image_url, image_path, source_url)
            image_paths.append(image_path)
        ocr_items = run_ocr(script, image_paths)
        for image_path, image_url in zip(image_paths, image_urls):
            rows.extend(
                parse_image(
                    args,
                    image_path=image_path,
                    image_url=image_url,
                    source_url=source_url,
                    items=ocr_items,
                )
            )
    selected_years = {str(year) for year in args.years}
    return dedupe_rows([row for row in rows if row["year"] in selected_years])


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (
            row["year"],
            row["track"],
            row["batch"],
            row["major_group"],
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
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"SCAU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import South China Agricultural University official Guangdong major-level scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
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
    missing_score = 0
    for row in rows:
        by_year[row["year"]] = by_year.get(row["year"], 0) + 1
        by_plan[row["plan_type"]] = by_plan.get(row["plan_type"], 0) + 1
        if not row["min_score"]:
            missing_score += 1
    print("# 华南农业大学专业录取分数导入\n")
    print(f"- 来源：{PAGES[args.track]}")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(year) for year in args.years)}")
    print(f"- 获取专业记录：{len(rows)}；分年：{by_year}；类型：{by_plan}")
    print(f"- 缺最低分记录：{missing_score}（可用 fill_admission_scores_from_rank.py 按位次补齐）")
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
