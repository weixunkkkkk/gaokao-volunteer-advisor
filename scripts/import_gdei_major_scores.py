#!/usr/bin/env python3
"""Import Guangdong University of Education official Guangdong major scores."""

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
except ImportError:
    print(
        "This importer needs Pillow. Run it with the bundled Python: "
        "python3",
        file=sys.stderr,
    )
    raise


SOURCE_NAME = "广东第二师范学院招生办公室"
SCHOOL_NAME = "广东第二师范学院"
PAGES = {
    2025: "https://web.gdei.edu.cn/zsb/2025/1106/c58a101900/page.htm",
    2024: "https://web.gdei.edu.cn/zsb/2024/1115/c58a94587/page.htm",
    2023: "https://web.gdei.edu.cn/zsb/2023/1115/c58a86995/page.htm",
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


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        src = dict(attrs).get("src")
        if src and "_upload/article/images" in src:
            self.images.append(src)


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def int_text(value: object) -> str:
    return re.sub(r"\D", "", norm(value).replace(",", ""))


def score_text(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 300 <= number <= 750 else ""


def rank_text(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    if number > 500000 and text.startswith("1") and int(text[1:] or "0") <= 500000:
        text = text[1:]
        number = int(text)
    if number > 500000 and len(text) > 1 and int(text[:-1] or "0") <= 500000:
        text = text[:-1]
        number = int(text)
    return text if number >= 1 else ""


def count_text(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    if number > 1000 and len(text) >= 4:
        if len(text) == 4 and text[:2] in {str(value) for value in range(49, 59)}:
            return str(int(text[2:]))
        suffix = text[-3:]
        if int(suffix) == 0:
            suffix = text[-2:]
        if 1 <= int(suffix) <= 999:
            return str(int(suffix))
    return text if number <= 999 else ""


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urlopen(request, timeout=60).read().decode("utf-8", "ignore")


def page_image(url: str) -> str:
    parser = ImageParser()
    parser.feed(fetch_text(url))
    images = [urljoin(url, src) for src in parser.images]
    if not images:
        raise RuntimeError(f"No article image found: {url}")
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
    verticals: list[int] = []
    for x in range(width):
        count = sum(1 for y in range(height) if pixels[x, y] < 90)
        if count > height * 0.75:
            verticals.append(x)
    edges = line_groups(verticals)
    if not edges or edges[0] > 3:
        edges = [0] + edges
    if edges[-1] < width - 3:
        edges.append(width - 1)
    if len(edges) != 8:
        raise RuntimeError(f"Unexpected Guangdong University of Education column lines in {image_path}: {edges}")

    horizontals: list[int] = []
    for y in range(height):
        count = sum(1 for x in range(width) if pixels[x, y] < 90)
        if count > width * 0.45:
            horizontals.append(y)
    row_lines = line_groups(horizontals)
    return edges, row_lines, width, height


def top_y(item: dict[str, object], image_height: int) -> float:
    return (1.0 - float(item["cy"])) * image_height


def clean_text(value: str) -> str:
    text = value.replace("|", "").replace(" ", "").strip()
    text = re.sub(r"^[·•、]+", "", text)
    return text


def clean_major_name(value: str) -> str:
    text = clean_text(value)
    text = re.sub(r"(?<!（)师范）", "（师范）", text)
    if text.count("（") > text.count("）"):
        text += "）"
    return text


def clean_group_label(value: str) -> str:
    text = clean_text(value)
    match = re.match(r"^(\d{3}[\.\s]*(?:物理组|历史组)(?:[-—－][\u4e00-\u9fffA-Za-z（）]+)?)", text)
    if match:
        return match.group(1).replace(" ", "")
    return text


def cell_texts(
    row_items: list[dict[str, object]],
    *,
    edges: list[int],
    column: int,
    image_width: int,
) -> list[str]:
    pieces: list[tuple[float, str]] = []
    left, right = edges[column], edges[column + 1]
    for item in row_items:
        center_x = float(item["cx"]) * image_width
        if left <= center_x < right:
            pieces.append((center_x, str(item["text"]).strip()))
    return [text for _, text in sorted(pieces)]


def numeric_value(
    row_items: list[dict[str, object]],
    *,
    edges: list[int],
    column: int,
    image_width: int,
) -> str:
    texts = cell_texts(row_items, edges=edges, column=column, image_width=image_width)
    text = "".join(texts).replace("|", "")
    numbers = re.findall(r"\d+(?:\.\d+)?", text)
    return numbers[0] if numbers else ""


def target_group(label: str, track: str) -> bool:
    if track == "物理类":
        return "物理组" in label
    return "历史组" in label


def plan_type(group_label: str, major_name: str) -> str:
    text = f"{group_label}{major_name}"
    if "协同培养" in text:
        return "协同培养"
    if "学分互认" in text or "中外人才培养" in text:
        return "学分互认"
    return "普通类"


def parse_image(
    args: argparse.Namespace,
    *,
    year: int,
    source_url: str,
    image_url: str,
    image_path: Path,
    ocr_items: list[dict[str, object]],
) -> list[dict[str, str]]:
    edges, row_lines, image_width, image_height = table_lines(image_path)
    image_items = [item for item in ocr_items if Path(str(item["path"])).name == image_path.name]
    rows: list[dict[str, str]] = []
    current_group = ""
    import_current_group = False
    for y0, y1 in zip(row_lines, row_lines[1:]):
        if y1 - y0 < 8:
            continue
        row_items = [item for item in image_items if y0 <= top_y(item, image_height) < y1]
        first_col = clean_text("".join(cell_texts(row_items, edges=edges, column=0, image_width=image_width)))
        if not first_col:
            continue
        if re.match(r"^\d{3}[\.\s]*(?:物理|历史|音乐|美术|书法|体育)", first_col):
            current_group = clean_group_label(first_col)
            import_current_group = target_group(current_group, args.track)
            continue
        if not import_current_group:
            continue
        if any(token in first_col for token in ["专业组", "广东第二师范", "备注"]):
            continue
        major_name = clean_major_name(first_col)
        min_score = score_text(numeric_value(row_items, edges=edges, column=3, image_width=image_width))
        if not major_name or not min_score:
            continue
        min_rank = rank_text(numeric_value(row_items, edges=edges, column=6, image_width=image_width))
        admit_count = count_text(numeric_value(row_items, edges=edges, column=1, image_width=image_width))
        highest_score = score_text(numeric_value(row_items, edges=edges, column=2, image_width=image_width))
        average_score = norm(numeric_value(row_items, edges=edges, column=4, image_width=image_width))
        highest_rank = rank_text(numeric_value(row_items, edges=edges, column=5, image_width=image_width))
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": args.track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": current_group.split(".", 1)[0],
                "major_name": major_name,
                "plan_type": plan_type(current_group, major_name),
                "min_score": min_score,
                "min_rank": min_rank,
                "admit_count": admit_count,
                "source_url": source_url,
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        f"专业组={current_group}",
                        "学校官网图片表经OCR和表格线解析导入；只导入普通物理/历史本科专业组，不含艺体类",
                        f"最高分={highest_score}" if highest_score else "",
                        f"平均分={average_score}" if average_score else "",
                        f"最高排位={highest_rank}" if highest_rank else "",
                        f"图片源={image_url}",
                    ]
                    if part
                ),
            }
        )
    return dedupe_rows(rows)


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    script = Path(__file__).resolve().parent / "vision_ocr_image_zh.swift"
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="gdei_major_") as tmp_raw:
        tmp = Path(tmp_raw)
        image_paths: list[tuple[int, str, Path]] = []
        for year in args.years:
            source_url = PAGES[year]
            image_url = page_image(source_url)
            ext = image_url.rsplit(".", 1)[-1].split("?", 1)[0] or "png"
            image_path = tmp / f"gdei_{year}.{ext}"
            download(image_url, image_path, source_url)
            image_paths.append((year, image_url, image_path))
        ocr_items = run_ocr(script, [path for _, _, path in image_paths])
        for year, image_url, image_path in image_paths:
            rows.extend(
                parse_image(
                    args,
                    year=year,
                    source_url=PAGES[year],
                    image_url=image_url,
                    image_path=image_path,
                    ocr_items=ocr_items,
                )
            )
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["major_group"], row["major_name"], row["plan_type"])
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
        raise argparse.ArgumentTypeError(f"GDEI importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Guangdong University of Education official Guangdong major-level scores.")
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
    print("# 广东第二师范学院专业录取分数导入\n")
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
