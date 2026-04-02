#!/usr/bin/env python3
"""
Extract CDCR TPOP-1 PDFs into two CSVs:
  tpop1_summary.csv      — Total CDCR Population (page 1, one row per report row)
  tpop1_institutions.csv — Institution Population Detail (page 2, one row per institution)

Sources:
  Monthly 2019–2026: cdcr_population_pdfs/Tpop1d{YYMM}.pdf
  Weekly  2015–2018: cdcr_population_pdfs/tpop_weekly/{YYYY}/Tpop1d{YYMMDD}.pdf
                     → only last week of each month retained (mirrors monthly cadence)

Two page-2 formats:
  Format A (monthly 2019+, weekly 2018): "Full Name (ACRONYM)  pop  design  pct  staffed"
  Format B (weekly 2015–2017):           "ACRONYM (Short Name) felon [civil] total design pct staffed"
                                          garbled underscore characters for section headers/totals
"""

import re
import pandas as pd
from pathlib import Path
from collections import defaultdict
import pdfplumber

BASE = Path("data_sources/facilities/CDCR/cdcr_population_pdfs")

MONTH_NAMES = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}

# ── File selection ─────────────────────────────────────────────────────────

def get_all_files():
    """Return sorted list of (Path, format_label) for all PDFs to process."""
    files = []

    # Monthly 2019–2026 — several naming variants:
    #   Tpop1d{YYMM}.pdf        (standard)
    #   Tpop1d{YYMMDD}.pdf      (e.g. Tpop1d210630.pdf for June 2021)
    #   Tpop1d{YYMM}-1.pdf      (e.g. Tpop1d2111-1.pdf, duplicate-revision suffix)
    seen_monthly = set()
    for pattern in ("Tpop1d????.pdf", "Tpop1d??????.pdf", "Tpop1d????-*.pdf"):
        for f in BASE.glob(pattern):
            if f not in seen_monthly and "tpop_weekly" not in str(f):
                seen_monthly.add(f)
                files.append((f, "monthly"))

    # Weekly 2015–2018: keep only the last file per calendar month
    weekly_base = BASE / "tpop_weekly"
    by_ym = defaultdict(list)
    for year in ("2015", "2016", "2017", "2018"):
        year_dir = weekly_base / year
        if not year_dir.exists():
            continue
        for f in year_dir.glob("Tpop1d??????.pdf"):
            ym = f.stem[6:10]   # "Tpop1d{YY}{MM}{DD}" → YYMM
            by_ym[ym].append(f)
    for ym in sorted(by_ym):
        last_file = sorted(by_ym[ym])[-1]
        files.append((last_file, "weekly"))

    return sorted(files, key=lambda x: x[0].name)


# ── Date parsing ───────────────────────────────────────────────────────────

def extract_report_date(text):
    """Return YYYY-MM-DD from 'As of Midnight Month DD, YYYY' in page text (any case)."""
    m = re.search(r"AS OF MIDNIGHT\s+(\w+)\s+(\d{1,2}),\s+(\d{4})", text, re.IGNORECASE)
    if m:
        month = MONTH_NAMES.get(m.group(1).capitalize(), 0)
        return f"{m.group(3)}-{month:02d}-{int(m.group(2)):02d}"
    return None


def is_page1_format_b(text):
    """True for 2015–2017 weekly page 1: uppercase header, garbled section labels."""
    return bool(re.search(r"^AS OF MIDNIGHT", text, re.MULTILINE))


# ── Page 1 parsing ─────────────────────────────────────────────────────────

# Lines that are definitely not data rows
P1_SKIP_PATTERNS = re.compile(
    r"^(California Department|Division of|Office of Research|"
    r"Monthly Report|Weekly Report|As of Midnight|"
    r"Felon/|Population Other|Report #|RReport|Note |This report|"
    r"Total CDCR Population\s*$)"    # bare header, not the data row
)

# Page 1 data row:
#   label  pop  change_period  change_year  [design  pct  staffed]
# All three trailing capacity fields appear together or not at all.
# Change values may lack a sign when they are 0 (seen in 2023+).
P1_ROW_RE = re.compile(
    r"^(.+?)\s+"
    r"([\d,]+)"                                    # population
    r"(?:\s+([+\-]?[\d,]+)"                       # change_period (optional)
    r"(?:\s+([+\-]?[\d,]+))?)?"                   # change_year   (optional)
    r"(?:\s+([\d,]+)\s+([\d.]+)\s+([\d,]+))?"     # design / pct / staffed (optional)
    r"\s*$"
)

