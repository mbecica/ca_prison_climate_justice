# Impact Analysis

Analysis notebooks and scripts are in this directory. Outputs are written to `data/`.

This work produces **summary impact estimates** — not full risk calculations. Full risk calculations (hazard × exposure × vulnerability) are the intended long-term direction of this repository; the data collected across `data_sources/` is structured to support that. The summary analysis here is scoped to near-term advocacy use for AB-2499.

## Heat Activation Days

Daily maximum temperatures at each CDCR state prison are sourced from gridMET (University of Idaho, 4km gridded daily tmax, 1991–2025). See `scrapers/extract_gridmet_heat.py`. Outputs in `data_sources/hazards/`:

| File | Description |
| :--- | :--- |
| `heat_activations_daily.csv` | Daily tmax (°F) and threshold flags per facility, 2016–2025 |
| `heat_activations_annual.csv` | Annual count of days over 90°F, days over 95°F, and Skarha 10° exceedance days per facility |
| `heat_activations_monthly.csv` | Monthly count of days over 90°F and days over 95°F per facility per year |

Outdoor temperature thresholds:

| Column | Definition | Note |
| :--- | :--- | :--- |
| `over_90f` / `days_over_90f` | Outdoor tmax ≥ 90°F | Corresponds to CDCR Heat Pathology Plan Stage I outdoor trigger |
| `over_95f` / `days_over_95f` | Outdoor tmax ≥ 95°F | Corresponds to Stage III outdoor threshold; **Stage III protocol is triggered by indoor temperature**, so this column is an outdoor proxy only |
| `skarha10` / `days_skarha10` | Outdoor tmax ≥ facility mean summer tmax + 10°F (baseline: 1991–2020 Jun–Aug mean) | Skarha et al. (2023) marginal mortality metric |

### Outdoor vs. Indoor Temperature Gap

The CDCR Heat Pathology Plan Stage I and Stage III thresholds are defined by **indoor** housing unit temperatures (≥ 90°F and ≥ 95°F respectively). Outdoor gridMET data is used here as a proxy for exposure and trend analysis, but outdoor temperatures systematically overstate the number of days that cross indoor thresholds.

Available evidence on the outdoor-to-indoor gap:

**CalMatters CPRA data (one unnamed prison, 2023–2024):**

| Year | Outdoor days ≥ 90°F | Indoor days ≥ 90°F | Indoor days ≥ 95°F |
| :--- | :--- | :--- | :--- |
| 2023 | 166 | 59 | 20 |
| 2024 | 182 | 86 | 46 |

Indoor days at ≥ 90°F were roughly 35–47% of outdoor days at the same threshold in these two years.

**OIG audit, August 2022–October 2023 (Corcoran, High Desert, Lancaster):**

| Prison | Housing units tested | Units with ≥ 1 day over 89°F | Most days over 89°F in a single unit |
| :--- | :--- | :--- | :--- |
| High Desert | 27 | 3 | 1 |
| Lancaster | 29 | 10 | 2 |
| Corcoran | 33 | 23 | 23 |

Source: California Office of the Inspector General, heat log audit.

## Summary Graphs

Interactive, print-readable D3 charts in `analysis/heat_activation_charts.html`:

- **Annual line chart** — total facility-days with outdoor tmax ≥ 90°F across all 32 active prisons per year, 2016–2025
- **Per-facility horizontal bar** — average annual days ≥ 90°F per facility over the 10-year period
- **Per-facility line chart** — days ≥ 90°F per facility per year; color encodes cumulative outdoor heat exposure (light gray = low, dark red = high); labeled facilities sampled by tier and population

Summary statistics shown at the top of the page:
- Total facility-days ≥ 90°F outdoor: 27,722
- Average annual facility-days ≥ 90°F: 2,772
- Facilities with any day ≥ 90°F: 32 of 32

**Facility coverage notes:**
- CAC (private facility) and FWF (co-located with FOL) are excluded from all heat analysis
- CVSP is included for 2016–2023 only (closed mid-2024)

## Population Impacts

_In progress._ Population exposure estimates applied to heat activation days, broken out by:

- Age bracket (50–59, 60–69, 70–79, 80+), using CDCR Population Data Set 2025
- CCHCS health risk category (P1/P2/medium/low risk tiers), using CCHCS IPC Dashboard 2025

## Future: Full Risk Calculations

The hazard indices, facility characteristics, and population data collected in this repository are structured to support hazard × exposure × vulnerability risk calculations across all four climate hazards (heat, flood, wildfire, drought) for all 357 California carceral facilities. This is the intended next phase of analysis.
