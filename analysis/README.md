# Analysis

Notebooks and scripts are in this directory. Outputs are written to `data/`.

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

**Limitations and future work:**
- **Incarcerated workers** — the share of the facility population employed through Prison Industry Authority (PIA) or other work assignments is not included in the vulnerability component. PIA workers face elevated heat exposure from extended time in industrial or outdoor settings. Facility-level data on the full incarcerated worker participation rates are still being searched for; retained as future work.
- **Psychotropic medication use** — the share of incarcerated people on psychotropic medications is not included as a standalone sub-component. Psychotropic medications (antipsychotics, anticholinergics, mood stabilizers) impair thermoregulation and are an established heat vulnerability factor. Facility-level psychotropic prescription rates are not publicly available from CCHCS. The CCHCS health risk categories used in the medical acuity sub-component (P1, P2, medium risk) are used instead, with the assumption that psychotropic medication use is captured within those broader risk tier definitions; retained as future work for a more direct measure.

### Outdoor vs. Indoor Temperature Gap

The CDCR Heat Pathology Plan Stage I and Stage III thresholds are defined by **indoor** housing unit temperatures (≥ 90°F and ≥ 95°F respectively). Outdoor gridMET data is used as a proxy for trend analysis and hazard mapping, but outdoor temperatures systematically overstate the number of days that cross indoor thresholds. The exposure component of the risk index uses indoor 78°F day counts directly (from CDCR's January 2026 Air Cooling Pilot Supplemental Report) to address this gap.

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
