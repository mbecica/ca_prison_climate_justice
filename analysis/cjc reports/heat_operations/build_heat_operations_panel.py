"""
build_heat_operations_panel.py

Builds a facility x calendar-month panel joining:
  - Heat exposure (days_over_90f, days_over_95f, days_skarha10) from gridMET daily data
  - Outcomes from sb601_operations (Dental+MH Overtime, Modified Programs Days,
    Actual Expenditures (monthly, differenced from YTD), Institution Budget)
  - Outcomes from cchcs_measures (ED/Hospital Stay rate, staffing vacancies)
  - Crowding ratio from tpop1_institutions (time-varying control)
  - Static covariates: AC type, security level
  - AC event study indicator (ISP 3/2024, CIM 2/2025)

Output: analysis/cjc reports/heat_operations_panel.csv

Notes:
  - sb601 covers all 12 months/year (Jul-Jun); May-Jun were added in scraper v2
  - sb601 facility coverage is unbalanced: 26/13/19/17 facilities across FY2021-2025
    This reflects which facilities had reportable conditions, not data collection gaps.
    Flag as limitation in methods.
  - Actual Expenditures are reported YTD; differenced within fiscal year to get monthly spend.
    July = YTD value (= monthly). Aug+ = current month YTD minus prior month YTD.
  - Universe = facilities in heat data (gridMET coverage), 34 facilities 2016-2025
  - DVI and CCC excluded: both closed during study period, no heat data
"""

import csv
import os
import re
from datetime import datetime
from collections import defaultdict

DATA = "data_sources"
OUT_DIR = "analysis/cjc reports/heat_operations"

EXCLUDE_FACILITIES = {"DVI", "CCC"}

# ---------------------------------------------------------------------------
# Step 1: Aggregate daily heat to monthly
#   Input: heat_activations_daily.csv
#   Columns: cdcr_code, date, tmax_f, over_90f, over_95f, skarha10
# ---------------------------------------------------------------------------

print("Step 1: Aggregating daily heat to monthly...")

heat_monthly = defaultdict(lambda: {"days_over_90f": 0, "days_over_95f": 0, "days_skarha10": 0})

with open(f"{DATA}/hazards/heat/heat_activations_daily.csv") as f:
    for row in csv.DictReader(f):
        facility = row["cdcr_code"]
        d = datetime.strptime(row["date"], "%Y-%m-%d")
        key = (facility, d.year, d.month)
        heat_monthly[key]["days_over_90f"] += int(row["over_90f"])
        heat_monthly[key]["days_over_95f"] += int(row["over_95f"])
        heat_monthly[key]["days_skarha10"] += int(row["skarha10"])

print(f"  {len(heat_monthly)} facility-month heat records")

# ---------------------------------------------------------------------------
# Step 2: Reshape sb601 fiscal-year wide → calendar month long
#   Fiscal year "2021-2022": Jul=2021-07 ... Dec=2021-12, Jan=2022-01 ... Apr=2022-04
#   May and Jun are absent from SB 601 reporting entirely.
# ---------------------------------------------------------------------------

print("Step 2: Reshaping sb601 fiscal-year wide -> calendar month long...")

MONTH_MAP = {
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
}

SB601_OUTCOMES = {
    ("Overtime Hours", "Dental + Mental Health (Overtime)"): "dental_mh_overtime",
    ("Lockdowns and Modified Programs", "Incarcerated Persons-Days on Modified Programs"): "modified_programs_days",
    ("Number of Deaths", "Unexpected"): "deaths_unexpected",
    ("Use of Force (UOF)", "Total UOF Incidents"): "uof_incidents",
}

sb601 = defaultdict(dict)  # (facility, year, month) -> {col: value}

with open(f"{DATA}/facilities/CDCR/sb601_operations_2021-2025.csv") as f:
    for row in csv.DictReader(f):
        facility = row["institution"]
        if facility in EXCLUDE_FACILITIES:
            continue
        fy = row["fiscal_year"]
        fy_start = int(fy.split("-")[0])
        fy_end = int(fy.split("-")[1])

        col_key = (row["category"], row["metric"])
        if col_key not in SB601_OUTCOMES:
            continue
        col_name = SB601_OUTCOMES[col_key]

        for month_abbr, month_num in MONTH_MAP.items():
            raw = row.get(month_abbr, "").replace(",", "").strip()
            if not raw:
                continue
            try:
                val = float(raw)
            except ValueError:
                continue
            cal_year = fy_start if month_num >= 7 else fy_end
            key = (facility, cal_year, month_num)
            sb601[key][col_name] = val

print(f"  {len(sb601)} facility-month sb601 records")

