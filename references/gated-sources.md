# Gated sources — fetching X / LinkedIn / wearesellers / BDS / Walmart / YouTube via persistent Playwright profile

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
  `~/.config/wayamzpost/browser-profile/`) — your main session is
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
cd ~/.claude/skills/wayamzpost
npm install                          # installs playwright in skill's node_modules
npx playwright install chromium      # downloads the chromium browser binary
```

### 2. Enable in config.json

If you haven't already created your `config.json` (skipped during the
main install), do that first:

```bash
mkdir -p ~/.config/wayamzpost
cp config.example.json ~/.config/wayamzpost/config.json
$EDITOR ~/.config/wayamzpost/config.json
```

Then within the config file:

```jsonc
{
  "gated_sources": {
    "enabled": true,
    "browser_profile_dir": "~/.config/wayamzpost/browser-profile",
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

You have **two options** — pick based on whether Google blocks the
default Playwright Chromium with "This browser or app may not be
secure" when you try to log in.

#### Option A — Playwright Chromium (default, simpler)

```bash
node ~/.claude/skills/wayamzpost/scripts/fetch-gated.mjs --setup
```

Opens a Chromium window with a fresh profile (separate from your
daily Chrome). Log into the services you want fetched, close the
window or Ctrl+C in the terminal. Cookies save to
`browser_profile_dir`.

⚠ **If Google says "This browser or app may not be secure"** during
X / LinkedIn login, that's because Playwright's Chromium has
detectable automation indicators. **Switch to Option B**.

#### Option B — Real Chrome with a separate debug profile (workaround)

This uses **real Chrome** (not Playwright Chromium), but with a
**separate dedicated profile** — not your daily Chrome's profile.
Google sees real Chrome's fingerprint and doesn't trigger the "may
not be secure" warning. Real Chrome accepts CDP from any origin on
127.0.0.1.

> ⚠️ Why a separate profile, not your daily Chrome's profile?
>
> Chrome 136+ refuses `--remote-debugging-port` with the default user
> profile, by design — it's a security measure to prevent malicious
> sites from sniffing logged-in sessions in your real Chrome. So
> "connect Playwright to your already-logged-in daily Chrome" is
> impossible in modern Chrome. The workaround is a separate profile
> (still real Chrome, just isolated) where you log in once.

Setup:

```bash
cd ~/.claude/skills/wayamzpost
bash scripts/launch-chrome-debug.sh
```

This launches a **separate Chrome window** (parallel to your daily
Chrome — which is untouched) with a profile dir at
`~/.config/wayamzpost/chrome-debug-profile/`. First run is empty.
Log in (in that window) to whichever services you want fetched:

- **X / Twitter** — login required
- **LinkedIn** — login required
- **wearesellers.com** — login required (paid bounty posts get filtered out)
- **billiondollarsellers.com** — login + paid subscription required for
  full body extraction (otherwise only headlines)
- **YouTube** — anonymous works, but logging in surfaces your
  subscriber-only video history if relevant
- **Walmart corporate news** — fully public, no login

Cookies persist in the profile dir, so future runs of the script don't
relaunch Chrome (script is idempotent — sees Chrome already on debug
port and exits early).

Then verify Playwright can connect:

```bash
node scripts/fetch-gated.mjs --connect-cdp --setup
```

If you see `✓ Connected. Active tab title: …`, you're good.

#### Daily fetch

**Option A** (Playwright Chromium):
```bash
node scripts/fetch-gated.mjs --date YYYY-MM-DD
```

**Option B** (real Chrome + separate profile + CDP):
```bash
# Step 1: only if the debug Chrome isn't already running. The launch
# script is idempotent so running it always is safe — if Chrome is
# already up, it exits in <1s.
bash scripts/launch-chrome-debug.sh

# Step 2: fetch
node scripts/fetch-gated.mjs --connect-cdp --date YYYY-MM-DD
```

#### Behavior with your daily Chrome (Option B)

When you run `launch-chrome-debug.sh`:

- A **separate Chrome window** opens with the dedicated profile.
- Your **daily Chrome is not touched**. Different `--user-data-dir`
  values mean macOS treats them as two separate Chrome instances
  running in parallel.
- The `Dock` icon may show the same Chrome icon for both — they share
  the application binary but have separate windows and profiles.

When `fetch-gated.mjs --connect-cdp` runs:

- Opens **new tabs** in the *debug* Chrome (not your daily).
- Reads page DOM (no posts, likes, follows, DMs).
- Closes only the tabs it opened.
- Does not close the debug Chrome window — leave it running.

#### Resetting the debug profile

If logins go bad / you want a clean slate:
```bash
rm -rf ~/.config/wayamzpost/chrome-debug-profile/
bash scripts/launch-chrome-debug.sh
# Log in again in the new Chrome window
```

### 4. Daily fetch

```bash
node ~/.claude/skills/wayamzpost/scripts/fetch-gated.mjs \
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
- **如何应对 Frequently Returned 标签**  ("How to handle the Frequently
  Returned tag" — wearesellers is a Chinese-language seller community,
  so titles and bodies stay in Chinese in this output file)
  https://www.wearesellers.com/q/...
  详细回复内容…  (detailed reply content...)
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
rm -rf ~/.config/wayamzpost/browser-profile/
```
