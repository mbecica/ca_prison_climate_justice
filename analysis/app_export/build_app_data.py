#!/usr/bin/env python3
"""Build the front-end data bundle for the California Prison Heat Index web app.

Single reproducible step: joins the heat-risk index with the CDCR facilities
table, emits one framework-agnostic JSON (the app's source of truth), copies the
CA outline, and regenerates the 31 per-prison Hugo content stubs.

Re-run this whenever the underlying CSVs change:

    python3 analysis/app_export/build_app_data.py

Outputs (into the sibling `website` repo):
    website/data/prison_heat_index.json          (Hugo .Site.Data — no-JS list + stub gen)
    website/static/data/prison_heat_index.json   (fetched client-side by phi-*.js)
    website/static/data/ca_outline_simple.json   (D3 base map)
    website/content/prison-heat-index/<slug>.md  (31 routable profile stubs)
"""
import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import wkt
from shapely.geometry import mapping

REPO = Path(__file__).resolve().parents[2]          # ca_prison_climate_justice/
SITE = REPO.parent / "website"                        # sibling website repo (private)
OUT = Path(__file__).resolve().parent / "output"      # canonical open-source data, next to this script
RISK_CSV = REPO / "data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv"
FAC_CSV = REPO / "data/cdcr/cdcr_facilities.csv"
HAZ_CSV = REPO / "data/allfacilities_climate_hazards.csv"   # outdoor climate metrics
OUTLINE = REPO / "data/ca_outline_simple.json"

CATEGORIES = ["Lowest", "Moderate", "High", "Highest"]

# Canonical display names (source CSVs have inconsistent casing). SQ reflects the
# 2023 rename to San Quentin Rehabilitation Center.
NAMES = {
    "ASP": "Avenal State Prison",
    "CAL": "Calipatria State Prison",
    "CCI": "California Correctional Institution",
    "CCWF": "Central California Women's Facility",
    "CEN": "Centinela State Prison",
    "CHCF": "California Health Care Facility",
    "CIM": "California Institution for Men",
    "CIW": "California Institution for Women",
    "CMC": "California Men's Colony",
    "CMF": "California Medical Facility",
    "COR": "California State Prison, Corcoran",
    "CRC": "California Rehabilitation Center",
    "CTF": "Correctional Training Facility",
    "FOL": "Folsom State Prison",
    "HDSP": "High Desert State Prison",
    "ISP": "Ironwood State Prison",
    "KVSP": "Kern Valley State Prison",
    "LAC": "California State Prison, Los Angeles County",
    "MCSP": "Mule Creek State Prison",
    "NKSP": "North Kern State Prison",
    "PBSP": "Pelican Bay State Prison",
    "PVSP": "Pleasant Valley State Prison",
    "RJD": "Richard J. Donovan Correctional Facility",
    "SAC": "California State Prison, Sacramento",
    "SATF": "California Substance Abuse Treatment Facility",
    "SCC": "Sierra Conservation Center",
    "SOL": "California State Prison, Solano",
    "SQ": "San Quentin Rehabilitation Center",
    "SVSP": "Salinas Valley State Prison",
    "VSP": "Valley State Prison",
    "WSP": "Wasco State Prison",
}

SLUGS = {
    "ASP": "avenal-state-prison",
    "CAL": "calipatria-state-prison",
    "CCI": "california-correctional-institution",
    "CCWF": "central-california-womens-facility",
    "CEN": "centinela-state-prison",
    "CHCF": "california-health-care-facility",
    "CIM": "california-institution-for-men",
    "CIW": "california-institution-for-women",
    "CMC": "california-mens-colony",
    "CMF": "california-medical-facility",
    "COR": "california-state-prison-corcoran",
    "CRC": "california-rehabilitation-center",
    "CTF": "correctional-training-facility",
    "FOL": "folsom-state-prison",
    "HDSP": "high-desert-state-prison",
    "ISP": "ironwood-state-prison",
    "KVSP": "kern-valley-state-prison",
    "LAC": "california-state-prison-los-angeles-county",
    "MCSP": "mule-creek-state-prison",
    "NKSP": "north-kern-state-prison",
    "PBSP": "pelican-bay-state-prison",
    "PVSP": "pleasant-valley-state-prison",
    "RJD": "richard-j-donovan-correctional-facility",
    "SAC": "california-state-prison-sacramento",
    "SATF": "california-substance-abuse-treatment-facility",
    "SCC": "sierra-conservation-center",
    "SOL": "california-state-prison-solano",
    "SQ": "san-quentin-rehabilitation-center",
    "SVSP": "salinas-valley-state-prison",
    "VSP": "valley-state-prison",
    "WSP": "wasco-state-prison",
}

