# Analysis

Notebooks and scripts are in this directory. Outputs are written to `data/cdcr/` (CDCR) and `data/hazards/` (hazard layers).

## CDCR Facility Heat Risk Index

**Output files:**
- `data/cdcr/CDCR_heat_risk_index.csv` — facility-level component scores and risk scores for 31 CDCR state prisons, current and mid-century. Notebook: `CDCR_risk_indices/heat_risk_index.ipynb`.
- `data/cdcr/CDCR_heat_risk_sensitivity.csv` — weighting sensitivity analysis and VCP comparison. Notebook: `CDCR_risk_indices/sensitivity_analysis.ipynb`.

**Facility coverage:** 31 CDCR state prisons.

### Framework

Risk = Hazard × Exposure × Vulnerability, following Ovienmhada et al. (2024) and the California Vulnerable Communities and Places (VCP) environmental risk methodology. Each component is an equal-weight composite of sub-indicators normalized 0–1 across the 31 facilities before averaging. The final risk score is normalized 0–100 jointly across both time periods so that current and mid-century scores are directly comparable on the same scale.

The multiplicative structure means a facility must score poorly across all three components simultaneously to rank at the top of the index. A facility in a very hot location with full air conditioning and a younger population will score lower than one with moderate temperatures, poor cooling, and high medical acuity.

Adaptive capacity is not included as a fourth component, following Ovienmhada et al. (2024)'s treatment of carcerated populations as having effectively zero adaptive capacity. Incarcerated people cannot relocate, purchase cooling, choose their housing unit, or leave the facility during a heat event; the institutional and legal structure of incarceration removes the individual and collective agency that capacity metrics are designed to measure. We considered restricted housing unit (RHU) placement as a variable that partially relaxes this uniform assumption — RHU residents face additional restrictions on heat-adaptive behavior, and Cloud et al. (2023) explicitly identify people in solitary confinement as "especially susceptible to the hazards of extreme heat." However, RHU was ultimately excluded from the scored index because the literature does not provide quantified dose-response evidence sufficient to justify an equal-weight assumption. See the Excluded Variables section below.

### Hazard Component

Equal-weight average of three sub-indicators. Each is min-max normalized 0–1 across the 31 facilities before averaging.

| Sub-indicator | Variable | Description | Source |
| :--- | :--- | :--- | :--- |
| Days over 90°F | `days_over_90_historic` / `days_over_90_midcentury` | Annual days over 90°F at each facility's census tract. 30-year averages for 1991–2020 (historic) and 2041–2070 (mid-century) under SSP3-7.0. | Cal-Adapt, LOCA 2 downscaled projections |
| Hot nights | `hotnights_pre_pct` / `hotnights_fut_pct` | % of nights exceeding the 98th percentile of each tract's own historical minimum temperature. Uses a local relative definition to account for acclimatization. | LCI VCP, derived from LOCA 2 CA Hybrid (SSP 370, 2023) |
| Air quality | `AQI_norm` | Normalized AQI score (0–100) per facility county, derived from ozone, PM2.5, and diesel exposure percentiles. Held at historic CalEnviroScreen values for both time periods — tract-level AQI cannot be reliably projected. | CalEnviroScreen 5.0, 2025 |

Pre-computed by census tract in `data_sources/hazards/heat_hazard.ipynb`, joined to facilities via `tract_geoid`.

### Exposure Component

Equal-weight average of four sub-indicators capturing how effectively each facility's built environment translates outdoor heat into indoor heat burden. Each is min-max normalized 0–1 across the 31 facilities before averaging.

