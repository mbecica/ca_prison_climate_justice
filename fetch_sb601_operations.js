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
const OUT_PATH = path.join(__dirname, 'data_sources', 'facilities', 'CDCR', 'sb601_operations_2021-2025.csv');

const FISCAL_YEARS = ['2021-2022', '2022-2023', '2023-2024', '2024-2025'];
const TARGET_CATEGORIES = new Set([
  'Lockdowns and Modified Programs',
  'Number of Deaths',
  'Overtime Hours',
]);
// Generic month names in fiscal-year order (Jul = start of CA fiscal year)
const MONTH_NAMES = ['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar', 'Apr'];

async function ss(page, name) {
  const p = `/tmp/sb601ops_${name}.png`;
  await page.screenshot({ path: p, fullPage: true });
  console.log(`  Screenshot: ${p}`);
}

// Find center coordinates of an element matching aria-label, title, or exact text
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
  const gridGroup = await page.evaluate(() => {
    function find(root) {
      for (const el of root.querySelectorAll('[role="group"]')) {
        const text = (el.textContent || '').trim();
        if (text.startsWith('Press Enter to explore data')) {
          const r = el.getBoundingClientRect();
          if (r.width > 100) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
      }
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    return find(document);
  });
  if (gridGroup) {
    await page.mouse.click(gridGroup.x, gridGroup.y);
    await page.waitForTimeout(500);
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);
  }
}

async function scrollGrid(page) {
  await page.mouse.move(727, 464);
  await page.mouse.wheel(0, 300);
  await page.waitForTimeout(200);
  await page.evaluate(() => {
    function find(root) {
      for (const el of root.querySelectorAll('button')) {
        if ((el.textContent || '').trim() === 'Scroll down') { el.click(); return true; }
      }
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      return false;
    }
    find(document);
  });
  return { atBottom: false };
}

async function extractTable(page) {
  const seen = new Set();
  const allRows = [];
  const addRows = (rows) => {
    for (const row of rows) {
      const key = row.join('|');
      if (!seen.has(key)) { seen.add(key); allRows.push(row); }
    }
  };

  addRows(await extractVisibleRows(page));

  let noNewCount = 0;
  for (let i = 0; i < 200; i++) {
    const before = allRows.length;
    await scrollGrid(page);
    await page.waitForTimeout(700);
    addRows(await extractVisibleRows(page));
    if (allRows.length === before) {
      noNewCount++;
      if (i % 10 === 0) console.log(`    Scroll ${i}: ${allRows.length} rows (stalled ${noNewCount})`);
      if (noNewCount >= 8) break;
    } else {
      noNewCount = 0;
      if (i % 10 === 0) console.log(`    Scroll ${i}: ${allRows.length} rows`);
    }
  }

  console.log(`    Total unique rows: ${allRows.length}`);
  if (allRows.length === 0) return [];

  // Forward-fill Institution and Category
  let lastInst = '', lastCat = '';
  return allRows.map(row => {
    if (row[0] && !/^\d/.test(row[0].trim())) lastInst = row[0];
    if (row[1] && !/^\d/.test(row[1].trim())) lastCat = row[1];
    return [lastInst || row[0], lastCat || row[1], ...row.slice(2)];
  });
}

// Parse a header row like ["Institution","Category","Metric","Jul-24","Aug-24",...]
// and return the indices and month mapping
function parseHeaderRow(rows) {
  // Find the row that has "Institution" and "Category" — skip the quarter label row
  for (let i = 0; i < rows.length; i++) {
    const r = rows[i];
    if (r[0] === 'Institution' && r[1] === 'Category') {
      // Map month columns: "Jul-24" -> "Jul", "Aug-24" -> "Aug", etc.
      const months = r.slice(3).map(h => h.replace(/-\d{2}$/, ''));
      return { headerIdx: i, months };
    }
  }
  return null;
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
  const allData = []; // accumulated rows across all fiscal years

  try {
    // ── 1. Load and navigate to Institution Totals ─────────────────────────────
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

    // ── 2. Loop over fiscal years ──────────────────────────────────────────────
    for (const fy of FISCAL_YEARS) {
      console.log(`\n${'─'.repeat(60)}`);
      console.log(`Fiscal Year: ${fy}`);
      console.log('─'.repeat(60));

      await selectCombobox(page, ['Fiscal Year'], fy);
      await page.waitForTimeout(3000); // wait for table to re-render

      await focusTable(page);
      await ss(page, `02_fy_${fy.replace('-', '_')}`);

      const rawRows = await extractTable(page);

      // Skip header rows (Quarter label row + column header row) and filter categories
      const header = parseHeaderRow(rawRows);
      if (!header) {
        console.warn(`  Could not find header row for ${fy}`);
        continue;
      }

      const { headerIdx, months } = header;
      const dataRows = rawRows.slice(headerIdx + 1);

      let kept = 0;
      for (const row of dataRows) {
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

    // ── 3. Write CSV ───────────────────────────────────────────────────────────
    if (allData.length === 0) {
      console.warn('\nNo data collected.');
    } else {
      const csvHeader = ['institution', 'fiscal_year', 'category', 'metric', ...MONTH_NAMES];
      const csvRows = [csvHeader, ...allData.map(r => csvHeader.map(k => r[k] ?? ''))];
      fs.writeFileSync(OUT_PATH, toCsv(csvRows), 'utf8');
      console.log(`\nSaved ${allData.length} rows to: ${OUT_PATH}`);
      // Preview
      allData.slice(0, 3).forEach(r => console.log(' ', JSON.stringify(r)));
    }

  } catch (err) {
    console.error('Fatal:', err.message);
    await page.screenshot({ path: '/tmp/sb601ops_error.png', fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }
})();
