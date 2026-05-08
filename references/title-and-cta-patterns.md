# Title / CTA / Bullet / Hashtag Patterns

> Companion to [`editorial-sop.md`](editorial-sop.md) Stage 2. The point is
> conscious variation across 14 days so readers don't pattern-match the
> account into "always the same hook."
>
> **Voice supremacy still rules.** When any pattern below would force a
> sentence the persona wouldn't say, drop the pattern and document why in
> `post.json.qa_notes`.
>
> Two language tracks are provided: **ZH** (default, optimized for
> Xiaohongshu native audience) and **EN** (for Lemon8 / LinkedIn / X /
> Instagram). Pick one via `config.output_language` and align
> `config.title_constraints.must_contain` accordingly.

---

## 1. Title patterns (T1–T8)

### ZH

| ID  | Pattern                              | Example                       | Suits |
|-----|--------------------------------------|-------------------------------|-------|
| T1  | `亚马逊 + verb + object`             | 亚马逊在拆你的变体            | any (default) |
| T2  | `[N]类/件/步 + 亚马逊 + noun`        | 3类亚马逊隐性扣分             | white-hat / risk |
| T3  | `如果你是亚马逊 + state`             | 如果你是亚马逊新卖家          | white-hat / ai |
| T4  | `time-anchor + 亚马逊 + event`       | Prime Day前5周亚马逊政策大改  | news / walmart |
| T5  | `亚马逊 + vs / 对比 + object`        | 亚马逊vs沃尔玛广告ROI         | walmart / news |
| T6  | `别再…亚马逊…` (counter-consensus)   | 别再死磕亚马逊关键词          | ai / white-hat |
| T7  | `[N]个亚马逊… / [N]天亚马逊…`        | 3个亚马逊操盘动作             | white-hat / ai |
| T8  | `亚马逊 + metaphor`                  | 亚马逊在悄悄换牌              | risk / news |

### EN

| ID  | Pattern                                  | Example                            | Suits |
|-----|------------------------------------------|------------------------------------|-------|
| T1  | `Amazon + verb + object`                 | Amazon is killing your variations  | any (default) |
| T2  | `[N] hidden / quiet + Amazon + noun`     | 3 hidden Amazon penalties          | white-hat / risk |
| T3  | `If you sell on Amazon and you...`       | If you sell on Amazon, stop here   | white-hat / ai |
| T4  | `[time-anchor] before [event]: Amazon X` | 5 weeks before Prime Day: Amazon shifts policy | news / walmart |
| T5  | `Amazon vs / compared to + object`       | Amazon vs Walmart ad ROI in 2026   | walmart / news |
| T6  | `Stop... on Amazon` (counter-consensus)  | Stop optimizing keywords on Amazon | ai / white-hat |
| T7  | `[N] Amazon... that...`                  | 3 Amazon moves before Prime Day    | white-hat / ai |
| T8  | `Amazon is + metaphor`                   | Amazon is quietly changing the rules | risk / news |

### Selection rule

- **Same ID can't repeat within 7 days.** Pick the ID first, then write the
  title.
- Length ≤ 20 characters (validator hard rule; configurable via
  `config.title_constraints.max_chars`).
- Title must contain at least one keyword from
  `config.title_constraints.must_contain` (default: `["亚马逊"]`).
- Optional: log the chosen ID in `post.json.xhs.title_pattern_id` for
  future audits.

### Anti-pattern (don't do this)

- ❌ T1 three days in a row ("亚马逊在 X" / "亚马逊正在 X" / "亚马逊会 X")
- ❌ Same verb-object pair two days running ("杀转化", "打标签")

---

## 2. CTA patterns (CTA1–CTA6)

Used on card 6 (the last card).

### ZH

| ID    | Type                | Example |
|-------|---------------------|---------|
| CTA1  | Follow              | 点左上角+关注，<persona>，每天给你筛掉90%的亚马逊噪音 |
| CTA2  | Save-reminder       | 收藏这张图，Prime Day前一周翻出来对照 |
| CTA3  | Comment-prompt      | 评论区告诉我你卡在哪一步，挑3个问题明天回 |
| CTA4  | Time-commitment     | 这周内做完这3步，下周来看后台数据变化 |
| CTA5  | Share-trigger       | 分享给你的运营/选品同事，少踩一个坑就值了 |
| CTA6  | Reverse question    | 你今年敢动这一步吗？踩雷过的留言告诉我 |

### EN

| ID    | Type                | Example |
|-------|---------------------|---------|
| CTA1  | Follow              | Follow <persona> for the 10% of Amazon news that actually moves PnL |
| CTA2  | Save-reminder       | Save this — pull it back up the week before Prime Day |
| CTA3  | Comment-prompt      | Drop your stuck step in comments. I'll pick 3 to answer tomorrow |
| CTA4  | Time-commitment     | Do these 3 steps this week, check your dashboard next Monday |
| CTA5  | Share-trigger       | Share with your ops or sourcing teammate — saves them one landmine |
| CTA6  | Reverse question    | Would you actually pull this lever this year? Comment if you've been burned |

### Selection rule

- **CTA ID can't repeat within 3 days** on card 6.
- The last sentence MUST contain at least one CTA token from the
  configured set. Defaults are language-aware: ZH = `点赞 / 收藏 / 关注 /
  评论 / 不迷路`. EN = `like / save / follow / comment / share / subscribe`.
  Override via `config.cta_tokens` if you have a different vocabulary.
- Don't stack 5 CTAs on one card — pick 1 primary + 1 secondary at most.
- Validator additionally hard-fails if card 6's full text is ≥ 70% Levenshtein
  similar to any of the previous 3 days' card 6 text.

### Anti-pattern

