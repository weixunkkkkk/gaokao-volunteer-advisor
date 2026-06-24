#!/usr/bin/env python3
"""Import JNU official major-level admission scores for Guangdong.

Source: 暨南大学招生办公室 province-specific admission score pages.
The official pages publish 2023, 2024, and 2025 Guangdong admission results
by major. This importer normalizes those HTML tables into admission_records.csv.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NAME = "暨南大学招生办公室"
SCHOOL_NAME = "暨南大学"
SOURCE_URLS = {
    2025: "https://zsb.jnu.edu.cn/2026/0331/c33879a852689/page.htm",
    2024: "https://zsb.jnu.edu.cn/2025/0307/c33879a831322/page.htm",
    2023: "https://zsb.jnu.edu.cn/2024/0410/c33879a810398/page.htm",
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


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.current_row = []
        if tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.in_cell:
            text = re.sub(r"\s+", " ", "".join(self.current_cell)).strip()
            self.current_row.append(text)
            self.in_cell = False
        if tag == "tr" and self.current_row:
            self.rows.append(self.current_row)


@dataclass
class RowContext:
    track: str = ""
    campus: str = ""
    college: str = ""


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def clean_group(value: str) -> str:
    return norm(value).replace("组", "")


def normalize_track(value: str) -> str:
    text = norm(value)
    if "物理" in text:
        return "物理类"
    if "历史" in text:
        return "历史类"
    return text


def normalize_plan_type(major_name: str, college: str) -> str:
    text = f"{major_name} {college}"
    if "中外合作" in text or "伯明翰大学联合学院" in text:
        return "中外合作办学"
    if "戏剧影视文学" in major_name:
        return "戏文单列"
    return "普通类"


def fetch_table(year: int) -> list[list[str]]:
    url = SOURCE_URLS[year]
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urlopen(request, timeout=30).read().decode("utf-8", "replace")
    parser = TableParser()
    parser.feed(html)
    return parser.rows


def is_summary(row: list[str]) -> bool:
    return any("汇总" in cell for cell in row)


def has_score_tail(row: list[str], tail_len: int) -> bool:
    if len(row) < tail_len:
        return False
    return all(re.fullmatch(r"\d+(?:\.\d+)?", cell) for cell in row[-tail_len:] if cell)


def row_for_output(
    *,
    year: int,
    source_url: str,
    target_track: str,
    batch: str,
    school_code: str,
    context: RowContext,
    major_group: str,
    major_name: str,
    admit_count: str,
    min_score: str,
    max_score: str,
    avg_score: str,
    min_rank: str,
) -> dict[str, str] | None:
    track = normalize_track(context.track)
    if track != target_track:
        return None
    if not major_name or not min_score.isdigit():
        return None
    notes = [
        "学校官网专业录取分数",
        f"校区={context.campus}" if context.campus else "",
        f"学院={context.college}" if context.college else "",
        f"最高分={max_score}" if max_score else "",
        f"平均分={avg_score}" if avg_score else "",
    ]
    return {
        "year": str(year),
        "province": "广东",
        "track": target_track,
        "batch": batch,
        "school_name": SCHOOL_NAME,
        "school_code": school_code,
        "major_group": clean_group(major_group),
        "major_name": major_name,
        "plan_type": normalize_plan_type(major_name, context.college),
        "min_score": min_score,
        "min_rank": min_rank,
        "admit_count": admit_count,
        "source_url": source_url,
        "source_name": SOURCE_NAME,
        "notes": "；".join(part for part in notes if part),
    }


def parse_2025(rows: list[list[str]], target_track: str, batch: str, school_code: str) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    context = RowContext()
    for row in rows[1:]:
        if is_summary(row):
            continue
        if len(row) == 9:
            context = RowContext(track=row[0], campus=row[1], college=row[2])
            major_name, admit_count, max_score, avg_score, min_score, min_rank = row[3:9]
        elif len(row) == 7 and has_score_tail(row, 5):
            context.college = row[0]
            major_name, admit_count, max_score, avg_score, min_score, min_rank = row[1:7]
        else:
            continue
        normalized = row_for_output(
            year=2025,
            source_url=SOURCE_URLS[2025],
            target_track=target_track,
            batch=batch,
            school_code=school_code,
            context=context,
            major_group="",
            major_name=major_name,
            admit_count=admit_count,
            min_score=min_score,
            max_score=max_score,
            avg_score=avg_score,
            min_rank=min_rank,
        )
        if normalized:
            output.append(normalized)
    return output


def parse_2024(rows: list[list[str]], target_track: str, batch: str, school_code: str) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    context = RowContext()
    for row in rows[1:]:
        if is_summary(row):
            continue
        if len(row) == 9:
            context = RowContext(track=row[0], campus=row[1], college=row[2])
            major_name, admit_count, min_score, max_score, avg_score, min_rank = row[3:9]
        elif len(row) == 7 and has_score_tail(row, 5):
            context.college = row[0]
            major_name, admit_count, min_score, max_score, avg_score, min_rank = row[1:7]
        elif len(row) == 6 and has_score_tail(row, 5):
            major_name, admit_count, min_score, max_score, avg_score, min_rank = row
        else:
            continue
        normalized = row_for_output(
            year=2024,
            source_url=SOURCE_URLS[2024],
            target_track=target_track,
            batch=batch,
            school_code=school_code,
            context=context,
            major_group="",
            major_name=major_name,
            admit_count=admit_count,
            min_score=min_score,
            max_score=max_score,
            avg_score=avg_score,
            min_rank=min_rank,
        )
        if normalized:
            output.append(normalized)
    return output


def parse_2023(rows: list[list[str]], target_track: str, batch: str, school_code: str) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in rows[1:]:
        if len(row) < 11 or is_summary(row):
            continue
        province, _, source_track, campus, college, major_name, admit_count, min_score, max_score, avg_score, group = row[:11]
        if province != "广东":
            continue
        context = RowContext(track=source_track, campus=campus, college=college)
        normalized = row_for_output(
            year=2023,
            source_url=SOURCE_URLS[2023],
            target_track=target_track,
            batch=batch,
            school_code=school_code,
            context=context,
            major_group=group,
            major_name=major_name,
            admit_count=admit_count,
            min_score=min_score,
            max_score=max_score,
            avg_score=avg_score,
            min_rank="",
        )
        if normalized:
            output.append(normalized)
    return output


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for year in args.years:
        rows = fetch_table(year)
        if year == 2025:
            output.extend(parse_2025(rows, args.track, args.batch, args.school_code))
        elif year == 2024:
            output.extend(parse_2024(rows, args.track, args.batch, args.school_code))
        elif year == 2023:
            output.extend(parse_2023(rows, args.track, args.batch, args.school_code))
        else:
            raise ValueError(f"Unsupported year: {year}")
    return output


def read_existing(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ADMISSION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def import_rows(args: argparse.Namespace, rows: list[dict[str, str]]) -> tuple[int, int]:
    path = Path(args.data_dir).expanduser().resolve() / "admission_records.csv"
    existing = read_existing(path)
    before = len(existing)
    if args.replace_existing:
        existing = [
            row
            for row in existing
            if not (
                norm(row.get("source_name")) == SOURCE_NAME
                and norm(row.get("school_name")) == SCHOOL_NAME
                and norm(row.get("province")) == "广东"
                and norm(row.get("track")) == args.track
                and norm(row.get("batch")) == args.batch
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = []
    for chunk in raw.replace("，", ",").split(","):
        chunk = chunk.strip()
        if chunk:
            years.append(int(chunk))
    if not years:
        raise argparse.ArgumentTypeError("years cannot be empty")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import JNU official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--track", required=True, help="Normalized target track, e.g. 物理类")
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default="")
    parser.add_argument("--years", type=parse_years, default=[2023, 2024, 2025])
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = normalized_rows(args)
    by_year: dict[str, int] = {}
    for row in rows:
        by_year[row["year"]] = by_year.get(row["year"], 0) + 1
    print("# 暨南大学专业录取分数导入\n")
    print("- 来源：")
    for year in args.years:
        print(f"  - {year}: {SOURCE_URLS[year]}")
    print(f"- 范围：广东 / {args.track} / {', '.join(str(y) for y in args.years)}")
    print(f"- 获取专业记录：{len(rows)}；分年：{by_year}")
    print(f"- 输出目录：{Path(args.data_dir).expanduser().resolve()}")
    if rows:
        print(f"- 预览：{rows[:3]}")
    if args.dry_run:
        print("- 模式：预览，不写入")
        return
    before, after = import_rows(args, rows)
    print(f"- 模式：写入；原记录 {before}，写入后 {after}")


if __name__ == "__main__":
    main()
