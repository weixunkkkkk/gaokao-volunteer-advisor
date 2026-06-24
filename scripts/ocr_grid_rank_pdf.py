#!/usr/bin/env python3
"""Import clear image-only score-band PDF tables by grid/template OCR.

This handles official scanned/image PDFs with one simple table:

    score | same-score count | cumulative count

The importer detects the table grid, learns digit templates from the known
descending score column, reads the count and cumulative columns, and validates
that same-score count equals the difference between cumulative counts.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import shutil
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "assets" / "data"
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
class PageGrid:
    image: np.ndarray
    x_lines: list[int]
    row_ranges: list[tuple[int, int]]
    raw_x_lines: list[int]


@dataclass
class Component:
    x0: int
    y0: int
    x1: int
    y1: int
    area: int
    crop: np.ndarray


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


def cluster_positions(values: np.ndarray, max_gap: int = 3) -> list[int]:
    clusters: list[list[int]] = []
    for value in values.tolist():
        value = int(value)
        if not clusters or value - clusters[-1][-1] > max_gap:
            clusters.append([value])
        else:
            clusters[-1].append(value)
    return [round(sum(cluster) / len(cluster)) for cluster in clusters]


def render_page(input_pdf: Path, page: int, dpi: int, out_dir: Path) -> Path:
    base = out_dir / f"page-{page:03d}"
    proc = subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page), "-l", str(page), str(input_pdf), str(base)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.stderr:
        pass
    matches = sorted(out_dir.glob(f"page-{page:03d}-*.png"))
    if not matches:
        raise FileNotFoundError(f"pdftoppm did not render page {page}")
    return matches[0]


def pick_table_columns(raw_x_lines: list[int], width: int) -> list[int]:
    best: tuple[float, tuple[int, ...]] | None = None
    for combo in itertools.combinations(raw_x_lines, 4):
        gaps = [combo[index + 1] - combo[index] for index in range(3)]
        avg_gap = sum(gaps) / len(gaps)
        if not width * 0.18 <= avg_gap <= width * 0.30:
            continue
        spread = max(gaps) - min(gaps)
        span = combo[-1] - combo[0]
        score = spread - span * 0.001 + abs(avg_gap - width * 0.236) * 0.2
        if best is None or score < best[0]:
            best = (score, combo)
    if best is None:
        raise ValueError(f"could not select four table column lines from {raw_x_lines}")
    return list(best[1])


def detect_page_grid(image_path: Path, line_threshold: int) -> PageGrid:
    image = np.array(Image.open(image_path).convert("L"))
    height, width = image.shape
    line_mask = image < line_threshold

    row_counts = line_mask[:, int(width * 0.1) : int(width * 0.9)].sum(axis=1)
    y_candidates = np.where(row_counts > int(width * 0.45))[0]
    y_lines = [line for line in cluster_positions(y_candidates) if 80 < line < height - 80]
    if len(y_lines) < 4:
        raise ValueError(f"could not detect table rows in {image_path}; y_lines={y_lines[:20]}")

    y_start, y_end = y_lines[0], y_lines[-1]
    col_counts = line_mask[y_start:y_end, :].sum(axis=0)
    x_candidates = np.where(col_counts > int((y_end - y_start) * 0.45))[0]
    raw_x_lines = cluster_positions(x_candidates)
    x_lines = pick_table_columns(raw_x_lines, width)

    # y_lines[0]-y_lines[1] is the header row. Data rows start after it.
    row_ranges = list(zip(y_lines[1:-1], y_lines[2:]))
    return PageGrid(image=image, x_lines=x_lines, row_ranges=row_ranges, raw_x_lines=raw_x_lines)


def extract_components(
    page: PageGrid,
    column_index: int,
    row_index: int,
    digit_threshold: int,
    pad_x: int,
    pad_y: int,
) -> list[Component]:
    y_top, y_bottom = page.row_ranges[row_index]
    x_left, x_right = page.x_lines[column_index], page.x_lines[column_index + 1]
    crop = page.image[y_top + pad_y : y_bottom - pad_y, x_left + pad_x : x_right - pad_x]
    bitmap = crop < digit_threshold
    seen = np.zeros(bitmap.shape, dtype=bool)
    height, width = bitmap.shape
    components: list[Component] = []

    for yy in range(height):
        for xx in np.where(bitmap[yy] & ~seen[yy])[0].tolist():
            if seen[yy, xx] or not bitmap[yy, xx]:
                continue
            stack = [(yy, xx)]
            seen[yy, xx] = True
            points: list[tuple[int, int]] = []
            while stack:
                cy, cx = stack.pop()
                points.append((cy, cx))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if not dy and not dx:
                            continue
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < height and 0 <= nx < width and bitmap[ny, nx] and not seen[ny, nx]:
                            seen[ny, nx] = True
                            stack.append((ny, nx))
            ys = [point[0] for point in points]
            xs = [point[1] for point in points]
            x0, x1 = min(xs), max(xs) + 1
            y0, y1 = min(ys), max(ys) + 1
            area = len(points)
            if area >= 8 and y1 - y0 >= 8 and x1 - x0 >= 2:
                components.append(Component(x0=x0, y0=y0, x1=x1, y1=y1, area=area, crop=crop))

    return sorted(components, key=lambda component: component.x0)


def normalize_glyph(component: Component, digit_threshold: int, size: tuple[int, int] = (18, 26)) -> np.ndarray:
    glyph = component.crop[component.y0 : component.y1, component.x0 : component.x1] < digit_threshold
    image = Image.fromarray(glyph.astype("uint8") * 255)
    side = max(image.width, image.height)
    canvas = Image.new("L", (side, side), 0)
    canvas.paste(image, ((side - image.width) // 2, (side - image.height) // 2))
    return np.array(canvas.resize(size, Image.Resampling.NEAREST)) > 0


def build_digit_templates(pages: list[PageGrid], args: argparse.Namespace) -> dict[str, list[np.ndarray]]:
    templates: dict[str, list[np.ndarray]] = defaultdict(list)
    score = args.first_score
    for page in pages:
        for row_index in range(len(page.row_ranges)):
            expected = str(score)
            components = extract_components(page, 0, row_index, args.digit_threshold, args.pad_x, args.pad_y)
            if len(components) == len(expected):
                for digit, component in zip(expected, components):
                    templates[digit].append(normalize_glyph(component, args.digit_threshold))
            score -= 1
    missing = [digit for digit in "0123456789" if not templates.get(digit)]
    if missing:
        raise ValueError(f"missing digit templates: {', '.join(missing)}")
    return templates


def classify_digit(glyph: np.ndarray, templates: dict[str, list[np.ndarray]]) -> tuple[str, float]:
    best_digit = ""
    best_score = float("inf")
    for digit, examples in templates.items():
        for example in examples:
            score = float(np.mean(example != glyph))
            if score < best_score:
                best_digit = digit
                best_score = score
    return best_digit, best_score


def read_numeric_cell(
    page: PageGrid,
    column_index: int,
    row_index: int,
    templates: dict[str, list[np.ndarray]],
    args: argparse.Namespace,
) -> tuple[int | None, list[float], int]:
    components = extract_components(page, column_index, row_index, args.digit_threshold, args.pad_x, args.pad_y)
    digits: list[str] = []
    scores: list[float] = []
    for component in components:
        digit, score = classify_digit(normalize_glyph(component, args.digit_threshold), templates)
        digits.append(digit)
        scores.append(score)
    if not digits:
        return None, scores, len(components)
    return int("".join(digits)), scores, len(components)


def build_rows(
    pages: list[PageGrid],
    templates: dict[str, list[np.ndarray]],
    args: argparse.Namespace,
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    rows: list[dict[str, str]] = []
    warnings: list[str] = []
    errors: list[str] = []
    previous_cumulative: int | None = None
    score = args.first_score

    for page_number, page in zip(args.pages, pages):
        for row_index in range(len(page.row_ranges)):
            count_value, count_scores, count_components = read_numeric_cell(page, 1, row_index, templates, args)
            cumulative_value, cumulative_scores, cumulative_components = read_numeric_cell(page, 2, row_index, templates, args)
            if count_value is None or cumulative_value is None:
                errors.append(
                    f"score {score}: missing numeric cell; count={count_value}, cumulative={cumulative_value}"
                )
                score -= 1
                continue

            if any(item > args.max_digit_score for item in [*count_scores, *cumulative_scores]):
                warnings.append(
                    f"score {score}: high template distance; count_components={count_components}, "
                    f"cumulative_components={cumulative_components}"
                )

            if previous_cumulative is not None and cumulative_value <= previous_cumulative:
                if count_value > 0:
                    corrected = previous_cumulative + count_value
                    warnings.append(
                        f"score {score}: cumulative {cumulative_value} corrected to {corrected} from count"
                    )
                    cumulative_value = corrected
                else:
                    errors.append(
                        f"score {score}: cumulative did not increase; previous={previous_cumulative}, "
                        f"cumulative={cumulative_value}"
                    )
                    score -= 1
                    continue

            derived_count = cumulative_value if previous_cumulative is None else cumulative_value - previous_cumulative
            if count_value != derived_count:
                warnings.append(f"score {score}: count {count_value} changed to derived count {derived_count}")
                count_value = derived_count
            if count_value <= 0:
                errors.append(f"score {score}: non-positive same-score count {count_value}")
                score -= 1
                continue

            min_rank = cumulative_value - count_value + 1
            rows.append(
                {
                    "year": str(args.year),
                    "province": args.province,
                    "track": args.track,
                    "score": str(score),
                    "min_rank": str(min_rank),
                    "max_rank": str(cumulative_value),
                    "same_score_count": str(count_value),
                    "source_url": args.source_url,
                    "source_name": args.source_name,
                }
            )
            previous_cumulative = cumulative_value
            score -= 1

    if args.last_score is not None:
        actual_last_score = args.first_score - len(rows) + 1
        if actual_last_score != args.last_score:
            errors.append(f"last score mismatch; detected={actual_last_score}, expected={args.last_score}")
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
    parser = argparse.ArgumentParser(description="OCR clear three-column scanned rank PDF tables.")
    parser.add_argument("--input", required=True, help="Official scanned PDF")
    parser.add_argument("--pages", type=parse_pages, required=True, help="Pages to import, e.g. 1-4")
    parser.add_argument("--first-score", type=int, required=True)
    parser.add_argument("--last-score", type=int)
    parser.add_argument("--year", required=True)
    parser.add_argument("--province", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-file")
    parser.add_argument("--dpi", type=int, default=160)
    parser.add_argument("--line-threshold", type=int, default=80)
    parser.add_argument("--digit-threshold", type=int, default=100)
    parser.add_argument("--pad-x", type=int, default=20)
    parser.add_argument("--pad-y", type=int, default=4)
    parser.add_argument("--max-digit-score", type=float, default=0.20)
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

    with tempfile.TemporaryDirectory(prefix="gaokao-grid-rank-") as tmp:
        work_dir = Path(tmp)
        image_paths = [render_page(input_pdf, page, args.dpi, work_dir) for page in args.pages]
        pages = [detect_page_grid(path, args.line_threshold) for path in image_paths]
        templates = build_digit_templates(pages, args)
        rows, warnings, errors = build_rows(pages, templates, args)

    output_path = output_path_for(Path(args.data_dir).expanduser().resolve(), args.output_file)
    print("# Grid rank PDF OCR import\n")
    print(f"- Input: {input_pdf}")
    print(f"- Pages: {', '.join(str(page) for page in args.pages)}")
    print(f"- Row counts: {', '.join(str(len(page.row_ranges)) for page in pages)}")
    print(f"- Rows: {len(rows)}")
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
