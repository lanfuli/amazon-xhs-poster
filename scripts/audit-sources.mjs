#!/usr/bin/env node
/*
 * audit-sources.mjs — periodic URL decay check for the source ladder.
 *
 * USAGE
 *   node scripts/audit-sources.mjs            # full report to stdout
 *   node scripts/audit-sources.mjs --json     # machine-readable JSON
 *   node scripts/audit-sources.mjs --quiet    # only print URLs with issues
 *
 * What it does
 *   - Hits every public Tier A/B URL from references/editorial-sop.md
 *   - Reports HTTP status, content-length, and a recency hint where possible
 *     (looks for YYYY-MM-DD-style dates in the body)
 *   - Surfaces URLs that 404, 301-redirect, or look like they haven't been
 *     updated in 90+ days
 *
 * Run cadence: monthly (or before adding new sources to confirm baseline).
 *
 * This script does NOT touch gated sources (X, LinkedIn, wearesellers, BDS,
 * YouTube) — those need a logged-in browser session. Use fetch-gated.mjs
 * for those; if those start failing you'll see it in the next daily run.
 */

const args = process.argv.slice(2);
const FORMAT_JSON = args.includes('--json');
const QUIET = args.includes('--quiet');
const STALE_DAYS = 90;

// Tier A/B sources (PUBLIC, no auth needed). Each entry:
//   { url, tier, label, dateRegex }
// dateRegex is OPTIONAL — when present, audit-sources greps the body for
// the most recent matching date and flags if older than STALE_DAYS. This
// is fuzzy by design; the goal is to catch obvious decay, not to validate
// every page's editorial freshness.
const SOURCES = [
  // ----- Tier A (dated, public) -----
  {
    url: 'https://developer-docs.amazon.com/sp-api/docs/sp-api-release-notes',
    tier: 'A',
    label: 'SP-API release notes',
    dateRegex: /(20\d{2}-\d{2}-\d{2})/,
  },
  {
    url: 'https://marketplacelearn.walmart.com/releasenotes',
    tier: 'A',
    label: 'Walmart Marketplace release notes',
    dateRegex: /(20\d{2}-\d{2}-\d{2}|[A-Z][a-z]+ \d{1,2},? 20\d{2})/,
  },
  {
    url: 'https://www.amz123.com/t',
    tier: 'A',
    label: 'amz123 cross-border headlines',
  },
  {
    url: 'https://www.amz123.com/amazon/news',
    tier: 'A',
    label: 'amz123 Amazon news',
  },
  {
    url: 'https://www.helium10.com/category/podcast/',
    tier: 'A',
    label: 'Helium 10 / Serious Sellers Podcast',
  },
  {
    url: 'https://corporate.walmart.com/news.sitemap.xml',
    tier: 'A',
    label: 'Walmart corporate news sitemap',
    dateRegex: /<lastmod>(20\d{2}-\d{2}-\d{2})/,
  },

  // ----- Tier B (real content, no listing dates) -----
  {
    url: 'https://www.aboutamazon.com/news/retail',
    tier: 'B',
    label: 'aboutamazon retail news',
  },
  {
    url: 'https://www.aboutamazon.com/news/policy-news-views',
    tier: 'B',
    label: 'aboutamazon policy news',
  },
  {
    url: 'https://advertising.amazon.com/library/newsroom',
    tier: 'B',
    label: 'Amazon Ads newsroom',
  },
  {
    // Old /blog 301-redirects to /resources/library since at least 2026-05.
    // editorial-sop.md uses the canonical URL.
    url: 'https://advertising.amazon.com/resources/library',
    tier: 'B',
    label: 'Amazon Ads resources/library (old /blog)',
  },
  {
    url: 'https://buywithprime.amazon.com/blog',
    tier: 'B',
    label: 'Buy with Prime blog',
  },
];

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 amazon-xhs-poster/audit';

async function probe(source) {
  const start = Date.now();
  let status = 0;
  let contentLength = 0;
  let mostRecentDate = null;
  let error = null;
  let finalUrl = source.url;

  try {
    const resp = await fetch(source.url, {
      headers: { 'User-Agent': UA, Accept: '*/*' },
      redirect: 'follow',
    });
    status = resp.status;
    finalUrl = resp.url;
    if (resp.ok) {
      const text = await resp.text();
      contentLength = text.length;
      if (source.dateRegex) {
        const matches = [...text.matchAll(new RegExp(source.dateRegex.source, 'g'))];
        // Find the most recent ISO-like date (sortable as string)
        const dates = matches
          .map(m => m[1])
          .filter(Boolean)
          .filter(d => /^20\d{2}-\d{2}-\d{2}/.test(d));
        if (dates.length) {
          dates.sort();
          mostRecentDate = dates[dates.length - 1];
        }
      }
    }
  } catch (e) {
    error = e.message;
  }

  const elapsedMs = Date.now() - start;
  let staleHint = null;
  if (mostRecentDate) {
    const ageDays = Math.floor((Date.now() - new Date(mostRecentDate).getTime()) / (1000 * 60 * 60 * 24));
    staleHint = ageDays > STALE_DAYS ? `STALE (${ageDays}d since ${mostRecentDate})` : `fresh (${ageDays}d since ${mostRecentDate})`;
  }
  const redirected = finalUrl !== source.url;
  return { ...source, status, contentLength, mostRecentDate, staleHint, error, elapsedMs, finalUrl, redirected };
}

