"""Robust casing normalizer for California carceral-facility names/addresses.

Background
----------
The base facilities data comes from FEMA RAPT in ALL CAPS. The build notebooks
(``create_facilities.ipynb`` -> ``ca_facilities.csv``,
``create_cdcr_facilities.ipynb`` -> ``cdcr_facilities.csv``) used to run a naive
``str.title()`` over the name/address/city columns. Python's ``.title()`` leaves
a family of predictable artifacts that flow downstream into the CA Carceral
Facility Heat Tracker:

    "WOMEN'S"  -> "Women'S"   (should be "Women's")
    "FCI DUBLIN" -> "Fci Dublin"  (should be "FCI Dublin")
    "MCCAIN ..." -> "Mccain ..."  (should be "McCain ...")
    "BRYAN II"  -> "Bryan Ii"     (should be "Bryan II")
    "... (CCFW)" -> "... (Ccfw)"  (should be "... (CCWF)" — FEMA transposed it)

This module replaces the naive title-casing with a *curated* normalizer built
from explicit sets/maps rather than a pile of one-off ``.replace()`` calls, so a
name like "O'Brien" (a real surname, not a possessive) survives untouched.

The public entry point is :func:`normalize_facility_name`, used for the name,
address, and city columns alike.
"""

from __future__ import annotations

import re

__all__ = ["normalize_facility_name"]


# --- Curated data -----------------------------------------------------------

# Institution acronyms that appear as standalone tokens in facility names and
# should be fully uppercased. Curated (do NOT auto-uppercase arbitrary short
# tokens) so ordinary words are never clobbered.
ACRONYMS = {
    "FCI",  # Federal Correctional Institution
    "USP",  # United States Penitentiary
    "MCC",  # Metropolitan Correctional Center
    "FMC",  # Federal Medical Center
    "FDC",  # Federal Detention Center
    "CCA",  # Corrections Corporation of America
    "RJD",  # R. J. Donovan
    "CIM",  # California Institution for Men
    "CMC",  # California Men's Colony
}

# "Mc" surnames whose letter after "Mc" must be capitalized. Curated because
# some "Mc…" tokens are acronyms (MCC, MCSP) rather than surnames — those are
# handled by ACRONYMS / the parenthetical-code logic, not here.
MC_SURNAMES = {
    "mccain",
    "mcfarland",
    "mcdonnell",
    "mccoy",
    "mcadams",
}

# Standalone Roman numerals to uppercase. Only multi-character numerals are
# listed: a bare "I"/"V"/"X" is left alone (it is usually the pronoun "I", a
# lone letter, or already correct).
ROMAN_NUMERALS = {"II", "III", "IV", "VI", "VII", "VIII", "IX"}

# Valid CDCR facility codes, verified against data/cdcr/cdcr_facilities.csv
# (the authoritative source). A parenthetical token in a name is only treated
# as a code — and uppercased — when it resolves into this set; otherwise the
# parenthetical is descriptive text (e.g. "(South)", "(Honor Farm)") and is
# left in title case.
VALID_CDCR_CODES = {
    "ASP", "CAC", "CAL", "CCI", "CCWF", "CEN", "CHCF", "CIM", "CIW", "CMC",
    "CMF", "COR", "CRC", "CTF", "CVSP", "FOL", "FWF", "HDSP", "ISP", "KVSP",
    "LAC", "MCSP", "NKSP", "PBSP", "PVSP", "RJD", "SAC", "SATF", "SCC", "SOL",
    "SQ", "SVSP", "VSP", "WSP",
}

# FEMA parenthetical codes that don't match CDCR's own code for the facility.
# Mirrors the fema_to_cdcr map in create_cdcr_facilities.ipynb so the visible
# code in ca_facilities.csv agrees with the authoritative cdcr_code column.
FEMA_CODE_FIX = {
    "CCFW": "CCWF",  # Central California Women's Facility: FEMA transposed the letters
    "FSP": "FOL",    # Folsom State Prison: FEMA uses FSP, CDCR uses FOL
}

