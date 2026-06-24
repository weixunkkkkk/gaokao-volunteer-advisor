#!/usr/bin/env python3
"""Import image-only one-score-one-rank tables with macOS Vision OCR.

This handles official JPG/PNG rank tables where each image contains one or more
page-like segments, and each segment contains repeated score/count/cumulative
column groups. It uses score OCR only to learn row positions, then derives
same-score counts from cumulative ranks whenever possible.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


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
class Token:
    x: float
    y: float
    text: str
    value: int


def parse_score_ranges(raw: str) -> list[tuple[int, int]]:
    ranges = []
    for chunk in raw.replace("，", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" not in chunk:
            raise argparse.ArgumentTypeError(f"score range must be start-end: {chunk}")
        start_raw, end_raw = chunk.split("-", 1)
        start = int(start_raw)
        end = int(end_raw)
        if start < end:
            raise argparse.ArgumentTypeError(f"score range must descend: {chunk}")
        ranges.append((start, end))
    if not ranges:
        raise argparse.ArgumentTypeError("score ranges cannot be empty")
    return ranges


def parse_x_triplets(raw: str) -> list[tuple[float, float, float]]:
    triplets = []
    for chunk in raw.split(";"):
        values = [float(item.strip()) for item in chunk.split(",") if item.strip()]
        if len(values) != 3:
            raise argparse.ArgumentTypeError(f"x triplet must contain score,count,cumulative: {chunk}")
        triplets.append((values[0], values[1], values[2]))
    if not triplets:
        raise argparse.ArgumentTypeError("x triplets cannot be empty")
    return triplets


def clean_int(text: str) -> int | None:
    cleaned = re.sub(r"[\s,，.。]", "", text)
    if not re.fullmatch(r"\d+", cleaned):
        return None
    return int(cleaned)


def run_vision_ocr(image_path: Path) -> list[Token]:
    swift = shutil.which("swift")
    if not swift:
        raise SystemExit("swift is required for macOS Vision OCR")
    env = os.environ.copy()
    env.setdefault("CLANG_MODULE_CACHE_PATH", "/private/tmp/clang-module-cache")
    proc = subprocess.run(
        [swift, str(VISION_HELPER), str(image_path)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    tokens: list[Token] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 6:
            continue
        value = clean_int(parts[-1])
        if value is None:
            continue
        x = float(parts[1]) + float(parts[3]) / 2
        y = float(parts[2]) + float(parts[4]) / 2
        tokens.append(Token(x=x, y=y, text=parts[-1], value=value))
    return tokens


def y_segments(count: int) -> list[tuple[float, float]]:
    if count == 1:
        return [(0.0, 1.0)]
    if count == 2:
        return [(0.5, 1.0), (0.0, 0.5)]
    step = 1.0 / count
    return [(1.0 - (idx + 1) * step, 1.0 - idx * step) for idx in range(count)]


def near(value: float, target: float, tolerance: float) -> bool:
    return abs(value - target) <= tolerance


def fit_row_positions(
    tokens: list[Token],
    segment: tuple[float, float],
    score_x: float,
    score_range: tuple[int, int],
    x_tolerance: float,
) -> tuple[dict[int, float], list[str]]:
    start_score, end_score = score_range
    candidates: dict[int, list[float]] = {}
    y_min, y_max = segment
    for token in tokens:
        if not (y_min <= token.y <= y_max and near(token.x, score_x, x_tolerance)):
            continue
        if end_score <= token.value <= start_score:
            row_index = start_score - token.value
            candidates.setdefault(row_index, []).append(token.y)
    points = [(idx, sum(values) / len(values)) for idx, values in candidates.items()]
    warnings: list[str] = []
    if len(points) < 2:
        raise ValueError(f"not enough score OCR points for range {start_score}-{end_score}")

    n = len(points)
    sum_x = sum(idx for idx, _ in points)
    sum_y = sum(y for _, y in points)
    sum_xx = sum(idx * idx for idx, _ in points)
    sum_xy = sum(idx * y for idx, y in points)
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        raise ValueError(f"cannot fit row positions for range {start_score}-{end_score}")
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    if slope >= 0:
        warnings.append(f"row position slope is non-descending for range {start_score}-{end_score}: {slope:.6f}")
    row_count = start_score - end_score + 1
    return {idx: intercept + slope * idx for idx in range(row_count)}, warnings


def token_near(tokens: list[Token], x: float, y: float, x_tolerance: float, y_tolerance: float) -> int | None:
    matches = [
        token
        for token in tokens
        if near(token.x, x, x_tolerance) and abs(token.y - y) <= y_tolerance
    ]
    if not matches:
        return None
    return min(matches, key=lambda token: abs(token.x - x) + abs(token.y - y)).value


def build_rows(
    tokens: list[Token],
    args: argparse.Namespace,
    score_ranges: list[tuple[int, int]],
    x_triplets: list[tuple[float, float, float]],
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    segments = y_segments((len(score_ranges) + len(x_triplets) - 1) // len(x_triplets))
    rows: list[dict[str, str]] = []
    warnings: list[str] = []
    errors: list[str] = []
    previous_cum: int | None = None
    for range_index, score_range in enumerate(score_ranges):
        segment = segments[range_index // len(x_triplets)]
        score_x, count_x, cum_x = x_triplets[range_index % len(x_triplets)]
        try:
            row_y, fit_warnings = fit_row_positions(tokens, segment, score_x, score_range, args.x_tolerance)
            warnings.extend(fit_warnings)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        start_score, end_score = score_range
        for row_index in range(start_score - end_score + 1):
            score = start_score - row_index
            y = row_y[row_index]
            count = token_near(tokens, count_x, y, args.x_tolerance, args.y_tolerance)
            cumulative = token_near(tokens, cum_x, y, args.x_tolerance, args.y_tolerance)
            if cumulative is None:
                if previous_cum is not None and count is not None:
                    cumulative = previous_cum + count
                    warnings.append(f"{score}: cumulative missing; derived from previous cumulative and count")
                else:
                    errors.append(f"{score}: missing cumulative OCR")
                    continue
            if previous_cum is not None and cumulative <= previous_cum:
                if count is not None and count > 0:
                    cumulative = previous_cum + count
                    warnings.append(f"{score}: cumulative OCR did not increase; corrected from count")
                else:
                    errors.append(f"{score}: cumulative did not increase")
                    continue
            derived_count = cumulative if previous_cum is None else cumulative - previous_cum
            if count is not None and count != derived_count:
                warnings.append(f"{score}: count OCR={count}, derived={derived_count}")
            min_rank = cumulative - derived_count + 1
            rows.append(
                {
                    "year": str(args.year),
                    "province": args.province,
                    "track": args.track,
                    "score": str(score),
                    "min_rank": str(min_rank),
                    "max_rank": str(cumulative),
                    "same_score_count": str(derived_count),
                    "source_url": args.source_url,
                    "source_name": args.source_name,
                }
            )
            previous_cum = cumulative
    rows.sort(key=lambda row: int(row["score"]), reverse=True)
    return rows, warnings, errors


def write_rows(path: Path, rows: list[dict[str, str]], append: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RANK_COLUMNS)
        if mode == "w":
            writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OCR image-only rank table on macOS.")
    parser.add_argument("--input", required=True, help="Official JPG/PNG image")
    parser.add_argument("--score-ranges", type=parse_score_ranges, required=True, help="Descending ranges, e.g. 683-644,643-604")
    parser.add_argument(
        "--x-triplets",
        type=parse_x_triplets,
        default=parse_x_triplets("0.08,0.17,0.25;0.40,0.49,0.56;0.72,0.81,0.88"),
        help="Repeated normalized x positions for score,count,cumulative groups",
    )
    parser.add_argument("--x-tolerance", type=float, default=0.035)
    parser.add_argument("--y-tolerance", type=float, default=0.008)
    parser.add_argument("--year", required=True)
    parser.add_argument("--province", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-file")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strict-ocr-warnings", action="store_true")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"input image not found: {input_path}")
    tokens = run_vision_ocr(input_path)
    rows, warnings, errors = build_rows(tokens, args, args.score_ranges, args.x_triplets)
    output_path = Path(args.output_file).expanduser().resolve() if args.output_file else Path(args.data_dir).expanduser().resolve() / "rank_table.csv"

    result = {
        "input": str(input_path),
        "tokens": len(tokens),
        "rows": len(rows),
        "output": str(output_path),
        "dry_run": args.dry_run,
        "preview": rows[:5],
        "warnings": warnings,
        "errors": errors,
    }
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("# Image rank OCR import")
        print(f"- Input: {input_path}")
        print(f"- OCR tokens: {len(tokens)}")
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
