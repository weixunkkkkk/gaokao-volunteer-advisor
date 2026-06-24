# 广东46所公办本科高校 - 采集清单与覆盖台账

> 更新时间：2026-06-24 | 与当前 gaokao-volunteer-advisor 数据目录同步
> 数据范围：2023-2025年广东物理类/历史类本科批分专业录取分数候选源
> 使用边界：本文件是采集清单。学校官网、省考试院等官方来源优先；聚合站可作为补充数据源导入，但必须在 `source_name`/`source_url` 保留聚合站来源，并在 `notes` 标注 `聚合站来源，待官方复核`。
> 覆盖目标：广东公办本科46所全部纳入；新升本科/新建本科院校和公安/艺术/体育类特殊院校均在范围内。术科、校考、综合分、公安提前批等特殊录取类型需单独标注，不能和普通本科批混用。

## 状态说明

| 状态 | 含义 |
|------|------|
| ✅ imported | 已完整导入2023-2025专业级数据 |
| 🔶 imported_partial | 部分导入，缺某年份或某科类数据 |
| 🟣 imported_aggregator | 已用聚合站/API补充导入，能进入推荐参考，但必须标注待官方复核 |
| 🔵 source_candidate | 官方来源已初步定位，待逐项复核并编写导入器 |
| 🟡 limited_data | 新建/新升本科院校，历史数据不足3年，已有可用年数据 |
| ⚪ candidate_only | 仅作采集线索，尚未进入正式推荐数据 |

---

## 一、已完整导入 (28所) ✅

> 本次整合已登记：仲恺农业工程学院（专用导入器 `import_zhku_major_scores.py`）。

| # | 学校 | 城市 | 数据年份 | 格式 | 官方来源URL |
|---|------|------|---------|------|------------|
| 1 | 中山大学 | 广州 | 2023-2025 | JSON API | https://admission.sysu.edu.cn/zsw/lnfs.html |
| 2 | 暨南大学 | 广州 | 2023-2025 | HTML 表格 | https://zsb.jnu.edu.cn/2016/1206/c3468a93231/page.htm |
| 3 | 汕头大学 | 汕头 | 2023-2025 | JSON 数据 | https://zs.stu.edu.cn/bkzn/lnfs.htm |
| 4 | 华南理工大学 | 广州 | 2023-2025 | JSON API | https://admission.scut.edu.cn/30821/list.htm |
| 5 | 华南农业大学 | 广州 | 2023-2025 | 图片表+OCR | https://zsb.scau.edu.cn/lnlqfs/list.psp |
| 6 | 广州医科大学 | 广州 | 2023-2025 | 图片表+OCR | https://zs.gzhmu.edu.cn/wnlqfs/ |
| 7 | 广东医科大学 | 湛江 | 2023-2025 | 图片表+OCR | https://zs.gdmu.edu.cn/info/1036/2717.htm |
| 8 | 广州中医药大学 | 广州 | 2023-2025 | 图片表+OCR | https://xsc.gzucm.edu.cn/bkzs1/zsxx/lnlqqk.htm |
| 9 | 广东药科大学 | 广州 | 2023-2025 | PDF/Excel | https://zsb.gdpu.edu.cn/ |
| 10 | 华南师范大学 | 广州 | 2023-2025 | PDF 文本表 | https://zsb.scnu.edu.cn/zhiyuancankao/ |
| 11 | 惠州学院 | 惠州 | 2023-2025 | 图片表+OCR | https://zs.hzu.edu.cn/4728/list.htm |
| 12 | 韩山师范学院 | 潮州 | 2023-2025 | HTML 表格 | https://zsb.hstc.edu.cn/ |
| 13 | 岭南师范学院 | 湛江 | 2023-2025 | HTML/图片表 | https://zsb.lingnan.edu.cn/zszn/wnlq.htm |
| 14 | 嘉应学院 | 梅州 | 2023-2025 | Excel 附件 | https://zs.jyu.edu.cn/ |
| 15 | 广东技术师范大学 | 广州 | 2023-2025 | API/HTML | https://bkzs.gpnu.edu.cn/ |
| 16 | 深圳大学 | 深圳 | 2024-2025* | 网页表格 | https://zs.szu.edu.cn/info/1153/2985.htm |
| 17 | 广东财经大学 | 广州 | 2023-2025 | PDF/图片表 | https://zsb.gdufe.edu.cn/11400/list.htm |
| 18 | 广州大学 | 广州 | 2023-2025 | JSON API | https://zsjy.gzhu.edu.cn/bkzn/lnfs2.htm |
| 19 | 广州航海学院 | 广州 | 2023-2025 | HTML/PDF | https://zsb.gzmtu.edu.cn/wnck.htm |
| 20 | 广东石油化工学院 | 茂名 | 2023-2025 | 结构化API | https://zs.gdupt.edu.cn/module/recruit_line.html |
| 21 | 东莞理工学院 | 东莞 | 2023-2025 | HTML 表格 | https://zsb.dgut.edu.cn/ |
| 22 | 广东工业大学 | 广州 | 2023-2025 | 图片表+OCR | https://zsb.gdut.edu.cn/xxcx/lqsj.htm |
| 23 | 广东外语外贸大学 | 广州 | 2023-2025 | JSON API | https://zsxc.gdufs.edu.cn/zsxx/zsw/lnfs.html |
| 24 | 南方医科大学 | 广州 | 2023-2025 | JSON API | https://portal.smu.edu.cn/bkzs/bkzn/wnfs.htm |
| 25 | 广东第二师范学院 | 广州 | 2023-2025 | 图片表+OCR | https://web.gdei.edu.cn/zsb/ |
| 26 | 深圳技术大学 | 深圳 | 2023-2025 | 查询接口 | https://zs.sztu.edu.cn/bkzn/lnlq1.htm |
| 27 | 五邑大学 | 江门 | 2023-2025 | GIF图片+OCR | https://www.wyu.edu.cn/zsb/ |
| 28 | **仲恺农业工程学院** | 广州 | 2023-2025 | Excel附件 | https://zsb-portal.zhku.edu.cn/details/article?id=675793 |

