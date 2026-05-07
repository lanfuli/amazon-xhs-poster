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
// opt() returns the value AFTER `name`, but only if that value isn't itself
// another flag (i.e. doesn't start with `--`). This means `--connect-cdp
// --setup` correctly treats --connect-cdp as a flag (no value) and --setup
// as the next flag, instead of binding --setup as --connect-cdp's value.
const opt = (name) => {
  const i = args.indexOf(name);
  if (i < 0 || i + 1 >= args.length) return null;
  const next = args[i + 1];
  if (next.startsWith('--')) return null;
  return next;
};

const SETUP_MODE = flag('--setup');
const HEADED_MODE = flag('--headed') || SETUP_MODE;
const DATE_OVERRIDE = opt('--date');
const CONFIG_PATH_OVERRIDE = opt('--config');
const DRY_RUN = flag('--dry-run');
const CONNECT_CDP = flag('--connect-cdp');
// Default to 127.0.0.1 (IPv4) NOT localhost — on macOS localhost resolves
// to ::1 (IPv6) but Chrome's --remote-debugging-port only binds IPv4, so
// connecting via localhost gives ECONNREFUSED ::1:9222.
const CDP_URL = opt('--connect-cdp') || 'http://127.0.0.1:9222';

if (flag('-h') || flag('--help')) {
  console.log(`fetch-gated.mjs — fetch X / LinkedIn / wearesellers content

USAGE
  --setup            First run: open headed Playwright Chromium (separate
                     profile), you log in there, profile saves to disk
  --connect-cdp [url] Connect to an already-running real Chrome via Chrome
                     DevTools Protocol (default url: http://127.0.0.1:9222).
                     Use this if Google blocks Playwright Chromium with
                     "This browser or app may not be secure" — connecting
                     to your real Chrome bypasses that detection because
                     Google sees a real Chrome (not Playwright Chromium).
                     Pre-requisite: Chrome must be running with the flag
                     --remote-debugging-port=9222. See:
                       scripts/launch-chrome-debug.sh
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

const browserMode = CONNECT_CDP
  ? `CDP (${CDP_URL}) — connect to existing Chrome`
  : `persistent Chromium profile (${profileDir})`;
console.log(`config:    ${cfgPath}`);
console.log(`browser:   ${browserMode}`);
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

// ----- launch / connect browser -----
//
// Two modes:
//   1) Persistent Chromium profile (default): Playwright manages its own
//      Chromium binary in a separate profile dir. Fast, isolated, but Google
//      sometimes flags this with "browser may not be secure" because
//      Playwright Chromium has detectable automation indicators.
//   2) CDP connect to existing Chrome (--connect-cdp): connects to a
//      separately-launched real Chrome via Chrome DevTools Protocol. Real
//      Chrome bypasses Google's "may not be secure" check. The user must
//      have launched Chrome with --remote-debugging-port=9222 (see
//      scripts/launch-chrome-debug.sh).
async function launchBrowser() {
  if (CONNECT_CDP) {
    let browser;
    try {
      browser = await chromium.connectOverCDP(CDP_URL, { timeout: 5000 });
    } catch (e) {
      console.error(`Failed to connect to Chrome via CDP at ${CDP_URL}.`);
      console.error('');
      console.error('Make sure Chrome is running with --remote-debugging-port=9222:');
      console.error('  bash scripts/launch-chrome-debug.sh');
      console.error('  # or manually: open -na "Google Chrome" --args --remote-debugging-port=9222');
      console.error('');
      console.error(`Original error: ${e.message}`);
      process.exit(1);
    }
    const ctxs = browser.contexts();
    const ctx = ctxs[0] || await browser.newContext();
    // Tag so we know how to clean up: do NOT close the browser at the end
    // because that would close the user's whole Chrome.
    ctx._isCDP = true;
    ctx._browser = browser;
    return ctx;
  }
  return await chromium.launchPersistentContext(profileDir, {
    headless: !HEADED_MODE,
    viewport: { width: 1280, height: 900 },
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
  });
}

async function closeContext(ctx) {
  if (ctx._isCDP) {
    // Don't close the user's Chrome; just disconnect Playwright.
    await ctx._browser.close();
  } else {
    await ctx.close();
  }
}

// ----- SETUP mode -----
if (SETUP_MODE) {
  if (CONNECT_CDP) {
    console.log('⚠️  SETUP MODE + --connect-cdp');
    console.log('Verifying Chrome is reachable at', CDP_URL, '...');
    const ctx = await launchBrowser();
    const page = await ctx.newPage();
    try {
      await page.goto('https://x.com/home', { timeout: 10000 });
      const title = await page.title();
      console.log(`✓ Connected. Active tab title: ${title}`);
      console.log('Make sure your Chrome is already logged into:');
      console.log('  • https://x.com/');
      console.log('  • https://www.linkedin.com/');
      console.log('  • https://www.wearesellers.com/');
      console.log('Once logged in there, run without --setup to fetch.');
    } finally {
      await page.close();
      await closeContext(ctx);
    }
    process.exit(0);
  }

  console.log('⚠️  SETUP MODE (Playwright Chromium, separate profile)');
  console.log('This opens a Chromium window with a fresh profile.');
  console.log('');
  console.log('Note: Google sometimes blocks Playwright Chromium with');
  console.log('"This browser or app may not be secure". If that happens,');
  console.log('cancel and use --connect-cdp instead — see');
  console.log('references/gated-sources.md.');
  console.log('');
  console.log('Otherwise, log in to whichever services you want fetched:');
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

  await new Promise((resolve) => {
    process.on('SIGINT', () => { console.log('\nClosing...'); resolve(); });
    ctx.on('close', resolve);
  });
  await closeContext(ctx);
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

await closeContext(ctx);

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
