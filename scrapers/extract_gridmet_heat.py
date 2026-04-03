"""
gridMET daily maximum temperature extraction for CDCR state prisons.

Outputs:
  data_sources/hazards/heat_activations_daily.csv   — daily tmax + activation flags per facility (2016–2025)
  data_sources/hazards/heat_activations_annual.csv  — annual counts per facility
  data_sources/hazards/heat_activations_monthly.csv — monthly stage1/stage3 counts per facility per year

Metrics:
  stage1    — outdoor tmax >= 90°F  (CDCR Heat Pathology Plan Stage I threshold)
  stage3    — outdoor tmax >= 95°F  (CDCR Heat Pathology Plan Stage III threshold)
  skarha10  — tmax >= facility mean summer (Jun–Aug) tmax + 10°F
              Based on Skarha et al. (2023) marginal mortality metric.
              Baseline: 1991–2020 mean Jun–Aug tmax per facility (WMO 30-year normal period).

Source: gridMET (University of Idaho), variable tmmx (daily maximum temperature, Kelvin)
        https://www.northwestknowledge.net/metdata/data/tmmx_{year}.nc

Usage:
  conda run -n data_science python3 scrapers/extract_gridmet_heat.py

Runtime: ~30–45 minutes (downloads ~5.8 GB across 40 year files; files are deleted after use).
"""

import os
import sys
import tempfile
import requests
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GRIDMET_URL = "https://www.northwestknowledge.net/metdata/data/tmmx_{year}.nc"

BASELINE_YEARS = range(1991, 2021)   # 1991–2020 inclusive, for Skarha mean
ANALYSIS_YEARS = range(2016, 2026)   # 2016–2025 inclusive

STAGE1_F = 90.0
STAGE3_F = 95.0
SKARHA_DELTA_F = 10.0  # degrees above facility mean summer tmax

REPO_ROOT = Path(__file__).parent.parent
FACILITIES_CSV = REPO_ROOT / "data" / "cdcr_facilities.csv"
OUTPUT_DIR = REPO_ROOT / "data_sources" / "hazards"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def kelvin_to_f(k):
    return (k - 273.15) * 9 / 5 + 32


def load_facilities():
    """Return the 31 CDCR state prisons (non-camp, cdcr_code present)."""
    df = pd.read_csv(FACILITIES_CSV)
    prisons = df[
        df["cdcr_code"].notna() &
        (df["cdcr_firecamp"] != True)
    ][["cdcr_code", "name", "latitude", "longitude"]].copy()
    prisons = prisons.reset_index(drop=True)
    print(f"  {len(prisons)} CDCR state prisons loaded")
    return prisons


def download_year(year, tmp_path):
    """Download one year of gridMET tmmx to tmp_path. Returns file size."""
    url = GRIDMET_URL.format(year=year)
    r = requests.get(url, stream=True, timeout=300)
    r.raise_for_status()
    total = 0
    with open(tmp_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=4 * 1024 * 1024):
            f.write(chunk)
            total += len(chunk)
    return total


def extract_facility_tmax(nc_path, facilities):
    """
    Open a gridMET year file and extract daily tmax (°F) for each facility.

    Returns a DataFrame with columns: cdcr_code, date, tmax_f
    """
    ds = xr.open_dataset(nc_path)

    lats = xr.DataArray(facilities["latitude"].values, dims="facility")
    lons = xr.DataArray(facilities["longitude"].values, dims="facility")

    # Nearest-neighbor selection — loads only the selected pixels
    pts = ds["air_temperature"].sel(lat=lats, lon=lons, method="nearest")
    # pts shape: (day, facility)

    tmax_k = pts.values  # (n_days, n_facilities)
    tmax_f = kelvin_to_f(tmax_k)
    dates = pd.to_datetime(ds["day"].values)

    ds.close()

    rows = []
    for fi, row in facilities.iterrows():
        df = pd.DataFrame({
            "cdcr_code": row["cdcr_code"],
            "date": dates,
            "tmax_f": tmax_f[:, fi],
        })
        rows.append(df)

    return pd.concat(rows, ignore_index=True)


# ---------------------------------------------------------------------------
# Step 1: Compute per-facility mean summer (Jun–Aug) tmax over 1991–2020
# ---------------------------------------------------------------------------