// Categorize a redirect as benign (trailing-slash, http→https, same-domain
// canonical) vs concerning (hostname change, redirected to bare homepage,
// path completely rewritten). Used to suppress noisy flags from sites that
// add UTM params or normalize URLs.
function redirectKind(source, finalUrl) {
  if (!finalUrl || finalUrl === source.url) return 'none';
  try {
    const a = new URL(source.url);
    const b = new URL(finalUrl);
    if (a.hostname !== b.hostname) return 'different-host';
    if (b.pathname === '/' && a.pathname !== '/') return 'to-homepage';
    if (a.pathname.replace(/\/$/, '') === b.pathname.replace(/\/$/, '')) return 'trailing-slash';
    if (a.pathname.toLowerCase() === b.pathname.toLowerCase()) return 'case-only';
    return 'path-rewrite';
  } catch {
    return 'parse-error';
  }
}

// Re-probe a URL once if its first probe looked redirected, to filter
// out transient CDN flips. amz123 has been observed doing this — one
// request gets a redirect to /, the next a clean 200. If the re-probe
// agrees with the first, the redirect is real; if not, treat as
// transient and trust the second result.
async function reprobeIfRedirected(result) {
  if (!result.redirected) return result;
  await new Promise(r => setTimeout(r, 500));
  const second = await probe({ url: result.url, tier: result.tier, label: result.label, dateRegex: result.dateRegex });
  if (!second.redirected) {
    return { ...second, _firstProbeRedirected: true, _note: 'transient redirect on first probe; second probe was clean' };
  }
  return result;
}

function isProblem(r) {
  if (r.error) return true;
  if (r.status >= 400) return true;
  if (r.redirected) {
    const kind = redirectKind(r, r.finalUrl);
    // Trailing-slash and case-only redirects are benign — don't flag.
    if (kind === 'trailing-slash' || kind === 'case-only') return false;
    // Everything else (different host, to homepage, path rewrite) is a real rename.
    return true;
  }
  if (r.staleHint?.startsWith('STALE')) return true;
  if (r.contentLength < 500) return true;  // suspicious empty page
  return false;
}

(async () => {
  const results = [];
  // Probe in parallel with a small concurrency cap (not all at once — be
  // polite). Batch of 4 at a time.
  for (let i = 0; i < SOURCES.length; i += 4) {
    const batch = SOURCES.slice(i, i + 4);
    const batchResults = await Promise.all(batch.map(probe));
    // Re-probe any redirected results once to filter out transient CDN flips.
    const settled = await Promise.all(batchResults.map(reprobeIfRedirected));
    results.push(...settled);
  }

  if (FORMAT_JSON) {
    console.log(JSON.stringify(results, null, 2));
    return;
  }

  const problems = results.filter(isProblem);
  const ok = results.filter(r => !isProblem(r));

  if (!QUIET) {
    console.log(`# Source audit — ${new Date().toISOString().slice(0, 10)}`);
    console.log('');
    console.log(`Probed ${results.length} URLs. ${ok.length} OK, ${problems.length} flagged.`);
    console.log('');
  }

  if (problems.length) {
    console.log('## ⚠ Flagged URLs');
    console.log('');
    for (const r of problems) {
      const reason = r.error
        ? `error: ${r.error}`
        : r.status >= 400
          ? `HTTP ${r.status}`
          : r.redirected
            ? `redirected → ${r.finalUrl}`
            : r.staleHint?.startsWith('STALE')
              ? r.staleHint
              : r.contentLength < 500
                ? `suspiciously small (${r.contentLength} bytes)`
                : 'flagged';
      console.log(`- [${r.tier}] ${r.label}`);
      console.log(`  ${r.url}`);
      console.log(`  ${reason}`);
    }
    console.log('');
  }

  if (!QUIET && ok.length) {
    console.log('## ✓ OK');
    console.log('');
    for (const r of ok) {
      const recency = r.mostRecentDate ? ` — last date ${r.mostRecentDate}` : '';
      console.log(`- [${r.tier}] ${r.label} (HTTP ${r.status}, ${r.contentLength} bytes, ${r.elapsedMs}ms)${recency}`);
    }
    console.log('');
  }

  if (problems.length) {
    process.exitCode = 1;
  }
})();
