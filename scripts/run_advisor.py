#!/usr/bin/env python3
"""Friendly entry point for running the Gaokao advisor skill."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT_DATA_DIR = ROOT / "assets" / "pilot-data"
NATIONAL_DATA_DIR = ROOT / "assets" / "national-data"
sys.path.insert(0, str(ROOT / "scripts"))

from recommend import build_result, render_markdown  # noqa: E402


@dataclass
class DataProfile:
    name: str
    data_dir: Path
    province: str
    track: str
    admission_rows: int
    rank_rows: int


def norm(value: str | None) -> str:
    return (value or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def discover_profiles() -> list[DataProfile]:
    profiles: list[DataProfile] = []
    for root_dir in [PILOT_DATA_DIR, NATIONAL_DATA_DIR]:
        if not root_dir.exists():
            continue
        for data_dir in sorted(path for path in root_dir.iterdir() if path.is_dir()):
            admissions = read_csv(data_dir / "admission_records.csv")
            ranks = read_csv(data_dir / "rank_table.csv")
            province = next((norm(row.get("province")) for row in admissions if norm(row.get("province"))), "")
            track = next((norm(row.get("track")) for row in admissions if norm(row.get("track"))), "")
            if province and track:
                profiles.append(
                    DataProfile(
                        name=f"{root_dir.name}/{data_dir.name}",
                        data_dir=data_dir,
                        province=province,
                        track=track,
                        admission_rows=len(admissions),
                        rank_rows=len(ranks),
                    )
                )
    return profiles


def choose_profile(profiles: list[DataProfile], province: str | None, track: str | None) -> DataProfile:
    if province:
        matches = [item for item in profiles if item.province == province and (not track or item.track == track)]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            available = "；".join(f"{item.province}/{item.track}" for item in profiles)
            raise SystemExit(f"当前没有 {province}{'/' + track if track else ''} 的正式可用数据。可用：{available}")
        options = "\n".join(f"- {item.province}/{item.track}：{item.name}" for item in matches)
        raise SystemExit(f"{province} 有多个科类，请补充 --track。\n{options}")

    print("当前可用数据：")
    for index, item in enumerate(profiles, 1):
        print(f"{index}. {item.province}/{item.track} ({item.name})")
    while True:
        raw = input("选择省份数据编号：").strip()
        try:
            selected = int(raw)
        except ValueError:
            print("请输入编号。")
            continue
        if 1 <= selected <= len(profiles):
            return profiles[selected - 1]
        print("编号超出范围。")


def prompt_int(label: str, required: bool) -> int | None:
    while True:
        raw = input(label).strip()
        if not raw and not required:
            return None
        try:
            return int(raw)
        except ValueError:
            print("请输入数字。")


def build_recommend_args(args: argparse.Namespace, profile: DataProfile) -> argparse.Namespace:
    score = args.score
    rank = args.rank
    interests = args.interests
    if score is None and rank is None:
        score = prompt_int("输入高考分数：", required=True)
        rank = prompt_int("输入位次，未知可直接回车：", required=False)
    if interests is None:
        interests = input("输入感兴趣方向，用逗号分隔，未知可回车：").strip()

    return argparse.Namespace(
        province=profile.province,
        track=profile.track,
        score=score,
        rank=rank,
        interests=interests or "",
        data_dir=str(profile.data_dir),
        per_level=args.per_level,
        major_limit=args.major_limit,
        include_risky=args.include_risky,
        include_special_plans=args.include_special_plans,
        target_years=args.target_years,
        format=args.format,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Gaokao volunteer advisor with less setup.")
    parser.add_argument("--province", help="Candidate province, e.g. 上海")
    parser.add_argument("--track", help="Subject track, e.g. 普通类 or 物理类")
    parser.add_argument("--score", type=int, help="Gaokao score")
    parser.add_argument("--rank", type=int, help="Candidate rank/位次")
    parser.add_argument("--interests", help="Comma-separated interests, e.g. 人工智能,财经")
    parser.add_argument("--per-level", type=int, default=5)
    parser.add_argument("--major-limit", type=int, default=5)
    parser.add_argument("--include-risky", action="store_true")
    parser.add_argument("--include-special-plans", action="store_true", help="Include提前批、专项、定向、艺术体育等特殊计划")
    parser.add_argument("--target-years", default="2023,2024,2025")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    profiles = discover_profiles()
    if not profiles:
        raise SystemExit("还没有正式可用数据包。请先导入并审计 assets/pilot-data 或 assets/national-data。")
    profile = choose_profile(profiles, args.province, args.track)
    recommend_args = build_recommend_args(args, profile)
    result = build_result(recommend_args)
    if args.format == "json":
        import json

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print(render_markdown(result))


if __name__ == "__main__":
    main()
