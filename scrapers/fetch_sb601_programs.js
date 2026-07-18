/**
 * Extracts the SB 601 Programs dashboard institution totals table from Power BI.
 *
 * Usage:
 *   node fetch_sb601_programs.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiYzlkM2RiNWEtZDRjMi00ODllLTg2YzEtZjYyM2MwMjA5NmQ0IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9&pageName=5a926528bbf7e48d60c2';
const OUT_PATH = path.join(__dirname, '..', 'data_sources', 'facilities', 'CDCR', 'sb601_programs.csv');
// To advance a year at refresh time, bump FISCAL_YEAR — the filename is stable. See REFRESH.md.
const FISCAL_YEAR = '2024-2025';

async function ss(page, name) {
  const p = `/tmp/sb601_${name}.png`;
  await page.screenshot({ path: p, fullPage: true });
  console.log(`  Screenshot: ${p}`);
}

async function dumpShadowDom(page, label) {
  const result = await page.evaluate(() => {
    const lines = [];
    function walk(root, depth) {
      if (depth > 8) return;
      for (const el of root.querySelectorAll('*')) {
        const tag = el.tagName ? el.tagName.toLowerCase() : '';
        const role = el.getAttribute('role') || '';
        const title = (el.getAttribute('title') || '').slice(0, 100);
        const aria = (el.getAttribute('aria-label') || '').slice(0, 100);
        const text = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 100);
        const rect = el.getBoundingClientRect();
        const pos = rect.width > 0 ? ` [x:${Math.round(rect.x)},y:${Math.round(rect.y)},w:${Math.round(rect.width)},h:${Math.round(rect.height)}]` : '';
        if (role || title || (text && text.length > 0 && text.length < 100)) {
          lines.push(`${'  '.repeat(depth)}<${tag} role="${role}" title="${title}" aria="${aria}"${pos}> "${text}"`);
        }
        if (el.shadowRoot) {
          lines.push(`${'  '.repeat(depth)}  [shadow root]`);
          walk(el.shadowRoot, depth + 1);
        }
      }
    }
    walk(document, 0);
    return lines.join('\n');
  });
  const p = `/tmp/sb601_shadow_${label}.txt`;
  fs.writeFileSync(p, result);
  console.log(`  Shadow DOM dump: ${p}`);
  return result;
}

// Get center coordinates of an element in shadow DOM matching aria-label or text content
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
    console.log(`  Found <${box.tag}> aria="${box.aria}" text="${box.text}" at (${Math.round(box.x)}, ${Math.round(box.y)})`);
    await page.mouse.move(box.x, box.y);
    await page.waitForTimeout(300);
    await page.mouse.click(box.x, box.y);
    return true;
  }
  console.warn(`  Not found: ${label}`);
  return false;
}

// Handle combobox: click to open, then click the desired option
async function selectCombobox(page, comboboxAriaTerms, optionText) {
  console.log(`  Selecting combobox option: "${optionText}"`);

  // Click to open the combobox
  const opened = await mouseClick(page, comboboxAriaTerms, `combobox for ${optionText}`);
  if (!opened) return false;
  await page.waitForTimeout(1500);

  // Now find and click the option in the dropdown
  const clicked = await mouseClick(page, [optionText], `option "${optionText}"`);
  if (!clicked) {
    console.warn(`  Option "${optionText}" not found after opening combobox`);
    return false;
  }
  await page.waitForTimeout(500);
  return true;
}

// Click slicer buttons (role="button" items in a slicer group)
async function clickSlicerButtons(page, buttonTexts) {
  for (const text of buttonTexts) {
    console.log(`  Clicking slicer button: "${text}"`);
    const clicked = await mouseClick(page, [text], `slicer button "${text}"`);
    if (!clicked) console.warn(`  Slicer button not found: "${text}"`);
    await page.waitForTimeout(600);
  }
}

// Extract visible rows from the grid (rowheaders + gridcells)
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

// Focus the grid container and press Enter to activate Power BI's keyboard navigation mode.
// The outer group has text "Press Enter to explore data" — Enter activates arrow key / PageDown navigation.
async function focusTable(page) {
  // Find the outer grid group container (role="group" with "Press Enter to explore data")
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
    console.log(`  Grid group found at (${Math.round(gridGroup.x)}, ${Math.round(gridGroup.y)})`);
    await page.mouse.click(gridGroup.x, gridGroup.y);
    await page.waitForTimeout(500);
    await page.keyboard.press('Enter'); // Activate keyboard navigation mode
    await page.waitForTimeout(500);
  } else {
    console.warn('  Grid group not found, clicking first gridcell fallback');
    const firstCell = await page.evaluate(() => {
      function find(root) {
        const cell = root.querySelector('[role="gridcell"]');
        if (cell) {
          const r = cell.getBoundingClientRect();
          if (r.width > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
        }
        for (const el of root.querySelectorAll('*')) {
          if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
        }
        return null;
      }
      return find(document);
    });
    if (firstCell) {
      await page.mouse.click(firstCell.x, firstCell.y);
      await page.waitForTimeout(300);
    }
  }
}

async function scrollGrid(page) {
  // Try 1: wheel over grid center (grid is at approx x:727, y:464 from shadow DOM analysis)
  await page.mouse.move(727, 464);
  await page.mouse.wheel(0, 300);
  await page.waitForTimeout(200);

  // Try 2: accessibility "Scroll down" button click via DOM
  await page.evaluate(() => {
    function find(root) {
      for (const el of root.querySelectorAll('button')) {
        if ((el.textContent || '').trim() === 'Scroll down') {
          el.click();
          return true;
        }
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

  // Collect initial visible rows
  addRows(await extractVisibleRows(page));

  // Scroll down in steps, re-rendering virtualized rows each time
  let atBottom = false;
  let noNewCount = 0;
  for (let i = 0; i < 200 && !atBottom; i++) {
    const before = allRows.length;
    const state = await scrollGrid(page);
    atBottom = state.atBottom;
    await page.waitForTimeout(700); // let Power BI virtualization re-render
    addRows(await extractVisibleRows(page));
    if (allRows.length === before) {
      noNewCount++;
      if (i % 10 === 0) console.log(`  Scroll ${i}: ${allRows.length} rows (no-new count: ${noNewCount})`);
      if (noNewCount >= 8) break; // no new rows after 8 consecutive scrolls — done
    } else {
      noNewCount = 0;
      if (i % 5 === 0) console.log(`  Scroll ${i}: ${allRows.length} rows`);
    }
  }

  console.log(`  Collected ${allRows.length} unique rows across all scroll positions`);
  if (allRows.length === 0) return null;

  // Forward-fill Institution and Category — they span rows in Power BI matrix visuals
  let lastInstitution = '';
  let lastCategory = '';
  return allRows.map(row => {
    if (row[0] && !/^\d/.test(row[0].trim())) lastInstitution = row[0];
    if (row[1] && !/^\d/.test(row[1].trim())) lastCategory = row[1];
    return [lastInstitution || row[0], lastCategory || row[1], ...row.slice(2)];
  });
}

function toCsv(rows) {
  return rows.map(row =>
    row.map(v => /[,"\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v).join(',')
  ).join('\n');
}

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  try {
    // ── 1. Load ────────────────────────────────────────────────────────────────
    console.log('Loading...');
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(8000);
    await ss(page, '01_loaded');

    // ── 2. Programs page ───────────────────────────────────────────────────────
    console.log('\nNavigating to Programs...');
    await mouseClick(page, ['Programs'], 'Programs tile');
    await page.waitForTimeout(8000);
    await ss(page, '02_programs');

    // ── 3. Click "Data Tables" icon ────────────────────────────────────────────
    // aria-label is "Page navigation . Click to view Data Tables."
    console.log('\nClicking Data Tables icon...');
    await mouseClick(page, ['Click to view Data Tables', 'Data Tables'], '"Click to view Data Tables"');
    await page.waitForTimeout(8000);
    await ss(page, '03_data_tables');
    await dumpShadowDom(page, '03_data_tables');

    // ── 4. Set Fiscal Year combobox ────────────────────────────────────────────
    // aria="Fiscal Year", currently shows "2025-2026"
    console.log(`\nSetting Fiscal Year to "${FISCAL_YEAR}"...`);
    await selectCombobox(page, ['Fiscal Year'], FISCAL_YEAR);
    await page.waitForTimeout(2000);
    await ss(page, '04_fiscal_year');

    // ── 5. Set Category/Metric combobox ────────────────────────────────────────
    // aria="Category - Statewide, Metric - Statewide", currently shows "All"
    // Select both "Cognitive Behavioral Intervention" and "Rehabilitative Programs"
    console.log('\nSetting Category/Metric...');
    await selectCombobox(page, ['Category - Statewide', 'Category/Metric'], 'Cognitive Behavioral Intervention');
    await page.waitForTimeout(1000);
    // Select second option while dropdown is still open (CTRL+click for multi-select)
    const secondOptBox = await getCenter(page, ['Rehabilitative Programs']);
    if (secondOptBox) {
      await page.keyboard.down('Control');
      await page.mouse.click(secondOptBox.x, secondOptBox.y);
      await page.keyboard.up('Control');
      console.log('  Also selected: Rehabilitative Programs');
    }
    // Close dropdown by clicking elsewhere
    await page.mouse.click(900, 400);
    await page.waitForTimeout(2000);
    await ss(page, '05_category');

    // ── 6. Click "institution totals" ──────────────────────────────────────────
    // aria="Page navigation . Click to view Institution Totals."
    console.log('\nClicking Institution Totals...');
    await mouseClick(page, ['Click to view Institution Totals', 'Institution Totals'], '"Institution Totals"');
    await page.waitForTimeout(6000);
    await ss(page, '06_institution_totals');
    await dumpShadowDom(page, '06_institution_totals');

    // ── 7. Focus table and extract ─────────────────────────────────────────────
    console.log('\nFocusing table for keyboard navigation...');
    await focusTable(page);
    await ss(page, '07_focused');

    console.log('\nExtracting table...');
    const tableData = await extractTable(page);

    if (!tableData || tableData.length === 0) {
      console.warn('No table found.');
      fs.writeFileSync('/tmp/sb601_page_text.txt', await page.evaluate(() => document.body.innerText));
      await ss(page, '06_no_table');
    } else {
      console.log(`Extracted ${tableData.length} rows x ${tableData[0].length} columns`);
      tableData.slice(0, 5).forEach(r => console.log(' ', r.join(' | ')));
      fs.writeFileSync(OUT_PATH, toCsv(tableData), 'utf8');
      console.log(`\nSaved: ${OUT_PATH}`);
    }

  } catch (err) {
    console.error('Fatal:', err.message);
    await page.screenshot({ path: '/tmp/sb601_error.png', fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }
})();
