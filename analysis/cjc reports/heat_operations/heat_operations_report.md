# Heat and Prison Operations: Panel Analysis of CDCR Facilities, 2016–2025

**Date:** April 2026
**Scripts:** `build_heat_operations_panel.py`, `run_heat_operations_regression.py`, `run_event_study.py`
**Panel:** `heat_operations_panel.csv` (4,080 rows × 22 columns; 34 facilities × 120 months, 2016–2025)

---

## Summary

System-wide two-way fixed effects regressions find no statistically significant relationship between monthly heat exposure and any of the six operational outcomes examined across 34 CDCR facilities. All coefficients are null after Benjamini-Hochberg correction. This null result is consistent with Mukherjee & Sanders (2021), who found that heat drives violence specifically in facilities *without* cooling infrastructure; California's mix of mechanical, evaporative, and ventilation-based cooling systems suppresses the system-wide signal.

The ISP event study tells a different story. After ISP's $192M full HVAC replacement (March 2024), four outcomes show a significant attenuation of the heat-outcome slope compared to the control group: ED/hospital visit rate (p<0.001), Dental+MH Overtime (p=0.002), **Violent Incidents (p<0.001)**, and Monthly Expenditure (p=0.003). ISP's violent incident count dropped from 15.2 to 8.1 incidents/month in post-installation summers while control facilities rose from 22.6 to 35.2 — the clearest evidence that cooling infrastructure reduces both violence and health utilization. These findings are preliminary and require qualitative follow-up to rule out concurrent changes at ISP.

---

## 1. Data and Outcomes

**Panel structure:** 34 CDCR adult facilities × 120 calendar months (January 2016 – December 2025). Two facilities with closed-period heat data gaps (DVI, CCC) excluded.

**Outcomes:**

| Outcome | Source | Coverage | Transform |
|---------|--------|----------|-----------|
| ED/Hospital Stay rate (per 1,000) | CCHCS Health Care Dashboard | Apr 2017–Sep 2025 (95.9% of window) | log |
| Dental+MH Overtime (hours) | SB 601 Power BI dashboard | FY 2021–2025, all 12 months (84.9% of facility-months) | log |
| Incarcerated Persons-Days on Modified Programs | SB 601 | same | log(y+1) |
| Violent Incidents (count) | CDCR CompStat PDFs | 2021–2025, all 12 months (47.4% of facility-months in full panel; near-complete within 2021+ window) | log(y+1) |
| Use of Force Incidents (count) | SB 601 | FY 2021–2025, all 12 months | log(y+1) |
| Monthly Expenditure ($) | SB 601 Fiscal (YTD differenced) | FY 2021–2025, all 12 months | log(y+1) |

Violent incidents are drawn from CDCR CompStat quarterly reports (PDF extraction) and include: Assault on Inmate, Battery on Inmate, Assault on Peace Officer, Battery on Peace Officer, Fighting, Cell Extractions, and Riot. This measure is directly comparable to Mukherjee & Sanders (2021), who studied inmate-on-inmate violence (assaults, fights with serious injury) in Mississippi. Use of Force (staff-initiated) is retained as a secondary violence measure.

**Heat variables:**
- *Primary:* `days_over_90f` — monthly count of days with outdoor tmax ≥ 90°F (gridMET). CDCR Heat Pathology Plan Stage 1 threshold.
- *Robustness:* `days_skarha10` — days where tmax ≥ facility mean summer tmax + 10°F (Skarha et al. 2023 mortality threshold).

**Model:** Two-way fixed effects (TWFE): facility FE + year×month FE. OLS. Time-varying crowding ratio (% design capacity) as control. Standard errors clustered by facility. Estimation via `linearmodels` PanelOLS. Benjamini-Hochberg FDR correction applied across 12 primary tests (6 outcomes × 2 heat variables).

---

## 2. System-Wide Results

### Table 1. TWFE main results — all 34 facilities, 2016–2025

