/**
 * Scrapes selected measures from the CCHCS Health Care Services Dashboard
 * for every available month (Jan 2017–Dec 2025, 108 months):
 *
 *   Staffing:    Actual Vacancies (All), Medical Vacancies (All),
 *                Mental Health Vacancies (All), Dental Vacancies (All)
 *   Major Costs: Total Labor Cost (All), ED & Hospital Stays
 *   Other Trends: ED/Hospital Stay*
 *
 * Output: long-format CSV — month, group, institution, measure, value
 * Saved to: data_sources/facilities/CDCR/cchcs_measures_2017-2025.csv
 *
 * Checkpoint: /tmp/cchcs_measures_checkpoint.json  (delete to re-scrape)
 *
 * Usage:
 *   node scrapers/fetch_cchcs_measures.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiY2QyNzllZWItMmIxYi00NTk0LWI0OWQtNWEzMTkwYzA3NGE4IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9';
const OUT_PATH = path.join(__dirname, '..', 'data_sources', 'facilities', 'CDCR', 'cchcs_measures_2017-2025.csv');
const CHECKPOINT_PATH = '/tmp/cchcs_measures_checkpoint.json';

// Each group: treeItem is the exact text to click in the Domain dropdown.
// keepMeasures: only these row labels are saved (all others are read but discarded).
// Each group gets its own page load to avoid multi-select state accumulation.
const MEASURE_GROUPS = [
  {
    name: 'Staffing',
    treeItem: 'Staffing',
    keepMeasures: new Set([
      'Actual Vacancies (All)',
      'Medical Vacancies (All)',
      'Mental Health Vacancies (All)',
      'Dental Vacancies (All)',
    ]),
  },
  {
    name: 'Major Costs',
    treeItem: 'Major Costs per patient per Month',
    keepMeasures: new Set([
      'Total Labor Cost (All)',
      'ED & Hospital Stays',
    ]),
  },
  {
    name: 'Other Trends',
    treeItem: 'Other Trends',
    keepMeasures: new Set([
      'ED/Hospital Stay*',
    ]),
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────────

async function ss(page, name) {
  await page.screenshot({ path: `/tmp/cchcs_measures_${name}.png` });
  console.log(`  Screenshot: /tmp/cchcs_measures_${name}.png`);
}

async function getCombobox(page, ariaLabel) {
  return await page.evaluate((label) => {
    function find(root) {
      for (const el of root.querySelectorAll('[role="combobox"]')) {
        if ((el.getAttribute('aria-label') || '').toLowerCase().includes(label.toLowerCase())) {
          const r = el.getBoundingClientRect();
          if (r.width > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
      }
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    return find(document);
  }, ariaLabel);
}

async function selectTreeItem(page, targetText, dropdownX = 998) {
  for (let i = 0; i < 80; i++) {
    const found = await page.evaluate((t) => {
      for (const el of document.querySelectorAll('[role="treeitem"]')) {
        if ((el.textContent || '').trim() === t) {
          const r = el.getBoundingClientRect();
          if (r.width > 0) { el.click(); return true; }
        }
      }
      return false;
    }, targetText);
    if (found) return true;
    await page.mouse.move(dropdownX, 300);
    await page.mouse.wheel(0, 200);
    await page.waitForTimeout(150);
  }
  return false;
}

function generateMonthList() {
  const names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const months = [];
  for (let year = 2025; year >= 2017; year--) {
    for (let m = 11; m >= 0; m--) {
      months.push(`${names[m]} ${year}`);
    }
  }
  return months; // 108 months, newest first
}

async function selectMonth(page, monthStr, positionIndex) {
  const dm = await getCombobox(page, 'Dashboard Month');
  await page.mouse.click(dm.x, dm.y);
  await page.waitForTimeout(1500);

  const setScrollTop = async (pos) => {
    await page.evaluate((p) => {
      const opts = document.querySelectorAll('[role="option"]');
      if (opts.length === 0) return;
      let el = opts[0];
      while (el && el !== document.body) {
        if (el.scrollHeight > el.clientHeight + 5) { el.scrollTop = p; return; }
        el = el.parentElement;
      }
    }, pos);
  };

  const getScrollInfo = async () => await page.evaluate(() => {
    const opts = document.querySelectorAll('[role="option"]');
    if (opts.length === 0) return { scrollTop: 0, maxScroll: 1900 };
    let el = opts[0];
    while (el && el !== document.body) {
      if (el.scrollHeight > el.clientHeight + 5)
        return { scrollTop: el.scrollTop, maxScroll: el.scrollHeight - el.clientHeight };
      el = el.parentElement;
    }
    return { scrollTop: 0, maxScroll: 1900 };
  });

  const tryClick = async () => await page.evaluate((target) => {
    for (const el of document.querySelectorAll('[role="option"]')) {
      if ((el.textContent || '').trim() === target) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) { el.click(); return true; }
      }
    }
    return false;
  }, monthStr);

  const dropCenter = await page.evaluate(() => {
    const opts = document.querySelectorAll('[role="option"]');
    if (opts.length === 0) return null;
    const r = opts[0].getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  });
  if (!dropCenter) {
    console.warn(`  Dropdown not open for: "${monthStr}"`);
    await page.keyboard.press('Escape');
    return false;
  }

  const { maxScroll } = await getScrollInfo();
  const targetScrollTop = Math.max(0, positionIndex * 21 - 90);
  const scanStart = Math.max(0, targetScrollTop - 300);
  const scanEnd = Math.min(targetScrollTop + 300, maxScroll);

  for (let pos = scanStart; pos <= scanEnd; pos += 60) {
    await setScrollTop(pos);
    await page.waitForTimeout(500);
    if (await tryClick()) return true;
  }

  if (targetScrollTop > maxScroll) {
    const extraChunks = Math.ceil((targetScrollTop - maxScroll) / 500) + 1;
    for (let c = 0; c < extraChunks; c++) {
      if (await tryClick()) return true;
      await page.mouse.move(dropCenter.x, dropCenter.y);
      await page.mouse.wheel(0, 500);
      await page.waitForTimeout(600);
    }
    if (await tryClick()) return true;
    const { scrollTop: base } = await getScrollInfo();
    for (let delta = -150; delta <= 150; delta += 30) {
      await setScrollTop(Math.max(0, base + delta));
      await page.waitForTimeout(400);
      if (await tryClick()) return true;
    }
  }

  console.warn(`  Could not find month: "${monthStr}"`);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  return false;
}

function cleanValue(raw) {
  return raw
    .replace(/\s*Additional Conditional Formatting\s*/g, '')
    .replace(/,/g, '')
    .trim();
}

