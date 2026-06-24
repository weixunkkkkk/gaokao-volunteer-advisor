#!/usr/bin/env python3
"""Import scanned one-score-one-rank PDF tables with macOS Vision OCR.

This is intended for official scanned PDFs where pdfplumber cannot extract text
or table cells. It detects the regular score-segment grid, crops numeric cells,
uses the local Swift Vision helper for OCR, and validates cumulative counts.
"""

from __future__ import annotations

import argparse
import csv
import itertools
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


@dataclass
class Cell:
    path: Path
    page: int
    row_index: int
    field: str


def parse_pages(raw: str) -> list[int]:
    pages: list[int] = []
    for chunk in raw.replace("，", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_raw, end_raw = chunk.split("-", 1)
            start = int(start_raw)
            end = int(end_raw)
            pages.extend(range(start, end + 1))
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


def detect_data_lines(gray: Image.Image) -> list[int]:
    pixels = np.array(gray)
    mask = pixels < 170
    height, width = pixels.shape
    row_counts = mask[:, int(width * 0.08) : int(width * 0.94)].sum(axis=1)
    candidates = np.where(row_counts > max(350, int(width * 0.13)))[0]
    lines = [line for line in cluster_positions(candidates) if 80 < line < height - 120]

    best: list[int] = []
    for index in range(len(lines)):
        run = [lines[index]]
        for current, nxt in zip(lines[index:], lines[index + 1 :]):
            gap = nxt - current
            if 45 <= gap <= 75:
                run.append(nxt)
            else:
                break
        if len(run) > len(best):
            best = run

    if len(best) < 5:
        raise ValueError(f"could not detect table data rows; horizontal lines={lines[:20]}")
    return best


def detect_column_lines(gray: Image.Image, y_start: int, y_end: int) -> list[int]:
    pixels = np.array(gray)
    mask = pixels < 170
    col_counts = mask[y_start:y_end, :].sum(axis=0)
    candidates = np.where(col_counts > 250)[0]
    positions = cluster_positions(candidates)

    best: tuple[float, tuple[int, ...]] | None = None
    for combo in itertools.combinations(positions, 6):
        gaps = [combo[i + 1] - combo[i] for i in range(5)]
        avg_gap = sum(gaps) / len(gaps)
        if not 300 <= avg_gap <= 450:
            continue
        if max(gaps) - min(gaps) > 45:
            continue
        score = abs(avg_gap - 385) + (max(gaps) - min(gaps))
        if best is None or score < best[0]:
            best = (score, combo)

    if best is None:
        raise ValueError(f"could not detect six table columns; vertical positions={positions[:30]}")
    return list(best[1])


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
    crop = image.crop((left, top, right, bottom)).convert("L")
    crop = ImageOps.autocontrast(crop)
    crop = crop.resize((crop.width * scale, crop.height * scale), Image.Resampling.LANCZOS)
    crop.save(out_path)


def build_cells(input_pdf: Path, pages: list[int], dpi: int, scale: int, work_dir: Path) -> list[Cell]:
    cells: list[Cell] = []
    row_index = 0
    for page in pages:
        image_path = render_page(input_pdf, page, dpi, work_dir)
        image = Image.open(image_path)
        gray = image.convert("L")
        try:
            y_lines = detect_data_lines(gray)
            x_lines = detect_column_lines(gray, y_lines[0], y_lines[-1])
        except ValueError as exc:
            raise ValueError(f"page {page}: {exc}") from exc
        for y0, y1 in zip(y_lines, y_lines[1:]):
            if y1 - y0 < 35:
                continue
            row_index += 1
            row_boxes = {
                "score": (x_lines[0] + 22, y0 + 8, x_lines[1] - 22, y1 - 8),
                "count": (x_lines[1] + 22, y0 + 8, x_lines[2] - 22, y1 - 8),
                "cum": (x_lines[2] + 22, y0 + 8, x_lines[3] - 22, y1 - 8),
            }
            for field, box in row_boxes.items():
                cell_path = work_dir / f"p{page:03d}_r{row_index:04d}_{field}.png"
                save_cell_crop(image, box, cell_path, scale)
                cells.append(Cell(cell_path, page, row_index, field))
    return cells


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
    if not re.fullmatch(r"\d+", cleaned):
        return None
    return int(cleaned)


def build_rows(
    cells: list[Cell],
    ocr_text: dict[Path, str],
    first_score: int,
    args: argparse.Namespace,
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    by_row: dict[int, dict[str, int | None]] = {}
    warnings: list[str] = []
    errors: list[str] = []
    for cell in cells:
        by_row.setdefault(cell.row_index, {})
        by_row[cell.row_index][cell.field] = first_number(ocr_text.get(cell.path, ""))

    rows: list[dict[str, str]] = []
    previous_cum: int | None = None
    valid_rows = 0
    for row_index in sorted(by_row):
        expected_score = first_score - valid_rows
        fields = by_row[row_index]
        ocr_score = fields.get("score")
        ocr_count = fields.get("count")
        cumulative = fields.get("cum")
        if ocr_score is not None and ocr_score != expected_score:
            warnings.append(f"row {row_index}: score OCR={ocr_score}, expected={expected_score}")
        if cumulative is None:
            if previous_cum is not None and ocr_count is not None and ocr_count > 0:
                cumulative = previous_cum + ocr_count
                warnings.append(f"row {row_index}: cumulative OCR missing; derived from count={ocr_count}")
            else:
                warnings.append(f"row {row_index}: skipped non-data or unreadable row with no cumulative OCR")
                continue
        if previous_cum is not None and cumulative <= previous_cum:
            if ocr_count is not None and ocr_count > 0:
                corrected = previous_cum + ocr_count
                warnings.append(
                    f"row {row_index}: cumulative OCR={cumulative} corrected to {corrected} using count={ocr_count}"
                )
                cumulative = corrected
            else:
                errors.append(
                    f"row {row_index}: cumulative did not increase; previous={previous_cum}, cumulative={cumulative}"
                )
                continue
        count = cumulative if previous_cum is None else cumulative - previous_cum
        if count <= 0:
            errors.append(f"row {row_index}: non-positive derived count; previous={previous_cum}, cumulative={cumulative}")
            continue
        if ocr_count is not None and ocr_count != count:
            warnings.append(f"row {row_index}: count OCR={ocr_count}, derived={count}")
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
        valid_rows += 1

    if args.last_score is not None:
        actual_last = first_score - len(rows) + 1
        if actual_last != args.last_score:
            errors.append(f"last score mismatch; detected={actual_last}, expected={args.last_score}")
    return rows, warnings, errors


def output_path_for(data_dir: Path, output_file: str | None) -> Path:
    if output_file:
        return Path(output_file).expanduser().resolve()
    return data_dir / "rank_table.csv"


def write_rows(path: Path, rows: list[dict[str, str]], append: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RANK_COLUMNS)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR scanned rank-table PDF pages on macOS.")
    parser.add_argument("--input", required=True, help="Official scanned PDF")
    parser.add_argument("--pages", type=parse_pages, required=True, help="Pages to import, e.g. 15-28")
    parser.add_argument("--first-score", type=int, required=True, help="Score in the first imported row")
    parser.add_argument("--last-score", type=int, help="Expected score in the last imported row")
    parser.add_argument("--year", required=True)
    parser.add_argument("--province", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-file")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--scale", type=int, default=4)
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

    with tempfile.TemporaryDirectory(prefix="gaokao-ocr-rank-") as tmp:
        work_dir = Path(tmp)
        cells = build_cells(input_pdf, args.pages, args.dpi, args.scale, work_dir)
        ocr_text = run_vision_ocr(cells)
        rows, warnings, errors = build_rows(cells, ocr_text, args.first_score, args)

    output_path = output_path_for(Path(args.data_dir).expanduser().resolve(), args.output_file)
    print("# Scanned rank PDF OCR import\n")
    print(f"- Input: {input_pdf}")
    print(f"- Pages: {', '.join(str(page) for page in args.pages)}")
    print(f"- OCR cells: {len(cells)}")
    print(f"- Rows: {len(rows)}")
    print(f"- Output: {output_path}")
    print(f"- Mode: {'dry-run' if args.dry_run else ('append' if args.append else 'overwrite')}")
    if rows:
        print(f"- Score range: {rows[0]['score']} to {rows[-1]['score']}")
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