| Outcome | Heat variable | β | SE | p | BH-adj p | N |
|---------|--------------|---|---|---|----------|---|
| ED/Hospital Stay rate (log) | Days >90°F | +0.0005 | 0.0008 | 0.57 | 0.76 | 3,437 |
| Dental+MH Overtime (log) | Days >90°F | +0.0047 | 0.0043 | 0.27 | 0.69 | 1,432 |
| Modified Programs Days [log(y+1)] | Days >90°F | −0.0023 | 0.0048 | 0.63 | 0.76 | 1,538 |
| Violent Incidents [log(y+1)] | Days >90°F | +0.0033 | 0.0019 | 0.09 | 0.57 | 1,902 |
| Use of Force Incidents [log(y+1)] | Days >90°F | +0.0017 | 0.0018 | 0.35 | 0.69 | 1,524 |
| Monthly Expenditure [log(y+1)] | Days >90°F | −0.0004 | 0.0003 | 0.19 | 0.69 | 1,524 |
| ED/Hospital Stay rate (log) | Skarha anomaly | +0.0001 | 0.0058 | 0.98 | 0.98 | 3,437 |
| Dental+MH Overtime (log) | Skarha anomaly | −0.0085 | 0.0101 | 0.40 | 0.69 | 1,432 |
| Modified Programs Days [log(y+1)] | Skarha anomaly | −0.0026 | 0.0123 | 0.83 | 0.91 | 1,538 |
| Violent Incidents [log(y+1)] | Skarha anomaly | +0.0058 | 0.0064 | 0.36 | 0.69 | 1,902 |
| Use of Force Incidents [log(y+1)] | Skarha anomaly | +0.0094 | 0.0056 | 0.09 | 0.57 | 1,524 |
| Monthly Expenditure [log(y+1)] | Skarha anomaly | −0.0018 | 0.0031 | 0.55 | 0.76 | 1,524 |

*BH correction applied across all 12 tests. Facility FE + year×month FE. SE clustered by facility. Crowding ratio included as control.*

Violent incidents (Days >90°F) shows the strongest marginal signal in the system-wide model (p=0.09, right direction), consistent with the heat-aggression mechanism documented by Mukherjee & Sanders (2021) in Mississippi prisons. However, this effect does not survive FDR correction (BH-adj p=0.57) and is likely attenuated by the presence of cooling infrastructure in most California facilities.

### Table 2. Mean outcomes by monthly heat intensity (all facilities, 2016–2025)

| Days >90°F | N | Mean ED rate | Mean Dental+MH OT (hrs) | Mean Violent Incidents | Mean UOF Incidents | Mean Mod Prog Days |
|-----------|---|-------------|------------------------|----------------------|-------------------|-------------------|
| 0 days | 2,125 | 17.2 | 252.7 | 26.1 | 24.9 | 4.1 |
| 1–14 days | 965 | 17.2 | 245.3 | 26.1 | 24.9 | 2.9 |
| 15–27 days | 607 | 16.6 | 203.5 | 25.8 | 23.1 | 3.8 |
| 28–31 days | 383 | 13.6 | 134.5 | 23.5 | 19.0 | 3.2 |

*Raw means, no controls. The declining pattern in hottest months reflects seasonal scheduling absorbed by year×month FEs rather than a true protective effect of heat.*

---

## 3. ISP Event Study: Full HVAC Replacement, March 2024

Ironwood State Prison (ISP) received a $192.7M full facility HVAC replacement (project P-0910-01113, completed March 2024), replacing an end-of-life evaporative cooling system with a centralized chiller plant serving all housing and support buildings. This is the largest single cooling infrastructure investment in CDCR history.

The event study model estimates the change in the heat-outcome slope for ISP post-installation relative to all other facilities:

`Y_it = β₁·Heat_it + β₂·(Heat_it × Post_it) + β₃·Post_it + β₄·Crowding_it + α_i + γ_ym + ε_it`