LAYER_META = {
    "risk": {
        "label": "Overall Risk",
        "short": "Who is most at risk if cooling fails",
        "desc": "A combined score: one part heat hazard, one part exposure, and "
                "two parts vulnerability. Higher means people here are more at "
                "risk from extreme heat than at other California prisons.",
    },
    "hazard": {
        "label": "Heat Hazard",
        "short": "How hot and smoky the outdoor climate is",
        "desc": "How extreme the local climate is: hot days, nights that stay "
                "warm, and air quality, modeled for the area around each prison.",
    },
    "exposure": {
        "label": "Exposure",
        "short": "How much that heat reaches people inside",
        "desc": "How much of that outdoor heat actually reaches people inside: "
                "indoor hot days, how much the buildings trap heat, the urban "
                "heat island, and how little real air conditioning there is.",
    },
    "vulnerability": {
        "label": "Vulnerability",
        "short": "Who is least able to withstand heat",
        "desc": "How much harm that heat is likely to cause the people held "
                "here, based on age, serious mental-health and disability needs, "
                "and overall medical acuity. It carries the most weight, because "
                "people in prison can't cool themselves at will.",
    },
}


def title_county(s):
    return None if pd.isna(s) else str(s).title()


def full_address(f):
    """Compose 'street, City, ST zip' from the facility row; None if no street."""
    if pd.isna(f.get("address")):
        return None
    street = str(f["address"]).strip()
    city = "" if pd.isna(f.get("city")) else str(f["city"]).title()
    state = "" if pd.isna(f.get("state")) else str(f["state"]).upper()
    zc = "" if pd.isna(f.get("zip")) else str(int(float(f["zip"]))).zfill(5)
    tail = " ".join(x for x in (state, zc) if x)          # "CA 93204"
    head = ", ".join(x for x in (street, city) if x)       # "1 Kings Way, Avenal"
    return ", ".join(x for x in (head, tail) if x)         # "..., CA 93204"


def num(v, digits=None):
    """NaN -> None; optionally round; keep ints clean."""
    if pd.isna(v):
        return None
    v = float(v)
    if digits is not None:
        v = round(v, digits)
    return int(v) if v == int(v) else v


def bool_from(v):
    if pd.isna(v):
        return None
    s = str(v).strip().lower()
    if s in ("yes", "true", "1", "1.0"):
        return True
    if s in ("no", "false", "0", "0.0", ""):
        return False
    return True  # any non-empty descriptive value counts as present


def quantile_bins(values):
    """Three inner breaks (25/50/75th pct) over non-null values -> 4 classes."""
    arr = np.array([v for v in values if v is not None and not pd.isna(v)], float)
    return np.percentile(arr, [25, 50, 75]).tolist()


def classify(v, breaks):
    if v is None or pd.isna(v):
        return None
    for i, b in enumerate(breaks):
        if v <= b:
            return CATEGORIES[i]
    return CATEGORIES[-1]


