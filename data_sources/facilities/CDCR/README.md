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
| `age_over_60_pct` | % of population aged 60 and older averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `age_over_65_pct` | % of population aged 65 and older averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `gender_male_pct` | % of population identifying as Male averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `gender_female_pct` | % of population identifying as Female averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `race_white_pct` | % of population identifying as White averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |
| `race_peopleofcolor_pct` | % of population identifying as any race other than White averaged from monthly counts in 2025. | CDCR Population Data Set, 2025 |

### Housing & Cooling

| Variable | Description | Source |
| :--- | :--- | :--- |
| `n_housing_buildings` | Number of distinct housing buildings at the facility. | Raychaudhuri et al., Reuters, 2025 |
| `n_housing_units` | Number of housing HVAC units (air handling units, evaporative coolers, etc.) at the facility. | Raychaudhuri et al., Reuters, 2025 |
| `pct_units_evaporation` | Proportion of housing HVAC units using evaporation cooling. Sums to 1.0 with refrigeration and ventilation. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_evaporation` | Proportion of housing buildings with at least one evaporation cooling unit. Buildings with mixed cooling types are counted under each applicable type, so values across cooling types may sum to more than 1. | Raychaudhuri et al., Reuters, 2025 |
| `pct_units_refrigeration` | Proportion of housing HVAC units using refrigeration cooling. Sums to 1.0 with evaporation and ventilation. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_refrigeration` | Proportion of housing buildings with at least one refrigeration cooling unit. Buildings with mixed cooling types are counted under each applicable type, so values across cooling types may sum to more than 1. | Raychaudhuri et al., Reuters, 2025 |
| `pct_units_ventilation` | Proportion of housing HVAC units providing ventilation without cooling. Sums to 1.0 with evaporation and refrigeration. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_ventilation` | Proportion of housing buildings with at least one ventilation-without-cooling unit. Buildings with mixed cooling types are counted under each applicable type, so values across cooling types may sum to more than 1. | Raychaudhuri et al., Reuters, 2025 |

### Facility Characteristics

| Variable | Description | Source |
| :--- | :--- | :--- |
| `year_opened` | The year the facility was opened as a state facility. | Collected from online documentation. |
| `year_opened_notes` | Notes on the year opened, e.g. if the facility was previously a different institution. | Collected from online documentation. |
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

### `sb601_operations_2021-2025.csv`
Monthly operational metrics for all 32–35 CDCR institutions across fiscal years 2021-2022 through 2024-2025. Columns: `institution` (CDCR code), `fiscal_year`, `category`, `metric`, and one column per month (`Jul` through `Apr`). Three categories: Lockdowns and Modified Programs, Number of Deaths, and Overtime Hours. Source: CDCR SB 601 Programs Dashboard.

### `sb601_programs_2024-2025.csv`
Program operational capacity by institution for fiscal year 2024-2025. Used to derive the `cognitive_behavioral_interventions` and `rehabilitative_programs` columns. Source: CDCR SB 601 Programs Dashboard.

### `cchcs_ipc_2017-2025.csv`
Monthly Institution & Population Characteristics for all CDCR institutions, January 2017–December 2025 (108 months), in long format. Columns: `month`, `institution` (CDCR code), `measure`, `value`. Measures include the eight health classification variables above plus Institution Population (total facility headcount). Source: CCHCS Health Care Services Dashboard.

### `cchcs_measures_2017-2025.csv`
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

### `sco_staffing_2020-2026.csv`
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
