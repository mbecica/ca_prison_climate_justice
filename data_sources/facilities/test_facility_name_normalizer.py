"""Unit tests for facility_name_normalizer.

Run with:  python -m pytest data_sources/facilities/test_facility_name_normalizer.py
       or:  python data_sources/facilities/test_facility_name_normalizer.py
"""

from facility_name_normalizer import normalize_facility_name as N


CASES = [
    # --- possessives / contractions (lowercase the suffix) ---
    ("Tulare County Men'S Correctional Facility",
     "Tulare County Men's Correctional Facility"),
    ("Women'S", "Women's"),
    ("Charlie'S Place Juvenile Day Reporting Center",
     "Charlie's Place Juvenile Day Reporting Center"),
    ("19005 Wiley'S Well Road", "19005 Wiley's Well Road"),

    # --- real apostrophe-names must SURVIVE (not lowercased) ---
    ("O'Brien", "O'Brien"),
    ("D'Angelo Correctional Facility", "D'Angelo Correctional Facility"),
    ("O'Neill Hall", "O'Neill Hall"),

    # --- Roman numerals (uppercase standalone tokens) ---
    ("Carl F. Bryan Ii Juvenile Hall", "Carl F. Bryan II Juvenile Hall"),
    ("Fci Victorville Medium Ii", "FCI Victorville Medium II"),
    ("Fci Victorville Medium I", "FCI Victorville Medium I"),  # bare I untouched

    # --- institution acronyms (curated set) ---
    ("Fci Dublin", "FCI Dublin"),
    ("Usp Atwater", "USP Atwater"),
    ("Mcc San Diego", "MCC San Diego"),
    ("Herlong Fci Camp", "Herlong FCI Camp"),

    # --- Mc surnames (curated) ---
    ("Mccain Valley Conservation Camp #21", "McCain Valley Conservation Camp #21"),
    ("Mcfarland Female Community Reentry Facility",
     "McFarland Female Community Reentry Facility"),
    ("1500 S Mcdonnell Ave", "1500 S McDonnell Ave"),
    ("31801 Mccoy Rd", "31801 McCoy Rd"),
    ("17148 Mcadams Creek Road", "17148 McAdams Creek Road"),

    # --- parenthetical CDCR codes (authoritative, uppercase) ---
    ("Central California Women'S Facility (Ccfw)",  # transposition bug fix
     "Central California Women's Facility (CCWF)"),
    ("California Men'S Colony (Cmc)", "California Men's Colony (CMC)"),
    ("Folsom Women'S Facility (Fwf)", "Folsom Women's Facility (FWF)"),
    ("Mule Creek State Prison (Mcsp)", "Mule Creek State Prison (MCSP)"),
    ("Folsom State Prison (Fsp)", "Folsom State Prison (FOL)"),  # FEMA->CDCR fix
    ("San Quentin State Prison (Sq)", "San Quentin State Prison (SQ)"),

    # --- descriptive parentheticals must NOT be uppercased ---
    ("Santa Clara County Main Jail Complex (South)",
     "Santa Clara County Main Jail Complex (South)"),
    ("San Joaquin County Jail (Honor Farm)",
     "San Joaquin County Jail (Honor Farm)"),
    ("Ventura County Pre-Trial Detention Facility (Main Jail)",
     "Ventura County Pre-Trial Detention Facility (Main Jail)"),

    # --- combinations / idempotence ---
    ("Fci Dublin Camp", "FCI Dublin Camp"),
    ("MCFARLAND FEMALE COMMUNITY REENTRY FACILITY",  # raw ALL CAPS input
     "McFarland Female Community Reentry Facility"),
    ("Central California Women's Facility (CCWF)",  # already-clean -> unchanged
     "Central California Women's Facility (CCWF)"),
]


def test_cases():
    failures = []
    for src, expected in CASES:
        got = N(src)
        if got != expected:
            failures.append(f"  {src!r}\n    got:      {got!r}\n    expected: {expected!r}")
    assert not failures, "Normalizer mismatches:\n" + "\n".join(failures)


def test_none_and_nan_passthrough():
    assert N(None) is None
    assert N(float("nan")) != N(float("nan"))  # NaN passes through unchanged


if __name__ == "__main__":
    test_cases()
    test_none_and_nan_passthrough()
    print(f"OK — {len(CASES)} name cases + passthrough checks passed.")
