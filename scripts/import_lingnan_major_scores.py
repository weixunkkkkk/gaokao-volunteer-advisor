#!/usr/bin/env python3
"""Import Lingnan Normal University official Guangdong major scores."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from io import StringIO
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

try:
    import pandas as pd
    from PIL import Image
except ImportError:
    print(
        "This importer needs pandas and Pillow. Run it with the bundled Python: "
        "python3",
        file=sys.stderr,
    )
    raise


SOURCE_NAME = "岭南师范学院招生信息网"
SCHOOL_NAME = "岭南师范学院"
SCHOOL_CODE = "10579"
PAGES = {
    2025: "https://zsb.lingnan.edu.cn/info/1032/8018.htm",
    2024: "https://zsb.lingnan.edu.cn/info/1032/6748.htm",
    2023: "https://zsb.lingnan.edu.cn/info/1032/4128.htm",
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

TEXT_FIXES = {
    "思根政治教育（师范）": "思想政治教育（师范）",
    "思 政治教育（师范）": "思想政治教育（师范）",
    "教师币专项历史类": "教师专项历史类",
}

MANUAL_RANK_FIXES = {
    (2024, "历史类", "市场营销", "509"): "33688",
}


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        attr = dict(attrs)
        src = attr.get("orisrc") or attr.get("src")
        if src and "__local" in src:
            self.images.append(src)


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def clean_text(value: object) -> str:
    text = norm(value).replace("\u3000", "").replace(" ", "")
    text = text.replace("|", "").replace("（ ", "（").replace(" ）", "）")
    text = re.sub(r"\s+", "", text)
    return TEXT_FIXES.get(text, text)


def int_text(value: object) -> str:
    return re.sub(r"\D", "", norm(value).replace(",", ""))


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


def count_text(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 1 <= number <= 9999 else ""


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urlopen(request, timeout=60).read().decode("utf-8", "ignore")


def page_image(url: str) -> str:
    parser = ImageParser()
    parser.feed(fetch_text(url))
    images = [urljoin(url, src) for src in parser.images]
    if not images:
        raise RuntimeError(f"No official image table found: {url}")
    return images[0]


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


def line_groups(values: list[int]) -> list[int]:
    groups: list[list[int]] = []
    for value in values:
        if not groups or value - groups[-1][-1] > 1:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [(group[0] + group[-1]) // 2 for group in groups]


def table_lines(image_path: Path) -> tuple[list[int], list[int], int, int]:
    image = Image.open(image_path).convert("L")
    width, height = image.size
    pixels = image.load()
    xs: list[int] = []
    for x in range(width):
        count = sum(1 for y in range(height) if pixels[x, y] < 80)
        if count > height * 0.45:
            xs.append(x)
    edges = line_groups(xs)
    while len(edges) > 8:
        gaps = [(edges[index + 1] - edges[index], index) for index in range(len(edges) - 1)]
        _, index = min(gaps)
        del edges[index if index > 0 else index + 1]
    if len(edges) != 8:
        raise RuntimeError(f"Unexpected Lingnan column lines in {image_path}: {edges}")

    ys: list[int] = []
    for y in range(height):
        count = sum(1 for x in range(width) if pixels[x, y] < 80)
        if count > width * 0.45:
            ys.append(y)
    row_lines = line_groups(ys)
    return edges, row_lines, width, height


def top_y(item: dict[str, object], image_height: int) -> float:
    return (1.0 - float(item["cy"])) * image_height


def cell_items(
    items: list[dict[str, object]],
    *,
    edges: list[int],
    column: int,
    y0: int,
    y1: int,
    image_width: int,
    image_height: int,
) -> list[dict[str, object]]:
    left, right = edges[column], edges[column + 1]
    return [
        item
        for item in items
        if left <= float(item["cx"]) * image_width < right and y0 <= top_y(item, image_height) < y1
    ]


def cell_text(
    items: list[dict[str, object]],
    *,
    edges: list[int],
    column: int,
    y0: int,
    y1: int,
    image_width: int,
    image_height: int,
) -> str:
    pieces = cell_items(items, edges=edges, column=column, y0=y0, y1=y1, image_width=image_width, image_height=image_height)
    return clean_text("".join(str(item["text"]) for item in sorted(pieces, key=lambda row: float(row["cx"]))))


def run_cell_ocr(script: Path, cells: list[Path]) -> dict[str, str]:
    if not cells:
        return {}
    items = run_ocr(script, cells)
    by_path: dict[str, list[dict[str, object]]] = {}
    for item in items:
        by_path.setdefault(str(item["path"]), []).append(item)
    output: dict[str, str] = {}
    for path in cells:
        pieces = sorted(by_path.get(str(path), []), key=lambda row: float(row["cx"]))
        output[str(path)] = clean_text("".join(str(row["text"]) for row in pieces))
    return output


def target_category(category: str, track: str) -> bool:
    if track == "历史类":
        return "历史" in category
    return "物理" in category


def plan_type(category: str, major_name: str) -> str:
    text = f"{category}{major_name}"
    if "教师专项" in text:
        return "教师专项"
    if "中外" in text:
        return "中外合作"
    if "协同培养" in text:
        return "协同培养"
    return "普通类"


def clean_major_name(value: str) -> str:
    text = clean_text(value)
    text = re.sub(r"(?<!（)师范）", "（师范）", text)
    if text.count("（") > text.count("）"):
        text += "）"
    return TEXT_FIXES.get(text, text)


def row_from_values(
    args: argparse.Namespace,
    *,
    year: int,
    category: str,
    major_name: str,
    admit_count: str,
    high_score: str,
    min_score: str,
    min_rank: str,
    source_url: str,
    notes: str,
) -> dict[str, str] | None:
    category = clean_text(category)
    major_name = clean_major_name(major_name)
    if not category or not target_category(category, args.track):
        return None
    if any(word in category for word in ["体育", "音乐", "美术", "书法", "舞蹈"]):
        return None
    if not major_name or any(word in category for word in ["艺术"]):
        return None
    min_score_value = score_text(min_score)
    if not min_score_value:
        return None
    plan = plan_type(category, major_name)
    normalized_min_rank = rank_text(min_rank) or MANUAL_RANK_FIXES.get((year, args.track, major_name, min_score_value), "")
    return {
        "year": str(year),
        "province": args.province,
        "track": args.track,
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": "",
        "major_name": major_name,
        "plan_type": plan,
        "min_score": min_score_value,
        "min_rank": normalized_min_rank,
        "admit_count": count_text(admit_count),
        "source_url": source_url,
        "source_name": SOURCE_NAME,
        "notes": "；".join(
            part
            for part in [
                notes,
                f"官网类别={category}",
                f"最高分={score_text(high_score)}" if score_text(high_score) else "",
            ]
            if part
        ),
    }


def parse_html_year(args: argparse.Namespace, year: int, source_url: str) -> list[dict[str, str]]:
    html = fetch_text(source_url)
    table = pd.read_html(StringIO(html))[0]
    rows: list[dict[str, str]] = []
    for _, raw in table.iterrows():
        if norm(raw.iloc[1]) in {"序号", ""}:
            continue
        row = row_from_values(
            args,
            year=year,
            category=norm(raw.iloc[2]),
            major_name=norm(raw.iloc[3]),
            admit_count=norm(raw.iloc[4]),
            high_score=norm(raw.iloc[5]),
            min_score=norm(raw.iloc[6]),
            min_rank=norm(raw.iloc[7]),
            source_url=source_url,
            notes="学校官网HTML表格导入",
        )
        if row:
            rows.append(row)
    return rows


def parse_image_year(args: argparse.Namespace, year: int, source_url: str, image_url: str, image_path: Path) -> list[dict[str, str]]:
    script = Path(__file__).resolve().parent / "vision_ocr_image_zh.swift"
    edges, row_lines, image_width, image_height = table_lines(image_path)
    image_items = run_ocr(script, [image_path])
    image = Image.open(image_path).convert("RGB")
    rows: list[dict[str, str]] = []
    category_paths: list[Path] = []
    cell_paths: list[Path] = []
    numeric_paths: list[Path] = []
    row_meta: list[tuple[int, int, int, str, str, str, str, str, str, str, str, str, str, str]] = []
    with tempfile.TemporaryDirectory(prefix=f"lingnan_{year}_cells_") as tmp_raw:
        tmp = Path(tmp_raw)
        for index, (y0, y1) in enumerate(zip(row_lines[:-1], row_lines[1:])):
            if y1 - y0 < 8:
                continue
            cat_cell = tmp / f"row_{index:03d}_cat.png"
            image.crop((edges[1], y0, edges[2], y1)).resize(((edges[2] - edges[1]) * 4, max(1, (y1 - y0) * 4))).save(cat_cell)
            category_paths.append(cat_cell)
            cell = tmp / f"row_{index:03d}.png"
            image.crop((edges[2], y0, edges[3], y1)).resize(((edges[3] - edges[2]) * 4, max(1, (y1 - y0) * 4))).save(cell)
            cell_paths.append(cell)
            numeric_cells: dict[int, Path] = {}
            for column in [3, 4, 5, 6]:
                num_cell = tmp / f"row_{index:03d}_col_{column}.png"
                image.crop((edges[column], y0, edges[column + 1], y1)).resize(
                    ((edges[column + 1] - edges[column]) * 4, max(1, (y1 - y0) * 4))
                ).save(num_cell)
                numeric_paths.append(num_cell)
                numeric_cells[column] = num_cell
            row_meta.append(
                (
                    index,
                    y0,
                    y1,
                    cell_text(image_items, edges=edges, column=1, y0=y0, y1=y1, image_width=image_width, image_height=image_height),
                    str(cat_cell),
                    cell_text(image_items, edges=edges, column=3, y0=y0, y1=y1, image_width=image_width, image_height=image_height),
                    cell_text(image_items, edges=edges, column=4, y0=y0, y1=y1, image_width=image_width, image_height=image_height),
                    cell_text(image_items, edges=edges, column=5, y0=y0, y1=y1, image_width=image_width, image_height=image_height),
                    cell_text(image_items, edges=edges, column=6, y0=y0, y1=y1, image_width=image_width, image_height=image_height),
                    str(cell),
                    str(numeric_cells[3]),
                    str(numeric_cells[4]),
                    str(numeric_cells[5]),
                    str(numeric_cells[6]),
                )
            )
        major_by_cell = run_cell_ocr(script, cell_paths)
        category_by_cell = run_cell_ocr(script, category_paths)
        number_by_cell = run_cell_ocr(script, numeric_paths)
        for _, _, _, category, cat_cell, admit_count, high_score, min_score, min_rank, cell, count_cell, high_cell, min_cell, rank_cell in row_meta:
            category = category or category_by_cell.get(cat_cell, "")
            if not category or clean_text(category) in {"科类"}:
                continue
            row = row_from_values(
                args,
                year=year,
                category=category,
                major_name=major_by_cell.get(cell, ""),
                admit_count=admit_count or number_by_cell.get(count_cell, ""),
                high_score=high_score or number_by_cell.get(high_cell, ""),
                min_score=min_score or number_by_cell.get(min_cell, ""),
                min_rank=min_rank or number_by_cell.get(rank_cell, ""),
                source_url=source_url,
                notes=f"学校官网图片表经OCR和表格线解析导入；图片源={image_url}",
            )
            if row:
                rows.append(row)
    return rows


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="lingnan_major_") as tmp_raw:
        tmp = Path(tmp_raw)
        for year in args.years:
            source_url = PAGES[year]
            if year == 2025:
                rows.extend(parse_html_year(args, year, source_url))
                continue
            image_url = page_image(source_url)
            ext = image_url.rsplit(".", 1)[-1].split("?", 1)[0] or "png"
            image_path = tmp / f"lingnan_{year}.{ext}"
            download(image_url, image_path, source_url)
            rows.extend(parse_image_year(args, year, source_url, image_url, image_path))
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
    unsupported = sorted(set(years) - set(PAGES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"Lingnan importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Lingnan Normal University official Guangdong major scores.")
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
    print("# 岭南师范学院专业录取分数导入\n")
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
