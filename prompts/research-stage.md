# Research Stage Prompt

This is the Stage 1 (research) prompt for the agent driving the skill. It
assumes `init-day.py` has already created `<DRAFTS_ROOT>/<DATE>/` and
populated `research/recent_history.{json,md}`.

---

## Inputs

- `<DRAFTS_ROOT>/<DATE>/research/recent_history.md` — last 30 days
- `<DRAFTS_ROOT>/<DATE>/post.json` — skeleton with empty topic block
- [`references/angle-rotation.md`](../references/angle-rotation.md)
- [`references/editorial-sop.md`](../references/editorial-sop.md)

## Tasks

### 1. Pick the angle

Read `recent_history.md`. Count category occurrences over the last 14
days. Apply the [angle rotation algorithm](../references/angle-rotation.md):

```
1. Drop categories at/over their ceiling.
2. Among the rest, pick the one with the largest floor gap.
3. Tie-break: longest time since last appearance.
```

Cold-start (history empty)? Pick a category that hasn't appeared in the
last 7 days; if all six are eligible, default to the highest-floor option
(`amazon-news`, `white-hat-tactic`, or `risk-warning`).

### 2. Find a sharp topic in that category

Open the top-tier sources for that category (see editorial-sop.md §"Source
ladder"). Scan for an angle that is:

- **Concrete** — a specific decision, workflow change, or risk signal a
  busy seller can act on within 30 seconds of reading
- **Currently relevant** — there's a "why now" that doesn't sound forced
- **Not already saturated** — check `recent_history.md` "Angle keyword
  frequency" — pass on keywords with ≥ 3 mentions in 30 days

Reject:
- Vague themes ("Amazon is changing")
- Pure emotion bait ("锁钱 7 天" / "lock in your money for 7 days")
- Anything that requires writing step-by-step black-hat instructions
- Topics where the only "value" is repeating something the official press
  release already said

### 3. Gather 2–5 source URLs

- Real `https://` URLs only (validator hard-fails on slugs)
- Mix of Amazon-official + at least one operator-level signal
- Don't write source names into public copy later — they're for your own
  trace, not for the post

### 4. Write `research/topic.md`

Replace the stub with:

```markdown
# Topic — <DATE>

## Selection
- **Category**: <one of the 6>
- **Selection reason**: <category>: 14d count=N, floor=F, gap=G
- **Angle**: <1–2 sentence narrative>
- **Why now**: <real urgency tied to a date or event>

## Sources
1. https://...
2. https://...

## Public-source policy
Do not name sites in cards / xhs.content.
```

### 5. Update `post.json.topic`

```json
"topic": {
  "category": "<chosen>",
  "angle": "<full angle narrative>",
  "why_now": "<urgency context>",
  "selection_reason": "<chosen>: 14d count=N, floor=F, gap=G",
  "sources": ["https://...", "https://..."]
}
```

Set `status.research = "complete"`.

## Stop condition

You're done with Stage 1 when:
- `topic.md` is written and answerable
- `post.json.topic` has all four fields populated
- All `topic.sources` are real `https://` URLs
- The chosen category respects the 14-day ceiling

Hand off to the editorial stage.
