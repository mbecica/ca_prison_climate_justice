"""
Extract CDCR facility staff counts from State Controller's Office
"Active State Employees by Department" PDFs.

Input:  data_sources/facilities/CDCR/cdcr_staffing/*.pdf
Output: data_sources/facilities/CDCR/sco_staffing_2020-2026.csv

Columns in output: date, sco_facility_name, full_time, part_time,
                   intermittent, indeterminate, total

Methodology
-----------
For 2020-2024 and 2026, pdfplumber extract_text() yields clean lines in the format:
  CDCR <FACILITY NAME> <FT> <PT> <INT> <INDET> <TOTAL>
parsed with a regex. Multi-line name splits (e.g. "SUBSTANCE ABUSE TREAT-" /
"CDCR CORCORAN ...") are resolved by looking back at the preceding raw lines.

For 2025, the PDF font encoding produces wrapped text, so we use table extraction.
Garbled names (e.g. "I R ONWOOD") are resolved via a normalized name lookup
(strip non-alphanumeric) built from the clean PDFs.

If two PDFs share the same "Data as of" date (identical snapshots), duplicates
are removed from the output.
"""

import csv
import re
import sys
from pathlib import Path
from datetime import datetime

import pdfplumber

# ---------------------------------------------------------------------------
# Name fragments produced by multi-line name splitting in older PDFs
# These are second-line tails that follow a line ending with '-'.
# They match as valid CDCR rows but are fragments, not real facility names.
# ---------------------------------------------------------------------------
KNOWN_FRAGMENTS = {
    normalize_key := lambda s: re.sub(r'[^a-z0-9]', '', s.lower()),
}


def normalize(name: str) -> str:
    """Strip everything except letters/digits, lowercase. Used for matching."""
    return re.sub(r'[^a-z0-9]', '', name.lower())


# Rows whose normalized name starts with these prefixes are non-prison CDCR rows
EXCLUDE_NORM_PREFIXES = (
    'cchcs',        # CCHCS-HEADQUARTERS, CCHCS-CENTRAL/NORTHERN/SOUTHERN REGION
    'ctra',         # CTRA-* training academies
    'cdcrchcf',     # CDCR-CHCF-PIP (admin entry)
    'cdcrcamedi',   # CDCR-CA MEDICAL FACILITY-PIP
    'cdcrsalinas',  # CDCR-SALINAS VALLEY-PIP
    'parole',       # PAROLE & COMMUNITY SVS DIV
    'richardamcgee',       # RICHARD A MCGEE CORR TR CENTER
    'correctionsadmin',    # CORRECTIONS/ADMINISTRATION
    'correctionsa',        # garbled CORRECTIONS/ADMINISTRATION
    'youth',               # YOUTH AUTHORITY/ADMINISTRATION
)
EXCLUDE_NORM_CONTAINS = (
    'welfarefund',   # CORR/INMATE WELFARE FUND
    'revolvingfund', # CORR/IND REVOLVING FUND
)


def is_prison_row(norm: str) -> bool:
    for prefix in EXCLUDE_NORM_PREFIXES:
        if norm.startswith(prefix):
            return False
    for substr in EXCLUDE_NORM_CONTAINS:
        if substr in norm:
            return False
    return True


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------
def extract_date(pdf) -> str:
    for page in pdf.pages:
        text = page.extract_text() or ''
        m = re.search(r'Data as of[:\s]+([A-Za-z]+ \d{4})', text, re.IGNORECASE)
        if m:
            raw = m.group(1)
            try:
                return datetime.strptime(raw, '%B %Y').strftime('%B %Y')
            except ValueError:
                try:
                    return datetime.strptime(raw.title(), '%B %Y').strftime('%B %Y')
                except ValueError:
                    return raw
    return 'UNKNOWN'


# ---------------------------------------------------------------------------
# Text-extraction method (clean PDFs: 2020-2024, 2026)
# ---------------------------------------------------------------------------
LINE_RE = re.compile(
    r'^CDCR\s+(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$'
)


