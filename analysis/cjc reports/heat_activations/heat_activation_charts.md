# Heat Activation Charts

`analysis/heat_activation_charts.html` — interactive, print-readable D3 charts visualizing outdoor heat exposure at CDCR state prisons. All charts use outdoor gridMET tmax as the exposure metric (see outdoor vs. indoor gap note in `analysis/README.md`).

## Charts

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

### Population impacts — health risk category × Skarha threshold (2016–2025 avg)

Person-days over Skarha 10°F threshold = population in each health risk tier × avg annual days outdoor tmax exceeds facility mean summer tmax by ≥ 10°F, 2016–2025. All 31 active facilities, sorted by combined P1+P2 person-days. Same risk tiers and sort logic as the ≥ 90°F health risk chart.

System-wide:
- **59.2%** of the total population (52,915 of 89,394) is in medium or higher health risk category
- **9.8 avg Skarha threshold days/person/year** for medium+ population (520,840 person-days ÷ 52,915 people)

### Population impacts — EOP mental health × Skarha threshold (2016–2025 avg)

EOP person-days over Skarha 10°F threshold = EOP people × avg annual days outdoor tmax exceeds facility mean summer tmax by ≥ 10°F, 2016–2025. Top 12 facilities by EOP person-days. System avg: 9.4 Skarha threshold days per facility per year (32 facilities, 2016–2025).

All 23 facilities with EOP > 0, sorted by EOP person-days (8 facilities with 0% EOP excluded: ASP, CAL, CEN, CTF, FOL, ISP, SCC, SOL):

| Facility | EOP people | EOP % | Avg Skarha days/yr | EOP person-days/yr |
| :--- | ---: | ---: | ---: | ---: |
| CMC | 647 | 30% | 15.9 | 10,287 |
| RJD | 916 | 26% | 10.8 | 9,893 |
| SAC | 878 | 41% | 9.8 | 8,604 |
| CMF | 495 | 24% | 15.1 | 7,474 |
| MCSP | 794 | 21% | 8.6 | 6,828 |
| LAC | 605 | 20% | 11.2 | 6,776 |
| SVSP | 272 | 11% | 20.1 | 5,467 |
| CHCF | 468 | 21% | 10.6 | 4,961 |
| SQ | 247 | 9% | 15.1 | 3,730 |
| SATF | 616 | 12% | 5.6 | 3,450 |
| CIM | 168 | 7% | 13.9 | 2,335 |
| VSP | 327 | 10% | 6.6 | 2,158 |
| HDSP | 103 | 4% | 15.6 | 1,607 |
| COR | 258 | 10% | 5.6 | 1,445 |
| KVSP | 337 | 11% | 3.6 | 1,213 |
| CIW | 69 | 6% | 12.7 | 876 |
| PBSP | 94 | 4% | 8.0 | 752 |
| PVSP | 153 | 5% | 4.6 | 704 |
| CCWF | 102 | 5% | 6.6 | 673 |
| CCI | 151 | 6% | 4.3 | 649 |
| WSP | 125 | 3% | 3.8 | 475 |
| CRC | 42 | 2% | 10.1 | 424 |
| NKSP | 80 | 3% | 3.6 | 288 |

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
