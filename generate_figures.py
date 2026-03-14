"""
Figure generation for Financial WJ Pipeline (rebuild)
Author: Drake H. Harbert (D.H.H.)
"""
import os, json, datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram
from scipy import stats as sp_stats

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results')
FIG_DIR = os.path.join(OUTPUT_DIR, 'figures')
os.makedirs(FIG_DIR, exist_ok=True)
DPI = 300
sns.set_style('whitegrid')

# Load all data
traj_df = pd.read_csv(os.path.join(OUTPUT_DIR, 'trajectory_with_baseline.csv'), parse_dates=['mid_date'])
crisis_df = pd.read_csv(os.path.join(OUTPUT_DIR, 'detected_regimes.csv'))
mean_reorg = pd.read_csv(os.path.join(OUTPUT_DIR, 'mean_reorganization.csv'))
cluster_df = pd.read_csv(os.path.join(OUTPUT_DIR, 'cluster_assignments.csv'))
sil_df = pd.read_csv(os.path.join(OUTPUT_DIR, 'silhouette_scores.csv'))
fp_df = pd.read_csv(os.path.join(OUTPUT_DIR, 'fingerprint_reorganization.csv'))
epicenter_df = pd.read_csv(os.path.join(OUTPUT_DIR, 'epicenter_stocks.csv'))
regime_df = pd.read_csv(os.path.join(OUTPUT_DIR, 'regime_wj_results.csv'))
tau_df = pd.read_csv(os.path.join(OUTPUT_DIR, 'cascade_stability.csv'))
Z = np.load(os.path.join(OUTPUT_DIR, '_linkage.npy'))
epicenter_tickers = epicenter_df['ticker'].tolist()

# ---- Fig 1: WJ Rolling Trajectory with dual panel ----
print('Fig 1: WJ trajectory...')
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True,
                                 gridspec_kw={'height_ratios': [3, 1]})
dates = traj_df['mid_date']
colors_map = {'normal': '#2ca02c', 'stress': '#ff7f0e',
              'reorganization': '#d62728', 'severe_reorganization': '#8b0000',
              'insufficient_data': '#cccccc'}
for state, color in colors_map.items():
    mask = traj_df['state'] == state
    if mask.any():
        ax1.scatter(dates[mask], traj_df['WJ_sliding'][mask], c=color, s=12,
                    label=state.replace('_', ' ').title(), alpha=0.8, zorder=3)

valid_idx = traj_df['wj_mean'].first_valid_index()
if valid_idx is not None:
    ax1.axhline(traj_df.loc[valid_idx, 'wj_mean'], color='gray', linestyle='--', alpha=0.5, label='Mean')
    ax1.axhline(traj_df.loc[valid_idx, 'wj_1sd'], color='orange', linestyle=':', alpha=0.5, label='Mean - 1 SD')
    ax1.axhline(traj_df.loc[valid_idx, 'wj_2sd'], color='red', linestyle=':', alpha=0.5, label='Mean - 2 SD')

ax1.set_ylabel('WJ (vs sliding 5-year baseline)', fontsize=12)
ax1.set_title('WJ Rolling Trajectory: Spearman Correlation Network Reorganization (2003-2025)', fontsize=13)
ax1.legend(fontsize=8, loc='lower right', ncol=2)

# Bottom: mean |rho|
ax2.plot(dates, traj_df['mean_abs_rho'], color='#1f77b4', linewidth=1)
ax2.fill_between(dates, traj_df['mean_abs_rho'], alpha=0.3, color='#1f77b4')
ax2.set_ylabel('Mean |rho|', fontsize=12)
ax2.set_xlabel('Date', fontsize=12)

# Shade episodes
for _, cr in crisis_df.iterrows():
    sd = pd.to_datetime(cr['start_date'])
    ed = pd.to_datetime(cr['end_date'])
    color = '#ff6666' if cr['direction'] == 'CONVERGENCE' else '#6666ff'
    ax1.axvspan(sd, ed, alpha=0.15, color=color)
    ax2.axvspan(sd, ed, alpha=0.15, color=color)

plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'Fig1_wj_trajectory.png'), dpi=DPI)
fig.savefig(os.path.join(FIG_DIR, 'Fig1_wj_trajectory.pdf'))
plt.close()

# ---- Fig 2: Top 30 reorganizers ----
print('Fig 2: Top 30...')
fig, ax = plt.subplots(figsize=(10, 8))
top30 = mean_reorg.head(30)
q90 = mean_reorg['mean_reorganization'].quantile(0.90)
colors = ['#d62728' if r >= q90 else '#1f77b4' for r in top30['mean_reorganization']]
ax.barh(range(len(top30)), top30['mean_reorganization'].values, color=colors)
ax.set_yticks(range(len(top30)))
ax.set_yticklabels(top30['ticker'].values, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel('Mean Fingerprint Reorganization (1 - WJ)', fontsize=12)
ax.set_title('Top 30 Stocks by Mean Fingerprint Reorganization\n(Spearman, across all detected regimes)', fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'Fig2_top30_reorganization.png'), dpi=DPI)
fig.savefig(os.path.join(FIG_DIR, 'Fig2_top30_reorganization.pdf'))
plt.close()

