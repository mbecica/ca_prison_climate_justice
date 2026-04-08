# California Prison Climate Justice
This is a working repository for collecting climate hazard data for California carceral facilities. 

All facilities (local and county jails, state prisons, federal prisons) have climate hazard data associated with them plus their population, capacity, and security level if that data was available from FEMA and HiFLD. State prisons have additional facilities data which can be used to inform exposure and vulnerability calculations. As of March 2026, there were 357 facilities total, and 84 facilities with state jurisdiction. 

This project is in support of Climate Justice Coalition 4 California Prisons and a masters capstone at UC Berkeley's Department of City & Regional Planning. It is inspired by and continues the work of the [Toxic Prisons Project](http://toxicprisons.com/) and Ella Baker Center's [Hidden Hazards Report](https://ellabakercenter.org/reports/hiddenhazards/) (2023).

# Data Files

| File | Description |
| :--- | :--- |
| `data/allfacilities_climate_hazards.csv` | All 357 facilities with all climate hazard fields joined (heat/AQI, flood, drought, wildfire FHSZ/WUI). Build with `analysis/hazards/join_climate_hazards.ipynb`. |
| `data/cdcr/CDCR_heat_risk_index.csv` | 31 CDCR state prisons — heat risk index (Hazard × Exposure × Vulnerability), current and mid-century. Build with `analysis/CDCR_risk_indices/heat_risk_index.ipynb`. |

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
| `uhi_normalized` | Urban heat island exposure score (0–1). Derived from Benz & Burney (2021) daytime surface urban heat anomaly (ΔT). Negative ΔT clamped to 0; normalized against the maximum ΔT across state prisons (7.247°C, CIM). Direct tract match applied to all 357 facilities (267 matched); 1-mile polygon-edge buffer applied to CDCR state prisons only where validated (8 additional). 82 facilities null — primarily rural fire camps and remote county jails in undeveloped NLCD tracts. See `data_sources/hazards/README.md` for full methodology and source comparison. | Benz & Burney (2021), Harvard Dataverse doi:10.7910/DVN/1F72FB | 

### Isolation

All facilities also include the following isolation variables:

| Variable | Description | Source |
| :--- | :--- | :--- |
| `dist_nearest_medical_mi` | Great-circle distance in miles to the nearest Medical & Emergency Response facility — the minimum across hospitals/medical centers, ambulance services, and fire/EMS stations in California. Calculated from each facility's centroid. | USGS National Map Structures layer (layers 14–16), April 2026 |
| `in_urban_area_2020` | `Boolean` True if the facility centroid falls within a 2020 Census Urban Area boundary (Urbanized Areas ≥50,000 population or Urban Clusters 2,500–49,999 population), False otherwise. | U.S. Census Bureau, 2020 Urban Area cartographic boundary file (cb_2020_us_ua20_500k) |

CDCR state prison facilities have additional variables covering population demographics, housing and cooling infrastructure, programs, and health care population characteristics. See [`data_sources/facilities/CDCR/README.md`](data_sources/facilities/CDCR/README.md) for full field descriptions and sources.

## Climate Hazard Data

### Heat and Air Quality Index

The heat and air quality index combines daytime heat, nighttime heat recovery failure, and air quality into two comparable indices — current and mid-century. Each temperature indicator is normalized min-max across both time periods combined. Hot nights use VCP's relative definition (% of nights exceeding the 98th percentile of each tract's own historical minimum temperature), which accounts for local acclimatization. AQI is held at historic CalEnviroScreen values for both indices, as tract-level air quality cannot be reliably projected. All three components carry equal weight, giving temperature 2/3 collective weight and AQI 1/3.

| Variable | Description | Source |
| :--- | :--- | :--- |
| `days_over_90_historic` | Near-historic annual number of days over 90°F per census tract. | Cal-Adapt, 2025 |
| `days_over_90_midcentury` | Projected annual number of days over 90°F per census tract by mid-century (2041–2070). | Cal-Adapt, 2025 |
| `delta_90` | Change in annual days over 90°F between mid-century and historic. | Cal-Adapt, 2025 |
| `hotnights_pre_pct` | % of nights exceeding the 98th percentile of each tract's historical minimum temperature, current timescale (2015–2044). | LCI VCP, 2025, derived from LOCA 2 CA Hybrid (SSP 370, 2023) |
| `hotnights_fut_pct` | % of nights exceeding the 98th percentile of each tract's historical minimum temperature, mid-century timescale (2045–2074). | LCI VCP, 2025, derived from LOCA 2 CA Hybrid (SSP 370, 2023) |
| `PollutionP` | Normalized pollution exposure (0–100) per census tract; includes all pollution types. | CalEnviroScreen 5.0, 2025 |
| `AQI_norm` | Normalized AQI exposure (0–100) per census tract. Calculated from Ozone, PM2.5, and Diesel exposure percentiles. | CalEnviroScreen 5.0, 2025 |
| `heat_hazard_idx_norm` | Normalized Heat and Air Quality Hazard Index (0–100), current. Equal-weight mean of normalized historic days over 90°F, current hot nights frequency, and AQI. | Derived from Cal-Adapt, 2025; LCI VCP, 2025; CalEnviroScreen 5.0, 2025 |
| `heat_hazard_fut_idx_norm` | Normalized Heat and Air Quality Hazard Index (0–100), mid-century (2041–2070). Equal-weight mean of normalized mid-century days over 90°F, mid-century hot nights frequency, and AQI (held at historic levels). | Derived from Cal-Adapt, 2025; LCI VCP, 2025; CalEnviroScreen 5.0, 2025 |

