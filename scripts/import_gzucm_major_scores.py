#!/usr/bin/env python3
"""Import GZUCM official Guangdong major-level admission scores from image tables."""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.request import Request, urlopen, urlretrieve


SOURCE_NAME = "广州中医药大学本科招生网"
SCHOOL_NAME = "广州中医药大学"
OFFICIAL_LIST_URL = "https://xsc.gzucm.edu.cn/bkzs1/zsxx/lnlqqk.htm"
SOURCE_URLS = {
    2023: "https://xsc.gzucm.edu.cn/info/1039/4129.htm",
    2024: "https://mp.weixin.qq.com/s/sarxY-j19q9rHcjKfHPisg",
    2025: "https://mp.weixin.qq.com/s/AIoN8lwpEfnVWmzun_v2LQ",
}
IMAGE_URL_2023 = "https://xsc.gzucm.edu.cn/__local/5/0D/AE/9CAA1A17476745E194459A2C58A_F3C4CC08_14663B.png"
WECHAT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"
OCR_SCRIPT = Path(__file__).resolve().parent / "vision_ocr_image_zh.swift"
GZUCM_2024_COLUMN_EDGES = [0, 242, 297, 428, 498, 563, 624, 693, 766, 835, 890, 945, 1010, 1077]

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
class Token:
    x: float
    y: float
    w: float
    h: float
    text: str


def clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value).replace("\u3000", " ").replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact(value: object) -> str:
    return clean(value).replace(" ", "")


def normalize_major_name(value: object) -> str:
    text = compact(value)
    text = text.replace("（\"", "（“").replace("\"", "”").replace("”一体化", "”一体化")
    text = re.sub(r"[459]年\.?$", "", text)
    if "5+3" in text and "儿科" in text:
        return "中医学（“5+3”一体化，儿科）"
    if "5+3" in text:
        return "中医学（“5+3”一体化）"
    if text.count("（") > text.count("）"):
        text += "）"
    return text


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


def plan_type(major_name: str, level: str) -> str:
    text = f"{major_name}{level}"
    if "定向" in text or "卫生" in text:
        return "卫生专项"
    if "地方专项" in text or "贫困地区专项" in text:
        return "地方专项"
    return "普通类"


def fetch_text(url: str, *, wechat: bool = False) -> str:
    headers = {"User-Agent": WECHAT_UA if wechat else "Mozilla/5.0"}
    return urlopen(Request(url, headers=headers), timeout=60).read().decode("utf-8", "ignore")


def decode_wechat_url(raw: str) -> str:
    try:
        value = raw.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        value = raw
    return html.unescape(value).replace("&amp;", "&")


def extract_wechat_images(year: int) -> list[tuple[str, int, int]]:
    text = fetch_text(SOURCE_URLS[year], wechat=True)
    patterns = [
        r"['\"]cdn_url['\"]\s*:\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]width['\"]\s*:\s*['\"]?(\d+)['\"]?\s*,\s*['\"]height['\"]\s*:\s*['\"]?(\d+)",
        r"cdn_url\s*:\s*['\"]([^'\"]+)['\"]\s*,\s*width\s*:\s*['\"]?(\d+)['\"]?\s*,\s*height\s*:\s*['\"]?(\d+)",
    ]
    images: list[tuple[str, int, int]] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            url = decode_wechat_url(match.group(1))
            width = int(match.group(2))
            height = int(match.group(3))
            if width >= 900 and height >= 150 and url not in seen:
                images.append((url, width, height))
                seen.add(url)
    return images


def image_url_for(year: int, track: str) -> str:
    if year == 2023:
        return IMAGE_URL_2023
    images = extract_wechat_images(year)
    if year == 2024:
        if len(images) < 2:
            raise RuntimeError("GZUCM 2024 WeChat image list did not expose the Guangdong table image")
        return images[1][0]
    # In the 2025 official article, index 1 is the cover, then Guangdong physical/history tables.
    target_index = 2 if track == "物理类" else 3
    if len(images) <= target_index:
        raise RuntimeError(f"GZUCM 2025 WeChat image list too short for {track}: {len(images)}")
    return images[target_index][0]


def download_image(url: str, target: Path) -> None:
    request = Request(url, headers={"User-Agent": WECHAT_UA if "mmbiz.qpic.cn" in url else "Mozilla/5.0"})
    with urlopen(request, timeout=90) as response:
        target.write_bytes(response.read())


