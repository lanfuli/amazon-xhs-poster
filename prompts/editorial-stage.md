# Editorial Stage Prompt

This is the Stage 2 (editorial) prompt for the agent. It assumes Stage 1
has populated `post.json.topic` and `research/topic.md`.

---

## Inputs

- `<DRAFTS_ROOT>/<DATE>/post.json` (with topic block populated)
- `<DRAFTS_ROOT>/<DATE>/research/topic.md`
- [`references/title-and-cta-patterns.md`](../references/title-and-cta-patterns.md)
- [`references/voice-and-persona.md`](../references/voice-and-persona.md)
- [`references/card-schema.md`](../references/card-schema.md)
- `recent_history.md` (for title/CTA dedup awareness)

## Task

Fill in `post.json.xhs`, `post.json.cards`, and `post.json.seo` to a state
that passes [`scripts/validate.py`](../scripts/validate.py).

### 1. Title

- Pick a title pattern (T1–T8) that hasn't been used in the last 7 days
  per `recent_history.md`.
- Write a title ≤ 20 chars, must contain at least one keyword from
  `config.title_constraints.must_contain` (default: `亚马逊`).
- Optional: log the chosen ID in `post.json.xhs.title_pattern_id`.

### 2. Six cards (default)

| # | Kind         | What it does |
|---|--------------|--------------|
| 1 | `hook`       | Earn the scroll-stop in 3 seconds |
| 2 | `tension`    | What sellers usually get wrong about this |
| 3 | `framework`  | What changed / what it really means |
| 4 | `checklist`  | Concrete actions or SOP changes |
| 5 | `ai-angle`   | Workflow leverage; if `topic.category="ai-workflow"`, MUST end on a decision verb (决定/判断/换/停/加预算/下架/挑选/暂停/转移/重组/砍/上架/留) |
| 6 | `cta`        | Action / takeaway / signature; MUST contain one of `点赞/收藏/关注/评论/不迷路` |

Expand to 7–8 cards only if the topic genuinely needs the room (comparison,
extra example, recap). Don't pad.

For each card, set:

```json
{
  "id": "card_0X",
  "kind": "<kind>",
  "eyebrow": "<small label, e.g. '触发逻辑' or '今晚就做'>",
  "headline": "<2-line max, can use \\n>",
  "body": "<supporting paragraph, optional>",
  "bullets": ["...", "...", "..."],
  "footer": "<persona signature>"
}
```

### 3. CTA on card 6

- Pick a CTA ID (CTA1–CTA6) that hasn't appeared on card 6 in the last 3
  days per the on-disk neighbors (the validator will catch the CTA-similarity
  case automatically).
- Last sentence MUST contain one of `点赞 / 收藏 / 关注 / 评论 / 不迷路`.

### 4. Hashtags

5–10 tags, each ≤ 12 chars. Three-tier structure:

- 1–2 brand/persona tags (e.g. `亚马逊`, `<persona-name>`, `亚马逊卖家`)
- 3–5 topic-specific tags (must share token with topic.angle / xhs.title /
  card 1–3 headlines)
- 2–3 broad-SEO tags (e.g. `跨境电商`, `出海`, `美国电商`)

At least one tag must contain a keyword from
`config.title_constraints.must_contain` (default: `亚马逊`).

Write tags into `post.json.xhs.tags` AND make sure they're appended to
`xhs.content` as a trailing hashtag block (`#A #B #C ...`).

### 5. xhs.content

Full XHS body. Format:

- Opening hook (often = `xhs.opening_hook`)
- Paragraph or two of context / framework
- Concrete checklist or numbered actions
- Closing CTA (mirror card 6's last line)
- Blank line, then the hashtag block

Use blank lines for paragraph breaks (`\n\n` in JSON). Keep it skimmable.

### 6. Voice override (the most important rule)

If any of the patterns above force a sentence the persona wouldn't say:

- **Drop the pattern.**
- Write the natural line.
- Append a note to `post.json.qa_notes` explaining why.

Voice always wins.

### 7. Final self-check (Tier C)

Before declaring Stage 2 complete:

1. Card 1 stop-scroll in 3 seconds?
2. Busy seller decides a concrete action in 30 seconds?
3. First-time visitor has a credible follow reason?
4. Does it feel like "this account filters 90% of the noise"?

Any "no" → rewrite that section before moving on.

## Stop condition

You're done with Stage 2 when:
- All 6+ cards filled in (id, kind, eyebrow, headline, body/bullets, footer)
- xhs.title, xhs.content, xhs.tags populated
- xhs.content ends with the hashtag block
- `validate.py --json` would run without errors (you can run it; the
  renderer also runs it as a hard gate)

Hand off to render.mjs.
