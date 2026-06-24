# Data Collection

Use this file when turning the demo Skill into real 2026志愿参考 coverage.

## Collection Order

1. Pick one province and track first. Do not attempt national coverage before one province is clean end to end.
2. Collect 2023, 2024, and 2025 historical data:
   - one-score-one-rank table (`rank_table.csv`)
   - school or school-major-group投档/录取 cutoff (`admission_records.csv`)
   - source URL and source name for every row
3. Register each official article and attachment in `assets/data/collection_manifest.csv` before importing. Use `status=discovered` for located official attachments and `status=needs_discovery` for missing official artifacts.
4. Collect 2026 current-year context:
   - provincial招生工作通知 and录取办法
   - current一分一段表 after scores are released
   -招生计划,专业组,选科要求,学费,校区
5. Normalize data according to `data-schema.md`.
6. Use `scripts/normalize_data.py` for CSV/XLSX source tables:

```bash
python3 scripts/normalize_data.py --kind admission --input raw_admission.csv --year 2025 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url SOURCE_URL --dry-run
python3 scripts/normalize_data.py --kind admission --input raw_admission.csv --year 2025 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url SOURCE_URL --append
python3 scripts/normalize_data.py --kind rank --input raw_rank.csv --year 2025 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url SOURCE_URL --append
```

7. Run `scripts/audit_data.py --target-years 2023,2024,2025`.
8. Run recommendations only after the audit clearly reports no demo rows and no missing required years for the target province/track.

## Import Mapping

`normalize_data.py` auto-detects common Chinese headers such as `院校名称`, `专业组代码`, `投档最低分`, `投档最低排位`, `分数`, `本段人数`, and `累计人数`.

For unusual source headers, pass explicit mappings:

```bash
python3 scripts/normalize_data.py --kind admission --input raw.csv --mapping school_name=学校 --mapping min_score=最低投档分 --mapping min_rank=最低排位 --year 2025 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url SOURCE_URL --dry-run
```

For Excel files, use the bundled Python runtime if the system Python cannot import `openpyxl`, or save the file as CSV first. For old `.xls` files that cannot be read by `openpyxl`, convert them to CSV first with a spreadsheet engine such as LibreOffice/soffice, then run `normalize_data.py`.
Use `--header-row` when a title row appears above the real table header. Empty or duplicate headers are exposed as `column_1`, `column_2`, or suffixed names such as `本段人数_2`, so wide score-band tables can still be mapped explicitly.
Use `--split-school-prefix` and `--strip-major-code-prefix` for values such as `A001北京大学` and `17文科试验班类`.
Use `scripts/html_table_to_csv.py` first when an official page embeds an Excel-like HTML table, then run `normalize_data.py` on the raw CSV:

```bash
python3 scripts/html_table_to_csv.py --input official.html --output raw.csv
python3 scripts/normalize_data.py --kind admission --input raw.csv --header-row 1 --year 2025 --province 北京 --track 普通类 --mapping school_code=院校 --mapping school_name=院校_2 --mapping major_group=专业组 --mapping major_name=专业组_2 --mapping min_score=总分 --append
```

When an official admission table gives最低位次 but not最低分, import the rows first, then fill missing scores from the same-year score-band table:

```bash
python3 scripts/fill_admission_scores_from_rank.py --data-dir assets/pilot-data/shandong-ordinary --province 山东 --track 普通类
```

This helper only fills blank `min_score` values; it does not overwrite official score values.

When an official admission table gives最低分 but not最低位次, import the rows first, then fill missing ranks from the same-year score-band table:

```bash
python3 scripts/fill_admission_ranks_from_score.py --data-dir assets/pilot-data/beijing-ordinary --province 北京 --track 普通类
```

This helper only fills blank `min_rank` values; it does not overwrite official rank values.

