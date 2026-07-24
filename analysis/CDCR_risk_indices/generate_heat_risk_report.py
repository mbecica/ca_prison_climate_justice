#!/usr/bin/env python3
"""
Generate CDCR Heat Risk Index report:
  - PNG maps (risk, hazard, exposure, vulnerability — current + mid-century)
  - Markdown report: analysis/cjc reports/heat_risk_index/heat_risk_index_report.md

Run from project root:
  conda run -n data_science python3 analysis/CDCR_risk_indices/generate_heat_risk_report.py
"""

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT    = Path('.')
OUT_DIR = ROOT / 'analysis/cjc reports/heat_risk_index'
OUT_DIR.mkdir(parents=True, exist_ok=True)

INDEX   = ROOT / 'data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv'
CA_GEO  = ROOT / 'data/ca_outline_simple.json'
SENS    = ROOT / 'data/cdcr/CDCR_heat_risk_sensitivity.csv'

df_all  = pd.read_csv(INDEX)
ca      = gpd.read_file(CA_GEO)

cur  = df_all[df_all['time_period'] == 'current'].set_index('cdcr_code')
mc   = df_all[df_all['time_period'] == 'midcentury'].set_index('cdcr_code')

# ── Color palette ─────────────────────────────────────────────────────────────
TIER_COLORS = {
    'Highest':  '#7a1010',
    'High':     '#c44020',
    'Moderate': '#e89050',
    'Lowest':   '#c8c0a8',
}
TIER_ORDER = ['Highest', 'High', 'Moderate', 'Lowest']

SCORE_CMAP = 'YlOrRd'

# ── Helper: draw one facility-bubble map ─────────────────────────────────────
def draw_bubble_map(ax, data, score_col, title, cmap=SCORE_CMAP,
                    vmin=None, vmax=None, category_col=None, size_col='average_2025_population'):
    """
    Plot CA outline + facility bubbles sized by population, colored by score_col.
    If category_col is provided, color bubbles by tier instead of continuous score.
    """
    ca.plot(ax=ax, color='#f0ede6', edgecolor='#bbb', linewidth=0.6)

    pop = data[size_col].fillna(3000)
    sizes = (pop / pop.max() * 220 + 30).values

    if category_col is not None:
        colors = data[category_col].map(TIER_COLORS).fillna('#c8c0a8')
        sc = ax.scatter(data['longitude'], data['latitude'],
                        s=sizes, c=colors, zorder=5,
                        edgecolors='white', linewidths=0.5, alpha=0.92)
    else:
        vmin_ = vmin if vmin is not None else data[score_col].min()
        vmax_ = vmax if vmax is not None else data[score_col].max()
        sc = ax.scatter(data['longitude'], data['latitude'],
                        s=sizes, c=data[score_col], cmap=cmap,
                        vmin=vmin_, vmax=vmax_, zorder=5,
                        edgecolors='white', linewidths=0.5, alpha=0.92)

    ax.set_xlim(-124.6, -113.8)
    ax.set_ylim(32.4, 42.1)
    ax.set_title(title, fontsize=9, fontweight='bold', pad=5)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.spines[:].set_visible(False)

    return sc


# ═══════════════════════════════════════════════════════════════════════════════
# MAP 1: Risk tier — current vs. mid-century side-by-side
# ═══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(11, 6))
fig.suptitle('CDCR Heat Risk Index — Risk Tier by Facility', fontsize=11, fontweight='bold', y=0.98)

for ax, data, label in [
    (axes[0], cur, 'Historic (1991–2020)'),
    (axes[1], mc,  'Mid-century (2041–2070)'),
]:
    draw_bubble_map(ax, data, 'risk_score', label, category_col='risk_category')

# Legend
patches = [mpatches.Patch(color=TIER_COLORS[t], label=t) for t in TIER_ORDER]
size_legend = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#888',
           markersize=s, label=lbl)
    for s, lbl in [(5, '2,000'), (9, '4,000'), (13, '6,000+')]
]
fig.legend(handles=patches + size_legend, loc='lower center',
           ncol=4, fontsize=8, frameon=False,
           title='Risk tier (bubble size = 2025 avg population)',
           title_fontsize=8)
