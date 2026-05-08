#!/usr/bin/env node
/*
 * Amazon XHS card renderer — Playwright-driven, theme-tinted, deterministic.
 *
 * Reads post.json, runs sibling validate.py first (hard-fail gate), then
 * generates one HTML + PNG per card under <paths.cards_dir> (default:
 * <job_dir>/cards/). When config.paths.desktop_root is set, mirrors PNGs +
 * manifests + post.json into <desktop_root>/cards/ and <desktop_root>/meta/
 * for easy phone hand-off; if empty/null/false, skips the mirror.
 *
 * Usage:
 *   node render.mjs <post.json> [--config <path>]
 *
 * Config resolution (used for the sibling validate.py only — render itself
 * gets all parameters from post.json):
 *   1. --config <path>
 *   2. XHS_AMAZON_CONFIG env var
 *   3. ~/.config/amazon-xhs-poster/config.json
 */
import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function detectImageKind(buffer) {
  if (buffer.length >= 8 && buffer[0] === 0x89 && buffer[1] === 0x50 && buffer[2] === 0x4E && buffer[3] === 0x47) return 'png';
  if (buffer.length >= 3 && buffer[0] === 0xFF && buffer[1] === 0xD8 && buffer[2] === 0xFF) return 'jpeg';
  return 'unknown';
}

function expandHome(p) {
  if (!p) return p;
  if (p.startsWith('~/')) return path.join(os.homedir(), p.slice(2));
  if (p === '~') return os.homedir();
  return p;
}

const argv = process.argv.slice(2);
let postJsonPath = null;
let configPath = null;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--config' && argv[i + 1]) {
    configPath = argv[++i];
  } else if (a === '-h' || a === '--help') {
    console.log('Usage: node render.mjs <post.json> [--config <path>]');
    process.exit(0);
  } else if (!postJsonPath) {
    postJsonPath = a;
  }
}

if (!postJsonPath) {
  console.error('Usage: node render.mjs <post.json> [--config <path>]');
  process.exit(1);
}

const validatorPath = path.join(__dirname, 'validate.py');
const validatorArgs = [validatorPath, postJsonPath, '--json'];
if (configPath) validatorArgs.push('--config', configPath);
const validator = spawnSync('python3', validatorArgs, { stdio: 'pipe', encoding: 'utf8' });
if (validator.status !== 0) {
  process.stderr.write(validator.stdout || '');
  process.stderr.write(validator.stderr || '');
  console.error('Amazon XHS post validation failed before render');
  process.exit(validator.status || 1);
}

const root = JSON.parse(await fs.readFile(postJsonPath, 'utf8'));
const jobDir = expandHome(root.paths?.job_dir);
const desktopRootRaw = root.paths?.desktop_root;
const desktopRoot = desktopRootRaw ? expandHome(desktopRootRaw) : null;
const cardsDir = expandHome(root.paths?.cards_dir) || path.join(jobDir, 'cards');
const renderManifestPath = expandHome(root.paths?.render_manifest) || path.join(cardsDir, 'render_manifest.json');

if (!jobDir) {
  console.error('post.json is missing paths.job_dir');
  process.exit(1);
}

await fs.mkdir(cardsDir, { recursive: true });
const desktopCardsDir = desktopRoot ? path.join(desktopRoot, 'cards') : null;
const desktopMetaDir = desktopRoot ? path.join(desktopRoot, 'meta') : null;
if (desktopCardsDir) await fs.mkdir(desktopCardsDir, { recursive: true });
if (desktopMetaDir) await fs.mkdir(desktopMetaDir, { recursive: true });

