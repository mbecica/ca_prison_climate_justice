"""
LOCA2-CA daily heat metric extraction for all California correctional facilities.

Outputs:
  data_sources/hazards/heat/loca2_facility_cells.csv  — facility -> grid cell assignment
  data_sources/hazards/heat/loca2_facility_heat.csv   — the facility-level heat data product
  data_sources/hazards/heat/loca2_members/*.json      — per-member cache (gitignored, resumable)

Method is documented in data_sources/hazards/heat/README.md. In brief:

  Ensemble    14 models, 62 members. A member is used only if it exists in both `historical`
              and `ssp370`, so composition is identical in every period. HadGEM3-GC31-LL is
              excluded throughout because Cal-Adapt carries no ssp370 for it.
  Weighting   Thresholds and counts per member, then mean within model, then mean across the
              14 models. Every model carries 1/14 regardless of member count.
  Spatial     The grid cell containing the facility. Nearest valid land cell only if the
              containing cell is masked. San Quentin is the sole manual override.
  Baselines   Each member's own 1981-2010 value, held fixed and applied to every period.

Source: LOCA2-CA (Pierce, Cayan & Dehann), grid d03 at 1/32 degree, via the Cal-Adapt
        Analytics Engine S3 zarr store. Anonymous access, no download required.

Usage:
  caffeinate -is conda run --no-capture-output -n data_science python3 scrapers/extract_loca2_heat.py

Runtime: ~6 hours from cold (62 members x 3 periods x 2 variables). Safe to interrupt and
re-run — completed members are cached and skipped. When a v0.1 cache is present, only tasmin
is re-read (~3.5 hours): the validated tasmax counts are reused and the tasmin warm-night
metrics are recomputed under the v0.2 definition (Apr-Oct P95/P98, 1961-1990 baseline).

The data product is written only when all 62 members are cached. A partial cache would pool
into a product built on a smaller ensemble than the method claims while looking complete, so
an incomplete run exits without writing. Use --allow-partial to write a labelled preview to
loca2_facility_heat_PREVIEW.csv instead, and --pool-only to re-pool without re-extracting.
"""

import os
import json
import time
import argparse
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import xarray as xr
import intake

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CATALOG = "https://cadcat.s3.amazonaws.com/cae-collection.json"
GRID = "d03"
DROP_MODEL = "HadGEM3-GC31-LL"   # no ssp370 on cadcat; see README
NON_LOCA2_SOURCES = {"ERA5", "CESM2"}

PERIODS = [
    ("historic",   "historical", 1981, 2010),
    ("midcentury", "ssp370",     2041, 2070),
    ("endcentury", "ssp370",     2071, 2100),
]

TMAX_ABS_F = [80, 90, 100, 110]
TMIN_ABS_F = [60, 70, 80, 90]
SUMMER_MONTHS = [6, 7, 8]
DELTA_F = 10.0

# Warm-night thresholds follow the California agency convention: a percentile of
# warm-season (Apr-Oct) daily minimum temperature over a fixed baseline window,
# counted over Apr-Oct of each period. Because the baseline window (1961-1990)
# differs from the counting windows, the current-period count varies across
# facilities rather than collapsing to the percentile's own tail fraction.
# P95 is primary (OEHHA Indicators of Climate Change); P98 (Cal-Adapt / Fifth
# Assessment) is emitted as sensitivity. See data_sources/hazards/heat/README.md.
NIGHT_SEASON = [4, 5, 6, 7, 8, 9, 10]      # April-October
NIGHT_BASELINE = (1961, 1990)              # observed-era analogue, within LOCA2 historical
NIGHT_PCTLS = [95, 98]

# San Quentin sits on water in the LOCA2 land mask. Nearest-by-distance crosses
# Richardson Bay to a cell open to the Golden Gate and 3.1F cooler; this cell is
# contiguous land and sheltered as the facility is.
SQ_OVERRIDE = (37.953125, -122.515625)

