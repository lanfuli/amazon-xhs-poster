# wayamzpost

[![CI](https://github.com/lanfuli/wayamzpost/actions/workflows/ci.yml/badge.svg)](https://github.com/lanfuli/wayamzpost/actions/workflows/ci.yml)

> Formerly `amazon-xhs-poster`. Renamed in v1.7.0 since the skill now
> serves 4 platforms, not just Xiaohongshu. Old GitHub URL redirects;
> legacy `XHS_AMAZON_CONFIG` env var + `~/.config/amazon-xhs-poster/`
> path are still honored as fallbacks for existing installs.

A Claude Code skill that runs a daily Amazon-seller content engine: it
collects research signal from 11+ verified sources (X, LinkedIn,
wearesellers, BDS, Walmart, YouTube, plus dated public feeds), turns
your topic-of-the-day into 6–9 image cards + a publish-ready markdown
post, and supports four target platforms (Xiaohongshu / LinkedIn / X /
Instagram) in Chinese or English.

> **Skill identifier:** `wayamzpost` (the directory name and
> `SKILL.md` `name:` field — that's what Claude Code's trigger system
> matches against). **Project brand:** `wayamzpost`. The skill identifier
> and GitHub project name now intentionally match.

This is a packaged version of a methodology that has been running
daily since early 2026. It encodes:

- **A 6-fetcher gated-source pipeline** (X, LinkedIn, wearesellers,
  BDS, Walmart corporate news, YouTube creator-signal) — runs via your
  real Chrome over Chrome DevTools Protocol so logged-in services see
  a normal browser, not a Playwright Chromium fingerprint
- **A monthly source-decay audit** (`scripts/audit-sources.mjs`) that
  hits every Tier A/B URL and flags 4xx / redirects / stale content
- **A 14-day rolling angle rotation** across 6 content categories
  with floor/ceiling quotas (amazon-news, white-hat-tactic,
  risk-warning, ai-workflow, walmart-multi-channel, creator-signal)
- **Title pattern library** (T1–T8) with 7-day no-repeat
- **CTA pattern library** (CTA1–CTA6) with 3-day no-repeat
- **Hashtag tiering** with 60% relevance enforcement
- **A persona voice supremacy rule** that overrides structural
  patterns when needed
- **A confidentiality boundary** that prevents internal tooling and
  paid-feed source names from leaking into public copy
- **Apple-Notes-inspired editorial card design** with theme-tinted
  color psychology (one accent color per content category)
- **5 target platforms** with platform-native char limits, hashtag
  rules, card count ranges, and post.md output layouts; X applies
  CJK weighting per twitter-text spec
- **Both Chinese and English** fully supported on every platform —
  pick any combination of `output_language` + `platform`

## Install

```bash
# 1. Clone into your Claude skills directory. The directory name must
#    match the skill identifier (wayamzpost) so Claude Code's
#    trigger system can find it.
git clone https://github.com/lanfuli/wayamzpost.git \
  ~/.claude/skills/wayamzpost

# 2. Install dependencies — Python 3.9+, Node.js 18+
cd ~/.claude/skills/wayamzpost
npm install                          # playwright + node tests
npx playwright install chromium      # one-time, ~150 MB

# 3. Create your config — pick the variant that matches your default
#    output language. Both have the same schema; defaults differ.
mkdir -p ~/.config/wayamzpost

#    Option A: zh-default (Xiaohongshu native audience):
cp config.example.json ~/.config/wayamzpost/config.json

#    Option B: en-default (LinkedIn / X / Instagram / EN-Xiaohongshu):
cp config-en.example.json ~/.config/wayamzpost/config.json

$EDITOR ~/.config/wayamzpost/config.json
```

> ⚠ **Don't commit `config.json` to a public repo.** It contains your
> persona name, brand string, and `forbidden_brands_in_copy` /
> `forbidden_source_tokens` lists — names you specifically don't want
> showing up in your feed. The skill's `.gitignore` already excludes
> `config.json`, but if you fork this repo or move the config into
> your own repo, double-check it stays out of git. Use
> [`config.example.json`](config.example.json) as the version-controlled
> template instead.

In the config, at minimum:

- Set `persona.brand_cn` (your account brand / display string)
- Set `persona.identity` and `persona.signature`
- Pick a real path for `paths.drafts_root`
- Pick `output_language`: `"zh"` (Chinese, default for the zh-config
  template) or `"en"` (English, default for the en-config template).
  The two configs are independent templates with the same schema; pick
  whichever matches your primary audience.
- Pick `platform`. Choices:
  - `"xiaohongshu"` (default) — 6–9 image cards, ≤20 char title
  - `"linkedin"` — long-form text, ≤3000 chars, 3–5 hashtags, no cards
  - `"x"` — single tweet (≤280) or thread of up to 25, 0–2 hashtags
  - `"instagram"` — 1–10 carousel + ≤2200 char caption, 5–30 hashtags

That's it for first run. The other defaults (angle quotas, forbidden
source tokens, hashtag rules) are sensible starting points; adjust
over time per [`references/customization.md`](references/customization.md).
See [`references/platforms.md`](references/platforms.md) for full
platform-specific rules.

### Optional: enable the gated-source fetcher

Off by default. When enabled, `scripts/fetch-gated.mjs` walks 6
sources daily and writes raw signal into
`<drafts_root>/<DATE>/research/gated-signal.md`. Editorial stage folds
relevant items into `topic.md`.

> ⚠ **`launch-chrome-debug.sh` starts a separate Chrome debug profile.**
> Your normal Chrome session is not touched. The script is idempotent —
> re-running it while the debug Chrome is already listening just exits early.

```bash
# 1. Flip gated_sources.enabled = true in config.json

# 2. Launch a separate Chrome with debug-port enabled (one-time per session):
bash scripts/launch-chrome-debug.sh

# 3. Log in (in that Chrome) to whichever services you want fetched:
#      x.com, linkedin.com, wearesellers.com, billiondollarsellers.com
#    YouTube and Walmart corporate news work without login.

# 4. Daily fetch:
node scripts/fetch-gated.mjs --date 2026-05-08 --connect-cdp
```

**Risk notice:** automating logged-in access to X / LinkedIn may
violate their Terms of Service and could risk account suspension.
Read [`references/gated-sources.md`](references/gated-sources.md)
before enabling. Use only for personal research — never share cookies,
never share what you fetch.

### Optional: monthly source-decay audit

```bash
node scripts/audit-sources.mjs            # full report
node scripts/audit-sources.mjs --json     # machine-readable
node scripts/audit-sources.mjs --quiet    # only print URLs with issues
```

Hits all 11 Tier A/B URLs with plain `fetch()` (no Playwright, no
auth), reports HTTP status / size / last-seen date, flags problems.
Exits non-zero on any flag — wire into CI for monthly cadence.

## How to use it

In a Claude Code session, just say one of:

> Write an Amazon seller post for Xiaohongshu

> 写一条小红书 amazon post

> linkedin amazon post  (or: x amazon thread / instagram amazon carousel)

Claude will recognize the trigger, follow `SKILL.md`, and walk you
through all 6 stages (init day → research → editorial → render → QA →
hand-off). You'll end up with:

- `<drafts_root>/<DATE>/cards/card_01.png … card_0N.png`
- `<drafts_root>/<DATE>/post.md` ← open this on your phone, copy/paste
- `<drafts_root>/<DATE>/post.json` (the canonical artifact, audit-friendly)
- `<drafts_root>/<DATE>/research/gated-signal.md` (if gated_sources is on)

If `config.paths.desktop_root` is set, you also get a mirror copy
under `<desktop_root>/<DATE>/cards/` — handy for AirDrop / iCloud sync.

## Manual flow (without Claude)

Each script is also runnable on its own:

```bash
SKILL=~/.claude/skills/wayamzpost

# 1. Initialize today (idempotent)
python3 $SKILL/scripts/init-day.py

# 2. (Optional) Fetch gated-source signal
node $SKILL/scripts/fetch-gated.mjs --connect-cdp

# 3. Edit research/topic.md and post.json by hand (or via your own LLM)

# 4. Validate
python3 $SKILL/scripts/validate.py <drafts_root>/2026-05-08/post.json --json

# 5. Render PNGs
node $SKILL/scripts/render.mjs <drafts_root>/2026-05-08/post.json

# 6. Build post.md
python3 $SKILL/scripts/make-post-md.py <drafts_root>/2026-05-08/post.json
```

## Source ladder

The skill tracks every public source via the Tier system in
[`references/editorial-sop.md`](references/editorial-sop.md). Summary:

| Tier | Definition | Count |
|---|---|---|
| **A** | Public, dated, automation-friendly | 6 URLs |
| **B** | Public, real content, no listing dates | 5 URLs |
| **C** | Gated — login or subscription required | 6 fetcher targets |
| **D** | Dead / removed (documented to prevent re-adding) | 7 URLs |
| **E** | Audience signal only — never copy verbatim | Reddit, XHS community |

Tier C is automated via `fetch-gated.mjs`; Tier A/B is checked monthly
by `audit-sources.mjs`. Tier D entries are kept in the doc as a
"don't re-add this" record for future contributors.

## What it deliberately does NOT do

- **Auto-publish to Xiaohongshu.** The original author was bot-flagged
  twice while running automated publishing; the skill ships with the
  publish adapter disabled. See
  [`references/publish-adapter.md`](references/publish-adapter.md)
  before enabling.
- **Multi-account management.** One config = one persona. Run two
  configs (different `WAYAMZPOST_CONFIG` paths) if you operate
  multiple accounts.
- **Real-time scraping of paid feeds beyond the 6 supported sources.**
  Source URLs in `topic.sources[]` come from your own research; the
  skill validates they're real `https://` URLs but doesn't fetch them.
- **Image-model card generation.** Card design is deterministic
  HTML/CSS rendered via Playwright. There is no LLM image generation
  in the loop.

## Configuration in detail

See [`references/customization.md`](references/customization.md) for
the full guide on adapting the skill to a different platform /
language / audience / persona.

## Notation

- `${SKILL_DIR}` in commands → substitute literally with your install
  path (e.g. `~/.claude/skills/wayamzpost`), or
  `export SKILL_DIR=~/.claude/skills/wayamzpost` once per shell.
- `<DRAFTS_ROOT>` in example JSON files → not a real syntax. It's a
  placeholder for whatever path you put in `config.paths.drafts_root`.
  The examples use it because the absolute path is environment-specific;
  in your own `post.json` the field will be expanded to a real path
  by `init-day.py`.

## Trouble-shooting

**`python3: command not found`** — try `python` instead. The scripts
use `sys.executable` internally so they call back to whichever Python
you launched them with. Just adjust the install command.

**On Windows** — the skill assumes POSIX paths (`~/`, forward slashes).
WSL2 works out of the box; bare Windows requires translating paths to
`%APPDATA%`-style equivalents in your config.json. PRs welcome.

**"no config.json found"** — the skill resolves config in this order;
first match wins:

1. `--config <path>` CLI arg (when supported by the script)
2. `$WAYAMZPOST_CONFIG` environment variable
3. `~/.config/wayamzpost/config.json` (canonical default)
4. `$XHS_AMAZON_CONFIG` (legacy env var, kept for existing installs)
5. `~/.config/amazon-xhs-poster/config.json` (legacy path)

If none of those exist, the validator refuses to run and prints this
list. Set one of the above to fix.

**"persona.brand_cn must be ..."** — your `post.json.persona.brand_cn`
doesn't match `config.persona.brand_cn`. Re-run `init-day.py` to write
a fresh skeleton.

**"playwright" not found** — run `npx playwright install chromium`
once. Subsequent runs reuse the installed browser.

**`fetch-gated.mjs` says "DevTools endpoint not responding"** — Chrome
isn't running with `--remote-debugging-port=9222`. Run
`bash scripts/launch-chrome-debug.sh` first. See
[`references/gated-sources.md`](references/gated-sources.md).

**`fetch-gated.mjs` says "browser may not be secure" on a login page** —
Google's anti-automation triggered against Playwright Chromium. Use
`--connect-cdp` to attach to your real Chrome instead (the launch
script handles this).

**"public content leaks source token"** — your draft uses a name
that's in `config.forbidden_source_tokens`. Either rewrite the line
to remove it, or trim the list if you don't need that protection.

**"category X would reach Y in last 14 days (ceiling Z)"** — soft-warn,
not blocking. You can ignore it for one post, but it's a real signal
that you're over-indexing on that category.

**"hashtag relevance too low"** — your hashtags don't share enough
tokens with the post's title / topic / first 3 card headlines. Trim
broad-SEO tags and add topic-specific ones.

## Running tests

```bash
# Python (55 tests covering validate / init-day / make-post-md / history,
# including bilingual edge cases and regression tests for the v1.8 audit fixes)
pip3 install pytest
pytest tests/python/ -v

# Node (6 tests covering render.mjs empty-cards path + validation gate)
cd tests/node && npm install && npm test
```

## Production audits (not tests; run on demand)

```bash
# Source-decay check — hits all 11 Tier A/B URLs, flags 4xx / redirects / stale.
# Network-dependent; not in CI. Run monthly.
node scripts/audit-sources.mjs
```

GitHub Actions runs the Python and Node suites on every push to `main`
and every PR. Real PNG rendering (which needs Chromium) is not in CI;
it's exercised via the manual end-to-end smoke tests in the
`examples/` flow.

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including
commercially. Forks are welcome to relicense their derivative work;
just keep the original copyright notice in any portion you reuse
verbatim.
