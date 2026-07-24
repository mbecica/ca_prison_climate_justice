"""
Annual summer average tmax per CDCR facility, 1990–2025.

Computes mean Jun–Aug daily maximum temperature (°F) per facility per year.
For 1990–2015: downloads gridMET year files, extracts summer tmax, deletes file.
For 2016–2025: reads from existing heat_activations_daily.csv.

Output:
  data_sources/hazards/summer_avg_tmax_annual.csv
  Columns: cdcr_code, year, avg_summer_tmax_f

Usage:
  conda run -n data_science python3 data_sources/hazards/heat/extraction/extract_gridmet_summer_avg.py

Runtime: ~15–25 minutes (downloads ~3.5 GB across 26 year files; deleted after use).
"""

import os
import tempfile
import csv
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import xarray as xr

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GRIDMET_URL   = "https://www.northwestknowledge.net/metdata/data/tmmx_{year}.nc"
DOWNLOAD_YEARS = range(1990, 2016)   # 1990–2015; 2016–2025 read from existing CSV
REPO_ROOT      = Path(__file__).resolve().parents[4]
FACILITIES_CSV = REPO_ROOT / "data" / "cdcr" / "cdcr_facilities.csv"
DAILY_CSV      = REPO_ROOT / "data_sources" / "hazards" / "heat" / "heat_activations_daily.csv"
OUTPUT_CSV     = REPO_ROOT / "data_sources" / "hazards" / "heat" / "summer_avg_tmax_annual.csv"


# ---------------------------------------------------------------------------
# Helpers (shared with extract_gridmet_heat.py)
# ---------------------------------------------------------------------------

def kelvin_to_f(k):
    return (k - 273.15) * 9 / 5 + 32


def load_facilities():
    df = pd.read_csv(FACILITIES_CSV)
    prisons = df[
        df["cdcr_code"].notna() &
        (df["cdcr_firecamp"] != True)
    ][["cdcr_code", "name", "latitude", "longitude"]].copy()
    prisons = prisons.reset_index(drop=True)
    print(f"  {len(prisons)} CDCR state prisons loaded")
    return prisons


def download_year(year, tmp_path):
    url = GRIDMET_URL.format(year=year)
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    total = 0
    with open(tmp_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
            f.write(chunk)
            total += len(chunk)
    return total


def summer_avg_from_nc(nc_path, facilities, year):
    """Extract Jun–Aug daily tmax per facility from a gridMET file, return avg per facility."""
    ds = xr.open_dataset(nc_path)
    lats = xr.DataArray(facilities["latitude"].values, dims="facility")
    lons = xr.DataArray(facilities["longitude"].values, dims="facility")
    pts = ds["air_temperature"].sel(lat=lats, lon=lons, method="nearest")
    tmax_k = pts.values           # (n_days, n_facilities)
    tmax_f = kelvin_to_f(tmax_k)
    dates  = pd.to_datetime(ds["day"].values)
    ds.close()

    summer_mask = pd.Series(dates).dt.month.isin([6, 7, 8]).values
    summer_f = tmax_f[summer_mask, :]   # (n_summer_days, n_facilities)

    rows = []
    for fi, row in facilities.iterrows():
        avg = float(np.mean(summer_f[:, fi]))
        rows.append({"cdcr_code": row["cdcr_code"], "year": year, "avg_summer_tmax_f": round(avg, 2)})
    return rows


# ---------------------------------------------------------------------------
# Step 1: Download 1990–2015 and compute summer averages
# ---------------------------------------------------------------------------

def compute_historic(facilities):
    records = []
    for year in DOWNLOAD_YEARS:
        tmp = tempfile.mktemp(suffix=".nc")
        try:
            size_mb = download_year(year, tmp) / 1e6
            print(f"  {year}  {size_mb:.0f} MB downloaded", end="  ", flush=True)
            rows = summer_avg_from_nc(tmp, facilities, year)
            records.extend(rows)
            avgs = [r["avg_summer_tmax_f"] for r in rows]
            print(f"avg across facilities: {sum(avgs)/len(avgs):.1f}°F")
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return records


# ---------------------------------------------------------------------------
# Step 2: Read 2016–2025 averages from existing daily CSV
# ---------------------------------------------------------------------------

def compute_from_daily():
    summer_by = defaultdict(list)
    with open(DAILY_CSV) as f:
        for row in csv.DictReader(f):
            month = int(row["date"].split("-")[1])
            if month in (6, 7, 8):
                year = int(row["date"].split("-")[0])
                summer_by[(row["cdcr_code"], year)].append(float(row["tmax_f"]))

    records = []
    for (code, year), vals in sorted(summer_by.items()):
        records.append({
            "cdcr_code": code,
            "year": year,
            "avg_summer_tmax_f": round(sum(vals) / len(vals), 2),
        })
    print(f"  Read {len(records)} facility-years from existing daily CSV (2016–2025)")
    return records


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading facilities...")
    facilities = load_facilities()

    print(f"\n=== Downloading and computing 1990–2015 summer averages ===")
    historic = compute_historic(facilities)

    print(f"\n=== Computing 2016–2025 summer averages from existing daily CSV ===")
    recent = compute_from_daily()

    all_records = historic + recent
    all_records.sort(key=lambda r: (r["cdcr_code"], r["year"]))

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["cdcr_code", "year", "avg_summer_tmax_f"])
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\nWrote {len(all_records)} rows → {OUTPUT_CSV.relative_to(REPO_ROOT)}")
    print("\nSample (hottest facilities, 2024):")
    sample = sorted([r for r in all_records if r["year"] == 2024],
                    key=lambda r: -r["avg_summer_tmax_f"])[:5]
    for r in sample:
        print(f"  {r['cdcr_code']:6s}  {r['avg_summer_tmax_f']:.1f}°F")


if __name__ == "__main__":
    main()
