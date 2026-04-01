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

### Isolation

All facilities also include the following isolation variables:

| Variable | Description | Source |
| :--- | :--- | :--- |
| `dist_nearest_medical_mi` | Great-circle distance in miles to the nearest Medical & Emergency Response facility — the minimum across hospitals/medical centers, ambulance services, and fire/EMS stations in California. Calculated from each facility's centroid. | USGS National Map Structures layer (layers 14–16), April 2026 |
| `in_urban_area_2020` | `Boolean` True if the facility centroid falls within a 2020 Census Urban Area boundary (Urbanized Areas ≥50,000 population or Urban Clusters 2,500–49,999 population), False otherwise. | U.S. Census Bureau, 2020 Urban Area cartographic boundary file (cb_2020_us_ua20_500k) |

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

### Wildfire Risk

Fire Hazard Severity Zone (FHSZ) classifications from CalFire, assigned to each facility via a point-in-polygon join against two responsibility layers:

- **SRA (State Responsibility Area):** Areas where the state has primary responsibility for fire protection. 2022 FHSZ boundaries.
- **LRA (Local Responsibility Area):** Areas where local agencies (cities, counties) have primary fire protection responsibility. 2025 FHSZ boundaries.

Facilities not within any classified zone are unclassified (considered lowest risk). The two layers are mutually exclusive — a facility falls in either SRA or LRA jurisdiction.

| Variable | Description | Source |
| :--- | :--- | :--- |
| `fhsz` | Fire Hazard Severity Zone classification: `Very High`, `High`, `Moderate`, or blank if the facility is not within a classified zone. | CalFire FHSZ, SRA 2022 / LRA 2025 |
| `fhsz_responsibility` | Responsibility area type: `SRA` (State) or `LRA` (Local). Blank if the facility is not within a classified zone. | CalFire FHSZ, SRA 2022 / LRA 2025 |

# References

## Facilities

FEMA. (2025). Prison Boundaries RAPT. [Dataset]. https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/Prison_Boundaries_RAPT/FeatureServer

- The FEMA prison data set was "downloaded from HiFLD Open on July 22, 2025"

USGS National Map Structures. (2026). Medical & Emergency Response facilities [Dataset]. U.S. Geological Survey. https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer

U.S. Census Bureau. (2020). Urban Area cartographic boundary file (cb_2020_us_ua20_500k) [Dataset]. https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_ua20_500k.zip

See [`data_sources/facilities/CDCR/README.md`](data_sources/facilities/CDCR/README.md) for CDCR-specific references.

## Climate Hazards

Vulnerable Communities Platform Methods Report. (2025). Governor’s Office of Land Use and Climate Innovation. https://docs.google.com/viewerng/viewer?url=https://gov-opr.maps.arcgis.com/sharing/rest/content/items/ff3579e26cf643e082344b91d3f591d2/data


CalEnviroScreen 5.0. (2026). [Dataset]. California Office of Environmental Health Hazard Assessment. https://data.ca.gov/dataset/draft-calenviroscreen-5-0

Cal-Adapt. (Forthcoming). [Dataset]. Climate datasets prepared for California's Fifth Climate Change Assessment.

CalFire. (2022, 2025). Fire Hazard Severity Zones [Dataset]. California Department of Forestry and Fire Protection. https://osfm.fire.ca.gov/divisions/community-wildfire-preparedness-and-mitigation/wildland-hazard-and-building-codes/fire-hazard-severity-zones-maps/
