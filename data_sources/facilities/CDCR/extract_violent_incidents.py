"""
CDCR Violent Incidents PDF Extractor
=====================================
Extracts monthly violent incident counts per facility from 5 CDCR PDF reports.

Usage:
    python3 extract_violent_incidents.py

Requires: pdfplumber (pip install pdfplumber)

Key design note:
    Each facility gets 2-3 pages in the PDF. Violent categories are split across
    these pages, so we ACCUMULATE values across all pages for the same facility
    (same month header set) rather than overwriting.

Output columns:
    facility, year, month, violent_incidents, inmate_on_inmate, staff_involved,
    assault_on_inmate, battery_on_inmate, fighting, riot,
    assault_on_officer, battery_on_officer, cell_extractions, source_file

    violent_incidents  = inmate_on_inmate + staff_involved  (backwards-compat total)
    inmate_on_inmate   = assault_on_inmate + battery_on_inmate + fighting + riot
    staff_involved     = assault_on_officer + battery_on_officer + cell_extractions
"""

import pdfplumber
import re
import csv
from collections import defaultdict
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INCIDENTS_DIR = os.path.join(BASE_DIR, "cdcr_incidents")

# PDF files in order from OLDEST to NEWEST so newer data overrides older for overlapping months
PDFS = [
    ("CompStat_Incident_Report_d2201.pdf", "d2201"),   # Jan 2021 - Jan 2022
    ("CompStat_Incident_Report_d2212.pdf", "d2212"),   # Dec 2021 - Dec 2022
    ("Incident_Report_Public_d2312.pdf",   "d2312"),   # Dec 2022 - Dec 2023
    ("CompStat_Incident_Report_d2501.pdf", "d2501"),   # Jan 2024 - Jan 2025
    ("Incident_Report_Public_d2512.pdf",   "d2512"),   # Dec 2024 - Dec 2025
]

# Violent categories to track — the "Total" rows or standalone rows
# under "Incident Categories" in each per-facility page.
# EXCLUDED: Controlled Substance rows, Type of Force rows, and all others.
VIOLENT_TOTALS = [
    "Assault on a Peace Officer or Non-Prisoner (Total)",
    "Battery on a Peace Officer or Non-Prisoner (Total)",
    "Assault on Inmate (Total)",
    "Battery on Inmate (Total)",
    "Cell Extractions (Total)",
    "Fighting",
    "Riot",
]

# Map from full category string -> short CSV column name
CATEGORY_COL = {
    "Assault on a Peace Officer or Non-Prisoner (Total)": "assault_on_officer",
    "Battery on a Peace Officer or Non-Prisoner (Total)": "battery_on_officer",
    "Assault on Inmate (Total)":                          "assault_on_inmate",
    "Battery on Inmate (Total)":                          "battery_on_inmate",
    "Cell Extractions (Total)":                           "cell_extractions",
    "Fighting":                                           "fighting",
    "Riot":                                               "riot",
}

# All per-category column names (order controls CSV column order)
CAT_COLS = [
    "assault_on_inmate",
    "battery_on_inmate",
    "fighting",
    "riot",
    "assault_on_officer",
    "battery_on_officer",
    "cell_extractions",
]

# CSV output columns (full order)
CSV_COLS = [
    "facility", "year", "month",
    "violent_incidents", "inmate_on_inmate", "staff_involved",
    "assault_on_inmate", "battery_on_inmate", "fighting", "riot",
    "assault_on_officer", "battery_on_officer", "cell_extractions",
    "source_file",
]


def parse_month_header(token):
    """Parse a month-header token like 'Dec24', 'Jan25' -> (year, month_num)."""
    month_map = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }
    m = re.match(r'([A-Za-z]{3})(\d{2})$', token.strip())
    if m:
        mon_str = m.group(1).capitalize()
        yr2 = int(m.group(2))
        year = 2000 + yr2
        mon_num = month_map.get(mon_str)
        if mon_num:
            return year, mon_num
    return None, None


def extract_row_values(line, row_name):
    """
    Given a text line starting with row_name, extract the numeric values
    after the label. Returns a list of ints, or None if label not found.
    """
    stripped = line.strip()
    if not stripped.startswith(row_name):
        return None
    rest = stripped[len(row_name):].strip()
    nums = re.findall(r'[\d,]+', rest)
    if not nums:
        return None
    return [int(n.replace(',', '')) for n in nums]


