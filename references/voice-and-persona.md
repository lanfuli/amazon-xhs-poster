# Voice & Persona — the supremacy rule

## The rule

> **Persona voice > all structural rules.**

The patterns in [`title-and-cta-patterns.md`](title-and-cta-patterns.md) and
the rotation logic in [`angle-rotation.md`](angle-rotation.md) exist to
prevent staleness. They are **not** a checklist that overrides judgment.
When a pattern would force a sentence the persona wouldn't say, **drop the
pattern**, write the natural line, and document why in
`post.json.qa_notes`.

This rule is intentional and load-bearing: structure rules degrade copy
faster than they protect it when applied mechanically.

## Three tiers of rules (in priority order)

| Tier | Source | Examples | Override-able? |
|------|--------|----------|----------------|
| **C** | Voice & taste | "no clickbait", "no marketing brochure feel" | This is the override layer itself |
| **A** | Validator hard-fail | Title length, must-contain keyword, hashtag count, source URL format, persona brand match, last-card CTA token | NO — these are platform/account contracts |
| **B** | Validator soft-warn | 14-day ceiling, AI-workflow decision verb, parallel-dimension bullets | Tier C may override; document in qa_notes |

A and B are mechanical. Tier C is human (or Claude-acting-as-editor)
judgment.

## Defining the persona

Your `config.persona` answers four questions:

1. **Who are they?** (`brand_cn`, `identity`, `location`, `years_experience`)
2. **How do they sound?** (`voice` — keywords like "克制 / 实战 / 不卖鸡汤")
3. **What do they sign with?** (`signature` — usually same as `brand_cn`)
4. **What identity DO they not claim?** (handled by `forbidden_brands_in_copy` —
   make sure your AI-tooling brand names go here so they never leak)

The fewer the words in `voice`, the better. Pick 3–5 adjectives that genuinely
distinguish this account from generic content.

## Voice tests (taste-level, no automation)

Before publishing, ask:

- **3-second test**: does card 1 stop the scroll without clickbait?
- **30-second test**: can a busy seller decide a concrete action by the end?
- **Follow-worthiness**: does a first-time visitor get a credible reason to
  follow, not just "this account exists"?
- **Filter-feeling**: does it read like "this account filters 90% of the
  noise for me"?

Any "no" → back to Stage 2.

## Anti-patterns (drop these voice habits on sight)

| Voice habit | Why it kills | Replace with |
|-------------|--------------|--------------|
| "今天我看了 X" / "I checked X today" | Exposes research stack; reads as content-farm process | Stated conclusion / inferred trend |
| "AI is the future" filler | Generic; no decision change | Concrete decision the seller now makes differently |
| "学会了点赞" / generic XHS CTA filler | Reads as fishing | Specific reason to act (CTA1–CTA6) |
| "creator-advice tone" (talking about XHS strategy itself) | Wrong audience signal | Operator memo about Amazon work |
| Naming internal tooling | Brand boundary leak | Generic "AI agent" / "AI 帮你..." |

## When the validator and your judgment disagree

The validator is a contract, not a brain. Two cases come up:

### 1. Hard-fail you can't fix without breaking voice

Almost never happens with the defaults. If it does (e.g. you genuinely think
the title shouldn't contain `亚马逊` for one specific post), edit
`config.title_constraints.must_contain` for your account, not just for one
post. Don't bypass the validator.

### 2. Soft-warn that's intentional

Common — for example, an ai-workflow post where card 5's natural framing
doesn't use the seven decision verbs. If you've genuinely thought through
the decision change, write it into `post.json.qa_notes`:

```json
{
  "qa_notes": [
    "card 5 decision-verb soft-warn ignored — the 'change' here is the seller stops paying for noise data; framed as '不再' instead of one of the listed verbs",
    "T2 numeric pattern unsuitable for today's narrative; fell back to T1"
  ]
}
```

These notes are durable: when someone audits the account in 6 months, the
exception trail is right there.

## A diagnostic question (when you're stuck)

> **If a real seller texted me this in a private chat, would they send it
> exactly like this?**

If yes → ship it. If no → rewrite to that bar, then check the validator.
