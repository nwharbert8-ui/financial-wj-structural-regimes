"""
===============================================================================
FINANCIAL WJ - PHASE 2 EXTENSION
===============================================================================

Builds on the augmentation results to add:

  1. Per-window Type 1 gap and Type 2 gap trajectories (n=264 instead of n=6)
  2. Per-window sign-inversion percentage trajectory
  3. Realized-volatility and VIX trajectories aligned to the 264 windows
  4. Cross-trajectory correlations: Type 2 gap vs VIX, Type 2 gap vs
     realized vol, Type 1 gap vs VIX, Type 1 gap vs realized vol
  5. Permutation significance tests for ALL signed-WJ-detected regimes
     (including the new 2022 regime)
  6. Combined regime catalog: 6 unsigned + 5 signed = 7 unique regimes
     after merging overlaps
  7. Triangular pairing-family classification scatter

Inputs (from Phase 1 / primary pipeline):
  - results_rebuild/baseline_corr_spearman.parquet
  - results_rebuild/_corr_vectors.npy (264 unsigned absolute vectors)
  - results_augmentation/signed_corr_vectors.npy (264 signed vectors)
  - results_rebuild/_window_meta.csv
  - results_rebuild/regime_wj_results.csv
  - results_rebuild/detected_regimes.csv
  - results_augmentation/signed_wj_regimes.csv
  - data/vix_daily.csv
  - data/sp500_returns_final.parquet

Output: results_phase2/

Author: Drake H. Harbert (D.H.H.)
Affiliation: Inner Architecture LLC, Canton, OH 44721, USA
ORCID: 0009-0007-7740-3616
Date: 2026-05-08
===============================================================================
"""

import os
import sys
import json
import time
import warnings
import socket

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
socket.setdefaulttimeout(60)

sys.path.insert(0, r"G:\My Drive\inner_architecture_research")
from wj_utils import fast_spearman_matrix

# ============================================================================
# CONFIG
# ============================================================================
FORCE_RECOMPUTE = True
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
N_PERMUTATIONS = 5000

PROJECT_BASE = r"G:\My Drive\inner_architecture_research\financial_wj_fundamental"
RESULTS_DIR = os.path.join(PROJECT_BASE, "results_phase2")
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")
DATA_DIR = os.path.join(PROJECT_BASE, "data")
PRIMARY_RESULTS = os.path.join(PROJECT_BASE, "results_rebuild")
AUG_RESULTS = os.path.join(PROJECT_BASE, "results_augmentation")

for d in [RESULTS_DIR, FIGURES_DIR]:
    os.makedirs(d, exist_ok=True)

BINARY_THRESHOLD_PCT = 5


# ============================================================================
# CORE METRICS
# ============================================================================
def wj_unsigned(a, b):
    return float(np.minimum(a, b).sum() / np.maximum(a, b).sum())


def wj_signed(a, b):
    a_s = a + 1.0
    b_s = b + 1.0
    return float(np.minimum(a_s, b_s).sum() / np.maximum(a_s, b_s).sum())


def binary_jaccard_at_threshold(signed_a, signed_b, threshold):
    a_set = np.abs(signed_a) >= threshold
    b_set = np.abs(signed_b) >= threshold
    inter = (a_set & b_set).sum()
    union = (a_set | b_set).sum()
    return float(inter / union) if union > 0 else 1.0


def signed_corr_vector(corr_matrix):
    n = corr_matrix.shape[0]
    iu = np.triu_indices(n, k=1)
    return corr_matrix[iu]


