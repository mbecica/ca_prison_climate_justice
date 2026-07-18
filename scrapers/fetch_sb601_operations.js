/**
 * Scrapes Institution Totals for four operational categories across all fiscal years
 * from the SB 601 Programs Power BI dashboard:
 *   - Lockdowns and Modified Programs
 *   - Number of Deaths
 *   - Overtime Hours
 *   - Use of Force
 *
 * Output columns: institution, fiscal_year, category, metric, Jul, Aug, Sep, Oct, Nov, Dec, Jan, Feb, Mar, Apr, May, Jun
 *
 * Two-pass horizontal extraction:
 *   Pass 1 (left):  captures Jul–Apr (columns visible at default scroll position)
 *   Pass 2 (right): scrolled right to reveal May–Jun; merges those values into pass-1 rows
 *
 * Usage:
 *   node fetch_sb601_operations.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiYzlkM2RiNWEtZDRjMi00ODllLTg2YzEtZjYyM2MwMjA5NmQ0IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9&pageName=5a926528bbf7e48d60c2';
const OUT_PATH = path.join(__dirname, '..', 'data_sources', 'facilities', 'CDCR', 'sb601_operations.csv');
// To add a year at refresh time, append it to FISCAL_YEARS below — the filename is stable. See REFRESH.md.

const FISCAL_YEARS = ['2021-2022', '2022-2023', '2023-2024', '2024-2025'];
const TARGET_CATEGORIES = new Set([
  'Lockdowns and Modified Programs',
  'Number of Deaths',
  'Overtime Hours',
  'Use of Force (UOF)',
  'Fiscal',
]);
// Full fiscal year: Jul through Jun (12 months)
const MONTH_NAMES = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'];

// Month abbreviation -> canonical name (strips year suffix, e.g. "Jul-22" -> "Jul")
function parseMonthHeader(h) {
  if (!h) return null;
  const clean = h.trim();
  // "Jul-22", "Aug-22", etc. — strip suffix
  const m = clean.match(/^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i);
  if (!m) return null;
  const name = m[1].charAt(0).toUpperCase() + m[1].slice(1).toLowerCase();
  return MONTH_NAMES.includes(name) ? name : null;
}

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

// Scroll the grid horizontally to the leftmost position.
async function scrollGridToLeft(page) {
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
    // Large leftward wheel scroll (negative x)
    await page.mouse.wheel(-50000, 0);
    await page.waitForTimeout(1000);
    await page.mouse.wheel(-50000, 0);
    await page.waitForTimeout(800);
  }
}

// Scroll the grid horizontally to the rightmost position.
async function scrollGridToRight(page) {
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
    // Large rightward wheel scroll (positive x)
    await page.mouse.wheel(50000, 0);
    await page.waitForTimeout(1000);
    await page.mouse.wheel(50000, 0);
    await page.waitForTimeout(800);
  }
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

// Read column headers from the currently visible grid position.
// Returns an array of month names (or null for non-month columns) indexed by cell position.
// Positions 0,1,2 are always Institution, Category, Metric (fixed).
// Positions 3+ are month columns — header text like "Jul-22" -> "Jul".
//
// The Institution Totals table has a two-level header:
//   Row 1 (grouping): "", "", "Quarter", "Q1", "Q1", "Q1", "Q2", ...
//   Row 2 (months):   "", "", "Metric",  "Jul-22", "Aug-22", "Sep-22", ...
// We prefer the row that contains actual month abbreviations.
async function getVisibleColumnHeaders(page) {
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
    const monthRe = /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i;
    const rows = grid.querySelectorAll('[role="row"]');
    let firstHeaderRow = null;
    for (const row of rows) {
      const headers = row.querySelectorAll('[role="columnheader"]');
      if (headers.length === 0) continue;
      const texts = Array.from(headers).map(h => (h.innerText || h.textContent || '').trim().replace(/\s+/g, ' '));
      // Prefer the row that contains at least one month abbreviation
      if (texts.some(t => monthRe.test(t))) return texts;
      if (!firstHeaderRow) firstHeaderRow = texts;
    }
    // Fallback: return the first header row found
    return firstHeaderRow || [];
  });
}

// One vertical pass: scroll from top to bottom, collecting rows.
// Returns a map of key -> { inst, cat, met, monthVals: { [monthName]: value } }
// where monthVals are keyed by month name using the provided colHeaders array.
async function collectPass(page, colHeaders, passLabel) {
  console.log(`  [${passLabel}] Collecting rows with headers: ${JSON.stringify(colHeaders)}`);

  // Map cell position (0-based from row start) to month name
  // Positions 0,1,2 = Institution, Category, Metric (fixed cols)
  // Positions 3+ = month cols based on headers[3+]
  const posToMonth = {};
  for (let i = 3; i < colHeaders.length; i++) {
    const mn = parseMonthHeader(colHeaders[i]);
    if (mn) posToMonth[i] = mn;
  }
  console.log(`  [${passLabel}] Month positions: ${JSON.stringify(posToMonth)}`);

  const byKey = new Map(); // key -> { inst, cat, met, monthVals }
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
        byKey.set(key, { inst, cat, met, monthVals: {} });
      }
      const entry = byKey.get(key);
      // Fill in month values from visible positions (don't overwrite already-set values)
      for (const [pos, monthName] of Object.entries(posToMonth)) {
        const cellIdx = parseInt(pos);
        if (cellIdx < row.length) {
          const val = (row[cellIdx] || '').trim();
          if (!(monthName in entry.monthVals) || entry.monthVals[monthName] === '') {
            entry.monthVals[monthName] = val;
          }
        }
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
      if (i % 50 === 0) console.log(`    [${passLabel}] Scroll ${i}: ${byKey.size} records (stalled ${noNewCount})`);
      if (noNewCount >= 100) break;
    } else {
      noNewCount = 0;
      if (i % 50 === 0) console.log(`    [${passLabel}] Scroll ${i}: ${byKey.size} records`);
    }
  }

  console.log(`    [${passLabel}] Total unique records: ${byKey.size}`);
  return byKey;
}

// Extract all rows from the wide-format Institution Totals matrix using two passes:
//   Pass 1 (left):  grid at default scroll (Jul–Apr visible)
//   Pass 2 (right): grid scrolled right (May–Jun visible)
// Results are merged: pass-2 fills in month values missing from pass-1.
async function extractTable(page) {
  // --- Pass 1: left position (Jul–Apr) ---
  await scrollGridToTop(page);
  await scrollGridToLeft(page);
  await scrollGridToTop(page);
  await page.waitForTimeout(500);

  const headers1 = await getVisibleColumnHeaders(page);
  console.log(`  Pass 1 headers: ${JSON.stringify(headers1)}`);
  await ss(page, 'pass1_headers');

  const pass1 = await collectPass(page, headers1, 'Pass1');

  // --- Pass 2: right position (May–Jun) ---
  // Scroll grid back to top first, then scroll horizontally right
  await scrollGridToTop(page);
  await scrollGridToRight(page);
  await scrollGridToTop(page);
  await page.waitForTimeout(500);

  const headers2 = await getVisibleColumnHeaders(page);
  console.log(`  Pass 2 headers: ${JSON.stringify(headers2)}`);
  await ss(page, 'pass2_headers');

  const pass2 = await collectPass(page, headers2, 'Pass2');

  // --- Merge pass2 into pass1 ---
  // For keys in pass2, fill in any month values not already captured in pass1.
  // Also add keys that only appear in pass2 (shouldn't happen but be safe).
  for (const [key, entry2] of pass2) {
    if (pass1.has(key)) {
      const entry1 = pass1.get(key);
      for (const [month, val] of Object.entries(entry2.monthVals)) {
        if (!(month in entry1.monthVals) || entry1.monthVals[month] === '') {
          entry1.monthVals[month] = val;
        }
      }
    } else {
      pass1.set(key, entry2);
    }
  }

  console.log(`    Total unique records after merge: ${pass1.size}`);

  // Convert map to array in [inst, cat, met, Jul, Aug, ..., Jun] format
  const result = [];
  for (const { inst, cat, met, monthVals } of pass1.values()) {
    const monthArray = MONTH_NAMES.map(m => monthVals[m] ?? '');
    result.push([inst, cat, met, ...monthArray]);
  }
  return result;
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

      // rawRows are already processed as [inst, cat, met, Jul, Aug, ..., Jun].
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
