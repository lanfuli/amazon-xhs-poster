# Changelog

All notable changes to this project are documented here. Format inspired
by [Keep a Changelog](https://keepachangelog.com/); the project follows
[Semantic Versioning](https://semver.org/) where reasonable.

## [v1.7.0] — 2026-05-07

### Added

- **Walmart corporate news fetcher** (`fetchWalmartNews()` in
  `scripts/fetch-gated.mjs`) — pulls `corporate.walmart.com/news.sitemap.xml`
  (machine-readable XML with `<lastmod>` timestamps), filters to
  `/news/YYYY/MM/DD/<slug>` entries, picks top N by lastmod, and uses
  Playwright to extract each article body. Closes the gap that
  `walmart-multi-channel` angle had only 1 source (release notes).

- **YouTube creator-signal fetcher** (`fetchYouTube()` in
  `scripts/fetch-gated.mjs`) — visits `youtube.com/@<handle>/videos`
  via the user's logged-in Chrome (CDP) and scrapes the rendered
  `ytd-rich-item-renderer` grid. Workaround for YouTube's RSS endpoint
  returning HTTP 404 from many regions as of 2026-05. Default
  channels: `@Helium10`, `@MyAmazonGuy`. Fills the previously-empty
  `creator-signal` angle quota.

- **`scripts/audit-sources.mjs`** — periodic decay-check for Tier A/B
  public sources. Hits every URL with plain `fetch()` (no Playwright,
  no auth), reports HTTP status / content-length / last-seen date, and
  flags problems (4xx, redirects, suspiciously small payloads, dates
  >90 days old). Exits non-zero on any flag — wire into CI for
  monthly cadence. Confirmed `advertising.amazon.com/blog` now
  301-redirects to `/resources/library`; updated editorial-sop.md to
  use the canonical URL.

- `gated_sources.walmart` and `gated_sources.youtube` config blocks
  in `config.example.json` and user config schema. Both PUBLIC (no
  login needed) but grouped under `gated_sources` for organizational
  unity — they share the same Playwright/CDP plumbing.

### Changed

- `editorial-sop.md` — Tier A grew from 4 → 6 entries (added Walmart
  corporate news sitemap + YouTube channel pattern). The dead entry
  for `corporate.walmart.com/news` listing now points to the sitemap
  as replacement. Added "Source-decay audit" section pointing at
  `audit-sources.mjs`.

- `fetch-gated.mjs` run-all loop now iterates 6 fetchers (was 4):
  X, LinkedIn, wearesellers, BDS, Walmart-news, YouTube.

### Reasoning

Audit of v1.6.0 source list revealed three structural gaps: (1)
`walmart-multi-channel` angle quota allowed up to 3 cards/day but had
only 1 Walmart source feeding it; (2) `creator-signal` quota allowed
up to 2 cards/day but had zero feeds; (3) every URL was last-verified
on the same day (2026-05-07) with no re-verification cadence baked in.
This release closes all three.

## [v1.6.0] — 2026-05-07

### Added

- **BDS (billiondollarsellers.com) gated fetcher** — new `fetchBDS()`
  in `scripts/fetch-gated.mjs` walks `https://www.billiondollarsellers.com/archive`,
  picks top N article links (deduped by canonical `/p/<slug>`), and
  extracts each body via verified selector chain `#content-blocks` →
  `.dream-post-content-doc` → `.rendered-post`. Confirmed via CDP
  probe 2026-05-07 to extract ~9k chars of clean post content per
  article when the connected Chrome is signed into a paid subscription.

- `gated_sources.bds` config block (`enabled`, `top_n`) in
  `config.example.json` and user config schema. Enabled by default
  with `top_n: 5`; flip to `enabled: false` if you don't have a BDS
  subscription (avoids noisy "body not extracted" lines).

### Changed

- `editorial-sop.md` — BDS entry under Tier C now reflects the
  fetcher integration: subscribed users get full body via
  `--connect-cdp`, non-subscribers see headlines only.

### Reasoning

Previous v1.5.0 audit treated BDS as headline-only because anonymous
WebFetch only sees the article preview. User pointed out that with
a paid subscription the full body IS readable through the
`--connect-cdp` flow we already ship. CDP probe confirmed
`#content-blocks` returns 9006 chars of real content; adding BDS as
a fourth source type costs ~110 LoC and meaningfully expands signal
coverage.

## [v1.4.2] — 2026-05-07

### Added

- **`fetch-gated.mjs --connect-cdp [url]`** — connect to an
  already-running real Chrome via Chrome DevTools Protocol instead of
  launching Playwright's bundled Chromium. Workaround for Google's
  "This browser or app may not be secure" block (which targets
  Playwright Chromium's automation indicators; real Chrome doesn't
  trigger it).

- **`scripts/launch-chrome-debug.sh`** — one-line helper that quits
  Chrome cleanly via AppleScript, then relaunches with
  `--remote-debugging-port=9222` so the fetcher can attach via CDP.
  Supports `--help` and validates the port arg is numeric so it
  doesn't accidentally kill Chrome on malformed input.

- `references/gated-sources.md` — both flow paths (Option A:
  Playwright Chromium with separate profile; Option B: CDP attach to
  real Chrome) documented with explicit "Google blocks me" trigger.

### Behavior

- `--connect-cdp` opens new tabs in your real Chrome for fetch
  targets, reads DOM, closes those tabs only. Does NOT close your
  Chrome window or touch your existing tabs.
- `--connect-cdp --setup` just verifies the connection (Chrome
  reachable + can open a page) — there's no separate "log in to
  Playwright profile" step because you're already logged in via
  your real Chrome.
- The persistent-profile flow (Option A) is still the default.

## [v1.5.0] — 2026-05-07

Strict source-ladder audit + Tier-based reorganization.

### Changed

- **Every URL in `references/editorial-sop.md` source ladder retested
  individually via WebFetch.** Each source is now classified by what
  you actually get from it:
  - **Tier A** (✅): dated content, public, automation-ready —
    SP-API release notes, Walmart Marketplace release notes, amz123/t,
    helium10 podcast.
  - **Tier B** (🟡): real content but listing pages don't show dates,
    use page order as recency proxy — aboutamazon.com news/retail and
    news/policy-news-views, advertising.amazon.com/library/newsroom
    and /blog, buywithprime.amazon.com/blog (sparse updates).
  - **Tier C** (🚧): gated, login required — wearesellers (handled by
    fetch-gated.mjs), billiondollarsellers (paywall body but public
    headlines), Seller Central forums.
  - **Tier D** (❌): explicitly listed DEAD — `advertising.amazon.com/library`
    (404), `developer.amazonservices.com/release-notes` (moved),
    `brandservices.amazon.com/blog` (redirects to marketing),
    `marketplace.walmart.com/blog` (404), `marketplace-help.walmart.com`
    (DNS), `corporate.walmart.com/news` (JS-rendered, scraper-blind),
    `walmartconnect.com/insights` (only stale 2025 case studies).
- Doug McMillon removed from default LinkedIn watchlist (consistently
  empty — he doesn't post on LinkedIn). Profile count reduced 7 → 6.

### Why retesting was needed

User flagged that prior audits accepted homepage-loads-OK as proof of
"working", but didn't verify dated-content visibility. Strict pass
revealed:
- 5 of 8 Amazon official URLs lack listing-page dates (still useful
  but you can't filter by recency programmatically — need to crawl
  each article).
- 3 of 4 Walmart URLs are dead or stale; only marketplacelearn works.
- The "is this URL useful for daily automated fetching" answer is
  different from "does the URL respond 200 OK".

### Self-correction

Two prior errors traced back to the same root: I declared sources
"WORKS PUBLICLY" without verifying dated content. Going forward, every
default URL gets the strict test (quote 3 most recent dated headlines
or admit it's missing) before being added to the SOP.

## [v1.4.1] — 2026-05-07

Doc-only patch.

### Fixed

- `references/editorial-sop.md` — corrected `amz123.com` URL pattern.
  v1.3.1 listed `https://www.amz123.com/t/...` as the cross-border
  headlines URL, but `/t/<slug>` is actually the URL pattern for
  *individual* articles. The list page is `/t` (no slug). Also added
  `/amazon/news` as the Amazon-specific subsection. Both confirmed
  PUBLIC (no login required) via WebFetch with dated 2026-05-07
  content visible.

This is the second time a source URL was misclassified during
ladder audits. Future source-ladder verification: each URL gets
its own WebFetch probe — homepage accessibility doesn't imply
arbitrary path accessibility.

## [v1.4.0] — 2026-05-07

Optional gated-source automation: pull research signal from X / LinkedIn /
wearesellers.com using a persistent Playwright profile (the user's own
logged-in session, kept in a separate browser profile from their daily
browser).

### Added

- **`scripts/fetch-gated.mjs`** — Playwright-driven fetcher. First run
  with `--setup` opens a visible Chrome window, the user logs in to X /
  LinkedIn / wearesellers manually, profile saves. Subsequent runs go
  headless and reuse cookies. Outputs
  `<drafts_root>/<DATE>/research/gated-signal.md` for the editorial
  stage to fold into `topic.md`.
- **`config.gated_sources` block** — `enabled` flag (default false),
  `browser_profile_dir`, configurable per-source lists (X handles,
  LinkedIn slugs, wearesellers top-N) and lookback window.
- **`references/gated-sources.md`** — full setup guide, ToS / risk
  warning, troubleshooting (cookies expired / rate-limited / no
  posts visible).
- **Top-level `package.json`** — declares `playwright` as the
  fetcher's dep. Users run `npm install` once at skill root, then
  `npx playwright install chromium`. The render.mjs continues to use
  `npx playwright` per-invocation independently.
- **8 default X handles + 5 LinkedIn defaults** preconfigured: official
  (@AmazonNews, @SellingonAmazon, @AmazonAds), analysts
  (@MarketplacePulse, @juokaz, @retailgeek), press (@spencersoper),
  practitioner (@BradleyASutton); LinkedIn — Andy Jassy / Doug
  Herrington / Dharmesh Mehta / Doug McMillon / Juozas Kaziukenas.

### Changed

- **`references/editorial-sop.md`** — corrected `wearesellers.com`
  classification from PUBLIC to GATED (homepage shows titles, full
  bodies require login). Pointer added to fetch-gated.mjs as the
  optional automation path.
- **SKILL.md tree** updated to include the new script and reference
  doc.

### Risk note

This release adds opt-in automation against logged-in services. X and
LinkedIn ToS prohibit automated access; running fetch-gated.mjs against
your account carries a real (low-but-nonzero) suspension risk. The
script uses a separate browser profile, runs read-only, paces requests
with random delays, and is **disabled by default**. See
`references/gated-sources.md` before enabling.

## [v1.3.1] — 2026-05-07

Doc-only release. Probed all 16 documented data source URLs in the
editorial SOP source ladder; replaced 6 dead URLs with current working
equivalents, flagged 4 gated sources, added X/Twitter handles tier as
human-research signal (NOT automation — that comes in v1.4.0).

Plus housekeeping: removed stale "Threads" platform mentions, fixed
README clone URL placeholder, added CHANGELOG.md (this file).

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
  `post.md`. Translated to `## 正文` (Body) / `## 线程` (Thread) /
  `## 卡片` (Cards).
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

[v1.5.0]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.4.0...main
[v1.4.2]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.4.1...v1.4.2
[v1.4.1]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.4.0...v1.4.1
[v1.4.0]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.3.1...v1.4.0
[v1.3.1]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.3.0...v1.3.1
[v1.3.0]: https://github.com/lanfuli/amazon-xhs-poster/releases/tag/v1.3.0
[v1.2.0]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.1.0...v1.2.0
[v1.1.0]: https://github.com/lanfuli/amazon-xhs-poster/compare/v1.0.0...v1.1.0
[v1.0.0]: https://github.com/lanfuli/amazon-xhs-poster/releases/tag/v1.0.0
