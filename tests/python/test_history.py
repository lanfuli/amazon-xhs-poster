"""Tests for scripts/history.py — building recent_history.{json,md}."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent


def _run_history(config_path, output_json, output_md=None, drafts_root=None, days=None):
    args = [
        sys.executable,
        str(SKILL_ROOT / "scripts" / "history.py"),
        "--config", str(config_path),
        "--output-json", str(output_json),
    ]
    if output_md:
        args.extend(["--output-md", str(output_md)])
    if drafts_root:
        args.extend(["--drafts-root", str(drafts_root)])
    if days is not None:
        args.extend(["--days", str(days)])
    return subprocess.run(args, capture_output=True, text=True)


def _make_eligible_post(drafts_root, date, title, angle="test angle", category="risk-warning"):
    job_dir = drafts_root / date
    cards_dir = job_dir / "cards"
    cards_dir.mkdir(parents=True, exist_ok=True)
    # Eligibility marker: render_manifest.json must exist
    manifest = {"platform": "xiaohongshu", "theme": "default", "renderedAt": "x", "cards": []}
    (cards_dir / "render_manifest.json").write_text(json.dumps(manifest))
    post = {
        "version": "1.1", "job_date": date, "language": "zh", "platform": "xiaohongshu",
        "persona": {"brand_cn": "Test"},
        "topic": {"category": category, "angle": angle, "sources": []},
        "seo": {"hashtags": []},
        "xhs": {"title": title, "tags": []},
        "cards": [],
        "paths": {},
        "status": {},
    }
    post_path = job_dir / "post.json"
    post_path.write_text(json.dumps(post, ensure_ascii=False))
    return post_path


def test_history_with_no_posts_returns_empty(write_config, tmp_path):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    drafts = tmp_path / "drafts"
    drafts.mkdir(exist_ok=True)
    out_json = tmp_path / "history.json"
    res = _run_history(cfg, out_json, drafts_root=drafts)
    assert res.returncode == 0
    payload = json.loads(out_json.read_text())
    assert payload["count"] == 0
    assert payload["recent_posts"] == []


def test_history_collects_eligible_posts(write_config, tmp_path):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    drafts = tmp_path / "drafts"
    drafts.mkdir(exist_ok=True)
    _make_eligible_post(drafts, "2026-04-01", "First post")
    _make_eligible_post(drafts, "2026-04-15", "Second post")
    _make_eligible_post(drafts, "2026-05-01", "Third post")
    out_json = tmp_path / "history.json"
    res = _run_history(cfg, out_json, drafts_root=drafts, days=30)
    assert res.returncode == 0
    payload = json.loads(out_json.read_text())
    # 30-day window from 2026-05-01 backwards → catches 2026-04-02 .. 2026-05-01
    assert payload["count"] >= 2  # at least the most recent two
    titles = payload["recent_titles"]
    assert "Third post" in titles


def test_history_excludes_ineligible_posts(write_config, tmp_path):
    """Posts without rendered cards (no manifest, no card_06.png, no publish_result)
    should NOT be counted."""
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    drafts = tmp_path / "drafts"
    drafts.mkdir(exist_ok=True)
    # Make a post without rendering
    job_dir = drafts / "2026-05-01"
    job_dir.mkdir()
    post = {"version": "1.1", "job_date": "2026-05-01", "platform": "xiaohongshu",
            "topic": {"category": "risk-warning", "angle": "x"},
            "xhs": {"title": "Unrendered post", "tags": []},
            "seo": {"hashtags": []}}
    (job_dir / "post.json").write_text(json.dumps(post))
    out_json = tmp_path / "history.json"
    res = _run_history(cfg, out_json, drafts_root=drafts)
    assert res.returncode == 0
    payload = json.loads(out_json.read_text())
    titles = [r["title"] for r in payload["recent_posts"]]
    assert "Unrendered post" not in titles


def test_history_markdown_output(write_config, tmp_path):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    drafts = tmp_path / "drafts"
    drafts.mkdir(exist_ok=True)
    _make_eligible_post(drafts, "2026-05-01", "Post about Amazon FBA returns")
    out_json = tmp_path / "history.json"
    out_md = tmp_path / "history.md"
    res = _run_history(cfg, out_json, output_md=out_md, drafts_root=drafts)
    assert res.returncode == 0
    md = out_md.read_text()
    assert "Recent Amazon XHS History" in md
    assert "Post about Amazon FBA returns" in md


def test_history_extra_keywords_merged(write_config, tmp_path):
    """config.extra_angle_keywords should be merged with defaults."""
    cfg_data = json.loads(write_config(platform="xiaohongshu", output_language="zh").read_text())
    cfg_data["extra_angle_keywords"] = ["walmart connect", "tiktok shop"]
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg_data))

    drafts = tmp_path / "drafts"
    drafts.mkdir(exist_ok=True)
    _make_eligible_post(drafts, "2026-05-01", "Walmart Connect launched", angle="walmart connect spend")
    _make_eligible_post(drafts, "2026-05-02", "Walmart Connect again", angle="walmart connect changes")
    out_json = tmp_path / "history.json"
    out_md = tmp_path / "history.md"
    res = _run_history(cfg_path, out_json, output_md=out_md, drafts_root=drafts)
    assert res.returncode == 0
    # Custom keyword should appear in the markdown frequency table
    md = out_md.read_text()
    assert "walmart connect" in md.lower()
