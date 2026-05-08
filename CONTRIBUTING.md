# Contributing to wayamzpost

Thanks for considering a contribution. wayamzpost is a personal-skill
repo (not a library), so the bar for changes is "useful for at least
one operator's daily flow." If your fork diverges in a useful way,
PRs welcome — the maintainer reads them.

## Local setup

```bash
git clone https://github.com/lanfuli/wayamzpost.git ~/.claude/skills/wayamzpost
cd ~/.claude/skills/wayamzpost
npm install
npx playwright install chromium
mkdir -p ~/.config/wayamzpost
cp config.example.json ~/.config/wayamzpost/config.json   # or config-en.example.json
$EDITOR ~/.config/wayamzpost/config.json                  # fill in persona
```

## Tests

```bash
pytest tests/python/ -v          # 55 unit tests, ~2s
cd tests/node && npm test        # 6 Node tests, ~1s
node scripts/audit-sources.mjs   # network-dependent; run before publishing changes to sources
```

GitHub Actions runs python + node suites on every push to `main` and
every PR. Real PNG rendering (Playwright) is exercised manually via
the `examples/` flow, not in CI.

## Lock files

`package-lock.json` is `.gitignored` at both the repo root and in
`tests/node/`. This is a deliberate tradeoff: the project is a personal
skill (not a library), and maintaining a checked-in lockfile across a
single-author project added friction without helping reproducibility.
If a contributor PR needs deterministic deps, consider committing the
lockfile in your fork. We may revisit if the contributor base grows.

## Code style

- **Python**: 4-space indent, type hints encouraged, no formatter enforcement.
- **JavaScript / Node**: 2-space indent, ES modules (`type: module` in package.json), no formatter enforcement.
- **Bash**: `set -euo pipefail` at the top. Validate args defensively.
- **Comments**: explain *why*, not *what*. The audit history (commits
  `78befe0`, `e1ae1a6`, post-rename PRs) shows several places where
  the right comment would have prevented bugs.

## Known coverage gaps

- `tests/node/` only has 6 tests for ~3,800 lines of node code.
  Largest gap: render.mjs HTML generation has no snapshot test.
  PRs welcome.
- No JSON schema file for `post.json` / `config.json`. Validation lives
  in `scripts/validate.py` only. PRs welcome.

## Adding a new platform

The presets live in three places:
- `scripts/validate.py` — `PLATFORM_PRESETS` dict
- `scripts/init-day.py` — `PLATFORM_DEFAULTS` dict
- `scripts/make-post-md.py` — `PLATFORM_FORMAT` + `HEADERS_BY_LANG[*].h1_per_platform` + `footer_per_platform`

Add an entry to all three; the renderer picks up new platforms
automatically as long as `renders_cards` is set correctly.

## Adding a new gated source

`scripts/fetch-gated.mjs` runs N fetcher functions in sequence. To add
one:
1. Write `async function fetchYourSource()` following the pattern of
   the existing 6 fetchers (X, LinkedIn, wearesellers, BDS, Walmart, YouTube).
2. Add it to the run-all loop near the bottom of fetch-gated.mjs.
3. Add a config block + `_yoursource_help` to BOTH `config.example.json`
   and `config-en.example.json`, defaulting to `enabled: false`.
4. Document the source in `references/editorial-sop.md` (Tier C section)
   and update `references/gated-sources.md` setup instructions.

## License

[MIT](LICENSE) — same as the repo.
