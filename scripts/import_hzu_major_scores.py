#!/usr/bin/env python3
"""Import Huizhou University official Guangdong major scores."""

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


SOURCE_NAME = "惠州学院招生信息网"
SCHOOL_NAME = "惠州学院"
PAGES = {
    (2025, "物理类"): "https://zs.hzu.edu.cn/2025/1118/c4728a272292/page.htm",
    (2025, "历史类"): "https://zs.hzu.edu.cn/2025/1118/c4728a272293/page.htm",
    (2024, "物理类"): "https://zs.hzu.edu.cn/2024/1129/c4728a262630/page.htm",
    (2024, "历史类"): "https://zs.hzu.edu.cn/2024/1129/c4728a262631/page.htm",
    (2023, "物理类"): "https://zs.hzu.edu.cn/2023/1201/c4728a246725/page.htm",
    (2023, "历史类"): "https://zs.hzu.edu.cn/2023/1201/c4728a246726/page.htm",
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
    return text if number >= 1000 else ""


def clean_major_name(value: str) -> str:
    text = value.replace(" ", "").replace("|", "")
    if text.count("（") > text.count("）"):
        text += "）"
    return text


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


def dark_lines(image_path: Path) -> tuple[list[int], list[int], list[int], int, int]:
    image = Image.open(image_path).convert("L")
    width, height = image.size
    pixels = image.load()
    xs: list[int] = []
    for x in range(width):
        count = sum(1 for y in range(height) if pixels[x, y] < 80)
        if count > height * 0.35:
            xs.append(x)
    ys: list[int] = []
    for y in range(height):
        count = sum(1 for x in range(width) if pixels[x, y] < 80)
        if count > width * 0.35:
            ys.append(y)
    edges = line_groups(xs)
    while len(edges) > 9:
        gaps = [(edges[index + 1] - edges[index], index) for index in range(len(edges) - 1)]
        _, index = min(gaps)
        # The spurious line is usually a dense vertical stroke inside the rank column.
        del edges[index + 1]
    group_bounds: list[int] = []
    group_width = edges[1] if len(edges) > 1 else max(1, width // 10)
    for y in range(height):
        count = sum(1 for x in range(0, group_width + 1) if pixels[x, y] < 80)
        if count > group_width * 0.6:
            group_bounds.append(y)
    return edges, line_groups(ys), line_groups(group_bounds), width, height


def top_y(item: dict[str, object], image_height: int) -> float:
    return (1.0 - float(item["cy"])) * image_height


def assign_numeric(row_items: list[dict[str, object]], edges: list[int], image_width: int) -> dict[int, str]:
    values: dict[int, list[str]] = {column: [] for column in range(2, 8)}
    centers = {column: (edges[column] + edges[column + 1]) / 2 for column in range(2, 8)}
    for item in row_items:
        text = str(item["text"]).replace("|", "")
        if not re.search(r"\d", text):
            continue
        if any(header in text for header in ["专业组", "最高分", "最低分", "平均分", "排位", "录取"]):
            continue
        tokens = re.findall(r"\d+(?:\.\d+)?", text)
        if not tokens:
            continue
        x0 = float(item["x"]) * image_width
        x1 = (float(item["x"]) + float(item["w"])) * image_width
        center = float(item["cx"]) * image_width
        if center < edges[2]:
            continue
        if len(tokens) > 1:
            for index, token in enumerate(tokens):
                estimate = x0 + (x1 - x0) * (index + 0.5) / len(tokens)
                column = min(centers, key=lambda col: abs(centers[col] - estimate))
                values[column].append(token)
        else:
            column = min(centers, key=lambda col: abs(centers[col] - center))
            values[column].append(tokens[0])
    output: dict[int, str] = {}
    for column, tokens in values.items():
        output[column] = tokens[0] if tokens else ""
    return output


def group_for_row(
    image_items: list[dict[str, object]],
    *,
    edges: list[int],
    group_bounds: list[int],
    row_mid: float,
    image_width: int,
    image_height: int,
) -> str:
    previous_bounds = [bound for bound in group_bounds if bound <= row_mid]
    next_bounds = [bound for bound in group_bounds if bound > row_mid]
    y0 = previous_bounds[-1] if previous_bounds else 0
    y1 = next_bounds[0] if next_bounds else image_height
    pieces: list[tuple[float, str]] = []
    for item in image_items:
        center_x = float(item["cx"]) * image_width
        y = top_y(item, image_height)
        text = int_text(item["text"])
        if 0 <= center_x < edges[1] and y0 <= y < y1 and re.fullmatch(r"\d{3}", text):
            pieces.append((y, text))
    if pieces:
        return sorted(pieces)[0][1]
    return ""


def plan_type(major_name: str) -> str:
    if "中外" in major_name or "联合培养" in major_name:
        return "中外合作"
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
    edges, row_lines, group_bounds, image_width, image_height = dark_lines(image_path)
    if len(edges) != 9:
        raise RuntimeError(f"Unexpected column count in {image_path}: {edges}")
    image_items = [item for item in ocr_items if Path(str(item["path"])).name == image_path.name]
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
            if edges[1] <= center_x < edges[2] and re.search(r"[\u4e00-\u9fffA-Za-z]", text):
                if not any(skip in text for skip in ["专业名称", "惠州学院"]):
                    name_pieces.append((top_y(item, image_height), center_x, text))
        if not name_pieces:
            continue
        numeric = assign_numeric(row_items, edges, image_width)
        major_name = clean_major_name("".join(text for _, _, text in sorted(name_pieces)))
        min_score = score_text(numeric.get(4))
        min_rank = rank_text(numeric.get(7))
        if not major_name or not min_score:
            continue
        major_group = group_for_row(
            image_items,
            edges=edges,
            group_bounds=group_bounds,
            row_mid=row_mid,
            image_width=image_width,
            image_height=image_height,
        )
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": args.track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": major_group,
                "major_name": major_name,
                "plan_type": plan_type(major_name),
                "min_score": min_score,
                "min_rank": min_rank,
                "admit_count": int_text(numeric.get(2)),
                "source_url": source_url,
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        "学校官网图片表经OCR和表格线解析导入",
                        f"最高分={score_text(numeric.get(3))}" if score_text(numeric.get(3)) else "",
                        f"平均分={norm(numeric.get(5))}" if norm(numeric.get(5)) else "",
                        f"最高排位={rank_text(numeric.get(6))}" if rank_text(numeric.get(6)) else "",
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
    with tempfile.TemporaryDirectory(prefix="hzu_major_") as tmp_raw:
        tmp = Path(tmp_raw)
        image_paths: list[tuple[int, str, Path]] = []
        for year in args.years:
            source_url = PAGES[(year, args.track)]
            image_url = page_image(source_url)
            ext = image_url.rsplit(".", 1)[-1].split("?", 1)[0] or "png"
            image_path = tmp / f"hzu_{year}_{args.track}.{ext}"
            download(image_url, image_path, source_url)
            image_paths.append((year, image_url, image_path))
        ocr_items = run_ocr(script, [path for _, _, path in image_paths])
        for year, image_url, image_path in image_paths:
            rows.extend(
                parse_image(
                    args,
                    year=year,
                    source_url=PAGES[(year, args.track)],
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
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"HZU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Huizhou University official Guangdong major-level scores.")
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
    print("# 惠州学院专业录取分数导入\n")
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
