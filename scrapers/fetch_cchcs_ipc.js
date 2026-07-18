/**
 * Scrapes the "Institution & Population Characteristics" measure from the
 * CCHCS Health Care Services Dashboard for every available month (Jan 2017–Dec 2025).
 *
 * Measures extracted per institution per month:
 *   High Risk Priority 1, High Risk Priority 2, Medium Risk, Low Risk,
 *   Mental Health EOP, Disability Placement Program (DPP) Patients,
 *   Patients 50 Years or Older, Specialized Health Care Beds, Institution Population
 *
 * Output: long-format CSV — month, institution, measure, value
 *
 * Usage:
 *   node fetch_cchcs_ipc.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiY2QyNzllZWItMmIxYi00NTk0LWI0OWQtNWEzMTkwYzA3NGE4IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9';
const OUT_PATH = path.join(__dirname, '..', 'data_sources', 'facilities', 'CDCR', 'cchcs_ipc.csv');
const CHECKPOINT_PATH = '/tmp/cchcs_ipc_checkpoint.json';

// Month range to scrape. To advance a year at refresh time, bump LATEST_YEAR —
// nothing else (filename, downstream reads) changes. See REFRESH.md.
const FIRST_YEAR = 2017;
const LATEST_YEAR = 2025;

// Measures to keep (skip group/sub-group header rows with no data)
const SKIP_MEASURES = new Set(['Institution & Population Characteristics', 'Patient Panel']);

// ── Helpers ────────────────────────────────────────────────────────────────────

async function ss(page, name) {
  await page.screenshot({ path: `/tmp/cchcs_ipc_${name}.png` });
  console.log(`  Screenshot: /tmp/cchcs_ipc_${name}.png`);
}

// Find role="combobox" by aria-label (searches shadow DOM too)
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

// Scroll treeitem dropdown and click a specific item
async function selectTreeItem(page, targetText, dropdownX = 998) {
  for (let i = 0; i < 40; i++) {
    const found = await page.evaluate((t) => {
      for (const el of document.querySelectorAll('[role="treeitem"]')) {
        if ((el.textContent || '').trim() === t) {
          const r = el.getBoundingClientRect();
          if (r.width > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
      }
      return null;
    }, targetText);
    if (found) { await page.mouse.click(found.x, found.y); return true; }
    await page.mouse.move(dropdownX, 300);
    await page.mouse.wheel(0, 200);
    await page.waitForTimeout(150);
  }
  return false;
}

// Generate target month list programmatically: Dec 2025 → Jan 2017
function generateMonthList() {
  const names = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const months = [];
  for (let year = LATEST_YEAR; year >= FIRST_YEAR; year--) {
    for (let m = 11; m >= 0; m--) {
      months.push(`${names[m]} ${year}`);
    }
  }
  return months; // newest first
}

// Open Dashboard Month dropdown and select a month.
// Strategy: scan ±300px around the estimated scrollTop in 60px steps (reliable for positions
// within the container's native maxScroll ~1900px). For older months beyond that cap, expand
// the virtual list with mouse wheel chunks.
async function selectMonth(page, monthStr, positionIndex) {
  const dm = await getCombobox(page, 'Dashboard Month');
  await page.mouse.click(dm.x, dm.y);
  await page.waitForTimeout(1500);

  // Helpers that walk up from opts[0] to find the actual scrollable ancestor
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

  // Get dropdown center (for mouse wheel) and current maxScroll
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

  // Each item is ~21px tall. Target: centre item in the 200px viewport.
  const targetScrollTop = Math.max(0, positionIndex * 21 - 90);

  // Phase 1: scan ±300px around target using direct scrollTop (works up to maxScroll)
  const scanStart = Math.max(0, targetScrollTop - 300);
  const scanEnd = Math.min(targetScrollTop + 300, maxScroll);

  for (let pos = scanStart; pos <= scanEnd; pos += 60) {
    await setScrollTop(pos);
    await page.waitForTimeout(500);
    if (await tryClick()) return true;
  }

  // Phase 2: for very old months whose target exceeds maxScroll, expand with mouse wheel
  if (targetScrollTop > maxScroll) {
    const extraPx = targetScrollTop - maxScroll;
    const extraChunks = Math.ceil(extraPx / 500) + 1;
    for (let c = 0; c < extraChunks; c++) {
      if (await tryClick()) return true;
      await page.mouse.move(dropCenter.x, dropCenter.y);
      await page.mouse.wheel(0, 500);
      await page.waitForTimeout(600);
    }
    if (await tryClick()) return true;
    // Fine-tune ±150px around the expanded position
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

// Clean a cell value: strip "Additional Conditional Formatting", remove commas
function cleanValue(raw) {
  return raw
    .replace(/\s*Additional Conditional Formatting\s*/g, '')
    .replace(/,/g, '')
    .trim();
}

// Extract one horizontal snapshot of the grid:
// Returns { institutions: ['SW','ASP',...], rows: [{measure, values: ['9%','0%',...]}] }
async function extractGridSnapshot(page) {
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
    if (!grid) return null;

    const headerRow = grid.querySelector('[role="row"]');
    const institutions = headerRow
      ? Array.from(headerRow.querySelectorAll('[role="columnheader"]'))
          .map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '))
          .filter(h => h !== 'Measures')
      : [];

    const dataRows = Array.from(grid.querySelectorAll('[role="row"]')).slice(1);
    const rows = [];
    for (const row of dataRows) {
      const rh = row.querySelector('[role="rowheader"]');
      const measure = rh ? (rh.innerText || rh.textContent || '').trim().replace(/\s+/g, ' ') : '';
      const cells = Array.from(row.querySelectorAll('[role="gridcell"]'))
        .map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '));
      rows.push({ measure, values: cells });
    }
    return { institutions, rows };
  });
}

