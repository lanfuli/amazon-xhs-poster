#!/usr/bin/env python3
"""Build the recent_history.json + recent_history.md guardrail used by the
editorial stage to dedup angles / titles / categories within a rolling window.

Reads `paths.drafts_root` and `paths.history_lookback_days` from config.json
(unless overridden by --drafts-root / --days). Output paths are required.

Resolution order for config:
  1. --config <path>
  2. XHS_AMAZON_CONFIG env var
  3. ~/.config/amazon-xhs-poster/config.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


DEFAULT_ANGLE_KEYWORDS = [
    "关税", "tariff", "广告费", "回款", "现金流", "利润", "折扣",
    "COSMO", "Rufus", "算法", "排名", "买家意图", "search", "ranking",
    "广告", "PPC", "否词", "negative", "predicted impact", "ASIN", "搜索词",
    "listing", "review", "评论", "差评", "封号", "停售", "stop selling",
    "断货", "库存", "FBA", "FBM",
    "Buy with Prime", "Brand Registry", "Project Zero",
    "Walmart Marketplace", "Walmart Connect",
    "AI agent", "generative", "Nano", "automation",
    "供应链", "越南", "印度", "墨西哥", "China",
    "选品", "新品", "上架", "投放", "测款",
]

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
        return {}
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def infer_date_string(*candidates):
    for candidate in candidates:
        raw = (candidate or "").strip()
        if not raw:
            continue
        for pattern, fmt, render in (
            (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d", lambda m: m.group(1)),
            (r"(\d{4})(\d{2})(\d{2})", "%Y%m%d", lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
        ):
            match = re.search(pattern, raw)
            if not match:
                continue
            normalized = render(match)
            try:
                return normalized, datetime.strptime(normalized, "%Y-%m-%d")
            except Exception:
                continue
    return (candidates[0] or "").strip(), None


def load_post(path: Path):
    try:
        data = json.loads(path.read_text())
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    title = (((data.get("xhs") or {}).get("title")) or "").strip()
    angle = (((data.get("topic") or {}).get("angle")) or "").strip()
    category = (((data.get("topic") or {}).get("category")) or "").strip()
    why_now = (((data.get("topic") or {}).get("why_now")) or "").strip()
    tags = ((data.get("seo") or {}).get("hashtags")) or []
    sources = ((data.get("topic") or {}).get("sources")) or []
    if not title and not angle:
        return None
    publish_result = path.parent / "publish" / "publish_result.json"
    published_at = ""
    if publish_result.exists():
        try:
            published_at = str((json.loads(publish_result.read_text()).get("published_at") or "")).strip()
        except Exception:
            published_at = ""
    job_date, dt = infer_date_string(data.get("job_date"), path.parent.name, published_at)
    return {
        "job_date": job_date,
        "date_sort": dt.isoformat() if dt else "",
        "title": title,
        "angle": angle,
        "category": category,
        "hashtags": [str(x) for x in tags][:8],
        "why_now": why_now,
        "sources": [str(x) for x in sources],
        "post_json": str(path),
    }


def is_history_eligible(post_path: Path) -> bool:
    cards_dir = post_path.parent / "cards"
    if (cards_dir / "render_manifest.json").exists():
        return True
    if (cards_dir / "card_06.png").exists():
        return True

    publish_result = post_path.parent / "publish" / "publish_result.json"
    if not publish_result.exists():
        return False
    try:
        result = json.loads(publish_result.read_text())
    except Exception:
        return False
    if result.get("published") is True:
        return True
    if result.get("status") == "draft_saved" and result.get("ok") is True and result.get("drafted") is True:
        return True
    return False


def keyword_frequency(rows: list[dict], keywords: list[str]) -> list[tuple[str, int, list[str]]]:
    hits = defaultdict(list)
    for row in rows:
        blob = " ".join([row.get("title") or "", row.get("angle") or ""]).lower()
        for kw in keywords:
            if kw.lower() in blob:
                hits[kw].append(row.get("job_date") or "")
    out = [(kw, len(dates), dates) for kw, dates in hits.items() if len(dates) >= 2]
    out.sort(key=lambda x: (-x[1], x[0]))
    return out


def render_markdown(payload: dict, keywords: list[str]) -> str:
    window = payload.get("window_days", 30)
    rows = payload.get("recent_posts", [])
    total = len(rows)

    lines = [
        "# Recent Amazon XHS History",
        "",
        f"Lookback: last {window} days. Total: {total} post(s).",
        "",
        "Use this file to avoid repeating the same topic family / title pattern / core angle within the lookback window.",
        "",
    ]

    if not rows:
        lines.append("_(no posts in window — cold start)_")
        return "\n".join(lines) + "\n"

    by_cat = defaultdict(list)
    for row in rows:
        by_cat[row.get("category") or "(uncategorized)"].append(row)

    lines.append("## By Category")
    lines.append("")
    for cat in sorted(by_cat.keys(), key=lambda c: (-len(by_cat[c]), c)):
        items = sorted(by_cat[cat], key=lambda r: r.get("date_sort") or r.get("job_date") or "")
        lines.append(f"### {cat} ({len(items)} post{'s' if len(items) != 1 else ''})")
        lines.append("")
        for r in items:
            date = r.get("job_date") or "(undated)"
            title = r.get("title") or "(untitled)"
            angle = r.get("angle") or ""
            lines.append(f"- **{date}** — {title}")
            if angle and angle != title:
                lines.append(f"  - angle: {angle}")
        lines.append("")

    kfreq = keyword_frequency(rows, keywords)
    if kfreq:
        lines.append("## Angle keyword frequency")
        lines.append("")
        lines.append(f"Keywords appearing >= 2 times across titles + angles in the last {window} days. Treat anything >= 3 mentions as saturated.")
        lines.append("")
        for kw, count, dates in kfreq[:15]:
            sample = ", ".join(dates[:6])
            lines.append(f"- `{kw}`: {count} mentions ({sample})")
        lines.append("")

    lines.append("## All posts (chronological)")
    lines.append("")
    for r in sorted(rows, key=lambda r: r.get("date_sort") or r.get("job_date") or ""):
        date = r.get("job_date") or "(undated)"
        cat = r.get("category") or "(uncat)"
        title = r.get("title") or "(untitled)"
        lines.append(f"- {date} | {cat} | {title}")
    lines.append("")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=None, help="path to config.json")
    parser.add_argument("--drafts-root", default=None,
                        help="overrides config.paths.drafts_root")
    parser.add_argument("--days", type=int, default=None,
                        help="overrides config.paths.history_lookback_days (default 30)")
    parser.add_argument("--output-json", required=True,
                        help="where to write recent_history.json")
    parser.add_argument("--output-md", default=None,
                        help="where to write recent_history.md (optional)")
    args = parser.parse_args()

    config = load_config(args.config)
    paths_cfg = (config.get("paths") or {})

    drafts_root_raw = args.drafts_root or paths_cfg.get("drafts_root")
    if not drafts_root_raw:
        sys.exit("no drafts_root: set config.paths.drafts_root or pass --drafts-root")
    draft_root = Path(drafts_root_raw).expanduser().resolve()
    if not draft_root.is_dir():
        sys.exit(f"drafts_root does not exist: {draft_root}")

    days = args.days if args.days is not None else int(paths_cfg.get("history_lookback_days") or 30)

    keywords = list(DEFAULT_ANGLE_KEYWORDS) + list(config.get("extra_angle_keywords") or [])

    output_json = Path(args.output_json).expanduser().resolve()
    output_md = Path(args.output_md).expanduser().resolve() if args.output_md else None

    rows = []
    for post in sorted(draft_root.glob("*/post.json")):
        if "_smoke-tests" in post.parts:
            continue
        if not is_history_eligible(post):
            continue
        loaded = load_post(post)
        if loaded:
            rows.append(loaded)

    rows.sort(key=lambda x: x["date_sort"] or x["job_date"])

    parsed_dates = [
        datetime.fromisoformat(row["date_sort"])
        for row in rows
        if row.get("date_sort")
    ]
    if parsed_dates:
        anchor = max(parsed_dates)
        cutoff = anchor - timedelta(days=max(days - 1, 0))
        recent = [
            row for row in rows
            if row.get("date_sort") and datetime.fromisoformat(row["date_sort"]) >= cutoff
        ]
    else:
        recent = rows[-days:]
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "window_days": days,
        "count": len(recent),
        "recent_posts": recent,
        "recent_titles": [x["title"] for x in recent if x["title"]],
        "recent_angles": [x["angle"] for x in recent if x["angle"]],
        "recent_categories": [x["category"] for x in recent if x["category"]],
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    if output_md:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(payload, keywords))

    print(f"wrote {payload['count']} post(s) within {days}-day window to {output_json}")
    if output_md:
        print(f"wrote markdown summary to {output_md}")


if __name__ == "__main__":
    main()
