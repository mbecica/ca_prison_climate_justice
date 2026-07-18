/**
 * Scrapes per-institution monthly In-Custody population from the CDCR
 * Population Data Points dashboard:
 *   In-Custody > Crosstabs > Rows = "Location", Columns = "None"
 *
 * This is the per-facility population that feeds `average_YYYY_population` /
 * `capacity_percent_YYYY` in cdcr_facilities.csv. It replaces the hand-made
 * CDCR_YYYY_pop_averages.csv transcription and removes the need to download
 * TPOP-1 population PDFs (CDCR's dashboard now carries the same institution
 * counts). See REFRESH.md §2.
 *
 * The "Location" dimension lists every CDCR institution code (ASP, CTF, SATF, …)
 * plus a few non-institution programs (Community Reentry, Department of State
 * Hospitals, Alternative Custody, Medical Reprieve); downstream code filters to
 * the institution codes in cdcr_facilities.csv. Counts < 10 are suppressed by
 * CDCR (shown as "*") and are emitted as blank.
 *
 * Output (stable, un-dated LIVING file — the full monthly series grows each
 * refresh; annual averages are computed downstream in create_cdcr_facilities.ipynb):
 *   data_sources/facilities/CDCR/cdcr_population_by_location.csv
 *   columns: year, month, cdcr_code, in_custody
 *
 * Usage:
 *   node scrapers/fetch_cdcr_population.js
 *
 * Interactive: launches a visible Chromium window and drives the Power BI Gov
 * dashboard by mouse/scroll. Needs a display; brittle to dashboard layout
 * changes (like the sibling CDCR scrapers). Screenshots to /tmp for debugging.
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiN2RjZmFjNzItMzI0Ni00M2IwLWJmZjgtNDgyMjUyMjVhOWMwIiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9&pageName=6eb2cf1a956ed8b180cb';
const OUT_PATH = path.join(__dirname, '..', 'data_sources', 'facilities', 'CDCR', 'cdcr_population_by_location.csv');

const MONTHS = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6,
                 Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };

async function ss(page, name) {
  const p = `/tmp/cdcr_pop_${name}.png`;
  await page.screenshot({ path: p, fullPage: true }).catch(() => {});
  console.log(`  Screenshot: ${p}`);
}

// Click an element whose visible text (or aria-label) exactly matches `label`,
// searching through shadow roots. Used for the population-type buttons and the
// crosstab radio options.
async function clickByText(page, label) {
  console.log(`  Click: "${label}"`);
  const found = await page.evaluate((lbl) => {
    function find(root) {
      for (const el of root.querySelectorAll('*')) {
        const text = (el.textContent || '').trim();
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        if (text === lbl || aria === lbl.toLowerCase()) {
          const r = el.getBoundingClientRect();
          if (r.width > 0 && r.height > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2, tag: el.tagName, text: text.slice(0, 60) };
        }
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    return find(document);
  }, label);
  if (found) {
    console.log(`    <${found.tag}> "${found.text}" at (${Math.round(found.x)}, ${Math.round(found.y)})`);
    await page.mouse.click(found.x, found.y);
    return true;
  }
  console.warn(`    Not found: "${label}"`);
  return false;
}

async function clickByAriaIncludes(page, substr) {
  console.log(`  Click aria~="${substr}"`);
  const found = await page.evaluate((s) => {
    function find(root) {
      for (const el of root.querySelectorAll('*')) {
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        if (aria.includes(s.toLowerCase())) {
          const r = el.getBoundingClientRect();
          if (r.width > 0 && r.height > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    return find(document);
  }, substr);
  if (found) { await page.mouse.click(found.x, found.y); return true; }
  console.warn(`    Not found: aria~="${substr}"`);
  return false;
}

// Return the currently-rendered grid rows as {idx, cells}. Each Power BI grid
// row carries a stable absolute aria-rowindex; we dedup on that (not on visible
// text) so rows that render with the same visible text — e.g. a merged-away
// Year/Month cell, or two months with identical population — are never
// collapsed. Cells carry aria-colindex so we can place Year/Month/Location/value
// even when leading cells are visually merged.
async function extractVisibleRows(page) {
  return await page.evaluate(() => {
    function findGrid(root) {
      const g = root.querySelector('[role="grid"]');
      if (g) return g;
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = findGrid(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    const grid = findGrid(document);
    if (!grid) return [];
    const out = [];
    for (const row of grid.querySelectorAll('[role="row"]')) {
      const idx = row.getAttribute('aria-rowindex');
      if (!idx) continue;
      const cells = {};
      for (const c of row.querySelectorAll('[role="rowheader"], [role="columnheader"], [role="gridcell"]')) {
        const col = c.getAttribute('aria-colindex');
        cells[col] = (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' ');
      }
      out.push({ idx: +idx, cells });
    }
    return out;
  });
}

// Gentle scroll: small wheel steps so no row is skipped between captures.
async function scrollGrid(page) {
  await page.mouse.move(700, 450);
  await page.mouse.wheel(0, 120);
  await page.waitForTimeout(120);
}

async function extractFullTable(page) {
  const byIdx = new Map();   // rowindex -> {idx, cells}
  const capture = (rows) => { for (const r of rows) byIdx.set(r.idx, r); };
  capture(await extractVisibleRows(page));
  let noNew = 0;
  for (let i = 0; i < 600; i++) {
    const before = byIdx.size;
    await scrollGrid(page);
    await page.waitForTimeout(280);
    capture(await extractVisibleRows(page));
    if (byIdx.size === before) { if (++noNew >= 20) break; } else { noNew = 0; }
    if (i % 20 === 0) console.log(`    Scroll ${i}: ${byIdx.size} unique rows`);
  }
  const rows = [...byIdx.values()].sort((a, b) => a.idx - b.idx);
  console.log(`    Total unique rows: ${rows.length} (idx ${rows[0]?.idx}..${rows[rows.length-1]?.idx})`);
  return rows;
}

// Rows are {idx, cells:{colindex->text}} sorted by absolute row index.
// Columns: 1=Year, 2=Month, 3=Location, 4=In-Custody. Year/Month are visually
// merged (present only on the first row of each group), so forward-fill them
// down the idx-ordered rows. Suppressed values ("*") become blank.
function normalize(rows) {
  const out = [];
  let year = null, month = null;
  for (const { cells } of rows) {
    const y = cells['1'], m = cells['2'], loc = cells['3'], val = cells['4'];
    if (y && /^\d{4}$/.test(y)) year = y;
    if (m && MONTHS[m]) month = MONTHS[m];
    if (!loc || loc === 'Location') continue;              // header / empty
    if (val === undefined || val === 'In-Custody') continue;
    if (year === null || month === null) continue;
    const inCustody = (val === '*' || val === '') ? '' : val.replace(/,/g, '');
    if (inCustody !== '' && !/^\d+$/.test(inCustody)) continue;   // skip stray rows
    out.push({ year, month, cdcr_code: loc, in_custody: inCustody });
  }
  return out;
}

function toCsv(records) {
  const header = 'year,month,cdcr_code,in_custody';
  const lines = records.map(r => {
    const code = /[",\n]/.test(r.cdcr_code) ? `"${r.cdcr_code.replace(/"/g, '""')}"` : r.cdcr_code;
    return `${r.year},${r.month},${code},${r.in_custody}`;
  });
  return [header, ...lines].join('\n') + '\n';
}

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  try {
    console.log('Loading CDCR Population Data Points dashboard...');
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(12000);
    await ss(page, '01_loaded');

    console.log('\nClicking landing button...');
    await clickByText(page, 'Population Data Points Dashboard');
    await page.waitForTimeout(10000);
    await ss(page, '02_dashboard');

    console.log('\nSelecting In-Custody population type...');
    await clickByText(page, 'In-Custody');
    await page.waitForTimeout(5000);
    await ss(page, '03_in_custody');

    console.log('\nNavigating to Crosstabs...');
    await clickByAriaIncludes(page, 'crosstab');
    await page.waitForTimeout(8000);
    await ss(page, '04_crosstabs');

    // In the In-Custody Crosstabs: Rows (Data Point) = Location, Columns (Demographic) = None.
    console.log('\nSelecting Rows = Location...');
    await clickByText(page, 'Location');
    await page.waitForTimeout(4000);
    console.log('Selecting Columns = None...');
    await clickByText(page, 'None');
    await page.waitForTimeout(4000);
    await ss(page, '05_location_none');

    console.log('\nExtracting table (scrolling through all months × locations)...');
    const rawRows = await extractFullTable(page);
    if (rawRows.length === 0) {
      const html = await page.content();
      fs.writeFileSync('/tmp/cdcr_pop_page.html', html, 'utf8');
      throw new Error('No rows extracted — saved /tmp/cdcr_pop_page.html for debugging');
    }
    console.log('\nRaw rows (first 8):');
    rawRows.slice(0, 8).forEach((r, i) => console.log(`  [${i}]`, r));

    const records = normalize(rawRows);
    const codes = [...new Set(records.map(r => r.cdcr_code))].sort();
    const years = [...new Set(records.map(r => r.year))].sort();
    console.log(`\nNormalized ${records.length} rows: ${codes.length} locations × years ${years.join(', ')}`);
    console.log(`Locations: ${codes.join(', ')}`);

    fs.writeFileSync(OUT_PATH, toCsv(records), 'utf8');
    console.log(`\nSaved -> ${OUT_PATH}`);
  } catch (err) {
    console.error('Fatal:', err.message);
    await page.screenshot({ path: '/tmp/cdcr_pop_error.png', fullPage: true }).catch(() => {});
    process.exitCode = 1;
  } finally {
    await browser.close();
  }
})();
