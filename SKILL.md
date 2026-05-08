---
name: wayamzpost
description: Generate one Amazon-seller post tailored to a specific platform — Xiaohongshu (default, 6-9 cards), Lemon8 (6-10 cards), LinkedIn (long-form text, ≤3000 chars, 3-5 hashtags), X / Twitter (single tweet ≤280 chars OR thread of up to 25), or Instagram (1-10 carousel + ≤2200 char caption). Each platform has its own char limits, hashtag rules, card count range, and post.md output layout. Supports Chinese (default) or English output via config.output_language. Trigger when the user says "写小红书 amazon post / 亚马逊小红书 / amazon seller post / linkedin amazon post / x amazon thread / instagram amazon carousel" or asks for a platform-specific seller-audience post. Generates artifacts only; does NOT auto-publish unless the user explicitly enables a publish adapter in their config.
version: 1.7.0
---

# wayamzpost

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
   [`config.example.json`](config.example.json) to `~/.config/wayamzpost/config.json`
   (or wherever; set `WAYAMZPOST_CONFIG=<path>`) and fill in `persona.brand_cn`.
   Existing installs that still use `XHS_AMAZON_CONFIG` or
   `~/.config/amazon-xhs-poster/config.json` remain supported as a legacy
   fallback.
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
typically `~/.claude/skills/wayamzpost`. Substitute literally before
running, or `export SKILL_DIR=~/.claude/skills/wayamzpost` first.

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
   URLs from the Tier ladder in
   [`references/editorial-sop.md`](references/editorial-sop.md). Tier A
   (public, dated, automation-friendly) and Tier B (public, no listing
   dates) are the day-to-day candidates. Tier C (gated; X / LinkedIn /
   wearesellers / BDS / Walmart corp news / YouTube creator-signal) is
   automated via `fetch-gated.mjs` if the user has it enabled — see the
   "Optional gated-source pipeline" section below.
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

## Optional gated-source pipeline

When `config.gated_sources.enabled = true`, the skill ships a 6-fetcher
research pipeline that pulls structured signal into
`<job_dir>/research/gated-signal.md` for Stage 1 to fold into `topic.md`.
**Disabled by default** — automating logged-in services has real ToS /
account-suspension risk. Read [`references/gated-sources.md`](references/gated-sources.md)
before enabling.

The 6 fetchers (run in one command):

| Source                       | Auth needed?       | What it pulls                                  |
|------------------------------|--------------------|------------------------------------------------|
| X / Twitter                  | Real Chrome (CDP)  | Recent tweets from configured handles          |
| LinkedIn                     | Real Chrome (CDP)  | Recent activity from configured profile slugs  |
| wearesellers.com             | Real Chrome (CDP)  | Top hot non-paid threads with body extraction  |
| billiondollarsellers.com     | Real Chrome (CDP)  | Top archive articles (subscribers see body)    |
| corporate.walmart.com        | Public             | Top recent news via `news.sitemap.xml`         |
| YouTube                      | Real Chrome (CDP)  | Recent videos from configured channel handles  |

Setup (one-time):

```bash
# 1. Launch a separate Chrome with debug port enabled.
#    NOTE: this uses a dedicated debug profile and leaves your normal
#    Chrome session alone.
bash ${SKILL_DIR}/scripts/launch-chrome-debug.sh

# 2. In that Chrome, log in to: x.com, linkedin.com, wearesellers.com,
#    billiondollarsellers.com.  YouTube + Walmart are public.

# 3. Daily fetch:
node ${SKILL_DIR}/scripts/fetch-gated.mjs --connect-cdp [--date YYYY-MM-DD]
```

Output: `<drafts_root>/<DATE>/research/gated-signal.md`. Editorial stage
folds relevant items into `topic.md` and `post.json.topic.sources[]`.

## Source-decay audit

Public Tier A/B URLs bit-rot. Run monthly to catch decay:

```bash
node ${SKILL_DIR}/scripts/audit-sources.mjs            # full report
node ${SKILL_DIR}/scripts/audit-sources.mjs --quiet    # only flagged
node ${SKILL_DIR}/scripts/audit-sources.mjs --json     # machine-readable
```

Hits all 11 Tier A/B URLs with plain `fetch()`, reports HTTP / size /
last-seen date, flags 4xx, redirects, suspiciously small payloads, and
content older than 90 days. Exits non-zero on any flag.

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
wayamzpost/
├── SKILL.md                    (this file)
├── README.md                   (install + first-run; user-facing)
├── config.example.json         (zh-default; copy and fill)
├── config-en.example.json      (en-default; copy if output_language="en")
├── references/
│   ├── editorial-sop.md        (Tier A/B/C/D source ladder + workflow)
│   ├── angle-rotation.md
│   ├── title-and-cta-patterns.md
│   ├── card-schema.md
│   ├── voice-and-persona.md
│   ├── customization.md
│   ├── platforms.md            (per-platform limits + workflow)
│   ├── gated-sources.md        (X/LinkedIn/wearesellers/BDS/Walmart/YouTube auto-fetch)
│   └── publish-adapter.md
├── prompts/
│   ├── research-stage.md
│   └── editorial-stage.md
├── scripts/
│   ├── init-day.py             (Stage 0; platform-aware skeleton)
│   ├── history.py              (called by init-day; safe to call alone)
│   ├── validate.py             (Stage 3 gate; reads PLATFORM_PRESETS)
│   ├── render.mjs              (Stage 3; skips when cards is empty)
│   ├── make-post-md.py         (Stage 5; per-platform output layout)
│   ├── fetch-gated.mjs         (optional Stage 1 helper; 6 fetchers via CDP)
│   ├── launch-chrome-debug.sh  (one-shot launcher for fetch-gated CDP attach)
│   └── audit-sources.mjs       (monthly Tier A/B URL decay check)
└── examples/
    ├── post.example.json                (xiaohongshu / ZH canonical)
    ├── post-en.example.json             (xiaohongshu / EN)
    ├── post-linkedin.example.json       (linkedin / EN)
    ├── post-linkedin-zh.example.json    (linkedin / ZH)
    ├── post-x.example.json              (x / EN thread)
    ├── post-x-zh.example.json           (x / ZH thread)
    ├── post-instagram.example.json      (instagram / EN)
    ├── post-instagram-zh.example.json   (instagram / ZH)
    └── persona.example.json             (alternate persona block)
```
