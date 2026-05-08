"""
WJ Utilities — Standard implementations for all pipelines.
Every pipeline should import from here instead of reimplementing.
Includes: unsigned WJ, signed WJ, binary Jaccard, implementation divergence,
          and defensive validation functions.

Author: Drake H. Harbert (D.H.H.)
Affiliation: Inner Architecture LLC
Date: 2026-03-21
Updated: 2026-03-24 — Added validate_correlation_matrix, estimate_memory,
         validate_aggregation_match, pipeline_preflight

Usage:
    from wj_utils import weighted_jaccard, signed_weighted_jaccard, \
                          binary_jaccard, implementation_divergence, \
                          validate_correlation_matrix, estimate_memory, \
                          validate_aggregation_match, pipeline_preflight
"""
import numpy as np
from scipy.stats import rankdata


def fast_spearman_matrix(data):
    """Spearman correlation matrix via Pearson on ranks.
    Args: data (n_features x n_samples)
    Returns: n_features x n_features correlation matrix
    """
    n = data.shape[0]
    ranked = np.zeros_like(data, dtype=np.float64)
    for i in range(n):
        ranked[i] = rankdata(data[i])
    ranked -= ranked.mean(axis=1, keepdims=True)
    norms = np.sqrt(np.sum(ranked ** 2, axis=1, keepdims=True))
    norms[norms == 0] = 1.0
    ranked /= norms
    corr = ranked @ ranked.T
    np.clip(corr, -1.0, 1.0, out=corr)
    return corr


def fast_pearson_matrix(data):
    """Pearson correlation matrix.
    Args: data (n_features x n_samples)
    Returns: n_features x n_features correlation matrix
    """
    centered = data - data.mean(axis=1, keepdims=True)
    norms = np.sqrt(np.sum(centered ** 2, axis=1, keepdims=True))
    norms[norms == 0] = 1.0
    centered /= norms
    corr = centered @ centered.T
    np.clip(corr, -1.0, 1.0, out=corr)
    return corr


def weighted_jaccard(corr_A, corr_B):
    """Unsigned weighted Jaccard between two correlation matrices.
    Measures magnitude reorganization. Blind to sign inversions.
    """
    idx = np.triu_indices(corr_A.shape[0], k=1)
    a = np.abs(corr_A[idx])
    b = np.abs(corr_B[idx])
    num = np.minimum(a, b).sum()
    den = np.maximum(a, b).sum()
    return float(num / den) if den > 0 else 1.0


def signed_weighted_jaccard(corr_A, corr_B):
    """Signed weighted Jaccard. Captures sign inversions that unsigned misses.
    Shifts correlations to [0, 2] before computing min/max.
    """
    idx = np.triu_indices(corr_A.shape[0], k=1)
    a = corr_A[idx] + 1.0
    b = corr_B[idx] + 1.0
    num = np.minimum(a, b).sum()
    den = np.maximum(a, b).sum()
    return float(num / den) if den > 0 else 1.0


def binary_jaccard(corr_A, corr_B, threshold=0.3):
    """Binary Jaccard at a given edge threshold.
    Measures topological reorganization (edges gained/lost).
    """
    idx = np.triu_indices(corr_A.shape[0], k=1)
    a = np.abs(corr_A[idx]) >= threshold
    b = np.abs(corr_B[idx]) >= threshold
    intersection = (a & b).sum()
    union = (a | b).sum()
    return float(intersection / union) if union > 0 else 1.0


def implementation_divergence(corr_A, corr_B):
    """Compute the implementation divergence between unsigned and signed WJ.
    Returns a dict with:
      - wj_unsigned: standard WJ (blind to sign inversions)
      - wj_signed: signed WJ (captures sign inversions)
      - gap: signed - unsigned (always >= 0)
      - sign_inversion_pct: % of reorganization from sign inversions
      - magnitude_change_pct: % of reorganization from magnitude changes
    The gap IS the blind spot map. Where gap is large, unsigned WJ is
    missing signal that signed WJ captures (sign inversions).
    """
    wj_u = weighted_jaccard(corr_A, corr_B)
    wj_s = signed_weighted_jaccard(corr_A, corr_B)
    gap = wj_s - wj_u
    reorg_unsigned = 1.0 - wj_u
    reorg_signed = 1.0 - wj_s

    if reorg_unsigned > 0:
        sign_inv_pct = gap / reorg_unsigned * 100
        magnitude_pct = 100 - sign_inv_pct
    else:
        sign_inv_pct = 0.0
        magnitude_pct = 100.0

    return {
        'wj_unsigned': wj_u,
        'wj_signed': wj_s,
        'gap': gap,
        'sign_inversion_pct': sign_inv_pct,
        'magnitude_change_pct': magnitude_pct,
    }


