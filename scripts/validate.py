#!/usr/bin/env python3
"""Validate a wayamzpost post.json against the rules defined in config.json.

This is a parameterized port of the in-house validator
(`validate-wayamzpost.py`). All hardcoded persona / brand / forbidden
tokens / angle ceilings have been moved to config.json so anyone can use the
same methodology with their own account, voice, and confidentiality boundary.

Resolution order for config:
  1. --config <path> argument
  2. WAYAMZPOST_CONFIG env var
  3. XHS_AMAZON_CONFIG env var (legacy)
  4. ~/.config/wayamzpost/config.json
  5. ~/.config/amazon-xhs-poster/config.json (legacy)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
from difflib import SequenceMatcher
from pathlib import Path

ALLOWED_STYLES = {"iphone-notes-editorial-v4"}

RECENT_TITLE_WINDOW_DAYS = 7
RECENT_CTA_WINDOW_DAYS = 3
CTA_SIMILARITY_THRESHOLD = 0.7
HASHTAG_RELEVANCE_MIN_RATIO = 0.6

# Per-platform structural limits. Each preset captures the platform's
# native constraints — title length, body cap, hashtag count + token length,
# card count range, whether the renderer paints PNG cards, and whether the
# platform supports thread-mode multi-post output. Validator reads the
# preset matching `config.platform` (default "xiaohongshu").
# PLATFORM_PRESETS: per-platform validator constraints. New explicit knob:
#   requires_inbody_hashtags — whether xhs.append_hashtags_to_content must
#   be true. Was previously inferred from format=="carousel"; making it
#   explicit prevents future format-string renames from silently flipping
#   the check.
PLATFORM_PRESETS = {
    "xiaohongshu": {
        "title_max": 20,
        "title_required": True,
        "body_max": None,
        "hashtag_min": 5,
        "hashtag_max": 10,
        "hashtag_token_max": 12,
        "card_min": 6,
        "card_max": 9,
        "renders_cards": True,
        "supports_thread": False,
        "requires_inbody_hashtags": True,
        "format": "carousel",
        "description": "Xiaohongshu native (default for ZH). 20-char title cap, 6-9 image cards, 5-10 hashtags ≤12 chars each.",
    },
    "linkedin": {
        "title_max": 0,
        "title_required": False,
        "body_max": 3000,
        "hashtag_min": 3,
        "hashtag_max": 5,
        "hashtag_token_max": 50,
        "card_min": 0,
        "card_max": 0,
        "renders_cards": False,
        "supports_thread": False,
        "requires_inbody_hashtags": False,
        "format": "long-form-text",
        "description": "LinkedIn long-form text post. No carousel by default. 3000-char body, 3-5 hashtags, no separate title (first line acts as hook).",
    },
    "x": {
        "title_max": 0,
        "title_required": False,
        "body_max": 280,
        "hashtag_min": 0,
        "hashtag_max": 2,
        "hashtag_token_max": 30,
        "card_min": 0,
        "card_max": 0,
        "renders_cards": False,
        "supports_thread": True,
        "thread_max_posts": 25,
        "requires_inbody_hashtags": False,
        "format": "post-or-thread",
        "description": "X (Twitter) — single 280-char post or a thread of up to 25 posts via xhs.thread[]. Hashtags discouraged (0-2).",
    },
    "instagram": {
        "title_max": 0,
        "title_required": False,
        "body_max": 2200,
        "hashtag_min": 5,
        "hashtag_max": 30,
        "hashtag_token_max": 30,
        "card_min": 1,
        "card_max": 10,
        "renders_cards": True,
        "supports_thread": False,
        "requires_inbody_hashtags": True,
        "format": "carousel-with-caption",
        "description": "Instagram carousel (1-10 cards) + caption (≤2200 chars). 5-30 hashtags allowed, but 5-10 is optimal for reach.",
    },
}

DEFAULT_PLATFORM = "xiaohongshu"

CTA_TOKENS_BY_LANG = {
    "zh": ["点赞", "收藏", "关注", "不迷路", "评论"],
    "en": ["like", "save", "follow", "comment", "share", "subscribe"],
}

DECISION_VERBS_BY_LANG = {
    "zh": [
        "决定", "判断", "换", "停", "加预算", "下架",
        "挑选", "暂停", "转移", "重组", "砍", "上架", "留",
    ],
    "en": [
        "decide", "switch", "pause", "stop", "increase budget",
        "remove", "select", "transfer", "rebuild", "cut",
        "promote", "keep", "kill",
    ],
}

DEFAULT_TITLE_KEYWORDS_BY_LANG = {
    "zh": ["亚马逊"],
    "en": ["Amazon"],
}

PARALLEL_DIM_PATTERNS = [
    re.compile(r"第[1-9一二三四五六七八九]+步"),
    re.compile(r"第[1-9一二三四五六七八九]+种"),
    re.compile(r"第[1-9一二三四五六七八九]+类"),
    re.compile(r"类型[1-9一二三四五六七八九]"),
    re.compile(r"风险[1-9一二三四五六七八九]"),
]
PARALLEL_DIM_PREFIX = re.compile(r"^第[1-9一二三四五六七八九]+[步种类个项]")


# ---------- Config loading ----------

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


def load_config(cli_path: str | None) -> dict:
    path = resolve_config_path(cli_path)
    if not path:
        raise SystemExit(
            "no config.json found; pass --config <path>, set WAYAMZPOST_CONFIG, "
            f"or place a config at {DEFAULT_CONFIG_PATH} "
            f"(legacy fallback: {LEGACY_CONFIG_PATH})"
        )
    if not path.exists():
        raise SystemExit(f"config not found: {path}")
    return json.loads(path.read_text())


# ---------- Helpers ----------

def normalized_tags(post: dict) -> list[str]:
    xhs_tags = (post.get("xhs") or {}).get("tags") or []
    seo_tags = (post.get("seo") or {}).get("hashtags") or []
    chosen = xhs_tags if xhs_tags else seo_tags
    if not isinstance(chosen, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in chosen:
        # Skip non-string entries (None, dicts, lists, ints) — caller will
        # have separately checked the input shape and emitted an error.
        if not isinstance(raw, str):
            continue
        tag = raw.lstrip("#").strip().replace(" ", "")
        if not tag or tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return out


def text_contains_any(value: str, tokens: list[str]) -> str | None:
    low = value.lower()
    for token in tokens:
        if not token:
            continue
        if str(token).lower() in low:
            return token
    return None


def is_valid_source_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    if not v.startswith("https://"):
        return False
    try:
        parsed = urllib.parse.urlparse(v)
    except Exception:
        return False
    if not parsed.netloc or "." not in parsed.netloc:
        return False
    return True


def post_anchor_date(post_path: Path) -> datetime.date | None:
    name = post_path.parent.name
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})$", name)
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def load_recent_history(post_path: Path) -> dict | None:
    history_path = post_path.parent / "research" / "recent_history.json"
    if not history_path.exists():
        return None
    try:
        return json.loads(history_path.read_text())
    except Exception:
        return None


def row_within_days(row: dict, days: int, anchor: datetime.date) -> bool:
    raw = row.get("date_sort") or row.get("job_date") or ""
    if not raw:
        return False
    try:
        dt = datetime.datetime.fromisoformat(raw).date()
    except Exception:
        try:
            dt = datetime.datetime.strptime(raw, "%Y-%m-%d").date()
        except Exception:
            return False
    delta = (anchor - dt).days
    return 0 < delta <= days


def card_text_blob(card: dict) -> str:
    return "\n".join([
        str(card.get("eyebrow") or ""),
        str(card.get("headline") or ""),
        str(card.get("body") or ""),
        " ".join(str(x) for x in (card.get("bullets") or [])),
        str(card.get("footer") or ""),
    ])


def load_last_n_days_card6(post_path: Path, days: int) -> list[tuple[str, str]]:
    parent = post_path.parent.parent
    today = post_path.parent.name
    out: list[tuple[str, str]] = []
    if not parent.is_dir():
        return out
    candidates = []
    for d in parent.iterdir():
        if not d.is_dir():
            continue
        if d.name == today:
            continue
        if not re.match(r"\d{4}-\d{2}-\d{2}$", d.name):
            continue
        candidates.append(d)
    candidates.sort(key=lambda d: d.name, reverse=True)
    for d in candidates[:days]:
        pj = d / "post.json"
        if not pj.exists():
            continue
        try:
            old = json.loads(pj.read_text())
        except Exception:
            continue
        old_cards = old.get("cards") or []
        if old_cards:
            out.append((d.name, card_text_blob(old_cards[-1])))
    return out


def tokenize_for_relevance(s: str) -> set[str]:
    s = (s or "")
    # Split CamelCase / PascalCase boundaries so "AmazonSeller" → "amazon seller".
    # This makes English hashtag matching robust against the common
    # camel-cased tag spellings used on XHS / IG.
    s_split = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
    s_split = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", s_split)
    s_lower = s_split.lower()
    tokens: set[str] = set(re.findall(r"[a-z0-9]+", s_lower))
    han = re.sub(r"[^一-龥]", " ", s)
    for chunk in han.split():
        for size in (2, 3):
            for i in range(len(chunk) - size + 1):
                tokens.add(chunk[i:i + size])
    return tokens


def hashtag_relevance_ratio(tags: list[str], post: dict) -> float:
    # Defensive: caller already guards `len(tags) >= hashtag_min` before
    # calling, so empty tags is unreachable in normal flow. Kept for
    # robustness if the function is reused elsewhere.
    if not tags:
        return 1.0
    topic = post.get("topic") or {}
    xhs = post.get("xhs") or {}
    cards = post.get("cards") or []
    corpus = " ".join([
        str(topic.get("angle") or ""),
        str(topic.get("category") or ""),
        str(topic.get("why_now") or ""),
        str(xhs.get("title") or ""),
        # Include body + opening hook for text-only platforms (LinkedIn, X)
        # where cards/title are empty — the body IS the post.
        str(xhs.get("opening_hook") or ""),
        str(xhs.get("content") or ""),
        " ".join(str(t) for t in (xhs.get("thread") or [])),
        " ".join(str(c.get("headline") or "") for c in cards),
        " ".join(str(c.get("eyebrow") or "") for c in cards),
    ])
    corpus_tokens = tokenize_for_relevance(corpus)
    if not corpus_tokens:
        return 1.0
    relevant = 0
    for tag in tags:
        tag_tokens = tokenize_for_relevance(tag)
        if tag_tokens & corpus_tokens:
            relevant += 1
    return relevant / len(tags)


def x_weighted_length(text: str) -> int:
    """X (Twitter) weighted length per twitter-text spec.

    Weight 1 (basic Latin scripts and a few related ranges):
      - Latin + Latin-1 Supplement (0000-00FF)
      - Latin Extended-A / B (0100-024F)
      - IPA Extensions (0250-02AF)
      - Spacing Modifier Letters (02B0-02FF)
      - Combining Diacritical Marks (0300-036F)
      - Cyrillic + Cyrillic Supplement (0400-052F)

    Weight 2: everything else, including CJK Unified Ideographs (4E00-9FFF),
    Hiragana (3040-309F), Katakana (30A0-30FF), Hangul Syllables
    (AC00-D7AF), full-width punctuation (FF00-FFEF), and emoji.

    A 280-weight limit therefore allows ~280 ASCII chars, ~140 Chinese
    chars, or any mix in between.
    """
    weight = 0
    for ch in text:
        cp = ord(ch)
        is_weight_1 = (
            cp <= 0x00FF or                 # Latin + Latin-1 Supplement
            0x0100 <= cp <= 0x024F or       # Latin Extended-A / B
            0x0250 <= cp <= 0x02AF or       # IPA Extensions
            0x02B0 <= cp <= 0x02FF or       # Spacing Modifier Letters
            0x0300 <= cp <= 0x036F or       # Combining Diacritical
            0x0400 <= cp <= 0x052F          # Cyrillic + Cyrillic Supplement
        )
        weight += 1 if is_weight_1 else 2
    return weight


def platform_body_length(text: str, platform: str) -> int:
    """Effective body length for the platform's character limit check."""
    if platform == "x":
        return x_weighted_length(text)
    return len(text)