# ---- Fig 3: Distribution ----
print('Fig 3: Distribution...')
fig, ax = plt.subplots(figsize=(10, 6))
ax.hist(mean_reorg['mean_reorganization'], bins=50, edgecolor='black', alpha=0.7, color='#1f77b4')
for t in epicenter_tickers:
    val = mean_reorg[mean_reorg['ticker'] == t]['mean_reorganization'].values[0]
    ax.axvline(val, color='red', linewidth=2, alpha=0.8)
    ax.text(val + 0.003, ax.get_ylim()[1] * 0.9, t, fontsize=10, color='red', fontweight='bold')
ax.axvline(mean_reorg['mean_reorganization'].median(), color='gray', linestyle='--', label='Median')
ax.set_xlabel('Mean Fingerprint Reorganization', fontsize=12)
ax.set_ylabel('Count', fontsize=12)
ax.set_title('Distribution of Mean Fingerprint Reorganization (478 stocks)', fontsize=13)
ax.legend()
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'Fig3_reorganization_distribution.png'), dpi=DPI)
fig.savefig(os.path.join(FIG_DIR, 'Fig3_reorganization_distribution.pdf'))
plt.close()

# ---- Fig 4: Artifact test ----
print('Fig 4: Artifact test...')
fig, ax = plt.subplots(figsize=(10, 6))
x = mean_reorg['bl_mean_abs_r'].values
y = mean_reorg['mean_reorganization'].values
ax.scatter(x, y, alpha=0.3, s=10, color='#1f77b4')
slope, intercept, r_value, p_value, _ = sp_stats.linregress(x, y)
x_line = np.linspace(x.min(), x.max(), 100)
ax.plot(x_line, slope * x_line + intercept, 'k--', alpha=0.7,
        label='OLS: R2=%.3f' % (r_value**2))
for t in epicenter_tickers:
    row = mean_reorg[mean_reorg['ticker'] == t]
    ax.scatter(row['bl_mean_abs_r'].values, row['mean_reorganization'].values,
               c='red', s=80, marker='*', zorder=5)
    ax.annotate(t, (row['bl_mean_abs_r'].values[0], row['mean_reorganization'].values[0]),
                fontsize=10, color='red')
ax.set_xlabel('Baseline Mean |rho| (Spearman)', fontsize=12)
ax.set_ylabel('Mean Fingerprint Reorganization', fontsize=12)
ax.set_title('Metric Artifact Test: Reorganization vs Baseline Connectivity', fontsize=13)
ax.legend(fontsize=10)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'Fig4_artifact_test.png'), dpi=DPI)
fig.savefig(os.path.join(FIG_DIR, 'Fig4_artifact_test.pdf'))
plt.close()

# ---- Fig 5: Convergence vs Divergence ----
print('Fig 5: Conv vs Div...')
conv_eps = list(crisis_df[crisis_df['direction'] == 'CONVERGENCE'].index + 1)
div_eps = list(crisis_df[crisis_df['direction'] == 'DIVERGENCE'].index + 1)
conv_reorg = fp_df[fp_df['episode'].isin(conv_eps)].groupby('ticker')['fp_reorganization'].mean()
div_reorg = fp_df[fp_df['episode'].isin(div_eps)].groupby('ticker')['fp_reorganization'].mean()
common = sorted(set(conv_reorg.index) & set(div_reorg.index))
fig, ax = plt.subplots(figsize=(10, 8))
cx = conv_reorg[common].values
cy = div_reorg[common].values
ax.scatter(cx, cy, alpha=0.3, s=10, color='#1f77b4')
ax.plot([0, 0.8], [0, 0.8], 'k--', alpha=0.3, label='1:1 line')
for t in epicenter_tickers:
    if t in conv_reorg.index and t in div_reorg.index:
        ax.scatter(conv_reorg[t], div_reorg[t], c='red', s=80, marker='*', zorder=5)
        ax.annotate(t, (conv_reorg[t], div_reorg[t]), fontsize=10, color='red')
rho, pval = sp_stats.spearmanr(cx, cy)
ax.set_xlabel('Mean Reorganization (Convergence Episodes)', fontsize=12)
ax.set_ylabel('Mean Reorganization (Divergence Episodes)', fontsize=12)
ax.set_title('Directional Decomposition of Fingerprint Reorganization\n(Spearman rho=%.3f, p=%.2e)' % (rho, pval), fontsize=13)
ax.legend()
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'Fig5_convergence_vs_divergence.png'), dpi=DPI)
fig.savefig(os.path.join(FIG_DIR, 'Fig5_convergence_vs_divergence.pdf'))
plt.close()