| Sub-indicator | Variable | Description | Source |
| :--- | :--- | :--- | :--- |
| Indoor 78°F days | `days_indoor_above_78f_2025` | Annual days with indoor temperatures above 78°F (2025). The 78°F threshold is the lower bound of CDCR's Stage I heat pathology activation. Where CDCR's 2026 report provided housing unit counts rather than facility averages, facility-level values were calculated from unit-level data. | CDCR Air Cooling Pilot Supplemental Report, January 2026 |
| Indoor/outdoor ratio | `ratio_indoor_to_outdoor` | Ratio of indoor 78°F days to outdoor 78°F days per facility. Captures the degree to which a building amplifies or attenuates outdoor conditions. PBSP is an outlier (15.75) driven by ~4 outdoor 78°F days/year at the Crescent City coast — physically plausible and retained without capping. | Derived from CDCR 2026 and gridMET outdoor temperature data |
| Urban heat island | `uhi_normalized` | UHI intensity (0–1), from Benz & Burney (2021) daytime surface urban heat anomaly (ΔT). Negative ΔT clamped to 0; normalized against the maximum ΔT across state prisons (7.247°C, CIM). CCI and PVSP null (undeveloped tract classification) — imputed with the system mean. | Benz & Burney (2021), Harvard Dataverse doi:10.7910/DVN/1F72FB |
| No AC (inverted) | `inverted_ac_fraction` | 1 minus the fraction of housing units with refrigerated air conditioning, so that facilities with more cooling score lower on this sub-indicator. | CDCR Air Cooling Pilot Supplemental Report, January 2026 |

**Note on outdoor vs. indoor temperatures:** The CDCR Heat Pathology Plan Stage I and Stage III thresholds are defined by indoor housing unit temperatures (≥ 90°F and ≥ 95°F respectively). Outdoor gridMET data is used as a proxy for trend analysis and hazard mapping, but outdoor temperatures systematically overstate the number of days that cross indoor thresholds. Available evidence on the gap:

*CalMatters CPRA data (one unnamed prison, 2023–2024):*

| Year | Outdoor days ≥ 90°F | Indoor days ≥ 90°F | Indoor days ≥ 95°F |
| :--- | :--- | :--- | :--- |
| 2023 | 166 | 59 | 20 |
| 2024 | 182 | 86 | 46 |

Indoor days at ≥ 90°F were roughly 35–47% of outdoor days at the same threshold. The exposure component uses indoor 78°F day counts directly to address this gap.

*OIG audit, August 2022–October 2023 (Corcoran, High Desert, Lancaster):*

| Prison | Housing units tested | Units with ≥ 1 day over 89°F | Most days over 89°F in a single unit |
| :--- | :--- | :--- | :--- |
| High Desert | 27 | 3 | 1 |
| Lancaster | 29 | 10 | 2 |
| Corcoran | 33 | 23 | 23 |

Source: California Office of the Inspector General, heat log audit.

### Vulnerability Component

Equal-weight average of five sub-indicators describing each facility's population. Each is min-max normalized 0–1 across the 31 facilities before averaging.

| Sub-indicator | Variable | Description | Source |
| :--- | :--- | :--- | :--- |
| Medical acuity | `medical_acuity` | Share of the facility population in CCHCS health risk tiers P1 (highest), P2, or medium risk (2025). These tiers capture chronic and acute conditions that increase heat sensitivity, including cardiovascular disease, diabetes, and respiratory illness. | CCHCS Health Care Dashboard, 2025 |
| Age 50+ | `cchcs_age_over_50_pct_2025` | Share of the facility population aged 50 or older (2025). Age 50 is used as the threshold consistent with CDCR's own heat pathology plan definitions and the accelerated aging literature on incarcerated populations. | CDCR Population Data Points, 2025 |
| Mental health (EOP) | `cchcs_mental_health_eop_pct_2025` | Share enrolled in the Enhanced Outpatient Program for mental health (2025). EOP enrollment is used as a proxy for psychotropic medication use, which impairs thermoregulation through anticholinergic and antipsychotic mechanisms. | CCHCS Health Care Dashboard, 2025 |
| Disability (DPP) | `cchcs_dpp_pct_2025` | Share with a Disability Placement Program designation (2025). DPP covers mobility, vision, hearing, and other impairments that may limit a person's ability to respond to heat stress or access cooling resources. | CCHCS Health Care Dashboard, 2025 |
| Race/POC | `race_peopleofcolor_pct` | Share identifying as people of color (2025), consistent with Ovienmhada et al. (2024)'s treatment of race as a heat vulnerability factor given documented disparities in heat-related health outcomes and access to care. | CDCR Population Data Points, 2025 |

