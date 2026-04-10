"""
run_event_study.py

Event study: ISP full HVAC replacement (Mar 2024) and CIM Air Cooling Facility A (Feb 2025).
Frame as descriptive case illustration — N=2 treated facilities is too small for causal DiD.

For each outcome:
  1. DiD model: Y ~ heat + heat×post_treat + post_treat + crowding + facility_FE + ym_FE
     β on heat×post_treat = change in heat slope for treated facility post-installation
  2. Event-time plot: treated facility outcome vs. control mean, with treatment date marked
  3. Descriptive table: pre/post means for treated vs. control, summer months only

Outputs (to analysis/cjc reports/):
  heat_ops_did_isp.csv            — ISP DiD coefficients
  heat_ops_did_cim.csv            — CIM DiD coefficients
  heat_ops_event_study_isp.png/.svg
  heat_ops_event_study_cim.png/.svg
  heat_ops_event_study_table.csv  — pre/post descriptive table

Usage:
  python3 analysis/run_event_study.py
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

from linearmodels.panel import PanelOLS

OUT_DIR = "analysis/cjc reports/heat_operations"

# ---------------------------------------------------------------------------
# Load and prep
# ---------------------------------------------------------------------------

print("Loading panel...")
df = pd.read_csv(os.path.join(OUT_DIR, "heat_operations_panel.csv"))
for col in ["days_over_90f", "days_skarha10", "ed_hospital_rate",
            "dental_mh_overtime", "modified_programs_days", "crowding_pct",
            "uof_incidents", "violent_incidents", "actual_expenditure_monthly"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
df["log_ed"]      = np.log(df["ed_hospital_rate"].replace(0, np.nan))
df["log_dental"]  = np.log(df["dental_mh_overtime"].replace(0, np.nan))
df["log_modprog"] = np.log1p(df["modified_programs_days"])
df["crowding_10pp"] = df["crowding_pct"] / 10

# ---------------------------------------------------------------------------
# Merge additional SB601 OT categories (Custody, Non-Custody, Total)
# not in the main panel
# ---------------------------------------------------------------------------

MONTH_MAP = {"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12,
             "Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6}
EXTRA_OT = {
    ("Overtime Hours","Custody (Overtime)"):       "custody_ot",
    ("Overtime Hours","Non-Custody (Overtime)"):   "noncustody_ot",
    ("Overtime Hours","Total Overtime Hours"):      "total_ot",
}
import csv as csvmod
extra = {}
with open("data_sources/facilities/CDCR/sb601_operations_2021-2025.csv") as f:
    for row in csvmod.DictReader(f):
        key = (row["category"], row["metric"])
        if key not in EXTRA_OT:
            continue
        col = EXTRA_OT[key]
        fac = row["institution"]
        fy_start = int(row["fiscal_year"].split("-")[0])
        fy_end   = int(row["fiscal_year"].split("-")[1])
        for m_abbr, m_num in MONTH_MAP.items():
            raw = row.get(m_abbr, "").replace(",", "").strip()
            if not raw:
                continue
            try:
                val = float(raw)
            except ValueError:
                continue
            cal_year = fy_start if m_num >= 7 else fy_end
            extra[(fac, cal_year, m_num, col)] = val

for col in ("custody_ot", "noncustody_ot", "total_ot"):
    df[col] = df.apply(
        lambda r: extra.get((r["facility"], r["year"], r["month"], col), np.nan), axis=1
    )

print(f"  Extra OT columns merged: {(~df['custody_ot'].isna()).sum()} non-null custody_ot rows")

AC_EVENTS = {
    "ISP": pd.Timestamp("2024-03-01"),
    "CIM": pd.Timestamp("2025-02-01"),
}

OUTCOMES = [
    ("log_ed",                    "ED/Hospital Stay rate (log)",       "ed_hospital_rate",            "ED/Hosp rate\n(per 1,000)"),
    ("dental_mh_overtime",        "Dental+MH Overtime (hours)",        "dental_mh_overtime",          "Dental+MH OT\n(hours)"),
    ("violent_incidents",         "Violent Incidents (raw)",           "violent_incidents",           "Violent\nIncidents"),
    ("uof_incidents",             "Use of Force Incidents (raw)",      "uof_incidents",               "UOF\nIncidents"),
    ("custody_ot",                "Custody Overtime (hours)",          "custody_ot",                  "Custody OT\n(hours)"),
    ("noncustody_ot",             "Non-Custody Overtime (hours)",      "noncustody_ot",               "Non-Custody OT\n(hours)"),
    ("total_ot",                  "Total Overtime Hours",              "total_ot",                    "Total OT\n(hours)"),
    ("modified_programs_days",    "Modified Programs Days (raw)",      "modified_programs_days",      "Modified\nPrograms Days"),
    ("actual_expenditure_monthly","Monthly Expenditure ($)",           "actual_expenditure_monthly",  "Monthly\nExpenditure ($)"),
]
# Raw (not log) for OT and modprog so ISP's post-installation zeros are
# kept as real observations rather than being dropped by log(0)=NaN.

# ---------------------------------------------------------------------------
# DiD model helper
# ---------------------------------------------------------------------------

def run_did(df, treated_fac, treat_date, outcome, heat_var="days_over_90f"):
    """
    Y ~ heat + heat×post_treat + post_treat + crowding + facility_FE + ym_FE
    post_treat = 1 for treated_fac in months >= treat_date.
    Returns dict of coefficients.
    """
    sub = df.copy()
    sub["post_treat"] = ((sub["facility"] == treated_fac) &
                          (sub["date"] >= treat_date)).astype(float)
    sub["heat_x_post"] = sub[heat_var] * sub["post_treat"]

    cols = [outcome, heat_var, "heat_x_post", "post_treat", "crowding_10pp"]
    sub = sub[["facility", "date"] + cols].dropna(subset=cols)

    if sub["facility"].nunique() < 5 or len(sub) < 50:
        return None

    sub = sub.set_index(["facility", "date"])
    mod = PanelOLS(
        dependent=sub[outcome],
        exog=sub[[heat_var, "heat_x_post", "post_treat", "crowding_10pp"]],
        entity_effects=True,
        time_effects=True,
        check_rank=False,
    )
    try:
        res = mod.fit(cov_type="clustered", cluster_entity=True)
        out = {}
        for var in [heat_var, "heat_x_post", "post_treat"]:
            out[f"beta_{var}"] = res.params.get(var, np.nan)
            out[f"se_{var}"]   = res.std_errors.get(var, np.nan)
            out[f"p_{var}"]    = res.pvalues.get(var, np.nan)
        out["n_obs"] = int(res.nobs)
        out["n_fac"] = int(res.entity_info["total"])
        return out
    except Exception as e:
        print(f"    DiD warning ({treated_fac}, {outcome}): {e}")
        return None


def sig_stars(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.1:   return "."
    return ""

# ---------------------------------------------------------------------------
# Run DiD for ISP and CIM
# ---------------------------------------------------------------------------

for treated_fac, treat_date in AC_EVENTS.items():
    print(f"\n{'='*60}")
    print(f"DiD: {treated_fac} (treatment: {treat_date.strftime('%b %Y')})")
    print(f"{'='*60}")

    rows = []
    for outcome, outcome_label, _, _ in OUTCOMES:
        result = run_did(df, treated_fac, treat_date, outcome)
        if result is None:
            print(f"  {outcome_label[:40]}: insufficient data")
            continue
        result["outcome"] = outcome_label
        result["facility"] = treated_fac
        result["treat_date"] = treat_date.strftime("%Y-%m")
        rows.append(result)

        b_heat    = result["beta_days_over_90f"]
        b_ix      = result["beta_heat_x_post"]
        p_ix      = result["p_heat_x_post"]
        b_post    = result["beta_post_treat"]
        print(f"  {outcome_label[:38]}: "
              f"heat β={b_heat:+.4f}, "
              f"heat×post β={b_ix:+.4f} (p={p_ix:.3f}{sig_stars(p_ix)}), "
              f"post β={b_post:+.4f}, "
              f"N={result['n_obs']}, Fac={result['n_fac']}")

    if rows:
        out_df = pd.DataFrame(rows).round(4)
        out_df.to_csv(os.path.join(OUT_DIR, f"heat_ops_did_{treated_fac.lower()}.csv"), index=False)

# ---------------------------------------------------------------------------
# Pre/post descriptive table (summer months: Jun–Sep, hot days > 0)
# ---------------------------------------------------------------------------

print("\nBuilding pre/post descriptive table...")

desc_rows = []
for treated_fac, treat_date in AC_EVENTS.items():
    fac_df = df[df["facility"] == treated_fac].copy()
    ctrl_df = df[df["facility"] != treated_fac].copy()

    for period_label, mask_fn in [("Pre", lambda d: d["date"] < treat_date),
                                   ("Post", lambda d: d["date"] >= treat_date)]:
        for grp_label, grp_df in [(treated_fac, fac_df), ("Control (mean)", ctrl_df)]:
            sub = grp_df[mask_fn(grp_df) & (grp_df["month"].isin([6, 7, 8, 9]))]
            row = {
                "Facility": grp_label,
                "Period": period_label,
                "Treat date": treat_date.strftime("%b %Y"),
                "N months": len(sub),
                "Mean days >90°F": round(sub["days_over_90f"].mean(), 1),
                "Mean ED rate": round(sub["ed_hospital_rate"].mean(), 2),
                "Mean Dental+MH OT": round(sub["dental_mh_overtime"].mean(), 1),
                "Mean Violent Incidents": round(sub["violent_incidents"].mean(), 1),
                "Mean UOF Incidents": round(sub["uof_incidents"].mean(), 1),
                "Mean Mod Prog Days": round(sub["modified_programs_days"].mean(), 1),
            }
            desc_rows.append(row)

desc_df = pd.DataFrame(desc_rows)
desc_df.to_csv(os.path.join(OUT_DIR, "heat_ops_event_study_table.csv"), index=False)
print(desc_df.to_string(index=False))

# ---------------------------------------------------------------------------
# Event-time figures
# ---------------------------------------------------------------------------

def make_event_figure(treated_fac, treat_date):
    fac_df  = df[df["facility"] == treated_fac].sort_values("date")
    ctrl_df = df[df["facility"] != treated_fac].copy()

    plot_specs = [
        ("ed_hospital_rate",           "ED/Hospital Stay Rate\n(per 1,000)"),
        ("dental_mh_overtime",         "Dental+MH Overtime\n(hours/month)"),
        ("violent_incidents",          "Violent Incidents\n(count/month)"),
        ("uof_incidents",              "Use of Force Incidents\n(count/month)"),
        ("actual_expenditure_monthly", "Monthly Expenditure\n($ millions)"),
        ("custody_ot",                 "Custody Overtime\n(hours/month)"),
        ("noncustody_ot",              "Non-Custody Overtime\n(hours/month)"),
        ("total_ot",                   "Total Overtime\n(hours/month)"),
        ("modified_programs_days",     "Modified Programs Days\n(person-days)"),
    ]

    # Scale expenditure to millions for legibility
    for d in (fac_df, ctrl_df):
        if "actual_expenditure_monthly" in d.columns:
            d["actual_expenditure_monthly"] = d["actual_expenditure_monthly"] / 1e6

    # Compute control group monthly mean and 95% CI for each column
    ctrl_agg = {}
    for col, _ in plot_specs:
        g = ctrl_df.groupby("date")[col].agg(["mean","std","count"]).reset_index()
        g["se"] = g["std"] / np.sqrt(g["count"].clip(lower=1))
        ctrl_agg[col] = g

    pre_date  = treat_date - pd.DateOffset(months=36)
    post_date = df["date"].max()

    ncols = 2
    nrows = int(np.ceil(len(plot_specs) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 4.5 * nrows))
    axes = axes.flatten()

    fig.suptitle(
        f"{treated_fac}: AC Installation ({treat_date.strftime('%b %Y')}) — "
        f"All Outcomes vs. Control Group Mean (33 facilities)\n"
        f"Red dashed line = installation date. Gray band = 95% CI across control facilities. Orange bars = days >90°F ({treated_fac}).",
        fontsize=9, y=1.01
    )

    # Heat series for the treated facility (days >90°F), trimmed to plot window
    heat_plot = fac_df[(fac_df["date"] >= pre_date) & (fac_df["date"] <= post_date)][["date", "days_over_90f"]].copy()

    for ax, (fac_col, ylabel) in zip(axes, plot_specs):
        fac_plot  = fac_df[(fac_df["date"] >= pre_date) & (fac_df["date"] <= post_date)]
        ctrl_plot = ctrl_agg[fac_col]
        ctrl_plot = ctrl_plot[(ctrl_plot["date"] >= pre_date) & (ctrl_plot["date"] <= post_date)]

        # Secondary axis: heat (days >90°F) as light orange bars behind the outcome
        ax2 = ax.twinx()
        ax2.bar(heat_plot["date"], heat_plot["days_over_90f"],
                width=20, color="darkorange", alpha=0.18, label="Days >90°F")
        ax2.set_ylim(0, heat_plot["days_over_90f"].max() * 4)  # keep bars unobtrusive
        ax2.set_ylabel("Days >90°F", fontsize=6, color="darkorange")
        ax2.tick_params(axis="y", labelsize=6, colors="darkorange")
        ax2.spines["right"].set_edgecolor("darkorange")

        ax.fill_between(
            ctrl_plot["date"],
            (ctrl_plot["mean"] - 1.96 * ctrl_plot["se"]).clip(lower=0),
            ctrl_plot["mean"] + 1.96 * ctrl_plot["se"],
            alpha=0.18, color="gray"
        )
        ax.plot(ctrl_plot["date"], ctrl_plot["mean"],
                color="gray", linewidth=1.2, linestyle="--", label="Control mean")
        ax.plot(fac_plot["date"], fac_plot[fac_col],
                color="steelblue", linewidth=2, marker="o", markersize=3,
                label=treated_fac)
        ax.axvline(treat_date, color="red", linestyle="--", linewidth=1.5, label="AC install")
        ax.set_zorder(ax2.get_zorder() + 1)  # outcome line on top of heat bars
        ax.patch.set_visible(False)

        ax.set_title(ylabel, fontsize=8, pad=4)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        ax.tick_params(labelsize=7)
        ax.legend(fontsize=7, loc="upper left")
        ax.set_ylim(bottom=0)

    for ax in axes[len(plot_specs):]:
        ax.set_visible(False)

    plt.tight_layout()
    for ext in ("png", "svg"):
        path = os.path.join(OUT_DIR, f"heat_ops_event_study_{treated_fac.lower()}.{ext}")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"  Saved {path}")
    plt.close()


print("\nGenerating event-time figures...")
for treated_fac, treat_date in AC_EVENTS.items():
    make_event_figure(treated_fac, treat_date)

print("\nDone.")
