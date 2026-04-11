#!/usr/bin/env python3
"""
Extract CDCR Restricted Housing (STA429) monthly PDFs into a long-format CSV.

Reads all STA429-MMDDYY-M.pdf files from:
  data_sources/facilities/CDCR/restricted_housing/

Extracts Table 2 (page 2): institution-level RH population, total population,
and % in RH for each month.

Filename convention: STA429-MMDDYY-M.pdf
  Publication date = MM/DD/YY
  Data as-of date  = last day of the prior month
  (e.g. STA429-030525-M.pdf published Mar 5 2025 → data as of Feb 28 2025)

Output: data_sources/facilities/CDCR/restricted_housing_2025.csv
  Columns: data_month, cdcr_code, rhu_population, total_population, pct_in_rhu
"""

import re
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
import pdfplumber

BASE = Path("data_sources/facilities/CDCR/restricted_housing")
OUT  = Path("data_sources/facilities/CDCR/restricted_housing_2025.csv")

# Rows to skip in Table 2 (not facility rows)
SKIP_ROWS = {"Other In-Custody Populations", "Total"}

# Regex to extract CDCR code from institution name like "Avenal State Prison (ASP)"
CODE_RE = re.compile(r'\(([A-Z]{2,5})\)\s*$')


def parse_pub_date(stem: str) -> date:
    """Parse publication date from filename stem like STA429-030525-M."""
    m = re.search(r'-(\d{6})-', stem)
    if not m:
        raise ValueError(f"Cannot parse date from {stem}")
    mmddyy = m.group(1)
    mm, dd, yy = int(mmddyy[:2]), int(mmddyy[2:4]), int(mmddyy[4:6])
    year = 2000 + yy
    return date(year, mm, dd)


def data_month_from_pub(pub: date) -> str:
    """Data is end of the month prior to publication date."""
    first_of_pub_month = pub.replace(day=1)
    last_of_prior = first_of_pub_month - timedelta(days=1)
    return last_of_prior.strftime("%Y-%m")


def extract_table2(pdf_path: Path) -> list[dict]:
    """Extract institution rows from Table 2 (page 2) of a STA429 PDF."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[1]  # page 2 (0-indexed)
        tables = page.extract_tables()
        if not tables:
            print(f"  WARNING: no tables found on page 2 of {pdf_path.name}")
            return rows

        # Table 2 is the first (usually only) table on page 2.
        # pdfplumber produces sparse rows: many None cells due to merged PDF headers,
        # and column alignment shifts between rows in some months.
        # Strategy: find the institution name cell anywhere in the row, then collect
        # the next 5 non-empty values as: RH Units, RH Pop, Total Pop, Pct, Staff Ratio.
        table = tables[0]

        for row in table:
            non_empty = [str(c).strip() for c in row if c and str(c).strip()]
            if not non_empty:
                continue

            # Find institution name: first cell matching CDCR code pattern
            institution = None
            name_pos = None
            for i, c in enumerate(non_empty):
                if CODE_RE.search(c):
                    institution = c
                    name_pos = i
                    break

            if institution is None:
                continue
            if any(skip in institution for skip in SKIP_ROWS):
                continue

            cdcr_code = CODE_RE.search(institution).group(1)

            # Values after the name: RH Units, RH Population, Total Population,
            # Percent in RH, Staff Ratio
            after = non_empty[name_pos + 1:]
            if len(after) < 4:
                print(f"  WARNING: too few values after name in {pdf_path.name}: {non_empty}")
                continue

            try:
                # after[0] = RH Units (skip), after[1] = RH Pop, after[2] = Total Pop,
                # after[3] = Pct in RH
                rhu_pop   = int(after[1].replace(",", ""))
                total_pop = int(after[2].replace(",", ""))
                pct_raw   = after[3].replace("%", "").strip()
                pct       = float(pct_raw) if pct_raw else None
            except (ValueError, IndexError):
                print(f"  WARNING: could not parse values in {pdf_path.name}: {after}")
                continue

            rows.append({
                "cdcr_code":       cdcr_code,
                "rhu_population":  rhu_pop,
                "total_population": total_pop,
                "pct_in_rhu":      pct,
            })

    return rows


def main():
    pdfs = sorted(BASE.glob("STA429-*-M.pdf"))
    if not pdfs:
        print(f"No PDFs found in {BASE}")
        return

    all_rows = []
    for pdf_path in pdfs:
        try:
            pub_date   = parse_pub_date(pdf_path.stem)
            data_month = data_month_from_pub(pub_date)
        except ValueError as e:
            print(f"Skipping {pdf_path.name}: {e}")
            continue

        print(f"{pdf_path.name}  →  data month: {data_month}")
        rows = extract_table2(pdf_path)
        for r in rows:
            r["data_month"] = data_month
        all_rows.extend(rows)

    if not all_rows:
        print("No rows extracted.")
        return

    df = pd.DataFrame(all_rows, columns=[
        "data_month", "cdcr_code", "rhu_population", "total_population", "pct_in_rhu"
    ])
    df = df.sort_values(["data_month", "cdcr_code"]).reset_index(drop=True)

    # ASP (Avenal State Prison) has 0 RH units and 0 RH population every month.
    # Its row name is dropped in the Apr 2025 PDF due to a rendering artifact.
    # Impute with 0 for that month so n_months=12.
    df_2025 = df[df["data_month"].str.startswith("2025")]
    asp_months = set(df_2025[df_2025["cdcr_code"] == "ASP"]["data_month"])
    all_2025_months = set(df_2025["data_month"].unique())
    for missing_month in sorted(all_2025_months - asp_months):
        print(f"  Imputing ASP {missing_month} = 0 (0 RH units, rendering artifact)")
        df = pd.concat([df, pd.DataFrame([{
            "data_month": missing_month,
            "cdcr_code": "ASP",
            "rhu_population": 0,
            "total_population": None,
            "pct_in_rhu": 0.0,
        }])], ignore_index=True)
    df = df.sort_values(["data_month", "cdcr_code"]).reset_index(drop=True)

    df.to_csv(OUT, index=False)
    print(f"\nWrote {len(df)} rows → {OUT}")

    # Summary: 2025 months available per facility
    df_2025 = df[df["data_month"].str.startswith("2025")]
    months_available = df_2025["data_month"].nunique()
    print(f"\n2025 months available: {sorted(df_2025['data_month'].unique())}")
    print(f"Facilities with data: {df_2025['cdcr_code'].nunique()}")
    print(f"\n2025 annual average % in RH by facility:")
    avg = (df_2025.groupby("cdcr_code")["pct_in_rhu"]
           .agg(["mean", "count"])
           .rename(columns={"mean": "avg_pct_in_rhu_2025", "count": "n_months"})
           .sort_values("avg_pct_in_rhu_2025", ascending=False))
    print(avg.to_string())


if __name__ == "__main__":
    main()
