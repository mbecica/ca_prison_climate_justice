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

Output: `data_sources/facilities/CDCR/cchcs_ipc.csv`

---

### `fetch_sb601_programs.js`
Scrapes the **CDCR SB 601 Programs Dashboard** for program operational capacity data by institution for fiscal year 2024-2025.

```
node fetch_sb601_programs.js
```

Output: `data_sources/facilities/CDCR/sb601_programs.csv`

---

### `fetch_sb601_operations.js`
Scrapes the **CDCR SB 601 Programs Dashboard** for operational metrics (Lockdowns and Modified Programs, Number of Deaths, Overtime Hours) across all available fiscal years (2021-2022 through 2024-2025).

```
node fetch_sb601_operations.js
```

Output: `data_sources/facilities/CDCR/sb601_operations.csv`

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

Output: `data_sources/facilities/CDCR/cchcs_measures.csv`

---

---

### `extract_sco_staffing.py`
Extracts total active employee counts at CDCR facilities from State Controller's Office PDF reports stored in `data_sources/facilities/CDCR/cdcr_staffing/`. Uses `pdfplumber`; requires `pip install pdfplumber`.

Handles two PDF encoding variants: older reports (2020–2024) use text extraction; 2025 reports have garbled font encoding and are parsed via table extraction with normalized name lookup. Duplicate PDFs (same "Data as of" date) are automatically skipped.

```
python3 scrapers/extract_sco_staffing.py
```

Output: `data_sources/facilities/CDCR/sco_staffing.csv`

---

### `build_sco_staffing_avg.py`
Reads `sco_staffing.csv`, filters to the three 2025 snapshots (February, May, June), averages staff counts across snapshots, and maps each row to a CDCR institutional code. Applies name corrections for two garbled/truncated entries from the 2025 table-extracted PDFs.

```
python3 scrapers/build_sco_staffing_avg.py
```

Output: `data_sources/facilities/CDCR/sco_staffing_avg.csv`

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

### `extract_specialized_beds.py`
Extracts CDCR specialized mental health bed data from PDF reports stored in `data_sources/facilities/CDCR/specialized_beds/` (see the README there for source URLs). Uses `pdfplumber`.

Writes five CSVs to `data_sources/facilities/CDCR/`:

- `pip_census.csv` — Psychiatric Inpatient Program census by facility, program (APP/ICF), and custody level, one snapshot per report date. `Out of LRH`, `PC 1370`, and `WIC 7301` are informational subsets of the census, not additive with the level rows.
- `pip_coleman_waitlist.csv` — PIP capacity, census, reserved/redlined beds, and waitlist by facility. Referral/waitlist columns are only reported on section `Total` rows in the source (facility cells are blank → 0). `GRAND TOTALS` rows carry `section="All PIPs"`.
- `mhcb_census.csv` — system-level Mental Health Crisis Bed capacity/census (male/female/total).
- `bed_need_study_actuals.csv` — historical actuals and forecasts by program from the Bed Need Study. `Avg Census` is the program census; `Total ADC` = `Avg Census` + `Avg Pending List`; in CCCMS/EOP tables `Total ADC` is the only census measure. `is_forecast` is true for FY2026+.
- `mhsds_programs_by_facility.csv` — facility × program flag matrix from the MHSDS map. The map's icon letters are real text glyphs in the PDF, extracted by position and clustered to facility labels (not read from the rendered image).

```
python3 scrapers/extract_specialized_beds.py
```

New monthly PIP/MHCB reports can be added by downloading them into `specialized_beds/` with a `YYYY-MM-DD_` filename prefix and re-running; duplicate report dates are skipped automatically.

---

### `extract_loca2_heat.py`
Extracts facility-relative heat thresholds from **LOCA2-CA daily** projections (Cal-Adapt / cadcat).
This is an API/catalog read, not a scrape: it opens the cadcat S3 zarr store anonymously via
`intake-esm` and reads `tasmax`/`tasmin` lazily at each facility's containing grid cell. Ensemble is
14 models / 62 members, pooled by model democracy (per member → within model → across models);
periods are historic (1981–2010), mid-century (2041–2070, ssp370), and end-century.

Writes `data_sources/hazards/heat/loca2_facility_heat.csv` (357 facilities × absolute and relative
threshold counts for all three periods). Cell assignment is cached in `loca2_facility_cells.csv`; a
per-member JSON cache lives in `loca2_members/` (gitignored, regenerable) so interrupted runs resume
for free.

```
python3 scrapers/extract_loca2_heat.py            # cells → extract → pool
python3 scrapers/extract_loca2_heat.py --pool-only # re-pool cached members without re-extracting
```

**~6 hours.** Run it detached — the script uses a double-fork `os.setsid()` launcher (under
`caffeinate`) because harness-tracked background jobs are reaped around 60–80 min. Full method,
ensemble rationale, spatial rule, and the reproduction gate against the published Cal-Adapt layer are
documented in `data_sources/hazards/heat/README.md`. Re-run only when the model set, cell rule, or
threshold definitions change — LOCA2-CA is a fixed projection product with no seasonal cadence.
(A pending refactor will move this and the gridMET extractors out of `scrapers/` into
`data_sources/hazards/heat/extraction/`, since they are reads rather than scrapes.)

---

### `probe_cchcs.js`
Exploratory script used to inspect the CCHCS dashboard DOM structure (grid layout, dropdown scroll behavior, institution column headers). Not intended for production use.
