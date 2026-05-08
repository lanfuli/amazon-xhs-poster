# Platforms

> Set `config.platform` to pick the target. Each platform has its own
> **validator limits** (title length, body cap, hashtag rules, card count
> range) and its own **`post.md` output layout** (carousel / long-form /
> thread). The renderer itself is platform-agnostic — it paints PNG
> cards when `cards[]` is non-empty (size already enforced by the
> validator), and writes an empty manifest otherwise (text-only
> platforms). Defaults below are platform-natural; tighten via
> `config.title_constraints` / `config.cta_tokens` etc. as needed.

## Language × Platform matrix

`output_language` and `platform` are **independent**. Every combination
works:

|              | zh (Chinese)              | en (English)              |
|--------------|---------------------------|---------------------------|
| xiaohongshu  | ✓ default                 | ✓ EN-on-XHS (rare but works) |
| linkedin     | ✓ Chinese B2B / cross-border | ✓ Western B2B            |
| x            | ✓ Chinese tweets (CJK weight × 2) | ✓ standard                |
| instagram    | ✓ Chinese caption         | ✓ standard                |

The matrix is full-coverage: pick whichever language + platform combination
fits your audience. `make-post-md.py` reads both fields independently
when emitting `post.md`.

## Quick reference

| Platform     | Title cap | Body cap | Hashtags  | Cards   | Format             |
|--------------|-----------|----------|-----------|---------|--------------------|
| xiaohongshu  | 20 chars  | (soft)   | 5–10 (≤12) | 6–9     | image carousel     |
| linkedin     | (none)    | 3000     | 3–5 (≤50)  | 0       | long-form text     |
| x            | (none)    | 280/post | 0–2 (≤30)  | 0       | post or thread     |
| instagram    | (none)    | 2200     | 5–30 (≤30) | 1–10    | carousel + caption |

The renderer paints PNGs only for platforms where `renders_cards = true`
(xiaohongshu / instagram). Text-only platforms (linkedin / x) get an
empty `render_manifest.json` and `make-post-md.py` produces a text-shaped
`post.md`.

---

## xiaohongshu (default)

The original target. Optimized for the Chinese Xiaohongshu audience: short
title, image-first carousel, hashtag block in body for search reach.

- Title: ≤ 20 chars, must contain a token from
  `config.title_constraints.must_contain` (zh-default `["亚马逊"]`,
  i.e. "Amazon" in zh; en-default `["Amazon"]`)
- Body: no enforced cap (XHS soft-limits around ~1000 chars; the editorial
  pattern produces 600–900)
- Hashtags: 5–10, each ≤ 12 chars, ≥ 60% must share token with topic
- Cards: 6 default, 7–9 when topic warrants
- Output: `post.md` lists card filenames; user uploads PNGs via XHS app

---

## linkedin

Long-form B2B post. Text-first; carousel ("document post" PDF) is out of
scope for v1 — set `cards: []`.

- No separate title; the first 1–2 lines of `xhs.content` serve as the hook
  (LinkedIn truncates the feed preview around line 3)
- Body: ≤ 3000 chars
- Hashtags: 3–5, each ≤ 50 chars, placed at the END of the body
- Cards: 0 (validator hard-fails if non-empty for linkedin)
- Output: `post.md` is one continuous text block with hashtags appended

**Editorial note**: LinkedIn rewards structured insight + a single sharp
takeaway. Lead with a counter-intuitive 1-line hook, follow with 2–4
short paragraphs of evidence, end with a CTA that asks for a specific
reply ("what's your call here?" beats "what do you think?").

---

## x (twitter)

Single tweet OR a numbered thread. Pick by populating `xhs.content`
(single) or `xhs.thread` (array).

- No title
- Single tweet: `xhs.content` ≤ 280 weight
- Thread: `xhs.thread` array, each item ≤ 280 weight, max 25 posts
- Hashtags: 0–2 (more than 2 measurably reduces reach on X)
- Cards: 0
- Output: `post.md` shows the thread broken into numbered tweets with
  per-tweet character counts, so you can paste each into X individually

### Char counting — important for Chinese / Japanese / emoji

