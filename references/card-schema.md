# `post.json` Schema

> The complete shape of `post.json`. Required fields are validator-enforced.
> Source columns: **U** = user fills (via config), **C** = Claude writes
> during editorial, **S** = a script writes (init-day / render).

## Top-level

| Field | Type | Required | Source | Notes |
|-------|------|----------|--------|-------|
| `version` | string | yes | S | Schema version. Currently `"1.1"`. |
| `job_date` | `YYYY-MM-DD` | yes | S | America/Los_Angeles date. |
| `language` | `"zh"` \| `"en"` | recommended | S | Output language. Read by `make-post-md.py` for header text; written by `init-day.py` from `config.output_language`. |
| `persona` | object | yes | U+S | See below. Must match `config.persona`. |
| `topic` | object | yes | C | See below. |
| `seo` | object | yes | C | Optional but recommended. |
| `strategy` | object | optional | C | Editorial guardrails. |
| `design` | object | yes | C+S | Card design. |
| `xhs` | object | yes | C | Final published copy. |
| `cards` | array | yes | C | 6–9 cards. |
| `paths` | object | yes | S | All filesystem paths. |
| `status` | object | optional | S | Stage tracking. |
| `qa_notes` | array of strings | optional | C | Document any pattern overrides. |
| `job_type` | string | optional | S | Default `"daily"`. |

## `persona`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `brand_cn` | string | yes | Must equal `config.persona.brand_cn`. |
| `identity` | string | yes | One-line backstory. |
| `voice` | string | recommended | Tone keywords. |
| `signature` | string | yes | Card footer text. |
| `location` | string | optional | |
| `years_experience` | number | optional | |

## `topic`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `category` | string | yes | One of the keys in `config.angle_quotas`. |
| `angle` | string | yes | 1–2 sentence angle statement. |
| `why_now` | string | recommended | Why this matters tonight. |
| `selection_reason` | string | recommended | "<cat>: 14d count=X, floor=Y, gap=Z". |
| `risk_policy` | string | optional | E.g. "Treat black-hat only as risk-warning…" |
| `sources` | array of strings | yes | Each must be a valid `https://` URL. Validator hard-fails on slugs. |

## `seo`

| Field | Type | Notes |
|-------|------|-------|
| `primary_keywords` | string array | 3–5 high-intent. |
| `secondary_keywords` | string array | Long-tail. |
| `hashtags` | string array | Optional fallback if `xhs.tags` is empty. |

## `strategy`

| Field | Type | Notes |
|-------|------|-------|
| `attention_goal` | string | E.g. "3秒内停留并产生关注/收藏意图". |
| `psychology_hooks` | string array | At least one of: loss-aversion, curiosity-gap, identity-mirroring, operator-authority, credible-urgency. |
| `ai_positioning` | string | Generic AI framing rule for ai-workflow posts. |
| `dedupe_window_days` | number | Default 30. |
| `source_priority` | array | Optional reference list. |
| `public_source_policy` | string | Reminds you to keep research stack internal. |

## `design`

| Field | Type | Required | Validator |
|-------|------|----------|-----------|
| `style` | string | yes | Must be `"iphone-notes-editorial-v4"`. |
| `theme` | string | yes | `"auto"` or one of: `amazon-news`, `white-hat-tactic`, `risk-warning`, `ai-workflow`, `walmart-multi-channel`, `creator-signal`. |
| `cards` | number | yes | Must be 6–9. |
| `cards_min` | number | optional | If present must equal 6. |
| `cards_max` | number | optional | If present must equal 9. |
| `ratio` | string | optional | `"3:4"` |
| `width` | number | optional | 1080 |
| `height` | number | optional | 1440 |
| `accent_strategy` | string | optional | `"color-psychology"` |

## `xhs`

| Field | Type | Required | Validator |
|-------|------|----------|-----------|
| `title` | string | yes | Length ≤ `config.title_constraints.max_chars` (default 20); must contain a keyword from `must_contain` (default `["亚马逊"]`); not duplicate of any title in last 7 days. |
| `title_max_length` | number | optional | Mirrors config; informational. |
| `opening_hook` | string | recommended | First 3-second hook. |
| `content` | string | yes | Full XHS body. Hashtag block is appended at the end. |
| `cta` | string | recommended | Closing line; mirrored in card 6. |
| `tags` | string array | yes | 5–10 tags, each ≤ 12 chars; ≥1 contains the must-contain keyword; ≥60% must share token with topic/headlines. |
| `append_hashtags_to_content` | boolean | yes | Must be `true`. |
| `schedule_at` | string | optional | Empty for manual mode. |
| `delivery_mode` | string | optional | `"manual"` (default and recommended). |
| `title_pattern_id` | string | optional | T1–T8 audit aid. |

