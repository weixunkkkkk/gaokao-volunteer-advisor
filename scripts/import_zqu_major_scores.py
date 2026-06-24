#!/usr/bin/env python3
"""Import Zhaoqing University official Guangdong major scores from image tables."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from pathlib import Path

from PIL import Image


SOURCE_NAME = "肇庆学院本科招生网"
SCHOOL_NAME = "肇庆学院"
SCHOOL_CODE = "10580"
IMAGE_SOURCES = {
    2024: {
        "image": "assets/raw-cache/zqu/2024_guangdong_history_physics.jpg",
        "url": "https://zqu1-101.m.eduwebportal.net/webIndex.jsp?isRedirect=true#/indexPages/newsDetail/newsDetail?id=193",
        "title": "广东省本科历史、物理类录取分数线",
        "notes": "学校官方历年分数小程序图片表；2024年广东省本科历史、物理类录取分数线",
        "columns": {
            "group": (0.00, 0.14),
            "major": (0.14, 0.40),
            "count": (0.40, 0.49),
            "high": (0.49, 0.57),
            "low": (0.57, 0.66),
            "high_rank": (0.66, 0.82),
            "low_rank": (0.82, 1.00),
        },
        "spans": [
            ("201.历史组", 80, 336),
            ("202.历史组", 336, 592),
            ("203.历史组", 592, 720),
            ("204.历史组", 720, 1104),
            ("205.历史组", 1104, 1296),
            ("206.历史组", 1296, 1360),
            ("207.历史组", 1360, 1424),
            ("208.物理组", 1424, 1744),
            ("209.物理组", 1744, 2000),
            ("210.物理组", 2000, 2128),
            ("211.物理组", 2128, 2512),
            ("212.物理组", 2512, 2960),
            ("213.物理组", 2960, 3408),
            ("214.物理组", 3408, 3792),
            ("215.物理组", 3792, 4176),
            ("216.物理组", 4176, 4240),
            ("217.物理组", 4240, 4304),
            ("218.物理组", 4304, 4368),
            ("219.物理组", 4368, 4547),
        ],
        "manual_rows": [
            {
                "track": "物理类",
                "major_group": "211.物理组",
                "major_name": "商务英语",
                "admit_count": "40",
                "high_score": "515",
                "min_score": "509",
                "high_rank": "121785",
                "min_rank": "132808",
            },
            {
                "track": "物理类",
                "major_group": "214.物理组",
                "major_name": "食品营养与健康（创新班）",
                "admit_count": "30",
                "high_score": "509",
                "min_score": "497",
                "high_rank": "132771",
                "min_rank": "152734",
            },
            {
                "track": "物理类",
                "major_group": "219.物理组",
                "major_name": "风景园林",
                "admit_count": "60",
                "high_score": "511",
                "min_score": "499",
                "high_rank": "134455",
                "min_rank": "149860",
            },
        ],
    },
    2023: {
        "image": "assets/raw-cache/zqu/2023_guangdong_undergrad.jpg",
        "url": "https://zqu1-101.m.eduwebportal.net/webIndex.jsp?isRedirect=true#/indexPages/newsDetail/newsDetail?id=182",
        "title": "广东省本科批录取分数线",
        "notes": "学校官方历年分数小程序图片表；2023年广东省本科批录取分数线",
        "columns": {
            "group": (0.06, 0.34),
            "major": (0.34, 0.53),
            "count": (0.53, 0.63),
            "high": (0.63, 0.71),
            "low": (0.71, 0.80),
            "avg": (0.80, 0.89),
            "low_rank": (0.89, 1.00),
        },
        "spans": [
            ("201.历史组", 42, 492),
            ("202.历史组*不招色盲色弱", 492, 566),
            ("204.历史组*不招色盲色弱", 566, 599),
            ("206.历史组", 599, 642),
            ("207.物理组", 642, 1349),
            ("208.物理组*化学", 1349, 1499),
            ("209.物理组*化学*不招色盲色弱", 1499, 1691),
            ("210.物理组*化学/生物*不招色盲色弱", 1691, 1766),
            ("211.物理组*不招色盲色弱", 1766, 1841),
            ("212.物理组/地理*不招色盲", 1841, 1874),
            ("213.物理组*生物/地理*不招色盲", 1874, 1916),
            ("214.物理组*不招单色识别不全者", 1916, 1949),
            ("215.物理组", 1949, 1991),
        ],
    },
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


def clean_text(value: object) -> str:
    text = norm(value).replace("\u3000", "")
    text = text.replace(" ", "").replace("|", "").replace("．", ".")
    text = text.replace("(", "（").replace(")", "）")
    text = re.sub(r"\s+", "", text)
    text = text.replace("组本", "组").replace("弱弱", "弱")
    if text.count("（") > text.count("）"):
        text += "）"
    return text


def int_text(value: object) -> str:
    return re.sub(r"\D", "", norm(value).replace(",", ""))


def score_text(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 100 <= number <= 750 else ""


def rank_text(value: object) -> str:
    text = int_text(value)
    if not text:
        return ""
    number = int(text)
    return text if 1 <= number <= 500000 else ""


def avg_text(value: object) -> str:
    match = re.search(r"\d+(?:\.\d+)?", norm(value))
    return match.group(0) if match else ""


def run_ocr(script: Path, images: list[Path]) -> list[dict[str, object]]:
    cmd = ["swift", str(script), *[str(path) for path in images]]
    proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    rows: list[dict[str, object]] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 6:
            continue
        path, x, y, w, h, text = parts
        x_f, y_f, w_f, h_f = float(x), float(y), float(w), float(h)
        rows.append(
            {
                "path": path,
                "x": x_f,
                "y": y_f,
                "w": w_f,
                "h": h_f,
                "cx": x_f + w_f / 2,
                "cy": y_f + h_f / 2,
                "text": text.strip(),
            }
        )
    return rows


def in_col(item: dict[str, object], bounds: tuple[float, float]) -> bool:
    return bounds[0] <= float(item["cx"]) < bounds[1]


def group_labels(items: list[dict[str, object]], columns: dict[str, tuple[float, float]]) -> list[dict[str, object]]:
    labels: list[dict[str, object]] = []
    for item in items:
        text = clean_text(item["text"])
        if in_col(item, columns["group"]) and re.search(r"^\d{3}[.．]", text):
            labels.append({"text": text, "cy": float(item["cy"])})
    labels.sort(key=lambda row: -float(row["cy"]))
    return labels


def nearest_group(labels: list[dict[str, object]], cy: float) -> str:
    if not labels:
        return ""
    nearest = min(labels, key=lambda row: abs(float(row["cy"]) - cy))
    return clean_text(nearest["text"])


def track_from_group(group: str) -> str:
    if "历史" in group:
        return "历史类"
    if "物理" in group:
        return "物理类"
    return ""


def image_height(path: Path) -> int:
    with Image.open(path) as image:
        return int(image.height)


def group_from_spans(spans: list[tuple[str, int, int]], height: int, cy: float) -> str:
    y_from_top = (1.0 - cy) * height
    for group, top, bottom in spans:
        if top <= y_from_top < bottom:
            return clean_text(group)
    return ""


def column_text(items: list[dict[str, object]], columns: dict[str, tuple[float, float]], column: str, cy: float, tolerance: float = 0.0065) -> str:
    pieces = [
        item
        for item in items
        if in_col(item, columns[column]) and abs(float(item["cy"]) - cy) <= tolerance
    ]
    return clean_text("".join(str(item["text"]) for item in sorted(pieces, key=lambda row: float(row["cx"]))))


def plan_type(major_name: str, group: str) -> str:
    text = f"{major_name}{group}"
    if "中外" in text or "联合培养" in text:
        return "中外合作"
    if "协同" in text:
        return "协同培养"
    return "普通类"


def manual_rows(args: argparse.Namespace, year: int, meta: dict[str, object]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for raw in meta.get("manual_rows", []):  # type: ignore[union-attr]
        row = dict(raw)  # type: ignore[arg-type]
        if row.get("track") != args.track:
            continue
        major_name = str(row["major_name"])
        group = str(row["major_group"])
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": args.track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": group,
                "major_name": major_name,
                "plan_type": plan_type(major_name, group),
                "min_score": str(row["min_score"]),
                "min_rank": str(row["min_rank"]),
                "admit_count": str(row["admit_count"]),
                "source_url": str(meta["url"]),
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        str(meta["notes"]),
                        "按官网图片人工校准",
                        f"最高分={row.get('high_score')}" if row.get("high_score") else "",
                        f"专业最高排位={row.get('high_rank')}" if row.get("high_rank") else "",
                        f"图片源={meta['image']}",
                    ]
                    if part
                ),
            }
        )
    return rows


def parse_image(args: argparse.Namespace, year: int, meta: dict[str, object], items: list[dict[str, object]]) -> list[dict[str, str]]:
    image_path = str(Path(str(meta["image"])).resolve())
    page_items = [item for item in items if str(Path(str(item["path"])).resolve()) == image_path]
    columns = meta["columns"]  # type: ignore[assignment]
    labels = group_labels(page_items, columns)  # type: ignore[arg-type]
    spans = meta.get("spans", [])
    height = image_height(Path(str(meta["image"])).resolve())
    rows: list[dict[str, str]] = []
    major_items = [
        item
        for item in page_items
        if in_col(item, columns["major"])  # type: ignore[index]
        and re.search(r"[\u4e00-\u9fffA-Za-z]", str(item["text"]))
        and not any(header in str(item["text"]) for header in ["专业名称", "专业组"])
    ]
    for item in sorted(major_items, key=lambda row: -float(row["cy"])):
        cy = float(item["cy"])
        major_name = clean_text(item["text"])
        group = group_from_spans(spans, height, cy) if spans else nearest_group(labels, cy)  # type: ignore[arg-type]
        track = track_from_group(group)
        if track != args.track:
            continue
        min_score = score_text(column_text(page_items, columns, "low", cy))  # type: ignore[arg-type]
        min_rank = rank_text(column_text(page_items, columns, "low_rank", cy))  # type: ignore[arg-type]
        if not major_name or not min_score or not min_rank:
            continue
        high_score = score_text(column_text(page_items, columns, "high", cy))  # type: ignore[arg-type]
        high_rank = rank_text(column_text(page_items, columns, "high_rank", cy)) if "high_rank" in columns else ""
        avg_score = avg_text(column_text(page_items, columns, "avg", cy)) if "avg" in columns else ""
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": args.track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": group,
                "major_name": major_name,
                "plan_type": plan_type(major_name, group),
                "min_score": min_score,
                "min_rank": min_rank,
                "admit_count": int_text(column_text(page_items, columns, "count", cy)),  # type: ignore[arg-type]
                "source_url": str(meta["url"]),
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        str(meta["notes"]),
                        f"最高分={high_score}" if high_score else "",
                        f"平均分={avg_score}" if avg_score else "",
                        f"专业最高排位={high_rank}" if high_rank else "",
                        f"图片源={meta['image']}",
                    ]
                    if part
                ),
            }
        )
    rows.extend(manual_rows(args, year, meta))
    return dedupe_rows(rows)


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    script = Path(__file__).resolve().parent / "vision_ocr_image_zh.swift"
    image_paths = [Path(str(meta["image"])).resolve() for year, meta in IMAGE_SOURCES.items() if year in args.years]
    missing = [path for path in image_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing official cached images: {missing}")
    items = run_ocr(script, image_paths)
    rows: list[dict[str, str]] = []
    for year, meta in IMAGE_SOURCES.items():
        if year in args.years:
            rows.extend(parse_image(args, year, meta, items))
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["major_group"], row["major_name"], row["min_score"], row["min_rank"])
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
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - set(IMAGE_SOURCES))
    if unsupported:
        raise argparse.ArgumentTypeError(f"ZQU importer currently has official images for 2023/2024 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Zhaoqing University official Guangdong major scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
    parser.add_argument("--batch", default="本科批")
    parser.add_argument("--school-code", default=SCHOOL_CODE)
    parser.add_argument("--years", type=parse_years, default=[2023, 2024])
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
    print("# 肇庆学院专业录取分数导入\n")
    print(f"- 范围：{args.province} / {args.track} / {', '.join(str(year) for year in args.years)}")
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
