# Advising Rules

## Recommendation Basis

Rank/位次 is the primary comparison unit. Raw score is secondary because exam difficulty changes year to year. When rank is missing and no one-score-one-rank table is available, give only a rough score-based reference and ask for rank.

For a quick reference, do not block on every profile field. For a formal志愿方案, collect or explicitly mark assumptions for:

- Province and Gaokao year.
- Track/subject type and, in new-Gaokao provinces, elective-subject combination.
- Score, whether it includes policy加分, and province-wide rank.
- Target regions and whether省外 is acceptable.
- Interest majors plus excluded majors.
- School preferences: 985/211/双一流/公办/民办/中外合作/职业本科.
- Whether the candidate accepts专业调剂.
- Tuition tolerance, campus/city preferences,学制, and住宿/通勤 constraints.
- Body, color-vision, height, single-subject, oral-English, and foreign-language restrictions.
- Career direction:就业,考研,考公,留学,医学规培,教师编, etc.

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

`险` means the candidate is materially behind the historical cutoff and should not be treated as a safety option. When a user asks for a complete志愿表, add `垫` manually by selecting the safest `保` rows, normally where `rank_gap >= max(2 * band, candidate_rank * 0.30)` or where the school/major has multiple years of stable low cutoffs. Keep `垫` to 1-3 options unless the province's志愿数量 requires more.

Adjust manually when:

- The school changed major groups, campus, plan type, tuition, or招生规模.
- A program is first-year招生 or had征集志愿.
- The candidate has strict city, tuition, public/private, medical, teacher-training, or中外合作 constraints.
- The province changed batch structure or elective-subject requirements.
- 2026招生计划 materially expands or shrinks.
- The school uses a professional admission rule such as 分数优先, 专业志愿优先, or专业级差.

Suggested formal-plan allocation:

- `冲`: about 20%-30%, only when the candidate accepts the downside, especially调剂 risk.
- `稳`: about 40%-50%, the main body of the plan.
- `保`: about 20%-30%, with clear rank buffer.
- `垫`: 1-3 rows for extreme fallback, chosen from the safest verified options.

For new-Gaokao provinces, compare by院校专业组 or major whenever available. School-level最低线 is only a floor;热门专业 can be materially higher.

## Data Checks

Before giving a serious recommendation, check:

- Current one-score-one-rank table for rank conversion.
- 2023-2025 school, major-group, and major-level cutoff rows.
- Current-year招生计划, plan changes, new/paused majors, campus changes, and tuition changes.
- Major admission rules and transfer-major policy.
- Special requirements:体检,色盲色弱,外语语种,口试,单科成绩,男女比例,政审/面试 for special categories.
- Whether the source is provincial authority, official school site, official WeChat account, or only an aggregator. Use aggregators only for discovery.

## Output Tone

Use concrete wording:

- Say "按现有数据更像稳妥档" instead of "一定能上".
- Say "需要核对 2026 招生计划和选科要求" when current-year data is missing.
- Say "样例数据不能用于真实填报" if any recommendation uses demo rows.
- Refuse or correct promises like "包过" or "绝对录取"; use probability language such as "较高/中等/偏低".

## Formal Output

For a user-facing full plan, prefer a table with:

`志愿顺序 | 院校 | 专业/专业组 | 近三年最低分/位次 | 考生位次对比 | 层级 | 概率表述 | 关键说明`

Then add:

- Overall strategy and why the tiers are arranged that way.
- Key risks for each tier.
- Major-specific notes when major-level data exists.
- Official final-check list: provincial志愿填报系统, school招生网,院校代码,专业代码,招生计划,选科要求,学费,学制,校区,体检 and单科限制.
- Backup path if the ideal major is missed, such as转专业,辅修,考研方向, or same-field adjacent majors.

## Major and Employment Guidance

Major advice should combine fit and market:

- Interest fit: what the student wants to study or do daily.
- Ability fit: math, programming, memorization, communication, lab work, long training.
- Credential barrier: medicine, law, teaching, finance, accounting, engineering licensing.
- Market volatility: AI, media, finance, civil-service tracks, real estate-related fields.
- Region and school platform: internships, local industry, alumni pipeline.

Do not give salary promises or guarantee就业. Give "常见去向" and "风险点".