def bullets_have_parallel_dimensions(bullets: list) -> bool:
    if len(bullets) < 2:
        return False
    blob = " ".join(str(b) for b in bullets)
    if any(p.search(blob) for p in PARALLEL_DIM_PATTERNS):
        return True
    parallel_prefix = sum(
        1 for b in bullets if PARALLEL_DIM_PREFIX.match(str(b).strip())
    )
    return parallel_prefix >= 2


# ---------- Validation ----------

def validate(post_path: Path, config: dict) -> tuple[list[str], list[str], dict, list[str]]:
    # Read + parse the post file with explicit guards. Without these, a
    # corrupt post.json (trailing comma, unbalanced brace) would surface
    # as a Python traceback to the user — and render.mjs runs validate.py
    # as a subprocess BEFORE doing its own JSON.parse, so render.mjs's
    # nice error message never fires unless validate.py reports cleanly.
    try:
        raw = post_path.read_text()
    except OSError as err:
        return (
            [f"cannot read {post_path}: {err}"],
            [], {"post_json": str(post_path)}, [],
        )
    try:
        post = json.loads(raw)
    except json.JSONDecodeError as err:
        return (
            [
                f"post.json is malformed JSON: {err.msg} (line {err.lineno}, col {err.colno})",
                f"file: {post_path}",
                "common causes: trailing commas, unbalanced braces, unescaped quotes inside strings",
            ],
            [], {"post_json": str(post_path)}, [],
        )
    if not isinstance(post, dict):
        return (
            [f"post.json top-level must be a JSON object, got {type(post).__name__}"],
            [], {"post_json": str(post_path)}, [],
        )
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    persona_cfg = config.get("persona") or {}
    title_cfg = config.get("title_constraints") or {}
    forbidden_brands = config.get("forbidden_brands_in_copy") or []
    forbidden_sources = config.get("forbidden_source_tokens") or []
    angle_quotas = config.get("angle_quotas") or {}

    language = (config.get("output_language") or "zh").strip().lower()
    if language not in CTA_TOKENS_BY_LANG:
        warnings.append(
            f"unknown output_language={language!r}; falling back to 'zh'. "
            f"supported: {sorted(CTA_TOKENS_BY_LANG.keys())}"
        )
        language = "zh"

    platform = (config.get("platform") or DEFAULT_PLATFORM).strip().lower()
    if platform not in PLATFORM_PRESETS:
        warnings.append(
            f"unknown platform={platform!r}; falling back to {DEFAULT_PLATFORM!r}. "
            f"supported: {sorted(PLATFORM_PRESETS.keys())}"
        )
        platform = DEFAULT_PLATFORM
    preset = PLATFORM_PRESETS[platform]

    cta_tokens_cfg = config.get("cta_tokens")
    if cta_tokens_cfg is None:
        cta_tokens = list(CTA_TOKENS_BY_LANG[language])
    else:
        cta_tokens = [str(x).strip() for x in cta_tokens_cfg if str(x).strip()]
        if not cta_tokens:
            info.append(
                "config.cta_tokens is set to an empty list — last-card CTA token "
                "check is DISABLED. Set to null to use the language default, or "
                "provide ['like', 'follow', ...] to override the vocabulary."
            )

    decision_verbs_cfg = config.get("decision_verbs")
    if decision_verbs_cfg is None:
        decision_verbs = list(DECISION_VERBS_BY_LANG[language])
    else:
        decision_verbs = [str(x).strip() for x in decision_verbs_cfg if str(x).strip()]
        if not decision_verbs:
            info.append(
                "config.decision_verbs is set to an empty list — ai-workflow "
                "card 5 decision-verb soft-warn is DISABLED. Set to null to use "
                "the language default."
            )

    expected_brand_cn = (persona_cfg.get("brand_cn") or "").strip()
    if not expected_brand_cn or expected_brand_cn.startswith("REPLACE_ME"):
        errors.append(
            "config.persona.brand_cn is empty or unfilled; copy config.example.json "
            "and set your account brand string before validating"
        )

    # Title length cap. Three states:
    #   - max_chars: null  → use platform preset
    #   - max_chars: 0     → no cap (special-case for "ignore platform preset")
    #   - max_chars: N>0   → enforce N as the cap
    # Note this differs from cta_tokens / decision_verbs (where null = use
    # language default and [] = disable). The title knob's null-vs-0 distinction
    # is intentional — many users want to keep the platform default but not
    # special-case empty arrays here.
    title_max_cfg = title_cfg.get("max_chars")
    if title_max_cfg is not None:
        try:
            title_max = int(title_max_cfg)
        except (TypeError, ValueError):
            errors.append(
                f"config.title_constraints.max_chars must be an integer or null, "
                f"got {title_max_cfg!r} ({type(title_max_cfg).__name__})"
            )
            title_max = int(preset["title_max"]) if preset["title_max"] else 0
    else:
        title_max = int(preset["title_max"]) if preset["title_max"] else 0
    raw_must_contain = title_cfg.get("must_contain")
    if raw_must_contain is None:
        must_contain_list = list(DEFAULT_TITLE_KEYWORDS_BY_LANG[language])
    elif not isinstance(raw_must_contain, list):
        must_contain_list = [str(raw_must_contain)]
    else:
        must_contain_list = [str(x) for x in raw_must_contain if str(x).strip()]
        if not must_contain_list:
            info.append(
                "config.title_constraints.must_contain is set to an empty list — "
                "the must-contain keyword check (across title / body / cards / "
                "hashtags) is DISABLED. Set to null to use the language default, "
                "or ['Amazon', ...] to require any of those tokens."
            )
    must_contain_lower = [kw.lower() for kw in must_contain_list]

    xhs = post.get("xhs") or {}
    persona = post.get("persona") or {}
    design = post.get("design") or {}
    cards = post.get("cards") or []
    topic = post.get("topic") or {}

    title = str(xhs.get("title") or "").strip()
    content = str(xhs.get("content") or "").strip()
    thread = xhs.get("thread") or []

    # Validate raw tag input shape before normalizing. We surface a clean
    # error for None / int / dict entries instead of letting them fall
    # through to .lower() and crash with AttributeError.
    raw_tag_sources = [
        ("xhs.tags", (xhs.get("tags") if isinstance(xhs.get("tags"), list) else None)),
        ("seo.hashtags", ((post.get("seo") or {}).get("hashtags") if isinstance((post.get("seo") or {}).get("hashtags"), list) else None)),
    ]
    for src_name, raw_list in raw_tag_sources:
        if raw_list is None:
            continue
        bad = [(i, v) for i, v in enumerate(raw_list) if not isinstance(v, str)]
        if bad:
            errors.append(
                f"{src_name} contains non-string entries at index "
                f"{[i for i, _ in bad]} (values: {[type(v).__name__ for _, v in bad]}) "
                f"— hashtags must all be strings"
            )

    tags = normalized_tags(post)

    # Title checks — only enforced when the platform has a title concept.
    # The must_contain keyword check is intentionally NOT done here at the
    # title level; it's checked against the full public corpus further
    # below so that text-only platforms (LinkedIn, X, IG with empty title)
    # still get the keyword requirement enforced via body / thread / cards.
    if preset["title_required"] and not title:
        errors.append("xhs.title is empty")
    if title and title_max > 0 and len(title) > title_max:
        errors.append(
            f"xhs.title exceeds {title_max} characters (platform={platform!r}): {len(title)}"
        )

    # Improvement 2: warn when title appears verbatim in content's opening
    # (carousel platforms only — visual redundancy when first card and post body
    # both lead with the same line). Compare lowercase, prefix-2x window.
    if preset["renders_cards"] and title and content:
        prefix_window = content.lower()[:max(len(title) * 2, 60)]
        if title.lower() in prefix_window:
            warnings.append(
                f"xhs.title ({title!r}) appears verbatim in the opening of xhs.content; "
                f"consider varying the headline to avoid visual redundancy in post.md"
            )

    # Body cap (skipped if preset.body_max is None, e.g. xiaohongshu uses
    # soft target rather than hard cap). For X, CJK characters count as
    # weight 2 toward the 280-char limit (twitter-text spec).
    if preset["body_max"] is not None:
        eff_len = platform_body_length(content, platform)
        if eff_len > preset["body_max"]:
            note = ""
            if platform == "x" and eff_len != len(content):
                note = f" (CJK weighting: {len(content)} chars → {eff_len} weight)"
            errors.append(
                f"xhs.content exceeds {preset['body_max']} characters "
                f"(platform={platform!r}): {eff_len}{note}"
            )

    # Thread mode (X / Threads). Each post must respect body_max.
    if preset.get("supports_thread") and thread:
        # X-specific: content and thread are mutually exclusive
        if platform == "x" and content and thread:
            errors.append(
                f"xhs.content and xhs.thread are mutually exclusive for platform {platform!r}; "
                f"set xhs.content for a single tweet OR xhs.thread for a thread, not both"
            )
        thread_limit = preset.get("thread_max_posts")
        per_post_limit = preset["body_max"]
        if thread_limit and len(thread) > thread_limit:
            errors.append(
                f"xhs.thread has {len(thread)} posts but platform "
                f"{platform!r} caps threads at {thread_limit}"
            )
        # Improvement 1: soft-warn for X threads >10 posts (drop-off is steep
        # after 7-8 in practice; engagement data shows 5-7 is the sweet spot).
        if platform == "x" and len(thread) > 10:
            warnings.append(
                f"xhs.thread has {len(thread)} posts; X engagement drops sharply "
                f"after ~7 tweets. Consider splitting into multiple threads or "
                f"compressing to 5-7 posts."
            )
        for i, item in enumerate(thread):
            t = str(item or "").strip()
            t_len = platform_body_length(t, platform)
            if per_post_limit and t_len > per_post_limit:
                note = ""
                if platform == "x" and t_len != len(t):
                    note = f" (CJK weighting: {len(t)} chars → {t_len} weight)"
                errors.append(
                    f"xhs.thread[{i}] exceeds {per_post_limit} characters: {t_len}{note}"
                )
    elif thread and not preset.get("supports_thread"):
        # Hard-fail: thread on a platform that doesn't support it would silently
        # drop the thread content during render. Better to make the user pick.
        errors.append(
            f"xhs.thread is set but platform {platform!r} does not support thread mode. "
            f"Either remove xhs.thread, or switch to a thread-capable platform (e.g. 'x')."
        )

    if expected_brand_cn and persona.get("brand_cn") != expected_brand_cn:
        errors.append(
            f"persona.brand_cn must be {expected_brand_cn!r} "
            f"(matches config.persona.brand_cn)"
        )

    # Design.style only applies to platforms that render cards.
    if preset["renders_cards"] and design.get("style") not in ALLOWED_STYLES:
        errors.append(
            f"design.style must be one of {sorted(ALLOWED_STYLES)} "
            f"(older v1/v2/v3 layouts are deprecated)"
        )

    # Card count range from platform preset.
    card_min = preset["card_min"]
    card_max = preset["card_max"]
    if card_max == 0:
        # Text-only platform — cards must be empty.
        if cards:
            errors.append(
                f"platform {platform!r} is text-only (no carousel); "
                f"cards must be empty, got {len(cards)}"
            )
    else:
        if not (card_min <= len(cards) <= card_max):
            errors.append(
                f"cards length must be {card_min}-{card_max} for platform "
                f"{platform!r}, got {len(cards)}"
            )
        if "cards_min" in design and design.get("cards_min") != card_min:
            warnings.append(
                f"design.cards_min={design.get('cards_min')} but platform "
                f"{platform!r} expects {card_min}"
            )
        if "cards_max" in design and design.get("cards_max") != card_max:
            warnings.append(
                f"design.cards_max={design.get('cards_max')} but platform "
                f"{platform!r} expects {card_max}"
            )

    # Hashtag-block-in-body requirement is platform-driven. Read explicitly
    # from PLATFORM_PRESETS; fall back to the legacy inference for forward-
    # compatibility with older preset blobs that lack the explicit key.
    requires_inbody_hashtags = preset.get(
        "requires_inbody_hashtags",
        preset["renders_cards"] or preset["format"] == "carousel",
    )
    if requires_inbody_hashtags and xhs.get("append_hashtags_to_content", True) is not True:
        errors.append("xhs.append_hashtags_to_content must be true for this platform")

    hashtag_min = preset["hashtag_min"]
    hashtag_max = preset["hashtag_max"]
    hashtag_token_max = preset["hashtag_token_max"]
    if len(tags) < hashtag_min:
        errors.append(
            f"hashtag count must be >= {hashtag_min} for {platform!r}, got {len(tags)}"
        )
    if len(tags) > hashtag_max:
        errors.append(
            f"hashtag count must be <= {hashtag_max} for {platform!r}, got {len(tags)}"
        )
    overlong = [t for t in tags if len(t) > hashtag_token_max]
    if overlong:
        errors.append(
            f"hashtags exceeding {hashtag_token_max} chars for {platform!r}: {overlong}"
        )
    # Hashtag-level must_contain check (case-insensitive). Useful for platforms
    # where hashtag-driven discovery matters (XHS, IG). For text-only platforms
    # with low hashtag count this is a weaker signal but still checked when
    # tags are present.
    if tags and must_contain_lower and not any(
        any(kw in t.lower() for kw in must_contain_lower) for t in tags
    ):
        errors.append(
            f"at least one hashtag must include one of {must_contain_list} (case-insensitive)"
        )

    topic_sources = (post.get("topic") or {}).get("sources") or []
    for idx, src in enumerate(topic_sources):
        if not is_valid_source_url(src):
            errors.append(
                f"topic.sources[{idx}] is not a real https:// URL: {src!r}"
            )

    merged_public = [title, content]
    # Include thread items so X / threads-mode posts contribute to corpus checks.
    for t_item in thread:
        merged_public.append(str(t_item or ""))
    for card in cards:
        merged_public.extend([
            str(card.get("eyebrow") or ""),
            str(card.get("headline") or ""),
            str(card.get("body") or ""),
            " ".join(str(x) for x in (card.get("bullets") or [])),
            str(card.get("footer") or ""),
        ])
    public_blob = "\n".join(merged_public)
    public_blob_lower = public_blob.lower()

    # CORPUS-LEVEL must_contain check: at least one keyword must appear
    # somewhere in the public copy (title / body / thread / cards). Replaces
    # the old title-only check which silently bypassed when title was empty
    # (Bug 1 in v1.3.0 audit). Case-insensitive throughout.
    if must_contain_lower and not any(kw in public_blob_lower for kw in must_contain_lower):
        errors.append(
            f"public copy must mention at least one of {must_contain_list} "
            f"somewhere in title / body / thread / cards (case-insensitive). "
            f"Per config.title_constraints.must_contain."
        )
    src_token = text_contains_any(public_blob, forbidden_sources)
    if src_token:
        errors.append(
            f"public content leaks source token from forbidden_source_tokens: {src_token!r}"
        )
    brand_leak = text_contains_any(public_blob, forbidden_brands)
    if brand_leak:
        errors.append(
            f"public content leaks brand from forbidden_brands_in_copy: {brand_leak!r}"
        )

    if cards and cta_tokens:
        last_blob = card_text_blob(cards[-1]).lower()
        if not any(token.lower() in last_blob for token in cta_tokens):
            errors.append(
                f"last card must contain at least one CTA token from {cta_tokens}"
            )

    anchor = post_anchor_date(post_path) or datetime.date.today()
    recent_history = load_recent_history(post_path)
    history_rows = (recent_history or {}).get("recent_posts") or []

    cold_start = recent_history is None or not history_rows
    if cold_start:
        if recent_history is None:
            info.append(
                "no recent_history.json found in research/ — "
                "skipping 7-day title dedup, 3-day CTA similarity, and 14-day ceiling checks "
                "(cold-start mode)"
            )
        else:
            info.append(
                "recent_history.json exists but contains zero posts — "
                "dedup checks will silently skip until at least one historical post is recorded "
                "(cold-start mode)"
            )

    if title and history_rows:
        last_7d_titles = [
            (r.get("title") or "").strip()
            for r in history_rows
            if row_within_days(r, RECENT_TITLE_WINDOW_DAYS, anchor)
        ]
        if title in last_7d_titles:
            errors.append(
                f"xhs.title duplicates a title from the last {RECENT_TITLE_WINDOW_DAYS} days: {title!r}"
            )

    if cards:
        current_card6 = card_text_blob(cards[-1]).strip()
        if current_card6:
            for old_date, old_card6 in load_last_n_days_card6(post_path, RECENT_CTA_WINDOW_DAYS):
                if not old_card6.strip():
                    continue
                ratio = SequenceMatcher(None, current_card6, old_card6).ratio()
                if ratio >= CTA_SIMILARITY_THRESHOLD:
                    errors.append(
                        f"card 6 CTA too similar to {old_date} (similarity {ratio:.2f} >= {CTA_SIMILARITY_THRESHOLD}); "
                        f"rotate per references/title-and-cta-patterns.md"
                    )
                    break

    # Hashtag relevance check only applies when the platform actually
    # uses hashtags meaningfully (i.e. requires a non-zero minimum). Skip
    # for X / single-tweet platforms where hashtags are decorative.
    if hashtag_min > 0 and len(tags) >= hashtag_min:
        ratio = hashtag_relevance_ratio(tags, post)
        if ratio < HASHTAG_RELEVANCE_MIN_RATIO:
            errors.append(
                f"hashtag relevance too low: {ratio:.0%} of tags share a token with topic/headlines "
                f"(need >= {HASHTAG_RELEVANCE_MIN_RATIO:.0%}); see references/title-and-cta-patterns.md hashtag tiering"
            )

    current_category = (topic.get("category") or "").strip()
    if current_category and current_category in angle_quotas and history_rows:
        recent_14d = [
            r for r in history_rows
            if row_within_days(r, 14, anchor)
        ]
        same_cat_count = sum(
            1 for r in recent_14d
            if (r.get("category") or "").strip() == current_category
        )
        ceiling = int(angle_quotas[current_category].get("ceiling") or 99)
        if same_cat_count + 1 > ceiling:
            warnings.append(
                f"category {current_category!r} would reach {same_cat_count + 1} in last 14 days "
                f"(ceiling {ceiling}); see references/angle-rotation.md"
            )

    if current_category == "ai-workflow" and len(cards) >= 5 and decision_verbs:
        card5 = cards[4]
        card5_blob = (str(card5.get("body") or "") + " " + " ".join(
            str(b) for b in (card5.get("bullets") or [])
        )).lower()
        if not any(v.lower() in card5_blob for v in decision_verbs):
            warnings.append(
                f"ai-workflow card 5 body missing decision verb from {decision_verbs[:6]}…; "
                f"frame around what decision changes, not just what time saves"
            )

    for idx, card in enumerate(cards, start=1):
        if (card.get("kind") or "").strip() == "matrix":
            continue
        bullets = card.get("bullets") or []
        if bullets_have_parallel_dimensions(bullets):
            warnings.append(
                f"card_{idx:02d} bullets look like parallel categories "
                f"(第N步/第N种/类型N) but kind != 'matrix' — consider matrix kind"
            )

    summary = {
        "title": title,
        "title_length": len(title),
        "cards": len(cards),
        "thread_posts": len(thread) if isinstance(thread, list) else 0,
        "body_length": len(content),
        "style": design.get("style"),
        "tags": tags,
        "category": current_category,
        "language": language,
        "platform": platform,
        "history_rows": len(history_rows),
        "cold_start": cold_start,
    }
    return errors, warnings, summary, info


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("post_json", help="path to post.json to validate")
    parser.add_argument("--config", default=None, help="path to config.json")
    parser.add_argument("--json", action="store_true", help="emit JSON payload to stdout")
    args = parser.parse_args()

    config = load_config(args.config)
    post_path = Path(args.post_json).expanduser().resolve()
    errors, warnings, summary, info = validate(post_path, config)

    payload = {
        "ok": not errors,
        "post_json": str(post_path),
        "summary": summary,
        "errors": errors,
        "warnings": warnings,
        "info": info,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"ok={payload['ok']}")
        for key, value in summary.items():
            print(f"{key}={value}")
        for note in info:
            print(f"info: {note}")
        if errors:
            print("errors:")
            for error in errors:
                print(f"- {error}")
        if warnings:
            print("warnings (soft — exit 0):")
            for warning in warnings:
                print(f"- {warning}")

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
