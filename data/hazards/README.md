# Hazard Index Methods

Tract-level hazard indices for all 357 CA carceral facilities. Each index is built in `data_sources/hazards/` and joined to facilities in `analysis/hazards/join_climate_hazards.ipynb` via `tract_geoid`.

VCP excludes census tracts with high group-quarters populations (including state prisons) from its composite scores, but the underlying raw indicators are available for all tracts and are used directly here.

**Scale convention:** composite indices are 0–100 (`_idx` suffix). Raw sub-components stay in natural units (days, °C, %).

---

## Heat and Air Quality Index

**Notebook:** `data_sources/hazards/heat_hazard.ipynb`

Combines daytime heat, nighttime heat recovery failure, and air quality into two comparable indices — current and mid-century. Each temperature indicator is normalized min-max across both time periods combined. Hot nights use VCP's relative definition (% of nights exceeding the 98th percentile of each tract's own historical minimum temperature), which accounts for local acclimatization. AQI is held at historic CalEnviroScreen values for both indices, as tract-level air quality cannot be reliably projected. All three components carry equal weight, giving temperature 2/3 collective weight and AQI 1/3.

| Component | Current | Mid-century | Source |
| :--- | :--- | :--- | :--- |
| Daytime heat | Days over 90°F (1991–2020) | Days over 90°F (2041–2070) | Cal-Adapt, LOCA 2 downscaled |
| Hot nights | % nights > 98th pctl of tract's own historical min temp (2015–2044) | Same threshold (2045–2074) | LCI VCP / LOCA 2 CA Hybrid SSP 370 |
| Air quality | AQI from ozone, PM2.5, diesel percentiles | Held at historic — no tract-level projection | CalEnviroScreen 5.0, 2025 |

### Columns in `heat_air_hazard.csv`

| Column | Description |
| :--- | :--- |
| `GEOID` | 11-digit census tract GEOID |
| `uhi_normalized` | Urban heat island score (0–1). See `data_sources/hazards/README.md` for UHI methodology. |
| `days_over_90_historic` | Annual days over 90°F, 1991–2020 average |
| `days_over_90_midcentury` | Annual days over 90°F, 2041–2070 projected |
| `delta_90` | Change in annual days over 90°F (mid-century minus historic) |
| `hotnights_pre_pct` | % of nights exceeding tract 98th-pctl min temp, current (2015–2044) |
| `hotnights_fut_pct` | % of nights exceeding tract 98th-pctl min temp, mid-century (2045–2074) |
| `AQI_norm` | AQI percentile (0–100) from CalEnviroScreen ozone, PM2.5, diesel sub-indicators |
| `heat_hazard_idx_norm` | Heat & AQI Hazard Index (0–100), current → renamed `heat_hazard_historic_idx` in output |
| `heat_hazard_fut_idx_norm` | Heat & AQI Hazard Index (0–100), mid-century → renamed `heat_hazard_midcentury_idx` in output |

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
