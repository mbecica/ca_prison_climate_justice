# Impact Analysis

Analysis notebooks and scripts are in this directory. Outputs are written to `data/`.

This work produces **summary impact estimates** — not full risk calculations. Full risk calculations (hazard × exposure × vulnerability) are the intended long-term direction of this repository; the data collected across `data_sources/` is structured to support that. The summary analysis here is scoped to near-term advocacy use for AB-2499.

## Heat Activation Days

Daily maximum temperatures at each CDCR state prison are sourced from gridMET (University of Idaho, 4km gridded daily tmax, 1991–2025). See `scrapers/extract_gridmet_heat.py`. Outputs in `data_sources/hazards/`:

| File | Description |
| :--- | :--- |
| `heat_activations_daily.csv` | Daily tmax (°F) and activation flags per facility, 2016–2025 |
| `heat_activations_annual.csv` | Annual count of Stage 1, Stage 3, and Skarha 10° exceedance days per facility |
| `heat_activations_monthly.csv` | Monthly count of Stage 1 and Stage 3 days per facility per year |

Activation thresholds:

| Metric | Definition | Source |
| :--- | :--- | :--- |
| `stage1` | Outdoor tmax ≥ 90°F | CDCR Heat Pathology Plan Stage I |
| `stage3` | Outdoor tmax ≥ 95°F | CDCR Heat Pathology Plan Stage III |
| `skarha10` | Outdoor tmax ≥ facility mean summer tmax + 10°F (baseline: 1991–2020 Jun–Aug mean) | Skarha et al. (2023) marginal mortality metric |

## Summary Graphs

Print-readable figures produced in `analysis/heat_activation_graphs.ipynb`:

- Total Stage 1 and Stage 3 heat days across all CDCR facilities, 2016–2025
- Total Stage 3 days per facility, 2016–2025

## Population Impacts

_In progress._ Population exposure estimates applied to heat activation days, broken out by:

- Age bracket (50–59, 60–69, 70–79, 80+), using CDCR Population Data Set 2025
- CCHCS health risk category (P1/P2/medium/low risk tiers), using CCHCS IPC Dashboard 2025

## Future: Full Risk Calculations

The hazard indices, facility characteristics, and population data collected in this repository are structured to support hazard × exposure × vulnerability risk calculations across all four climate hazards (heat, flood, wildfire, drought) for all 357 California carceral facilities. This is the intended next phase of analysis.
