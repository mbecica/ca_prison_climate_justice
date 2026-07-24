# CDCR Facilities Data

This folder contains source data for California Department of Corrections and Rehabilitation (CDCR) state prisons. Processed output is at `data/cdcr_facilities.csv`.

Data collection scripts are in the `scrapers/` directory.

## `cdcr_facilities.csv` Field Descriptions

### Identification

| Variable | Description | Source |
| :--- | :--- | :--- |
| `cdcr_code` | Facility acronym used by CDCR to identify state prisons. | Derived from FEMA, 2025 facility name |
| `cdcr_firecamp` | `Boolean` True or False if the facility is a fire camp. | Derived from FEMA, 2025 facility name |

### Population

| Variable | Description | Source |
| :--- | :--- | :--- |
| `average_2025_population` | Annual monthly average of total daily population in 2025. | CDCR TPOP1 PDF Reports, 2025 |
| `capacity_percent_2025` | A 0-1 value calculated from 2025 `average_2025_population` / `capacity`. Values over 1 indicate the facility is over capacity. | Derived from CDCR TPOP1 PDF Reports, 2025 |
| `age_over_50_pct` | % of population aged 50 and older averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `age_over_55_pct` | % of population aged 55 and older averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `age_50_59_pct` | % of population aged 50–59 averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `age_60_69_pct` | % of population aged 60–69 averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `age_70_79_pct` | % of population aged 70–79 averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `age_80plus_pct` | % of population aged 80 and older averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `gender_male_pct` | % of population identifying as Male averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `gender_female_pct` | % of population identifying as Female averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `race_white_pct` | % of population identifying as White averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `race_peopleofcolor_pct` | % of population identifying as any race other than White averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |

### Housing & Cooling