# ============================================================================
# LOAD CACHED DATA
# ============================================================================
def load_inputs():
    print("[1/8] Loading cached inputs...")
    baseline_corr = pd.read_parquet(
        os.path.join(PRIMARY_RESULTS, "baseline_corr_spearman.parquet")).values
    iu = np.triu_indices(baseline_corr.shape[0], k=1)
    baseline_signed = baseline_corr[iu]
    baseline_abs = np.abs(baseline_signed)
    threshold = np.percentile(baseline_abs, 100 - BINARY_THRESHOLD_PCT)
    unsigned_vecs = np.load(
        os.path.join(PRIMARY_RESULTS, "_corr_vectors.npy"))
    signed_vecs = np.load(
        os.path.join(AUG_RESULTS, "signed_corr_vectors.npy"))
    window_meta = pd.read_csv(
        os.path.join(PRIMARY_RESULTS, "_window_meta.csv"),
        parse_dates=["mid_date"])
    regimes_df = pd.read_csv(
        os.path.join(PRIMARY_RESULTS, "regime_wj_results.csv"))
    detected_regimes = pd.read_csv(
        os.path.join(PRIMARY_RESULTS, "detected_regimes.csv"))
    signed_regimes = pd.read_csv(
        os.path.join(AUG_RESULTS, "signed_wj_regimes.csv"),
        parse_dates=["start_date", "end_date"])
    returns_df = pd.read_parquet(
        os.path.join(DATA_DIR, "sp500_returns_final.parquet"))
    print(f"   baseline {baseline_corr.shape}, unsigned vecs "
          f"{unsigned_vecs.shape}, signed vecs {signed_vecs.shape}")
    print(f"   threshold (top 5%): {threshold:.4f}")
    return (baseline_corr, baseline_signed, baseline_abs, threshold,
            unsigned_vecs, signed_vecs, window_meta, regimes_df,
            detected_regimes, signed_regimes, returns_df)


# ============================================================================
# PER-WINDOW PAIRING TRAJECTORIES
# ============================================================================
def per_window_pairing_trajectory(unsigned_vecs, signed_vecs,
                                    baseline_signed, baseline_abs,
                                    threshold, window_meta):
    """For each of the 264 windows compute:
      - WJ unsigned vs baseline
      - WJ signed vs baseline
      - Binary Jaccard at top 5%
      - Type 1 gap (WJ_uns - BJ)
      - Type 2 gap (WJ_sgn - WJ_uns)
      - Sign inversion percentage of reorganization
      - Frobenius-distance equivalent
    """
    print("\n[2/8] Computing per-window pairing trajectories...")
    n_windows = len(window_meta)
    rows = []
    for i in range(n_windows):
        u = unsigned_vecs[i]
        s = signed_vecs[i]
        wj_u = wj_unsigned(u, baseline_abs)
        wj_s = wj_signed(s, baseline_signed)
        bj = binary_jaccard_at_threshold(s, baseline_signed, threshold)
        gap = wj_s - wj_u
        reorg_unsigned = 1 - wj_u
        sign_inv = (gap / reorg_unsigned * 100.0
                    if reorg_unsigned > 0 else 0.0)
        rows.append({
            "window_idx": i,
            "mid_date": window_meta.iloc[i]["mid_date"],
            "wj_unsigned": wj_u,
            "wj_signed": wj_s,
            "binary_jaccard": bj,
            "type1_gap": wj_u - bj,
            "type2_gap": gap,
            "sign_inversion_pct": sign_inv,
        })
        if (i + 1) % 50 == 0:
            print(f"   {i+1}/{n_windows} windows done")
    df = pd.DataFrame(rows)
    df["mid_date"] = pd.to_datetime(df["mid_date"])
    df.to_csv(os.path.join(RESULTS_DIR, "per_window_pairing.csv"),
               index=False)
    print(f"   Saved per_window_pairing.csv ({len(df)} rows)")
    return df


