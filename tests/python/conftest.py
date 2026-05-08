"""Shared pytest fixtures for wayamzpost validation/skeleton tests.

Provides:
- skill_root: path to the skill root (auto-detected via pytest rootdir)
- scripts_dir: path to scripts/
- fresh_drafts: temp dir scrubbed each test
- write_config(...) helper: build a config.json with sensible defaults
- write_post(...) helper: build a minimal post.json that's also valid
- run_validate(...): subprocess wrapper that returns parsed JSON output

The fixtures give every test a clean working tree so cross-test state
doesn't leak.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"


@pytest.fixture
def skill_root():
    return SKILL_ROOT


@pytest.fixture
def scripts_dir():
    return SCRIPTS_DIR


@pytest.fixture
def fresh_drafts(tmp_path):
    """Per-test temp drafts root. Gets cleaned up by pytest's tmp_path."""
    root = tmp_path / "drafts"
    root.mkdir()
    return root


def _base_quotas():
    return {
        "amazon-news":           {"floor": 2, "ceiling": 5, "color": "amber"},
        "white-hat-tactic":      {"floor": 2, "ceiling": 5, "color": "green"},
        "risk-warning":          {"floor": 2, "ceiling": 5, "color": "red"},
        "ai-workflow":           {"floor": 2, "ceiling": 4, "color": "blue"},
        "walmart-multi-channel": {"floor": 1, "ceiling": 3, "color": "slate"},
        "creator-signal":        {"floor": 0, "ceiling": 2, "color": "violet"},
    }


