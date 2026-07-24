#!/usr/bin/env python3
"""
Wet-bulb / evaporative-cooling-capacity extraction for the indoor/outdoor heat analysis.

Per CDCR prison, warm season (May–Oct) 2025, from gridMET:
  - daily-max dry-bulb tmax   (reused from data_sources/hazards/heat/heat_activations_daily.csv;
                               grid-verified: reproduces days_outdoor_above_78f_2025 to 0 error)
  - daily-min relative humidity rmin (afternoon condition, coincident with tmax)
  - wet-bulb temperature via Stull (2011)                         twb_f
  - wet-bulb depression = evaporative cooling capacity, in °F     wbd_f = tmax − twb
  - evaporative supply-air temperature                            evap_supply = tmax − ε·wbd
  - days the cooler cannot reach 78°F / 85°F (counts over window) at ε = 0.70 / 0.80 / 0.85

Pairing rationale: an evaporative ("swamp") cooler's binding design condition is the hot, dry
part of the day → daily maximum temperature paired with daily minimum RH. Night (tmin+rmax) is
not the cooling-demand condition and is out of scope. ε (direct-evaporative effectiveness) spans
0.70–0.85; the wet-bulb depression itself is ε-independent, so the regression/clustering tests
that use wbd do not depend on ε — only the descriptive cannot-reach counts do.

Thresholds: 85°F = AB 2499 indoor reporting threshold; 78°F = the threshold the CDCR Air Cooling
Pilot indoor day-counts use, kept for comparability with days_indoor_above_78f_2025.

Source: gridMET (University of Idaho), rmin/rmax = daily min/max relative humidity (2 m, %).
        https://www.northwestknowledge.net/metdata/data/{rmin,rmax}_2025.nc
Note:   gridMET temperature is bias-corrected to PRISM; RH is a derived field (from specific
        humidity + temperature) and is not itself PRISM-bias-corrected. PRISM distributes
        dewpoint/VPD so gridMET RH is not un-anchored, but it carries more uncertainty than tmax.

Usage:
  conda run -n data_science python3 "analysis/cjc reports/indoor_outdoor_heat/extract_wetbulb.py"
"""
import os, tempfile, requests
import numpy as np, pandas as pd, xarray as xr
from pathlib import Path

RH_URL = "https://www.northwestknowledge.net/metdata/data/{v}_2025.nc"
WARM_MONTHS, JJA = [5, 6, 7, 8, 9, 10], [6, 7, 8]
EPS = (0.70, 0.80, 0.85)

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
IO_CSV = HERE / "indoor_outdoor_heat_2025.csv"
TMAX_CSV = REPO / "data_sources/hazards/heat/heat_activations_daily.csv"
OUT_CSV = HERE / "facility_wetbulb_2025.csv"


def f_to_c(f): return (f - 32.0) * 5.0 / 9.0
def c_to_f(c): return c * 9.0 / 5.0 + 32.0


def stull_twb_c(T_c, RH):
    """Stull (2011) wet-bulb temperature. T in °C, RH in %. Fitted domain RH 5–99%, T −20..50°C."""
    RH = np.clip(RH, 5.0, 99.0)   # desert rmin can dip <5%; clip to Stull's fitted floor
    return (T_c * np.arctan(0.151977 * np.sqrt(RH + 8.313659))
            + np.arctan(T_c + RH)
            - np.arctan(RH - 1.676331)
            + 0.00391838 * RH**1.5 * np.arctan(0.023101 * RH)
            - 4.686035)


def download(v, path):
    r = requests.get(RH_URL.format(v=v), stream=True, timeout=600); r.raise_for_status()
    with open(path, "wb") as f:
        for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
            f.write(chunk)


def extract_rh(ncfile, fac):
    ds = xr.open_dataset(ncfile)
    lats = xr.DataArray(fac["latitude"].values, dims="facility")
    lons = xr.DataArray(fac["longitude"].values, dims="facility")
    arr = ds["relative_humidity"].sel(lat=lats, lon=lons, method="nearest").values  # (day, fac)
    dates = pd.to_datetime(ds["day"].values); ds.close()
    return pd.concat([pd.DataFrame({"cdcr_code": c, "date": dates, "rh": arr[:, i]})
                      for i, c in enumerate(fac["cdcr_code"])], ignore_index=True)


def main():
    fac = pd.read_csv(IO_CSV)[["cdcr_code", "latitude", "longitude", "elevation_m"]]

    rh = {}
    for v in ("rmin", "rmax"):
        tmp = tempfile.mktemp(suffix=".nc")
        try:
            print(f"  downloading {v}_2025 …", flush=True)
            download(v, tmp)
            rh[v] = extract_rh(tmp, fac).rename(columns={"rh": v})
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

    tmax = pd.read_csv(TMAX_CSV, parse_dates=["date"])
    tmax = tmax[tmax.date.dt.year == 2025][["cdcr_code", "date", "gridmet_tmax_f"]]

    daily = (tmax.merge(rh["rmin"], on=["cdcr_code", "date"])
                  .merge(rh["rmax"], on=["cdcr_code", "date"]))
    daily = daily[daily.cdcr_code.isin(fac.cdcr_code)].copy()

    twb = c_to_f(stull_twb_c(f_to_c(daily.gridmet_tmax_f.values), daily.rmin.values))
    daily["twb_f"] = twb
    daily["wbd_f"] = daily.gridmet_tmax_f - daily.twb_f
    for e in EPS:
        daily[f"supply_{int(e*100)}"] = daily.gridmet_tmax_f - e * daily.wbd_f
    daily["month"] = daily.date.dt.month

    def summarize(sub, tag):
        g = sub.groupby("cdcr_code")
        out = pd.DataFrame({
            f"n_days_{tag}": g.size(),
            f"rmin_mean_{tag}": g.rmin.mean().round(2),
            f"rmax_mean_{tag}": g.rmax.mean().round(2),
            f"twb_mean_f_{tag}": g.twb_f.mean().round(2),
            f"wbd_mean_f_{tag}": g.wbd_f.mean().round(2),
        })
        for e in EPS:
            col = f"supply_{int(e*100)}"
            out[f"days_evap_cannot_reach_78f_eps{int(e*100)}_{tag}"] = g[col].apply(lambda s: int((s > 78).sum()))
            out[f"days_evap_cannot_reach_85f_eps{int(e*100)}_{tag}"] = g[col].apply(lambda s: int((s > 85).sum()))
        return out

    warm = summarize(daily[daily.month.isin(WARM_MONTHS)], "may_oct")
    jja = summarize(daily[daily.month.isin(JJA)], "jja")[["wbd_mean_f_jja"]]  # JJA sensitivity: wbd only

    out = fac.merge(warm, left_on="cdcr_code", right_index=True).merge(jja, left_on="cdcr_code", right_index=True)
    out = out.sort_values("wbd_mean_f_may_oct").reset_index(drop=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {len(out)} facilities → {OUT_CSV.relative_to(REPO)}")
    print(out[["cdcr_code", "wbd_mean_f_may_oct",
               "days_evap_cannot_reach_78f_eps80_may_oct",
               "days_evap_cannot_reach_85f_eps80_may_oct"]].to_string(index=False))


if __name__ == "__main__":
    main()
