# Impact Analysis

Analysis notebooks and scripts are in this directory. Outputs are written to `data/`.

This work produces **summary impact estimates** — not full risk calculations. Full risk calculations (hazard × exposure × vulnerability) are the intended long-term direction of this repository; the data collected across `data_sources/` is structured to support that. The summary analysis here is scoped to near-term advocacy use for AB-2499.

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

## Urban Heat Island Exposure

Urban heat island (UHI) effect is tracked as an **exposure metric**, not added to the hazard estimate. Two data sources were evaluated for coverage across state prison census tracts:

### Benz & Burney (2021) — daytime surface heat anomaly

**Source:** Benz SA, Burney JA. "Widespread race and class disparities in surface urban heat islands across the United States." *Earth's Future* 9(7):e2021EF002016. Data archived at Harvard Dataverse, doi:10.7910/DVN/1F72FB. CC0 license.

**Method:** MODIS land surface temperature (2010–2014), 95th-percentile summer daytime values. ΔT = local LST minus median rural background LST for the surrounding region. Aggregated to 2010 census tracts for all US cities/metropolitan areas included in NLCD "developed" land classification.

**California subset:** `data_sources/hazards/benz_uhi_ca_tracts.csv` — 7,993 CA tracts with ΔT ranging from −13.78°C to +11.27°C. Negative ΔT indicates urban cooling effect (evapotranspiration from parks, water, coastal areas).

**Prison tract matching:** Facilities were joined on `tract_geoid` (pre-computed in `data/cdcr_facilities.csv`). 26 of 40 CDCR facility rows matched Benz coverage. CMF and SOL share the same tract (06095253000, both in Vacaville) — identical scores.

**Coverage gap:** 14 facilities have no Benz ΔT because their census tracts are classified as predominantly undeveloped in NLCD. This is a fundamental limitation of the tract-level approach for rural/exurban prison locations. Affected facilities: CCI, CIM, CIW, COR, CVSP, ISP, PVSP, RJD, SATF, WSP, and others (see choropleth map).

**Normalization (for future exposure index):** Clamp negative ΔT to 0 (urban cooling = no additional UHI exposure); then min-max normalize clamped ΔT against the max across state prison tracts only (not all CA tracts). Results in a 0–1 score where 0 = no UHI or urban cooling, 1 = highest UHI among CA state prison locations.

**Key findings:**
- NKSP has highest Benz ΔT among state prisons (4.55°C); SOL/CMF second (4.21°C); CRC third (4.14°C)
- SAC, FOL, FWF share tract 06067988300 (Folsom area): ΔT = −0.53°C (urban cooling — consistent with Sierra foothills location)
- SQ: ΔT = −5.31°C (strong cooling, consistent with San Francisco Bay maritime influence)
- CAL: ΔT = −4.40°C (Imperial Valley desert, below rural background)

**Choropleth map:** `analysis/benz_uhi_choropleth.html` — Leaflet map of all CA census tracts colored by Benz ΔT (diverging blue → white → red scale, −14°C to +11°C). All 31 active state prison facilities labeled; 14 facilities with no Benz coverage shown as orange markers. Neighboring tract values visible for coverage gap assessment.

**Simplified geojson:** `data_sources/hazards/benz_uhi_ca_tracts.geojson` — CA tract boundaries with Benz `day` ΔT joined. Simplified with geopandas `simplify(tolerance=500, preserve_topology=True)` in EPSG:3857 for web rendering (4.65 MB vs. 153 MB original).

### VCP UHI_sc — binary classification

**Source:** California Vibrant Communities Project (VCP), LCI/Governor's Office of Land Use and Climate Innovation. Field: `UHI_sc` (binary: 0 = No, 2 = Yes) across 9,106 CA census tracts.

**Prison coverage:** All 31 state prisons matched a VCP tract (full coverage).

### Three-source UHI comparison — all 31 facilities

Sources: (1) Benz & Burney ΔT (direct tract or 1-mi buffer); (2) VCP UHI_sc (binary, 0/2); (3) CDCR 2020 Sustainability Report Table 8 — "Top Five Facilities Located in Urban Heat Islands (Sorted by highest UHII)." CDCR only published top 5; all others are "not listed" rather than confirmed No.