def parse_page1(text, report_date):
    rows = []
    lines = _join_wrapped_lines(text.split("\n"))

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if P1_SKIP_PATTERNS.match(line):
            continue

        # Grand total row (label contains commas/numbers — match explicitly)
        m_total = re.match(
            r"^Total CDCR Population\s+([\d,]+)\s+([+\-]?[\d,]+)\s+([+\-]?[\d,]+)\s*$",
            line,
        )
        if m_total:
            rows.append(_p1_row(
                report_date, "Total CDCR Population",
                m_total.group(1), m_total.group(2), m_total.group(3),
                None, None, None,
            ))
            continue

        m = P1_ROW_RE.match(line)
        if not m:
            continue
        label = m.group(1).strip()
        # Exclude header-like labels (no actual population data)
        if re.match(r"^(Capacity|Occupied|Other|Last)", label):
            continue
        rows.append(_p1_row(
            report_date, label,
            m.group(2), m.group(3), m.group(4),
            m.group(5), m.group(6), m.group(7),
        ))
    return rows


def _p1_row(report_date, label, pop, chg_period, chg_year, design, pct, staffed):
    return {
        "report_date":      report_date,
        "row_label":        label,
        "population":       _int(pop),
        "change_last_period": _signed_int(chg_period),
        "change_last_year": _signed_int(chg_year),
        "design_capacity":  _int(design),
        "pct_occupied":     float(pct) if pct else None,
        "staffed_capacity": _int(staffed),
    }


def parse_page1_format_b(text, report_date):
    """
    Parse 2015–2017 weekly page 1.
    Format: LABEL  felon [civil] total  change_no  change_pct  [design pct staffed]
    Garbled underscore lines (category headers / aggregate totals) are skipped.
    The 'population' stored is the TOTAL column (felon + civil addict).
    change_last_period = change_no (since last year), change_last_year = None.
    """
    rows = []
    P1B_ROW_RE = re.compile(
        r"^([\w(].+?)\s+"
        r"([\d,]+)"                                    # felon/other
        r"(?:\s+([\d,]+))?"                            # civil addict (optional)
        r"\s+([\d,]+)"                                 # total
        r"\s+([+\-][\d,]+)"                           # change_no
        r"\s+([+\-][\d.]+)"                           # change_pct
        r"(?:\s+([\d,]+)\s+([\d.]+)\s+([\d,]+))?"     # design, pct, staffed
        r"\s*$"
    )
    for line in text.split("\n"):
        line = line.strip()
        if not line or "_" in line:
            continue
        if re.match(r"^(Data Analysis|Estimates|Offender|WEEKLY|CHANGE FROM|This report)", line):
            continue
        m = P1B_ROW_RE.match(line)
        if not m:
            continue
        label = m.group(1).strip()
        total = m.group(4)
        rows.append({
            "report_date":        report_date,
            "row_label":          label,
            "population":         _int(total),
            "change_last_period": _signed_int(m.group(5)),
            "change_last_year":   None,
            "design_capacity":    _int(m.group(7)),
            "pct_occupied":       float(m.group(8)) if m.group(8) else None,
            "staffed_capacity":   _int(m.group(9)),
        })
    return rows


def _join_wrapped_lines(lines):
    """
    Join a label-only line with the following data line when the label wraps
    (e.g. 'Custody to Community Treatment\\nReentry Program  392 +11 +76').
    """
    result = []
    i = 0
    while i < len(lines):
        cur = lines[i].strip()
        if (cur
                and i + 1 < len(lines)
                and not re.search(r"\d", cur)           # current line has no numbers
                and re.search(r"[\d,]+ +[+\-]?[\d,]+", lines[i + 1])):  # next has data
            result.append(cur + " " + lines[i + 1].strip())
            i += 2
        else:
            result.append(cur)
            i += 1
    return result


# ── Page 2 parsing ─────────────────────────────────────────────────────────

def is_format_b(text):
    """True for 2015–2017 weekly PDFs: garbled underscore headers."""
    return text.lstrip().startswith("_")


# Format A: "Full Institution Name (ACRONYM)  felon_other  design  pct  staffed"
P2A_ROW_RE = re.compile(
    r"^(.+?)\s+\(([A-Z][A-Z0-9]{1,4})\)\s+"
    r"([\d,]+)\s+([\d,]+)\s+([\d.]+)\s+([\d,]+)\s*$"
)
P2A_SKIP_STARTS = (
    "Male Institutions", "Female Institutions",
    "Male Total", "Female Total", "Institution Total",
    "Institutions", "Camps(", "California Department",
    "Division of", "Office of Research",
    "Monthly", "Weekly", "Report #", "RReport",
    "As of", "Design capacity", "Note",
)


