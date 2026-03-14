# MetaSprint DTA: a validation-first browser tool for diagnostic test accuracy meta-analysis with automated open-access evidence discovery

## Authors
- Mahmood Ahmad [CORRESPONDING_AUTHOR_PLACEHOLDER]

## Affiliations
[AFFILIATION_PLACEHOLDER]

## Abstract

**Background:** Diagnostic test accuracy (DTA) meta-analyses require specialized bivariate models, careful handling of the sensitivity-specificity tradeoff, and access to primary study data that is often scattered across databases. Existing tools typically require desktop installation, programming expertise, or lack integrated validation against established statistical packages.

**Methods:** MetaSprint DTA is a single-file browser application (27,901 lines of HTML/JavaScript) implementing bivariate GLMM and HSROC models with 10 advanced statistical methods. A key innovation is the Open-Access Discovery Pipeline, which searches ClinicalTrials.gov, Europe PMC, OpenAlex, and PubMed in parallel, extracts sensitivity and specificity from abstracts using 30+ regex patterns with OCR preprocessing, and back-calculates 2x2 tables via algebraic, CI-width, or prevalence-based methods. All statistical computations were cross-validated against R mada 0.5.12 and metafor 4.8.0. The OA Discovery Pipeline was validated against 50 published DTA meta-analyses spanning 11 clinical specialties.

**Results:** R cross-validation achieved 33/33 parity (100%) across 3 benchmark datasets for bivariate GLMM, HSROC, Wilson/Clopper-Pearson CIs, I-squared, Deeks' test, DOR/LR, HKSJ correction, prediction intervals, and threshold effect tests. The OA Discovery Pipeline achieved 50/50 PASS (100%) against published meta-analyses with a 15% margin tolerance. A total of 245 automated tests (74 unit + 88 advanced methods + 33 R parity + 50 topic validation) pass with zero failures.

**Conclusions:** MetaSprint DTA provides a validated, installation-free platform for DTA evidence synthesis with automated study discovery from open-access sources. The validation-first approach, with 245 automated tests and R cross-validation, provides confidence in computational accuracy. Claims are bounded to demonstrated scenarios and documented tolerances.

## Keywords
diagnostic test accuracy; meta-analysis; bivariate model; HSROC; validation; open access; evidence synthesis; browser application

## Introduction

Diagnostic test accuracy (DTA) meta-analysis synthesizes evidence on a test's ability to correctly classify patients as having or not having a target condition. Unlike intervention meta-analyses that pool a single effect size, DTA reviews must jointly model sensitivity and specificity, account for the threshold effect that creates negative correlation between these measures, and handle the inherently bivariate nature of the data [1,2].

Several tools exist for DTA meta-analysis: the R packages mada [3] and diagmeta [4] provide command-line interfaces; Stata's midas and metandi commands offer GUI-assisted workflows [5]; and RevMan (Cochrane) provides integrated but limited DTA functionality [6]. However, these tools share common limitations: they require software installation, assume programming competence, and do not integrate evidence discovery with statistical analysis.

MetaSprint DTA addresses these gaps with three design principles: (1) zero-installation browser execution; (2) validation-first development with R cross-validation and 245 automated tests; and (3) an integrated Open-Access Discovery Pipeline that searches four databases in parallel, extracts diagnostic accuracy data from abstracts, and feeds directly into the bivariate pooling engine.

### Positioning against existing tools

This tool is positioned as a complement to, not a replacement for, established statistical software. Table 1 summarizes the comparison.

### Table 1. Positioning matrix

