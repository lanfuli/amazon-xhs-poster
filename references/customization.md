# Customizing the skill for your account

The skill ships with defaults aimed at Amazon-seller XHS content in
Mandarin. Almost everything is configurable through one `config.json`. This
doc walks through the realistic customizations.

> **Privacy reminder**: your filled-in `config.json` should NEVER be
> committed to a public repository. It contains identifying details (your
> persona name, brand string, location) plus your `forbidden_brands_in_copy`
> and `forbidden_source_tokens` lists — which together advertise exactly
> which competitor / paid-feed names you don't want surfacing in your
> output. Treat the config like an env file. The skill's `.gitignore`
> already excludes it; verify your fork preserves that rule.

## 1. Setting your persona

Open your `config.json` and edit the `persona` block:

```json
"persona": {
  "brand_cn": "Your Xiaohongshu account brand string (CJK or Latin)",
  "identity": "One-line persona description (industry + years + perspective)",
  "voice": "3-5 voice keywords, comma-separated",
  "signature": "Footer signature on each card, usually same as brand_cn",
  "location": "City, ST",
  "years_experience": 8
}
```

Validator will refuse to run while `brand_cn` still says `REPLACE_ME`. The
persona must match what's in `post.json.persona.brand_cn` exactly, so
`init-day.py` writes it for you on each new day.

## 2. Target platform

The biggest UX lever after persona. Set `config.platform`:

```json
"platform": "xiaohongshu"   // or linkedin / x / instagram
```

This drives **everything** about how the post is shaped: title length,
body cap, hashtag count + length, card count range, and post.md output
layout.

Quick reference:

| Platform     | Cards | Title cap | Body cap | Hashtags  | Best for |
|--------------|-------|-----------|----------|-----------|----------|
| xiaohongshu  | 6–9   | 20 chars  | (soft)   | 5–10 (≤12)| ZH carousel; the original target |
| linkedin     | 0     | (none)    | 3000     | 3–5 (≤50) | B2B long-form text |
| x            | 0     | (none)    | 280/post | 0–2       | Single tweet or thread |
| instagram    | 1–10  | (none)    | 2200     | 5–30 (≤30)| Lifestyle / visual-first |

Full per-platform rules, character-count gotchas, and cross-posting
workflows live in [`platforms.md`](platforms.md). Each platform has its
own example post in `examples/`:
- `post.example.json` (xiaohongshu / ZH)
- `post-en.example.json` (xiaohongshu / EN)
- `post-linkedin.example.json` (LinkedIn text-only)
- `post-x.example.json` (X thread)
- `post-instagram.example.json` (Instagram carousel)

## 3. Output language

The skill ships with two language tracks: **ZH** (default, optimized for
Xiaohongshu native audience) and **EN** (for LinkedIn / X / Instagram /
English-speaking creator platforms).

```json
"output_language": "zh"   // or "en"
```

Setting `output_language` to `"en"` auto-selects English defaults for:
- `must_contain` → `["Amazon"]` (used for title and hashtag enforcement)
- `cta_tokens` → `["like", "save", "follow", "comment", "share", "subscribe"]`
- `decision_verbs` → `["decide", "switch", "pause", "stop", "increase budget", "remove", "select", "transfer", "rebuild", "cut", "promote", "keep", "kill"]`
- `post.md` headers → English (`# Amazon Seller Note — DATE`, `## Title`, `## Body`, etc.)
- `init-day.py` `strategy.attention_goal` → English variant

**You can still override any of these explicitly.** Three states:

| Value                        | Meaning |
|------------------------------|---------|
| `null` (or field omitted)    | Use the language default for `output_language`. |
| `["a", "b", ...]` (non-empty)| Use exactly these as the allowed/required tokens. |
| `[]` (explicitly empty)      | **Disable that check entirely.** The validator emits an `info` line so the bypass is visible. Use only when you have a deliberate reason (e.g. you're publishing to a platform that doesn't need a CTA token, or you handle title gating elsewhere). |

### Mixed-language workflows

If you want a Chinese title with English body (e.g. cross-posting to a
Chinese platform but with bilingual content), set `output_language: "zh"`
and write the body in English by hand. The validator only enforces
`must_contain` on the title, and the `cta_tokens` check is on the last
card. Both can be overridden.

### Renderer note

Card layout (`iphone-notes-editorial-v4`) uses a font stack that handles
both Chinese (PingFang SC) and Latin scripts (SF Pro Display, Helvetica
Neue). English content renders correctly without changes; the only
potentially-Chinese chip labels in the renderer are the theme labels
(`全球新闻` "Global News", `白帽运营` "White-Hat Ops", etc.) which are
emitted in zh-mode by default but get overridden when you set
`card.eyebrow` explicitly. In practice, EN-mode posts always set
`eyebrow` per card, so the chip text is never auto-generated Chinese.

## 4. Title constraints (manual override)

```json
"title_constraints": {
  "max_chars": 20,
  "must_contain": ["亚马逊"]
}
```

- `max_chars`: XHS truncates beyond this. 20 is the platform-wide soft
  ceiling; 22-24 sometimes works for short-character titles. Don't set it
  higher than 25.
- `must_contain`: a list (any-of). Set to `null` or omit to inherit from
  `output_language` defaults.

### Switching to a different platform / vertical

Want this skill to write Walmart-Marketplace content instead?

```json
"output_language": "zh",
"title_constraints": { "max_chars": 20, "must_contain": ["沃尔玛"] }  // Walmart in CN
```

You'll also want to:
- Edit your `angle_quotas` to be Walmart-shaped (e.g. drop ai-workflow
  ceiling, add `walmart-suppliers` floor).
