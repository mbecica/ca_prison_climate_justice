#!/usr/bin/env python3
"""One-time cross-check of the Heat Tracker ERA5 baselines against the existing
CDCR-only `skarha10` gridMET work.

Both are 1991–2020 mean Jun–Aug daily-max temperatures, but from different
datasets: this repo's gridMET extraction (scrapers/extract_gridmet_heat.py,
annual means in data_sources/hazards/heat/summer_avg_tmax_annual.csv) versus
the Open-Meteo ERA5 pull (analysis/heatwave_app/build_baselines.py). A large
systematic offset would bias threshold crossings — see SCOPE_AND_PLAN §2.

    python3 analysis/heatwave_app/validate_baselines.py

Writes analysis/heatwave_app/data/baseline_validation_skarha.csv and prints a
comparison table.
"""
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

annual = pd.read_csv(REPO / "data_sources/hazards/heat/summer_avg_tmax_annual.csv")
cdcr = pd.read_csv(REPO / "data/cdcr/cdcr_facilities.csv")
era5 = pd.read_csv(HERE / "data/baselines.csv")

gridmet = (annual[annual.year.between(1991, 2020)]
           .groupby("cdcr_code")["avg_summer_tmax_f"].agg(["mean", "count"])
           .rename(columns={"mean": "gridmet_baseline_f", "count": "n_years"}))

prisons = cdcr[cdcr.cdcr_code.notna()][["cdcr_code", "facilityid", "name"]]
cmp = (prisons.merge(gridmet, on="cdcr_code")
       .merge(era5[["facilityid", "baseline_summer_avg_tmax_f", "grid_elevation_m"]],
              on="facilityid", how="left")
       .rename(columns={"baseline_summer_avg_tmax_f": "era5_baseline_f"}))
cmp["diff_f"] = (cmp.era5_baseline_f - cmp.gridmet_baseline_f).round(2)
cmp["gridmet_baseline_f"] = cmp.gridmet_baseline_f.round(2)
cmp = cmp.sort_values("diff_f")

out = HERE / "data/baseline_validation_skarha.csv"
cmp.to_csv(out, index=False)

done = cmp.era5_baseline_f.notna()
print(f"Compared {done.sum()} of {len(cmp)} CDCR facilities "
      f"(missing ERA5: {', '.join(cmp[~done].cdcr_code)})" if (~done).any() else
      f"Compared all {len(cmp)} CDCR facilities")
d = cmp.loc[done, "diff_f"]
print(f"\nERA5 minus gridMET (°F): mean {d.mean():+.2f}, median {d.median():+.2f}, "
      f"sd {d.std():.2f}, range [{d.min():+.2f}, {d.max():+.2f}]")
print(f"|diff| <= 2°F: {(d.abs() <= 2).sum()}/{len(d)}   "
      f"|diff| <= 5°F: {(d.abs() <= 5).sum()}/{len(d)}")
print("\nLargest discrepancies:")
cols = ["cdcr_code", "name", "gridmet_baseline_f", "era5_baseline_f", "diff_f", "grid_elevation_m"]
print(pd.concat([cmp[done].head(5), cmp[done].tail(5)])[cols].to_string(index=False))
print(f"\nWrote {out.relative_to(REPO)}")
