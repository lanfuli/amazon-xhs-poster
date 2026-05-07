#!/usr/bin/env python3
"""Render `post.md` from `post.json` + `cards/render_manifest.json`.

The markdown file is what the user actually opens on their phone (or copy-
pastes into the Xiaohongshu app) when publishing manually:

  # 小红书亚马逊主题 — YYYY-MM-DD
  ## 标题       <xhs.title>
  ## 正文       <xhs.content verbatim, with \\n preserved>
  ## Hashtags   <space-joined #tags>
  ## 卡片清单   - card_01.png
                - card_02.png
                ...
  ---
  生成于 <ISO timestamp PT> · 发布方式：手动上传到小红书 APP

Writes to <job_dir>/post.md unless --output is given.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


HEADERS_BY_LANG = {
    "zh": {
        "h1_default": "小红书亚马逊主题",
        "h1_per_platform": {
            "xiaohongshu": "小红书亚马逊主题",
            "lemon8":      "Lemon8 亚马逊主题",
            "linkedin":    "LinkedIn 亚马逊帖子",
            "x":           "X 亚马逊帖子",
            "instagram":   "Instagram 亚马逊主题",
        },
        "title": "标题",
        "body": "正文",
        "caption": "正文",
        "hashtags": "话题标签",
        "cards": "卡片清单",
        "carousel": "卡片",
        "thread": "线程",
        "tweet": "推文",
        "post": "贴子",
        "empty": "_(未填)_",
        "no_render": "_(尚未渲染，先跑 render.mjs)_",
        "footer_per_platform": {
            "xiaohongshu": "生成于 {ts} · 发布方式：手动上传到小红书 APP",
            "lemon8":      "生成于 {ts} · 发布方式：手动上传到 Lemon8 APP",
            "linkedin":    "生成于 {ts} · 发布方式：复制粘贴到 LinkedIn",
            "x":           "生成于 {ts} · 发布方式：复制粘贴到 X / Twitter",
            "instagram":   "生成于 {ts} · 发布方式：手动上传到 Instagram",
        },
    },
    "en": {
        "h1_default": "Amazon Seller Note",
        "h1_per_platform": {
            "xiaohongshu": "Amazon Seller Note",
            "lemon8":      "Amazon Seller Note (Lemon8)",
            "linkedin":    "Amazon Seller Post (LinkedIn)",
            "x":           "Amazon Seller Post (X)",
            "instagram":   "Amazon Seller Carousel (Instagram)",
        },
        "title": "Title",
        "body": "Body",
        "caption": "Caption",
        "hashtags": "Hashtags",
        "cards": "Cards",
        "carousel": "Carousel",
        "thread": "Thread",
        "tweet": "Tweet",
        "post": "Post",
        "empty": "_(empty)_",
        "no_render": "_(not rendered yet — run render.mjs first)_",
        "footer_per_platform": {
            "xiaohongshu": "Generated {ts} · publish manually to Xiaohongshu",
            "lemon8":      "Generated {ts} · publish manually to Lemon8",
            "linkedin":    "Generated {ts} · paste manually into LinkedIn",
            "x":           "Generated {ts} · paste manually into X / Twitter",
            "instagram":   "Generated {ts} · publish manually to Instagram",
        },
    },
}


PLATFORM_FORMAT = {
    "xiaohongshu": "carousel",
    "lemon8":      "carousel",
    "instagram":   "carousel-with-caption",
    "linkedin":    "long-form-text",
    "x":           "post-or-thread",
}


DEFAULT_CONFIG_PATH = Path("~/.config/amazon-xhs-poster/config.json").expanduser()


def _read_config(cli_config: str | None) -> dict | None:
    config_path = None
    if cli_config:
        config_path = Path(cli_config).expanduser()
    elif os.environ.get("XHS_AMAZON_CONFIG"):
        config_path = Path(os.environ["XHS_AMAZON_CONFIG"]).expanduser()
    elif DEFAULT_CONFIG_PATH.exists():
        config_path = DEFAULT_CONFIG_PATH
    if config_path and config_path.exists():
        try:
            return json.loads(config_path.read_text())
        except Exception:
            return None
    return None


def resolve_language(cli_language: str | None, post: dict, cli_config: str | None) -> str:
    if cli_language:
        return cli_language.strip().lower()
    pj_lang = (post.get("language") or "").strip().lower()
    if pj_lang in HEADERS_BY_LANG:
        return pj_lang
    cfg = _read_config(cli_config) or {}
    cfg_lang = (cfg.get("output_language") or "").strip().lower()
    if cfg_lang in HEADERS_BY_LANG:
        return cfg_lang
    return "zh"


def resolve_platform(cli_platform: str | None, post: dict, cli_config: str | None) -> str:
    if cli_platform:
        return cli_platform.strip().lower()
    pj_platform = (post.get("platform") or "").strip().lower()
    if pj_platform in PLATFORM_FORMAT:
        return pj_platform
    cfg = _read_config(cli_config) or {}
    cfg_platform = (cfg.get("platform") or "").strip().lower()
    if cfg_platform in PLATFORM_FORMAT:
        return cfg_platform
    return "xiaohongshu"


def render_carousel(post, cards, hashtag_line, H, platform, job_date, timestamp):
    title = (post.get("xhs") or {}).get("title", "").strip()
    content = (post.get("xhs") or {}).get("content", "").strip()
    body_label = H["caption"] if platform == "instagram" else H["body"]
    cards_label = H["carousel"] if platform == "instagram" else H["cards"]
    h1 = H["h1_per_platform"].get(platform, H["h1_default"])

    lines = [f"# {h1} — {job_date}", ""]
    if title:
        lines += [f"## {H['title']}", "", title, ""]
    lines += [f"## {body_label}", "", content or H["empty"], ""]
    lines += [f"## {H['hashtags']}", "", hashtag_line or H["empty"], ""]
    lines += [f"## {cards_label}", ""]
    if cards:
        for c in cards:
            lines.append(f"- {c}")
    else:
        lines.append(H["no_render"])
    lines += ["", "---", "", H["footer_per_platform"][platform].format(ts=timestamp), ""]
    return lines


def render_long_form(post, hashtag_line, H, platform, job_date, timestamp):
    """LinkedIn-style: one continuous body block, no card list."""
    content = (post.get("xhs") or {}).get("content", "").strip()
    h1 = H["h1_per_platform"].get(platform, H["h1_default"])
    lines = [f"# {h1} — {job_date}", "",
             f"## {H['body']}", "", content or H["empty"], "",
             f"## {H['hashtags']}", "", hashtag_line or H["empty"], "",
             "---", "", H["footer_per_platform"][platform].format(ts=timestamp), ""]
    return lines


def _x_weighted_length(text: str) -> int:
    """Mirror of validate.py:x_weighted_length.

    Weight 1: Latin + Latin Extended + IPA + Spacing Modifier +
    Combining Diacritical + Cyrillic. Weight 2: everything else
    (CJK, Hiragana, Katakana, Hangul, full-width punctuation, emoji).
    """
    weight = 0
    for ch in text:
        cp = ord(ch)
        is_w1 = (
            cp <= 0x00FF or
            0x0100 <= cp <= 0x024F or
            0x0250 <= cp <= 0x02AF or
            0x02B0 <= cp <= 0x02FF or
            0x0300 <= cp <= 0x036F or
            0x0400 <= cp <= 0x052F
        )
        weight += 1 if is_w1 else 2
    return weight


def _len_label(text: str, platform: str) -> str:
    raw = len(text)
    if platform == "x":
        weight = _x_weighted_length(text)
        if weight != raw:
            return f"{raw} chars / {weight} weight"
    return f"{raw} chars"


def render_thread(post, hashtag_line, H, platform, job_date, timestamp):
    """X / Twitter: render thread (if non-empty) or single body."""
    xhs = post.get("xhs") or {}
    thread = xhs.get("thread") or []
    content = xhs.get("content", "").strip()
    h1 = H["h1_per_platform"].get(platform, H["h1_default"])
    label = H["thread"] if thread else H["post"]

    lines = [f"# {h1} — {job_date}", "", f"## {label}", ""]
    if thread:
        for i, t in enumerate(thread, start=1):
            t_text = str(t or "").strip() or H["empty"]
            lines += [f"**{H['tweet']} {i}/{len(thread)}** ({_len_label(t_text, platform)})",
                      "", t_text, ""]
    else:
        lines += [content or H["empty"], "", f"_(length: {_len_label(content, platform)})_", ""]
    if hashtag_line:
        lines += [f"## {H['hashtags']}", "", hashtag_line, ""]
    lines += ["---", "", H["footer_per_platform"][platform].format(ts=timestamp), ""]
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post_json", help="path to post.json")
    parser.add_argument("--output", default=None,
                        help="path to write post.md (default: <job_dir>/post.md)")
    parser.add_argument("--config", default=None,
                        help="path to config.json (only used to read output_language)")
    parser.add_argument("--language", default=None,
                        help="override language: zh | en")
    parser.add_argument("--platform", default=None,
                        help="override platform: xiaohongshu | lemon8 | linkedin | x | instagram")
    args = parser.parse_args()

    post_path = Path(args.post_json).expanduser().resolve()
    if not post_path.exists():
        sys.exit(f"post.json not found: {post_path}")
    post = json.loads(post_path.read_text())

    job_date = post.get("job_date") or post_path.parent.name
    job_dir = Path((post.get("paths") or {}).get("job_dir") or post_path.parent).expanduser()
    cards_dir = Path((post.get("paths") or {}).get("cards_dir") or (job_dir / "cards")).expanduser()

    tags = (post.get("xhs") or {}).get("tags") or []
    if not tags:
        tags = (post.get("seo") or {}).get("hashtags") or []
    hashtag_line = " ".join(
        ("#" + str(t).lstrip("#").strip().replace(" ", ""))
        for t in tags if str(t).strip()
    )

    cards = []
    manifest_path = cards_dir / "render_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for c in manifest.get("cards") or []:
            png = Path(c.get("png") or "")
            cards.append(png.name)
    else:
        for png in sorted(cards_dir.glob("card_*.png")):
            cards.append(png.name)
        for jpg in sorted(cards_dir.glob("card_*.jpg")):
            cards.append(jpg.name)

    timestamp = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M %Z")

    language = resolve_language(args.language, post, args.config)
    platform = resolve_platform(args.platform, post, args.config)
    H = HEADERS_BY_LANG[language]
    fmt = PLATFORM_FORMAT.get(platform, "carousel")

    if fmt == "long-form-text":
        lines = render_long_form(post, hashtag_line, H, platform, job_date, timestamp)
    elif fmt == "post-or-thread":
        lines = render_thread(post, hashtag_line, H, platform, job_date, timestamp)
    else:
        lines = render_carousel(post, cards, hashtag_line, H, platform, job_date, timestamp)

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else (job_dir / "post.md")
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines))
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
