#!/usr/bin/env node
/*
 * fetch-gated.mjs — fetch login-protected content (X, LinkedIn, wearesellers,
 * billiondollarsellers.com) using a persistent Playwright profile.
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
  console.log(`fetch-gated.mjs — fetch research signal from 6 sources:
  X / Twitter, LinkedIn, wearesellers.com, billiondollarsellers.com,
  corporate.walmart.com news, YouTube creator-signal.

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
      console.log('  • https://www.billiondollarsellers.com/  (subscription)');
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
  console.log('  • https://www.billiondollarsellers.com/sign-in  (subscription required for full body)');
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
        return nodes.slice(0, 12).map((node) => {
          const tEl = node.querySelector('time');
          const linkEl = tEl?.closest('a');
          const text = node.querySelector('[data-testid="tweetText"]')?.innerText?.trim() || '';
          // Detect pinned tweet — its socialContext element typically reads
          // "Pinned" / "已置顶". We don't filter it out (still useful), but
          // tag it so age-based filtering doesn't reject it incorrectly.
          const ctx = node.querySelector('[data-testid="socialContext"]')?.innerText?.trim() || '';
          const isPinned = /pinned|置顶/i.test(ctx);
          return {
            ts: tEl?.getAttribute('datetime') || '',
            url: linkEl?.href || '',
            text: text.slice(0, 600),
            isPinned,
          };
        });
      });

      // Take up to 5 tweets total. Don't reject by 24h cutoff (X profiles
      // often have 1+ pinned old tweets; analysts may not post daily).
      // Editorial stage decides what's relevant by glancing at timestamps.
      const recent = tweets.filter(t => t.text).slice(0, 5);
      lines.push(`### @${handle} (${tier})`);
      if (!recent.length) {
        lines.push(`_(no tweets visible — check handle exists at https://x.com/${handle})_`);
        lines.push('');
      } else {
        for (const t of recent) {
          const tsHuman = t.ts ? new Date(t.ts).toISOString().slice(0, 16).replace('T', ' ') : '?';
          const pin = t.isPinned ? ' (pinned)' : '';
          lines.push(`- **${tsHuman}**${pin} — ${t.text.split('\n').slice(0, 4).join(' / ')}`);
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

      const posts = await page.$$eval(
        'div.feed-shared-update-v2, [data-urn^="urn:li:activity:"]',
        (nodes) => {
          // LinkedIn renders post containers with screen-reader labels like
          // "Feed post number 1" inside hidden visually-hidden spans. Naïve
          // innerText on the container picks those up. Look INSIDE for the
          // actual post commentary text via LinkedIn's content classes.
          const contentSelectors = [
            '.update-components-text',
            '.feed-shared-text__text-view',
            '.feed-shared-update-v2__commentary',
            '[data-test-id="main-feed-activity-card__commentary"]',
            '.feed-shared-text',
          ];
          return nodes.slice(0, 5).map((node) => {
            let text = '';
            for (const sel of contentSelectors) {
              const el = node.querySelector(sel);
              if (el && el.innerText?.trim()) {
                text = el.innerText.trim();
                break;
              }
            }
            // If nothing matched, fall back to innerText but strip the
            // common screen-reader prefixes we know about.
            if (!text) {
              text = (node.innerText || '').trim()
                .replace(/^(Feed post number \d+\s*\/\s*[^/]+\s*\/\s*)+/i, '')
                .replace(/\b\w+\s+(?:reposted this|liked this|commented on this)\s*/gi, '');
            }
            const link = node.querySelector('a[href*="/posts/"], a[href*="/pulse/"]')?.href || '';
            return { text: text.slice(0, 500), url: link };
          });
        }
      );

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

    // wearesellers DOM structure (verified 2026-05):
    //   - Hot post badge: <span class="badge-hot">热</span> (热 = "hot")
    //   - Paid post icon: <img src=".../pay_fee.png"> or pay_high.png
    //     or pay_fee_black.png (post types in zh: 悬赏 = "bounty",
    //     私密悬赏 = "private bounty", 已公开悬赏 = "publicly disclosed
    //     bounty"). All three are paid; we drop them.
    //
    // We want HOT posts that are NOT paid. The script walks each anchor
    // and inspects its parent row for these markers, then sorts: hot+free
    // first, then plain free, then drop paid entirely.
    // Two-pass DOM walk. wearesellers' logged-in homepage marks hot posts
    // with <span class="zd-question">热</span> (NOT .badge-hot — that's
    // the anonymous-view class) and paid posts with <img src=".../pay_fee.png">
    // or pay_high.png / pay_fee_black.png. Anchors don't have <li> parents,
    // so we walk up to 6 levels from each marker to find the nearest
    // question/article/headline anchor that the marker belongs to.
    const links = await page.evaluate(() => {
      const allAnchors = Array.from(document.querySelectorAll(
        'a[href*="/question/"], a[href*="/headline/"], a[href*="/article/"]'
      ));

      // Walk up from `el` looking for any element that contains an anchor
      // matching `selector`. Returns that anchor or null.
      function findNearestAnchor(el, selector, maxLevels = 6) {
        let row = el;
        for (let i = 0; i < maxLevels && row?.parentElement; i++) {
          row = row.parentElement;
          const a = row.querySelector(selector);
          if (a) return a;
        }
        return null;
      }

      const ANCHOR_SEL = 'a[href*="/question/"], a[href*="/headline/"], a[href*="/article/"]';

      // Pass 1: hot anchors. Match spans whose text is exactly "热"
      // (the literal Chinese character meaning "hot" — wearesellers
      // emits this as the hot-post badge text). Class is zd-question
      // for logged-in view, badge-hot for anonymous; both accepted.
      const hotMarkers = [
        ...document.querySelectorAll('.badge-hot'),
        ...Array.from(document.querySelectorAll('span.zd-question'))
          .filter(s => s.textContent?.trim() === '热'),
      ];
      const hotAnchorSet = new Set();
      for (const marker of hotMarkers) {
        const a = findNearestAnchor(marker, ANCHOR_SEL);
        if (a) hotAnchorSet.add(a);
      }

      // Pass 2: paid anchors.
      const payIcons = document.querySelectorAll(
        'img[src*="pay_fee"], img[src*="pay_high"], img[src*="pay_fee_black"]'
      );
      const paidAnchorSet = new Set();
      for (const icon of payIcons) {
        const a = findNearestAnchor(icon, ANCHOR_SEL);
        if (a) paidAnchorSet.add(a);
      }

      return allAnchors.slice(0, 100).map((n) => ({
        href: n.href,
        text: n.innerText?.trim().slice(0, 160) || '',
        isHot: hotAnchorSet.has(n),
        isPaid: paidAnchorSet.has(n),
      }));
    });

    // Dedupe by canonical question/article ID — wearesellers homepage links
    // include many anchors to the same thread (one per recent reply). We
    // want one link per *thread*, normalized to its base URL.
    const canonicalKey = (href) => {
      const m = href.match(/wearesellers\.com\/(question|article|headline)\/([^/?#]+)/);
      return m ? `${m[1]}/${m[2]}` : href;
    };
    // Also reject anchor texts that look like usernames (no Chinese chars,
    // short ASCII-only) — those happen when the homepage links author
    // names from question metadata.
    const looksLikeUsername = (text) => {
      if (text.length > 30) return false;
      // Regex range U+4E00..U+9FFF covers CJK Unified Ideographs.
      if (/[一-鿿]/.test(text)) return false; // contains Chinese, fine
      if (/^[a-zA-Z0-9_]+$/.test(text)) return true;  // pure handle-like
      return false;
    };

    const seen = new Set();
    // Simple filter: anything non-paid is fair game. Hot tag is annotated
    // for editorial visibility but not used to prioritize.
    const unique = links.filter(l => {
      if (!l.href.includes('wearesellers.com')) return false;
      if (l.isPaid) return false;                     // visual icon test
      if (/\/article\/paid\//.test(l.href)) return false;  // URL path test (belt+suspenders)
      if (/[?&]page=|\/category-/.test(l.href)) return false;
      if (l.text.length < 12) return false;
      if (looksLikeUsername(l.text)) return false;
      const key = canonicalKey(l.href);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, topN);

    if (!unique.length) {
      lines.push('_(no posts found on homepage — check login state)_');
    } else {
      for (const link of unique) {
        try {
          // Strip the query string so we hit the canonical thread URL.
          const cleanUrl = link.href.split('?')[0].split('#')[0];
          await page.goto(cleanUrl, { waitUntil: 'domcontentloaded', timeout: 20000 });
          await sleep(1500);
          const hotTag = link.isHot ? ' [hot]' : '';
          // wearesellers question pages use WeCenter-style classes (verified
          // via CDP probe on logged-in view 2026-05-07):
          //   .aw-question-detail — wraps the question post
          //   .mod-body           — body block of question OR answer
          //   .content.markitup-box — markdown-rendered content
          // The page typically has 1 question .mod-body and N answer
          // .mod-body siblings. We grab the question detail first, then
          // the first 1-2 answer bodies, and concatenate.
          const body = await page.evaluate(() => {
            // Prefer .mod-body since that's the cleanest content slice.
            // Take up to 3 of them (question + 2 best answers).
            const modBodies = Array.from(document.querySelectorAll('.mod-body'))
              .filter(el => el.innerText?.trim().length > 50)
              .slice(0, 3);
            if (modBodies.length) {
              return modBodies.map(el => el.innerText.trim()).join('\n\n').slice(0, 1500);
            }
            // Fallback: try .aw-question-detail then .content.markitup-box
            for (const sel of ['.aw-question-detail', '.content.markitup-box', '.aw-main-content']) {
              const el = document.querySelector(sel);
              if (el?.innerText?.trim().length > 100) {
                return el.innerText.trim().slice(0, 1500);
              }
            }
            return '';
          }).catch(() => '');
          lines.push(`- **${link.text}**${hotTag}`);
          lines.push(`  ${cleanUrl}`);
          if (body) {
            const summary = body.split('\n').filter(l => l.trim()).slice(0, 5).join(' / ');
            lines.push(`  ${summary}`);
          } else {
            lines.push(`  _(body not extracted — DOM selector mismatch or login required)_`);
          }
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

// ===== BDS (billiondollarsellers.com) =====
async function fetchBDS() {
  const bdsCfg = gatedCfg.bds || {};
  if (!bdsCfg.enabled) {
    return { name: 'billiondollarsellers.com', skipped: true, reason: 'disabled' };
  }

  const topN = bdsCfg.top_n || 5;
  const lines = [`## billiondollarsellers.com — top ${topN} archive posts`, ''];

  if (DRY_RUN) {
    lines.push('_(DRY RUN: would fetch /archive and click into top posts)_');
    return { name: 'billiondollarsellers.com', body: lines.join('\n') };
  }

  const page = await ctx.newPage();
  try {
    await page.goto('https://www.billiondollarsellers.com/archive', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await sleep(2500);

    // BDS archive structure (verified via CDP probe 2026-05-07):
    //   - Article links: <a href="/p/<slug>"> within the archive list
    //   - Date text appears as "Mon DD, YYYY • N min read" near each title
    //   - Article body container: #content-blocks (id) OR .dream-post-content-doc
    //
    // We collect the top N article anchors (deduped by canonical /p/<slug>),
    // then navigate into each to extract the body.
    const links = await page.$$eval('a[href*="/p/"]', (nodes) => {
      // BDS archive anchors include date / "N min read" / bullet separator
      // in the same innerText as the title. Strip those so the title is
      // just the article title (typically prefixed with "[ BDSN ]").
      const cleanTitle = (raw) => {
        return raw
          .split('\n')
          .map(s => s.trim())
          .filter(Boolean)
          .filter(s => s !== '•')
          .filter(s => !/^\d+\s*min\s*read$/i.test(s))
          .filter(s => !/^[A-Z][a-z]+ \d{1,2}, \d{4}$/.test(s))  // "May 7, 2026"
          .join(' ')
          .slice(0, 200);
      };
      return nodes
        .map((n) => ({
          href: n.href,
          text: (() => {
            const direct = cleanTitle(n.innerText || '');
            if (direct.length > 8) return direct;
            const parent = n.parentElement;
            if (!parent) return direct;
            const heading = parent.querySelector('h1, h2, h3, h4');
            return cleanTitle(heading?.innerText || direct);
          })(),
        }))
        .filter(l => /\/p\/[^/?#]+/.test(l.href))
        .slice(0, 80);
    });

    const canonicalKey = (href) => {
      const m = href.match(/billiondollarsellers\.com\/p\/([^/?#]+)/);
      return m ? m[1] : href;
    };

    const seen = new Set();
    const unique = links.filter((l) => {
      if (l.text.length < 6) return false;
      const key = canonicalKey(l.href);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, topN);

    if (!unique.length) {
      lines.push('_(no articles found on /archive — check login state or layout change)_');
    } else {
      for (const link of unique) {
        try {
          const cleanUrl = link.href.split('?')[0].split('#')[0];
          await page.goto(cleanUrl, { waitUntil: 'domcontentloaded', timeout: 25000 });
          await sleep(1800);

          const result = await page.evaluate(() => {
            // Body extraction (verified selectors, in priority order):
            //   1. #content-blocks — canonical id on subscribed view
            //   2. .dream-post-content-doc — alternate class on same node
            //   3. .rendered-post — wrapping container fallback
            const selectors = ['#content-blocks', '.dream-post-content-doc', '.rendered-post'];
            let body = '';
            for (const sel of selectors) {
              const el = document.querySelector(sel);
              if (el?.innerText?.trim().length > 100) {
                body = el.innerText.trim().slice(0, 1800);
                break;
              }
            }
            // Date: BDS shows "Mon DD, YYYY • N min read" near the title.
            // Try the first <time> element, then fall back to scanning text.
            let dateStr = document.querySelector('time')?.getAttribute('datetime')
              || document.querySelector('time')?.innerText?.trim()
              || '';
            if (!dateStr) {
              const m = document.body.innerText?.match(/([A-Z][a-z]+ \d{1,2}, \d{4})/);
              if (m) dateStr = m[1];
            }
            return { body, dateStr };
          }).catch(() => ({ body: '', dateStr: '' }));

          const datePart = result.dateStr ? ` (${result.dateStr})` : '';
          lines.push(`- **${link.text}**${datePart}`);
          lines.push(`  ${cleanUrl}`);
          if (result.body) {
            const summary = result.body.split('\n').filter(l => l.trim()).slice(0, 6).join(' / ');
            lines.push(`  ${summary}`);
          } else {
            lines.push(`  _(body not extracted — paywalled article or DOM change)_`);
          }
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

  return { name: 'billiondollarsellers.com', body: lines.join('\n') };
}

// ===== Walmart corporate news (PUBLIC, sitemap-driven) =====
// Walmart's /news listing page is JS-rendered (only nav chrome in raw HTML),
// but `https://corporate.walmart.com/news.sitemap.xml` is a real machine-
// readable sitemap with <lastmod> timestamps. This fetcher pulls the
// sitemap, picks the top N most-recently-modified URLs that look like
// /news/YYYY/MM/DD/<slug> articles (filtering out events/, content/,
// suppliers/), and uses Playwright to extract title + first-paragraph body.
async function fetchWalmartNews() {
  const wmCfg = gatedCfg.walmart || {};
  if (!wmCfg.enabled) {
    return { name: 'corporate.walmart.com', skipped: true, reason: 'disabled' };
  }

  const topN = wmCfg.top_n || 5;
  const lines = [`## corporate.walmart.com — top ${topN} recent news`, ''];

  if (DRY_RUN) {
    lines.push('_(DRY RUN: would fetch news.sitemap.xml and click into top N)_');
    return { name: 'corporate.walmart.com', body: lines.join('\n') };
  }

  let sitemapXml;
  try {
    const resp = await fetch('https://corporate.walmart.com/news.sitemap.xml', {
      headers: { 'User-Agent': 'Mozilla/5.0 amazon-xhs-poster/1.7' },
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    sitemapXml = await resp.text();
  } catch (err) {
    lines.push(`_⚠ sitemap fetch failed: ${err.message}_`);
    return { name: 'corporate.walmart.com', body: lines.join('\n') };
  }

  // Parse sitemap entries: <url><loc>...</loc><lastmod>...</lastmod></url>
  const entries = [];
  const urlBlockRe = /<url>([\s\S]*?)<\/url>/g;
  let m;
  while ((m = urlBlockRe.exec(sitemapXml)) !== null) {
    const block = m[1];
    const loc = (block.match(/<loc>([^<]+)<\/loc>/) || [])[1];
    const lastmod = (block.match(/<lastmod>([^<]+)<\/lastmod>/) || [])[1];
    if (!loc) continue;
    // Keep only article-style URLs: /news/YYYY/MM/DD/<slug>
    if (!/\/news\/\d{4}\/\d{2}\/\d{2}\//.test(loc)) continue;
    entries.push({ loc, lastmod: lastmod || '' });
  }
  // Sort by lastmod desc; ties → URL date desc.
  entries.sort((a, b) => (b.lastmod || '').localeCompare(a.lastmod || ''));
  const picks = entries.slice(0, topN);

  if (!picks.length) {
    lines.push('_(no /news/YYYY/MM/DD/ articles found in sitemap)_');
    return { name: 'corporate.walmart.com', body: lines.join('\n') };
  }

  const page = await ctx.newPage();
  try {
    for (const entry of picks) {
      try {
        await page.goto(entry.loc, { waitUntil: 'domcontentloaded', timeout: 25000 });
        await sleep(1500);
        const result = await page.evaluate(() => {
          const title = document.querySelector('h1')?.innerText?.trim() || '';
          // Walmart article body: try common containers in priority order.
          const bodySelectors = [
            'article',
            '.cmp-text',
            '[class*="news-detail"]',
            'main',
          ];
          let body = '';
          for (const sel of bodySelectors) {
            const el = document.querySelector(sel);
            if (el?.innerText?.trim().length > 200) {
              body = el.innerText.trim();
              break;
            }
          }
          return { title, body: body.slice(0, 1500) };
        }).catch(() => ({ title: '', body: '' }));

        const dateLabel = entry.lastmod ? entry.lastmod.slice(0, 10) : 'undated';
        lines.push(`- **${result.title || entry.loc}** (${dateLabel})`);
        lines.push(`  ${entry.loc}`);
        if (result.body) {
          const summary = result.body.split('\n').filter(l => l.trim()).slice(0, 4).join(' / ');
          lines.push(`  ${summary}`);
        } else {
          lines.push(`  _(body not extracted — DOM selector mismatch)_`);
        }
        lines.push('');
      } catch (err) {
        lines.push(`- ${entry.loc} — _⚠ ${err.message?.slice(0, 100)}_`);
        lines.push('');
      }
      await sleep(randomDelay());
    }
  } finally {
    await page.close();
  }

  return { name: 'corporate.walmart.com', body: lines.join('\n') };
}

// ===== YouTube creator-signal (Playwright via existing CDP) =====
// YouTube's `/feeds/videos.xml?channel_id=...` RSS endpoint is unreliable
// (returns 404 from many IPs / regions as of 2026-05). Workaround: visit
// the channel's /videos page via the user's logged-in Chrome (CDP) and
// extract titles + relative dates from the rendered DOM.
async function fetchYouTube() {
  const ytCfg = gatedCfg.youtube || {};
  if (!ytCfg.enabled || !ytCfg.channels?.length) {
    return { name: 'YouTube', skipped: true, reason: 'disabled or no channels configured' };
  }

  const lines = [`## YouTube — recent uploads`, ''];

  if (DRY_RUN) {
    for (const c of ytCfg.channels) {
      lines.push(`### ${c.name || c.handle} — DRY RUN`);
      lines.push('');
    }
    return { name: 'YouTube', body: lines.join('\n') };
  }

  const page = await ctx.newPage();
  try {
    for (const ch of ytCfg.channels) {
      const handle = ch.handle?.startsWith('@') ? ch.handle : `@${ch.handle}`;
      const name = ch.name || handle;
      const url = `https://www.youtube.com/${handle}/videos`;
      try {
        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
        // YouTube is JS-heavy; wait for the video grid.
        await page.waitForSelector('ytd-rich-item-renderer, ytd-grid-video-renderer', { timeout: 12000 }).catch(() => null);
        await sleep(2000);
        const videos = await page.$$eval(
          'ytd-rich-item-renderer, ytd-grid-video-renderer',
          (nodes) => nodes.slice(0, 5).map((node) => {
            const titleEl = node.querySelector('#video-title, a#video-title-link, h3 a');
            const title = titleEl?.innerText?.trim() || titleEl?.getAttribute('title') || '';
            const link = titleEl?.href || '';
            // Metadata line typically reads "1.2K views · 3 days ago"
            const meta = node.querySelector('#metadata-line')?.innerText?.trim() || '';
            return { title, url: link, meta };
          }).filter(v => v.title)
        );

        lines.push(`### ${name}`);
        if (!videos.length) {
          lines.push(`_(no videos visible at ${url})_`);
          lines.push('');
        } else {
          for (const v of videos) {
            const metaLine = v.meta ? ` (${v.meta.replace(/\s+/g, ' ')})` : '';
            lines.push(`- **${v.title}**${metaLine}`);
            if (v.url) lines.push(`  ${v.url}`);
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
  } finally {
    await page.close();
  }

  return { name: 'YouTube', body: lines.join('\n') };
}

// ----- run all -----
const results = [];
for (const fn of [fetchX, fetchLinkedIn, fetchWearesellers, fetchBDS, fetchWalmartNews, fetchYouTube]) {
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