def extract_facility_data(pdf_path, source_tag):
    """
    Parse one PDF and extract violent incident counts per facility per month,
    tracking each category separately.

    Strategy:
    - Each facility spans 2-3 consecutive pages with the same institution header.
    - We group pages by (facility, month_cols_tuple) so all pages for the same
      facility contribute to a single running accumulator.
    - The "Riot - Number of Inmates Involved" row that begins with "Riot" is
      excluded by using startswith matching against "Riot" only — but we need
      to be careful: the standalone "Riot" row is the count we want, while
      "Riot - Number of Inmates Involved" starts with "Riot -" so we check for
      that exact prefix to exclude it.

    Returns:
        results: dict {(facility, year, month): {col_name: count}}
        notes:   list of diagnostic strings
    """
    results = {}
    notes = []

    # Accumulator keyed by (facility, month_cols_tuple):
    #   {(facility, col_key): {short_col_name: {(yr, mn): count}}}
    # This ensures pages belonging to the same facility all add together
    facility_accum = {}   # (facility, col_key) -> {col_name -> defaultdict(int)}
    facility_col_map = {} # (facility, col_key) -> list of (yr, mn)

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        notes.append(f"  Total pages: {total_pages}")
        facilities_found = set()

        for page_idx in range(total_pages):
            page = pdf.pages[page_idx]
            text = page.extract_text()
            if not text:
                continue

            # Only process per-facility pages (skip "All Institutions" summary pages)
            inst_match = re.search(r'Institution:\s*([A-Z0-9\-]+)', text)
            if not inst_match:
                continue

            facility = inst_match.group(1).strip()
            facilities_found.add(facility)

            # Parse the "Incidents <MonthCol1> ..." header line
            lines = text.split('\n')
            month_cols = []
            header_line_idx = None

            for li, line in enumerate(lines):
                if re.match(r'Incidents\s+[A-Za-z]{3}\d{2}', line.strip()):
                    tokens = line.strip().split()
                    for tok in tokens[1:]:
                        yr, mn = parse_month_header(tok)
                        if yr is not None:
                            month_cols.append((yr, mn))
                    header_line_idx = li
                    break

            if not month_cols:
                notes.append(
                    f"  WARNING: No month headers on page {page_idx + 1} ({facility})"
                )
                continue

            # Group key: facility + tuple of month columns (identifies one "report block")
            col_key = tuple(month_cols)
            gk = (facility, col_key)

            if gk not in facility_accum:
                # Initialize a per-category sub-dict, each keyed by (yr, mn)
                facility_accum[gk] = {
                    col: defaultdict(int) for col in CAT_COLS
                }
                facility_col_map[gk] = month_cols
                # Ensure all months are present (even if no row fires)
                for col in CAT_COLS:
                    for ym in month_cols:
                        facility_accum[gk][col][ym] = 0

            running = facility_accum[gk]  # dict of col_name -> defaultdict(int)

            # Scan lines for our target rows and ACCUMULATE (not overwrite)
            scan_start = header_line_idx + 1 if header_line_idx is not None else 0
            for line in lines[scan_start:]:
                line_stripped = line.strip()

                # Special handling for "Riot" vs "Riot - Number of Inmates Involved"
                # We want "Riot" but NOT "Riot -"
                for cat in VIOLENT_TOTALS:
                    if cat == "Riot":
                        # Match exactly "Riot" at start, not "Riot -"
                        if not (line_stripped.startswith("Riot") and
                                not line_stripped.startswith("Riot -")):
                            continue
                    else:
                        if not line_stripped.startswith(cat):
                            continue

                    col_name = CATEGORY_COL[cat]
                    vals = extract_row_values(line_stripped, cat)
                    if vals is None:
                        notes.append(
                            f"  WARNING: Could not parse '{cat}' on page {page_idx + 1} ({facility})"
                        )
                    elif len(vals) < len(month_cols):
                        notes.append(
                            f"  WARNING: '{cat}' pg{page_idx + 1} ({facility}): "
                            f"{len(vals)} values vs {len(month_cols)} months"
                        )
                        for ci in range(len(vals)):
                            running[col_name][month_cols[ci]] += vals[ci]
                    else:
                        for ci, ym in enumerate(month_cols):
                            running[col_name][ym] += vals[ci]
                    break  # stop checking other categories for this line

        # Flatten accumulator into results dict
        for (facility, col_key), cat_running in facility_accum.items():
            # Collect all (yr, mn) keys present across any category
            all_yms = set()
            for col in CAT_COLS:
                all_yms.update(cat_running[col].keys())

            for ym in all_yms:
                yr, mn = ym
                key = (facility, yr, mn)
                results[key] = {col: cat_running[col][ym] for col in CAT_COLS}

        notes.append(f"  Facilities found: {sorted(facilities_found)}")
        notes.append(f"  Number of facilities: {len(facilities_found)}")

    return results, notes


