# Analysis

Notebooks and scripts are in this directory. Outputs are written to `data/`.

## Heat Activation Days

Daily maximum temperatures at each CDCR state prison are sourced from gridMET (University of Idaho, 4km gridded daily tmax, 1991–2025). See `scrapers/extract_gridmet_heat.py`. Outputs in `data_sources/hazards/`:

| File | Description |
| :--- | :--- |
| `heat_activations_daily.csv` | Daily tmax (°F) and threshold flags per facility, 2016–2025 |
| `heat_activations_annual.csv` | Annual count of days over 90°F, days over 95°F, and Skarha 10° exceedance days per facility |
| `heat_activations_monthly.csv` | Monthly count of days over 90°F and days over 95°F per facility per year |

Outdoor temperature thresholds:

| Column | Definition | Note |
| :--- | :--- | :--- |
| `over_90f` / `days_over_90f` | Outdoor tmax ≥ 90°F | Corresponds to CDCR Heat Pathology Plan Stage I outdoor trigger |
| `over_95f` / `days_over_95f` | Outdoor tmax ≥ 95°F | Corresponds to Stage III outdoor threshold; **Stage III protocol is triggered by indoor temperature**, so this column is an outdoor proxy only |
| `skarha10` / `days_skarha10` | Outdoor tmax ≥ facility mean summer tmax + 10°F (baseline: 1991–2020 Jun–Aug mean) | Skarha et al. (2023) marginal mortality metric |

### Outdoor vs. Indoor Temperature Gap

The CDCR Heat Pathology Plan Stage I and Stage III thresholds are defined by **indoor** housing unit temperatures (≥ 90°F and ≥ 95°F respectively). Outdoor gridMET data is used here as a proxy for exposure and trend analysis, but outdoor temperatures systematically overstate the number of days that cross indoor thresholds.

Available evidence on the outdoor-to-indoor gap:

**CalMatters CPRA data (one unnamed prison, 2023–2024):**

| Year | Outdoor days ≥ 90°F | Indoor days ≥ 90°F | Indoor days ≥ 95°F |
| :--- | :--- | :--- | :--- |
| 2023 | 166 | 59 | 20 |
| 2024 | 182 | 86 | 46 |

Indoor days at ≥ 90°F were roughly 35–47% of outdoor days at the same threshold in these two years.

**OIG audit, August 2022–October 2023 (Corcoran, High Desert, Lancaster):**

| Prison | Housing units tested | Units with ≥ 1 day over 89°F | Most days over 89°F in a single unit |
| :--- | :--- | :--- | :--- |
| High Desert | 27 | 3 | 1 |
| Lancaster | 29 | 10 | 2 |
| Corcoran | 33 | 23 | 23 |

Source: California Office of the Inspector General, heat log audit.

## Summary Graphs

Interactive, print-readable D3 charts in `analysis/heat_activation_charts.html`. All charts use outdoor gridMET tmax as the exposure metric (see outdoor vs. indoor gap note above).

### Heat activation days (2016–2025)

- **Annual line chart** — total facility-days ≥ 90°F and ≥ 95°F across all 32 active prisons per year, 2016–2025
- **Per-facility horizontal bar** — average annual days ≥ 90°F per facility over the 10-year period
- **Per-facility line chart** — days ≥ 90°F per facility per year; color encodes cumulative outdoor heat exposure (light gray = low, dark red = high)

Summary statistics (2016–2025):
- Total facility-days ≥ 90°F outdoor: 27,722
- Average annual facility-days ≥ 90°F: 2,772
- Facilities with any day ≥ 90°F: 32 of 32

### Historical summer temperature (1990–2025)

Summer average tmax (mean Jun–Aug daily maximum temperature) per facility per year, 1990–2025. Source: gridMET annual tmax files for 1990–2015 (downloaded and deleted); `heat_activations_daily.csv` for 2016–2025. Scraper: `scrapers/extract_gridmet_summer_avg.py`. Output: `data_sources/hazards/summer_avg_tmax_annual.csv`.

- **System-wide average line** — mean Jun–Aug tmax across all facilities, 1990–2025
- **Per-facility line chart** — one line per facility, same red color scale as heat activation charts; bold black system average overlay

Period averages (system-wide):

| Period | Avg summer tmax |
| :--- | :--- |
| 1990–1999 | 90.43°F |
| 2000–2009 | 91.45°F |
| 2010–2019 | 91.97°F |
| 2020–2025 | 91.92°F |

First 5-year period (1990–1994) vs. last 5-year period (2021–2025): **+1.32°F**. Year-over-year variance is high; period averages are more stable. Single hottest year: 2017 (93.73°F). Single coolest year: 1991 (88.80°F).

### Population impacts — age (2025)

