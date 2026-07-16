#!/usr/bin/env python3
"""
Improved clustering pipeline for the indoor/outdoor heat analysis.

Supersedes the z-score-only k-means in build_indoor_outdoor_analysis.py. Changes,
motivated by methods_review_clustering.ipynb:

  1. Skew        -> Yeo-Johnson (power transform) the continuous numeric features,
                    instead of StandardScaler alone (which leaves skew untouched).
  2. Zeros       -> the three compositional, zero-inflated cooling shares
                    (refrigeration / evaporation / ventilation) are collapsed to ONE
                    categorical feature: the facility's dominant cooling system.
  3. Data fix    -> pct_buildings_evaporation clipped to <= 1 (SATF was 1.03).
  4. k           -> k = 3, which is the most stable choice once (1)-(2) are applied
                    (resample ARI ~0.85; Gower+K-Medoids converges to the same
                    partition once cooling is fairly weighted).

Non-destructive: adds `cooling_type` and `cluster_v2` columns to the CSV (keeps the
original `cluster`), and writes correlation + z-profile side tables for review.

Run from anywhere:
  conda run -n data_science python3 "analysis/cjc reports/indoor_outdoor_heat/build_improved_clustering.py"
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import StandardScaler, PowerTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from scipy.stats import pearsonr
import warnings
warnings.filterwarnings('ignore')

HERE = Path(__file__).resolve().parent
CSV  = HERE / 'indoor_outdoor_heat_2025.csv'

RANDOM_STATE, N_INIT = 42, 50

# The nine raw features (used only for the z-score PROFILE / interpretation) --------
FEATURES9 = ['year_opened', 'pct_buildings_refrigeration', 'pct_buildings_evaporation',
             'days_outdoor_above_78f_2025', 'days_indoor_above_78f_2025', 'uhi_normalized',
             'elevation_m', 'latitude', 'hotnights_pre_pct']
# Numeric features that actually go into the improved clustering (Yeo-Johnson'd) -----
CLUSTER_NUM = ['year_opened', 'days_outdoor_above_78f_2025', 'days_indoor_above_78f_2025',
               'uhi_normalized', 'elevation_m', 'latitude', 'hotnights_pre_pct']
COOL_COLS   = ['pct_buildings_refrigeration', 'pct_buildings_evaporation', 'pct_buildings_ventilation']

# ── Load & clean ──────────────────────────────────────────────────────────────
df = pd.read_csv(CSV)
df['uhi_normalized']    = df['uhi_normalized'].fillna(0)
df['hotnights_pre_pct'] = df['hotnights_pre_pct'].fillna(0)

# Data fix: evaporation share cannot exceed 1 (SATF = 1.03)
bad = df['pct_buildings_evaporation'] > 1
if bad.any():
    print(f"Data fix: clipping pct_buildings_evaporation > 1 for {df.loc[bad,'cdcr_code'].tolist()}")
    df['pct_buildings_evaporation'] = df['pct_buildings_evaporation'].clip(upper=1.0)

# Dominant cooling system -> single categorical feature
df['cooling_type'] = df[COOL_COLS].idxmax(axis=1).str.replace('pct_buildings_', '', regex=False)

# ── Improved feature matrix: Yeo-Johnson numerics + one-hot cooling ───────────
num_yj = PowerTransformer('yeo-johnson', standardize=True).fit_transform(df[CLUSTER_NUM])
cool_ohe = pd.get_dummies(df['cooling_type'])
X = np.hstack([num_yj, StandardScaler().fit_transform(cool_ohe.to_numpy(float))])

km = KMeans(n_clusters=3, random_state=RANDOM_STATE, n_init=N_INIT).fit(X)
df['_k'] = km.labels_

# ── Label the clusters by dominant cooling type -> A / B / C ──────────────────
# A = ventilation-only, B = refrigerated (full AC), C = evaporative
COOL_TO_LETTER = {'ventilation': 'A', 'refrigeration': 'B', 'evaporation': 'C'}
cluster_letter = {}
for kk in sorted(df['_k'].unique()):
    dom = df.loc[df['_k'] == kk, 'cooling_type'].mode()[0]
    cluster_letter[kk] = COOL_TO_LETTER[dom]
if len(set(cluster_letter.values())) < 3:
    raise RuntimeError(f"Cluster->letter mapping not 1:1: {cluster_letter}")
df['cluster_v2'] = df['_k'].map(cluster_letter)
df = df.drop(columns='_k')

# ── Diagnostics ──────────────────────────────────────────────────────────────
print(f"\nImproved k=3 clustering (n={len(df)}), silhouette = {silhouette_score(X, km.labels_):.3f}")
print(f"vs shipped A/B/C: {(df.cluster_v2 == df.cluster).mean():.0%} overlap, "
      f"ARI = {adjusted_rand_score(df.cluster, df.cluster_v2):.3f}\n")

for lab in ['A', 'B', 'C']:
    sub = df[df.cluster_v2 == lab]
    print(f"  {lab} (n={len(sub)}): {', '.join(sorted(sub.cdcr_code))}")

print("\nCluster vs dominant cooling type (purity):")
print(pd.crosstab(df.cluster_v2, df.cooling_type))

print("\nMovers vs shipped labels:")
mv = df[df.cluster_v2 != df.cluster][['cdcr_code', 'cluster', 'cluster_v2', 'cooling_type']]
print(mv.to_string(index=False) if len(mv) else "  none")

# ── Z-score cluster PROFILE (raw 9 features, standardized, mean per cluster) ──
z = pd.DataFrame(StandardScaler().fit_transform(df[FEATURES9]), columns=FEATURES9)
z['cluster_v2'] = df['cluster_v2'].values
zprof = z.groupby('cluster_v2').mean().round(2)
zprof['n'] = df.groupby('cluster_v2').size()
print("\nZ-SCORE cluster profile (mean standardized value per feature; +/- in SD units):")
print(zprof.T.to_string())

# raw means too, for the human-readable summary
rawprof = df.groupby('cluster_v2')[FEATURES9].mean().round(2)
rawprof['n'] = df.groupby('cluster_v2').size()

# ── Recompute indoor~outdoor correlations on the NEW clusters ─────────────────
def corr(sub, out_col):
    r, p = pearsonr(sub[out_col], sub['days_indoor_above_78f_2025'])
    return round(r, 3), round(p, 3)

rows = []
for lab, sub in [('all', df)] + [(l, df[df.cluster_v2 == l]) for l in ['A', 'B', 'C']]:
    r78, p78 = corr(sub, 'days_outdoor_above_78f_2025')
    r90, p90 = corr(sub, 'days_outdoor_90f_2025')
    rows.append({'cluster': lab, 'n': len(sub),
                 'r_indoor_vs_outdoor78': r78, 'p78': p78,
                 'r_indoor_vs_outdoor90': r90, 'p90': p90})
corr_tbl = pd.DataFrame(rows)
print("\nIndoor vs outdoor correlations (new clusters):")
print(corr_tbl.to_string(index=False))

# ── Write outputs ────────────────────────────────────────────────────────────
df.to_csv(CSV, index=False)
zprof.T.to_csv(HERE / 'cluster_zprofiles_v2.csv')
rawprof.T.to_csv(HERE / 'cluster_rawprofiles_v2.csv')
corr_tbl.to_csv(HERE / 'correlations_v2.csv', index=False)
print(f"\nWrote cluster_v2 + cooling_type to {CSV.name}")
print("Wrote cluster_zprofiles_v2.csv, cluster_rawprofiles_v2.csv, correlations_v2.csv")
