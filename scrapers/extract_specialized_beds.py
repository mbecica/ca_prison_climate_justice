#!/usr/bin/env python3
"""
Extract specialized mental health bed data from CDCR PDF reports into CSVs:

  1. PIP Census Reports → pip_census.csv
     Facility-level APP/ICF bed capacity and occupancy by custody level.

  2. Coleman PIP Waitlist Reports → pip_coleman_waitlist.csv
     Facility-level capacity, census, reserved, redlined, available beds, waitlist.

  3. MHCB Reports → mhcb_census.csv
     System-level (male/female) MHCB capacity, census, redlined, available.

  4. Bed Need Study → bed_need_study_actuals.csv
     System-wide historical actuals by program type (APP, ICF-High, ICF-Low,
     MHCB, EOP-GP, RHE, CCCMS) from 2014–2025.

  5. MHSDS Map (2021) → mhsds_programs_by_facility.csv
     Facility-level mental health program flags read from the map's icon
     letters in the PDF text layer.

Sources: data_sources/facilities/CDCR/specialized_beds/*.pdf

Usage:
  python3 scrapers/extract_specialized_beds.py
"""

import re
import pandas as pd
import pdfplumber
from pathlib import Path

SRC = Path("data_sources/facilities/CDCR/specialized_beds")
OUT = Path("data_sources/facilities/CDCR")


# ── Helpers ─────────────────────────────────────────────────────────────────

