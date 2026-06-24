#!/usr/bin/env python3
"""Import supplemental Guangdong major scores from the Gaokao.cn public API."""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


SOURCE_NAME = "掌上高考（聚合补充）"
API_URL = "https://static-data.gaokao.cn/www/2.0/schoolspecialscore/{school_id}/{year}/{province_id}.json"

TARGET_SCHOOLS = {
    "广东海洋大学": 288,
    "韶关学院": 298,
    "佛山大学": 306,
    "南方科技大学": 2941,
    "广东金融学院": 1031,
    "肇庆学院": 961,
    "广东轻工职业技术大学": 2048,
    "深圳职业技术大学": 646,
    "广州职业技术大学": 2481,
    "深圳信息职业技术大学": 985,
    "肇庆医学院": 968,
    "深圳理工大学": 3704,
    "大湾区大学": 3810,
    "顺德职业技术大学": 974,
    "广东警官学院": 963,
    "广州体育学院": 303,
    "广州美术学院": 304,
    "星海音乐学院": 305,
}

ADMISSION_COLUMNS = [
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
]


def norm(value: object) -> str:
    return str(value or "").strip().replace("（", "").replace("）", "") if value is not None else ""


def clean_group(value: object) -> str:
    text = str(value or "").strip()
    return text.replace("（", "").replace("）", "")


def numeric_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip().replace(",", "")
    if not text or text in {"0", "-", "--"}:
        return ""
    try:
        number = int(float(text))
    except ValueError:
        return ""
    return str(number)


def track_from_item(item: dict[str, object]) -> str:
    first_km = str(item.get("first_km", ""))
    item_type = str(item.get("type", ""))
    type_name = str(item.get("type_name") or "")
    sg_info = str(item.get("sg_info", ""))
    if first_km == "70000" or item_type == "2073" or "首选物理" in sg_info:
        return "物理类"
    if first_km == "70004" or item_type == "2074" or "首选历史" in sg_info:
        return "历史类"
    if item_type == "3" or type_name in {"综合", "普通类"}:
        return "普通类"
    if item_type == "1" or type_name == "理科":
        return "理科"
    if item_type == "2" or type_name == "文科":
        return "文科"
    if type_name:
        return type_name
    return ""


def fetch_api(school_id: int, year: int, province_id: int) -> dict[str, object]:
    url = API_URL.format(school_id=school_id, year=year, province_id=province_id)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.gaokao.cn/",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return {"code": "404", "data": {}}
        raise


def is_undergraduate(item: dict[str, object]) -> bool:
    level = str(item.get("level1_name", ""))
    batch = str(item.get("local_batch_name", ""))
    return "本科" in level and "本科" in batch


def plan_type(school_name: str, item: dict[str, object]) -> str:
    zslx = str(item.get("zslx_name") or "").strip()
    batch = str(item.get("local_batch_name") or "").strip()
    info = str(item.get("info") or item.get("spname") or "").strip()
    marker_text = f"{batch} {info}"
    if "提前" in batch and school_name == "广东警官学院":
        return "公安提前批"
    if "提前" in batch:
        return "提前批"
    if "地方专项" in marker_text:
        return "地方专项"
    if "教师专项" in marker_text:
        return "教师专项"
    if "卫生专项" in marker_text or "免费医学生" in marker_text:
        return "卫生专项"
    if "协同培养" in marker_text:
        return "协同培养"
    if "中外" in marker_text:
        return "中外合作"
    if "国际班" in marker_text:
        return "国际班"
    if "学分互认" in marker_text:
        return "学分互认"
    if "校企" in marker_text:
        return "校企联合培养"
    if zslx and zslx != "-":
        return zslx
    return batch or "普通类"


def normalize_item(
    school_name: str,
    school_id: int,
    year: int,
    item: dict[str, object],
    args: argparse.Namespace,
) -> dict[str, str] | None:
    track = track_from_item(item)
    if track != args.track:
        return None
    if not is_undergraduate(item):
        return None
    min_score = numeric_text(item.get("min"))
    min_rank = numeric_text(item.get("min_section"))
    major_name = str(item.get("sp_name") or item.get("spname") or "").strip()
    if not min_score or not major_name:
        return None
    source_url = API_URL.format(school_id=school_id, year=year, province_id=args.province_id)
    info_parts = [
        f"聚合站来源，待官方复核；掌上高考公开API补充",
        f"school_id={school_id}",
        f"province_id={args.province_id}",
        f"原始专业名={item.get('spname', '')}",
        f"批次={item.get('local_batch_name', '')}",
        f"选科={item.get('sg_info', '')}",
        f"类别={item.get('level1_name', '')}/{item.get('level2_name', '')}/{item.get('level3_name', '')}",
        f"备注={item.get('info', '')}",
    ]
    return {
        "year": str(year),
        "province": args.province,
        "track": track,
        "batch": str(item.get("local_batch_name") or args.batch).strip(),
        "school_name": school_name,
        "school_code": "",
        "major_group": clean_group(item.get("sg_name")),
        "major_name": major_name,
        "plan_type": plan_type(school_name, item),
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": numeric_text(item.get("lq_num")),
        "source_url": source_url,
        "source_name": SOURCE_NAME,
        "notes": "；".join(part for part in info_parts if part and not part.endswith("=")),
    }


