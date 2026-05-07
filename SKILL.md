---
name: amazon-xhs-poster
description: Generate one Amazon-seller-themed creator post — 6-9 deterministic PNG cards plus a post.md ready for manual upload to Xiaohongshu (default), Lemon8, Threads, or any multi-card creator surface. Supports Chinese (default) or English output via config.output_language. Trigger when the user says "写小红书 amazon post / 亚马逊小红书 / 来一篇亚马逊笔记 / xhs amazon / amazon seller post / amazon creator note" or asks for a multi-card seller-audience post. Generates artifacts only; does NOT auto-publish unless the user explicitly enables a publish adapter in their config.
version: 1.1.0
---

# Amazon XHS Poster

Generate one Amazon-seller-themed Xiaohongshu (小红书) post per day:
6–9 deterministic image cards rendered from HTML templates, plus a
markdown file with title / body / hashtags / card list ready for manual
upload to the Xiaohongshu app.

## HARD RULES (read these first)

1. **No automated publishing by default.** This skill stops at producing
   `cards/*.png` and `post.md`. Never call any XHS publish flow,
   `playwright_publish_*`, or external upload tooling unless the user
   explicitly sets `publish_adapter.enabled = true` in their config and
   provides a `module_path`. See [references/publish-adapter.md](references/publish-adapter.md).
2. **Config is mandatory.** First-run users must copy
   [`config.example.json`](config.example.json) to `~/.config/amazon-xhs-poster/config.json`
   (or wherever; set `XHS_AMAZON_CONFIG=<path>`) and fill in `persona.brand_cn`.
   The validator refuses to run while it still says `REPLACE_ME`. Pick
   `output_language: "zh"` or `"en"` here too — it changes the title
   keyword, CTA tokens, decision verbs, and post.md header language.
3. **Voice supremacy.** When any pattern in the references would force a
   sentence the persona wouldn't say, **drop the pattern**, write the
   natural line, and append the reason to `post.json.qa_notes`. Mechanical
   rule-following degrades copy faster than it protects it.
4. **Confidentiality boundary.** Public copy must not leak any token from
   `config.forbidden_source_tokens` (paid feed names) or
   `config.forbidden_brands_in_copy` (your internal tooling). The
   validator hard-fails on either.
5. **Manual decisions belong to the user.** Pick the angle, write the
   draft, render the cards — but never auto-confirm "this is good enough
   to post" without showing the user the rendered output and `post.md`.

## What you produce

```
<config.paths.drafts_root>/<DATE>/
├── research/
│   ├── topic.md                # angle + sources, drives editorial
│   ├── recent_history.json     # 30-day rolling, dedup data
│   └── recent_history.md
├── cards/
│   ├── card_01.html …          # source HTML (debug)
│   ├── card_01.png …           # 1080×1440 PNGs ready for upload
│   └── render_manifest.json
├── post.json                   # canonical post artifact
└── post.md                     # final hand-off file (title / body / hashtags / card list)
```

Optionally mirrored to `<config.paths.desktop_root>/<DATE>/` for
AirDrop/iCloud sync to phone.

## Workflow (6 stages)

### Stage 0 — Initialize the day

In every command below, `${SKILL_DIR}` is the install path of this skill —
typically `~/.claude/skills/amazon-xhs-poster`. Substitute literally before
running, or `export SKILL_DIR=~/.claude/skills/amazon-xhs-poster` first.

```bash
python3 ${SKILL_DIR}/scripts/init-day.py [--config <path>] [--date YYYY-MM-DD]
```

Creates the day's directory tree, writes the `post.json` skeleton (persona
from config), and runs `history.py` to generate `recent_history.{json,md}`.
Defaults today to America/Los_Angeles. Idempotent — re-running on the
same date reuses the existing files.

### Stage 1 — Research & angle selection

Follow [`prompts/research-stage.md`](prompts/research-stage.md):

1. Read `research/recent_history.md`.
2. Apply the 14-day rotation in [`references/angle-rotation.md`](references/angle-rotation.md)
   to pick today's `topic.category`.
3. Find a sharp topic in that category; gather 2–5 real `https://` source
   URLs.
4. Write `research/topic.md` and fill `post.json.topic` (category, angle,
   why_now, selection_reason, sources).

### Stage 2 — Editorial (write `post.json`)