def compute_skarha_baselines(facilities):
    """
    Download 1991–2020 gridMET files and compute mean Jun–Aug tmax per facility.

    Returns a dict: cdcr_code -> mean_summer_tmax_f
    """
    print("\n=== Computing Skarha baselines (1991–2020 mean Jun–Aug tmax) ===")

    # Accumulate summer days across all baseline years
    summer_records = []

    for year in BASELINE_YEARS:
        tmp = tempfile.mktemp(suffix=".nc")
        try:
            size_mb = download_year(year, tmp) / 1e6
            print(f"  {year}  {size_mb:.0f} MB", end="  ", flush=True)

            df = extract_facility_tmax(tmp, facilities)
            df["date"] = pd.to_datetime(df["date"])
            summer = df[df["date"].dt.month.isin([6, 7, 8])]
            summer_records.append(summer[["cdcr_code", "tmax_f"]])
            print(f"{len(summer)} summer days extracted")

        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    all_summer = pd.concat(summer_records, ignore_index=True)
    baselines = (
        all_summer.groupby("cdcr_code")["tmax_f"]
        .mean()
        .to_dict()
    )

    print("\nFacility mean summer tmax (°F):")
    for code, mean_f in sorted(baselines.items()):
        print(f"  {code:6s}  {mean_f:.1f}°F  (threshold: {mean_f + SKARHA_DELTA_F:.1f}°F)")

    return baselines


# ---------------------------------------------------------------------------
# Step 2: Extract 2016–2025 daily data and apply thresholds
# ---------------------------------------------------------------------------

def extract_analysis_years(facilities, skarha_baselines):
    """
    Download 2016–2025 gridMET files and build the daily activation dataset.

    Returns daily DataFrame with: cdcr_code, date, tmax_f, stage1, stage3, skarha10
    """
    print("\n=== Extracting analysis years (2016–2025) ===")

    all_records = []

    for year in ANALYSIS_YEARS:
        tmp = tempfile.mktemp(suffix=".nc")
        try:
            size_mb = download_year(year, tmp) / 1e6
            print(f"  {year}  {size_mb:.0f} MB", end="  ", flush=True)

            df = extract_facility_tmax(tmp, facilities)
            df["date"] = pd.to_datetime(df["date"])
            all_records.append(df)
            print(f"{len(df)} rows")

        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    daily = pd.concat(all_records, ignore_index=True)
    daily = daily.sort_values(["cdcr_code", "date"]).reset_index(drop=True)

    # Apply thresholds
    daily["stage1"] = (daily["tmax_f"] >= STAGE1_F).astype(int)
    daily["stage3"] = (daily["tmax_f"] >= STAGE3_F).astype(int)
    daily["skarha_threshold_f"] = daily["cdcr_code"].map(
        lambda c: skarha_baselines.get(c, np.nan) + SKARHA_DELTA_F
    )
    daily["skarha10"] = (daily["tmax_f"] >= daily["skarha_threshold_f"]).astype(int)
    daily = daily.drop(columns=["skarha_threshold_f"])

    return daily


# ---------------------------------------------------------------------------
# Step 3: Aggregate to annual and monthly
# ---------------------------------------------------------------------------

def aggregate(daily):
    """Build annual and monthly summary DataFrames."""
    daily["year"] = daily["date"].dt.year
    daily["month"] = daily["date"].dt.month

    annual = (
        daily.groupby(["cdcr_code", "year"])
        .agg(
            stage1_days=("stage1", "sum"),
            stage3_days=("stage3", "sum"),
            skarha10_days=("skarha10", "sum"),
        )
        .reset_index()
    )

    monthly = (
        daily.groupby(["cdcr_code", "year", "month"])
        .agg(
            stage1_days=("stage1", "sum"),
            stage3_days=("stage3", "sum"),
        )
        .reset_index()
    )

    return annual, monthly


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Loading facilities...")
    facilities = load_facilities()

    skarha_baselines = compute_skarha_baselines(facilities)

    daily = extract_analysis_years(facilities, skarha_baselines)

    annual, monthly = aggregate(daily)

    # Drop intermediate columns before writing daily output
    daily_out = daily.drop(columns=["year", "month"], errors="ignore")

    # Write outputs
    daily_path = OUTPUT_DIR / "heat_activations_daily.csv"
    annual_path = OUTPUT_DIR / "heat_activations_annual.csv"
    monthly_path = OUTPUT_DIR / "heat_activations_monthly.csv"

    daily_out.to_csv(daily_path, index=False)
    annual.to_csv(annual_path, index=False)
    monthly.to_csv(monthly_path, index=False)

    print(f"\nWrote {len(daily_out):,} rows  → {daily_path.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(annual):,} rows  → {annual_path.relative_to(REPO_ROOT)}")
    print(f"Wrote {len(monthly):,} rows  → {monthly_path.relative_to(REPO_ROOT)}")

    print("\nSample annual output (top 10 by skarha10_days):")
    print(annual.nlargest(10, "skarha10_days").to_string(index=False))


if __name__ == "__main__":
    main()
