# Heat and Prison Operations: Panel Regression Analysis Spec

**Status**: Design complete, not yet built
**Output target**: Table/figure exports for Google Doc
**Language**: Python

---

## 1. Research Question

Does monthly heat exposure predict worse operational outcomes at CDCR facilities, controlling for facility-level fixed effects and system-wide time shocks? This extends Skarha (2023) and Cloud (2023) — which established heat → mortality and heat → mental health pathways — to operational outcomes not previously tested in the prison literature.

---

## 2. Data Sources

| Role | File | Coverage |
|------|------|----------|
| Heat exposure (primary) | `data_sources/hazards/heat/heat_activations_monthly.csv` | 2016–2025, monthly, per facility |
| Heat exposure (robustness) | `data_sources/hazards/heat/heat_activations_daily.csv` | 2016–2025, daily — used to compute Skarha anomaly |
| Outcome: ED/Hospital Stay rate | `data_sources/facilities/CDCR/cchcs_measures.csv` | Apr 2017–Sep 2025, monthly |
| Outcome: Dental+MH Overtime | `data_sources/facilities/CDCR/sb601_operations.csv` | FY 2021–2025, wide format |
| Outcome: Modified Programs Days | same as above | FY 2021–2025, wide format |
| Crowding ratio (time-varying control) | `data_sources/facilities/CDCR/tpop1_institutions.csv` | Jan 2015–Mar 2026, monthly |
| AC type (cross-sectional moderator) | `data_sources/facilities/CDCR/air_cooling_infrastructure_dec2025.csv` | Dec 2025 snapshot |
| Security level (moderator) | `data_sources/facilities/ca_facilities.csv` | static |
| UHI (absorbed by facility FE) | `data_sources/hazards/heat/benz_uhi_facilities.csv` | static |
| AC event study: ISP completion | `data_sources/facilities/CDCR/mpar_projects_completed.csv` | P-0910-01113, 3/2024 |
| AC event study: CIM completion | same | P-1718-00132, 2/2025 |

---

## 3. Outcome Variables

### Primary (confirmatory — BH FDR correction applied)

| Outcome | Source column | Transformation | Note |
|---------|--------------|----------------|------|
| ED/Hospital Stay rate | `ED/Hospital Stay` (Other Trends group; asterisk removed) | log | Rate per 1,000 incarcerated population per month |
| Dental+MH Overtime | `Dental + Mental Health (Overtime)` | log | Hours per month |
| Incarcerated Persons-Days on Modified Programs | `Incarcerated Persons-Days on Modified Programs` | log(y+1) | 40% zeros; note in methods |

### Secondary (exploratory — labeled hypothesis-generating)

- Staffing vacancies: All, Medical, Dental, Mental Health (`cchcs_measures.csv`, Staffing group)

---

## 4. Heat Exposure Variables

### Primary
`gridmet_days_over_90f` — monthly count of days with outdoor tmax ≥ 90°F (gridMET)
Rationale: CDCR Heat Pathology Plan Stage 1 outdoor trigger; policy-relevant threshold

### Robustness check
**Skarha facility-relative anomaly**: days where tmax ≥ (facility mean summer tmax + 10°F)
- Baseline: facility-specific mean Jun–Aug tmax, 1991–2020 (WMO 30-year period)
- Compute from `heat_activations_daily.csv`
- Anchors directly to Skarha (2023), which found 5.2% increase in all-cause mortality per 10°F above facility mean

### Note on thresholds
The 90°F and 95°F fixed thresholds have no direct mortality calibration in the literature — frame only as regulatory exposure burden. The Skarha anomaly variable is the only metric with a published mortality coefficient.

---

## 5. Model Specification

### Base model (all primary outcomes)

```
Y_{it} = β₁ · Heat_{it} + β₂ · Crowding_{it} + α_i + γ_{ym} + ε_{it}
```

- `i` = facility, `t` = calendar month-year
- `α_i` = facility fixed effects (absorbs all time-invariant facility characteristics: security level, UHI, baseline climate, building type, location)
- `γ_{ym}` = year × calendar-month fixed effects (absorbs system-wide shocks: COVID, statewide policy, seasonal patterns)
- `Crowding_{it}` = `pct_occupied` from tpop1_institutions, matched to calendar month
- Standard errors: clustered by facility
- Estimation: OLS (linear TWFE); Poisson TWFE as robustness for Modified Programs Days

### Lag structure
- **Primary**: lag 0 (same calendar month)
- **Robustness table**: lag 1 (heat from prior month)
- Rationale: overtime and modified programs likely contemporaneous; ED visits could plausibly lag 1–2 months

### Multiple testing
Benjamini-Hochberg FDR correction (α = 0.05) applied across the 3 primary outcomes.
Secondary/moderation results reported with uncorrected p-values, labeled exploratory.

---

## 6. Moderation Analyses (Exploratory)

### 6a. AC type interaction (cross-sectional)
Add interaction: `Heat_{it} × AC_type_i`
AC type categories (from `air_cooling_infrastructure_dec2025.csv`):
- Mechanical cooling (refrigeration) — reference
- Evaporative cooling
- Air handlers only (ventilation)

