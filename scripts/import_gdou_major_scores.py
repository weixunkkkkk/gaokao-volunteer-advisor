#!/usr/bin/env python3
"""Import Guangdong Ocean University official 2025 Guangdong major scores."""

from __future__ import annotations

import argparse
import csv
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_NAME = "广东海洋大学招生网"
SCHOOL_NAME = "广东海洋大学"
PAGES = {
    2025: "https://zsjy.gdou.edu.cn/info/1174/1606.htm",
}
RAW_CACHE = {
    2025: Path("assets/raw-cache/gdou/2025-guangdong-major-scores.html"),
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
        self.in_table = False
        self.in_cell = False
        self.tables: list[list[list[str]]] = []
        self.rows: list[list[str]] = []
        self.row: list[str] = []
        self.buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.in_table = True
            self.rows = []
        if self.in_table and tag == "tr":
            self.row = []
        if self.in_table and tag in {"td", "th"}:
            self.in_cell = True
            self.buf = []

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self.in_table and tag in {"td", "th"} and self.in_cell:
            self.row.append(" ".join("".join(self.buf).split()))
            self.in_cell = False
        if self.in_table and tag == "tr":
            if any(self.row):
                self.rows.append(self.row)
        if tag == "table" and self.in_table:
            self.tables.append(self.rows)
            self.in_table = False


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def int_text(value: object) -> str:
    return re.sub(r"\D", "", norm(value).replace(",", ""))


def score_text(value: object) -> str:
    text = norm(value)
    if text in {"", "/"}:
        return ""
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return ""
    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else str(number)


def track_text(value: str) -> str:
    if "物理" in value:
        return "物理类"
    if "历史" in value:
        return "历史类"
    return value


def plan_type(category: str, major_name: str) -> str:
    text = f"{category} {major_name}"
    if "地方专项" in text:
        return "地方专项"
    if "中外" in text:
        return "中外合作"
    if "航海" in text:
        return "航海类"
    if "体育" in text:
        return "体育类"
    if "艺术" in text or any(word in text for word in ["音乐", "舞蹈", "美术", "播音", "表演"]):
        return "艺术类"
    return category or "普通类"


def fetch_html(year: int) -> str:
    cache_path = RAW_CACHE[year]
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8", errors="ignore")
    text = urlopen(Request(PAGES[year], headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "ignore")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(text, encoding="utf-8")
    return text


def fetch_tables(year: int) -> list[list[list[str]]]:
    text = fetch_html(year)
    parser = TableParser()
    parser.feed(text)
    return parser.tables


def parse_tables(args: argparse.Namespace, year: int, tables: list[list[list[str]]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    state = {"batch": "", "category": "", "track": "", "college": "", "campus": ""}
    for table in tables:
        for raw in table:
            cells = [cell for cell in raw if cell]
            if not cells or cells[0] == "批次":
                continue
            if len(cells) >= 12 and track_text(cells[2]) not in {"物理类", "历史类"}:
                state = {
                    "batch": cells[0],
                    "category": cells[1],
                    "track": track_text(cells[2]),
                    "college": cells[10],
                    "campus": cells[11],
                }
                continue
            if len(cells) >= 10 and cells[0] in {"艺术类", "体育类"}:
                state = {
                    "batch": state["batch"],
                    "category": cells[0],
                    "track": track_text(cells[1]),
                    "college": cells[-2],
                    "campus": cells[-1],
                }
                continue
            if len(cells) >= 12 and track_text(cells[2]) in {"物理类", "历史类"}:
                state = {
                    "batch": cells[0],
                    "category": cells[1],
                    "track": track_text(cells[2]),
                    "college": cells[10],
                    "campus": cells[11],
                }
                major_name, plan_count, admit_count, min_score, min_rank, avg_score, major_group = (
                    cells[3],
                    cells[4],
                    cells[5],
                    cells[6],
                    cells[7],
                    cells[8],
                    cells[9],
                )
            elif state["track"] in {"物理类", "历史类"} and len(cells) >= 7:
                major_name, plan_count, admit_count, min_score, min_rank, avg_score, major_group = cells[:7]
                if len(cells) >= 9:
                    state["college"] = cells[7]
                    state["campus"] = cells[8]
            else:
                continue
            if state["track"] != args.track:
                continue
            if not score_text(min_score):
                continue
            rows.append(
                {
                    "year": str(year),
                    "province": args.province,
                    "track": args.track,
                    "batch": state["batch"],
                    "school_name": SCHOOL_NAME,
                    "school_code": args.school_code,
                    "major_group": int_text(major_group),
                    "major_name": major_name,
                    "plan_type": plan_type(state["category"], major_name),
                    "min_score": score_text(min_score),
                    "min_rank": int_text(min_rank),
                    "admit_count": int_text(admit_count),
                    "source_url": PAGES[year],
                    "source_name": SOURCE_NAME,
                    "notes": "；".join(
                        part
                        for part in [
                            "学校官网HTML专业投档录取分数",
                            f"计划数={int_text(plan_count)}" if int_text(plan_count) else "",
                            f"投档平均分={score_text(avg_score)}" if score_text(avg_score) else "",
                            f"类别={state['category']}" if state["category"] else "",
                            f"学院={state['college']}" if state["college"] else "",
                            f"校区={state['campus']}" if state["campus"] else "",
                        ]
                        if part
                    ),
                }
            )
    return dedupe_rows(rows)


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for year in args.years:
        rows.extend(parse_tables(args, year, fetch_tables(year)))
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["batch"], row["major_group"], row["major_name"], row["plan_type"])
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
                and norm(row.get("province")) == args.province
                and norm(row.get("track")) == args.track
                and (not args.batch or norm(row.get("batch")) == args.batch)
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - set(PAGES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"GDOU importer maps 2025 only right now, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Guangdong Ocean University official Guangdong major-level scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="")
    parser.add_argument("--school-code", default="")
    parser.add_argument("--years", type=parse_years, default=[2025])
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = normalized_rows(args)
    by_year: dict[str, int] = {}
    by_plan: dict[str, int] = {}
    for row in rows:
        by_year[row["year"]] = by_year.get(row["year"], 0) + 1
        by_plan[row["plan_type"]] = by_plan.get(row["plan_type"], 0) + 1
    print("# 广东海洋大学专业录取分数导入\n")
    print(f"- 来源：{PAGES[2025]}")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(year) for year in args.years)}")
    print(f"- 获取专业记录：{len(rows)}；分年：{by_year}；类型：{by_plan}")
    print(f"- 输出目录：{Path(args.data_dir).expanduser().resolve()}")
    if rows:
        print(f"- 预览：{rows[:5]}")
    if args.dry_run:
        print("- 模式：预览，不写入")
        return
    before, after = import_rows(args, rows)
    print(f"- 模式：写入；原记录 {before}，写入后 {after}")


if __name__ == "__main__":
    main()