def parse_page2_format_a(text, report_date):
    rows = []
    gender = None
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line == "Male Institutions":
            gender = "Male"
            continue
        if line == "Female Institutions":
            gender = "Female"
            continue
        if any(line.startswith(s) for s in P2A_SKIP_STARTS):
            continue
        m = P2A_ROW_RE.match(line)
        if not m:
            continue
        name = m.group(1).strip()
        # Skip aggregate rows that happen to match the pattern
        if re.search(r"\bTotal\b|\bInstitutions\b|\bCamps\b", name, re.I):
            continue
        rows.append({
            "report_date":      report_date,
            "cdcr_code":        m.group(2),
            "institution_name": name,
            "gender":           gender,
            "felon_other":      _int(m.group(3)),
            "design_capacity":  _int(m.group(4)),
            "pct_occupied":     float(m.group(5)),
            "staffed_capacity": _int(m.group(6)),
        })
    return rows


# Format B: "ACRONYM (Short Name)  felon [civil]  total  design  pct  staffed"
P2B_ROW_RE = re.compile(r"^([A-Z]{2,5})\s+\(([^)]+)\)\s+(.*)")
P2B_NUM_RE  = re.compile(r"[\d,]+(?:\.\d+)?")


def parse_page2_format_b(text, report_date):
    rows = []
    gender = None
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("_"):
            continue
        if line == "MALE":
            gender = "Male"
            continue
        if line == "FEMALE":
            gender = "Female"
            continue
        m = P2B_ROW_RE.match(line)
        if not m:
            continue
        code = m.group(1)
        name = m.group(2)
        nums = P2B_NUM_RE.findall(m.group(3))
        if len(nums) == 6:
            # felon, civil, total, design, pct, staffed
            felon, _civil, _total, design, pct, staffed = nums
        elif len(nums) == 5:
            # civil addict blank → felon repeated as total: felon, total(=felon), design, pct, staffed
            felon, _total, design, pct, staffed = nums
        elif len(nums) == 4:
            felon, design, pct, staffed = nums
        else:
            continue
        rows.append({
            "report_date":      report_date,
            "cdcr_code":        code,
            "institution_name": name,
            "gender":           gender,
            "felon_other":      _int(felon),
            "design_capacity":  _int(design),
            "pct_occupied":     float(pct),
            "staffed_capacity": _int(staffed),
        })
    return rows


# ── Helpers ────────────────────────────────────────────────────────────────

def _int(s):
    if s is None:
        return None
    return int(str(s).replace(",", "").replace("+", ""))


def _signed_int(s):
    if s is None:
        return None
    s = str(s).replace(",", "")
    return int(s)   # handles '+123', '-456', '0'


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    files = get_all_files()
    print(f"Processing {len(files)} PDFs…")

    summary_rows = []
    institution_rows = []
    errors = []

    for pdf_path, fmt in files:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                p1_text = pdf.pages[0].extract_text() or ""
                p2_text = pdf.pages[1].extract_text() if len(pdf.pages) > 1 else ""
        except Exception as e:
            errors.append(f"  READ ERROR {pdf_path.name}: {e}")
            continue

        report_date = extract_report_date(p1_text)
        if not report_date:
            errors.append(f"  DATE MISSING {pdf_path.name}")
            continue

        # Page 1
        try:
            if is_page1_format_b(p1_text):
                p1_rows = parse_page1_format_b(p1_text, report_date)
            else:
                p1_rows = parse_page1(p1_text, report_date)
            summary_rows.extend(p1_rows)
        except Exception as e:
            errors.append(f"  P1 ERROR {pdf_path.name}: {e}")
            p1_rows = []

        # Page 2
        try:
            if is_format_b(p2_text):
                inst_rows = parse_page2_format_b(p2_text, report_date)
            else:
                inst_rows = parse_page2_format_a(p2_text, report_date)
            institution_rows.extend(inst_rows)
        except Exception as e:
            errors.append(f"  P2 ERROR {pdf_path.name}: {e}")
            inst_rows = []

        print(
            f"  {pdf_path.name:25s}  {report_date}  "
            f"p1={len(p1_rows):2d}  p2={len(inst_rows):2d}  fmt={fmt}"
        )

    # Write outputs
    out_dir = Path("data_sources/facilities/CDCR")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_dir / "tpop1_summary.csv", index=False)

    inst_df = pd.DataFrame(institution_rows)
    inst_df.to_csv(out_dir / "tpop1_institutions.csv", index=False)

    print(f"\nWrote {len(summary_df):,} rows  → {out_dir / 'tpop1_summary.csv'}")
    print(f"Wrote {len(inst_df):,} rows  → {out_dir / 'tpop1_institutions.csv'}")

    if errors:
        print(f"\n{len(errors)} errors:")
        for e in errors:
            print(e)


if __name__ == "__main__":
    main()