Person-days = facility population in age bracket × days outdoor tmax ≥ 90°F at that facility, 2025. Age bracket populations from CDCR Population Data Set 2025 monthly averages.

| Age group | People | Person-days ≥ 90°F | Avg days/person |
| :--- | :--- | :--- | :--- |
| 50–59 | 14,163 | 1,019,387 | 72.0 |
| 60–69 | 9,036 | 588,907 | 65.2 |
| 70–79 | 2,746 | 161,970 | 59.0 |
| 80+ | 543 | 34,786 | 64.1 |
| **50+ total** | **26,487** | **1,805,051** | **68.1** |

Per-facility grouped bar chart (top 12 by total 50+ person-days) also shown, with estimated % refrigeration cooling as a sub-label on each facility axis tick.

### Population impacts — CCHCS health risk category (2025)

Person-days by CCHCS risk tier: High Risk Priority 1, High Risk Priority 2, and Medium Risk. Top 12 facilities selected and sorted by combined P1+P2 person-days. Health risk percentages from CCHCS IPC Dashboard (most recent 2025 month per facility).

**Note on selection:** Sorting by total person-days and sorting by P1+P2 person-days produce different top-12 sets. Facilities with high heat exposure but low clinical acuity (ASP, NKSP, WSP — with near-zero P1/P2) rank highly on total but drop out when sorting by P1+P2. Facilities with high clinical complexity but moderate heat exposure (CMF, SOL, SAC) enter the P1+P2 top-12 but not the total top-12. The chart uses P1+P2 combined as the primary sort.

### Cooling infrastructure (Reuters 2025 FOIA data)

Source: `data_sources/facilities/CDCR/Reuters_CDCR_cooling.xlsx` — CDCR AHU equipment data provided to Reuters under FOIA, June 2025. 1,556 AHU records; 563 unique (facility, building) combinations across 31 facilities. Mixed-type buildings (8 total) are assigned by refrigeration priority.

**CTF correction:** Reuters FOIA had CTF coded as "Refrigeration Cooling." CDCR clarified by email (June 2025) that CTF units are not refrigerated — corrected to "Ventilation Without Cooling" in the xlsx.

System-wide population-weighted cooling (facility pop × building fraction, 31 facilities):
- Refrigeration (AC): 29%
- Evaporative cooling: 54%
- Ventilation only: 17%

6 facilities are 100% refrigeration: CAL, CEN, CHCF, CIM, ISP, SQ. Facilities with 0% refrigeration: ASP, CCI, CMC, COR, CTF, VSP.

**CDCR 2025 Climate Report discrepancy:** CDCR's 2025 report states 19% mechanical cooling vs. our 29% population-weighted figure. The gap is not fully reconcilable. To reach 19% from our 152 refrigeration buildings, the total building denominator would need to grow by ~42% (~800 buildings vs. our 563). Most likely explanation: CDCR counts at housing pod or cell level rather than building level. The Reuters FOIA was scoped to AHUs only, which may exclude facilities with fans-only ventilation, slightly inflating our refrigeration percentage. Do not use CDCR 2025 pie chart figures as a cross-check without resolving this.

**Building-level bed count limitation:** CDCR does not publicly publish bed counts at the building or housing unit level. The finest public granularity is yard-level (Capacity Assessment 2024 Attachment B). Population weighting in this analysis uses facility-level totals as a proxy.

**Person-days by cooling type:** A second cooling chart multiplies people in each cooling type by that facility's average annual days ≥ 90°F (2016–2025), producing person-days by cooling type per facility. System-wide: 34.6% of heat person-days occur in refrigerated units, 60.5% in evaporative units, 4.9% in ventilation-only units.

### Marginal mortality estimate — Skarha 10°F threshold

**Formula:** projected person-days/year × (baseline mortality rate / 365) × 5.2% × slope adjustment

**Inputs:**
- Projected person-days/year above Skarha threshold: 840,457 (sum across 31 facilities: 2025 pop × avg annual Skarha days, 2016–2025)
- Baseline mortality rate: 3.07/1,000/year (CCHCS 2016–2019 average, pre-COVID, pre-fentanyl)
- Slope adjustment: 1.31× — the Skarha 5.2% is a continuous slope coefficient, not a binary threshold effect; mean excess on Skarha days = 3.11°F above threshold (i.e., 13.11/10 = 1.31 weight)
- Slope-adjusted person-days: 1,102,039

**Result:** 0.48 deaths/year → **1 expected heat-attributable death every 2.1 years**

**Non-refrigeration flag:** 72.7% of person-days (611,051) occur at facilities with evaporative or ventilation-only cooling. Skarha's 5.2% was estimated across AC and non-AC facilities, attenuating the national estimate. Applying the same formula to non-refrigeration person-days only:
- Non-ref slope-adjusted person-days: 801,488
- Result: 0.35 deaths/year → **1 expected death every 2.9 years** among the non-refrigerated population

