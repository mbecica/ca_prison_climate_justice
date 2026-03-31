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

CDCR state prison facilities have additional variables covering population demographics, housing and cooling infrastructure, programs, and health care population characteristics. See [`data_sources/facilities/CDCR/README.md`](data_sources/facilities/CDCR/README.md) for full field descriptions and sources.

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
| `heat_hazard_idx_norm` | Normalized Heat Hazard Index (0-100) per census tract. Calulated from AQI and historic annual days above 90F. | Derived from CalEnviroScreen 5.0, 2025 and Cal-Adapt, 2025 |

# References

## Facilities

FEMA. (2025). Prison Boundaries RAPT. [Dataset]. https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/Prison_Boundaries_RAPT/FeatureServer

- The FEMA prison data set was "downloaded from HiFLD Open on July 22, 2025"

See [`data_sources/facilities/CDCR/README.md`](data_sources/facilities/CDCR/README.md) for CDCR-specific references.

## Climate Hazards

Vulnerable Communities Platform Methods Report. (2025). Governor’s Office of Land Use and Climate Innovation. https://docs.google.com/viewerng/viewer?url=https://gov-opr.maps.arcgis.com/sharing/rest/content/items/ff3579e26cf643e082344b91d3f591d2/data


CalEnviroScreen 5.0. (2026). [Dataset]. California Office of Environmental Health Hazard Assessment. https://data.ca.gov/dataset/draft-calenviroscreen-5-0

Cal-Adapt. (Forthcoming). [Dataset]. Climate datasets prepared for California's Fifth Climate Change Assessment.
