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
5. **Source ladder** — sources are tagged by access type. PUBLIC sources
   can be fetched by any tool (curl, WebFetch, etc.). GATED sources need a
   logged-in human researcher (no automation). DEAD sources used to work
   but no longer do — listed here so previous SOPs aren't followed blindly.

   ### Tier A — Amazon official (PUBLIC, automation-friendly)

   These return real dated content with no login. Verified 2026-05-07.
   - `https://www.aboutamazon.com/news/retail` — platform / strategy
   - `https://www.aboutamazon.com/news/policy-news-views` — policy
   - `https://advertising.amazon.com/library/newsroom` — Amazon Ads
     announcements (replaces the old `advertising.amazon.com/library` 404)
   - `https://advertising.amazon.com/resources/whats-new` — Ads what's new
   - `https://developer-docs.amazon.com/sp-api/docs/sp-api-release-notes` —
     SP-API release notes (replaces the old `developer.amazonservices.com`)
   - `https://buywithprime.amazon.com/blog` — Buy with Prime updates
     (note: the old `buywithprime.com/blog` 301-redirects here)

   ### Tier B — Walmart official (PUBLIC, partially)

   - `https://marketplacelearn.walmart.com/releasenotes` — Walmart
     Marketplace release notes, dated, frequently updated (replaces dead
     `marketplace.walmart.com/blog` and `marketplace-help.walmart.com`)
   - `https://corporate.walmart.com/news` — Walmart leadership /
     strategy news. Page works but article list is JS-rendered;
     individual article URLs are direct-readable.
   - `https://www.walmartconnect.com/insights` — Walmart Connect ads
     content. Real, but mostly case studies (not real-time insights).

   ### Tier C — Operator + analyst signal (GATED for automation)

   These are valuable signals but require a logged-in browser session.
   The validator can't auto-fetch them; they're inputs for a human or
   logged-in agent reading and pasting summaries into `topic.md`.

   - **LinkedIn watchlist** (login required for posts; profiles are
     visible without login but post content is partially gated):
     - Amazon: Andy Jassy (CEO), Doug Herrington (CEO Worldwide Stores),
       Adam Selipsky (advisor), Dharmesh Mehta (VP Worldwide Selling
       Partner Services)
     - Walmart: Doug McMillon (CEO), Casey Carl (CSDO), Whitney Cleary
       (Marketplace lead)
     - Analysts / press: Juozas Kaziukėnas (Marketplace Pulse),
       Krystina Gustafson (Modern Retail), Jason Goldberg (Publicis
       Retail Geek), Andrea Leigh (Allume Group), Rachel Tipograph (MikMak)
     - Search filters: Posts past 24h, language EN, sorted by Recent.

   - **X (Twitter) watchlist** — useful but X has aggressive
     anti-scraping (HTTP 402 / 429 to most automation). Treat as human-
     research signal, not automation:
     - Amazon official: `@AmazonNews`, `@SellingonAmazon`, `@AmazonAds`
     - Analyst signal: `@MarketplacePulse`, `@juokaz` (Juozas
       Kaziukėnas), `@retailgeek` (Jason Goldberg)
     - Reporters covering Amazon: `@spencersoper` (Bloomberg)
     - Practitioner / community: `@BradleyASutton` (Helium 10),
       `@AmazonASGTG` (third-party seller community)

   ### Tier D — Specialist supplemental (mixed access)

   - `https://www.helium10.com/category/podcast/` — PUBLIC. Operator
     interviews and tactical case studies; episode list dated.
   - `https://www.wearesellers.com/` — **GATED**. Homepage shows post
     titles + metadata, but full discussion bodies require login. Use
     `scripts/fetch-gated.mjs` (Tier C automation, see below) or paste
     manually after logging in via your browser.
   - `https://www.amz123.com/t/...` — PUBLIC. Specific topic pages work,
     homepage is just a portal index.
   - `https://www.billiondollarsellers.com/archive` — GATED (paywall;
     headlines visible but full articles require subscription).
   - PPC Land / Marketplace Pulse / Modern Retail / SmartScout / Jungle
     Scout — used only when the topic genuinely needs them; label as
     supplemental, not primary.

   ### Optional automation: `scripts/fetch-gated.mjs`

   For users who want gated-source signal automated, the skill ships
   `fetch-gated.mjs` — a Playwright script with persistent profile that
   fetches X / LinkedIn / wearesellers content using your own browser
   session. **Read [`gated-sources.md`](gated-sources.md) before
   enabling**: there's a real ToS / account-suspension risk with
   automating logged-in services. It's optional and disabled by default.

   ### Tier E — Audience signal only (NEVER copy verbatim)

   - Xiaohongshu seller community — used to calibrate packaging,
     audience language, and search phrasing.
   - Reddit r/AmazonSeller / r/FulfillmentByAmazon — same role.

   ### DEAD URLs (do NOT include in `topic.sources`; they 404 / require login)

   These were in earlier versions of this SOP and are no longer valid:
   - `https://sellercentral.amazon.com/forums/c/news-and-announcements`
     (login required as of 2026)
   - `https://advertising.amazon.com/library` (404; use
     `/library/newsroom` instead)
   - `https://developer.amazonservices.com/release-notes` (moved; use
     `developer-docs.amazon.com/sp-api/docs/sp-api-release-notes`)
   - `https://brandservices.amazon.com/blog` (redirects to a marketing
     landing page; no longer a news source)
   - `https://marketplace.walmart.com/blog` (404; use
     `marketplacelearn.walmart.com/releasenotes` instead)
   - `https://marketplace-help.walmart.com` (DNS / connection refused)

   The validator hard-fails if `topic.sources[]` contains a slug stub or
   non-`https://` value. Real, working URLs only.

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
