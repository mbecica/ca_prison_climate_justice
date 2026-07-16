# CDCR specialized mental health bed reports

Source PDFs for `scrapers/extract_specialized_beds.py`, downloaded 2026-05-01.
These files are kept out of git — download them from the sources below into
this directory (keep the `YYYY-MM-DD_` filename prefix; it is parsed for the
report date).

## Sources

**Monthly PIP census, Coleman PIP waitlist, and MHCB census/waitlist reports**
Posted monthly (new reports appear under the same naming pattern) on the CCHCS
Reports & Court Orders page:
https://cchcs.ca.gov/reports/

- section "CDCR Psychiatric Inpatient Programs (PIP) Coleman Patient Census and Waitlist Report" — paired monthly PDFs, e.g.
  `https://cchcs.ca.gov/wp-content/uploads/sites/60/2026-06-22_PIP-Census-Report.pdf`
  `https://cchcs.ca.gov/wp-content/uploads/sites/60/2026-06-22_CDCR-PIP-Coleman-Patient-Census-and-Waitlist-Report.pdf`
- section "CDCR Mental Health Crisis Bed Patient Census and Waitlist Report", e.g.
  `https://cchcs.ca.gov/wp-content/uploads/sites/60/2026-06-22_CDCR-Mental-Health-Crisis-Bed-Patient-Census-and-Waitlist.pdf`

Reports held here: Oct 2025, Nov 2025, Dec 2025, Jan 2026 (+ Mar 2026 PIP
census only). Earlier report dates used slightly different filenames
(`PIP-Census-Rpt`, `CDCR-PIP-Waitlist`, `CDCR-MHCB-Court-Report`); the scraper
globs all variants.

**Fall 2025 Mental Health Bed Need Study**
https://cchcs.ca.gov/wp-content/uploads/sites/60/Fall-2025-Mental-Health-Bed-Need-Study.pdf
(newer editions, e.g. Spring 2026, are posted on the same reports page)

**MHSDS Map (Mental Health Services Delivery System), revised 2021-07-02**
https://www.cdcr.ca.gov/bph/wp-content/uploads/sites/161/2021/10/MHSDS-Map-2021.07.02.pdf
