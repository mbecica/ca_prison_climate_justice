/**
 * Scrapes Average Sentence by Admission Type (2023–2026) from the CDCR
 * Population Data Points dashboard:
 *   Admissions > Population Demographics > Crosstabs > Average Sentence by Admission Type
 *
 * Admission types captured:
 *   - Felon New Admissions
 *   - Felon Parole Violators (Return to Custody)
 *   - Felon Parole Violators (With New Term)
 *   - Felon Pending Revocations
 *   - 3N Population (with and without Prior Serious or Violent)
 *
 * Output: data_sources/facilities/CDCR/cdcr_avg_sentence_by_admission.csv
 *
 * Usage:
 *   node fetch_cdcr_avg_sentence.js
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiN2RjZmFjNzItMzI0Ni00M2IwLWJmZjgtNDgyMjUyMjVhOWMwIiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9&pageName=6eb2cf1a956ed8b180cb';
const OUT_PATH = path.join(__dirname, '..', 'data_sources', 'facilities', 'CDCR', 'cdcr_avg_sentence_by_admission.csv');

async function ss(page, name) {
  const p = `/tmp/cdcr_sentence_${name}.png`;
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
              return { x: r.x + r.width / 2, y: r.y + r.height / 2, tag: el.tagName, aria: el.getAttribute('aria-label'), text: (el.textContent || '').trim().slice(0, 80) };
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
    // Also try table elements
    function findTable(root) {
      const t = root.querySelector('table');
      if (t) return t;
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = findTable(el.shadowRoot); if (f) return f; }
      }
      return null;
    }

    const grid = findGrid(document);
    if (grid) {
      const rows = grid.querySelectorAll('[role="row"]');
      const result = [];
      for (const row of rows) {
        const cells = row.querySelectorAll('[role="rowheader"], [role="columnheader"], [role="gridcell"]');
        const r = Array.from(cells).map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '));
        if (r.length > 0 && r.some(v => v)) result.push(r);
      }
      return result;
    }

    const tbl = findTable(document);
    if (tbl) {
      const rows = tbl.querySelectorAll('tr');
      const result = [];
      for (const row of rows) {
        const cells = row.querySelectorAll('th, td');
        const r = Array.from(cells).map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '));
        if (r.length > 0 && r.some(v => v)) result.push(r);
      }
      return result;
    }

    return [];
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

// Dump all visible page text for debugging navigation
async function dumpPageText(page, label) {
  const text = await page.evaluate(() => {
    const nodes = [];
    function collect(root) {
      for (const el of root.querySelectorAll('button, [role="tab"], [role="menuitem"], [role="option"], a, [aria-label]')) {
        const t = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().slice(0, 100);
        if (t) nodes.push(`<${el.tagName}> ${t}`);
      }
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) collect(el.shadowRoot);
      }
    }
    collect(document);
    return nodes.slice(0, 80).join('\n');
  });
  console.log(`\n--- Page elements (${label}) ---\n${text}\n---`);
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

  // Click a radio-style option by matching its text exactly
  async function clickRadioOption(page, label) {
    console.log(`  Selecting radio: "${label}"`);
    const found = await page.evaluate((lbl) => {
      function find(root) {
        for (const el of root.querySelectorAll('*')) {
          const text = (el.textContent || '').trim();
          const aria = (el.getAttribute('aria-label') || '').toLowerCase();
          if (text === lbl || aria === lbl.toLowerCase()) {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2, tag: el.tagName, text };
          }
          if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
        }
        return null;
      }
      return find(document);
    }, label);
    if (found) {
      console.log(`    Found <${found.tag}> "${found.text}" at (${Math.round(found.x)}, ${Math.round(found.y)})`);
      await page.mouse.click(found.x, found.y);
      return true;
    }
    console.warn(`    Not found: "${label}"`);
    return false;
  }

  try {
    console.log('Loading CDCR Population Data Points dashboard...');
    await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
    await page.waitForTimeout(12000);
    await ss(page, '01_loaded');

    // Step 1: Click landing button "Population Data Points Dashboard"
    console.log('\nClicking landing button...');
    const btn = await page.evaluate(() => {
      function find(root) {
        for (const el of root.querySelectorAll('*')) {
          if ((el.textContent || '').trim() === 'Population Data Points Dashboard') {
            const r = el.getBoundingClientRect();
            if (r.width > 0) return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
          }
          if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
        }
        return null;
      }
      return find(document);
    });
    if (btn) {
      console.log(`  Button at (${Math.round(btn.x)}, ${Math.round(btn.y)})`);
      await page.mouse.click(btn.x, btn.y);
      await page.waitForTimeout(10000);
    } else {
      console.warn('  Landing button not found — may already be on dashboard page');
    }
    await ss(page, '02_after_landing');

    // Step 2: Click Crosstabs page nav icon (aria: "select the crosstabs icon to view details over time")
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
      await page.waitForTimeout(8000);
    } else {
      console.warn('  Crosstabs element not found');
    }
    await ss(page, '03_crosstabs');

    // Step 3: Select "Average Sentence" measure
    console.log('\nSelecting Average Sentence measure...');
    await clickRadioOption(page, 'Average Sentence');
    await page.waitForTimeout(4000);
    await ss(page, '04_avg_sentence_selected');

    // Step 4: Select "Admission Type" for rows
    console.log('\nSelecting Admission Type for rows...');
    await clickRadioOption(page, 'Admission Type');
    await page.waitForTimeout(4000);
    await ss(page, '05_admission_type_selected');

    // Step 5: Select "None" for demographic columns (aggregate view)
    console.log('\nSelecting None for demographic columns...');
    await clickRadioOption(page, 'None');
    await page.waitForTimeout(4000);
    await ss(page, '06_none_selected');

    // Step 6: Extract the table
    console.log('\nExtracting table data...');
    const rawRows = await extractFullTable(page);

    if (rawRows.length === 0) {
      console.warn('No rows extracted. Dumping full page HTML for debugging...');
      const html = await page.content();
      fs.writeFileSync('/tmp/cdcr_sentence_page.html', html, 'utf8');
      console.log('Page HTML saved to /tmp/cdcr_sentence_page.html');
    } else {
      console.log(`\nRaw rows (first 15):`);
      rawRows.slice(0, 15).forEach((r, i) => console.log(`  [${i}]`, r));

      // Write raw extraction as CSV
      fs.writeFileSync(OUT_PATH, toCsv(rawRows), 'utf8');
      console.log(`\nSaved ${rawRows.length} rows to: ${OUT_PATH}`);
    }

  } catch (err) {
    console.error('Fatal:', err.message, err.stack);
    await page.screenshot({ path: '/tmp/cdcr_sentence_error.png', fullPage: true }).catch(() => {});
  } finally {
    await browser.close();
  }
})();
