#!/usr/bin/env python3
"""Import SCNU official major-level admission scores for Guangdong.

Source: 华南师范大学本科招生网广东省录取情况 PDF attachments. The PDFs have a
text layer and are parsed via the local `pdftotext -layout` command.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_NAME = "华南师范大学本科招生网"
SCHOOL_NAME = "华南师范大学"
SOURCES = {
    2025: [
        ("普通类", "物理类", "2025年华南师范大学本科批普通类（物理类）投档情况表", "https://zsb.scnu.edu.cn/a/20260105/721.html", "https://statics.scnu.edu.cn/pics/zsb/2026/0605/1780625285776000.pdf"),
        ("普通类", "历史类", "2025年华南师范大学本科批普通类（历史类）投档情况表", "https://zsb.scnu.edu.cn/a/20260105/721.html", "https://statics.scnu.edu.cn/pics/zsb/2026/0605/1780625285389678.pdf"),
        ("地方专项", "", "2025年华南师范大学地方专项投档情况表", "https://zsb.scnu.edu.cn/a/20260105/721.html", "https://statics.scnu.edu.cn/pics/zsb/2026/0605/1780625285899414.pdf"),
    ],
    2024: [
        ("普通类", "物理类", "2024年华南师范大学本科批次普通类物理类", "http://zsb.scnu.edu.cn/a/20250127/672.html", "http://statics.scnu.edu.cn/pics/zsb/2025/0324/1742785853590789.pdf"),
        ("普通类", "历史类", "2024年华南师范大学本科批次普通类历史类", "http://zsb.scnu.edu.cn/a/20250127/672.html", "http://statics.scnu.edu.cn/pics/zsb/2025/0324/1742785853715118.pdf"),
        ("地方专项", "", "2024年华南师范大学本科批次地方专项", "http://zsb.scnu.edu.cn/a/20250127/672.html", "http://statics.scnu.edu.cn/pics/zsb/2025/0324/1742785853794403.pdf"),
    ],
    2023: [
        ("普通类", "物理类", "2023年华南师范大学本科批次普通类物理类", "http://zsb.scnu.edu.cn/a/20240124/630.html", "http://statics.scnu.edu.cn/pics/zsb/2024/0623/1719105671432739.pdf"),
        ("普通类", "历史类", "2023年华南师范大学本科批次普通类历史类", "http://zsb.scnu.edu.cn/a/20240124/630.html", "http://statics.scnu.edu.cn/pics/zsb/2024/0623/1719105671210144.pdf"),
        ("地方专项", "", "2023年华南师范大学本科批次地方专项", "http://zsb.scnu.edu.cn/a/20240124/630.html", "http://statics.scnu.edu.cn/pics/zsb/2024/0623/1719105671159606.pdf"),
    ],
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
    return "" if value is None else str(value).strip()


def normalize_track(value: str) -> str:
    if "物理" in value:
        return "物理类"
    if "历史" in value:
        return "历史类"
    return value


def clean_group(group: str) -> str:
    text = norm(group)
    text = re.sub(r"\.(物理|历史)组", "", text)
    text = text.replace("-地方专项", "")
    return text


def pdf_to_text(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "source.pdf"
        request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        path.write_bytes(urlopen(request, timeout=30).read())
        result = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout


def parse_text(
    *,
    text: str,
    year: int,
    source_track: str,
    target_track: str,
    plan_type: str,
    article_url: str,
    pdf_url: str,
    batch: str,
    school_code: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current_group = ""
    group_re = re.compile(r"(?P<group>\d{3}\.(?:物理|历史)组(?:（[^）]+）)?(?:-地方专项)?)")
    tail_re = re.compile(
        r"\s(?P<count>\d+)\s+(?P<max>\d+)\s+(?P<avg>\d+(?:\.\d+)?)\s+"
        r"(?P<min>\d+)\s+(?P<rank>\d+)(?:\s+\S+)?\s*$"
    )
    for raw_line in text.splitlines():
        line = raw_line.replace("\u3000", " ").strip()
        compact_line = re.sub(r"\s+", " ", line)
        if not line or "合计" in line or "投档" in line or "录取专业" in line or "第" in line and "页" in line:
            group_match = group_re.search(line)
            if group_match:
                current_group = group_match.group("group")
            continue
        group_match = group_re.search(line)
        row_group = current_group
        if group_match:
            row_group = group_match.group("group")
            current_group = row_group
        row_track = normalize_track(row_group or source_track)
        if row_track != target_track:
            continue
        tail_match = tail_re.search(line)
        if not tail_match:
            continue
        prefix = line[: tail_match.start()].strip()
        if group_match:
            prefix = prefix.replace(group_match.group("group"), " ", 1).strip()
        prefix = re.sub(r"^(10574|80002)\s+", "", prefix).strip()
        prefix = re.sub(r"^(不限|政治|化学|化学\+生物|化学\+地理)\s+", "", prefix).strip()
        major_match = re.search(r"(?:^|\s)(?P<code>\d{3})\s+(?P<rest>.+)$", prefix)
        if not major_match:
            continue
        rest = major_match.group("rest").strip()
        parts = [part.strip() for part in re.split(r"\s{2,}", rest) if part.strip()]
        if not parts:
            continue
        major_name = parts[0]
        if major_name in {"合计", "人数"} or re.fullmatch(r"\d+", major_name):
            continue
        college = parts[1] if len(parts) > 1 else ""
        campus = parts[2] if len(parts) > 2 else ""
        inline_college = re.search(r"(?P<major>.+?)\s+(?P<college>[^ ]+(?:学院|学部|书院|中心))$", major_name)
        if inline_college:
            major_name = inline_college.group("major").strip()
            college = inline_college.group("college").strip()
            campus = parts[1] if len(parts) > 1 else campus
        rows.append(
            {
                "year": str(year),
                "province": "广东",
                "track": target_track,
                "batch": batch,
                "school_name": SCHOOL_NAME,
                "school_code": school_code,
                "major_group": clean_group(row_group),
                "major_name": major_name,
                "plan_type": plan_type,
                "min_score": tail_match.group("min"),
                "min_rank": tail_match.group("rank"),
                "admit_count": tail_match.group("count"),
                "source_url": article_url,
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        "学校官网PDF专业录取分数",
                        f"PDF={pdf_url}",
                        f"学院={college}" if college else "",
                        f"校区={campus}" if campus else "",
                        f"最高分={tail_match.group('max')}",
                        f"平均分={tail_match.group('avg')}",
                    ]
                    if part
                ),
            }
        )
    return rows


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for year in args.years:
        for plan_type, source_track, _title, article_url, pdf_url in SOURCES[year]:
            if source_track and source_track != args.track:
                continue
            text = pdf_to_text(pdf_url)
            output.extend(
                parse_text(
                    text=text,
                    year=year,
                    source_track=source_track,
                    target_track=args.track,
                    plan_type=plan_type,
                    article_url=article_url,
                    pdf_url=pdf_url,
                    batch=args.batch,
                    school_code=args.school_code,
                )
            )
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
    parser = argparse.ArgumentParser(description="Import SCNU official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True)
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
    by_plan: dict[str, int] = {}
    for row in rows:
        by_year[row["year"]] = by_year.get(row["year"], 0) + 1
        by_plan[row["plan_type"]] = by_plan.get(row["plan_type"], 0) + 1
    print("# 华南师范大学专业录取分数导入\n")
    print("- 来源：华南师范大学本科招生网广东省录取情况PDF")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(y) for y in args.years)}")
    print(f"- 获取专业记录：{len(rows)}；分年：{by_year}；类型：{by_plan}")
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
