# Analysis

Notebooks and scripts are in this directory. Outputs are written to `data/cdcr/` (CDCR) and `data/hazards/` (hazard layers).

## CDCR Facility Heat Risk Index

**Output files:**
- `data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv` — facility-level component scores and risk scores for 31 CDCR state prisons, current and mid-century (additive 0.25H + 0.25E + 0.50V). Notebook: `CDCR_risk_indices/heat_risk_index.ipynb`.
- `data/cdcr/CDCR_heat_risk_sensitivity.csv` — weighting sensitivity analysis and VCP comparison. Notebook: `CDCR_risk_indices/sensitivity_analysis.ipynb`.

**Facility coverage:** 31 CDCR state prisons.

### Framework

Risk = 0.25H + 0.25E + 0.50V (additive, vulnerability double-weighted), following Ovienmhada et al. (2024). Each component is an equal-weight composite of sub-indicators normalized 0–1 across the 31 facilities before averaging. The final risk score is normalized 0–100 jointly across both time periods by max-normalization (dividing by the shared cross-period maximum), so current and mid-century scores are directly comparable on the same scale and no facility is forced to a false 0.

Vulnerability receives double weight because cooling in prisons is controlled by staff who, as Brunn et al. (2025) document, withhold AC, water, and shade to punish and retaliate. The additive form also prevents a facility with full mechanical AC from scoring zero risk; a multiplicative model would zero out CHCF, which has the highest vulnerability in the system but no indoor heat days.

Adaptive capacity is not included as a fourth component, following Ovienmhada et al. (2024)'s treatment of carcerated populations as having effectively zero adaptive capacity. Incarcerated people cannot relocate, purchase cooling, choose their housing unit, or leave the facility during a heat event; the institutional and legal structure of incarceration removes the individual and collective agency that capacity metrics are designed to measure. We considered restricted housing unit (RHU) placement as a variable that partially relaxes this uniform assumption — RHU residents face additional restrictions on heat-adaptive behavior, and Cloud et al. (2023) explicitly identify people in solitary confinement as "especially susceptible to the hazards of extreme heat." However, RHU was ultimately excluded from the scored index because the literature does not provide quantified dose-response evidence sufficient to justify an equal-weight assumption. See the Excluded Variables section below.

### Hazard Component

A blended daytime term and a warm-night term, each max-normalized 0–1 across the 31 facilities (cross-period), averaged, then multiplied by an air-quality modifier. Counts come from a LOCA2-CA daily extraction at each facility's grid cell (14-model ensemble, model democracy — see `data/hazards/README.md`). Max-normalization (not min-max) means a facility with no exceedances scores 0.

