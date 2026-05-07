"""Tests for scripts/make-post-md.py — per-platform output layout."""
import json
import pytest


# --- Per-platform output H1 + section labels ---

def test_zh_xhs_post_md_has_chinese_headers(write_config, make_post, run_make_post_md):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    post_path, _ = make_post(platform="xiaohongshu", language="zh")
    rc, md, _ = run_make_post_md(post_path, cfg)
    assert rc == 0
    assert md.startswith("# 小红书亚马逊主题")
    assert "## 标题" in md
    assert "## 正文" in md
    assert "## 卡片清单" in md


def test_zh_instagram_post_md_uses_zh_caption_and_carousel(write_config, make_post, run_make_post_md):
    """Bug 2 regression: ZH IG should use 正文 + 卡片, not Caption + Carousel."""
    cfg = write_config(platform="instagram", output_language="zh")
    post_path, _ = make_post(platform="instagram", language="zh")
    rc, md, _ = run_make_post_md(post_path, cfg)
    assert rc == 0
    assert "## 正文" in md, "ZH IG should use 正文 (not 'Caption')"
    assert "## 卡片" in md, "ZH IG should use 卡片 (not 'Carousel')"
    assert "Caption" not in md
    assert "Carousel" not in md


def test_zh_x_post_md_uses_zh_thread_label(write_config, make_post, run_make_post_md):
    """Bug 2 regression: ZH X should use 线程, not Thread."""
    cfg = write_config(platform="x", output_language="zh")
    post_path, _ = make_post(
        platform="x", language="zh",
        thread=["亚马逊推文 1", "亚马逊推文 2", "亚马逊推文 3"],
        content="", tags=["亚马逊"],
    )
    rc, md, _ = run_make_post_md(post_path, cfg)
    assert rc == 0
    assert "## 线程" in md or "## 推文" in md
    # English "Thread" should not appear as a header
    assert not any(line.strip() == "## Thread" for line in md.split("\n"))


def test_en_linkedin_post_md_layout(write_config, make_post, run_make_post_md):
    cfg = write_config(platform="linkedin", output_language="en")
    post_path, _ = make_post(platform="linkedin", language="en")
    rc, md, _ = run_make_post_md(post_path, cfg)
    assert rc == 0
    assert md.startswith("# Amazon Seller Post (LinkedIn)")
    assert "## Body" in md
    assert "## Hashtags" in md
    # LinkedIn doesn't render cards
    assert "## Cards" not in md
    assert "## Carousel" not in md


def test_en_x_thread_shows_per_tweet_char_count(write_config, make_post, run_make_post_md):
    cfg = write_config(platform="x", output_language="en")
    post_path, _ = make_post(
        platform="x", language="en",
        thread=["Amazon tweet 1", "Amazon tweet 2", "Amazon tweet 3"],
        content="", tags=[],
    )
    rc, md, _ = run_make_post_md(post_path, cfg)
    assert rc == 0
    assert "Tweet 1/3" in md
    assert "chars" in md  # the count display


def test_zh_x_thread_shows_chars_and_weight(write_config, make_post, run_make_post_md):
    cfg = write_config(platform="x", output_language="zh")
    post_path, _ = make_post(
        platform="x", language="zh",
        thread=["亚马逊推文 1 包含足够的字符。", "亚马逊推文 2 测试。"],
        content="", tags=[],
    )
    rc, md, _ = run_make_post_md(post_path, cfg)
    assert rc == 0
    assert "chars / " in md and "weight" in md, \
        "ZH X tweets should show 'X chars / Y weight' for CJK transparency"


# --- Improvement 3: manifest platform drift detection ---

def test_manifest_platform_drift_warns(write_config, make_post, run_make_post_md, tmp_path):
    """If manifest says one platform but make-post-md is invoked with --platform x
    different, stderr should contain a warning."""
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    post_path, _ = make_post(platform="xiaohongshu", language="zh")
    # Write a fake manifest claiming linkedin
    cards_dir = post_path.parent / "cards"
    manifest = {
        "platform": "linkedin",
        "theme": "default",
        "renderedAt": "2026-05-07T00:00:00Z",
        "cards": [],
    }
    (cards_dir / "render_manifest.json").write_text(json.dumps(manifest))
    rc, md, stderr = run_make_post_md(post_path, cfg)
    # rc still 0; just a warning to stderr
    assert "different platform" in stderr.lower() or "drift" in stderr.lower() or "manifest" in stderr.lower()


def test_no_drift_warning_when_platforms_match(write_config, make_post, run_make_post_md):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    post_path, _ = make_post(platform="xiaohongshu", language="zh")
    cards_dir = post_path.parent / "cards"
    manifest = {
        "platform": "xiaohongshu",
        "theme": "default",
        "renderedAt": "2026-05-07T00:00:00Z",
        "cards": [],
    }
    (cards_dir / "render_manifest.json").write_text(json.dumps(manifest))
    rc, md, stderr = run_make_post_md(post_path, cfg)
    assert "different platform" not in stderr.lower()


# --- --platform CLI override ---

def test_platform_cli_override(write_config, make_post, run_make_post_md):
    """--platform x should produce X-style output even if post.json says xiaohongshu."""
    cfg = write_config(platform="xiaohongshu", output_language="en")
    post_path, _ = make_post(
        platform="x", language="en",
        thread=["Amazon tweet 1", "Amazon tweet 2"],
        content="", tags=["Amazon"],
    )
    # Override post.json to say xiaohongshu but call with --platform x
    post = json.loads(post_path.read_text())
    post["platform"] = "xiaohongshu"
    post_path.write_text(json.dumps(post, ensure_ascii=False))
    rc, md, _ = run_make_post_md(post_path, cfg, platform="x")
    assert rc == 0
    assert "## Thread" in md or "Tweet 1/2" in md
