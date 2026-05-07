---
name: amazon-xhs-poster
description: Generate one Amazon-seller post tailored to a specific platform — Xiaohongshu (default, 6-9 cards), Lemon8 (6-10 cards), LinkedIn (long-form text, ≤3000 chars, 3-5 hashtags), X / Twitter (single tweet ≤280 chars OR thread of up to 25), or Instagram (1-10 carousel + ≤2200 char caption). Each platform has its own char limits, hashtag rules, card count range, and post.md output layout. Supports Chinese (default) or English output via config.output_language. Trigger when the user says "写小红书 amazon post / 亚马逊小红书 / amazon seller post / linkedin amazon post / x amazon thread / instagram amazon carousel" or asks for a platform-specific seller-audience post. Generates artifacts only; does NOT auto-publish unless the user explicitly enables a publish adapter in their config.
version: 1.2.0
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
   `output_language: "zh"` or `"en"` AND `platform: "xiaohongshu" |
   "lemon8" | "linkedin" | "x" | "instagram"` here — they change the title
   keyword, CTA tokens, char limits, hashtag rules, card count range, and
   post.md output layout. See [references/platforms.md](references/platforms.md).
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

- "写小红书 amazon post" / "亚马逊小红书" / "xhs amazon" / "来一篇亚马逊笔记"
- "amazon seller post" / "amazon creator note"
- "linkedin amazon post" / "linkedin amazon thread"
- "x amazon post" / "amazon twitter thread" / "amazon x thread"
- "instagram amazon carousel" / "ig amazon post"
- "lemon8 amazon post"
- Any request to produce a platform-specific Amazon-seller-audience post

## Quick triggers (when NOT to invoke)

- AI-builder digest / 9-card AI content (different methodology)
- Single-image (non-carousel) XHS posts
- Video content
- Non-Amazon-seller audiences

## Platform support

Set `config.platform` to one of:

| Platform     | Format            | Title cap | Body cap | Hashtags  | Cards |
|--------------|-------------------|-----------|----------|-----------|-------|
| xiaohongshu  | image carousel    | 20 chars  | (soft)   | 5–10      | 6–9   |
| lemon8       | image carousel    | 30 chars  | 2000     | 5–15      | 6–10  |
| linkedin     | long-form text    | (none)    | 3000     | 3–5       | 0     |
| x            | post or thread    | (none)    | 280/post | 0–2       | 0     |
| instagram    | carousel + caption| (none)    | 2200     | 5–30      | 1–10  |

**Every platform supports both `output_language: "zh"` and `"en"`.** They
are independent fields. So `language=zh + platform=linkedin` produces
Chinese LinkedIn posts; `language=en + platform=x` produces English X
threads. For X specifically, the validator applies CJK weighting (each
Chinese char counts as 2 toward the 280 weight cap, per twitter-text spec).

See [references/platforms.md](references/platforms.md) for the full
language × platform matrix, post.json shape (especially `xhs.thread` for
X), per-platform editorial guidance, and cross-posting workflow.

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
│   ├── platforms.md            (per-platform limits + workflow)
│   └── publish-adapter.md
├── prompts/
│   ├── research-stage.md
│   └── editorial-stage.md
├── scripts/
│   ├── init-day.py             (Stage 0; platform-aware skeleton)
│   ├── history.py              (called by init-day; safe to call alone)
│   ├── validate.py             (Stage 3 gate; reads PLATFORM_PRESETS)
│   ├── render.mjs              (Stage 3; skips when cards is empty)
│   └── make-post-md.py         (Stage 5; per-platform output layout)
└── examples/
    ├── post.example.json            (xiaohongshu / ZH canonical)
    ├── post-en.example.json         (xiaohongshu / EN)
    ├── post-linkedin.example.json   (linkedin / EN)
    ├── post-x.example.json          (x / EN thread)
    ├── post-instagram.example.json  (instagram / EN)
    └── persona.example.json         (alternate persona block)
```
