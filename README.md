# Weighted Jaccard Detects Bidirectional Structural Regimes in S&P 500 Correlation Networks

**Author:** Drake H. Harbert (D.H.H.)
**Affiliation:** Inner Architecture LLC, Canton, OH
**ORCID:** [0009-0007-7740-3616](https://orcid.org/0009-0007-7740-3616)

## Overview

This repository contains the complete analysis pipeline for detecting bidirectional structural regimes in S&P 500 correlation networks using the weighted Jaccard (WJ) similarity index applied to Spearman rank correlations.

**Key finding:** The QE-era decorrelation (December 2016–September 2017) is the deepest structural regime in 22 years of S&P 500 data — more extreme than the Global Financial Crisis. WJ detects both convergence (correlation increase) and divergence (correlation decrease) reorganization, revealing that cascade ordering is direction-dependent.

## Key Results

- **6 structural regimes** detected algorithmically (3 convergence, 3 divergence; all p < 0.001)
- **QE decorrelation** produces the strongest signal (WJ = 0.681, z = −22.39), exceeding GFC (WJ = 0.740, z = −18.08)
- **Direction-dependent cascades**: same-direction tau = 0.525–0.664; cross-direction tau ≈ 0.119
- **GICS captures ~10%** of correlation architecture (ARI = 0.101)
- **2 extreme reorganizers** (CVG, EP) identified across both directions (z = 8.98)

## Requirements

```
pip install -r requirements.txt
```

Python 3.10+. See `requirements.txt` for dependencies.

## Data

- **S&P 500 constituents:** Historical membership from [fja05680/sp500](https://github.com/fja05680/sp500) (MIT license)
- **Price data:** Yahoo Finance daily adjusted closing prices (2003–2025)
- **GICS sectors:** Current S&P 500 sector classifications (comparison only, not used as analytical input)

Data files are not included in this repository. The pipeline downloads and caches data automatically on first run.

## Pipeline

### `financial_wj_pipeline.py`

Complete WJ-native analysis pipeline. Single execution produces all results.

```
python financial_wj_pipeline.py
```

**Stages:**
1. Data loading (478 stocks, 5,785 days, 114,003 pairwise correlations)
2. Rolling WJ trajectory (264 windows, Spearman correlations)
3. Algorithmic regime detection (sliding 5-year baseline)
4. WJ-native baseline construction (pooled normal-state windows)
5. Regime-level WJ with permutation testing (5,000 permutations)
6. Stock-level fingerprint reorganization
7. WJ-native fingerprint clustering
8. Natural group (epicenter) discovery
9. Cascade stability analysis

### `generate_figures.py`

Generates all 8 publication figures (300 DPI PNG + PDF).

### `generate_manuscript.py`

Generates the manuscript .docx file from pipeline outputs.

## Methodology

- **Fundamental units:** Individual stocks (never ETFs, indices, or sector composites)
- **Correlation method:** Spearman rank correlation (robust to non-normal return distributions)
- **Full pairwise matrix:** All 114,003 pairs, no pre-filtering
- **Regime detection:** Algorithmic, no manually imposed dates
- **Random seed:** 42 (all results reproducible)
- **GICS sectors:** Post-discovery comparison only

## AI Disclosure

Claude (Anthropic) was used as a programming assistant during pipeline development, manuscript formatting, and code review. All analytical decisions, methodology design, data interpretation, and scientific conclusions are solely the work of the author.

## License

MIT

## Citation

Harbert, D.H. (2026). Weighted Jaccard Detects Bidirectional Structural Regimes in S&P 500 Correlation Networks: QE-Era Decorrelation as the Deepest Reorganization Event (2003–2025). *Physica A: Statistical Mechanics and its Applications*, under review.
