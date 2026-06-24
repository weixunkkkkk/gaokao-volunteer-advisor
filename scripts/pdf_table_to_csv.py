#!/usr/bin/env python3
"""Convert official Gaokao PDF tables into normalized advisor CSV files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from normalize_data import (
    DEFAULT_DATA_DIR,
    DEFAULT_OUTPUT,
    SCHEMA_COLUMNS,
    apply_postprocess,
    detect_mapping,
    has_content,
    normalize_row,
    output_path_for,
    parse_pairs,
    preview_rows,
    write_rows,
)


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def clean_pdf_cell(value: object) -> str:
    text = norm(value)
    if not text:
        return ""
    watermark_chars = set("广东省教育考试院上海市")
    parts = []
    for part in text.splitlines():
        cleaned = part.strip()
        if len(cleaned) == 1 and cleaned in watermark_chars:
            continue
        parts.append(cleaned)
    return " ".join(part for part in parts if part).strip()


def load_pdf_tables(path: Path, pages: str | None) -> tuple[list[str], list[dict[str, str]], dict[str, int]]:
    try:
        import pdfplumber
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "读取 PDF 需要 pdfplumber。请使用 Codex 内置 Python 运行，或先把 PDF 表格另存为 CSV/XLSX。"
        ) from exc

    selected_pages = parse_page_selection(pages)
    headers: list[str] = []
    rows: list[dict[str, str]] = []
    stats = {"pages_seen": 0, "tables_seen": 0, "raw_rows": 0}

    with pdfplumber.open(path) as pdf:
        page_indexes = selected_pages if selected_pages is not None else range(len(pdf.pages))
        for page_index in page_indexes:
            if page_index < 0 or page_index >= len(pdf.pages):
                continue
            stats["pages_seen"] += 1
            page = pdf.pages[page_index]
            tables = page.extract_tables()
            stats["tables_seen"] += len(tables)
            for table in tables:
                table = [[clean_pdf_cell(cell) for cell in row] for row in table if row and any(norm(cell) for cell in row)]
                if len(table) < 2:
                    continue
                table_headers, data_start = normalize_table_headers(table)
                if not headers:
                    headers = table_headers
                for raw in table[data_start:]:
                    padded = raw + [""] * max(0, len(table_headers) - len(raw))
                    row = {table_headers[idx]: padded[idx] for idx in range(len(table_headers))}
                    rows.append(row)
                    stats["raw_rows"] += 1
    return headers, rows, stats


def normalize_table_headers(table: list[list[str]]) -> tuple[list[str], int]:
    first = table[0]
    second = table[1] if len(table) > 1 else []
    if second and not looks_like_data_row(second):
        headers = []
        last_group = ""
        width = max(len(first), len(second))
        for index in range(width):
            top = first[index].strip() if index < len(first) else ""
            sub = second[index].strip() if index < len(second) else ""
            if top:
                last_group = top
            if top and not sub:
                header = top
            elif sub and last_group and last_group != top:
                header = f"{last_group}{sub}"
            else:
                header = sub or top
            headers.append(header)
        return dedupe_headers(headers), 2
    return dedupe_headers(first), 1


def looks_like_data_row(row: list[str]) -> bool:
    first = row[0].strip() if row else ""
    return bool(first and any(char.isdigit() for char in first))


def dedupe_headers(headers: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    output = []
    for index, header in enumerate(headers):
        base = header.strip() or f"column_{index + 1}"
        counts[base] = counts.get(base, 0) + 1
        if counts[base] == 1:
            output.append(base)
        else:
            output.append(f"{base}_{counts[base]}")
    return output


def parse_page_selection(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    indexes: list[int] = []
    for chunk in raw.replace("，", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_raw, end_raw = chunk.split("-", 1)
            start = int(start_raw)
            end = int(end_raw)
            indexes.extend(range(start - 1, end))
        else:
            indexes.append(int(chunk) - 1)
    return indexes


def build_constants(args: argparse.Namespace) -> dict[str, str]:
    constants = parse_pairs(args.const, "--const")
    quick = {
        "year": args.year,
        "province": args.province,
        "track": args.track,
        "batch": args.batch,
        "plan_type": args.plan_type,
        "source_url": args.source_url,
        "source_name": args.source_name,
        "notes": args.notes,
    }
    for key, value in quick.items():
        if value is not None:
            constants[key] = value
    return constants


def infer_plan_type(row: dict[str, str]) -> str | None:
    text = " ".join(row.values())
    if "中外合作" in text or "中外合办" in text:
        return "中外合作"
    if "联合培养" in text:
        return "联合培养"
    if "地方专项" in text:
        return "地方专项"
    if "少数民族" in text:
        return "少数民族班"
    if "预科" in text:
        return "预科班"
    return None


def normalize_rows(
    kind: str,
    raw_rows: list[dict[str, str]],
    mapping: dict[str, str],
    constants: dict[str, str],
    infer_plan: bool,
    split_major_group_suffix: bool,
) -> list[dict[str, str]]:
    normalized = []
    for raw in raw_rows:
        row_constants = dict(constants)
        if infer_plan and kind == "admission":
            inferred = infer_plan_type(raw)
            if inferred:
                row_constants["plan_type"] = inferred
        row = normalize_row(kind, raw, mapping, row_constants)
        if kind == "admission":
            row = apply_postprocess(
                row,
                split_school_prefix=False,
                strip_major_code_prefix=False,
                split_major_group_suffix=split_major_group_suffix,
            )
        if kind == "rank":
            repair_top_rank_band(raw, mapping, row)
        if has_content(row, kind):
            normalized.append(row)
    return normalized


def repair_top_rank_band(raw: dict[str, str], mapping: dict[str, str], row: dict[str, str]) -> None:
    """Handle top score-band labels such as 693↑ where 人数 is intentionally blank."""
    score_source = mapping.get("score")
    raw_score = raw.get(score_source, "") if score_source else ""
    if "↑" not in raw_score and "及以上" not in raw_score:
        return
    if row.get("max_rank") and not row.get("same_score_count"):
        row["same_score_count"] = row["max_rank"]
    if row.get("max_rank") and not row.get("min_rank"):
        row["min_rank"] = "1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract normalized Gaokao advisor CSV rows from official PDF tables.")
    parser.add_argument("--kind", choices=["admission", "rank"], default="admission")
    parser.add_argument("--input", required=True, help="Official PDF file")
    parser.add_argument("--pages", help="1-based pages or ranges, e.g. 1-3,8")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Output data directory")
    parser.add_argument("--output-file", help="Override exact output CSV path")
    parser.add_argument("--mapping", action="append", default=[], help="target=source header mapping; repeatable")
    parser.add_argument("--const", action="append", default=[], help="target=value constant; repeatable")
    parser.add_argument("--year", help="Constant year")
    parser.add_argument("--province", help="Constant province")
    parser.add_argument("--track", help="Constant track")
    parser.add_argument("--batch", help="Constant batch")
    parser.add_argument("--plan-type", help="Constant plan_type")
    parser.add_argument("--infer-plan-type", action="store_true", help="Infer special plan_type from row text")
    parser.add_argument("--split-major-group-suffix", action="store_true", help="Split values like 复旦大学(01) into school_name=复旦大学 and major_group=01")
    parser.add_argument("--source-url", help="Constant source_url")
    parser.add_argument("--source-name", help="Constant source_name")
    parser.add_argument("--notes", help="Constant notes")
    parser.add_argument("--append", action="store_true", help="Append to output CSV instead of overwriting")
    parser.add_argument("--dry-run", action="store_true", help="Print detected mapping and preview without writing")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"输入文件不存在：{input_path}")

    headers, raw_rows, stats = load_pdf_tables(input_path, args.pages)
    explicit_mapping = parse_pairs(args.mapping, "--mapping")
    mapping = detect_mapping(args.kind, headers, explicit_mapping)
    constants = build_constants(args)
    normalized_rows = normalize_rows(
        args.kind,
        raw_rows,
        mapping,
        constants,
        args.infer_plan_type,
        args.split_major_group_suffix,
    )
    output_path = output_path_for(args.kind, Path(args.data_dir).expanduser().resolve(), args.output_file)

    result = {
        "input": str(input_path),
        "kind": args.kind,
        "headers": headers,
        "mapping": mapping,
        "constants": constants,
        "stats": stats,
        "normalized_rows": len(normalized_rows),
        "output": str(output_path),
        "preview": preview_rows(normalized_rows, 5),
        "dry_run": args.dry_run,
    }

    if not args.dry_run:
        write_rows(output_path, args.kind, normalized_rows, args.append)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("# PDF 表格规范化导入\n")
    print(f"- 输入：{result['input']}")
    print(f"- 类型：{result['kind']}")
    print(f"- 页数处理：{stats['pages_seen']}；表格数：{stats['tables_seen']}；原始表格行：{stats['raw_rows']}")
    print(f"- 有效导入行数：{result['normalized_rows']}")
    print(f"- 输出：{result['output']}")
    print(f"- 模式：{'预览，不写入' if args.dry_run else ('追加' if args.append else '覆盖')}")
    print("\n## 字段映射")
    for target in SCHEMA_COLUMNS[args.kind]:
        source = mapping.get(target)
        const = constants.get(target)
        if const is not None:
            print(f"- `{target}` = 常量 `{const}`")
        elif source:
            print(f"- `{target}` <- `{source}`")
        else:
            print(f"- `{target}` <- 空")
    print("\n## 预览")
    print(json.dumps(result["preview"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