def weighted_jaccard_chunked(corr_A, corr_B, chunk_size=2000):
    """Memory-efficient unsigned WJ using chunked upper triangle extraction.
    Use when n_features > 10,000 and full upper triangle won't fit in RAM.
    """
    n = corr_A.shape[0]
    num = 0.0
    den = 0.0
    for i in range(0, n, chunk_size):
        ie = min(i + chunk_size, n)
        for j in range(i, n, chunk_size):
            je = min(j + chunk_size, n)
            a = np.abs(corr_A[i:ie, j:je])
            b = np.abs(corr_B[i:ie, j:je])
            if i == j:
                mask = np.triu(np.ones((ie - i, je - j), dtype=bool), k=1)
                num += np.minimum(a[mask], b[mask]).sum()
                den += np.maximum(a[mask], b[mask]).sum()
            elif j > i:
                num += np.minimum(a, b).sum()
                den += np.maximum(a, b).sum()
    return float(num / den) if den > 0 else 1.0


# =============================================================================
# DEFENSIVE VALIDATION FUNCTIONS
# Added 2026-03-24 to prevent recurring pipeline crashes and methodology errors.
# Every pipeline should call pipeline_preflight() before computation.
# =============================================================================


def validate_correlation_matrix(matrix, label=""):
    """Validate a correlation matrix for common corruption patterns.
    Checks: NaN, Inf, symmetry, diagonal=1, values in [-1, 1].
    Raises ValueError with specific diagnosis on failure.
    Returns True if clean.
    """
    prefix = f"[{label}] " if label else ""

    if not isinstance(matrix, np.ndarray):
        raise ValueError(f"{prefix}Expected numpy array, got {type(matrix)}")

    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(
            f"{prefix}Expected square matrix, got shape {matrix.shape}"
        )

    # NaN check
    nan_count = np.isnan(matrix).sum()
    if nan_count > 0:
        nan_rows = np.where(np.isnan(matrix).any(axis=1))[0]
        raise ValueError(
            f"{prefix}NaN contamination: {nan_count} NaN values in "
            f"{len(nan_rows)} rows. First affected rows: "
            f"{nan_rows[:5].tolist()}. Check for constant-value features "
            f"(zero variance) that produce undefined correlations."
        )

    # Inf check
    inf_count = np.isinf(matrix).sum()
    if inf_count > 0:
        raise ValueError(
            f"{prefix}Inf values detected: {inf_count}. Check for division "
            f"by zero in correlation computation."
        )

    # Range check
    out_of_range = ((matrix < -1.0 - 1e-10) | (matrix > 1.0 + 1e-10)).sum()
    if out_of_range > 0:
        vmin, vmax = matrix.min(), matrix.max()
        raise ValueError(
            f"{prefix}Values outside [-1, 1]: {out_of_range} entries. "
            f"Range: [{vmin:.6f}, {vmax:.6f}]. This is not a valid "
            f"correlation matrix."
        )

    # Symmetry check
    asym = np.abs(matrix - matrix.T).max()
    if asym > 1e-10:
        raise ValueError(
            f"{prefix}Matrix is not symmetric. Max asymmetry: {asym:.2e}. "
            f"Check that the correlation function produces symmetric output."
        )

    # Diagonal check
    diag = np.diag(matrix)
    diag_off = np.abs(diag - 1.0)
    if diag_off.max() > 1e-10:
        bad_idx = np.where(diag_off > 1e-10)[0]
        raise ValueError(
            f"{prefix}Diagonal not all 1.0. {len(bad_idx)} entries deviate. "
            f"First: index {bad_idx[0]}, value {diag[bad_idx[0]]:.6f}. "
            f"Check for zero-variance features."
        )

    return True


def estimate_memory(n_features, n_samples=None, dtype_bytes=8):
    """Estimate peak memory for WJ pipeline and warn if >80% of system RAM.

    Args:
        n_features: number of fundamental units (genes, sensors, stocks, etc.)
        n_samples: number of observations per feature (optional, for raw data)
        dtype_bytes: bytes per element (default 8 for float64)

    Returns:
        dict with estimated_gb, available_gb, pct_of_ram, safe (bool), message
    """
    import psutil
    available_bytes = psutil.virtual_memory().total
    available_gb = available_bytes / (1024 ** 3)

    # Correlation matrix: n_features x n_features
    corr_bytes = n_features * n_features * dtype_bytes
    # Two correlation matrices (condition A and B)
    two_corr = corr_bytes * 2
    # Upper triangle extraction: n_features*(n_features-1)/2 * dtype_bytes * 2
    tri_bytes = int(n_features * (n_features - 1) / 2) * dtype_bytes * 2
    # Raw data if provided
    raw_bytes = (n_features * n_samples * dtype_bytes) if n_samples else 0

    peak_bytes = two_corr + tri_bytes + raw_bytes
    peak_gb = peak_bytes / (1024 ** 3)
    pct = (peak_bytes / available_bytes) * 100

    safe = pct < 80.0
    if safe:
        msg = (f"Estimated peak: {peak_gb:.2f} GB / {available_gb:.1f} GB "
               f"({pct:.1f}%). OK.")
    else:
        msg = (f"WARNING: Estimated peak: {peak_gb:.2f} GB / "
               f"{available_gb:.1f} GB ({pct:.1f}%). Exceeds 80% threshold. "
               f"Use weighted_jaccard_chunked() or reduce to streaming "
               f"computation.")

    return {
        'estimated_gb': round(peak_gb, 2),
        'available_gb': round(available_gb, 1),
        'pct_of_ram': round(pct, 1),
        'safe': safe,
        'message': msg,
    }