plt.tight_layout(rect=[0, 0.06, 1, 0.97])
map1_path = OUT_DIR / 'map_risk_tier.png'
fig.savefig(map1_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved {map1_path}')


# ═══════════════════════════════════════════════════════════════════════════════
# MAP 2: Continuous risk score — current vs. mid-century
# ═══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(11, 6))
fig.suptitle('CDCR Heat Risk Index — Continuous Score (0–100)', fontsize=11, fontweight='bold', y=0.98)

for ax, data, label in [
    (axes[0], cur, 'Historic (1991–2020)'),
    (axes[1], mc,  'Mid-century (2041–2070)'),
]:
    sc = draw_bubble_map(ax, data, 'risk_score', label, vmin=0, vmax=100)

cb = fig.colorbar(sc, ax=axes, orientation='horizontal', fraction=0.04, pad=0.04, shrink=0.5)
cb.set_label('Risk score (0–100, cross-period normalized)', fontsize=8)
cb.ax.tick_params(labelsize=7)
plt.tight_layout(rect=[0, 0.06, 1, 0.97])
map2_path = OUT_DIR / 'map_risk_score.png'
fig.savefig(map2_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved {map2_path}')


# ═══════════════════════════════════════════════════════════════════════════════
# MAP 3: Component scores — hazard, exposure, vulnerability (mid-century)
# ═══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(15, 6))
fig.suptitle('CDCR Heat Risk Components — Mid-century', fontsize=11, fontweight='bold', y=0.98)

component_configs = [
    ('hazard_score',        'Hazard (0–1)'),
    ('exposure_score',      'Exposure (0–1)'),
    ('vulnerability_score', 'Vulnerability (0–1)'),
]

sc_ref = None
for ax, (col, label) in zip(axes, component_configs):
    sc = draw_bubble_map(ax, mc, col, label, vmin=0, vmax=1)
    sc_ref = sc

cb = fig.colorbar(sc_ref, ax=axes, orientation='horizontal', fraction=0.03, pad=0.04, shrink=0.4)
cb.set_label('Component score (0–1)', fontsize=8)
cb.ax.tick_params(labelsize=7)
plt.tight_layout(rect=[0, 0.06, 1, 0.97])
map3_path = OUT_DIR / 'map_components_midcentury.png'
fig.savefig(map3_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved {map3_path}')


# ═══════════════════════════════════════════════════════════════════════════════
# MAP 4: Vulnerability sub-indicators (RHU + medical acuity) — mid-century
# ═══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(11, 6))
fig.suptitle('Vulnerability Sub-indicators: RHU Rate and Medical Acuity (2025)', fontsize=10, fontweight='bold', y=0.98)

sub_configs = [
    ('rhu_pct_2025',   'RHU rate (% in restricted housing, 2025 avg)'),
    ('medical_acuity', 'Medical acuity (P1+P2+medium risk, % of population)'),
]

for ax, (col, label) in zip(axes, sub_configs):
    sc = draw_bubble_map(ax, mc, col, label)

    # label top facilities
    top = mc.nlargest(5, col)
    for code, row in top.iterrows():
        ax.annotate(code, (row['longitude'], row['latitude']),
                    textcoords='offset points', xytext=(4, 4),
                    fontsize=6, color='#222')

    cb = fig.colorbar(
        plt.cm.ScalarMappable(
            cmap=SCORE_CMAP,
            norm=plt.Normalize(mc[col].min(), mc[col].max())
        ),
        ax=ax, orientation='horizontal', fraction=0.04, pad=0.04, shrink=0.7
    )
    cb.ax.tick_params(labelsize=6)

plt.tight_layout(rect=[0, 0.04, 1, 0.97])
map4_path = OUT_DIR / 'map_vuln_subindicators.png'
fig.savefig(map4_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved {map4_path}')


# ═══════════════════════════════════════════════════════════════════════════════
# CHART: Component bar chart — mid-century, ranked by risk score
# ═══════════════════════════════════════════════════════════════════════════════
mc_ranked = mc.sort_values('risk_score', ascending=True)
codes = mc_ranked.index.tolist()
n = len(codes)
y = np.arange(n)
bar_h = 0.25

fig, ax = plt.subplots(figsize=(8, 9))
ax.barh(y - bar_h, mc_ranked['hazard_score'],       height=bar_h, color='#e07850', label='Hazard')
ax.barh(y,         mc_ranked['exposure_score'],      height=bar_h, color='#5090c8', label='Exposure')
ax.barh(y + bar_h, mc_ranked['vulnerability_score'], height=bar_h, color='#60a060', label='Vulnerability')
ax.set_yticks(y)
ax.set_yticklabels(codes, fontsize=8)
ax.set_xlabel('Component score (0–1)', fontsize=9)
ax.set_title('CDCR Heat Risk — Component Scores, Mid-century\n(Ranked by risk score)', fontsize=10)
ax.legend(fontsize=9, loc='lower right')
ax.set_xlim(0, 1.05)
ax.axvline(0.5, color='#bbb', linewidth=0.5, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
chart1_path = OUT_DIR / 'chart_components_ranked.png'
fig.savefig(chart1_path, dpi=150, bbox_inches='tight')
plt.close()
print(f'Saved {chart1_path}')


# ═══════════════════════════════════════════════════════════════════════════════
# MARKDOWN REPORT
# ═══════════════════════════════════════════════════════════════════════════════

def fmt_pct(v, digits=1):
    if pd.isna(v): return '—'
    return f'{v:.{digits}f}%'

def fmt_f(v, digits=2):
    if pd.isna(v): return '—'
    return f'{v:.{digits}f}'

def fmt_i(v):
    if pd.isna(v): return '—'
    return f'{int(v):,}'

# Build full mid-century table
mc_full = mc.sort_values('risk_score', ascending=False).reset_index()
mc_full['rank'] = range(1, len(mc_full) + 1)

# Load sensitivity if available
sens_df = None
if SENS.exists():
    sens_df = pd.read_csv(SENS)

# Compute Jenks breaks from mid-century scores (reproduce)
mc_scores = mc['risk_score'].values
import mapclassify as mc_cls
jnb = mc_cls.NaturalBreaks(mc_scores, k=4)
breaks_arr = jnb.bins
break_low_mod   = round(float(breaks_arr[0]), 1)
break_mod_high  = round(float(breaks_arr[1]), 1)
break_high_crit = round(float(breaks_arr[2]), 1)

tier_counts = mc_full.groupby('risk_category')['cdcr_code'].apply(list)

def tier_facilities(tier):
    if tier in tier_counts.index:
        codes = tier_counts[tier]
        return ', '.join(codes)
    return '—'

md_lines = [
    f'# CDCR Facility Heat Risk Index — Report',
    f'',
    f'**Date:** April 2026',
    f'**Notebook:** `analysis/CDCR_risk_indices/heat_risk_index.ipynb`',
    f'**Sensitivity:** `analysis/CDCR_risk_indices/sensitivity_analysis.ipynb`',
    f'**Output data:** `data/cdcr/CDCR_heat_risk_index_additive_25_25_50.csv`, `data/cdcr/CDCR_heat_risk_sensitivity.csv`',
    f'',
    f'---',
    f'',
    f'## Framework',
    f'',
    f'**Risk = 0.25·Hazard + 0.25·Exposure + 0.50·Vulnerability**, following Ovienmhada et al. (2024) and the California Vulnerable Communities Platform (VCP) methodology. Vulnerability is double-weighted: the index answers "where are people most at risk if cooling fails?", and the additive form keeps a fully air-conditioned but highly vulnerable facility from scoring zero risk. Each component is a composite of sub-indicators normalized 0–1 across the 31 facilities before averaging. The final risk score is normalized 0–100 jointly across both time periods (current: 1991–2020; mid-century: 2041–2070, SSP3-7.0). This report reflects heat index **v0.2**, whose hazard component uses facility-relative temperature thresholds from a LOCA2-CA daily extraction.',
    f'',
    f'Adaptive capacity is excluded as a standalone component following Ovienmhada et al. (2024). Incarcerated people cannot relocate, purchase cooling, or leave the facility — the institutional structure of incarceration removes the individual and collective agency that adaptive capacity metrics are designed to measure.',
    f'',
    f'**Facility coverage:** 31 of 34 CDCR state prisons. CAC, CVSP, and FWF excluded — no indoor heat model data available.',
    f'',
    f'---',
    f'',
    f'## 1. Variable Selection',
    f'',
    f'### Hazard Component',
    f'',
    f'Two relative-threshold temperature indicators, each max-normalized 0–1 across 31 facilities and averaged, then amplified by an air-quality modifier. Temperature counts come from a LOCA2-CA daily extraction at each facility\'s own grid cell (14-model ensemble, model democracy).',
    f'',
    f'| Sub-indicator | Description | Research justification | Source |',
    f'|:---|:---|:---|:---|',
    f'| Hot days | Annual days above the facility\'s own mean summer daily max + 10°F (Skarha threshold, 1981–2010 baseline; `loca2_days_over_avg_plus10`) | A facility-relative threshold captures acclimatization: a +10°F anomaly is a shock to a cool-climate facility that an absolute 90°F count is blind to. The +10°F offset is calibrated to the mortality estimate in Skarha et al. (2023) | LOCA2-CA daily (SSP3-7.0), Cal-Adapt via cadcat |',
    f'| Warm nights | Annual Apr–Oct nights with tmin above the 95th percentile of the facility\'s 1961–1990 April–October distribution (`loca2_nights_over_p95`) | Nighttime heat prevents physiological recovery from daytime exposure; the community-heat-health convention (OEHHA) uses a percentile relative to a fixed baseline window, so the count measures distributional shift rather than moving with the climate it detects | LOCA2-CA daily (SSP3-7.0), Cal-Adapt via cadcat |',
    f'| Air quality (AQI) | Multiplicative modifier `× (1 + 0.30·AQI/100)` on the temperature hazard, not a separate additive term; AQI is the CalEnviroScreen 5.0 ozone/PM2.5/diesel percentile mean | Ozone and PM2.5 compound heat-health risk (Chen et al. 2024). A multiplier amplifies hazard where heat is present but cannot create hazard from pollution alone (×1.0 at AQI = 0); β = 0.30 is a design parameter capping amplification at +30% at the worst-air facility | CalEnviroScreen 5.0, 2025 |',
    f'',
    f'### Exposure Component',
    f'',
    f'Equal-weight average of four sub-indicators. Building envelope and cooling infrastructure do not change with climate scenario; the same 2025 values are applied to both time periods.',
    f'',
    f'| Sub-indicator | Description | Research justification | Source |',
    f'|:---|:---|:---|:---|',
    f'| Indoor 78°F days | Annual days with indoor temperatures above 78°F (institution-level, as reported by CDCR, 2025) | Outdoor temperature data systematically overstates indoor burden; CPRA data show indoor days at ≥90°F were 35–47% of outdoor days at the same threshold; 78°F is the lower bound of CDCR\'s Stage I heat pathology activation | CDCR Air Cooling Pilot Supplemental Report, Jan 2026 |',
    f'| Indoor/outdoor ratio | Ratio of indoor 78°F days to outdoor 78°F days | Captures building envelope performance independently of climate — two facilities with identical outdoor heat can have very different indoor burdens depending on construction and cooling; addresses a gap identified in the OIG heat log audit | Derived from CDCR 2026 and gridMET |',
    f'| Urban heat island (UHI) | Daytime surface UHI anomaly (ΔT), normalized 0–1 | Benz & Burney (2021) document systematic race and class disparities in UHI intensity across the US; included in VCP heat hazard methodology; prisons in urban or industrialized tracts face compounded outdoor heat beyond gridded climate data | Benz & Burney (2021), Harvard Dataverse |',
    f'| No AC (inverted) | 1 minus fraction of housing units with refrigerated air conditioning | Skarha et al. (2022) found AC reduced heat-related mortality by 99% in Texas prisons; ISP event study (this project) shows post-HVAC installation reduced ED rates, violent incidents, and overtime costs; refrigerated AC is the primary evidence-based heat intervention | CDCR Air Cooling Pilot Supplemental Report, Jan 2026 |',
    f'',
    f'### Vulnerability Component',
    f'',
    f'Equal-weight average of six sub-indicators. All capture physiological susceptibility to heat stress or, for the gendered population term, documented differences in heat-health burden.',
    f'',
    f'| Sub-indicator | Description | Research justification | Source |',
    f'|:---|:---|:---|:---|',
    f'| Medical acuity | Share of population in CCHCS risk tiers P1, P2, or medium risk (12-month avg, 2025) | Cardiovascular disease, diabetes, and respiratory illness are established heat mortality risk factors (Skarha et al. 2023); CCHCS risk tiers are the available facility-level proxy for chronic disease burden; Ovienmhada et al. (2024) include health vulnerability as a component | CCHCS Health Care Dashboard, 2025 |',
    f'| Age 50+ | Share of population aged 50 or older (12-month avg, 2025) | Age is one of the strongest individual-level heat vulnerability factors; CDCR\'s own heat pathology plan designates age ≥ 55 as a risk factor; accelerated aging literature treats age 50 in incarcerated populations as equivalent to age 65 in the general population; Ovienmhada et al. (2024) include age | CDCR Population Data Points, 2025 |',
    f'| Mental health (EOP) | Share enrolled in Enhanced Outpatient Program (12-month avg, 2025) | Antipsychotic and anticholinergic medications impair thermoregulation through multiple mechanisms; Cloud et al. (2023) and Hidden Hazards (2023) identify psychotropic medication use as a heat vulnerability factor; EOP enrollment is the available facility-level proxy for psychotropic medication prevalence | CCHCS Health Care Dashboard, 2025 |',
    f'| Disability (DPP) | Share with Disability Placement Program designation (12-month avg, 2025) | Mobility, vision, and other impairments limit ability to respond to heat stress or access cooling resources; Hidden Hazards (2023) identifies disability as a vulnerability factor; DPP is the available facility-level designation for documented functional limitations | CCHCS Health Care Dashboard, 2025 |',
    f'| Race/POC | Share identifying as people of color (12-month avg, 2025) | Ovienmhada et al. (2024) include race as a heat vulnerability factor, citing documented disparities in heat-related health outcomes, access to care, and historical disinvestment in cooling infrastructure; Benz & Burney (2021) show race is the strongest predictor of UHI exposure | CDCR Population Data Points, 2025 |',
    f'| Gender (% female) | Share of the facility population that is female (12-month avg, 2025) | Included to reflect documented sex-based differences in thermoregulation and heat-health outcomes, and the distinct medical profile of women\'s facilities; retained as an equal-weight vulnerability sub-indicator | CDCR Population Data Points, 2025 |',
    f'',
    f'### Excluded Variables',
    f'',
    f'The following variables were considered and excluded. They are retained in the output data as descriptive columns.',
    f'',
    f'| Variable | Rationale for exclusion |',
    f'|:---|:---|',
    f'| Capacity utilization (`capacity_percent_2025`) | Overcrowding is identified as a vulnerability factor by Hidden Hazards (2023) — crowding impairs ventilation and limits movement to cooler areas. Data are available for all 31 facilities (2025 annual average from CDCR TPOP reports; range 76%–161%). Conceptually, overcrowding would belong in the exposure component, but direct testing shows it does not explain indoor/outdoor ratio variance beyond AC fraction (OLS: coef=0.002, p=0.60, R² change <0.01). Retained as a descriptive column. |',
    f'| Security level (`securelvl`) | Security level (Maximum vs. Medium) was considered as an exposure variable — higher-security housing involves more time in cell, more restricted movement, and potentially less access to cooling areas. Literature is mixed with most studies finding no significant independent effect. Direct testing confirms this: OLS of indoor/outdoor ratio on AC fraction plus security level shows security level is not significant (coef=−0.081, p=0.68) and adding it reduces adjusted R². It also does not improve k-means cluster coherence — adding it as a clustering feature reassigns RJD from Cluster A and breaks the key r=0.806 outdoor-indoor correlation without producing a more interpretable structure. |',
    f'| Restricted housing rate (`rhu_pct_2025`) | Cloud et al. (2023) identify solitary confinement as a heat vulnerability factor. However, the literature does not provide quantified dose-response evidence between RHU status and heat health outcomes relative to the general incarcerated population. Including it at equal weight would imply an equivalence with physiological susceptibility indicators that cannot be substantiated. Two extreme outliers (COR 13.6%, SAC 12.7%) would also produce score separation disproportionate to the available evidence. |',
    f'| Geographic isolation (`dist_nearest_medical_mi`) | Hidden Hazards (2023) identifies remoteness from hospitals as an emergency vulnerability factor. Among the 31 active CDCR state prisons, the variable shows insufficient differentiation: median 0.52 miles, maximum 1.51 miles (KVSP). No facilities are isolated enough for this to meaningfully separate facilities in the index. |',
    f'| Incarcerated workers (% assigned to work) | Work assignments — particularly kitchen, laundry, and outdoor labor — involve sustained physical exertion and/or exposure to high-heat environments with limited ability to self-limit activity. This represents a meaningful exposure pathway not captured by facility-level indoor temperature data. Days above 80°F increase the risk of workplace injuries by 3%, and days above 90°F increase the risk by 10% (LAO, 2024; Alahmad, 2025). Facility-level data on work assignment rates are not currently available in this project. |',
    f'',
    f'**Note on total population:** `average_2025_population` (2025 annual average) is used only for bubble sizing in the maps — it is not a scored variable. It is the only population count in this index; capacity utilization is not scored for the reasons above.',
    f'',
    f'---',
    f'',
    f'## 2. Mid-century Risk Ranking',
    f'',
    f'![Risk tier maps](map_risk_tier.png)',
    f'',
    f'![Component scores bar chart](chart_components_ranked.png)',
    f'',
    f'### Table 1. Mid-century risk ranking — all 31 facilities',
    f'',
    f'| # | Facility | Code | Risk Score | Tier | Hazard | Exposure | Vulnerability |',
    f'|---|----------|------|-----------|------|--------|----------|----------------|',
]

for _, row in mc_full.iterrows():
    name = str(row['name'])[:30]
    md_lines.append(
        f"| {int(row['rank'])} | {name} | {row['cdcr_code']} | {row['risk_score']:.1f} | "
        f"{row['risk_category']} | {row['hazard_score']:.2f} | "
        f"{row['exposure_score']:.2f} | {row['vulnerability_score']:.2f} |"
    )

# Risk tier summary
highest_list = tier_facilities('Highest')
high_list    = tier_facilities('High')
mod_list     = tier_facilities('Moderate')
lowest_list  = tier_facilities('Lowest')

n_highest = len(tier_counts.get('Highest', []))
n_high    = len(tier_counts.get('High', []))
n_mod     = len(tier_counts.get('Moderate', []))
n_lowest  = len(tier_counts.get('Lowest', []))

md_lines += [
    f'',
    f'### Table 2. Risk tier classification (Jenks natural breaks, mid-century)',
    f'',
    f'| Tier | Score range | n facilities | Facilities |',
    f'|------|------------|--------------|------------|',
    f'| Highest | > {break_high_crit} | {n_highest} | {highest_list} |',
    f'| High | {break_mod_high} – {break_high_crit} | {n_high} | {high_list} |',
    f'| Moderate | {break_low_mod} – {break_mod_high} | {n_mod} | {mod_list} |',
    f'| Lowest | ≤ {break_low_mod} | {n_lowest} | {lowest_list} |',
    f'',
    f'> Jenks natural breaks computed on mid-century risk scores (k=4). Same thresholds applied to current-period scores for comparability.',
    f'',
    f'---',
    f'',
    f'## 3. Component Maps',
    f'',
    f'![Risk score maps (continuous)](map_risk_score.png)',
    f'',
    f'![Component maps (hazard, exposure, vulnerability)](map_components_midcentury.png)',
    f'',
    f'---',
    f'',
    f'## 4. Hazard Component',
    f'',
    f'Two relative-threshold temperature indicators, each max-normalized 0–1 across 31 facilities and averaged, then amplified by an air-quality modifier (`× (1 + 0.30·AQI/100)`):',
    f'',
    f'| Sub-indicator | Variable | Source |',
    f'|:---|:---|:---|',
    f'| Hot days | `loca2_days_over_avg_plus10_historic` / `_midcentury` | LOCA2-CA daily (SSP3-7.0), Cal-Adapt via cadcat |',
    f'| Warm nights | `loca2_nights_over_p95_historic` / `_midcentury` | LOCA2-CA daily (SSP3-7.0), Cal-Adapt via cadcat |',
    f'| Air quality (modifier) | `AQI_norm` | CalEnviroScreen 5.0, 2025 |',
    f'',
    f'### Table 3. Hazard scores by facility',
    f'',
    f'| Facility | Code | Historic | Mid-century | Δ |',
    f'|----------|------|---------|------------|---|',
]

haz = mc_full[['name','cdcr_code','hazard_score']].merge(
    cur.reset_index()[['cdcr_code','hazard_score']].rename(columns={'hazard_score':'hazard_cur'}),
    on='cdcr_code'
).sort_values('hazard_score', ascending=False)

for _, row in haz.iterrows():
    delta = row['hazard_score'] - row['hazard_cur']
    md_lines.append(
        f"| {str(row['name'])[:28]} | {row['cdcr_code']} | {row['hazard_cur']:.2f} | "
        f"{row['hazard_score']:.2f} | +{delta:.2f} |"
    )

md_lines += [
    f'',
    f'---',
    f'',
    f'## 5. Exposure Component',
    f'',
    f'Equal-weight average of four sub-indicators (mid-century uses same 2025 values — building envelope and cooling do not change with climate scenario):',
    f'',
    f'| Sub-indicator | Variable | Source |',
    f'|:---|:---|:---|',
    f'| Indoor 78°F days | `days_indoor_above_78f_2025` | CDCR Air Cooling Pilot Supplemental Report, Jan 2026 |',
    f'| Indoor/outdoor ratio | `ratio_indoor_to_outdoor` | Derived from CDCR 2026 + gridMET |',
    f'| Urban heat island | `uhi_normalized` | Benz & Burney (2021), Harvard Dataverse |',
    f'| No AC (inverted) | `inverted_ac_fraction` | CDCR Air Cooling Pilot Supplemental Report, Jan 2026 |',
    f'',
    f'### Table 4. Exposure sub-indicator values — top and bottom 10 facilities (mid-century)',
    f'',
    f'| Facility | Code | Indoor 78°F days | Ratio in/out | UHI (0–1) | No-AC fraction | Exposure score |',
    f'|----------|------|-----------------|-------------|-----------|----------------|----------------|',
]

exp_data = mc_full.sort_values('exposure_score', ascending=False)
for _, row in exp_data.iterrows():
    md_lines.append(
        f"| {str(row['name'])[:28]} | {row['cdcr_code']} "
        f"| {fmt_i(row['days_indoor_above_78f_2025'])} "
        f"| {fmt_f(row['ratio_indoor_to_outdoor'])} "
        f"| {fmt_f(row['uhi_normalized'])} "
        f"| {fmt_f(1 - row.get('pct_hu_mechanical', 0) if 'pct_hu_mechanical' in row.index else float('nan'))} "
        f"| {row['exposure_score']:.2f} |"
    )

md_lines += [
    f'',
    f'> PBSP has ratio = 15.75 (vs. system max ~2.0 for other facilities) driven by ~4 outdoor 78°F days/year at the Crescent City coast. Retained without capping — physically plausible.',
    f'',
    f'---',
    f'',
    f'## 6. Vulnerability Component',
    f'',
    f'Equal-weight average of six sub-indicators, each capturing physiological susceptibility to heat stress or documented differences in heat-health burden.',
    f'',
    f'| Sub-indicator | Variable | Source |',
    f'|:---|:---|:---|',
    f'| Medical acuity | `medical_acuity` (P1+P2+medium risk %) | CCHCS Health Care Dashboard, 2025 |',
    f'| Age 50+ | `cchcs_age_over_50_pct_2025` | CDCR Population Data Points, 2025 |',
    f'| Mental health (EOP) | `cchcs_mental_health_eop_pct_2025` | CCHCS Health Care Dashboard, 2025 |',
    f'| Disability (DPP) | `cchcs_dpp_pct_2025` | CCHCS Health Care Dashboard, 2025 |',
    f'| Race/POC | `race_peopleofcolor_pct` | CDCR Population Data Points, 2025 |',
    f'| Gender (% female) | `gender_female_pct` | CDCR Population Data Points, 2025 |',
    f'',
    f'![Vulnerability sub-indicator maps (RHU + medical acuity)](map_vuln_subindicators.png)',
    f'',
    f'### Table 5. Vulnerability sub-indicators — all 31 facilities',
    f'',
    f'| Facility | Code | Medical acuity | Age 50+ | EOP % | DPP % | POC % | RHU % | Vuln. score |',
    f'|----------|------|---------------|---------|-------|-------|-------|-------|-------------|',
]

vuln_data = mc_full.sort_values('vulnerability_score', ascending=False)
for _, row in vuln_data.iterrows():
    md_lines.append(
        f"| {str(row['name'])[:28]} | {row['cdcr_code']} "
        f"| {fmt_pct(row['medical_acuity'] * 100 if row['medical_acuity'] < 1.5 else row['medical_acuity'])} "
        f"| {fmt_pct(row['cchcs_age_over_50_pct_2025'])} "
        f"| {fmt_pct(row['cchcs_mental_health_eop_pct_2025'])} "
        f"| {fmt_pct(row['cchcs_dpp_pct_2025'])} "
        f"| {fmt_pct(row['race_peopleofcolor_pct'])} "
        f"| {fmt_pct(row['rhu_pct_2025'])} "
        f"| {row['vulnerability_score']:.2f} |"
    )

md_lines += [
    f'',
    f'---',
    f'',
    f'## 7. Descriptive Context (not scored)',
    f'',
    f'These variables are included in the output data for context but are NOT part of the index score.',
    f'Geographic isolation showed insufficient differentiation across the 31 active CDCR facilities (median 0.52 mi to nearest medical facility; KVSP most isolated at 1.48 mi) to warrant inclusion as a scored sub-indicator. Hidden Hazards (2023) identifies remoteness from hospitals as a vulnerability factor conceptually but does not operationalize it as a scored variable.',
    f'',
    f'### Table 6. Descriptive facility characteristics',
    f'',
    f'| Facility | Code | Year opened | Urban area | Dist. medical (mi) | CA Model |',
    f'|----------|------|------------|-----------|-------------------|----------|',
]

desc_data = mc_full.sort_values('risk_score', ascending=False)
for _, row in desc_data.iterrows():
    yr   = str(int(row['year_opened'])) if not pd.isna(row.get('year_opened', float('nan'))) else '—'
    urb  = 'Yes' if row.get('in_urban_area_2020') else 'No'
    dist = fmt_f(row.get('dist_nearest_medical_mi', float('nan')), 2)
    cal  = 'Yes' if str(row.get('california_model_facility', '')).strip().lower() == 'yes' else '—'
    md_lines.append(
        f"| {str(row['name'])[:28]} | {row['cdcr_code']} | {yr} | {urb} | {dist} | {cal} |"
    )

# Sensitivity section
if sens_df is not None:
    md_lines += [
        f'',
        f'---',
        f'',
        f'## 7. Sensitivity Analysis',
        f'',
        f'Three weighting schemes tested against the equal-weight multiplicative baseline (mid-century only):',
        f'',
        f'| Scheme | Formula | Logic |',
        f'|--------|---------|-------|',
        f'| A — Equal multiplicative (baseline) | H × E × V | All components equal |',
        f'| B — Additive 25/25/50 | 0.25H + 0.25E + 0.50V | Ovienmhada vulnerability upweighting |',
        f'| C — Multiplicative V² | H × E × V² | Vulnerability amplified, multiplicative structure preserved |',
        f'',
        f'Spearman rank correlations: **A vs B = 0.877**, **A vs C = 0.935**, **B vs C = 0.946**.',
        f'Top 5 facilities are stable across all three schemes.',
        f'CHCF has the largest rank swing (16 positions): ranks 22nd under equal weighting but rises to 6th under the additive scheme — high medical complexity drives vulnerability even without indoor heat exposure days (full AC).',
        f'',
        f'> VCP `ExHeatHealth_Idx` comparison: Spearman r = −0.17 between this index and the surrounding community VCP index. The low correlation supports the case for a prison-specific framework.',
        f'',
    ]

    # Print top rows of sensitivity
    if 'rank_scheme_a' in sens_df.columns:
        md_lines += [
            f'### Table 7. Sensitivity — rank by scheme (mid-century)',
            f'',
            f'| Facility | Rank A (baseline) | Rank B (additive) | Rank C (V²) | Max swing |',
            f'|----------|-------------------|------------------|------------|-----------|',
        ]
        for _, row in sens_df.sort_values('rank_scheme_a').iterrows():
            swing = max(
                abs(row.get('rank_scheme_a', 0) - row.get('rank_scheme_b', 0)),
                abs(row.get('rank_scheme_a', 0) - row.get('rank_scheme_c', 0)),
            )
            md_lines.append(
                f"| {row.get('cdcr_code', '—')} "
                f"| {int(row.get('rank_scheme_a', 0))} "
                f"| {int(row.get('rank_scheme_b', 0))} "
                f"| {int(row.get('rank_scheme_c', 0))} "
                f"| {int(swing)} |"
            )

md_lines += [
    f'',
    f'---',
    f'',
    f'## 9. Limitations and Future Work',
    f'',
    f'- **Incarcerated workers** — share of facility population employed through PIA or outdoor work assignments not included. PIA workers face elevated heat exposure. Facility-level data on full participation rates are still being sought.',
    f'- **Psychotropic medication** — facility-level prescription rates not publicly available from CCHCS. EOP enrollment used as proxy.',
    f'- **Geographic isolation** — retained as descriptive variable only. Weak differentiation across 31 active facilities (median 0.52 mi; range 0.07–1.51 mi) makes it unsuitable as a scored sub-indicator. Hidden Hazards (2023) identifies remoteness conceptually.',
    f'- **AQI held constant** — no tract-level AQI projections available; historic CalEnviroScreen 5.0 values enter the hazard multiplier for both time periods.',
    f'- **β = 0.30 (AQI amplification)** — a design parameter, not a carceral-validated coefficient; it caps air-quality amplification of the heat hazard at +30% at the worst-air facility.',
    f'- **Exposure component fixed across time periods** — indoor days, AC fraction, UHI, and indoor/outdoor ratio are 2025 values applied to both current and mid-century. These reflect current infrastructure, not projected changes.',
    f'',
]

report_path = OUT_DIR / 'heat_risk_index_report.md'
with open(report_path, 'w') as f:
    f.write('\n'.join(md_lines))
print(f'Saved {report_path}')
print('Done.')
