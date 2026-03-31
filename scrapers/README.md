# Scrapers

Playwright-based scripts for collecting data from California state agency Power BI dashboards. All scripts write output to `../data_sources/facilities/CDCR/`.

## Requirements

```
npm install playwright
npx playwright install chromium
```

## Scripts

### `fetch_cchcs_ipc.js`
Scrapes the **CCHCS Health Care Services Dashboard** ([cchcs.ca.gov/dashboard](https://cchcs.ca.gov/dashboard/)) for the "Institution & Population Characteristics" measure across all available months (Jan 2017–Dec 2025, 108 months). Outputs long-format CSV: `month`, `institution`, `measure`, `value`.

Supports checkpoint/resume — progress is saved to `/tmp/cchcs_ipc_checkpoint.json` after each month. Delete that file to start a full re-scrape.

```
node fetch_cchcs_ipc.js
```

Output: `data_sources/facilities/CDCR/cchcs_ipc_2017-2025.csv`

---

### `fetch_sb601_programs.js`
Scrapes the **CDCR SB 601 Programs Dashboard** for program operational capacity data by institution for fiscal year 2024-2025.

```
node fetch_sb601_programs.js
```

Output: `data_sources/facilities/CDCR/sb601_programs_2024-2025.csv`

---

### `fetch_sb601_operations.js`
Scrapes the **CDCR SB 601 Programs Dashboard** for operational metrics (Lockdowns and Modified Programs, Number of Deaths, Overtime Hours) across all available fiscal years (2021-2022 through 2024-2025).

```
node fetch_sb601_operations.js
```

Output: `data_sources/facilities/CDCR/sb601_operations_2021-2025.csv`

---

### `probe_cchcs.js`
Exploratory script used to inspect the CCHCS dashboard DOM structure (grid layout, dropdown scroll behavior, institution column headers). Not intended for production use.