**Key caveats:**
1. Skarha's West region estimate (6.4%) is not statistically significant (CI: −1.6%, 15%); national 5.2% used
2. Skarha's 5.2% is derived from Jun–Aug deaths; the CDCR baseline (3.07/1,000) is annual — summer-specific CDCR rate is unavailable
3. Outdoor tmax systematically underestimates indoor exposure, making all estimates conservative
4. 2025 population snapshot used; populations vary year to year

**Facility coverage notes:**
- CAC (private facility) and FWF (co-located with FOL) are excluded from all heat analysis
- CVSP is included for 2016–2023 only (closed mid-2024)

## Indoor vs. Outdoor Heat Gap — AB 2499 Analysis

`analysis/indoor_outdoor_heat_2025.html` — interactive D3 report analyzing the discrepancy between outdoor and indoor heat at 31 CDCR adult prisons in 2025, framed around AB 2499 (introduced February 20, 2026; 85°F indoor reporting threshold; 3 pilot monitoring locations by July 2027).

`analysis/indoor_outdoor_heat_2025.csv` — flat data table, 31 rows × 19 columns, sorted by indoor-to-outdoor 78°F ratio descending.

### Clustering

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

### Building envelope

Roofing and building envelope project status per facility drawn from:
- CDCR MPAR capital project records (2020–2025)
- LAO budget analyses (2017–2025) for named appropriations
- CDCR SIFC Roof Replacement Needs page (2018, phased program)
- Contractor portfolios and procurement records for pre-2020 partial projects (FOL 2016, SQ 2019)
- DOF Budget Change Proposals for funding/reappropriation status (CMF)

Pre-2017 roofing was funded through a pooled annual special repair appropriation with no facility-level legislative itemization; projects were largely performed by inmate day labor with no public procurement record. The CDCR phased statewide roof replacement program was established in 2017. The 2023–2024 CDCR Master Plan Annual Reports characterize prisons built in the 1980s–1990s as having original single-ply roof systems beyond their useful life; ASP (1987), MCSP (1987), PBSP (1989), and WSP (1991) appear to be on original roofs.

### Data sources

| Column | Source |
| :--- | :--- |
| `days_indoor_above_78f_2025` | CDCR Air Cooling Pilot Program Supplemental Report, January 2026, Table 1 |
| `days_outdoor_above_78f_2025`, `days_outdoor_90f_2025` | gridMET daily tmax (tmmx), University of Idaho, 2025. Days computed May–October. |
| `pct_buildings_refrigeration/evaporation/ventilation` | Reuters FOIA AHU data (June 2025); CTF corrected per CDCR email |
| `uhi_normalized` | Benz & Burney (2021), same as facilities dataset |
| `hotnights_pre_pct` | CalEnviroScreen 4.0 / OEHHA |
| `elevation_m` | USGS National Elevation Dataset (EPQS API) |
| `avg_tmin_f_2025` | gridMET daily tmin (tmmn), May–October 2025 |
| `envelope_work` | CDCR MPAR, LAO budget analyses, SIFC Roof Replacement Needs page, contractor records |

## Violent Incidents by Facility (2021–2025)

`data_sources/facilities/CDCR/cdcr_violent_incidents_by_facility.csv` — monthly violent incident counts per facility, extracted from CDCR Incident Report PDFs (CompStat and Public series). Script: `data_sources/facilities/CDCR/extract_violent_incidents.py`.

**Coverage:** 35 facilities, January 2021–December 2025. Facility count ranges from 35 (2021) to 31 (2025), reflecting closures (CVSP, DVI, CCC, CAC).

**Violent categories included** (summed per facility per month):
- Assault on a Peace Officer or Non-Prisoner (Total)
- Battery on a Peace Officer or Non-Prisoner (Total)
- Assault on Inmate (Total)
- Battery on Inmate (Total)
- Cell Extractions (Total)
- Fighting
- Riot (incident count only, not "Riot – Number of Inmates Involved")

**Excluded:** all Controlled Substance rows, Type of Force rows.

**Overlap resolution:** For months covered by multiple PDFs, the most recent report takes precedence.

**Validation:** Spot-checked 7 facility-month combinations against All Institutions summary totals across multiple PDFs — all passed.

| Year | System-wide violent incidents |
| :--- | :--- |
| 2021 | 7,169 |
| 2022 | 8,015 |
| 2023 | 10,077 |
| 2024 | 12,376 |
| 2025 | 12,512 |

**Per-facility average** (`avg_annual_violent_incidents`) added to `data/cdcr_facilities.csv` — average annual violent incidents across all years present in the data (2021–2025). System-wide average: ~9,900/year.