- The pattern examples in `references/title-and-cta-patterns.md` are
  Amazon-themed (亚马逊 in zh / "Amazon" in en) — adapt mentally or
  fork the doc.

## 5. Forbidden brands and source tokens (privacy)

These are **merge** lists, not **replace** lists. The defaults are a starter
set the skill ships with — your own additions stack on top.

### `forbidden_brands_in_copy`

Stops your internal tool / brand names from accidentally leaking into public
copy. Defaults are placeholder examples from the original author —
**replace them with names that actually matter for you**:

```json
"forbidden_brands_in_copy": [
  "your-internal-tool-name",
  "your-internal-product",
  "your-deprecated-brand"
]
```

The defaults (`openclaw`, `亚马逊大龙虾` "Amazon big lobster",
`nano banana`, `lobster mark`) are specific to the original author's
environment — clean them out unless you genuinely want them blocked too.

### `forbidden_source_tokens`

Stops paid feed / research source names from leaking. The shipped defaults
cover well-known external paid sources (BDS, AMZ123, Helium 10 Podcast,
Marketplace Pulse, Modern Retail, PPC Land, We Are Sellers). **Keep them**
unless you have a specific reason to drop one — they're worth blocking by
default. Then add your own:

```json
"forbidden_source_tokens": [
  "billion dollar sellers",
  "we are sellers",
  "amz123",
  "bds",
  "wearesellers",
  "billiondollarsellers",
  "helium 10 podcast",
  "marketplace pulse",
  "modern retail",
  "ppc land",

  "your-internal-database",
  "your-paid-tracker",
  "your-private-data-feed"
]
```

The validator does **case-insensitive substring matching**, so
`"helium 10"` will catch `"Helium 10"`, `"helium10"`, `"HELIUM 10 podcast"`,
etc. This is intentional (catches casing tricks) but creates a foot-gun:

- ❌ Don't add short generic tokens like `"open"` or `"ai"` — they'll
  trigger on "open source", "open API", "AI agent", etc.
- ✅ Do use distinctive multi-word phrases or rare brand codes:
  `"acme research desk"`, `"bds"` (where the meaning is bounded), or
  internal slugs like `"projx-dashboard"`.

If you're unsure whether a token is "specific enough", grep your last
month of drafts for it — if it appears anywhere in legitimate copy, it's
too broad.

## 6. Angle quotas

To rebalance which categories get how much airtime:

```json
"angle_quotas": {
  "amazon-news":           { "floor": 3, "ceiling": 6, "color": "amber"  },
  "ai-workflow":           { "floor": 1, "ceiling": 2, "color": "blue"   },
  "your-new-category":     { "floor": 1, "ceiling": 3, "color": "amber"  }
}
```

- `floor` and `ceiling` are over a 14-day rolling window.
- `color` must be one of: `amber`, `green`, `red`, `blue`, `slate`,
  `violet`. New colors require renderer changes.
- New categories must also be referenced in `post.json.topic.category` and
  `design.theme` — the renderer falls back to `default` (neutral indigo)
  for unknown values.

The sum of floors should be ≤ 14; the sum of ceilings should be > 14
(otherwise some days have no allowed category).

## 7. Paths

```json
"paths": {
  "drafts_root": "~/wayamzpost-drafts",
  "desktop_root": "",
  "history_lookback_days": 30
}
```

- `drafts_root`: parent of all daily directories. `~` is expanded.
- `desktop_root`: optional mirror destination (e.g. `~/Desktop/XHS-Amazon`)
  so the rendered cards land somewhere you can airdrop / iCloud-sync to your
  phone. Empty string = skip mirror.
- `history_lookback_days`: validator dedup window. 30 is the default; 14 is
  reasonable if you post more than once a day.

## 8. Adding industry-specific keywords

The history builder counts how often certain keywords appear in titles +
angles, so you can see saturation. Default keywords are Amazon-seller
specific (PPC, COSMO, FBA, Brand Registry, etc.). Add your own:

```json
"extra_angle_keywords": [
  "Walmart Connect",
  "Sponsored Search",
  "your-niche-keyword"
]
```

These get merged with the defaults, not replacing them. They show up in
`research/recent_history.md` as an extra audit signal.

## 9. Where the config lives

Resolution order (every script in this skill):

1. `--config <path>` argument
2. `WAYAMZPOST_CONFIG` env var (an absolute path)
3. `XHS_AMAZON_CONFIG` env var (legacy)
4. `~/.config/wayamzpost/config.json`
5. `~/.config/amazon-xhs-poster/config.json` (legacy)

For a one-shot test or alternate persona:

```bash
WAYAMZPOST_CONFIG=/tmp/walmart-config.json \
  python3 ~/.claude/skills/wayamzpost/scripts/init-day.py
```

For production: drop a working config at the default path and forget about
it.

## 10. Things you genuinely should not change

- `design.style` validator allowlist. Only `iphone-notes-editorial-v4`
  matches the renderer's CSS contract. (Only applies to platforms that
  render cards.)
- The card count range for each platform — these mirror the platform's
  actual carousel limit (XHS 6–9, IG 1–10). Going outside the platform's
  range will produce uploads that fail or look wrong.
- `append_hashtags_to_content: true` for carousel platforms — search
  reach on XHS / IG depends on in-body hashtags, not just the tag field.
  (Validator skips this requirement for LinkedIn and X where it doesn't
  apply.)

If you find yourself wanting to change these, it's worth pausing and asking
why — they're shaped by platform constraints, not author preference. If
you genuinely need different platform limits, consider adding a new
preset (see `platforms.md` "Adding a new platform") rather than bending
an existing one.
