#!/usr/bin/env python3
"""Validate an Amazon XHS post.json against the rules defined in config.json.

This is a parameterized port of the in-house validator
(`validate-amazon-xhs-post.py`). All hardcoded persona / brand / forbidden
tokens / angle ceilings have been moved to config.json so anyone can use the
same methodology with their own account, voice, and confidentiality boundary.

Resolution order for config:
  1. --config <path> argument
  2. XHS_AMAZON_CONFIG env var
  3. ~/.config/amazon-xhs-poster/config.json
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
HASHTAG_MIN = 5
HASHTAG_MAX = 10
HASHTAG_MAX_LEN = 12

RECENT_TITLE_WINDOW_DAYS = 7
RECENT_CTA_WINDOW_DAYS = 3
CTA_SIMILARITY_THRESHOLD = 0.7
HASHTAG_RELEVANCE_MIN_RATIO = 0.6

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

DEFAULT_CONFIG_PATH = Path("~/.config/amazon-xhs-poster/config.json").expanduser()


def resolve_config_path(cli_path: str | None) -> Path | None:
    if cli_path:
        return Path(cli_path).expanduser().resolve()
    env = os.environ.get("XHS_AMAZON_CONFIG")
    if env:
        return Path(env).expanduser().resolve()
    if DEFAULT_CONFIG_PATH.exists():
        return DEFAULT_CONFIG_PATH
    return None


def load_config(cli_path: str | None) -> dict:
    path = resolve_config_path(cli_path)
    if not path:
        raise SystemExit(
            "no config.json found; pass --config <path>, set XHS_AMAZON_CONFIG, "
            f"or place a config at {DEFAULT_CONFIG_PATH}"
        )
    if not path.exists():
        raise SystemExit(f"config not found: {path}")
    return json.loads(path.read_text())


# ---------- Helpers ----------

def normalized_tags(post: dict) -> list[str]:
    xhs_tags = (post.get("xhs") or {}).get("tags") or []
    seo_tags = (post.get("seo") or {}).get("hashtags") or []
    chosen = xhs_tags if xhs_tags else seo_tags
    out: list[str] = []
    seen: set[str] = set()
    for raw in chosen:
        tag = str(raw).lstrip("#").strip().replace(" ", "")
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
    if not (v.startswith("http://") or v.startswith("https://")):
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
    # This makes English hashtag matching robust against the common XHS / Lemon8
    # convention of camel-cased tag spellings.
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
    post = json.loads(post_path.read_text())
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

    cta_tokens_cfg = config.get("cta_tokens")
    if cta_tokens_cfg is None:
        cta_tokens = list(CTA_TOKENS_BY_LANG[language])
    else:
        cta_tokens = [str(x).strip() for x in cta_tokens_cfg if str(x).strip()]

    decision_verbs_cfg = config.get("decision_verbs")
    if decision_verbs_cfg is None:
        decision_verbs = list(DECISION_VERBS_BY_LANG[language])
    else:
        decision_verbs = [str(x).strip() for x in decision_verbs_cfg if str(x).strip()]

    expected_brand_cn = (persona_cfg.get("brand_cn") or "").strip()
    if not expected_brand_cn or expected_brand_cn.startswith("REPLACE_ME"):
        errors.append(
            "config.persona.brand_cn is empty or unfilled; copy config.example.json "
            "and set your account brand string before validating"
        )

    title_max = int(title_cfg.get("max_chars") or 20)
    raw_must_contain = title_cfg.get("must_contain")
    if raw_must_contain is None:
        must_contain_list = list(DEFAULT_TITLE_KEYWORDS_BY_LANG[language])
    elif not isinstance(raw_must_contain, list):
        must_contain_list = [str(raw_must_contain)]
    else:
        must_contain_list = [str(x) for x in raw_must_contain if str(x).strip()]

    xhs = post.get("xhs") or {}
    persona = post.get("persona") or {}
    design = post.get("design") or {}
    cards = post.get("cards") or []
    topic = post.get("topic") or {}

    title = str(xhs.get("title") or "").strip()
    content = str(xhs.get("content") or "").strip()
    tags = normalized_tags(post)

    if not title:
        errors.append("xhs.title is empty")
    if len(title) > title_max:
        errors.append(f"xhs.title exceeds {title_max} characters: {len(title)}")
    if must_contain_list and title and not any(kw in title for kw in must_contain_list):
        errors.append(
            f"xhs.title must include at least one of {must_contain_list} "
            f"(per config.title_constraints.must_contain)"
        )

    if expected_brand_cn and persona.get("brand_cn") != expected_brand_cn:
        errors.append(
            f"persona.brand_cn must be {expected_brand_cn!r} "
            f"(matches config.persona.brand_cn)"
        )
    if design.get("style") not in ALLOWED_STYLES:
        errors.append(
            f"design.style must be one of {sorted(ALLOWED_STYLES)} "
            f"(older v1/v2/v3 layouts are deprecated)"
        )

    if not (6 <= len(cards) <= 9):
        errors.append(f"cards length must be 6-9, got {len(cards)}")
    if "cards_min" in design and design.get("cards_min") != 6:
        errors.append("design.cards_min must be 6")
    if "cards_max" in design and design.get("cards_max") != 9:
        errors.append("design.cards_max must be 9")

    if xhs.get("append_hashtags_to_content", True) is not True:
        errors.append("xhs.append_hashtags_to_content must be true")

    if len(tags) < HASHTAG_MIN:
        errors.append(f"hashtag count must be >= {HASHTAG_MIN}, got {len(tags)}")
    if len(tags) > HASHTAG_MAX:
        errors.append(f"hashtag count must be <= {HASHTAG_MAX}, got {len(tags)}")
    overlong = [t for t in tags if len(t) > HASHTAG_MAX_LEN]
    if overlong:
        errors.append(f"hashtags exceeding {HASHTAG_MAX_LEN} chars: {overlong}")
    if tags and must_contain_list and not any(
        any(kw in t for kw in must_contain_list) for t in tags
    ):
        errors.append(
            f"at least one hashtag must include one of {must_contain_list}"
        )

    topic_sources = (post.get("topic") or {}).get("sources") or []
    for idx, src in enumerate(topic_sources):
        if not is_valid_source_url(src):
            errors.append(
                f"topic.sources[{idx}] is not a real https:// URL: {src!r}"
            )

    merged_public = [title, content]
    for card in cards:
        merged_public.extend([
            str(card.get("eyebrow") or ""),
            str(card.get("headline") or ""),
            str(card.get("body") or ""),
            " ".join(str(x) for x in (card.get("bullets") or [])),
            str(card.get("footer") or ""),
        ])
    public_blob = "\n".join(merged_public)
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

    if recent_history is None:
        info.append(
            "no recent_history.json found in research/ — "
            "skipping 7-day title dedup, 3-day CTA similarity, and 14-day ceiling checks "
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

    if len(tags) >= HASHTAG_MIN:
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
        "style": design.get("style"),
        "tags": tags,
        "category": current_category,
        "language": language,
        "history_rows": len(history_rows),
        "cold_start": recent_history is None,
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