| Code | Benz ΔT | Source | VCP | CDCR 2020 | Notes |
| :--- | ---: | :--- | :--- | :--- | :--- |
| ASP | −0.141 | direct | 0 | — | |
| CAC | −0.322 | direct | 0 | — | |
| CAL | −4.399 | direct | 0 | — | |
| CCI | null | missing | 0 | — | 4.4 mi to nearest Benz tract |
| CCWF | +0.662 | direct | 2 | — | |
| CEN | −0.057 | direct | 0 | — | |
| CHCF | +2.480 | direct | 2 | — | |
| CIM | +7.247 | buffer | 2 | **Yes** | all 3 agree |
| **CIW** | **null** | **missing** | **0** | **Yes** | **CDCR=Yes; Benz null (1.04 mi); VCP=No** |
| CMC | +0.506 | direct | 0 | — | Benz+, VCP/CDCR not listed |
| CMF | +4.214 | direct | 2 | **Yes** | all 3 agree |
| COR | +4.188 | buffer | 0 | — | Benz+, VCP/CDCR not listed |
| CRC | +4.140 | direct | 2 | **Yes** | all 3 agree |
| CTF | −1.007 | direct | 0 | — | |
| CVSP | −0.538 | buffer | 0 | — | |
| FOL | −0.534 | direct | 2 | — | VCP=2, Benz negative |
| FWF | −0.534 | direct | 2 | — | VCP=2, Benz negative |
| HDSP | +0.297 | direct | 0 | — | Benz+, VCP/CDCR not listed |
| ISP | −0.538 | buffer | 0 | — | |
| KVSP | +1.090 | direct | 0 | — | Benz+, VCP/CDCR not listed |
| LAC | −1.114 | direct | 2 | — | VCP=2, Benz negative |
| MCSP | +1.902 | direct | 0 | — | Benz+, VCP/CDCR not listed |
| NKSP | +4.548 | direct | 0 | — | Benz+, VCP/CDCR not listed |
| PBSP | +2.244 | direct | 0 | — | Benz+, VCP/CDCR not listed |
| PVSP | null | missing | 0 | — | 2.2 mi to nearest Benz tract |
| RJD | −1.542 | buffer | 0 | — | |
| SAC | −0.534 | direct | 2 | — | VCP=2, Benz negative |
| SATF | +4.354 | buffer | 0 | — | Benz+, VCP/CDCR not listed |
| SCC | −0.122 | direct | 0 | — | |
| SOL | +4.214 | direct | 2 | **Yes** | all 3 agree |
| SQ | −5.309 | direct | 0 | — | |
| SVSP | −1.007 | direct | 0 | — | |
| VSP | +0.662 | direct | 2 | — | |
| WSP | +3.507 | buffer | 0 | — | Benz+, VCP/CDCR not listed |

**Benz vs. VCP summary (31 comparable):** 18 agree / 13 disagree (42% mismatch).

**CDCR 2020 vs. Benz (4 of 5 CDCR facilities have Benz data):** CRC, CIM, CMF, SOL all have positive Benz ΔT — 4/4 agree. CIW is the exception: CDCR identifies it as 3rd highest UHII facility; Benz tract is null (1.04 mi gap); VCP = 0.

**CIW implication:** CIW is in Chino (San Bernardino/Riverside Inland Empire), a heavily developed, high-heat suburban area. CDCR's UHII corroborates a UHI effect that neither Benz nor VCP captures. The 1.04-mi Benz gap is just 230m beyond the 1-mile cutoff. **Decision: extend buffer to 1.1 miles for CIW only, using CDCR 2020 as corroborating authority.** Assign CIW the nearest tract value (+4.385°C, tract 06071000115, 1.04 mi) and flag as `buffer_cdcr_corroborated`.

**Systematic disagreement patterns (Benz vs. VCP):**
- *Benz positive, VCP = 0:* COR, SATF, NKSP, KVSP, WSP, MCSP, PBSP, HDSP, CMC — rural/exurban Central Valley and mountain prisons with local industrial or agricultural heat in satellite LST, not captured by VCP's urban classification.
- *VCP = 2, Benz negative:* SAC, FOL, FWF, LAC — suburban areas with tree cover, parkland, or coastal influence depressing local LST below rural background despite urban land use.

**Decision:** Benz ΔT is the preferred metric. VCP not used as fallback (42% mismatch). CIW assigned buffer value per CDCR 2020 corroboration. CCI and PVSP remain null.

### Normalized UHI exposure column

**`data/cdcr_facilities.csv`** — one column added:

| Column | Type | Description |
| :--- | :--- | :--- |
| `uhi_normalized` | float 0–1 | Normalized UHI exposure score: clamp(`benz_uhi_dt`, 0) ÷ 7.247 |

**`data_sources/hazards/benz_uhi_facilities.csv`** — per-facility Benz source detail:

| Column | Type | Description |
| :--- | :--- | :--- |
| `cdcr_code` | string | Facility code |
| `benz_uhi_dt` | float | Raw Benz & Burney daytime ΔT (°C); negative = urban cooling below rural background |
| `benz_uhi_source` | string | `direct` (prison's own tract), `buffer` (nearest polygon within 1 mi), `buffer_cdcr_corroborated` (CIW, 1.04 mi, CDCR 2020 Table 8 confirms UHI) |
| `uhi_normalized` | float 0–1 | Same normalized score, included for reference |

**Normalization:** Negative ΔT values are clamped to 0 (urban cooling = no additional UHI exposure relative to rural surroundings). The clamped value is divided by the maximum clamped ΔT across all state prisons (7.247°C, CIM — buffer value). Result is a 0–1 score where 0 = no UHI or urban cooling and 1 = highest UHI among CA state prison locations.

**Coverage:** 32 of 34 state prisons. CCI (4.4 mi to nearest Benz tract) and PVSP (2.2 mi) remain null.

**Facilities with highest normalized UHI (uhi_normalized ≥ 0.5):**

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

Facilities with `uhi_normalized = 0` (urban cooling or no positive UHI): CAL, SQ, CTF, SVSP, LAC, RJD, ISP, CVSP, FOL, FWF, SAC, ASP, CEN, SCC, CEN.

