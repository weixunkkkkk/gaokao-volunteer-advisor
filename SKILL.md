---
name: gaokao-volunteer-advisor
description: Build and run a Gaokao college-application advisor for Chinese candidates. Use when the user wants 2026 高考志愿参考, school recommendations from province/track/score/rank, 冲稳保垫志愿方案, admission-risk assessment, past-three-year admission cutoff comparison, one-score-one-rank handling, major recommendations from interests, professional admission-score analysis, or employment-outlook guidance for majors.
---

# Gaokao Volunteer Advisor

## Core Rule

Treat every recommendation as a reference, not a guarantee. Prefer rank/位次 over raw score, report data coverage, cite source fields when available, and say clearly when the bundled data is incomplete or sample-only.

For 2026 candidates, use 2023, 2024, and 2025 admission/cutoff data as the normal three-year historical baseline. If the user asks during 2026 filing, also verify current-year provincial rules, batch settings, elective-subject constraints, and招生计划 before giving concrete advice.

Use two service depths:

- **Quick reference**: province, track, score/rank, and interests are enough. State missing assumptions clearly.
- **Formal志愿方案**: collect region, school type, tuition, public/private/中外合作 tolerance, whether服从调剂, body/单科/外语 restrictions, and career direction before finalizing a table.

## Workflow

1. Collect minimum inputs:
   - Province, such as `广东`
   - Gaokao year, especially whether the user needs 2026 planning
   - Track or subject type, such as `物理类`, `历史类`, `理科`, `文科`, or a province-specific category
   - Score and rank. If rank is missing, estimate it from a one-score-one-rank table only when the local data contains that table.
   - Interests or fields, such as `人工智能`, `医学`, `新能源`, `财经`, `传媒`
2. Check data coverage in `assets/data` or the user-provided data directory. Do not imply national coverage unless the CSVs actually contain it.
3. If importing raw official CSV/XLSX tables, normalize them first:

```bash
python3 scripts/normalize_data.py --kind admission --input raw.csv --year 2025 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url https://example.gov.cn --append
python3 scripts/normalize_data.py --kind rank --input rank.csv --year 2025 --province 广东 --track 物理类 --source-name 广东省教育考试院 --source-url https://example.gov.cn --append
```

For official PDF tables, use the bundled Python runtime when system Python lacks `pdfplumber`:

```bash
python3 scripts/pdf_table_to_csv.py --input table.pdf --kind admission --year 2025 --province 广东 --track 物理类 --batch 本科批 --source-name 广东省教育考试院 --source-url https://example.gov.cn --dry-run
```

Use `--dry-run` before writing when working with a new province or new table layout.

4. Run `scripts/audit_data.py` before giving real advice:

```bash
python3 scripts/audit_data.py --data-dir assets/data --target-years 2023,2024,2025
```

If the audit reports demo data, missing required years, or missing required columns, say that the current result is not ready for real志愿填报.

5. For a simple user-facing run, use `scripts/run_advisor.py`. It discovers verified pilot data directories and asks for score, rank, and interests when missing:

```bash
python3 scripts/run_advisor.py --province 上海 --score 555 --interests 人工智能,财经
python3 scripts/run_advisor.py
```

6. Run `scripts/recommend.py` directly when you need deterministic ranking with explicit data paths:

```bash
python3 scripts/recommend.py --province 广东 --track 物理类 --score 600 --rank 43000 --interests 人工智能,新能源
```

Use `--data-dir /path/to/data` when the real CSV files live outside the skill folder.

7. Interpret the output:
   - `冲`: candidate rank is slightly behind recent historical cutoff.
   - `稳`: candidate rank is close to or modestly better than recent historical cutoff.
   - `保`: candidate rank is clearly better than recent historical cutoff.
   - `险`: candidate rank is far behind historical cutoff; include only as a risk note or when the user explicitly wants aggressive options.
   - `垫`: for a formal志愿表, select from the safest `保` rows with a large rank buffer; do not confuse it with `险`.
   - If `major_name` is present, treat the row as major-level evidence. If only `major_group` is present, treat it as a school/major-group floor and say that group-internal热门专业 may be higher.
