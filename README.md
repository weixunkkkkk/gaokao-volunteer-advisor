# 2026 高考志愿参考 Skill

2016 年我填报高考志愿的时候，互联网远没有今天这么发达。

那时候获取信息的主要方式，还是翻阅一本厚厚的《招生计划与报考指南》。很多学校、专业、就业方向的信息都不透明，不同渠道的数据也很难交叉验证，信息差非常明显。

所以今年，我利用 AI 做了这个「2026 高考志愿参考 Skill」，并将项目开源。

这个 Skill 的目标不是替考生做决定，也不是告诉你“报哪所学校一定能录取”。它会结合省份、选科（科类）、高考分数、全省位次、兴趣方向等信息，再参考近几年公开录取数据，帮助考生建立一个相对客观的定位参考。

项目现在的定位是：面向全国省份、城市、院校和专业，读取本地或仓库内置的高考 Excel 数据包，按考生位次和兴趣专业生成院校、专业、冲稳保垫与本省/省外推荐。clone 仓库后，默认会优先读取 `assets/raw-data/各省份`，不依赖任何个人本机路径。

我不希望把它做成一个“玄学推荐学校”的工具。更希望它成为一个能够提供依据、解释逻辑、展示风险边界的参考工具。

## 它和简单志愿推荐工具有什么不同

很多志愿工具只看学校最低录取分数线，但高校公布的最低录取线，往往对应某个专业组、调剂专业或者相对冷门方向。

同一所学校里，热门专业、优势学科、特色专业的录取分数和位次，通常会明显高于学校最低线。

因此，本项目不只整理院校或院校专业组最低线，也在持续整理专业级录取数据。尤其是广东高校，我正在优先从官方来源拆解到专业层级的最低录取分数和最低录取位次。

通过这些数据，你可以更方便地了解：

- 当前分数和位次大致处于什么区间
- 对应有哪些可能的院校选择
- 哪些学校属于冲、稳、保、垫
- 学校最低线与目标专业线之间存在多大差距
- 感兴趣的专业对应哪些培养方向
- 这些专业未来的就业方向、发展路径以及潜在风险

## 数据覆盖

已导入并严格审计的 2023-2025 官方历史数据：

- 广东物理类
- 广东历史类
- 浙江普通类
- 山东普通类
- 北京普通类
- 上海普通类

数据来源优先使用各省市教育考试院/招生考试院官方页面和附件。每个试点目录下都有 `source_registry.csv` 和 `collection_manifest.csv` 记录来源、附件、导入器和状态。

仓库同时内置全国 Excel 原始数据包：

- 路径：`assets/raw-data/各省份`
- 规模：约 1.28GB，1045 个有效文件，其中 Excel 文件 1010 个（已过滤 `.DS_Store` 等系统文件）
- 范围：全国省份/直辖市/自治区数据文件夹，包括北京、上海、广东、福建、湖南、江苏、浙江、山东、四川、河南、河北等 31 个省级目录
- 内容：近年招生计划、专业录取分数、院校录取分数、一分一段表等 Excel 表格

当目标省份/科类没有完整试点 CSV 数据时，脚本会自动读取这个 Excel 原始数据包，尽量识别 2023-2025 年的专业录取线、一分一段表、学校所在省份、学校性质、985/211 等字段，再生成推荐。正式填报前仍需要回到省教育考试院和高校招生网核对当年招生计划、专业组、选科、学费和校区。

广东高校专业级录取数据正在持续整理中，来源包括但不限于：

- 高校招生官网
- 官方招生网
- 官方微信公众号
- 官方 PDF 文件
- 官方公布图片表格
- 公开接口数据

只要能够确认是官方来源，都会尽量拆解到专业层级，并保留来源、附件、缓存路径和导入说明，方便后续交叉核验。

## 复制链接使用

仓库地址：

```text
https://github.com/weixunkkkkk/gaokao-volunteer-advisor
```

在支持从 GitHub 安装 Skill 的客户端中，直接粘贴上面的仓库链接即可。仓库根目录已经包含 `SKILL.md` 和 `agents/openai.yaml`，导入后可以用“高考志愿顾问”或 `gaokao-volunteer-advisor` 调用。

本地运行可以直接 clone：

```bash
git clone https://github.com/weixunkkkkk/gaokao-volunteer-advisor.git
cd gaokao-volunteer-advisor
python3 -m pip install -r requirements.txt
python3 scripts/run_advisor.py --province 广东 --track 物理类 --rank 31500 --interests 电气,计算机,自动化
```

## 用 Codex 使用

本项目已经整理成 Skill 结构，仓库根目录包含：

- `SKILL.md`
- `agents/openai.yaml`
- `scripts/run_advisor.py`
- `assets/pilot-data`
- `assets/raw-data`

在 Codex 中使用时，可以直接通过 GitHub 仓库链接导入：