| Sub-indicator | Variable | Description | Source |
| :--- | :--- | :--- | :--- |
| Hot days (blended) | `loca2_days_over_avg_plus10` ⊕ `loca2_days_over_90` | 50/50 blend of a facility-relative threshold (days above the facility's mean summer daily-max + 10°F, 1981–2010 baseline) and an absolute threshold (days over 90°F), each max-normalized before blending. The 50% weight is a parameter (`W_REL`). | LOCA2-CA daily (SSP3-7.0), Cal-Adapt via cadcat |
| Warm nights | `loca2_nights_over_p95_historic` / `_midcentury` | April–October nights with tmin above the 95th percentile of the facility's 1961–1990 April–October minimum-temperature distribution (OEHHA convention). | LOCA2-CA daily (SSP3-7.0), Cal-Adapt via cadcat |
| Air quality (modifier) | `AQI_norm` | Multiplicative modifier: `H = temp × (1 + 0.30·AQI_norm/100)`, ×1.0 at AQI = 0. AQI_norm is the CalEnviroScreen 5.0 ozone/PM2.5/diesel percentile mean, held at historic values for both periods. β = 0.30 is a parameter. | CalEnviroScreen 5.0, 2025 |

The all-facilities hazard product is built for 357 facilities in `data_sources/hazards/heat/heat_hazard.ipynb` (normalized across all 357); the index recomputes the same equation across its 31 facilities and joins by `cdcr_code`.

### Exposure Component

Equal-weight average of four sub-indicators capturing how effectively each facility's built environment translates outdoor heat into indoor heat burden. Each is min-max normalized 0–1 across the 31 facilities before averaging.

| Sub-indicator | Variable | Description | Source |
| :--- | :--- | :--- | :--- |
| Indoor 78°F days | `days_indoor_above_78f_2025` | Annual days with indoor temperatures above 78°F (2025). The 78°F threshold is the lower bound of CDCR's Stage I heat pathology activation. Where CDCR's 2026 report provided housing unit counts rather than facility averages, facility-level values were calculated from unit-level data. | CDCR Air Cooling Pilot Supplemental Report, January 2026 |
| Indoor/outdoor ratio | `ratio_indoor_to_outdoor` | Ratio of indoor 78°F days to outdoor 78°F days per facility. Captures the degree to which a building amplifies or attenuates outdoor conditions. PBSP is an outlier (15.75) driven by ~4 outdoor 78°F days/year at the Crescent City coast — physically plausible and retained without capping. | Derived from CDCR 2026 and gridMET outdoor temperature data |
| Urban heat island | `uhi_normalized` | UHI intensity (0–1), from Benz & Burney (2021) daytime surface urban heat anomaly (ΔT). Negative ΔT clamped to 0; normalized against the maximum ΔT across state prisons (7.247°C, CIM). CCI and PVSP null (undeveloped tract classification) — imputed with the system mean. | Benz & Burney (2021), Harvard Dataverse doi:10.7910/DVN/1F72FB |
| No AC (inverted) | `1 − pct_hu_mechanical` | 1 minus the fraction of housing units (wings/dorms/tiers) with refrigerated/mechanical air conditioning, so facilities with more real AC score lower on this sub-indicator. Only mechanical cooling counts as AC here; evaporative and ventilation both read as exposed. Uses the CDCR report's `pct_hu_*` inventory — **not** the older, incomplete Reuters FOIA `pct_units_*` (which overstated AC at 16 of 31 facilities, e.g. CIM 100% vs the report's ~43%). | CDCR Air Cooling Pilot Supplemental Report, January 2026 (as of Dec 2025) |

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

*Comparison of OIG audit findings to 2025 exposure sub-indicators (COR, HDSP, LAC):*

The OIG audit (89°F threshold, unit-level) and our 2025 exposure data (78°F threshold, institution-level as reported by CDCR) use different thresholds and units of analysis but are directionally consistent. COR is the worst performer in both; LAC shows strong attenuation of outdoor heat in both; HDSP has many moderately warm indoor days but rarely crosses higher thresholds.

| Facility | OIG: units w/ ≥ 1 day > 89°F | OIG: max days > 89°F (single unit) | 2025: indoor 78°F days (CDCR reported) | 2025: outdoor 78°F days | 2025: indoor/outdoor ratio | Cooling type | Elevation | UHI (0–1) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Corcoran (COR) | 23 of 33 (70%) | 23 | 159 | 163 | 0.975 | 100% evaporative | 55 m | 0.578 |
| High Desert (HDSP) | 3 of 27 (11%) | 1 | 89 | 128 | 0.695 | 100% evaporative | 1,267 m | 0.041 |
| Lancaster (LAC) | 10 of 29 (34%) | 2 | 39 | 162 | 0.241 | 96% evaporative | 716 m | 0.000 |

LAC's low indoor/outdoor ratio (0.241) despite 162 outdoor 78°F days reflects strong indoor attenuation of outdoor heat. It is not a humidity effect: LAC is the driest of the 31 facilities (summer wet-bulb depression 30.4°F), but COR is nearly as dry (26.9°F) with a ratio of 0.975, so evaporative-cooling capacity does not distinguish them — the difference is in the buildings, not the climate. COR's ratio of 0.975 means its buildings provide almost no attenuation — consistent with 70% of OIG-audited units recording extreme heat days.

### Vulnerability Component

Equal-weight average of six sub-indicators describing each facility's population. Each is min-max normalized 0–1 across the 31 facilities before averaging.

