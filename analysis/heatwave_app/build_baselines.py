#!/usr/bin/env python3
"""Per-facility temperature baselines for the CA Carceral Facility Heat Tracker.

For every OPEN facility in ca_facilities.csv, computes the 1991–2020 mean
June–August daily maximum temperature (°F) from the Open-Meteo Historical
Weather API (ERA5/ERA5-Land reanalysis, model pinned to era5_seamless). The
app's display threshold is this baseline + 10°F (Skarha et al. 2023 metric —
same definition as the CDCR-only `skarha10` work in this repo, which used
gridMET; see scrapers/extract_gridmet_heat.py).

The 1991–2020 window is fixed by definition (WMO normal period) — this script
never "refreshes"; it only reruns for facilities added to the list:

    python3 analysis/heatwave_app/build_baselines.py                 # all facilities
    python3 analysis/heatwave_app/build_baselines.py --only-missing  # new facilities only

Output: analysis/heatwave_app/data/baselines.csv
    facilityid, name, latitude, longitude, baseline_summer_avg_tmax_f,
    n_summer_days, grid_elevation_m, source, retrieved

Runtime: ~5–15 min for all ~357 facilities (30 years of daily data each,
batched requests, throttled for the free tier).
"""
import argparse
import csv
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FAC_CSV = REPO / "data_sources/facilities/ca_facilities.csv"
OUT_CSV = HERE / "data/baselines.csv"

API = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "era5_seamless"
START, END = "1991-01-01", "2020-12-31"
SUMMER_MONTHS = ("-06-", "-07-", "-08-")
BATCH = 25            # locations per request
PAUSE_S = 2.0         # between requests (free-tier courtesy)
SOURCE = f"open-meteo archive ({MODEL}), 1991-2020 Jun-Aug"


def fetch_batch(rows, retries=20):
    """rows: list of (facilityid, name, lat, lon). Returns list of result dicts.

    Free-tier quotas are minute- AND hour-bucketed, so on 429 we wait long
    enough for the hourly budget to trickle back rather than failing fast."""
    params = {
        "latitude": ",".join(f"{r[2]:.5f}" for r in rows),
        "longitude": ",".join(f"{r[3]:.5f}" for r in rows),
        "start_date": START,
        "end_date": END,
        "daily": "temperature_2m_max",
        "temperature_unit": "fahrenheit",
        "timezone": "America/Los_Angeles",
        "models": MODEL,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp:
                data = json.loads(resp.read())
            return data if isinstance(data, list) else [data]
        except Exception as e:
            wait = min(600, 60 * (attempt + 1))
            print(f"    request failed ({e}); retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"batch failed after {retries} attempts")


def summer_mean(result):
    """Mean of Jun–Aug daily tmax across all years; returns (mean_f, n_days)."""
    days = result["daily"]["time"]
    vals = result["daily"]["temperature_2m_max"]
    summer = [v for d, v in zip(days, vals)
              if d[4:8] in ("-06-", "-07-", "-08-") and v is not None]
    if not summer:
        return None, 0
    return round(sum(summer) / len(summer), 2), len(summer)


def main():
    ap = argparse.ArgumentParser(description="Build 1991-2020 summer tmax baselines")
    ap.add_argument("--only-missing", action="store_true",
                    help="skip facilities already in baselines.csv")
    args = ap.parse_args()

    fac = pd.read_csv(FAC_CSV)
    fac = fac[fac["status"] == "OPEN"]
    rows = [(int(f.facilityid), f.name, float(f.latitude), float(f.longitude))
            for f in fac.itertuples()]

    existing = []
    if OUT_CSV.exists():
        with open(OUT_CSV) as f:
            existing = list(csv.DictReader(f))
    if args.only_missing:
        done = {int(r["facilityid"]) for r in existing}
        rows = [r for r in rows if r[0] not in done]
        print(f"--only-missing: {len(done)} already built, {len(rows)} to fetch")
    else:
        existing = []

    if not rows:
        print("Nothing to fetch.")
        return

    today = date.today().isoformat()
    out_rows = existing
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        print(f"  batch {i // BATCH + 1}/{-(-len(rows) // BATCH)} "
              f"({batch[0][1][:32]} … {batch[-1][1][:32]})", flush=True)
        results = fetch_batch(batch)
        if len(results) != len(batch):
            raise RuntimeError(f"expected {len(batch)} results, got {len(results)}")
        for (fid, name, lat, lon), res in zip(batch, results):
            mean_f, n = summer_mean(res)
            out_rows.append({
                "facilityid": fid, "name": name,
                "latitude": lat, "longitude": lon,
                "baseline_summer_avg_tmax_f": mean_f,
                "n_summer_days": n,
                "grid_elevation_m": res.get("elevation"),
                "source": SOURCE, "retrieved": today,
            })
        # incremental save so an interrupted run resumes with --only-missing
        OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_CSV, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
        time.sleep(PAUSE_S)

    n_null = sum(1 for r in out_rows if not r["baseline_summer_avg_tmax_f"])
    print(f"Wrote {len(out_rows)} baselines -> {OUT_CSV.relative_to(REPO)}"
          + (f" ({n_null} null!)" if n_null else ""))


if __name__ == "__main__":
    main()
