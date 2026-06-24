# 全国版高考志愿顾问 Skill — 完整方案文档

> 输出时间：2026-06-24
> 目标：将志愿顾问从当前试点数据扩展为"全国31省市自治区 × 本科院校 × 各专业录取分数"的完整覆盖
> 本文档是全国化路线图和采集清单，不代表当前数据已经全国可用。正式推荐仍以 `scripts/audit_data.py` 的当前数据覆盖为准。

---

## 一、全国高考数据体系总览

### 1.1 全国高校规模（教育部2025年6月名单）

| 类别 | 数量 |
|------|------|
| 全国高等学校总数 | 3167所 |
| 普通高等学校 | 2919所 |
| **本科学校** | **1365所** |
| 高职(专科)学校 | 1554所 |
| 成人高等学校 | 248所 |

> 本Skill目标覆盖范围：**1365所本科院校**（不含港澳台、不含成人高校、不含专科）

### 1.2 新高考改革进度（截至2026年）

| 批次 | 实行年份 | 省份 | 模式 |
|------|---------|------|------|
| 第一批 | 2017 | 上海、浙江 | 3+3 |
| 第二批 | 2020 | 北京、天津、山东、海南 | 3+3 |
| 第三批 | 2021 | 河北、辽宁、江苏、福建、湖北、湖南、广东、重庆 | 3+1+2 |
| 第四批 | 2024 | 黑龙江、甘肃、吉林、安徽、江西、贵州、广西 | 3+1+2 |
| 第五批 | 2025 | 四川、河南、云南、陕西、内蒙古、山西、宁夏、青海 | 3+1+2 |
| **未改革** | - | 新疆、西藏 | 传统文理 |

> **2025年起，全国29个省份已全面实行新高考**，仅新疆、西藏仍为传统文理模式。

### 1.3 数据维度

每个录取数据点包含5个核心维度：

```
院校(1365所) × 省份(31个) × 年份(2023-2025) × 科类/选科组合 × 专业/专业组
```

预估数据量：
- 省级投档表层面：31省 × 3年 × ~1500校/省 ≈ **14万条**
- 专业级层面（理想）：31省 × 3年 × ~1500校 × ~30专业/校 ≈ **420万条**
- 实际可获取专业级（通过掌上高考API）：预估 **50-100万条**

---

## 二、全国31省教育考试院官方数据源

### 2.1 新高考3+1+2省份（21省）

> 科类：物理类 / 历史类 + 再选科目

| # | 省份 | 官方教育考试院 | 官网URL | 一分一段表 | 投档表 |
|---|------|--------------|---------|-----------|--------|
| 1 | 广东 | 广东省教育考试院 | https://eea.gd.gov.cn/ | ✅ 已导入 | ✅ 已导入 |
| 2 | 河北 | 河北省教育考试院 | http://www.hebeea.edu.cn/ | 🔶 OCR待复核 | 🔶 待导入 |
| 3 | 辽宁 | 辽宁招生考试之窗 | https://www.lnzsks.com/ | 🔵 待采集 | 🔵 待采集 |
| 4 | 江苏 | 江苏省教育考试院 | https://www.jseea.cn/ | 🔶 已发现 | 🔶 待导入 |
| 5 | 福建 | 福建省教育考试院 | https://www.eeafj.cn/ | 🔵 待采集 | 🔵 待采集 |
| 6 | 湖北 | 湖北省教育考试院 | http://www.hbea.edu.cn/ | 🔵 待采集 | 🔵 待采集 |
| 7 | 湖南 | 湖南省教育考试院 | http://jyt.hunan.gov.cn/jyt/sjyt/hnsjyksy/ | 🔵 待采集 | 🔵 待采集 |
| 8 | 重庆 | 重庆教育考试院 | https://www.cqksy.cn/ | 🔵 待采集 | 🔵 待采集 |
| 9 | 黑龙江 | 黑龙江省招生考试院 | https://www.hljea.org.cn/ | 🔵 待采集 | 🔵 待采集 |
| 10 | 甘肃 | 甘肃省教育考试院 | https://www.ganseea.cn/ | 🔵 待采集 | 🔵 待采集 |
| 11 | 吉林 | 吉林省教育考试院 | https://www.jleea.edu.cn/ | 🔵 待采集 | 🔵 待采集 |
| 12 | 安徽 | 安徽省教育招生考试院 | https://www.ahzsks.cn/ | 🔵 待采集 | 🔵 待采集 |
| 13 | 江西 | 江西省教育考试院 | http://www.jxeea.cn/ | 🔵 待采集 | 🔵 待采集 |
| 14 | 贵州 | 贵州省招生考试院 | https://zsksy.guizhou.gov.cn/ | 🔵 待采集 | 🔵 待采集 |
| 15 | 广西 | 广西招生考试院 | https://www.gxeea.cn/ | 🔵 待采集 | 🔵 待采集 |
| 16 | 四川 | 四川省教育考试院 | https://www.sceea.cn/ | 🔵 待采集 | 🔵 待采集 |
| 17 | 河南 | 河南省教育考试院 | https://www.haeea.cn/ | 🔵 待采集 | 🔵 待采集 |
| 18 | 云南 | 云南省招生考试院 | https://www.ynzs.cn/ | 🔵 待采集 | 🔵 待采集 |
| 19 | 陕西 | 陕西省教育考试院 | https://www.sneea.cn/ | 🔵 待采集 | 🔵 待采集 |
| 20 | 内蒙古 | 内蒙古招生考试信息网 | https://www.nm.zsks.cn/ | 🔵 待采集 | 🔵 待采集 |
| 21 | 山西 | 山西招生考试网 | http://www.sxkszx.cn/ | 🔵 待采集 | 🔵 待采集 |