# ---------------------------------------------------------------------------
# Step 2b: Process fiscal data (Actual Expenditures YTD → monthly; Institution Budget)
#   Actual Expenditures are cumulative YTD within each fiscal year.
#   Monthly spend = current month YTD − previous month YTD (July = YTD = monthly).
#   Institution Budget is the current authorized annual budget (revised by amendments).
# ---------------------------------------------------------------------------

print("Step 2b: Processing fiscal data...")

# Fiscal month sequence within a fiscal year (Jul=first, Jun=last)
FISCAL_MONTH_SEQ = ["Jul","Aug","Sep","Oct","Nov","Dec","Jan","Feb","Mar","Apr","May","Jun"]

# Raw YTD values keyed by (facility, fiscal_year_str, month_abbr)
ytd_actual = {}
budget_raw = {}

with open(f"{DATA}/facilities/CDCR/sb601_operations_2021-2025.csv") as f:
    for row in csv.DictReader(f):
        facility = row["institution"]
        if facility in EXCLUDE_FACILITIES:
            continue
        if row["category"] != "Fiscal":
            continue
        if row["metric"] not in ("Actual Expenditures ($)", "Institution Budget ($)"):
            continue
        fy = row["fiscal_year"]
        for m_abbr in FISCAL_MONTH_SEQ:
            raw = row.get(m_abbr, "").replace(",", "").strip()
            if not raw:
                continue
            try:
                val = float(raw)
            except ValueError:
                continue
            store = ytd_actual if row["metric"] == "Actual Expenditures ($)" else budget_raw
            store[(facility, fy, m_abbr)] = val

# Difference YTD actuals to get monthly spend; store budget as-is
fiscal = defaultdict(dict)  # (facility, cal_year, cal_month) -> {actual_expenditure_monthly, institution_budget}

for (facility, fy, m_abbr), ytd in ytd_actual.items():
    fy_start = int(fy.split("-")[0])
    m_num = MONTH_MAP[m_abbr]
    cal_year = fy_start if m_num >= 7 else int(fy.split("-")[1])
    idx = FISCAL_MONTH_SEQ.index(m_abbr)
    if idx == 0:
        monthly_spend = ytd  # July: first month, YTD = monthly
    else:
        prev_ytd = ytd_actual.get((facility, fy, FISCAL_MONTH_SEQ[idx - 1]))
        monthly_spend = (ytd - prev_ytd) if prev_ytd is not None else None
    if monthly_spend is not None:
        fiscal[(facility, cal_year, m_num)]["actual_expenditure_monthly"] = monthly_spend

for (facility, fy, m_abbr), val in budget_raw.items():
    fy_start = int(fy.split("-")[0])
    m_num = MONTH_MAP[m_abbr]
    cal_year = fy_start if m_num >= 7 else int(fy.split("-")[1])
    fiscal[(facility, cal_year, m_num)]["institution_budget"] = val

print(f"  {len(fiscal)} facility-month fiscal records")

# Report coverage by FY for documentation
print("  sb601 coverage note (Dental+MH OT metric, for reference):")
fy_coverage = defaultdict(set)
with open(f"{DATA}/facilities/CDCR/sb601_operations_2021-2025.csv") as f:
    for row in csv.DictReader(f):
        if (row["category"], row["metric"]) == ("Overtime Hours", "Dental + Mental Health (Overtime)"):
            fy_coverage[row["fiscal_year"]].add(row["institution"])
for fy in sorted(fy_coverage):
    print(f"    {fy}: {len(fy_coverage[fy])} facilities")

# ---------------------------------------------------------------------------
# Step 3: Load cchcs_measures
#   - ED/Hospital Stay rate (Other Trends, "ED/Hospital Stay*") -> ed_hospital_rate
#   - Staffing vacancies
#   FSP in cchcs = FOL in heat data
# ---------------------------------------------------------------------------

print("Step 3: Loading CCHCS measures...")

CCHCS_RECODE = {"FSP": "FOL"}

CCHCS_OUTCOMES = {
    ("Other Trends", "ED/Hospital Stay*"): "ed_hospital_rate",
    ("Staffing", "Actual Vacancies (All)"): "vacancy_all",
    ("Staffing", "Medical Vacancies (All)"): "vacancy_medical",
    ("Staffing", "Dental Vacancies (All)"): "vacancy_dental",
    ("Staffing", "Mental Health Vacancies (All)"): "vacancy_mh",
}

cchcs = defaultdict(dict)  # (facility, year, month) -> {col: value}