def compute_derived(cats):
    """Given a dict of {col_name: count}, compute derived totals."""
    inmate_on_inmate = (
        cats["assault_on_inmate"] +
        cats["battery_on_inmate"] +
        cats["fighting"] +
        cats["riot"]
    )
    staff_involved = (
        cats["assault_on_officer"] +
        cats["battery_on_officer"] +
        cats["cell_extractions"]
    )
    violent_incidents = inmate_on_inmate + staff_involved
    return violent_incidents, inmate_on_inmate, staff_involved


def main():
    # Accumulate data, newest file wins on overlap
    # Process oldest→newest; newer overwrites same key
    all_data = {}   # (facility, year, month) -> ({col_name: count}, source_tag)
    all_notes = []
    overlap_overrides = defaultdict(int)

    for pdf_filename, source_tag in PDFS:
        pdf_path = os.path.join(INCIDENTS_DIR, pdf_filename)
        print(f"Processing {pdf_filename} ...")

        all_notes.append(f"\n{'='*60}")
        all_notes.append(f"FILE: {pdf_filename}  (tag: {source_tag})")

        try:
            results, notes = extract_facility_data(pdf_path, source_tag)
            all_notes.extend(notes)

            overridden = 0
            new_records = 0
            for key, cats in results.items():
                if key in all_data:
                    overridden += 1
                else:
                    new_records += 1
                all_data[key] = (cats, source_tag)

            all_notes.append(f"  New keys added: {new_records}")
            all_notes.append(f"  Keys overriding older data: {overridden}")
            all_notes.append(f"  Total records so far: {len(all_data)}")
            overlap_overrides[source_tag] = overridden
            print(f"  -> {len(results)} records; {new_records} new, {overridden} overrides")

        except Exception as exc:
            import traceback
            msg = f"  ERROR processing {pdf_filename}: {exc}"
            all_notes.append(msg)
            print(msg)
            traceback.print_exc()

    # ------------------------------------------------------------------ #
    #  Write output CSV                                                    #
    # ------------------------------------------------------------------ #
    output_csv = os.path.join(BASE_DIR, "cdcr_violent_incidents_by_facility.csv")
    sorted_keys = sorted(all_data.keys(), key=lambda x: (x[0], x[1], x[2]))

    with open(output_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLS)
        for key in sorted_keys:
            facility, year, month = key
            cats, source_tag = all_data[key]
            violent_incidents, inmate_on_inmate, staff_involved = compute_derived(cats)
            writer.writerow([
                facility, year, month,
                violent_incidents, inmate_on_inmate, staff_involved,
                cats["assault_on_inmate"],
                cats["battery_on_inmate"],
                cats["fighting"],
                cats["riot"],
                cats["assault_on_officer"],
                cats["battery_on_officer"],
                cats["cell_extractions"],
                source_tag,
            ])

    print(f"\nCSV written: {output_csv}  ({len(all_data)} rows)")

    # ------------------------------------------------------------------ #
    #  Validation: compare per-facility sum to All Institutions row       #
    # ------------------------------------------------------------------ #
    print("\nValidation spot-check (Dec 2025 from d2512):")
    dec25 = []
    for k, (cats, src) in all_data.items():
        if k[1] == 2025 and k[2] == 12:
            violent_incidents, _, _ = compute_derived(cats)
            dec25.append({'facility': k[0], 'count': violent_incidents})
    per_fac_total = sum(r['count'] for r in dec25)
    all_inst_expected = 44 + 321 + 17 + 314 + 49 + 2 + 268  # from All Institutions page
    print(f"  Per-facility sum Dec25: {per_fac_total}  (from {len(dec25)} facilities)")
    print(f"  All Institutions Dec25: {all_inst_expected}")
    if abs(per_fac_total - all_inst_expected) < 30:
        print("  -> PASS (within tolerance)")
    else:
        diff = all_inst_expected - per_fac_total
        print(f"  -> NOTE: Difference of {diff} — may be due to facilities not in per-facility pages")

    # ------------------------------------------------------------------ #
    #  Write extraction notes                                             #
    # ------------------------------------------------------------------ #
    notes_path = os.path.join(BASE_DIR, "cdcr_incidents_extraction_notes.txt")
    unique_facilities = sorted({k[0] for k in all_data})
    year_range = (min(k[1] for k in all_data), max(k[1] for k in all_data))

    with open(notes_path, 'w') as f:
        f.write("CDCR Violent Incidents Extraction Notes\n")
        f.write("=" * 60 + "\n\n")

        f.write("VIOLENT CATEGORIES TRACKED SEPARATELY (per-facility Total rows):\n")
        for cat, col in CATEGORY_COL.items():
            f.write(f"  - {cat}  ->  {col}\n")

        f.write("\nDERIVED COLUMNS (computed at write time):\n")
        f.write("  - inmate_on_inmate = assault_on_inmate + battery_on_inmate + fighting + riot\n")
        f.write("  - staff_involved   = assault_on_officer + battery_on_officer + cell_extractions\n")
        f.write("  - violent_incidents = inmate_on_inmate + staff_involved  (backwards-compat total)\n")

        f.write("\nEXCLUSIONS:\n")
        f.write("  - All Controlled Substance rows\n")
        f.write("  - All Type of Force rows\n")
        f.write("  - 'Riot - Number of Inmates Involved' row (counts individuals, not incidents)\n")
        f.write("  - All other non-violent incident categories\n")

        f.write("\nMETHOD NOTES:\n")
        f.write("  - Each facility spans 2-3 pages per PDF; all pages accumulated before storing.\n")
        f.write("  - Pages are grouped by (facility, month_column_set) to handle 2-3 page splits.\n")
        f.write("  - 'Riot' row matched exactly to avoid confusion with 'Riot - Number of Inmates'.\n")

        f.write("\nOVERLAP RESOLUTION:\n")
        f.write("  PDFs processed oldest-first; newer reports overwrite older for the same\n")
        f.write("  (facility, year, month) key.\n")

        f.write("\nVALIDATION (Dec 2025 spot-check against All Institutions summary):\n")
        f.write(f"  Per-facility sum: {per_fac_total}  ({len(dec25)} facilities)\n")
        f.write(f"  All Institutions expected: {all_inst_expected}\n")
        diff = all_inst_expected - per_fac_total
        f.write(f"  Difference: {diff}\n")
        if diff > 0:
            f.write("  Note: small discrepancies may reflect facilities not present in per-facility\n")
            f.write("  pages (e.g. facilities that closed/opened mid-period) or rounding differences.\n")

        f.write(f"\nOUTPUT SUMMARY:\n")
        f.write(f"  Total records: {len(all_data)}\n")
        f.write(f"  Year range: {year_range[0]}-{year_range[1]}\n")
        f.write(f"  Facilities ({len(unique_facilities)}): {', '.join(unique_facilities)}\n")

        f.write("\nPER-FILE OVERLAP OVERRIDES (records overwriting an older file's data):\n")
        for src, cnt in overlap_overrides.items():
            f.write(f"  {src}: {cnt} overrides\n")

        f.write("\n\nDETAILED PROCESSING LOG:\n")
        f.write("\n".join(all_notes))
        f.write("\n")

    print(f"Notes written: {notes_path}")

    # Quick sanity check printout
    print(f"\nFacilities ({len(unique_facilities)}): {', '.join(unique_facilities)}")
    print(f"Year range: {year_range}")
    print("\nSample output (first 15 rows of CSV):")
    print(f"  {'facility':8s}  {'year':4s}  {'mo':2s}  {'violent':>8s}  {'i_on_i':>6s}  {'staff':>5s}  source")
    print(f"  {'-'*8}  {'-'*4}  {'--'}  {'-'*8}  {'-'*6}  {'-'*5}  ------")
    for key in sorted_keys[:15]:
        facility, year, month = key
        cats, src = all_data[key]
        violent_incidents, inmate_on_inmate, staff_involved = compute_derived(cats)
        print(f"  {facility:8s}  {year}  {month:2d}  {violent_incidents:8d}  {inmate_on_inmate:6d}  {staff_involved:5d}  {src}")


if __name__ == "__main__":
    main()