// Theme palette + default chip label per content category.
// `chip` is the small-label string painted on each card by default
// (zh-mode strings shown below: "Global News" / "White-Hat Ops" /
// "Risk Alert" / "AI Productivity" / "Walmart Multi-Channel" /
// "Xiaohongshu Signal" / "Seller Notes").
// For en-mode posts, set `card.eyebrow` explicitly per card to override
// the default — see references/customization.md §3 (Renderer note).
const themes = {
  'amazon-news': {
    accent: '#C96B25', accentSoft: '#F8E7D8', paper: '#FFF9F2', ink: '#261B14', muted: '#7E5E49',
    chip: '全球新闻',
    bgFrom: '#F4EEE4', bgTo: '#EDE4D8', sheetTop: '#FFFDFC', sheetBottom: '#FBF4E9',
    halo: 'rgba(201,107,37,0.18)'
  },
  'white-hat-tactic': {
    accent: '#177E5A', accentSoft: '#E3F3EC', paper: '#FBFDFB', ink: '#17231E', muted: '#517061',
    chip: '白帽运营',
    bgFrom: '#EAF4EE', bgTo: '#DEEDE3', sheetTop: '#FCFFFD', sheetBottom: '#F2F9F4',
    halo: 'rgba(23,126,90,0.16)'
  },
  'risk-warning': {
    accent: '#B64033', accentSoft: '#F8E1DD', paper: '#FFF8F7', ink: '#281817', muted: '#7F5752',
    chip: '风险预警',
    bgFrom: '#F7E9E7', bgTo: '#EFD9D5', sheetTop: '#FFFAF9', sheetBottom: '#FCEDEA',
    halo: 'rgba(182,64,51,0.18)'
  },
  'ai-workflow': {
    accent: '#275FD5', accentSoft: '#E3ECFF', paper: '#F8FAFF', ink: '#162238', muted: '#55657F',
    chip: 'AI 提效',
    bgFrom: '#E8EEFA', bgTo: '#D9E2F3', sheetTop: '#FAFCFF', sheetBottom: '#EEF3FC',
    halo: 'rgba(39,95,213,0.16)'
  },
  'walmart-multi-channel': {
    accent: '#3B6FB6', accentSoft: '#E1ECF7', paper: '#F7FAFD', ink: '#15212F', muted: '#516074',
    chip: 'Walmart 多渠道',
    bgFrom: '#EAF1F8', bgTo: '#DBE6F1', sheetTop: '#F9FBFD', sheetBottom: '#EEF4FA',
    halo: 'rgba(59,111,182,0.16)'
  },
  'creator-signal': {
    accent: '#7E4DC2', accentSoft: '#EFE5FA', paper: '#FBF8FF', ink: '#1F1531', muted: '#6A5882',
    chip: '小红书信号',
    bgFrom: '#EFE8F8', bgTo: '#E2D8F0', sheetTop: '#FBF8FF', sheetBottom: '#F4ECFB',
    halo: 'rgba(126,77,194,0.16)'
  },
  default: {
    accent: '#3B5BDB', accentSoft: '#E7ECFF', paper: '#FFFDF9', ink: '#1E2024', muted: '#697180',
    chip: '卖家笔记',
    bgFrom: '#EDEFF6', bgTo: '#E0E4EE', sheetTop: '#FCFCFE', sheetBottom: '#F3F5FB',
    halo: 'rgba(59,91,219,0.16)'
  }
};

