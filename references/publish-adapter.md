# Publish Adapter — DANGER ZONE

> **The default state of this skill is "generate, don't publish."** This
> document describes the optional bypass — implement only if you fully
> understand the risk.

## Why generate-only is the default

The original author of this methodology had their account flagged twice by
Xiaohongshu's bot-detection in 2026 while running automated publishing.
They quarantined every publish-side script and shifted to manual upload.
Eight months in, manual uploads have had zero account warnings.

Your account isn't fungible. A 6-month-old XHS account with built-up
followers can take a long time to recover from a publishing-bot flag. The
small operational savings from automating uploads are not worth that risk
for most operators.

## When automation might still make sense

- You are testing a new account with no history at risk
- You're a CMS / agency wrapping the skill for a client and accept the
  liability
- You have access to genuine browser automation tooling (like Browser-Use
  with proper session warming) that you've tested independently
- You're publishing to a non-XHS surface (Instagram, LinkedIn, or X via
  official API) where the API is documented and your account is in good
  standing

## How to enable

In `config.json`:

```json
"publish_adapter": {
  "enabled": true,
  "module_path": "/absolute/path/to/your/publish_adapter.py"
}
```

The skill will then call your adapter after `make-post-md.py` completes.
**Nothing in this skill ships an adapter.** You write your own.

## The contract

Your adapter must be a Python file (or a shim that wraps any other tool)
exposing one function:

```python
def publish(post_json_path: str, cards_dir: str, config: dict) -> dict:
    """
    Args:
      post_json_path: absolute path to the rendered post.json
      cards_dir: absolute path to <job_dir>/cards/ containing card_*.png
      config: parsed config.json

    Returns:
      dict with at least:
        - "published": bool
        - "url": str (canonical post URL, optional)
        - "error": str (on failure, optional)
        - any other diagnostic fields you want logged
    """
    ...
```

**Hard constraints on any adapter you write:**

- Must NOT modify `post.json` except to append a publish-result block.
- Must NOT block indefinitely. Apply your own timeout and return
  `{"published": false, "error": "timeout"}`.
- Must NOT auto-retry across days. If today's publish failed, surface the
  failure; the operator decides whether to retry tomorrow.
- Must respect the platform's bot-detection signals. If your adapter sees a
  CAPTCHA, a "verify your account" dialog, or anything that looks like
  scrutiny — **stop and surface the failure**. Don't try to bypass.
- Must NOT touch any system or browser session it didn't itself create.
  Don't re-use the user's regular Chrome profile; spin up your own.

## SKILL.md hard rule

The skill's main `SKILL.md` includes this rule:

> **Do not invoke any publish flow unless `config.publish_adapter.enabled
> === true`.**

Claude (or whoever is driving the skill) must check this flag before
attempting to call the adapter. If the flag is `false`, the workflow stops
at `post.md` and the user uploads manually.

## Recommended alternative: make manual upload painless

Before you build an adapter, ask whether you can automate the *boring*
parts without touching XHS:

- **Transfer**: cards mirrored to `~/Desktop/.../cards/` (built-in via
  `desktop_root`), then AirDrop / iCloud Drive / Google Drive sync to your
  phone — no XHS account contact at all.
- **Copy text**: `post.md` is plain markdown; opening it in a phone editor
  and tap-to-copy gets the body + hashtag block in one action.
- **Schedule reminders**: macOS calendar event → "publish today's XHS card"
  with a deeplink to the cards folder. No third-party tool needed.

Most of the perceived friction of "I have to upload manually" is actually
"the cards aren't on my phone yet." Solve that, and the whole thing becomes
a 90-second task.

## If you ship an adapter anyway

Document, for whoever inherits your account:
- What tool / library does the adapter use? (Playwright? Selenium? An XHS
  agent service?)
- Where does the session/cookie state live?
- What's the rollback path when XHS's anti-bot heuristics shift?
- Who watches for bot-detection warnings, and what triggers a kill-switch?

If you can't answer all four, you don't have a publish adapter — you have a
wager.
