# MetaSprint DTA

Browser-based diagnostic test accuracy meta-analysis with automated open-access evidence discovery.

## Features

- **Bivariate REML** (Reitsma et al. 2005, REML tau-squared) and **HSROC** (Rutter & Gatsonis 2001) models
- **OA Discovery Pipeline** — searches CT.gov, Europe PMC, OpenAlex, and PubMed in parallel; extracts sensitivity/specificity from abstracts; back-calculates 2x2 tables
- **70-topic validation** against published DTA meta-analyses (100% pass rate across 13 specialties)
- **R cross-validation** — 33/33 parity with R mada 0.5.12 + metafor 4.8.0
- **10 advanced methods**: Cook's D/DFBETAS, Copas selection model, P-curve, profile likelihood CIs, bootstrap BCa, LASSO meta-regression, what-if simulator, NND with CIs
- **Auto-generated text**: Methods and Results sections ready for manuscripts
- **R/Python/Stata replication code** export with one click
- Forest plots, SROC curves, Deeks' funnel, DCA, Fagan nomogram
- QUADAS-2 risk of bias, GRADE-DTA, PRISMA-DTA checklist
- Dark/light mode, full keyboard accessibility

## Live Demo

**Try it now:** [https://mahmood726-cyber.github.io/metasprint-dta/](https://mahmood726-cyber.github.io/metasprint-dta/)

Quick demo links (auto-load a validated topic):
- [Heart failure + BNP](https://mahmood726-cyber.github.io/metasprint-dta/metasprint-dta.html?demo=bnp)
- [Tuberculosis + Xpert MTB/RIF](https://mahmood726-cyber.github.io/metasprint-dta/metasprint-dta.html?demo=tb)
- [Appendicitis + Ultrasound](https://mahmood726-cyber.github.io/metasprint-dta/metasprint-dta.html?demo=appendicitis)
- [COVID-19 + Rapid antigen test](https://mahmood726-cyber.github.io/metasprint-dta/metasprint-dta.html?demo=covid)

## Quick Start

Open `metasprint-dta.html` in any modern browser (Chrome, Firefox, Edge, Safari). No installation required.

## Validation

| Suite | Tests | Status |
|-------|-------|--------|
| Unit tests (`test_oa_discovery.py`) | 74 | PASS |
| Advanced methods (`test_advanced_methods.py`) | 88 | PASS |
| R cross-validation (`R_validation/test_r_validation.py`) | 33 | PASS |
| Topic validation (`test_13_topics.py` + `test_post2015_topics.py`) | 50 | PASS |
| **Total** | **245** | **ALL PASS** |

### R Validation

```bash
# Generate R reference values (requires R + mada + metafor + PropCIs)
Rscript R_validation/validate_metasprint_dta.R

# Compare app output against R reference
python R_validation/test_r_validation.py
```

### Run All Tests

```bash
python test_oa_discovery.py
python test_advanced_methods.py
python test_13_topics.py
python test_post2015_topics.py
```

Requires: Python 3.9+, selenium, Chrome + ChromeDriver.

## Statistical Methods

| Method | Implementation | R Equivalent |
|--------|---------------|--------------|
| Bivariate GLMM | DerSimonian-Laird on logit scale, t(k-2) CIs | `mada::reitsma()` |
| HSROC | Moses-Littenberg, AUC via Phi(Lambda/sqrt(2)) | `mada::SummaryPts()` |
| Heterogeneity | I-squared with Higgins-Thompson CIs | `metafor::rma()` |
| Publication bias | Deeks' funnel, Copas selection, trim-and-fill, P-curve | `lm()` on logDOR~1/sqrt(ESS) |
| Influence | Cook's D (p=2), DFBETAS, leave-one-out | Manual LOO |
| CIs | Wilson score, Clopper-Pearson, profile likelihood | `PropCIs::scoreci()` |
| Bootstrap | BCa with jackknife acceleration | Manual |

## OA Discovery Pipeline

Searches 4 open-access sources in parallel for DTA studies on any condition + index test combination:

1. **ClinicalTrials.gov** — completed interventional/observational with results
2. **Europe PMC** — open-access abstracts with DTA MeSH terms
3. **OpenAlex** — open-access works with concept filtering
4. **PubMed E-utilities** — direct PubMed search with DTA filters

Extraction patterns handle: sensitivity/specificity (6+ formats), PPA/NPA, PPV/NPV with CIs, AUC/AUROC/C-statistic with CIs, LR+/LR-/DOR, FPR/FNR derivation, threshold/cutoff, prevalence, TP/FP/FN/TN direct, fraction format, "respectively" format, parenthetical format, detection rate, "no false positives", screen-positive rate.

Text preprocessing: Unicode normalization (U+037E, fullwidth chars), OCR correction (Cl->CI, O->0), European decimal comma handling.

## License

MIT License. See [LICENSE](LICENSE).

## Citation

[CITATION_PLACEHOLDER] — manuscript in preparation for F1000Research.

## Repository

https://github.com/mahmood726-cyber/metasprint-dta

## Zenodo DOI

[ZENODO_DOI_PLACEHOLDER]
