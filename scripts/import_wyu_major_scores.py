#!/usr/bin/env python3
"""Import Wuyi University official Guangdong major-level admission scores."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen


SOURCE_NAME = "五邑大学本科招生网"
SCHOOL_NAME = "五邑大学"
PAGES = {
    (2025, "物理类"): "https://www.wyu.edu.cn/zsb/info/1025/5750.htm",
    (2025, "历史类"): "https://www.wyu.edu.cn/zsb/info/1025/5740.htm",
    (2024, "物理类"): "https://www.wyu.edu.cn/zsb/info/1025/5140.htm",
    (2024, "历史类"): "https://www.wyu.edu.cn/zsb/info/1025/5130.htm",
    (2023, "物理类"): "https://www.wyu.edu.cn/zsb/info/1042/4566.htm",
    (2023, "历史类"): "https://www.wyu.edu.cn/zsb/info/1042/4564.htm",
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

MANUAL_IMAGE_ROWS = {
    (2023, "物理类", "24C7C13B7639BBC8AF3AF845121_9F32A235_D4A7.gif"): [
        ("202", "116", "食品科学与工程", "14", "522", "505", "510", "143370", "江门市内"),
        ("202", "122", "环境工程", "15", "536", "499", "508", "143370", "江门市内"),
        ("204", "114", "制药工程", "22", "523", "501", "509", "159891", "江门市内"),
        ("204", "118", "化学工程与工艺", "24", "505", "488", "496", "159891", "江门市内"),
        ("204", "124", "纺织工程", "77", "501", "488", "492", "159891", "江门市内"),
        ("204", "128", "交通工程", "93", "513", "489", "497", "159891", "江门市内"),
        ("206", "090", "材料科学与工程", "12", "509", "499", "504", "145229", "江门市内"),
        ("206", "104", "机械工程", "60", "535", "499", "505", "145229", "江门市内"),
        ("206", "108", "建筑学", "8", "528", "499", "509", "145229", "江门市内"),
        ("206", "126", "工业设计", "27", "543", "498", "503", "145229", "江门市内"),
        ("208", "086", "电气工程及其自动化", "20", "548", "530", "535", "128852", "江门市内"),
        ("208", "088", "自动化", "18", "541", "517", "525", "128852", "江门市内"),
        ("208", "092", "电子信息工程", "166", "562", "509", "520", "128852", "江门市内"),
        ("208", "094", "通信工程", "127", "540", "509", "520", "128852", "江门市内"),
        ("208", "096", "计算机科学与技术", "20", "588", "540", "548", "128852", "江门市内"),
        ("208", "098", "软件工程", "20", "552", "529", "533", "128852", "江门市内"),
        ("208", "102", "网络工程", "17", "535", "513", "521", "128852", "江门市内"),
        ("210", "048", "国际经济与贸易", "11", "523", "490", "504", "157965", "江门市内"),
        ("210", "050", "工商管理", "13", "525", "489", "502", "157965", "江门市内"),
        ("210", "052", "市场营销", "6", "513", "489", "497", "157965", "江门市内"),
        ("210", "054", "旅游管理", "6", "511", "495", "503", "157965", "江门市内"),
        ("210", "056", "法学", "13", "543", "522", "530", "157965", "江门市内"),
        ("210", "058", "社会工作", "9", "517", "491", "501", "157965", "江门市内"),
        ("210", "060", "汉语言文学", "12", "555", "507", "528", "157965", "江门市内"),
        ("210", "062", "汉语言文学（师范）", "9", "554", "528", "540", "157965", "江门市内"),
        ("210", "064", "英语（师范）", "5", "524", "500", "509", "157965", "江门市内"),
        ("210", "066", "英语", "4", "515", "494", "502", "157965", "江门市内"),
        ("210", "068", "商务英语", "9", "512", "502", "506", "157965", "江门市内"),
        ("210", "070", "日语", "4", "507", "493", "504", "157965", "江门市内"),
        ("210", "072", "金融学", "16", "527", "489", "503", "157965", "江门市内"),
        ("210", "074", "会计学", "11", "539", "514", "524", "157965", "江门市内"),
        ("210", "076", "信息管理与信息系统", "14", "531", "501", "506", "157965", "江门市内"),
        ("210", "078", "电子商务", "19", "522", "489", "499", "157965", "江门市内"),
        ("210", "080", "数学与应用数学（师范）", "18", "542", "490", "514", "157965", "江门市内"),
        ("210", "082", "精算学", "21", "513", "489", "500", "157965", "江门市内"),
        ("210", "084", "数据科学与大数据技术", "15", "528", "508", "517", "157965", "江门市内"),
        ("210", "106", "土木工程", "41", "526", "490", "499", "157965", "江门市内"),
        ("210", "112", "工程管理", "16", "520", "489", "504", "157965", "江门市内"),
    ],
}


class ImageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        src = dict(attrs).get("src")
        if src and "__local" in src:
            self.images.append(src)


def norm(value: object) -> str:
    return "" if value is None else str(value).strip()


def int_text(value: object) -> str:
    return re.sub(r"\D", "", norm(value).replace(",", ""))


def score_text(value: object) -> str:
    match = re.search(r"\d+(?:\.\d+)?", norm(value))
    if not match:
        return ""
    number = float(match.group(0))
    return str(int(number)) if number.is_integer() else str(number)


def fetch_text(url: str) -> str:
    return urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "ignore")


def page_images(url: str) -> list[str]:
    parser = ImageParser()
    parser.feed(fetch_text(url))
    return [urljoin(url, src) for src in parser.images]


def download(url: str, dest: Path, referer: str) -> None:
    data = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": referer}), timeout=60).read()
    dest.write_bytes(data)


def run_ocr(script: Path, images: list[Path]) -> list[dict[str, object]]:
    cmd = ["swift", str(script), *[str(path) for path in images]]
    proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    rows: list[dict[str, object]] = []
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 6:
            continue
        path, x, y, w, h, text = parts
        rows.append(
            {
                "path": path,
                "x": float(x),
                "y": float(y),
                "w": float(w),
                "h": float(h),
                "cx": float(x) + float(w) / 2,
                "cy": float(y) + float(h) / 2,
                "text": text.strip(),
            }
        )
    return rows


def cluster_by_row(items: list[dict[str, object]], tolerance: float = 0.0065) -> list[list[dict[str, object]]]:
    clusters: list[list[dict[str, object]]] = []
    for item in sorted(items, key=lambda row: -float(row["cy"])):
        if not clusters:
            clusters.append([item])
            continue
        last = clusters[-1]
        avg_y = sum(float(row["cy"]) for row in last) / len(last)
        if abs(float(item["cy"]) - avg_y) <= tolerance:
            last.append(item)
        else:
            clusters.append([item])
    return [sorted(cluster, key=lambda row: float(row["cx"])) for cluster in clusters]


def column_profile(items: list[dict[str, object]], year: int) -> dict[str, float]:
    has_wide_group_col = any(str(item["text"]) == "专业代号" and float(item["cx"]) > 0.20 for item in items)
    if year == 2024 and has_wide_group_col:
        return {"group_max": 0.22, "code_min": 0.20, "name_min": 0.30, "num_min": 0.50, "rank_min": 0.86}
    if year == 2023:
        return {"group_max": 0.10, "code_min": 0.08, "name_min": 0.18, "num_min": 0.48, "rank_min": 0.86}
    return {"group_max": 0.08, "code_min": 0.08, "name_min": 0.16, "num_min": 0.52, "rank_min": 0.86}


def page_plan_type(items: list[dict[str, object]], year: int) -> str:
    title = " ".join(str(row["text"]) for row in items if float(row["cy"]) > 0.95)
    if "江门市外" in title:
        return "江门市外"
    if "江门市内" in title:
        return "江门市内"
    return ""


def plan_type_from_note(note: str, major_name: str, fallback: str) -> str:
    text = f"{note} {major_name} {fallback}"
    if "中外" in text or "联培" in text or "联合培养" in text:
        return "中外联合培养"
    if "外市" in text or "市外" in text:
        return "江门市外"
    if "江门" in text or "市内" in text:
        return "江门市内"
    if "全省" in text:
        return "面向全省"
    return fallback or "普通类"


def extract_groups(clusters: list[list[dict[str, object]]], profile: dict[str, float], fallback: str) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    pending_note = ""
    for cluster in clusters:
        left = [item for item in cluster if float(item["cx"]) < profile["group_max"]]
        code = ""
        notes: list[str] = []
        cy_values: list[float] = []
        for item in left:
            text = str(item["text"])
            if re.fullmatch(r"\d{3}", int_text(text)):
                code = int_text(text)
                cy_values.append(float(item["cy"]))
            elif any(word in text for word in ["面向", "江门", "全省", "联培", "市内", "市外"]):
                notes.append(text)
                cy_values.append(float(item["cy"]))
        if code:
            note = " ".join(notes) or pending_note or fallback
            groups.append({"group": code, "cy": sum(cy_values) / len(cy_values), "note": note})
            pending_note = ""
        elif notes:
            pending_note = " ".join(notes)
            if groups and abs(float(left[0]["cy"]) - float(groups[-1]["cy"])) < 0.025:
                groups[-1]["note"] = pending_note
    return sorted(groups, key=lambda row: -float(row["cy"]))


def group_for_y(groups: list[dict[str, object]], cy: float, fallback: str) -> tuple[str, str]:
    if not groups:
        return "", fallback
    if len(groups) == 1:
        return str(groups[0]["group"]), str(groups[0]["note"] or fallback)
    for index, group in enumerate(groups):
        upper = 1.1 if index == 0 else (float(groups[index - 1]["cy"]) + float(group["cy"])) / 2
        lower = -0.1 if index == len(groups) - 1 else (float(group["cy"]) + float(groups[index + 1]["cy"])) / 2
        if upper >= cy >= lower:
            return str(group["group"]), str(group["note"] or fallback)
    nearest = min(groups, key=lambda group: abs(float(group["cy"]) - cy))
    return str(nearest["group"]), str(nearest["note"] or fallback)


def group_rank_for_y(rank_items: list[dict[str, object]], cy: float) -> str:
    if not rank_items:
        return ""
    nearest = min(rank_items, key=lambda row: abs(float(row["cy"]) - cy))
    return int_text(nearest["text"])


def parse_image_items(
    args: argparse.Namespace,
    *,
    year: int,
    track: str,
    source_url: str,
    image_url: str,
    items: list[dict[str, object]],
) -> list[dict[str, str]]:
    for (manual_year, manual_track, marker), manual_rows in MANUAL_IMAGE_ROWS.items():
        if year == manual_year and track == manual_track and marker in image_url:
            return [
                {
                    "year": str(year),
                    "province": args.province,
                    "track": track,
                    "batch": args.batch,
                    "school_name": SCHOOL_NAME,
                    "school_code": args.school_code,
                    "major_group": group,
                    "major_name": major_name,
                    "plan_type": plan_type_from_note(group_note, major_name, group_note),
                    "min_score": min_score,
                    "min_rank": "",
                    "admit_count": admit_count,
                    "source_url": source_url,
                    "source_name": SOURCE_NAME,
                    "notes": "；".join(
                        [
                            "学校官网GIF图片表手工校准导入",
                            f"专业代号={major_code}",
                            f"最高分={max_score}",
                            f"平均分={avg_score}",
                            f"专业组投档最低排位={group_rank}",
                            f"专业组说明={group_note}",
                            f"图片源={image_url}",
                        ]
                    ),
                }
                for group, major_code, major_name, admit_count, max_score, min_score, avg_score, group_rank, group_note in manual_rows
            ]
    profile = column_profile(items, year)
    fallback_plan = page_plan_type(items, year)
    clusters = cluster_by_row(items)
    groups = extract_groups(clusters, profile, fallback_plan)
    rank_items = [
        item
        for item in items
        if float(item["cx"]) >= profile["rank_min"] and re.fullmatch(r"\d{4,7}", int_text(item["text"]))
    ]
    rows: list[dict[str, str]] = []
    for cluster in clusters:
        cy = sum(float(item["cy"]) for item in cluster) / len(cluster)
        texts = [str(item["text"]) for item in cluster]
        if any(header in " ".join(texts) for header in ["专业名称", "五邑大学", "专业组投档"]):
            continue
        candidates = [
            item
            for item in cluster
            if profile["code_min"] <= float(item["cx"]) < profile["name_min"] and re.fullmatch(r"\d{3}", int_text(item["text"]))
        ]
        if not candidates:
            candidates = [
                item
                for item in cluster
                if float(item["cx"]) < profile["name_min"] and re.fullmatch(r"\d{3}", int_text(item["text"]))
            ]
        name_items = [
            item
            for item in cluster
            if profile["name_min"] <= float(item["cx"]) < profile["num_min"] and re.search(r"[\u4e00-\u9fffA-Za-z]", str(item["text"]))
        ]
        numeric = [
            item
            for item in cluster
            if profile["num_min"] <= float(item["cx"]) < profile["rank_min"] and re.fullmatch(r"\d+(?:\.\d+)?", str(item["text"]))
        ]
        if not candidates or not name_items or len(numeric) < 4:
            continue
        major_code = int_text(max(candidates, key=lambda item: float(item["cx"]))["text"])
        major_name = "".join(str(item["text"]) for item in sorted(name_items, key=lambda item: float(item["cx"]))).replace(" ", "")
        numeric = sorted(numeric, key=lambda item: float(item["cx"]))
        admit_count = int_text(numeric[0]["text"])
        max_score = score_text(numeric[1]["text"])
        min_score = score_text(numeric[2]["text"])
        avg_score = score_text(numeric[3]["text"])
        if not min_score or not major_name:
            continue
        major_group, group_note = group_for_y(groups, cy, fallback_plan)
        group_rank = group_rank_for_y(rank_items, cy)
        plan_type = plan_type_from_note(group_note, major_name, fallback_plan)
        rows.append(
            {
                "year": str(year),
                "province": args.province,
                "track": track,
                "batch": args.batch,
                "school_name": SCHOOL_NAME,
                "school_code": args.school_code,
                "major_group": major_group,
                "major_name": major_name,
                "plan_type": plan_type,
                "min_score": min_score,
                "min_rank": "",
                "admit_count": admit_count,
                "source_url": source_url,
                "source_name": SOURCE_NAME,
                "notes": "；".join(
                    part
                    for part in [
                        "学校官网GIF图片表经macOS Vision OCR导入",
                        f"专业代号={major_code}",
                        f"最高分={max_score}" if max_score else "",
                        f"平均分={avg_score}" if avg_score else "",
                        f"专业组投档最低排位={group_rank}" if group_rank else "",
                        f"专业组说明={group_note}" if group_note else "",
                        f"图片源={image_url}",
                    ]
                    if part
                ),
            }
        )
    return rows


def normalized_rows(args: argparse.Namespace) -> list[dict[str, str]]:
    script = Path(__file__).resolve().parent / "vision_ocr_image_zh.swift"
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="wyu_major_") as tmp_raw:
        tmp = Path(tmp_raw)
        for year in args.years:
            source_url = PAGES[(year, args.track)]
            image_urls = page_images(source_url)
            image_paths: list[Path] = []
            for index, image_url in enumerate(image_urls):
                ext = image_url.rsplit(".", 1)[-1].split("?", 1)[0] or "gif"
                image_path = tmp / f"{year}_{args.track}_{index}.{ext}"
                download(image_url, image_path, source_url)
                image_paths.append(image_path)
            ocr_items = run_ocr(script, image_paths)
            for image_path, image_url in zip(image_paths, image_urls):
                image_items = [item for item in ocr_items if Path(str(item["path"])).name == image_path.name]
                rows.extend(
                    parse_image_items(
                        args,
                        year=year,
                        track=args.track,
                        source_url=source_url,
                        image_url=image_url,
                        items=image_items,
                    )
                )
    return dedupe_rows(rows)


def dedupe_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = (row["year"], row["track"], row["major_group"], row["major_name"], row["plan_type"], row["min_score"])
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
                and norm(row.get("batch")) == args.batch
            )
        ]
    write_rows(path, existing + rows)
    return before, len(existing + rows)


def parse_years(raw: str) -> list[int]:
    years = [int(chunk.strip()) for chunk in raw.replace("，", ",").split(",") if chunk.strip()]
    unsupported = sorted(set(years) - {2023, 2024, 2025})
    if unsupported:
        raise argparse.ArgumentTypeError(f"WYU importer maps 2023/2024/2025 only, got {unsupported}")
    return years


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import Wuyi University official Guangdong major-level admission scores.")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--province", default="广东")
    parser.add_argument("--track", required=True, choices=["物理类", "历史类"])
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
    print("# 五邑大学专业录取分数导入\n")
    print(f"- 来源：{PAGES[(2025, args.track)]}")
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
