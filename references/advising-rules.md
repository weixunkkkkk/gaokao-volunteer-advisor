# Advising Rules

## Recommendation Basis

Rank/位次 is the primary comparison unit. Raw score is secondary because exam difficulty changes year to year. When rank is missing and no one-score-one-rank table is available, give only a rough score-based reference and ask for rank.

## Default Bands

The script uses a dynamic rank band:

`band = max(1000, min(15000, candidate_rank * 0.08))`

Compare the candidate rank with the median historical cutoff rank:

- `rank_gap = historical_cutoff_rank - candidate_rank`
- Positive gap means the candidate rank is better than the historical cutoff.
- `保`: `rank_gap >= band`
- `稳`: `0 <= rank_gap < band`
- `冲`: `-band <= rank_gap < 0`
- `险`: `rank_gap < -band`

Adjust manually when:

- The school changed major groups, campus, plan type, tuition, or招生规模.
- A program is first-year招生 or had征集志愿.
- The candidate has strict city, tuition, public/private, medical, teacher-training, or中外合作 constraints.
- The province changed batch structure or elective-subject requirements.

## Output Tone

Use concrete wording:

- Say "按现有数据更像稳妥档" instead of "一定能上".
- Say "需要核对 2026 招生计划和选科要求" when current-year data is missing.
- Say "样例数据不能用于真实填报" if any recommendation uses demo rows.

## Major and Employment Guidance

Major advice should combine fit and market:

- Interest fit: what the student wants to study or do daily.
- Ability fit: math, programming, memorization, communication, lab work, long training.
- Credential barrier: medicine, law, teaching, finance, accounting, engineering licensing.
- Market volatility: AI, media, finance, civil-service tracks, real estate-related fields.
- Region and school platform: internships, local industry, alumni pipeline.

Do not give salary promises or guarantee就业. Give "常见去向" and "风险点".
