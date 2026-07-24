# Indoor vs. Outdoor Heat Gap — AB 2499 Analysis

`analysis/indoor_outdoor_heat_2025.html` — interactive D3 report analyzing the discrepancy between outdoor and indoor heat at 31 CDCR adult prisons in 2025, framed around AB 2499 (introduced February 20, 2026; 85°F indoor reporting threshold; 3 pilot monitoring locations by July 2027).

`data/indoor_outdoor_heat_2025.csv` — flat data table, 31 rows × 19 columns, sorted by indoor-to-outdoor 78°F ratio descending.

## Clustering

k=3 k-means on 9 z-score standardized features: year_opened, pct_ref, pct_evap, outdoor_78f, indoor_78f, uhi_normalized, elevation_m, latitude, hotnights_pre_pct.

| Cluster | Label | n | Facilities |
| :--- | :--- | :--- | :--- |
| A | Thermal Trap | 8 | CCI CMC CTF FOL PBSP RJD SQ SVSP |
| B | Full Mechanical AC | 5 | CAL CEN CHCF CIM ISP |
| C | Predominantly Evaporative Cooling | 18 | ASP CCWF CIW CMF COR CRC HDSP KVSP LAC MCSP NKSP PVSP SAC SATF SCC SOL VSP WSP |

Pearson r (indoor 78°F days vs outdoor 78°F days, 2025):
- Cluster A: r=+0.806, p=0.016 (only statistically significant result)
- Cluster B: r=−0.173, p=0.78
- Cluster C: r=+0.104, p=0.68

## Building Envelope

Roofing and building envelope project status per facility drawn from:
- CDCR MPAR capital project records (2020–2025)
- LAO budget analyses (2017–2025) for named appropriations
- CDCR SIFC Roof Replacement Needs page (2018, phased program)
- Contractor portfolios and procurement records for pre-2020 partial projects (FOL 2016, SQ 2019)
- DOF Budget Change Proposals for funding/reappropriation status (CMF)

Pre-2017 roofing was funded through a pooled annual special repair appropriation with no facility-level legislative itemization; projects were largely performed by inmate day labor with no public procurement record. The CDCR phased statewide roof replacement program was established in 2017. The 2023–2024 CDCR Master Plan Annual Reports characterize prisons built in the 1980s–1990s as having original single-ply roof systems beyond their useful life; ASP (1987), MCSP (1987), PBSP (1989), and WSP (1991) appear to be on original roofs.

## Data Sources

| Column | Source |
| :--- | :--- |
| `days_indoor_above_78f_2025` | CDCR Air Cooling Pilot Program Supplemental Report, January 2026, Table 1 |
| `days_outdoor_above_78f_2025`, `days_outdoor_90f_2025` | gridMET daily tmax (tmmx), University of Idaho, 2025. Days computed May–October. |
| `pct_hu_mechanical/evaporation/ventilation` | Reuters FOIA AHU data (June 2025); CTF corrected per CDCR email |
| `uhi_normalized` | Benz & Burney (2021), same as facilities dataset |
| `hotnights_pre_pct` | CalEnviroScreen 4.0 / OEHHA |
| `elevation_m` | USGS National Elevation Dataset (EPQS API) |
| `avg_tmin_f_2025` | gridMET daily tmin (tmmn), May–October 2025 |
| `envelope_work` | CDCR MPAR, LAO budget analyses, SIFC Roof Replacement Needs page, contractor records |