### Flood Risk

The flood hazard index follows the methodology of the Governor's Office of Land Use and Climate Innovation (LCI) Vulnerable Communities Platform (VCP). VCP's composite flood score for census tracts with high group-quarters populations (including state prisons) is excluded from their index, but the underlying raw indicators are available for all tracts and are used directly here.

The index combines two components:
- **BAM floodplain exposure** (full weight): % of tract within the DWR Best Available Maps floodplain.
- **Very wet days** (half weight): % of years classified as very wet from LOCA 2 CA Hybrid precipitation projections. Normalized min-max across both time periods combined before applying the 0.5 weight reduction.

Current hazard uses the 100-year floodplain and historic very wet day frequency; mid-century hazard uses the 500-year floodplain and projected very wet day frequency (2045–2074). Both are normalized to 0–100 after combining.

| Variable | Description | Source |
| :--- | :--- | :--- |
| `flood_bam_100_pct` | % of census tract area within the DWR BAM 100-year floodplain (current). | LCI VCP, derived from DWR Best Available Maps |
| `flood_bam_500_pct` | % of census tract area within the DWR BAM 500-year floodplain (future/2050 proxy). | LCI VCP, derived from DWR Best Available Maps |
| `flood_verywet_pre_pct` | % of years classified as very wet under historic conditions per census tract. | LCI VCP, derived from LOCA 2 CA Hybrid (SSP 370, 2023) |
| `flood_verywet_fut_pct` | % of years classified as very wet under mid-century conditions (2045–2074) per census tract. | LCI VCP, derived from LOCA 2 CA Hybrid (SSP 370, 2023) |
| `flood_hazard_idx_norm` | Normalized Flood Hazard Index (0–100), current. Calculated from 100-year BAM floodplain exposure (full weight) and historic very wet day frequency (half weight), following VCP methodology. | Derived from LCI VCP, 2025 |
| `flood_hazard_fut_idx_norm` | Normalized Flood Hazard Index (0–100), mid-century. Calculated from 500-year BAM floodplain exposure (full weight) and projected very wet day frequency (half weight), following VCP methodology. | Derived from LCI VCP, 2025 |

### Wildfire Risk

Fire Hazard Severity Zone (FHSZ) classifications from CalFire, assigned to each facility via a point-in-polygon join against two responsibility layers:

- **SRA (State Responsibility Area):** Areas where the state has primary responsibility for fire protection. 2022 FHSZ boundaries.
- **LRA (Local Responsibility Area):** Areas where local agencies (cities, counties) have primary fire protection responsibility. 2025 FHSZ boundaries.

Facilities not within any classified zone are unclassified (considered lowest risk). The two layers are mutually exclusive — a facility falls in either SRA or LRA jurisdiction.

| Variable | Description | Source |
| :--- | :--- | :--- |
| `fhsz` | Fire Hazard Severity Zone classification: `Very High`, `High`, `Moderate`, or blank if the facility is not within a classified zone. | CalFire FHSZ, SRA 2022 / LRA 2025 |
| `fhsz_responsibility` | Responsibility area type: `SRA` (State) or `LRA` (Local). Blank if the facility is not within a classified zone. | CalFire FHSZ, SRA 2022 / LRA 2025 |
| `wui_type` | Wildland-Urban Interface classification: `Intermix` (homes interspersed within wildland vegetation), `Interface` (homes adjacent to wildland), or `Influence Zone` (within ~1.5 miles of Interface/Intermix areas). Blank if outside all WUI boundaries. | CalFire Wildland-Urban Interface shapefile |

### Drought Risk

The drought hazard index follows VCP's three-indicator methodology. VCP's composite drought score excludes all-group-quarters census tracts (including state prisons), but the underlying raw indicators are available for all tracts and are used directly.

The index combines three equal-weight components:
- **June–August temperature change** (°C above baseline): captures temperature-driven evapotranspiration demand, a primary driver of drought in the western US. Normalized min-max across both time periods combined.
- **Water Shortage Vulnerability (WSV)**: DWR physical risk score reflecting overdrafted basins, dry well susceptibility, and declining groundwater levels. Same value used in both timescales.
- **Precipitation/demand ratio**: ratio of 30-year average precipitation to population and cultivated land per watershed. Higher values indicate lower water stress, so this component is inverted before combining. Same value used in both timescales.

