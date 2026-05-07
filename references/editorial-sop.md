# Editorial SOP — Amazon Seller XHS Daily

> Day-to-day editorial workflow. Adapted from a production SOP that has been
> running daily since early 2026. The skill orchestrates this; you (or Claude)
> follow it.

## Mission

Persona = **operator-led seller account on Xiaohongshu**. The persona is a
human Amazon seller who *uses* AI as leverage — **not** an AI product, not a
content-farm channel, not a creator-advice account. Daily output is one
operator-memo-style multi-card post that makes Chinese-speaking Amazon sellers
feel "this account filters 90% of the noise for me."

The exact persona name, voice, and signature come from your `config.json`.

## Roles (mental model)

| Role | What it does | Output |
|------|--------------|--------|
| Research lead | Picks today's angle, gathers sources | `research/topic.md` |
| Editor-in-chief | Writes the post, applies patterns | `post.json` |
| Card designer | Renders deterministic visuals | `cards/card_*.png` |
| Hook/SEO/CTA QA | Final pass on stop-scroll, CTA, hashtag tier | `qa_notes` in post.json |

In practice Claude plays all four roles in one turn. The split exists so each
phase has a clear bar.

## Directory contract

For each day, the skill creates:

```
<DRAFTS_ROOT>/<DATE>/
├── research/
│   ├── topic.md             # selection_reason + source links + why-now
│   ├── recent_history.json  # auto-built; 30-day rolling
│   └── recent_history.md    # human-readable companion
├── cards/
│   ├── card_01.html
│   ├── card_01.png
│   ├── ...
│   └── render_manifest.json
├── post.json                # the canonical post artifact
└── post.md                  # final hand-off file for manual XHS publish
```

`<DRAFTS_ROOT>` and date are pulled from `config.paths.drafts_root` + today
in America/Los_Angeles.

## Stage 1 — Research

**Goal**: pick one angle that earns a serious operator's attention tonight.

1. Read `research/recent_history.md` (the previous 30 days).
2. Read [`angle-rotation.md`](angle-rotation.md) and choose a category that
   respects the 14-day rolling floor/ceiling.
3. Pick ONE angle; reject vague / emotional-bait topics with no concrete
   takeaway.
4. Drop 2-5 real `https://` URLs into `topic.md` Sources block. Slug stubs
   and human-readable IDs fail validation.
5. Source ladder (start at top; descend only if higher tier has nothing):
   - **Amazon official** (aboutamazon.com news/policy, Seller Central forums,
     advertising.amazon.com library/blog, SP-API release notes,
     brandservices.amazon.com, buywithprime.com)
   - **Walmart official** (corporate.walmart.com, marketplace.walmart.com,
     walmartconnect.com)
   - **LinkedIn** retail leadership + analysts (last 24h, EN, Recent)
   - **Xiaohongshu seller community** — packaging/language signal only,
     never copy verbatim
   - Supplemental specialist sources — list as supplemental, not primary
6. Black-hat topics → frame as risk / detection / enforcement / lessons
   learned. Never write step-by-step abusive SOPs.
7. Write the chosen angle and `selection_reason` into the `topic` block of
   `post.json`.

**Confidentiality boundary**: keep your research stack INTERNAL. Validator
will hard-fail if any token from `config.forbidden_source_tokens` shows up
in the public copy. The default list is a starter set — extend it for your
own paid feeds, internal databases, scraped sources.

## Stage 2 — Editorial

**Voice supremacy** (highest rule):

> Persona voice > all structural rules.

If a pattern from [`title-and-cta-patterns.md`](title-and-cta-patterns.md) or
[`angle-rotation.md`](angle-rotation.md) forces a sentence the persona
wouldn't say, drop the rule, document the exception in `post.json.qa_notes`,
and write the natural line.

**Card structure** (6 default, expand to 7-8 only if topic genuinely needs
the room):

1. **Hook** — tension / contrarian insight that earns the scroll-stop
2. **Tension** — what sellers usually get wrong about this
3. **Framework** — what changed / what it means
4. **Checklist** — exact actions / SOP changes
5. **AI / tool** — workflow leverage (ai-workflow only: must end on a
   decision verb — see [`title-and-cta-patterns.md`](title-and-cta-patterns.md) §5)
6. **CTA** — action / takeaway / signature; must contain at least one of
   `点赞 / 收藏 / 关注 / 评论 / 不迷路`

Optional 7-8: comparison, examples, objections, recap.

**Psychology**: title + card 1 must use at least one of:
- loss aversion
- curiosity gap
- identity mirroring (e.g. "如果你是亚马逊新卖家…")
- insider advantage
- credible urgency (real deadline / real cost)

Show the cost of inaction early. Busy sellers stop for downside, not
generic inspiration. Voice = high-agency, slightly elite: calm, specific,
decisive.

**AI topics specifically**:
- Frame the seller's AI workflow generically (e.g. "AI agent 自动…",
  "用 AI 帮你算账"). Do NOT name your internal tooling.
- The persona is a human operator who uses AI, not an AI product.
- Skip "AI is the future" filler. Show one concrete seller workflow that
  AI changes.
- Card 5 must answer "what decision does the seller change because AI is
  running?" Concrete decision verb required (see patterns doc).

**Forbidden brand check**: validator hard-fails on anything in
`config.forbidden_brands_in_copy`.

## Stage 3 — Render

```bash
node <skill>/scripts/render.mjs <DRAFTS_ROOT>/<DATE>/post.json [--config <cfg>]
```

The renderer:
- Runs the validator first; render only proceeds on exit 0.
- Writes `cards/card_01.png` … `card_0N.png` + `render_manifest.json`.
- Mirrors to `<config.paths.desktop_root>/<DATE>/cards/` if that path is set.
- Writes back `status.render = "done"` into post.json.
- Uses `iphone-notes-editorial-v4` template only (v1/v2/v3 are deprecated).

Color theme is picked from `design.theme` (or `topic.category` if
`design.theme = "auto"`). Supported: amber / green / red / blue / slate /
violet (matching the 6 angle categories).

## Stage 4 — QA

Before declaring done, answer all 4:

1. Does card 1 stop the scroll in 3 seconds?
2. Can a busy seller decide a concrete action in 30 seconds?
3. Does a first-time visitor get a credible reason to follow?
4. Does the post feel like "this account filters 90% of the noise for me"?

Any "no" → fix `post.json` and re-render.

## Stage 5 — Hand-off (no automated publish)

```bash
python3 <skill>/scripts/make-post-md.py <DRAFTS_ROOT>/<DATE>/post.json
```

Produces `post.md` with the title / body / hashtags / card list. The user
opens that on their phone and uploads to Xiaohongshu manually.

**No publish automation by default.** If you genuinely need to plug in an
auto-publisher, see [`publish-adapter.md`](publish-adapter.md) — but read
it carefully, the cost of getting bot-detected is higher than you think.

## Quality bar

- Reads like an operator memo, not a marketing brochure
- First card wins attention without clickbait nonsense
- Design clean enough to read on a phone
- SEO maximized without keyword stuffing
- Public copy = synthesized operator judgment; internal task/research note =
  source traceability