def validate_aggregation_match(df_a, df_b, label_a="A", label_b="B"):
    """Confirm two dataframes are at the same aggregation level.
    Detects subject-level vs group-averaged mismatch.

    Args:
        df_a, df_b: pandas DataFrames or numpy arrays
        label_a, label_b: names for error messages

    Returns:
        dict with matched (bool), details (str)

    Raises ValueError if clear mismatch detected.
    """
    shape_a = df_a.shape
    shape_b = df_b.shape

    if len(shape_a) == 2 and len(shape_b) == 2:
        samples_a = min(shape_a)
        samples_b = min(shape_b)

        # One sample vs many = group-average vs subject-level
        if samples_a == 1 and samples_b > 1:
            raise ValueError(
                f"Aggregation mismatch: {label_a} has {samples_a} sample "
                f"(group-averaged?) but {label_b} has {samples_b} samples "
                f"(subject-level?). Both must be at the same level."
            )
        if samples_b == 1 and samples_a > 1:
            raise ValueError(
                f"Aggregation mismatch: {label_b} has {samples_b} sample "
                f"(group-averaged?) but {label_a} has {samples_a} samples "
                f"(subject-level?). Both must be at the same level."
            )

        # >10x difference in sample count = likely mismatch
        if samples_a > 0 and samples_b > 0:
            ratio = max(samples_a, samples_b) / min(samples_a, samples_b)
            if ratio > 10:
                return {
                    'matched': False,
                    'details': (
                        f"WARNING: {label_a} has {samples_a} samples, "
                        f"{label_b} has {samples_b} samples (ratio: "
                        f"{ratio:.1f}x). Verify both are at the same "
                        f"aggregation level."
                    ),
                }

    return {
        'matched': True,
        'details': (
            f"{label_a} shape {shape_a}, {label_b} shape {shape_b}. "
            f"Aggregation levels appear consistent."
        ),
    }


def pipeline_preflight(n_features, n_samples=None, corr_matrices=None,
                       data_pairs=None):
    """Run all validation checks before pipeline computation begins.
    Call this at the top of every pipeline after loading data.

    Args:
        n_features: number of fundamental units
        n_samples: samples per feature (for memory estimation)
        corr_matrices: list of (matrix, label) tuples to validate
        data_pairs: list of (df_a, df_b, label_a, label_b) tuples
                    to check aggregation match

    Returns:
        dict with all_clear (bool), checks (list of results)

    Raises ValueError on hard failures (NaN, memory, aggregation mismatch).
    """
    checks = []
    all_clear = True

    # Memory check
    mem = estimate_memory(n_features, n_samples)
    checks.append({'check': 'memory', 'result': mem})
    if not mem['safe']:
        all_clear = False
        print(f"PREFLIGHT FAIL: {mem['message']}")
    else:
        print(f"PREFLIGHT OK: {mem['message']}")

    # Correlation matrix validation
    if corr_matrices:
        for matrix, label in corr_matrices:
            try:
                validate_correlation_matrix(matrix, label)
                checks.append({
                    'check': f'corr_matrix_{label}',
                    'result': 'PASS',
                })
                print(f"PREFLIGHT OK: [{label}] correlation matrix clean "
                      f"({matrix.shape[0]}x{matrix.shape[1]})")
            except ValueError as e:
                all_clear = False
                checks.append({
                    'check': f'corr_matrix_{label}',
                    'result': f'FAIL: {e}',
                })
                raise

    # Aggregation match
    if data_pairs:
        for df_a, df_b, la, lb in data_pairs:
            result = validate_aggregation_match(df_a, df_b, la, lb)
            checks.append({
                'check': f'aggregation_{la}_vs_{lb}',
                'result': result,
            })
            if result['matched']:
                print(f"PREFLIGHT OK: {result['details']}")
            else:
                all_clear = False
                print(f"PREFLIGHT WARN: {result['details']}")

    if all_clear:
        print("PREFLIGHT: All checks passed.")
    else:
        print("PREFLIGHT: Issues detected. Review warnings above.")

    return {'all_clear': all_clear, 'checks': checks}
