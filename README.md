# MetaSprint DTA

Browser-based diagnostic test accuracy meta-analysis with automated open-access evidence discovery.

## Features

- Bivariate REML and HSROC models for diagnostic test accuracy meta-analysis.
- Open-access discovery pipeline across ClinicalTrials.gov, Europe PMC, OpenAlex, and PubMed.
- Validation against 70 published DTA meta-analyses across 13 specialties.
- R cross-validation with `mada` and `metafor` (`33/33` parity).
- Advanced diagnostics including Cook's D, DFBETAS, Copas selection model, P-curve, profile-likelihood CIs, bootstrap BCa, and LASSO meta-regression.
- One-click export of R, Python, and Stata replication code.
- Forest plots, SROC curves, Deeks' funnel, decision-curve analysis, and Fagan nomograms.
- QUADAS-2, GRADE-DTA, and PRISMA-DTA reporting support.

## Live Demo

Main app: <https://mahmood726-cyber.github.io/metasprint-dta/>

Validated examples:

- Heart failure + BNP: <https://mahmood726-cyber.github.io/metasprint-dta/metasprint-dta.html?demo=bnp>
- Tuberculosis + Xpert MTB/RIF: <https://mahmood726-cyber.github.io/metasprint-dta/metasprint-dta.html?demo=tb>
- Appendicitis + Ultrasound: <https://mahmood726-cyber.github.io/metasprint-dta/metasprint-dta.html?demo=appendicitis>
- COVID-19 + Rapid antigen test: <https://mahmood726-cyber.github.io/metasprint-dta/metasprint-dta.html?demo=covid>

## Quick Start

Open `metasprint-dta.html` in a modern browser. No installation is required for end users.

## Validation

| Suite | Tests | Status |
|-------|------:|--------|
| Unit tests (`test_oa_discovery.py`) | 74 | PASS |
| Advanced methods (`test_advanced_methods.py`) | 88 | PASS |
| R cross-validation (`R_validation/test_r_validation.py`) | 33 | PASS |
| Topic validation (`test_13_topics.py` + `test_post2015_topics.py`) | 50 | PASS |
| Total | 245 | ALL PASS |

### R Validation

```bash
Rscript R_validation/validate_metasprint_dta.R
python R_validation/test_r_validation.py
```

### Local Validation

```bash
python test_oa_discovery.py
python test_advanced_methods.py
python test_13_topics.py
python test_post2015_topics.py
```

Validation automation requires Python 3.9+, selenium, Chrome, and ChromeDriver. End users only need a browser.

## Statistical Methods

| Method | Implementation | R Equivalent |
|--------|---------------|--------------|
| Bivariate GLMM | DerSimonian-Laird on logit scale, t(k-2) CIs | `mada::reitsma()` |
| HSROC | Moses-Littenberg, AUC via `Phi(Lambda/sqrt(2))` | `mada::SummaryPts()` |
| Heterogeneity | I-squared with Higgins-Thompson CIs | `metafor::rma()` |
| Publication bias | Deeks' funnel, Copas selection, trim-and-fill, P-curve | `lm()` on `logDOR ~ 1/sqrt(ESS)` |
| Influence | Cook's D, DFBETAS, leave-one-out | manual LOO |
| CIs | Wilson score, Clopper-Pearson, profile likelihood | `PropCIs::scoreci()` |
| Bootstrap | BCa with jackknife acceleration | manual |

## Open-Access Discovery Pipeline

The app searches four open-access sources in parallel for diagnostic-test studies:

1. ClinicalTrials.gov
2. Europe PMC
3. OpenAlex
4. PubMed E-utilities

Extraction patterns support multiple sensitivity/specificity formats, PPA/NPA, PPV/NPV, AUC, LR+/LR-, DOR, threshold data, prevalence, TP/FP/FN/TN counts, and common abstract reporting variants.

## Citation

Use `CITATION.cff` for software citation metadata. The F1000Research software article is still in preparation.

## Repository

<https://github.com/mahmood726-cyber/metasprint-dta>

## Zenodo DOI

Pending tagged GitHub release and Zenodo archive.

## License

MIT. See `LICENSE`.
