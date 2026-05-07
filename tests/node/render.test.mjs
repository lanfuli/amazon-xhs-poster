/**
 * Tests for scripts/render.mjs.
 *
 * Strategy: render.mjs is an executable that spawns `npx playwright`. Real
 * rendering needs Chromium, which is too heavy for CI. We test:
 *
 * 1. EMPTY-CARDS path (text-only platforms LinkedIn / X) — fully covered
 *    without playwright. Manifest written, status updated, exit 0.
 * 2. Validation gate — render.mjs runs validate.py first; we feed an
 *    invalid post and expect non-zero exit.
 * 3. CARD-COUNT cap — render.mjs caps at 10. Beyond that → exit 1 fast,
 *    no playwright spawned.
 *
 * Real rendering (with PNG comparison) is left for manual smoke testing.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(__dirname, '..', '..');
const RENDER = path.join(SKILL_ROOT, 'scripts', 'render.mjs');

function tmpdir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'render-test-'));
}

function writeConfig(dir, overrides = {}) {
  const cfg = {
    output_language: 'en',
    platform: 'linkedin',
    persona: {
      brand_cn: 'Test Brand',
      identity: 't', voice: 'v', signature: 'Test Brand',
      location: 'L', years_experience: 1,
    },
    title_constraints: { max_chars: null, must_contain: null },
    cta_tokens: null,
    decision_verbs: null,
    forbidden_brands_in_copy: [],
    forbidden_source_tokens: [],
    angle_quotas: {
      'amazon-news': { floor: 2, ceiling: 5, color: 'amber' },
      'white-hat-tactic': { floor: 2, ceiling: 5, color: 'green' },
      'risk-warning': { floor: 2, ceiling: 5, color: 'red' },
      'ai-workflow': { floor: 2, ceiling: 4, color: 'blue' },
      'walmart-multi-channel': { floor: 1, ceiling: 3, color: 'slate' },
      'creator-signal': { floor: 0, ceiling: 2, color: 'violet' },
    },
    paths: {
      drafts_root: path.join(dir, 'drafts'),
      desktop_root: '',
      history_lookback_days: 30,
    },
    publish_adapter: { enabled: false, module_path: null },
    ...overrides,
  };
  const p = path.join(dir, 'config.json');
  fs.writeFileSync(p, JSON.stringify(cfg, null, 2));
  return p;
}

function writePost(dir, post) {
  const jobDir = path.join(dir, 'drafts', '2026-05-07');
  const cardsDir = path.join(jobDir, 'cards');
  fs.mkdirSync(cardsDir, { recursive: true });
  fs.mkdirSync(path.join(jobDir, 'research'), { recursive: true });
  post.paths = {
    job_dir: jobDir,
    desktop_root: '',
    research_note: path.join(jobDir, 'research/topic.md'),
    post_json: path.join(jobDir, 'post.json'),
    render_manifest: path.join(cardsDir, 'render_manifest.json'),
    cards_dir: cardsDir,
  };
  const postPath = path.join(jobDir, 'post.json');
  fs.writeFileSync(postPath, JSON.stringify(post, null, 2));
  return { postPath, jobDir, cardsDir };
}

const TEXT_ONLY_BASE = {
  version: '1.1',
  job_date: '2026-05-07',
  language: 'en',
  platform: 'linkedin',
  persona: { brand_cn: 'Test Brand', identity: 't', voice: 'v', signature: 'Test Brand' },
  topic: {
    category: 'risk-warning',
    angle: 'Amazon FBA risk content for testing',
    why_now: 'now',
    selection_reason: 'test',
    sources: ['https://example.com/article'],
  },
  seo: { hashtags: [] },
  strategy: { attention_goal: 'x', psychology_hooks: [], ai_positioning: '', dedupe_window_days: 30 },
  design: { cards: 0, cards_min: 0, cards_max: 0, renders_cards: false },
  xhs: {
    title: '',
    opening_hook: 'Amazon hook',
    content: 'Amazon body relevant enough. FBA returns PrimeDay seller. Follow.',
    cta: 'follow',
    tags: ['Amazon', 'FBA', 'PrimeDay', 'Seller'],
    thread: [],
    append_hashtags_to_content: true,
    delivery_mode: 'manual',
  },
  cards: [],
  status: { research: 'complete', editorial: 'complete', render: 'skipped-no-cards', qa: 'complete', publish: 'manual' },
  qa_notes: [],
};

describe('render.mjs: empty-cards path (text-only platforms)', () => {
  let dir;
  beforeEach(() => {
    dir = tmpdir();
  });

  it('writes empty manifest with platform field set', () => {
    const cfg = writeConfig(dir);
    const { postPath, cardsDir } = writePost(dir, structuredClone(TEXT_ONLY_BASE));
    const result = spawnSync('node', [RENDER, postPath, '--config', cfg], { encoding: 'utf8' });
    expect(result.status).toBe(0);
    const manifestPath = path.join(cardsDir, 'render_manifest.json');
    expect(fs.existsSync(manifestPath)).toBe(true);
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    expect(manifest.platform).toBe('linkedin');
    expect(manifest.cards).toEqual([]);
    expect(manifest.note).toMatch(/no cards to render/i);
  });

  it('updates status.render to skipped-no-cards', () => {
    const cfg = writeConfig(dir);
    const { postPath } = writePost(dir, structuredClone(TEXT_ONLY_BASE));
    spawnSync('node', [RENDER, postPath, '--config', cfg], { encoding: 'utf8' });
    const post = JSON.parse(fs.readFileSync(postPath, 'utf8'));
    expect(post.status.render).toBe('skipped-no-cards');
  });

  it('manifest platform reflects post.platform=x', () => {
    const cfg = writeConfig(dir, { platform: 'x' });
    const post = structuredClone(TEXT_ONLY_BASE);
    post.platform = 'x';
    post.xhs.thread = ['Amazon tweet 1 mentions briefly.', 'Tweet 2.'];
    post.xhs.content = '';
    post.xhs.tags = ['Amazon'];
    post.xhs.append_hashtags_to_content = false;
    const { postPath, cardsDir } = writePost(dir, post);
    spawnSync('node', [RENDER, postPath, '--config', cfg], { encoding: 'utf8' });
    const manifest = JSON.parse(fs.readFileSync(path.join(cardsDir, 'render_manifest.json'), 'utf8'));
    expect(manifest.platform).toBe('x');
  });
});

describe('render.mjs: validation gate', () => {
  let dir;
  beforeEach(() => {
    dir = tmpdir();
  });

  it('exits non-zero when post.json fails validation (e.g. brand_cn mismatch)', () => {
    const cfg = writeConfig(dir);
    const post = structuredClone(TEXT_ONLY_BASE);
    post.persona.brand_cn = 'Different Brand'; // mismatch with config
    const { postPath } = writePost(dir, post);
    const result = spawnSync('node', [RENDER, postPath, '--config', cfg], { encoding: 'utf8' });
    expect(result.status).not.toBe(0);
  });

  it('exits 1 when post.json has no paths.job_dir', () => {
    const cfg = writeConfig(dir);
    const jobDir = path.join(dir, 'drafts', '2026-05-07');
    fs.mkdirSync(jobDir, { recursive: true });
    const postPath = path.join(jobDir, 'post.json');
    const post = structuredClone(TEXT_ONLY_BASE);
    delete post.paths;  // no paths block at all
    fs.writeFileSync(postPath, JSON.stringify(post, null, 2));
    const result = spawnSync('node', [RENDER, postPath, '--config', cfg], { encoding: 'utf8' });
    expect(result.status).not.toBe(0);
  });
});

describe('render.mjs: card count cap', () => {
  let dir;
  beforeEach(() => {
    dir = tmpdir();
  });

  it('refuses to render if cards.length > 10 (renderer hard cap)', () => {
    // Even though validator caps platform-specific, the renderer has its own
    // safety cap at 10 to avoid runaway invocations.
    const cfg = writeConfig(dir, { platform: 'instagram' });
    const post = structuredClone(TEXT_ONLY_BASE);
    post.platform = 'instagram';
    post.design = {
      theme: 'auto', style: 'iphone-notes-editorial-v4',
      cards: 11, cards_min: 1, cards_max: 10, renders_cards: true,
      ratio: '3:4', width: 1080, height: 1440,
      accent_strategy: 'color-psychology',
    };
    post.xhs.title = '';
    post.cards = Array.from({ length: 11 }, (_, i) => ({
      id: `card_${String(i + 1).padStart(2, '0')}`,
      kind: 'hook', eyebrow: 'x', headline: 'Amazon hook',
      body: 'b', bullets: [], footer: 'sig',
    }));
    const { postPath } = writePost(dir, post);
    const result = spawnSync('node', [RENDER, postPath, '--config', cfg], { encoding: 'utf8' });
    // Validator catches >10 first; renderer cap is a backstop.
    expect(result.status).not.toBe(0);
  });
});