| Sub-indicator | Variable | Description | Source |
| :--- | :--- | :--- | :--- |
| Medical acuity | `medical_acuity` | Share of the facility population in CCHCS health risk tiers P1 (highest), P2, or medium risk (2025). These tiers capture chronic and acute conditions that increase heat sensitivity, including cardiovascular disease, diabetes, and respiratory illness. | CCHCS Health Care Dashboard, 2025 |
| Age 50+ | `cchcs_age_over_50_pct_2025` | Share of the facility population aged 50 or older (2025). Age 50 is used as the threshold consistent with CDCR's own heat pathology plan definitions and the accelerated aging literature on incarcerated populations. | CDCR Population Data Points, 2025 |
| Mental health (EOP) | `cchcs_mental_health_eop_pct_2025` | Share enrolled in the Enhanced Outpatient Program for mental health (2025). EOP enrollment is used as a proxy for psychotropic medication use, which impairs thermoregulation through anticholinergic and antipsychotic mechanisms. | CCHCS Health Care Dashboard, 2025 |
| Disability (DPP) | `cchcs_dpp_pct_2025` | Share with a Disability Placement Program designation (2025). DPP covers mobility, vision, hearing, and other impairments that may limit a person's ability to respond to heat stress or access cooling resources. | CCHCS Health Care Dashboard, 2025 |
| Race/POC | `race_peopleofcolor_pct` | Share identifying as people of color (2025), consistent with Ovienmhada et al. (2024)'s treatment of race as a heat vulnerability factor given documented disparities in heat-related health outcomes and access to care. | CDCR Population Data Points, 2025 |
| Gender (female) | `gender_female_pct` | Share of the facility population who are women (2025). Included because women's carceral facilities differ systematically in medical infrastructure, and the pregnancy and reproductive-health conditions concentrated in these facilities carry additional heat sensitivity. | CDCR Population Data Points, 2025 |

### Excluded Variables

The following variables were considered for inclusion and rejected after methodological review. Scored variables are retained in the output data as descriptive columns where available.

**Restricted housing unit rate (`rhu_pct_2025`)** — 12-month average share of the facility population in restricted housing units (2025), from CDCR STA429 monthly reports. RHU residents face meaningful additional constraints on heat-adaptive behavior: they cannot access cooler facility areas, cannot self-regulate their physical location or activity during heat events, and average approximately one hour of out-of-cell time per day — meeting the UN Mandela Rules definition of solitary confinement (≥22 hours/day in cell). Cloud et al. (2023) explicitly identify solitary confinement as a heat vulnerability factor. However, the existing literature does not provide a quantified dose-response between RHU status and heat health outcomes relative to the general incarcerated population. Including RHU as an equal-weight vulnerability sub-indicator would implicitly assert that 1% of RHU population is equivalent in vulnerability impact to 1% additional EOP enrollment, age 50+, or medical acuity — a claim that cannot be substantiated with current evidence. The variable also has two extreme outliers (COR 13.6%, SAC 12.7%, vs. IQR fence of 6.8%), which under min-max normalization produced disproportionate score separation not grounded in comparative heat outcome data. Retained as a descriptive output column; flagged as a priority candidate for inclusion when dose-response research becomes available.

**Capacity utilization (`capacity_percent_2025`)** — 2025 annual average occupancy as a share of CDCR design capacity (from TPOP reports), available for all 31 facilities (range 76%–161%). Overcrowding impairs ventilation and limits movement to cooler areas, so it would belong in the exposure component. However, direct regression testing shows capacity utilization does not explain indoor/outdoor ratio variance beyond AC fraction (OLS: coef=0.002, p=0.60, R² change <0.01), and adding it as a k-means clustering feature produces no facility reassignments. The indoor temperature data appears to already capture the thermal outcome of overcrowding through direct measurement. Retained as a descriptive output column.

**Security level (`securelvl`)** — Maximum vs. Medium security. Higher-security housing involves more time in cell, more restricted movement, and potentially less access to cooling. The literature on security level and heat outcomes is mixed, with most studies finding no significant independent effect. Direct testing confirms: security level does not explain indoor/outdoor ratio variance (OLS: coef=−0.081, p=0.68) and adding it as a clustering feature reassigns one facility (RJD, A→B) without improving cluster coherence or the key r=0.806 outdoor-indoor correlation in Cluster A. Analysis script: `analysis/cjc reports/indoor_outdoor_heat/build_indoor_outdoor_analysis.py`.