REPO_ROOT = Path(__file__).parent.parent
ALL_FACILITIES_CSV = REPO_ROOT / "data_sources" / "facilities" / "ca_facilities.csv"
CDCR_FACILITIES_CSV = REPO_ROOT / "data" / "cdcr" / "cdcr_facilities.csv"
OUTPUT_DIR = REPO_ROOT / "data_sources" / "hazards" / "heat"
MEMBER_CACHE = OUTPUT_DIR / "loca2_members"
CELLS_CSV = OUTPUT_DIR / "loca2_facility_cells.csv"
PRODUCT_CSV = OUTPUT_DIR / "loca2_facility_heat.csv"
PREVIEW_CSV = OUTPUT_DIR / "loca2_facility_heat_PREVIEW.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def f_to_k(f):
    return (f - 32) * 5 / 9 + 273.15


def k_to_f(k):
    return (k - 273.15) * 9 / 5 + 32


def km_between(lat0, lon0, lat1, lon1):
    """Great-circle-ish distance in km. Raw degrees overweight longitude by ~25%
    at latitude 38 and select the wrong nearest cell, so always scale."""
    return np.hypot((lat1 - lat0) * 111.0,
                    (lon1 - lon0) * 111.0 * np.cos(np.radians(lat0)))


def open_member(cat, source_id, experiment_id, member_id, variable_id):
    df = cat.df
    m = df[(df.source_id == source_id) & (df.experiment_id == experiment_id)
           & (df.member_id == member_id) & (df.table_id == "day")
           & (df.variable_id == variable_id) & (df.grid_label == GRID)]
    if len(m) == 0:
        raise KeyError(f"{source_id}/{experiment_id}/{member_id}/{variable_id}")
    return xr.open_zarr(m.iloc[0].path, storage_options={"anon": True}, consolidated=True)


# ---------------------------------------------------------------------------
# Step 1: assign every facility to a grid cell
# ---------------------------------------------------------------------------

def build_cell_assignment(cat):
    print("\n=== Step 1: facility -> cell assignment ===")
    allf = pd.read_csv(ALL_FACILITIES_CSV)
    cdcr = pd.read_csv(CDCR_FACILITIES_CSV)

    fac = allf[["facilityid", "name", "latitude", "longitude"]].dropna(
        subset=["latitude", "longitude"]).reset_index(drop=True)

    # ca_facilities names carry a trailing "(CODE)"; cdcr_facilities names do not.
    # Joining on name matches 1 of 357 rows and silently disables the SQ override.
    fac["cdcr_code"] = fac["name"].str.extract(r"\(([A-Z0-9]{2,5})\)$")[0]
    known = set(cdcr["cdcr_code"].dropna())
    fac.loc[~fac["cdcr_code"].isin(known), "cdcr_code"] = np.nan
    by_id = cdcr.dropna(subset=["cdcr_code"]).set_index("facilityid")["cdcr_code"].to_dict()
    fac["cdcr_code"] = fac["cdcr_code"].fillna(fac["facilityid"].map(by_id))
    print(f"  {len(fac)} facilities, {fac.cdcr_code.notna().sum()} matched to a cdcr_code")

    masks = {}
    for var in ("tasmax", "tasmin"):
        ds = open_member(cat, "ACCESS-CM2", "historical", "r1i1p1f1", var)
        masks[var] = np.isfinite(ds[var].isel(time=0).values)
        if var == "tasmax":
            glat = np.asarray(ds.lat.values, "float64")
            glon = np.asarray(ds.lon.values, "float64")
    identical = bool((masks["tasmax"] == masks["tasmin"]).all())
    print(f"  land mask: {masks['tasmax'].sum():,} valid cells, tasmax==tasmin: {identical}")
    valid = masks["tasmax"] & masks["tasmin"]
    vi, vj = np.nonzero(valid)
    vlat, vlon = glat[vi], glon[vj]

    rows = []
    for _, r in fac.iterrows():
        la, lo = float(r.latitude), float(r.longitude)
        i = int(np.abs(glat - la).argmin())
        j = int(np.abs(glon - lo).argmin())
        contained_ok = bool(valid[i, j])
        clat, clon, note = glat[i], glon[j], ""
        if not contained_ok:
            d = km_between(la, lo, vlat, vlon)
            k = int(np.argmin(d))
            clat, clon = float(vlat[k]), float(vlon[k])
            note = "masked cell -> nearest valid land"
        if r.cdcr_code == "SQ":
            clat, clon = SQ_OVERRIDE
            note = "manual override (contiguous land WNW)"
        rows.append(dict(facilityid=r.facilityid, name=r["name"], cdcr_code=r.cdcr_code,
                         latitude=la, longitude=lo,
                         cell_lat=clat, cell_lon=clon,
                         cell_dist_km=round(float(km_between(la, lo, clat, clon)), 3),
                         contained_cell_valid=contained_ok,
                         mask_override=bool(note), note=note))

    cells = pd.DataFrame(rows)
    cells["cell_key"] = (cells.cell_lat.round(6).astype(str) + "," +
                         cells.cell_lon.round(6).astype(str))
    cells.to_csv(CELLS_CSV, index=False)
    n_override = int(cells.mask_override.sum())
    print(f"  {len(cells)} facilities -> {cells.cell_key.nunique()} distinct cells")
    print(f"  {n_override} needed a fallback or override: "
          f"{list(cells.loc[cells.mask_override, 'cdcr_code'].fillna('?'))}")
    print(f"  wrote {CELLS_CSV.relative_to(REPO_ROOT)}")
    return cells


