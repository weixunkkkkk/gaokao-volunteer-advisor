#!/usr/bin/env python3
"""Audit nationwide Gaokao coverage roadmap and usable data directories."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "assets" / "source-discovery" / "national" / "province_manifest.csv"
DEFAULT_PROVINCE_MAP = ROOT / "assets" / "source-discovery" / "national" / "gaokao_cn_province_id_map.csv"
DEFAULT_SCHOOL_IDS = ROOT / "assets" / "source-discovery" / "national" / "gaokao_cn_school_ids.csv"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_int(value: str | None) -> int | None:
    text = (value or "").strip().replace(",", "")
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def resolve_data_dirs(raw: str) -> list[Path]:
    dirs: list[Path] = []
    for chunk in (raw or "").split("|"):
        chunk = chunk.strip()
        if not chunk:
            continue
        path = Path(chunk)
        dirs.append(path if path.is_absolute() else ROOT / path)
    return dirs


def rows_and_years(path: Path, filename: str) -> tuple[int, set[int]]:
    rows = read_csv(path / filename)
    years = {year for row in rows if (year := as_int(row.get("year"))) is not None}
    return len(rows), years


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def summarize_dirs(data_dirs: list[Path], target_years: set[int]) -> dict[str, object]:
    if not data_dirs:
        return {
            "kind": "missing",
            "usable": False,
            "admission_rows": 0,
            "rank_rows": 0,
            "missing_admission_years": sorted(target_years),
            "missing_rank_years": sorted(target_years),
            "labels": [],
        }

    admission_rows = 0
    rank_rows = 0
    missing_admission: set[int] = set()
    missing_rank: set[int] = set()
    labels: list[str] = []
    has_data_dir = False
    has_source_only_dir = False

    for data_dir in data_dirs:
        labels.append(display_path(data_dir))
        admission_path = data_dir / "admission_records.csv"
        rank_path = data_dir / "rank_table.csv"
        if admission_path.exists() or rank_path.exists():
            has_data_dir = True
            current_admission_rows, admission_years = rows_and_years(data_dir, "admission_records.csv")
            current_rank_rows, rank_years = rows_and_years(data_dir, "rank_table.csv")
            admission_rows += current_admission_rows
            rank_rows += current_rank_rows
            missing_admission.update(target_years - admission_years)
            missing_rank.update(target_years - rank_years)
        elif data_dir.exists():
            has_source_only_dir = True
            missing_admission.update(target_years)
            missing_rank.update(target_years)
        else:
            missing_admission.update(target_years)
            missing_rank.update(target_years)

    usable = has_data_dir and admission_rows > 0 and rank_rows > 0 and not missing_admission and not missing_rank
    if usable:
        kind = "usable_data"
    elif has_data_dir:
        kind = "partial_data"
    elif has_source_only_dir:
        kind = "source_discovery"
    else:
        kind = "missing"

    return {
        "kind": kind,
        "usable": usable,
        "admission_rows": admission_rows,
        "rank_rows": rank_rows,
        "missing_admission_years": sorted(missing_admission),
        "missing_rank_years": sorted(missing_rank),
        "labels": labels,
    }


def render_table(rows: list[list[str]], headers: list[str]) -> str:
    if not rows:
        return ""
    def clean_cell(value: str) -> str:
        return value.replace("\n", " ").replace("|", "\\|")

    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    output.extend("| " + " | ".join(clean_cell(cell) for cell in row) + " |" for row in rows)
    return "\n".join(output)


def years_text(years: list[int]) -> str:
    return ",".join(str(year) for year in years) if years else "-"


def build_report(args: argparse.Namespace) -> str:
    target_years = {int(chunk.strip()) for chunk in args.target_years.replace("，", ",").split(",") if chunk.strip()}
    manifest_rows = read_csv(Path(args.manifest))
    province_map_rows = read_csv(Path(args.province_map))
    school_id_rows = read_csv(Path(args.school_ids))

    rank_status_counts = Counter(row.get("rank_status", "") for row in manifest_rows)
    admission_status_counts = Counter(row.get("admission_status", "") for row in manifest_rows)

    detail_rows: list[list[str]] = []
    usable_provinces = 0
    source_only_provinces = 0
    partial_data_provinces = 0
    missing_provinces = 0

    for row in manifest_rows:
        summary = summarize_dirs(resolve_data_dirs(row.get("current_data_dir", "")), target_years)
        if summary["usable"]:
            usable_provinces += 1
        elif summary["kind"] == "source_discovery":
            source_only_provinces += 1
        elif summary["kind"] == "partial_data":
            partial_data_provinces += 1
        else:
            missing_provinces += 1

        missing_text = (
            f"录取:{years_text(summary['missing_admission_years'])}; "
            f"位次:{years_text(summary['missing_rank_years'])}"
        )
        detail_rows.append(
            [
                row.get("province", ""),
                row.get("mode", ""),
                row.get("tracks", ""),
                row.get("rank_status", ""),
                row.get("admission_status", ""),
                "是" if summary["usable"] else "否",
                str(summary["admission_rows"]),
                str(summary["rank_rows"]),
                missing_text,
                "；".join(summary["labels"]) if summary["labels"] else "-",
            ]
        )

    lines = ["# 全国高考志愿覆盖审计", ""]
    lines.append(f"- 省份台账行数：{len(manifest_rows)}")
    lines.append(f"- 掌上高考省份ID：{len(province_map_rows)}")
    lines.append(f"- 掌上高考学校ID行数：{len(school_id_rows)}（未按本科过滤，正式全国本科清单仍需教育部/阳光高考复核）")
    lines.append(f"- 当前可用于推荐的省份：{usable_provinces}/{len(manifest_rows)}")
    lines.append(f"- 只有来源发现目录的省份：{source_only_provinces}")
    lines.append(f"- 有部分数据但未满足三年审计的省份：{partial_data_provinces}")
    lines.append(f"- 尚无本地数据目录的省份：{missing_provinces}")
    lines.append("- 一分一段状态：" + "；".join(f"{key}={value}" for key, value in sorted(rank_status_counts.items())))
    lines.append("- 投档/录取状态：" + "；".join(f"{key}={value}" for key, value in sorted(admission_status_counts.items())))
    lines.append("")
    lines.append("## 省份明细")
    lines.append(
        render_table(
            detail_rows,
            ["省份", "模式", "科类", "位次状态", "录取状态", "可推荐", "录取行", "位次行", "缺年份", "当前目录"],
        )
    )
    lines.append("")
    lines.append("## 使用结论")
    lines.append("- `可推荐=是` 只表示本地目录有 2023-2025 录取线和一分一段基础数据，仍需正式填报前核验 2026 招生计划、选科、学费、校区和体检限制。")
    lines.append("- `source_discovery` 目录只表示来源已发现或 OCR 草稿存在，不能直接用于真实考生推荐。")
    lines.append("- 掌上高考/API 专业线可作为批量补充，但必须保留聚合来源和 `待官方复核` 标记。")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit nationwide Gaokao coverage status.")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--province-map", default=str(DEFAULT_PROVINCE_MAP))
    parser.add_argument("--school-ids", default=str(DEFAULT_SCHOOL_IDS))
    parser.add_argument("--target-years", default="2023,2024,2025")
    return parser.parse_args()


def main() -> None:
    print(build_report(parse_args()))


if __name__ == "__main__":
    main()
