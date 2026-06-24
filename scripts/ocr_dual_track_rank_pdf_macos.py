#!/usr/bin/env python3
"""Import scanned dual-track one-score-one-rank PDFs with macOS Vision OCR.

Some provinces publish one score column plus two track blocks in a scanned PDF,
for example: score | physics count | physics cumulative | history count |
history cumulative. This importer writes one selected track at a time while
keeping score progression aligned to the shared score column.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "assets" / "data"
VISION_HELPER = ROOT / "scripts" / "vision_ocr_image.swift"
RANK_COLUMNS = [
    "year",
    "province",
    "track",
    "score",
    "min_rank",
    "max_rank",
    "same_score_count",
    "source_url",
    "source_name",
]


@dataclass(frozen=True)
class Cell:
    path: Path
    page: int
    score_index: int
    expected_score: int
    field: str


def parse_pages(raw: str) -> list[int]:
    pages: list[int] = []
    for chunk in raw.replace("，", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_raw, end_raw = chunk.split("-", 1)
            pages.extend(range(int(start_raw), int(end_raw) + 1))
        else:
            pages.append(int(chunk))
    if not pages:
        raise argparse.ArgumentTypeError("pages cannot be empty")
    return pages


def cluster_positions(values: np.ndarray, max_gap: int = 4) -> list[int]:
    clusters: list[list[int]] = []
    for value in values.tolist():
        if not clusters or value - clusters[-1][-1] > max_gap:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return [round(sum(cluster) / len(cluster)) for cluster in clusters]


def detect_data_lines(gray: Image.Image, row_gap_min: int, row_gap_max: int) -> list[int]:
    pixels = np.array(gray)
    mask = pixels < 170
    height, width = pixels.shape
    row_counts = mask[:, int(width * 0.08) : int(width * 0.94)].sum(axis=1)
    candidates = np.where(row_counts > max(350, int(width * 0.13)))[0]
    min_data_y = int(height * 0.18)
    lines = [line for line in cluster_positions(candidates) if min_data_y < line < height - 120]

    best: list[int] = []
    for index in range(len(lines)):
        run = [lines[index]]
        last = lines[index]
        for nxt in lines[index + 1 :]:
            gap = nxt - last
            if gap < row_gap_min:
                continue
            if gap <= row_gap_max:
                run.append(nxt)
                last = nxt
            else:
                break
        if len(run) > len(best):
            best = run

    if len(best) < 3:
        raise ValueError(f"could not detect table data rows; horizontal lines={lines[:30]}")
    return best


def detect_column_lines(gray: Image.Image, y_start: int, y_end: int) -> list[int]:
    pixels = np.array(gray)
    mask = pixels < 170
    span = y_end - y_start
    col_counts = mask[y_start:y_end, :].sum(axis=0)
    candidates = np.where(col_counts > max(150, int(span * 0.62)))[0]
    positions = cluster_positions(candidates)
    if len(positions) != 6:
        raise ValueError(f"expected six table column lines; detected={positions}")
    return positions


def render_page(input_pdf: Path, page: int, dpi: int, out_dir: Path) -> Path:
    base = out_dir / f"page-{page:03d}"
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page), str(input_pdf), str(base)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    matches = sorted(out_dir.glob(f"page-{page:03d}-*.png"))
    if not matches:
        raise FileNotFoundError(f"pdftoppm did not render page {page}")
    return matches[0]


def save_cell_crop(image: Image.Image, box: tuple[int, int, int, int], out_path: Path, scale: int) -> None:
    left, top, right, bottom = box
    crop_rgb = image.crop((left, top, right, bottom)).convert("RGB")
    arr = np.array(crop_rgb)
    max_channel = arr.max(axis=2)
    min_channel = arr.min(axis=2)
    mean_channel = arr.mean(axis=2)
    neutral = (max_channel - min_channel) < 55
    gray = mean_channel.astype("uint8")
    gray = np.where(neutral, gray, 255).astype("uint8")
    gray = np.where(gray < 215, gray, 255).astype("uint8")
    crop = Image.fromarray(gray, "L")
    crop = ImageOps.autocontrast(crop)
    pixels = np.array(crop)
    ink = np.where(pixels < 245)
    if ink[0].size:
        y0, y1 = int(ink[0].min()), int(ink[0].max())
        x0, x1 = int(ink[1].min()), int(ink[1].max())
        pad = 10
        crop = crop.crop(
            (
                max(0, x0 - pad),
                max(0, y0 - pad),
                min(crop.width, x1 + pad + 1),
                min(crop.height, y1 + pad + 1),
            )
        )
        crop = ImageOps.expand(crop, border=12, fill=255)
    crop = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.LANCZOS)
    crop.convert("RGB").save(out_path)


def build_cells(input_pdf: Path, args: argparse.Namespace, work_dir: Path) -> tuple[list[Cell], int]:
    cells: list[Cell] = []
    score_index = 0
    side_offsets = {
        "left": ("left_count", "left_cum", 1, 2, 3),
        "right": ("right_count", "right_cum", 3, 4, 5),
    }
    count_field, cum_field, count_left, cum_left, cum_right = side_offsets[args.side]
    for page in args.pages:
        image_path = render_page(input_pdf, page, args.dpi, work_dir)
        image = Image.open(image_path)
        gray = image.convert("L")
        try:
            y_lines = detect_data_lines(gray, args.row_gap_min, args.row_gap_max)
            x_lines = detect_column_lines(gray, y_lines[0], y_lines[-1])
        except ValueError as exc:
            raise ValueError(f"page {page}: {exc}") from exc

        for y0, y1 in zip(y_lines, y_lines[1:]):
            if y1 - y0 < args.row_gap_min - 15:
                continue
            expected_score = args.first_score - score_index
            score_index += 1
            boxes = {
                "score": (x_lines[0] + 8, y0 + 8, x_lines[1] - 8, y1 - 8),
                "count": (x_lines[count_left] + 8, y0 + 8, x_lines[cum_left] - 8, y1 - 8),
                "cum": (x_lines[cum_left] + 8, y0 + 8, x_lines[cum_right] - 8, y1 - 8),
            }
            for field, box in boxes.items():
                cell_path = work_dir / f"p{page:03d}_s{score_index:04d}_{field}.png"
                save_cell_crop(image, box, cell_path, args.scale)
                cells.append(Cell(cell_path, page, score_index, expected_score, field))
    return cells, score_index


def run_vision_ocr(cells: list[Cell]) -> dict[Path, str]:
    swift = shutil.which("swift")
    if not swift:
        raise SystemExit("swift is required for macOS Vision OCR")
    if not VISION_HELPER.exists():
        raise SystemExit(f"missing Vision helper: {VISION_HELPER}")

    env = os.environ.copy()
    env.setdefault("CLANG_MODULE_CACHE_PATH", "/private/tmp/clang-module-cache")
    command = [swift, str(VISION_HELPER), *[str(cell.path) for cell in cells]]
    proc = subprocess.run(command, check=True, capture_output=True, text=True, env=env)

    grouped: dict[Path, list[str]] = {}
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        grouped.setdefault(Path(parts[0]), []).append(parts[-1])
    return {path: " ".join(values) for path, values in grouped.items()}


def first_number(text: str) -> int | None:
    cleaned = re.sub(r"[\s,，.。]", "", text)
    match = re.search(r"\d+", cleaned)
    if not match:
        return None
    return int(match.group(0))


def repair_decreased_cumulative(previous: int, cumulative: int) -> int | None:
    """Repair OCR values that dropped because a leading digit was missed or confused."""
    text = str(cumulative)
    candidates: set[int] = set()
    if len(text) > 1:
        for digit in "123456789":
            candidates.add(int(digit + text[1:]))
    width = 10 ** len(text)
    candidate = cumulative
    while candidate <= previous:
        candidate += width
    candidates.add(candidate)
    plausible = sorted(value for value in candidates if previous < value and value - previous <= 10000)
    return plausible[0] if plausible else None


def build_rows(
    cells: list[Cell], ocr_text: dict[Path, str], args: argparse.Namespace
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    by_score: dict[int, dict[str, int | None]] = {}
    expected_by_score: dict[int, int] = {}
    warnings: list[str] = []
    errors: list[str] = []

    for cell in cells:
        by_score.setdefault(cell.score_index, {})
        expected_by_score[cell.score_index] = cell.expected_score
        value = first_number(ocr_text.get(cell.path, ""))
        by_score[cell.score_index][cell.field] = value

    rows: list[dict[str, str]] = []
    previous_cum: int | None = None
    for score_index in sorted(by_score):
        expected_score = expected_by_score[score_index]
        fields = by_score[score_index]
        ocr_score = fields.get("score")
        ocr_count = fields.get("count")
        cumulative = fields.get("cum")

        if ocr_score is not None and ocr_score != expected_score:
            warnings.append(f"score row {score_index}: score OCR={ocr_score}, expected={expected_score}")
        if cumulative is None:
            continue
        if previous_cum is not None and cumulative <= previous_cum:
            if ocr_count is not None and ocr_count > 0:
                corrected = previous_cum + ocr_count
                warnings.append(
                    f"score {expected_score}: cumulative OCR={cumulative} corrected to {corrected} using count={ocr_count}"
                )
                cumulative = corrected
            else:
                repaired = repair_decreased_cumulative(previous_cum, cumulative)
                if repaired is not None:
                    warnings.append(
                        f"score {expected_score}: cumulative OCR={cumulative} repaired to {repaired} from previous={previous_cum}"
                    )
                    cumulative = repaired
                else:
                    errors.append(
                        f"score {expected_score}: cumulative did not increase; previous={previous_cum}, cumulative={cumulative}"
                    )
                    continue
        count = cumulative if previous_cum is None else cumulative - previous_cum
        if count <= 0:
            errors.append(f"score {expected_score}: non-positive derived count; previous={previous_cum}, cumulative={cumulative}")
            continue
        if ocr_count is not None and ocr_count != count:
            warnings.append(f"score {expected_score}: count OCR={ocr_count}, derived={count}")
        min_rank = cumulative - count + 1
        rows.append(
            {
                "year": str(args.year),
                "province": args.province,
                "track": args.track,
                "score": str(expected_score),
                "min_rank": str(min_rank),
                "max_rank": str(cumulative),
                "same_score_count": str(count),
                "source_url": args.source_url,
                "source_name": args.source_name,
            }
        )
        previous_cum = cumulative

    if args.last_score is not None and rows:
        actual_last = int(rows[-1]["score"])
        if actual_last != args.last_score:
            errors.append(f"last output score mismatch; detected={actual_last}, expected={args.last_score}")
    return rows, warnings, errors


def write_rows(path: Path, rows: list[dict[str, str]], append: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RANK_COLUMNS)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)


def output_path_for(data_dir: Path, output_file: str | None) -> Path:
    if output_file:
        return Path(output_file).expanduser().resolve()
    return data_dir / "rank_table.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR scanned dual-track rank PDF pages on macOS.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--pages", type=parse_pages, required=True)
    parser.add_argument("--side", choices=["left", "right"], required=True, help="Track block to import")
    parser.add_argument("--first-score", type=int, required=True, help="Score in the first shared score row")
    parser.add_argument("--last-score", type=int, help="Expected last imported score for this selected track")
    parser.add_argument("--year", required=True)
    parser.add_argument("--province", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-file")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--row-gap-min", type=int, default=70)
    parser.add_argument("--row-gap-max", type=int, default=105)
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict-ocr-warnings", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_pdf = Path(args.input).expanduser().resolve()
    if not input_pdf.exists():
        raise SystemExit(f"input PDF not found: {input_pdf}")
    if not shutil.which("pdftoppm"):
        raise SystemExit("pdftoppm is required")

    with tempfile.TemporaryDirectory(prefix="gaokao-dual-rank-") as tmp:
        cells, shared_score_rows = build_cells(input_pdf, args, Path(tmp))
        ocr_text = run_vision_ocr(cells)
        rows, warnings, errors = build_rows(cells, ocr_text, args)

    output_path = output_path_for(Path(args.data_dir).expanduser().resolve(), args.output_file)
    print("# Dual-track scanned rank PDF OCR import\n")
    print(f"- Input: {input_pdf}")
    print(f"- Pages: {', '.join(str(page) for page in args.pages)}")
    print(f"- Side: {args.side}")
    print(f"- Shared score rows: {shared_score_rows}")
    print(f"- OCR cells: {len(cells)}")
    print(f"- Output rows: {len(rows)}")
    print(f"- Output: {output_path}")
    print(f"- Mode: {'dry-run' if args.dry_run else ('append' if args.append else 'overwrite')}")
    if rows:
        print(f"- Score range: {rows[0]['score']} to {rows[-1]['score']}")
        print(f"- Rank range: {rows[0]['min_rank']} to {rows[-1]['max_rank']}")
        print(f"- Preview: {rows[:3]}")
    if warnings:
        print("\n## Warnings")
        for warning in warnings[:30]:
            print(f"- {warning}")
        if len(warnings) > 30:
            print(f"- ... {len(warnings) - 30} more warnings")
    if errors:
        print("\n## Errors")
        for error in errors[:30]:
            print(f"- {error}")
        if len(errors) > 30:
            print(f"- ... {len(errors) - 30} more errors")
    if errors or (warnings and args.strict_ocr_warnings):
        raise SystemExit(2)
    if not args.dry_run:
        write_rows(output_path, rows, args.append)


if __name__ == "__main__":
    main()
