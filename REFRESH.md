# REFRESH.md — Data Refresh Runbook

How to refresh the data in this repository, family by family: which scraper to run,
which notebook/script rebuilds what, which `data/` outputs change, and which downstream
consumers need to be rebuilt afterward. Consumers include the
[Prison Heat Index](https://marybecica.com/prison-heat-index/) export (`analysis/app_export/`),
the Heat Tracker static builds (in the `ca-carceral-heat-tracker` repo, which reads these CSVs),
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
| **Pre-season (Apr–May)** — the main refresh | CDCR population (TPOP-1), CCHCS vulnerability dashboards, HiFLD facility list re-download, rebuild `cdcr_facilities.csv` + `ca_facilities.csv`; then rebuild downstream consumers (PHI export; the Heat Tracker's builds, per **its own repo's REFRESH**) | Consumers enter summer with current numbers |
| **Post-season (Nov–Dec)** | Population touch-up; extend gridMET analysis years if the heat-operations work continues | Annual touch-up |
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
  → ca-carceral-heat-tracker/pipeline (separate app repo; reads these CSVs)
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
| Cooling / master plan | CDCR MPAR + Air Cooling reports | `data_sources/facilities/CDCR/cdcr_facilities_planning/` | (manually transcribed) |

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
| Consumers | `create_cdcr_facilities.ipynb` · `analysis/hazards/join_climate_hazards.ipynb` · `analysis/cjc reports/heat_operations/build_heat_operations_panel.py` · **Heat Tracker:** its `pipeline/build_*.py` (in the app repo) |
| After refresh | Rebuild `cdcr_facilities.csv` (family 2); rerun `join_climate_hazards.ipynb`; rerun Heat Tracker builds (family 11) — `build_baselines.py --only-missing` and `build_historic_bands.py --only-missing` for any new facilities |

Update the HiFLD vintage where it's displayed: `FACILITY_LIST_AS_OF` in
the tracker's `pipeline/build_facilities.py` (app repo), and the PHI/tracker methods pages.

## 2. CDCR population, demographics & capacity

| Step | What |
|---|---|
| Sources | **Population (current, manual):** hand-made `CDCR_2025_pop_averages.csv` (**FROZEN**, a new year lands alongside as `CDCR_2026_pop_averages.csv`); it is the source of `average_2025_population`. **Demographics:** `cdcr_in-custody-*_2025.csv` from the CDCR Population Data Set (**manual → FROZEN**). **Capacity:** the FEMA `capacity` column already in `ca_facilities.csv`. **TPOP-1 PDFs** (`extract_tpop1.py`) feed capacity/occupancy series only |
| Rebuild | `data_sources/facilities/create_cdcr_facilities.ipynb` |
| Output | `data/cdcr/cdcr_facilities.csv` — **LIVING file with FROZEN vintaged columns** (`average_2025_population`, `capacity_percent_2025`, `cchcs_*_2025`, `rhu_pct_2025`, …). A refresh **adds** `*_2026` columns; it does not rename or drop `*_2025` |
| Consumers | PHI `build_app_data.py` (pinned to `_2025` columns) · `heat_risk_index.ipynb` · `sensitivity_analysis.ipynb` · hazard-rank notebooks · `build_indoor_outdoor_analysis.py` · **Heat Tracker** `build_facilities.py` (auto-discovers the latest `average_YYYY_population` / `cchcs_*_YYYY` columns) |
| After refresh | Rerun Heat Tracker `build_facilities.py` (picks up the new vintage automatically). PHI stays on its pinned vintage until deliberately re-exported |

## 3. CCHCS vulnerability (risk tiers, EOP, DPP, age 50+)

| Step | What |
|---|---|
| Source | CCHCS Power BI dashboard via `node scrapers/fetch_cchcs_ipc.js` — **interactive** (visible browser), checkpoint at `/tmp/cchcs_ipc_checkpoint.json`. To extend a year, bump `LATEST_YEAR` at the top of the script — the filename is stable |
| Output | `data_sources/facilities/CDCR/cchcs_ipc.csv` — **LIVING (extendable)**: re-scrapes the full history each run, same filename |
| Rebuild | `create_cdcr_facilities.ipynb` → the `cchcs_*_YYYY` columns of `cdcr_facilities.csv` |
| Consumers | Same as family 2 |

The companion `fetch_cchcs_measures.js` (staffing/costs, same `LATEST_YEAR` knob; its
checkpoint `cchcs_measures_checkpoint.json` is now git-ignored and must be deleted
for a full re-scrape) feeds the heat-operations panel (family 8).

## 4. CDCR cooling infrastructure

**Never on a schedule — always a separate, user-initiated update.** Cooling data changes
only when a master-plan project completes (extracted from the MPAR PDFs) or CDCR/FOIA
releases a new cooling report. There is no cadence; this section documents *how* to fold
in a new release when one appears.

| Step | What |
|---|---|
| Sources | All **manual**, all **FROZEN**: `air_cooling_housing_units_dec2025.csv` + `air_cooling_infrastructure_dec2025.csv` (transcribed from CDCR Air Cooling Pilot Supplemental Report, Jan 2026), `Reuters_CDCR_cooling.xlsx` (Reuters FOIA, 2025), and MPAR project-completion extracts. A new release lands alongside with its own vintage name |
| Rebuild | `create_cdcr_facilities.ipynb` → cooling columns of `cdcr_facilities.csv` |
| Consumers | PHI cooling pie · Heat Tracker CDCR cooling block · heat-operations panel |
| When a new release appears | Add the new vintage file; point `create_cdcr_facilities.ipynb` at it (deliberate consumer move, rule 2); update `COOLING_AS_OF` in the tracker's `pipeline/build_facilities.py` (app repo); rerun it |

## 5. Other CDCR operational sources (reports/capstone only)

All in `data_sources/facilities/CDCR/`; none feed the two apps. Human downloads
PDFs first; scrapers only parse. Outputs are **LIVING (extendable)** unless noted —
stable filenames, re-scraped in full each refresh.

| Source | Scraper | Output |
|---|---|---|
| SCO staffing PDFs | `extract_sco_staffing.py`, then `build_sco_staffing_avg.py` | `sco_staffing.csv`, `sco_staffing_avg.csv` (`LATEST_YEAR` knob) |
| Restricted housing (STA429 PDFs) | `extract_restricted_housing.py` | `restricted_housing.csv` — reprocesses every PDF in the folder, all years |
| Specialized beds (CCHCS PDFs) | `extract_specialized_beds.py` | `pip_census.csv`, `mhcb_census.csv`, etc. (report-date rows appended) |
| Violent incidents (5 hardcoded PDFs) | `data_sources/facilities/CDCR/extract_violent_incidents.py` (⚠ lives outside `scrapers/`) | `cdcr_violent_incidents_by_facility.csv` |
| SB 601 dashboards | `fetch_sb601_programs.js`, `fetch_sb601_operations.js` — **interactive**; bump `FISCAL_YEAR`/`FISCAL_YEARS`, filenames stable | `sb601_programs.csv`, `sb601_operations.csv` |
| Recidivism / avg sentence dashboards | `fetch_cdcr_recidivism_los.js`, `fetch_cdcr_avg_sentence.js` — **interactive** | `cdcr_recidivism_los.csv`, `cdcr_avg_sentence_by_admission.csv` (**LIVING**, dashboard-driven range) |
| Mortality, MPAR, manual flags | none (hand-curated) | `cchcs_mortality_2006-2024.csv`, `mpar_*.csv`, `cdcr_manual_data.csv` |

## 6. Tract-level climate hazards (heat/air, flood, drought, wildfire)

**Never on a schedule — one-off updates only.** These tract layers change only when the
upstream agency re-releases a dataset (a new Cal-Adapt run, a new CalEnviroScreen version,
new CalFire FHSZ boundaries). Refresh the affected family when that happens; don't put it
on the seasonal calendar.

| Step | What |
|---|---|
| Sources | Manual downloads, refreshed only when the agencies re-release: `droughtfrequency_tract.csv`, OPR/LCI `VCP_Tracts.geojson`, CalEnviroScreen (`calenviroscreen50csv_d_12226.csv`, still the AQI source), Benz & Burney UHI (⚠ processing not scripted in-repo), CalFire FHSZ + WUI. **Heat daytime/nighttime come from the LOCA2-CA daily extraction (family 6b).** `heatdays_alltimes_tract.csv` is **DEPRECATED** (read only by the frozen `hazard_top10_table.ipynb` / `hazard_heatmap_table.ipynb`). |
| Rebuild | `data_sources/hazards/heat/heat_hazard.ipynb` (inputs: `heat/loca2_facility_heat.csv` from family 6b + CalEnviroScreen AQI) → `data/hazards/heat_air_hazard.csv`; `flood/flood_hazard.ipynb` → `flood_hazard.csv`; `drought/drought_hazard.ipynb` → `drought_hazard.csv` (all **LIVING**); then `analysis/hazards/join_climate_hazards.ipynb` → `data/allfacilities_climate_hazards.csv` (**LIVING**). Heat now joins by `facilityid`; flood/drought stay tract-level. The join snapshots `allfacilities_climate_hazards_v0.1.csv` on first v0.2 run. |
| Consumers | PHI `build_app_data.py` (outdoor climate block) · `heat_risk_index.ipynb` · hazard-rank notebooks |
| After refresh | Rerun `join_climate_hazards.ipynb`, then any analyses you intend to re-cut. The Heat Tracker does **not** consume these (it reads only `ca_facilities.csv` / `cdcr_facilities.csv`; its baseline is PRISM, per family 11) |

## 6b. LOCA2-CA daily heat extraction (modeled — feeds the heat hazard)

Supplies the heat hazard's daytime and nighttime heat, extracted per facility from LOCA2-CA
daily projections at each facility's grid cell.

| Step | What |
|---|---|
| Extraction | `data_sources/hazards/heat/extraction/extract_loca2_heat.py` — anonymous cadcat S3 zarr read (intake-esm), 14 models / 62 members × 3 periods × `tasmax`+`tasmin` at 274 distinct cells → `data_sources/hazards/heat/loca2_facility_heat.csv` (357 facilities). **~6 h**; run detached (double-fork `os.setsid` launcher under `caffeinate`) — harness-tracked background jobs get reaped at ~60–80 min. Per-member JSON cache (`heat/loca2_members/`, gitignored) makes restarts free; `--pool-only` re-pools without re-extracting. |
| Classification | The relative-threshold **baselines are FROZEN by definition** (hot days 1981–2010; warm nights 1961–1990 Apr–Oct P95) — never re-window. The counts are **re-run only** when the ensemble definition, cell assignment, or thresholds change; LOCA2-CA is a fixed projection product, so there is no new-vintage cadence. |
| Trigger | Re-run only if: cadcat republishes LOCA2-CA, the model/member set or spatial rule changes, or a threshold definition changes. |
| Consumers | `heat_hazard.ipynb` (→ `heat_air_hazard.csv`). The product also stands alone (all 357 facilities, 3 periods, absolute + relative thresholds) for anyone wanting facility-level heat metrics. |

## 7. gridMET heat activations & summer averages (CDCR-only)

| Step | What |
|---|---|
| Extractors | In `data_sources/hazards/heat/extraction/`: `extract_gridmet_heat.py` (fully automatic, ~5.8 GB / 30–45 min) → `heat_activations_{daily,annual,monthly}.csv`; `extract_gridmet_summer_avg.py` (~3.5 GB) → `summer_avg_tmax_annual.csv` |
| Outputs | All four CSVs write to `data_sources/hazards/heat/` (where the committed files live). |
| Classification | The 1991–2020 mean summer tmax baseline (`base1991_2020` in the column names) inside `extract_gridmet_heat.py` is **FROZEN by definition** (WMO normal period — never re-window). The daily/annual/monthly activation files and `summer_avg_tmax_annual.csv` are **LIVING-extendable**: re-running with `ANALYSIS_YEARS` extended appends seasons under the same names |
| Consumers | `build_heat_operations_panel.py` (family 8) · the heat_activations report · Heat Tracker baseline **validation** (one-time cross-check) |

## 8. CJC report analyses (heat operations, indoor/outdoor, risk report)

The CJC reports are **one-time memos: FROZEN.** Their outputs (and the hazard-rank
tables that feed them) are published analyses and are never refreshed in place — if a
report is ever redone for a new period it's a new vintage (new subdir/filename). In practice these need no action during a routine refresh.

- Heat operations panel: `build_heat_operations_panel.py` → `run_heat_operations_regression.py` → `run_event_study.py` (inputs: SB601 operations, CCHCS measures, TPOP-1, air-cooling infra, violent incidents, `ca_facilities.csv`, `heat_activations_daily.csv`).
- Indoor/outdoor heat: `build_indoor_outdoor_analysis.py`, `build_improved_clustering.py` (inputs incl. `data/cdcr/indoor_outdoor_heat_2025.csv` — ⚠ **no in-repo builder**; document/script its upstream before it's needed again).
- Heat risk report: `analysis/CDCR_risk_indices/generate_heat_risk_report.py`.
- ⚠ The `heat_activations` report has no in-repo builder script.

## 9. CDCR heat risk index (what the Prison Heat Index consumes)

| Step | What |
|---|---|
| Rebuild | `analysis/CDCR_risk_indices/heat_risk_index.ipynb` (inputs: `cdcr_facilities.csv`, `heat_air_hazard.csv`, `indoor_outdoor_heat_2025.csv`) and `sensitivity_analysis.ipynb` |
| Outputs | `data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv`, `CDCR_heat_risk_sensitivity.csv` — **VERSIONED (semantic `index_version`, currently v0.3).** The index is a methodology artifact: the top-level file is always the **current** version and a re-cut **overwrites** it. Before overwriting, the notebooks archive the on-disk build (keyed by its own `index_version`) to `data/cdcr/archive/CDCR_heat_risk_*_vX.Y.csv`, so every shipped version stays retrievable. The `index_version` column identifies which build produced any row. See the changelog in `analysis/README.md`. |
| Consumers | PHI `build_app_data.py` · `generate_heat_risk_report.py` · `sensitivity_analysis.ipynb` |

## 10. Prison Heat Index app export (→ website repo)

| Step | What |
|---|---|
| Rebuild | `python3 analysis/app_export/build_app_data.py` — **only deliberately**, since it re-publishes; it reads the pinned 2025-vintage risk index and `_2025` columns |
| Outputs | `analysis/app_export/output/` (canonical) + copies into `../website`: `data/prison_heat_index.json`, `static/data/{prison_heat_index.json, prison_boundaries.geojson, ca_outline_simple.json}`, `content/prison-heat-index/<slug>.md` × 31 — **LIVING** (regenerated wholesale on each deliberate export) |
| After refresh | Nothing automatic. PHI moves to a new data vintage only when you edit `build_app_data.py` to read it (rule 2), then commit + push `website` |

## 11. Heat Tracker — this repo is only an input

**The Heat Tracker's build scripts live in its own repo** —
`ca-carceral-heat-tracker/pipeline/`. This repo just supplies two **inputs** the tracker
reads as a sibling checkout: `ca_facilities.csv` and `data/cdcr/cdcr_facilities.csv`.
Nothing here consumes the tracker's outputs, and the tracker's own data (baselines, bands,
slug registry, live feed) lives entirely in its repo. Its build/refresh runbook lives there
too (`ca-carceral-heat-tracker/pipeline/` + that repo's docs).

**What a refresh here means for the tracker:** when you re-scrape and rebuild
`cdcr_facilities.csv` / `ca_facilities.csv` (families 1–4), afterward go to the app repo
and rerun its builds against these updated CSVs (`pipeline/build_facilities.py`, plus
`build_baselines.py`/`build_historic_bands.py --only-missing` if the facility list
changed). Both checkouts must sit side-by-side for the app's static builds to find these
files. Then commit each repo; the app-repo commit triggers its Cloudflare rebuild, and
`git tag refresh-YYYY-MM` here (rule 3).

---

# Classification table

Every tracked output, with its frozen/living/versioned classification.

| Output | Class | Rationale |
|---|---|---|
| `data_sources/facilities/ca_facilities.csv` | LIVING | Current facility roster; consumers want "now" |
| `data/cdcr/cdcr_facilities.csv` | LIVING (vintaged columns FROZEN) | One row per facility stays current; `*_2025` columns are immutable, `*_2026` added alongside |
| **Re-scraped time series** — `cchcs_ipc.csv`, `cchcs_measures.csv`, `sb601_operations.csv`, `sb601_programs.csv`, `sco_staffing.csv`, `sco_staffing_avg.csv`, `restricted_housing.csv` | **LIVING (extendable)** | Each refresh re-scrapes the full history and the series grows. Filenames are stable (no baked-in year); advance a year with the single `LATEST_YEAR`/`FISCAL_YEAR` knob at the top of each scraper |
| `tpop1_institutions.csv`, `tpop1_summary.csv` | LIVING (extendable) | Month rows appended; no vintage in name |
| `specialized_beds` outputs, `cdcr_recidivism_los.csv`, `cdcr_avg_sentence_by_admission.csv` | LIVING (extendable) | Report-date/month rows appended |
| **Manual vintaged snapshots** — `CDCR_YYYY_pop_averages.csv`, `cdcr_in-custody-*_YYYY.csv`, `air_cooling_*_dec2025.csv`, `cchcs_mortality_2006-2024.csv`, MPAR extracts | FROZEN | Hand-made point-in-time snapshots; a new one lands alongside |
| `data/hazards/{heat_air,flood,drought}_hazard.csv` | LIVING | Rebuilt only when a source layer re-releases (unscheduled) |
| `data/allfacilities_climate_hazards.csv` | LIVING | Join of living inputs |
| `data_sources/hazards/heat/heat_activations_*.csv`, `summer_avg_tmax_annual.csv` | LIVING (extendable) | Seasons appended; the mean summer tmax baseline inside is definitionally fixed |
| `data_sources/hazards/heat/loca2_facility_heat.csv` | FROZEN (fixed projection product) | LOCA2-CA daily extraction (family 6b); the relative-threshold baselines are definitionally fixed. Regenerable from `extract_loca2_heat.py`; re-run only if the model set, cell rule, or thresholds change |
| `data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv`, `CDCR_heat_risk_sensitivity.csv` | **VERSIONED (current build)** | Semantic `index_version` (v0.3); top-level file is the current version and is overwritten on re-cut, with prior builds archived under `data/cdcr/archive/` and the app JSON under `analysis/app_export/output/archive/` |
| `data/cdcr/indoor_outdoor_heat_2025.csv` | FROZEN (manual, one-time) | Built once from a specific CDCR PDF for the memo; no builder script exists. ⚠ Gap: if indoor data is ever re-released, write a builder then — otherwise it never updates |
| `data/cdcr/CDCR_heat_risk_index_multiplicative.csv` | FROZEN (alternate method) | Intentional alternate index formulation, kept for possible future re-evaluation — not stale, do not delete |
| `data/ca_outline.json`, `ca_outline_simple.json` | LIVING (static asset) | No builder; effectively never changes |
| `analysis/cjc reports/**` outputs | **FROZEN (one-time memos)** | Published analyses; never refreshed in place |
| `analysis/CDCR_hazard_rank/*.csv` | FROZEN | Feed the frozen CJC memos |
| PHI export (`app_export/output/*`, website copies) | LIVING (deliberate rebuilds only) | Regenerated wholesale by `build_app_data.py` |
