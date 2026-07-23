# Heat Hazard — LOCA2-CA Daily Extraction

Facility-level heat metrics for all 357 California correctional facilities, computed from
LOCA2-CA daily `tasmax` and `tasmin`. This replaces the tract-level joins that previously
supplied daytime heat from `heatdays_alltimes_tract.csv`.

Extraction script: `scrapers/extract_loca2_heat.py`. Observed-temperature counterparts, on
gridMET rather than model data, are documented in `../README.md`.

## Source

LOCA2-CA is the 3 km statistical downscaling of CMIP6 produced at Scripps (Pierce, Cayan and
Dehann) and distributed through Cal-Adapt: Analytics Engine. Data is read from the S3 zarr
store rather than downloaded:

```python
intake.open_esm_datastore('https://cadcat.s3.amazonaws.com/cae-collection.json')
# s3://cadcat/loca2/ucsd/<model>/<experiment>/<member>/day/<var>/d03/
```

Grid `d03` is 1/32° (about 3 km), 495 × 559 cells covering 29.58–45.02 N and 128.42–110.98 W.
Access is anonymous and supports lazy point selection, so only the chunks containing facility
cells are read.

The pre-reduced `LOCA2CA.*.annual_count.nc` files in the recj-fifth-assessment repository cannot
substitute for this. They hold 30-year mean annual counts over fixed absolute thresholds, so no
daily distribution survives in them and no relative or percentile threshold can be recovered.

## Ensemble

Fourteen models, 62 members, identical in every period.

| Model | Members | Model | Members |
| :--- | ---: | :--- | ---: |
| CESM2-LENS | 10 | ACCESS-CM2 | 3 |
| IPSL-CM6A-LR | 10 | KACE-1-0-G | 3 |
| MPI-ESM1-2-HR | 10 | MIROC6 | 3 |
| INM-CM5-0 | 5 | EC-Earth3 | 2 |
| MRI-ESM2-0 | 5 | CNRM-ESM2-1 | 1 |
| EC-Earth3-Veg | 4 | GFDL-ESM4 | 1 |
| FGOALS-g3 | 4 | TaiESM1 | 1 |

**Weighting.** Thresholds and counts are computed per member. Members are then averaged within
each model, and the 14 model means are averaged with equal weight. Every model therefore carries
1/14 of the result regardless of how many runs it contributed.

The alternative, averaging all member files directly, would give CESM2-LENS, IPSL-CM6A-LR and
MPI-ESM1-2-HR 30 of 62 runs between them. Member counts in the CMIP6 archive reflect the
computing budgets of the centers that produced them, and additional runs of one model sample that
model's internal variability rather than adding an independent estimate of the forced response
(Knutti 2010; Knutti et al. 2010; Lehner et al. 2020). Averaging within model first is the
standard correction, and the IPCC AR6 Interactive Atlas applies the same principle by taking one
member per model (Iturbide et al. 2021).

Averaging all of a model's members is preferred here over selecting `r1i1p1f1` alone. A single
realization is a noisy estimate of its own model's forced response. Seasonal means settle after
five to ten members, but threshold-exceedance frequency at grid-cell scale often needs 15 to 25
before the forced response separates from the noise (Maher et al. 2019; Milinski et al. 2020).
Measured at the CDCR cells, `r1i1p1f1` sits between 3.4 days below and 3.0 days above its own
model's mean for days over 90 °F, reaching 5.4 days at individual facilities. That is roughly
five times the difference between the weighting schemes themselves.

**Fixed composition.** A member is included only if it exists in both `historical` and `ssp370`,
and HadGEM3-GC31-LL is excluded from every period because Cal-Adapt carries no `ssp370` for it.
The published Cal-Adapt product averages 15 models historically and 14 at mid-century, which is
consistent for a per-period climatology. The index here differences the periods, and a change in
which models are averaged would otherwise enter the delta as though it were climate (Tebaldi and
Knutti 2007; Christensen et al. 2019).

## Periods

| Name | Experiment | Years |
| :--- | :--- | :--- |
| `historic` | historical | 1981–2010 |
| `midcentury` | ssp370 | 2041–2070 |
| `endcentury` | ssp370 | 2071–2100 |

All three appear in this data product. The heat risk index uses `historic` and `midcentury` only,
because flood and drought have no end-century data and a third period would leave the
multi-hazard comparison with nothing to compare against.

## Reproduction Against the Published Product

