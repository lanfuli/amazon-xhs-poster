#!/usr/bin/env node
/*
 * fetch-gated.mjs — fetch login-protected content (X, LinkedIn, wearesellers)
 * using a persistent Playwright profile.
 *
 * USAGE
 *   First run, interactively log in to all 3 services:
 *     node scripts/fetch-gated.mjs --setup [--config <path>]
 *
 *   Daily fetch (uses saved cookies):
 *     node scripts/fetch-gated.mjs --date 2026-05-08 [--config <path>]
 *
 *   The output is written to <drafts_root>/<DATE>/research/gated-signal.md.
 *   It's input material for the editorial stage; not the final post.
 *
 * ⚠️  RISK NOTICE
 *   Automating logged-in access to X, LinkedIn, and similar services may
 *   violate their Terms of Service and could risk account suspension. This
 *   script is for personal research only — not commercial scraping. It runs
 *   with a separate browser profile from your daily browser, uses your own
 *   cookies (never shares them), runs at modest pace with delays, and never
 *   posts / DMs / interacts (read-only). USE AT YOUR OWN RISK.
 */
import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ----- CLI args -----
const args = process.argv.slice(2);
const flag = (name) => args.includes(name);
const opt = (name) => {
  const i = args.indexOf(name);
  return i >= 0 && i + 1 < args.length ? args[i + 1] : null;
};

const SETUP_MODE = flag('--setup');
const HEADED_MODE = flag('--headed') || SETUP_MODE;
const DATE_OVERRIDE = opt('--date');
const CONFIG_PATH_OVERRIDE = opt('--config');
const DRY_RUN = flag('--dry-run');

if (flag('-h') || flag('--help')) {
  console.log(`fetch-gated.mjs — fetch X / LinkedIn / wearesellers content
  --setup            First run: open headed browser, you log in, profile saves
  --date YYYY-MM-DD  Job date (default: today PT)
  --config <path>    Override config.json path
  --headed           Run with browser visible (debugging)
  --dry-run          Print what would be fetched, don't actually fetch`);
  process.exit(0);
}

// ----- config loading -----
function expandHome(p) {
  if (!p) return p;
  if (p.startsWith('~/')) return path.join(os.homedir(), p.slice(2));
  if (p === '~') return os.homedir();
  return p;
}

function resolveConfigPath() {
  if (CONFIG_PATH_OVERRIDE) return path.resolve(expandHome(CONFIG_PATH_OVERRIDE));
  if (process.env.XHS_AMAZON_CONFIG) return path.resolve(expandHome(process.env.XHS_AMAZON_CONFIG));
  const def = expandHome('~/.config/amazon-xhs-poster/config.json');
  if (fsSync.existsSync(def)) return def;
  return null;
}

const cfgPath = resolveConfigPath();
if (!cfgPath || !fsSync.existsSync(cfgPath)) {
  const defaultLocation = expandHome('~/.config/amazon-xhs-poster/config.json');
  console.error('config.json not found.');
  console.error('');
  console.error('First-time setup (run from skill root):');
  console.error('  mkdir -p ~/.config/amazon-xhs-poster');
  console.error('  cp config.example.json ~/.config/amazon-xhs-poster/config.json');
  console.error('  $EDITOR ~/.config/amazon-xhs-poster/config.json   # fill in persona, paths, set gated_sources.enabled=true');
  console.error('');
  console.error(`Default config path: ${defaultLocation}`);
  console.error('Override via --config <path> or XHS_AMAZON_CONFIG env var.');
  process.exit(1);
}
const config = JSON.parse(fsSync.readFileSync(cfgPath, 'utf8'));
const gatedCfg = config.gated_sources || {};

if (!gatedCfg.enabled && !SETUP_MODE) {
  console.error('config.gated_sources.enabled is false. Set it to true to use this script.');
  console.error('See references/gated-sources.md for setup.');
  process.exit(1);
}

