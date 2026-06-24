#!/usr/bin/env python3
"""Extract an HTML table from an official page into a raw CSV file."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract raw table rows from an official HTML page.")
    parser.add_argument("--input", required=True, help="Official HTML file saved locally")
    parser.add_argument("--output", required=True, help="Raw CSV output path")
    parser.add_argument("--table-index", type=int, default=0, help="0-based table index; defaults to first table")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"输入文件不存在：{input_path}")
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise SystemExit("读取 HTML 表格需要 pandas/lxml。请使用 Codex 内置 Python 运行。") from exc

    tables = pd.read_html(input_path, header=None)
    if args.table_index < 0 or args.table_index >= len(tables):
        raise SystemExit(f"表格序号超出范围：{args.table_index}；共 {len(tables)} 个表格")
    table = tables[args.table_index]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_path, index=False, header=False)
    print("# HTML 表格转 CSV")
    print(f"- 输入：{input_path}")
    print(f"- 表格数：{len(tables)}")
    print(f"- 选中表格：{args.table_index}")
    print(f"- 行列：{table.shape[0]} x {table.shape[1]}")
    print(f"- 输出：{output_path}")


if __name__ == "__main__":
    main()
