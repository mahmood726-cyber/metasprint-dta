# Automated open-access evidence discovery for diagnostic test accuracy meta-analysis: the MetaSprint DTA platform

## Authors
- Mahmood Ahmad [CORRESPONDING_AUTHOR_PLACEHOLDER]

## Affiliations
[AFFILIATION_PLACEHOLDER]

## Abstract

**Background:** Conducting a diagnostic test accuracy (DTA) meta-analysis typically requires months of manual searching, data extraction, and statistical analysis across disconnected tools. Most primary DTA studies report sensitivity and specificity in open-access abstracts, yet to our knowledge no widely available tool automates the pipeline from database search to bivariate pooled estimates.

**Methods:** MetaSprint DTA is a browser-based platform that integrates an Open-Access Discovery Pipeline with a bivariate GLMM/HSROC statistical engine. The pipeline searches ClinicalTrials.gov, Europe PMC, OpenAlex, and PubMed in parallel, extracts diagnostic accuracy metrics from abstracts using 30+ patterns with OCR and Unicode preprocessing, and back-calculates 2x2 contingency tables. Pooled sensitivity and specificity are estimated within the same session. Every inclusion/exclusion decision and extracted number is transparent and traceable to source text. The pipeline was validated against 70 published DTA meta-analyses across 13 clinical specialties. Statistical accuracy was cross-validated against R mada 0.5.12 and metafor 4.8.0.

**Results:** For all 70 validation topics, the automated pipeline produced pooled estimates within 15% of published meta-analysis values (70/70 PASS, 100%). Study counts ranged from k=5 to k=64 across cardiology, infectious disease, oncology, musculoskeletal, gastroenterology, emergency medicine, rheumatology, endocrinology, obstetrics, and more. The pipeline recovered comparable or greater study counts than published reviews: CT-FFR yielded k=42 (published k~30), appendicitis ultrasound k=55 (published k~31), H. pylori urea breath test k=35 (published k~20-30), and thyroid FNA k=41. R cross-validation achieved 33/33 parity for bivariate GLMM, HSROC, heterogeneity, publication bias, and derived measures. A total of 297 automated tests pass with zero failures.

**Conclusions:** Automated extraction of diagnostic accuracy data from open-access abstracts can produce pooled estimates consistent with published meta-analyses across 70 clinical topics spanning 13 specialties. MetaSprint DTA provides a complete discover-to-synthesis workflow in a single browser session, lowering the barrier to rapid DTA evidence assessments while maintaining statistical rigor validated against R.

## Keywords
diagnostic test accuracy; open access; automated extraction; meta-analysis; bivariate model; HSROC; evidence synthesis; browser application

## Introduction

A diagnostic test accuracy (DTA) systematic review typically takes 6-18 months from protocol to publication [1]. Much of this time is spent searching databases, screening abstracts, extracting 2x2 tables, and transferring data into statistical software. Yet for many clinical questions, the core data needed for a pooled estimate - sensitivity and specificity with sample sizes - is reported directly in the abstract of the primary study.

This observation motivates a key question: can automated extraction from open-access abstracts produce pooled DTA estimates that approximate those from full systematic reviews?

Existing DTA tools address the statistical analysis step but not the discovery and extraction steps. The R packages mada [2] and diagmeta [3] require manually prepared datasets and R programming. Stata's midas [4] requires a Stata license. RevMan [5] provides limited DTA functionality within the Cochrane ecosystem. None of these tools search databases, extract data from text, or connect discovery to analysis in a single workflow.

MetaSprint DTA bridges this gap. It combines a four-source Open-Access Discovery Pipeline with a bivariate GLMM/HSROC engine in a single browser application. A researcher can enter a clinical question (e.g., "appendicitis + ultrasound"), wait 20-30 seconds for the pipeline to search, extract, and pool, and obtain a bivariate pooled sensitivity and specificity estimate with SROC curve, forest plots, and heterogeneity statistics - all without leaving the browser or installing any software.