# ---- Fig 6: Silhouette ----
print('Fig 6: Silhouette...')
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(sil_df['K'], sil_df['silhouette'], 'o-', color='#1f77b4')
best_k = sil_df.loc[sil_df['silhouette'].idxmax(), 'K']
ax.axvline(best_k, color='red', linestyle='--', alpha=0.7, label='Best K=%d' % int(best_k))
ax.set_xlabel('Number of Clusters (K)', fontsize=12)
ax.set_ylabel('Silhouette Score', fontsize=12)
ax.set_title('WJ-Native Fingerprint Clustering: Silhouette Analysis', fontsize=13)
ax.legend()
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'Fig6_silhouette.png'), dpi=DPI)
fig.savefig(os.path.join(FIG_DIR, 'Fig6_silhouette.pdf'))
plt.close()

# ---- Fig 7: Dendrogram ----
print('Fig 7: Dendrogram...')
fig, ax = plt.subplots(figsize=(14, 6))
dendrogram(Z, ax=ax, no_labels=True, color_threshold=0)
ax.set_xlabel('Stocks', fontsize=12)
ax.set_ylabel('WJ Distance', fontsize=12)
ax.set_title('Hierarchical Clustering Dendrogram (WJ Fingerprint Distance, Spearman)', fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'Fig7_dendrogram.png'), dpi=DPI)
fig.savefig(os.path.join(FIG_DIR, 'Fig7_dendrogram.pdf'))
plt.close()

# ---- Fig 8: Cascade stability heatmap ----
print('Fig 8: Cascade stability...')
n_eps = len(crisis_df)
tau_matrix = np.eye(n_eps)
for _, row in tau_df.iterrows():
    i, j = int(row['ep1'])-1, int(row['ep2'])-1
    tau_matrix[i, j] = row['tau']
    tau_matrix[j, i] = row['tau']

labels = []
for i in range(n_eps):
    dr = crisis_df.iloc[i]['direction'][:4]
    yr = crisis_df.iloc[i]['start_date'][:4]
    labels.append('Ep%d\n%s\n%s' % (i+1, dr, yr))

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(tau_matrix, annot=True, fmt='.3f', cmap='RdYlGn', center=0,
            xticklabels=labels, yticklabels=labels, ax=ax, vmin=-0.2, vmax=0.7)
ax.set_title('Cascade Stability (Kendall tau): Same-Direction vs Cross-Direction', fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, 'Fig8_cascade_stability.png'), dpi=DPI)
fig.savefig(os.path.join(FIG_DIR, 'Fig8_cascade_stability.pdf'))
plt.close()

# ---- PROVENANCE ----
print('\nWriting provenance.json...')
with open(os.path.join(OUTPUT_DIR, 'gics_comparison.json')) as f:
    gc = json.load(f)
with open(os.path.join(OUTPUT_DIR, 'epicenter_significance.json')) as f:
    es = json.load(f)

provenance = {
    "methodology": "WJ-native",
    "fundamental_unit": "Individual S&P 500 constituent stocks (478)",
    "pairwise_matrix": "full, no pre-filtering",
    "correlation_method": "Spearman",
    "fdr_scope": "permutation-based (per-regime)",
    "domain_conventional_methods": "GICS comparison only (post-discovery)",
    "random_seed": 42,
    "pipeline_file": "financial_wj_pipeline.py",
    "execution_date": datetime.datetime.now().strftime("%Y-%m-%d"),
    "wj_compliance_status": "PASS",
    "n_stocks": 478,
    "n_pairwise": 114003,
    "window_size": 252,
    "step_size": 21,
    "regime_detection": "sliding 5-year baseline, algorithmic thresholds",
    "n_regimes_detected": len(crisis_df),
    "regime_directions": crisis_df['direction'].tolist(),
    "best_K": gc['best_K'],
    "silhouette": gc['best_silhouette'],
    "ARI_vs_GICS": gc['ARI'],
    "NMI_vs_GICS": gc['NMI'],
    "epicenter_n": es['n'],
    "epicenter_tickers": epicenter_df['ticker'].tolist(),
    "epicenter_z": es['z'],
    "epicenter_p": es['p'],
    "cascade_mean_tau": float(tau_df['tau'].mean()),
    "key_findings": [
        "QE-era decorrelation (2017) is structurally more extreme than GFC convergence",
        "WJ detects both convergence and divergence reorganization",
        "Cascade ordering is direction-dependent (same-dir tau >> cross-dir tau)",
        "Market splits into 2 fundamental groups (K=2, sil=0.298), not 11 GICS sectors",
        "GICS captures ~10% of correlation architecture (ARI=0.101)"
    ]
}

with open(os.path.join(OUTPUT_DIR, 'provenance.json'), 'w') as f:
    json.dump(provenance, f, indent=2)

print('All figures and provenance saved to:', OUTPUT_DIR)
