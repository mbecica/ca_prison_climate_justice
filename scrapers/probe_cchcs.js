const { chromium } = require('playwright');
const fs = require('fs');

const URL = 'https://app.powerbigov.us/view?r=eyJrIjoiY2QyNzllZWItMmIxYi00NTk0LWI0OWQtNWEzMTkwYzA3NGE4IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9';

async function getCombobox(page, ariaLabel) {
  return await page.evaluate((label) => {
    function find(root) {
      for (const el of root.querySelectorAll('[role="combobox"]')) {
        if ((el.getAttribute('aria-label') || '').toLowerCase().includes(label.toLowerCase())) {
          const r = el.getBoundingClientRect();
          if (r.width > 0) return { x: r.x + r.width/2, y: r.y + r.height/2 };
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
  for (let i = 0; i < 30; i++) {
    const found = await page.evaluate((t) => {
      for (const el of document.querySelectorAll('[role="treeitem"]')) {
        if ((el.textContent || '').trim() === t) {
          const r = el.getBoundingClientRect();
          if (r.width > 0) return { x: r.x + r.width/2, y: r.y + r.height/2 };
        }
      }
      return null;
    }, targetText);
    if (found) { await page.mouse.click(found.x, found.y); return true; }
    await page.mouse.move(dropdownX, 300);
    await page.mouse.wheel(0, 200);
    await page.waitForTimeout(200);
  }
  return false;
}

// Extract a snapshot of the grid: returns { headers: [...], rows: [{measure, values: [...]}] }
// headers = institution codes from columnheaders; rows = measure names + corresponding cell values
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
    const headers = headerRow
      ? Array.from(headerRow.querySelectorAll('[role="columnheader"]'))
          .map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '))
      : [];

    const dataRows = Array.from(grid.querySelectorAll('[role="row"]')).slice(1);
    const rows = [];
    for (const row of dataRows) {
      const rh = row.querySelector('[role="rowheader"]');
      const measure = rh ? (rh.innerText || rh.textContent || '').trim().replace(/\s+/g, ' ') : '';
      const cells = Array.from(row.querySelectorAll('[role="gridcell"]'))
        .map(c => (c.innerText || c.textContent || '').trim().replace(/\s+/g, ' '));
      if (measure || cells.length > 0) rows.push({ measure, cells });
    }
    return { headers, rows };
  });
}

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

  console.log('Loading...');
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(10000);

  // ── 1. Select IPC measure ─────────────────────────────────────────────────
  const mc = await getCombobox(page, 'Domain, SubDomain, Element');
  await page.mouse.click(mc.x, mc.y);
  await page.waitForTimeout(1500);
  await selectTreeItem(page, 'Institution & Population Characteristics');
  await page.waitForTimeout(3000);

  // ── 2. Probe horizontal scrolling of the grid ─────────────────────────────
  console.log('\n--- Horizontal scroll probe ---');
  let snap = await extractGridSnapshot(page);
  console.log('Initial headers:', snap?.headers);
  console.log('Initial rows:');
  snap?.rows.forEach(r => console.log(`  "${r.measure}":`, r.cells));

  // Try scrolling right
  const gridInfo = await page.evaluate(() => {
    function find(root) {
      const g = root.querySelector('[role="grid"]');
      if (g) { const r = g.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height }; }
      for (const el of root.querySelectorAll('*')) {
        if (el.shadowRoot) { const f = find(el.shadowRoot); if (f) return f; }
      }
      return null;
    }
    return find(document);
  });
  console.log('\nGrid center:', gridInfo);

  // Scroll right 5 times and check new headers
  console.log('\nScrolling right...');
  for (let i = 0; i < 5; i++) {
    await page.mouse.move(gridInfo.x, gridInfo.y);
    await page.mouse.wheel(300, 0); // horizontal wheel
    await page.waitForTimeout(600);
    const s = await extractGridSnapshot(page);
    console.log(`After right scroll ${i+1}:`, s?.headers);
  }

  // ── 3. Probe month dropdown scrolling ─────────────────────────────────────
  console.log('\n--- Month dropdown scroll probe ---');
  const dm = await getCombobox(page, 'Dashboard Month');
  await page.mouse.click(dm.x, dm.y);
  await page.waitForTimeout(1500);

  // Find the dropdown container element
  const dropdownContainer = await page.evaluate(() => {
    for (const el of document.querySelectorAll('[role="listbox"], [role="list"]')) {
      const r = el.getBoundingClientRect();
      if (r.width > 0 && r.height > 50) return { x: r.x + r.width/2, y: r.y + r.height/2, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight };
    }
    // fallback: find visible options and their container
    const opts = document.querySelectorAll('[role="option"]');
    if (opts.length > 0) {
      const parent = opts[0].parentElement;
      const r = parent.getBoundingClientRect();
      return { x: r.x + r.width/2, y: r.y + r.height/2, scrollHeight: parent.scrollHeight, clientHeight: parent.clientHeight, tag: parent.tagName };
    }
    return null;
  });
  console.log('Dropdown container:', dropdownContainer);

  // Try scrolling the dropdown using scrollTop
  const monthsBefore = await page.evaluate(() =>
    Array.from(document.querySelectorAll('[role="option"]'))
      .filter(el => el.getBoundingClientRect().width > 0)
      .map(el => (el.textContent || '').trim())
  );
  console.log('Visible months before scroll:', monthsBefore);

  // Set scrollTop directly on the options container
  await page.evaluate(() => {
    const opts = document.querySelectorAll('[role="option"]');
    if (opts.length > 0) {
      let el = opts[0].parentElement;
      while (el && el.scrollHeight <= el.clientHeight) el = el.parentElement;
      if (el) { el.scrollTop = 500; }
    }
  });
  await page.waitForTimeout(500);

  const monthsAfter = await page.evaluate(() =>
    Array.from(document.querySelectorAll('[role="option"]'))
      .filter(el => el.getBoundingClientRect().width > 0)
      .map(el => (el.textContent || '').trim())
  );
  console.log('Visible months after scrollTop=500:', monthsAfter);

  // Also try keyboard: arrow down from first option
  await page.keyboard.press('Escape');
  await page.waitForTimeout(500);
  await page.mouse.click(dm.x, dm.y);
  await page.waitForTimeout(1500);

  // Press End key to jump to last option
  await page.keyboard.press('End');
  await page.waitForTimeout(500);
  const monthsEnd = await page.evaluate(() =>
    Array.from(document.querySelectorAll('[role="option"]'))
      .filter(el => el.getBoundingClientRect().width > 0)
      .map(el => (el.textContent || '').trim())
  );
  console.log('Months visible after End key:', monthsEnd);

  await page.screenshot({ path: '/tmp/cchcs_probe_final.png' });
  await browser.close();
})();
