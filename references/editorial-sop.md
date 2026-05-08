# Editorial SOP — wayamzpost (Amazon-Seller Daily, multi-platform)

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
5. **Source ladder** — every URL was strict-tested 2026-05-07. Each entry
   labeled by what you actually get from it: ✅ dates+content (best),
   🟡 content-but-no-listing-dates (use page order as recency), 🚧 gated
   (need login or paid subscription), ❌ dead (do not use).

   ### Tier A — ✅ Date-stamped, public, automation-friendly

   These are the spine. Listing pages show real dates, no login, ready
   for automated daily fetch. Strict-tested.

   - `https://developer-docs.amazon.com/sp-api/docs/sp-api-release-notes`
     SP-API release notes. Verified May 2026: dated entries Apr 29 /
     Apr 1 / Feb 23. Public.
   - `https://marketplacelearn.walmart.com/releasenotes`
     Walmart Marketplace release notes. Verified: May 7 / May 7 / May 4.
     Replaces dead `marketplace.walmart.com/blog`.
   - `https://www.amz123.com/t` (and `/amazon/news` subsection)
     Cross-border headlines (China-facing). Verified: May 7 17:42 /
     17:13 / 17:04. Public, dated to the minute.
     NOTE: `/t/<slug>` (e.g. `/t/XcuJgR4l`) is INDIVIDUAL article URL,
     not the list. List = `/t` with no suffix.
   - `https://www.helium10.com/category/podcast/`
     Helium 10 / Serious Sellers Podcast. Verified: latest #746 May
     2026 / #745 Apr 27 / #744 Apr 20.
   - `https://corporate.walmart.com/news.sitemap.xml`
     Walmart corporate news sitemap (machine-readable XML with
     `<lastmod>` timestamps). Listing page at `/news` is JS-rendered
     (broken for scrapers) but the sitemap exposes every dated
     article URL — fetch-gated.mjs `fetchWalmartNews()` reads this
     sitemap, picks top N by lastmod, and extracts each article body
     via Playwright. Public, dated to the second.
   - `https://www.youtube.com/feeds/videos.xml?channel_id=<UC...>`
     YouTube channel RSS feed PATTERN. As of 2026-05 the public RSS
     endpoint returns HTTP 404 from many regions — fetch-gated.mjs
     `fetchYouTube()` works around this by visiting `youtube.com/@<handle>/videos`
     via the user's logged-in Chrome (CDP) and scraping the rendered
     `ytd-rich-item-renderer` grid. Configured channels:
     - Helium 10 (`@Helium10`, channel UCpBvckYg2UXArcfzRcjpPjw)
     - My Amazon Guy (`@MyAmazonGuy`, channel UClUSEsDS2sdgNJfCcCM_5Uw)

   ### Tier B — 🟡 Real content, but listing pages don't show dates

   Page works, articles are real, but you can't filter by recency from
   the listing alone — order on the page is the only signal. For
   automated daily use, treat the top N items as "most recent N" and
   trust the page sort.

   - `https://www.aboutamazon.com/news/retail`
     Amazon retail / platform / strategy news. ~469 articles. No
     listing-page dates; click into each for publish timestamp.
   - `https://www.aboutamazon.com/news/policy-news-views`
     Amazon policy news. ~105 articles. Same pattern.
   - `https://advertising.amazon.com/library/newsroom`
     Amazon Ads announcements. (Replaces dead
     `advertising.amazon.com/library`.) Hub-style.
   - `https://advertising.amazon.com/resources/library`
     Amazon Ads resource library (canonical URL — old `/blog`
     301-redirects here). Hub-style; same content surface as
     newsroom with no individual post dates.
   - `https://buywithprime.amazon.com/blog`
     Real blog with dates per post BUT update frequency is low (latest
     post Feb 4 2026 as of audit). Use as supplementary, not daily.
     (Old `buywithprime.com/blog` 301-redirects here.)

   ### Tier C — 🚧 Gated (need login or subscription)

   These have substantive value but require a logged-in browser
   session. For automation, use `scripts/fetch-gated.mjs` (Playwright
   with persistent profile). For manual use, log into your daily
   browser, navigate, copy relevant items into `research/topic.md`.

   - **X / Twitter watchlist** (anti-scraping HTTP 402 — automation
     via the gated-sources fetcher only):
     - Amazon official: `@AmazonNews`, `@AmazonAds`
     - Community: `@AmazonASGTG`
     - Analysts: `@MarketplacePuls` (NOT MarketplacePulse — that
       handle exceeds X's 15-char username limit and doesn't exist),
       `@juokaz`, `@retailgeek`
     - Press: `@spencersoper` (Bloomberg)
   - **LinkedIn watchlist** (login required):
     - Amazon: Andy Jassy (`andy-jassy-8b1615`), Doug Herrington
       (`doug-herrington`), Dharmesh Mehta (`dharmeshmmehta` —
       NOTE the double 'm', single 'm' goes to a different person),
       Steve Pope (`steven-pope` — My Amazon Guy CEO),
       Bradley Sutton (`h10bradley` — Helium 10)
     - Analysts: Juozas Kaziukenas (`juozas` — note: not the same as
       his X handle `juokaz`)
   - `https://www.wearesellers.com/`
     Chinese seller community (知无不言, "say what you know without
     reservation"). Homepage shows titles +
     metadata; full discussion bodies require login. The fetch-gated
     script handles this end-to-end (filters out paid bounty posts,
     extracts question + answer body via `.mod-body` class).
   - `https://www.billiondollarsellers.com/archive`
     Top-operator newsletter. Headlines + dates publicly visible
     (verified May 7 / May 4 / Apr 30 2026); full article body
     requires paid subscription. The fetch-gated script handles BDS
     end-to-end if your Chrome is signed into a paid subscription —
     it walks `/archive`, picks top N article links, and extracts
     each body via `#content-blocks` (verified 2026-05-07, ~9k chars
     of clean post content per article). Without a subscription,
     leave `gated_sources.bds.enabled=false` to avoid noisy
     "body not extracted" lines.
   - `https://sellercentral.amazon.com/forums/c/news-and-announcements`
     Amazon Seller Central forums. Login required. Useful when you're
     researching a specific seller-side issue, less useful for daily
     automated harvest.

   ### Tier D — ❌ DEAD / removed (do NOT use)

   These appeared in v1.0 / v1.3 SOPs but were strict-tested as broken.
   Listed here so future contributors don't re-add them.

   - `https://advertising.amazon.com/library` — 404. Replaced by
     `/library/newsroom`.
   - `https://developer.amazonservices.com/release-notes` — moved to
     `developer-docs.amazon.com/sp-api/docs/sp-api-release-notes`.
   - `https://brandservices.amazon.com/blog` — 301-redirects to
     marketing landing page (`sell.amazon.com/brand-registry`); no
     longer a news source. Brand Registry / Project Zero / IP news is
     announced in `aboutamazon.com/news/policy-news-views` instead.
   - `https://marketplace.walmart.com/blog` — 404. Walmart Marketplace
     news lives at `marketplacelearn.walmart.com/releasenotes`.
   - `https://marketplace-help.walmart.com` — DNS / connection
     refused. No replacement; Walmart help content is at
     `marketplacelearn.walmart.com`.
   - `https://corporate.walmart.com/news` — JavaScript-rendered
     listing; HTML scrapers see only navigation chrome. Individual
     article URLs (e.g. `/news/2026/04/23/walmart-releases-2026-annual-report`)
     work. **Replacement: use `corporate.walmart.com/news.sitemap.xml`**
     (Tier A) which has every article with `<lastmod>` timestamps.
   - `https://www.walmartconnect.com/insights` — only stale 2025
     case studies, not real-time insights. Drop unless you want
     long-form case study material specifically.

   The validator hard-fails if `topic.sources[]` contains a slug stub
   or non-`https://` value. Use Tier A / B URLs above for that field.

   ### Optional automation: `scripts/fetch-gated.mjs`

   For Tier C sources (and a couple of Tier A sources where Playwright
   is needed for body extraction — Walmart corporate articles, YouTube
   channel videos), the skill ships `fetch-gated.mjs` — a Playwright
   script with persistent profile that fetches X / LinkedIn /
   wearesellers / BDS / Walmart-news / YouTube content via your own
   browser session. Read
   [`gated-sources.md`](gated-sources.md) before enabling — real ToS /
   account-suspension risk for automating logged-in services. Optional,
   disabled by default.

   ### Source-decay audit: `scripts/audit-sources.mjs`

   Public sources (Tier A / B) bit-rot — pages get renamed, redirected,
   replaced, or quietly stop updating. To catch decay before it shows up
   as an empty `gated-signal.md`, run monthly:

       node scripts/audit-sources.mjs            # full report to stdout
       node scripts/audit-sources.mjs --json     # machine-readable
       node scripts/audit-sources.mjs --quiet    # only print URLs with issues

   The script hits every Tier A/B URL with plain `fetch()` (no Playwright,
   no auth), reports HTTP status / content-length / last-seen date, and
   flags problems: 4xx/5xx, redirects (often a sign of rename), suspiciously
   small payloads, and dates older than 90 days when a date regex is given.
   Exits non-zero when any URL is flagged so you can wire it into CI.

   ### Tier E — Audience signal only (NEVER copy verbatim)

   - Xiaohongshu seller community — packaging, audience language,
     search phrasing only. Not a content source.
   - Reddit r/AmazonSeller / r/FulfillmentByAmazon — same role.

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
   `点赞 / 收藏 / 关注 / 评论 / 不迷路` (zh-mode tokens: like / save /
   follow / comment / "don't get lost"). En-mode equivalents: `like /
   save / follow / comment / share / subscribe`. Token list configurable
   via `config.cta_tokens`.

Optional 7-8: comparison, examples, objections, recap.

**Psychology**: title + card 1 must use at least one of:
- loss aversion
- curiosity gap
- identity mirroring (e.g. "如果你是亚马逊新卖家…" / "If you're a new
  Amazon seller…")
- insider advantage
- credible urgency (real deadline / real cost)

Show the cost of inaction early. Busy sellers stop for downside, not
generic inspiration. Voice = high-agency, slightly elite: calm, specific,
decisive.

**AI topics specifically**:
- Frame the seller's AI workflow generically (e.g. "AI agent 自动…" /
  "AI agent automates…", "用 AI 帮你算账" / "use AI to handle the
  numbers for you"). Do NOT name your internal tooling.
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
