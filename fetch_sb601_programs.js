/**
 * Extracts the SB 601 Programs dashboard institution totals table from Power BI.
 *
 * Navigates to the Programs page, opens the data table view, sets filters to:
 *   - Category/metric: "Cognitive Behavioral Intervention" + "Rehabilitative Programs"
 *   - Fiscal Year: "2024-2025"
 * Then reads the accessible table DOM and writes the result to:
 *   data_sources/facilities/CDCR/sb601_programs_2024-2025.csv
 *
 * Usage:
 *   npx playwright install chromium   # first time only
 *   node fetch_sb601_programs.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiYzlkM2RiNWEtZDRjMi00ODllLTg2YzEtZjYyM2MwMjA5NmQ0IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9&pageName=5a926528bbf7e48d60c2';
const OUT_PATH = path.join(__dirname, 'data_sources', 'facilities', 'CDCR', 'sb601_programs_2024-2025.csv');
const CATEGORIES = ['Cognitive Behavioral Intervention', 'Rehabilitative Programs'];
const FISCAL_YEAR = '2024-2025';

// How long to wait after interactions before checking the DOM (ms)
const SETTLE_MS = 2500;

async function selectDropdownOptions(page, labelText, optionTexts) {
  console.log(`  Setting dropdown "${labelText}" to: ${optionTexts.join(', ')}`);

  // Power BI dropdowns are role="listbox" slicers — find by nearby label text
  const slicers = page.locator('[role="listbox"]');
  const count = await slicers.count();
  let matched = null;

  for (let i = 0; i < count; i++) {
    const slicer = slicers.nth(i);
    // Check nearby heading/label text
    const container = slicer.locator('xpath=ancestor::*[3]');
    const text = await container.innerText().catch(() => '');
    if (text.toLowerCase().includes(labelText.toLowerCase())) {
      matched = slicer;
      break;
    }
  }

  if (!matched) {
    // Fallback: look for any element containing the label text and find nearest slicer
    console.warn(`  Could not find listbox for "${labelText}" via ancestor text. Trying title search.`);
    const title = page.locator(`[title*="${labelText}"], [aria-label*="${labelText}"]`).first();
    matched = title;
  }

  // Click each desired option
  for (const opt of optionTexts) {
    const option = page.locator(`[role="option"]`).filter({ hasText: opt }).first();
    if (await option.count() === 0) {
      console.warn(`  Warning: option "${opt}" not found in dropdown`);
      continue;
    }
    const isSelected = await option.getAttribute('aria-selected');
    if (isSelected !== 'true') {
      await option.click();
      await page.waitForTimeout(500);
    } else {
      console.log(`  "${opt}" already selected`);
    }
  }
}

async function extractTable(page) {
  // Power BI renders accessible tables with role="grid" or actual <table> elements
  // Try role="grid" first (Power BI's accessible table mode)
  const grids = page.locator('[role="grid"]');
  const gridCount = await grids.count();
  console.log(`  Found ${gridCount} role="grid" element(s)`);

  if (gridCount > 0) {
    const grid = grids.first();
    const rows = grid.locator('[role="row"]');
    const rowCount = await rows.count();
    console.log(`  Grid has ${rowCount} rows`);

    const data = [];
    for (let r = 0; r < rowCount; r++) {
      const row = rows.nth(r);
      const cells = row.locator('[role="columnheader"], [role="gridcell"]');
      const cellCount = await cells.count();
      const rowData = [];
      for (let c = 0; c < cellCount; c++) {
        const text = await cells.nth(c).innerText().catch(() => '');
        rowData.push(text.trim().replace(/\n/g, ' '));
      }
      if (rowData.some(v => v)) data.push(rowData);
    }
    return data;
  }

  // Fallback: regular <table>
  const tables = page.locator('table');
  const tableCount = await tables.count();
  console.log(`  Found ${tableCount} <table> element(s)`);

  if (tableCount > 0) {
    return await page.evaluate(() => {
      const table = document.querySelector('table');
      const rows = Array.from(table.querySelectorAll('tr'));
      return rows.map(row =>
        Array.from(row.querySelectorAll('th, td')).map(cell => cell.innerText.trim().replace(/\n/g, ' '))
      ).filter(r => r.some(v => v));
    });
  }

  return null;
}

function toCsv(rows) {
  return rows.map(row =>
    row.map(cell => {
      const escaped = cell.replace(/"/g, '""');
      return /[,"\n]/.test(escaped) ? `"${escaped}"` : escaped;
    }).join(',')
  ).join('\n');
}

(async () => {
  const browser = await chromium.launch({ headless: false }); // headless: false so you can watch/intervene
  const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await context.newPage();

  try {
    console.log('Loading dashboard...');
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(SETTLE_MS);

    // Take a screenshot to see what loaded
    await page.screenshot({ path: '/tmp/sb601_01_loaded.png' });
    console.log('Page loaded. Screenshot: /tmp/sb601_01_loaded.png');

    // Step 1: Click "click to view data tables" link
    console.log('\nLooking for "click to view data tables" link...');
    const dataTablesLink = page.getByText(/click to view data tables/i).first();
    if (await dataTablesLink.count() > 0) {
      await dataTablesLink.click();
      await page.waitForTimeout(SETTLE_MS);
      await page.screenshot({ path: '/tmp/sb601_02_data_tables.png' });
      console.log('Clicked data tables link. Screenshot: /tmp/sb601_02_data_tables.png');
    } else {
      console.warn('Could not find "click to view data tables" link. Check /tmp/sb601_01_loaded.png to see what loaded.');
    }

    // Step 2: Click "Click to view institution totals"
    console.log('\nLooking for "institution totals" link...');
    const institutionLink = page.getByText(/institution totals/i).first();
    if (await institutionLink.count() > 0) {
      await institutionLink.click();
      await page.waitForTimeout(SETTLE_MS);
      await page.screenshot({ path: '/tmp/sb601_03_institution_totals.png' });
      console.log('Clicked institution totals. Screenshot: /tmp/sb601_03_institution_totals.png');
    } else {
      console.warn('Could not find "institution totals" link. Check screenshots.');
    }

    // Step 3: Set fiscal year dropdown
    console.log(`\nSetting Fiscal Year to "${FISCAL_YEAR}"...`);
    await selectDropdownOptions(page, 'Fiscal Year', [FISCAL_YEAR]);
    await page.waitForTimeout(SETTLE_MS);
    await page.screenshot({ path: '/tmp/sb601_04_fiscal_year.png' });

    // Step 4: Set category/metric dropdown
    console.log(`\nSetting Category/metric to: ${CATEGORIES.join(', ')}...`);
    await selectDropdownOptions(page, 'Category', CATEGORIES);
    await page.waitForTimeout(SETTLE_MS);
    await page.screenshot({ path: '/tmp/sb601_05_categories.png' });
    console.log('Filters set. Screenshot: /tmp/sb601_05_categories.png');

    // Step 5: Extract table
    console.log('\nExtracting table data...');
    const tableData = await extractTable(page);

    if (!tableData || tableData.length === 0) {
      // Dump all visible text as a fallback
      console.warn('No table found via DOM. Dumping page text to /tmp/sb601_page_text.txt for inspection.');
      const text = await page.evaluate(() => document.body.innerText);
      fs.writeFileSync('/tmp/sb601_page_text.txt', text);
      await page.screenshot({ path: '/tmp/sb601_final.png', fullPage: true });
      console.log('Full-page screenshot: /tmp/sb601_final.png');
    } else {
      console.log(`\nExtracted ${tableData.length} rows, ${tableData[0].length} columns.`);
      console.log('Preview (first 3 rows):');
      tableData.slice(0, 3).forEach(row => console.log(' ', row));

      const csv = toCsv(tableData);
      fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
      fs.writeFileSync(OUT_PATH, csv, 'utf8');
      console.log(`\nSaved to: ${OUT_PATH}`);
    }

  } catch (err) {
    console.error('Error:', err.message);
    await page.screenshot({ path: '/tmp/sb601_error.png', fullPage: true }).catch(() => {});
    console.log('Error screenshot: /tmp/sb601_error.png');
  } finally {
    await browser.close();
  }
})();