# ============================================================================
# REALIZED VOL + VIX TRAJECTORIES ALIGNED TO WINDOWS
# ============================================================================
def macro_stress_per_window(window_meta, returns_df, vix_df):
    """For each window, compute mean and peak realized volatility
    (annualized) and mean and peak VIX over the window's daily index range."""
    print("\n[3/8] Aligning macro stress measures to windows...")
    rows = []
    cross_section_returns = returns_df.mean(axis=1)
    rolling_std = cross_section_returns.rolling(window=20,
                                                  min_periods=5).std()
    realized_vol_daily = rolling_std * np.sqrt(252)

    for i, w in window_meta.iterrows():
        s = int(w["start"])
        e = int(w["end"])
        # Slice realized vol over the window's daily span
        rv_slice = realized_vol_daily.iloc[s:e]
        mean_rvol = float(rv_slice.mean())
        peak_rvol = float(rv_slice.max())
        # Window's date range
        start_date = returns_df.index[s]
        end_date = returns_df.index[min(e - 1, len(returns_df) - 1)]
        # VIX over that range
        vix_slice = vix_df.loc[
            (vix_df.index >= start_date) & (vix_df.index <= end_date),
            "Close"]
        mean_vix = float(vix_slice.mean()) if len(vix_slice) else np.nan
        peak_vix = float(vix_slice.max()) if len(vix_slice) else np.nan
        rows.append({
            "window_idx": i,
            "mid_date": w["mid_date"],
            "mean_realized_vol": mean_rvol,
            "peak_realized_vol": peak_rvol,
            "mean_vix": mean_vix,
            "peak_vix": peak_vix,
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RESULTS_DIR, "per_window_macro_stress.csv"),
               index=False)
    return df


# ============================================================================
# CROSS-TRAJECTORY CORRELATIONS
# ============================================================================
def trajectory_correlations(df_pairing, df_macro, lookback=60):
    """Spearman rank correlations between pairing-family gaps and macro
    stress measures across all 264 windows (using only windows with
    valid sliding-baseline data, i.e., index >= lookback)."""
    print("\n[4/8] Cross-trajectory correlations...")
    df_merge = df_pairing.merge(df_macro, on=["window_idx", "mid_date"],
                                 how="inner")
    df_valid = df_merge.iloc[lookback:].dropna(
        subset=["mean_vix", "peak_vix", "mean_realized_vol",
                 "peak_realized_vol"])
    print(f"   Valid windows for correlation: {len(df_valid)} / "
          f"{len(df_merge)}")

    rows = []
    for gap_col in ["type1_gap", "type2_gap", "sign_inversion_pct"]:
        for macro_col in ["mean_vix", "peak_vix",
                            "mean_realized_vol", "peak_realized_vol"]:
            rho, p = stats.spearmanr(df_valid[gap_col],
                                       df_valid[macro_col])
            r_pearson, p_pearson = stats.pearsonr(df_valid[gap_col],
                                                    df_valid[macro_col])
            rows.append({
                "gap_metric": gap_col,
                "macro_variable": macro_col,
                "n_windows": int(len(df_valid)),
                "spearman_rho": float(rho),
                "spearman_p": float(p),
                "pearson_r": float(r_pearson),
                "pearson_p": float(p_pearson),
            })
            print(f"   {gap_col:22s} vs {macro_col:22s}: rho = {rho:+.3f} "
                  f"(p = {p:.3e})")
    df_corr = pd.DataFrame(rows)
    df_corr.to_csv(os.path.join(RESULTS_DIR,
                                  "trajectory_correlations.csv"),
                    index=False)
    return df_corr