> *深圳大学2023年只有投档层面汇总，无专业级数据

---

## 二、聚合/API补充已导入，待官方复核 (18所) 🟣

> 以下学校已经进入正式 `admission_records.csv`。其中掌上高考公开API补充行的 `source_name` 为 `掌上高考（聚合补充）`，`notes` 包含 `聚合站来源，待官方复核`；星海音乐学院普通类艺术管理来自 Workbuddy 补充清单。后续仍应优先用学校官网/公众号原始表替换或交叉核验。

| # | 学校 | 城市 | 当前导入范围 | 数据性质 | 复核重点 |
|---|------|------|-------------|---------|---------|
| 29 | 广东海洋大学 | 湛江 | 2023-2025 物理/历史专业级；2025含官网来源 | 官网+掌上高考补充 | 2023-2024官网附件需继续争取原件 |
| 30 | 广东金融学院 | 广州 | 2023-2025 物理/历史专业级；2023-2024含官网来源 | 官网+掌上高考补充 | 2025官网/公众号分专业表需复核 |
| 31 | 肇庆学院 | 肇庆 | 2023-2025 物理/历史专业级；2023-2024含官网来源 | 官网+掌上高考补充 | 2025官方小程序/招生网需复核 |
| 32 | 韶关学院 | 韶关 | 2023-2025 物理/历史专业级 | 掌上高考补充 | 官网附件格式和原始专业表需复核 |
| 33 | 佛山大学 | 佛山 | 2023-2025 物理/历史专业级 | 掌上高考补充 | 学校官网目前主要是投档表，专业级需官方复核 |
| 34 | 南方科技大学 | 深圳 | 2025物理类本科批专业级 | 掌上高考补充 | 普通批/中外合作与综合评价招生口径需分开 |
| 35 | 广东轻工职业技术大学 | 广州 | 2024-2025物理类，2024历史类本科专业级 | 掌上高考补充 | 职业本科首招年份和本科层次口径需核验 |
| 36 | 深圳职业技术大学 | 深圳 | 2023-2025物理类，2025历史类本科专业级 | 掌上高考补充 | 2023本科合作/本科层次口径需核验 |
| 37 | 广州职业技术大学 | 广州 | 2025物理类本科专业级 | 掌上高考补充 | 2025首批本科专业和校名变更口径需核验 |
| 38 | 深圳信息职业技术大学 | 深圳 | 2025物理类本科专业级 | 掌上高考补充 | 2025首批本科专业和校名变更口径需核验 |
| 39 | 肇庆医学院 | 肇庆 | 2024-2025物理/历史本科专业级 | 掌上高考补充 | 卫生专项、专科、普通本科批需分开 |
| 40 | 深圳理工大学 | 深圳 | 2024-2025物理类本科专业级 | 掌上高考补充 | 新建院校招生专业和选科要求需复核 |
| 41 | 大湾区大学 | 东莞 | 2025物理类本科专业级 | 掌上高考补充 | 2025首年招生计划、校区和培养模式需复核 |
| 42 | 顺德职业技术大学 | 佛山 | 2025物理类本科专业级 | 掌上高考补充 | 2025首批本科专业和职业本科口径需复核 |
| 43 | 广东警官学院 | 广州 | 2023-2025普通本科批补充；2023-2025公安提前批专业级 | Workbuddy+掌上高考补充 | 公安提前批按性别/地市/选科限制，不可和普通批混用 |
| 44 | 广州体育学院 | 广州 | 2023-2025物理/历史普通类本科专业级 | 掌上高考补充 | 体育术科/艺术类不纳入普通类比较 |
| 45 | 广州美术学院 | 广州 | 2023-2025物理/历史普通类本科专业级 | 掌上高考补充 | 艺术校考/统考综合分不纳入普通类比较 |
| 46 | 星海音乐学院 | 广州 | 2023-2025物理/历史普通类艺术管理专业级 | Workbuddy补充 | 音乐类校考专业不纳入普通类比较 |