def main():
    risk = pd.read_csv(RISK_CSV)
    fac = pd.read_csv(FAC_CSV).dropna(subset=["cdcr_code"])
    haz = pd.read_csv(HAZ_CSV).set_index("facilityid")   # outdoor climate, by facilityid

    # Self-identifying index version (from the index CSV; defaults to v0.2).
    index_version = str(risk["index_version"].iloc[0]) if "index_version" in risk.columns else "v0.2"

    cur = risk[risk.time_period == "current"].set_index("cdcr_code")
    mid = risk[risk.time_period == "midcentury"].set_index("cdcr_code")
    facx = fac.set_index("cdcr_code")
    codes = list(cur.index)
    assert len(codes) == 31, f"expected 31 prisons, got {len(codes)}"

    # Bin breaks per layer, pooled so colors are comparable across the set.
    hazard_breaks = quantile_bins(list(cur["hazard_score"]) + list(mid["hazard_score"]))
    exposure_breaks = quantile_bins(list(cur["exposure_score"]))
    vuln_breaks = quantile_bins(list(cur["vulnerability_score"]))

    def layer_block(row, key, raw_to_display, breaks=None, category=None):
        raw = row[key] if not pd.isna(row[key]) else None
        display = None if raw is None else round(raw_to_display(raw))
        cat = category if category is not None else classify(raw, breaks)
        return {"value": num(raw, 2), "display": display, "category": cat}

    def period(row):
        return {
            "risk": layer_block(row, "risk_score", lambda v: v,
                                category=row["risk_category"]),
            "hazard": layer_block(row, "hazard_score", lambda v: v * 100,
                                  breaks=hazard_breaks),
            "exposure": layer_block(row, "exposure_score", lambda v: v * 100,
                                    breaks=exposure_breaks),
            "vulnerability": layer_block(row, "vulnerability_score", lambda v: v * 100,
                                         breaks=vuln_breaks),
        }

    # NOTE (open item, flagged by author July 2026): the CSV calls the baseline
    # period "current", but it is a 1991–2020 modeled HISTORIC baseline, so the
    # app labels it "Historic". The intended full set is Historic / Mid-Century /
    # End-Century; End-Century data does not exist in the source CSV yet, so only
    # two periods ship for now. Exposure & vulnerability are held constant across
    # periods (2025 values) by design — only the heat hazard changes.
    prisons = []
    for code in codes:
        c, m, f = cur.loc[code], mid.loc[code], facx.loc[code]
        h = haz.loc[f["facilityid"]] if f["facilityid"] in haz.index else None
        def hz(col):
            return None if h is None or pd.isna(h[col]) else h[col]
        prisons.append({
            "code": code,
            "name": NAMES[code],
            "slug": SLUGS[code],
            "city": None if pd.isna(f["city"]) else str(f["city"]),
            "county": title_county(f["county"]),
            "address": full_address(f),
            "jurisdiction": None if pd.isna(f.get("type")) else str(f["type"]).title(),
            "lat": num(c["latitude"], 5),
            "lon": num(c["longitude"], 5),
            "year_opened": num(c["year_opened"]),
            "population": num(c["average_2025_population"]),
            "capacity_pct": num(f.get("capacity_percent_2025"), 3),
            "security": None if pd.isna(f.get("securelvl")) else str(f["securelvl"]).title(),
            "periods": {"historic": period(c), "midcentury": period(m)},
            "profile": {
                "hazard": {
                    # Modeled outdoor climate (heat index v0.3). days_over_90 is an
                    # absolute-threshold display metric; the hazard SCORE is built on
                    # the relative thresholds below (hot days above the facility's own
                    # summer mean +10°F, warm nights above its 1961-1990 Apr-Oct P95).
                    "days_over_90": {
                        "historic": num(hz("heat_days_over_90_historic")),
                        "midcentury": num(hz("heat_days_over_90_midcentury")),
                    },
                    "hot_days": {  # days_over_avg_plus10 (relative, Skarha threshold)
                        "historic": num(hz("heat_days_over_avg_plus10_historic"), 1),
                        "midcentury": num(hz("heat_days_over_avg_plus10_midcentury"), 1),
                        # Facility's historic mean summer daily-high (°F). The hot-day
                        # threshold is this + 10°F, so the app can label the metric with
                        # the actual per-facility cutoff.
                        "avg_summer_high_f": num(hz("heat_avg_summer_tmax_f"), 1),
                    },
                    "warm_nights": {  # nights_over_p95, Apr-Oct, per year (relative)
                        "historic": num(hz("heat_nights_over_p95_historic"), 1),
                        "midcentury": num(hz("heat_nights_over_p95_midcentury"), 1),
                    },
                    "aqi_pctile": num(hz("heat_aqi_pctile")),
                },
                "cooling": {
                    # Housing-unit cooling mix from the CDCR Air Cooling Pilot
                    # Supplemental Report (Jan 2026, as of Dec 2025) — the newest,
                    # complete, per-facility source. Replaces the older, incomplete
                    # Reuters FOIA equipment inventory (pct_units_*). Mixed-cooling
                    # units are counted under each type, so shares can sum slightly >1.
                    # Only "mechanical" is refrigerated AC; evaporative and ventilation
                    # do not provide reliable cooling.
                    "mechanical_pct": num(f["pct_hu_mechanical"], 4),
                    "evaporative_pct": num(f["pct_hu_evaporative"], 4),
                    "air_handlers_pct": num(f["pct_hu_air_handlers"], 4),
                    "n_housing_units": num(f["n_housing_units"]),
                    "as_of": "2025-12",
                    "source": "CDCR Air Cooling Pilot Supplemental Report, Jan 2026",
                },
                "demographics": {
                    # gender_female_pct and race_peopleofcolor_pct are fractions
                    # (0-1) in source; CCHCS *_pct fields are already percentages.
                    "female_pct": num(f["gender_female_pct"] * 100, 1),
                    "poc_pct": num(f["race_peopleofcolor_pct"] * 100, 1),
                    "age_over_50_pct": num(f["cchcs_age_over_50_pct_2025"], 1),
                },
                "medical": {
                    "mental_health_eop_pct": num(f["cchcs_mental_health_eop_pct_2025"], 1),
                    "dpp_pct": num(f["cchcs_dpp_pct_2025"], 1),
                    "high_risk_p1_pct": num(f["cchcs_high_risk_p1_pct_2025"], 1),
                    "high_risk_p2_pct": num(f["cchcs_high_risk_p2_pct_2025"], 1),
                    "medium_risk_pct": num(f["cchcs_medium_risk_pct_2025"], 1),
                },
                "heat": {
                    "days_indoor_above_78f_2025": num(c["days_indoor_above_78f_2025"]),
                    "ratio_indoor_to_outdoor": num(c["ratio_indoor_to_outdoor"], 3),
                    "uhi_normalized": num(c["uhi_normalized"], 3),
                },
                "context": {
                    "dist_nearest_medical_mi": num(c["dist_nearest_medical_mi"], 2),
                    "rhu_pct": num(c["rhu_pct_2025"], 3),
                    "california_model_facility": bool_from(c["california_model_facility"]),
                    "air_cooling_pilot": bool_from(f["cdcr_air_cooling_pilot"]),
                    "planned_closure": bool_from(f["planned_closure"]),
                    "avg_annual_violent_incidents": num(f["avg_annual_violent_incidents"], 1),
                },
            },
        })

    prisons.sort(key=lambda p: p["name"])

    # Overall-risk ranking, computed WITHIN each period: the hazard component moves
    # between periods, so a prison's standing does too, and the profile's rank line
    # follows its period toggle. Ranked on the unrounded `value` — the rounded
    # `display` ties often (e.g. two prisons both showing 100), which would make the
    # order between them arbitrary.
    n = len(prisons)

    def risk_value(p, period):
        v = p["periods"][period]["risk"]["value"]
        return -1 if v is None else v

    for period in ("historic", "midcentury"):
        ranked = sorted(prisons, key=lambda p: risk_value(p, period), reverse=True)
        for i, p in enumerate(ranked):
            p["periods"][period]["risk_rank"] = i + 1

    # Neighbor links for profile prev/next, ordered by the app's DEFAULT period.
    default_ranked = sorted(prisons, key=lambda p: risk_value(p, "historic"), reverse=True)
    for i, p in enumerate(default_ranked):
        p["risk_rank_total"] = n
        hi = default_ranked[i - 1] if i > 0 else None      # higher overall risk
        lo = default_ranked[i + 1] if i < n - 1 else None  # lower overall risk
        p["neighbors"] = {
            "higher": {"slug": hi["slug"], "name": hi["name"]} if hi else None,
            "lower": {"slug": lo["slug"], "name": lo["name"]} if lo else None,
        }

    bundle = {
        "meta": {
            "index_version": index_version,
            "n_prisons": len(prisons),
            "weights": {"hazard": 0.25, "exposure": 0.25, "vulnerability": 0.50},
            "periods": {
                "historic": {"label": "Current", "sub": "1991–2020"},
                "midcentury": {"label": "Mid-century", "sub": "2041–2070"},
            },
            "planned_periods": ["endcentury"],  # data not yet available; see script note
            "period_note": "Periods are modeled climate data, not observed "
                           "weather. Only the heat hazard changes between periods; "
                           "exposure and vulnerability are held constant (2025 "
                           "values).",
            "scale_note": "Scores are relative to California's 31 state prisons: "
                          "the lowest sits near 0 and the highest near 100. A low "
                          "score means lower risk than other prisons, not that the "
                          "heat is safe.",
            "categories": CATEGORIES,
            "layers": LAYER_META,
        },
        "prisons": prisons,
    }

    # ---- write outputs -------------------------------------------------------
    # Canonical, open-sourced JSON lives here in the public repo; copies are also
    # written into the private website repo (SITE) for the Hugo build.
    (SITE / "data").mkdir(parents=True, exist_ok=True)
    (SITE / "static/data").mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(bundle, ensure_ascii=False, indent=2)
    (OUT / "prison_heat_index.json").write_text(payload)
    (SITE / "data/prison_heat_index.json").write_text(payload)
    (SITE / "static/data/prison_heat_index.json").write_text(payload)
    shutil.copyfile(OUTLINE, SITE / "static/data/ca_outline_simple.json")

    write_stubs(prisons)
    write_boundaries(prisons, facx)

    print(f"Wrote {len(prisons)} prisons -> {SITE/'data/prison_heat_index.json'}")
    print(f"JSON size: {len(payload)/1024:.1f} KB")