Hypothesis: heat coefficient larger at ventilation-only and evaporative facilities.
Note: AC type is time-invariant and absorbed by facility FE in the main model — the interaction term is identified from cross-facility variation in the heat slope, not the AC level itself.

### 6b. Security level interaction
Add interaction: `Heat_{it} × SecurityLevel_i`
Source: `securelvl` from `ca_facilities.csv`
Precedent: Tahamont (2019) establishes security level as a determinant of rules violations in CA prisons.
Hypothesis: heat effects on modified programs larger at higher security levels.

---

## 7. Event Study: ISP Full HVAC Replacement

### Design
Difference-in-differences with staggered adoption (N=2 treated facilities):

| Facility | Project | Completion | Type |
|----------|---------|------------|------|
| ISP | P-0910-01113 HVAC | 3/2024 | Full facility replacement — primary |
| CIM | P-1718-00132 Air Cooling Facility A | 2/2025 | Partial — secondary, limited post-period |

Treatment indicator: `Post_{it}` = 1 for facility i in months ≥ completion date.

### Model
```
Y_{it} = β₁ · Heat_{it} + β₂ · (Heat_{it} × Post_{it}) + β₃ · Post_{it} + β₂ · Crowding_{it} + α_i + γ_{ym} + ε_{it}
```

`β₂` is the key coefficient: does the heat-outcome relationship weaken after AC installation?

Control group: all non-treated CDCR facilities in the panel.

### Caveats
- N=2 treated facilities is too small for formal staggered DiD (Callaway-Sant'Anna etc.)
- Frame as descriptive event study / case illustration, not causal identification
- ISP is primary; CIM has ~1 summer of post-period data only
- SATF (11/2025) excluded — outside the operations data window

---

## 8. Required Data Pipeline (build before analysis)

### Step 1: Reshape sb601 fiscal-year wide → calendar month long
- Input: `sb601_operations.csv` (wide: columns Jul–Apr per fiscal year)
- Map fiscal year months to calendar months: FY 2021-2022 Jul = July 2021, etc.
- Output: long format with columns `facility`, `year`, `month`, `category`, `metric`, `value`

### Step 2: Build master panel
Join all sources to a single `facility × calendar_month` panel:
- Heat: `heat_activations_monthly.csv` (`gridmet_days_over_90f`, `gridmet_days_over_95f`)
- Crowding: `tpop1_institutions.csv` (pct_occupied) — match on facility + nearest report date
- Outcomes from cchcs: direct merge on facility + month-year
- Outcomes from sb601: after Step 1

### Step 3: Compute Skarha facility-relative anomaly
- From `heat_activations_daily.csv`, compute each facility's mean Jun–Aug tmax over 1991–2020
- For each facility-day: flag if tmax ≥ (facility mean + 10°F)
- Aggregate to monthly count: `gridmet_days_over_avg_plus10_base1991_2020`

### Step 4: Merge static covariates
- AC type: `air_cooling_infrastructure_dec2025.csv` → categorical variable (mechanical / evaporative / ventilation)
- Security level: `ca_facilities.csv` → `securelvl`
- AC event study indicator: construct `post_ac` from mpar completion dates

### Step 5: Validate panel balance
- Report facility × month coverage by outcome
- Flag facilities with <12 months of data in any outcome
- Note: ED/Hospital Stay covers 2017–2025; sb601 outcomes cover 2021–2025 only

---

## 9. Anchoring Literature

| Paper | What we borrow |
|-------|---------------|
| Skarha et al. (2023) *PLOS ONE* | Facility-relative heat anomaly metric; distributed lag framework; TWFE precedent for prison panel |
| Cloud et al. (2023) *JAMA Network Open* | Conditional FE regression in prison context; dose-response framing |
| Ovienmhada et al. (2024) *GeoHealth* | Applies Skarha threshold to CA facilities specifically |
| Mukherjee & Sanders (2021) *NBER WP 28987* | Causal evidence for heat → inmate violence in Mississippi prisons (no A/C); TWFE with facility + year + week-of-year FEs; ~20% increase in violent acts on 80°F+ days; effects specific to intense violence, null for minor infractions. Directly motivates our UOF outcome and explains our California system-wide null (most CA facilities have cooling). ISP post-HVAC UOF drop is consistent with their A/C policy implication. |
| Tahamont (2019) | Security level as covariate for rules violations in CA prisons |
| Burke et al. (2015); Graff Zivin & Neidell (2014) | TWFE with year×month FEs; clustered SEs; log outcomes in environmental economics panels |

**Framing**: This analysis extends Skarha and Cloud by testing operational outcomes (staffing, utilization, programs) rather than mortality and behavioral incidents. It is the first (to our knowledge) to use CDCR's own SB 601 reporting data to test heat-operations relationships at the facility-month level.

---

## 10. Output Plan

| Output | Type | destination |
|--------|------|-------------|
| Main results table | 3 outcomes × 2 heat metrics, β + SE + p + BH-adjusted p | Google Doc table |
| Robustness table | Lag 1 results; Poisson for Modified Programs | Google Doc table |
| Moderation table | AC type and security level interactions | Google Doc table |
| ISP event study figure | Heat coefficient pre/post by month (event-time plot) | exported PNG/SVG |
| Panel summary table | N facilities, N months, mean outcomes by heat quartile | Google Doc table |
