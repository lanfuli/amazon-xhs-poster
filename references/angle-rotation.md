# Angle Rotation — 14-day rolling floor / ceiling

> Single source of truth for which category is allowed today. Stage 1 must
> consult this before locking the angle. Was written to combat one-category
> over-concentration (in the production data set, ai-workflow had hit 50%
> share over 14 days while walmart-multi-channel and creator-signal sat at 0%).

## Categories and quotas

Quotas live in `config.angle_quotas`. The defaults shipped with the skill:

| Category (`topic.category`) | Color  | Floor | Ceiling | Notes |
|----------------------------|--------|-------|---------|-------|
| `amazon-news`              | amber  | 2     | 5       | Platform / ads / policy official news |
| `white-hat-tactic`         | green  | 2     | 5       | White-hat tactics, operator SOPs |
| `risk-warning`             | red    | 2     | 5       | Risk warning, black-hat case analysis |
| `ai-workflow`              | blue   | 2     | **4**   | Ceiling deliberately lower — prevents AI over-concentration |
| `walmart-multi-channel`    | slate  | 1     | 3       | Walmart Marketplace / Walmart Connect / multi-channel |
| `creator-signal`           | violet | 0     | 2       | XHS / cross-border creator signals — rare appearance for variety |

Sum of floors = 9. Sum of ceilings = 24. Real output = 14 posts in 14 days,
so both ends have buffer.

## Selection algorithm (in order)

```
1. Skip every category whose 14-day count >= ceiling
2. Among the remaining categories:
   - If any have count < floor, pick the one with the largest gap
     (gap = floor - current_count)
   - Tie-break by longest time since last appearance
3. Write `topic.selection_reason` into post.json with the math, e.g.
   "walmart-multi-channel: 14d count=0, floor=1, gap=∞"
```

## Edge cases

### First run / cold start

`recent_history.json` doesn't exist yet (or has < 14 days of posts). Skip
this table; pick freely per Stage 1 SOP, but **prefer a category that
hasn't appeared in the last 7 days**.

The validator gracefully skips the 14-day ceiling check when history is
missing.

### All 6 categories at ceiling

Sum of ceilings (24) > 14 days, so this is impossible if the math is
right. If it happens, the history builder is producing wrong data — stop
and inspect, don't pick anyway.

### User explicitly requests a follow-up

If the user says "接着昨天讲" / "continue yesterday's thread" / similar,
override is allowed: pick the same category, write `"user follow-up
override"` in `selection_reason`.

## Color mapping (renderer)

The renderer recognizes all six category names directly as theme keys and
maps them to:
- `amber` (orange-ish) → amazon-news
- `green` → white-hat-tactic
- `red` → risk-warning
- `blue` → ai-workflow
- `slate` (cool blue-grey) → walmart-multi-channel
- `violet` → creator-signal

In `post.json.design.theme`, set either `"auto"` (use category name) or one
of the six category strings. Unknown values fall back to a neutral default.

## Validator integration

| Rule | Severity |
|------|----------|
| 14-day ceiling exceeded for the chosen category | soft-warn (exit 0) |
| Floor not yet met | not checked at the post level (it's a multi-day metric) |

## Maintenance

Review every month or every ~50 posts:
- Which category gets the most saves / follows?
- Should floor/ceiling shift?
- Any new pool worth adding (TikTok Shop, Temu, etc.)?

Edit `config.angle_quotas` to bring in a new category or change limits — no
code change needed.
