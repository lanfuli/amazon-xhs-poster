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
        "h1": "小红书亚马逊主题",
        "title": "标题",
        "body": "正文",
        "hashtags": "Hashtags",
        "cards": "卡片清单",
        "empty": "_(未填)_",
        "no_render": "_(尚未渲染，先跑 render.mjs)_",
        "footer": "生成于 {ts} · 发布方式：手动上传到小红书 APP",
    },
    "en": {
        "h1": "Amazon Seller Note",
        "title": "Title",
        "body": "Body",
        "hashtags": "Hashtags",
        "cards": "Cards",
        "empty": "_(empty)_",
        "no_render": "_(not rendered yet — run render.mjs first)_",
        "footer": "Generated {ts} · publish manually to your target platform",
    },
}


DEFAULT_CONFIG_PATH = Path("~/.config/amazon-xhs-poster/config.json").expanduser()


def resolve_language(cli_language: str | None, post: dict, cli_config: str | None) -> str:
    if cli_language:
        return cli_language.strip().lower()
    pj_lang = (post.get("language") or "").strip().lower()
    if pj_lang in HEADERS_BY_LANG:
        return pj_lang
    config_path = None
    if cli_config:
        config_path = Path(cli_config).expanduser()
    elif os.environ.get("XHS_AMAZON_CONFIG"):
        config_path = Path(os.environ["XHS_AMAZON_CONFIG"]).expanduser()
    elif DEFAULT_CONFIG_PATH.exists():
        config_path = DEFAULT_CONFIG_PATH
    if config_path and config_path.exists():
        try:
            cfg = json.loads(config_path.read_text())
            cfg_lang = (cfg.get("output_language") or "").strip().lower()
            if cfg_lang in HEADERS_BY_LANG:
                return cfg_lang
        except Exception:
            pass
    return "zh"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post_json", help="path to post.json")
    parser.add_argument("--output", default=None,
                        help="path to write post.md (default: <job_dir>/post.md)")
    parser.add_argument("--config", default=None,
                        help="path to config.json (only used to read output_language)")
    parser.add_argument("--language", default=None,
                        help="override language: zh | en")
    args = parser.parse_args()

    post_path = Path(args.post_json).expanduser().resolve()
    if not post_path.exists():
        sys.exit(f"post.json not found: {post_path}")
    post = json.loads(post_path.read_text())

    job_date = post.get("job_date") or post_path.parent.name
    job_dir = Path((post.get("paths") or {}).get("job_dir") or post_path.parent).expanduser()
    cards_dir = Path((post.get("paths") or {}).get("cards_dir") or (job_dir / "cards")).expanduser()

    title = (post.get("xhs") or {}).get("title", "").strip()
    content = (post.get("xhs") or {}).get("content", "").strip()
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
    H = HEADERS_BY_LANG[language]

    lines = [
        f"# {H['h1']} — {job_date}",
        "",
        f"## {H['title']}",
        "",
        title or H["empty"],
        "",
        f"## {H['body']}",
        "",
        content or H["empty"],
        "",
        f"## {H['hashtags']}",
        "",
        hashtag_line or H["empty"],
        "",
        f"## {H['cards']}",
        "",
    ]
    if cards:
        for c in cards:
            lines.append(f"- {c}")
    else:
        lines.append(H["no_render"])
    lines += [
        "",
        "---",
        "",
        H["footer"].format(ts=timestamp),
        "",
    ]

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
