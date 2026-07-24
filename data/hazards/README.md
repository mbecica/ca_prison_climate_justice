# Hazard Index Methods

Hazard indices for all 357 CA carceral facilities, built in `data_sources/hazards/` and joined in `analysis/hazards/join_climate_hazards.ipynb`. As of heat index **v0.2**, heat is **facility-level** — each facility carries its own LOCA2-CA grid cell and joins by `facilityid`. Flood and drought remain **tract-level** joins (via `tract_geoid`). This mixed basis is an improvement over the prior all-tract state (where heat was tract-level too) and is stated here plainly; flood and drought are the candidates for the same facility-level treatment in a later version.

VCP excludes census tracts with high group-quarters populations (including state prisons) from its composite scores, but the underlying raw indicators are available for all tracts and are used directly here.

**Scale convention:** composite indices are 0–100 (`_idx` suffix). Raw sub-components stay in natural units (days, °C, %).

---

## Heat and Air Quality Index (v0.2)

**Notebook:** `data_sources/hazards/heat/heat_hazard.ipynb`

Combines daytime heat, nighttime heat recovery failure, and air quality into two comparable indices — current and mid-century — for all 357 facilities. Temperature indicators are drawn from a LOCA2-CA daily extraction (`loca2_facility_heat.csv`), not the tract product used in v0.1.

