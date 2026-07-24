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

## Humidity and evaporative cooling capacity

An evaporative ("swamp") cooler cannot cool air below the wet-bulb temperature, so its physical
capacity is the wet-bulb depression `wbd = tmax − twb` (°F). `facility_wetbulb_2025.csv`
(`extract_wetbulb.py`) reports `wbd`, the delivered supply-air temperature `tmax − ε·wbd`
(ε = 0.70/0.80/0.85 direct-evaporative effectiveness), and the count of days a cooler cannot
reach 78°F/85°F, per facility over May–Oct 2025, from gridMET daily-min relative humidity paired
with the coincident daily-max temperature (Stull 2011 wet-bulb).

In California's dry heat, humidity does not limit evaporative cooling. Wet-bulb depression at the
predominantly-evaporative facilities (evaporative the dominant cooling mode, n=15) is 20–28°F.
Every facility reaches 85°F on every summer day (`days_evap_cannot_reach_85f` = 0 at ε=0.80, and
still 0 at the conservative ε=0.70), and reaches 78°F on all but ≤2 days. The large cannot-reach
counts (50–62 days) belong to CAL/CEN/ISP — full-mechanical Imperial Valley prisons that do not
use evaporative cooling and are limited by dry-bulb magnitude.

Humidity also does not explain the indoor-day spread within the predominantly-evaporative group
(range 1–159 days). Correlations with `days_indoor_above_78f_2025`:

| predictor | r | p |
| :--- | ---: | ---: |
| wet-bulb depression (`wbd`) | +0.31 | 0.26 |
| evaporative share × `wbd` (effective evaporative capacity) | +0.17 | 0.55 |
| evaporative share | −0.10 | 0.73 |

The wet-bulb depression is null and, where it trends, drier facilities have slightly *more* indoor
hot days — dryness coincides with Central Valley heat, the opposite of a humidity limitation. The
spread belongs to building envelope, cooler sizing and condition, operations, or occupancy. LAC's
low indoor/outdoor ratio (0.241) is not a humidity effect: LAC is the driest of the 31 (`wbd`
30.4°F) but COR is equally dry (`wbd` 26.9°F) with a ratio of 0.975. Humidity is therefore left
out of the clustering, the regression, and the risk index; the clustering stays k=3 on the
feature set above.

Humidity as a *hazard* is separately settled: Skarha et al. (2023) tested heat index and WBGT
against carceral mortality and neither improved on dry-bulb tmax.

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
| `facility_wetbulb_2025.csv` (`wbd_mean_f_may_oct`, `days_evap_cannot_reach_{78,85}f_eps{70,80,85}_may_oct`, …) | gridMET daily-min/max relative humidity (rmin/rmax), University of Idaho, 2025, paired with gridMET tmax; wet-bulb via Stull (2011). Built by `extract_wetbulb.py`. |