const profileDir = path.resolve(expandHome(
  gatedCfg.browser_profile_dir || '~/.config/amazon-xhs-poster/browser-profile'
));
const draftsRoot = path.resolve(expandHome(
  (config.paths && config.paths.drafts_root) || '~/xhs-amazon-drafts'
));
const lookbackHours = gatedCfg.lookback_hours || 24;
const fetchDelay = gatedCfg.fetch_delay_seconds || [3, 8];

// ----- date / paths -----
const today = (() => {
  const fmt = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Los_Angeles',
    year: 'numeric', month: '2-digit', day: '2-digit'
  });
  return fmt.format(new Date());
})();
const date = DATE_OVERRIDE || today;
const jobDir = path.join(draftsRoot, date);
const researchDir = path.join(jobDir, 'research');
const outputPath = path.join(researchDir, 'gated-signal.md');

await fs.mkdir(researchDir, { recursive: true });
await fs.mkdir(profileDir, { recursive: true });

console.log(`config:    ${cfgPath}`);
console.log(`profile:   ${profileDir}`);
console.log(`output:    ${outputPath}`);
console.log(`date:      ${date}`);
console.log(`mode:      ${SETUP_MODE ? 'SETUP' : (DRY_RUN ? 'DRY-RUN' : 'FETCH')}`);
console.log('');

// ----- import playwright (lazy, lets the rest of CLI work without it) -----
let chromium;
try {
  ({ chromium } = await import('playwright'));
} catch (e) {
  console.error('playwright not installed. Run from the skill root:');
  console.error('  cd ~/.claude/skills/amazon-xhs-poster');
  console.error('  npm install');
  console.error('  npx playwright install chromium');
  console.error('');
  console.error('(render.mjs uses `npx playwright` per-invocation — fetch-gated.mjs');
  console.error('needs the full playwright npm package. The skill\'s package.json');
  console.error('declares it as a dependency.)');
  process.exit(1);
}

// ----- helpers -----
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function randomDelay() {
  const [min, max] = fetchDelay;
  return Math.floor(Math.random() * (max - min) * 1000) + min * 1000;
}

function within24h(timestampStr) {
  const t = new Date(timestampStr).getTime();
  if (isNaN(t)) return true; // be permissive
  const ageHours = (Date.now() - t) / (1000 * 60 * 60);
  return ageHours <= lookbackHours;
}

// ----- launch browser -----
async function launchBrowser() {
  return await chromium.launchPersistentContext(profileDir, {
    headless: !HEADED_MODE,
    viewport: { width: 1280, height: 900 },
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  });
}

// ----- SETUP mode: just open browser, let user log in, exit on Ctrl+C -----
if (SETUP_MODE) {
  console.log('⚠️  SETUP MODE');
  console.log('This will open a Chrome window with a fresh profile.');
  console.log('Log in to whichever services you want fetched:');
  console.log('  • https://x.com/login');
  console.log('  • https://www.linkedin.com/login');
  console.log('  • https://www.wearesellers.com/account/login/');
  console.log('');
  console.log('When done, close the window OR press Ctrl+C here.');
  console.log('Cookies are saved to:', profileDir);
  console.log('');

  const ctx = await launchBrowser();
  const page = ctx.pages()[0] || await ctx.newPage();
  await page.goto('https://x.com/login');

  // Wait for browser close or signal
  await new Promise((resolve) => {
    process.on('SIGINT', () => { console.log('\nClosing...'); resolve(); });
    ctx.on('close', resolve);
  });
  await ctx.close();
  console.log('✓ Profile saved to', profileDir);
  console.log('Run fetch-gated.mjs without --setup next time.');
  process.exit(0);
}

// ----- FETCH mode -----
const ctx = await launchBrowser();
const sections = []; // collected output blocks