- **Hot days (blended)** — a 50/50 blend of a facility-relative threshold (days above the facility's mean summer daily-max + 10°F, 1981–2010 baseline) and an absolute threshold (days over 90°F), each max-normalized before blending. The 50% weight is a parameter.
- **Warm nights** — April–October nights above the 95th percentile of the facility's 1961–1990 April–October minimum-temperature distribution (OEHHA convention).

The blended daytime term and the warm-night term are each max-normalized across the facilities and both periods (dividing by the cross-period max, not min-max), so a facility with no exceedances scores 0. The two are averaged, then multiplied by an air-quality modifier: `H = temp × (1 + 0.30·AQI_norm/100)`, ×1.0 at AQI = 0. AQI is held at historic CalEnviroScreen values for both periods; β = 0.30 is a parameter.

**Provenance.** LOCA2-CA daily, accessed anonymously from the cadcat S3 zarr store (`s3://cadcat/loca2/ucsd/...`, grid `d03`, ≈3 km cells). The ensemble is **14 models** (HadGEM3-GC31-LL dropped — no ssp370 on cadcat), pooled by **model democracy**: counts are computed per member, averaged within model, then across models, so each model carries weight 1/14 regardless of how many members it contributes. Threshold and count are computed **per member, then pooled** — computing a threshold from the ensemble mean would smooth away the daily variance the exceedance count measures. Historic = 1981–2010, mid-century = 2041–2070 (ssp370). See `data_sources/hazards/README.md` for the spatial cell-assignment rule and the reproduction-gate result against the published Cal-Adapt layer.

| Component | Current | Mid-century | Source |
| :--- | :--- | :--- | :--- |
| Hot days (blended) | 50/50 blend: days above facility summer-mean tmax + 10°F (relative, 1981–2010) ⊕ days over 90°F (absolute) | Same thresholds (2041–2070) | LOCA2-CA daily (SSP3-7.0) via cadcat |
| Warm nights | Apr–Oct nights > P95 of facility 1961–1990 Apr–Oct tmin | Same threshold (2041–2070) | LOCA2-CA daily (SSP3-7.0) via cadcat |
| Air quality | Multiplicative modifier `× (1 + 0.30·AQI/100)` | Held at historic — no tract-level projection | CalEnviroScreen 5.0, 2025 |

### Columns in `heat_air_hazard.csv`

Keyed on `facilityid`; 357 facilities. The composite here is normalized across all 357; the CDCR index recomputes the same equation across its 31 facilities.

| Column | Description |
| :--- | :--- |
| `facilityid` / `name` / `cdcr_code` / `tract_geoid` | Facility keys (`cdcr_code` blank for non-CDCR facilities) |
| `loca2_days_over_avg_plus10_historic` / `_midcentury` | Annual days above facility summer-mean tmax + 10°F |
| `loca2_nights_over_p95_historic` / `_midcentury` | Annual Apr–Oct nights above facility 1961–1990 Apr–Oct P95 tmin |
| `loca2_days_over_90_historic` / `_midcentury` | Annual days over an absolute 90°F — display metric, not scored |
| `loca2_avg_summer_tmax_f` | Facility mean summer (Jun–Aug) daily-max, °F — hot-day baseline (auditability) |
| `loca2_p95_tmin_f` | Facility P95 of 1961–1990 Apr–Oct tmin, °F — warm-night baseline (auditability) |
| `AQI_norm` | AQI percentile (0–100) from CalEnviroScreen ozone, PM2.5, diesel sub-indicators |
| `heat_hazard_historic_idx` | Heat & AQI Hazard Index (0–100), current, normalized across all 357 |
| `heat_hazard_midcentury_idx` | Heat & AQI Hazard Index (0–100), mid-century, normalized across all 357 |

The full three-period facility grid (including end-century and absolute-threshold counts) lives in the standalone data product `data_sources/hazards/heat/loca2_facility_heat.csv`. Flood and drought remain **two-period** (`_historic`/`_midcentury`); end-century is out of scope for the multi-hazard comparison because flood and drought have no end-century layer.

---

## Flood Hazard Index

**Notebook:** `data_sources/hazards/flood_hazard.ipynb`

Follows VCP's composite flood methodology. Combines BAM floodplain exposure (full weight) and very wet day frequency (half weight). Current hazard uses the 100-year floodplain; mid-century uses the 500-year floodplain and projected very wet day frequency (2045–2074). The 500-year floodplain is used as the mid-century proxy because climate change is expected to make currently rare flood events more frequent, bringing the effective return period closer to what the 100-year floodplain represents today.

| Component | Current | Mid-century | Weight | Source |
| :--- | :--- | :--- | :--- | :--- |
| Floodplain | % tract in DWR BAM 100-year floodplain | % tract in DWR BAM 500-year floodplain | 1.0 | DWR BAM via VCP |
| Very wet days | % years classified as very wet (historic) | % years very wet (2045–2074) | 0.5 | LCI VCP / LOCA 2 CA Hybrid SSP 370 |

### Columns in `flood_hazard.csv`

| Column | Description |
| :--- | :--- |
| `GEOID` | 11-digit census tract GEOID |
| `flood_bam_100_pct` | % of tract area within DWR BAM 100-year floodplain |
| `flood_bam_500_pct` | % of tract area within DWR BAM 500-year floodplain |
| `flood_verywet_pre_pct` | % of historic years classified as very wet (sub-component only, not in final output) |
| `flood_verywet_fut_pct` | % of projected years classified as very wet, 2045–2074 (sub-component only, not in final output) |
| `flood_hazard_idx_norm` | Flood Hazard Index (0–100), current → renamed `flood_hazard_historic_idx` in output |
| `flood_hazard_fut_idx_norm` | Flood Hazard Index (0–100), mid-century → renamed `flood_hazard_midcentury_idx` in output |

---

## Drought Hazard Index

**Notebook:** `data_sources/hazards/drought_hazard.ipynb`

Follows VCP's three-indicator drought methodology. Three equal-weight components, each normalized min-max across both time periods combined before averaging. Temperature change drives the temporal difference between current and mid-century scores; WSV and precip/demand ratio are static across timescales.

| Component | Current | Mid-century | Source |
| :--- | :--- | :--- | :--- |
| Jun–Aug temp change (°C above baseline) | 2015–2044 | 2045–2074 | LCI VCP / LOCA 2 CA Hybrid SSP 370 |
| Water Shortage Vulnerability (WSV) | DWR physical risk score — same for both timescales | ← | VCP / DWR WSV Tool (updated 2024) |
| Precip/demand ratio (inverted) | 30-yr avg precip ÷ (population + cultivated land) — same for both | ← | VCP / PRISM 1991–2020 + DWR Crop Mapping |

SPEI-12 delta is included as a standalone variable but not in the composite: SPEI accounts for both precipitation deficit and evapotranspiration, but a meaningful historic equivalent cannot be derived because the historic baseline is ~5% by construction of the 5th-percentile threshold. Uses SSP 2-4.5 (moderate emissions), per California's Fifth Climate Assessment (2026, forthcoming).

### Columns in `drought_hazard.csv`

| Column | Description |
| :--- | :--- |
| `GEOID` | 11-digit census tract GEOID |
| `Dr_delta_JA_max_pre` | Change in Jun–Aug mean max temp (°C above baseline), current (2015–2044) → renamed `drought_delta_temp_ja_historic` in output |
| `Dr_delta_JA_max_fut` | Change in Jun–Aug mean max temp (°C above baseline), mid-century (2045–2074) → renamed `drought_delta_temp_ja_midcentury` in output |
| `drought_delta_spei12_midcentury` | % change in SPEI-12 drought frequency from historic baseline to mid-century (2041–2070) |
| `Dr_WSV_average` | Water Shortage Vulnerability score (sub-component; not in final output — captured by index) |
| `Dr_precip_demand_ratio` | Precip/demand ratio (sub-component; not in final output — captured by index) |
| `drought_hazard_idx_norm` | Drought Hazard Index (0–100), current → renamed `drought_hazard_historic_idx` in output |
| `drought_hazard_fut_idx_norm` | Drought Hazard Index (0–100), mid-century → renamed `drought_hazard_midcentury_idx` in output |

---

## Wildfire Risk

**No composite index.** Wildfire hazard uses categorical classifications from CalFire, assigned via point-in-polygon join in `analysis/hazards/join_climate_hazards.ipynb`.

- **FHSZ:** Fire Hazard Severity Zone (Very High / High / Moderate / blank if unclassified) from SRA (2022) and LRA (2025) layers. SRA and LRA are mutually exclusive.
- **WUI:** Wildland-Urban Interface type (Intermix / Interface / Influence Zone / blank) from CalFire WUI boundaries.

Source files: `data_sources/hazards/wildfire/calfire_fhsz.geojson`, `data_sources/hazards/wildfire/Wildland_Urban_Interface.zip`.