### 2.2 新高考3+3省份（6省）

> 科类：综合/不分文理

| # | 省份 | 官方教育考试院 | 官网URL | 一分一段表 | 投档表 |
|---|------|--------------|---------|-----------|--------|
| 22 | 上海 | 上海市教育考试院 | https://www.shmeea.edu.cn/ | ✅ 已导入 | ✅ 已导入 |
| 23 | 浙江 | 浙江省教育考试院 | https://www.zjzs.net/ | ✅ 已导入 | ✅ 已导入 |
| 24 | 北京 | 北京教育考试院 | https://www.bjeea.cn/ | ✅ 已导入 | ✅ 已导入 |
| 25 | 天津 | 天津招考资讯网 | http://www.zhaokao.net/ | 🔵 待采集 | 🔵 待采集 |
| 26 | 山东 | 山东省教育招生考试院 | https://www.sdzk.cn/ | ✅ 已导入 | ✅ 已导入 |
| 27 | 海南 | 海南省考试局 | https://ea.hainan.gov.cn/ | 🔵 待采集 | 🔵 待采集 |

### 2.3 传统高考省份（2省）

> 科类：文科 / 理科

| # | 省份 | 官方教育考试院 | 官网URL | 一分一段表 | 投档表 |
|---|------|--------------|---------|-----------|--------|
| 28 | 新疆 | 新疆教育考试院 | https://www.xjzk.gov.cn/ | 🔵 待采集 | 🔵 待采集 |
| 29 | 西藏 | 西藏自治区教育考试院 | http://zsks.edu.xizang.gov.cn/ | 🔵 待采集 | 🔵 待采集 |

### 2.4 特殊地区

| # | 地区 | 说明 |
|---|------|------|
| 30 | 宁夏 | 3+1+2新高考(2025首届)，宁夏教育考试院 https://www.nxjyks.cn/ |
| 31 | 青海 | 3+1+2新高考(2025首届)，青海省考试网 https://www.qhjyks.com/ |

### 2.5 当前数据覆盖状态

| 状态 | 省份数 | 省份 |
|------|--------|------|
| ✅ 已导入试点数据 | 5省6个数据目录 | 广东(物理+历史)、浙江、山东、北京、上海；广东46所公办本科均有专业级/部分专业级数据，其中18所为聚合/API补充待官方复核 |
| 🔶 来源已发现待导入 | 2 | 江苏、河北 |
| 🔵 待采集 | 24 | 其余所有省份 |
| **合计** | **31** | |

---

## 三、全国数据采集技术路线

### 3.1 三级数据采集策略

```
┌─────────────────────────────────────────────────────────────┐
│  第一级：省级投档表（必采，覆盖面最广）                        │
│  来源：各省教育考试院                                         │
│  覆盖：该省所有在招院校（含外省院校）                          │
│  精度：院校专业组级（新高考）/ 院校级（传统高考）               │
│  数据量：~14万条                                              │
├─────────────────────────────────────────────────────────────┤
│  第二级：一分一段表（必采，位次转换必需）                       │
│  来源：各省教育考试院                                         │
│  覆盖：全省所有分数段                                          │
│  精度：每个分数对应的累计位次                                  │
│  数据量：~5万条                                               │
├─────────────────────────────────────────────────────────────┤
│  第三级：高校分专业录取分数（选采，精度最高）                   │
│  来源A：各高校招生网（官方，需逐校编写导入器）                  │
│  来源B：掌上高考API（聚合，可批量获取）                        │
│  来源C：阳光高考平台（教育部官方，需逐校查询）                  │
│  覆盖：仅限公开分专业数据的院校                                │
│  精度：专业级                                                  │
│  数据量：预估50-100万条                                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 掌上高考API批量采集方案（核心突破）

**发现：掌上高考(gaokao.cn)有公开JSON API，可批量获取全国高校分专业录取数据**

#### API接口

```
GET https://static-data.gaokao.cn/www/2.0/schoolspecialscore/{school_id}/{year}/{prov_id}.json
```

#### 请求参数

| 参数 | 说明 | 示例 |
|------|------|------|
| school_id | 学校ID（需先获取） | 1 (北京大学) |
| year | 年份 | 2025 |
| prov_id | 省份ID | 32 (江苏) |

#### 省份ID映射表

```python
PROVINCE_ID_MAP = {
    11: "北京", 12: "天津", 13: "河北", 14: "山西", 15: "内蒙古",
    21: "辽宁", 22: "吉林", 23: "黑龙江", 31: "上海", 32: "江苏",
    33: "浙江", 34: "安徽", 35: "福建", 36: "江西", 37: "山东",
    41: "河南", 42: "湖北", 43: "湖南", 44: "广东", 45: "广西",
    46: "海南", 50: "重庆", 51: "四川", 52: "贵州", 53: "云南",
    54: "西藏", 61: "陕西", 62: "甘肃", 63: "青海", 64: "宁夏",
    65: "新疆",
}
```

#### 返回数据结构

```json
{
  "data": {
    "普通本科": {
      "item": [
        {
          "type": "物理类",           // 科类
          "local_batch_name": "本科批", // 批次
          "min": 618,                 // 最低分
          "max": 635,                 // 最高分
          "average": 625,             // 平均分
          "min_section": 15000,       // 最低位次
          "lq_num": 34,              // 录取人数
          "zslx_name": "普通类",      // 录取类型
          "level1_name": "工学",      // 一级类别
          "level2_name": "计算机类",   // 二级类别
          "sp_name": "计算机科学与技术", // 专业名称
          "sg_name": "206",           // 专业组名称
          "sg_info": "物理+化学"      // 选科要求
        }
      ]
    }
  }
}
```

#### 批量采集脚本设计

```python
"""
全国高校分专业录取分数批量采集器
基于掌上高考公开API
"""
import requests
import pandas as pd
import time
import random
import os
from pathlib import Path