Follow [`prompts/editorial-stage.md`](prompts/editorial-stage.md):

1. Pick title and CTA patterns per [`references/title-and-cta-patterns.md`](references/title-and-cta-patterns.md)
   (T1–T8 / CTA1–CTA6, respecting 7-day title and 3-day CTA rotation).
2. Write 6 cards (expand to 7–8 only if needed) per the schema in
   [`references/card-schema.md`](references/card-schema.md). Each card has
   `id`, `kind`, `eyebrow`, `headline`, `body`, `bullets`, `footer`.
3. Write `xhs.title` (≤ 20 chars, must contain configured keyword),
   `xhs.content` (with hashtag block appended), `xhs.tags` (5–10, tiered).
4. **Voice supremacy**: if any pattern fights the persona, drop it and
   document in `qa_notes`. See [`references/voice-and-persona.md`](references/voice-and-persona.md).

### Stage 3 — Render cards + Validate

```bash
node ${SKILL_DIR}/scripts/render.mjs <DRAFTS_ROOT>/<DATE>/post.json [--config <path>]
```

The renderer:
- Runs `validate.py` first; render proceeds only on exit 0.
- Generates `card_01.png` … `card_0N.png` at 1080×1440 via Playwright.
- Mirrors to `desktop_root/cards/` if configured.
- Writes back `status.render = "done"` into `post.json`.

If the validator hard-fails, fix `post.json` and re-run. Soft-warnings are
informational; review them but don't block.

To run the validator manually any time:

```bash
python3 ${SKILL_DIR}/scripts/validate.py <DRAFTS_ROOT>/<DATE>/post.json --json
```

### Stage 4 — QA (Tier C taste check)

Answer all 4 before declaring done:

1. Does card 1 stop the scroll in 3 seconds?
2. Can a busy seller decide a concrete action in 30 seconds?
3. Does a first-time visitor get a credible reason to follow?
4. Does the post feel like "this account filters 90% of the noise"?

Any "no" → return to Stage 2.

### Stage 5 — Hand-off

```bash
python3 ${SKILL_DIR}/scripts/make-post-md.py <DRAFTS_ROOT>/<DATE>/post.json
```

Produces `post.md` at `<job_dir>/post.md`. The user opens this on their
phone and uploads to Xiaohongshu manually.

### ⛔ Stage 6 — Auto-publish (DEFAULT: DISABLED)

Only run if `config.publish_adapter.enabled === true` AND `module_path` is
set. See [`references/publish-adapter.md`](references/publish-adapter.md).
**Read that doc fully before enabling — getting bot-flagged is a real
risk.**

## Quick triggers (when to invoke)

- "写小红书 amazon post"
- "亚马逊小红书"
- "xhs amazon" / "amazon xhs"
- "来一篇亚马逊笔记"
- "今天的小红书亚马逊更新"
- Any request to produce a 6–9 card XHS post for Amazon sellers

## Quick triggers (when NOT to invoke)

- AI-builder digest / 9-card AI content (different methodology — the
  Amazon flow uses 6–9 cards with a different theme palette, validator,
  and source ladder)
- Single-image XHS posts
- Video XHS content
- English-only LinkedIn / Twitter posts (use a different skill)

## Dependencies

- Python 3.9+ (for `zoneinfo`)
- Node.js 18+
- Playwright with Chromium: `npx playwright install chromium`

## Tree

```
amazon-xhs-poster/
├── SKILL.md                    (this file)
├── README.md                   (install + first-run; user-facing)
├── config.example.json         (copy and fill)
├── references/
│   ├── editorial-sop.md
│   ├── angle-rotation.md
│   ├── title-and-cta-patterns.md
│   ├── card-schema.md
│   ├── voice-and-persona.md
│   ├── customization.md
│   └── publish-adapter.md
├── prompts/
│   ├── research-stage.md
│   └── editorial-stage.md
├── scripts/
│   ├── init-day.py             (Stage 0)
│   ├── history.py              (called by init-day; safe to call alone)
│   ├── validate.py             (Stage 3 gate; safe to call standalone)
│   ├── render.mjs              (Stage 3)
│   ├── make-post-md.py         (Stage 5)
│   └── templates/              (reserved; v4 HTML is inlined in render.mjs)
└── examples/
    ├── post.example.json       (canonical reference)
    └── persona.example.json    (alternate persona to prove configurability)
```