**Geographic isolation (`dist_nearest_medical_mi`, `in_urban_area_2020`)** — distance to the nearest medical facility and whether the facility is in a 2020 Census urban area. Hidden Hazards (2023) identifies remoteness from hospitals as a vulnerability factor in emergency response, and the concept is conceptually sound (isolated facilities have slower access to higher-level care during heat emergencies). However, among the 31 active CDCR state prisons, this variable shows insufficient differentiation to function as a scored sub-indicator: the median distance to the nearest medical facility is 0.52 miles, the maximum is 1.51 miles (KVSP), and there are no facilities with the degree of isolation that would drive the index in a meaningful way. The variable is more appropriately treated as facility-level context. Retained as a descriptive output column.

**Incarcerated workers (% assigned to work)** — work assignments in kitchens, laundry, and outdoor labor involve sustained physical exertion and/or prolonged exposure to high-heat environments with limited ability to self-limit activity, representing a meaningful exposure pathway not captured by facility-level indoor temperature data. Days above 80°F increase the risk of workplace injuries by 3%, and days above 90°F increase the risk by 10% (LAO, 2024; Alahmad, 2025). Facility-level data on work assignment rates are not currently available in this project. *Data gap — candidate for inclusion if CDCR work assignment data becomes available.*

### Risk Tier Classification

Risk scores are classified into four tiers using Jenks natural breaks (k=4, `jenkspy`), computed to minimize within-class variance. As of **v0.3, breaks are computed separately for each time period** — each period is classified against its own range — so both periods span all four tiers. (v0.2 applied the mid-century breaks to both periods; because the cross-period score makes the cooler current period genuinely lower, that collapsed the current period into just Moderate and Lowest.)

A category is therefore **relative within a period**: "Highest" in the current period is a lower absolute risk than "Highest" mid-century. The 0–100 risk score stays cross-period normalized (see Versioning → v0.3), so the absolute current → mid-century increase is carried by the score; only the label is within-period. One consequence: a facility high on the constant exposure + vulnerability (e.g. RJD, PBSP) can sit a tier higher in the current period — where hazard spread is compressed — than mid-century, even though its score rises.

Tiers are named to reflect relative risk within the CDCR system. All incarcerated people face elevated heat risk compared to the general population; these labels indicate which facilities face the highest risk relative to peers, not that lower-ranked facilities are safe.

The tables below reflect the **additive default model** (Risk = 0.25 H + 0.25 E + 0.50 V), the published default since the 2026-04-21 switch from the multiplicative baseline, at **heat index v0.3**. The score span shown for each tier is the observed span within that tier; Jenks breaks fall in the gaps between tiers.

**Mid-century (2041–2070):**

| Tier | Score span | n | Facilities | Color |
| :--- | :--- | :--- | :--- | :--- |
| Highest | 91.2 – 100.0 | 5 | CIM, CMF, CIW, COR, SATF | `#7a1010` |
| High | 78.9 – 86.8 | 8 | SAC, CHCF, CCWF, LAC, VSP, RJD, CRC, SOL | `#c44020` |
| Moderate | 66.0 – 75.9 | 10 | MCSP, KVSP, NKSP, SQ, HDSP, CCI, WSP, FOL, PBSP, CMC | `#e89050` |
| Lowest | 49.1 – 63.4 | 8 | CTF, SVSP, PVSP, ASP, SCC, ISP, CAL, CEN | `#e8e0c8` |

**Current (1991–2020):**

| Tier | Score span | n | Facilities | Color |
| :--- | :--- | :--- | :--- | :--- |
| Highest | 65.7 – 75.3 | 7 | CIM, CMF, COR, SATF, SAC, CIW, RJD | `#7a1010` |
| High | 55.9 – 63.2 | 9 | CHCF, CCWF, SOL, LAC, VSP, CRC, MCSP, PBSP, KVSP | `#c44020` |
| Moderate | 48.5 – 54.2 | 9 | CMC, NKSP, SQ, WSP, CTF, FOL, HDSP, SVSP, CCI | `#e89050` |
| Lowest | 34.0 – 43.2 | 6 | ASP, PVSP, CAL, SCC, ISP, CEN | `#e8e0c8` |

No current-period score is 0: max-normalization (v0.3) removes the false floor that put CEN at exactly 0.0 under v0.2's min-max. The lowest current score is CEN at 34.0.

**Mid-century top 5 by risk score:** CIM (100.0), CMF (92.5), CIW (92.1), COR (91.7), SATF (90.9).