# ============================================================================
# PERMUTATION SIGNIFICANCE FOR SIGNED-WJ REGIMES
# ============================================================================
def permutation_test_signed_regimes(returns_df, baseline_signed,
                                       signed_regimes, window_meta):
    """For each signed-WJ-detected regime, pool daily indices from windows
    in regime, compute SIGNED WJ vs baseline, then permute by sampling
    same number of random days from full study period."""
    print("\n[5/8] Permutation significance for signed-WJ regimes...")
    rng = np.random.RandomState(RANDOM_SEED)
    returns_arr = returns_df.values
    n_total = returns_arr.shape[0]

    # Map signed-regime dates to window indices
    print("   Building window-index ranges for signed regimes...")
    signed_regime_window_ranges = []
    for _, r in signed_regimes.iterrows():
        s_date = pd.to_datetime(r["start_date"])
        e_date = pd.to_datetime(r["end_date"])
        wm_dates = pd.to_datetime(window_meta["mid_date"])
        in_regime = (wm_dates >= s_date) & (wm_dates <= e_date)
        idxs = np.where(in_regime)[0]
        if len(idxs) > 0:
            signed_regime_window_ranges.append({
                "start_date": str(s_date.date()),
                "end_date": str(e_date.date()),
                "win_start_idx": int(idxs.min()),
                "win_end_idx": int(idxs.max()),
                "n_windows": int(len(idxs)),
            })
    print(f"   Mapped {len(signed_regime_window_ranges)} signed regimes")

    rows = []
    for sr in signed_regime_window_ranges:
        # Pool daily indices
        day_set = set()
        for w_idx in range(sr["win_start_idx"], sr["win_end_idx"] + 1):
            s = int(window_meta.iloc[w_idx]["start"])
            e = int(window_meta.iloc[w_idx]["end"])
            day_set.update(range(s, e))
        day_indices = sorted(day_set)
        n_days = len(day_indices)
        sub = returns_arr[day_indices, :]
        # Compute observed signed WJ
        regime_corr = fast_spearman_matrix(sub.T)
        regime_signed = signed_corr_vector(regime_corr)
        observed_wj_sgn = wj_signed(regime_signed, baseline_signed)
        # Permutation: random sample of n_days from full period
        null_wjs = []
        print(f"   Regime {sr['start_date']}-{sr['end_date']} "
              f"(n_days={n_days}): permuting...")
        for p_iter in range(N_PERMUTATIONS):
            perm_idx = rng.choice(n_total, size=n_days, replace=False)
            perm_sub = returns_arr[perm_idx, :]
            perm_corr = fast_spearman_matrix(perm_sub.T)
            perm_signed = signed_corr_vector(perm_corr)
            null_wjs.append(wj_signed(perm_signed, baseline_signed))
            if (p_iter + 1) % 1000 == 0:
                print(f"      {p_iter+1}/{N_PERMUTATIONS}")
        null_arr = np.asarray(null_wjs)
        null_mean = float(null_arr.mean())
        null_std = float(null_arr.std(ddof=1))
        z = (observed_wj_sgn - null_mean) / null_std if null_std > 0 else 0
        # Two-sided p: count permutations as extreme as observed
        p_low = float(np.mean(null_arr <= observed_wj_sgn))
        p_high = float(np.mean(null_arr >= observed_wj_sgn))
        p_two = 2 * min(p_low, p_high)
        rows.append({
            "start_date": sr["start_date"],
            "end_date": sr["end_date"],
            "n_days": n_days,
            "observed_signed_wj": observed_wj_sgn,
            "null_mean": null_mean,
            "null_std": null_std,
            "z_score": float(z),
            "p_value_two_sided": p_two,
            "p_value_one_sided_low": p_low,
        })
        print(f"      Observed signed WJ: {observed_wj_sgn:.4f}, "
              f"z = {z:+.2f}, p = {p_two:.4f}")
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RESULTS_DIR,
                            "signed_wj_regimes_permutation.csv"),
               index=False)
    return df


