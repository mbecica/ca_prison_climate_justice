# Hazards Data

Hazard datasets and processing notebooks for the CA prison climate justice analysis. Tract-level indices cover all 357 carceral facilities via census tract join. Facility-level heat data (gridMET) covers CDCR state prisons only.


## Hazard Index Methods

All four tract-level indices are computed in the notebooks above and joined to `data/cdcr_facilities.csv` via `tract_geoid`. Each index is normalized 0–100. VCP excludes census tracts with high group-quarters populations (including state prisons) from its composite scores, but the underlying raw indicators are available for all tracts and are used directly here.

### Heat and Air Quality Index

**Notebook:** `heat_hazard.ipynb`

Combines daytime heat, nighttime heat recovery failure, and air quality into a single index. Each component is normalized min-max across both time periods combined before averaging. Temperature carries 2/3 collective weight; AQI carries 1/3.

| Component | Current | Mid-century | Source |
| :--- | :--- | :--- | :--- |
| Daytime heat | Days over 90°F (historic) | Days over 90°F (2041–2070) | Cal-Adapt |
| Hot nights | % nights > 98th pctl of tract's own historical min temp (2015–2044) | Same threshold (2045–2074) | VCP / LOCA 2 CA Hybrid SSP 370 |
| Air quality | AQI (ozone, PM2.5, diesel) | Held at historic — no tract-level projection available | CalEnviroScreen 5.0 |

Hot nights use VCP's relative definition (per-tract 98th percentile of historical minimum temperature), which accounts for local acclimatization rather than a fixed absolute threshold.

**Output columns in `data/cdcr_facilities.csv`:** `heat_hazard_idx_norm` (current), `heat_hazard_fut_idx_norm` (mid-century).

### Flood Hazard Index

**Notebook:** `flood_hazard.ipynb`

Follows VCP's composite flood methodology. Combines floodplain exposure (full weight) and very wet day frequency (half weight); normalized min-max across both time periods combined.

| Component | Current | Mid-century | Source |
| :--- | :--- | :--- | :--- |
| Floodplain | % tract in DWR BAM 100-year floodplain | % tract in DWR BAM 500-year floodplain | DWR BAM via VCP |
| Very wet days | % years classified as very wet (historic) | % years very wet (2045–2074) | VCP / LOCA 2 CA Hybrid SSP 370 |

The 500-year floodplain is used as the mid-century proxy because climate change is expected to make currently rare flood events more frequent, bringing the effective return period closer to what the 100-year floodplain represents today.

**Output columns:** `flood_hazard_idx_norm` (current), `flood_hazard_fut_idx_norm` (mid-century).

### Wildfire Risk

**Notebook:** join step only — FHSZ and WUI classifications are point-in-polygon joins, not index calculations.

Fire Hazard Severity Zone (FHSZ) from CalFire, assigned via point-in-polygon against SRA (2022) and LRA (2025) layers. WUI type from CalFire WUI boundaries. Facilities outside all classified zones are unclassified (lowest risk). SRA and LRA are mutually exclusive.

**Output columns:** `fhsz` (Very High / High / Moderate / blank), `fhsz_responsibility` (SRA / LRA / blank), `wui_type` (Intermix / Interface / Influence Zone / blank).

### Drought Hazard Index

**Notebook:** `drought_hazard.ipynb`

Follows VCP's three-indicator drought methodology. Three equal-weight components, all normalized min-max across both time periods combined.

| Component | Current | Mid-century | Source |
| :--- | :--- | :--- | :--- |
| Jun–Aug temp change (°C above baseline) | 2015–2044 | 2045–2074 | VCP / LOCA 2 CA Hybrid SSP 370 |
| Water Shortage Vulnerability (WSV) | DWR physical risk score — same for both timescales | ← | VCP / DWR WSV Tool (updated 2024) |
| Precip/demand ratio (inverted) | 30-yr avg precip ÷ (population + cultivated land) — same for both | ← | VCP / PRISM 1991–2020 + DWR Crop Mapping |

Temperature change drives the temporal difference between current and mid-century scores; WSV and precip/demand ratio are static across timescales. The precip/demand ratio is inverted before combining (higher ratio = less water stress = lower drought risk).

SPEI-12 delta is included as a standalone variable (`drought_delta_spei12_midcentury`) but not in the composite: SPEI accounts for both precipitation deficit and evapotranspiration, but a meaningful historic equivalent cannot be derived because the historic baseline is ~5% by construction of the 5th-percentile threshold. Uses SSP 2-4.5 (moderate emissions), per California's Fifth Climate Assessment (2026, forthcoming).

**Output columns:** `drought_hazard_idx_norm` (current), `drought_hazard_fut_idx_norm` (mid-century).

---

## Urban Heat Island

Urban heat island (UHI) effect is tracked as an **exposure metric**, not added to the hazard estimate.

### Benz & Burney (2021) — daytime surface heat anomaly

**Citation:** Benz SA, Burney JA. "Widespread race and class disparities in surface urban heat islands across the United States." *Earth's Future* 9(7):e2021EF002016. Harvard Dataverse, doi:10.7910/DVN/1F72FB. CC0 license.