// Scroll the grid right and extract all institution columns for the current month
async function extractAllInstitutions(page) {
  const result = {}; // { measure: { institution: value } }

  // Reset horizontal scroll first (scroll all the way left)
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

  // Scroll left to reset position
  for (let i = 0; i < 12; i++) {
    await page.mouse.move(gridCenter.x, gridCenter.y);
    await page.mouse.wheel(-500, 0);
  }
  await page.waitForTimeout(500);

  // Now scroll right, collecting new institutions at each step
  const seenInstitutions = new Set();
  let noNewCount = 0;

  for (let scroll = 0; scroll < 15; scroll++) {
    const snap = await extractGridSnapshot(page);
    if (!snap) break;

    let newInstitutions = 0;
    snap.institutions.forEach((inst, i) => {
      if (!seenInstitutions.has(inst)) {
        seenInstitutions.add(inst);
        newInstitutions++;
      }
      snap.rows.forEach(({ measure, values }) => {
        if (!result[measure]) result[measure] = {};
        if (!(inst in result[measure])) {
          result[measure][inst] = cleanValue(values[i] || '');
        }
      });
    });

    if (newInstitutions === 0) {
      noNewCount++;
      if (noNewCount >= 3) break;
    } else {
      noNewCount = 0;
    }

    // Scroll right
    await page.mouse.move(gridCenter.x, gridCenter.y);
    await page.mouse.wheel(300, 0);
    await page.waitForTimeout(500);
  }

  return result;
}

// ── Main ───────────────────────────────────────────────────────────────────────

function toCsvRow(cols) {
  return cols.map(v => {
    const s = String(v ?? '');
    return /[,"\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  }).join(',');
}

(async () => {
  // Load checkpoint if it exists
  let checkpoint = { done: [], rows: [] };
  if (fs.existsSync(CHECKPOINT_PATH)) {
    checkpoint = JSON.parse(fs.readFileSync(CHECKPOINT_PATH, 'utf8'));
    console.log(`Resuming from checkpoint: ${checkpoint.done.length} months already done`);
  }

  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  try {
    console.log('Loading dashboard...');
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(10000);
    await ss(page, '01_loaded');

    // ── Select Institution & Population Characteristics ────────────────────────
    console.log('\nSelecting "Institution & Population Characteristics" measure...');
    const mc = await getCombobox(page, 'Domain, SubDomain, Element');
    await page.mouse.click(mc.x, mc.y);
    await page.waitForTimeout(1500);
    const selected = await selectTreeItem(page, 'Institution & Population Characteristics');
    if (!selected) throw new Error('Could not select IPC measure');
    await page.waitForTimeout(3000);
    await ss(page, '02_ipc_selected');

    // ── Generate month list ───────────────────────────────────────────────────
    const targetMonths = generateMonthList(); // Dec 2025 → Jan 2017
    console.log(`\nTarget months: ${targetMonths.length} (${targetMonths[0]} → ${targetMonths[targetMonths.length - 1]})`);

    // ── Loop through each month ────────────────────────────────────────────────
    for (let mi = 0; mi < targetMonths.length; mi++) {
      const month = targetMonths[mi];

      if (checkpoint.done.includes(month)) {
        if (mi % 12 === 0) console.log(`  [${mi + 1}/${targetMonths.length}] ${month} — already done, skipping`);
        continue;
      }

      console.log(`\n[${mi + 1}/${targetMonths.length}] ${month}`);

      const ok = await selectMonth(page, month, mi + 1); // +1 because Dec 2025 is position 1
      if (!ok) { console.warn(`  Skipping ${month}`); continue; }
      await page.waitForTimeout(2500);

      const data = await extractAllInstitutions(page);
      const institutions = Object.values(data)[0] ? Object.keys(Object.values(data)[0]) : [];

      for (const inst of institutions) {
        for (const [measure, instValues] of Object.entries(data)) {
          if (SKIP_MEASURES.has(measure)) continue;
          checkpoint.rows.push([month, inst, measure, instValues[inst] ?? '']);
        }
      }

      checkpoint.done.push(month);
      fs.writeFileSync(CHECKPOINT_PATH, JSON.stringify(checkpoint));
      console.log(`  Saved (${institutions.length} institutions, ${Object.keys(data).length - SKIP_MEASURES.size} measures)`);
    }

    // ── Write final CSV ────────────────────────────────────────────────────────
    const header = ['month', 'institution', 'measure', 'value'];
    const csvLines = [toCsvRow(header), ...checkpoint.rows.map(toCsvRow)];
    fs.writeFileSync(OUT_PATH, csvLines.join('\n'), 'utf8');
    console.log(`\nSaved ${checkpoint.rows.length} rows to: ${OUT_PATH}`);

  } catch (err) {
    console.error('Fatal:', err.message);
    await ss(page, 'error');
  } finally {
    await browser.close();
  }
})();