For official school-site major-level score queries, keep the source separate from provincial投档线 and preserve the official school source in every row. Guangdong currently has dedicated importers for 中山大学、华南理工大学、暨南大学、深圳大学、南方医科大学、广州大学、华南师范大学、广东金融学院、广东财经大学、广东工业大学、广东外语外贸大学、广东医科大学、广州医科大学、汕头大学、东莞理工学院、广东海洋大学、五邑大学、华南农业大学、惠州学院、广东第二师范学院、广州航海学院、广东石油化工学院、广东技术师范大学、深圳技术大学、广州中医药大学、广东药科大学、岭南师范学院、韩山师范学院、肇庆学院、嘉应学院:

```bash
python3 scripts/import_scut_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --source-track '理工/物理类' --replace-existing
python3 scripts/import_scut_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --source-track '文史/历史类' --replace-existing
python3 scripts/import_jnu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_jnu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_szu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_szu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_smu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_smu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gzhu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gzhu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_scnu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_scnu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gduf_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gduf_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gdufe_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gdufe_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gdut_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gdut_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gdufs_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gdufs_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_sysu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_sysu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gdmu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gdmu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gzhmu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gzhmu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_stu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_stu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_dgut_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_dgut_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gdou_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gdou_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_wyu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_wyu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_scau_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_scau_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_hzu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_hzu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gdei_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gdei_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gzmtu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gzmtu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_gdupt_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_gdupt_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gpnu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gpnu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/import_sztu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
python3 scripts/import_sztu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gzucm_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gzucm_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gdpu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_gdpu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_lingnan_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_lingnan_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_hstc_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_hstc_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_zqu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_zqu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_jyu_major_scores.py --data-dir assets/pilot-data/guangdong-physics --track 物理类 --replace-existing
/Users/xueweixun/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/import_jyu_major_scores.py --data-dir assets/pilot-data/guangdong-history --track 历史类 --replace-existing
python3 scripts/fill_admission_ranks_from_score.py --data-dir assets/pilot-data/guangdong-physics --province 广东 --track 物理类
python3 scripts/fill_admission_ranks_from_score.py --data-dir assets/pilot-data/guangdong-history --province 广东 --track 历史类
```

School-site rows with `major_name` are more precise than province-level院校专业组 rows for热门专业判断, but they cover only that school and must not be described as province-wide major coverage.
The Guangdong public-undergraduate target scope from `https://www.dxsbb.com/news/51305.html` is stored in `assets/source-discovery/guangdong/target_public_undergraduate_schools_2026.csv`; use it as a coverage checklist only. Admission-score rows still require official school or provincial sources. Do not expand the scope to ordinary专科院校; for new职业技术大学 entries, import only本科层次 admission rows after official verification.

For official PDF tables, use:

```bash
python3 scripts/pdf_table_to_csv.py --input official.pdf --kind admission --year 2025 --province 广东 --track 物理类 --batch 本科批 --source-name 广东省教育考试院 --source-url SOURCE_URL --dry-run
python3 scripts/pdf_table_to_csv.py --input official.pdf --kind admission --data-dir assets/pilot-data/guangdong-physics --year 2025 --province 广东 --track 物理类 --batch 本科批 --source-name 广东省教育考试院 --source-url SOURCE_URL
```

Use the bundled Python runtime if the system Python cannot import `pdfplumber`.
Some one-score-one-rank PDFs use a top score label such as `693↑`. The PDF importer treats that row as score 693 and above, sets `min_rank=1`, and uses the cumulative count as `same_score_count`.

For clear image-only official score-band PDFs with one regular table containing `分数 / 人数 / 累计人数`, use the grid/template OCR importer. It detects the table grid, learns digit templates from the known descending score column, and validates cumulative counts:

```bash
python3 scripts/ocr_grid_rank_pdf.py --input scanned-grid.pdf --pages 1-4 --first-score 623 --last-score 402 --year 2025 --province 上海 --track 普通类 --source-name 上海市教育考试院 --source-url SOURCE_URL --strict-ocr-warnings --dry-run
python3 scripts/ocr_grid_rank_pdf.py --input scanned-grid.pdf --pages 1-4 --first-score 623 --last-score 402 --year 2025 --province 上海 --track 普通类 --source-name 上海市教育考试院 --source-url SOURCE_URL --strict-ocr-warnings --data-dir assets/pilot-data/shanghai-ordinary --append
```

Only promote this output into `assets/pilot-data` when the importer reports zero errors and no OCR warnings under `--strict-ocr-warnings`.

For scanned official rank PDFs on macOS, use the Vision OCR importer after confirming page ranges and score ranges:

```bash
python3 scripts/ocr_scanned_rank_pdf_macos.py --input scanned.pdf --pages 15-28 --first-score 700 --last-score 100 --year 2023 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url SOURCE_URL --dry-run
python3 scripts/ocr_scanned_rank_pdf_macos.py --input scanned.pdf --pages 15-28 --first-score 700 --last-score 100 --year 2023 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url SOURCE_URL --data-dir assets/pilot-data/guangdong-physics --append
```

This importer derives `same_score_count` from consecutive cumulative ranks and uses cell OCR only as a cross-check, because single-digit count cells are more error-prone than cumulative rank cells.

For official image-only rank tables, use the image OCR importer in dry-run mode first:

```bash
python3 scripts/ocr_rank_image_macos.py --input rank.jpg --score-ranges 683-644,643-604,603-564 --year 2025 --province 江苏 --track 物理类 --source-name 江苏省教育考试院 --source-url SOURCE_URL --dry-run
```

Do not write image OCR output into a real pilot directory until the row count, score range, cumulative ranks, and warnings have been checked against the image.

For scanned official rank PDFs that publish one score column with two side-by-side tracks, use the dual-track OCR importer one side at a time:

```bash
python3 scripts/ocr_dual_track_rank_pdf_macos.py --input scanned.pdf --pages 1-18 --side left --first-score 693 --last-score 140 --year 2025 --province 河北 --track 物理科目组合 --source-name 河北省教育考试院 --source-url SOURCE_URL --dry-run
python3 scripts/ocr_dual_track_rank_pdf_macos.py --input scanned.pdf --pages 1-18 --side right --first-score 693 --last-score 140 --year 2025 --province 河北 --track 历史科目组合 --source-name 河北省教育考试院 --source-url SOURCE_URL --dry-run
```

Do not promote a dual-track OCR draft into `assets/pilot-data` until high-score and watermark-heavy rows have been spot-checked against the rendered PDF image.

## Source Priority

Prefer official sources in this order:

1. Provincial education examination authority for省内 rules,一分一段,批次线,投档情况.
2. Official university admission office for major-level admissions and招生章程.
3. Ministry of Education / 阳光高考 for admissions policy,招生章程,选科 and official national entry points.
4. Aggregators only to discover candidate URLs; do not mark rows verified from aggregators alone.

## Guangdong Pilot Sources

These are verified entry points for the first pilot province. Keep exact row-level source URLs in CSV rows after importing real data.

- 广东省教育考试院 homepage: `https://eea.gd.gov.cn/`
- 广东省 2026 年普通高考成绩发布通知: `https://eea.gd.gov.cn/ptgk/content/post_4914634.html`
- 广东省 2026 年普通高校招生工作通知: `https://eea.gd.gov.cn/ptgk/content/post_4896195.html`
- 广东 2027 年起拟在粤招生本专科专业选考科目要求: `https://www.eeagd.edu.cn/xkcx2027/`
- 教育部阳光高考信息平台: `https://gaokao.chsi.com.cn/`

Pilot historical source status is tracked in each pilot directory's `collection_manifest.csv`. Guangdong school-site major-source progress is tracked in `assets/source-discovery/guangdong/major_source_inventory.csv`.