| Variable | Description | Source |
| :--- | :--- | :--- |
| `n_housing_buildings` | Number of active housing units (HUs) at the facility as of December 2025. HUs are wings, dormitories, or cell tiers — finer-grained than buildings. Denominator for `pct_buildings_*` columns. CVSP and FWF are null (not included in CDCR Jan 2026 report). | CDCR Air Cooling Pilot Program Supplemental Report, January 2026 (Table 2) |
| `n_housing_units` | Number of housing HVAC units (air handling units, evaporative coolers, etc.) at the facility. This is an equipment-level count from the Reuters FOIA (563 buildings × average AHUs), distinct from the housing-unit count in `n_housing_buildings`. | Raychaudhuri et al., Reuters, 2025 |
| `pct_units_evaporation` | Proportion of housing HVAC units using evaporation cooling. Sums to 1.0 with refrigeration and ventilation. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_evaporation` | Proportion of housing units (HUs) with evaporative cooling. HUs with mixed cooling types are counted under each applicable type, so values across cooling types may sum to more than 1 (e.g., SATF = 1.03). | CDCR Air Cooling Pilot Program Supplemental Report, January 2026 (Table 2) |
| `pct_units_refrigeration` | Proportion of housing HVAC units using refrigeration cooling. Sums to 1.0 with evaporation and ventilation. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_refrigeration` | Proportion of housing units (HUs) with mechanical (refrigerant) cooling. HUs with mixed cooling types are counted under each applicable type. | CDCR Air Cooling Pilot Program Supplemental Report, January 2026 (Table 2) |
| `pct_units_ventilation` | Proportion of housing HVAC units providing ventilation without cooling. Sums to 1.0 with evaporation and refrigeration. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_ventilation` | Proportion of housing units (HUs) with air handlers only (ventilation, no cooling). HUs with mixed cooling types are counted under each applicable type. | CDCR Air Cooling Pilot Program Supplemental Report, January 2026 (Table 2) |
| `rhu_pct_2025` | % of facility population in restricted housing units (12-month average, 2025). Derived from CDCR STA429 Restricted Housing Monthly Reports (Jan–Dec 2025). CRC and ASP consistently reported 0 RH units. See `restricted_housing.csv` and scraper `scrapers/extract_restricted_housing.py`. | CDCR Office of Research, STA429 Restricted Housing Monthly Reports, 2025 |

> **⚠ Cooling data — use `pct_buildings_*`, not `pct_units_*`.** There are two cooling sources here and they are easy to confuse (the column names are misleading):
> - **`pct_buildings_*` / `n_housing_buildings`** come from the **CDCR Air Cooling Pilot Supplemental Report (Jan 2026, as of Dec 2025)** — the newest, most authoritative, **complete** per-facility inventory at the housing-unit (wing/dorm/tier) level. **This is the source to use** for cooling coverage and the heat-risk index's AC sub-indicator (`pct_buildings_refrigeration`).
> - **`pct_units_*` / `n_housing_units`** come from the older **Reuters FOIA (2025)** HVAC-equipment inventory. It is **incomplete — it misses housing at 11 of 31 facilities** (e.g. CIM: 15 equipment rows, yielding a spurious 100% refrigeration vs the CDCR report's ~43%). Retained for provenance only; **do not use it for cooling coverage.**
>
> Validated against CDCR's own June-2025 statewide pie (evaporative 52% / mechanical 24% / air-handlers 19% / fans 5%): the `pct_buildings_*` report matches on mechanical (23%); its lower evaporative / higher "ventilation only" reflects real degradation of swamp-cooling systems by Dec 2025, not a labeling error. Two per-facility caveats: mixed-cooling units are counted under each type (shares can sum >1, e.g. SATF 1.03), and CIM reads 0% evaporative even though its Facility A retrofit (completed Feb 2025) is evaporative per CEQA #2018128257 — CIM's mix is the least certain. A full source-explicit column rename (`pct_units_*` → `*_reuters`) is deferred because it ripples into the frozen indoor/outdoor and heat-operations memo builders.

### Facility Characteristics

| Variable | Description | Source |
| :--- | :--- | :--- |
| `year_opened` | The year the facility was opened as a state facility. Primary source: LAO 2020 Figure 1 (all 34 prisons). Corrections: FOL set to 1880 (was null — key mismatch in source file), CVSP set to 1988 (was null), CMC corrected to 1961 (was 1954), CTF corrected to 1946 (was 1948). FWF set to 2013 (co-located women's facility at Folsom, not in LAO). | Legislative Analyst's Office (2020). *Effectively Managing State Prison Infrastructure* (Report 4186, Feb. 2020), Figure 1, p. 4. https://lao.ca.gov/reports/2020/4186/prison-infrastructure-022820.pdf |
| `year_opened_notes` | Notes on the year opened, e.g. if the facility was previously a different institution, or source discrepancies. | Legislative Analyst's Office (2020). *Effectively Managing State Prison Infrastructure*, Figure 1. |
| `planned_closure` | If the facility is marked for closure, indicated by `Yes` or `No`. | Collected from online documentation. |
| `california_model_facility` | If the facility is included in The California Model plan, indicated by `Yes` or `No`. | Collected from online documentation. |
| `cdcr_air_cooling_pilot` | If the facility is included in the Air Cooling Pilot, indicated by `Yes` or `No`. | Collected from online documentation. |

### Staffing

| Variable | Description | Source |
| :--- | :--- | :--- |
| `sco_state_staff_2025` | Average total active state employees in 2025 (mean of February, May, and June snapshots). Excludes Prison Industry Authority (PIA) sub-entries. For CHCF, includes both CDCR operational staff and CCHCS healthcare staff, which are reported as separate entries in the SCO data but co-located at the same facility. | California State Controller's Office Active State Employees by Department reports, 2025 |
| `sco_incarcerated_staff_2025` | Average total Prison Industry Authority (PIA) workers in 2025 (mean of February, May, and June snapshots). PIA workers are incarcerated people employed through the Prison Industry Authority at each facility. Blank if the facility has no PIA operation. | California State Controller's Office Active State Employees by Department reports, 2025 |

### Programs (SB 601)

| Variable | Description | Source |
| :--- | :--- | :--- |
| `cognitive_behavioral_interventions` | Semicolon-separated list of Cognitive Behavioral Intervention programs the facility had operational capacity for during 2024-2025. Programs include Life Skills and Outpatient. Blank if the facility reported no CBI capacity. | CDCR SB 601 Programs Dashboard, 2024-2025 |
| `rehabilitative_programs` | Semicolon-separated list of Rehabilitative Programs the facility had operational capacity for during 2024-2025. Programs include Academic Education, Career Technical Education, Cognitive Behavioral Intervention - Sex Offender, and Transitions. Blank if the facility reported no rehabilitative program capacity. | CDCR SB 601 Programs Dashboard, 2024-2025 |

### Health Care Population (CCHCS)

The denominator for all CCHCS percentage metrics is the total facility population. The four risk tiers (High Risk Priority 1, High Risk Priority 2, Medium Risk, Low Risk) sum to exactly 100% of the facility population for every month in the source data. Values are 12-month averages across all available months in 2025 (31 of 34 facilities matched; FWF has no separate CCHCS entry, CCC and DVI are closed).

Risk tier definitions (source: CCHCS Health Care Services Dashboard):

**High Risk Priority 1:** Patients triggering 2 of the following flags: (1) Sensitive Medical Condition; (2) High hospital, ED, Specialty Care, and Pharmacy costs; (3) Multiple hospitalizations (2 or more)\*; (4) Multiple ED visits (3 or more)\*; (5) High Risk Specialty Consultations; (6) Significant Abnormal Labs; (7) Age 65 or older; (8) Specific High-Risk Diagnoses/Procedures. \*A patient receiving a point for multiple hospitalizations cannot also receive a point for multiple ED visits.

**High Risk Priority 2:** Patients triggering 1 of the flags listed in High Risk Priority 1.

**Medium Risk:** Patients with 1 or more chronic illnesses (based on prescribed medications, lab tests, or MHSDS enrollment), including MH High Utilization and Permanent ADA. Excludes High Risk 1/2 patients and those with well-controlled chronic conditions. Well-controlled conditions include: Asthma, Diabetes, Hypertension, HCV, Latent TB.

**Low Risk:** Patients with no chronic conditions or with well-controlled chronic conditions (same criteria as Medium Risk exclusions above).

| Variable | Description | Source |
| :--- | :--- | :--- |
| `cchcs_high_risk_p1_pct_2025` | % of facility population classified as High Risk Priority 1 (12-month average, 2025). | CCHCS Health Care Services Dashboard, 2025 |
| `cchcs_high_risk_p2_pct_2025` | % of facility population classified as High Risk Priority 2 (12-month average, 2025). | CCHCS Health Care Services Dashboard, 2025 |
| `cchcs_medium_risk_pct_2025` | % of facility population classified as Medium Risk (12-month average, 2025). | CCHCS Health Care Services Dashboard, 2025 |
| `cchcs_low_risk_pct_2025` | % of facility population classified as Low Risk (12-month average, 2025). | CCHCS Health Care Services Dashboard, 2025 |
| `cchcs_mental_health_eop_pct_2025` | % of facility population in the Mental Health Enhanced Outpatient Program (EOP) (12-month average, 2025). | CCHCS Health Care Services Dashboard, 2025 |
| `cchcs_dpp_pct_2025` | % of facility population enrolled in the Disability Placement Program (DPP) (12-month average, 2025). | CCHCS Health Care Services Dashboard, 2025 |
| `cchcs_age_over_50_pct_2025` | % of facility population aged 50 or older (12-month average, 2025). | CCHCS Health Care Services Dashboard, 2025 |
| `cchcs_specialized_beds_2025` | Number of Specialized Health Care Beds at the facility (12-month average count, 2025). | CCHCS Health Care Services Dashboard, 2025 |

## Additional Source Files

### `mpar_projects_completed.csv`
Completed capital projects from CDCR Master Plan Annual Reports (MPARs) for fiscal years 2022 through 2025. Each row is a single project marked as Complete in the given MPAR year. Columns: `mpar_year` (MPAR edition year, 2022–2025), `institution` (CDCR facility code — FSP used for Folsom State Prison per source documents; SQ used for 2022 San Quentin, SQRC for 2023–2025; Multiple for statewide projects), `project_id` (CDCR project identifier, format P-YYMM-NNNNN), `title` (project title), `type` (MA = Major Capital Outlay, MI = Minor Capital Outlay, SRP = Special Repair Program, DM = Deferred Maintenance Program, E = Energy Conservation/Sustainability Program), `completed` (completion date as M/YYYY), `total_approved_funding` (total approved funding in dollars; 0 for statewide program projects where funding is tracked at the program level). Cross-MPAR deduplication rule: projects appearing as Complete in multiple MPARs are assigned to the earliest year. Only confirmed duplicate: SATF P-1314-00201 (Complete in both 2024 and 2025 MPARs) → assigned mpar_year=2024. Source: CDCR Facilities Planning and Construction Management Division MPAR PDFs, 2022–2025, in `cdcr_facilities_planning/`.

### `air_cooling_housing_units_dec2025.csv`
Housing unit design types and 2025 indoor heat exposure by institution, as of December 2025. Columns: `institution` (CDCR code; FSP used for Folsom per source document), `hu_270` through `hu_nonstandard` (count of active housing units of each design type: 270-style, 180-style, Dormitories, Cross-Top, Non-Standard), `days_above_78f_2025` (number of days May–October 2025 with indoor temperatures exceeding 78°F). Non-Standard includes single cells, restricted housing, outpatient housing, and other atypical designs. Total active housing units across 31 institutions: 791. Source: CDCR Air Cooling Pilot Program Supplemental Report, January 2026 (Table 1).

### `air_cooling_infrastructure_dec2025.csv`
Air cooling infrastructure by institution as of December 2025. Columns: `institution` (CDCR code; FSP used for Folsom), `n_housing_units` (total active housing units), `hu_air_handlers_only` (HUs with air handlers/ventilation only, no cooling), `hu_evaporative_cooling` (HUs with evaporative cooling), `hu_mechanical_cooling` (HUs with mechanical/refrigerant cooling). Column values are not mutually exclusive — housing units with mixed cooling systems may be counted in multiple columns, so per-institution column sums may exceed `n_housing_units`. System-wide totals: 791 total HUs; 262 air-handlers-only (33%), 348 evaporative (44%), 181 mechanical (23%). Note: SCC `n_housing_units` corrected from OCR-read 61 to 81 (consistent with Table 1 design counts and the 791 column total). Source: CDCR Air Cooling Pilot Program Supplemental Report, January 2026 (Table 2).

### `sb601_operations.csv`
Monthly operational metrics for all 32–35 CDCR institutions across fiscal years 2021-2022 through 2024-2025. Columns: `institution` (CDCR code), `fiscal_year`, `category`, `metric`, and one column per month (`Jul` through `Apr`). Three categories: Lockdowns and Modified Programs, Number of Deaths, and Overtime Hours. Source: CDCR SB 601 Programs Dashboard.

### `sb601_programs.csv`
Program operational capacity by institution for fiscal year 2024-2025. Used to derive the `cognitive_behavioral_interventions` and `rehabilitative_programs` columns. Source: CDCR SB 601 Programs Dashboard.

### `cchcs_ipc.csv`
Monthly Institution & Population Characteristics for all CDCR institutions, January 2017–December 2025 (108 months), in long format. Columns: `month`, `institution` (CDCR code), `measure`, `value`. Measures include the eight health classification variables above plus Institution Population (total facility headcount). Source: CCHCS Health Care Services Dashboard.

### `cchcs_measures.csv`
Monthly staffing vacancy rates, labor costs, and ED/hospital utilization for all CDCR institutions, January 2017–December 2025 (108 months), in long format. Columns: `month`, `group`, `institution` (CDCR code), `measure`, `value`. Contains 26,302 rows across 7 measures in three groups:

| Group | Measure | Description |
| :--- | :--- | :--- |
| Staffing | `Actual Vacancies (All)` | Overall vacancy rate across all health care staff |
| Staffing | `Medical Vacancies (All)` | Vacancy rate for medical staff |
| Staffing | `Mental Health Vacancies (All)` | Vacancy rate for mental health staff |
| Staffing | `Dental Vacancies (All)` | Vacancy rate for dental staff |
| Major Costs | `Total Labor Cost (All)` | Total labor cost per patient per month (dollars) |
| Major Costs | `ED & Hospital Stays` | Non-labor cost of ED and hospital stays per patient per month (dollars) |
| Other Trends | `ED/Hospital Stay*` | ED and hospital send-out rate (encounters per 1,000 patients per month) |

Source: CCHCS Health Care Services Dashboard.

### `sco_staffing.csv`
Total active employees at CDCR facilities from the California State Controller's Office "Active State Employees by Department" reports. Cross-sectional snapshots extracted from PDFs in `cdcr_staffing/`. Long format: one row per facility per snapshot. Columns: `date` (report date as "Month YYYY"), `sco_facility_name` (facility name as it appears in the SCO report), `full_time`, `part_time`, `intermittent`, `indeterminate`, `total`.

**Coverage:** 8 snapshots spanning April 2021 – February 2026. Extraction script: `scrapers/extract_sco_staffing.py`.

**Rows included:** All CDCR-department rows except: CCHCS regional offices, CTRA training academies, CDCR-CHCF-PIP, Parole & Community Services, Richard A. McGee Correctional Training Center, Corrections/Administration, Youth Authority/Administration, Corr/Inmate Welfare Fund, and CORR/IND Revolving Fund. Prison Industry Authority (PIA) sub-entries are retained as separate rows with names ending in `- PIA`. The row `CDCR/CCHCS CA HEALTH CARE` represents CCHCS healthcare staff co-located at the California Health Care Facility (CHCF); it is separate from the `CA. HEALTH CARE FACILITY` row which covers CDCR operational staff at the same facility.

Source: California State Controller's Office Active State Employees by Department reports, collected via Wayback Machine snapshots.

## References

CDCR 2025 Monthly Total Population (TPOP1) Archive. (2025). [Dataset]. CDCR Office of Research. https://www.cdcr.ca.gov/research/2025-monthly-total-population-tpop1-archive/

CDCR Population Data Set. (2025). [Dataset]. CDCR Office of Research.

Raychaudhuri, D., Farley, C., Hartman, T., & Arranz, A. (2025, July 30). Scorching cells: How heat threatens lives in America's prisons. Reuters. https://www.reuters.com/graphics/USA-TEMPERATURE/PRISONS/jnpwbejwlvw/

CDCR SB 601 Programs Dashboard. (2025). [Interactive dashboard]. California Department of Corrections and Rehabilitation. https://app.powerbigov.us/view?r=eyJrIjoiYzlkM2RiNWEtZDRjMi00ODllLTg2YzEtZjYyM2MwMjA5NmQ0IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9&pageName=5a926528bbf7e48d60c2

CCHCS Health Care Services Dashboard. (2025). [Interactive dashboard]. California Correctional Health Care Services. https://cchcs.ca.gov/dashboard/

California State Controller's Office. (2021–2026). Active State Employees by Department [PDF reports]. California State Controller's Office. Retrieved via Wayback Machine snapshots.

Legislative Analyst's Office. (2020). *Effectively Managing State Prison Infrastructure* (Report 4186). California Legislative Analyst's Office. https://lao.ca.gov/reports/2020/4186/prison-infrastructure-022820.pdf

CDCR Facilities Planning and Construction Management Division. (2022–2025). *Master Plan Annual Reports*. California Department of Corrections and Rehabilitation. PDFs in `cdcr_facilities_planning/`.

CDCR. (2026, January). *Air Cooling Pilot Program Supplemental Report*. California Department of Corrections and Rehabilitation. https://www.cdcr.ca.gov/fpcm/wp-content/uploads/sites/184/2026/02/Air_Cooling_Document_for_Legislature.pdf


---

## Behavioral & Incarceration Statistics

### Violent Incidents by Facility (2021–2025)

`cdcr_violent_incidents_by_facility.csv` — monthly violent incident counts per facility, extracted from CDCR Incident Report PDFs (CompStat and Public series). Script: `extract_violent_incidents.py`.

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

The per-facility annual average (`avg_annual_violent_incidents`) is added to `data/cdcr_facilities.csv`. System-wide average: ~9,900/year across 2021–2025.

### Average Sentence by Admission Type (2023–2026)

`cdcr_avg_sentence_by_admission.csv` — average sentence length in months per admission type per month, scraped from the CDCR Population Data Points Power BI dashboard (Admissions > Population Demographics > Crosstabs > Average Sentence, rows: Admission Type, columns: None). Script: `scrapers/fetch_cdcr_avg_sentence.js`.

**Coverage:** January 2023–March 2026, 4 admission types. Some months suppressed (counts < 10).

| Admission Type | Mean sentence | Range |
| :--- | :--- | :--- |
| Felon New Admissions | 84 months (7.0 yrs) | 65–97 mo |
| Felon Parole Violators – With New Term | 53 months (4.4 yrs) | 43–71 mo |
| Felon Parole Violators – Return to Custody | 155 months (13.0 yrs) | 60–252 mo |
| Felon Pending Revocations | 41 months (3.4 yrs) | 16–96 mo |

Values are average sentence at time of admission, not additional time added. "Return to Custody" counts are largely suppressed (<10/month); the operative recidivist sentence length is "With New Term" at 4.4 years.

### Three-Year Return Rate by Length of Stay (2008–2020)

`cdcr_recidivism_los.csv` — three-year return-to-prison rate by length-of-stay category and fiscal year, scraped from the CDCR Adult Recidivism Power BI dashboard (Returns measure → Crosstabs → Fiscal Year: All → Row: Length of Stay → Column: Length of Stay). Script: `scrapers/fetch_cdcr_recidivism_los.js`.

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

Return rates declined substantially after California's 2011 Public Safety Realignment, which shifted low-level offenders from state prison to county jails. Pre-2011 system-wide rates (~55–65%) are not comparable to post-2011 rates (~17–24%) due to this structural break in the release cohort composition. The 2017-18 through 2019-20 cohorts show an additional downward bias from COVID-19 disruptions to policing, courts, and CDCR intakes. Pre-COVID system-wide baseline (4-cohort average, FY 2013-14 through FY 2016-17): **23.7%**.
