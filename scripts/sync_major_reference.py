#!/usr/bin/env python3
"""Sync the Markdown major reference table into normalized majors.csv files."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT / "references" / "major-reference.md"
MAJOR_COLUMNS = [
    "interest_keywords",
    "major_name",
    "degree_category",
    "employment_outlook",
    "typical_roles",
    "fit_notes",
    "risk_notes",
]

DEGREE_KEYWORDS = {
    "工学": ["工科", "工程", "技术"],
    "理学": ["理科", "科研", "数据"],
    "医学": ["医学", "医生", "医院"],
    "管理学": ["管理", "商业", "运营"],
    "经济学": ["财经", "金融", "经济"],
    "文学": ["文学", "语言", "传媒", "内容"],
    "法学": ["法律", "法学", "公检法"],
    "教育学": ["教育", "师范", "教师"],
    "农学": ["农学", "农业", "乡村振兴"],
}

NAME_KEYWORDS = [
    ("计算机", ["AI", "人工智能", "计算机", "编程", "软件"]),
    ("软件", ["计算机", "软件", "编程"]),
    ("人工智能", ["AI", "人工智能", "算法", "数据"]),
    ("数据", ["数据", "算法", "统计"]),
    ("电子", ["电子信息", "芯片", "硬件"]),
    ("通信", ["通信", "电子信息", "网络"]),
    ("微电子", ["芯片", "半导体", "集成电路"]),
    ("电气", ["新能源", "电力", "电网", "储能"]),
    ("新能源", ["新能源", "储能", "电力"]),
    ("车辆", ["汽车", "新能源车", "智能驾驶"]),
    ("机器", ["机器人", "智能制造", "自动化"]),
    ("自动化", ["自动化", "控制", "智能制造"]),
    ("机械", ["机械", "制造", "装备"]),
    ("材料", ["材料", "新材料", "半导体"]),
    ("土木", ["土木", "建筑", "基建"]),
    ("建筑", ["建筑", "设计", "城市"]),
    ("环境", ["环境", "环保", "双碳"]),
    ("食品", ["食品", "质检", "研发"]),
    ("医学", ["医学", "医生", "医院"]),
    ("临床", ["医学", "医生", "临床"]),
    ("口腔", ["医学", "口腔", "医生"]),
    ("护理", ["医学", "护理", "医院"]),
    ("药", ["医学", "药学", "药企"]),
    ("康复", ["医学", "康复", "医院"]),
    ("会计", ["财经", "会计", "审计", "财务"]),
    ("财务", ["财经", "财务", "会计"]),
    ("金融", ["财经", "金融", "投资", "银行"]),
    ("经济", ["财经", "经济", "商业"]),
    ("贸易", ["财经", "外贸", "跨境电商"]),
    ("法学", ["法律", "律师", "公检法"]),
    ("知识产权", ["法律", "专利", "知识产权"]),
    ("汉语言", ["中文", "写作", "师范", "公务员"]),
    ("英语", ["英语", "外贸", "翻译"]),
    ("新闻", ["传媒", "新闻", "内容"]),
    ("广告", ["传媒", "广告", "营销"]),
    ("新媒体", ["传媒", "新媒体", "内容"]),
    ("教育", ["教育", "师范", "教师"]),
    ("农", ["农业", "农学", "乡村振兴"]),
    ("园林", ["园林", "景观", "设计"]),
    ("动物", ["动物", "兽医", "宠物"]),
    ("海洋", ["海洋", "水产", "沿海"]),
]


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def normalize_difficulty(value: str) -> str:
    match = re.search(r"\d", value)
    return match.group(0) if match else value.strip()


def parse_reference(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = split_markdown_row(line)
        if not cells or cells[0] in {"专业名称", "专业", "难度"}:
            continue
        if len(cells) >= 7 and cells[1] in DEGREE_KEYWORDS:
            major_name, degree, outlook, difficulty, roles, course, trend = cells[:7]
        elif len(cells) >= 5 and cells[1] in DEGREE_KEYWORDS:
            major_name, degree, outlook, difficulty, roles = cells[:5]
            course = ""
            trend = roles
        else:
            continue
        keywords = build_keywords(major_name, degree, roles, trend)
        rows.append(
            {
                "interest_keywords": "|".join(keywords),
                "major_name": major_name,
                "degree_category": degree,
                "employment_outlook": f"评级{outlook}；学习难度{normalize_difficulty(difficulty)}/5；{trend}",
                "typical_roles": roles,
                "fit_notes": f"核心课程/能力：{course}" if course else "参考相近专业的课程和能力要求",
                "risk_notes": risk_note(outlook, difficulty, trend),
            }
        )
    return dedupe_by_major(rows)


def build_keywords(major_name: str, degree: str, roles: str, trend: str) -> list[str]:
    keywords: list[str] = [major_name, degree]
    keywords.extend(DEGREE_KEYWORDS.get(degree, []))
    text = f"{major_name}{roles}{trend}"
    for token, additions in NAME_KEYWORDS:
        if token in text:
            keywords.extend(additions)
    for part in re.split(r"[、/，,；;（）()]+", roles):
        part = part.strip()
        if 2 <= len(part) <= 8:
            keywords.append(part)
    seen = set()
    output: list[str] = []
    for keyword in keywords:
        keyword = keyword.strip()
        if keyword and keyword.lower() not in seen:
            seen.add(keyword.lower())
            output.append(keyword)
    return output[:18]


def risk_note(outlook: str, difficulty: str, trend: str) -> str:
    difficulty_text = normalize_difficulty(difficulty)
    notes = [f"就业评级{outlook}", f"学习难度{difficulty_text}/5"]
    if outlook in {"D", "E"} or "红牌" in trend or "供过于求" in trend:
        notes.append("谨慎选择，需用证书、实习或作品拉开差距")
    elif difficulty_text in {"4", "5"}:
        notes.append("学习压力较高，适合基础扎实且愿意长期投入的学生")
    else:
        notes.append("仍需结合学校层次、城市和实习资源判断")
    return "；".join(notes)


def dedupe_by_major(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    output: list[dict[str, str]] = []
    for row in rows:
        key = row["major_name"]
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


def merge_rows(existing: list[dict[str, str]], parsed: list[dict[str, str]]) -> list[dict[str, str]]:
    by_major = {row.get("major_name", ""): {col: row.get(col, "") for col in MAJOR_COLUMNS} for row in existing}
    for row in parsed:
        major = row["major_name"]
        if major in by_major:
            merged_keywords = merge_keywords(by_major[major].get("interest_keywords", ""), row["interest_keywords"])
            by_major[major]["interest_keywords"] = merged_keywords
            by_major[major]["employment_outlook"] = row["employment_outlook"]
            by_major[major]["risk_notes"] = row["risk_notes"]
        else:
            by_major[major] = row
    return [by_major[key] for key in sorted(by_major)]


def merge_keywords(left: str, right: str) -> str:
    output: list[str] = []
    seen = set()
    for part in f"{left}|{right}".split("|"):
        part = part.strip()
        if part and part.lower() not in seen:
            seen.add(part.lower())
            output.append(part)
    return "|".join(output[:24])


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAJOR_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync major-reference.md into majors.csv.")
    parser.add_argument("--reference", default=str(DEFAULT_REFERENCE))
    parser.add_argument("--data-dir", action="append", required=True)
    parser.add_argument("--replace", action="store_true", help="Replace instead of merging with existing majors.csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    parsed = parse_reference(Path(args.reference).expanduser().resolve())
    for raw_dir in args.data_dir:
        data_dir = Path(raw_dir).expanduser().resolve()
        path = data_dir / "majors.csv"
        rows = parsed if args.replace else merge_rows(read_existing(path), parsed)
        write_csv(path, rows)
        print(f"{path}: wrote {len(rows)} rows from {len(parsed)} reference majors")


if __name__ == "__main__":
    main()