# 1. 获取掌上高考高校ID列表
SCHOOL_LIST_URL = "https://static-data.gaokao.cn/www/2.0/school/school_code.json?a=www.gaokao.cn"

def fetch_all_school_ids():
    """获取掌上高考school_id原始列表；本科范围需再用教育部/阳光高考清单过滤。"""
    resp = requests.get(SCHOOL_LIST_URL, timeout=15)
    schools = resp.json().get("data", {})
    return [{"source_code": code,
             "school_id": item["school_id"],
             "school_name": item["name"]}
            for code, item in schools.items()]

# 2. 批量采集分专业录取分数
SCORE_URL = "https://static-data.gaokao.cn/www/2.0/schoolspecialscore/{school_id}/{year}/{prov_id}.json"

def fetch_school_scores(school_id, year, prov_id):
    """获取某校某年某省的分专业录取数据"""
    url = SCORE_URL.format(school_id=school_id, year=year, prov_id=prov_id)
    resp = requests.get(url, timeout=10)
    time.sleep(random.uniform(0.5, 1.5))  # 控制频率

    if resp.status_code == 404:
        return []  # 该校在该省无招生

    data = resp.json().get("data", {})
    rows = []
    for major_type, major_info in data.items():
        for item in major_info.get("item", []):
            rows.append({
                "year": year,
                "province": PROVINCE_ID_MAP.get(prov_id, str(prov_id)),
                "track": item.get("type", ""),
                "batch": item.get("local_batch_name", ""),
                "school_name": school_name,
                "major_group": item.get("sg_name", ""),
                "major_name": item.get("sp_name", ""),
                "plan_type": item.get("zslx_name", "普通类"),
                "min_score": item.get("min", ""),
                "max_score": item.get("max", ""),
                "avg_score": item.get("average", ""),
                "min_rank": item.get("min_section", ""),
                "admit_count": item.get("lq_num", ""),
                "subject_requirement": item.get("sg_info", ""),
                "level1_category": item.get("level1_name", ""),
                "level2_category": item.get("level2_name", ""),
                "source_url": url,
                "source_name": "掌上高考(gaokao.cn)",
                "notes": f"API采集;招生类型={major_type}"
            })
    return rows