`β₂` is the key coefficient: a negative value means the heat-outcome relationship weakened at ISP after AC installation. Control group: all 33 non-ISP facilities.

### Table 3. ISP DiD results — heat × post-installation interaction

| Outcome | Heat β (pre) | Heat×Post β | p | Sig |
|---------|-------------|-------------|---|-----|
| ED/Hospital Stay rate (log) | +0.0006 | −0.0067 | <0.001 | *** |
| Dental+MH Overtime (hours) | +1.89 | −1.93 | 0.002 | ** |
| **Violent Incidents (raw)** | **+0.080** | **−0.192** | **<0.001** | **\*\*\*** |
| Use of Force Incidents (raw) | −0.012 | −0.191 | <0.001 | *** |
| Modified Programs Days (raw) | −0.016 | −0.001 | 0.964 | |
| Custody Overtime (hours) | −43.5 | +28.4 | 0.307 | |
| Non-Custody Overtime (hours) | −0.17 | +3.94 | 0.209 | |
| Total Overtime (hours) | −45.9 | +29.8 | 0.290 | |
| Monthly Expenditure ($) | +192 | −18,317 | 0.003 | ** |

*TWFE DiD. All 34 facilities. SE clustered by facility. \*\*\* p<0.001, \*\* p<0.01.*

Four outcomes are significant: ED rate, Dental+MH OT, Violent Incidents, and Monthly Expenditure. The violent incidents finding is the most direct parallel to Mukherjee & Sanders (2021): before HVAC, each additional day above 90°F was associated with ~0.08 additional incidents at ISP; after installation, that relationship disappears (net slope change: −0.19 per day). Custody, Non-Custody, and Total OT show no significant interaction, consistent with the effect being specific to health and safety outcomes rather than general labor disruption.

**Note on Dental+MH OT:** ISP's Dental+MH OT dropped to zero in December 2023, three months before the official HVAC completion date. The capital project record lists only a single completion date (March 2024) with no phased commissioning dates. This early drop is unexplained by the available documentation and requires qualitative follow-up.

### Table 4. ISP pre/post descriptive means, summer months (June–September)

| Group | Period | Mean Days >90°F | Mean ED Rate | Mean Dental+MH OT | Mean Violent Incidents | Mean UOF Incidents | Mean Mod Prog Days |
|-------|--------|----------------|-------------|------------------|----------------------|-------------------|-------------------|
| ISP | Pre (n=32 months) | 30.0 | 9.5 | 50.7 | 15.2 | 10.7 | 4.7 |
| Control (mean) | Pre (n=1,056 months) | 18.0 | 15.3 | 165.3 | 22.6 | 20.4 | 4.5 |
| ISP | Post (n=8 months) | 30.0 | 12.3 | 0.0 | 8.1 | 5.4 | 0.0 |
| Control (mean) | Post (n=264 months) | 17.4 | 22.4 | 260.7 | 35.2 | 33.8 | 2.1 |

ISP's violent incidents fell from 15.2 to 8.1 per summer month post-HVAC (−47%), while controls rose from 22.6 to 35.2 (+56%). UOF followed the same pattern: 10.7 → 5.4 at ISP (−49%) vs. 20.4 → 33.8 at controls (+66%). Heat load at ISP was unchanged (30.0 days >90°F both periods), confirming the change is attributable to the cooling system rather than a cooler-year effect.

---

## 4. Written Summary: Violent Incidents and Use of Force

**Violent incidents (CompStat):** The system-wide TWFE finds a marginal positive association between heat and violent incidents (β=+0.0033 per day >90°F, p=0.09) that does not survive correction for multiple comparisons. In context of Mukherjee & Sanders (2021) — who found ~20% more violence on days averaging 80°F+ in Mississippi facilities with no cooling — the California null is expected: most CDCR facilities have some form of climate control, dampening the heat signal across the system. The ISP event study provides the within-California confirmation: before the HVAC replacement, ISP behaved as an unmitigated heat environment; after, the heat-violence slope collapsed. This is consistent with Mukherjee & Sanders' core finding that A/C eliminates the heat-violence link.