The current pilot data directories are `assets/pilot-data/guangdong-physics` and `assets/pilot-data/guangdong-history`. They contain real 2023, 2024, and 2025 Guangdong本科普通类投档数据, plus 2023, 2024, and 2025 ordinary score-segment rank data for the matching track imported from official PDFs/ZIP attachments. They also include official school-site major-level admission rows for 中山大学、华南理工大学、暨南大学、深圳大学、南方医科大学、广州大学、华南师范大学、广东金融学院、广东财经大学、广东工业大学、广东外语外贸大学、广东医科大学、广州医科大学、汕头大学、东莞理工学院、广东海洋大学、五邑大学、华南农业大学、惠州学院、广东第二师范学院、广州航海学院、广东石油化工学院、广东技术师范大学、深圳技术大学、广州中医药大学、广东药科大学、岭南师范学院、韩山师范学院、肇庆学院、嘉应学院: 5680 physics rows and 2205 history rows. 深圳大学专业级 coverage is 2024-2025 only because the official Guangdong page exposes 2023 only at投档 summary level. 广东金融学院专业级 coverage is 2023-2024 only because the 2025 official major-score page has not been located in the school information-disclosure admission-results column. 广东海洋大学专业级 coverage is 2025 only because 2023-2024 official attachments currently require captcha-gated downloads. 华南师范大学 currently imports ordinary and地方专项 PDF rows; 中外合作PDF is registered for later extension. 广东财经大学2024-2025专业级数据来自官网PDF文本表，2023来自官网图片表并经macOS Vision OCR导入。广东工业大学2023-2025专业级数据来自官网长图片表，已导入普通类、国际班、地方专项，艺术类未混入普通物理/历史推荐数据。广东医科大学2023-2025专业级数据来自官网图片表，已导入普通类。广州医科大学2023-2025专业级数据来自官网图片表，已导入普通类、地方专项。汕头大学2023-2025专业级数据来自官网JSON，已导入普通类、地方专项、卫生专项，min_rank由同年分数段表按最低分补齐。东莞理工学院2023-2025专业级数据来自官网HTML表格，已导入普通类、地方专项、粤台联合培养、中外合作。广东海洋大学2025专业级数据来自官网HTML表格，已导入普通类、地方专项、中外合作、航海类。五邑大学2023-2025专业级数据来自官网GIF图片表，经macOS Vision OCR导入；2023物理类江门市内表按官网图片手工校准，专业min_rank按同年分数段表由最低分补齐，notes保留专业组投档最低排位。华南农业大学2023-2025专业级数据来自官网近三年图片表，经OCR和表格线解析；2024-2023主要发布最低排位，min_score按同年分数段表补齐。惠州学院2023-2025专业级数据来自官网历年招生图片表，已导入本科批普通类和中外合作，不含专科。广东第二师范学院2023-2025专业级数据来自官网本科专业志愿组图片表，已导入普通物理/历史本科专业组及学分互认/协同培养，不含艺体类和专科。广州航海学院2023-2025专业级数据来自官网往年参考HTML表/PDF，已导入普通物理/历史本科专业组，包含航海类、中外合作、中外联合培养，不含美术类和专科。广东石油化工学院2023-2025专业级数据来自官网招生网历年录取分数线结构化接口，2025/2024官网详情页登记官微原文，已导入本科批普通物理/历史专业行，不含体育/艺术/专科。广东技术师范大学2023-2025专业级数据来自官网本科招生网招生专业录取情况统计接口，已导入普通类、国际班、地方专项、少数民族、教师专项、河源校区、协同培养等本科物理/历史专业行，不含艺体类和专科。深圳技术大学2023-2025专业级数据来自官网历年录取查询接口，已导入普通物理/历史本科专业行，不含艺术类、音乐类、美术类和专科。广州中医药大学2023-2025专业级数据来自官网历年录取情况页及其官方公众号本科专业录取分数线图片表，已导入普通类、卫生专项、地方专项本科物理/历史专业行，不含体育/艺术/专科；2024图片表按网格切格OCR，2023/2025图片表经macOS Vision OCR导入。广东药科大学2023-2025专业级数据来自学校招生办官方PDF/Excel附件，已导入普通类、国际班和卫生专项本科专业行；附件下载需验证码，原件缓存于`assets/raw-cache/gdpu`，不含专科。岭南师范学院2023-2025专业级数据来自官网往年录取栏目，2025为HTML表，2024/2023为官网图片表经表格线切格和macOS Vision OCR导入，已导入普通类、教师专项、协同培养、中外合作本科专业行，剔除体育/艺术类和专科；2024历史类市场营销最低排位按官网图校准为33688。韩山师范学院2023-2025专业级数据来自官网HTML表格缓存，已导入本科批普通类、协同培养、中外合作及2023/2025教师专项，剔除专科、3+证书和高水平运动队；2024教师专项统计表未在官网最新消息全分页标题中定位。肇庆学院2023-2024专业级数据来自学校官方历年分数小程序图片表，已导入广东本科批普通物理/历史专业行；2024部分OCR缺排位行按官网图人工校准；2025官方广东分专业录取分数未定位，暂记为部分导入。嘉应学院2023-2025专业级数据来自学校官网历年录取情况栏目Excel附件，已导入普通类、教师专项、卫生专项、协同培养、中外合作本科物理/历史专业行，剔除体育/音乐/美术/舞蹈等艺体类和专科。中山大学、广东外语外贸大学2023-2025专业级数据来自官网招生系统JSON接口。The 2023 rank tables and 广东金融学院/广东财经大学/广东工业大学/广东医科大学/广州医科大学/五邑大学/华南农业大学/惠州学院/广东第二师范学院/广州中医药大学/岭南师范学院/肇庆学院 image tables came from official image-only material and were imported with macOS Vision OCR or grid OCR, so keep OCR warnings and spot checks with the import log when using them for real counseling.