---

## 三、公安/艺术/体育类院校说明

> 当前目标覆盖全部46所，特殊类型院校已纳入采集；普通本科批可直接比较，公安提前批、术科/校考/综合分数据需单独标注。
> **详情见 `references/special-schools-inventory.md`**

| # | 学校 | 城市 | 类型 | 数据年份 | 官方URL | 说明 |
|---|------|------|------|---------|---------|------|
| 43 | 广东警官学院 | 广州 | 公安 | 2023-2025 | https://zsb.gdppla.edu.cn/ | 本科批(法学/社工/行管)+提前批(公安专业)，有完整3年专业级数据 |
| 44 | 广州体育学院 | 广州 | 体育 | 2023-2025 | https://gtzs.gzsport.edu.cn/ | 普通类本科批(体经/新闻/康复等)，仅导入非术科类专业 |
| 45 | 广州美术学院 | 广州 | 艺术 | 2023-2025 | https://zs.gzarts.edu.cn/ | 普通类本科批(建筑学/风景园林等)，仅导入非校考类专业 |
| 46 | 星海音乐学院 | 广州 | 音乐 | 2023-2025 | https://zs.xhcom.edu.cn/ | 普通类本科批(仅艺术管理1个专业) |

---

## 汇总统计

| 类别 | 数量 | 官方三年完整 | 聚合/API补充已入库 | 待官方复核 |
|------|------|-------------|------------------|-----------|
| 985/211/双一流 | 8 | 8 ✅ | 0 | 0 |
| 其他已完整官方导入 | 20 | 20 ✅ | 0 | 0 |
| 普通本科缺口补充 | 6 | 0 | 6 🟣 | 6 |
| 新升本科/新建 | 8 | 0 | 8 🟣 | 8 |
| 公安/艺术/体育类 | 4 | 0 | 4 🟣 | 4 |
| **合计** | **46** | **28** | **18** | **18** |

> 当前正式推荐数据以 `assets/source-discovery/guangdong/major_source_inventory.csv` 和 `scripts/audit_data.py` 输出为准。
> 当前正式采集目标为46所：28所已有学校官网三年完整专业级数据；其余18所已用聚合/API或Workbuddy补充数据入库，能支撑候选参考，但后续必须继续做官方来源复核。

---

## Codex 执行任务清单

> 2026-06-24更新：`scripts/import_gaokao_cn_major_scores.py` 已把下列缺口学校的掌上高考公开API本科专业线导入正式数据。以下任务清单保留为“官方来源复核/替换”清单，不再表示当前推荐数据完全缺失。

### 优先级 1：官方复核3个普通本科缺口学校

#### 1.1 韶关学院导入器
```
学校: 韶关学院
代码: 10576
来源: https://www.sgu.edu.cn/zsxxw/lnfs.htm
数据页:
  - 2025省内: https://www.sgu.edu.cn/zsxxw/info/1022/12638.htm
  - 2024省内: https://www.sgu.edu.cn/zsxxw/info/1022/11278.htm
  - 2023省内本科: https://www.sgu.edu.cn/zsxxw/info/1022/2118.htm
格式: 页面提示"请查询附件"，需下载附件确认格式(xls/pdf)
脚本名: import_sgu_major_scores.py
```