Before any of the relative thresholds were built, the extraction was checked by reproducing
`annualavgcount_gt_{80,90,100,110}_tasmax` from the Cal-Adapt `.nc` files at the facility cells,
using Ullrich's own weighting of all 70 historical member runs. Agreement at the 33 valid CDCR
cells:

| Threshold | max abs. difference | MAE |
| :--- | ---: | ---: |
| `gt_80` | 0.088 | 0.013 |
| `gt_90` | 0.005 | 0.0005 |
| `gt_100` | 0.000 | 0.000 |
| `gt_110` | 0.000 | 0.000 |

The two highest thresholds agree exactly at float32 precision. The residual at `gt_80` scales
with the size of the count (r = 0.64) and peaks at 0.036% of the value at the hottest desert
cells, which is consistent with float32 accumulation inside `ncea` rather than a difference in
method. The zarr store and the published files share all 495 latitudes and 559 longitudes
exactly, so no regridding enters the comparison.

The published metric was built with
[TempestExtremes](https://github.com/ClimateGlobalChange/tempestextremes). Matching it on all
four thresholds is what licenses the claim that this pipeline uses the same definition: calendar
handling, Kelvin-to-Fahrenheit conversion, the comparison convention, the 30-year annual-count
definition and ensemble pooling all agree.

## Spatial Assignment

Each facility takes the single cell that contains it. We apply no neighborhood averaging and no
interpolation. Spatial averaging is a low-pass filter and damps the daily peaks these metrics
count; bilinear interpolation alters the tails of the daily distribution that statistical
downscaling exists to produce (Maraun 2013; Maraun and Widmann 2018; IPCC AR6 WGI Ch. 11 §11.2.1,
on areal reduction).

Averaging over a 5 × 5 neighborhood costs HDSP 45% of its days over 90 °F. That facility sits on
a valley floor at 1267 m ringed by higher terrain, so the neighborhood pulls in cold cells nobody
at the facility experiences.

Ovienmhada et al. (2024) is the nearest comparison in the prison-heat literature. They compute
facility-level metrics from a 1 km Daymet grid over HIFLD polygon boundaries, but do not state
in the main text whether a facility value is a zonal mean over the polygon or a sampled cell, so
they are not a precedent for the choice made here either way. Their limitations section argues
that gridded-temperature error should not much affect the relative ranking of the most exposed
facilities, since the metrics are time-averaged. The same reasoning applies here, where the
output feeds a ranked index rather than an absolute-temperature claim.

A `d03` cell covers about 9.6 km² against a prison compound of roughly 1–3 km². The cell is
already broader than the facility, so "point extraction" is a misnomer, and the reported value
carries representativeness error wherever local terrain or land cover differs from the cell as a
whole. Cell selection is recorded per facility in `cell_lat`, `cell_lon`, `cell_dist_km` and
`mask_override`.

357 facilities resolve to 274 distinct cells; 83 share a cell with another facility, and one cell
near Corcoran holds six.

**San Quentin** is the only facility whose containing cell is masked, and the only manual
override. It sits on water in the LOCA2 land mask. Nearest-by-distance selects 37.9219,
−122.4844, 2.08 km SSE, which lies across Richardson Bay and open to the Golden Gate. The cell
used instead is 37.9531, −122.5156, 2.65 km WNW, on contiguous land and sheltered as the facility
is. Mean tmax differs by 3.1 °F between them. The `tasmin` mask was checked separately and is
identical to the `tasmax` mask.

Two failure modes abort the run rather than being reported afterwards. NaN silently fails a
`> threshold` comparison and yields a count of 0 instead of an error, so any NaN cell raises; and
every period must return exactly 30 years. Distances are computed as `dlat × 111` and
`dlon × 111 × cos(lat)`, since at latitude 38 raw degrees overweight longitude by about 25% and
select the wrong nearest cell.

## Columns

Every facility carries the identical column set. Period suffix is one of `historic`,
`midcentury`, `endcentury`.

| Group | Columns |
| :--- | :--- |
| Absolute tmax | `loca2_days_over_{80,90,100,110}_{period}` |
| Absolute tmin | `loca2_nights_over_{60,70,80,90}_{period}` |
| Relative tmax | `loca2_days_over_avg_{period}`, `loca2_days_over_avg_plus10_{period}`, `loca2_avg_summer_tmax_f` |
| Relative tmin | `loca2_nights_over_avg_{period}`, `loca2_nights_over_avg_plus10_{period}`, `loca2_avg_summer_tmin_f`, `loca2_nights_over_p98_{period}`, `loca2_p98_tmin_f` |
| Provenance | `cell_lat`, `cell_lon`, `cell_dist_km`, `n_models`, `mask_override` |

Absolute thresholds match the published Cal-Adapt variables, so the reproduction check above
covers all four. Relative thresholds are anchored to each member's own 1981–2010 value, held
fixed and applied to every period. A baseline that moved with the climate would cancel the shift
these counts exist to measure.

`days_over_avg` counts the whole year against a summer-mean threshold, so in the historical
period it lands near half of summer by construction plus the shoulder-season days that also
clear it: 71 days a year at the median facility, 77 on average, ranging 60 to 131. The
information is in how far mid- and end-century rise above that, not in the level itself. Across
357 facilities the historical-to-mid-century increase averages +38.5 days.

The `plus10` rung follows Skarha et al. (2023), whose facility-relative anomaly carries a
published mortality coefficient. Ovienmhada et al. (2024) apply the same threshold as one of
four facility-level heat metrics across 1,614 US prisons, which is the closest published
precedent for computing it per facility rather than per tract. Summer means use June–August. `p98_tmin_f` is the 98th
percentile of the full-year historical `tasmin` distribution, not summer only.

Naming follows the convention in `../README.md`: a source prefix on every column, and the
baseline window named wherever a threshold is relative. LOCA2 relative thresholds are anchored to
1981–2010 and carry the period suffix; the gridMET observed columns are anchored to 1991–2020 and
carry `base1991_2020`. The two are not interchangeable.

## Mixed Basis With Other Hazards

Heat is facility-level for all 357 facilities. Flood and drought remain tract-level joins, so the
multi-hazard tables combine hazards resolved at different spatial units.

## References

Christensen, O. B., et al. (2019). Consistency of climate change signals across CMIP and CORDEX
ensembles. *Climate Dynamics*, 53, 6299–6312. doi:10.1007/s00382-019-04933-y

Iturbide, M., et al. (2021). Repository supporting the implementation of FAIR principles in the
IPCC-WGI Interactive Atlas. *Zenodo*. doi:10.5281/zenodo.3691645

IPCC (2021). *Climate Change 2021: The Physical Science Basis*, WGI Chapter 11, Weather and
Climate Extreme Events in a Changing Climate. Cambridge University Press.

Knutti, R. (2010). The end of model democracy? *Climatic Change*, 102(3–4), 395–404.
doi:10.1007/s10584-010-9800-2

Knutti, R., Furrer, R., Tebaldi, C., Cermak, J., & Meehl, G. A. (2010). Challenges in combining
projections from multiple climate models. *Journal of Climate*, 23(10), 2739–2758.
doi:10.1175/2009JCLI3361.1

Lehner, F., Deser, C., Maher, N., Marotzke, J., Fischer, E. M., Brunner, L., Knutti, R., &
Hawkins, E. (2020). Partitioning climate projection uncertainty with multiple large ensembles and
CMIP5/6. *Earth System Dynamics*, 11(2), 491–508. doi:10.5194/esd-11-491-2020

Maher, N., Milinski, S., & Ludwig, R. (2019). Large ensembles and their role in estimating
internal climate variability and the response to anthropogenic forcing. *Environmental Research
Letters*, 14(10), 103001. doi:10.1088/1748-9326/ab3570

Maraun, D. (2013). Bias correction, downscaling, and stochastic weather generators from the
climate service perspective. *Frontiers in Environmental Science*, 1, 4.
doi:10.3389/fenvs.2013.00004

Maraun, D., & Widmann, M. (2018). *Statistical Downscaling and Bias Correction for Climate
Research*. Cambridge University Press.

Ovienmhada, U., Hines, M., Krisch, M., Diongue, A. T., Minchew, B., & Wood, D. R. (2024).
Spatiotemporal facility-level patterns of summer heat exposure, vulnerability, and risk in
United States prison landscapes. *GeoHealth*, 8(9), e2024GH001108. doi:10.1029/2024GH001108

Milinski, S., Maher, N., & Olonscheck, D. (2020). How large does a large ensemble need to be?
*Earth System Dynamics*, 11(4), 885–901. doi:10.5194/esd-11-885-2020

Skarha, J., Jackson, A., Zlotnik, H., Williams, B., & Wildeman, C. (2023). Heat and mortality in
US state prisons. *PLOS ONE*.

Tebaldi, C., & Knutti, R. (2007). The use of the multi-model ensemble in probabilistic climate
projections. *Philosophical Transactions of the Royal Society A*, 365(1857), 2053–2075.
doi:10.1098/rsta.2007.2076
