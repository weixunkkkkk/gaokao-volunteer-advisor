---
name: gaokao-volunteer-advisor
description: Build and run a Gaokao college-application advisor for Chinese candidates. Use when the user wants 2026 高考志愿参考, school recommendations from province/track/score/rank, 冲稳保院校分层, past-three-year admission cutoff comparison, one-score-one-rank handling, major recommendations from interests, or employment-outlook guidance for majors.
---

# Gaokao Volunteer Advisor

## Core Rule

Treat every recommendation as a reference, not a guarantee. Prefer rank/位次 over raw score, report data coverage, cite source fields when available, and say clearly when the bundled data is incomplete or sample-only.

For 2026 candidates, use 2023, 2024, and 2025 admission/cutoff data as the normal three-year historical baseline. If the user asks during 2026 filing, also verify current-year provincial rules, batch settings, elective-subject constraints, and招生计划 before giving concrete advice.

## Workflow

1. Collect minimum inputs:
   - Province, such as `广东`
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
8. Recommend majors after school fit:
   - Match interests to major families.
   - Explain就业前景 in practical terms: common roles, industry demand, volatility, learning burden, and credential barriers.
   - Avoid promising salary, employment certainty, or guaranteed admissions.

## Resources

- Read `references/data-schema.md` before creating, cleaning, or importing admission CSV data.
- Read `references/data-collection.md` before collecting real 2023-2025 provincial data or current-year 2026 policy data.
- Read `references/advising-rules.md` before changing recommendation thresholds or writing a detailed counseling answer.
- Use `scripts/normalize_data.py` to convert raw official CSV/XLSX tables into the standard CSV schema.
- Use `scripts/pdf_table_to_csv.py` to convert official PDF tables into the standard CSV schema.
- Use `scripts/html_table_to_csv.py` to convert official HTML tables into raw CSV before normalizing.
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
- `assets/source-discovery/jiangsu` contains discovered Jiangsu official sources; it is not yet a usable pilot data directory.
- `assets/source-discovery/hebei` contains discovered Hebei official sources plus an OCR draft; it is not yet a usable pilot data directory.
- `assets/data` contains tiny demo CSVs marked `DEMO_NOT_REAL`; replace or override them with verified provincial and school data before real counseling.

## Output Standard

For user-facing answers, include:

1. Input summary.
2. Data coverage: province, track, years, row count, and whether data is demo or verified.
3. School recommendations grouped by `冲/稳/保`, with historical rank and score references.
4. Major suggestions tied to the user's interests.
5. Missing information and next checks, especially 2026招生计划、选科限制、学费、城市、家庭预算、是否接受中外合作/民办/独立学院.
