# Changelog

All notable changes to this project are documented here. Format inspired
by [Keep a Changelog](https://keepachangelog.com/); the project follows
[Semantic Versioning](https://semver.org/) where reasonable.

## [v1.3.0] — 2026-05-07

Correctness pass + formal test infrastructure.

### Fixed (4 real bugs surfaced by an independent audit)

- **must_contain bypass on X**: when `xhs.title` is empty AND
  `xhs.tags` is empty (X allows zero hashtags), the validator silently
  let posts through that never mentioned the required keyword anywhere.
  Replaced the title-only check with a corpus-level check across title /
  body / thread / cards. Now also case-insensitive.
- **ZH headers in English**: ZH users posting to Instagram / X got
  `## Caption` / `## Thread` (English) inside otherwise-Chinese
  `post.md`. Translated to `## 正文` / `## 线程` / `## 卡片`.
- **must_contain case-sensitivity**: `kw in title` was case-sensitive,
  so `must_contain=["Amazon"]` would fail on `title="amazon notes"`.
  All comparisons now `.lower()`-normalized.
- **X content + thread mutual exclusion**: setting both `xhs.content`
  and `xhs.thread` for X used to silently drop one during render. Now
  hard-fails with a clear "mutually exclusive" error.

### Fixed (edge-case gaps)

- **Cold-start info now fires for empty history file** (was missing-only).
- **`xhs.thread` on text-only platform other than X is now hard-error**
  (was soft-warn that silently dropped the thread during render).
- **`design.style` no longer written into text-only-platform skeleton**
  (validator already skipped it; init-day was just adding noise).

### Added (improvements)

- **X thread > 10 posts → soft-warn** (engagement data shows 5–7 is the
  sweet spot; >10 has steep drop-off).
- **Title verbatim in content opening → soft-warn** for carousel
  platforms (visual redundancy when post.md renders both).
- **`render_manifest.json` records `platform`**; `make-post-md.py`
  detects platform drift when `--platform` overrides post.json.
- **`must_contain=[]` emits info** message, consistent with
  `cta_tokens=[]` and `decision_verbs=[]` (all three are valid escape
  hatches but should be visible when used).

### Added (test infrastructure)

- **53 pytest tests** in `tests/python/` covering validate.py,
  init-day.py, make-post-md.py, history.py — every bug fix has a
  regression test.
- **6 vitest tests** in `tests/node/` covering render.mjs's empty-cards
  path and validation gate (real PNG rendering kept out of CI to avoid
  Chromium overhead — exercised manually via examples flow).
- **GitHub Actions CI** in `.github/workflows/ci.yml`: pytest +
  vitest run on every push / PR to `main`. ~30-60s wall time.

### Behavior change to flag

`must_contain` now checks the FULL public corpus (title + content +
thread + cards) instead of title only. Posts that previously passed
because the keyword was only in the hashtag block (not in title /
body / cards) will keep passing — the hashtag-level check is
independent and unchanged. But posts that had the keyword nowhere in
either corpus AND nowhere in hashtags will start failing where they
used to pass. This is the intended fix.

## [v1.2.0] — 2026-05-07

Multi-platform support: same skill, 5 target platforms.

### Added

- **5 platforms** (`config.platform`): xiaohongshu, lemon8, linkedin,
  x, instagram. Each has native validator limits (title cap, body cap,
  hashtag count + length, card count range) and `post.md` output
  layout.
- **Thread mode for X** via `xhs.thread[]` array, max 25 posts each
  ≤280 chars.
- **CJK weighting for X** per twitter-text spec: CJK chars count as 2
  weight toward the 280 cap, so 280-weight = ~140 Chinese chars.
  Errors and post.md surface both raw and weighted counts.
- **`references/platforms.md`** documenting per-platform rules and
  cross-posting workflow.
- **3 new English platform examples** (LinkedIn, X, Instagram) plus
  3 new Chinese platform examples (LinkedIn, X, Instagram).

### Changed

- `render.mjs` now skips cleanly when `cards` is empty (text-only
  platforms LinkedIn / X). Writes empty manifest, marks
  `status.render = 'skipped-no-cards'`, exits 0.
- `make-post-md.py` formats output per-platform: carousel for
  XHS / Lemon8 / IG, long-form for LinkedIn, thread layout for X with
  per-tweet character counts.
- HTML `<html lang>` attribute now reflects `post.json.language`.

## [v1.1.0] — 2026-05-07

Bilingual output. Independent of platform.

### Added

- `config.output_language: "zh" | "en"` (default "zh"). Switching to
  "en" auto-defaults `must_contain` to `["Amazon"]`, `cta_tokens` to
  English follow/like/save/comment/share/subscribe, and decision_verbs
  to English equivalents. Each can still be overridden explicitly.
- ZH and EN headers in `post.md` (h1, section labels, footer).
- English example post (`examples/post-en.example.json`) demonstrating
  the EN flow on XHS.
- Hashtag relevance tokenizer now splits CamelCase
  (e.g. `AmazonSeller` → `amazon` + `seller`).

## [v1.0.0] — 2026-05-06

Initial public release. Single platform (Xiaohongshu), Chinese-first.

### Added

- Deterministic 6–9 image card rendering via Playwright + iPhone-Notes-
  inspired editorial CSS template (`iphone-notes-editorial-v4`).
- Validator-enforced editorial rules: title length, hashtag tiering,
  CTA rotation, source URL hygiene, persona name match.
- 14-day rolling angle rotation across 6 content categories
  (amazon-news, white-hat-tactic, risk-warning, ai-workflow,
  walmart-multi-channel, creator-signal).
- Title pattern library T1–T8 and CTA pattern library CTA1–CTA6.
- Persona voice supremacy rule overriding structural patterns when
  needed.
- Confidentiality boundary keeping internal tooling and paid feed
  names out of public copy via `forbidden_brands_in_copy` and
  `forbidden_source_tokens`.
- 5 utility scripts: `init-day.py`, `validate.py`, `render.mjs`,
  `make-post-md.py`, `history.py`.
- Generate-only by default; opt-in `publish_adapter` hook for those
  who genuinely want to automate publishing.

[v1.3.0]: https://github.com/lanfuli/amazon-xhs-poster/releases/tag/v1.3.0
[v1.2.0]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.1.0...v1.2.0
[v1.1.0]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.0.0...v1.1.0
[v1.0.0]: https://github.com/lanfuli/amazon-xhs-poster/releases/tag/v1.0.0
