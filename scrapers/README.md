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

### `fetch_cchcs_measures.js`
Scrapes three additional measure groups from the **CCHCS Health Care Services Dashboard** for every available month (Jan 2017–Dec 2025, 108 months):

- **Staffing** — `Actual Vacancies (All)`, `Medical Vacancies (All)`, `Mental Health Vacancies (All)`, `Dental Vacancies (All)`
- **Major Costs per patient per Month** — `Total Labor Cost (All)`, `ED & Hospital Stays`
- **Other Trends** — `ED/Hospital Stay*`

Grid orientation for these measures is institutions-as-columns / measures-as-rows. The scraper performs a 2D grid traversal (scrolls both right for institutions and down for measures) to capture all cells. Each measure group gets a fresh page load to avoid multi-select state accumulation.

Supports checkpoint/resume — progress is saved to `/tmp/cchcs_measures_checkpoint.json` after each group-month. Delete that file to start a full re-scrape.

```
node fetch_cchcs_measures.js
```

Output: `data_sources/facilities/CDCR/cchcs_measures_2017-2025.csv`

---

---

### `extract_sco_staffing.py`
Extracts total active employee counts at CDCR facilities from State Controller's Office PDF reports stored in `data_sources/facilities/CDCR/cdcr_staffing/`. Uses `pdfplumber`; requires `pip install pdfplumber`.

Handles two PDF encoding variants: older reports (2020–2024) use text extraction; 2025 reports have garbled font encoding and are parsed via table extraction with normalized name lookup. Duplicate PDFs (same "Data as of" date) are automatically skipped.

```
python3 scrapers/extract_sco_staffing.py
```

Output: `data_sources/facilities/CDCR/sco_staffing_2020-2026.csv`

---

### `build_sco_staffing_2025.py`
Reads `sco_staffing_2020-2026.csv`, filters to the three 2025 snapshots (February, May, June), averages staff counts across snapshots, and maps each row to a CDCR institutional code. Applies name corrections for two garbled/truncated entries from the 2025 table-extracted PDFs.

```
python3 scrapers/build_sco_staffing_2025.py
```

Output: `data_sources/facilities/CDCR/sco_staffing_2025_avg.csv`

Columns: `cdcr_code`, `sco_facility_name`, `is_pia` (Prison Industry Authority sub-entry; workers are incarcerated people), `is_cchcs` (CCHCS healthcare staff at CHCF), `n_snapshots`, `full_time`, `part_time`, `intermittent`, `indeterminate`, `total`.

---

### `fetch_national_map_medical.py`
Downloads Medical & Emergency Response facilities for California from the USGS National Map Structures layer. Queries three sublayers with pagination: Hospitals/Medical Centers (layer 14), Ambulance Services (layer 15), and Fire Stations/EMS Stations (layer 16). No dependencies beyond the standard library.

```
python3 scrapers/fetch_national_map_medical.py
```

Output: `data_sources/national_map_medical_emergency.csv`

Columns: `layer` (sublayer label), `name`, `fcode`, `address`, `city`, `state`, `longitude`, `latitude`. 3,877 features as of April 2026 (490 hospitals, 209 ambulance, 3,178 fire/EMS).

---

### `probe_cchcs.js`
Exploratory script used to inspect the CCHCS dashboard DOM structure (grid layout, dropdown scroll behavior, institution column headers). Not intended for production use.