## Zhejiang Pilot Sources

Zhejiang ordinary-category data is tracked in `assets/pilot-data/zhejiang-ordinary`.

- 浙江省教育考试院 homepage: `https://www.zjzs.net/`
- 浙江省2025年普通高校招生成绩分数段表（总分）: `https://www.zjzs.net/art/2025/6/25/art_45_11373.html`
- 浙江省2024年普通高校招生成绩分数段表（总分）: `https://www.zjzs.net/art/2024/6/26/art_45_9753.html`
- 浙江省2023年普通高校招生成绩分数段表(总分): `https://www.zjzs.net/art/2023/6/26/art_45_6936.html`
- 浙江省2025年普通高校招生普通类第一段平行投档分数线表: `https://www.zjzs.net/art/2025/7/21/art_45_11467.html`
- 浙江省2024年普通高校招生普通类第一段平行投档分数线表: `https://www.zjzs.net/art/2024/7/21/art_45_9899.html`
- 浙江省2023年普通高校招生普通类第一段平行投档分数线表: `https://www.zjzs.net/art/2023/7/19/art_45_2052.html`
- 2023年至2025年浙江省普通高校招生投档及专业录取情况: `https://www.zjzs.net/art/2026/6/22/art_45_12416.html`

The current Zhejiang pilot imports the 2023, 2024, and 2025 ordinary-category score-segment rank PDFs plus the ordinary first-segment parallel投档 `.xls` files. The 2026-06-22 three-year professional录取 PDFs are registered as discovered source artifacts for later deeper validation.

## Shandong Pilot Sources

Shandong ordinary-category data is tracked in `assets/pilot-data/shandong-ordinary`.

- 山东省教育招生考试院 homepage: `https://www.sdzk.cn/`
- 2025年夏季高考文化成绩一分一段表: `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6943`
- 2024年夏季高考文化成绩一分一段表: `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6577`
- 2023年夏季高考文化成绩一分一段表: `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6212`
- 山东省2025年普通类常规批第1次志愿投档情况表: `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6996`
- 山东省2024年普通类常规批第1次志愿投档情况表: `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6656`
- 山东省2023年普通类常规批第1次志愿投档情况表: `https://www.sdzk.cn/NewsInfo.aspx?NewsID=6279`

