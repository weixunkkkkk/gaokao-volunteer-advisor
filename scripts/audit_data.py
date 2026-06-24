#!/usr/bin/env python3
"""Audit normalized Gaokao advising CSV coverage and obvious data risks."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = ROOT / "assets" / "data"

REQUIRED_COLUMNS = {
    "admission_records.csv": [
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
    ],
    "rank_table.csv": [
        "year",
        "province",
        "track",
        "score",
        "min_rank",
        "max_rank",
        "same_score_count",
        "source_url",
        "source_name",
    ],
    "majors.csv": [
        "interest_keywords",
        "major_name",
        "degree_category",
        "employment_outlook",
        "typical_roles",
        "fit_notes",
        "risk_notes",
    ],
    "source_registry.csv": [
        "province",
        "source_type",
        "source_name",
        "url",
        "verified_date",
        "notes",
    ],
    "collection_manifest.csv": [
        "province",
        "year",
        "dataset",
        "track",
        "article_title",
        "article_url",
        "attachment_url",
        "file_type",
        "status",
        "importer",
        "notes",
    ],
}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def norm(value: str | None) -> str:
    return (value or "").strip()


def as_int(value: str | None) -> int | None:
    value = norm(value).replace(",", "")
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def is_demo(row: dict[str, str]) -> bool:
    joined = " ".join(norm(value) for value in row.values()).upper()
    return "DEMO" in joined or "示例" in joined


def required_column_audit(data_dir: Path) -> list[dict[str, object]]:
    results = []
    for filename, required in REQUIRED_COLUMNS.items():
        path = data_dir / filename
        columns, rows = read_csv(path)
        missing = [column for column in required if column not in columns]
        results.append(
            {
                "file": filename,
                "exists": path.exists(),
                "rows": len(rows),
                "missing_columns": missing,
            }
        )
    return results


def grouped_year_coverage(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, object]]:
    groups: dict[tuple[str, str], dict[str, object]] = defaultdict(
        lambda: {"years": set(), "rows": 0, "demo_rows": 0, "missing_source_rows": 0}
    )
    for row in rows:
        province = norm(row.get("province")) or "UNKNOWN"
        track = norm(row.get("track")) or "UNKNOWN"
        year = as_int(row.get("year"))
        key = (province, track)
        groups[key]["rows"] = int(groups[key]["rows"]) + 1
        if year is not None:
            groups[key]["years"].add(year)
        if is_demo(row):
            groups[key]["demo_rows"] = int(groups[key]["demo_rows"]) + 1
        if not norm(row.get("source_url")) or not norm(row.get("source_name")):
            groups[key]["missing_source_rows"] = int(groups[key]["missing_source_rows"]) + 1
    return groups


def build_audit(data_dir: Path, target_years: list[int], province: str | None, track: str | None) -> dict[str, object]:
    file_audit = required_column_audit(data_dir)
    _, admission_rows = read_csv(data_dir / "admission_records.csv")
    _, rank_rows = read_csv(data_dir / "rank_table.csv")
    _, major_rows = read_csv(data_dir / "majors.csv")
    _, manifest_rows = read_csv(data_dir / "collection_manifest.csv")

    if province:
        admission_rows = [row for row in admission_rows if norm(row.get("province")) == province]
        rank_rows = [row for row in rank_rows if norm(row.get("province")) == province]
        manifest_rows = [row for row in manifest_rows if norm(row.get("province")) == province]
    if track:
        admission_rows = [row for row in admission_rows if norm(row.get("track")) == track]
        rank_rows = [row for row in rank_rows if norm(row.get("track")) == track]
        manifest_rows = [row for row in manifest_rows if not norm(row.get("track")) or norm(row.get("track")) == track]

    admission_groups = grouped_year_coverage(admission_rows)
    rank_groups = grouped_year_coverage(rank_rows)

    coverage = []
    keys = sorted(set(admission_groups) | set(rank_groups))
    target_set = set(target_years)
    for key in keys:
        admission = admission_groups.get(key, {"years": set(), "rows": 0, "demo_rows": 0, "missing_source_rows": 0})
        rank = rank_groups.get(key, {"years": set(), "rows": 0, "demo_rows": 0, "missing_source_rows": 0})
        admission_years = set(admission["years"])
        rank_years = set(rank["years"])
        coverage.append(
            {
                "province": key[0],
                "track": key[1],
                "admission_years": sorted(admission_years),
                "missing_admission_years": sorted(target_set - admission_years),
                "admission_rows": admission["rows"],
                "admission_demo_rows": admission["demo_rows"],
                "admission_missing_source_rows": admission["missing_source_rows"],
                "rank_years": sorted(rank_years),
                "missing_rank_years": sorted(target_set - rank_years),
                "rank_rows": rank["rows"],
                "rank_demo_rows": rank["demo_rows"],
                "rank_missing_source_rows": rank["missing_source_rows"],
            }
        )

    return {
        "data_dir": str(data_dir),
        "target_years": target_years,
        "files": file_audit,
        "coverage": coverage,
        "majors": {
            "rows": len(major_rows),
            "demo_rows": sum(1 for row in major_rows if is_demo(row)),
            "missing_keyword_rows": sum(1 for row in major_rows if not norm(row.get("interest_keywords"))),
        },
        "collection_manifest": summarize_manifest(manifest_rows, target_set),
    }


def summarize_manifest(rows: list[dict[str, str]], target_years: set[int]) -> dict[str, object]:
    status_counts: dict[str, int] = defaultdict(int)
    dataset_counts: dict[str, int] = defaultdict(int)
    missing = []
    for row in rows:
        status = norm(row.get("status")) or "UNKNOWN"
        dataset = norm(row.get("dataset")) or "UNKNOWN"
        status_counts[status] += 1
        dataset_counts[dataset] += 1
        year = as_int(row.get("year"))
        if status in {"needs_discovery", "needs_ocr"} or not norm(row.get("article_url")) or not norm(row.get("attachment_url")):
            if year is None or year in target_years:
                missing.append(
                    {
                        "province": norm(row.get("province")),
                        "year": year,
                        "dataset": dataset,
                        "track": norm(row.get("track")),
                        "title": norm(row.get("article_title")),
                        "status": status,
                    }
                )
    return {
        "rows": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "dataset_counts": dict(sorted(dataset_counts.items())),
        "needs_discovery": missing,
    }


def markdown_table(rows: list[list[str]], headers: list[str]) -> str:
    if not rows:
        return ""
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    output.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(output)


def render_markdown(audit: dict[str, object]) -> str:
    lines = ["# 高考志愿数据覆盖审计", ""]
    lines.append(f"- 数据目录：{audit['data_dir']}")
    lines.append(f"- 目标年份：{', '.join(str(year) for year in audit['target_years'])}")
    lines.append("")

    file_rows = []
    for item in audit["files"]:
        file_rows.append(
            [
                str(item["file"]),
                "是" if item["exists"] else "否",
                str(item["rows"]),
                ", ".join(item["missing_columns"]) if item["missing_columns"] else "-",
            ]
        )
    lines.append("## 文件结构")
    lines.append(markdown_table(file_rows, ["文件", "存在", "行数", "缺失字段"]))
    lines.append("")

    coverage_rows = []
    for item in audit["coverage"]:
        risks = []
        if item["missing_admission_years"]:
            risks.append("录取线缺年")
        if item["missing_rank_years"]:
            risks.append("一分一段缺年")
        if item["admission_demo_rows"] or item["rank_demo_rows"]:
            risks.append("含 demo")
        if item["admission_missing_source_rows"] or item["rank_missing_source_rows"]:
            risks.append("来源缺失")
        coverage_rows.append(
            [
                str(item["province"]),
                str(item["track"]),
                ", ".join(str(year) for year in item["admission_years"]) or "-",
                ", ".join(str(year) for year in item["missing_admission_years"]) or "-",
                str(item["admission_rows"]),
                ", ".join(str(year) for year in item["rank_years"]) or "-",
                ", ".join(str(year) for year in item["missing_rank_years"]) or "-",
                str(item["rank_rows"]),
                ", ".join(risks) if risks else "可用于进一步复核",
            ]
        )
    lines.append("## 省份/科类覆盖")
    if coverage_rows:
        lines.append(
            markdown_table(
                coverage_rows,
                ["省份", "科类", "录取线年份", "缺录取线", "录取线行数", "一分一段年份", "缺一分一段", "一分一段行数", "风险"],
            )
        )
    else:
        lines.append("- 没有可审计的省份/科类数据。")
    lines.append("")

    majors = audit["majors"]
    lines.append("## 专业库")
    lines.append(f"- 专业记录：{majors['rows']}；demo 行：{majors['demo_rows']}；缺关键词行：{majors['missing_keyword_rows']}")
    lines.append("")

    manifest = audit["collection_manifest"]
    lines.append("## 采集清单")
    lines.append(f"- 记录数：{manifest['rows']}")
    if manifest["status_counts"]:
        lines.append(
            "- 状态分布："
            + "；".join(f"{status}={count}" for status, count in manifest["status_counts"].items())
        )
    if manifest["dataset_counts"]:
        lines.append(
            "- 数据类型分布："
            + "；".join(f"{dataset}={count}" for dataset, count in manifest["dataset_counts"].items())
        )
    missing = manifest["needs_discovery"]
    if missing:
        rows = [
            [
                str(item["province"]),
                str(item["year"] or "-"),
                str(item["dataset"]),
                str(item["track"] or "-"),
                str(item["title"] or "-"),
                str(item["status"]),
            ]
            for item in missing
        ]
        lines.append(markdown_table(rows, ["省份", "年份", "数据", "科类", "标题", "状态"]))
    return "\n".join(lines)


def has_blocking_risk(audit: dict[str, object]) -> bool:
    for item in audit["files"]:
        if not item["exists"] or item["missing_columns"]:
            return True
    for item in audit["coverage"]:
        if (
            item["missing_admission_years"]
            or item["missing_rank_years"]
            or item["admission_demo_rows"]
            or item["rank_demo_rows"]
            or item["admission_missing_source_rows"]
            or item["rank_missing_source_rows"]
        ):
            return True
    return False


def parse_target_years(raw: str) -> list[int]:
    years = []
    for chunk in raw.replace("，", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            years.append(int(chunk))
    if not years:
        raise argparse.ArgumentTypeError("target years cannot be empty")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit normalized Gaokao advising data coverage.")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory containing normalized CSV files")
    parser.add_argument("--target-years", type=parse_target_years, default=[2023, 2024, 2025])
    parser.add_argument("--province", help="Optional province filter")
    parser.add_argument("--track", help="Optional track filter")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when blocking risks are found")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_audit(Path(args.data_dir).expanduser().resolve(), args.target_years, args.province, args.track)
    if args.format == "json":
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(audit))
    if args.strict and has_blocking_risk(audit):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
