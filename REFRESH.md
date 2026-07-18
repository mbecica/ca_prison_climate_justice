# REFRESH.md — Data Refresh Runbook

**DRAFT — pending review of the frozen/living classification. Do not treat as adopted.**

How to refresh the data in this repository, family by family: which scraper to run,
which notebook/script rebuilds what, which `data/` outputs change, and which downstream
consumers need to be rebuilt afterward. Consumers include the
[Prison Heat Index](https://marybecica.com/prison-heat-index/) export (`analysis/app_export/`),
the Heat Tracker static builds (`analysis/heatwave_app/` → the `ca-carceral-heat-tracker` repo),
and the capstone/CJC report analyses.

## Versioning convention: frozen vs. living

Every output in this repo is one of two kinds, and a refresh must never blur the line:

- **LIVING** — refreshed in place under the same filename; currency tracked with as-of
  stamps (in a column, a README note, or the consuming app's `vintages` metadata).
- **FROZEN** — a vintaged analysis or source snapshot. A refresh never overwrites it:
  the new cut lands **alongside** under a new vintage name (`*_2026.csv`, new `_YYYY`
  columns), and downstream consumers keep reading their pinned vintage until they are
  deliberately re-exported.

Rules that follow from this:

1. New vintages of frozen files/columns are **added**, old ones are **never deleted or
   renamed** during a refresh.
2. Consumers name the vintage they read (e.g., `build_app_data.py` reads the
   `*_2025` columns). Moving a consumer to a new vintage is its own deliberate,
   reviewed change — not a side effect of a refresh.
3. Tag the repo after every refresh (`git tag refresh-2027-04`) as a whole-repo
   fallback for anything not vintage-named.
4. If a frozen file's name doesn't yet carry its vintage (see the classification
   table), it inherits one at its *next* re-cut; the existing file stays untouched.

## Refresh calendar

| When | What | Why |
|---|---|---|
| **Pre-season (Apr–May)** — the main refresh | CDCR population (TPOP-1), CCHCS vulnerability dashboards, HiFLD facility list re-download, rebuild `cdcr_facilities.csv` + `ca_facilities.csv`, rerun Heat Tracker static builds | The heat apps enter summer with current numbers |
| **Post-season (Nov–Dec)** | Population touch-up; roll the Heat Tracker 10-year hourly envelope forward one season (`build_historic_bands.py`); extend gridMET analysis years if the heat-operations work continues | Annual climate roll-forward |
| **Unscheduled (user-initiated)** | Anything event-driven, run only when its trigger happens — a closure or large population move; **cooling infrastructure** (a master-plan project completes, or CDCR/FOIA releases a new cooling report); refreshed hazard/climate source layers (Cal-Adapt, VCP, CalEnviroScreen, CalFire) or Census boundaries | One-off, no calendar |

Estimated effort for a pre-season refresh: about half a session, dominated by scraper
runtime (the Power BI scrapers are interactive and brittle — budget for babysitting).

## Build tiers (dependency order)

```
scrapers/* + manual downloads
  → data_sources/**                       (raw + vintaged source files)
  → data_sources/*/create_*.ipynb,
    data_sources/hazards/*/*.ipynb        (core table builders)
  → data/**                               (processed tables)
  → analysis/hazards, CDCR_risk_indices,
    CDCR_hazard_rank, cjc reports         (analyses)
  → analysis/app_export (PHI → website repo)
  → analysis/heatwave_app (→ ca-carceral-heat-tracker repo)
```

## Manual PDF downloads (do this before running the PDF scrapers)

Several CDCR scrapers only *parse* PDFs — a human must download the new PDFs first and
drop them in the right folder (these folders are git-ignored). If you're doing a full
refresh, grab the latest for whichever families you're updating:

| Data family | Download from | Put PDFs in | Naming the scraper expects |
|---|---|---|---|
| Population (TPOP-1) | cdcr.ca.gov/research → Population Reports | `data_sources/facilities/CDCR/cdcr_population_pdfs/` (weekly under `tpop_weekly/{YYYY}/`) | `Tpop1d{YYMM}.pdf` (monthly), `Tpop1d{YYMMDD}.pdf` (weekly) |
| Restricted housing | CDCR Office of Research, STA429 monthly reports | `data_sources/facilities/CDCR/restricted_housing/` | `STA429-MMDDYY-M.pdf` (filename date = publication date) |
| Specialized beds | cchcs.ca.gov/reports (Bed Need Study, MHCB/PIP census) | `data_sources/facilities/CDCR/specialized_beds/` | prefix each with `YYYY-MM-DD_` (report date) |
| SCO staffing | State Controller "Active State Employees by Department" (Wayback) | `data_sources/facilities/CDCR/cdcr_staffing/` | `YYYY[_month]_active_state_employees_by_department.pdf` |
| Violent incidents | CDCR CompStat / Public incident reports | `data_sources/facilities/CDCR/cdcr_incidents/` | ⚠ filenames are hardcoded in `extract_violent_incidents.py` — add the new PDF, then add its filename to the script's list |
| Cooling / master plan | CDCR MPAR + Air Cooling reports | `data_sources/facilities/CDCR/cdcr_facilities_planning/` | (manually transcribed, not auto-parsed) |

The Power BI scrapers (CCHCS, SB 601) don't use PDFs — they drive live dashboards and need
a visible browser; see each family's section.

---

# Data families

## 1. Facility list (all CA, ~357 facilities)

| Step | What |
|---|---|
| Sources | FEMA RAPT / HiFLD "Prison Boundaries" layer (**manual download** → `data_sources/facilities/Prison_Boundaries_RAPT.geojson`); USGS National Map medical/EMS layer (`python3 scrapers/fetch_national_map_medical.py`, fully automatic → `data_sources/national_map_medical_emergency.csv`); Census tract/urban-area boundary zips (manual, rarely change); CalFire WUI zip |
| Rebuild | `data_sources/facilities/create_facilities.ipynb` |
| Output | `data_sources/facilities/ca_facilities.csv` — **LIVING** |
| Consumers | `create_cdcr_facilities.ipynb` · `analysis/hazards/join_climate_hazards.ipynb` · `analysis/cjc reports/heat_operations/build_heat_operations_panel.py` · **Heat Tracker:** all three `analysis/heatwave_app/build_*.py` |
| After refresh | Rebuild `cdcr_facilities.csv` (family 2); rerun `join_climate_hazards.ipynb`; rerun Heat Tracker builds (family 11) — `build_baselines.py --only-missing` and `build_historic_bands.py --only-missing` for any new facilities |

Update the HiFLD vintage where it's displayed: `FACILITY_LIST_AS_OF` in
`analysis/heatwave_app/build_facilities.py`, and the PHI/tracker methods pages.

## 2. CDCR population, demographics & capacity

✅ **Resolved (investigated Jul 17 2026): scrape the dashboard, retire the population PDFs.**
The `average_2025_population` column that everything consumes does **not** come from the
TPOP-1 PDFs — `create_cdcr_facilities.ipynb` merges it from a hand-made
`CDCR_2025_pop_averages.csv` (Facility_Name, Facility_Code, Average_2025_Population), and
the TPOP-1 scraper's output isn't wired into the population column at all. The **Population
Data Points dashboard carries this data directly**: *In-Custody → Crosstabs → Rows =
Location, Columns = None* yields monthly in-custody population per CDCR institution code
(ASP, CTF, SATF, …) for Jan 2023 – Jun 2026 (counts < 10 suppressed; the Location list
also includes a few non-institution programs — Community Reentry, DSH, Alternative Custody
— that a scraper filters out). **Plan:** build `fetch_cdcr_population.js` (sibling to
`fetch_cdcr_avg_sentence.js`, same navigation) to scrape Year/Month/Location/In-Custody,
average the 12 months per institution per year, and emit `CDCR_YYYY_pop_averages.csv`
directly — removing both the manual transcription and the PDF download. TPOP-1 PDFs
(`extract_tpop1.py`) can then be retired for population (they'd only be needed if we ever
want design/staffed *capacity*, which currently comes from FEMA anyway).

| Step | What |
|---|---|
| Sources | **Population (current, manual):** hand-made `CDCR_2025_pop_averages.csv` (**FROZEN**, a new year lands alongside as `CDCR_2026_pop_averages.csv`). **Demographics:** `cdcr_in-custody-*_2025.csv` from the CDCR Population Data Set (**manual → FROZEN**). **Capacity:** the FEMA `capacity` column already in `ca_facilities.csv`. **TPOP-1 PDFs** (`extract_tpop1.py`) feed capacity/occupancy series only, and are a candidate to retire — see the open question above |
| Rebuild | `data_sources/facilities/create_cdcr_facilities.ipynb` |
| Output | `data/cdcr/cdcr_facilities.csv` — **LIVING file with FROZEN vintaged columns** (`average_2025_population`, `capacity_percent_2025`, `cchcs_*_2025`, `rhu_pct_2025`, …). A refresh **adds** `*_2026` columns; it does not rename or drop `*_2025` |
| Consumers | PHI `build_app_data.py` (pinned to `_2025` columns) · `heat_risk_index.ipynb` · `sensitivity_analysis.ipynb` · hazard-rank notebooks · `build_indoor_outdoor_analysis.py` · **Heat Tracker** `build_facilities.py` (auto-discovers the latest `average_YYYY_population` / `cchcs_*_YYYY` columns) |
| After refresh | Rerun Heat Tracker `build_facilities.py` (picks up the new vintage automatically). PHI stays on its pinned vintage until deliberately re-exported |

**Next task (confirmed feasible, off the heat-data critical path):** build
`fetch_cdcr_population.js` (In-Custody → Crosstabs → Location) to write
`CDCR_YYYY_pop_averages.csv` directly, then update `create_cdcr_facilities.ipynb` to read
it and drop the manual step + PDF download from the population refresh.

## 3. CCHCS vulnerability (risk tiers, EOP, DPP, age 50+)

| Step | What |
|---|---|
| Source | CCHCS Power BI dashboard via `node scrapers/fetch_cchcs_ipc.js` — **interactive** (visible browser), checkpoint at `/tmp/cchcs_ipc_checkpoint.json`. ⚠ The month range **and** the output filename are hardcoded (`2017–2025`): to extend, edit `generateMonthList()` and write to a new filename |
| Output | `data_sources/facilities/CDCR/cchcs_ipc_2017-2025.csv` — **FROZEN** (range in name; a new pull lands alongside as `cchcs_ipc_2017-2026.csv` or similar) |
| Rebuild | `create_cdcr_facilities.ipynb` → the `cchcs_*_YYYY` columns of `cdcr_facilities.csv` |
| Consumers | Same as family 2 |

The companion `fetch_cchcs_measures.js` (staffing/costs, same hardcoded range; its
checkpoint `cchcs_measures_checkpoint.json` sits **in the repo** and must be deleted
for a full re-scrape) feeds the heat-operations panel (family 8), not `cdcr_facilities.csv`.

## 4. CDCR cooling infrastructure

**Never on a schedule — always a separate, user-initiated update.** Cooling data changes
only when a master-plan project completes (extracted from the MPAR PDFs) or CDCR/FOIA
releases a new cooling report. There is no cadence; this section documents *how* to fold
in a new release when one appears, not *when*.

| Step | What |
|---|---|
| Sources | All **manual**, all **FROZEN**: `air_cooling_housing_units_dec2025.csv` + `air_cooling_infrastructure_dec2025.csv` (transcribed from CDCR Air Cooling Pilot Supplemental Report, Jan 2026), `Reuters_CDCR_cooling.xlsx` (Reuters FOIA, 2025), and MPAR project-completion extracts. A new release lands alongside with its own vintage name |
| Rebuild | `create_cdcr_facilities.ipynb` → cooling columns of `cdcr_facilities.csv` |
| Consumers | PHI cooling pie · Heat Tracker CDCR cooling block · heat-operations panel |
| When a new release appears | Add the new vintage file; point `create_cdcr_facilities.ipynb` at it (deliberate consumer move, rule 2); update `COOLING_AS_OF` in `analysis/heatwave_app/build_facilities.py`; rerun `build_facilities.py` |

## 5. Other CDCR operational sources (reports/capstone only)

All in `data_sources/facilities/CDCR/`; none feed the two apps. Human downloads
PDFs first; scrapers only parse. All outputs **FROZEN** (vintage in name) unless noted.

| Source | Scraper | Output |
|---|---|---|
| SCO staffing PDFs | `extract_sco_staffing.py`, then `build_sco_staffing_2025.py` | `sco_staffing_2020-2026.csv`, `sco_staffing_2025_avg.csv` |
| Restricted housing (STA429 PDFs) | `extract_restricted_housing.py` | `restricted_housing_2025.csv` ⚠ output name hardcoded `_2025` but the input folder already holds 2026 PDFs — re-running today would mix vintages under a 2025 name; rename the output constant first |
| Specialized beds (CCHCS PDFs) | `extract_specialized_beds.py` | `pip_census.csv`, `mhcb_census.csv`, etc. (**LIVING**, report-date rows appended) |
| Violent incidents (5 hardcoded PDFs) | `data_sources/facilities/CDCR/extract_violent_incidents.py` (⚠ lives outside `scrapers/`) | `cdcr_violent_incidents_by_facility.csv` |
| SB 601 dashboards | `fetch_sb601_programs.js`, `fetch_sb601_operations.js` — **interactive**; fiscal years + filenames hardcoded | `sb601_programs_2024-2025.csv`, `sb601_operations_2021-2025.csv` |
| Recidivism / avg sentence dashboards | `fetch_cdcr_recidivism_los.js`, `fetch_cdcr_avg_sentence.js` — **interactive** | `cdcr_recidivism_los.csv`, `cdcr_avg_sentence_by_admission.csv` (**LIVING**, dashboard-driven range) |
| Mortality, MPAR, manual flags | none (hand-curated) | `cchcs_mortality_2006-2024.csv`, `mpar_*.csv`, `cdcr_manual_data.csv` |

## 6. Tract-level climate hazards (heat/air, flood, drought, wildfire)

**Never on a schedule — one-off updates only.** These tract layers change only when the
upstream agency re-releases a dataset (a new Cal-Adapt run, a new CalEnviroScreen version,
new CalFire FHSZ boundaries). Refresh the affected family when that happens; don't put it
on the seasonal calendar.

| Step | What |
|---|---|
| Sources | All **manual downloads**, refreshed only when the agencies re-release: Cal-Adapt tract extracts (`heatdays_alltimes_tract.csv`, `droughtfrequency_tract.csv`), OPR/LCI `VCP_Tracts.geojson`, CalEnviroScreen (`calenviroscreen50csv_d_12226.csv`), Benz & Burney UHI (⚠ processing not scripted in-repo), CalFire FHSZ + WUI |
| Rebuild | `data_sources/hazards/heat/heat_hazard.ipynb` → `data/hazards/heat_air_hazard.csv`; `flood/flood_hazard.ipynb` → `flood_hazard.csv`; `drought/drought_hazard.ipynb` → `drought_hazard.csv` (all **LIVING**); then `analysis/hazards/join_climate_hazards.ipynb` → `data/allfacilities_climate_hazards.csv` (**LIVING**) |
| Consumers | PHI `build_app_data.py` (outdoor climate block) · `heat_risk_index.ipynb` · hazard-rank notebooks |
| After refresh | Rerun `join_climate_hazards.ipynb`, then any analyses you intend to re-cut. The Heat Tracker does **not** consume these (it uses its own ERA5 pulls) |

## 7. gridMET heat activations & summer averages (CDCR-only)

| Step | What |
|---|---|
| Scrapers | `extract_gridmet_heat.py` (fully automatic, ~5.8 GB / 30–45 min) → `heat_activations_{daily,annual,monthly}.csv`; `extract_gridmet_summer_avg.py` (~3.5 GB) → `summer_avg_tmax_annual.csv` |
| ⚠ Path drift | Both scripts write to `data_sources/hazards/` but the committed CSVs live in `data_sources/hazards/heat/` — fix the output constants (or move files) before re-running |
| Classification | The 1991–2020 skarha baseline inside `extract_gridmet_heat.py` is **FROZEN by definition** (WMO normal period — never re-window). The daily/annual/monthly activation files and `summer_avg_tmax_annual.csv` are **LIVING-extendable**: re-running with `ANALYSIS_YEARS` extended appends seasons under the same names |
| Consumers | `build_heat_operations_panel.py` (family 8) · the heat_activations report · Heat Tracker baseline **validation** (one-time cross-check, not a runtime dependency) |

## 8. CJC report analyses (heat operations, indoor/outdoor, risk report)

The CJC reports are **one-time memos: FROZEN.** Their outputs (and the hazard-rank
tables that feed them) are published analyses and are never refreshed in place — if a
report is ever redone for a new period it's a new vintage (new subdir/filename), not an
overwrite. In practice these need no action during a routine refresh.

- Heat operations panel: `build_heat_operations_panel.py` → `run_heat_operations_regression.py` → `run_event_study.py` (inputs: SB601 operations, CCHCS measures, TPOP-1, air-cooling infra, violent incidents, `ca_facilities.csv`, `heat_activations_daily.csv`).
- Indoor/outdoor heat: `build_indoor_outdoor_analysis.py`, `build_improved_clustering.py` (inputs incl. `data/cdcr/indoor_outdoor_heat_2025.csv` — ⚠ **no in-repo builder**; document/script its upstream before it's needed again).
- Heat risk report: `analysis/CDCR_risk_indices/generate_heat_risk_report.py`.
- ⚠ The `heat_activations` report has no in-repo builder script.

## 9. CDCR heat risk index (what the Prison Heat Index consumes)

| Step | What |
|---|---|
| Rebuild | `analysis/CDCR_risk_indices/heat_risk_index.ipynb` (inputs: `cdcr_facilities.csv`, `heat_air_hazard.csv`, `indoor_outdoor_heat_2025.csv`) and `sensitivity_analysis.ipynb` |
| Outputs | `data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv`, `CDCR_heat_risk_sensitivity.csv` — **FROZEN: this is the 2025-vintage analysis PHI ships.** The next re-cut lands alongside with a vintage in the name (rule 4); these files are never overwritten |
| Consumers | PHI `build_app_data.py` · `generate_heat_risk_report.py` · `sensitivity_analysis.ipynb` |
| Orphans | `CDCR_heat_risk_index_multiplicative.csv` (no builder, no consumer — likely a stale variant), `facility_tmin_2025.csv` (no builder, no consumer). Candidates to delete or document |

## 10. Prison Heat Index app export (→ website repo)

| Step | What |
|---|---|
| Rebuild | `python3 analysis/app_export/build_app_data.py` — **only deliberately**, since it re-publishes; it reads the pinned 2025-vintage risk index and `_2025` columns |
| Outputs | `analysis/app_export/output/` (canonical) + copies into `../website`: `data/prison_heat_index.json`, `static/data/{prison_heat_index.json, prison_boundaries.geojson, ca_outline_simple.json}`, `content/prison-heat-index/<slug>.md` × 31 — **LIVING** (regenerated wholesale on each deliberate export) |
| After refresh | Nothing automatic. PHI moves to a new data vintage only when you edit `build_app_data.py` to read it (rule 2), then commit + push `website` |

## 11. Heat Tracker static builds (→ ca-carceral-heat-tracker repo)

Scripts in `analysis/heatwave_app/`; outputs go to the sibling app repo. The live
3-hour pipeline (`fetch_current.py`, GitHub Actions) lives in the app repo and just
reads these files — it needs no changes when the facility list changes.

| Script | Inputs | Outputs | Classification |
|---|---|---|---|
| `build_baselines.py` | `ca_facilities.csv` (lat/lon), Open-Meteo ERA5 archive | `analysis/heatwave_app/data/baselines.csv` | **FROZEN by definition** (1991–2020 window never re-windows). Run `--only-missing` for new facilities only |
| `build_facilities.py` | `ca_facilities.csv`, `cdcr_facilities.csv` (auto-discovers latest vintage columns), `data/baselines.csv`, PHI export (cross-links) | app repo `static/data/facilities.json`, `facility_boundaries.geojson`, `content/facilities/*.md`, `static/_redirects`; local `slugs.csv` | facilities.json **LIVING** (vintage-stamped in `meta.vintages`); `slugs.csv` **LIVING, append-only** — never edit slugs by hand, retired slugs are never reused |
| `build_historic_bands.py` | `ca_facilities.csv`, `slugs.csv`, Open-Meteo ERA5 archive | app repo `static/data/bands/<slug>.json` | **LIVING** — post-season, roll the 10-year window forward one year (edit the year constants) and rerun; `--only-missing` for new facilities mid-cycle |

### Heat Tracker refresh procedure

1. Run the relevant scrapers per families 1–4 above (the slow, human-in-the-loop part).
2. Rebuild `data/cdcr/cdcr_facilities.csv` and (pre-season) `ca_facilities.csv`.
3. `python3 analysis/heatwave_app/build_facilities.py`; if the facility list changed,
   also `build_baselines.py --only-missing` and `build_historic_bands.py --only-missing`,
   then rerun `build_facilities.py` so new thresholds land in the master JSON.
4. Review the git diff **in the app repo** — it shows exactly which facilities'
   numbers changed (this is the sanity check). Closures should show as: stub deleted,
   `_redirects` line added, slug marked retired in `slugs.csv`.
5. Update vintage constants if their sources moved (`FACILITY_LIST_AS_OF`,
   `COOLING_AS_OF` in `build_facilities.py`; population/CCHCS years are auto-discovered).
6. Commit both repos; the app-repo commit triggers its Cloudflare Pages rebuild.
7. `git tag refresh-YYYY-MM` in this repo (rule 3).

---

# Classification table (review me)

Every tracked output, with its draft frozen/living call. **This table is the part
that needs Mary's sign-off before this runbook is adopted.**

| Output | Class | Rationale |
|---|---|---|
| `data_sources/facilities/ca_facilities.csv` | LIVING | Current facility roster; consumers want "now" |
| `data/cdcr/cdcr_facilities.csv` | LIVING (vintaged columns FROZEN) | One row per facility stays current; `*_2025` columns are immutable, `*_2026` added alongside |
| **Re-scraped time series** — `cchcs_ipc_*.csv`, `cchcs_measures_*.csv`, `sb601_operations_*.csv`, `sb601_programs_*.csv`, `sco_staffing_*.csv`, `restricted_housing_*.csv` | **LIVING (extendable)** | Each refresh re-scrapes the full history and the series grows. ⚠ Today their filenames bake in a year range (`_2017-2025`, `_2025`), which fights "same filename in place" — this is exactly what the *hardcoded-dates scope* below proposes to fix |
| `tpop1_institutions.csv`, `tpop1_summary.csv` | LIVING (extendable) | Month rows appended; no vintage in name (may be retired — see §2 open question) |
| `specialized_beds` outputs, `cdcr_recidivism_los.csv`, `cdcr_avg_sentence_by_admission.csv` | LIVING (extendable) | Report-date/month rows appended |
| **Manual vintaged snapshots** — `CDCR_YYYY_pop_averages.csv`, `cdcr_in-custody-*_YYYY.csv`, `air_cooling_*_dec2025.csv`, `cchcs_mortality_2006-2024.csv`, MPAR extracts | FROZEN | Hand-made point-in-time snapshots; a new one lands alongside |
| `data/hazards/{heat_air,flood,drought}_hazard.csv` | LIVING | Rebuilt only when a source layer re-releases (unscheduled) |
| `data/allfacilities_climate_hazards.csv` | LIVING | Join of living inputs |
| `data_sources/hazards/heat/heat_activations_*.csv`, `summer_avg_tmax_annual.csv` | LIVING (extendable) | Seasons appended; skarha baseline inside is definitionally fixed |
| `data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv`, `CDCR_heat_risk_sensitivity.csv` | **FROZEN (2025 vintage)** | The analysis PHI ships; next cut gets a vintage name alongside |
| `data/cdcr/indoor_outdoor_heat_2025.csv` | FROZEN (manual, one-time) | Built once from a specific CDCR PDF for the memo; no builder script exists. ⚠ Gap: if indoor data is ever re-released, write a builder then — otherwise it never updates |
| `data/cdcr/CDCR_heat_risk_index_multiplicative.csv` | FROZEN (alternate method) | Intentional alternate index formulation, kept for possible future re-evaluation — not stale, do not delete |
| `data/ca_outline.json`, `ca_outline_simple.json` | LIVING (static asset) | No builder; effectively never changes |
| `analysis/cjc reports/**` outputs | **FROZEN (one-time memos)** | Published analyses; never refreshed in place |
| `analysis/CDCR_hazard_rank/*.csv` | FROZEN | Feed the frozen CJC memos |
| PHI export (`app_export/output/*`, website copies) | LIVING (deliberate rebuilds only) | Regenerated wholesale by `build_app_data.py` |
| `analysis/heatwave_app/data/baselines.csv` | **FROZEN by definition** | 1991–2020 WMO normal window |
| `analysis/heatwave_app/slugs.csv` | LIVING (append-only) | URL stability contract |
| Heat Tracker app-repo outputs (`facilities.json`, bands, stubs) | LIVING | Vintage-stamped in `meta.vintages`; rebuilt each refresh |

## Resolved (Mary, Jul 17 2026)

1. **`indoor_outdoor_heat_2025.csv`** — one-time manual build from a specific PDF for the memo; no builder exists (documented gap). Add a builder only if indoor data is re-released.
2. **`facility_tmin_2025.csv`** — ✅ deleted (orphan, no builder/consumer).
3. **`CDCR_heat_risk_index_multiplicative.csv`** — kept: valid alternate index method for future re-evaluation. Reclassified FROZEN (alternate method), not orphan.
4. **Population source** (§2) — ✅ confirmed: the dashboard carries per-institution monthly population (In-Custody → Crosstabs → Location). Build `fetch_cdcr_population.js`, retire the population PDFs.
5. **`cchcs_measures_checkpoint.json`** — regenerable scraper resume-state, not source data. Pending Mary's OK to git-ignore.

# Known issues to fix before the next refresh

1. **gridMET path drift** — `extract_gridmet_heat.py` / `extract_gridmet_summer_avg.py` write to `data_sources/hazards/` but files live in `data_sources/hazards/heat/`.
2. **`restricted_housing_2025.csv`** — output name hardcoded while 2026 input PDFs already sit in the folder.
3. **`indoor_outdoor_heat_2025.csv`** — live dependency of the risk index with no in-repo builder; document or script its upstream.
4. **Hardcoded year ranges** in `fetch_cchcs_*.js` (month loop + filename) and `fetch_sb601_operations.js` (`FISCAL_YEARS` + filename) — each needs a code-and-filename edit to advance a year.
5. **`cchcs_measures_checkpoint.json`** (2.2 MB) committed in the data dir; delete to force a full re-scrape (and consider git-ignoring it).
6. **Benz UHI processing** not scripted in-repo (outputs only).
7. **`extract_violent_incidents.py`** lives outside `scrapers/` with 5 hardcoded input PDF names; not covered by `scrapers/README.md`.
8. **`heat_activations` report** has no builder script in-repo.
9. **Power BI scraper fragility** — all five depend on exact dashboard DOM/canvas layouts; expect breakage after CDCR/CCHCS dashboard updates.

# Appendix: hardcoded-date cleanup (proposed, not yet done)

The re-scraped time series are conceptually LIVING but their filenames/loops bake in a
year, forcing a code edit + rename every refresh. **All six are in scope** — a dataset
that currently feeds only a frozen memo is still a living dataset that new analyses will
re-consume; freezing the *memo* does not freeze the *data*.

**Approved: option A (Mary, Jul 17 2026).** Give each scraper a single dated constant at
the top (`LATEST_YEAR` / `LATEST_FY`) and a **stable, un-dated output filename**; update
the one downstream read for each. Advancing a year becomes a one-line edit, no rename.
(Option B — auto-detect the latest period from each dashboard — removes even that edit but
bolts brittle scraping onto interactive tools a human already babysits; rejected.)

| Scraper | Hardcoded spot | Stable output name → | Downstream to update |
|---|---|---|---|
| `fetch_cchcs_ipc.js` | `generateMonthList()` end-year + `_2017-2025` name | `cchcs_ipc.csv` | `create_cdcr_facilities.ipynb` |
| `fetch_cchcs_measures.js` | end-year loop + `_2017-2025` name | `cchcs_measures.csv` | `build_heat_operations_panel.py` |
| `fetch_sb601_programs.js` | `FISCAL_YEAR='2024-2025'` + name | `sb601_programs.csv` | `create_cdcr_facilities.ipynb` |
| `fetch_sb601_operations.js` | `FISCAL_YEARS` array + name | `sb601_operations.csv` | `build_heat_operations_panel.py`, `run_event_study.py` |
| `extract_sco_staffing.py` + `build_sco_staffing_2025.py` | `_2020-2026` / `_2025_avg` names; `_2025` cross-section | `sco_staffing.csv` / `sco_staffing_avg.csv` | `create_cdcr_facilities.ipynb` |
| `extract_restricted_housing.py` | `_2025` name; 2026 PDFs already present (fixes issue #2) | `restricted_housing.csv` | rhu_pct column |

Estimated effort: about half a session for all six (mechanical renames + one dated
constant each + six downstream read updates). The interactive Power BI scrapers can't be
test-run headless, so verification is a manual re-scrape when you next refresh.