@pytest.fixture
def write_config(tmp_path):
    """Build a minimal valid config.json. Override fields via kwargs.

    Returns a callable that writes the config to a temp path and returns it.
    """
    def _write(
        platform="xiaohongshu",
        output_language="zh",
        brand_cn=None,
        must_contain=None,
        cta_tokens=None,
        decision_verbs=None,
        max_chars=None,
        forbidden_brands=None,
        forbidden_sources=None,
        drafts_root=None,
    ):
        cfg = {
            "output_language": output_language,
            "platform": platform,
            "persona": {
                "brand_cn": brand_cn or ("可乐讲卖货" if output_language == "zh" else "Test Brand"),
                "identity": "test op",
                "voice": "test",
                "signature": brand_cn or ("可乐讲卖货" if output_language == "zh" else "Test Brand"),
                "location": "Test City",
                "years_experience": 1,
            },
            "title_constraints": {"max_chars": max_chars, "must_contain": must_contain},
            "cta_tokens": cta_tokens,
            "decision_verbs": decision_verbs,
            "forbidden_brands_in_copy": forbidden_brands if forbidden_brands is not None else [],
            "forbidden_source_tokens": forbidden_sources if forbidden_sources is not None else [],
            "angle_quotas": _base_quotas(),
            "paths": {
                "drafts_root": str(drafts_root or tmp_path / "drafts"),
                "desktop_root": "",
                "history_lookback_days": 30,
            },
            "extra_angle_keywords": [],
            "publish_adapter": {"enabled": False, "module_path": None},
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
        return path

    return _write


def _build_carousel_post(platform, language, **overrides):
    """A platform-valid carousel-style post (XHS / IG)."""
    is_zh = language == "zh"
    persona_name = overrides.get("brand_cn") or ("可乐讲卖货" if is_zh else "Test Brand")
    title = overrides.get("title", "亚马逊测试标题" if is_zh else "Amazon test title")
    body = overrides.get("content", "亚马逊正文，关注 评论。" if is_zh else "Amazon body content, follow.")
    tags = overrides.get("tags", ["亚马逊", "FBA", "亚马逊运营", "PrimeDay", "跨境电商"] if is_zh
                          else ["Amazon", "FBA", "AmazonSeller", "PrimeDay", "Ecommerce"])
    cta_word = "关注" if is_zh else "follow"
    cards = []
    for i in range(1, 7):
        cards.append({
            "id": f"card_0{i}",
            "kind": "hook" if i == 1 else "cta" if i == 6 else "framework",
            "eyebrow": "测试" if is_zh else "test",
            "headline": "亚马逊 hook" if is_zh else "Amazon hook",
            "body": (f"决定 {cta_word}" if is_zh else f"decide and {cta_word}") if i == 6 else "亚马逊 body" if is_zh else "Amazon body",
            "bullets": [],
            "footer": persona_name,
        })
    return {
        "version": "1.1",
        "job_date": "2026-05-07",
        "language": language,
        "platform": platform,
        "persona": {
            "brand_cn": persona_name,
            "identity": "test", "voice": "test", "signature": persona_name,
        },
        "topic": {
            "category": "risk-warning",
            "angle": "亚马逊 PrimeDay 退货 FBA listing 风险" if is_zh else "Amazon PrimeDay FBA returns listing risk",
            "why_now": "now",
            "selection_reason": "test",
            "sources": ["https://example.com/article"],
        },
        "seo": {"hashtags": []},
        "strategy": {"attention_goal": "x", "psychology_hooks": [], "ai_positioning": "", "dedupe_window_days": 30},
        "design": {
            "theme": "auto",
            "style": "iphone-notes-editorial-v4",
            "cards": 6, "cards_min": 6, "cards_max": 9,
            "renders_cards": True,
            "ratio": "3:4", "width": 1080, "height": 1440,
            "accent_strategy": "color-psychology",
        },
        "xhs": {
            "title": title,
            "title_max_length": 20 if platform == "xiaohongshu" else 30,
            "opening_hook": body,
            "content": body,
            "cta": "follow",
            "tags": tags,
            "thread": [],
            "append_hashtags_to_content": True,
            "schedule_at": "",
            "delivery_mode": "manual",
        },
        "cards": cards,
        "paths": {},  # filled by tests
        "status": {"research": "complete", "editorial": "complete",
                   "render": "done", "qa": "complete", "publish": "manual"},
        "qa_notes": [],
    }


def _build_text_post(platform, language, **overrides):
    """A platform-valid text-only post (LinkedIn / X)."""
    is_zh = language == "zh"
    persona_name = overrides.get("brand_cn") or ("可乐讲卖货" if is_zh else "Test Brand")
    body = overrides.get("content", "亚马逊正文需要够长以满足相关性。FBA 退货 PrimeDay 跨境 Amazon。关注我。"
                         if is_zh else "Amazon body relevant enough. FBA returns PrimeDay seller. Follow.")
    thread = overrides.get("thread", [])
    if platform == "x" and not thread and not overrides.get("content"):
        # X default to a thread (more common)
        body = ""
        thread = (
            ["亚马逊推文 1：FBA PrimeDay 风险，关注。"] * 3
            if is_zh else
            ["Amazon FBA tweet 1: PrimeDay risk, follow."] * 3
        )

    tag_set = overrides.get("tags",
        ["亚马逊", "FBA", "PrimeDay", "跨境电商"] if (is_zh and platform == "linkedin")
        else ["Amazon", "FBA", "PrimeDay", "Seller"] if platform == "linkedin"
        else ["亚马逊"] if (is_zh and platform == "x")
        else ["Amazon"] if platform == "x"
        else ["亚马逊"])

    return {
        "version": "1.1",
        "job_date": "2026-05-07",
        "language": language,
        "platform": platform,
        "persona": {
            "brand_cn": persona_name,
            "identity": "test", "voice": "test", "signature": persona_name,
        },
        "topic": {
            "category": "risk-warning",
            "angle": "亚马逊 FBA PrimeDay 退货" if is_zh else "Amazon FBA PrimeDay returns",
            "why_now": "now",
            "selection_reason": "test",
            "sources": ["https://example.com/article"],
        },
        "seo": {"hashtags": []},
        "strategy": {"attention_goal": "x", "psychology_hooks": [], "ai_positioning": "", "dedupe_window_days": 30},
        "design": {"cards": 0, "cards_min": 0, "cards_max": 0, "renders_cards": False},
        "xhs": {
            "title": "",
            "opening_hook": body,
            "content": body,
            "cta": "follow",
            "tags": tag_set,
            "thread": thread,
            "append_hashtags_to_content": True if platform == "linkedin" else False,
            "delivery_mode": "manual",
        },
        "cards": [],
        "paths": {},
        "status": {"research": "complete", "editorial": "complete",
                   "render": "skipped-no-cards", "qa": "complete", "publish": "manual"},
        "qa_notes": [],
    }


@pytest.fixture
def make_post(tmp_path):
    """Build a valid post.json on disk. Returns (path, post_dict).

    Override fields via overrides kwarg. Automatically fixes paths block.
    """
    def _make(platform="xiaohongshu", language="zh", **overrides):
        if platform in ("xiaohongshu", "instagram"):
            post = _build_carousel_post(platform, language, **overrides)
        else:
            post = _build_text_post(platform, language, **overrides)
        # Apply any extra overrides (deep merge for xhs / design / etc)
        for key, val in overrides.items():
            if key in post and isinstance(val, dict) and isinstance(post[key], dict):
                post[key].update(val)
            elif key not in ("title", "content", "thread", "tags", "brand_cn"):
                post[key] = val
        # Build paths
        date = post["job_date"]
        job_dir = tmp_path / "drafts" / date
        cards_dir = job_dir / "cards"
        research_dir = job_dir / "research"
        cards_dir.mkdir(parents=True, exist_ok=True)
        research_dir.mkdir(parents=True, exist_ok=True)
        post["paths"] = {
            "job_dir": str(job_dir),
            "desktop_root": "",
            "research_note": str(research_dir / "topic.md"),
            "post_json": str(job_dir / "post.json"),
            "render_manifest": str(cards_dir / "render_manifest.json"),
            "cards_dir": str(cards_dir),
        }
        post_path = job_dir / "post.json"
        post_path.write_text(json.dumps(post, ensure_ascii=False, indent=2))
        return post_path, post

    return _make


@pytest.fixture
def run_validate():
    """Run validate.py and return parsed JSON payload."""
    def _run(post_path, config_path):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "validate.py"),
             str(post_path), "--config", str(config_path), "--json"],
            capture_output=True, text=True,
        )
        try:
            return json.loads(result.stdout), result.returncode
        except json.JSONDecodeError:
            return {"_raw_stdout": result.stdout, "_raw_stderr": result.stderr}, result.returncode

    return _run


@pytest.fixture
def run_init_day():
    """Run init-day.py and return (returncode, stdout, stderr)."""
    def _run(config_path, date="2026-05-07"):
        env = os.environ.copy()
        env["WAYAMZPOST_CONFIG"] = str(config_path)
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "init-day.py"), "--date", date],
            capture_output=True, text=True, env=env,
        )
        return result.returncode, result.stdout, result.stderr

    return _run


@pytest.fixture
def run_make_post_md():
    """Run make-post-md.py and return (returncode, post_md_text, stderr)."""
    def _run(post_path, config_path, **kwargs):
        args = [sys.executable, str(SCRIPTS_DIR / "make-post-md.py"),
                str(post_path), "--config", str(config_path)]
        if "platform" in kwargs:
            args.extend(["--platform", kwargs["platform"]])
        if "language" in kwargs:
            args.extend(["--language", kwargs["language"]])
        result = subprocess.run(args, capture_output=True, text=True)
        post = json.loads(Path(post_path).read_text())
        job_dir = Path(post["paths"]["job_dir"])
        md_path = job_dir / "post.md"
        md_text = md_path.read_text() if md_path.exists() else ""
        return result.returncode, md_text, result.stderr

    return _run