#### 1.2 佛山大学导入器
```
学校: 佛山大学 (原佛山科学技术学院)
代码: 11847
来源: https://zsb.fosu.edu.cn/?cat=91
数据页:
  - 2025广东投档: https://zsb.fosu.edu.cn/?p=9077
  - 2024广东投档: https://zsb.fosu.edu.cn/?p=8277
  - 2023广东投档: https://zsb.fosu.edu.cn/?p=7521
格式: HTML页面内嵌表格(院校专业组级别)
注意: 投档表为专业组级别，非专业级。专业级数据需额外获取。
脚本名: import_fosu_major_scores.py
```

#### 1.3 南方科技大学（特殊处理）
```
学校: 南方科技大学
代码: 14325
来源: https://zs.sustech.edu.cn/
说明: 综合评价招生为主，2025年首次开放广东普通批。
      按大类招生入学不分专业，专业级数据不适用。
处理: 仅导入2025年普通批投档线(物理类652分)，notes注明"大类招生不分专业"
数据仅1年，在推荐结果中标注风险。
```

### 优先级 2：补全3所部分导入学校

#### 2.1 广东海洋大学（补2023-2024）
```
当前: 仅2025已导入
来源: https://zsjy.gdou.edu.cn/info/1174/1606.htm
方案:
  1. 尝试直接下载2023-2024官网附件(需绕过验证码)
  2. 从广东省教育考试院公布的本科投档表提取广东海洋大学行
  3. 联系招生办获取Excel原始数据
  4. 如以上均失败，仅保留2025数据并在notes注明
```

#### 2.2 广东金融学院（补2025）
```
当前: 2023-2024已导入
来源: https://xxgk.gduf.edu.cn/xxgklm/zsksxx/lqjg.htm
方案:
  1. 检查官方信息公开网2025页面是否已更新
  2. 搜索微信公众号"广东金融学院招生办"2025年录取推送
  3. 从省考试院投档表补投档层面数据
  4. 如以上均失败，仅保留2023-2024数据
```

#### 2.3 肇庆学院（补2025）
```
当前: 2023-2024已导入
来源: https://zqu1-101.m.eduwebportal.net/
方案:
  1. 检查学校招生网/小程序2025广东分专业页面
  2. 从省考试院投档表补投档层面数据
  3. 如以上均失败，仅保留2023-2024数据
```

### 优先级 3：导入8所新升本科院校可用数据

#### 3.1 深圳职业技术大学
```
代码: 44037 (新本科代码)
来源: https://zhaosheng.szpu.edu.cn/zszn/lnlqfs.htm
数据页:
  - 2025本科: https://zhaosheng.szpu.edu.cn/info/1016/3263.htm
  - 2024本科: https://zhaosheng.szpu.edu.cn/info/1016/3112.htm
  - 2023本科(省内): https://zhaosheng.szpu.edu.cn/info/1016/2953.htm
格式: HTML表格
注意: 只导入本科层次数据，不导入专科
```

#### 3.2 肇庆医学院
```
来源: https://zhaosheng.zqmc.edu.cn/lnfs.htm
数据页:
  - 2025广东: https://zhaosheng.zqmc.edu.cn/info/1213/1992.htm
  - 2024本科批: https://zhaosheng.zqmc.edu.cn/info/1213/1864.htm
格式: HTML页面
注意: 只导入本科层次数据，不导入专科/卫生定向
```

#### 3.3 顺德职业技术大学
```
来源: https://zs.sdpt.edu.cn/ug/lnfs.htm
数据页:
  - 2025本科: https://zs.sdpt.edu.cn/ug/info/1064/2203.htm
格式: HTML页面
注意: 2025年首招本科，仅1年数据
```

#### 3.4 其余5所（广州职业技术大学/深圳信息职业技术大学/广东轻工职业技术大学/深圳理工大学/大湾区大学）
```
均为2024-2025年新设本科，数据1-2年
需逐一访问官方招生网提取本科录取分数
官方URL:
  - 广州职业技术大学: https://www.gzpyp.edu.cn/zs/
  - 深圳信息职业技术大学: https://zhaob.sziit.edu.cn/
  - 广东轻工职业技术大学: https://zs.gdip.edu.cn/
  - 深圳理工大学: https://zs.suat-sz.edu.cn/
  - 大湾区大学: https://zs.gbu.edu.cn/
```