# 3. 断点续采 + 多线程
# 使用日志文件记录已完成的 (school_id, year, prov_id) 组合
# 10线程并发，预计完整采集需3-5天
```

#### 采集预估

| 项目 | 数量 |
|------|------|
| 本科院校数 | 1365所 |
| 省份数 | 31个 |
| 年份数 | 3年(2023-2025) |
| 总请求数 | 1365 × 31 × 3 = **127,055次** |
| 单线程预计耗时 | ~7天(每次1.5秒) |
| 10线程预计耗时 | ~18小时 |
| 预计有效数据行 | **50-100万条** |

### 3.3 省级教育考试院采集方案

每个省需采集两类数据：

#### A. 一分一段表

| 省份类型 | 格式 | 采集方式 |
|---------|------|---------|
| 新高考3+1+2 | 物理类/历史类分开 | PDF/Excel/图片，需OCR或解析 |
| 新高考3+3 | 综合类不分科 | PDF/Excel |
| 传统高考 | 文科/理科分开 | PDF/Excel |

#### B. 本科投档表

| 省份类型 | 格式 | 投档精度 |
|---------|------|---------|
| 新高考3+1+2 | 院校专业组级 | 含专业组代码、最低分、最低排位 |
| 新高考3+3 | 院校专业组级(上海) / 专业级(浙江/山东) | 浙江/山东直接到专业级 |
| 传统高考 | 院校级 | 仅院校最低分 |

### 3.4 高校官网采集方案（精度最高但工作量最大）

针对重点高校（985/211/双一流约150所），从各校招生网获取专业级数据：

| 技术路线 | 适用院校 | 已有导入器 |
|---------|---------|-----------|
| JSON API | 中山大学、华南理工、广东外语外贸、汕头大学等 | 5个 |
| HTML表格 | 暨南大学、东莞理工、韩山师范等 | 15个 |
| PDF文本表 | 华南师范、广东财经等 | 5个 |
| 图片表+OCR | 华南农业、广东工业、广东医科等 | 10个 |
| Excel附件 | 嘉应学院、仲恺农业等 | 3个 |

> 全国150所重点高校逐校编写导入器工作量巨大，建议**优先使用掌上高考API批量采集，再对重点高校用官网数据交叉验证**。

---

## 四、全国版数据架构

### 4.1 目录结构

```
gaokao-volunteer-advisor/
├── SKILL.md
├── references/
│   ├── data-schema.md                      # 数据格式规范(不变)
│   ├── data-collection.md                  # 数据采集指南(扩展全国)
│   ├── advising-rules.md                   # 推荐规则
│   ├── major-reference.md                  # 专业就业前景与学习难度
│   ├── province-sources.md                 # 🆕 全国31省数据源清单
│   ├── national-schools-inventory.md       # 🆕 全国1365所本科院校清单
│   └── guangdong-schools-inventory.md      # 广东46校详细清单(已有)
├── scripts/
│   ├── export_gaokao_cn_school_ids.py      # 掌上高考school_id导出器(已有)
│   ├── import_gaokao_cn_major_scores.py    # 掌上高考API补充导入器(已有，支持province-id/schools-csv)
│   ├── fetch_province_rank_table.py        # 🆕 省级一分一段表采集器
│   ├── fetch_province_admission.py         # 🆕 省级投档表采集器
│   ├── normalize_data.py                   # 通用归一化(已有)
│   ├── pdf_table_to_csv.py                 # PDF解析(已有)
│   ├── html_table_to_csv.py                # HTML解析(已有)
│   ├── ocr_*.py / vision_ocr_*.swift       # OCR工具(已有)
│   ├── fill_admission_*.py                 # 位次/分数补齐(已有)
│   ├── audit_data.py                       # 审计(已有)
│   ├── recommend.py                        # 推荐(需扩展多省份)
│   └── run_advisor.py                      # 交互入口(需扩展多省份)
└── assets/
    ├── pilot-data/                         # 已有6省试点数据
    │   ├── guangdong-physics/              # ✅ 16634条
    │   ├── guangdong-history/              # ✅ 7684条
    │   ├── zhejiang-ordinary/              # ✅ 51939条
    │   ├── shandong-ordinary/              # ✅ 60911条
    │   ├── beijing-ordinary/               # ✅ 3956条
    │   └── shanghai-ordinary/              # ✅ 4253条
    ├── national-data/                      # 🆕 全国数据目录
    │   ├── hebei-physics/                  # 河北(3+1+2)
    │   ├── hebei-history/
    │   ├── jiangsu-physics/                # 江苏(3+1+2)
    │   ├── jiangsu-history/
    │   ├── anhui-physics/                  # 安徽(3+1+2)
    │   ├── anhui-history/
    │   ├── ... (每省2个目录,物理+历史)
    │   ├── tianjin-ordinary/               # 天津(3+3)
    │   ├── hainan-ordinary/                # 海南(3+3)
    │   ├── xinjiang-science/               # 新疆(传统-理科)
    │   ├── xinjiang-liberal/               # 新疆(传统-文科)
    │   └── ... (共约55个目录)
    ├── school-major-scores/                # 🆕 全国高校专业级数据
    │   ├── by-school/                      # 按学校组织(官网采集)
    │   │   ├── sysu/                       # 中山大学
    │   │   ├── pku/                        # 北京大学
    │   │   └── ...
    │   └── by-api/                         # 按API批次组织(掌上高考)
    │       ├── batch_001.csv
    │       └── ...
    └── source-discovery/                   # 来源发现
        ├── guangdong/                      # 广东(已有)
        └── national/                       # 🆕 全国来源发现
            ├── province_manifest.csv       # 各省采集清单
            ├── gaokao_cn_province_id_map.csv # 掌上高考省份ID映射
            └── gaokao_cn_school_ids.csv    # 掌上高考学校ID映射
```

### 4.2 扩展的CSV格式

`admission_records.csv` 增加省份考生维度（已有province字段，无需改动）：

```csv
year,province,track,batch,school_name,school_code,major_group,major_name,plan_type,min_score,min_rank,admit_count,source_url,source_name,notes
```

> 现有格式已支持全国数据，`province` 字段记录考生所在省份，不是学校所在省份。

### 4.3 推荐引擎扩展

`recommend.py` 需扩展以支持多省份：

```bash
# 当前(仅支持已有试点数据的省份)
python3 scripts/recommend.py --province 广东 --track 物理类 --score 600 --rank 43000

