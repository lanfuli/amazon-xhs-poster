# amazon-xhs-poster

A Claude Code skill that turns daily Amazon-seller commentary into a
ready-to-post Xiaohongshu (小红书) carousel: 6–9 deterministic image cards
plus a markdown file with the title, body, and hashtag block. You upload
manually from your phone.

This is a packaged version of a methodology that has been running daily
since early 2026. It encodes:

- A 14-day rolling angle rotation across 6 content categories
- Title pattern library (T1–T8) with 7-day no-repeat
- CTA pattern library (CTA1–CTA6) with 3-day no-repeat
- Hashtag tiering with 60% relevance enforcement
- A persona voice supremacy rule that overrides structural patterns when
  needed
- A confidentiality boundary that prevents internal tooling and paid
  feed names from leaking into public copy
- Apple-Notes-inspired editorial card design with theme-tinted color
  psychology (one accent color per content category)
- 5 target platforms (Xiaohongshu / Lemon8 / LinkedIn / X / Instagram)
  with platform-native char limits, hashtag rules, and post.md output
  layouts; X applies CJK weighting per twitter-text spec
- Both Chinese (中文) and English fully supported on every platform —
  pick any combination of `output_language` + `platform`

## Install

```bash
# 1. Clone (or unzip) into your Claude skills directory
git clone <repo-url> ~/.claude/skills/amazon-xhs-poster

# 2. Install dependencies
#    Requires: Python 3.9+, Node.js 18+
pip3 install --upgrade pip          # zoneinfo is stdlib in 3.9+
npx playwright install chromium     # one-time, ~150 MB

# 3. Create your config
mkdir -p ~/.config/amazon-xhs-poster
cp ~/.claude/skills/amazon-xhs-poster/config.example.json \
   ~/.config/amazon-xhs-poster/config.json
$EDITOR ~/.config/amazon-xhs-poster/config.json
```

> ⚠ **Don't commit `config.json` to a public repo.** It contains your
> persona name, brand string, and `forbidden_brands_in_copy` /
> `forbidden_source_tokens` lists — names you specifically don't want
> showing up in your feed. The skill's `.gitignore` already excludes
> `config.json`, but if you fork this repo or move the config into your
> own repo, double-check it stays out of git. Use
> [`config.example.json`](config.example.json) as the version-controlled
> template instead.

In the config, at minimum:

- Set `persona.brand_cn` (your account brand / display string)
- Set `persona.identity` and `persona.signature`
- Pick a real path for `paths.drafts_root`
- Pick `output_language`: `"zh"` (default — Chinese) or `"en"` (English)
- Pick `platform`: which surface you're publishing to. Choices:
  - `"xiaohongshu"` (default) — 6–9 image cards, ≤20 char title
  - `"lemon8"` — 6–10 image cards, ≤30 char title
  - `"linkedin"` — long-form text, ≤3000 chars, 3–5 hashtags, no cards
  - `"x"` — single tweet (≤280) or thread of up to 25, 0–2 hashtags
  - `"instagram"` — 1–10 carousel + ≤2200 char caption, 5–30 hashtags

That's it for first run. The other defaults (angle quotas, forbidden source
tokens, hashtag rules) are sensible starting points; adjust over time per
[`references/customization.md`](references/customization.md).
See [`references/platforms.md`](references/platforms.md) for full
platform-specific rules and cross-posting workflows.

## How to use it

In a Claude Code session, just say:

> 写一条小红书 amazon post

Claude will recognize the trigger, follow `SKILL.md`, and walk you through
all 6 stages (init day → research → editorial → render → QA → hand-off).
You'll end up with:

- `<drafts_root>/<DATE>/cards/card_01.png … card_0N.png`
- `<drafts_root>/<DATE>/post.md` ← open this on your phone and copy/paste
- `<drafts_root>/<DATE>/post.json` (the canonical artifact, audit-friendly)

If `config.paths.desktop_root` is set, you also get a mirror copy under
`<desktop_root>/<DATE>/cards/` — handy for AirDrop / iCloud sync.

## Manual flow (without Claude)

Each script is also runnable on its own:

```bash
SKILL=~/.claude/skills/amazon-xhs-poster

# 1. Initialize today (idempotent)
python3 $SKILL/scripts/init-day.py

# 2. Edit research/topic.md and post.json by hand (or via your own LLM)

# 3. Validate
python3 $SKILL/scripts/validate.py <drafts_root>/2026-05-06/post.json --json

# 4. Render PNGs
node $SKILL/scripts/render.mjs <drafts_root>/2026-05-06/post.json

# 5. Build post.md
python3 $SKILL/scripts/make-post-md.py <drafts_root>/2026-05-06/post.json
```

## What it deliberately does NOT do

- **Auto-publish to Xiaohongshu.** The original author was bot-flagged
  twice while running automated publishing; the skill ships with the
  publish adapter disabled. See
  [`references/publish-adapter.md`](references/publish-adapter.md) before
  enabling it.
- **Multi-account management.** One config = one persona. Run two configs
  (different `XHS_AMAZON_CONFIG` paths) if you operate multiple accounts.
- **Real-time scraping of paid feeds.** Source URLs come from your own
  research; the skill validates that they're real `https://` URLs but
  doesn't fetch them.
- **Image-model card generation.** Card design is deterministic HTML/CSS
  rendered via Playwright. There's no LLM image generation in the loop.

## Configuration in detail

See [`references/customization.md`](references/customization.md) for the
full guide on adapting the skill to a different platform / language /
audience / persona.

## Notation

- `${SKILL_DIR}` in commands → substitute literally with your install path
  (e.g. `~/.claude/skills/amazon-xhs-poster`), or
  `export SKILL_DIR=~/.claude/skills/amazon-xhs-poster` once per shell.
- `<DRAFTS_ROOT>` in example JSON files → not a real syntax. It's a
  placeholder for whatever path you put in `config.paths.drafts_root`. The
  examples use it because the absolute path is environment-specific; in
  your own `post.json` the field will be expanded to a real path by
  `init-day.py`.

## Trouble-shooting

**`python3: command not found`** — try `python` instead. The scripts use
`sys.executable` internally so they call back to whichever Python you
launched them with. Just adjust the install command.

**On Windows** — the skill assumes POSIX paths (`~/`, forward slashes).
WSL2 works out of the box; bare Windows requires translating paths to
`%APPDATA%`-style equivalents in your config.json. PRs welcome to make
this nicer.

**"no config.json found"** — set `XHS_AMAZON_CONFIG` to your config path,
or place it at `~/.config/amazon-xhs-poster/config.json`.

**"persona.brand_cn must be ..."** — your `post.json.persona.brand_cn`
doesn't match `config.persona.brand_cn`. Re-run `init-day.py` to write a
fresh skeleton.

**"playwright" not found** — run `npx playwright install chromium` once.
Subsequent runs reuse the installed browser.

**"public content leaks source token"** — your draft uses a name that's in
`config.forbidden_source_tokens`. Either rewrite the line to remove it, or
trim the list if you don't need that protection.

**"category X would reach Y in last 14 days (ceiling Z)"** — soft-warn,
not blocking. You can ignore it for one post, but it's a real signal that
you're over-indexing on that category.

**"hashtag relevance too low"** — your hashtags don't share enough tokens
with the post's title / topic / first 3 card headlines. Trim broad-SEO
tags and add topic-specific ones.

## License

[MIT](LICENSE) — free to use, modify, and redistribute, including
commercially. Forks are welcome to relicense their derivative work; just
keep the original copyright notice in any portion you reuse verbatim.
