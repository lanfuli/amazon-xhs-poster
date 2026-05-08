#!/usr/bin/env python3
"""Initialize today's wayamzpost draft directory.

Creates:
  <drafts_root>/<DATE>/
    research/
      topic.md                 (empty stub for the editorial agent to fill)
      recent_history.json      (built by history.py)
      recent_history.md
    cards/                     (empty; renderer fills it later)
    post.json                  (skeleton — persona + paths from config; topic / cards left empty)

Defaults today's date to America/Los_Angeles (override with --date YYYY-MM-DD).

Resolution order for config:
  1. --config <path>
  2. WAYAMZPOST_CONFIG env var
  3. XHS_AMAZON_CONFIG env var (legacy)
  4. ~/.config/wayamzpost/config.json
  5. ~/.config/amazon-xhs-poster/config.json (legacy)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

DEFAULT_CONFIG_PATH = Path("~/.config/wayamzpost/config.json").expanduser()
LEGACY_CONFIG_PATH = Path("~/.config/amazon-xhs-poster/config.json").expanduser()


def resolve_config_path(cli_path: str | None) -> Path | None:
    if cli_path:
        return Path(cli_path).expanduser().resolve()
    env = os.environ.get("WAYAMZPOST_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    legacy_env = os.environ.get("XHS_AMAZON_CONFIG")
    if legacy_env:
        return Path(legacy_env).expanduser().resolve()
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH
    if LEGACY_CONFIG_PATH.exists():
        return LEGACY_CONFIG_PATH
    return None


def load_config(cli_path: str | None) -> tuple[dict, Path]:
    path = resolve_config_path(cli_path)
    if not path:
        sys.exit(
            "no config.json found; copy config.example.json from the skill, "
            "fill it in, and either pass --config <path>, set WAYAMZPOST_CONFIG, "
            f"or place it at {DEFAULT_CONFIG_PATH} "
            f"(legacy fallback: {LEGACY_CONFIG_PATH})"
        )
    if not path.exists():
        sys.exit(f"config not found: {path}")
    return json.loads(path.read_text()), path


def today_pt() -> str:
    return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")


def expand(p: str | None) -> Path | None:
    if not p:
        return None
    return Path(p).expanduser().resolve()


TOPIC_STUB = """# Topic — {date}

> Fill this in during Stage 1 (research). Drop links inside the Sources block;
> the editorial stage reads from this file plus `research/recent_history.md`.

## Selection

- **Category**: (one of: amazon-news / white-hat-tactic / risk-warning / ai-workflow / walmart-multi-channel / creator-signal)
- **Selection reason**: (e.g. "walmart-multi-channel: 14d count=0, floor=1, gap=∞")
- **Angle (1-2 sentences)**:
- **Why now**:

## Sources (must be real https:// URLs)

1.
2.
3.

## Public-source policy