```text
https://github.com/weixunkkkkk/gaokao-volunteer-advisor
```

导入后，可以这样提问：

```text
使用高考志愿顾问。
我是广东物理类考生，2026 年高考，全省位次 31500 名。
我想读非广东的院校，专业方向关注电气工程、计算机、自动化。
请帮我按冲、稳、保、垫推荐学校和专业，并说明依据和风险。
```

也可以只给部分信息：

```text
使用高考志愿顾问。
省份：广东
科类：物理类
位次：31500
兴趣方向：电气、计算机、自动化
地域偏好：优先省外
```

建议尽量提供以下信息，结果会更准确：

- 省份
- 科类/选科
- 分数
- 全省位次
- 想去的城市或省份
- 是否接受省内/省外
- 感兴趣的专业方向
- 是否接受民办、中外合作、专项计划、提前批等特殊类型

## 用 WorkBuddy / FRAE 使用

如果你使用的是 WorkBuddy、FRAE 或其他支持 GitHub Skill / Agent 导入的工具，可以直接粘贴本仓库链接：

```text
https://github.com/weixunkkkkk/gaokao-volunteer-advisor
```

导入后，选择或调用：

```text
gaokao-volunteer-advisor
```

或者使用中文名称：

```text
高考志愿顾问
```

推荐输入格式：

```text
请调用高考志愿顾问 Skill。

考生信息：
- 省份：广东
- 科类：物理类
- 位次：31500
- 分数：如果没有可以不填
- 地域偏好：非广东院校
- 专业兴趣：电气工程、计算机、自动化
- 目标：推荐冲、稳、保、垫学校，并说明专业就业前景和风险
```

如果工具要求填写 Skill 来源，填写：

```text
GitHub Repository
```

仓库地址填写：

```text
https://github.com/weixunkkkkk/gaokao-volunteer-advisor
```

如果工具不支持直接导入 Skill，也可以把仓库 clone 到本地后运行：

```bash
git clone https://github.com/weixunkkkkk/gaokao-volunteer-advisor.git
cd gaokao-volunteer-advisor
python3 -m pip install -r requirements.txt
python3 scripts/run_advisor.py --province 广东 --track 物理类 --rank 31500 --interests 电气,计算机,自动化
```

## 使用边界

这个 Skill 不是“替你决定报哪所学校”的工具，而是一个基于公开历史数据的参考系统。

它会尽量说明：

- 推荐依据
- 历史分数和位次
- 冲稳保垫判断
- 学校最低线和专业线的差异
- 专业就业方向
- 潜在风险

但它不能保证录取结果。正式填报时，仍然需要以各省教育考试院、目标高校招生官网、当年招生计划和最新招生章程为准。

## 快速运行

```bash
python3 scripts/run_advisor.py --province 广东 --track 物理类 --rank 31500 --interests 电气,计算机,自动化
python3 scripts/run_advisor.py --province 广东 --track 物理类 --rank 50000 --interests 计算机
python3 scripts/run_advisor.py --province 湖南 --track 物理类 --score 570 --interests 计算机
python3 scripts/run_advisor.py --province 上海 --score 555 --interests 人工智能,财经
python3 scripts/run_advisor.py
```

`run_advisor.py` 会优先匹配 `assets/pilot-data` 和 `assets/national-data` 下已审计的数据包；如果目标省份/科类不在试点数据里，会自动读取仓库内置的 `assets/raw-data/各省份` Excel 数据源。若不传参数，会进入交互式输入。

脚本会把匹配省份、科类、2023-2025 年份的专业录取线读入；只给分数时，会用一分一段表估算位次，再按位次做冲稳保判断；结果里会增加“本省/省外重点”。可用 `--raw-data-root ""` 关闭原始 Excel 读取，或用 `--raw-data-root /path/to/各省份` 指定其他目录。

## 数据审计

```bash
python3 scripts/audit_data.py --data-dir assets/pilot-data/guangdong-physics --target-years 2023,2024,2025 --strict
```

批量审计示例：

```bash
for d in assets/pilot-data/*; do
  [ -d "$d" ] && python3 scripts/audit_data.py --data-dir "$d" --target-years 2023,2024,2025 --strict
done
```

## 重要边界

- 本 Skill 提供的是基于公开数据和规则分析生成的参考信息，不构成任何录取承诺、升学保证或报考建议。
- 高考录取受到招生计划变化、报考人数变化、专业冷热程度、政策调整等多种因素影响，历史数据不代表未来结果。
- 优先按位次判断，分数只作为辅助。
- 多数省份官方投档表是“院校专业组”维度，不等于专业级录取线。
- 正式填报志愿时，仍建议结合各省教育考试院公布的信息、高校官方招生简章以及专业招生政策进行综合判断，并进行多渠道交叉核验。
- 给 2026 考生使用前，必须核对当年招生计划、专业组、选科要求、学费、校区、中外合作/专项计划差异。
