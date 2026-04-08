# Hazards Data Sources

Raw source data and processing notebooks for CA prison climate hazard indices. Tract-level processed outputs go to `data/hazards/`. See [`data/hazards/README.md`](../../data/hazards/README.md) for index methodology and column documentation.

---

## Urban Heat Island

Urban heat island (UHI) effect is tracked as an **exposure metric**, not added to the hazard estimate. Source: Benz & Burney (2021) daytime surface UHI anomaly (ΔT), MODIS land surface temperature (2010–2014), 95th-percentile summer daytime values. ΔT = local LST minus median rural background LST. Aggregated to 2010 census tracts for areas classified as "developed" in NLCD.

**Citation:** Benz SA, Burney JA. "Widespread race and class disparities in surface urban heat islands across the United States." *Earth's Future* 9(7):e2021EF002016. Harvard Dataverse, doi:10.7910/DVN/1F72FB. CC0 license.

**Full system coverage:** Direct tract match applied to all 357 CA carceral facilities via `tract_geoid`. 267 facilities matched directly; 8 CDCR state prisons added via buffer (see below) = 275 facilities total with `uhi_normalized`. 82 facilities remain null — primarily rural fire/conservation camps and remote county jails in census tracts classified as undeveloped in NLCD. Non-CDCR facilities receive direct tract match only; null values are not imputed.

**Files:**

- `benz_uhi_ca_tracts.csv` — 7,993 CA tracts, ΔT range −13.78 to +11.27°C
- `benz_uhi_ca_tracts.geojson` — simplified tract boundaries with ΔT joined; `simplify(tolerance=500, preserve_topology=True)` in EPSG:3857
- `benz_uhi_facilities.csv` — per-facility detail for CDCR state prisons (see below)

**Normalization:** Clamp negative ΔT to 0 (urban cooling = no additional UHI exposure). Divide by maximum clamped ΔT across all state prisons (7.247°C, CIM). Result is a 0–1 score (`uhi_normalized`).

### CDCR State Prisons — Buffer and Validation

9 CDCR state prisons had no direct Benz ΔT match because their census tracts are classified as predominantly undeveloped in NLCD despite being built-up facilities. Resolved using nearest-polygon-edge distance (EPSG:3310):

- **1-mile buffer (7 facilities):** COR, SATF, CIM, WSP, RJD, CVSP, ISP
- **Extended to 1.04 mi (CIW):** CDCR 2020 Sustainability Report Table 8 identifies CIW as 3rd highest UHII facility; Benz and VCP both miss it — CDCR corroboration used to justify the minor buffer extension
- **Still null (2 facilities):** CCI (4.4 mi to nearest tract), PVSP (2.2 mi) — imputed with system mean in the risk index

Results were validated against VCP `UHI_sc` and CDCR 2020 Sustainability Roadmap Table 8 (top five UHII facilities: CRC, CIM, CIW, CMF, SOL). VCP `UHI_sc` (binary field in `VCP_Tracts.geojson`) was not used as the primary metric due to 42% disagreement rate with Benz.

`benz_uhi_facilities.csv` columns:

| Column | Description |
| :--- | :--- |
| `cdcr_code` | Facility code |
| `benz_uhi_dt` | Raw ΔT (°C); negative = urban cooling below rural background |
| `benz_uhi_source` | `direct`, `buffer`, or `buffer_cdcr_corroborated` |
| `uhi_normalized` | 0–1 normalized score |

Facilities with `uhi_normalized ≥ 0.5`:

| Code | Raw ΔT | uhi_normalized | Source |
| :--- | ---: | ---: | :--- |
| CIM | +7.247 | 1.000 | buffer |
| NKSP | +4.548 | 0.628 | direct |
| CIW | +4.385 | 0.605 | buffer_cdcr_corroborated |
| SATF | +4.354 | 0.601 | buffer |
| SOL | +4.214 | 0.581 | direct |
| CMF | +4.214 | 0.581 | direct |
| COR | +4.188 | 0.578 | buffer |
| CRC | +4.140 | 0.571 | direct |
| WSP | +3.507 | 0.484 | buffer |

Facilities with `uhi_normalized = 0` (urban cooling or no positive ΔT): CAL, SQ, CTF, SVSP, LAC, RJD, ISP, CVSP, FOL, FWF, SAC, ASP, CEN, SCC.

---

## Historic Observed Temperatures — CDCR State Prisons

Daily and annual observed outdoor temperatures at CDCR state prisons, derived from gridMET 4km gridded daily maximum temperature (`tmmx`). Scraper: `scrapers/extract_gridmet_heat.py`.

**Source:** Abatzoglou, J.T. (2013). Development of gridded surface meteorological data for ecological applications and modelling. *International Journal of Climatology*, 33(1), 121–131. doi:10.1002/joc.3413. Data accessed via [climatologylab.org/gridmet.html](http://www.climatologylab.org/gridmet.html).

**Facility coverage:** 32 active CDCR state prisons. CAC and FWF excluded throughout. CVSP included for 2016–2023 only (closed mid-2024).

### Threshold definitions

| Column | Definition | Note |
| :--- | :--- | :--- |
| `over_90f` / `days_over_90f` | Outdoor tmax ≥ 90°F | Corresponds to CDCR Heat Pathology Plan Stage I outdoor trigger |
| `over_95f` / `days_over_95f` | Outdoor tmax ≥ 95°F | Corresponds to Stage III outdoor threshold; **Stage III protocol is triggered by indoor temperature** — outdoor is a proxy only |
| `skarha10` / `days_skarha10` | Outdoor tmax ≥ facility mean summer tmax + 10°F (baseline: 1991–2020 Jun–Aug mean) | Skarha et al. (2023) marginal mortality metric; the only threshold with a mortality calibration |

The 90°F and 95°F thresholds have no direct mortality calibration in the literature — they are regulatory exposure metrics only. The Skarha 10°F threshold carries a statistically significant 5.2% all-cause mortality association (see `heat_hazard.ipynb`).

### Files

| File | Description | Years | Source |
| :--- | :--- | :--- | :--- |
| `heat_activations_daily.csv` | Daily tmax (°F) and threshold flags (`over_90f`, `over_95f`, `skarha10`) per facility | 2016–2025 | gridMET (Abatzoglou, 2013) |
| `heat_activations_annual.csv` | Annual count of days over 90°F, days over 95°F, and Skarha 10°F threshold exceedances per facility | 2016–2025 | gridMET (Abatzoglou, 2013) |
| `heat_activations_monthly.csv` | Monthly count of days over 90°F and 95°F per facility per year | 2016–2025 | gridMET (Abatzoglou, 2013) |
| `summer_avg_tmax_annual.csv` | Mean Jun–Aug daily tmax (°F) per facility per year | 1990–2025 | gridMET (Abatzoglou, 2013) |

---

## References

Abatzoglou, J.T. (2013). Development of gridded surface meteorological data for ecological applications and modelling. *International Journal of Climatology*, 33(1), 121–131. doi:10.1002/joc.3413

Benz SA, Burney JA. (2021). Widespread race and class disparities in surface urban heat islands across the United States. *Earth's Future*, 9(7), e2021EF002016. Harvard Dataverse, doi:10.7910/DVN/1F72FB. CC0 license.

California Department of Corrections and Rehabilitation. (2020). Sustainability Roadmap. CDCR.

Governor's Office of Land Use and Climate Innovation. (2025). Vulnerable Communities Platform [Dataset]. https://opr.ca.gov/planning/vulnerable-communities-platform/