# Possessive / contraction suffixes to lowercase after an apostrophe. Anything
# not in this set (a real name after the apostrophe, e.g. O'Brien, D'Angelo)
# keeps its capital.
_POSSESSIVE_RE = re.compile(r"'(S|T|D|M|LL|RE|VE)(?![A-Za-z])", re.IGNORECASE)
_PAREN_RE = re.compile(r"\(([^)]+)\)")
_TOKEN_SPLIT_RE = re.compile(r"(\s+)")
_ALPHA_ONLY_RE = re.compile(r"[^A-Za-z]")

# Ordinal suffix directly following digits (e.g. "14Th" -> "14th"). Scoped to
# digit+suffix so it never touches the "St"/"Rd" street-type abbreviations or
# directionals ("N"/"W").
_ORDINAL_RE = re.compile(r"\b(\d+)(ST|ND|RD|TH)\b", re.IGNORECASE)

# "PO Box" is title-cased to "Po Box"; restore the initialism.
_PO_BOX_RE = re.compile(r"\bPo Box\b", re.IGNORECASE)

# Missing space before an opening parenthesis (e.g. "Prison(PVSP)").
_PAREN_SPACING_RE = re.compile(r"(?<=\S)\(")


# --- Helpers ----------------------------------------------------------------

def _fix_possessives(s: str) -> str:
    """Lowercase possessive/contraction suffixes; leave real names alone."""
    return _POSSESSIVE_RE.sub(lambda m: "'" + m.group(1).lower(), s)


def _fix_ordinals(s: str) -> str:
    """Lowercase ordinal suffixes that directly follow digits (14Th -> 14th)."""
    return _ORDINAL_RE.sub(lambda m: m.group(1) + m.group(2).lower(), s)


def _apply_special(s: str) -> str:
    """Small unambiguous fixups: PO Box initialism, missing space before '('."""
    s = _PO_BOX_RE.sub("PO Box", s)
    s = _PAREN_SPACING_RE.sub(" (", s)
    return s


def _fix_parenthetical_codes(s: str) -> str:
    """Uppercase parenthetical CDCR codes (with FEMA corrections); leave
    descriptive parentheticals in title case."""
    def repl(m: "re.Match") -> str:
        inner = m.group(1).strip()
        code = FEMA_CODE_FIX.get(inner.upper(), inner.upper())
        if code in VALID_CDCR_CODES:
            return f"({code})"
        return m.group(0)

    return _PAREN_RE.sub(repl, s)


def _fix_token(token: str) -> str:
    """Uppercase acronyms/Roman numerals and fix Mc surnames for one token."""
    core = _ALPHA_ONLY_RE.sub("", token)
    if not core:
        return token

    upper = core.upper()
    if upper in ACRONYMS:
        return token.upper()
    if upper in ROMAN_NUMERALS:
        return token.upper()
    if token.isalpha() and token.lower() in MC_SURNAMES:
        return "Mc" + token[2:].capitalize()
    return token


# --- Public API -------------------------------------------------------------

def normalize_facility_name(value):
    """Return a cleanly-cased facility name/address/city.

    Applies title-case as a baseline, then repairs the artifact classes that
    ``str.title()`` produces: possessive suffixes, standalone Roman numerals,
    institution acronyms, "Mc" surnames, and parenthetical CDCR codes.

    Non-string input (None / NaN) is returned unchanged so it can be applied
    directly to a pandas Series.
    """
    if value is None:
        return value
    # pandas NaN is a float; guard without importing pandas here.
    if isinstance(value, float):
        return value

    s = str(value).title()
    s = _fix_possessives(s)
    s = _fix_ordinals(s)
    s = _apply_special(s)
    s = _fix_parenthetical_codes(s)
    parts = _TOKEN_SPLIT_RE.split(s)
    parts = [p if i % 2 else _fix_token(p) for i, p in enumerate(parts)]
    return "".join(parts)