def run_ocr(image_path: Path) -> list[Token]:
    if not OCR_SCRIPT.exists():
        raise RuntimeError(f"missing OCR script: {OCR_SCRIPT}")
    result = subprocess.run(
        ["swift", str(OCR_SCRIPT), str(image_path)],
        check=True,
        text=True,
        capture_output=True,
    )
    tokens: list[Token] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t", 5)
        if len(parts) != 6:
            continue
        _, x, y, w, h, text = parts
        text = clean(text)
        if text:
            tokens.append(Token(float(x), float(y), float(w), float(h), text))
    return tokens


def run_ocr_texts(image_paths: list[Path]) -> dict[Path, str]:
    if not image_paths:
        return {}
    result = subprocess.run(
        ["swift", str(OCR_SCRIPT), *[str(path) for path in image_paths]],
        check=True,
        text=True,
        capture_output=True,
    )
    pieces: dict[Path, list[tuple[float, float, str]]] = {path: [] for path in image_paths}
    for line in result.stdout.splitlines():
        parts = line.split("\t", 5)
        if len(parts) != 6:
            continue
        path, x, y, _w, _h, text = parts
        key = Path(path)
        if key not in pieces:
            continue
        pieces[key].append((float(y), float(x), clean(text)))
    output: dict[Path, str] = {}
    for path, cells in pieces.items():
        output[path] = clean(" ".join(text for _y, _x, text in sorted(cells, key=lambda item: (-item[0], item[1]))))
    return output


def grouped_dark_lines(values: list[int]) -> list[int]:
    groups: list[list[int]] = []
    for value in values:
        if not groups or value - groups[-1][-1] > 2:
            groups.append([value])
        else:
            groups[-1].append(value)
    return [(group[0] + group[-1]) // 2 for group in groups]


def horizontal_table_lines(image_path: Path) -> list[int]:
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - depends on runtime
        raise RuntimeError(
            "GZUCM 2024 image-grid parsing needs Pillow. Use the bundled Python runtime."
        ) from exc

    image = Image.open(image_path).convert("L")
    width, height = image.size
    pixels = image.load()
    hits: list[int] = []
    for y in range(height):
        count = sum(1 for x in range(width) if pixels[x, y] < 200)
        if count > width * 0.65:
            hits.append(y)
    lines = [line for line in grouped_dark_lines(hits) if line >= 50]
    if len(lines) < 30:
        raise RuntimeError(f"GZUCM 2024 table line detection found too few lines: {lines}")
    return lines


def ocr_2024_cells(image_path: Path, work_dir: Path) -> list[dict[int, str]]:
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover - depends on runtime
        raise RuntimeError(
            "GZUCM 2024 image-grid parsing needs Pillow. Use the bundled Python runtime."
        ) from exc

    image = Image.open(image_path).convert("RGB")
    row_lines = horizontal_table_lines(image_path)
    rows: list[dict[int, Path]] = []
    all_paths: list[Path] = []
    for row_index, (y0, y1) in enumerate(zip(row_lines, row_lines[1:])):
        # The first detected line after the two-row header is the top of the first data row.
        if y1 - y0 < 12:
            continue
        row_paths: dict[int, Path] = {}
        for column_index, (x0, x1) in enumerate(zip(GZUCM_2024_COLUMN_EDGES, GZUCM_2024_COLUMN_EDGES[1:])):
            crop = image.crop((x0 + 1, y0 + 1, x1 - 1, y1 - 1))
            crop = ImageOps.expand(crop, border=8, fill="white")
            crop = crop.resize((crop.width * 6, crop.height * 6))
            path = work_dir / f"gzucm_2024_cell_{row_index:02d}_{column_index:02d}.png"
            crop.save(path)
            row_paths[column_index] = path
            all_paths.append(path)
        rows.append(row_paths)
    texts = run_ocr_texts(all_paths)
    return [{column: texts.get(path, "") for column, path in row_paths.items()} for row_paths in rows]


def parse_2024_grid(args: argparse.Namespace, track: str, image_path: Path, image_url: str, work_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    column_offset = 3 if track == "物理类" else 8
    for cells in ocr_2024_cells(image_path, work_dir):
        major = normalize_major_name(cells.get(0, ""))
        if not major or "专业" in major or "体育教育" in major:
            continue
        duration = clean(cells.get(1, ""))
        level = clean(cells.get(2, ""))
        admit_count = digits(cells.get(column_offset, ""))
        high_score = valid_score(cells.get(column_offset + 1, ""))
        min_score = valid_score(cells.get(column_offset + 2, ""))
        average = clean(cells.get(column_offset + 3, ""))
        min_rank = valid_rank(cells.get(column_offset + 4, ""))
        if not min_score or not min_rank:
            continue
        rows.append(
            {
                "year": "2024",
                "province": args.province,
                "track": track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": "",
                "major_name": major,
                "plan_type": plan_type(major, level),
                "min_score": min_score,
                "min_rank": min_rank,
                "admit_count": admit_count,
                "source_url": SOURCE_URLS[2024],
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        "学校官网/官方公众号图片表按网格切格OCR导入",
                        f"学制={duration}" if duration else "",
                        f"层次={level}" if level else "",
                        f"最高分={high_score}" if high_score else "",
                        f"平均分={average}" if average and re.fullmatch(r"\d+(?:\.\d+)?", average) else "",
                        f"图片={image_url}",
                        "体育/艺术及无普通位次行已排除",
                    ]
                    if part
                ),
            }
        )
    return rows