### 优先级 4：更新 major_source_inventory.csv

导入完成后，更新 `assets/source-discovery/guangdong/major_source_inventory.csv`：
- 将已导入学校 status 改为 `imported`
- 填写 source_url 和 coverage 字段
- notes 注明数据来源和导入方式

### 优先级 5：更新 SKILL.md 和 data-collection.md

在 SKILL.md 的 Resources 部分添加新导入器条目：
```
- Use `scripts/import_sgu_major_scores.py` to import 韶关学院...
- Use `scripts/import_fosu_major_scores.py` to import 佛山大学...
```

在 data-collection.md 的 Guangdong Pilot Sources 部分更新已导入学校列表。

### 优先级 7：导入4所公安/艺术/体育类院校（普通类专业部分）

> **详情见 `references/special-schools-inventory.md`**

#### 7.1 广东警官学院
```
代码: 11110
来源: https://zsb.gdppla.edu.cn/
数据页:
  - 2025本科批: https://zsb.gdppla.edu.cn/info/1002/1839.htm
  - 2025提前批: https://zsb.gdppla.edu.cn/info/1002/1819.htm
  - 2024本科批: https://zsb.gdppla.edu.cn/info/1005/1579.htm
  - 2023数据: 可用聚合站dxsbb补充，source_name/source_url保留聚合站，notes标注待官方复核
格式: HTML表格(含专业组/专业/最高分/最低分/最低排位/平均分)
plan_type: 本科批→"普通类", 提前批→"公安提前批"
注意: 提前批按地市+性别分设专业组，男女生分数线差异大，不可合并
脚本名: import_gdppla_major_scores.py
```

#### 7.2 广州体育学院
```
代码: 10585
来源: https://gtzs.gzsport.edu.cn/node/199
补充: 可用聚合站hfplg补充投档层面数据，source_name/source_url保留聚合站，notes标注待官方复核
格式: HTML表格
plan_type: "普通类"（仅导入非体育术科类专业）
不导入: 体育教育/运动训练等需术科考试的专业
脚本名: import_gzsport_major_scores.py
```

#### 7.3 广州美术学院
```
代码: 11841
来源: https://zs.gzarts.edu.cn/
补充: 可用聚合站gk100补充投档层面数据，source_name/source_url保留聚合站，notes标注待官方复核
格式: HTML页面
plan_type: "普通类"（仅导入非艺术校考类专业）
不导入: 美术/设计类校考专业
注意: 普通类招生专业少(建筑学/风景园林等)，数据量小
脚本名: import_gzarts_major_scores.py
```

#### 7.4 星海音乐学院
```
代码: 10587
来源: https://zs.xhcom.edu.cn/index/lnfsx.htm
格式: HTML页面
plan_type: "普通类"
仅导入: 艺术管理(普通类)1个专业3年数据
不导入: 音乐类校考专业
注意: 普通类仅1个专业，数据量极小
脚本名: import_xhcom_major_scores.py
```

### 优先级 8：运行审计

```bash
# 导入完成后运行审计
python3 scripts/audit_data.py --data-dir assets/pilot-data/guangdong-physics --target-years 2023,2024,2025
python3 scripts/audit_data.py --data-dir assets/pilot-data/guangdong-history --target-years 2023,2024,2025

# 补齐缺失位次
python3 scripts/fill_admission_ranks_from_score.py --data-dir assets/pilot-data/guangdong-physics --province 广东 --track 物理类
python3 scripts/fill_admission_ranks_from_score.py --data-dir assets/pilot-data/guangdong-history --province 广东 --track 历史类
```

---

## 数据完整性目标

| 目标 | 当前状态 | 目标状态 |
|------|---------|---------|
| 广东46所公办本科覆盖 | 46所均已有本科层次专业级或专业组级数据入库 | **46所全部完成官方来源复核** |
| 学校官网三年完整数据(2023-2025) | 28所 | 逐步替换18所聚合/API补充源 |
| 聚合/API补充已入库 | 18所 | 保留来源标注，优先用官网原始表复核 |
| 新升本科/新建 | 8所已按实际本科招生年份导入 | 持续补2026及以后年份 |
| 仍需官方复核 | 18所 | 0所 |
| 物理类总记录数 | 16634 | 后续随官方复核替换，不追求无来源膨胀 |
| 历史类总记录数 | 7684 | 后续随官方复核替换，不追求无来源膨胀 |
