"""Tests for scripts/validate.py — happy paths + bug-fix regression + edge cases."""
import json

import pytest


# --- Happy paths: 8 platform × language combinations ---

@pytest.mark.parametrize(
    "platform,language",
    [
        ("xiaohongshu", "zh"),
        ("xiaohongshu", "en"),
        ("lemon8", "en"),
        ("linkedin", "zh"),
        ("linkedin", "en"),
        ("x", "zh"),
        ("x", "en"),
        ("instagram", "zh"),
        ("instagram", "en"),
    ],
)
def test_happy_path_all_combos(platform, language, write_config, make_post, run_validate):
    cfg = write_config(platform=platform, output_language=language)
    post_path, _ = make_post(platform=platform, language=language)
    payload, rc = run_validate(post_path, cfg)
    assert rc == 0, f"{platform}/{language} validate failed: {payload.get('errors')}"
    assert payload["ok"] is True


# --- Bug 1 regression: must_contain corpus check ---

def test_bug1_x_no_keyword_anywhere_fails(write_config, make_post, run_validate):
    """X with empty title + 0 hashtags + content not mentioning the keyword
    must FAIL (was silently bypassing pre-v1.3.0)."""
    cfg = write_config(platform="x", output_language="en", must_contain=["Amazon"])
    post_path, _ = make_post(
        platform="x", language="en",
        content="Some random text without the brand keyword.",
        thread=[], tags=[],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc != 0
    assert any("must mention at least one of" in e for e in payload["errors"]), \
        f"Expected corpus must_contain error, got: {payload['errors']}"


def test_bug1_x_keyword_in_content_passes(write_config, make_post, run_validate):
    """X with empty title + 0 hashtags BUT 'Amazon' in content should pass."""
    cfg = write_config(platform="x", output_language="en", must_contain=["Amazon"])
    post_path, _ = make_post(
        platform="x", language="en",
        content="Amazon sellers should know this risk.",
        thread=[], tags=[],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc == 0, f"Errors: {payload.get('errors')}"


def test_bug1_keyword_in_thread_passes(write_config, make_post, run_validate):
    """X thread with keyword in any tweet should pass corpus check."""
    cfg = write_config(platform="x", output_language="en", must_contain=["Amazon"])
    post_path, _ = make_post(
        platform="x", language="en",
        thread=["Tweet without keyword.", "Tweet 2 mentions Amazon clearly.", "Final tweet."],
        content="", tags=[],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc == 0


# --- Bug 3 regression: case-insensitive must_contain ---

def test_bug3_lowercase_title_matches_capitalized_must_contain(write_config, make_post, run_validate):
    """title='amazon ...' + must_contain=['Amazon'] should pass (case-insensitive)."""
    cfg = write_config(
        platform="xiaohongshu", output_language="en",
        must_contain=["Amazon"], max_chars=30,
    )
    post_path, _ = make_post(
        platform="xiaohongshu", language="en",
        title="amazon return rate notes",
        content="amazon body about returns. follow.",
        tags=["amazon", "return", "prime", "listing", "risk"],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc == 0, f"Should pass with lowercase title, got: {payload.get('errors')}"


# --- Bug 4 regression: X content + thread mutual exclusion ---

def test_bug4_x_content_and_thread_both_set_fails(write_config, make_post, run_validate):
    cfg = write_config(platform="x", output_language="en")
    post_path, _ = make_post(
        platform="x", language="en",
        content="Single tweet content with Amazon",
        thread=["Tweet 1 with Amazon", "Tweet 2"],
        tags=[],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc != 0
    assert any("mutually exclusive" in e for e in payload["errors"])


# --- Gap 1 regression: cold-start info both states ---

def test_gap1_cold_start_when_history_missing(write_config, make_post, run_validate, tmp_path):
    cfg = write_config(platform="xiaohongshu", output_language="en", must_contain=["Amazon"], max_chars=30)
    post_path, _ = make_post(platform="xiaohongshu", language="en")
    # research/recent_history.json should not exist
    payload, rc = run_validate(post_path, cfg)
    assert payload["summary"]["cold_start"] is True
    assert any("cold-start" in i.lower() for i in payload["info"])


def test_gap1_cold_start_when_history_empty(write_config, make_post, run_validate, tmp_path):
    cfg = write_config(platform="xiaohongshu", output_language="en", must_contain=["Amazon"], max_chars=30)
    post_path, post = make_post(platform="xiaohongshu", language="en")
    # Create an EMPTY history file (the gap 1 scenario)
    history = {
        "generated_at": "2026-05-07T00:00:00Z",
        "window_days": 30,
        "count": 0,
        "recent_posts": [],
        "recent_titles": [], "recent_angles": [], "recent_categories": [],
    }
    research_dir = post_path.parent / "research"
    research_dir.mkdir(exist_ok=True)
    (research_dir / "recent_history.json").write_text(json.dumps(history))
    payload, rc = run_validate(post_path, cfg)
    assert payload["summary"]["cold_start"] is True, \
        "Empty history file should still be cold-start"
    assert any("zero posts" in i for i in payload["info"]), \
        f"Expected 'zero posts' info; got: {payload['info']}"


# --- Gap 2 regression: LinkedIn thread → hard error ---

def test_gap2_linkedin_thread_fails(write_config, make_post, run_validate):
    cfg = write_config(platform="linkedin", output_language="en")
    post_path, _ = make_post(
        platform="linkedin", language="en",
        thread=["Stray tweet that shouldn't be here on LinkedIn"],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc != 0
    assert any("does not support thread mode" in e for e in payload["errors"])


# --- Improvement 1: X thread > 10 → soft-warn ---

def test_improve1_x_long_thread_warns(write_config, make_post, run_validate):
    cfg = write_config(platform="x", output_language="en")
    post_path, _ = make_post(
        platform="x", language="en",
        thread=[f"Tweet {i} mentions Amazon briefly." for i in range(1, 13)],
        content="", tags=[],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc == 0, "Long thread is a soft-warn, not a hard error"
    assert any("X engagement drops sharply" in w for w in payload["warnings"])


# --- Improvement 2: title verbatim in content opening ---

def test_improve2_title_verbatim_in_content_warns(write_config, make_post, run_validate):
    cfg = write_config(
        platform="xiaohongshu", output_language="en",
        must_contain=["Amazon"], max_chars=30,
    )
    title = "Amazon return"
    post_path, _ = make_post(
        platform="xiaohongshu", language="en",
        title=title,
        content=f"{title}: detailed body about returns. Follow Amazon for more.",
        tags=["amazon", "return", "prime", "listing", "risk"],
    )
    payload, rc = run_validate(post_path, cfg)
    assert any("appears verbatim" in w for w in payload["warnings"])


# --- Improvement 4 / Bug 1 partner: must_contain=[] info ---

def test_must_contain_empty_emits_info(write_config, make_post, run_validate):
    cfg = write_config(platform="xiaohongshu", output_language="zh", must_contain=[])
    post_path, _ = make_post(platform="xiaohongshu", language="zh")
    payload, rc = run_validate(post_path, cfg)
    assert any("DISABLED" in i for i in payload["info"])


# --- CJK weighting boundary on X ---

def test_x_cjk_weighting_140_chinese_chars_passes(write_config, make_post, run_validate):
    """140 Chinese characters = 280 weight = at the limit; passes."""
    cfg = write_config(platform="x", output_language="zh")
    char = "亚"  # weight 2
    tweet = char * 140  # exactly 280 weight, must contain 亚马逊
    tweet = tweet[:137] + "亚马逊"  # ensure must_contain hits
    post_path, _ = make_post(
        platform="x", language="zh",
        thread=[tweet], content="", tags=[],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc == 0, f"140-char Chinese tweet should pass, got: {payload.get('errors')}"


def test_x_cjk_weighting_141_chinese_chars_fails(write_config, make_post, run_validate):
    """141 Chinese characters = 282 weight > 280 limit; fails."""
    cfg = write_config(platform="x", output_language="zh")
    tweet = "亚马逊" + "测" * 138 + "亚马逊"  # 141 CJK chars = 282 weight
    post_path, _ = make_post(
        platform="x", language="zh",
        thread=[tweet], content="", tags=[],
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc != 0
    assert any("CJK weighting" in e for e in payload["errors"]), \
        f"Expected CJK weighting error, got: {payload['errors']}"


# --- Required title check ---

def test_xiaohongshu_empty_title_fails(write_config, make_post, run_validate):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    post_path, _ = make_post(platform="xiaohongshu", language="zh", title="")
    payload, rc = run_validate(post_path, cfg)
    assert rc != 0
    assert any("title is empty" in e for e in payload["errors"])


def test_linkedin_empty_title_passes(write_config, make_post, run_validate):
    """LinkedIn doesn't require a title."""
    cfg = write_config(platform="linkedin", output_language="en")
    post_path, _ = make_post(platform="linkedin", language="en")
    payload, rc = run_validate(post_path, cfg)
    assert rc == 0


# --- Title length cap ---

def test_xiaohongshu_title_over_20_chars_fails(write_config, make_post, run_validate):
    cfg = write_config(platform="xiaohongshu", output_language="zh")
    post_path, _ = make_post(
        platform="xiaohongshu", language="zh",
        title="亚马逊这标题超过二十字符限制了对不对你说呢真的的的",
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc != 0
    assert any("exceeds 20 characters" in e for e in payload["errors"])


# --- Forbidden brands ---

def test_forbidden_brand_in_content_fails(write_config, make_post, run_validate):
    cfg = write_config(
        platform="xiaohongshu", output_language="zh",
        forbidden_brands=["myinternaltool"],
    )
    post_path, _ = make_post(
        platform="xiaohongshu", language="zh",
        content="亚马逊正文 myinternaltool 测试 关注",
    )
    payload, rc = run_validate(post_path, cfg)
    assert rc != 0
    assert any("forbidden_brands" in e.lower() or "myinternaltool" in e.lower() for e in payload["errors"])


# --- Persona unfilled ---

def test_persona_replace_me_fails(write_config, make_post, run_validate, tmp_path):
    cfg_path = tmp_path / "config.json"
    cfg_data = json.loads(write_config(platform="xiaohongshu", output_language="zh").read_text())
    cfg_data["persona"]["brand_cn"] = "REPLACE_ME — your brand"
    cfg_path.write_text(json.dumps(cfg_data))
    post_path, _ = make_post(platform="xiaohongshu", language="zh")
    payload, rc = run_validate(post_path, cfg_path)
    assert rc != 0
    assert any("REPLACE_ME" in e or "unfilled" in e for e in payload["errors"])
