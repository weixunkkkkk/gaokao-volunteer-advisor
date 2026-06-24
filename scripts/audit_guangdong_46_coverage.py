#!/usr/bin/env python3
"""Audit Guangdong 46 public-undergraduate coverage for the advisor skill."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = ROOT / "assets" / "source-discovery" / "guangdong" / "target_public_undergraduate_schools_2026.csv"
DEFAULT_INVENTORY = ROOT / "assets" / "source-discovery" / "guangdong" / "major_source_inventory.csv"
DEFAULT_PHYSICS = ROOT / "assets" / "pilot-data" / "guangdong-physics"
DEFAULT_HISTORY = ROOT / "assets" / "pilot-data" / "guangdong-history"
TRACK_DIRS = {
    "物理类": DEFAULT_PHYSICS,
    "历史类": DEFAULT_HISTORY,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean_major_name(raw: str) -> str:
    text = (raw or "").strip()
    text = text.replace("〈", "（").replace("〉", "）").replace("《", "（").replace("》", "）")
    text = re.sub(r"^[/\s]+", "", text)
    text = re.sub(r"^[A-Z]?\d{2,4}[.、\-\s]*", "", text)
    text = re.sub(r"[（(【\[].*$", "", text)
    text = re.sub(r"\d+年?$", "", text)
    text = re.sub(r"\d+$", "", text)
    text = text.replace("（", "").replace("）", "")
    text = re.sub(r"\s+", "", text)
    text = text.strip(" /-—_，,；;:：")
    if text.endswith("师范"):
        text = text[:-2]
    return text


def valid_major_name(name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 26:
        return False
    if any(token in name for token in ["专业组", "历史组", "物理组", "音教组", "舞蹈类组", "招生办", "学分互认"]):
        return False
    if re.search(r"[A-Za-z]", name):
        return False
    return bool(re.search(r"[\u4e00-\u9fff]", name))


def target_school_names(path: Path) -> list[str]:
    return [row["school_name"].strip() for row in read_csv(path) if row.get("school_name", "").strip()]


def inventory_by_school(path: Path) -> dict[str, dict[str, str]]:
    return {row["school_name"].strip(): row for row in read_csv(path) if row.get("school_name", "").strip()}


def admission_rows_by_track(track_dirs: dict[str, Path]) -> dict[str, list[dict[str, str]]]:
    return {
        track: read_csv(data_dir / "admission_records.csv")
        for track, data_dir in track_dirs.items()
    }


def major_profiles(data_dir: Path) -> set[str]:
    names: set[str] = set()
    for row in read_csv(data_dir / "majors.csv"):
        name = clean_major_name(row.get("major_name", ""))
        if valid_major_name(name):
            names.add(name)
    return names


def year_counts(rows: list[dict[str, str]], school: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        if row.get("school_name") == school:
            counter[row.get("year", "")] += 1
    return counter


def row_counts(rows: list[dict[str, str]], school: str) -> tuple[int, int, int]:
    selected = [row for row in rows if row.get("school_name") == school]
    major_level = sum(1 for row in selected if row.get("major_name", "").strip())
    aggregator = sum(1 for row in selected if "聚合" in row.get("source_name", "") or "掌上高考" in row.get("source_name", ""))
    return len(selected), major_level, aggregator


def collect_clean_major_names(rows: list[dict[str, str]]) -> set[str]:
    output: set[str] = set()
    for row in rows:
        name = clean_major_name(row.get("major_name", ""))
        if valid_major_name(name):
            output.add(name)
    return output


def render_table(rows: list[list[str]], headers: list[str]) -> str:
    if not rows:
        return ""
    output = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    output.extend("| " + " | ".join(cell.replace("\n", " ") for cell in row) + " |" for row in rows)
    return "\n".join(output)


def build_report(args: argparse.Namespace) -> str:
    target_names = target_school_names(Path(args.targets))
    inventory = inventory_by_school(Path(args.inventory))
    track_dirs = {
        "物理类": Path(args.physics_dir).expanduser().resolve(),
        "历史类": Path(args.history_dir).expanduser().resolve(),
    }
    rows_by_track = admission_rows_by_track(track_dirs)
    profile_names_by_track = {track: major_profiles(data_dir) for track, data_dir in track_dirs.items()}
    clean_majors_by_track = {track: collect_clean_major_names(rows) for track, rows in rows_by_track.items()}
    missing_profiles_by_track = {
        track: sorted(clean_majors - profile_names_by_track[track])
        for track, clean_majors in clean_majors_by_track.items()
    }
    missing_profiles_count = sum(len(names) for names in missing_profiles_by_track.values())

    lines = ["# 广东46所公办本科覆盖审计", ""]
    lines.append(f"- 目标学校数：{len(target_names)}")
    lines.append(f"- 物理类记录数：{len(rows_by_track['物理类'])}")
    lines.append(f"- 历史类记录数：{len(rows_by_track['历史类'])}")
    lines.append(
        "- 专业画像数："
        + "；".join(f"{track}={len(names)}" for track, names in profile_names_by_track.items())
    )
    lines.append(f"- 已导入专业名画像缺口：{missing_profiles_count}")
    status_counts = Counter(row.get("status", "") for row in inventory.values())
    lines.append("- 来源状态：" + "；".join(f"{key}={value}" for key, value in sorted(status_counts.items())))
    lines.append("")

    summary_rows: list[list[str]] = []
    missing_any_track: list[str] = []
    for index, school in enumerate(target_names, 1):
        inv = inventory.get(school, {})
        physics_years = year_counts(rows_by_track["物理类"], school)
        history_years = year_counts(rows_by_track["历史类"], school)
        physics_total, physics_major, physics_agg = row_counts(rows_by_track["物理类"], school)
        history_total, history_major, history_agg = row_counts(rows_by_track["历史类"], school)
        if not physics_total or not history_total:
            missing_any_track.append(school)
        summary_rows.append(
            [
                str(index),
                school,
                inv.get("status", "-"),
                inv.get("coverage", "-"),
                "/".join(f"{year}:{physics_years.get(year, 0)}" for year in ["2023", "2024", "2025"]),
                f"{physics_total}/{physics_major}/{physics_agg}",
                "/".join(f"{year}:{history_years.get(year, 0)}" for year in ["2023", "2024", "2025"]),
                f"{history_total}/{history_major}/{history_agg}",
            ]
        )

    lines.append("## 学校覆盖明细")
    lines.append(
        render_table(
            summary_rows,
            [
                "#",
                "学校",
                "来源状态",
                "台账覆盖",
                "物理年行数",
                "物理总/专业/聚合",
                "历史年行数",
                "历史总/专业/聚合",
            ],
        )
    )
    lines.append("")

    if missing_any_track:
        lines.append("## 单科类无记录说明")
        for school in missing_any_track:
            inv = inventory.get(school, {})
            lines.append(f"- {school}：{inv.get('notes', '当前数据中仅见另一科类本科招生记录，需按当年招生计划复核。')}")
        lines.append("")

    lines.append("## 结论")
    physics_present = {row.get("school_name") for row in rows_by_track["物理类"]}
    history_present = {row.get("school_name") for row in rows_by_track["历史类"]}
    all_present = [school for school in target_names if school in physics_present or school in history_present]
    lines.append(f"- 46校至少一个科类有本科录取记录：{len(all_present)}/{len(target_names)}")
    lines.append(f"- 物理类有记录学校：{sum(1 for school in target_names if school in physics_present)}/{len(target_names)}")
    lines.append(f"- 历史类有记录学校：{sum(1 for school in target_names if school in history_present)}/{len(target_names)}")
    lines.append(f"- 已导入专业名均有专业画像：{'是' if not missing_profiles_count else '否'}")
    for track, missing_profiles in missing_profiles_by_track.items():
        if missing_profiles:
            lines.append(f"- {track}缺画像专业：" + "、".join(missing_profiles[:50]))
    lines.append("- `imported_aggregator` 表示已用聚合/API补充入库，正式填报前仍需用学校官网、招生计划或招生章程复核。")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit Guangdong 46 public-undergraduate coverage.")
    parser.add_argument("--targets", default=str(DEFAULT_TARGETS))
    parser.add_argument("--inventory", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--physics-dir", default=str(DEFAULT_PHYSICS))
    parser.add_argument("--history-dir", default=str(DEFAULT_HISTORY))
    return parser.parse_args()


def main() -> None:
    print(build_report(parse_args()))


if __name__ == "__main__":
    main()