def extract_via_text(pdf, canonical_lookup: dict) -> list[dict] | None:
    """
    Extract CDCR rows using text extraction.
    Returns list of dicts if successful (≥5 matching lines), else None.
    Handles multi-line name splits and truncated names ending with '-'.
    """
    # Collect all raw lines across pages
    all_lines: list[str] = []
    for page in pdf.pages:
        text = page.extract_text() or ''
        all_lines.extend(text.split('\n'))

    rows = []
    for idx, line in enumerate(all_lines):
        m = LINE_RE.match(line.strip())
        if not m:
            continue

        name = m.group(1).strip()
        ft, pt, interm, indet, total = (
            int(m.group(i).replace(',', '')) for i in range(2, 7)
        )

        # --- Multi-line name handling ---
        # Two patterns observed across different PDF versions:
        #
        # Old PDFs (2020-2022): the name tail appears on a standalone line BEFORE
        #   the CDCR data line.  e.g.  "RICHARD A MCGEE CORR TR" (line n)
        #                              "CDCR CENTER 424 0 ..." (line n+1)
        #
        # New PDFs (2026): the name tail appears on a standalone line AFTER
        #   the CDCR data line.  e.g.  "CDCR SUBSTANCE ABUSE TREAT- 1894 ..." (line n)
        #                              "CORCORAN" (line n+1)

        _HEADER_WORDS = frozenset(('TIME', 'TENT', 'MINATE', 'DEPARTMENT', 'BUREAU',
                                    'INDETERM', 'INTERMIT', 'BOARD/BUREAU'))

        def is_continuation(s: str) -> bool:
            """True if s looks like a name fragment (no numbers, not CDCR, not a header)."""
            if not s or s.startswith('CDCR') or re.search(r'\d', s):
                return False
            words = s.split()
            if not (1 <= len(words) <= 6):
                return False
            if any(w in _HEADER_WORDS for w in words):
                return False
            return True

        # Pattern 1 (old PDFs): name is short → look at immediately preceding line
        if len(name.split()) <= 2:
            prev = all_lines[idx - 1].strip() if idx > 0 else ''
            if prev.endswith('-') and is_continuation(prev):
                name = prev + name
            elif is_continuation(prev) and len(prev.split()) > 2:
                name = prev + ' ' + name

        # Pattern 2 (new PDFs): name ends with '-' → look forward for the tail
        if name.endswith('-'):
            for fwd in range(idx + 1, min(idx + 3, len(all_lines))):
                nxt = all_lines[fwd].strip()
                if is_continuation(nxt):
                    name = name + nxt
                    break
                if nxt.startswith('CDCR'):
                    break  # next CDCR row, stop looking

        if len(name) < 4:
            continue

        # Resolve to canonical if available
        norm = normalize(name)
        canonical = canonical_lookup.get(norm, name)

        rows.append({
            'sco_facility_name': canonical,
            'full_time': ft,
            'part_time': pt,
            'intermittent': interm,
            'indeterminate': indet,
            'total': total,
        })

    # Quality check: fall back to table extraction if text is garbled.
    # Signs of garbling: names with a single-letter first word (e.g. "C ENTINELA")
    # or very short names (<8 chars) that lack a known facility suffix.
    FACILITY_SUFFIXES = ('PRISON', 'FACILITY', 'CENTER', 'COLONY', 'INSTITUTION',
                         'ACADEMY', 'CAMP', 'UNIT', 'COMPLEX', 'PRISON - PIA',
                         'FACILITY - PIA', 'CORCORAN', 'RANCH')
    def looks_garbled(name: str) -> bool:
        first_word = name.split()[0] if name.split() else ''
        if len(first_word) == 1 and first_word.isupper():
            return True
        if len(name) < 8 and not any(name.upper().endswith(s) for s in FACILITY_SUFFIXES):
            return True
        return False
    garbled = sum(1 for r in rows if looks_garbled(r['sco_facility_name']))
    if garbled > len(rows) * 0.10:
        return None  # signal caller to fall back to table extraction

    return rows if len(rows) >= 5 else None


