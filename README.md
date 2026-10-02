# California Prison Climate Justice

Climate hazard data for California's 357 carceral facilities: local and county jails, state prisons, and federal prisons. Each facility is joined to published climate and hazard datasets, including LOCA2-CA downscaled projections from California's Fifth Climate Change Assessment, the Vulnerable Communities Platform, CalEnviroScreen, CalFire hazard maps, and Benz & Burney's (2021) surface urban heat island data. As of March 2026 there were 357 facilities, 84 of them under state jurisdiction.

This project supports the Climate Justice Coalition for California Prisons and a master's capstone at UC Berkeley's Department of City & Regional Planning. It builds on the [Toxic Prisons Project](http://toxicprisons.com/) and the Ella Baker Center's [Hidden Hazards](https://ellabakercenter.org/reports/hiddenhazards/) report (2023).

Related repositories:

- [cdcr_facility_data](https://github.com/mbecica/cdcr_facility_data): population, health care, cooling, staffing, and other data for CDCR state prisons.
- [cdcr_prison_heat_index](https://github.com/mbecica/cdcr_prison_heat_index): the heat risk index for CDCR prisons, built from this repository's hazard data and cdcr_facility_data.

## Datasets

| File | Contents | Built by |
| :--- | :--- | :--- |
| `data/allfacilities_climate_hazards.csv` | All 357 facilities with every hazard field below | `analysis/hazards/join_climate_hazards.ipynb` |
| `data_sources/facilities/ca_facilities.csv` | Facility list with location, isolation, and urban heat island fields | `data_sources/facilities/create_facilities.ipynb` |
| `data/hazards/heat_air_hazard.csv` | Facility-level heat and air quality indicators and index | `data_sources/hazards/heat/heat_hazard.ipynb` |
| `data/hazards/flood_hazard.csv` | Tract-level flood indicators | `data_sources/hazards/flood/flood_hazard.ipynb` |
| `data/hazards/drought_hazard.csv` | Tract-level drought indicators | `data_sources/hazards/drought/drought_hazard.ipynb` |
| `data_sources/hazards/heat/loca2_facility_heat.csv` | Full LOCA2-CA heat extraction: absolute and relative thresholds, three periods | `data_sources/hazards/heat/extraction/extract_loca2_heat.py` |
| `data_sources/facilities/facility_elevation.csv` | Ground elevation at each facility | `scrapers/fetch_facility_elevation.py` |

## Facility fields

Every facility has its name, address, telephone, and website from the FEMA facility layer, plus:

| Variable | Description | Source |
| :--- | :--- | :--- |
| `facilityid` | Facility ID. | FEMA, 2025 |
| `type` | Jurisdiction: `LOCAL` (54), `COUNTY` (188), `MULTI` (3), `STATE` (84), `FEDERAL` (28). Five facilities were retyped after manual review. | FEMA, 2025 |
| `population` | Population. Only 68 facilities have a value, and the year is not stated. | FEMA, 2025 |
| `capacity_percent` | `population` / `capacity`, as a 0–1 value. | Derived from FEMA, 2025 |
| `latitude`, `longitude` | Centroid of the facility boundary. | Derived from FEMA, 2025 |
| `tract_geoid` | 11-digit census tract GEOID containing the centroid. | U.S. Census Bureau, 2020 tracts |
| `dist_nearest_medical_mi` | Great-circle distance in miles from the centroid to the nearest hospital, ambulance service, or fire/EMS station in California. | USGS National Map Structures (layers 14–16), April 2026 |
| `in_urban_area_2020` | True if the centroid falls within a 2020 Census Urban Area. | U.S. Census Bureau, cb_2020_us_ua20_500k |
| `benz_uhi_dt` | Summer daytime surface urban heat island anomaly (°C) for the facility's census tract. Blank for 82 facilities in tracts classified as undeveloped. | Benz & Burney (2021) |
| `benz_uhi_source` | `direct` for a tract match; `buffer` or `buffer_cdcr_corroborated` for eight state prisons assigned the nearest developed tract. | Benz & Burney (2021) |

## Hazard fields

`allfacilities_climate_hazards.csv` carries the facility fields above, with the UHI fields named `heat_uhi_dt` and `heat_uhi_source`, and the following. Historic is 1981–2010 for the LOCA2-CA heat fields; see each source for other windows. Mid-century is 2041–2070 unless noted.

### Heat and air quality

| Variable | Description | Source |
| :--- | :--- | :--- |
| `heat_days_over_avg_plus10_historic`, `_midcentury` | Annual days above the facility's mean summer daily maximum plus 10°F (1981–2010 baseline). | LOCA2-CA daily (SSP3-7.0), Cal-Adapt |
| `heat_days_over_90_historic`, `_midcentury` | Annual days above 90°F. | LOCA2-CA daily (SSP3-7.0), Cal-Adapt |
| `heat_nights_over_p95_historic`, `_midcentury` | Annual April–October nights above the 95th percentile of the facility's 1961–1990 April–October minimum temperatures. | LOCA2-CA daily (SSP3-7.0), Cal-Adapt |
| `heat_avg_summer_tmax_f`, `heat_p95_tmin_f` | The facility's hot-day and warm-night baselines (°F). | LOCA2-CA daily, Cal-Adapt |
| `heat_aqi_pctile` | Air quality percentile (0–100) for the census tract, from the ozone, PM2.5, and diesel indicators. | CalEnviroScreen 5.0, 2025 |
| `heat_hazard_historic_idx`, `heat_hazard_midcentury_idx` | Heat and Air Quality Hazard Index (0–100). Hot days (an equal blend of the relative and 90°F counts) and warm nights, each scaled to their maximum and averaged, then multiplied by `1 + 0.30 × AQI/100`. Normalized across all 357 facilities; air quality is held at current values for both periods. | Derived from LOCA2-CA and CalEnviroScreen 5.0 |

### Flood

| Variable | Description | Source |
| :--- | :--- | :--- |
| `flood_bam_100_pct` | % of the census tract within the DWR 100-year floodplain. | VCP, from DWR Best Available Maps |
| `flood_bam_500_pct` | % of the census tract within the DWR 500-year floodplain. | VCP, from DWR Best Available Maps |
| `flood_verywet_pct_historic`, `_midcentury` | Share of annual precipitation falling on very wet days; mid-century is 2045–2074. | VCP, from LOCA2-CA Hybrid (SSP3-7.0) |

### Drought

| Variable | Description | Source |
| :--- | :--- | :--- |
| `drought_delta_temp_ja_historic` | Change in June–August mean maximum temperature (°C), 2015–2044. | VCP, from LOCA2-CA Hybrid (SSP3-7.0) |
| `drought_delta_temp_ja_midcentury` | Change in June–August mean maximum temperature (°C), 2045–2074. | VCP, from LOCA2-CA Hybrid (SSP3-7.0) |
| `drought_water_shortage_vulnerability` | DWR Water Shortage Vulnerability score. | VCP, from DWR Water Shortage Vulnerability Tool (2024) |
| `drought_precip_demand_ratio` | 30-year average precipitation relative to demand from population and cultivated land. | VCP, from PRISM 1991–2020 and DWR Crop Mapping |
| `drought_delta_spei12_midcentury` | Change in SPEI-12 drought frequency from the historic baseline (about 5%) to 2041–2070. | Cal-Adapt, from LOCA2-CA Hybrid (SSP2-4.5) |

### Wildfire

| Variable | Description | Source |
| :--- | :--- | :--- |
| `fire_fhsz` | Fire Hazard Severity Zone: `Very High`, `High`, `Moderate`, or blank if unclassified. | CalFire FHSZ, SRA 2022 / LRA 2025 |
| `fire_fhsz_responsibility` | `SRA` (state) or `LRA` (local) responsibility area; blank if unclassified. | CalFire FHSZ, SRA 2022 / LRA 2025 |
| `fire_wui_type` | Wildland-Urban Interface class: `Intermix`, `Interface`, or `Influence Zone`; blank if outside. | CalFire Wildland-Urban Interface |

## Methods

### Spatial units

Heat is resolved per facility: each facility takes the LOCA2-CA grid cell containing its centroid. Flood and drought are Vulnerable Communities Platform (VCP) census tract indicators joined through `tract_geoid`; the VCP publishes them for every tract, including tracts with large group-quarters populations such as state prisons. Wildfire classes are assigned by point-in-polygon join.

### Heat and air quality index

Temperature indicators come from a facility-level extraction of LOCA2-CA daily maximum and minimum temperatures: 14 models and 62 members under SSP3-7.0, with each model weighted equally. Thresholds and counts are computed per ensemble member before averaging. Historic is 1981–2010 and mid-century is 2041–2070. The extraction, ensemble, cell assignment, and validation against Cal-Adapt's published counts are documented in [`data_sources/hazards/heat/README.md`](data_sources/hazards/heat/README.md).

- **Hot days:** an equal blend of days above the facility's mean summer daily maximum plus 10°F (1981–2010 baseline) and days above 90°F. Each count is divided by its maximum across facilities and both periods before blending.
- **Warm nights:** April–October nights above the 95th percentile of the facility's 1961–1990 April–October minimum temperatures, the convention OEHHA uses.

The two terms are averaged and multiplied by `1 + 0.30 × AQI/100`, then divided by the maximum across facilities and both periods and scaled to 0–100. A facility with no exceedances scores 0. AQI is the mean of the CalEnviroScreen ozone, PM2.5, and diesel percentiles, rescaled across tracts, and is held at current values in both periods because no tract-level projection exists. The 0.30 coefficient and the 50% blend weight are design parameters.

### Flood and drought

The VCP uses the 500-year floodplain as its mid-century floodplain measure, on the expectation that events rare today become more frequent. Water Shortage Vulnerability and the precipitation/demand ratio have one value for both periods. SPEI-12 measures drought from both precipitation deficit and evapotranspiration; it has no meaningful historic value, because the historic frequency is about 5% by construction of the 5th-percentile threshold, and Cal-Adapt publishes it under SSP2-4.5.

### Urban heat island

Each facility takes the Benz & Burney (2021) ΔT of the tract containing its centroid: local MODIS land surface temperature (2010–2014, 95th-percentile summer daytime) minus the median rural background, published for tracts NLCD classifies as developed. 267 facilities match directly and 82 have no value, mostly rural fire camps and remote county jails.

Ten state prisons sit in undeveloped tracts even though the facilities are built up. Eight were assigned the nearest developed tract by polygon-edge distance (EPSG:3310): COR, SATF, CIM, WSP, RJD, CVSP, and ISP within 1 mile, and CIW at 1.04 miles, supported by CDCR's 2020 Sustainability Roadmap (Table 8), which ranks CIW third for urban heat island intensity. CCI (4.4 miles) and PVSP (2.2 miles) are blank. The assignments are recorded in `data_sources/hazards/heat/benz_uhi_facilities.csv`.

## Updating the data

Source layers are downloaded by hand; most change only when the publishing agency releases a new version. After updating any source, rerun its builder, then `analysis/hazards/join_climate_hazards.ipynb`.

| Data | Source | Run |
| :--- | :--- | :--- |
| Facility list | Download the FEMA Prison Boundaries layer to `data_sources/facilities/Prison_Boundaries_RAPT.geojson` | `create_facilities.ipynb` |
| Medical and emergency facilities | USGS National Map (automatic) | `python3 scrapers/fetch_national_map_medical.py`, then `create_facilities.ipynb` |
| Elevation | USGS Elevation Point Query Service (automatic, about 15 minutes) | `python3 scrapers/fetch_facility_elevation.py` |
| LOCA2-CA heat | Cal-Adapt cadcat store (automatic, about 6 hours) | `python3 data_sources/hazards/heat/extraction/extract_loca2_heat.py`, then `heat_hazard.ipynb`. Only needed if new facilities are added or LOCA2-CA is republished. |
| Air quality | CalEnviroScreen release | `heat_hazard.ipynb` |
| Flood and drought | VCP release (`data_sources/hazards/VCP_Tracts.geojson`), Cal-Adapt SPEI | `flood_hazard.ipynb`, `drought_hazard.ipynb` |
| Wildfire | CalFire FHSZ and WUI releases | `join_climate_hazards.ipynb` |
| Urban heat island | Benz & Burney tract file (fixed dataset) | `create_facilities.ipynb` |

When the facility list changes, rebuild `ca_facilities.csv` first; the heat extraction, the join, and the downstream repositories all read it.

## License

Code is MIT and data is CC BY 4.0; see [LICENSE.md](LICENSE.md).

## References

### Facilities

FEMA. (2025). *Prison Boundaries RAPT* [Dataset]. Downloaded from HIFLD Open, July 22, 2025. https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/Prison_Boundaries_RAPT/FeatureServer

U.S. Geological Survey. (2026). *National Map Structures: Medical & Emergency Response facilities* [Dataset]. https://carto.nationalmap.gov/arcgis/rest/services/structures/MapServer

U.S. Geological Survey. (2026). *Elevation Point Query Service* [Web service]. https://epqs.nationalmap.gov/v1/json

U.S. Census Bureau. (2020). *Urban Area cartographic boundary file (cb_2020_us_ua20_500k)* [Dataset]. https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_ua20_500k.zip

### Climate hazards

Benz, S. A., & Burney, J. A. (2021). Widespread race and class disparities in surface urban heat islands across the United States. *Earth's Future*, 9(7), e2021EF002016. Data: Harvard Dataverse, doi:10.7910/DVN/1F72FB. CC0 license.

Cal-Adapt. (Forthcoming). Climate datasets prepared for California's Fifth Climate Change Assessment [Dataset].

California Department of Forestry and Fire Protection. (2022, 2025). *Fire Hazard Severity Zones* [Dataset]. https://osfm.fire.ca.gov/divisions/community-wildfire-preparedness-and-mitigation/wildland-hazard-and-building-codes/fire-hazard-severity-zones-maps/

California Department of Forestry and Fire Protection. *Wildland-Urban Interface* [Dataset]. https://www.fire.ca.gov/what-we-do/fire-resource-assessment-program/wildland-urban-interface

California Department of Water Resources. (2008, updated periodically). *Best Available Maps (BAM) Floodplains* [Dataset].

California Department of Water Resources. (2024). *Water Shortage Vulnerability Tool* [Dataset].

California Department of Corrections and Rehabilitation. (2020). *Sustainability Roadmap 2020–2021*.

California Office of Environmental Health Hazard Assessment. (2026). *CalEnviroScreen 5.0* [Dataset]. https://data.ca.gov/dataset/draft-calenviroscreen-5-0

Governor's Office of Land Use and Climate Innovation. (2025). *Vulnerable Communities Platform* [Dataset]. https://opr.ca.gov/planning/vulnerable-communities-platform/

Governor's Office of Land Use and Climate Innovation. (2025). *Vulnerable Communities Platform Methods Report*. https://docs.google.com/viewerng/viewer?url=https://gov-opr.maps.arcgis.com/sharing/rest/content/items/ff3579e26cf643e082344b91d3f591d2/data