**Method:** MODIS land surface temperature (2010–2014), 95th-percentile summer daytime values. ΔT = local LST minus median rural background LST. Aggregated to 2010 census tracts for areas classified as "developed" in NLCD.

**Coverage gap:** 14 facilities initially had no Benz ΔT because their census tracts are classified as predominantly undeveloped in NLCD despite being built-up facilities. Resolved using nearest-polygon-edge distance (EPSG:3310) to find the nearest tract with Benz data:

- **1-mile buffer (7 facilities):** COR, SATF, CIM, WSP, RJD, CVSP, ISP
- **Extended to 1.04 mi (CIW):** CDCR 2020 Sustainability Report Table 8 identifies CIW as 3rd highest UHII facility; Benz and VCP both miss it — CDCR corroboration used to justify the minor buffer extension
- **Still null (2 CDCR state prisons):** CCI (4.4 mi to nearest tract), PVSP (2.2 mi)

**Scope of buffer:** The 1-mile buffer is applied only to CDCR state prisons, where results were validated against VCP UHI_sc and CDCR 2020 Table 8. Non-CDCR facilities receive direct tract match only; null values are not imputed.

**Full system coverage:** Direct match applied to all 357 CA carceral facilities via `tract_geoid`. 267 matched directly; 8 CDCR state prisons added via buffer = 275 facilities total with `uhi_normalized`. 82 facilities remain null — primarily rural fire/conservation camps and remote county jails in census tracts classified as undeveloped in NLCD.

**Files:**

- `benz_uhi_ca_tracts.csv` — 7,993 CA tracts, ΔT range −13.78 to +11.27°C
- `benz_uhi_ca_tracts.geojson` — simplified tract boundaries with ΔT joined; `simplify(tolerance=500, preserve_topology=True)` in EPSG:3857
- `benz_uhi_facilities.csv` — per-facility detail (32 state prisons):

| Column | Description |
| :--- | :--- |
| `cdcr_code` | Facility code |
| `benz_uhi_dt` | Raw ΔT (°C); negative = urban cooling below rural background |
| `benz_uhi_source` | `direct`, `buffer`, or `buffer_cdcr_corroborated` |
| `uhi_normalized` | 0–1 normalized score (see below) |

**Normalization:** Clamp negative ΔT to 0 (urban cooling = no additional UHI exposure). Divide by maximum clamped ΔT across all state prisons (7.247°C, CIM). Result is a 0–1 score added to `data/cdcr_facilities.csv` as `uhi_normalized`.

**Facilities with uhi_normalized ≥ 0.5:**

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


### VCP UHI_sc

**Source:** California Vibrant Communities Project (VCP), LCI/Governor's Office of Land Use and Climate Innovation. Field `UHI_sc` (binary: 0 = No, 2 = Yes) in `VCP_Tracts.geojson`. Full coverage for all 31 state prisons. Not used as primary metric due to 42% disagreement rate with Benz.

### CDCR 2020 Sustainability Report — Table 8

Top five facilities located in urban heat islands (sorted by highest UHII): **CRC, CIM, CIW, CMF, SOL**. Source: CDCR 2020 Sustainability Roadmap, Chapter 1, p. 22. UHII methodology not specified. Only top 5 published; absence from list does not mean no UHI.

---

## Heat Activation Days (CDCR Facility-Level)

Daily and annual counts of outdoor heat threshold exceedances at CDCR state prisons, derived from gridMET 4km gridded daily maximum temperature (tmmx). Scraper: `scrapers/extract_gridmet_heat.py`.

**Facility coverage:** 32 active CDCR state prisons. CAC and FWF excluded throughout. CVSP included for 2016–2023 only (closed mid-2024).

### Threshold definitions

| Column | Definition | Note |
| :--- | :--- | :--- |
| `over_90f` / `days_over_90f` | Outdoor tmax ≥ 90°F | Corresponds to CDCR Heat Pathology Plan Stage I outdoor trigger |
| `over_95f` / `days_over_95f` | Outdoor tmax ≥ 95°F | Corresponds to Stage III outdoor threshold; **Stage III protocol is triggered by indoor temperature** — outdoor is a proxy only |
| `skarha10` / `days_skarha10` | Outdoor tmax ≥ facility mean summer tmax + 10°F (baseline: 1991–2020 Jun–Aug mean) | Skarha et al. (2023) marginal mortality metric; the only threshold with a mortality calibration |

The 90°F and 95°F thresholds have no direct mortality calibration in the literature — they are regulatory exposure metrics only. The Skarha 10°F threshold carries a statistically significant 5.2% all-cause mortality association (see `heat_hazard.ipynb`).

### Files

| File | Description |
| :--- | :--- |
| `heat_activations_daily.csv` | Daily tmax (°F) and threshold flags (`over_90f`, `over_95f`, `skarha10`) per facility, 2016–2025 |
| `heat_activations_annual.csv` | Annual count of days over 90°F, days over 95°F, and Skarha 10°F threshold exceedances per facility |
| `heat_activations_monthly.csv` | Monthly count of days over 90°F and 95°F per facility per year |
| `summer_avg_tmax_annual.csv` | Mean Jun–Aug daily tmax (°F) per facility per year, 1990–2025 |