## `cards[]`

Array of 6–9 card objects.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | `card_01` … `card_0N`. Drives PNG filename. |
| `kind` | enum | `hook` / `tension` / `framework` / `checklist` / `ai-angle` / `cta` / `matrix` / `note`. The renderer treats them all uniformly in v4 except for hero-card halo on the first card. `matrix` is reserved (renderer support pending). |
| `eyebrow` | string | Small label above the headline (e.g. `2026.05  风险预警`). |
| `headline` | string | Large title; supports `\n` for line breaks. |
| `body` | string | Optional supporting paragraph; supports `\n`. |
| `bullets` | array of strings | Up to 5; renderer ignores beyond 5. |
| `footer` | string | Card footer; usually persona signature. |

### Last card extra rules (validator)

- `card[N-1]` must include at least one of: `点赞 / 收藏 / 关注 / 评论 / 不迷路`
- `card[N-1]` text must be < 70% Levenshtein-similar to any of the past 3 days'
  card N-1 text.

### AI-workflow card 5 rules (validator soft-warn)

If `topic.category == "ai-workflow"` and there's a card at index 4, its body
+ bullets together should include at least one decision verb.

## `paths`

All written by `init-day.py`. Override only if you really know what you're
doing.

| Field | Notes |
|-------|-------|
| `job_dir` | `<drafts_root>/<DATE>` |
| `desktop_root` | `<config.paths.desktop_root>/<DATE>` or empty string when desktop mirror is disabled |
| `research_note` | `<job_dir>/research/topic.md` |
| `post_json` | `<job_dir>/post.json` |
| `render_manifest` | `<job_dir>/cards/render_manifest.json` |
| `cards_dir` | `<job_dir>/cards` |

## `status`

Optional but useful for orchestration:

```json
{
  "research": "pending|complete",
  "editorial": "pending|complete",
  "render": "pending|done",
  "qa": "pending|complete",
  "publish": "manual"
}
```

The renderer flips `status.render` to `"done"` after a successful run.

## Forbidden in public copy (validator hard-fail)

- Any token from `config.forbidden_source_tokens` (default: BDS, AMZ123,
  We Are Sellers, Helium 10 Podcast, Marketplace Pulse, Modern Retail, PPC
  Land — extend with your own)
- Any token from `config.forbidden_brands_in_copy` (default: openclaw,
  亚马逊大龙虾, nano banana, lobster mark — these were the original author's
  internal references; replace with your own internal brand names)

## Minimum compliant skeleton

```json
{
  "version": "1.1",
  "job_date": "2026-05-06",
  "persona": {
    "brand_cn": "<your brand>",
    "identity": "<one-line backstory>",
    "voice": "<tone keywords>",
    "signature": "<card footer>"
  },
  "topic": {
    "category": "amazon-news",
    "angle": "...",
    "why_now": "...",
    "selection_reason": "amazon-news: 14d count=2, floor=2, gap=0",
    "sources": ["https://aboutamazon.com/news/..."]
  },
  "seo": { "hashtags": ["..."] },
  "design": {
    "theme": "auto", "style": "iphone-notes-editorial-v4",
    "cards": 6, "cards_min": 6, "cards_max": 9
  },
  "xhs": {
    "title": "亚马逊...", "content": "...",
    "tags": ["...", "...", "...", "...", "..."],
    "append_hashtags_to_content": true
  },
  "cards": [
    /* 6 cards, each with id/kind/eyebrow/headline/body/bullets/footer */
  ],
  "paths": {
    "job_dir": "<DRAFTS_ROOT>/2026-05-06",
    "cards_dir": "<DRAFTS_ROOT>/2026-05-06/cards"
  }
}
```

See [`examples/post.example.json`](../examples/post.example.json) for a
fully-filled-in sample.