with open(f"{DATA}/facilities/CDCR/cchcs_measures_2017-2025.csv") as f:
    for row in csv.DictReader(f):
        facility = CCHCS_RECODE.get(row["institution"], row["institution"])
        if facility in EXCLUDE_FACILITIES or facility == "SW":
            continue
        col_key = (row["group"], row["measure"])
        if col_key not in CCHCS_OUTCOMES:
            continue
        col_name = CCHCS_OUTCOMES[col_key]
        try:
            dt = datetime.strptime(row["month"], "%b %Y")
        except ValueError:
            continue
        raw = row["value"].replace("%", "").replace("$", "").replace(",", "").strip()
        try:
            val = float(raw)
        except ValueError:
            continue
        cchcs[(facility, dt.year, dt.month)][col_name] = val

print(f"  {len(cchcs)} facility-month CCHCS records")

# ---------------------------------------------------------------------------
# Step 4: Load crowding ratio from tpop1_institutions
#   report_date is end-of-month; match to (year, month) of that date
# ---------------------------------------------------------------------------

print("Step 4: Loading crowding ratio from tpop1...")

crowding = {}  # (facility, year, month) -> pct_occupied

with open(f"{DATA}/facilities/CDCR/tpop1_institutions.csv") as f:
    for row in csv.DictReader(f):
        facility = row["cdcr_code"]
        if facility in EXCLUDE_FACILITIES:
            continue
        try:
            d = datetime.strptime(row["report_date"], "%Y-%m-%d")
            pct = float(row["pct_occupied"])
        except (ValueError, KeyError):
            continue
        crowding[(facility, d.year, d.month)] = pct

print(f"  {len(crowding)} facility-month crowding records")

# ---------------------------------------------------------------------------
# Step 5: Load static covariates
#   AC type: dominant cooling category per facility
#   Security level: extracted from ca_facilities.csv name field
# ---------------------------------------------------------------------------

print("Step 5: Loading static covariates...")

# AC type
ac_type = {}

with open(f"{DATA}/facilities/CDCR/air_cooling_infrastructure_dec2025.csv") as f:
    for row in csv.DictReader(f):
        facility = row["institution"]
        try:
            mechanical = int(row["hu_mechanical_cooling"])
            evaporative = int(row["hu_evaporative_cooling"])
            air_handlers = int(row["hu_air_handlers_only"])
            total = mechanical + evaporative + air_handlers
        except (ValueError, KeyError):
            continue
        if total == 0:
            ac_type[facility] = "unknown"
        elif mechanical == total:
            ac_type[facility] = "mechanical"
        elif evaporative == total:
            ac_type[facility] = "evaporative"
        elif air_handlers == total:
            ac_type[facility] = "ventilation_only"
        else:
            dominant = max(
                [("mechanical", mechanical), ("evaporative", evaporative), ("ventilation_only", air_handlers)],
                key=lambda x: x[1]
            )[0]
            ac_type[facility] = f"mixed_{dominant}"

# Security level: extract cdcr code from parentheses in facility name
# e.g. "Calipatria State Prison (Cal)" -> "CAL" -> MAXIMUM
SECURELVL_RECODE = {"CCFW": "CCWF", "FSP": "FOL"}

security_level = {}

with open(f"{DATA}/facilities/ca_facilities.csv") as f:
    for row in csv.DictReader(f):
        if row.get("type") != "STATE":
            continue
        securelvl = row.get("securelvl", "").strip()
        if not securelvl or securelvl in ("NOT AVAILABLE", "JUVENILE"):
            continue
        name = row.get("name", "")
        m = re.search(r"\(([A-Za-z]{2,6})\)", name)
        if m:
            code = SECURELVL_RECODE.get(m.group(1).upper(), m.group(1).upper())
            security_level[code] = securelvl

# Avenal SP (ASP) has no parenthesized code in ca_facilities
security_level["ASP"] = "MEDIUM"

print(f"  AC type coverage: {len(ac_type)} facilities")
print(f"  Security level coverage: {len(security_level)} facilities")
print(f"  Security levels assigned: {sorted(security_level.items())}")

# ---------------------------------------------------------------------------
# Step 6: AC event study indicator
#   ISP: post_ac = 1 from 2024-03 onward (full HVAC, P-0910-01113)
#   CIM: post_ac = 1 from 2025-02 onward (Air Cooling Facility A, P-1718-00132)
# ---------------------------------------------------------------------------

AC_EVENTS = {
    "ISP": (2024, 3),
    "CIM": (2025, 2),
}

def get_post_ac(facility, year, month):
    if facility not in AC_EVENTS:
        return 0
    event_year, event_month = AC_EVENTS[facility]
    return 1 if (year, month) >= (event_year, event_month) else 0

# ---------------------------------------------------------------------------
# Step 7: Build master panel
#   Universe: all (facility, year, month) in heat data
# ---------------------------------------------------------------------------

print("Step 7: Building master panel...")

all_keys = sorted(heat_monthly.keys())

