# Gated sources — fetching X / LinkedIn / wearesellers via persistent Playwright profile

The validator's [editorial-sop.md](editorial-sop.md) lists "Tier C" sources
(LinkedIn watchlist, X / Twitter accounts) and notes they're **gated**:
they require a logged-in browser session, so the public web fetcher can't
reach them. The optional `scripts/fetch-gated.mjs` plugs that gap by using
your own browser session.

## ⚠️  Read this first

Automating logged-in access to X, LinkedIn, and similar services
**may violate their Terms of Service** and could result in account
warnings or suspension. The script is built for **personal research**
(read-only, modest pace, your own profile only). It is not a commercial
scraping tool. By using it you accept the risk on the account being used.

Concrete mitigations the script applies:
- Uses a **separate Chrome profile** from your daily browser (default
  `~/.config/amazon-xhs-poster/browser-profile/`) — your main session is
  unaffected.
- **Read-only**: never posts, DMs, follows, or interacts.
- **Random delay** between handles (default 3–8 sec) to avoid burst
  patterns.
- **Modest list size** (8 X handles, 5 LinkedIn profiles by default).
- Uses a **standard Chrome user agent**, not a "headless detected"
  signature.

What it does NOT do:
- IP rotation
- Captcha solving
- Account warming / multi-account
- Ban-avoidance heuristics beyond the basics

If your account gets flagged, **stop using the script for that account**.
The skill works without it (you fall back to public Tier A/B sources or
manual paste).

## When to use

Use it when you need fast daily intel from gated sources but don't want
to log into 3 services and scroll feeds yourself every morning. Skip it
if Tier A (Amazon official + Walmart marketplacelearn + Helium 10 podcast)
is already producing enough material.

## Setup

### 1. Install Playwright

The render.mjs uses `npx playwright`, which auto-downloads chromium per
invocation. The fetch-gated.mjs needs the `playwright` npm package
imported as a module. The skill ships a top-level `package.json` that
declares it as a dependency. One-time install from the skill root:

```bash
cd ~/.claude/skills/amazon-xhs-poster
npm install                          # installs playwright in skill's node_modules
npx playwright install chromium      # downloads the chromium browser binary
```

### 2. Enable in config.json

If you haven't already created your `config.json` (skipped during the
main install), do that first:

```bash
mkdir -p ~/.config/amazon-xhs-poster
cp config.example.json ~/.config/amazon-xhs-poster/config.json
$EDITOR ~/.config/amazon-xhs-poster/config.json
```

Then within the config file:

```jsonc
{
  "gated_sources": {
    "enabled": true,
    "browser_profile_dir": "~/.config/amazon-xhs-poster/browser-profile",
    "lookback_hours": 24,
    "fetch_delay_seconds": [3, 8],

    "x": {
      "enabled": true,
      "handles": [
        { "handle": "AmazonNews", "tier": "official" },
        { "handle": "MarketplacePulse", "tier": "analyst" }
        // … see config.example.json for the default 8-handle list
      ]
    },

    "linkedin": {
      "enabled": true,
      "profiles": [
        { "name": "Andy Jassy", "slug": "andyjassy" }
        // …
      ]
    },

    "wearesellers": {
      "enabled": true,
      "top_n": 5
    }
  }
}
```

To find a LinkedIn slug: visit the person's profile in your browser, the
URL is `linkedin.com/in/<slug>/` — copy the `<slug>` part. Some
slugs are vanity (e.g. `andyjassy`), others are auto-generated long
strings (e.g. `doug-herrington-5b4a6710`).

### 3. First-run setup (interactive login)

```bash
node ~/.claude/skills/amazon-xhs-poster/scripts/fetch-gated.mjs --setup
```

This opens a visible Chrome window with a fresh profile. Log into:

- **X**: https://x.com/login
- **LinkedIn**: https://www.linkedin.com/login
- **wearesellers**: https://www.wearesellers.com/account/login/

You can skip any service you don't need. Close the window (or Ctrl+C
in the terminal) when done. Cookies are saved to your
`browser_profile_dir`.

### 4. Daily fetch

```bash
node ~/.claude/skills/amazon-xhs-poster/scripts/fetch-gated.mjs \
  --date 2026-05-08
```

Output:
`<drafts_root>/2026-05-08/research/gated-signal.md` — a single markdown
file structured by source:

```markdown
# Gated-source signal — 2026-05-08

## X / Twitter — last 24h

### @AmazonNews (official)
- 2026-05-07 18:34 — Today we're launching Buy with Prime in five new countries…
  https://x.com/AmazonNews/status/123…

### @MarketplacePulse (analyst)
- …

## LinkedIn — last 24h

### Andy Jassy
- …

## wearesellers.com — top 5 hot posts
- **如何应对 Frequently Returned 标签**
  https://www.wearesellers.com/q/...
  详细回复内容…
```

This file is **input material** for the Stage 2 editorial work, not the
final post. Fold the items you want into `research/topic.md` and
`post.json`. Don't paste it verbatim into XHS / LinkedIn copy — it
contains source attribution that the editorial-sop.md tells you to keep
internal.

## Cookies expiring

X cookies last about 30 days; LinkedIn similar; wearesellers shorter
(seems like 7-14 days). When fetches start failing or returning empty,
re-run `--setup` and log in again.

## Troubleshooting

**"playwright not installed"** — run the install commands in step 1. The
`render.mjs` script's `npx playwright` invocation isn't enough; this
script needs the persistent-context API.

**X tweets show as "no tweets in last 24h" but you know there are some**
— X loads tweets via JS after page load. The script waits 2s and scrolls;
if your network is slow, increase `fetch_delay_seconds` to e.g. `[5, 12]`.

**LinkedIn shows "no posts visible"** — most likely you've been silently
rate-limited. Try `--headed` to see what the page looks like; if there's
a "verify you're a human" prompt, the script can't get past it. Reduce
the number of profiles in your config and retry tomorrow.

**wearesellers doesn't show full content** — your login session may have
expired. Re-run `--setup`.

**"why doesn't the markdown contain ANY tweets"?** — likely the script
launched headless before login was saved. Try `--headed` to see the
browser; if it lands on the login page, run `--setup` first.

## Disabling

Set `gated_sources.enabled: false` in config.json (or simply don't run
the script). The rest of the skill works fine without it.

To wipe the saved profile completely:

```bash
rm -rf ~/.config/amazon-xhs-poster/browser-profile/
```