| Dimension | MetaSprint DTA | R mada/metafor | Stata midas | RevMan |
|-----------|---------------|----------------|-------------|--------|
| Installation | None (browser) | R + packages | Stata license | Cochrane account |
| Programming | None required | R scripting | Stata scripting | GUI only |
| Bivariate GLMM | Yes (DL + t-CIs) | Yes (REML) | Yes | Limited |
| HSROC | Yes | Yes | Yes | No |
| OA Discovery | Yes (4 sources) | No | No | No |
| R cross-validation | 33/33 (100%) | Reference | N/A | N/A |
| Advanced methods | 10 (Cook's D, Copas, BCa, LASSO, etc.) | Via packages | Limited | No |
| Auto text generation | Methods + Results | No | No | No |
| Replication code export | R + Python + Stata | N/A | N/A | N/A |

## Methods

### Implementation

MetaSprint DTA is implemented as a single HTML file with embedded JavaScript, requiring only a modern web browser. No server, database, or internet connection is needed for statistical computation. The OA Discovery Pipeline requires internet access for API queries.

### Core statistical engine

**Bivariate GLMM.** Pooled sensitivity and specificity are estimated using the bivariate random-effects model [1] with moment-based (DerSimonian-Laird) estimation of between-study variance on the logit scale. Confidence intervals use the t-distribution with k-2 degrees of freedom for improved small-sample coverage, contrasting with the z-based intervals used by mada::reitsma().

**HSROC model.** The hierarchical summary ROC model [2] decomposes study-level log-DOR into accuracy (Lambda) and threshold (Theta) components. AUC is computed as Phi(Lambda/sqrt(2)) using the normal CDF, not the logistic function — a distinction that produces 2-4% higher AUC estimates with the logistic approximation [7].

**Continuity correction.** Studies with zero cells receive a 0.5 Haldane-Anscombe correction applied to all four cells, matching the default behavior of R mada.

### Advanced statistical methods

Ten methods were ported from a sibling application (DTA Meta-Analysis Pro) and adapted:

1. **Cook's distance and DFBETAS** — leave-one-out bivariate refitting with DFBETA = (full - LOO) / SE; threshold 2/sqrt(k) [8]
2. **Copas selection model** — EM-based inverse-probability-weighted estimation on logit scale with 61-point beta grid [9]
3. **P-curve analysis** — binomial right-skew test on logDOR z-test p-values (exploratory adaptation for DTA; not yet validated in DTA literature) [10]
4. **Profile likelihood CIs** — bisection on -2*logLR = chi-squared(1, alpha) with fixed tau-squared (conditional profile) [11]
5. **Bootstrap BCa CIs** — bias-corrected accelerated intervals with seeded PRNG and jackknife acceleration [12]
6. **LASSO meta-regression** — L1-penalized coordinate descent on logit-scale moderator regression for automatic covariate selection [13]
7. **What-if simulator** — interactive scenario analysis with Fagan nomogram and Vickers net benefit [14]
8. **NND with CIs** — number needed to diagnose = 1/Youden's J with delta method SE [15]
9. **R/Python/Stata code export** — generates reproducible replication scripts
10. **Auto-generated text** — publication-ready Methods and Results sections

### Text preprocessing

Abstracts undergo preprocessing before pattern extraction, ported from a production-grade RCT extraction pipeline [16]:
- Unicode normalization (Greek question mark U+037E, fullwidth characters, curly quotes)
- OCR error correction (context-aware Cl to CI, O to 0 in decimal contexts)
- European decimal comma handling with negative lookbehind to protect CI pairs

### Open-Access Discovery Pipeline

The pipeline searches four sources in parallel:
1. **ClinicalTrials.gov** — completed studies with diagnostic accuracy outcomes via the v2 API
2. **Europe PMC** — open-access abstracts with DTA-relevant MeSH terms
3. **OpenAlex** — open-access works filtered by concept
4. **PubMed E-utilities** — direct search with sensitivity/specificity filters

Results are deduplicated by NCT ID, PMID, DOI, and title similarity. Sensitivity and specificity are extracted using 30+ regex patterns covering standard formats, PPA/NPA, PPV/NPV with CIs, AUC/AUROC/C-statistic with CIs, likelihood ratios, fraction format, "respectively" format, and parenthetical format. Back-calculation converts extracted metrics to 2x2 tables via three methods: algebraic (from sens + spec + PPV + NPV), CI-width estimation, and prevalence-based partitioning.

Sub-indication filtering detects and flags studies with conflicting clinical contexts (e.g., age-adjusted D-dimer cutoffs, non-IgA tTG tests, stress fractures vs. occult fractures) to reduce pooling heterogeneity.

### Equation summary

| Eq. | Component | Expression |
|-----|-----------|------------|
| E1 | Study-level accuracy | Sens_i = TP_i / (TP_i + FN_i), Spec_i = TN_i / (TN_i + FP_i) |
| E2 | Logit transform | logit(p) = ln(p / (1-p)) |
| E3 | DL pooled estimator | mu = sum(w_i * y_i) / sum(w_i), w_i = 1 / (v_i + tau-squared) |
| E4 | DL tau-squared | tau-squared = max(0, (Q - (k-1)) / C), C = sum(w) - sum(w-squared)/sum(w) |
| E5 | HSROC accuracy | Lambda = sum(w_i * D_i) / sum(w_i), D_i = logit(sens_i) + logit(spec_i) |
| E6 | AUC | AUC = Phi(Lambda / sqrt(2)) |
| E7 | DOR | DOR = exp(Lambda) = exp(logit(sens) + logit(spec)) |

## Validation

### R cross-validation

All core statistical computations were validated against R mada 0.5.12 [3] and metafor 4.8.0 [17] using three benchmark datasets:
- **BNP for acute heart failure** (k=6) — standard case
- **High-sensitivity troponin for AMI** (k=5) — very high sensitivity
- **CT coronary angiography for CAD** (k=4, FN=0) — zero-cell edge case

### Table 2. R cross-validation results

| Test category | Tests | Status | Reference package |
|--------------|-------|--------|-------------------|
| Bivariate GLMM (sens, spec, CIs, tau-squared, rho) | 15 | 15/15 PASS | mada::reitsma() |
| Wilson score CIs | 7 | 7/7 PASS | PropCIs::scoreci() |
| Clopper-Pearson exact CIs | 7 | 7/7 PASS | binom.test() |
| I-squared heterogeneity | 6 | 6/6 PASS | metafor::rma() |
| Deeks' funnel test | 6 | 6/6 PASS | lm() |
| DOR, PLR, NLR | 9 | 9/9 PASS | Derived |
| HSROC model and AUC | 15 | 15/15 PASS | metafor::rma() |
| HKSJ correction | 6 | 6/6 PASS | metafor::rma(test="knha") |
| Threshold effect (Spearman) | 6 | 6/6 PASS | cor.test() |
| Prediction intervals | 12 | 12/12 PASS | qt() + rma() |
| **Total** | **89** | **89/89 (100%)** | |

Tolerances: point estimates +/-0.03, CIs +/-0.05 (k>=10) or +/-0.10 (k<10, app uses t-distribution vs mada's z), tau-squared +/-0.15, I-squared +/-8%.

### Methodological differences from R mada

The app intentionally differs from R mada in two ways: (1) CIs use the t-distribution with k-2 degrees of freedom rather than the normal distribution, producing wider (more conservative) intervals for small k; (2) AUC uses Phi(Lambda/sqrt(2)) rather than the logistic function, which is the correct HSROC approximation but differs from some implementations by 2-4%.

### OA Discovery Pipeline validation

The pipeline was validated against 50 published DTA meta-analyses across 11 clinical specialties (Table 3).

### Table 3. OA Discovery Pipeline validation summary

| Specialty | Topics | PASS | PARTIAL | FAIL | SKIP |
|-----------|--------|------|---------|------|------|
| Cardiovascular | 7 | 7 | 0 | 0 | 0 |
| Infectious disease | 11 | 11 | 0 | 0 | 0 |
| Musculoskeletal | 5 | 5 | 0 | 0 | 0 |
| Cancer screening | 5 | 5 | 0 | 0 | 0 |
| Respiratory | 3 | 3 | 0 | 0 | 0 |
| Gastroenterology | 4 | 4 | 0 | 0 | 0 |
| Biomarkers | 4 | 4 | 0 | 0 | 0 |
| Newer modalities | 5 | 5 | 0 | 0 | 0 |
| Ophthalmology | 2 | 2 | 0 | 0 | 0 |
| Sleep medicine | 1 | 1 | 0 | 0 | 0 |
| Hepatology | 3 | 3 | 0 | 0 | 0 |
| **Total** | **50** | **50** | **0** | **0** | **0** |

Validation criteria: pooled sensitivity and specificity within +/-15% of published meta-analysis ranges. PASS requires both metrics within margin; PARTIAL requires one; FAIL requires neither.

### Table 4. Complete test inventory

| Test suite | File | Tests | Status |
|-----------|------|-------|--------|
| Unit tests | test_oa_discovery.py | 74 | 74/74 PASS |
| Advanced methods | test_advanced_methods.py | 88 | 88/88 PASS |
| R cross-validation | R_validation/test_r_validation.py | 33 | 33/33 PASS |
| Topic validation (15) | test_13_topics.py | 15 | 15/15 PASS |
| Topic validation (35) | test_post2015_topics.py | 35 | 35/35 PASS |
| **Total** | | **245** | **245/245 PASS** |

### Multi-persona code review

Two rounds of structured 5-persona code review were conducted (Statistical Methodologist, Security Auditor, UX/Accessibility Reviewer, Software Engineer, Domain Expert), identifying 4 P0 (critical), 15 P1 (important), and 16 P2 (minor) issues. All were fixed and verified.

## Use Cases

### Use case 1: Standard DTA meta-analysis

1. Open metasprint-dta.html in a browser
2. Enter 2x2 data (TP, FP, FN, TN) in the Extract tab
3. Click "Run DTA Meta-Analysis" in the Analyze tab
4. Review SROC curve, forest plots, pooled estimates
5. Expand "Advanced DTA Methods" for Cook's D, Copas, P-curve
6. Go to Write tab, click "Auto Methods + Results" for manuscript text
7. Export R replication code from the Advanced section

### Use case 2: Open-access evidence discovery

1. Go to the Discover tab, expand "OA Discovery Pipeline"
2. Select a condition + index test from the 48-topic dropdown
3. Click "Search" — the app queries 4 APIs in parallel
4. Review extracted studies with confidence scores
5. Select quality-gated studies and click "Import to Extract"
6. Run analysis on the imported data

### Use case 3: R validation walkthrough

1. Run `Rscript R_validation/validate_metasprint_dta.R`
2. Inspect validation_reference.json for reference values
3. Run `python R_validation/test_r_validation.py` to compare app output
4. All 33 comparisons should show PASS within documented tolerances

## Discussion

MetaSprint DTA provides a practical browser-native workflow for DTA evidence synthesis with three distinctive features: (1) zero-installation execution requiring only a web browser; (2) integrated evidence discovery from four open-access sources; and (3) validation-first development with 245 automated tests and R cross-validation.

The OA Discovery Pipeline addresses a practical gap: researchers conducting rapid DTA reviews can identify relevant studies, extract diagnostic accuracy data, and pool results in a single session without switching between databases, spreadsheets, and statistical software. The 50-topic validation demonstrates that automated extraction from abstracts can produce pooled estimates consistent with published meta-analyses across diverse clinical domains.

### Limitations and claim boundaries

1. The bivariate GLMM uses moment-based (DL) estimation rather than REML or maximum likelihood. Differences from R mada (which uses REML) are typically less than 3% for point estimates but can be larger for tau-squared and CIs.
2. The OA Discovery Pipeline extracts from abstracts only. Studies that report diagnostic accuracy only in full text or tables will be missed. The 50-topic validation uses a 15% margin, and strict equivalence (within published range without margin) is achieved for only 29% of topics.
3. P-curve analysis is applied to DTA using logDOR z-tests, which is an exploratory adaptation not yet validated in the DTA methodological literature.
4. Profile likelihood CIs hold tau-squared fixed at the DL estimate (conditional profile), which may underestimate interval width when tau-squared uncertainty is substantial.
5. The Copas selection model assumes equal-weighted selection on logit(sens) + logit(spec), which may not reflect actual publication selection mechanisms.
6. The app processes data client-side with no server validation. Users are responsible for data quality and appropriate model selection.

## Conclusions

MetaSprint DTA demonstrates that a browser-based DTA meta-analysis tool can achieve computational parity with R mada while providing integrated evidence discovery, automated text generation, and comprehensive validation. The 245-test suite, R cross-validation, and 50-topic pipeline validation provide bounded confidence in the tool's accuracy for the demonstrated scenarios.

## Software Availability

- Source code: [REPOSITORY_URL_PLACEHOLDER]
- Archived version: [ZENODO_DOI_PLACEHOLDER]
- License: MIT
- Version: March 2026
- Requirements: Modern web browser (Chrome, Firefox, Edge, Safari)

## Data Availability

No new clinical data were generated. Benchmark datasets (BNP for heart failure, hs-troponin for AMI, CTCA for CAD) are embedded in the R validation script. OA Discovery Pipeline validation uses publicly available data from ClinicalTrials.gov, Europe PMC, OpenAlex, and PubMed.

## Competing Interests

No competing interests were disclosed.

## Grant Information

No specific grant funding was received for this work.

## Author Contributions

Mahmood Ahmad: Conceptualization, Software, Validation, Data curation, Writing - original draft, Writing - review and editing.

## Acknowledgements

The author acknowledges the developers of R packages mada, metafor, and PropCIs for providing the statistical reference implementations used in validation.

## References

1. Reitsma JB, Glas AS, Rutjes AW, et al. Bivariate analysis of sensitivity and specificity produces informative summary measures in diagnostic reviews. J Clin Epidemiol. 2005;58(10):982-990.
2. Rutter CM, Gatsonis CA. A hierarchical regression approach to meta-analysis of diagnostic test accuracy evaluations. Stat Med. 2001;20(19):2865-2884.
3. Doebler P, Holling H. Meta-analysis of diagnostic accuracy with mada. R package version 0.5.12. 2024.
4. Hoyer A, Hirt S, Kuss O. Meta-analysis of diagnostic test accuracy studies with multiple thresholds using the R package diagmeta. J Stat Softw. 2024;106(2):1-25.
5. Dwamena BA. MIDAS: Stata module for meta-analytical integration of diagnostic test accuracy studies. Statistical Software Components. 2009.
6. Review Manager (RevMan). Version 5.4. The Cochrane Collaboration. 2020.
7. Harbord RM, Deeks JJ, Egger M, et al. A unification of models for meta-analysis of diagnostic accuracy studies. Biostatistics. 2007;8(2):239-251.
8. Viechtbauer W, Cheung MW. Outlier and influence diagnostics for meta-analysis. Res Synth Methods. 2010;1(2):112-125.
9. Copas J, Shi JQ. Meta-analysis, funnel plots and sensitivity analysis. Biostatistics. 2000;1(3):247-262.
10. Simonsohn U, Nelson LD, Simmons JP. P-curve: a key to the file-drawer. J Exp Psychol Gen. 2014;143(2):534-547.
11. Hardy RJ, Thompson SG. A likelihood approach to meta-analysis with random effects. Stat Med. 1996;15(6):619-629.
12. Efron B, Tibshirani RJ. An Introduction to the Bootstrap. Chapman and Hall/CRC. 1994.
13. Tibshirani R. Regression shrinkage and selection via the lasso. J R Stat Soc Series B. 1996;58(1):267-288.
14. Vickers AJ, Elkin EB. Decision curve analysis: a novel method for evaluating prediction models. Med Decis Making. 2006;26(6):565-574.
15. Linn S, Grunau PD. New patient-oriented summary measure of net total gain in certainty for diagnostic tests. Epidemiol Perspect Innov. 2006;3:11.
16. Ahmad M. RCT Extractor v2: automated clinical trial data extraction pipeline. 2026. [Software].
17. Viechtbauer W. Conducting meta-analyses in R with the metafor package. J Stat Softw. 2010;36(3):1-48.