Do not name sites or research stack in the public-facing copy
(`xhs.content`, `xhs.thread`, or any card body). Treat as internal
unless the user explicitly asks for attribution.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="path to config.json")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: today PT)")
    parser.add_argument("--skip-history", action="store_true",
                        help="don't run history.py; leave recent_history.* unbuilt")
    args = parser.parse_args()

    config, config_path = load_config(args.config)
    date = args.date or today_pt()

    paths_cfg = config.get("paths") or {}
    drafts_root = expand(paths_cfg.get("drafts_root"))
    if not drafts_root:
        sys.exit("config.paths.drafts_root is empty — set it in your config.json")

    # ─── Pre-flight checks BEFORE any mkdir / disk write ───────────────
    # Order matters: catch unfilled config values FIRST so we don't leave
    # orphan empty drafts_root / job_dir / cards/ trees behind when the
    # user is just trying things out with the unedited config template.

    persona_cfg = config.get("persona") or {}
    sig_raw = (persona_cfg.get("signature") or "").strip()
    brand_raw = (persona_cfg.get("brand_cn") or "").strip()
    identity_raw = (persona_cfg.get("identity") or "").strip()
    if not sig_raw and not brand_raw:
        sys.exit(
            "config.persona.brand_cn and config.persona.signature are BOTH empty. "
            "Set at least one (typically brand_cn — signature defaults to it). "
            "Without a signature, every rendered card footer will be blank."
        )
    placeholder_fields = []
    for field, value in (("brand_cn", brand_raw), ("identity", identity_raw), ("signature", sig_raw)):
        if value.startswith("REPLACE_ME"):
            placeholder_fields.append(field)
    if placeholder_fields:
        sys.exit(
            f"config.persona has unfilled REPLACE_ME placeholder(s): {placeholder_fields}. "
            "Open your config.json and replace the REPLACE_ME values with your "
            "actual brand / identity / signature before initializing a draft."
        )

    language = (config.get("output_language") or "zh").strip().lower()
    if language not in ("zh", "en"):
        language = "zh"

    platform = (config.get("platform") or "xiaohongshu").strip().lower()
    PLATFORM_DEFAULTS = {
        "xiaohongshu": {"title_max": 20, "card_min": 6, "card_max": 9, "renders_cards": True},
        "linkedin":    {"title_max": 0,  "card_min": 0, "card_max": 0,  "renders_cards": False},
        "x":           {"title_max": 0,  "card_min": 0, "card_max": 0,  "renders_cards": False},
        "instagram":   {"title_max": 0,  "card_min": 1, "card_max": 10, "renders_cards": True},
    }
    if platform not in PLATFORM_DEFAULTS:
        # Surface invalid platform clearly. Common case: user upgraded from
        # an older version that supported `lemon8` (removed in v1.8.0).
        print(
            f"warning: unknown platform={platform!r} in config; falling back to "
            f"'xiaohongshu'. supported: {sorted(PLATFORM_DEFAULTS)}",
            file=sys.stderr,
        )
        platform = "xiaohongshu"
    p_defaults = PLATFORM_DEFAULTS[platform]

    attention_goal_default = {
        "zh": "3秒内停留并产生关注/收藏意图",
        "en": "Stop the scroll in 3 seconds, earn a follow or save",
    }[language]

    # ─── All pre-flight checks passed; safe to create directories ──────

    try:
        drafts_root.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        sys.exit(
            f"config.paths.drafts_root ({drafts_root}) cannot be created: {err}\n"
            "Check the path exists in a writable location and that any "
            "parent symlinks resolve to a real directory."
        )
    # Probe writability — mkdir succeeds silently for symlinks-to-nowhere
    # and read-only volumes; downstream writes then fail cryptically.
    probe = drafts_root / ".wayamzpost-write-probe"
    try:
        probe.write_text("ok")
        probe.unlink()
    except OSError as err:
        sys.exit(
            f"config.paths.drafts_root ({drafts_root}) is not writable: {err}\n"
            "If this path is a symlink, verify its target exists and is writable."
        )

    job_dir = drafts_root / date
    research_dir = job_dir / "research"
    cards_dir = job_dir / "cards"
    job_dir.mkdir(parents=True, exist_ok=True)
    research_dir.mkdir(parents=True, exist_ok=True)
    cards_dir.mkdir(parents=True, exist_ok=True)

    desktop_root_raw = paths_cfg.get("desktop_root")
    if desktop_root_raw:
        desktop_root = expand(desktop_root_raw) / date
        (desktop_root / "cards").mkdir(parents=True, exist_ok=True)
        (desktop_root / "meta").mkdir(parents=True, exist_ok=True)
    else:
        desktop_root = None
    placeholder_fields = []
    for field, value in (("brand_cn", brand_raw), ("identity", identity_raw), ("signature", sig_raw)):
        if value.startswith("REPLACE_ME"):
            placeholder_fields.append(field)
    if placeholder_fields:
        sys.exit(
            f"config.persona has unfilled REPLACE_ME placeholder(s): {placeholder_fields}. "
            "Open your config.json and replace the REPLACE_ME values with your "
            "actual brand / identity / signature before initializing a draft."
        )

    post_json_path = job_dir / "post.json"
    if not post_json_path.exists():
        skeleton = {
            "version": "1.1",
            "job_date": date,
            "language": language,
            "platform": platform,
            "persona": {
                "identity": persona_cfg.get("identity", ""),
                "brand_cn": persona_cfg.get("brand_cn", ""),
                "location": persona_cfg.get("location", ""),
                "years_experience": persona_cfg.get("years_experience", 0),
                "voice": persona_cfg.get("voice", ""),
                "signature": (
                    persona_cfg.get("signature")
                    or persona_cfg.get("brand_cn")
                    or ""
                ),
            },
            "topic": {
                "category": "",
                "angle": "",
                "why_now": "",
                "selection_reason": "",
                "sources": []
            },
            "seo": {
                "primary_keywords": [],
                "secondary_keywords": [],
                "hashtags": []
            },
            "strategy": {
                "attention_goal": attention_goal_default,
                "psychology_hooks": [],
                "ai_positioning": "",
                "dedupe_window_days": int(paths_cfg.get("history_lookback_days") or 30)
            },
            "design": (
                {
                    # Carousel platforms: full design block including style & ratio
                    "theme": "auto",
                    "style": "iphone-notes-editorial-v4",
                    "ratio": "3:4",
                    "width": 1080,
                    "height": 1440,
                    "cards": p_defaults["card_min"],
                    "cards_min": p_defaults["card_min"],
                    "cards_max": p_defaults["card_max"],
                    "accent_strategy": "color-psychology",
                    "renders_cards": True,
                }
                if p_defaults["renders_cards"]
                else {
                    # Text-only platforms (LinkedIn, X): no card rendering, so
                    # design.style and ratio are meaningless. Keep cards=0 only.
                    "cards": 0,
                    "cards_min": 0,
                    "cards_max": 0,
                    "renders_cards": False,
                }
            ),
            "xhs": {
                "title": "",
                "title_max_length": int(
                    (config.get("title_constraints") or {}).get("max_chars")
                    or p_defaults["title_max"]
                    or 0
                ),
                "opening_hook": "",
                "content": "",
                "cta": "",
                "tags": [],
                "thread": [],
                "append_hashtags_to_content": True,
                "schedule_at": "",
                "delivery_mode": "manual"
            },
            "cards": [],
            "paths": {
                "job_dir": str(job_dir),
                "desktop_root": str(desktop_root) if desktop_root else "",
                "research_note": str(research_dir / "topic.md"),
                "post_json": str(post_json_path),
                "render_manifest": str(cards_dir / "render_manifest.json"),
                "cards_dir": str(cards_dir)
            },
            "status": {
                "research": "pending",
                "editorial": "pending",
                "render": "pending",
                "qa": "pending",
                "publish": "manual"
            },
            "qa_notes": [],
            "job_type": "daily"
        }
        post_json_path.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2) + "\n")
        print(f"created skeleton {post_json_path}")
    else:
        print(f"reusing existing {post_json_path}")

    topic_md = research_dir / "topic.md"
    if not topic_md.exists():
        topic_md.write_text(TOPIC_STUB.format(date=date))
        print(f"created topic stub {topic_md}")

    if not args.skip_history:
        history_script = Path(__file__).parent / "history.py"
        history_args = [
            sys.executable,
            str(history_script),
            "--config", str(config_path),
            "--output-json", str(research_dir / "recent_history.json"),
            "--output-md", str(research_dir / "recent_history.md"),
        ]
        result = subprocess.run(history_args, capture_output=True, text=True)
        if result.returncode != 0:
            sys.stderr.write(result.stdout)
            sys.stderr.write(result.stderr)
            sys.exit(f"history.py failed (rc={result.returncode})")
        print(result.stdout.strip())

    print(f"\nready: {job_dir}")
    # Platform-aware next-step hint. Carousel platforms (XHS, IG) need
    # the user to author 6+ cards; text-only platforms (LinkedIn, X)
    # write content / thread directly.
    if p_defaults["renders_cards"]:
        print("next: fill in research/topic.md, then write topic + cards into post.json")
    elif platform == "x":
        print("next: fill in research/topic.md, then write topic + content (or xhs.thread[]) into post.json")
    else:
        print("next: fill in research/topic.md, then write topic + xhs.content into post.json")


if __name__ == "__main__":
    main()
