"""
run_heat_operations_regression.py

TWFE panel regression: heat exposure → operational outcomes at CDCR facilities.
Extends Skarha (2023) and Cloud (2023) to operational outcomes using SB 601 and CCHCS data.

Model: Y_it = β1·Heat_it + β2·Crowding_it + α_i + γ_ym + ε_it
  - α_i  : facility fixed effects
  - γ_ym : year×month fixed effects
  - SE   : clustered by facility

Outputs (to analysis/cjc reports/):
  heat_ops_main_results.csv        — main table (3 outcomes × 2 heat vars)
  heat_ops_robustness.csv          — lag-1 and Poisson robustness
  heat_ops_moderation.csv          — AC type and security level interactions
  heat_ops_panel_summary.csv       — descriptive stats by heat quartile
  heat_ops_event_study.png/.svg    — ISP event-time plot

Usage:
  python3 analysis/run_heat_operations_regression.py
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import os

from linearmodels.panel import PanelOLS
from linearmodels.panel import PooledOLS

OUT_DIR = "analysis/cjc reports/heat_operations"

# ---------------------------------------------------------------------------
# 1. Load panel
# ---------------------------------------------------------------------------

print("Loading panel...")
df = pd.read_csv(os.path.join(OUT_DIR, "heat_operations_panel.csv"))
print(f"  {len(df)} rows, {df['facility'].nunique()} facilities, "
      f"{df['year'].min()}–{df['year'].max()}")

# ---------------------------------------------------------------------------
# 2. Prepare variables
# ---------------------------------------------------------------------------

print("Preparing variables...")

# Date index
df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
df["ym"] = df["year"].astype(str) + "_" + df["month"].astype(str).str.zfill(2)

# Log-transform outcomes (replace "" with NaN first)
for col in ["dental_mh_overtime", "modified_programs_days", "uof_incidents",
            "violent_incidents", "inmate_on_inmate", "staff_involved", "ed_hospital_rate",
            "ed_hospital_cost", "total_labor_cost",
            "specialty_care_referrals", "prescriptions_per_patient",
            "actual_expenditure_monthly", "institution_budget",
            "crowding_pct", "days_over_90f", "days_over_avg_plus10",
            "vacancy_all", "vacancy_medical", "vacancy_dental", "vacancy_mh"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["log_ed"]      = np.log(df["ed_hospital_rate"].replace(0, np.nan))
df["log_ed_cost"]        = np.log1p(df["ed_hospital_cost"].clip(lower=0))
df["log_labor_cost"]     = np.log1p(df["total_labor_cost"].clip(lower=0))
df["log_specialty"]      = np.log1p(df["specialty_care_referrals"].clip(lower=0))
df["log_prescriptions"]  = np.log(df["prescriptions_per_patient"].replace(0, np.nan))
df["log_dental"]  = np.log(df["dental_mh_overtime"].replace(0, np.nan))
df["log_modprog"] = np.log1p(df["modified_programs_days"])  # log(y+1) for 40% zeros
# Fiscal: monthly spend can be negative in rare months (downward budget corrections);
# use log(y+1) with floor at 0 to retain those rows rather than dropping them.
df["log_spend"]        = np.log1p(df["actual_expenditure_monthly"].clip(lower=0))
df["log_uof"]          = np.log1p(df["uof_incidents"])
df["log_violent"]      = np.log1p(df["violent_incidents"])
df["log_inmate_v"]     = np.log1p(df["inmate_on_inmate"])   # Mukherjee-comparable
df["log_staff_v"]      = np.log1p(df["staff_involved"])

# Lag-1 heat variables (within facility, by calendar date)
df_sorted = df.sort_values(["facility", "date"])
df["heat_90_lag1"]    = df_sorted.groupby("facility")["days_over_90f"].shift(1)
df["over_avg_plus10_lag1"] = df_sorted.groupby("facility")["days_over_avg_plus10"].shift(1)

# Crowding: standardize so coefficient is per 10pp
df["crowding_10pp"] = df["crowding_pct"] / 10

# pct_mechanical: fraction of housing units with mechanical cooling (0–1).
# Source: December 2025 snapshot — static for all facilities except ISP.
# ISP: 0.0 before 2024-03, 1.0 after (full HVAC replacement P-0910-01113).
import csv as _csv
_ac = {}
with open("data_sources/facilities/CDCR/air_cooling_infrastructure_dec2025.csv") as _f:
    for _row in _csv.DictReader(_f):
        try:
            _mech  = int(_row["hu_mechanical_cooling"])
            _total = int(_row["n_housing_units"])
            _ac[_row["institution"]] = _mech / _total if _total > 0 else np.nan
        except (ValueError, KeyError):
            pass

# Assign static snapshot value, then override ISP as time-varying
df["pct_mechanical"] = df["facility"].map(_ac)
isp_treat = pd.Timestamp("2024-03-01")
df.loc[df["facility"] == "ISP", "pct_mechanical"] = np.where(
    df.loc[df["facility"] == "ISP", "date"] >= isp_treat, 1.0, 0.0
)

# Security level: binary high (MAXIMUM) vs not
df["high_security"] = (df["security_level"] == "MAXIMUM").astype(float)
df.loc[df["security_level"] == "", "high_security"] = np.nan

print(f"  Log-transformed outcomes ready")
print(f"  Lag-1 heat variables ready")

# ---------------------------------------------------------------------------
# 3. TWFE helper
# ---------------------------------------------------------------------------

def run_twfe(data, outcome, heat_var, extra_vars=None, entity_col="facility"):
    """
    Run TWFE with facility FE and year×month FE.
    Returns result object or None if insufficient data.
    Time index is the date column (date-like, required by linearmodels).
    """
    cols = [outcome, heat_var, "crowding_10pp"] + (extra_vars or [])
    sub = data[["facility", "date"] + cols].dropna(subset=cols)
    if sub[entity_col].nunique() < 5 or len(sub) < 50:
        return None

    sub = sub.set_index([entity_col, "date"])
    # entity_effects = facility FE; time_effects = year×month FE
    mod = PanelOLS(
        dependent=sub[outcome],
        exog=sub[[heat_var, "crowding_10pp"] + (extra_vars or [])],
        entity_effects=True,
        time_effects=True,
    )
    try:
        res = mod.fit(cov_type="clustered", cluster_entity=True)
        return res
    except Exception as e:
        print(f"    Warning: {outcome} ~ {heat_var}: {e}")
        return None


def extract_coef(res, var):
    """Extract β, SE, p for a variable from a linearmodels result."""
    if res is None or var not in res.params.index:
        return dict(beta=np.nan, se=np.nan, p=np.nan, n_obs=np.nan, n_fac=np.nan)
    return dict(
        beta=res.params[var],
        se=res.std_errors[var],
        p=res.pvalues[var],
        n_obs=int(res.nobs),
        n_fac=int(res.entity_info["total"]),
    )


def bh_correct(pvals, alpha=0.05):
    """Benjamini-Hochberg FDR correction. Returns adjusted p-values."""
    pvals = np.array(pvals, dtype=float)
    n = len(pvals)
    order = np.argsort(pvals)
    adjusted = np.empty(n)
    adjusted[order] = pvals[order] * n / (np.arange(1, n + 1))
    # Enforce monotonicity from the right
    for i in range(n - 2, -1, -1):
        adjusted[order[i]] = min(adjusted[order[i]], adjusted[order[i + 1]])
    return np.clip(adjusted, 0, 1)


def sig_stars(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.1:   return "."
    return ""

# ---------------------------------------------------------------------------
# 4. Main results table
# ---------------------------------------------------------------------------

print("\nRunning main TWFE regressions...")

OUTCOMES = [
    ("log_ed",       "ED/Hospital Stay rate (log)"),
    ("log_ed_cost",       "ED & Hospital Stay Cost [log(y+1)]"),
    ("log_labor_cost",    "Total Labor Cost [log(y+1)]"),
    ("log_specialty",     "Specialty Care Referrals [log(y+1)]"),
    ("log_prescriptions", "Prescriptions Per Patient (log)"),
    ("log_dental",   "Dental+MH Overtime (log)"),
    ("log_modprog",  "Modified Programs Days [log(y+1)]"),
    ("log_inmate_v", "Inmate-on-Inmate Violence [log(y+1)]"),
    ("log_staff_v",  "Staff-Involved Incidents [log(y+1)]"),
    ("log_violent",  "All Violent Incidents [log(y+1)]"),
    ("log_uof",      "Use of Force Incidents [log(y+1)]"),
    ("log_spend",    "Monthly Expenditure [log(y+1)]"),
]
HEAT_VARS = [
    ("days_over_90f",  "Days >90°F"),
    ("days_over_avg_plus10",  "Days mean summer temp. anomaly"),
]

main_rows = []
all_pvals = []

for heat_var, heat_label in HEAT_VARS:
    for outcome, outcome_label in OUTCOMES:
        res = run_twfe(df, outcome, heat_var)
        coef = extract_coef(res, heat_var)
        coef.update({"outcome": outcome_label, "heat": heat_label})
        main_rows.append(coef)
        all_pvals.append(coef["p"])
        print(f"  {heat_label} → {outcome_label[:30]}: "
              f"β={coef['beta']:.4f}, SE={coef['se']:.4f}, p={coef['p']:.3f}, "
              f"N={coef['n_obs']}, Fac={coef['n_fac']}")

# BH correction across all 16 primary tests (8 outcomes × 2 heat vars)
bh_pvals = bh_correct(all_pvals)
for i, row in enumerate(main_rows):
    row["p_bh"] = bh_pvals[i]
    row["sig"] = sig_stars(row["p"])
    row["sig_bh"] = sig_stars(row["p_bh"])

main_df = pd.DataFrame(main_rows, columns=[
    "heat", "outcome", "beta", "se", "p", "sig", "p_bh", "sig_bh", "n_obs", "n_fac"
])
main_df = main_df.round({"beta": 4, "se": 4, "p": 4, "p_bh": 4})
main_df.to_csv(os.path.join(OUT_DIR, "heat_ops_main_results.csv"), index=False)
print(f"\nMain results saved.")

# ---------------------------------------------------------------------------
# 5. Robustness table (lag 1 + Poisson for Modified Programs)
# ---------------------------------------------------------------------------

print("\nRunning robustness regressions (lag-1)...")

rob_rows = []
for heat_var, heat_label in HEAT_VARS:
    lag_var = "heat_90_lag1" if heat_var == "days_over_90f" else "over_avg_plus10_lag1"
    for outcome, outcome_label in OUTCOMES:
        res = run_twfe(df, outcome, lag_var)
        coef = extract_coef(res, lag_var)
        coef.update({"outcome": outcome_label, "heat": heat_label, "spec": "Lag 1"})
        rob_rows.append(coef)
        print(f"  [Lag1] {heat_label} → {outcome_label[:28]}: "
              f"β={coef['beta']:.4f}, p={coef['p']:.3f}")

# Poisson TWFE for modified programs: use within-transformed (demeaned) Poisson
# via statsmodels GLM with facility + ym dummies.
print("\nRunning Poisson robustness for Modified Programs Days...")
try:
    import statsmodels.api as sm

    for heat_var, heat_label in HEAT_VARS:
        sub = df[["facility", "ym", "modified_programs_days",
                  heat_var, "crowding_10pp"]].dropna()
        sub = sub.copy()
        # Build dummy matrices
        fac_dummies = pd.get_dummies(sub["facility"], drop_first=True, prefix="fac")
        ym_dummies  = pd.get_dummies(sub["ym"],       drop_first=True, prefix="ym")
        X = pd.concat([sub[[heat_var, "crowding_10pp"]], fac_dummies, ym_dummies], axis=1)
        X = sm.add_constant(X)
        y = sub["modified_programs_days"]
        mod = sm.GLM(y, X, family=sm.families.Poisson()).fit(
            method="irls", maxiter=200, disp=False)
        beta = mod.params[heat_var]
        # Cluster-robust SE manually via HC (statsmodels Poisson + cluster)
        groups = sub["facility"].values
        score = mod.resid_response[:, None] * X.values
        meat = np.zeros((X.shape[1], X.shape[1]))
        for g in np.unique(groups):
            sg = score[groups == g].sum(axis=0)
            meat += np.outer(sg, sg)
        H = mod.cov_params()
        cov_cl = H @ meat @ H
        se = np.sqrt(np.diag(cov_cl))[list(X.columns).index(heat_var)]
        p  = 2 * (1 - stats.norm.cdf(abs(beta / se)))
        rob_rows.append(dict(
            outcome="Modified Programs Days [Poisson]",
            heat=heat_label, spec="Poisson (lag 0)",
            beta=beta, se=se, p=p, n_obs=int(mod.nobs),
            n_fac=sub["facility"].nunique()
        ))
        print(f"  [Poisson] {heat_label} → ModProg: β={beta:.4f}, p={p:.3f}")
except Exception as e:
    print(f"  Poisson skipped: {e}")

rob_df = pd.DataFrame(rob_rows)
rob_df = rob_df.round({"beta": 4, "se": 4, "p": 4})
rob_df["sig"] = rob_df["p"].apply(sig_stars)
rob_df.to_csv(os.path.join(OUT_DIR, "heat_ops_robustness.csv"), index=False)
print("Robustness results saved.")

# ---------------------------------------------------------------------------
# 6. Moderation: AC type and security level interactions
# ---------------------------------------------------------------------------

print("\nRunning moderation regressions...")

mod_rows = []

# 6a. pct_mechanical interaction (continuous; ISP is time-varying 0→1 at 2024-03)
# Interpretation: heat × pct_mechanical < 0 means more mechanical AC attenuates heat slope.
for heat_var, heat_label in HEAT_VARS:
    for outcome, outcome_label in OUTCOMES:
        sub = df[["facility", "date", outcome, heat_var, "crowding_10pp",
                  "pct_mechanical"]].dropna()
        if sub.empty:
            continue
        sub["heat_x_pct_mech"] = sub[heat_var] * sub["pct_mechanical"]
        res = run_twfe(sub, outcome, heat_var,
                       extra_vars=["heat_x_pct_mech", "pct_mechanical"])
        coef = extract_coef(res, "heat_x_pct_mech")
        coef.update({
            "outcome": outcome_label, "heat": heat_label,
            "moderator": "Heat × % Mechanical AC",
            "type": "AC coverage"
        })
        mod_rows.append(coef)

# 6b. Security level interaction (heat × high_security)
for heat_var, heat_label in HEAT_VARS:
    for outcome, outcome_label in OUTCOMES:
        sub = df[["facility", "date", outcome, heat_var, "crowding_10pp",
                  "high_security"]].dropna()
        if sub.empty:
            continue
        sub["heat_x_highsec"] = sub[heat_var] * sub["high_security"]
        res = run_twfe(sub, outcome, heat_var, extra_vars=["heat_x_highsec"])
        coef = extract_coef(res, "heat_x_highsec")
        coef.update({
            "outcome": outcome_label, "heat": heat_label,
            "moderator": "Heat × High Security (Maximum)",
            "type": "Security level"
        })
        mod_rows.append(coef)

mod_df = pd.DataFrame(mod_rows)
if not mod_df.empty:
    mod_df = mod_df.round({"beta": 4, "se": 4, "p": 4})
    mod_df["sig"] = mod_df["p"].apply(sig_stars)
    mod_df.to_csv(os.path.join(OUT_DIR, "heat_ops_moderation.csv"), index=False)
    print("Moderation results saved.")
    for _, row in mod_df.iterrows():
        print(f"  {row.get('heat','')[:14]} | {row.get('moderator','')[:30]} | "
              f"{row.get('outcome','')[:25]}: β={row['beta']:.4f}, p={row['p']:.3f} {sig_stars(row['p'])}")

# ---------------------------------------------------------------------------
# 7. Panel summary table by heat quartile
# ---------------------------------------------------------------------------

print("\nBuilding panel summary table...")

# days_over_90f is 52% zeros (Oct-Mar months), so quartile bins degenerate.
# Use substantive bins instead: 0 days / 1-14 / 15-27 / 28-31.
df["heat_q"] = pd.cut(
    df["days_over_90f"],
    bins=[-0.001, 0, 14, 27, 31],
    labels=["0 days", "1–14 days", "15–27 days", "28–31 days"],
)

summary_rows = []
for q in ["0 days", "1–14 days", "15–27 days", "28–31 days"]:
    grp = df[df["heat_q"] == q]
    summary_rows.append({
        "Heat quartile": q,
        "N facility-months": len(grp),
        "Mean days >90°F": grp["days_over_90f"].mean(),
        "Mean ED/Hosp rate": grp["ed_hospital_rate"].mean(),
        "Mean Dental+MH OT": grp["dental_mh_overtime"].mean(),
        "Mean Mod Programs Days": grp["modified_programs_days"].mean(),
        "Mean Violent Incidents": grp["violent_incidents"].mean(),
        "Mean UOF Incidents": grp["uof_incidents"].mean(),
        "Mean Crowding (%)": grp["crowding_pct"].mean(),
    })

summary_df = pd.DataFrame(summary_rows).round(2)
summary_df.to_csv(os.path.join(OUT_DIR, "heat_ops_panel_summary.csv"), index=False)
print("Panel summary saved.")
print(summary_df.to_string(index=False))

# ---------------------------------------------------------------------------
# 8. Event study: ISP HVAC replacement (3/2024)
# ---------------------------------------------------------------------------

print("\nRunning ISP event study...")

# For each outcome, estimate heat coefficient separately for each event-time bin
# (relative months to treatment). Use all non-ISP facilities as control.
# Focus on ED rate (most complete; ISP has 95.9% coverage for ED).

isp_treat_date = pd.Timestamp("2024-03-01")
isp_df = df[df["facility"] == "ISP"].copy()
isp_df["event_month"] = ((isp_df["date"].dt.year - isp_treat_date.year) * 12 +
                          (isp_df["date"].dt.month - isp_treat_date.month))

# Event study: compare ISP before/after vs. control group
# For each pre/post window, estimate a simple DiD: ISP × Post indicator
# Rather than bin-by-bin (N=1 treated), do descriptive: ISP outcome residualized by
# facility+ym FEs, plotted over event time, with control group mean as reference.

# Step 1: partial out facility and year×month FEs from the full panel
def partial_out_fes(data, outcome, heat_var):
    """Demean by facility mean and ym mean (within transformation)."""
    sub = data[["facility", "ym", "date", outcome, heat_var, "crowding_10pp"]].dropna()
    sub["y_dm"] = (sub[outcome]
                   - sub.groupby("facility")[outcome].transform("mean")
                   - sub.groupby("ym")[outcome].transform("mean")
                   + sub[outcome].mean())
    sub["heat_dm"] = (sub[heat_var]
                      - sub.groupby("facility")[heat_var].transform("mean")
                      - sub.groupby("ym")[heat_var].transform("mean")
                      + sub[heat_var].mean())
    return sub

event_fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=False)
event_fig.suptitle(
    "ISP Full HVAC Replacement (Mar 2024): Outcomes Around Treatment\n"
    "(demeaned by facility + year×month FEs; shaded = post-treatment)",
    fontsize=10
)

for ax, (outcome, outcome_label) in zip(axes, OUTCOMES):
    sub = partial_out_fes(df, outcome, "days_over_90f")
    isp_sub = sub[sub["facility"] == "ISP"].copy()
    isp_sub["event_month"] = ((isp_sub["date"].dt.year - isp_treat_date.year) * 12 +
                               (isp_sub["date"].dt.month - isp_treat_date.month))
    # Plot ISP demeaned outcome over event time
    isp_plot = isp_sub[isp_sub["event_month"].between(-36, 24)].sort_values("event_month")
    ax.plot(isp_plot["event_month"], isp_plot["y_dm"],
            color="steelblue", linewidth=1.5, marker="o", markersize=3, label="ISP")
    ax.axvline(0, color="red", linestyle="--", linewidth=1, label="HVAC completion")
    ax.axhspan(0, ax.get_ylim()[1] if ax.get_ylim()[1] > 0 else 1,
               alpha=0.06, color="red")
    ax.axhline(0, color="gray", linewidth=0.7, linestyle=":")
    ax.set_title(outcome_label, fontsize=8)
    ax.set_xlabel("Months relative to HVAC completion", fontsize=7)
    ax.set_ylabel("Demeaned outcome", fontsize=7)
    ax.legend(fontsize=7)
    ax.tick_params(labelsize=7)

plt.tight_layout()
for ext in ("png", "svg"):
    path = os.path.join(OUT_DIR, f"heat_ops_event_study_isp.{ext}")
    event_fig.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved {path}")
plt.close()

# ---------------------------------------------------------------------------
# 9. Print formatted main results for Google Doc
# ---------------------------------------------------------------------------

print("\n" + "=" * 70)
print("MAIN RESULTS TABLE (for Google Doc)")
print("=" * 70)
print(f"{'Outcome':<38} {'Heat var':<22} {'β':>8} {'SE':>7} {'p':>7} {'BH-p':>7} {'Sig':>5} {'N':>6} {'Fac':>4}")
print("-" * 70)
for _, row in main_df.iterrows():
    print(f"{row['outcome']:<38} {row['heat']:<22} "
          f"{row['beta']:>8.4f} {row['se']:>7.4f} {row['p']:>7.4f} "
          f"{row['p_bh']:>7.4f} {row['sig_bh']:>5} {int(row['n_obs']):>6} {int(row['n_fac']):>4}")

print("\n" + "=" * 70)
print("ROBUSTNESS TABLE (lag 1)")
print("=" * 70)
lag1 = rob_df[rob_df.get("spec", pd.Series()).str.contains("Lag", na=False)] if "spec" in rob_df.columns else rob_df
print(f"{'Outcome':<38} {'Heat var':<22} {'β':>8} {'SE':>7} {'p':>7} {'Sig':>5} {'N':>6}")
print("-" * 70)
for _, row in rob_df.iterrows():
    print(f"{row['outcome']:<38} {row['heat']:<22} "
          f"{row['beta']:>8.4f} {row['se']:>7.4f} {row['p']:>7.4f} {sig_stars(row['p']):>5} {int(row['n_obs']):>6}")

print("\nDone. All outputs in:", OUT_DIR)
