# CDCR TPOP-1 Population Report Scraper

`extract_tpop1.py` parses CDCR Monthly/Weekly Total Population Report PDFs (SOMS-TPOP-1) into two structured CSVs.

## Usage

```bash
# From repo root — requires the data_science conda env (pandas, pdfplumber)
conda run -n data_science python3 scrapers/extract_tpop1.py
```

Outputs written to `data_sources/facilities/CDCR/`:
- `tpop1_summary.csv` — Total CDCR Population table (page 1)
- `tpop1_institutions.csv` — Institution Population Detail table (page 2)

## Source PDFs

| Period | Format | Location | Naming |
| :--- | :--- | :--- | :--- |
| 2019–2026 | Monthly | `cdcr_population_pdfs/` | `Tpop1d{YYMM}.pdf` (standard); a few files use `Tpop1d{YYMMDD}.pdf` or `Tpop1d{YYMM}-1.pdf` |
| 2015–2018 | Weekly | `cdcr_population_pdfs/tpop_weekly/{YYYY}/` | `Tpop1d{YYMMDD}.pdf` |

**Weekly 2015–2018 selection:** Only the last weekly file of each calendar month is used, to match monthly reporting cadence. Files are grouped by `YYMM` from the filename and the lexicographically last file per group is selected (e.g., January 2018 → `Tpop1d180131.pdf`).

**Total: 135 months** (2015-01 through 2026-03), one row-set per month in each output CSV.

## PDF Format Variants

### Page 1 — Total CDCR Population

Two distinct formats:

**Format A** (monthly 2019+, weekly 2018): standard layout
```
A. Total In-Custody/CRPP Supervision  126,836  -873  -2,721
1. Institution/Camps                  117,230  -707   -197  89,763  130.6  122,302
Total CDCR Population                 183,103  -367   +340
```
Column order: label | population | change_last_period | change_last_year | [design_capacity | pct_occupied | staffed_capacity]

**Format B** (weekly 2015–2017): older layout with FELON/OTHER + CIVIL ADDICT + TOTAL columns; section headers and aggregate totals use a typewriter overprint underline technique decoded at the character level
```
(MEN, Subtotal)   116,796  1  116,797  -644  -0.5
INSTITUTIONS      112,821  1  112,822  -641  -0.5  82,707  136.4  123,183
```
Column order: label | felon/other | civil_addict | total | change_no | change_pct | [design | pct | staffed]

> In Format B, `change_last_period` stores the year-over-year absolute change (not week-over-week), and `change_last_year` is null.

### Page 2 — Institution Population Detail

Two distinct formats:

**Format A** (monthly 2019+, weekly 2018): full institution names, Male/Female section headers
```
Male Institutions
Avenal State Prison (ASP)   4,110  2,920  140.8  4,370
...
Female Institutions
Central California Women's Facility (CCWF)  2,812  2,004  140.3  2,964
```
Column order: name (code) | felon/other | design_capacity | pct_occupied | staffed_capacity

**Format B** (weekly 2015–2017): ACRONYM-first rows, section totals decoded from overprint characters; includes Civil Addict column (almost always zero or 1)
```
MALE
ASP (Avenal SP)  4,129  4,129  2,920  141.4  4,702
CMC (CA Men's Colony)  4,058  1  4,059  3,838  105.8  4,668   ← civil addict = 1
```
Column order: code (name) | felon/other | [civil_addict] | total | design_capacity | pct_occupied | staffed_capacity

Institution names differ by format: short names in 2015–2017 (e.g., "Avenal SP") vs. full names in 2018+ (e.g., "Avenal State Prison").

## Output Fields

### `tpop1_summary.csv`

| Field | Description |
| :--- | :--- |
| `report_date` | Report as-of date (YYYY-MM-DD) |
| `row_label` | Row label from the table (e.g., `A. Total In-Custody/CRPP Supervision`, `1. Institution/Camps`, `Total CDCR Population`) |
| `population` | Population count for that row (felon/other in Format A; total including civil addict in Format B) |
| `change_last_period` | Change since last month (Format A monthly), last week (Format A weekly 2018), or last year absolute (Format B 2015–2017) |
| `change_last_year` | Change since same month prior year; null for 2015–2017 Format B rows |
| `design_capacity` | Design capacity; only present for institution/camp aggregate rows |
| `pct_occupied` | Percent occupied; only present for institution/camp aggregate rows |
| `staffed_capacity` | Staffed capacity; only present for institution/camp aggregate rows |

Rows per month: 20–33.

### `tpop1_institutions.csv`

| Field | Description |
| :--- | :--- |
| `report_date` | Report as-of date (YYYY-MM-DD) |
| `cdcr_code` | CDCR institution acronym (e.g., `ASP`, `SQ`) |
| `institution_name` | Institution name. Short names (e.g., "Avenal SP") in 2015–2017; full names (e.g., "Avenal State Prison") in 2018+. |
| `gender` | `Male` or `Female` if the PDF has gendered sections; null for 2021-12-31+ when CDCR switched to alphabetical listing |
| `felon_other` | Felon/other population count |
| `design_capacity` | Design capacity |
| `pct_occupied` | Percent occupied (felon_other / design_capacity × 100) |
| `staffed_capacity` | Staffed capacity |

Institutions per month: 31–40 (varies as facilities opened, closed, or temporarily split populations). 35 unique institution codes across all months: ASP, CAL, CCC, CCI, CCWF, CEN, CHCF, CIM, CIW, CMC, CMF, COR, CRC, CTF, CVSP, DVI, FOL, FWF, HDSP, ISP, KVSP, LAC, MCSP, NKSP, PBSP, PVSP, RJD, SAC, SATF, SCC, SOL, SQ, SVSP, VSP, WSP.

**Note on FOL (Folsom State Prison):** FOL appears twice per month when gender sections are present — once for the male population and once for the female population housed there. Use the `gender` column to distinguish them.

## Known Limitations

- **Short institution names 2015–2017:** The older weekly format uses abbreviated names. These are not normalized to the full names used in monthly reports.
- **`change_last_period` semantics vary:** This column means different things depending on the source file (see format notes above). Do not compare across the 2018/2019 boundary without accounting for this.