# ---------------------------------------------------------------------------
# Step 2: per-member extraction
# ---------------------------------------------------------------------------

def build_roster(cat):
    d = cat.df
    d = d[(d.table_id == "day") & (d.grid_label == GRID) & (d.activity_id == "LOCA2")]
    roster = {}
    for m in sorted(d.source_id.unique()):
        if m == DROP_MODEL or m in NON_LOCA2_SOURCES:
            continue
        hist = set(d[(d.source_id == m) & (d.experiment_id == "historical") &
                     d.variable_id.isin(["tasmax", "tasmin"])].member_id)
        ssp = set(d[(d.source_id == m) & (d.experiment_id == "ssp370") &
                    d.variable_id.isin(["tasmax", "tasmin"])].member_id)
        both = sorted(hist & ssp)
        if both:
            roster[m] = both
    return roster


def annual_avg_count(vals, years, thresh_k):
    """Mean annual count of days above threshold. Matches Ullrich's
    annualavgcount_gt_<T>: count per calendar year, then mean over years."""
    flag = vals > thresh_k
    uy = np.unique(years)
    return np.stack([flag[years == y].sum(axis=0) for y in uy]).mean(axis=0)


def season_avg_count(vals, years, months, thresh_k, season):
    """Mean annual count of season-restricted days above threshold: count the
    days within `season` each calendar year, then mean over years."""
    sel = np.isin(months, season)
    v, y = vals[sel], years[sel]
    flag = v > thresh_k
    uy = np.unique(y)
    return np.stack([flag[y == yr].sum(axis=0) for yr in uy]).mean(axis=0)


def _read_points(cat, model, exp, member, var, y0, y1, ilat, ilon):
    ds = open_member(cat, model, exp, member, var)
    da = ds[var].sel(time=slice(f"{y0}-01-01", f"{y1}-12-31"))
    pts = da.isel(lat=xr.DataArray(ilat, dims="c"), lon=xr.DataArray(ilon, dims="c"))
    vals = pts.values
    t = pd.DatetimeIndex(pts.time.values)
    # NaN silently fails a `>` comparison and yields a count of 0 rather than an
    # error, so it must abort rather than be reported afterwards.
    n_nan = int(np.isnan(vals).any(axis=0).sum())
    if n_nan:
        raise ValueError(f"{model}/{member}/{var}/{y0}-{y1}: {n_nan} NaN cells")
    return vals, t.year.values, t.month.values