function escapeHtml(value = '') {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function normalizeCard(card, index) {
  return {
    id: card.id || `card_${String(index + 1).padStart(2, '0')}`,
    kind: card.kind || 'note',
    eyebrow: card.eyebrow || '',
    headline: card.headline || root.xhs?.title || '',
    body: card.body || root.xhs?.opening_hook || '',
    bullets: Array.isArray(card.bullets) ? card.bullets.filter(Boolean).slice(0, 5) : [],
    footer: card.footer || root.persona?.signature || ''
  };
}

function personaBrandCn() {
  return root.persona?.brand_cn || '';
}

function renderHtmlV4(card, theme, index, total) {
  const isHero = index === 0;
  const bulletsHtml = card.bullets.length
    ? `<div class="bullet-stack">${card.bullets.map((item, itemIndex) => `<div class="bullet-card"><div class="bullet-kicker">0${itemIndex + 1}</div><div class="bullet-copy">${escapeHtml(item)}</div></div>`).join('')}</div>`
    : '';

  const bodyHtml = card.body
    ? `<p class="body">${escapeHtml(card.body).replaceAll('\n', '<br/>')}</p>`
    : '';

  const eyebrow = escapeHtml(card.eyebrow || theme.chip);
  const headline = escapeHtml(card.headline).replaceAll('\n', '<br/>');
  const footer = escapeHtml(card.footer || '');
  const brandCn = escapeHtml(personaBrandCn());

  const progressSegments = Array.from({ length: total }, (_, i) =>
    `<span class="prog-seg ${i <= index ? 'on' : ''}"></span>`
  ).join('');

  const htmlLang = (root.language || 'zh').toLowerCase() === 'en' ? 'en' : 'zh-CN';
  return `<!doctype html>
<html lang="${htmlLang}">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=1080, initial-scale=1" />
<title>${escapeHtml(card.headline)}</title>
<style>
:root {
  --accent: ${theme.accent};
  --accent-soft: ${theme.accentSoft};
  --halo: ${theme.halo};
  --ink: #101114;
  --muted: #5E6671;
  --line: rgba(16, 17, 20, 0.09);
  --sheet-top: ${theme.sheetTop};
  --sheet-bottom: ${theme.sheetBottom};
  --bg-from: ${theme.bgFrom};
  --bg-to: ${theme.bgTo};
}
* { box-sizing: border-box; }
html, body {
  margin: 0;
  width: 1080px;
  height: 1440px;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'PingFang SC', 'Helvetica Neue', sans-serif;
  background:
    radial-gradient(circle at top left, rgba(255,255,255,0.78), transparent 32%),
    linear-gradient(180deg, var(--bg-from) 0%, var(--bg-to) 100%);
}
body { display: flex; }
.frame {
  width: 100%;
  height: 100%;
  padding: 38px;
  position: relative;
}
.sheet {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: 56px;
  background: linear-gradient(180deg, var(--sheet-top), var(--sheet-bottom));
  border: 1px solid rgba(255,255,255,0.7);
  box-shadow:
    0 40px 120px rgba(53, 39, 24, 0.14),
    0 8px 24px rgba(53, 39, 24, 0.05),
    inset 0 1px 0 rgba(255,255,255,0.95);
}
.sheet::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 6px;
  background: linear-gradient(90deg, var(--accent) 0%, var(--accent) 38%, transparent 95%);
  z-index: 3;
}
${isHero ? `
.sheet::after {
  content: '';
  position: absolute;
  top: -120px;
  left: -180px;
  width: 720px;
  height: 720px;
  background: radial-gradient(circle, var(--halo) 0%, transparent 62%);
  z-index: 1;
  pointer-events: none;
}` : ''}

.topbar {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 36px 56px 0;
}
.brand {
  font-size: 30px;
  font-weight: 870;
  letter-spacing: -0.03em;
  color: var(--ink);
}
.brand::before {
  content: '';
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--accent);
  margin-right: 12px;
  vertical-align: 2px;
}

.progress {
  position: relative;
  z-index: 2;
  display: flex;
  gap: 8px;
  padding: 22px 56px 0;
}
.prog-seg {
  flex: 1;
  height: 4px;
  border-radius: 999px;
  background: rgba(16,17,20,0.08);
}
.prog-seg.on {
  background: var(--accent);
}

.content {
  position: relative;
  z-index: 2;
  padding: 32px 56px 48px;
}
.meta {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 26px;
}
.chip {
  display: inline-flex;
  align-items: center;
  padding: 12px 20px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255,255,255,0.82), rgba(255,255,255,0.56)), var(--accent-soft);
  color: var(--accent);
  font-size: 22px;
  font-weight: 820;
  letter-spacing: -0.01em;
  box-shadow: 0 8px 24px rgba(0,0,0,0.04);
}
.kicker {
  font-size: 19px;
  font-weight: 720;
  color: var(--muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.headline {
  margin: 0 0 24px;
  max-width: 880px;
  font-size: ${isHero ? '94px' : '74px'};
  line-height: 0.96;
  font-weight: 880;
  letter-spacing: -0.055em;
  color: var(--ink);
  text-wrap: balance;
}
.headline .hl {
  box-shadow: inset 0 -0.34em 0 rgba(255, 208, 89, 0.42);
}
.body {
  margin: 0 0 28px;
  max-width: 900px;
  font-size: 34px;
  line-height: 1.48;
  font-weight: 585;
  letter-spacing: -0.018em;
  color: rgba(16,17,20,0.95);
}
.bullet-stack {
  display: grid;
  gap: 16px;
  margin-top: 12px;
}
.bullet-card {
  display: grid;
  grid-template-columns: 78px 1fr;
  gap: 18px;
  align-items: start;
  padding: 20px 22px;
  border-radius: 28px;
  background: rgba(255,255,255,0.62);
  border: 1px solid rgba(16,17,20,0.05);
  box-shadow: 0 12px 32px rgba(28, 22, 15, 0.04);
}
.bullet-kicker {
  width: 58px;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 18px;
  background: linear-gradient(180deg, var(--accent), color-mix(in srgb, var(--accent) 82%, #111 18%));
  color: #fff;
  font-size: 22px;
  font-weight: 860;
  letter-spacing: -0.02em;
}
.bullet-copy {
  font-size: 29px;
  line-height: 1.40;
  font-weight: 610;
  letter-spacing: -0.014em;
  color: rgba(16,17,20,0.96);
}

.footer {
  position: absolute;
  left: 56px;
  right: 56px;
  bottom: 42px;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 24px;
}
.footer-copy {
  max-width: 760px;
  font-size: 22px;
  line-height: 1.42;
  font-weight: 650;
  color: var(--muted);
}
.footer-page {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 18px;
  font-weight: 720;
  color: var(--muted);
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.footer-page strong {
  color: var(--accent);
  font-weight: 860;
}
</style>
</head>
<body>
  <div class="frame">
    <div class="sheet">
      <div class="topbar">
        <div class="brand">${brandCn}</div>
      </div>
      <div class="progress">${progressSegments}</div>
      <div class="content">
        <div class="meta">
          <div class="chip">${eyebrow}</div>
          ${isHero ? '<div class="kicker">SELLER MEMO</div>' : ''}
        </div>
        <h1 class="headline"><span class="hl">${headline}</span></h1>
        ${bodyHtml}
        ${bulletsHtml}
      </div>
      <div class="footer">
        <div class="footer-copy">${footer}</div>
        <div class="footer-page"><strong>${String(index + 1).padStart(2, '0')}</strong> / ${String(total).padStart(2, '0')}</div>
      </div>
    </div>
  </div>
</body>
</html>`;
}

const themeKey = root.design?.theme && root.design.theme !== 'auto'
  ? root.design.theme
  : root.topic?.category;
const theme = themes[themeKey] || themes.default;
const cards = (root.cards || []).map(normalizeCard);

// Text-only platforms (LinkedIn, X, Threads) ship with cards = []. Validator
// has already accepted that configuration; here we just write an empty
// manifest and exit cleanly so downstream make-post-md.py can run.
if (cards.length === 0) {
  const emptyManifest = {
    platform: root.platform || 'xiaohongshu',
    theme: themeKey || 'default',
    renderedAt: new Date().toISOString(),
    cards: [],
    note: 'no cards to render (text-only platform)'
  };
  await fs.writeFile(renderManifestPath, JSON.stringify(emptyManifest, null, 2));
  if (desktopMetaDir) {
    await fs.copyFile(renderManifestPath, path.join(desktopMetaDir, 'render_manifest.json'));
  }
  root.status = root.status || {};
  root.status.render = 'skipped-no-cards';
  await fs.writeFile(postJsonPath, JSON.stringify(root, null, 2) + '\n');
  console.log(JSON.stringify(emptyManifest, null, 2));
  process.exit(0);
}

// Render any non-empty card array. Platform-specific bounds (e.g. IG 1-10,
// XHS 6-9, Lemon8 6-10) are enforced by validate.py before this point.
if (cards.length > 10) {
  console.error(`Card count ${cards.length} exceeds the renderer's hard cap of 10. Trim post.json.cards.`);
  process.exit(1);
}

const outputs = [];
for (const [index, card] of cards.entries()) {
  const html = renderHtmlV4(card, theme, index, cards.length);
  const htmlPath = path.join(cardsDir, `${card.id}.html`);
  const pngPath = path.join(cardsDir, `${card.id}.png`);
  await fs.writeFile(htmlPath, html, 'utf8');
  const result = spawnSync(
    'npx',
    [
      'playwright',
      'screenshot',
      '--browser', 'chromium',
      '--viewport-size', '1080,1440',
      '--wait-for-timeout', '350',
      pathToFileURL(htmlPath).href,
      pngPath
    ],
    { stdio: 'pipe', encoding: 'utf8' }
  );

  if (result.status !== 0) {
    process.stderr.write(result.stdout || '');
    process.stderr.write(result.stderr || '');
    console.error(`Failed to render ${card.id}`);
    process.exit(result.status || 1);
  }

  const renderedBytes = await fs.readFile(pngPath);
  const renderedKind = detectImageKind(renderedBytes);
  let finalImagePath = pngPath;
  if (renderedKind === 'jpeg') {
    finalImagePath = path.join(cardsDir, `${card.id}.jpg`);
    await fs.rename(pngPath, finalImagePath);
  } else if (renderedKind !== 'png') {
    console.error(`Rendered ${card.id} has unexpected image signature: ${renderedKind}`);
    process.exit(1);
  }

  if (desktopCardsDir) {
    await fs.copyFile(finalImagePath, path.join(desktopCardsDir, path.basename(finalImagePath)));
  }
  outputs.push({ id: card.id, html: htmlPath, png: finalImagePath });
}

const renderManifest = {
  platform: root.platform || 'xiaohongshu',
  theme: themeKey || 'default',
  renderedAt: new Date().toISOString(),
  cards: outputs
};
await fs.writeFile(renderManifestPath, JSON.stringify(renderManifest, null, 2));
if (desktopMetaDir) {
  await fs.copyFile(renderManifestPath, path.join(desktopMetaDir, 'render_manifest.json'));
}

root.status = root.status || {};
root.status.render = 'done';
await fs.writeFile(postJsonPath, JSON.stringify(root, null, 2) + '\n');
if (desktopMetaDir) {
  await fs.copyFile(postJsonPath, path.join(desktopMetaDir, 'post.json'));
}

console.log(JSON.stringify(renderManifest, null, 2));