- ❌ "点左上角 + 关注" used as the only CTA for 14 days straight
- ❌ Filler like "学会了点赞" with no reason to act

---

## 3. Bullet vs Matrix decision

```
Items in a card?
│
├─ Are they sequential (step 1 → 2 → 3, time-ordered)?
│   └── YES → use bullets. zh: "第N步" (Step N) / "先 X 再 Y" (do X first, then Y);
│            en: "Step N" / "First X, then Y"
│
└─ Are they parallel categories (types, reasons, time windows)?
    └── YES → matrix card (kind: "matrix")
        e.g. 3 keyword types × (cause / action) → 3 rows × 2 cols
```

### Trigger phrases for matrix

- Bullets prefixed with (zh) `第N种 / 类型N / 第N类 / 第N个原因 / 风险N`
  ("Type N / Type N / Category N / Reason N / Risk N") or (en)
  `Type N / Reason N / Risk N`
- Each bullet is `X：Y` (label + explanation)
- Content naturally maps to a 2D table

### Matrix card schema (proposed; not yet rendered)

```json
{
  "id": "card_03",
  "kind": "matrix",
  "eyebrow": "三类关键词",
  "headline": "你 listing 里 80% 的词只占 20% 流量",
  "columns": [
    { "header": "词类",   "items": ["...", "...", "..."] },
    { "header": "成因",   "items": ["...", "...", "..."] },
    { "header": "行动",   "items": ["...", "...", "..."] }
  ],
  "footer": "..."
}
```

**Current status**: the renderer doesn't paint matrix cards yet. Workaround:
write `kind: "bullets"` with a `qa_notes` entry like
`"待 matrix 渲染支持后回填"` (zh: "backfill once matrix renderer ships";
en equivalent: `"backfill once matrix renderer ships"`). Validator will
soft-warn when bullets look parallel-dimensional but `kind != "matrix"`.

---

## 4. Hashtag tiering

Total hashtags 5–10 (validator hard rule). Three-tier structure:

**ZH track** examples:

| Tier            | Count | Content                              | Examples |
|-----------------|-------|--------------------------------------|----------|
| Brand / persona | 1–2   | Persistent account anchor            | `#亚马逊` `#<persona>` `#亚马逊卖家` |
| Topic-specific  | 3–5   | **Must share token** with today's headline / `topic.angle` | FBA returns post → `#FBA退货` `#退货标签` `#转化率` |
| Broad-SEO      | 2–3   | Cross-border SEO catch              | `#跨境电商` `#出海` `#美国电商` |

**EN track** examples:

| Tier            | Count | Content                              | Examples |
|-----------------|-------|--------------------------------------|----------|
| Brand / persona | 1–2   | Persistent account anchor            | `#Amazon` `#<persona>` `#AmazonSeller` |
| Topic-specific  | 3–5   | **Must share token** with headline / `topic.angle` | FBA returns post → `#FBAReturns` `#ReturnRate` `#Conversion` |
| Broad-SEO      | 2–3   | Cross-border SEO catch              | `#Ecommerce` `#DTC` `#USMarketplace` |

### Rules

- Topic-specific tier must share at least one token with `topic.angle` /
  `topic.category` / `xhs.title` / first 3 card headlines (validator hard-fails
  below 60% relevance ratio).
- Each hashtag ≤ 12 chars (validator hard rule).
- At least one hashtag must contain a keyword from
  `config.title_constraints.must_contain` (validator hard rule). Default
  is language-aware: ZH = `["亚马逊"]`, EN = `["Amazon"]`.
- Don't borrow Broad-SEO terms as topic tags (e.g. don't use `#PrimeDay备战`
  on an unrelated FBA returns post).

### Anti-pattern

- ❌ 5 of 6 returns-related posts each carrying `#PrimeDay备战` (irrelevant)
- ❌ 9 hashtags where 7 are Broad-SEO — no topic sharpness
- ❌ Using `#转化率优化` as a generic catch-all on every post

---

## 5. AI-workflow decision-switch test

Only for `topic.category = ai-workflow`. Card 5 (AI / tool / workflow
leverage) MUST answer:

> **"Because AI is running, what decision does the seller change?"**

Card 5 body must contain at least one decision verb. Defaults are
language-aware:

- **ZH**: `决定 / 判断 / 换 / 停 / 加预算 / 下架 / 挑选 / 暂停 / 转移 / 重组 / 砍 / 上架 / 留`
- **EN**: `decide / switch / pause / stop / increase budget / remove / select / transfer / rebuild / cut / promote / keep / kill`

Override via `config.decision_verbs` if your domain uses a different
vocabulary.

### Counter-example vs. example (ZH)

❌ "AI agent 自动每天抓退货数据" — describes automation, no decision change
✅ "AI 帮你每天扫退货榜，前 3 ASIN 立刻**暂停**广告投放，等下一轮 listing 改完再开" — concrete decision switch (pause ads / fix listing / re-enable)

### Counter-example vs. example (EN)

❌ "An AI agent pulls returns data every day" — describes automation, no decision change
✅ "AI scans the returns rank daily; the top 3 ASINs **pause** their ads immediately and resume only after the next listing fix" — concrete decision switch (pause ads / fix listing / re-enable)

### Validation

- Validator soft-warns when card 5 body lacks all decision verbs.
- Editorial QA hard-checks: write card 5, then ask yourself "what different
  decision will the reader make?" Can't answer → rewrite.

---

## Maintenance

- Audit your last 14 days roughly monthly. New anti-patterns → add to the
  "Anti-pattern" sections above.
- New title or CTA shapes that work → propose a T9 or CTA7 with examples.
- If a pattern starts feeling stale (saves drop), consider rotating it
  out of the active library.