def extract_tasmax(cat, model, member, ilat, ilon):
    """Absolute counts + relative avg / avg+10, baseline = summer 1981-2010.
    Unchanged from the validated v0.1 path (reproduction gate)."""
    res = {}
    base_mean = None
    for pname, exp, y0, y1 in PERIODS:
        vals, years, months = _read_points(cat, model, exp, member, "tasmax", y0, y1, ilat, ilon)
        if len(np.unique(years)) != 30:
            raise ValueError(f"{model}/{member}/tasmax/{pname}: expected 30 years")
        if pname == "historic":
            base_mean = vals[np.isin(months, SUMMER_MONTHS)].mean(axis=0)
            res["avg_summer_tasmax_f"] = k_to_f(base_mean).tolist()
        for t_f in TMAX_ABS_F:
            res[f"abs_tasmax_{t_f}_{pname}"] = annual_avg_count(vals, years, f_to_k(t_f)).tolist()
        res[f"rel_tasmax_avg_{pname}"] = annual_avg_count(vals, years, base_mean).tolist()
        res[f"rel_tasmax_avg_plus10_{pname}"] = annual_avg_count(
            vals, years, base_mean + DELTA_F * 5 / 9).tolist()
    return res


def extract_tasmin(cat, model, member, ilat, ilon):
    """Absolute counts (full-year, matching the published tasmin variable set) +
    relative warm-night counts (Apr-Oct P95/P98, baseline 1961-1990 Apr-Oct).

    A single historical read of 1961-2010 supplies both the baseline window and the
    historic counting window; the two projected periods are read separately."""
    res = {}
    b0, b1 = NIGHT_BASELINE
    vh, yh, mh = _read_points(cat, model, "historical", member, "tasmin", b0, 2010, ilat, ilon)

    base = np.isin(yh, np.arange(b0, b1 + 1)) & np.isin(mh, NIGHT_SEASON)
    if len(np.unique(yh[np.isin(yh, np.arange(b0, b1 + 1))])) != (b1 - b0 + 1):
        raise ValueError(f"{model}/{member}/tasmin: baseline {b0}-{b1} incomplete")
    pctl = {p: np.percentile(vh[base], p, axis=0) for p in NIGHT_PCTLS}
    for p in NIGHT_PCTLS:
        res[f"p{p}_tasmin_f"] = k_to_f(pctl[p]).tolist()

    hist_mask = np.isin(yh, np.arange(1981, 2011))
    period_data = {"historic": (vh[hist_mask], yh[hist_mask], mh[hist_mask])}
    for pname, exp, y0, y1 in PERIODS:
        if pname == "historic":
            continue
        period_data[pname] = _read_points(cat, model, exp, member, "tasmin", y0, y1, ilat, ilon)

    for pname, (vals, years, months) in period_data.items():
        if len(np.unique(years)) != 30:
            raise ValueError(f"{model}/{member}/tasmin/{pname}: expected 30 years")
        if pname == "historic":
            res["avg_summer_tasmin_f"] = k_to_f(
                vals[np.isin(months, SUMMER_MONTHS)].mean(axis=0)).tolist()
        for t_f in TMIN_ABS_F:
            res[f"abs_tasmin_{t_f}_{pname}"] = annual_avg_count(vals, years, f_to_k(t_f)).tolist()
        for p in NIGHT_PCTLS:
            res[f"rel_tasmin_p{p}_{pname}"] = season_avg_count(
                vals, years, months, pctl[p], NIGHT_SEASON).tolist()
    return res


def extract_member(cat, model, member, ilat, ilon):
    res = extract_tasmax(cat, model, member, ilat, ilon)
    res.update(extract_tasmin(cat, model, member, ilat, ilon))
    return res