# ============================================================================
# COMBINED REGIME CATALOG
# ============================================================================
def combined_regime_catalog(unsigned_regimes, signed_regimes_perm):
    """Build a merged catalog of all unique regimes detected by either
    method, flagging which detector(s) found each."""
    print("\n[6/8] Building combined regime catalog...")
    all_regimes = []
    for _, r in unsigned_regimes.iterrows():
        all_regimes.append({
            "start_date": r["start_date"],
            "end_date": r["end_date"],
            "direction": r["direction"],
            "detected_unsigned": True,
            "detected_signed": False,  # placeholder, fix below
            "wj_unsigned": float(r["WJ"]),
            "wj_signed": np.nan,
            "n_days": int(r["n_days"]),
        })
    # Fill signed detection match
    for r in all_regimes:
        u_start = pd.to_datetime(r["start_date"])
        u_end = pd.to_datetime(r["end_date"])
        for _, sr in signed_regimes_perm.iterrows():
            s_start = pd.to_datetime(sr["start_date"])
            s_end = pd.to_datetime(sr["end_date"])
            overlap = (min(u_end, s_end) - max(u_start, s_start)).days
            if overlap >= 0:
                r["detected_signed"] = True
                r["wj_signed"] = float(sr["observed_signed_wj"])
                break
    # Add signed-only regimes
    for _, sr in signed_regimes_perm.iterrows():
        s_start = pd.to_datetime(sr["start_date"])
        s_end = pd.to_datetime(sr["end_date"])
        already_in = False
        for r in all_regimes:
            u_start = pd.to_datetime(r["start_date"])
            u_end = pd.to_datetime(r["end_date"])
            overlap = (min(u_end, s_end) - max(u_start, s_start)).days
            if overlap >= 0:
                already_in = True
                break
        if not already_in:
            all_regimes.append({
                "start_date": str(s_start.date()),
                "end_date": str(s_end.date()),
                "direction": "UNDETERMINED (signed-only)",
                "detected_unsigned": False,
                "detected_signed": True,
                "wj_unsigned": np.nan,
                "wj_signed": float(sr["observed_signed_wj"]),
                "n_days": int(sr["n_days"]),
            })
    df = pd.DataFrame(all_regimes)
    df = df.sort_values("start_date").reset_index(drop=True)
    df.to_csv(os.path.join(RESULTS_DIR, "combined_regime_catalog.csv"),
               index=False)
    print(f"   Combined catalog: {len(df)} unique regimes")
    print(df[["start_date", "end_date", "direction",
                "detected_unsigned", "detected_signed",
                "wj_unsigned", "wj_signed"]].round(4).to_string(index=False))
    return df