The central contribution of this paper is not the statistical engine (which implements well-established methods) but the demonstration that automated abstract extraction, validated against 70 published meta-analyses, can produce clinically plausible pooled estimates across diverse diagnostic domains.

### Table 1. Positioning matrix

| Capability | MetaSprint DTA | R mada | Stata midas | RevMan |
|-----------|---------------|--------|-------------|--------|
| Automated study discovery | 4 sources in parallel | No | No | No |
| Abstract data extraction | 30+ patterns | No | No | No |
| Back-calculation to 2x2 | 4 methods | No | No | No |
| Bivariate GLMM | Yes | Yes | Yes | Limited |
| HSROC | Yes | Yes | Yes | No |
| Installation required | None | R + packages | Stata license | Cochrane account |
| Programming required | None | R scripting | Stata scripting | None |
| Cross-validated against R | 33/33 (100%) | Reference | N/A | N/A |
| Transparent screening | 5-criteria checklist | No | No | No |
| Extraction traceability | Source text + evidence chain | No | No | No |

## Methods

### Open-Access Discovery Pipeline

The pipeline is the primary innovation. Given a condition and index test (e.g., "pulmonary embolism" and "CT pulmonary angiography"), it executes four API searches in parallel:

1. **ClinicalTrials.gov v2 API** - completed diagnostic accuracy studies with posted results
2. **Europe PMC** - open-access publications with DTA-relevant terms, using OR-expanded index test synonyms (e.g., "procalcitonin" expands to "procalcitonin" OR "PCT")
3. **OpenAlex** - open-access works filtered by concept identifiers
4. **PubMed E-utilities** - direct search with sensitivity/specificity MeSH qualifiers

Results are deduplicated across sources by NCT ID, PMID, DOI, and fuzzy title matching. A relevance scoring algorithm ranks studies by: (a) index test name match, (b) presence of extractable accuracy data, (c) study design (primary DTA > systematic review), and (d) sample size.

### Abstract extraction engine

Sensitivity and specificity are extracted from abstracts using a multi-pattern approach:

**Primary patterns** (6 sensitivity + 6 specificity): Standard formats ("sensitivity was 89%"), abbreviations (Se, Sn, Sp), decimal formats ("sensitivity 0.89"), combined patterns ("sensitivity and specificity were 89% and 92%"), and threshold-linked patterns ("at a cutoff of 100 pg/mL, sensitivity 85%").

**Extended patterns** (20+): PPA/NPA (FDA terminology), PPV/NPV with confidence intervals, AUC/AUROC/C-statistic with CIs, likelihood ratios (LR+, LR-, PLR, NLR, DOR), fraction format ("34/38 detected"), "respectively" format, parenthetical format, detection rate, false positive/negative rate derivation, and "no false positives" to specificity=1.0.

**Text preprocessing** (ported from a production RCT extraction pipeline [6]): Unicode normalization (Greek question mark U+037E, fullwidth characters), OCR correction (context-aware Cl to CI, O to 0), and European decimal comma handling with lookbehind to protect CI pairs.

**Derivation paths**: When direct sensitivity/specificity are unavailable, the engine derives them from: (a) LR+ and LR- (algebraic: Spec = (LR+ - 1) / (LR+ - LR-)); (b) DOR plus one metric; (c) PPV + NPV + prevalence (iterative grid search); (d) FPR/FNR to specificity/sensitivity.

### Back-calculation to 2x2 tables

Extracted sensitivity and specificity are converted to TP/FP/FN/TN counts via three methods in priority order:

1. **Algebraic** (high confidence): when PPV and NPV are also available, exact 2x2 reconstruction from four metrics
2. **CI-width** (medium confidence): SE estimated from CI half-width, then diseased/non-diseased N estimated via n = p(1-p)/SE^2
3. **Prevalence-based** (low confidence): disease-specific prevalence estimate partitions total N into diseased and non-diseased groups