The current Shandong pilot imports the ordinary全体 score-band columns from the three cultural-score score-band `.xls` files and the ordinary regular-batch first-volunteer投档 `.xls` files. The投档 tables publish最低位次 but not最低分, so blank `min_score` values are filled from the same-year rank bands when the cutoff rank falls inside the public score-band table.

## Beijing Pilot Sources

Beijing ordinary-category data is tracked in `assets/pilot-data/beijing-ordinary`.

- 北京教育考试院 homepage: `https://www.bjeea.cn/`
- 北京教育考试院高考高招栏目: `https://www.bjeea.cn/html/gkgz/index.html`
- 2025年高招相关统计资料: `https://www.bjeea.cn/html/gkgz/tzgg/2026/0617/88221.html`
- 北京市2025年高考考生分数分布: `https://www.bjeea.cn/html/gkgz/tzgg/2025/0625/87165.html`
- 北京市2024年高考考生分数分布: `http://www.bjeea.cn/html/gkgz/fujian/2024/0625/85432.html`
- 2023年北京市高考考生分数分布: `http://www.bjeea.cn/html/gkgz/fujian/2023/0625/83922.html`
- 2025年北京市高招本科普通批录取投档线: `https://www.bjeea.cn/html/gkgz/tzgg/2025/0720/87252.html`
- 2024年北京市高招本科普通批录取投档线: `https://www.bjeea.cn/html/gkgz/tzgg/2024/0720/85632.html`
- 2023年北京市高招本科普通批录取投档线: `https://www.bjeea.cn/html/gkgz/tzgg/2023/0717/84120.html`

The current Beijing pilot imports 2023, 2024, and 2025 ordinary high-score distribution tables plus本科普通批投档线. The投档 tables publish最低分 but not最低位次, so blank `min_rank` values are filled from the same-year score distribution by cutoff score.

## Shanghai Pilot Sources

Shanghai ordinary-category data is tracked in `assets/pilot-data/shanghai-ordinary`.

- 上海市教育考试院 homepage: `https://www.shmeea.edu.cn/`
- 上海市教育考试院高考高招栏目: `https://www.shmeea.edu.cn/page/08000/index.html`
- 上海市2025年普通高校招生本科阶段考生各类别成绩分布表: `https://www.shmeea.edu.cn/page/08000/20250623/19547.html`
- 2024年考生高考各类别成绩分布表: `https://www.shmeea.edu.cn/page/08000/20240623/18609.html`
- 2023年考生高考各类别成绩分布表: `https://www.shmeea.edu.cn/page/08000/20230623/17660.html`
- 上海市2025年普通高校招生本科普通批次平行志愿院校专业组投档分数线: `https://www.shmeea.edu.cn/download/20250719/186.pdf`
- 上海市2025年普通高校招生本科普通批次平行志愿院校Q组及部分中外合作办学院校专业组投档分数线: `https://www.shmeea.edu.cn/download/20250719/185.pdf`
- 2024年上海市普通高校招生本科普通批次平行志愿院校专业组投档分数线: `https://www.shmeea.edu.cn/download/20240719/198.pdf`
- 2024年上海市普通高校招生本科普通批次平行志愿院校Q组投档分数线: `https://www.shmeea.edu.cn/download/20240719/197.pdf`
- 2023年上海市普通高校招生本科普通批次平行志愿院校专业组投档分数线: `https://www.shmeea.edu.cn/download/20230721/11115.pdf`
- 2023年上海市普通高校招生本科普通批次平行志愿院校Q组投档分数线: `https://www.shmeea.edu.cn/download/20230721/1114.pdf`

