#!/usr/bin/env python3
"""Per-facility historic hourly temperature envelopes for the CA Carceral
Facility Heat Tracker.

For each facility, pulls 10 years (2016–2025) of hourly temperature from the
Open-Meteo Historical Weather API (ERA5/ERA5-Land, era5_seamless — same family
as build_baselines.py) and computes, for every hour of the June 1 – October 31
season, the p10 / median / p90 across the 10 years. The app's detail-page chart
slices the current 2-week window out of this band ("you are here vs. the last
decade").

One small JSON per facility, named by slug (from slugs.csv — run
build_facilities.py first):

    static/data/bands/<slug>.json   in the ca-carceral-heat-tracker repo

    { "slug", "years", "season", "tz", "p10": [...], "p50": [...], "p90": [...] }
    (whole °F; index i = hour i of the season in local time, i.e. Jun 1 00:00 + i hours,
    DST-free calendar hours — 153 days x 24 = 3672 values per percentile)

Usage:

    python3 analysis/heatwave_app/build_historic_bands.py                 # all
    python3 analysis/heatwave_app/build_historic_bands.py --only-missing  # new/resume

The window rolls forward one year each post-season refresh (edit YEAR_START /
YEAR_END, then rerun WITHOUT --only-missing to rebuild all bands).

Runtime: one API request per facility (~10 years of hourly data each); with
free-tier throttling expect 1–2 hours for all ~357. Interruptible — rerun with
--only-missing to resume.
"""
import argparse
import csv
import json
import statistics
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
APP = REPO.parent / "ca-carceral-heat-tracker"
FAC_CSV = REPO / "data_sources/facilities/ca_facilities.csv"
REGISTRY_CSV = HERE / "slugs.csv"
BAND_DIR = APP / "static/data/bands"

API = "https://archive-api.open-meteo.com/v1/archive"
MODEL = "era5_seamless"
YEAR_START, YEAR_END = 2016, 2025        # 10-year window; roll forward post-season
SEASON = ("06-01", "10-31")              # Jun–Oct, matches the app's season
PAUSE_S = 3.0                            # base pause between facilities
TZ = "America/Los_Angeles"


def season_hours():
    """All (mm-dd, hh) slots Jun 1 – Oct 31, in order."""
    days = pd.date_range(f"2001-{SEASON[0]}", f"2001-{SEASON[1]}")   # any non-leap year
    return [(d.strftime("%m-%d"), h) for d in days for h in range(24)]


def fetch_hourly(lat, lon, retries=20):
    params = {
        "latitude": f"{lat:.5f}", "longitude": f"{lon:.5f}",
        "start_date": f"{YEAR_START}-{SEASON[0]}",
        "end_date": f"{YEAR_END}-{SEASON[1]}",
        "hourly": "temperature_2m",
        "temperature_unit": "fahrenheit",
        "timezone": TZ,
        "models": MODEL,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=300) as resp:
                return json.loads(resp.read())
        except Exception as e:
            wait = min(600, 60 * (attempt + 1))
            print(f"    request failed ({e}); retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"fetch failed after {retries} attempts")


def build_band(data, slots):
    """data: open-meteo hourly response. Returns dict slot -> (p10, p50, p90)."""
    times = data["hourly"]["time"]                    # local ISO "YYYY-MM-DDTHH:MM"
    temps = data["hourly"]["temperature_2m"]
    by_slot = {}
    for t, v in zip(times, temps):
        if v is None:
            continue
        key = (t[5:10], int(t[11:13]))                # (mm-dd, hour)
        by_slot.setdefault(key, []).append(v)

    p10, p50, p90 = [], [], []
    for key in slots:
        vals = by_slot.get(key)
        if not vals:
            p10.append(None); p50.append(None); p90.append(None)
            continue
        qs = statistics.quantiles(vals, n=10, method="inclusive")  # deciles
        p10.append(round(qs[0]))
        p50.append(round(statistics.median(vals)))
        p90.append(round(qs[8]))
    return p10, p50, p90


def main():
    ap = argparse.ArgumentParser(description="Build 10-yr hourly envelope bands")
    ap.add_argument("--only-missing", action="store_true",
                    help="skip facilities whose band JSON already exists (also = resume)")
    args = ap.parse_args()

    fac = pd.read_csv(FAC_CSV)
    fac = fac[fac["status"] == "OPEN"].set_index("facilityid")

    if not REGISTRY_CSV.exists():
        raise SystemExit("slugs.csv not found — run build_facilities.py first")
    with open(REGISTRY_CSV) as f:
        registry = [r for r in csv.DictReader(f) if not r["retired"]]

    todo = []
    for r in registry:
        fid = int(r["facilityid"])
        if fid not in fac.index:
            continue
        out = BAND_DIR / f"{r['slug']}.json"
        if args.only_missing and out.exists():
            continue
        todo.append((r["slug"], fac.loc[fid, "latitude"], fac.loc[fid, "longitude"], out))

    print(f"{len(todo)} bands to build ({YEAR_START}–{YEAR_END}, {SEASON[0]}..{SEASON[1]})")
    BAND_DIR.mkdir(parents=True, exist_ok=True)
    slots = season_hours()

    for i, (slug, lat, lon, out) in enumerate(todo, 1):
        print(f"  [{i}/{len(todo)}] {slug}", flush=True)
        data = fetch_hourly(float(lat), float(lon))
        p10, p50, p90 = build_band(data, slots)
        n_null = sum(1 for v in p50 if v is None)
        if n_null:
            print(f"    WARNING: {n_null}/{len(slots)} empty hour slots")
        band = {
            "slug": slug,
            "years": f"{YEAR_START}-{YEAR_END}",
            "season": f"{SEASON[0]}..{SEASON[1]}",
            "tz": TZ,
            "unit": "°F",
            "n_hours": len(slots),   # index i = Jun 1 00:00 local + i calendar hours
            "p10": p10, "p50": p50, "p90": p90,
        }
        out.write_text(json.dumps(band, ensure_ascii=False, separators=(",", ":")))
        time.sleep(PAUSE_S)

    print(f"Done -> {BAND_DIR}")


if __name__ == "__main__":
    main()
