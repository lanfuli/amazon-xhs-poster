"""Tests for scripts/init-day.py — skeleton creation per platform."""
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "platform,expected_card_min,expected_card_max,renders_cards",
    [
        ("xiaohongshu", 6, 9, True),
        ("instagram", 1, 10, True),
        ("linkedin", 0, 0, False),
        ("x", 0, 0, False),
    ],
)
def test_skeleton_card_counts_match_preset(
    platform, expected_card_min, expected_card_max, renders_cards,
    write_config, run_init_day, tmp_path,
):
    cfg = write_config(platform=platform, output_language="en")
    rc, stdout, stderr = run_init_day(cfg)
    assert rc == 0, f"init-day.py failed: {stderr}"

    drafts_root = tmp_path / "drafts"
    post_path = drafts_root / "2026-05-07" / "post.json"
    assert post_path.exists(), f"Skeleton not created at {post_path}"
    post = json.loads(post_path.read_text())

    assert post["platform"] == platform
    assert post["design"]["cards_min"] == expected_card_min
    assert post["design"]["cards_max"] == expected_card_max
    assert post["design"]["renders_cards"] == renders_cards


def test_text_only_skeleton_omits_design_style(write_config, run_init_day, tmp_path):
    """Gap 3 fix: text-only platforms shouldn't have design.style in skeleton."""
    cfg = write_config(platform="linkedin", output_language="en")
    rc, _, _ = run_init_day(cfg)
    assert rc == 0
    post = json.loads((tmp_path / "drafts" / "2026-05-07" / "post.json").read_text())
    assert "style" not in post["design"], \
        f"text-only skeleton should not write design.style, got: {post['design']}"
    assert "ratio" not in post["design"]


def test_carousel_skeleton_has_design_style(write_config, run_init_day, tmp_path):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    rc, _, _ = run_init_day(cfg)
    assert rc == 0
    post = json.loads((tmp_path / "drafts" / "2026-05-07" / "post.json").read_text())
    assert post["design"]["style"] == "iphone-notes-editorial-v4"


def test_skeleton_has_thread_field(write_config, run_init_day, tmp_path):
    """xhs.thread should be present (empty array) for all platforms; X uses it,
    others ignore it."""
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    rc, _, _ = run_init_day(cfg)
    post = json.loads((tmp_path / "drafts" / "2026-05-07" / "post.json").read_text())
    assert post["xhs"]["thread"] == []


def test_attention_goal_zh_vs_en(write_config, run_init_day, tmp_path):
    cfg_zh = write_config(platform="xiaohongshu", output_language="zh")
    rc, _, _ = run_init_day(cfg_zh)
    zh_post = json.loads((tmp_path / "drafts" / "2026-05-07" / "post.json").read_text())
    assert "3秒" in zh_post["strategy"]["attention_goal"]


def test_idempotent_existing_post(write_config, run_init_day, tmp_path):
    """Re-running init-day on the same date should NOT overwrite existing post.json."""
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    rc, _, _ = run_init_day(cfg)
    post_path = tmp_path / "drafts" / "2026-05-07" / "post.json"
    original = post_path.read_text()
    # Modify it
    post = json.loads(original)
    post["xhs"]["title"] = "user-edited"
    post_path.write_text(json.dumps(post, ensure_ascii=False))
    # Re-run init-day
    rc2, _, _ = run_init_day(cfg)
    assert rc2 == 0
    after = json.loads(post_path.read_text())
    assert after["xhs"]["title"] == "user-edited", "init-day overwrote user changes"


def test_research_topic_md_created(write_config, run_init_day, tmp_path):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    rc, _, _ = run_init_day(cfg)
    research_md = tmp_path / "drafts" / "2026-05-07" / "research" / "topic.md"
    assert research_md.exists()
    assert "Topic" in research_md.read_text()


def test_history_files_created(write_config, run_init_day, tmp_path):
    """init-day calls history.py to seed recent_history.json+md."""
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    rc, _, _ = run_init_day(cfg)
    research_dir = tmp_path / "drafts" / "2026-05-07" / "research"
    assert (research_dir / "recent_history.json").exists()
    assert (research_dir / "recent_history.md").exists()