# Sentinel key marking a cache entry as carrying the v0.2 warm-night definition.
# A v0.1 cache has full-year rel_tasmin_p98 and rel_tasmin_avg instead.
NIGHT_SENTINEL = "rel_tasmin_p95_historic"


def _is_v2_tasmin(cached):
    return NIGHT_SENTINEL in cached


def extract_all(cat, roster, ilat, ilon):
    print("\n=== Step 2: per-member extraction ===")
    MEMBER_CACHE.mkdir(parents=True, exist_ok=True)
    total = sum(len(v) for v in roster.values())
    print(f"  {len(roster)} models, {total} members")
    t0 = time.time()
    n = 0
    for model, members in roster.items():
        for member in members:
            n += 1
            path = MEMBER_CACHE / f"{model}__{member}.json"
            cached = json.load(open(path)) if path.exists() else None

            if cached is not None and _is_v2_tasmin(cached):
                print(f"  [{n:2d}/{total}] {model:18s} {member:10s} cached (v0.2)", flush=True)
                continue

            tmin = extract_tasmin(cat, model, member, ilat, ilon)
            if cached is not None:
                # Reuse the validated v0.1 tasmax computation; replace only the
                # tasmin keys (drops the discarded full-year p98 / avg / avg+10),
                # and drop the unused tasmax p98 baseline so key sets stay uniform.
                tasmax = {k: v for k, v in cached.items()
                          if "tasmin" not in k and k != "p98_tasmax_f"}
                res = {**tasmax, **tmin}
                tag = "tasmin re-extracted, tasmax reused"
            else:
                res = extract_tasmax(cat, model, member, ilat, ilon)
                res.update(tmin)
                tag = "full extract"
            json.dump(res, open(path, "w"))
            print(f"  [{n:2d}/{total}] {model:18s} {member:10s} {tag}  "
                  f"elapsed {(time.time()-t0)/60:6.1f}m", flush=True)


# ---------------------------------------------------------------------------
# Step 3: pool to model democracy and write the data product
# ---------------------------------------------------------------------------

def check_complete(roster):
    """Return (missing, expected). Pooling a partial cache silently produces a
    product built on a smaller ensemble than the method claims, so completeness
    is checked before anything is written rather than inferred afterwards."""
    missing = [(m, mem) for m, members in roster.items() for mem in members
               if not (MEMBER_CACHE / f"{m}__{mem}.json").exists()]
    expected = sum(len(v) for v in roster.values())
    return missing, expected