Overall risk rank correlates with v0.1 at Spearman ρ ≈ 0.84; exposure and vulnerability are unchanged, only the hazard component was rebuilt. The 50/50 daytime blend correlates with a pure-relative daytime term at ρ ≈ 0.96.

### Output Column Reference

`data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv`:

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
| `risk_category` | Jenks tier: `Highest`, `High`, `Moderate`, or `Lowest` — relative within the CDCR system |
| `AQI_norm` | AQI sub-indicator (raw, 0–100) |
| `ratio_indoor_to_outdoor` | Indoor/outdoor 78°F day ratio (raw) |
| `days_indoor_above_78f_2025` | Indoor 78°F days in 2025 (raw count) |
| `uhi_normalized` | UHI sub-indicator (normalized 0–1) |
| `medical_acuity` | Medical acuity sub-indicator (share 0–1) |
| `cchcs_age_over_50_pct_2025` | Age 50+ share (%) |
| `cchcs_mental_health_eop_pct_2025` | EOP share (%) |
| `cchcs_dpp_pct_2025` | DPP share (%) |
| `race_peopleofcolor_pct` | POC share (%) |
| `gender_female_pct` | Female share of population (fraction, 0–1) |
| `rhu_pct_2025` | Restricted housing unit share (12-month average %, 2025) — descriptive only, not scored |
| `dist_nearest_medical_mi` | Distance in miles to nearest medical/emergency facility — descriptive only, not scored |
| `in_urban_area_2020` | Whether facility falls within a 2020 Census urban area boundary — descriptive only, not scored |
| `california_model_facility` | Whether facility is designated a California Model facility — descriptive only, not scored |
| `year_opened` | Year the facility opened — descriptive only, not scored |
| `index_version` | Heat index version that produced the row (`v0.3`) |

### Versioning

The index is versioned so an exported artifact is self-identifying. The present state is **v0.3**;
the prior states are retroactively **v0.2** and **v0.1**. The version is carried in the `index_version`
column of `CDCR_heat_risk_index_additive_25_25_50.csv` and `CDCR_heat_risk_sensitivity.csv`, and in the
`meta.index_version` field of `prison_heat_index.json`. The top-level files are always the current
build; a copy of **every shipped version** is retained in dedicated archive directories —
`data/cdcr/archive/` for the CSVs and `analysis/app_export/output/archive/` for the app JSON
(`*_v0.1.*` through the current version) — so versions can be compared and any circulated figure stays
traceable. The build notebooks archive the on-disk build (keyed by its own `index_version`) before
overwriting, so the archive fills automatically.

#### Changelog — v0.3

- **Risk-score normalization: min-max → max-norm.** The final 0–100 risk score is now divided by the
  cross-period maximum only, with no minimum subtracted. Under v0.2's min-max, the single lowest
  facility-period was forced to exactly 0 — a misleading "zero heat risk" (CEN read 0.0 in the current
  period). Max-normalization keeps the shared cross-period denominator, so both periods stay comparable
  and the current → mid-century increase is preserved, while removing the false floor (CEN current is
  now 34.0). This mirrors the max-normalization already used inside the hazard component.
- **Risk categories: shared mid-century breaks → per-period Jenks.** Categories are now Jenks-classified
  separately for each period, so both periods span all four tiers. v0.2 applied the mid-century breaks
  to both periods, collapsing the cooler current period into just Moderate/Lowest. The trade-off: a
  category is now relative *within* a period (see Risk Tier Classification), while the score remains
  cross-period comparable.
- **Unchanged:** the hazard, exposure, and vulnerability components and all their inputs; the weights
  (0.25/0.25/0.50); the two periods; and the fact that the score is normalized jointly across both
  periods. v0.3 changes only the final combination step (normalization method + category breaks), so
  v0.2 → v0.3 rank movement within a period is small; what changes is the score floor and the
  current-period tier spread.

#### Changelog — v0.2