def fetch_rows_for_school(
    school_name: str,
    school_id: int,
    args: argparse.Namespace,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in args.years:
        payload = fetch_api(school_id, year, args.province_id)
        data = payload.get("data") if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            continue
        for section in data.values():
            if not isinstance(section, dict):
                continue
            for item in section.get("item", []):
                if not isinstance(item, dict):
                    continue
                row = normalize_item(school_name, school_id, year, item, args)
                if row:
                    rows.append(row)
        time.sleep(args.sleep)
    return dedupe_rows(rows)


def row_key(row: dict[str, str]) -> tuple[str, str, str, str, str, str, str, str]:
    return (
        row.get("year", ""),
        row.get("province", ""),
        row.get("track", ""),
        row.get("school_name", ""),
        row.get("major_group", ""),
        row.get("major_name", ""),
        row.get("plan_type", ""),
        row.get("batch", ""),
    )


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (*row_key(row), row.get("min_score", ""), row.get("min_rank", ""))
        if key in seen:
            continue
        seen.add(key)
        output.append(row)
    return output


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ADMISSION_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def merge_rows(existing: list[dict[str, str]], new_rows: list[dict[str, str]], args: argparse.Namespace) -> list[dict[str, str]]:
    target_schools = {row["school_name"] for row in new_rows}
    if args.replace_existing:
        existing = [
            row
            for row in existing
            if not (
                row.get("province") == args.province
                and row.get("track") == args.track
                and row.get("school_name") in target_schools
                and row.get("source_name") == SOURCE_NAME
            )
        ]
    existing_keys = {row_key(row) for row in existing if row.get("source_name") != SOURCE_NAME}
    filtered = [row for row in new_rows if row_key(row) not in existing_keys]
    skipped = len(new_rows) - len(filtered)
    print(f"Skipped {skipped} rows already covered by non-Gaokao.cn sources")
    return existing + filtered


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"Unsupported years: {unsupported}")
    return years


def parse_schools(raw: str) -> dict[str, int]:
    if not raw or raw == "target":
        return TARGET_SCHOOLS
    names = [chunk.strip() for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    missing = [name for name in names if name not in TARGET_SCHOOLS]
    if missing:
        raise argparse.ArgumentTypeError(f"Unknown schools: {missing}")
    return {name: TARGET_SCHOOLS[name] for name in names}


def load_schools_csv(path: Path) -> dict[str, int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise SystemExit(f"学校CSV缺少表头：{path}")
        output: dict[str, int] = {}
        for row in reader:
            name = (
                row.get("school_name")
                or row.get("name")
                or row.get("学校")
                or row.get("院校名称")
                or ""
            ).strip()
            school_id_raw = (row.get("school_id") or row.get("gaokao_school_id") or "").strip()
            if not name or not school_id_raw:
                continue
            try:
                school_id = int(float(school_id_raw))
            except ValueError as exc:
                raise SystemExit(f"学校ID格式错误：{school_id_raw} ({name})") from exc
            output[name] = school_id
    if not output:
        raise SystemExit(f"学校CSV没有可导入的 school_name/school_id 行：{path}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Gaokao.cn supplemental Guangdong major scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--province-id", type=int, default=44)
    parser.add_argument("--track", required=True, choices=["物理类", "历史类", "普通类", "理科", "文科"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--years", type=parse_years, default=[2023, 2024, 2025])
    parser.add_argument("--schools", type=parse_schools, default=TARGET_SCHOOLS)
    parser.add_argument("--schools-csv", help="CSV with school_name/name and school_id/gaokao_school_id columns; overrides --schools.")
    parser.add_argument("--sleep", type=float, default=0.1)
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    schools = load_schools_csv(Path(args.schools_csv).expanduser()) if args.schools_csv else args.schools
    rows: list[dict[str, str]] = []
    for school_name, school_id in schools.items():
        school_rows = fetch_rows_for_school(school_name, school_id, args)
        rows.extend(school_rows)
        print(f"{school_name}: fetched {len(school_rows)} {args.track} undergraduate rows")
    rows = dedupe_rows(rows)
    by_school: dict[str, int] = {}
    for row in rows:
        by_school[row["school_name"]] = by_school.get(row["school_name"], 0) + 1
    print(f"Prepared {len(rows)} {args.track} rows: {by_school}")
    if args.dry_run:
        for row in rows[:20]:
            print(row)
        return
    path = Path(args.data_dir).expanduser().resolve() / "admission_records.csv"
    existing = read_existing(path)
    before = len(existing)
    merged = merge_rows(existing, rows, args)
    write_rows(path, merged)
    print(f"Imported into {path} ({before} -> {len(merged)})")


if __name__ == "__main__":
    main()