// ===== X (Twitter) =====
async function fetchX() {
  const xCfg = gatedCfg.x || {};
  if (!xCfg.enabled || !xCfg.handles?.length) {
    return { name: 'X / Twitter', skipped: true, reason: 'disabled or no handles configured' };
  }

  const lines = [`## X / Twitter — last ${lookbackHours}h`, ''];
  const page = await ctx.newPage();

  for (const item of xCfg.handles) {
    const handle = typeof item === 'string' ? item : item.handle;
    const tier = typeof item === 'object' ? (item.tier || 'general') : 'general';
    if (!handle) continue;

    const url = `https://x.com/${handle}`;
    if (DRY_RUN) {
      lines.push(`### @${handle} (${tier}) — DRY RUN, would fetch ${url}`);
      lines.push('');
      continue;
    }

    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      // Wait for tweets; X is JS-heavy
      await page.waitForSelector('article[data-testid="tweet"]', { timeout: 15000 }).catch(() => null);
      // Scroll to load more
      await page.evaluate(() => window.scrollBy(0, 800));
      await sleep(2000);

      const tweets = await page.$$eval('article[data-testid="tweet"]', (nodes) => {
        return nodes.slice(0, 8).map((node) => {
          const tEl = node.querySelector('time');
          const linkEl = tEl?.closest('a');
          const text = node.querySelector('[data-testid="tweetText"]')?.innerText?.trim() || '';
          return {
            ts: tEl?.getAttribute('datetime') || '',
            url: linkEl?.href || '',
            text: text.slice(0, 600),
          };
        });
      });

      const recent = tweets.filter(t => t.text && (!t.ts || (Date.now() - new Date(t.ts).getTime()) / 36e5 <= 24));
      lines.push(`### @${handle} (${tier})`);
      if (!recent.length) {
        lines.push(`_(no tweets in last ${lookbackHours}h)_`);
        lines.push('');
      } else {
        for (const t of recent) {
          const tsHuman = t.ts ? new Date(t.ts).toISOString().slice(0, 16).replace('T', ' ') : '?';
          lines.push(`- **${tsHuman}** — ${t.text.split('\n').slice(0, 4).join(' / ')}`);
          if (t.url) lines.push(`  ${t.url}`);
        }
        lines.push('');
      }
    } catch (err) {
      lines.push(`### @${handle} (${tier})`);
      lines.push(`_⚠ fetch failed: ${err.message?.slice(0, 200)}_`);
      lines.push('');
    }

    await sleep(randomDelay());
  }

  await page.close();
  return { name: 'X / Twitter', body: lines.join('\n') };
}

// ===== LinkedIn =====
async function fetchLinkedIn() {
  const liCfg = gatedCfg.linkedin || {};
  if (!liCfg.enabled || !liCfg.profiles?.length) {
    return { name: 'LinkedIn', skipped: true, reason: 'disabled or no profiles configured' };
  }

  const lines = [`## LinkedIn — last ${lookbackHours}h`, ''];
  const page = await ctx.newPage();

  for (const item of liCfg.profiles) {
    const slug = typeof item === 'string' ? item : (item.slug || item.url);
    const name = typeof item === 'object' ? item.name : slug;
    if (!slug) continue;

    const url = slug.startsWith('http')
      ? slug.replace(/\/$/, '') + '/recent-activity/all/'
      : `https://www.linkedin.com/in/${slug}/recent-activity/all/`;
    if (DRY_RUN) {
      lines.push(`### ${name} — DRY RUN, would fetch ${url}`);
      lines.push('');
      continue;
    }

    try {
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await sleep(3000); // LinkedIn is heavy

      const posts = await page.$$eval('div.feed-shared-update-v2, [data-urn^="urn:li:activity:"]', (nodes) => {
        return nodes.slice(0, 5).map((node) => {
          const text = node.innerText?.trim() || '';
          const link = node.querySelector('a[href*="/posts/"], a[href*="/pulse/"]')?.href || '';
          return { text: text.slice(0, 500), url: link };
        });
      });

      lines.push(`### ${name}`);
      if (!posts.length) {
        lines.push(`_(no posts visible — may be rate-limited or no recent activity)_`);
        lines.push('');
      } else {
        for (const p of posts) {
          const snippet = p.text.split('\n').filter(l => l.trim()).slice(0, 3).join(' / ');
          lines.push(`- ${snippet}`);
          if (p.url) lines.push(`  ${p.url}`);
        }
        lines.push('');
      }
    } catch (err) {
      lines.push(`### ${name}`);
      lines.push(`_⚠ fetch failed: ${err.message?.slice(0, 200)}_`);
      lines.push('');
    }

    await sleep(randomDelay());
  }

  await page.close();
  return { name: 'LinkedIn', body: lines.join('\n') };
}