The current Shanghai pilot imports 2023, 2024, and 2025 ordinary score distribution tables plus本科普通批平行志愿院校专业组投档线. The 2025 score distribution PDF is image-only and was imported with `ocr_grid_rank_pdf.py` in strict warning mode. The投档 tables publish最低分 but not最低位次, so blank `min_rank` values are filled from the same-year score distribution by cutoff score. Rows from Q组 and部分中外合作办学 PDFs are preserved with `plan_type=Q组/中外合作`.

## Jiangsu Source Discovery

Jiangsu source discovery is tracked in `assets/source-discovery/jiangsu`. It is not yet a usable pilot data directory.

- 江苏省教育考试院 homepage: `https://www.jseea.cn/`
- 江苏省2025年普通高考第一阶段逐分段统计表: `https://www.jseea.cn/webfile/index/index_zkxx/2025-06-24/7343234265133355008.html`
- 江苏省2024年普通高考逐分段统计表（第一阶段）: `https://www.jseea.cn/webfile/index/index_zkxx/2024-06-24/7210960924591525888.html`
- 江苏省2025年普通高校招生普通类本科批次平行志愿投档线（物理等科目类）: `https://www.jseea.cn/webfile/index/index_zkxx/2025-07-18/7351781448019349504.html`
- 江苏省2025年普通高校招生普通类本科批次平行志愿投档线（历史等科目类）: `https://www.jseea.cn/webfile/index/index_zkxx/2025-07-18/7351781284785426432.html`
- 江苏省2024年普通类本科批次平行志愿投档线: `https://www.jseea.cn/webfile/index/index_zkxx/2024-07-18/7219509116052443136.html`
- 江苏省2023年普通类本科批次平行志愿投档线: `https://www.jseea.cn/webfile/index/index_zkxx/2023-07-18/7086888854866628608.html`

Current Jiangsu blocker: 2023 first-stage ordinary逐分段统计表 has not been located in the official site pages checked so far. The 2023 second-stage逐分段 page exists, but it should not be used as a replacement for本科批 historical recommendations without further verification.

## Hebei Source Discovery

Hebei source discovery is tracked in `assets/source-discovery/hebei`. It is not yet a usable pilot data directory.

- 河北省教育考试院 homepage: `https://www.hebeea.edu.cn/`
- 河北省教育考试院普通高考往年数据: `https://www.hebeea.edu.cn/ptgk/wnsj/`
- 2025年河北省普通高校招生各类考生成绩统计表: `https://www.hebeea.edu.cn/c/2025-06-24/488903.html`
- 2024年河北省普通高校招生各类考生成绩统计表: `https://www.hebeea.edu.cn/c/2024-06-24/489444.html`
- 2023年河北省普通高校招生各类考生成绩统计表: `https://www.hebeea.edu.cn/c/2023-06-24/488564.html`
- 2025年河北省本科批平行志愿投档情况统计: `https://www.hebeea.edu.cn/c/2025-07-23/489213.html`
- 2024年河北省本科批平行志愿投档情况统计: `https://www.hebeea.edu.cn/c/2024-07-22/489446.html`
- 2023年河北省本科批平行志愿投档情况统计: `https://www.hebeea.edu.cn/c/2023-07-25/489286.html`

Current Hebei blocker: the official score statistics PDFs are scanned image tables with red watermarks. `rank_table_ocr_draft.csv` has been generated, but OCR warnings showed concrete high-score errors such as a 2024 history cumulative value `66` being read as `99`. Keep Hebei out of `assets/pilot-data` until the OCR draft is manually spot-checked or replaced by a more deterministic importer.

## Normalization Warnings

- New Gaokao provinces often publish投档 by院校专业组. Preserve `major_group`; school-only matching can be misleading.
- Do not merge普通类,中外合作,专项计划,民族班,预科班,艺术体育 rows.
- Treat征集志愿 rows separately or mark them in `notes`; they can distort normal志愿 recommendations.
- If a province changes志愿模式,批次 structure, or选科 requirements, keep the historical rows but state the comparability risk in output.
