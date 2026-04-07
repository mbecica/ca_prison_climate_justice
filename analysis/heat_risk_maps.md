# Heat Risk Index Maps

`analysis/heat_risk_maps.html` — interactive D3 map report showing all components of the CDCR heat risk index for 31 state prisons, plus VCP comparison and weighting sensitivity maps.

## Maps

### Hazard (2 maps)
Historic and mid-century hazard scores. Equal-weight composite of Cal-Adapt days over 90°F, VCP hot nights (98th pctl), and CalEnviroScreen AQI. Normalized 0–1 cross-period so current and mid-century are directly comparable on the same scale.

### Exposure & Vulnerability (2 maps)
Static across time periods (both use 2025 data).

- **Exposure**: indoor 78°F days (2025), indoor/outdoor thermal ratio, UHI (Benz & Burney 2021), inverted AC fraction
- **Vulnerability**: CCHCS medical acuity (P1+P2+medium), age 50+, EOP, DPP, race/POC

### Full Risk Index (2 maps)
Historic and mid-century full risk scores (0–100). Risk = Hazard × Exposure × Vulnerability; normalized cross-period.

### VCP Comparison & Weighting Sensitivity (4 maps)

- **VCP community ExHeatHealth_Idx** — average VCP heat-health index across adjacent non-institutional census tracts (Pct_GroupQuarters ≤ 25%). Reflects community-facing heat risk in surrounding geography.
- **Rank divergence** — our risk rank minus community VCP rank. Diverging red/blue scale: red = our index ranks the facility at higher risk than VCP ranks surrounding community; blue = VCP ranks surrounding community higher. Low correlation (Spearman r=−0.17) supports the argument for a prison-specific framework.
- **Max rank swing** — maximum difference in rank position across three weighting schemes (equal multiplicative, additive 25/25/50, multiplicative V²). CHCF (swing=16) and ISP (swing=10) are the most sensitive; top 5 facilities are stable across all schemes.
- **Additive 25/25/50 score** — Ovienmhada (2024) vulnerability-upweighted variant. CHCF rises from rank 22 to rank 6 under this scheme due to high medical complexity despite zero indoor heat days (full AC).

## Data Sources

| Layer | Source file |
| :--- | :--- |
| Risk scores | `data/CDCR_heat_risk_index.csv` |
| Sensitivity & VCP comparison | `data/CDCR_heat_risk_sensitivity.csv` |
| CA outline | `data/ca_outline_simple.json` |
| Facility coordinates | `data/cdcr_facilities.csv` |
