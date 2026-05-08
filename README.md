# Weighted Jaccard Pairing-Family Decomposition of S&P 500 Correlation Networks

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19025536.svg)](https://doi.org/10.5281/zenodo.19025536)

**Author:** Drake H. Harbert (D.H.H.)
**Affiliation:** Inner Architecture LLC, Canton, OH
**ORCID:** [0009-0007-7740-3616](https://orcid.org/0009-0007-7740-3616)

## Overview

Complete analysis pipeline for detecting bidirectional structural regimes in S&P 500 correlation networks using the weighted Jaccard (WJ) similarity index applied to Spearman rank correlations among 478 individual S&P 500 constituent stocks (114,003 pairwise correlations, 2003-2025).

Includes the original WJ-native regime detection pipeline and a Layer 2H pairing-family extension that decomposes correlation reorganization into magnitude and sign components. Sign-inversion percentage rank-correlates with mean realized volatility at rho = -0.873 (p < 10^-64) across 204 valid windows.

## Key Findings

**Original WJ-native regime detection:**
- 6 structural regimes (3 convergence, 3 divergence; all p < 0.001)
- QE-era decorrelation: strongest unsigned signal (WJ = 0.681, z = -22.39), exceeding GFC (WJ = 0.740, z = -18.08)
- Direction-dependent cascades: same-direction tau = 0.525-0.664; cross-direction tau ~= 0.119
- GICS captures ~10% of correlation architecture (ARI = 0.101)
- 2 extreme reorganizers (CVG, EP) across both directions (z = 8.98)

**Pairing-family extension (Layer 2H):**
- Convergence and divergence regimes occupy distinct quadrants of pairing space
- Convergence: large Type 1 gap (mean 0.595), modest Type 2 gap (mean 0.177)
- Divergence: smaller Type 1 gap (mean 0.327), larger Type 2 gap (mean 0.227)
- Sign-inversion fraction vs mean realized volatility: rho = -0.873, p < 10^-64, n=204
- Sign-inversion fraction vs mean VIX: rho = -0.857, p < 10^-59, n=204
- New 2022 structural regime (2022-07-13 to 2022-08-11) detected by signed WJ only; signed WJ = 0.923, z = -13.20, p < 10^-3
- Combined regime catalog: 7 unique regimes 2003-2025
- Frobenius distance does not distinguish regimes (uniform 0.090-0.098)

## Repository Contents

### Pipeline scripts
- `financial_wj_pipeline.py` - Original primary pipeline (regime detection + clustering)
- `financial_wj_augmentation.py` - Layer 2H pairing-family extension (per-regime)
- `financial_wj_phase2.py` - Per-window trajectories + macro stress + 2022 regime
- `wj_utils.py` - Shared WJ utilities
- `generate_figures.py` - Original figure generation
- `generate_manuscript.py` - Original manuscript builder
- `build_manuscript_v3.py` - Repositioned manuscript builder

### Outputs (committed)
- `results_summary/` - 11 small CSVs and 2 provenance JSONs from augmentation and Phase 2 runs
- `figures_v3/` - 4 new figures in PDF and PNG

## Reproduction
```
pip install -r requirements.txt
python financial_wj_pipeline.py
python financial_wj_augmentation.py
python financial_wj_phase2.py
python build_manuscript_v3.py
```
Total runtime ~30 minutes on a 16 GB workstation.

## Citation

**Manuscript (in submission):**
Harbert, D.H. (2026). A Pairing-Family Decomposition of the Weighted Jaccard Index Reveals Direction-Specific Reorganization Modes and Macro-Stress-Coupled Sign-Inversion Dynamics in S&P 500 Correlation Networks (2003-2025). *Physica A: Statistical Mechanics and its Applications* (under review).

**Code and data (Zenodo):** https://doi.org/10.5281/zenodo.19025536

## License

MIT License. See `LICENSE`.

## Contact

Drake H. Harbert
Inner Architecture LLC, Canton, OH
Drake@innerarchitecturellc.com