def parse_date_from_filename(fname):
    """Extract YYYY-MM-DD date from filename like '2026-01-26_...'."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", fname)
    return m.group(1) if m else None


def clean_int(val):
    """Parse an integer from a string, return 0 for empty/None."""
    if val is None:
        return 0
    val = str(val).strip().replace(",", "")
    if val == "" or val == "-":
        return 0
    try:
        return int(float(val))
    except ValueError:
        return 0


# ── 1. PIP Census Reports ──────────────────────────────────────────────────

def extract_pip_census(pdf_path):
    """Parse a PIP Census Report into rows of (facility, section, program, measure, value)."""
    date = parse_date_from_filename(pdf_path.name)
    pdf = pdfplumber.open(pdf_path)
    rows = []

    # Collect all table rows across pages
    all_rows = []
    for page in pdf.pages:
        for table in page.extract_tables():
            all_rows.extend(table)

    current_facility = None
    current_section = None
    current_program = None  # APP or ICF (or Total Census for ICF-only sections)
    bed_capacity = None

    # Section headers that define program context
    section_headers = {
        "Male Flex Programs": "Male Flex (APP/ICF)",
        "Male Intermediate Care Facility (High Custody) Programs": "Male ICF High Custody",
        "Male Intermediate Care Facility (Low Custody) Programs": "Male ICF Low Custody",
        "Female Programs": "Female (APP/ICF)",
    }

    for row in all_rows:
        if not row or len(row) < 2:
            continue

        col0 = (row[0] or "").strip()
        col2 = (row[2] or "").strip() if len(row) > 2 else ""
        col3 = (row[3] or "").strip() if len(row) > 3 else ""

        # Skip header rows
        if col0 == "Facility":
            continue

        # Section header
        if col0 in section_headers:
            current_section = section_headers[col0]
            current_facility = None
            continue

        # Totals rows — skip (we'll compute from facility-level data)
        if col0.startswith("Totals for") or col0 == "GRAND TOTALS" or col0.startswith("Total Inpatient"):
            current_facility = None
            continue

        # Footnotes
        if col0.startswith("•") or col0.startswith("♦"):
            continue

        # New facility row
        if col0 and col0 not in ("", None):
            current_facility = col0
            bed_capacity = clean_int(row[1]) if len(row) > 1 else 0
            # Determine initial program type from context
            if current_section in ("Male ICF High Custody", "Male ICF Low Custody"):
                current_program = "ICF"
            else:
                current_program = "APP"  # Flex sections start with APP

        if not current_facility or not col2:
            continue

        # Determine measure and program
        measure = col2.rstrip(":")
        value = clean_int(col3)

        # Track program type transitions within Flex facilities
        if measure == "Total APP Census":
            rows.append({
                "date": date,
                "facility": current_facility,
                "section": current_section,
                "bed_capacity": bed_capacity,
                "program": "APP",
                "measure": "Total Census",
                "value": value,
            })
            # Next block within this facility will be ICF
            current_program = "ICF"
            continue
        elif measure == "Total ICF Census":
            rows.append({
                "date": date,
                "facility": current_facility,
                "section": current_section,
                "bed_capacity": bed_capacity,
                "program": "ICF",
                "measure": "Total Census",
                "value": value,
            })
            continue
        elif measure in ("Total APP/ICF Census", "Total Census"):
            rows.append({
                "date": date,
                "facility": current_facility,
                "section": current_section,
                "bed_capacity": bed_capacity,
                "program": "Total",
                "measure": "Total Census",
                "value": value,
            })
            # Reset program for next facility
            if current_section in ("Male ICF High Custody", "Male ICF Low Custody"):
                current_program = "ICF"
            else:
                current_program = "APP"
            continue
        elif measure == "Total ICF out of LRH":
            rows.append({
                "date": date,
                "facility": current_facility,
                "section": current_section,
                "bed_capacity": bed_capacity,
                "program": "ICF",
                "measure": "Out of LRH",
                "value": value,
            })
            continue
        elif measure == "Total out of LRH":
            rows.append({
                "date": date,
                "facility": current_facility,
                "section": current_section,
                "bed_capacity": bed_capacity,
                "program": "ICF",
                "measure": "Out of LRH",
                "value": value,
            })
            continue

        # Level rows and special categories
        if measure in ("No Score", "Level I", "Level II", "Level III", "Level IV",
                       "PC 1370", "WIC 7301"):
            rows.append({
                "date": date,
                "facility": current_facility,
                "section": current_section,
                "bed_capacity": bed_capacity,
                "program": current_program,
                "measure": measure,
                "value": value,
            })

    pdf.close()
    return rows


def normalize_facility_name(name):
    """Normalize facility names across PDF format variations."""
    if not name:
        return name
    # Fix newline-vs-dash variants
    name = name.replace("\n", " - ")
    # Standardize known names
    replacements = {
        "California Health Care Facility\n Single Cell": "CHCF - Single Cell",
        "California Health Care Facility - Single Cell": "CHCF - Single Cell",
        "California Medical Facility\n Single Cell": "CMF - Single Cell",
        "California Medical Facility - Single Cell": "CMF - Single Cell",
        "California Medical Facility\n Multi Person Cells": "CMF - Multi Person Cells",
        "California Medical Facility - Multi Person Cells": "CMF - Multi Person Cells",
        "California Medical Facility\n Dorms": "CMF - Dorms",
        "California Medical Facility - Dorms": "CMF - Dorms",
        "Salinas Valley\n Single Cell": "SVSP - Single Cell",
        "Salinas Valley - Single Cell": "SVSP - Single Cell",
        "Salinas Valley\n Multi-person Cells": "SVSP - Multi-person Cells",
        "Salinas Valley - Multi-person Cells": "SVSP - Multi-person Cells",
        "PIP - California Medical Facility": "CMF (Flex)",
        "PIP - California Health Care Facility": "CHCF (Flex)",
        "PIP-San Quentin": "SQ (Flex)",
        "PIP-California Men's Colony": "CMC (Flex)",
        "PIP-California Institution for Women": "CIW (Flex)",
        "California Health Care Facility\nSingle Cell": "CHCF - Single Cell",
        "California Medical Facility\nSingle Cell": "CMF - Single Cell",
        "California Medical Facility\nMulti Person Cells": "CMF - Multi Person Cells",
        "California Medical Facility\nDorms": "CMF - Dorms",
        "Salinas Valley\nSingle Cell": "SVSP - Single Cell",
        "Salinas Valley\nMulti-person Cells": "SVSP - Multi-person Cells",
    }
    return replacements.get(name, name)


def build_pip_census_csv():
    """Process all PIP Census PDFs and write pip_census.csv."""
    files = sorted(SRC.glob("*PIP-Census*"))
    all_rows = []
    for f in files:
        print(f"  PIP Census: {f.name}")
        all_rows.extend(extract_pip_census(f))

    df = pd.DataFrame(all_rows)
    df["facility"] = df["facility"].apply(normalize_facility_name)
    out_path = OUT / "pip_census.csv"
    df.to_csv(out_path, index=False)
    print(f"  → {out_path} ({len(df)} rows, {df['date'].nunique()} dates)")
    return df


# ── 2. Coleman PIP Waitlist Reports ────────────────────────────────────────

def extract_coleman_waitlist(pdf_path):
    """Parse a Coleman PIP Waitlist Report into facility-level rows."""
    date = parse_date_from_filename(pdf_path.name)
    pdf = pdfplumber.open(pdf_path)
    rows = []

    all_table_rows = []
    for page in pdf.pages:
        for table in page.extract_tables():
            all_table_rows.extend(table)

    current_section = None

    section_map = {
        "MALE INTERMEDIATE LOCKED DORM": "Male Intermediate Locked Dorm",
        "MALE INTERMEDIATE HIGH CUSTODY": "Male ICF High Custody",
        "MALE FLEX ACUTE PSYCHIATRIC PROGRAM &\nINTERMEDIATE CARE FACILITY": "Male Flex (APP/ICF)",
        "FEMALE HIGH CUSTODY": "Female High Custody",
    }

    for row in all_table_rows:
        if not row or len(row) < 7:
            continue

        col0 = (row[0] or "").strip()

        # Detect section headers
        for key, section_name in section_map.items():
            if col0.startswith(key.split("\n")[0]):
                current_section = section_name
                break

        # Skip header/section rows
        if col0 in section_map or col0.startswith("MALE") or col0.startswith("FEMALE"):
            continue
        if col0 == "" or col0 is None:
            continue

        if "GRAND TOTALS" in col0:
            facility = "GRAND TOTALS"
            current_section = "All PIPs"
        elif col0 == "Total":
            facility = f"Total - {current_section}"
        else:
            facility = col0

        rows.append({
            "date": date,
            "section": current_section,
            "facility": facility,
            "bed_capacity": clean_int(row[1]),
            "census": clean_int(row[2]),
            "beds_reserved": clean_int(row[3]),
            "beds_redlined": clean_int(row[4]),
            "medical_isolation_rooms": clean_int(row[5]),
            "available_beds": clean_int(row[6]),
            "pending_referrals": clean_int(row[7]) if len(row) > 7 else 0,
            "accepted_referrals": clean_int(row[8]) if len(row) > 8 else 0,
            "total_waitlist": clean_int(row[9]) if len(row) > 9 else 0,
        })

    pdf.close()
    return rows


def build_coleman_waitlist_csv():
    """Process all Coleman Waitlist PDFs and write pip_coleman_waitlist.csv."""
    files = sorted(SRC.glob("*PIP-Waitlist*")) + sorted(SRC.glob("*PIP-Coleman*"))
    # Deduplicate by date
    seen_dates = set()
    unique_files = []
    for f in files:
        d = parse_date_from_filename(f.name)
        if d and d not in seen_dates:
            seen_dates.add(d)
            unique_files.append(f)

    all_rows = []
    for f in sorted(unique_files):
        print(f"  Coleman Waitlist: {f.name}")
        all_rows.extend(extract_coleman_waitlist(f))

    df = pd.DataFrame(all_rows)
    out_path = OUT / "pip_coleman_waitlist.csv"
    df.to_csv(out_path, index=False)
    print(f"  → {out_path} ({len(df)} rows, {df['date'].nunique()} dates)")
    return df


# ── 3. MHCB Reports ───────────────────────────────────────────────────────

def extract_mhcb(pdf_path):
    """Parse an MHCB report into male/female rows."""
    date = parse_date_from_filename(pdf_path.name)
    pdf = pdfplumber.open(pdf_path)
    rows = []

    all_table_rows = []
    for page in pdf.pages:
        for table in page.extract_tables():
            all_table_rows.extend(table)

    for row in all_table_rows:
        if not row or len(row) < 7:
            continue
        col0 = (row[0] or "").strip()
        if col0 in ("Male Programs", "Female Programs", "Totals"):
            rows.append({
                "date": date,
                "program": col0,
                "bed_capacity": clean_int(row[1]),
                "census": clean_int(row[2]),
                "beds_redlined": clean_int(row[3]),
                "available_beds": clean_int(row[4]),
                "total_pending_referrals": clean_int(row[5]),
                "beds_assigned": clean_int(row[6]),
                "pending_referrals_gt_24hrs": clean_int(row[7]) if len(row) > 7 else 0,
            })

    pdf.close()
    return rows


def build_mhcb_csv():
    """Process all MHCB PDFs and write mhcb_census.csv."""
    files = sorted(SRC.glob("*MHCB*")) + sorted(SRC.glob("*Mental-Health-Crisis-Bed*"))
    seen_dates = set()
    unique_files = []
    for f in files:
        d = parse_date_from_filename(f.name)
        if d and d not in seen_dates:
            seen_dates.add(d)
            unique_files.append(f)

    all_rows = []
    for f in sorted(unique_files):
        print(f"  MHCB: {f.name}")
        all_rows.extend(extract_mhcb(f))

    df = pd.DataFrame(all_rows)
    out_path = OUT / "mhcb_census.csv"
    df.to_csv(out_path, index=False)
    print(f"  → {out_path} ({len(df)} rows, {df['date'].nunique()} dates)")
    return df


# ── 4. Bed Need Study ──────────────────────────────────────────────────────

def extract_bed_need_study(pdf_path):
    """Extract historical actuals from the Bed Need Study forecast tables.

    We pull the 'Avg Program Census' (or 'Total Avg Daily Census') and
    'Bed Need' rows from each program table, spanning 2014–2025.
    """
    pdf = pdfplumber.open(pdf_path)
    rows = []

    # Map table labels to program names
    program_markers = {
        "APP - MALE": "Male APP",
        "ICF-HIGH CUSTODY - MALE": "Male ICF-High",
        "ICF-LOW CUSTODY - MALE": "Male ICF-Low",
        "MHCB - Males": "Male MHCB",
        "EOP-GP - MALE": "Male EOP-GP",
        "RHE - Males": "Male RHE",
        "CCCMS - MALE": "Male CCCMS",
        "APP/ICF - FEMALE": "Female APP/ICF",
        "MHCB - FEMALE": "Female MHCB",
        "EOP-GP - FEMALE": "Female EOP-GP",
        "RHE - FEMALE": "Female RHE",
        "CCCMS - FEMALE": "Female CCCMS",
    }

    # Fiscal years end June 30; table columns labeled by FY ending year
    fy_years = list(range(2014, 2031))

    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 3:
                continue

            # Identify program from first column header
            header_col0 = (table[0][0] or "").strip()
            program = None
            for marker, prog in program_markers.items():
                if marker in header_col0:
                    program = prog
                    break
            if not program:
                continue

            # Parse each row
            for trow in table:
                label = (trow[0] or "").strip()

                # We want the census and bed need rows
                target_measures = {
                    "Census Rate": "Census Rate",
                    "Avg Program Census": "Avg Census",
                    # Total ADC = Avg Program Census + Avg Pending List;
                    # in CCCMS/EOP tables it is the only census row
                    "Total Avg Daily Census (ADC)": "Total ADC",
                    "Total Avg Daily Census": "Total ADC",
                    "Avg Program Census (CSH)": "Avg Census (CSH)",
                    "Avg Census (CHCF)": "Avg Census (CHCF)",
                    "Avg Census (VPP)": "Avg Census (VPP)",
                    "Avg Program Census (VPP)": "Avg Census (VPP)",
                    "Avg Program Census (ASH)": "Avg Census (ASH)",
                    "Avg Program Census (PSH)": "Avg Census (PSH)",
                    "Avg Program Census (CIW)": "Avg Census (CIW)",
                    "Bed Need (90% Occ)": "Bed Need (90%)",
                    "Bed Need (95% Occ)": "Bed Need (95%)",
                    "CDCR Total Male Population": "CDCR Male Pop",
                    "CDCR Total Female Population": "CDCR Female Pop",
                    "Avg Pending List": "Avg Pending List",
                    # EOP-GP per-level rows
                    "LEVEL I Census Rate": "Level I Census Rate",
                    "LEVEL I TOTAL ADC": "Level I Avg Census",
                    "LEVEL I Bed Need (95% Occ)": "Level I Bed Need (95%)",
                    "LEVEL II Census Rate": "Level II Census Rate",
                    "LEVEL II TOTAL ADC": "Level II Avg Census",
                    "LEVEL II Bed Need (95% Occ)": "Level II Bed Need (95%)",
                    "LEVEL III Census Rate": "Level III Census Rate",
                    "LEVEL III TOTAL ADC": "Level III Avg Census",
                    "LEVEL III Bed Need (95% Occ)": "Level III Bed Need (95%)",
                    "LEVEL IV Census Rate": "Level IV Census Rate",
                    "LEVEL IV TOTAL ADC": "Level IV Avg Census",
                    "LEVEL IV Bed Need (95% Occ)": "Level IV Bed Need (95%)",
                    "Total EOP-GP Bed Need": "Bed Need (95%)",
                }

                measure = target_measures.get(label)
                if not measure:
                    continue

                # Extract values for each year column
                for i, val in enumerate(trow[1:], start=0):
                    if i >= len(fy_years):
                        break
                    year = fy_years[i]
                    num = val
                    if num is None or str(num).strip() == "":
                        continue
                    num = str(num).strip().replace(",", "")
                    try:
                        num = float(num)
                    except ValueError:
                        continue

                    rows.append({
                        "program": program,
                        "measure": measure,
                        "fy_ending": year,
                        "value": num,
                        "is_forecast": year > 2025,
                    })

    pdf.close()
    return rows


def build_bed_need_study_csv():
    """Process Bed Need Study PDF and write bed_need_study_actuals.csv."""
    files = list(SRC.glob("*Bed-Need-Study*"))
    if not files:
        print("  No Bed Need Study PDF found.")
        return None

    f = files[0]
    print(f"  Bed Need Study: {f.name}")
    rows = extract_bed_need_study(f)

    df = pd.DataFrame(rows)
    out_path = OUT / "bed_need_study_actuals.csv"
    df.to_csv(out_path, index=False)
    print(f"  → {out_path} ({len(df)} rows, {df['program'].nunique()} programs)")
    return df


# ── 5. MHSDS Map ───────────────────────────────────────────────────────────

MHSDS_LETTER_COLS = {
    "R": "reception_center",
    "C": "cccms",
    "E": "eop",
    "M": "mhcb",
    "S": "short_term_rh",
    "L": "long_term_rh",
    "A": "asu_eop_hub",
    "P": "psychiatric_services_unit",
    "PI": "psychiatric_inpatient",
    "D": "developmental_disabilities",
}

MHSDS_FACILITIES = [
    "PBSP", "HDSP", "CCC", "FSP/FWF", "SAC", "CMF", "SOL", "SQ", "MCSP",
    "CHCF", "SCC", "DVI", "CCWF", "VSP", "CTF", "SVSP", "PVSP", "ASP",
    "COR", "SATF", "KVSP", "NKSP", "WSP", "CCI", "CAC", "CMC", "LAC",
    "CIM", "CIW", "CRC", "ISP", "CVSP", "CAL", "CEN", "RJD",
]


def extract_mhsds_map(pdf_path):
    """Extract the facility × program matrix from the MHSDS map PDF.

    The program icons next to each facility are diamonds whose letters
    (R, C, E, M, S, L, A, P, PI, D) are real text glyphs in a small
    Tahoma-Bold font, so we read them from the text layer and assign each
    glyph to the facility label on the same row, rather than reading the
    map as an image.
    """
    pdf = pdfplumber.open(pdf_path)
    page = pdf.pages[0]

    # Icon letters: small Tahoma glyphs. Facility labels are Arial 9pt.
    icons = [c for c in page.chars
             if "Tahoma" in c["fontname"] and c["size"] < 6 and c["text"].strip()]
    words = page.extract_words(extra_attrs=["fontname", "size"])
    label_words = [w for w in words
                   if "Arial" in w["fontname"] and 7.5 < w["size"] < 9.5]

    fac_names = set(MHSDS_FACILITIES)
    labels = [w for w in label_words if w["text"].strip("●•.") in fac_names]

    # A couple of labels (COR, SATF) are letter-spaced and come through as
    # fragments ('C','O','R' / 'S','AT','F'); reconstruct them per text line.
    found = {w["text"].strip("●•.") for w in labels}
    frags = [w for w in label_words if w["text"].strip("●•.") not in fac_names]
    by_line = {}
    for w in frags:
        by_line.setdefault(round(w["top"]), []).append(w)
    for line in by_line.values():
        line.sort(key=lambda w: w["x0"])
        joined = "".join(w["text"] for w in line).strip("●•.")
        if joined in fac_names and joined not in found:
            labels.append({
                "text": joined,
                "x0": min(w["x0"] for w in line),
                "x1": max(w["x1"] for w in line),
                "top": min(w["top"] for w in line),
                "bottom": max(w["bottom"] for w in line),
            })

    # Assign each icon glyph to the closest facility label on its row.
    assigned = {}
    for c in icons:
        cy = (c["top"] + c["bottom"]) / 2
        best, best_d = None, None
        for w in labels:
            wy = (w["top"] + w["bottom"]) / 2
            ydiff = abs(wy - cy)
            dx = c["x0"] - w["x1"]  # icons sit to the right of the label
            if ydiff > 5.5 or dx < -2 or dx > 130:
                continue
            d = ydiff + dx * 0.01
            if best_d is None or d < best_d:
                best, best_d = w["text"].strip("●•."), d
        if best is None:
            raise ValueError(
                f"MHSDS map: could not assign icon glyph {c['text']!r} "
                f"at ({c['x0']:.0f}, {c['top']:.0f}) to a facility")
        assigned.setdefault(best, []).append((c["x0"], c["text"]))
    pdf.close()

    rows = []
    for fac in MHSDS_FACILITIES:
        glyphs = sorted(assigned.get(fac, []))
        seq = [g for _, g in glyphs]
        letters, i = [], 0
        while i < len(seq):  # merge adjacent P + I into the PI icon
            if seq[i] == "P" and i + 1 < len(seq) and seq[i + 1] == "I":
                letters.append("PI")
                i += 2
            else:
                letters.append(seq[i])
                i += 1
        row = {"facility": "FSP" if fac == "FSP/FWF" else fac}
        row.update({col: 0 for col in MHSDS_LETTER_COLS.values()})
        for letter in letters:
            row[MHSDS_LETTER_COLS[letter]] = 1
        row["source"] = "MHSDS Map"
        row["source_date"] = "2021-07-02"
        rows.append(row)
    return rows


def build_mhsds_csv():
    """Process the MHSDS map PDF and write mhsds_programs_by_facility.csv."""
    files = list(SRC.glob("MHSDS-Map*"))
    if not files:
        print("  No MHSDS map PDF found.")
        return None

    f = files[0]
    print(f"  MHSDS Map: {f.name}")
    df = pd.DataFrame(extract_mhsds_map(f))
    out_path = OUT / "mhsds_programs_by_facility.csv"
    df.to_csv(out_path, index=False)
    n_flags = df[list(MHSDS_LETTER_COLS.values())].to_numpy().sum()
    print(f"  → {out_path} ({len(df)} facilities, {n_flags} program flags)")
    return df


# ── Main ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Extracting specialized bed data from PDFs...\n")

    print("1. PIP Census Reports")
    pip_df = build_pip_census_csv()
    print()

    print("2. Coleman PIP Waitlist Reports")
    waitlist_df = build_coleman_waitlist_csv()
    print()

    print("3. MHCB Reports")
    mhcb_df = build_mhcb_csv()
    print()

    print("4. Bed Need Study")
    bns_df = build_bed_need_study_csv()
    print()

    print("5. MHSDS Map")
    mhsds_df = build_mhsds_csv()
    print()

    print("Done.")