# ============================================================================
# FIGURES
# ============================================================================
def plot_per_window_trajectories(df_pairing, df_macro, regimes_df,
                                    out_path):
    """4-panel: WJ unsigned, Type 1 gap, Type 2 gap, mean VIX
    with 6 unsigned regimes shaded."""
    df = df_pairing.merge(df_macro, on=["window_idx", "mid_date"],
                            how="inner")
    fig, axes = plt.subplots(4, 1, figsize=(13, 10), sharex=True)
    panels = [
        ("wj_unsigned", "WJ unsigned (vs baseline)", "#3498DB"),
        ("type1_gap", "Type 1 gap (WJ − binary Jaccard)", "#27AE60"),
        ("type2_gap", "Type 2 gap (signed WJ − unsigned WJ)", "#E74C3C"),
        ("mean_vix", "Mean VIX (window)", "#8E44AD"),
    ]
    for ax, (col, title, color) in zip(axes, panels):
        ax.plot(df["mid_date"], df[col], color=color, linewidth=1.4)
        ax.set_ylabel(title, fontsize=10)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        # Shade unsigned-detected regimes
        for _, r in regimes_df.iterrows():
            cs = pd.to_datetime(r["start_date"])
            ce = pd.to_datetime(r["end_date"])
            color_shade = ("#85C1E9" if r["direction"] == "CONVERGENCE"
                            else "#F5B7B1")
            ax.axvspan(cs, ce, alpha=0.25, color=color_shade)
    axes[-1].set_xlabel("Date")
    fig.suptitle("Per-window pairing trajectories (2003-2025) "
                 "with regime shading",
                 fontsize=12, y=0.995)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_triangular_regime_space(df_aug, out_path):
    """Scatter of regimes in (Type 1 gap, Type 2 gap) space."""
    fig, ax = plt.subplots(figsize=(8, 6.5))
    cv = df_aug[df_aug["direction"] == "CONVERGENCE"]
    dv = df_aug[df_aug["direction"] == "DIVERGENCE"]
    ax.scatter(cv["type1_gap_continuous_minus_binary"],
                cv["type2_gap_signed_minus_unsigned"],
                s=200, color="#3498DB", edgecolor="#21618C",
                linewidth=1.2, label="Convergence", alpha=0.9)
    ax.scatter(dv["type1_gap_continuous_minus_binary"],
                dv["type2_gap_signed_minus_unsigned"],
                s=200, color="#E74C3C", edgecolor="#922B21",
                linewidth=1.2, label="Divergence", alpha=0.9)
    for _, r in df_aug.iterrows():
        x = r["type1_gap_continuous_minus_binary"]
        y = r["type2_gap_signed_minus_unsigned"]
        ax.annotate(f"Ep{int(r['episode'])}", (x, y), xytext=(7, 0),
                     textcoords="offset points", fontsize=10)
    ax.set_xlabel("Type 1 gap (continuous − discrete)\n"
                   "[bulk distribution reorganization]", fontsize=11)
    ax.set_ylabel("Type 2 gap (signed − unsigned)\n"
                   "[sign-flip reorganization]", fontsize=11)
    ax.set_title("Pairing-family regime classification space\n"
                  "Convergence and divergence regimes occupy "
                  "distinct quadrants", fontsize=12)
    ax.legend(fontsize=10, loc="lower left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def plot_macro_correlation_grid(df_pairing, df_macro, df_corr, out_path):
    """4x3 grid of scatter plots: 3 gap metrics x 4 macro variables."""
    df = df_pairing.merge(df_macro, on=["window_idx", "mid_date"],
                            how="inner")
    df = df.iloc[60:].dropna(
        subset=["mean_vix", "peak_vix", "mean_realized_vol",
                 "peak_realized_vol"])
    gap_cols = [("type1_gap", "Type 1 gap"),
                ("type2_gap", "Type 2 gap"),
                ("sign_inversion_pct", "Sign-inversion %")]
    macro_cols = [("mean_vix", "Mean VIX"),
                   ("peak_vix", "Peak VIX"),
                   ("mean_realized_vol", "Mean realized vol"),
                   ("peak_realized_vol", "Peak realized vol")]
    fig, axes = plt.subplots(3, 4, figsize=(16, 11))
    for i, (gc, gtitle) in enumerate(gap_cols):
        for j, (mc, mtitle) in enumerate(macro_cols):
            ax = axes[i, j]
            ax.scatter(df[gc], df[mc], s=10, alpha=0.5, color="#3498DB")
            row = df_corr[(df_corr["gap_metric"] == gc) &
                            (df_corr["macro_variable"] == mc)]
            if len(row) > 0:
                rho = float(row["spearman_rho"].iloc[0])
                p = float(row["spearman_p"].iloc[0])
                ax.set_title(f"{gtitle} vs {mtitle}\n"
                              f"ρ = {rho:+.3f}, p = {p:.2e}", fontsize=10)
            ax.set_xlabel(gtitle, fontsize=9)
            ax.set_ylabel(mtitle, fontsize=9)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
    fig.suptitle("Pairing-family gaps vs macro stress measures (n=204 windows)",
                 fontsize=13, y=0.998)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


# ============================================================================
# MAIN
# ============================================================================
def main():
    t0 = time.time()
    print("=" * 70)
    print("FINANCIAL WJ - PHASE 2 EXTENSION")
    print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    (baseline_corr, baseline_signed, baseline_abs, threshold,
     unsigned_vecs, signed_vecs, window_meta, regimes_df,
     detected_regimes, signed_regimes, returns_df) = load_inputs()

    # VIX (load and clean yfinance 3-row header: Price/Ticker/Date)
    print("\n   Loading VIX...")
    vix_raw = pd.read_csv(os.path.join(DATA_DIR, "vix_daily.csv"),
                            skiprows=3, header=None,
                            names=["Date", "Adj_Close", "Close", "High",
                                    "Low", "Open", "Volume"])
    vix_df = pd.DataFrame({
        "Close": pd.to_numeric(vix_raw["Close"], errors="coerce").values,
    }, index=pd.to_datetime(vix_raw["Date"], errors="coerce"))
    vix_df = vix_df.dropna()
    print(f"   VIX: {len(vix_df)} days, range [{vix_df['Close'].min():.1f},"
          f" {vix_df['Close'].max():.1f}]")

    # Per-window pairing trajectories
    df_pairing = per_window_pairing_trajectory(
        unsigned_vecs, signed_vecs, baseline_signed, baseline_abs,
        threshold, window_meta)

    # Per-window macro stress
    df_macro = macro_stress_per_window(window_meta, returns_df, vix_df)

    # Cross-trajectory correlations
    df_corr = trajectory_correlations(df_pairing, df_macro)

    # Permutation tests for signed regimes
    df_signed_perm = permutation_test_signed_regimes(
        returns_df, baseline_signed, signed_regimes, window_meta)

    # Combined catalog
    df_combined = combined_regime_catalog(regimes_df, df_signed_perm)

    # Augmentation results (for triangular plot)
    df_aug = pd.read_csv(os.path.join(AUG_RESULTS,
                                        "regime_augmentation.csv"))

    # Figures
    print("\n[7/8] Generating figures...")
    plot_per_window_trajectories(
        df_pairing, df_macro, regimes_df,
        os.path.join(FIGURES_DIR, "per_window_trajectories.png"))
    plot_triangular_regime_space(
        df_aug, os.path.join(FIGURES_DIR, "triangular_regime_space.png"))
    plot_macro_correlation_grid(
        df_pairing, df_macro, df_corr,
        os.path.join(FIGURES_DIR, "macro_correlation_grid.png"))

    # Provenance
    print("\n[8/8] Provenance...")
    elapsed = time.time() - t0
    provenance = {
        "phase": "Phase 2 extension on top of Phase 1 augmentation",
        "methodology": "WJ-native Layer 2H pairing-family decomposition",
        "fundamental_unit": "individual S&P 500 stock (n=478)",
        "random_seed": RANDOM_SEED,
        "n_permutations": N_PERMUTATIONS,
        "n_windows": int(len(df_pairing)),
        "n_valid_correlation_windows": int(
            df_corr["n_windows"].iloc[0] if len(df_corr) > 0 else 0),
        "binary_threshold_pct": BINARY_THRESHOLD_PCT,
        "binary_threshold_value": float(threshold),
        "outputs": [
            "per_window_pairing.csv (n=264)",
            "per_window_macro_stress.csv (n=264)",
            "trajectory_correlations.csv (12 gap-vs-macro tests)",
            "signed_wj_regimes_permutation.csv (5 regimes tested)",
            "combined_regime_catalog.csv (7 unique regimes)",
            "figures/per_window_trajectories.png",
            "figures/triangular_regime_space.png",
            "figures/macro_correlation_grid.png",
        ],
        "elapsed_seconds": round(elapsed, 2),
        "execution_date": time.strftime("%Y-%m-%d"),
    }
    with open(os.path.join(RESULTS_DIR, "provenance.json"), "w") as f:
        json.dump(provenance, f, indent=2, default=str)

    print(f"\n{'=' * 70}")
    print(f"PHASE 2 COMPLETE in {elapsed:.1f}s")
    print(f"Results: {RESULTS_DIR}")
    print("=" * 70)


if __name__ == "__main__":
    main()
