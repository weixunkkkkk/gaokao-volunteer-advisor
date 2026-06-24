# Gaokao Volunteer Advisor

2026 高考志愿参考 Skill 原型：输入省份、科类、分数或位次、兴趣方向，输出院校冲稳保建议和专业就业方向参考。

## 当前覆盖

已导入并严格审计的 2023-2025 官方历史数据：

- 广东物理类
- 广东历史类
- 浙江普通类
- 山东普通类
- 北京普通类
- 上海普通类

数据来源优先使用各省市教育考试院/招生考试院官方页面和附件。每个试点目录下都有 `source_registry.csv` 和 `collection_manifest.csv` 记录来源、附件、导入器和状态。

## 快速运行

```bash
python3 scripts/run_advisor.py --province 广东 --track 物理类 --rank 31500 --interests 电气,计算机,自动化
python3 scripts/run_advisor.py --province 上海 --score 555 --interests 人工智能,财经
python3 scripts/run_advisor.py
```

`run_advisor.py` 会自动匹配 `assets/pilot-data` 下已审计的数据包。若不传参数，会进入交互式输入。

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

- 当前是志愿参考工具，不保证录取。
- 优先按位次判断，分数只作为辅助。
- 多数省份官方投档表是“院校专业组”维度，不等于专业级录取线。
- 给 2026 考生使用前，必须核对当年招生计划、专业组、选科要求、学费、校区、中外合作/专项计划差异。