- **Daytime heat.** v0.1 used an absolute 90°F count (Cal-Adapt tract product). v0.2 daytime heat is a
  50/50 blend of a facility-relative threshold (days above the facility's mean summer max + 10°F) and
  an absolute 90°F count, each max-normalized before blending. The 50% weight is a parameter (`W_REL`).
- **Warm nights.** Rebuilt from LOCA2-CA `tasmin` (Apr–Oct P95 of the facility's 1961–1990
  distribution), replacing the VCP hot-nights field.
- **Heat hazard moves from tract joins to facility cells.** Every facility now carries its own
  LOCA2-CA grid cell (14-model ensemble, model democracy), replacing the tract-centroid join. This
  applies to all 357 CA carceral facilities in the hazard data product; the index remains CDCR-31.
- **AQI becomes a multiplicative modifier.** Air quality was an equal additive third of the hazard
  in v0.1; in v0.2 it multiplies the temperature hazard (`× (1 + 0.30·AQI_norm/100)`) so it amplifies
  heat where present but cannot create hazard from pollution alone.
- **AC sub-indicator source corrected.** The exposure "no-AC" term now uses `pct_hu_mechanical` from
  the CDCR Air Cooling Pilot Supplemental Report (Jan 2026, as of Dec 2025) — the complete per-facility
  housing-unit inventory — replacing the older, incomplete Reuters FOIA equipment inventory that
  overstated AC at 16 of 31 facilities (e.g. CIM 100% vs the report's ~43%). See
  `data_sources/facilities/CDCR/README.md`.
- **Hazard normalization: min-max → max-norm.** The temperature indicators are divided by their
  cross-period max rather than min-max scaled, so the coolest facility keeps a real, non-zero score
  instead of a false floor of 0.
- **Unchanged:** weights (0.25/0.25/0.50), the two periods (current 1991–2020, mid-century
  2041–2070), cross-period 0–100 normalization, and the exposure and vulnerability components. Because
  the normalization denominator is held fixed, v0.1 → v0.2 score movement is attributable to the
  hazard rebuild — though note the hazard now also normalizes across a different base (the 31 index
  facilities and their own cells, rather than the statewide tract distribution), so the rebuild
  changes both the threshold and the normalization base together.

### Sensitivity Analysis and VCP Comparison

`data/cdcr/CDCR_heat_risk_sensitivity.csv`. Notebook: `CDCR_risk_indices/sensitivity_analysis.ipynb`.

Three alternative weighting schemes are tested against the equal-weight multiplicative baseline (mid-century only):

| Scheme | Formula | Logic |
| :--- | :--- | :--- |
| A — Equal multiplicative (baseline) | H × E × V, normalized 0–100 | All components equal; risk requires elevation across all three |
| B — Additive 25/25/50 | 0.25H + 0.25E + 0.50V, normalized 0–100 | Ovienmhada vulnerability upweighting; additive structure means high vulnerability alone can drive rank |
| C — Multiplicative V² | H × E × V², normalized 0–100 | Preserves multiplicative structure; vulnerability amplified but still requires hazard and exposure |

Spearman rank correlations across schemes (heat index v0.3; unchanged from v0.2 — the scheme scores are min-max within mid-century and invariant to the v0.3 final-normalization change): A vs B = 0.901, A vs C = 0.945, B vs C = 0.971. Most facilities are stable across schemes. CHCF has the largest rank swing (17 positions): it ranks 26th under equal weighting but rises to 9th under the additive scheme, because high medical complexity drives vulnerability even without indoor heat exposure days (full AC). CRC has the next largest swing (7 positions).

VCP's `ExHeatHealth_Idx` for each prison's surrounding non-institutional census tracts (Pct_GroupQuarters ≤ 25%) is included for comparison. Spearman r between our index and the surrounding community VCP index is −0.17 — the low correlation supports the case for a prison-specific framework rather than applying community-facing indices directly to carceral facilities.

### Limitations and Future Work

- **Incarcerated workers** — the share of the facility population employed through the Prison Industry Authority (PIA) or other work assignments is not included in the vulnerability component. PIA workers face elevated heat exposure from extended time in industrial or outdoor settings. Facility-level data on full incarcerated worker participation rates are still being searched for; retained as future work.
- **Psychotropic medication use** — the share of incarcerated people on psychotropic medications is not included as a standalone sub-component. Psychotropic medications (antipsychotics, anticholinergics, mood stabilizers) impair thermoregulation and are an established heat vulnerability factor. Facility-level psychotropic prescription rates are not publicly available from CCHCS. The CCHCS health risk categories used in the medical acuity sub-component (P1, P2, medium risk) are used as proxies; retained as future work for a more direct measure.