# 扩展后(支持全国31省)
python3 scripts/recommend.py --province 四川 --track 物理类 --score 600 --rank 43000
python3 scripts/recommend.py --province 浙江 --track 普通类 --score 600 --rank 43000
python3 scripts/recommend.py --province 新疆 --track 理科 --score 600 --rank 43000
```

推荐引擎自动选择 `assets/national-data/{province}-{track}/` 目录的数据。

---

## 五、分阶段实施计划

### 阶段一：省级投档表全覆盖（优先级最高）

**目标**：31省 × 3年 的省级投档表 + 一分一段表全部导入

| 任务 | 省份 | 数据量预估 | 耗时预估 |
|------|------|-----------|---------|
| 已完成 | 5省6目录(粤物理/历史、浙、鲁、京、沪；含广东专业级补充) | 14.3万条 | ✅ |
| 来源已发现 | 2省(苏冀) | ~2万条 | 1天 |
| PDF/Excel可直接解析 | ~15省 | ~8万条 | 5天 |
| 需OCR处理 | ~8省 | ~4万条 | 10天 |
| **小计** | **31省** | **~28万条** | **~16天** |

### 阶段二：掌上高考API批量采集专业级数据

**目标**：1365所本科 × 31省 × 3年 的专业级录取数据

| 任务 | 说明 | 耗时预估 |
|------|------|---------|
| 获取全国高校ID列表 | 从掌上高考school_code接口导出，再用教育部/阳光高考本科名单过滤 | 1分钟 |
| 编写批量采集脚本 | `import_gaokao_cn_major_scores.py` 已支持 `--province-id`/`--schools-csv` | 已完成 |
| 10线程并发采集 | 127,055次请求 | 18-24小时 |
| 数据清洗+归一化 | 转为标准CSV格式 | 2天 |
| 审计+补齐位次 | 用一分一段表补齐 | 1天 |
| **小计** | - | **~5天** |

### 阶段三：重点高校官网数据交叉验证

**目标**：对985/211/双一流约150所重点高校，用官网数据验证掌上高考API数据的准确性

| 任务 | 说明 | 耗时预估 |
|------|------|---------|
| 已有导入器/补充导入器 | 广东46校（28校官方完整 + 18校聚合/API补充待复核） | ✅ |
| 编写985高校导入器 | ~39所(含已完成的广东8所) | 10天 |
| 编写211高校导入器 | ~73所(不含985) | 15天 |
| 编写双一流导入器 | ~38所(不含985/211) | 8天 |
| 交叉验证 | 对比API数据和官网数据 | 3天 |
| **小计** | ~150所 | **~36天** |

### 阶段四：推荐引擎全国化 + 测试

| 任务 | 说明 | 耗时预估 |
|------|------|---------|
| 扩展recommend.py | 支持31省+传统高考 | 2天 |
| 扩展run_advisor.py | 交互式全国省份选择 | 1天 |
| 扩展audit_data.py | 全国数据审计 | 1天 |
| 端到端测试 | 每省抽测1-2个案例 | 3天 |
| **小计** | - | **~7天** |

### 总时间预估

| 阶段 | 耗时 | 可并行 |
|------|------|--------|
| 阶段一 | 16天 | - |
| 阶段二 | 5天 | 与阶段一并行 |
| 阶段三 | 36天 | 与阶段一/二并行 |
| 阶段四 | 7天 | 需等阶段一/二完成 |
| **总计(串行)** | ~64天 | - |
| **总计(并行优化)** | **~30天** | - |

---

## 六、掌上高考API采集器规格

### 6.1 脚本：`scripts/import_gaokao_cn_major_scores.py`

```python
#!/usr/bin/env python3
"""
全国高校分专业录取分数补充导入器
数据源：掌上高考(gaokao.cn)公开JSON API
默认覆盖：广东剩余缺口学校；传 `--province-id` 和 `--schools-csv` 后可扩展到其他省份
"""

import argparse
import csv
import json
import os
import random
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# 省份ID映射
PROVINCE_ID_MAP = {
    11: "北京", 12: "天津", 13: "河北", 14: "山西", 15: "内蒙古",
    21: "辽宁", 22: "吉林", 23: "黑龙江", 31: "上海", 32: "江苏",
    33: "浙江", 34: "安徽", 35: "福建", 36: "江西", 37: "山东",
    41: "河南", 42: "湖北", 43: "湖南", 44: "广东", 45: "广西",
    46: "海南", 50: "重庆", 51: "四川", 52: "贵州", 53: "云南",
    54: "西藏", 61: "陕西", 62: "甘肃", 63: "青海", 64: "宁夏",
    65: "新疆",
}

SCHOOL_SEARCH_URL = "https://static-data.gaokao.cn/www/2.0/school/school_code.json?a=www.gaokao.cn"
SCORE_URL = "https://static-data.gaokao.cn/www/2.0/schoolspecialscore/{school_id}/{year}/{prov_id}.json"

# 标准CSV列(与现有格式兼容)
CSV_COLUMNS = [
    "year", "province", "track", "batch", "school_name", "school_code",
    "major_group", "major_name", "plan_type", "min_score", "min_rank",
    "admit_count", "source_url", "source_name", "notes"
]

def fetch_all_schools():
    """获取掌上高考school_id原始列表；本科范围需再用教育部/阳光高考清单过滤。"""
    resp = requests.get(SCHOOL_SEARCH_URL, timeout=15,
                       headers={"User-Agent": "Mozilla/5.0"})
    data = resp.json().get("data", {})
    schools = []
    for source_code, s in data.items():
        if isinstance(s, dict) and s.get("school_id") and s.get("name"):
            schools.append({
                "source_code": source_code,
                "school_id": s["school_id"],
                "school_name": s["name"],
                "nature": s.get("nature", ""),  # 公办/民办
                "type": s.get("type", ""),      # 综合/理工/师范...
            })
    return schools