def pool_and_write(roster, cells, ukey, allow_partial=False):
    print("\n=== Step 3: pooling (within model, then across models) ===")

    missing, expected = check_complete(roster)
    if missing:
        print(f"  INCOMPLETE: {len(missing)} of {expected} members not cached")
        for m, mem in missing[:10]:
            print(f"    missing {m} {mem}")
        if len(missing) > 10:
            print(f"    ... and {len(missing) - 10} more")
        if not allow_partial:
            raise SystemExit(
                f"\nRefusing to write {PRODUCT_CSV.name} from {expected - len(missing)}/"
                f"{expected} members.\nRe-run to finish the extraction (cached members are "
                f"skipped), or pass --allow-partial to write a clearly-labelled preview to "
                f"{PREVIEW_CSV.name}."
            )
        print("  --allow-partial set: writing a PREVIEW, not the data product")

    per_model = {}
    for model, members in roster.items():
        loaded = []
        for member in members:
            path = MEMBER_CACHE / f"{model}__{member}.json"
            if path.exists():
                loaded.append(json.load(open(path)))
        if not loaded:
            print(f"  {model:18s}  0 members — MODEL ABSENT from this pooling")
            continue
        keys = loaded[0].keys()
        per_model[model] = {k: np.mean([np.asarray(d[k]) for d in loaded], axis=0) for k in keys}
        print(f"  {model:18s} {len(loaded):2d} of {len(members):2d} members")

    models = sorted(per_model)
    keys = per_model[models[0]].keys()
    ens = {k: np.mean([per_model[m][k] for m in models], axis=0) for k in keys}
    print(f"  pooled across {len(models)} models, equal weight")

    rename = {}
    for pname, _, _, _ in PERIODS:
        for t_f in TMAX_ABS_F:
            rename[f"abs_tasmax_{t_f}_{pname}"] = f"loca2_days_over_{t_f}_{pname}"
        for t_f in TMIN_ABS_F:
            rename[f"abs_tasmin_{t_f}_{pname}"] = f"loca2_nights_over_{t_f}_{pname}"
        rename[f"rel_tasmax_avg_{pname}"] = f"loca2_days_over_avg_{pname}"
        rename[f"rel_tasmax_avg_plus10_{pname}"] = f"loca2_days_over_avg_plus10_{pname}"
        rename[f"rel_tasmin_p95_{pname}"] = f"loca2_nights_over_p95_{pname}"
        rename[f"rel_tasmin_p98_{pname}"] = f"loca2_nights_over_p98_{pname}"
    rename["avg_summer_tasmax_f"] = "loca2_avg_summer_tmax_f"
    rename["avg_summer_tasmin_f"] = "loca2_avg_summer_tmin_f"
    rename["p95_tasmin_f"] = "loca2_p95_tmin_f"
    rename["p98_tasmin_f"] = "loca2_p98_tmin_f"

    cell_df = ukey[["cell_key"]].copy()
    for src, dst in rename.items():
        if src in ens:
            cell_df[dst] = np.round(ens[src], 3)

    out = cells.merge(cell_df, on="cell_key", how="left")
    out["n_models"] = len(models)
    out["n_members"] = expected - len(missing)
    cols = ["facilityid", "name", "cdcr_code", "latitude", "longitude",
            "cell_lat", "cell_lon", "cell_dist_km", "n_models", "n_members", "mask_override"]
    cols += [c for c in out.columns if c.startswith("loca2_")]
    out = out[cols]

    dest = PREVIEW_CSV if missing else PRODUCT_CSV
    out.to_csv(dest, index=False)
    print(f"\n  wrote {len(out)} rows x {len(out.columns)} cols "
          f"-> {dest.relative_to(REPO_ROOT)}")
    if missing:
        print("  PREVIEW ONLY — incomplete ensemble, do not use downstream")
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--allow-partial", action="store_true",
                    help="pool whatever members are cached and write a clearly-labelled "
                         "preview instead of the data product")
    ap.add_argument("--pool-only", action="store_true",
                    help="skip extraction, pool the existing cache")
    args = ap.parse_args()

    cat = intake.open_esm_datastore(CATALOG)

    cells = build_cell_assignment(cat)
    ukey = cells.drop_duplicates("cell_key")[["cell_key", "cell_lat", "cell_lon"]].reset_index(drop=True)

    ds0 = open_member(cat, "ACCESS-CM2", "historical", "r1i1p1f1", "tasmax")
    glat = np.asarray(ds0.lat.values, "float64")
    glon = np.asarray(ds0.lon.values, "float64")
    ilat = np.array([int(np.abs(glat - v).argmin()) for v in ukey.cell_lat])
    ilon = np.array([int(np.abs(glon - v).argmin()) for v in ukey.cell_lon])
    assert np.abs(glat[ilat] - ukey.cell_lat.values).max() < 1e-6
    assert np.abs(glon[ilon] - ukey.cell_lon.values).max() < 1e-6

    roster = build_roster(cat)
    if not args.pool_only:
        extract_all(cat, roster, ilat, ilon)
    out = pool_and_write(roster, cells, ukey, allow_partial=args.allow_partial)

    print("\nSample (CDCR facilities, days over 90F):")
    sample = out[out.cdcr_code.notna()][
        ["cdcr_code", "loca2_days_over_90_historic", "loca2_days_over_90_midcentury"]
    ].sort_values("loca2_days_over_90_midcentury", ascending=False).head(10)
    print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
