#!/usr/bin/env python3
"""
Indoor/outdoor heat analysis — clustering and regression.

Replicates the k=3 k-means clustering from the HTML report, then tests
capacity utilization and security level as potential exposure covariates.

Run from project root:
  conda run -n data_science python3 "analysis/cjc reports/indoor_outdoor_heat/build_indoor_outdoor_analysis.py"

Outputs (same directory as this script):
  indoor_outdoor_heat_2025.csv        — updated with capacity_percent_2025, securelvl
  regression_results.csv              — OLS results: AC-only, +capacity, +security, +both
  cluster_sensitivity.csv             — cluster assignments under original and extended feature sets
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.stats import pearsonr
import statsmodels.formula.api as smf
import warnings
warnings.filterwarnings('ignore')

ROOT   = Path('.')
IO_DIR = ROOT / 'analysis/cjc reports/indoor_outdoor_heat'
CSV    = IO_DIR / 'indoor_outdoor_heat_2025.csv'
FAC    = ROOT / 'data/cdcr/cdcr_facilities.csv'

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV)
fac = pd.read_csv(FAC)[['cdcr_code', 'capacity_percent_2025', 'securelvl']]

df = df.merge(fac, on='cdcr_code', how='left')
df['cap_pct'] = df['capacity_percent_2025'] * 100

# Encode security level: MAXIMUM=1, MEDIUM=0, NOT AVAILABLE=NaN
df['is_maximum'] = df['securelvl'].map({'MAXIMUM': 1, 'MEDIUM': 0})

print(f"Loaded {len(df)} facilities")
print(f"  capacity_percent_2025 nulls: {df['cap_pct'].isna().sum()}")
print(f"  securelvl nulls (NOT AVAILABLE): {df['is_maximum'].isna().sum()} "
      f"({df[df['is_maximum'].isna()]['cdcr_code'].tolist()})")

# ── Replicate original k=3 clustering ─────────────────────────────────────────
# 9 features from the HTML report
BASE_FEATURES = [
    'year_opened',
    'pct_hu_mechanical',
    'pct_hu_evaporative',
    'days_outdoor_above_78f_2025',
    'days_indoor_above_78f_2025',
    'uhi_normalized',
    'elevation_m',
    'latitude',
    'hotnights_pre_pct',
]

# Fill the two CCI UHI nulls (same as original — set to 0)
df['uhi_normalized'] = df['uhi_normalized'].fillna(0)
df['hotnights_pre_pct'] = df['hotnights_pre_pct'].fillna(0)

X_base = df[BASE_FEATURES].values
scaler_base = StandardScaler()
X_base_z = scaler_base.fit_transform(X_base)

km_base = KMeans(n_clusters=3, random_state=42, n_init=50)
df['cluster_base'] = km_base.fit_predict(X_base_z)

# Match cluster labels A/B/C to the existing CSV labels by majority overlap
cluster_map = {}
for new_label in [0, 1, 2]:
    sub = df[df['cluster_base'] == new_label]['cluster']
    cluster_map[new_label] = sub.mode()[0]
df['cluster_replicated'] = df['cluster_base'].map(cluster_map)

match_rate = (df['cluster_replicated'] == df['cluster']).mean()
print(f"\nCluster replication match rate: {match_rate:.1%}")
mismatches = df[df['cluster_replicated'] != df['cluster']][['cdcr_code', 'cluster', 'cluster_replicated']]
if len(mismatches):
    print("Mismatches:")
    print(mismatches.to_string(index=False))

# ── Within-cluster Pearson r (indoor ~ outdoor) ───────────────────────────────
print("\n── Within-cluster correlation: indoor 78°F days vs outdoor 78°F days ──")
for label in ['A', 'B', 'C']:
    sub = df[df['cluster'] == label]
    r, p = pearsonr(sub['days_outdoor_above_78f_2025'], sub['days_indoor_above_78f_2025'])
    print(f"  Cluster {label} (n={len(sub)}): r={r:.3f}, p={p:.3f}")

# ── OLS regression: what explains indoor/outdoor ratio? ───────────────────────
# Outcome: ratio_indoor_to_outdoor (indoor 78°F days / outdoor 78°F days)
# Cap PBSP's extreme outlier (ratio=15.75) for regression stability — noted in report
df_reg = df[df['ratio_indoor_to_outdoor'] < 10].copy()  # excludes PBSP
print(f"\nRegression sample: n={len(df_reg)} (PBSP excluded, ratio=15.75)")

# For security level, further restrict to non-NA (drop SATF, CHCF)
df_reg_sec = df_reg[df_reg['is_maximum'].notna()].copy()
print(f"  With security level: n={len(df_reg_sec)} (SATF + CHCF excluded, securelvl=NOT AVAILABLE)")

models = {}

# Model 1: AC fraction only (baseline)
m1 = smf.ols('ratio_indoor_to_outdoor ~ pct_hu_mechanical', data=df_reg).fit()
models['AC only'] = m1

# Model 2: AC + capacity %
m2 = smf.ols('ratio_indoor_to_outdoor ~ pct_hu_mechanical + cap_pct', data=df_reg).fit()
models['AC + capacity'] = m2

# Model 3: AC + security level (on restricted n)
m3 = smf.ols('ratio_indoor_to_outdoor ~ pct_hu_mechanical + is_maximum', data=df_reg_sec).fit()
models['AC + security'] = m3

# Model 4: AC + capacity + security (restricted n)
m4 = smf.ols('ratio_indoor_to_outdoor ~ pct_hu_mechanical + cap_pct + is_maximum', data=df_reg_sec).fit()
models['AC + capacity + security'] = m4

print("\n── OLS results: ratio_indoor_to_outdoor ──")
print(f"{'Model':<30} {'n':>4}  {'R²':>6}  {'adj R²':>7}  {'AC coef':>9}  {'AC p':>7}  {'cap coef':>9}  {'cap p':>7}  {'sec coef':>9}  {'sec p':>7}")
for name, m in models.items():
    n = int(m.nobs)
    r2 = m.rsquared
    ar2 = m.rsquared_adj
    ac_c  = m.params.get('pct_hu_mechanical', np.nan)
    ac_p  = m.pvalues.get('pct_hu_mechanical', np.nan)
    cap_c = m.params.get('cap_pct', np.nan)
    cap_p = m.pvalues.get('cap_pct', np.nan)
    sec_c = m.params.get('is_maximum', np.nan)
    sec_p = m.pvalues.get('is_maximum', np.nan)
    print(f"{name:<30} {n:>4}  {r2:>6.3f}  {ar2:>7.3f}  "
          f"{ac_c:>9.3f}  {ac_p:>7.3f}  "
          f"{cap_c if not np.isnan(cap_c) else '—':>9}  "
          f"{cap_p if not np.isnan(cap_p) else '—':>7}  "
          f"{sec_c if not np.isnan(sec_c) else '—':>9}  "
          f"{sec_p if not np.isnan(sec_p) else '—':>7}")

# ── Descriptives: capacity and security by cluster ────────────────────────────
print("\n── Capacity % and security level by cluster ──")
print(df.groupby('cluster')[['cap_pct', 'is_maximum']].agg(['mean', 'std']).round(2))

# ── Clustering sensitivity: add capacity and/or security as features ──────────
# Test whether adding these features changes cluster assignments meaningfully
print("\n── Clustering sensitivity ──")

results = []
for label, extra_cols, extra_n in [
    ('base (9 features)',       [],          None),
    ('+capacity (10 features)', ['cap_pct'], None),
    ('+security (10 features)', ['is_maximum'], df[df['is_maximum'].notna()].index),
    ('+both (11 features)',     ['cap_pct', 'is_maximum'], df[df['is_maximum'].notna()].index),
]:
    sub = df if extra_n is None else df.loc[extra_n]
    feats = BASE_FEATURES + extra_cols
    X = sub[feats].copy()
    # fill any residual nulls
    X = X.fillna(X.mean())
    Xz = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=3, random_state=42, n_init=50)
    km.fit(Xz)
    inertia = km.inertia_
    labels = km.labels_
    # within-cluster r for each cluster (use original cluster grouping as reference)
    # map new labels to original A/B/C by majority
    sub = sub.copy()
    sub['new_cluster'] = labels
    mapping = {}
    for nl in [0, 1, 2]:
        m = sub[sub['new_cluster'] == nl]['cluster']
        if len(m):
            mapping[nl] = m.mode()[0]
        else:
            mapping[nl] = '?'
    sub['new_cluster_label'] = sub['new_cluster'].map(mapping)
    match = (sub['new_cluster_label'] == sub['cluster']).mean()
    results.append({'config': label, 'n': len(sub), 'inertia': round(inertia, 1), 'match_vs_base': f'{match:.1%}'})
    print(f"\n  {label}: inertia={inertia:.1f}, match vs original={match:.1%}")
    changed = sub[sub['new_cluster_label'] != sub['cluster']][['cdcr_code', 'cluster', 'new_cluster_label']]
    if len(changed):
        print(f"    Reassigned: {', '.join(changed['cdcr_code'] + ' (' + changed['cluster'] + '→' + changed['new_cluster_label'] + ')')}")
    else:
        print(f"    No reassignments")
    # per-cluster r
    for cl in ['A', 'B', 'C']:
        grp = sub[sub['new_cluster_label'] == cl]
        if len(grp) >= 3:
            r, p = pearsonr(grp['days_outdoor_above_78f_2025'], grp['days_indoor_above_78f_2025'])
            print(f"    Cluster {cl} (n={len(grp)}): r={r:.3f}, p={p:.3f}")

# ── Save outputs ───────────────────────────────────────────────────────────────
# Update CSV with new columns
df_out = df.drop(columns=['cluster_base', 'cluster_replicated', 'is_maximum'])
df_out.to_csv(CSV, index=False)
print(f"\nUpdated {CSV}")

# Regression results summary
reg_rows = []
for name, m in models.items():
    reg_rows.append({
        'model': name,
        'n': int(m.nobs),
        'r2': round(m.rsquared, 4),
        'adj_r2': round(m.rsquared_adj, 4),
        'ac_coef': round(m.params.get('pct_hu_mechanical', np.nan), 4),
        'ac_pvalue': round(m.pvalues.get('pct_hu_mechanical', np.nan), 4),
        'capacity_coef': round(m.params.get('cap_pct', np.nan), 4) if 'cap_pct' in m.params else None,
        'capacity_pvalue': round(m.pvalues.get('cap_pct', np.nan), 4) if 'cap_pct' in m.params else None,
        'security_coef': round(m.params.get('is_maximum', np.nan), 4) if 'is_maximum' in m.params else None,
        'security_pvalue': round(m.pvalues.get('is_maximum', np.nan), 4) if 'is_maximum' in m.params else None,
    })
pd.DataFrame(reg_rows).to_csv(IO_DIR / 'regression_results.csv', index=False)
print(f"Wrote regression_results.csv")
print("\nDone.")