def is_numeric_token(text: str) -> bool:
    if text in {"/", "／"}:
        return True
    return bool(re.search(r"\d", text))


def cluster_centers(tokens: list[Token], *, header_cutoff: float, min_x: float) -> list[float]:
    ys = sorted(
        [token.y for token in tokens if token.y < header_cutoff and token.x >= min_x and is_numeric_token(token.text)],
        reverse=True,
    )
    clusters: list[list[float]] = []
    for y in ys:
        if not clusters or abs(sum(clusters[-1]) / len(clusters[-1]) - y) > 0.010:
            clusters.append([y])
        else:
            clusters[-1].append(y)
    return [sum(cluster) / len(cluster) for cluster in clusters]


def nearest_center(y: float, centers: list[float], max_distance: float) -> float | None:
    if not centers:
        return None
    center = min(centers, key=lambda item: abs(item - y))
    return center if abs(center - y) <= max_distance else None


def add_cell(cells: dict[str, list[str]], name: str, text: str) -> None:
    if not text:
        return
    cells.setdefault(name, []).append(text)


def joined(cells: dict[str, list[str]], name: str) -> str:
    if name == "major":
        return compact("".join(cells.get(name, [])))
    return clean(" ".join(cells.get(name, [])))


def assign_single_track(tokens: list[Token], centers: list[float]) -> dict[float, dict[str, list[str]]]:
    rows: dict[float, dict[str, list[str]]] = {center: {} for center in centers}
    spacing = min([abs(a - b) for a, b in zip(centers, centers[1:])] or [0.028])
    max_distance = max(0.012, spacing * 0.62)
    for token in tokens:
        center = nearest_center(token.y, centers, max_distance)
        if center is None:
            continue
        x = token.x
        if x < 0.31:
            add_cell(rows[center], "major", token.text)
        elif 0.31 <= x < 0.40:
            add_cell(rows[center], "duration", token.text)
        elif 0.42 <= x < 0.51:
            add_cell(rows[center], "level", token.text)
        elif 0.52 <= x < 0.61:
            add_cell(rows[center], "admit", token.text)
        elif 0.62 <= x < 0.70:
            add_cell(rows[center], "min_score", token.text)
        elif 0.70 <= x < 0.80:
            add_cell(rows[center], "min_rank", token.text)
        elif 0.80 <= x < 0.88:
            add_cell(rows[center], "high_score", token.text)
        elif 0.88 <= x:
            add_cell(rows[center], "high_rank", token.text)
    return rows


def assign_dual_track(tokens: list[Token], centers: list[float]) -> dict[float, dict[str, list[str]]]:
    rows: dict[float, dict[str, list[str]]] = {center: {} for center in centers}
    spacing = min([abs(a - b) for a, b in zip(centers, centers[1:])] or [0.027])
    max_distance = max(0.014, spacing * 0.64)
    for token in tokens:
        center = nearest_center(token.y, centers, max_distance)
        if center is None:
            continue
        text = token.text
        x = token.x
        if x < 0.21:
            add_cell(rows[center], "major", text)
        elif 0.20 <= x < 0.26:
            add_cell(rows[center], "duration", text)
        elif 0.26 <= x < 0.33:
            add_cell(rows[center], "level", text)
        elif 0.33 <= x < 0.38:
            add_cell(rows[center], "phys_admit", text)
        elif 0.38 <= x < 0.43:
            add_cell(rows[center], "phys_high", text)
        elif 0.43 <= x < 0.49:
            add_cell(rows[center], "phys_min_score", text)
        elif 0.49 <= x < 0.535:
            add_cell(rows[center], "phys_avg", text)
        elif 0.535 <= x < 0.65:
            numbers = re.findall(r"\d+", text)
            if len(numbers) >= 2:
                add_cell(rows[center], "phys_high_rank", numbers[0])
                add_cell(rows[center], "phys_min_rank", numbers[1])
            elif x < 0.585:
                add_cell(rows[center], "phys_high_rank", text)
            else:
                add_cell(rows[center], "phys_min_rank", text)
        elif 0.65 <= x < 0.69:
            add_cell(rows[center], "hist_admit", text)
        elif 0.69 <= x < 0.735:
            add_cell(rows[center], "hist_high", text)
        elif 0.735 <= x < 0.785:
            add_cell(rows[center], "hist_min_score", text)
        elif 0.785 <= x < 0.835:
            add_cell(rows[center], "hist_avg", text)
        elif 0.835 <= x < 0.885:
            add_cell(rows[center], "hist_high_rank", text)
        elif 0.885 <= x:
            add_cell(rows[center], "hist_min_rank", text)
    return rows