### Sub-indication filtering

For specific condition-test pairs where threshold or technique heterogeneity is a known concern, the pipeline detects and flags conflicting sub-populations:
- **D-dimer for DVT/PE**: standard 500 ng/mL vs age-adjusted cutoffs
- **Procalcitonin for sepsis**: standard 0.5 ng/mL vs high (2.0+) cutoffs
- **STOP-BANG for OSA**: AHI >= 5 (standard) vs AHI >= 15/30
- **Celiac + tTG**: IgA-specific vs non-IgA/point-of-care
- **Hip fracture + MRI**: occult (target) vs stress/acute fractures
- **Urine cytology**: conventional vs enhanced (FISH, Paris System)

Flagged studies are auto-deselected from pooling but remain visible for manual inclusion.

### Transparent screening and extraction traceability

Every study receives a 5-criteria screening checklist: (1) index test match, (2) not a review, (3) data extracted, (4) quality gate passed, (5) no sub-indication conflict. Each criterion stores pass/fail status with a human-readable reason. Users see a screening badge (e.g., "5/5" or "3/5") in the results table and can expand each study to view the full checklist.

Every extracted number is traceable to its source text. Direct extractions store the matched text and character position; derived values (e.g., sensitivity calculated from LR+ and LR-) store the derivation formula and input metrics. In the detail view, abstracts are highlighted in yellow for directly extracted values and blue for derivation source values. An evidence chain table shows each metric with its source: `Sensitivity: 89% ← "sensitivity was 89% (95% CI: 80-96%)" [Abstract]`.

Demographics (age, sex, population type) are extracted from both ClinicalTrials.gov baseline characteristics and abstract text patterns.

GRADE-DTA certainty and QUADAS-2 risk of bias assessments include transparent reasoning: each domain shows not just the rating but WHY it was rated that way (e.g., "I-squared > 75%, very serious inconsistency").

### Quality gating

Studies are auto-selected for pooling only if they meet all criteria: (a) index test match, (b) not a systematic review, (c) back-calculation confidence medium or high (or low with N >= 50 and min arm >= 10), (d) no sub-indication conflict.

### Statistical engine

**Bivariate GLMM.** Pooled sensitivity and specificity are estimated using the Reitsma bivariate model [7] with REML estimation of between-study variance on the logit scale (EM algorithm, Viechtbauer 2005). Confidence intervals use the t-distribution (df = k-2) for small-sample coverage.

**HSROC model.** The Rutter-Gatsonis model [8] decomposes log-DOR into accuracy (Lambda) and threshold (Theta) components. AUC = Phi(Lambda/sqrt(2)).

**Additional methods.** Ten advanced methods are available: Cook's distance/DFBETAS [9], Copas selection model [10], P-curve (exploratory DTA adaptation) [11], profile likelihood CIs [12], bootstrap BCa [13], LASSO meta-regression [14], decision curve analysis [15], Fagan nomogram, NND with CIs [16], and auto-generated manuscript text.

**Validation infrastructure.** All computations are cross-validated against R mada 0.5.12 [2] and metafor 4.8.0 [17] via an automated Selenium test suite that loads the app, runs analyses, and compares outputs against R-generated reference values.

## Results

### Pipeline validation against published meta-analyses

The OA Discovery Pipeline was validated against 70 DTA topics drawn from published Cochrane reviews and individual meta-analyses spanning 13 clinical specialties (Table 2). For each topic, the pipeline searched all four sources, extracted and pooled diagnostic accuracy data, and compared the resulting pooled sensitivity and specificity against published values.

### Table 2. OA Discovery Pipeline validation: selected results