8. Recommend majors after school fit:
   - Match interests to major families.
   - Explain就业前景 in practical terms: common roles, industry demand, volatility, learning burden, and credential barriers.
   - Avoid promising salary, employment certainty, or guaranteed admissions.
9. For a formal plan, include official-confirmation reminders: provincial application system, school admission site, current招生计划,院校/专业代码,选科要求,体检限制,单科要求,学费,校区,学制, and专业录取规则.

## Resources

- Read `references/data-schema.md` before creating, cleaning, or importing admission CSV data.
- Read `references/data-collection.md` before collecting real 2023-2025 provincial data or current-year 2026 policy data.
- Read `references/advising-rules.md` before changing recommendation thresholds or writing a detailed counseling answer.
- Read `references/major-reference.md` when explaining major employment outlook, learning difficulty, green/red-card risk, or typical career paths.
- Read `references/guangdong-schools-inventory.md`, `references/special-schools-inventory.md`, and `references/supplementary-schools-data.md` when checking Guangdong public-undergraduate coverage gaps. Current Guangdong target covers all 46 public undergraduate schools, including new undergraduate vocational universities and special art/sports/public-security schools. Official sources are preferred, and reputable aggregator fallback rows may be imported only when `source_name`/`source_url` identify the aggregator and `notes` says `聚合站来源，待官方复核`.
- Read `references/national-coverage-plan.md`, `assets/source-discovery/national/province_manifest.csv`, `assets/source-discovery/national/gaokao_cn_province_id_map.csv`, and `assets/source-discovery/national/gaokao_cn_school_ids.csv` before planning national expansion beyond the current pilot provinces. These files are coverage roadmaps and import aids, not proof that every province is already usable.
- Use `scripts/normalize_data.py` to convert raw official CSV/XLSX tables into the standard CSV schema.
- Use `scripts/pdf_table_to_csv.py` to convert official PDF tables into the standard CSV schema.
- Use `scripts/html_table_to_csv.py` to convert official HTML tables into raw CSV before normalizing.
- Use `scripts/sync_major_reference.py` to sync manually curated `references/major-reference.md` rows into each data directory's `majors.csv`.
- Use `scripts/sync_major_profiles_from_admissions.py` after importing Guangdong major-score rows to backfill `majors.csv` profiles for every clean major name that appears in `admission_records.csv`; these generated rows are general major-family guidance, not a substitute for checking a school's培养方案 and就业质量报告.
- Use `scripts/export_gaokao_cn_school_ids.py` to refresh the local 掌上高考 school-ID list for nationwide API-based supplemental imports.
- Use `scripts/import_scut_major_scores.py` to import 华南理工大学 official school-site major-level scores into Guangdong pilot data.
- Use `scripts/import_jnu_major_scores.py` to import 暨南大学 official Guangdong major-level scores into Guangdong pilot data.
- Use `scripts/import_szu_major_scores.py` to import 深圳大学 official Guangdong major-level scores into Guangdong pilot data.
- Use `scripts/import_smu_major_scores.py` to import 南方医科大学 official Guangdong major-level scores into Guangdong pilot data.
- Use `scripts/import_gzhu_major_scores.py` to import 广州大学 official Guangdong major-level scores into Guangdong pilot data.
- Use `scripts/import_scnu_major_scores.py` to import 华南师范大学 official Guangdong major-level scores from official PDFs into Guangdong pilot data.
- Use `scripts/import_gduf_major_scores.py` to import 广东金融学院 official Guangdong major-level scores from school-site image tables into Guangdong pilot data.
- Use `scripts/import_gdufe_major_scores.py` to import 广东财经大学 official Guangdong major-level scores from school-site PDFs and image tables into Guangdong pilot data.
- Use `scripts/import_gdut_major_scores.py` to import 广东工业大学 official Guangdong major-level scores from school-site image tables into Guangdong pilot data.
- Use `scripts/import_gdufs_major_scores.py` to import 广东外语外贸大学 official Guangdong major-level scores from the school admission-system JSON API into Guangdong pilot data.
- Use `scripts/import_sysu_major_scores.py` to import 中山大学 official Guangdong major-level scores from the school admission-system JSON API into Guangdong pilot data.
- Use `scripts/import_gdmu_major_scores.py` to import 广东医科大学 official Guangdong major-level scores from school-site image tables into Guangdong pilot data.
- Use `scripts/import_gzhmu_major_scores.py` to import 广州医科大学 official Guangdong major-level scores from school-site image tables into Guangdong pilot data.
- Use `scripts/import_stu_major_scores.py` to import 汕头大学 official Guangdong major-level scores from school-site JSON into Guangdong pilot data.
- Use `scripts/import_dgut_major_scores.py` to import 东莞理工学院 official Guangdong major-level scores from school-site HTML tables into Guangdong pilot data.
- Use `scripts/import_gdou_major_scores.py` to import 广东海洋大学 official 2025 Guangdong major-level scores from the school-site HTML table into Guangdong pilot data.
- Use `scripts/import_wyu_major_scores.py` to import 五邑大学 official Guangdong major-level scores from school-site GIF image tables into Guangdong pilot data.
- Use `scripts/import_scau_major_scores.py` with the bundled Python runtime to import 华南农业大学 official Guangdong major-level scores from school-site image tables into Guangdong pilot data.
- Use `scripts/import_hzu_major_scores.py` with the bundled Python runtime to import 惠州学院 official Guangdong undergraduate major-level scores from school-site image tables into Guangdong pilot data.
- Use `scripts/import_gdei_major_scores.py` with the bundled Python runtime to import 广东第二师范学院 official Guangdong undergraduate major-level scores from school-site image tables into Guangdong pilot data.
- Use `scripts/import_gzmtu_major_scores.py` with the bundled Python runtime to import 广州航海学院 official Guangdong undergraduate major-level scores from school-site HTML/PDF tables into Guangdong pilot data.
- Use `scripts/import_gdupt_major_scores.py` to import 广东石油化工学院 official Guangdong undergraduate major-level scores from the school admission-site structured API into Guangdong pilot data.
- Use `scripts/import_gpnu_major_scores.py` with the bundled Python runtime to import 广东技术师范大学 official Guangdong undergraduate major-level scores from the school admission-site API/HTML tables into Guangdong pilot data.
- Use `scripts/import_sztu_major_scores.py` to import 深圳技术大学 official Guangdong undergraduate major-level scores from the school admission-site query interface into Guangdong pilot data.
- Use `scripts/import_gzucm_major_scores.py` with the bundled Python runtime to import 广州中医药大学 official Guangdong undergraduate major-level scores from school-site/official-WeChat image tables into Guangdong pilot data.
- Use `scripts/import_gdpu_major_scores.py` with the bundled Python runtime to import 广东药科大学 official Guangdong undergraduate major-level scores from cached school-site PDF/Excel attachments into Guangdong pilot data.
- Use `scripts/import_lingnan_major_scores.py` with the bundled Python runtime to import 岭南师范学院 official Guangdong undergraduate major-level scores from school-site HTML/image tables into Guangdong pilot data.
- Use `scripts/import_hstc_major_scores.py` with the bundled Python runtime to import 韩山师范学院 official Guangdong undergraduate major-level scores from cached school-site HTML tables into Guangdong pilot data.
- Use `scripts/import_zqu_major_scores.py` with the bundled Python runtime to import 肇庆学院 official Guangdong undergraduate major-level scores from cached school-site mini-app image tables into Guangdong pilot data.
- Use `scripts/import_jyu_major_scores.py` with the bundled Python runtime to import 嘉应学院 official Guangdong undergraduate major-level scores from cached school-site Excel attachments into Guangdong pilot data.
- Use `scripts/import_zhku_major_scores.py` with the bundled Python runtime to import 仲恺农业工程学院 official Guangdong undergraduate major-level scores from cached school-site Excel attachments into Guangdong pilot data.
- Use `scripts/import_special_reference_scores.py` to import Workbuddy supplemental/aggregator-marked ordinary-category major rows for special-scope Guangdong schools; these rows must keep `待官方复核` notes.
- Use `scripts/import_gaokao_cn_major_scores.py` to import 掌上高考 public-API supplemental undergraduate major rows. It defaults to Guangdong but supports `--province-id` and `--schools-csv` for national expansion; these rows must keep `source_name=掌上高考（聚合补充）`, `聚合站来源，待官方复核` notes, and batch/plan-type distinctions.
- Use `scripts/vision_ocr_image_zh.swift` for macOS Vision OCR on Chinese official image tables when a dedicated importer calls it.
- Use `scripts/ocr_grid_rank_pdf.py` for clear image-only official score-band PDFs that have one grid table with `分数 / 人数 / 累计人数`.
- Use `scripts/ocr_scanned_rank_pdf_macos.py` for scanned official one-score-one-rank PDFs on macOS when normal PDF text extraction fails.
- Use `scripts/ocr_rank_image_macos.py` for image-only official one-score-one-rank tables, and keep it in dry-run mode until OCR warnings have been checked.
- Use `scripts/ocr_dual_track_rank_pdf_macos.py` for scanned official rank PDFs where one score column contains two side-by-side tracks; keep OCR drafts out of `assets/pilot-data` until warnings are manually spot-checked.
- Use `scripts/fill_admission_scores_from_rank.py` to fill missing admission scores from same-year rank bands when an official投档 table publishes rank but not score.
- Use `scripts/fill_admission_ranks_from_score.py` to fill missing admission ranks from same-year score bands when an official投档 table publishes score but not rank.
- Use `scripts/audit_data.py` to verify data coverage before using recommendations for real candidates.
- Use `scripts/run_advisor.py` as the simplest interactive or low-parameter entry point.
- Use `scripts/recommend.py` to generate reproducible school and major recommendations.
- `assets/data/source_registry.csv` records known official source entry points and verification notes.
- `assets/templates` contains tiny raw-table examples for testing import mappings only.
- `assets/pilot-data/guangdong-physics` contains the current Guangdong physics pilot data directory.
- `assets/pilot-data/guangdong-history` contains the current Guangdong history pilot data directory.
- `assets/pilot-data/zhejiang-ordinary` contains the current Zhejiang ordinary-category pilot data directory.
- `assets/pilot-data/shandong-ordinary` contains the current Shandong ordinary-category pilot data directory.
- `assets/pilot-data/beijing-ordinary` contains the current Beijing ordinary-category pilot data directory.
- `assets/pilot-data/shanghai-ordinary` contains the current Shanghai ordinary-category pilot data directory.
- `assets/source-discovery/guangdong` tracks Guangdong school-site major-score source status, including the 2026 Guangdong public-undergraduate target list, imported sources, and not-yet-imported official sources.
- `assets/source-discovery/national/province_manifest.csv` tracks nationwide province-level collection status and current pilot/national data directories.
- `assets/source-discovery/national/gaokao_cn_province_id_map.csv` maps province names to 掌上高考 score API province IDs.
- `assets/source-discovery/national/gaokao_cn_school_ids.csv` is the exported 掌上高考 school-ID list used by `--schools-csv` national supplemental imports.
- `assets/source-discovery/jiangsu` contains discovered Jiangsu official sources; it is not yet a usable pilot data directory.
- `assets/source-discovery/hebei` contains discovered Hebei official sources plus an OCR draft; it is not yet a usable pilot data directory.
- `assets/data` contains tiny demo CSVs marked `DEMO_NOT_REAL`; replace or override them with verified provincial and school data before real counseling.

## Output Standard

For user-facing answers, include:

1. Input summary.
2. Data coverage: province, track, years, row count, and whether data is demo or verified.
3. School recommendations grouped by `冲/稳/保`; add `垫` for formal full志愿方案 when enough safe options exist.
4. Major suggestions tied to the user's interests.
5. A recommendation table when the user wants a方案: 志愿顺序、院校、专业/专业组、近三年最低分/位次、考生位次对比、层级、概率表述、数据精度、关键说明.
6. Missing information and next checks, especially 2026招生计划、选科限制、学费、城市、家庭预算、是否接受中外合作/民办/独立学院、是否服从调剂、体检/单科/外语限制.