## Average Sentence by Admission Type (2023–2026)

`data_sources/facilities/CDCR/cdcr_avg_sentence_by_admission.csv` — average sentence length in months per admission type per month, scraped from the CDCR Population Data Points Power BI dashboard (Admissions > Population Demographics > Crosstabs > Average Sentence, rows: Admission Type, columns: None). Script: `scrapers/fetch_cdcr_avg_sentence.js`.

**Coverage:** January 2023–March 2026, 4 admission types. Some months suppressed (counts < 10).

| Admission Type | Mean sentence | Range |
| :--- | :--- | :--- |
| Felon New Admissions | 84 months (7.0 yrs) | 65–97 mo |
| Felon Parole Violators – With New Term | 53 months (4.4 yrs) | 43–71 mo |
| Felon Parole Violators – Return to Custody | 155 months (13.0 yrs) | 60–252 mo |
| Felon Pending Revocations | 41 months (3.4 yrs) | 16–96 mo |

**Note:** Values are average sentence at time of admission, not additional time added.

## Three-Year Return Rate by Length of Stay (2008–2020)

`data_sources/facilities/CDCR/cdcr_recidivism_los.csv` — three-year return-to-prison rate by length of stay category and fiscal year, scraped from the CDCR Adult Recidivism Power BI dashboard (Returns measure → Crosstabs → Fiscal Year: All → Row: Length of Stay → Column: Length of Stay). Script: `scrapers/fetch_cdcr_recidivism_los.js`.

**Coverage:** 12 release cohorts, FY 2008-09 through 2019-20. 8 length-of-stay categories per cohort (96 data rows).

**2019-20 cohort (most recent):**

| Length of Stay | 3-Year Return Rate |
| :--- | :--- |
| Less than 1 year | 18.2% |
| 1 year (12–23 months) | 20.6% |
| 2 years (24–35 months) | 20.5% |
| 3 years (36–47 months) | 18.3% |
| 4 years (48–59 months) | 16.1% |
| 5–9 years | 12.0% |
| 10–14 years | 6.4% |
| 15 years or more | 2.4% |

System-wide three-year return-to-prison rate: 17.4% (2019-20). Return rates have declined substantially since 2008-09 (when the system-wide rate was ~60%) following California's Public Safety Realignment (2011) and subsequent sentencing reforms.

## CDCR Facility Heat Risk Index

`data/CDCR_heat_risk_index.csv` — facility-level heat risk scores for 31 CDCR state prisons, computed for two time periods (current historic and mid-century 2040–2070). Notebook: `heat_risk_index.ipynb`.

**Framework:** Risk = Hazard × Exposure × Vulnerability, following Ovienmhada et al. (2024) and the VCP environmental risk methodology. All sub-components are min-max normalized 0–1 across the 31 facilities before averaging within each component. Final risk score is normalized 0–100 cross-period (current and mid-century share the same denominator for direct comparison).

**Facility coverage:** 31 of 34 state prisons. CAC, CVSP, and FWF excluded — no indoor heat model data available.

| Component | Sub-components (equal weight) |
| :--- | :--- |
| **Hazard** | Days over 90°F (Cal-Adapt), hot nights (VCP 98th pctl), AQI (CalEnviroScreen) — pre-computed in `data_sources/hazards/heat_hazard.ipynb` |
| **Exposure** | Indoor days above 78°F (2025), indoor/outdoor ratio, UHI score (Benz & Burney 2021), inverted AC fraction |
| **Vulnerability** | Medical acuity (CCHCS P1+P2+medium), age over 50, mental health (EOP), disability (DPP), race/POC |

**Output columns:** `cdcr_code`, `name`, `average_2025_population`, `time_period`, `hazard_score`, `exposure_score`, `vulnerability_score`, `risk_score` (0–100), plus supporting raw inputs.

**Mid-century top 5 by risk score:** COR (100), SATF (97.8), CIM (82.7), CMF (60.9), SAC (58.7).

**Notes:**
- UHI nulls for CCI and PVSP (undeveloped tract classification) imputed with system mean
- PBSP `ratio_indoor_to_outdoor` = 15.75 is an outlier driven by ~4 outdoor 78°F days/year at the Crescent City coast; PBSP scores 1.0 on this sub-component but ranks 28th overall due to very low hazard
- ISP ranks last (0.01) despite highest hazard — its 2024 HVAC project reduced indoor 78°F days to ~1, correctly captured by the exposure component

## Urban Heat Island Exposure

UHI is tracked as an **exposure metric** added to `data/cdcr_facilities.csv` as `uhi_normalized` (0–1). Full methodology, source comparison, and per-facility values in `data_sources/hazards/README.md`.