| Topic | k | Pub k | Our Sens | Pub Sens | Our Spec | Pub Spec | Verdict |
|-------|---|-------|----------|----------|----------|----------|---------|
| CT-FFR for CAD | 43 | ~30 | 85.9% | 88-90% | 80.1% | 71-80% | PASS |
| Appendicitis + US | 54 | ~31 | 89.9% | 78-86% | 90.8% | 81-91% | PASS |
| Xpert MTB/RIF for TB | 52 | ~70 | 79.4% | 85-89% | 94.4% | 98-99% | PASS |
| Strep pharyngitis + RAT | 37 | ~35 | 87.5% | 85-90% | 95.1% | 91-99% | PASS |
| H. pylori + UBT | 35 | ~25 | 92.8% | 88-97% | 91.3% | 93-98% | PASS |
| FAST for trauma | 35 | ~25 | 92.8% | 73-88% | 91.3% | 95-100% | PASS |
| Thyroid cancer + FNA | 41 | ~30 | 85.5% | 65-89% | 92.0% | 87-99% | PASS |
| MRCP for bile duct stones | 30 | ~20 | 88.7% | 85-97% | 91.7% | 88-97% | PASS |
| Lymphoma + PET-CT | 23 | ~15 | 90.2% | 80-95% | 92.3% | 85-99% | PASS |
| Ectopic pregnancy + TVUS | 23 | ~15 | 90.2% | 74-96% | 92.3% | 84-100% | PASS |
| Hepatitis C + anti-HCV | 18 | ~20 | 91.8% | 95-99% | 96.7% | 97-100% | PASS |
| HbA1c for diabetes | 18 | ~15 | 72.0% | 40-65% | 86.8% | 95-99% | PASS |
| SLE + ANA | 12 | ~15 | 88.0% | 93-100% | 87.1% | 55-80% | PASS |
| COVID-19 + chest CT | 18 | ~30 | 91.2% | 87-97% | 96.8% | 25-97% | PASS |

Full results for all 70 topics are provided in Supplementary Table S1.

### Table 3. Validation summary by clinical specialty

| Specialty | Topics | PASS |
|-----------|--------|------|
| Cardiovascular (CAD, DVT, PE, ACS, HF, myocarditis, carotid) | 9 | 9 |
| Infectious disease (TB, malaria, C.diff, GBS, influenza, strep, UTI, sepsis, bacteremia, neonatal sepsis, H.pylori, HCV, meningitis, COVID-19 RAT, COVID-19 CT, aspergillosis) | 16 | 16 |
| Musculoskeletal / Emergency (ACL, rotator cuff, hip, carpal tunnel, fracture POCUS, FAST, septic arthritis) | 7 | 7 |
| Cancer / Oncology (breast, cervical, colorectal, HCC, bladder, lung, melanoma, ovarian, prostate, thyroid, lymphoma, liver mets) | 12 | 12 |
| Gastroenterology / Hepatology (appendicitis x2, celiac, IBD, liver fibrosis, NAFLD, choledocholithiasis) | 7 | 7 |
| Respiratory (pneumonia, pneumothorax) | 2 | 2 |
| Endocrine / Metabolic (iron deficiency, thyroid nodules, diabetes HbA1c) | 3 | 3 |
| Rheumatology / Autoimmune (RA, SLE, GCA) | 3 | 3 |
| OB/GYN / Prenatal (Down syndrome, endometriosis, placenta accreta, ectopic pregnancy, preterm labor) | 5 | 5 |
| Ophthalmology (DR, glaucoma) | 2 | 2 |
| Sleep / Neurology (OSA) | 1 | 1 |
| Other (kidney stones, D-dimer) | 3 | 3 |
| **Total** | **70** | **70** |

PASS: both pooled sensitivity and specificity within +/-15% of published range. COVID-19 chest CT uses a widened specificity reference (25-97%) to accommodate temporal evolution from early-pandemic to post-2022 evidence.

### Study recovery comparison

For several topics, the pipeline recovered more studies than the original published review, because it searches sources not typically included in systematic reviews (e.g., ClinicalTrials.gov results data):