# ---------------------------------------------------------------------------
# Table-extraction method (garbled PDFs: 2025)
# ---------------------------------------------------------------------------
def extract_via_table(pdf, canonical_lookup: dict) -> list[dict]:
    """
    Extract CDCR rows from table cells. Each data row has exactly 5 non-None
    numeric values after position 1 (FT, PT, INT, INDET, TOTAL).
    Uses canonical_lookup to fix garbled names.
    """
    rows = []
    seen = set()

    for page in pdf.pages:
        for tbl in page.extract_tables():
            for row in tbl:
                if not row or str(row[0]).strip() != 'CDCR':
                    continue
                raw_name = re.sub(r'\s+', ' ', (row[1] or '').replace('\n', ' ')).strip()
                if not raw_name:
                    continue

                nums = [
                    int(str(cell).replace(',', ''))
                    for cell in row[2:]
                    if cell and re.match(r'^[\d,]+$', str(cell).strip())
                ]
                if len(nums) != 5:
                    continue

                norm = normalize(raw_name)
                canonical = canonical_lookup.get(norm, raw_name)

                key = (canonical, nums[0], nums[4])
                if key in seen:
                    continue
                seen.add(key)

                rows.append({
                    'sco_facility_name': canonical,
                    'full_time': nums[0],
                    'part_time': nums[1],
                    'intermittent': nums[2],
                    'indeterminate': nums[3],
                    'total': nums[4],
                })

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    repo_root = Path(__file__).parent.parent
    input_dir = repo_root / 'data_sources' / 'facilities' / 'CDCR' / 'cdcr_staffing'
    output_file = repo_root / 'data_sources' / 'facilities' / 'CDCR' / 'sco_staffing_2020-2026.csv'

    pdf_paths = sorted(input_dir.glob('*.pdf'))
    if not pdf_paths:
        print(f'No PDFs found in {input_dir}', file=sys.stderr)
        sys.exit(1)

    # --- Pass 1: collect canonical names from clean PDFs ---
    canonical_names: set[str] = set()
    canonical_lookup: dict[str, str] = {}  # normalize(name) → canonical_name

    for pdf_path in pdf_paths:
        with pdfplumber.open(pdf_path) as pdf:
            rows = extract_via_text(pdf, {})  # first pass: no lookup yet
            if rows:
                for r in rows:
                    name = r['sco_facility_name']
                    if len(name) >= 4 and not name.endswith('-'):
                        canonical_names.add(name)

    # Build lookup: normalize → canonical (prefer longer names for same key)
    for name in sorted(canonical_names, key=len, reverse=True):
        norm = normalize(name)
        if norm not in canonical_lookup:
            canonical_lookup[norm] = name

    print(f'Canonical name variants: {len(canonical_names)}\n')

    # --- Pass 2: extract all PDFs with lookup ---
    all_rows = []
    seen_dates: set[str] = set()

    for pdf_path in sorted(pdf_paths):
        print(f'Processing {pdf_path.name} ...', end=' ', flush=True)
        with pdfplumber.open(pdf_path) as pdf:
            date = extract_date(pdf)
            rows = extract_via_text(pdf, canonical_lookup)
            method = 'text'
            if rows is None:
                rows = extract_via_table(pdf, canonical_lookup)
                method = 'table'

        # Skip duplicate PDFs (same date already processed)
        if date in seen_dates:
            print(f'{date} — DUPLICATE, skipping')
            continue
        seen_dates.add(date)

        # Filter to prison rows
        prison_rows = [r for r in rows if is_prison_row(normalize(r['sco_facility_name']))]

        # Deduplicate within this PDF (same facility name + totals)
        seen_within: set[tuple] = set()
        deduped = []
        for r in prison_rows:
            key = (r['sco_facility_name'], r['total'])
            if key not in seen_within:
                seen_within.add(key)
                deduped.append(r)

        print(f'{date} — {len(deduped)} facilities ({method})')

        for r in deduped:
            r['date'] = date
        all_rows.extend(deduped)

    # Sort by date, then facility name
    def sort_key(r):
        try:
            dt = datetime.strptime(r['date'], '%B %Y')
        except ValueError:
            dt = datetime(1900, 1, 1)
        return (dt, r['sco_facility_name'])

    all_rows.sort(key=sort_key)

    fieldnames = ['date', 'sco_facility_name', 'full_time', 'part_time',
                  'intermittent', 'indeterminate', 'total']

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f'\nWrote {len(all_rows)} rows → {output_file.relative_to(repo_root)}')


if __name__ == '__main__':
    main()