// ===== wearesellers =====
async function fetchWearesellers() {
  const wsCfg = gatedCfg.wearesellers || {};
  if (!wsCfg.enabled) {
    return { name: 'wearesellers.com', skipped: true, reason: 'disabled' };
  }

  const topN = wsCfg.top_n || 5;
  const lines = [`## wearesellers.com — top ${topN} hot posts`, ''];

  if (DRY_RUN) {
    lines.push('_(DRY RUN: would fetch homepage and click into top posts)_');
    return { name: 'wearesellers.com', body: lines.join('\n') };
  }

  const page = await ctx.newPage();
  try {
    await page.goto('https://www.wearesellers.com/', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await sleep(2000);

    const links = await page.$$eval('a[href*="/p/"], a[href*="/q/"], a[href*="/article/"]', (nodes) => {
      return nodes.slice(0, 30).map((n) => ({
        href: n.href,
        text: n.innerText?.trim().slice(0, 160) || '',
      })).filter(x => x.text && x.href.includes('wearesellers.com'));
    });

    const seen = new Set();
    const unique = links.filter(l => {
      if (seen.has(l.href)) return false;
      seen.add(l.href);
      return l.text.length >= 8;
    }).slice(0, topN);

    if (!unique.length) {
      lines.push('_(no posts found on homepage — check login state)_');
    } else {
      for (const link of unique) {
        try {
          await page.goto(link.href, { waitUntil: 'domcontentloaded', timeout: 20000 });
          await sleep(1500);
          const body = await page.$eval('article, .post-content, .article-content, main', el => el.innerText?.trim().slice(0, 800)).catch(() => '');
          lines.push(`- **${link.text}**`);
          lines.push(`  ${link.href}`);
          if (body) lines.push(`  ${body.split('\n').slice(0, 6).join(' / ')}`);
          lines.push('');
        } catch (err) {
          lines.push(`- **${link.text}** — _⚠ ${err.message?.slice(0, 100)}_`);
          lines.push('');
        }
        await sleep(randomDelay());
      }
    }
  } catch (err) {
    lines.push(`_⚠ fetch failed: ${err.message?.slice(0, 200)}_`);
  } finally {
    await page.close();
  }

  return { name: 'wearesellers.com', body: lines.join('\n') };
}

// ----- run all -----
const results = [];
for (const fn of [fetchX, fetchLinkedIn, fetchWearesellers]) {
  try {
    const r = await fn();
    results.push(r);
    if (r.skipped) {
      console.log(`✗ ${r.name}: skipped (${r.reason})`);
    } else {
      console.log(`✓ ${r.name}: fetched`);
    }
  } catch (err) {
    console.error(`✗ ${fn.name}: ${err.message}`);
    results.push({ name: fn.name, body: `## ${fn.name}\n\n_fetch crashed: ${err.message}_\n` });
  }
}

await ctx.close();

// ----- write output -----
const ts = new Date().toISOString();
const header = [
  `# Gated-source signal — ${date}`,
  '',
  `> Generated ${ts} by fetch-gated.mjs.`,
  '> This is **input material** for the editorial stage. Fold relevant',
  '> items into research/topic.md and post.json. Do NOT paste this file',
  '> verbatim into public copy — it contains source attribution and',
  '> raw text from gated communities.',
  '',
];

const body = results
  .filter(r => !r.skipped)
  .map(r => r.body)
  .join('\n\n');

const skipped = results.filter(r => r.skipped);
const skippedSection = skipped.length
  ? '\n\n## Skipped sources\n\n' + skipped.map(s => `- ${s.name}: ${s.reason}`).join('\n') + '\n'
  : '';

await fs.writeFile(outputPath, header.join('\n') + body + skippedSection);
console.log('');
console.log(`✓ Wrote ${outputPath}`);
console.log('  → fold relevant items into research/topic.md before editorial stage');