### Excluded Variables

Two variables were considered for inclusion and rejected after methodological review. Both are retained in the output data as descriptive columns.

**Restricted housing unit rate (`rhu_pct_2025`)** — 12-month average share of the facility population in restricted housing units (2025), from CDCR STA429 monthly reports. RHU residents face meaningful additional constraints on heat-adaptive behavior: they cannot access cooler facility areas, cannot self-regulate their physical location or activity during heat events, and average approximately one hour of out-of-cell time per day — meeting the UN Mandela Rules definition of solitary confinement (≥22 hours/day in cell). Cloud et al. (2023) explicitly identify solitary confinement as a heat vulnerability factor. However, the existing literature does not provide a quantified dose-response between RHU status and heat health outcomes relative to the general incarcerated population. Including RHU as an equal-weight vulnerability sub-indicator would implicitly assert that 1% of RHU population is equivalent in vulnerability impact to 1% additional EOP enrollment, age 50+, or medical acuity — a claim that cannot be substantiated with current evidence. The variable also has two extreme outliers (COR 13.6%, SAC 12.7%, vs. IQR fence of 6.8%), which under min-max normalization produced disproportionate score separation not grounded in comparative heat outcome data. Retained as a descriptive output column; flagged as a priority candidate for inclusion when dose-response research becomes available.

**Geographic isolation (`dist_nearest_medical_mi`, `in_urban_area_2020`)** — distance to the nearest medical facility and whether the facility is in a 2020 Census urban area. Hidden Hazards (2023) identifies remoteness from hospitals as a vulnerability factor in emergency response, and the concept is conceptually sound (isolated facilities have slower access to higher-level care during heat emergencies). However, among the 31 active CDCR state prisons, this variable shows insufficient differentiation to function as a scored sub-indicator: the median distance to the nearest medical facility is 0.52 miles, the maximum is 1.51 miles (KVSP), and there are no facilities with the degree of isolation that would drive the index in a meaningful way. The variable is more appropriately treated as facility-level context. Retained as a descriptive output column.

### Risk Tier Classification

Mid-century risk scores are classified into four tiers using Jenks natural breaks, computed to minimize within-class variance. Breaks are applied to the mid-century distribution only; historic scores use the same thresholds for comparability.

| Tier | Score range | n facilities | Color |
| :--- | :--- | :--- | :--- |
| Critical | > 82.7 | 3 (COR, SATF, CIM) | `#7a1010` |
| High | 36.4 – 82.7 | 10 (CMF, SAC, VSP, LAC, NKSP, SOL, CIW, KVSP, RJD, WSP) | `#c44020` |
| Moderate | 20.1 – 36.4 | 6 (CCWF, CRC, CCI, FOL, MCSP, HDSP) | `#e89050` |
| Low | ≤ 20.1 | 12 | `#e8e0c8` |

**Mid-century top 5 by risk score:** COR (100.0), SATF (97.8), CIM (82.7), CMF (60.9), SAC (58.7).

### Output Column Reference

`data/cdcr/CDCR_heat_risk_index.csv`:

| Column | Description |
| :--- | :--- |
| `cdcr_code` | CDCR facility code |
| `name` | Facility name |
| `latitude` / `longitude` | Facility centroid coordinates |
| `average_2025_population` | Average 2025 incarcerated population |
| `time_period` | `current` (1991–2020) or `midcentury` (2041–2070) |
| `hazard_score` | Hazard component score (0–1) |
| `exposure_score` | Exposure component score (0–1) |
| `vulnerability_score` | Vulnerability component score (0–1) |
| `risk_score` | Final risk score (0–100), normalized cross-period |
| `risk_category` | Jenks tier: `Critical`, `High`, `Moderate`, or `Low` |
| `AQI_norm` | AQI sub-indicator (raw, 0–100) |
| `ratio_indoor_to_outdoor` | Indoor/outdoor 78°F day ratio (raw) |
| `days_indoor_above_78f_2025` | Indoor 78°F days in 2025 (raw count) |
| `uhi_normalized` | UHI sub-indicator (normalized 0–1) |
| `medical_acuity` | Medical acuity sub-indicator (share 0–1) |
| `cchcs_age_over_50_pct_2025` | Age 50+ share (%) |
| `cchcs_mental_health_eop_pct_2025` | EOP share (%) |
| `cchcs_dpp_pct_2025` | DPP share (%) |
| `race_peopleofcolor_pct` | POC share (%) |
| `rhu_pct_2025` | Restricted housing unit share (12-month average %, 2025) — descriptive only, not scored |
| `dist_nearest_medical_mi` | Distance in miles to nearest medical/emergency facility — descriptive only, not scored |
| `in_urban_area_2020` | Whether facility falls within a 2020 Census urban area boundary — descriptive only, not scored |
| `california_model_facility` | Whether facility is designated a California Model facility — descriptive only, not scored |
| `year_opened` | Year the facility opened — descriptive only, not scored |

### Sensitivity Analysis and VCP Comparison

`data/cdcr/CDCR_heat_risk_sensitivity.csv`. Notebook: `CDCR_risk_indices/sensitivity_analysis.ipynb`.

Three alternative weighting schemes are tested against the equal-weight multiplicative baseline (mid-century only):

| Scheme | Formula | Logic |
| :--- | :--- | :--- |
| A — Equal multiplicative (baseline) | H × E × V, normalized 0–100 | All components equal; risk requires elevation across all three |
| B — Additive 25/25/50 | 0.25H + 0.25E + 0.50V, normalized 0–100 | Ovienmhada vulnerability upweighting; additive structure means high vulnerability alone can drive rank |
| C — Multiplicative V² | H × E × V², normalized 0–100 | Preserves multiplicative structure; vulnerability amplified but still requires hazard and exposure |

Spearman rank correlations across schemes: A vs B = 0.877, A vs C = 0.935, B vs C = 0.946. The top 5 facilities are stable across all three. CHCF has the largest rank swing (16 positions): it ranks 22nd under equal weighting but rises to 6th under the additive scheme, because high medical complexity drives vulnerability even without indoor heat exposure days (full AC). ISP has the second largest swing (10 positions).

VCP's `ExHeatHealth_Idx` for each prison's surrounding non-institutional census tracts (Pct_GroupQuarters ≤ 25%) is included for comparison. Spearman r between our index and the surrounding community VCP index is −0.17 — the low correlation supports the case for a prison-specific framework rather than applying community-facing indices directly to carceral facilities.

### Limitations and Future Work

- **Incarcerated workers** — the share of the facility population employed through the Prison Industry Authority (PIA) or other work assignments is not included in the vulnerability component. PIA workers face elevated heat exposure from extended time in industrial or outdoor settings. Facility-level data on full incarcerated worker participation rates are still being searched for; retained as future work.
- **Psychotropic medication use** — the share of incarcerated people on psychotropic medications is not included as a standalone sub-component. Psychotropic medications (antipsychotics, anticholinergics, mood stabilizers) impair thermoregulation and are an established heat vulnerability factor. Facility-level psychotropic prescription rates are not publicly available from CCHCS. The CCHCS health risk categories used in the medical acuity sub-component (P1, P2, medium risk) are used as proxies; retained as future work for a more direct measure.