The SPEI-12 delta is included as a standalone variable. SPEI accounts for both precipitation deficit and evapotranspiration together, but a meaningful historic equivalent cannot be derived — the historic baseline is ~5% by construction of the 5th-percentile threshold — so it is not included in the composite. The SPEI data uses SSP 2-4.5 (moderate emissions), methods determined by climatologists in California's Fifth Climate Assessment (2026, forthcoming).

| Variable | Description | Source |
| :--- | :--- | :--- |
| `Dr_delta_JA_max_pre` | Change in June–August mean maximum temperature (°C) above baseline, current timescale (2015–2044). | LCI VCP, 2025, derived from LOCA 2 CA Hybrid (SSP 370, 2023) |
| `Dr_delta_JA_max_fut` | Change in June–August mean maximum temperature (°C) above baseline, mid-century timescale (2045–2074). | LCI VCP, 2025, derived from LOCA 2 CA Hybrid (SSP 370, 2023) |
| `Dr_WSV_average` | Water Shortage Vulnerability physical risk score per census tract (0–100). | LCI VCP, 2025, derived from DWR Water Shortage Vulnerability Tool (updated 2024) |
| `Dr_precip_demand_ratio` | Ratio of 30-year average total precipitation to population and cultivated land per watershed. Higher values indicate less water stress. Inverted when computing the drought index. | LCI VCP, 2025, derived from PRISM 30-year normals (1991–2020) and DWR Statewide Crop Mapping |
| `drought_delta_spei12_midcentury` | % change in SPEI-12 drought frequency from the historic baseline (~5%) to mid-century (2041–2070). SPEI-12 is a 12-month drought index accounting for both precipitation deficit and evapotranspiration. | Cal-Adapt, derived from LOCA2 CA Hybrid (SSP 245) |
| `drought_hazard_idx_norm` | Normalized Drought Hazard Index (0–100), current. Equal-weight mean of normalized June–August temperature change (current), WSV, and inverted precipitation/demand ratio. | Derived from LCI VCP, 2025 |
| `drought_hazard_fut_idx_norm` | Normalized Drought Hazard Index (0–100), mid-century (2041–2070). Equal-weight mean of normalized June–August temperature change (mid-century), WSV, and inverted precipitation/demand ratio. | Derived from LCI VCP, 2025 |

# Impact Analysis

See [`analysis/README.md`](analysis/README.md) for the full impact analysis documentation, including heat activation days, summary graphs, and population impact methodology.

# References

## Facilities

FEMA. (2025). Prison Boundaries RAPT. [Dataset]. https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/Prison_Boundaries_RAPT/FeatureServer

- The FEMA prison data set was "downloaded from HiFLD Open on July 22, 2025"

USGS National Map Structures. (2026). Medical & Emergency Response facilities [Dataset]. U.S. Geological Survey. https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer

U.S. Census Bureau. (2020). Urban Area cartographic boundary file (cb_2020_us_ua20_500k) [Dataset]. https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_ua20_500k.zip

See [`data_sources/facilities/CDCR/README.md`](data_sources/facilities/CDCR/README.md) for CDCR-specific references.

## Climate Hazards

Governor’s Office of Land Use and Climate Innovation. (2025). Vulnerable Communities Platform [Dataset]. https://opr.ca.gov/planning/vulnerable-communities-platform/

Vulnerable Communities Platform Methods Report. (2025). Governor’s Office of Land Use and Climate Innovation. https://docs.google.com/viewerng/viewer?url=https://gov-opr.maps.arcgis.com/sharing/rest/content/items/ff3579e26cf643e082344b91d3f591d2/data

Department of Water Resources. (2008, updated periodically). Best Available Maps (BAM) Floodplains [Dataset]. California Department of Water Resources.


CalEnviroScreen 5.0. (2026). [Dataset]. California Office of Environmental Health Hazard Assessment. https://data.ca.gov/dataset/draft-calenviroscreen-5-0

Cal-Adapt. (Forthcoming). [Dataset]. Climate datasets prepared for California's Fifth Climate Change Assessment.

Department of Water Resources. (2024). Water Shortage Vulnerability Tool [Dataset]. California Department of Water Resources.

CalFire. (2022, 2025). Fire Hazard Severity Zones [Dataset]. California Department of Forestry and Fire Protection. https://osfm.fire.ca.gov/divisions/community-wildfire-preparedness-and-mitigation/wildland-hazard-and-building-codes/fire-hazard-severity-zones-maps/

CalFire. Wildland-Urban Interface [Dataset]. California Department of Forestry and Fire Protection. https://www.fire.ca.gov/what-we-do/fire-resource-assessment-program/wildland-urban-interface

Benz SA, Burney JA. (2021). Widespread race and class disparities in surface urban heat islands across the United States. *Earth's Future*, 9(7), e2021EF002016. Data: Harvard Dataverse, doi:10.7910/DVN/1F72FB. CC0 license.
