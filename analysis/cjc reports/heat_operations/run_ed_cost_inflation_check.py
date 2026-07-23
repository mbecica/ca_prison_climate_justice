"""
run_ed_cost_inflation_check.py

Robustness check: deflate ed_hospital_cost and total_labor_cost to 2024 dollars
using BLS medical care CPI (CUUR0000SAM / FRED CPIMEDSL), then rerun the ISP DiD.

Base period: 2024 annual average CPI (mean of 12 monthly values).
October 2025 is missing from the CPI series; rows for that month are dropped.

Output: printed table only (no CSV written — exploratory check).
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import os

from linearmodels.panel import PanelOLS

OUT_DIR = "analysis/cjc reports/heat_operations"

# ---------------------------------------------------------------------------
# 1. Medical care CPI (CPIMEDSL), Jan 2016 – Dec 2025, Oct 2025 missing
# ---------------------------------------------------------------------------

MEDICAL_CPI = {
    (2016,1):454.194,(2016,2):456.922,(2016,3):457.723,(2016,4):459.245,
    (2016,5):460.487,(2016,6):462.090,(2016,7):464.439,(2016,8):469.020,
    (2016,9):469.816,(2016,10):469.749,(2016,11):469.914,(2016,12):470.539,
    (2017,1):471.484,(2017,2):473.139,(2017,3):473.685,(2017,4):473.007,
    (2017,5):472.981,(2017,6):474.492,(2017,7):476.279,(2017,8):477.199,
    (2017,9):477.190,(2017,10):477.671,(2017,11):477.791,(2017,12):478.891,
    (2018,1):480.797,(2018,2):481.600,(2018,3):483.078,(2018,4):483.577,
    (2018,5):484.543,(2018,6):486.209,(2018,7):485.246,(2018,8):484.273,
    (2018,9):485.039,(2018,10):485.652,(2018,11):487.615,(2018,12):488.820,
    (2019,1):489.968,(2019,2):490.160,(2019,3):491.412,(2019,4):492.970,
    (2019,5):494.859,(2019,6):495.745,(2019,7):497.714,(2019,8):500.662,
    (2019,9):501.710,(2019,10):506.433,(2019,11):508.315,(2019,12):510.875,
    (2020,1):511.854,(2020,2):512.967,(2020,3):514.743,(2020,4):516.770,
    (2020,5):519.152,(2020,6):520.867,(2020,7):522.675,(2020,8):522.922,
    (2020,9):522.947,(2020,10):520.943,(2020,11):520.567,(2020,12):519.866,
    (2021,1):521.832,(2021,2):523.675,(2021,3):524.024,(2021,4):524.465,
    (2021,5):523.970,(2021,6):523.099,(2021,7):524.307,(2021,8):524.693,
    (2021,9):524.874,(2021,10):527.649,(2021,11):529.542,(2021,12):531.045,
    (2022,1):534.695,(2022,2):536.583,(2022,3):539.050,(2022,4):541.376,
    (2022,5):543.544,(2022,6):546.741,(2022,7):549.846,(2022,8):552.902,
    (2022,9):556.309,(2022,10):554.065,(2022,11):551.498,(2022,12):552.002,
    (2023,1):550.992,(2023,2):549.313,(2023,3):547.138,(2023,4):546.990,
    (2023,5):547.446,(2023,6):547.299,(2023,7):547.141,(2023,8):547.687,
    (2023,9):548.398,(2023,10):549.793,(2023,11):552.420,(2023,12):554.406,
    (2024,1):556.741,(2024,2):557.163,(2024,3):559.269,(2024,4):561.275,
    (2024,5):564.191,(2024,6):564.997,(2024,7):564.593,(2024,8):564.183,
    (2024,9):566.256,(2024,10):567.974,(2024,11):569.476,(2024,12):570.110,
    (2025,1):571.366,(2025,2):573.284,(2025,3):574.069,(2025,4):576.548,
    (2025,5):578.073,(2025,6):580.527,(2025,7):584.450,(2025,8):583.809,
    (2025,9):584.872,
    # (2025,10): not yet released — rows dropped below
    (2025,11):585.987,(2025,12):588.092,
}

# 2024 base: annual average
cpi_2024_base = np.mean([MEDICAL_CPI[(2024, m)] for m in range(1, 13)])
print(f"2024 medical CPI base (annual avg): {cpi_2024_base:.3f}")

# ---------------------------------------------------------------------------
# 2. Load panel and deflate
# ---------------------------------------------------------------------------

print("Loading panel...")
df = pd.read_csv(os.path.join(OUT_DIR, "heat_operations_panel.csv"))

for col in ["gridmet_days_over_90f", "ed_hospital_cost", "total_labor_cost", "crowding_pct"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1))
df["crowding_10pp"] = df["crowding_pct"] / 10

# Map CPI; rows with no CPI (Oct 2025) become NaN and drop in regression
df["cpi"] = df.apply(lambda r: MEDICAL_CPI.get((int(r["year"]), int(r["month"])), np.nan), axis=1)
df["ed_cost_real"]      = df["ed_hospital_cost"] * (cpi_2024_base / df["cpi"])
df["labor_cost_real"]   = df["total_labor_cost"]  * (cpi_2024_base / df["cpi"])
df["log_ed_cost_real"]    = np.log1p(df["ed_cost_real"].clip(lower=0))
df["log_ed_cost_nom"]     = np.log1p(df["ed_hospital_cost"].clip(lower=0))
df["log_labor_cost_real"] = np.log1p(df["labor_cost_real"].clip(lower=0))
df["log_labor_cost_nom"]  = np.log1p(df["total_labor_cost"].clip(lower=0))

n_missing_cpi = df["cpi"].isna().sum()
print(f"Rows dropped for missing CPI (Oct 2025): {n_missing_cpi}")
print(f"Non-null real cost rows: {df['log_ed_cost_real'].notna().sum()}")

# ---------------------------------------------------------------------------
# 3. ISP DiD helper
# ---------------------------------------------------------------------------

ISP_TREAT = pd.Timestamp("2024-03-01")

def run_did(df, outcome, label):
    sub = df.copy()
    sub["post_treat"]  = ((sub["facility"] == "ISP") & (sub["date"] >= ISP_TREAT)).astype(float)
    sub["heat_x_post"] = sub["gridmet_days_over_90f"] * sub["post_treat"]

    cols = [outcome, "gridmet_days_over_90f", "heat_x_post", "post_treat", "crowding_10pp"]
    sub = sub[["facility", "date"] + cols].dropna(subset=cols)
    sub = sub.set_index(["facility", "date"])

    mod = PanelOLS(
        dependent=sub[outcome],
        exog=sub[["gridmet_days_over_90f", "heat_x_post", "post_treat", "crowding_10pp"]],
        entity_effects=True,
        time_effects=True,
        check_rank=False,
    )
    res = mod.fit(cov_type="clustered", cluster_entity=True)

    def stars(p):
        if p < 0.001: return "***"
        if p < 0.01:  return "**"
        if p < 0.05:  return "*"
        if p < 0.1:   return "."
        return ""

    b_heat = res.params["gridmet_days_over_90f"]
    b_ix   = res.params["heat_x_post"]
    p_ix   = res.pvalues["heat_x_post"]
    se_ix  = res.std_errors["heat_x_post"]
    print(f"  {label:<35} heat β={b_heat:+.4f}  heat×post β={b_ix:+.4f}  SE={se_ix:.4f}  p={p_ix:.3f}{stars(p_ix)}  N={int(res.nobs)}")

# ---------------------------------------------------------------------------
# 4. Compare nominal vs. real
# ---------------------------------------------------------------------------

print("\nISP DiD — ED & Hospital Stay Cost (nominal vs. 2024-deflated)")
print("-" * 75)
run_did(df, "log_ed_cost_nom",  "Nominal (log)")
run_did(df, "log_ed_cost_real", "Real 2024$ (log)")

print("\nISP DiD — Total Labor Cost (nominal vs. 2024-deflated)")
print("-" * 75)
run_did(df, "log_labor_cost_nom",  "Nominal (log)")
run_did(df, "log_labor_cost_real", "Real 2024$ (log)")

print()
print("Note: deflator = BLS medical care CPI (CPIMEDSL). Base = 2024 annual avg.")