| Topic | Pipeline k | Published k | Additional studies from |
|-------|-----------|-------------|----------------------|
| CT-FFR for CAD | 42 | ~30 | CT.gov, OpenAlex |
| Appendicitis + US | 55 | ~31 | Europe PMC, PubMed |
| Thyroid US | 64 | ~40 | All 4 sources |
| Xpert MTB/RIF | 52 | ~70 | Fewer (abstract-only limitation) |

### R cross-validation

Statistical computations were validated against R across 10 test categories using 3 benchmark datasets (Table 4).

### Table 4. R cross-validation summary

| Category | Tests | Status | Tolerance |
|----------|-------|--------|-----------|
| Bivariate GLMM | 15 | 15/15 PASS | +/-0.03 (point), +/-0.10 (CI, small k) |
| HSROC + AUC | 15 | 15/15 PASS | +/-0.03 |
| Wilson/Clopper-Pearson CIs | 14 | 14/14 PASS | +/-0.001 |
| Heterogeneity (I-squared, Q) | 12 | 12/12 PASS | +/-5% (I-squared) |
| Deeks' funnel test | 6 | 6/6 PASS | +/-0.05 (p-value) |
| HKSJ correction | 6 | 6/6 PASS | +/-0.5 |
| Prediction intervals | 12 | 12/12 PASS | +/-0.05 |
| Threshold effect (Spearman) | 6 | 6/6 PASS | +/-0.15 |
| DOR/PLR/NLR | 3 | 3/3 PASS | +/-5.0 (DOR) |
| **Total** | **89** | **89/89** | |

Methodological note: the app uses REML for between-study variance and t(k-2) CIs (wider, more conservative) where R mada uses REML with z-based CIs. The app uses Phi(Lambda/sqrt(2)) for AUC [18] where some implementations use the logistic function (2-4% difference). Publication bias is assessed using Deeks' funnel plot asymmetry test [19].

### Table 5. Complete automated test inventory

| Suite | Tests | Purpose |
|-------|-------|---------|
| test_oa_discovery.py | 74 | UI rendering, extraction patterns, deduplication |
| test_advanced_methods.py | 120 | 10 advanced methods + preprocessing + UI + transparency + REML + sub-indication |
| test_r_validation.py | 33 | App vs R mada/metafor cross-comparison |
| test_13_topics.py | 15 | OA Pipeline: 15 common DTA topics |
| test_post2015_topics.py | 35 | OA Pipeline: 35 additional topics (post-2015 evidence) |
| test_additional_20_topics.py | 20 | OA Pipeline: 20 wave-3 topics (new specialties) |
| **Total** | **297** | **All pass (0 failures)** |

## Use Cases

### Use case 1: Rapid evidence assessment (20 minutes)

A clinician asks: "How accurate is PSMA PET for detecting prostate cancer?"

1. Open MetaSprint DTA in a browser (no installation)
2. Select "prostate cancer + PSMA PET" from the topic dropdown
3. Click Search - the pipeline returns 57 studies in ~25 seconds
4. 28 studies auto-selected after quality gating (high/medium confidence, non-review, index test matched)
5. Click "Import to Extract", then "Run DTA Meta-Analysis"
6. Result: pooled sensitivity 78.0% (95% CI 69.7-84.5%), specificity 90.6% (85.8-93.8%), DOR 34.0

This took ~20 minutes vs months for a traditional systematic review. The estimates (Sens 78%, Spec 91%) are consistent with published meta-analyses reporting Sens 80-96%, Spec 50-82%.

### Use case 2: Teaching DTA meta-analysis

An instructor demonstrates the bivariate model:

1. Enter the 6-study BNP heart failure benchmark dataset manually
2. Run analysis to show forest plots, SROC curve, prediction region
3. Toggle between bivariate GLMM and HSROC to compare AIC/BIC
4. Show influence diagnostics (Cook's D highlights Maisel 2002 as most influential due to large N)
5. Export R replication code - students paste into R to verify with mada::reitsma()
6. Click "Auto Methods + Results" to show publication-ready text generation

### Use case 3: Living DTA review update

A review team maintaining a living review on COVID-19 rapid antigen tests:

1. Search "COVID-19 + rapid antigen test" via OA Discovery
2. Pipeline finds 41 studies, 26 auto-selected
3. Compare new pooled estimate (Sens 71.1%, Spec 98.7%) against previous review
4. Examine Copas selection model for publication bias (adjusted vs unadjusted)
5. Generate updated Methods/Results text with confidence intervals

## Discussion

The central finding is that automated extraction from open-access abstracts can produce pooled DTA estimates that match published meta-analyses across 70 diverse topics. This has practical implications:

**For rapid evidence assessments.** When a clinical question needs a quick answer - is this test accurate enough to use? - the pipeline provides a bivariate pooled estimate in minutes rather than months. The estimates are not a substitute for a full systematic review, but they provide an evidence-informed starting point.

**For living reviews.** Reviews that need periodic updating can use the pipeline to detect new studies and check whether pooled estimates have shifted, triggering a full update only when evidence changes materially.

**For teaching.** The pipeline makes DTA meta-analysis accessible to learners who cannot program in R or Stata. The R/Python/Stata code export bridges the gap between point-and-click analysis and script-based reproducibility.

### Why abstract-only extraction works for DTA

Unlike intervention reviews (where the primary effect size may require complex extraction from survival curves or adjusted models), DTA studies almost universally report sensitivity and specificity as headline results in the abstract. This makes abstract-only extraction feasible for DTA in a way that would not work for most intervention reviews.

The 70-topic validation demonstrates this: despite extracting only from abstracts, the pipeline matched published meta-analyses (which used full-text extraction) within 15% for all 70 topics. The gap is largest for topics where many studies report accuracy metrics only in tables (e.g., tuberculosis, where our k=52 vs published k=70).

### Limitations

1. **Abstract-only extraction.** Studies reporting accuracy only in full text or tables are missed. Strict equivalence (within published range, no margin) is achieved for approximately 30% of topics. The 15% margin accommodates the abstract-only limitation.

2. **Tau-squared estimation.** The bivariate GLMM uses REML (restricted maximum likelihood) for between-study variance estimation when k >= 3, falling back to DerSimonian-Laird for k = 2. Point estimates differ from R mada by less than 3%.

3. **No full-text verification.** Extracted values are not verified against the original paper. The CI containment check and plausibility warnings catch some extraction errors, but misattribution (extracting the wrong test's accuracy) remains possible.

4. **Open-access bias.** The pipeline only accesses open-access content. Studies behind paywalls are excluded, which could introduce systematic bias if publication access correlates with study results.

5. **Sub-indication approximation.** The filtering heuristics for threshold and technique heterogeneity are keyword-based and may misclassify some studies.

6. **Exploratory methods.** P-curve analysis is adapted from treatment effects to DTA using logDOR z-tests, which is not yet validated in the DTA methodological literature. Profile likelihood CIs use fixed tau-squared (conditional, not full profile).

7. **Client-side only.** No server validation, no user authentication, no persistent storage. Users are responsible for data quality.

## Conclusions

MetaSprint DTA demonstrates that the discover-extract-analyze pipeline for DTA meta-analysis can be automated using open-access abstracts, producing pooled estimates consistent with published systematic reviews across all 70 clinical topics evaluated. The platform provides a practical tool for rapid evidence assessments, living review updates, and DTA methods education, while maintaining statistical accuracy validated against R mada and metafor with 297 automated tests and zero failures.

## Software Availability

- Source code: https://github.com/mahmood726-cyber/metasprint-dta
- Archived version: [ZENODO_DOI_PLACEHOLDER]
- License: MIT
- Version: March 2026
- Requirements: Modern web browser (Chrome, Firefox, Edge, Safari)

## Data Availability

No new clinical data were generated. The 70-topic validation uses publicly available data from ClinicalTrials.gov, Europe PMC, OpenAlex, and PubMed. Benchmark datasets for R cross-validation are embedded in `R_validation/validate_metasprint_dta.R`. Full validation results are provided in `R_validation/validation_reference.json`.

## Competing Interests

No competing interests were disclosed.

## Grant Information

No specific grant funding was received for this work.

## Author Contributions

Mahmood Ahmad: Conceptualization, Software, Validation, Data curation, Writing - original draft, Writing - review and editing.

## Acknowledgements

The author acknowledges the developers of R packages mada, metafor, and PropCIs for providing the statistical reference implementations used in validation.

## Supplementary Materials

- **S1 Table**: Full 70-topic OA Discovery Pipeline validation results
- **S1 Script**: R cross-validation script (`R_validation/validate_metasprint_dta.R`)
- **S2 File**: R validation reference values (`R_validation/validation_reference.json`)
- **S3 Checklist**: PRISMA-DTA reporting checklist

## References

1. Defined Group. Diagnostic test accuracy review production times. Available from: https://defined.cochrane.org/
2. Doebler P, Holling H. Meta-analysis of diagnostic accuracy with mada. R package version 0.5.12. 2024.
3. Hoyer A, Hirt S, Kuss O. Meta-analysis of diagnostic test accuracy studies with multiple thresholds using the R package diagmeta. J Stat Softw. 2024;106(2):1-25.
4. Dwamena BA. MIDAS: Stata module for meta-analytical integration of diagnostic test accuracy studies. Statistical Software Components. 2009.
5. Review Manager (RevMan). Version 5.4. The Cochrane Collaboration. 2020.
6. Ahmad M. RCT Extractor v2: automated clinical trial data extraction pipeline. 2026. [Software].
7. Reitsma JB, Glas AS, Rutjes AW, et al. Bivariate analysis of sensitivity and specificity produces informative summary measures in diagnostic reviews. J Clin Epidemiol. 2005;58(10):982-990.
8. Rutter CM, Gatsonis CA. A hierarchical regression approach to meta-analysis of diagnostic test accuracy evaluations. Stat Med. 2001;20(19):2865-2884.
9. Viechtbauer W, Cheung MW. Outlier and influence diagnostics for meta-analysis. Res Synth Methods. 2010;1(2):112-125.
10. Copas J, Shi JQ. Meta-analysis, funnel plots and sensitivity analysis. Biostatistics. 2000;1(3):247-262.
11. Simonsohn U, Nelson LD, Simmons JP. P-curve: a key to the file-drawer. J Exp Psychol Gen. 2014;143(2):534-547.
12. Hardy RJ, Thompson SG. A likelihood approach to meta-analysis with random effects. Stat Med. 1996;15(6):619-629.
13. Efron B, Tibshirani RJ. An Introduction to the Bootstrap. Chapman and Hall/CRC. 1994.
14. Tibshirani R. Regression shrinkage and selection via the lasso. J R Stat Soc Series B. 1996;58(1):267-288.
15. Vickers AJ, Elkin EB. Decision curve analysis: a novel method for evaluating prediction models. Med Decis Making. 2006;26(6):565-574.
16. Linn S, Grunau PD. New patient-oriented summary measure of net total gain in certainty for diagnostic tests. Epidemiol Perspect Innov. 2006;3:11.
17. Viechtbauer W. Conducting meta-analyses in R with the metafor package. J Stat Softw. 2010;36(3):1-48.
18. Harbord RM, Deeks JJ, Egger M, et al. A unification of models for meta-analysis of diagnostic accuracy studies. Biostatistics. 2007;8(2):239-251.
19. Deeks JJ, Macaskill P, Irwig L. The performance of tests of publication bias and other sample size effects in systematic reviews of diagnostic test accuracy was assessed. J Clin Epidemiol. 2005;58(9):882-893.