X uses **weighted length**, not raw character count. Per
[twitter-text spec](https://developer.twitter.com/en/docs/counting-characters):

- **Weight 1**: Latin / Latin Extended / IPA / Cyrillic / spacing
  modifier / combining diacritical (~Western scripts)
- **Weight 2**: everything else — CJK Unified Ideographs (Chinese),
  Hiragana / Katakana (Japanese), Hangul Syllables (Korean), full-width
  punctuation, and emoji

So a 280-weight tweet = roughly:
- 280 ASCII chars, **or**
- 140 Chinese / Japanese / Korean chars, **or**
- some mix in between

The validator computes weighted length for X automatically. If your
tweet exceeds 280 weight, the error message shows both raw chars and
weight: `xhs.thread[2] exceeds 280 characters: 312 (CJK weighting: 175 chars → 312 weight)`.

`post.md` for X shows weight side-by-side with raw chars on each tweet
(in zh-mode: `**推文 1/6** (82 chars / 133 weight)` where 推文 = tweet;
in en-mode: `**Tweet 1/6** (...)`) — so when you paste each tweet into
X manually you can verify it's still under 280 weight.

Other platforms (LinkedIn / Instagram) use raw character count;
only X applies CJK weighting.

**Editorial note**: thread mode works best for sequential reasoning (1
hook tweet + 4–6 evidence/example tweets + 1 CTA tweet). Single-tweet
mode works best for a single sharp claim with one piece of evidence.

**post.json shape for thread**:
```json
{
  "platform": "x",
  "xhs": {
    "title": "",
    "content": "",
    "thread": [
      "Hook tweet — counter-intuitive claim, end with hint that proof is below.",
      "Evidence tweet 1 — specific number or example, no fluff.",
      "Evidence tweet 2 — second angle.",
      "CTA tweet — ask for a reply or follow."
    ],
    "tags": ["Amazon"],
    "append_hashtags_to_content": false
  },
  "cards": []
}
```

For thread mode, `append_hashtags_to_content` should be `false`; place
hashtags inline in the last tweet if at all.

---

## instagram

Carousel (1–10 images) + a caption. The most permissive image platform.

- No separate title; the first ~125 chars of caption show in the feed
  (Instagram truncates with "...more" beyond that)
- Caption: ≤ 2200 chars
- Hashtags: 5–30, each ≤ 30 chars. 5–10 is optimal for current reach
  algorithms; 11–30 still works but skips the upper-tier feed boost
- Cards: 1–10 (single image is valid; full carousel = 10)
- Output: same as carousel layout, but `post.md` calls them "Carousel"
  and the body section is labeled "Caption"

**Editorial note**: Instagram audiences scroll faster than XHS. The first
card must work as a thumbnail in the grid view (text large, contrast
strong). Consider 6–8 cards rather than 10 — drop-off is steep after card 7.

---

## Switching platforms

Three ways to set the platform, in priority order:

1. CLI flag: `python3 scripts/make-post-md.py post.json --platform x`
2. `post.json.platform` field (written by `init-day.py` from config)
3. `config.platform`

The validator and renderer always read from `post.json.platform`
(written at init time). The CLI flag on `make-post-md.py` lets you
re-format the same `post.json` for a different platform without
re-rendering — useful when cross-posting.

## Cross-posting workflow

A common pattern: write the post for XHS first (full carousel), then
adapt for LinkedIn (text-only) and X (thread).

```bash
# Day 1: XHS native
python3 scripts/init-day.py --date 2026-05-07
# (edit post.json for XHS, render, etc.)

# Same content, LinkedIn-flavored
python3 scripts/make-post-md.py drafts/2026-05-07/post.json --platform linkedin --output drafts/2026-05-07/post-linkedin.md

# Same content, X thread (you'll need to populate xhs.thread first)
python3 scripts/make-post-md.py drafts/2026-05-07/post.json --platform x --output drafts/2026-05-07/post-x.md
```

The validator won't complain about cross-platform `post.json` shapes as
long as you re-validate against the target platform's config.

## Examples per platform-language combo

The skill ships canonical examples for every language-platform pair:

| File                                       | Language | Platform     |
|--------------------------------------------|----------|--------------|
| `examples/post.example.json`               | zh       | xiaohongshu  |
| `examples/post-en.example.json`            | en       | xiaohongshu  |
| `examples/post-linkedin.example.json`      | en       | linkedin     |
| `examples/post-linkedin-zh.example.json`   | zh       | linkedin     |
| `examples/post-x.example.json`             | en       | x            |
| `examples/post-x-zh.example.json`          | zh       | x            |
| `examples/post-instagram.example.json`     | en       | instagram    |
| `examples/post-instagram-zh.example.json`  | zh       | instagram    |

Copy the closest match and edit. The structure is the same across
languages within a platform; only the strings change.

## Adding a new platform

The presets live in `scripts/validate.py` (`PLATFORM_PRESETS`),
`scripts/init-day.py` (`PLATFORM_DEFAULTS`), and `scripts/make-post-md.py`
(`PLATFORM_FORMAT` + `HEADERS_BY_LANG[*].h1_per_platform` and
`footer_per_platform`). Add an entry to all three; the renderer picks up
new platforms automatically as long as `renders_cards` is set correctly.