def fetch_scores(school_id, school_name, year, prov_id, prov_name):
    """获取某校某年某省的分专业录取数据"""
    url = SCORE_URL.format(school_id=school_id, year=year, prov_id=prov_id)
    try:
        resp = requests.get(url, timeout=10,
                           headers={"User-Agent": "Mozilla/5.0",
                                    "Referer": "https://www.eol.cn/"})
        time.sleep(random.uniform(0.3, 1.0))  # 控制频率

        if resp.status_code == 404:
            return []  # 该校在该省无招生

        data = resp.json().get("data", {})
        rows = []
        for major_type, major_info in data.items():
            for item in major_info.get("item", []):
                rows.append({
                    "year": year,
                    "province": prov_name,
                    "track": item.get("type", ""),
                    "batch": item.get("local_batch_name", ""),
                    "school_name": school_name,
                    "school_code": str(school_id),
                    "major_group": item.get("sg_name", ""),
                    "major_name": item.get("sp_name", ""),
                    "plan_type": item.get("zslx_name", "普通类"),
                    "min_score": item.get("min", ""),
                    "min_rank": item.get("min_section", ""),
                    "admit_count": item.get("lq_num", ""),
                    "source_url": f"https://www.gaokao.cn/school/{school_id}/provincescore",
                    "source_name": "掌上高考",
                    "notes": f"API采集;类别={item.get('level1_name','')}/{item.get('level2_name','')};选科={item.get('sg_info','')};招生类型={major_type}"
                })
        return rows
    except Exception as e:
        print(f"  错误: {school_name} {year} {prov_name}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="掌上高考API批量采集器")
    parser.add_argument("--years", default="2023,2024,2025", help="年份(逗号分隔)")
    parser.add_argument("--provinces", default="", help="省份ID(逗号分隔,空=全部31省)")
    parser.add_argument("--max-workers", type=int, default=10, help="并发线程数")
    parser.add_argument("--output-dir", default="assets/school-major-scores/by-api",
                       help="输出目录")
    parser.add_argument("--resume", action="store_true", help="断点续采")
    args = parser.parse_args()

    years = [int(y) for y in args.years.split(",")]
    prov_ids = [int(p) for p in args.provinces.split(",")] if args.provinces else list(PROVINCE_ID_MAP.keys())

    # 1. 获取全国本科院校列表
    print("正在获取全国本科院校列表...")
    schools = fetch_all_schools()
    print(f"共获取 {len(schools)} 所本科院校")

    # 2. 断点续采
    log_file = Path(args.output_dir) / "progress.log"
    finished = set()
    if args.resume and log_file.exists():
        with open(log_file) as f:
            finished = set(line.strip().split(",") for line in f)

    # 3. 批量采集
    os.makedirs(args.output_dir, exist_ok=True)
    all_rows = []

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = []
        for school in schools:
            for year in years:
                for prov_id in prov_ids:
                    key = (str(school["school_id"]), str(year), str(prov_id))
                    if key in finished:
                        continue
                    futures.append(executor.submit(
                        fetch_scores,
                        school["school_id"], school["school_name"],
                        year, prov_id, PROVINCE_ID_MAP[prov_id]
                    ))

        for i, future in enumerate(as_completed(futures), 1):
            rows = future.result()
            all_rows.extend(rows)
            if i % 100 == 0:
                print(f"  进度: {i}/{len(futures)}")
                # 定期保存
                if all_rows:
                    batch_file = Path(args.output_dir) / f"batch_{i//100}.csv"
                    with open(batch_file, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                        writer.writeheader()
                        writer.writerows(all_rows)
                    all_rows = []

    # 4. 最终保存
    if all_rows:
        final_file = Path(args.output_dir) / "final_batch.csv"
        with open(final_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(all_rows)

    print(f"采集完成，数据保存到 {args.output_dir}")

if __name__ == "__main__":
    main()
```

### 6.2 使用方式

```bash
# 刷新掌上高考school_id清单
python3 scripts/export_gaokao_cn_school_ids.py

# 只采集特定省份的一个科类；先dry-run，确认来源和行数后再正式导入
python3 scripts/import_gaokao_cn_major_scores.py --data-dir assets/national-data/zhejiang-ordinary --province 浙江 --province-id 33 --track 普通类 --schools-csv assets/source-discovery/national/gaokao_cn_school_ids.csv --dry-run

# 只采集2025年
python3 scripts/import_gaokao_cn_major_scores.py --data-dir assets/national-data/zhejiang-ordinary --province 浙江 --province-id 33 --track 普通类 --schools-csv assets/source-discovery/national/gaokao_cn_school_ids.csv --years 2025 --dry-run
```

### 6.3 数据验证

采集完成后，与已有官方数据交叉验证：

```bash
# 对比掌上高考API数据 vs 已导入的官方数据
python3 scripts/audit_data.py \
  --data-dir assets/school-major-scores/by-api \
  --compare-dir assets/pilot-data/guangdong-physics \
  --target-years 2023,2024,2025
```

---

## 七、各省高考模式与数据格式速查

| 省份 | 模式 | 科类 | 批次 | 投档精度 | 一分一段表格式 |
|------|------|------|------|---------|--------------|
| 北京 | 3+3 | 普通类 | 本科普通批 | 院校专业组 | PDF文本表 |
| 天津 | 3+3 | 普通类 | 本科批A/B阶段 | 院校专业组 | PDF |
| 上海 | 3+3 | 普通类 | 本科普通批 | 院校专业组 | 图片PDF(需OCR) |
| 浙江 | 3+3 | 普通类 | 普通类第一段 | **专业级** | PDF文本表 |
| 山东 | 3+3 | 普通类 | 常规批第1次 | **专业级** | Excel |
| 海南 | 3+3 | 普通类 | 本科批 | 院校专业组 | PDF |
| 河北 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | 扫描PDF(需OCR) |
| 辽宁 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 江苏 | 3+1+2 | 物理/历史 | 本科批次 | 院校专业组 | 图片附件(需OCR) |
| 福建 | 3+1+2 | 物理/历史 | 普通类本科批 | 院校专业组 | PDF |
| 湖北 | 3+1+2 | 物理/历史 | 本科普通批 | 院校专业组 | PDF |
| 湖南 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 广东 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF/Excel |
| 重庆 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 黑龙江 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 甘肃 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 吉林 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 安徽 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 江西 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 贵州 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 广西 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 四川 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 河南 | 3+1+2 | 物理/历史 | 本科一批/二批 | 院校专业组 | PDF |
| 云南 | 3+1+2 | 物理/历史 | 本科一批/二批 | 院校专业组 | PDF |
| 陕西 | 3+1+2 | 物理/历史 | 本科一批/二批 | 院校专业组 | PDF |
| 内蒙古 | 3+1+2 | 物理/历史 | 本科一批/二批 | 院校专业组 | PDF |
| 山西 | 3+1+2 | 物理/历史 | 本科一批/二批 | 院校专业组 | PDF |
| 宁夏 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 青海 | 3+1+2 | 物理/历史 | 本科批 | 院校专业组 | PDF |
| 新疆 | 传统 | 文/理 | 本科一批/二批 | 院校级 | PDF |
| 西藏 | 传统 | 文/理 | 本科一批/二批 | 院校级 | PDF |

---

## 八、重点高校官网数据源（150所）

### 8.1 985高校（39所）

| 高校 | 所在地 | 招生网 | 数据格式 | 导入器状态 |
|------|--------|--------|---------|-----------|
| 北京大学 | 北京 | https://admission.pku.edu.cn/ | 查询系统 | 🔵 待编写 |
| 清华大学 | 北京 | https://join-tsinghua.edu.cn/ | 查询系统 | 🔵 待编写 |
| 复旦大学 | 上海 | https://ao.fudan.edu.cn/ | 查询系统 | 🔵 待编写 |
| 上海交通大学 | 上海 | https://admissions.sjtu.edu.cn/ | 查询系统 | 🔵 待编写 |
| 浙江大学 | 杭州 | https://zsb.zju.edu.cn/ | 查询系统 | 🔵 待编写 |
| 南京大学 | 南京 | https://bkzs.nju.edu.cn/ | 查询系统 | 🔵 待编写 |
| 中国科学技术大学 | 合肥 | https://zsb.ustc.edu.cn/ | 查询系统 | 🔵 待编写 |
| 武汉大学 | 武汉 | https://aoff.whu.edu.cn/ | 查询系统 | 🔵 待编写 |
| 华中科技大学 | 武汉 | https://zsb.hust.edu.cn/ | 查询系统 | 🔵 待编写 |
| 中山大学 | 广州 | https://admission.sysu.edu.cn/ | JSON API | ✅ 已有 |
| ... | ... | ... | ... | ... |

> 完整39所985 + 73所211 + 38所双一流(非985/211) 清单见附录

### 8.2 广东高校（46所，已有详细清单）

见 `references/guangdong-schools-inventory.md` + `references/special-schools-inventory.md`

---

## 九、推荐引擎全国化改造

### 9.1 改造要点

```python
# recommend.py 改造

# 1. 自动发现数据目录
def find_data_dir(province, track):
    """根据省份和科类自动定位数据目录"""
    # 新高考3+1+2
    if track in ("物理类", "历史类"):
        return f"assets/national-data/{province}-{track_map[track]}"
    # 新高考3+3
    elif track == "普通类":
        return f"assets/national-data/{province}-ordinary"
    # 传统高考
    elif track in ("理科", "文科"):
        return f"assets/national-data/{province}-{track_map[track]}"

# 2. 支持传统高考省份
# 新疆/西藏: track = "理科" / "文科", batch = "本科一批" / "本科二批"

# 3. 专业级数据优先
# 如果有 major_name 的数据，优先使用专业级数据推荐
# 否则使用院校专业组级数据

# 4. 外省院校推荐
# 考生省份=四川 时，从四川数据目录中读取所有在四川招生的院校(含外省院校)
```

### 9.2 推荐输出增强

```
全国版推荐输出：
1. 输入摘要(省份/科类/分数/位次/兴趣)
2. 数据覆盖声明(该省数据状态、院校数、年份)
3. 冲稳保垫志愿表
   - 含近3年最低分/位次
   - 标注数据精度(专业级/专业组级/院校级)
   - 标注院校所在地(本省/外省)
   - 标注院校层次(985/211/双一流/普通)
4. 专业前景分析
5. 院校信息补充(城市/学费/住宿/气候等)
6. 待确认事项
7. 风险提示
```

---

## 十、Codex 执行任务清单

### 任务1：扩展掌上高考API采集器（最高优先级）
```
文件: scripts/import_gaokao_cn_major_scores.py
当前功能: 默认广东缺口导入，支持 --province-id/--schools-csv 扩展到其他省份
后续功能: 增加断点续采、限速、分片输出和并发队列后，再批量采集1365校×31省×3年专业级录取数据
API: https://static-data.gaokao.cn/www/2.0/schoolspecialscore/{school_id}/{year}/{prov_id}.json
预估: 全国全量需分批运行和抽样校验，不能一次性写入正式推荐目录
输出: assets/school-major-scores/by-api/*.csv
```

### 任务2：编写省级数据采集器
```
文件: scripts/fetch_province_data.py
功能: 逐省采集一分一段表 + 本科投档表
来源: 各省教育考试院(见第二节URL清单)
优先级: 先做PDF/Excel可直接解析的15省, 再做需OCR的8省
输出: assets/national-data/{province}-{track}/*.csv
```

### 任务3：扩展推荐引擎
```
文件: scripts/recommend.py (修改)
功能: 支持全国31省 + 传统高考 + 新高考
新增: 自动定位数据目录、传统文理支持、院校层次标注
```

### 任务4：扩展审计工具
```
文件: scripts/audit_data.py (修改)
功能: 支持审计全国数据, 按省份统计覆盖率
```

### 任务5：获取全国高校ID映射表
```
文件: assets/source-discovery/national/gaokao_cn_school_ids.csv
功能: 存储掌上高考school_id与院校名称/代码的映射
来源: https://static-data.gaokao.cn/www/2.0/school/school_code.json?a=www.gaokao.cn
刷新命令: python3 scripts/export_gaokao_cn_school_ids.py
```

### 任务6：采集教育部全国高校名单
```
文件: references/national-schools-inventory.md
来源: https://hudong.moe.gov.cn/qggxmd/ (教育部官方)
内容: 1365所本科院校完整清单(名称/代码/所在地/类型/公办民办)
```

### 任务7：数据交叉验证
```
对已有广东46校的官网/补充数据 vs 掌上高考API数据做对比
验证API数据准确性
如果偏差<2分/500位次, 则API数据可用于推荐
如果偏差较大, 则该校需用官网数据覆盖
```

### 任务8：端到端测试
```
每省抽取1-2个测试案例:
- 高分段(全省前1%)
- 中分段(全省前20%)
- 低分段(刚过本科线)
验证推荐结果合理性
```

---

## 附录A：全国31省2026高考分数线速查

> 本附录是 Workbuddy 生成时的速查快照。高考分数线属于高时效数据，正式面向考生建议前必须回到各省考试院核验发布日期、批次线、特殊类型线和当年志愿规则。

| 省份 | 模式 | 本科线(物理/理科) | 本科线(历史/文科) | 特控线(物理) | 特控线(历史) |
|------|------|-----------------|-----------------|------------|------------|
| 广东 | 3+1+2 | 425 | 440 | 539 | 546 |
| 北京 | 3+3 | 430(综合) | - | 519 | - |
| 上海 | 3+3 | 403(综合) | - | 504 | - |
| 浙江 | 3+3 | 490(一段) | - | 592 | - |
| 山东 | 3+3 | 441(一段) | - | 521 | - |
| 江苏 | 3+1+2 | 463 | 482 | 519 | 537 |
| 河北 | 3+1+2 | 459 | 477 | 499 | 527 |
| 湖北 | 3+1+2 | 426 | 442 | 516 | 536 |
| 湖南 | 3+1+2 | 405 | 446 | 476 | 503 |
| 福建 | 3+1+2 | 441 | 450 | 520 | 531 |
| 重庆 | 3+1+2 | 425 | 438 | 498 | 515 |
| 辽宁 | 3+1+2 | 367 | 437 | 515 | 522 |
| 四川 | 3+1+2 | 438 | 467 | 518 | 533 |
| 河南 | 3+1+2 | 427 | 471 | 535 | 552 |
| 安徽 | 3+1+2 | 461 | 477 | 514 | 515 |
| 江西 | 3+1+2 | 429 | 486 | 505 | 539 |
| 陕西 | 3+1+2 | 394 | 414 | 473 | 497 |
| 云南 | 3+1+2 | 430 | 465 | 495 | 535 |
| 广西 | 3+1+2 | 370 | 402 | 495 | 518 |
| 贵州 | 3+1+2 | 387 | 458 | - | - |
| 甘肃 | 3+1+2 | 374 | 412 | 475 | 500 |
| 吉林 | 3+1+2 | 340 | 384 | 479 | 493 |
| 黑龙江 | 3+1+2 | 360 | 405 | 472 | 480 |
| 内蒙古 | 3+1+2 | 375 | 418 | 487 | 523 |
| 山西 | 3+1+2 | 419 | 443 | 507 | 534 |
| 宁夏 | 3+1+2 | 372 | 404 | 441 | 482 |
| 青海 | 3+1+2 | 350 | 405 | 420 | 450 |
| 天津 | 3+3 | 458(综合) | - | 547 | - |
| 海南 | 3+3 | 480(综合) | - | 568 | - |
| 新疆 | 传统 | 304(理二本) | 315(文二本) | 468(理一本) | 451(文一本) |
| 西藏 | 传统 | - | - | - | - |

---

## 附录B：数据源可靠性分级

| 级别 | 来源 | 可靠性 | 用途 |
|------|------|--------|------|
| S级 | 各省教育考试院官方投档表/一分一段表 | 最高 | 必须采集，作为基准 |
| S级 | 各高校招生网官方数据 | 最高 | 专业级数据首选 |
| A级 | 教育部阳光高考平台(gaokao.chsi.com.cn) | 高 | 交叉验证 |
| B级 | 掌上高考(gaokao.cn)API | 良好 | 批量采集专业级数据 |
| C级 | 其他聚合站(dxsbb/gk100/hfplg等) | 一般 | 可作为缺口补充，但必须显式标注来源和待官方复核 |

> **重要规则**：官方来源优先。聚合站(C级)可以补足缺口，但不得伪装成官方数据；每条聚合站补充记录的 `source_name`/`source_url` 必须保留聚合站来源，`notes` 必须标注 `聚合站来源，待官方复核`。
