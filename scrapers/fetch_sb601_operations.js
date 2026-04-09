/**
 * Scrapes Institution Totals for three operational categories across all fiscal years
 * from the SB 601 Programs Power BI dashboard:
 *   - Lockdowns and Modified Programs
 *   - Number of Deaths
 *   - Overtime Hours
 *
 * Output columns: institution, fiscal_year, category, metric, Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, Apr
 *
 * Usage:
 *   node fetch_sb601_operations.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiYzlkM2RiNWEtZDRjMi00ODllLTg2YzEtZjYyM2MwMjA5NmQ0IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9&pageName=5a926528bbf7e48d60c2';
const OUT_PATH = path.join(__dirname, '..', 'data_sources', 'facilities', 'CDCR', 'sb601_operations_2021-2025.csv');

const FISCAL_YEARS = ['2021-2022', '2022-2023', '2023-2024', '2024-2025'];
const TARGET_CATEGORIES = new Set([
  'Lockdowns and Modified Programs',
  'Number of Deaths',
  'Overtime Hours',
]);
// Full fiscal year: Jul through Jun (12 months)
const MONTH_NAMES = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];

// Known CDCR institution identifiers — used to anchor forward-fill.
// Only update lastInst when col[0] is one of these (case-insensitive prefix match or exact code).
const KNOWN_INSTITUTIONS = new Set([
  'ASP', 'CAC', 'CAL', 'CCC', 'CCI', 'CCWF', 'CEN', 'CHCF', 'CIM', 'CIW',
  'CMC', 'CMF', 'COR', 'CRC', 'CTF', 'CVSP', 'DVI', 'FOL', 'FSP', 'FWF',
  'HDSP', 'ISP', 'KVSP', 'LAC', 'MCSP', 'NKSP', 'PBSP', 'PVSP', 'RJD',
  'SAC', 'SATF', 'SCC', 'SOL', 'SQ', 'SQRC', 'SVSP', 'VSP', 'WSP',
]);

// Return true if val looks like a CDCR institution identifier (code or full name containing code)
function isInstitutionHeader(val) {
  if (!val) return false;
  const upper = val.trim().toUpperCase();
  // Direct code match
  if (KNOWN_INSTITUTIONS.has(upper)) return true;
  // Full name containing a known code in parens, e.g. "Avenal State Prison (ASP)"
  for (const code of KNOWN_INSTITUTIONS) {
    if (upper.includes(`(${code})`)) return true;
  }
  // Common full-name prefixes
  const PREFIXES = [
    'AVENAL', 'CALIPATRIA', 'CALIFORNIA', 'CENTINELA', 'CENTRAL', 'CHUCKAWALLA',
    'CORRECTIONAL', 'DEUEL', 'FOLSOM', 'HIGH DESERT', 'IRONWOOD', 'KERN VALLEY',
    'MULE CREEK', 'NORTH KERN', 'PELICAN BAY', 'PLEASANT VALLEY', 'RICHARD J',
    'SALINAS', 'SUBSTANCE', 'SIERRA', 'SAN QUENTIN', 'SVSP', 'VALLEY', 'WASCO',
  ];
  for (const p of PREFIXES) {
    if (upper.startsWith(p)) return true;
  }
  return false;
}

async function ss(page, name) {
  const p = `/tmp/sb601ops_${name}.png`;
  await page.screenshot({ path: p, fullPage: true });
  console.log(`  Screenshot: ${p}`);
}

async function getCenter(page, searchTerms) {
  return await page.evaluate((terms) => {
    function find(root) {
      for (const el of root.querySelectorAll('*')) {
        const aria = (el.getAttribute('aria-label') || '').toLowerCase();
        const title = (el.getAttribute('title') || '').toLowerCase();
        const text = (el.textContent || '').trim().toLowerCase();
        for (const term of terms) {
          const t = term.toLowerCase();
          if (aria.includes(t) || title.includes(t) || text === t) {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) {
              return { x: r.x + r.width / 2, y: r.y + r.height / 2, tag: el.tagName, aria: el.getAttribute('aria-label'), text: (el.textContent || '').trim().slice(0, 60) };
            }
          }
        }
        if (el.shadowRoot) {
          const found = find(el.shadowRoot);
          if (found) return found;
        }
      }
      return null;
    }
    return find(document);
  }, searchTerms);
}

async function mouseClick(page, searchTerms, label) {
  console.log(`  Clicking: ${label}`);
  const box = await getCenter(page, searchTerms);
  if (box) {
    console.log(`    Found <${box.tag}> aria="${box.aria}" text="${box.text}" at (${Math.round(box.x)}, ${Math.round(box.y)})`);
    await page.mouse.move(box.x, box.y);
    await page.waitForTimeout(300);
    await page.mouse.click(box.x, box.y);
    return true;
  }
  console.warn(`    Not found: ${label}`);
  return false;
}

async function selectCombobox(page, comboboxAriaTerms, optionText) {
  console.log(`  Selecting combobox: "${optionText}"`);
  const opened = await mouseClick(page, comboboxAriaTerms, `combobox for ${optionText}`);
  if (!opened) return false;
  await page.waitForTimeout(1500);
  const clicked = await mouseClick(page, [optionText], `option "${optionText}"`);
  if (!clicked) {
    console.warn(`    Option "${optionText}" not found`);
    return false;
  }
  await page.waitForTimeout(500);
  return true;
}

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
    const rows = grid.querySelectorAll('[role="row"]');
    const result = [];
    for (const row of rows) {
      const cells = row.querySelectorAll('[role="rowheader"], [role="columnheader"], [role="gridcell"]');
      const r = Array.from(cells).map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '));
      if (r.length > 0 && r.some(v => v)) result.push(r);
    }
    return result;
  });
}

async function focusTable(page) {
  // Click directly on the grid to give it focus.
  // Do NOT press Enter — that would drill into a Power BI nav group and change the view.
  const gridBox = await page.evaluate(() => {
    function findGrid(root) {
      const g = root.querySelector('[role="grid"]');
      if (g) return g;
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = findGrid(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    const grid = findGrid(document);
    if (!grid) return null;
    const r = grid.getBoundingClientRect();
    if (r.width < 100) return null;
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  });
  if (gridBox) {
    await page.mouse.click(gridBox.x, gridBox.y);
    await page.waitForTimeout(500);
  }
}

// Scroll the grid to the top using a large upward wheel scroll (same mechanism as
// the downward scroll, which reliably moves the Power BI virtual list).
async function scrollGridToTop(page) {
  const gridBox = await page.evaluate(() => {
    function findGrid(root) {
      const g = root.querySelector('[role="grid"]');
      if (g) return g;
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = findGrid(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    const grid = findGrid(document);
    if (!grid) return null;
    const r = grid.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  });
  if (gridBox) {
    await page.mouse.move(gridBox.x, gridBox.y);
    // Large upward wheel to ensure we reach the absolute top regardless of current position.
    await page.mouse.wheel(0, -50000);
    await page.waitForTimeout(1200);
    // Second pass in case the first didn't fully reach row 1.
    await page.mouse.wheel(0, -50000);
    await page.waitForTimeout(800);
  }
  // Backup: keyboard Ctrl+Home
  await focusTable(page);
  await page.keyboard.press('Control+Home');
  await page.waitForTimeout(800);
}

async function scrollGrid(page) {
  // Find the grid and mouse-wheel scroll it downward.
  // Keyboard PageDown requires focus that may not persist; mouse wheel is more reliable.
  const gridBox = await page.evaluate(() => {
    function findGrid(root) {
      const g = root.querySelector('[role="grid"]');
      if (g) return g;
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = findGrid(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    const grid = findGrid(document);
    if (!grid) return null;
    const r = grid.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  });
  if (gridBox) {
    await page.mouse.move(gridBox.x, gridBox.y);
    // Use small increment (100px ≈ 2-3 rows) so no institution header row is ever skipped.
    await page.mouse.wheel(0, 100);
  } else {
    // Fallback: keyboard ArrowDown
    await page.keyboard.press('ArrowDown');
  }
  await page.waitForTimeout(300);
}

// Extract all rows from the wide-format Institution Totals matrix.
//
// The grid has columns: Institution | Category | Metric | Jul-22 | Aug-22 | ... | Jun-23
// Months appear as column headers with year suffix (e.g. "Jul-22").
// Rows use forward-fill: Institution and Category only appear in group header rows;
// data rows have empty col[0]/col[1].
//
// Key fixes vs. original:
//   - Dedup by (inst, cat, met) identity — not row content — so institution header
//     rows are not falsely deduplicated when Power BI re-renders the virtual list.
//   - lastInst/lastCat persist across scroll steps (defined outside addRows) so
//     mid-scroll pages without a visible institution header still get attributed
//     to the correct institution.
//   - lastInst only updates for known institution identifiers (isInstitutionHeader).
//   - Stall threshold: 100 no-new-record steps (100px scroll each).
async function extractTable(page) {
  // (inst, cat, met) -> wide row array — keeps first seen occurrence
  const byKey = new Map();

  // Persist across scroll steps
  let lastInst = '';
  let lastCat = '';

  const addRows = (rows) => {
    for (const row of rows) {
      if (row[0] && isInstitutionHeader(row[0])) lastInst = row[0].trim();
      if (row[1] && !/^\d/.test(row[1].trim()) && row[1].trim() !== 'Institution' && row[1].trim() !== 'Category') {
        lastCat = row[1].trim();
      }
      const inst = lastInst || row[0];
      const cat  = lastCat  || row[1];
      const met  = (row[2] || '').trim();
      if (!inst || !cat || !met) continue;
      const key = `${inst}|${cat}|${met}`;
      if (!byKey.has(key)) {
        byKey.set(key, [inst, cat, met, ...row.slice(3)]);
      }
    }
  };

  addRows(await extractVisibleRows(page));

  let noNewCount = 0;
  for (let i = 0; i < 2000; i++) {
    const before = byKey.size;
    await scrollGrid(page);
    await page.waitForTimeout(200);
    addRows(await extractVisibleRows(page));
    if (byKey.size === before) {
      noNewCount++;
      if (i % 50 === 0) console.log(`    Scroll ${i}: ${byKey.size} records (stalled ${noNewCount})`);
      if (noNewCount >= 100) break;
    } else {
      noNewCount = 0;
      if (i % 50 === 0) console.log(`    Scroll ${i}: ${byKey.size} records`);
    }
  }

  console.log(`    Total unique records: ${byKey.size}`);
  return Array.from(byKey.values());
}


function toCsv(rows) {
  return rows.map(row =>
    row.map(v => (v !== null && v !== undefined && /[,"\n]/.test(String(v)))
      ? `"${String(v).replace(/"/g, '""')}"` : String(v ?? '')).join(',')
  ).join('\n');
}

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const allData = [];

  try {
    console.log('Loading dashboard...');
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(8000);

    console.log('\nNavigating to Programs...');
    await mouseClick(page, ['Programs'], 'Programs tile');
    await page.waitForTimeout(8000);

    console.log('\nClicking Data Tables...');
    await mouseClick(page, ['Click to view Data Tables', 'Data Tables'], 'Data Tables');
    await page.waitForTimeout(8000);

    console.log('\nClicking Institution Totals...');
    await mouseClick(page, ['Click to view Institution Totals', 'Institution Totals'], 'Institution Totals');
    await page.waitForTimeout(8000);
    await ss(page, '01_institution_totals');

    for (const fy of FISCAL_YEARS) {
      console.log(`\n${'─'.repeat(60)}`);
      console.log(`Fiscal Year: ${fy}`);
      console.log('─'.repeat(60));

      await selectCombobox(page, ['Fiscal Year'], fy);
      await page.waitForTimeout(5000); // increased from 3000ms — allow full re-render

      // FIX: scroll grid to top before extracting, so we start from row 1
      await scrollGridToTop(page);
      await ss(page, `02_fy_${fy.replace('-', '_')}`);

      const rawRows = await extractTable(page);

      // rawRows are already processed as [inst, cat, met, ...monthValues].
      // No header row exists in this output — use MONTH_NAMES directly.
      let kept = 0;
      for (const row of rawRows) {
        const institution = row[0];
        const category = row[1];
        const metric = row[2];
        if (!institution || !category || !metric) continue;
        if (!TARGET_CATEGORIES.has(category)) continue;

        const values = row.slice(3);
        const outRow = { institution, fiscal_year: fy, category, metric };
        MONTH_NAMES.forEach((m, i) => { outRow[m] = values[i] ?? ''; });
        allData.push(outRow);
        kept++;
      }
      console.log(`  Kept ${kept} rows for ${fy}`);
    }

    if (allData.length === 0) {
      console.warn('\nNo data collected.');
    } else {
      const csvHeader = ['institution', 'fiscal_year', 'category', 'metric', ...MONTH_NAMES];
      const csvRows = [csvHeader, ...allData.map(r => csvHeader.map(k => r[k] ?? ''))];
      fs.writeFileSync(OUT_PATH, toCsv(csvRows), 'utf8');
      console.log(`\nSaved ${allData.length} rows to: ${OUT_PATH}`);
      allData.slice(0, 3).forEach(r => console.log(' ', JSON.stringify(r)));
    }

  } catch (err) {
    console.error('Fatal:', err.message);
    await page.screenshot({ path: '/tmp/sb601ops_error.png', fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }
})();
