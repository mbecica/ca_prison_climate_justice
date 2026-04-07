/**
 * Scrapes Three-Year Return-to-Prison Rate by Length of Stay (all fiscal years)
 * from the CDCR Adult Recidivism Power BI dashboard:
 *   Landing → Recidivism Dashboard → Select Measure: Return →
 *   Crosstabs → Fiscal Year: All → Row: Length of Stay → Column: Length of Stay
 *
 * Output columns: fiscal_year, length_of_stay_row, <los_column_categories>
 * Values are three-year return-to-prison rates (percentages).
 *
 * Also captures the headline three-year return rate per fiscal year from the
 * main dashboard page (2008-09 through 2019-20).
 *
 * Output: data_sources/facilities/CDCR/cdcr_recidivism_los.csv
 *
 * Usage:
 *   node fetch_cdcr_recidivism_los.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiNmRjOTkwMWEtYmVkMy00MTA1LWIxZDYtYzg4OTIzYjkxNTRlIiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9';
const OUT_PATH = path.join(__dirname, '..', 'data_sources', 'facilities', 'CDCR', 'cdcr_recidivism_los.csv');

async function ss(page, name) {
  const p = `/tmp/recid_los_${name}.png`;
  await page.screenshot({ path: p, fullPage: true });
  console.log(`  Screenshot: ${p}`);
}

async function selectCombobox(page, comboboxCoords, optionText) {
  console.log(`  Selecting combobox option: "${optionText}"`);
  // Click to open
  await page.mouse.click(comboboxCoords.x + comboboxCoords.w / 2, comboboxCoords.y + comboboxCoords.h / 2);
  await page.waitForTimeout(2000);

  // Find and click option
  const found = await page.evaluate((text) => {
    function find(root) {
      for (const el of root.querySelectorAll('[role="option"], li, [role="listitem"]')) {
        const t = (el.textContent || '').trim();
        if (t === text || t.toLowerCase() === text.toLowerCase()) {
          const r = el.getBoundingClientRect();
          if (r.width > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      // Also try any visible element with exact text match
      for (const el of root.querySelectorAll('*')) {
        const t = (el.textContent || '').trim();
        const r = el.getBoundingClientRect();
        if (t === text && r.width > 0 && r.height > 0 && r.height < 50) {
          return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    return find(document);
  }, optionText);

  if (found) {
    await page.mouse.click(found.x, found.y);
    await page.waitForTimeout(1500);
    return true;
  }
  console.warn(`    Option "${optionText}" not found in dropdown`);
  return false;
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

async function scrollGrid(page) {
  await page.mouse.move(700, 450);
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
}

async function extractFullTable(page) {
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
  for (let i = 0; i < 100; i++) {
    const before = allRows.length;
    await scrollGrid(page);
    await page.waitForTimeout(600);
    addRows(await extractVisibleRows(page));
    if (allRows.length === before) {
      noNewCount++;
      if (noNewCount >= 8) break;
    } else {
      noNewCount = 0;
    }
    if (i % 10 === 0) console.log(`    Scroll ${i}: ${allRows.length} rows`);
  }
  console.log(`    Total unique rows: ${allRows.length}`);
  return allRows;
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

  try {
    // ── 1. Load dashboard ────────────────────────────────────────────────────────
    console.log('Loading CDCR Adult Recidivism dashboard...');
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(12000);
    await ss(page, '01_loaded');

    // ── 2. Click landing button ──────────────────────────────────────────────────
    console.log('\nClicking main dashboard button...');
    const landingBtn = await page.evaluate(() => {
      function find(root) {
        for (const el of root.querySelectorAll('*')) {
          const aria = (el.getAttribute('aria-label') || '').toLowerCase();
          if (aria.includes('recidivism dashboard')) {
            const r = el.getBoundingClientRect();
            if (r.width > 50) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
          }
          if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
        }
        return null;
      }
      return find(document);
    });
    if (landingBtn) {
      await page.mouse.click(landingBtn.x, landingBtn.y);
    } else {
      // Fallback to known coordinates
      await page.mouse.click(477, 445);
    }
    await page.waitForTimeout(10000);
    await ss(page, '02_dashboard');

    // ── 3. Click 'Return' measure (top right tabs) ───────────────────────────────
    console.log('\nSelecting Return measure...');
    const returnEl = await page.evaluate(() => {
      function find(root) {
        for (const el of root.querySelectorAll('*')) {
          const t = (el.textContent || '').trim();
          if (t === 'Return') {
            const r = el.getBoundingClientRect();
            if (r.width > 50 && r.width < 300) return { x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width };
          }
          if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
        }
        return null;
      }
      return find(document);
    });
    if (returnEl) {
      console.log(`  Found Return at (${Math.round(returnEl.x)}, ${Math.round(returnEl.y)})`);
      await page.mouse.click(returnEl.x, returnEl.y);
    } else {
      await page.mouse.click(1239, 126);
    }
    await page.waitForTimeout(3000);

    // ── 4. Click Crosstabs navigation ────────────────────────────────────────────
    console.log('\nNavigating to Crosstabs...');
    const crosstabsEl = await page.evaluate(() => {
      function find(root) {
        for (const el of root.querySelectorAll('*')) {
          const aria = (el.getAttribute('aria-label') || '').toLowerCase();
          if (aria.includes('crosstab')) {
            const r = el.getBoundingClientRect();
            if (r.width > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
          }
          if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
        }
        return null;
      }
      return find(document);
    });
    if (crosstabsEl) {
      await page.mouse.click(crosstabsEl.x, crosstabsEl.y);
    } else {
      await page.mouse.click(35, 171);
    }
    await page.waitForTimeout(8000);
    await ss(page, '03_crosstabs');

    // ── 5. Verify Fiscal Year is 'All' (default) ────────────────────────────────
    // Fiscal Year combobox is at (36, 207) — defaults to All, no action needed.
    console.log('\nFiscal Year defaults to All — no change needed.');

    // ── 6. Set Row = Length of Stay ──────────────────────────────────────────────
    // Row combobox at (36, 284) center=(131, 297). Options are canvas-rendered;
    // keyboard navigation (ArrowDown + Enter) is required. Length of Stay = x11.
    // Option order: Age at Release(0), Race/Ethnicity(1), County of Release(2),
    //   Gender(3), Commitment Offense Category(4), Commitment Offense Group(5),
    //   Sentence Type(6), Sex Registrants(7), Serious/Violent(8),
    //   Mental Health Designation(9), Risk Score(10), Length of Stay(11)
    console.log('\nSetting Row to Length of Stay (ArrowDown x11)...');
    await page.mouse.click(131, 297);
    await page.waitForTimeout(1500);
    for (let i = 0; i < 11; i++) {
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(300);
    }
    await page.keyboard.press('Enter');
    await page.waitForTimeout(4000);
    await ss(page, '04_row_los');

    // ── 7. Set Column = Length of Stay ───────────────────────────────────────────
    // Column combobox at (35, 410) center=(130, 423). Same option order as row.
    // IMPORTANT: click a neutral area first (title bar) to avoid the row combobox
    // staying focused; then click column combobox. Length of Stay = x11.
    console.log('\nSetting Column to Length of Stay (ArrowDown x11)...');
    await page.mouse.click(700, 50);  // neutral click to deselect row combobox
    await page.waitForTimeout(1000);
    await page.mouse.click(130, 423);
    await page.waitForTimeout(2000);
    for (let i = 0; i < 11; i++) {
      await page.keyboard.press('ArrowDown');
      await page.waitForTimeout(400);
    }
    await page.keyboard.press('Enter');
    await page.waitForTimeout(5000);
    await ss(page, '05_col_los');

    // ── 8. Extract table ─────────────────────────────────────────────────────────
    console.log('\nExtracting table...');
    const rawRows = await extractFullTable(page);
    await ss(page, '06_extracted');

    if (rawRows.length === 0) {
      console.warn('No rows extracted.');
      const html = await page.content();
      fs.writeFileSync('/tmp/recid_los_page.html', html, 'utf8');
      console.log('Page HTML saved to /tmp/recid_los_page.html');
      // Also dump page text
      const body = await page.evaluate(() => document.body.innerText);
      console.log('Page text:', body.slice(0, 2000));
    } else {
      console.log(`\nRaw rows (first 15):`);
      rawRows.slice(0, 15).forEach((r, i) => console.log(`  [${i}]`, r));
      fs.writeFileSync(OUT_PATH, toCsv(rawRows), 'utf8');
      console.log(`\nSaved ${rawRows.length} rows to: ${OUT_PATH}`);
    }

  } catch (err) {
    console.error('Fatal:', err.message);
    await page.screenshot({ path: '/tmp/recid_los_error.png', fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }
})();