// Extract all institution columns and all measure rows for the current month.
// Scrolls right to reveal hidden institution columns; reads all DOM rows at each
// scroll position (Power BI renders row elements even when scrolled off-screen
// vertically, so vertical scrolling is not needed).
async function extractAllInstitutions(page) {
  const result = {}; // { measure: { institution: value } }

  const gridCenter = await page.evaluate(() => {
    function find(root) {
      const g = root.querySelector('[role="grid"]');
      if (g) { const r = g.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; }
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    return find(document);
  });
  if (!gridCenter) return result;

  // Helper: read one snapshot of visible grid (institutions + rows)
  const readSnap = () => page.evaluate(() => {
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
    const headerRow = grid.querySelector('[role="row"]');
    const institutions = headerRow
      ? Array.from(headerRow.querySelectorAll('[role="columnheader"]'))
          .map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '))
          .filter(h => h !== 'Measures' && h.trim() !== '')
      : [];
    const dataRows = Array.from(grid.querySelectorAll('[role="row"]')).slice(1);
    const rows = dataRows.map(row => {
      const rh = row.querySelector('[role="rowheader"]');
      const measure = rh ? (rh.innerText || rh.textContent || '').trim().replace(/\s+/g, ' ') : '';
      const cells = Array.from(row.querySelectorAll('[role="gridcell"]'))
        .map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '));
      return { measure, values: cells };
    });
    return { institutions, rows };
  });

  // Reset to top-left
  for (let i = 0; i < 12; i++) {
    await page.mouse.move(gridCenter.x, gridCenter.y);
    await page.mouse.wheel(-500, 0);
  }
  for (let i = 0; i < 10; i++) {
    await page.mouse.move(gridCenter.x, gridCenter.y);
    await page.mouse.wheel(0, -500);
  }
  await page.waitForTimeout(500);

  // 2-D traversal: outer loop = scroll down to expose new rows,
  // inner loop = scroll right to expose new institution columns.
  const seenMeasures = new Set();
  let noNewRowsCount = 0;

  for (let vStep = 0; vStep < 15; vStep++) {
    // At this vertical position, sweep right across all institution columns
    const seenInstitutions = new Set();
    let noNewInstCount = 0;
    let visibleMeasures = new Set(); // measures visible at this v-position

    for (let hStep = 0; hStep < 20; hStep++) {
      const snap = await readSnap();
      if (!snap) break;

      let newInstitutions = 0;
      snap.institutions.forEach((inst, i) => {
        if (!seenInstitutions.has(inst)) {
          seenInstitutions.add(inst);
          newInstitutions++;
        }
        snap.rows.forEach(({ measure, values }) => {
          if (!measure) return;
          visibleMeasures.add(measure);
          const val = cleanValue(values[i] || '');
          if (!result[measure]) result[measure] = {};
          if (!(inst in result[measure])) {
            result[measure][inst] = val;
          }
        });
      });

      if (newInstitutions === 0) {
        noNewInstCount++;
        if (noNewInstCount >= 3) break;
      } else {
        noNewInstCount = 0;
      }

      await page.mouse.move(gridCenter.x, gridCenter.y);
      await page.mouse.wheel(300, 0);
      await page.waitForTimeout(500);
    }

    // Check if we saw any new row labels at this vertical position
    const newRows = [...visibleMeasures].filter(m => !seenMeasures.has(m));
    if (newRows.length === 0) {
      noNewRowsCount++;
      if (noNewRowsCount >= 3) break;
    } else {
      noNewRowsCount = 0;
      newRows.forEach(m => seenMeasures.add(m));
    }

    // Scroll back to left, then scroll down to reveal next batch of rows
    for (let i = 0; i < 15; i++) {
      await page.mouse.move(gridCenter.x, gridCenter.y);
      await page.mouse.wheel(-500, 0);
    }
    await page.waitForTimeout(200);
    await page.mouse.move(gridCenter.x, gridCenter.y);
    await page.mouse.wheel(0, 500);
    await page.waitForTimeout(400);
  }

  return result;
}

// ── CSV helpers ────────────────────────────────────────────────────────────────

function toCsvRow(cols) {
  return cols.map(v => {
    const s = String(v ?? '');
    return /[,"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }).join(',');
}

// ── Scrape one measure group across all months ─────────────────────────────────

async function scrapeGroup(group, targetMonths, checkpoint) {
  console.log(`\n${'═'.repeat(60)}`);
  console.log(`GROUP: ${group.name}  (tree item: "${group.treeItem}")`);
  console.log('═'.repeat(60));

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  try {
    console.log('Loading dashboard...');
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(10000);
    await ss(page, `${group.name.replace(/\s/g,'_')}_01_loaded`);

    // Select the measure group in the Domain dropdown
    console.log(`Selecting "${group.treeItem}"...`);
    const mc = await getCombobox(page, 'Domain, SubDomain, Element');
    await page.mouse.click(mc.x, mc.y);
    await page.waitForTimeout(1500);
    const selected = await selectTreeItem(page, group.treeItem);
    if (!selected) throw new Error(`Could not select: "${group.treeItem}"`);
    await page.waitForTimeout(4000);
    await ss(page, `${group.name.replace(/\s/g,'_')}_02_selected`);

    for (let mi = 0; mi < targetMonths.length; mi++) {
      const month = targetMonths[mi];
      const checkKey = `${group.name}:${month}`;

      if (checkpoint.done.includes(checkKey)) {
        if (mi % 12 === 0) console.log(`  [${mi+1}/${targetMonths.length}] ${month} — skipping`);
        continue;
      }

      console.log(`\n[${mi+1}/${targetMonths.length}] ${group.name} / ${month}`);

      const ok = await selectMonth(page, month, mi + 1);
      if (!ok) { console.warn(`  Skipping ${month}`); continue; }
      await page.waitForTimeout(2500);

      const data = await extractAllInstitutions(page);
      const institutions = Object.values(data)[0]
        ? Object.keys(Object.values(data)[0])
        : [];

      let rowCount = 0;
      for (const inst of institutions) {
        for (const [measure, instValues] of Object.entries(data)) {
          // Skip section-header rows and measures not in keepMeasures
          if (!group.keepMeasures.has(measure)) continue;
          const val = instValues[inst] ?? '';
          checkpoint.rows.push([month, group.name, inst, measure, val]);
          rowCount++;
        }
      }

      checkpoint.done.push(checkKey);
      fs.writeFileSync(CHECKPOINT_PATH, JSON.stringify(checkpoint));
      console.log(`  Saved (${institutions.length} institutions, ${rowCount} data cells)`);
    }

  } catch (err) {
    console.error(`Fatal in group ${group.name}:`, err.message);
    await ss(page, `${group.name.replace(/\s/g,'_')}_error`);
  } finally {
    await browser.close();
  }
}

// ── Main ───────────────────────────────────────────────────────────────────────

(async () => {
  let checkpoint = { done: [], rows: [] };
  if (fs.existsSync(CHECKPOINT_PATH)) {
    checkpoint = JSON.parse(fs.readFileSync(CHECKPOINT_PATH, 'utf8'));
    console.log(`Resuming from checkpoint: ${checkpoint.done.length} group-months already done`);
  }

  const targetMonths = generateMonthList(); // 108 months, Dec 2025 → Jan 2017

  for (const group of MEASURE_GROUPS) {
    const remaining = targetMonths.filter(m => !checkpoint.done.includes(`${group.name}:${m}`));
    if (remaining.length === 0) {
      console.log(`\nGroup "${group.name}" already complete, skipping.`);
      continue;
    }
    await scrapeGroup(group, targetMonths, checkpoint);
  }

  // Write final CSV
  const header = ['month', 'group', 'institution', 'measure', 'value'];
  const csvLines = [toCsvRow(header), ...checkpoint.rows.map(toCsvRow)];
  fs.writeFileSync(OUT_PATH, csvLines.join('\n'), 'utf8');
  console.log(`\n✓ Saved ${checkpoint.rows.length} rows to: ${OUT_PATH}`);
})();
