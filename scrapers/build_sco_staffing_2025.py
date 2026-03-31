"""
Build a 2025 cross-section from sco_staffing_2020-2026.csv.

Reads the three 2025 snapshots (February, May, June), averages the staff
counts, maps each row to a CDCR institutional code, and writes:

    data_sources/facilities/CDCR/sco_staffing_2025_avg.csv

Columns: cdcr_code, sco_facility_name, is_pia, is_cchcs,
         n_snapshots, full_time, part_time, intermittent, indeterminate, total

- cdcr_code: CDCR 3–4 letter code, or blank if unmatched.
- is_pia: True if the row is a Prison Industry Authority sub-entry.
- is_cchcs: True for the CDCR/CCHCS CA HEALTH CARE row (CCHCS healthcare
  staff co-located at CHCF, separate from CHCF operational staff).
- n_snapshots: number of 2025 snapshots the facility appeared in (1–3).
- Numeric columns are rounded means across available snapshots.
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Mapping: normalized SCO name → CDCR code
# Normalization: strip non-alphanumeric, lowercase (same as in the extractor)
# ---------------------------------------------------------------------------
def normalize(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())


# (normalized_name_fragment, cdcr_code)
# Key is normalize(sco_facility_name) with any trailing PIA/CCHCS stripped first.
# The mapping covers the base facility name; PIA rows are matched the same way
# after stripping the PIA suffix.
SCO_TO_CDCR = {
    normalize('AVENAL STATE PRISON'):               'ASP',
    normalize('CA. CORRECTIONAL CENTER'):           'CCC',   # closed 2013 (Susanville)
    normalize('CA CORRECTIONAL CENTER'):            'CCC',
    normalize('CA. CORRECTIONAL INSTITUTION'):      'CCI',
    normalize('CA CORRECTIONAL INSTITUTION'):       'CCI',
    normalize('CA. HEALTH CARE FACILITY'):          'CHCF',
    normalize('CA HEALTH CARE FACILITY'):           'CHCF',
    normalize('CDCR/CCHCS CA HEALTH CARE FACI'):    'CHCF',
    normalize('CDCR/CCHCS CA HEALTH CARE'):         'CHCF',
    normalize('CA. INSTITUTION FOR MEN'):           'CIM',
    normalize('CA INSTITUTION FOR MEN'):            'CIM',
    normalize('CA. INSTITUTION FOR WOMEN'):         'CIW',
    normalize('CA INSTITUTION FOR WOMEN'):          'CIW',
    normalize('CA. MEDICAL FACILITY'):              'CMF',
    normalize('CA MEDICAL FACILITY'):               'CMF',
    normalize("CA. MEN'S COLONY"):                  'CMC',
    normalize("CA MEN'S COLONY"):                   'CMC',
    normalize('CA. REHABILITATION CENTER'):         'CRC',
    normalize('CA REHABILITATION CENTER'):          'CRC',
    normalize('REHABILITATION CENTER'):             'CRC',
    normalize('CA. STATE PRISON - CORCORAN'):       'COR',
    normalize('CA STATE PRISON - CORCORAN'):        'COR',
    normalize('CA. STATE PRISON-CORCORAN'):         'COR',
    normalize('CA STATE PRISON-CORCORAN'):          'COR',
    normalize('CA. STATE PRISON - SACRAMENTO'):     'SAC',
    normalize('CA STATE PRISON - SACRAMENTO'):      'SAC',
    normalize('CA. STATE PRISON - SOLANO'):         'SOL',
    normalize('CA STATE PRISON - SOLANO'):          'SOL',
    normalize('CA. STATE PRISON - WASCO'):          'WSP',
    normalize('CA STATE PRISON - WASCO'):           'WSP',
    normalize('CALIPATRIA STATE PRISON'):           'CAL',
    normalize('CA. CITY CORR FACILITY'):            'CAC',  # closed 2019
    normalize('CA CITY CORR FACILITY'):             'CAC',
    normalize('CA CITY CORRECTIONAL FACILITY'):     'CAC',
    normalize('CA. CITY CORRECTIONAL FACILITY'):    'CAC',
    normalize('CENTINELA STATE PRISON'):            'CEN',
    normalize('CENTRAL CA. WOMENS FACILITY'):       'CCWF',
    normalize('CENTRAL CA WOMENS FACILITY'):        'CCWF',
    normalize('CORRECTIONAL TRAINING FACILITY'):    'CTF',
    normalize('CORR TRAINING FACILITY'):            'CTF',
    normalize('CSP - LOS ANGELES COUNTY'):          'LAC',
    normalize('DELANO II STATE PRISON'):            'KVSP',  # opened 2023 at former KVSP site
    normalize('FOLSOM STATE PRISON'):               'FOL',
    normalize('HIGH DESERT STATE PRISON'):          'HDSP',
    normalize('IRONWOOD STATE PRISON'):             'ISP',
    normalize('KERN VALLEY STATE PRISON'):          'KVSP',  # closed 2023, replaced by Delano II
    normalize('MULE CREEK STATE PRISON'):           'MCSP',
    normalize('NORTH KERN STATE PRISON'):           'NKSP',
    normalize('PELICAN BAY STATE PRISON'):          'PBSP',
    normalize('PLEASANT VALLEY STATE PRISON'):      'PVSP',
    normalize('PLEASANT VALLEY ST PRISON'):         'PVSP',
    normalize('R J DONOVAN CORR FACILITY'):         'RJD',
    normalize('SALINAS VALLEY STATE PRISON'):       'SVSP',
    normalize('SALINAS VALLEY ST. PRISON'):         'SVSP',
    normalize('SALINAS VALLEY ST PRISON'):          'SVSP',
    normalize('SAN QUENTIN STATE PRISON'):          'SQ',
    normalize('SIERRA CONSERVATION CENTER'):        'SCC',
    normalize('SUBSTANCE ABUSE TREAT-CORCORAN'):    'SATF',
    normalize('SUBSTANCE ABUSE TREAT FACILITY'):    'SATF',  # small PIA sub-entry
    normalize('VALLEY STATE PRISON'):               'VSP',
    normalize('VENTURA SCHOOL FOR GIRLS'):          None,    # youth / not a state prison
    normalize('NORTHERN CA. YOUTH CENTER'):         None,
    normalize('NORTHERN CA YOUTH CENTER'):          None,
}

PIA_SUFFIXES = (' - PIA', '-PIA', '- PIA')
CCHCS_INDICATOR = 'CDCR/CCHCS'

# Garbled or truncated names found in the 2025 PDFs → canonical form.
# Applied before grouping so these rows merge with their correct counterpart.
NAME_CORRECTIONS = {
    'C ENTRAL CA WOMENS FACILITY-PIA': 'CENTRAL CA WOMENS FACILITY-PIA',  # font garbling (Feb/Jun 2025)
    'CA INSTITUTION':                  'CA. INSTITUTION FOR WOMEN- PIA',   # truncated suffix (May 2025)
}


def strip_pia(name: str) -> str:
    """Remove PIA suffix variants and trailing whitespace/punctuation."""
    for suffix in PIA_SUFFIXES:
        if name.upper().endswith(suffix.upper()):
            return name[:len(name) - len(suffix)].rstrip(' -')
    return name


def get_cdcr_code(name: str) -> str:
    """Return CDCR code for a facility name, or empty string if unmapped."""
    base = strip_pia(name)
    # Direct lookup
    code = SCO_TO_CDCR.get(normalize(base))
    if code is not None:
        return code
    # Fallback: try truncated forms (e.g. "CA. STATE PRISON - CORCORAN -PIA")
    base_clean = re.sub(r'\s*-\s*PIA\s*$', '', base, flags=re.IGNORECASE).strip()
    code = SCO_TO_CDCR.get(normalize(base_clean))
    return code if code is not None else ''


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    repo_root = Path(__file__).parent.parent
    src = repo_root / 'data_sources' / 'facilities' / 'CDCR' / 'sco_staffing_2020-2026.csv'
    out = repo_root / 'data_sources' / 'facilities' / 'CDCR' / 'sco_staffing_2025_avg.csv'

    numeric_cols = ['full_time', 'part_time', 'intermittent', 'indeterminate', 'total']

    # Accumulate 2025 rows by facility name
    accum: dict[str, list[dict]] = defaultdict(list)
    with open(src) as f:
        for row in csv.DictReader(f):
            if '2025' not in row['date']:
                continue
            name = NAME_CORRECTIONS.get(row['sco_facility_name'], row['sco_facility_name'])
            accum[name].append(row)

    # Build averaged output rows
    out_rows = []
    for name, snapshots in sorted(accum.items()):
        is_pia = any(name.upper().endswith(s.upper()) for s in PIA_SUFFIXES)
        is_cchcs = name.upper().startswith(CCHCS_INDICATOR)
        cdcr_code = get_cdcr_code(name)

        means = {}
        for col in numeric_cols:
            vals = [int(r[col]) for r in snapshots if r[col] not in ('', None)]
            means[col] = round(sum(vals) / len(vals), 1) if vals else ''

        out_rows.append({
            'cdcr_code':       cdcr_code,
            'sco_facility_name': name,
            'is_pia':          is_pia,
            'is_cchcs':        is_cchcs,
            'n_snapshots':     len(snapshots),
            **means,
        })

    # Sort: code first, then name
    out_rows.sort(key=lambda r: (r['cdcr_code'] or 'ZZ', r['sco_facility_name']))

    fieldnames = ['cdcr_code', 'sco_facility_name', 'is_pia', 'is_cchcs',
                  'n_snapshots'] + numeric_cols

    with open(out, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    # Summary
    matched = sum(1 for r in out_rows if r['cdcr_code'])
    unmatched = [r['sco_facility_name'] for r in out_rows if not r['cdcr_code']]
    print(f'Wrote {len(out_rows)} rows → {out.relative_to(repo_root)}')
    print(f'  Mapped to cdcr_code: {matched} / {len(out_rows)}')
    if unmatched:
        print(f'  Unmatched ({len(unmatched)}):')
        for u in unmatched:
            print(f'    {repr(u)}')


if __name__ == '__main__':
    main()