def row_from_cells(
    args: argparse.Namespace,
    *,
    year: int,
    source_url: str,
    image_url: str,
    track: str,
    cells: dict[str, list[str]],
    prefix: str = "",
) -> dict[str, str] | None:
    major = joined(cells, "major")
    major = normalize_major_name(major)
    if not major or "专业" in major or "体育教育" in major:
        return None
    level = joined(cells, "level")
    duration = joined(cells, "duration")
    if prefix:
        admit_count = digits(joined(cells, f"{prefix}_admit"))
        min_score = valid_score(joined(cells, f"{prefix}_min_score"))
        min_rank = valid_rank(joined(cells, f"{prefix}_min_rank"))
        high_score = valid_score(joined(cells, f"{prefix}_high"))
        average = joined(cells, f"{prefix}_avg")
    else:
        admit_count = digits(joined(cells, "admit"))
        min_score = valid_score(joined(cells, "min_score"))
        min_rank = valid_rank(joined(cells, "min_rank"))
        high_score = valid_score(joined(cells, "high_score"))
        average = ""
    if not min_score or not min_rank:
        return None
    return {
        "year": str(year),
        "province": args.province,
        "track": track,
        "batch": args.batch,
        "school_name": SCHOOL_NAME,
        "school_code": args.school_code,
        "major_group": "",
        "major_name": major,
        "plan_type": plan_type(major, level),
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": admit_count,
        "source_url": source_url,
        "source_name": SOURCE_NAME,
        "notes": "；".join(
            part
            for part in [
                "学校官网/官方公众号图片表经macOS Vision OCR导入",
                f"学制={duration}" if duration else "",
                f"层次={level}" if level else "",
                f"最高分={high_score}" if high_score else "",
                f"平均分={average}" if average and re.fullmatch(r"\d+(?:\.\d+)?", average) else "",
                f"图片={image_url}",
                "体育/艺术及无普通位次行已排除",
            ]
            if part
        ),
    }


def parse_image(args: argparse.Namespace, year: int, track: str, image_path: Path, image_url: str) -> list[dict[str, str]]:
    tokens = run_ocr(image_path)
    if year == 2025:
        centers = cluster_centers(tokens, header_cutoff=0.935, min_x=0.52)
        cells_by_center = assign_single_track(tokens, centers)
        rows = [
            row_from_cells(args, year=year, source_url=SOURCE_URLS[year], image_url=image_url, track=track, cells=cells)
            for _, cells in sorted(cells_by_center.items(), reverse=True)
        ]
    else:
        centers = cluster_centers(tokens, header_cutoff=0.91 if year == 2024 else 0.86, min_x=0.33)
        cells_by_center = assign_dual_track(tokens, centers)
        prefix = "phys" if track == "物理类" else "hist"
        rows = [
            row_from_cells(args, year=year, source_url=SOURCE_URLS[year], image_url=image_url, track=track, cells=cells, prefix=prefix)
            for _, cells in sorted(cells_by_center.items(), reverse=True)
        ]
    return [row for row in rows if row]


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="gzucm_major_") as tmp:
        tmpdir = Path(tmp)
        for year in args.years:
            image_url = image_url_for(year, args.track)
            image_path = tmpdir / f"gzucm_{year}_{args.track}.png"
            download_image(image_url, image_path)
            if year == 2024:
                rows.extend(parse_2024_grid(args, args.track, image_path, image_url, tmpdir))
            else:
                rows.extend(parse_image(args, year, args.track, image_path, image_url))
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
                clean(row.get("source_name")) == SOURCE_NAME
                and clean(row.get("school_name")) == SCHOOL_NAME
                and clean(row.get("province")) == args.province
                and clean(row.get("track")) == args.track
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"GZUCM importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import GZUCM official Guangdong major-level scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="10572")
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
    print("# 广州中医药大学专业录取分数导入\n")
    print(f"- 来源：{OFFICIAL_LIST_URL}")
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
