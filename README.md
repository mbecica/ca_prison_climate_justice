# California Prison Climate Justice
This is a working repository for collecting climate hazard data for California carceral facilities. 

All facilities (local and county jails, state prisons, federal prisons) have climate hazard data associated with them plus their population, capacity, and security level if that data was available from FEMA and HiFLD. State prisons have additional facilities data which can be used to inform exposure and vulnerability calculations. As of March 2026, there were 357 facilities total, and 84 facilities with state jurisdiction. 

This project is in support of Climate Justice Coalition 4 California Prisons and a masters capstone at UC Berkeley's Department of City & Regional Planning. It is inspired by and continues the work of the [Toxic Prisons Project](http://toxicprisons.com/) and Ella Baker Center's [Hidden Hazards Report](https://ellabakercenter.org/reports/hiddenhazards/) (2023).

# Data Fields
Processed data can be found in the `data` folder. 

## Facilities Data

All facilities include their name, address, telephone and website information (FEMA, 2025) plus the following variables:
| Variable | Description | Source | 
| :--- | :--- | :--- | 
| `facilityid` | Facility ID from HiFLD Open. | FEMA, 2025 | 
| `type` | Jurisdiction of the facility (`LOCAL`:54, `COUNTY`:188, `MULTI`:3, `STATE`:84, `FEDERAL`:28. | FEMA, 2025 with manual review and updates to 5 facilities that were incorrectly typed. | 
| `population` | Population provided by FEMA and HiFLD Open. Only 68 facilities have data, and it is unclear what year this population data is from. | FEMA, 2025 | 
| `capacity_percent` | A 0-1 value calculated from `population` / `capacity`. | Derived from FEMA, 2025 | 
| `latitude` | Derived from the geographic centerpoint of the facility boundary. |  | 
| `longitude` | Derived from the geographic centerpoint of the facility boundary. |  | 
| `tract_geoid` | The 11-digit census tract GEOID that the facility centerpoint is within. |  | 

CDCR facilities have additional variables:
| Variable | Description | Source | 
| :--- | :--- | :--- | 
| `cdcr_code` | Facility acronym used by CDCR to identify state prisons. | Derived from FEMA, 2025 facility name |
| `cdcr_firecamp` | `Boolean` True or False if the facility is a fire camp. | Derived from FEMA, 2025 facility name | 
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
| `n_housing_buildings` | Number of distinct housing buildings at the facility. | Raychaudhuri et al., Reuters, 2025 |
| `n_housing_units` | Number of housing HVAC units (air handling units, evaporative coolers, etc.) at the facility. | Raychaudhuri et al., Reuters, 2025 |
| `pct_units_evaporation` | Proportion of housing HVAC units using evaporation cooling. Sums to 1.0 with refrigeration and ventilation. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_evaporation` | Proportion of housing buildings with at least one evaporation cooling unit. Buildings with mixed cooling types are counted under each applicable type, so values across cooling types may sum to more than 1. | Raychaudhuri et al., Reuters, 2025 |
| `pct_units_refrigeration` | Proportion of housing HVAC units using refrigeration cooling. Sums to 1.0 with evaporation and ventilation. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_refrigeration` | Proportion of housing buildings with at least one refrigeration cooling unit. Buildings with mixed cooling types are counted under each applicable type, so values across cooling types may sum to more than 1. | Raychaudhuri et al., Reuters, 2025 |
| `pct_units_ventilation` | Proportion of housing HVAC units providing ventilation without cooling. Sums to 1.0 with evaporation and refrigeration. | Raychaudhuri et al., Reuters, 2025 |
| `pct_buildings_ventilation` | Proportion of housing buildings with at least one ventilation-without-cooling unit. Buildings with mixed cooling types are counted under each applicable type, so values across cooling types may sum to more than 1. | Raychaudhuri et al., Reuters, 2025 |
| `year_opened` | The year the facility was opened as a state facility. | Collected from online documentation. |
| `year_opened_notes` | Notes on the year opened, e.g. if the facility was previously a different institution. | Collected from online documentation. |
| `planned_closure` | If the facility is marked for closure, indicated by `Yes` or `No`. | Collected from online documentation. |
| `california_model_facility` | If the facility is included in The California Model plan, indicated by `Yes` or `No`. | Collected from online documentation. |
| `cdcr_air_cooling_pilot` | If the facility is included in the Air Cooling Pilot, indicated by `Yes` or `No`. | Collected from online documentation. |
| `cognitive_behavioral_interventions` | Semicolon-separated list of Cognitive Behavioral Intervention programs the facility had operational capacity for during 2024-2025. Programs include Life Skills and Outpatient. Blank if the facility reported no CBI capacity. | CDCR SB 601 Programs Dashboard, 2024-2025 |
| `rehabilitative_programs` | Semicolon-separated list of Rehabilitative Programs the facility had operational capacity for during 2024-2025. Programs include Academic Education, Career Technical Education, Cognitive Behavioral Intervention - Sex Offender, and Transitions. Blank if the facility reported no rehabilitative program capacity. | CDCR SB 601 Programs Dashboard, 2024-2025 |

## Climate Hazard Data

### Heat and Air Quality Index

The heat hazard index includes both outside temperatures and air quality

Heat and Air Quality variables include:
| Variable | Description | Source | 
| :--- | :--- | :--- | 
| `days_over_90_historic` | Near-historic annual number of days over 90F per census tract. | Cal-Adapt, 2025 | 
| `days_over_90_midcentury` | Projected annual number of days over 90F per census tract by Mid-Century (2041-2070). | Cal-Adapt, 2025 | 
| `delta_90` | The change of annual number of days over 90F between Mid-Century (2041-2070) and historic. | Cal-Adapt, 2025 |
| `PollutionP` | Normalized pollution exposure (0-100) per census tract; includes all pollution types. | CalEnviroScreen 5.0, 2025 | 
| `AQI_norm` | Normalized AQI exposure (0-100) per census tract. Calulated from Ozone, PM2.5, and Diesel exposures. | CalEnviroScreen 5.0, 2025 | 
| `heat_hazard_idx_norm` | Normalized Heat Hazard Index (0-100) per census tract. Calulated from AQI and historic annual days above 90F. | CalEnviroScreen 5.0, 2025 | 

# References

## Facilities

FEMA. (2025). Prison Boundaries RAPT. [Dataset]. https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/Prison_Boundaries_RAPT/FeatureServer

- The FEMA prison data set was "downloaded from HiFLD Open on July 22, 2025"

CDCR 2025 Monthly Total Population (TPOP1) Archive. (2025). [Dataset]. CDCR Office of Research. https://www.cdcr.ca.gov/research/2025-monthly-total-population-tpop1-archive/

CDCR Population Data Set. (2025). [Dataset]. CDCR Office of Research.

Raychaudhuri, D., Farley, C., Hartman, T., & Arranz, A. (2025, July 30). Scorching cells: How heat threatens lives in America's prisons. Reuters. https://www.reuters.com/graphics/USA-TEMPERATURE/PRISONS/jnpwbejwlvw/

CDCR SB 601 Programs Dashboard. (2025). [Interactive dashboard]. California Department of Corrections and Rehabilitation. https://app.powerbigov.us/view?r=eyJrIjoiYzlkM2RiNWEtZDRjMi00ODllLTg2YzEtZjYyM2MwMjA5NmQ0IiwidCI6IjA2NjI0NzdkLWZhMGMtNDU1Ni1hOGY1LWMzYmM2MmFhMGQ5YyJ9&pageName=5a926528bbf7e48d60c2

## Climate Hazards

Vulnerable Communities Platform Methods Report. (2025). Governor’s Office of Land Use and Climate Innovation. https://docs.google.com/viewerng/viewer?url=https://gov-opr.maps.arcgis.com/sharing/rest/content/items/ff3579e26cf643e082344b91d3f591d2/data


CalEnviroScreen 5.0. (2026). [Dataset]. California Office of Environmental Health Hazard Assessment. https://data.ca.gov/dataset/draft-calenviroscreen-5-0

Cal-Adapt. (Forthcoming). [Dataset]. Climate datasets prepared for California's Fifth Climate Change Assessment.