def write_boundaries(prisons, facx):
    """Prison boundary polygons (FEMA/HiFLD, WKT -> GeoJSON) for the detail-page
    maps. Simplified slightly to shrink the file; keyed by cdcr code."""
    feats = []
    for p in prisons:
        raw = facx.loc[p["code"]].get("geometry")
        if pd.isna(raw):
            continue
        geom = wkt.loads(raw).simplify(0.00005, preserve_topology=True)
        feats.append({
            "type": "Feature",
            "properties": {
                "code": p["code"], "name": p["name"], "slug": p["slug"],
                "risk_category": p["periods"]["midcentury"]["risk"]["category"],
                "population": p["population"],
            },
            "geometry": mapping(geom),
        })
    fc = {"type": "FeatureCollection", "features": feats}
    geo = json.dumps(fc, ensure_ascii=False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "prison_boundaries.geojson").write_text(geo)          # canonical open-source copy
    out = SITE / "static/data/prison_boundaries.geojson"
    out.write_text(geo)
    print(f"Wrote {len(feats)} boundaries -> {out} ({out.stat().st_size/1024:.1f} KB)")


def write_stubs(prisons):
    """One thin routable Hugo content file per prison. Body renders client-side."""
    out = SITE / "content/prison-heat-index"
    out.mkdir(parents=True, exist_ok=True)
    for p in prisons:
        fm = (
            "---\n"
            f'title: "{p["name"]}"\n'
            f'code: "{p["code"]}"\n'
            f'slug: "{p["slug"]}"\n'
            "type: prison-heat-index\n"
            "layout: single\n"
            f'summary: "Extreme-heat risk profile for {p["name"]}, one of '
            'California\'s 31 state prisons."\n'
            "---\n"
        )
        (out / f"{p['slug']}.md").write_text(fm)
    print(f"Wrote {len(prisons)} content stubs -> {out}")


if __name__ == "__main__":
    main()
