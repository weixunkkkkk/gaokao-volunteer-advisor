#!/usr/bin/env python3
"""Backfill majors.csv profiles from imported admission major names."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAJOR_COLUMNS = [
    "interest_keywords",
    "major_name",
    "degree_category",
    "employment_outlook",
    "typical_roles",
    "fit_notes",
    "risk_notes",
]

SKIP_TOKENS = [
    "专业组",
    "历史组",
    "物理组",
    "音教组",
    "舞蹈类组",
    "招生办",
    "公安",
    "学分互认",
]

DEGREE_RULES = [
    ("医学", ["临床", "口腔", "医学", "麻醉", "儿科", "护理", "康复", "影像", "检验", "卫生", "中医", "中药", "药学", "药物", "助产", "基础医学", "针灸"]),
    ("工学", ["工程", "技术", "计算机", "软件", "网络", "数据", "智能", "电子", "通信", "电气", "自动化", "机械", "车辆", "材料", "土木", "建筑", "环境", "食品", "交通", "能源", "安全", "测绘", "包装", "印刷", "化工", "船舶", "光电", "集成电路", "物联网", "区块链", "密码", "机器", "无人", "制冷", "制药工程"]),
    ("经济学", ["经济", "金融", "财政", "税收", "贸易", "保险", "投资", "信用", "互联网金融", "数字经济"]),
    ("管理学", ["管理", "会计", "财务", "审计", "工商", "市场营销", "人力资源", "行政管理", "公共事业", "物流", "供应链", "工程造价", "旅游", "酒店", "电子商务", "信息管理", "土地资源", "健康服务", "文化产业", "会展", "养老服务", "创业"]),
    ("法学", ["法学", "知识产权", "社会工作", "政治", "国际事务", "公安", "侦查", "治安", "禁毒", "犯罪", "警务", "警犬", "纪检", "司法"]),
    ("教育学", ["教育", "学前", "小学", "体育教育", "特殊教育", "运动训练", "社会体育", "休闲体育"]),
    ("文学", ["汉语言", "英语", "日语", "德语", "法语", "俄语", "语言", "新闻", "传播", "广告", "编辑", "翻译", "商务英语", "网络与新媒体"]),
    ("理学", ["数学", "物理", "化学", "生物科学", "生态", "地理", "统计", "心理", "海洋科学", "大气", "天文", "地质", "应用气象"]),
    ("农学", ["农", "动物", "水产", "园艺", "植物", "林学", "草业", "智慧牧业"]),
    ("艺术学", ["艺术", "设计", "音乐", "舞蹈", "美术", "书法", "播音", "戏剧", "影视", "产品设计", "工艺美术"]),
    ("历史学", ["历史", "文物", "考古", "文化遗产"]),
    ("哲学", ["哲学", "逻辑学", "宗教学"]),
]

OUTLOOK_A = ["计算机", "软件", "人工智能", "数据", "网络安全", "电气", "自动化", "集成电路", "微电子", "通信", "电子信息", "新能源", "机器人工程", "临床", "口腔", "护理", "麻醉", "会计", "审计"]
OUTLOOK_C = ["土木", "建筑", "旅游", "酒店", "市场营销", "公共事业", "行政管理", "社会工作", "艺术", "音乐", "舞蹈", "美术", "广播电视编导", "哲学", "历史"]

ROLE_RULES = [
    (["计算机", "软件", "人工智能", "数据", "网络", "物联网", "区块链", "密码"], "软件开发、数据分析、算法/AI应用、信息安全"),
    (["电子", "通信", "集成电路", "微电子", "光电"], "电子工程、通信网络、芯片/半导体、硬件测试"),
    (["电气", "自动化", "能源", "储能", "智能电网"], "电力系统、自动化控制、新能源设备、智能制造"),
    (["机械", "车辆", "机器", "智能制造", "无人"], "装备制造、汽车工程、机器人应用、生产工艺"),
    (["临床", "口腔", "麻醉", "儿科", "中医", "医学"], "医生、医院科室、医学科研、基层医疗"),
    (["护理", "康复", "影像", "检验", "卫生"], "医院医技、护理、康复治疗、公共卫生"),
    (["药", "制药"], "药师、药品研发、药企注册/质量、医药销售"),
    (["金融", "经济", "投资", "保险", "税收"], "银行、证券、保险、财税、企业经营分析"),
    (["会计", "财务", "审计"], "会计、审计、税务、财务分析"),
    (["管理", "工商", "市场营销", "物流", "供应链", "电子商务"], "运营管理、市场营销、供应链、电子商务"),
    (["法学", "知识产权", "侦查", "治安", "警务"], "法律服务、公务员、公检法、合规风控"),
    (["教育", "学前", "小学", "师范"], "教师、教培、教育管理、课程研发"),
    (["新闻", "传播", "广告", "新媒体", "汉语言", "英语", "翻译"], "内容运营、媒体传播、外贸/翻译、教育"),
    (["农", "动物", "水产", "园艺", "林"], "农业技术、畜牧兽医、水产养殖、农产品研发"),
    (["艺术", "设计", "音乐", "舞蹈", "美术"], "设计、文创、艺术教育、展演/制作"),
]

INTEREST_RULES = [
    ("计算机", ["AI", "人工智能", "计算机", "编程", "软件"]),
    ("智能", ["AI", "人工智能", "智能制造"]),
    ("数据", ["数据", "算法", "统计"]),
    ("金融", ["财经", "金融", "投资"]),
    ("会计", ["财经", "会计", "审计"]),
    ("医学", ["医学", "医生", "医院"]),
    ("护理", ["医学", "护理", "医院"]),
    ("电气", ["新能源", "电力", "电网"]),
    ("能源", ["新能源", "储能", "双碳"]),
    ("新闻", ["传媒", "内容", "传播"]),
    ("教育", ["教育", "师范", "教师"]),
    ("法学", ["法律", "公务员", "公检法"]),
    ("动物", ["农学", "宠物", "兽医"]),
]


def clean_major_name(raw: str) -> str:
    text = (raw or "").strip()
    text = text.replace("〈", "（").replace("〉", "）").replace("《", "（").replace("》", "）")
    text = re.sub(r"^[/\s]+", "", text)
    text = re.sub(r"^[A-Z]?\d{2,4}[.、\-\s]*", "", text)
    text = re.sub(r"[（(【\\[].*$", "", text)
    text = re.sub(r"（.*$", "", text)
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
    if any(token in name for token in SKIP_TOKENS):
        return False
    if re.search(r"[A-Za-z]", name):
        return False
    if not re.search(r"[\u4e00-\u9fff]", name):
        return False
    return True


def infer_degree(name: str) -> str:
    for degree, tokens in DEGREE_RULES:
        if any(token in name for token in tokens):
            return degree
    return "交叉学科"


def infer_outlook(name: str, degree: str) -> str:
    if any(token in name for token in OUTLOOK_A):
        return "A"
    if any(token in name for token in OUTLOOK_C):
        return "C"
    if degree in {"工学", "医学", "经济学"}:
        return "B"
    return "B"


def infer_difficulty(name: str, degree: str) -> int:
    if any(token in name for token in ["临床", "口腔", "人工智能", "集成电路", "微电子", "密码", "建筑学"]):
        return 5
    if degree in {"医学", "工学", "理学"}:
        return 4
    if degree in {"经济学", "法学", "教育学", "农学"}:
        return 3
    return 3


def infer_roles(name: str, degree: str) -> str:
    for tokens, roles in ROLE_RULES:
        if any(token in name for token in tokens):
            return roles
    return {
        "工学": "工程技术、产品研发、生产运维、项目实施",
        "理学": "科研助理、数据分析、教师、技术支持",
        "医学": "医院、基层医疗、医药健康、公共卫生",
        "管理学": "企业运营、职能管理、数据分析、公共服务",
        "经济学": "金融机构、财税、咨询、企业经营分析",
        "文学": "内容传播、教育、外贸、公共服务",
        "法学": "法律服务、合规、公务员、公共治理",
        "教育学": "教师、教育管理、课程研发",
        "农学": "农业技术、乡村振兴、食品/生物相关产业",
        "艺术学": "设计、文创、艺术教育、传媒制作",
    }.get(degree, "结合具体课程方向选择行业岗位")


def trend_text(name: str, degree: str, outlook: str) -> str:
    if any(token in name for token in ["人工智能", "数据", "软件", "计算机", "网络安全"]):
        return "数字化和AI应用需求强，但技术迭代快，需要持续学习和项目作品"
    if any(token in name for token in ["电气", "能源", "储能", "新能源"]):
        return "电网、新能源和制造业升级带来稳定需求"
    if any(token in name for token in ["临床", "口腔", "护理", "康复"]):
        return "医疗健康刚需强，培养周期和执业资格要求高"
    if any(token in name for token in ["会计", "审计", "财务"]):
        return "岗位稳定，但基础核算受自动化影响，证书和实习很关键"
    if outlook == "C":
        return "行业周期或供需波动较明显，需要靠城市、学校平台、实习和作品提高确定性"
    return "就业面取决于学校平台、城市产业和个人实习/证书积累"


def build_keywords(name: str, degree: str, roles: str) -> str:
    keywords = [name, degree]
    for token, additions in INTEREST_RULES:
        if token in name:
            keywords.extend(additions)
    for part in re.split(r"[、/，,；;]+", roles):
        part = part.strip()
        if 2 <= len(part) <= 10:
            keywords.append(part)
    seen: set[str] = set()
    output: list[str] = []
    for item in keywords:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            output.append(item)
    return "|".join(output[:20])


def build_profile(name: str) -> dict[str, str]:
    degree = infer_degree(name)
    outlook = infer_outlook(name, degree)
    difficulty = infer_difficulty(name, degree)
    roles = infer_roles(name, degree)
    trend = trend_text(name, degree, outlook)
    risk = f"就业评级{outlook}；学习难度{difficulty}/5；{trend}"
    return {
        "interest_keywords": build_keywords(name, degree, roles),
        "major_name": name,
        "degree_category": degree,
        "employment_outlook": f"评级{outlook}；学习难度{difficulty}/5；{trend}",
        "typical_roles": roles,
        "fit_notes": f"通用画像：按教育部本科专业目录门类和相近专业归类；需结合学校培养方案复核核心课程",
        "risk_notes": risk,
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAJOR_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def collect_major_names(data_dirs: list[Path]) -> set[str]:
    names: set[str] = set()
    for data_dir in data_dirs:
        for row in read_csv(data_dir / "admission_records.csv"):
            name = clean_major_name(row.get("major_name", ""))
            if valid_major_name(name):
                names.add(name)
    return names


def merge_profiles(existing: list[dict[str, str]], generated_names: set[str]) -> list[dict[str, str]]:
    by_major: dict[str, dict[str, str]] = {}
    for row in existing:
        name = clean_major_name(row.get("major_name", ""))
        if valid_major_name(name):
            fixed = {col: row.get(col, "") for col in MAJOR_COLUMNS}
            fixed["major_name"] = name
            by_major[name] = fixed
    for name in generated_names:
        if name not in by_major:
            by_major[name] = build_profile(name)
    return [by_major[name] for name in sorted(by_major)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill major profiles from admission_records.csv major names.")
    parser.add_argument("--data-dir", action="append", required=True)
    parser.add_argument("--output-dir", action="append", help="Data directory whose majors.csv should be updated. Defaults to every --data-dir.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data_dirs = [Path(item).expanduser().resolve() for item in args.data_dir]
    output_dirs = [Path(item).expanduser().resolve() for item in (args.output_dir or args.data_dir)]
    names = collect_major_names(data_dirs)
    for output_dir in output_dirs:
        path = output_dir / "majors.csv"
        rows = merge_profiles(read_csv(path), names)
        write_csv(path, rows)
        print(f"{path}: wrote {len(rows)} rows; admission-derived profiles={len(names)}")


if __name__ == "__main__":
    main()