COLUMNS = [
    "facility", "year", "month",
    "days_over_90f", "days_over_95f", "days_skarha10",
    "dental_mh_overtime", "modified_programs_days", "deaths_unexpected",
    "uof_incidents",
    "ed_hospital_rate",
    "actual_expenditure_monthly", "institution_budget",
    "vacancy_all", "vacancy_medical", "vacancy_dental", "vacancy_mh",
    "crowding_pct",
    "ac_type", "security_level",
    "post_ac",
]

rows_out = []
missing_counts = defaultdict(int)

for facility, year, month in all_keys:
    row = {"facility": facility, "year": year, "month": month}

    h = heat_monthly[(facility, year, month)]
    row["days_over_90f"] = h["days_over_90f"]
    row["days_over_95f"] = h["days_over_95f"]
    row["days_skarha10"] = h["days_skarha10"]

    sb = sb601.get((facility, year, month), {})
    for col in ("dental_mh_overtime", "modified_programs_days", "deaths_unexpected", "uof_incidents"):
        val = sb.get(col, "")
        row[col] = val
        if val == "":
            missing_counts[col] += 1

    fc = fiscal.get((facility, year, month), {})
    for col in ("actual_expenditure_monthly", "institution_budget"):
        val = fc.get(col, "")
        row[col] = val
        if val == "":
            missing_counts[col] += 1

    cc = cchcs.get((facility, year, month), {})
    for col in ("ed_hospital_rate", "vacancy_all", "vacancy_medical", "vacancy_dental", "vacancy_mh"):
        val = cc.get(col, "")
        row[col] = val
        if val == "":
            missing_counts[col] += 1

    row["crowding_pct"] = crowding.get((facility, year, month), "")
    if row["crowding_pct"] == "":
        missing_counts["crowding_pct"] += 1

    row["ac_type"] = ac_type.get(facility, "")
    row["security_level"] = security_level.get(facility, "")
    row["post_ac"] = get_post_ac(facility, year, month)

    rows_out.append(row)

print(f"  Total panel rows: {len(rows_out)}")
print(f"  Missing value counts (structural gaps expected for pre-2021 sb601):")
for col, n in sorted(missing_counts.items()):
    pct = 100 * n / len(rows_out)
    print(f"    {col}: {n} ({pct:.1f}%)")

# ---------------------------------------------------------------------------
# Step 8: Write output
# ---------------------------------------------------------------------------

out_path = os.path.join(OUT_DIR, "heat_operations_panel.csv")
print(f"\nStep 8: Writing to {out_path}...")

with open(out_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(rows_out)

print(f"Done. {len(rows_out)} rows x {len(COLUMNS)} columns")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

print("\n--- Panel summary ---")
facilities = sorted(set(r["facility"] for r in rows_out))
years = sorted(set(r["year"] for r in rows_out))
print(f"Facilities: {len(facilities)}")
print(f"Years: {min(years)}-{max(years)}")

# Coverage within the sb601 window (2021-07 onward) for sb601 outcomes
sb601_window = [r for r in rows_out if (r["year"], r["month"]) >= (2021, 7)]
sb601_with_data = [r for r in sb601_window if r["dental_mh_overtime"] != ""]
print(f"\nSb601 window rows (Jul 2021+): {len(sb601_window)}")
print(f"  With dental_mh_overtime: {len(sb601_with_data)} ({100*len(sb601_with_data)/len(sb601_window):.1f}%)")

# Coverage for CCHCS ED outcome (Apr 2017+)
cchcs_window = [r for r in rows_out if (r["year"], r["month"]) >= (2017, 4)]
cchcs_with_ed = [r for r in cchcs_window if r["ed_hospital_rate"] != ""]
print(f"\nCCHCS window rows (Apr 2017+): {len(cchcs_window)}")
print(f"  With ed_hospital_rate: {len(cchcs_with_ed)} ({100*len(cchcs_with_ed)/len(cchcs_window):.1f}%)")

# Rows with all 3 primary outcomes
complete = [r for r in rows_out if all(r[c] != "" for c in ("dental_mh_overtime", "modified_programs_days", "ed_hospital_rate"))]
print(f"\nRows with all 3 primary outcomes: {len(complete)}")
if complete:
    fac_set = set(r["facility"] for r in complete)
    yr_set = sorted(set((r["year"], r["month"]) for r in complete))
    print(f"  Facilities: {len(fac_set)}")
    print(f"  Date range: {yr_set[0]} to {yr_set[-1]}")

# Event study counts
for fac, (ey, em) in AC_EVENTS.items():
    pre = [r for r in rows_out if r["facility"] == fac and (r["year"], r["month"]) < (ey, em)]
    post = [r for r in rows_out if r["facility"] == fac and (r["year"], r["month"]) >= (ey, em)]
    print(f"\n{fac} event study: {len(pre)} pre-treatment months, {len(post)} post-treatment months")
