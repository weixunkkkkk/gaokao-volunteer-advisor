# Data Schema

Use UTF-8 CSV files. Keep raw source files separately when possible, then normalize into the schemas below. Never mix different provinces or subject tracks without explicit `province` and `track` values.

## Required Files

### admission_records.csv

One row is one historical school or school-major-group admission cutoff.

Required columns:

- `year`: admission year, such as `2025`
- `province`: candidate province, such as `广东`
- `track`: subject type, such as `物理类`, `历史类`, `理科`, `文科`
- `batch`: admission batch, such as `本科批`
- `school_name`
- `school_code`
- `major_group`: school major group, professional group, or blank when not applicable
- `major_name`: major or major category if the source is major-level; blank for school-level cutoffs
- `plan_type`: 普通类, 中外合作, 地方专项, 艺术类, etc.
- `min_score`: lowest admitted or投档 score
- `min_rank`: lowest admitted or投档 rank/位次. Smaller number means stronger rank.
- `admit_count`: admitted count or plan count when available
- `source_url`: original source URL. Prefer official or school sources; if a reputable aggregator is used as a fallback, keep the aggregator URL here.
- `source_name`: source label
- `notes`: caveats, such as 征集志愿, 首年招生, 专业组调整, 聚合站来源/待官方复核

### rank_table.csv

One row is one score band from a province's one-score-one-rank table.

Required columns:

- `year`
- `province`
- `track`
- `score`
- `min_rank`: best rank in this score band
- `max_rank`: conservative/worst rank in this score band
- `same_score_count`
- `source_url`
- `source_name`

### majors.csv

One row is one major suggestion.

Required columns:

- `interest_keywords`: pipe-separated terms, such as `AI|人工智能|计算机|编程`
- `major_name`
- `degree_category`: 工学, 医学, 管理学, 文学, etc.
- `employment_outlook`: concise outlook statement
- `typical_roles`: common roles or industries
- `fit_notes`: what kind of student fits
- `risk_notes`: workload, credential, market, or policy risks

### source_registry.csv

One row is one source entry point or verified policy page. This file does not replace row-level source URLs in `admission_records.csv` or `rank_table.csv`; it helps track where future imports should be collected from.

Required columns:

- `province`: province or `全国`
- `source_type`: `homepage`, `rank_table`, `admission_cutoff`, `policy_2026`, `subject_requirements`, `official_platform`, etc.
- `source_name`
- `url`
- `verified_date`: date when the URL was last checked
- `notes`: collection or reliability notes

### collection_manifest.csv

One row is one source artifact that still needs to be downloaded, parsed, imported, or audited.

Required columns:

- `province`
- `year`
- `dataset`: `rank_table`, `admission_cutoff`, `policy`, `subject_requirements`, etc.
- `track`: `物理类`, `历史类`, `理科`, `文科`, or blank when the artifact covers multiple tracks
- `article_title`
- `article_url`: official article page
- `attachment_url`: direct official attachment URL when known
- `file_type`: `csv`, `xlsx`, `pdf`, `zip`, `html`, etc.
- `status`: `discovered`, `downloaded`, `parsed`, `imported`, `imported_pilot`, `audited`, `needs_discovery`, `needs_ocr`
- `importer`: suggested processing method, such as `normalize_data`, `manual_zip_then_normalize`, or `pdf_table_then_normalize`
- `notes`

## Source Priority

Use the highest-confidence available source:

1. Provincial education examination authority: one-score-one-rank tables, control lines, batch rules.
2. Official university admission office: major-level admission cutoffs and招生章程.
3. Ministry/official platforms and published admissions plans.
4. Reputable aggregators can be used as fallback admission-score sources when official pages are unavailable, captcha-gated, removed, or incomplete. Mark every such row clearly in `source_name` or `notes` as `聚合站` / `待官方复核`.

## Normalization Rules

- Preserve the original source URL and source name on every row.
- Do not combine score-only and rank-based data silently. If `min_rank` is unavailable, leave it blank and make the output say score-only.
- Mark demo rows with `source_name=DEMO_NOT_REAL`. Mark aggregator fallback rows with a real aggregator `source_name` and add `notes=聚合站来源，待官方复核` rather than pretending they are official.
- Split ordinary,中外合作,专项计划,艺术体育,民族班,预科班 into separate `plan_type` values.
- For new Gaokao provinces, keep `major_group`; school-level recommendations without group constraints are often too coarse.
- For 2026 advice, treat 2023-2025 as historical data and separately check 2026招生计划 and选科要求.

## Coverage Audit

Run this after every import:

```bash
python3 scripts/audit_data.py --data-dir assets/data --target-years 2023,2024,2025
```

Use `--strict` in automation. It exits non-zero when required CSV files, required columns, target years, row sources, or demo-data cleanup are not ready for real recommendations.

## Normalized Import

Use `scripts/normalize_data.py` to convert a raw official table into one of the required CSV files:

```bash
python3 scripts/normalize_data.py --kind admission --input raw.csv --year 2025 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url SOURCE_URL --dry-run
python3 scripts/normalize_data.py --kind admission --input raw.csv --year 2025 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url SOURCE_URL --append
```

Use `--mapping target=source_header` for non-standard headers and `--const target=value` for fixed values. Prefer `--dry-run` until the preview rows are correct.

Use `scripts/pdf_table_to_csv.py` for official PDF tables. It uses `pdfplumber`, so run it with a Python environment that has PDF table extraction support.