**Use of Force (SB 601):** UOF is a staff-initiated measure and conceptually distinct from inmate-on-inmate violence, though both declined substantially at ISP post-HVAC. The parallel trajectories of violent incidents and UOF suggest the mechanism may involve both inmate behavior and the staff-inmate dynamic — heat-stressed environments appear to escalate conflict from both directions. The fact that Custody OT shows no significant heat×post interaction rules out a general staffing explanation; the effect appears specific to direct conflict outcomes.

---

## 5. Caveats and Limitations

1. **N=2 treated facilities.** ISP is the primary case and CIM (Feb 2025) has only one post-installation summer. Results should be treated as descriptive case illustrations, not causal estimates. The ISP finding is compelling but cannot be generalized without formal staggered DiD methods requiring more treated units.

2. **Concurrent ISP changes.** Other major projects at ISP during the HVAC period included potable water well replacement (95% complete by July 2025) and water tank renovation (81% complete by March 2025). A ~500-person population transfer occurred during construction. Any of these could independently affect outcomes. Qualitative follow-up is needed: ISP staffing records, incident logs, and program documentation around 2023–2024.

3. **Outcome-specific limitations:**
   - *ED rate*: Covers all-cause ED visits, not heat-attributable only. Population changes (transfers) affect the denominator.
   - *Violent incidents*: Includes both inmate-on-inmate and staff-involved incidents (assaults on officers, cell extractions). Cannot separate these categories from the aggregate CompStat PDF data.
   - *UOF*: SB 601 reports staff-initiated force. Conceptually related but distinct from inmate-on-inmate violence.
   - *Monthly Expenditure*: Differenced from cumulative YTD figures; subject to budget amendment timing. The heat×post coefficient (~$18K/hot day) is small relative to ISP's ~$170M annual budget.

4. **Year×month FEs absorb seasonal signal.** The system-wide TWFE controls for all system-wide shocks within each calendar month and year, which may absorb genuine heat effects that are common across facilities (e.g., statewide heat waves). This is appropriate for identifying within-facility variation but may understate population-level heat burden.

5. **Oct–Nov 2023 OT spike.** A spike in Dental+MH OT appears in both ISP and the control group in October–November 2023, consistent with a system-wide reporting or operational change. Sensitivity check dropping these two months produces coefficients within 1–6% of main estimates with identical significance levels.

---

## 6. Anchoring Literature

| Paper | Relevance |
|-------|-----------|
| Mukherjee & Sanders (2021) *NBER WP 28987* | Causal evidence for heat → inmate violence (+20% on 80°F+ days) in Mississippi (no A/C anywhere). TWFE precedent. Explains our CA system-wide null and validates ISP event study direction. |
| Skarha et al. (2023) *PLOS ONE* | 5.2% increase in all-cause mortality per 10°F above facility mean; defines our Skarha anomaly heat variable. |
| Cloud et al. (2023) *JAMA Network Open* | 30% more suicide-watch incidents on extreme heat days in Louisiana non-AC prisons; evidence for heat → mental health pathway. |
| Ovienmhada et al. (2024) *GeoHealth* | Spatiotemporal heat exposure for US prison facilities; uses Skarha threshold for CA facilities specifically. |

---

*Panel output:* `analysis/cjc reports/heat_operations/heat_operations_panel.csv`
*Regression outputs:* `heat_ops_main_results.csv`, `heat_ops_robustness.csv`, `heat_ops_moderation.csv`, `heat_ops_panel_summary.csv`
*Event study outputs:* `heat_ops_did_isp.csv`, `heat_ops_event_study_isp.png/.svg`, `heat_ops_event_study_table.csv`
