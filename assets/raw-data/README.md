# Raw Gaokao Excel Data

`各省份/` contains the bundled nationwide Excel data package used by the advisor as a fallback source when normalized CSV pilot data is not available.

- File count: 1011 Excel files
- Approximate size: 1.2GB
- Contents: provincial招生计划、专业录取分数、院校录取分数、一分一段表 and related spreadsheets
- Default reader path: `assets/raw-data/各省份`

The advisor first checks normalized data under `assets/pilot-data` and `assets/national-data`. If the requested province/track is not available there, it reads this raw Excel bundle and attempts to extract 2023-2025 professional admission rows, score-rank tables, school location, school nature, and 985/211 metadata.

Official 2026招生计划、专业组、选科要求、学费、校区 and current-year provincial rules must still be checked before real志愿填报.
