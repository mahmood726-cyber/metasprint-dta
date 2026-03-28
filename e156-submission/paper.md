Mahmood Ahmad
Tahir Heart Institute
mahmood.ahmad2@nhs.net

MetaSprint DTA: Automated Open-Access Discovery for Diagnostic Test Accuracy Meta-Analysis

Can automated extraction from open-access abstracts produce pooled diagnostic accuracy estimates consistent with published meta-analyses across diverse specialties? MetaSprint DTA integrates a four-source discovery pipeline searching ClinicalTrials.gov, Europe PMC, OpenAlex, and PubMed with a bivariate GLMM and HSROC engine in a single browser application requiring no installation. The pipeline extracts sensitivity, specificity, and sample sizes using over 30 regex patterns with Unicode preprocessing, back-calculates two-by-two tables, and pools estimates within one session. Across 70 published DTA meta-analyses spanning 13 specialties, all pooled estimates fell within 15 percent of published values with study counts frequently exceeding published reviews, and R cross-validation achieved 33 of 33 parity against mada and metafor. Advanced diagnostics include Cook distance, DFBETAS, Copas selection model, profile-likelihood confidence intervals, and bootstrap BCa intervals. The platform bridges the months-long gap between clinical question and pooled diagnostic accuracy estimate. However, a limitation is that abstract-only extraction cannot capture studies reporting accuracy metrics solely in full-text tables.

Outside Notes

Type: methods
Primary estimand: Pooled sensitivity and specificity
App: MetaSprint DTA v1.0
Data: 70 published DTA meta-analyses across 13 specialties
Code: https://github.com/mahmood726-cyber/metasprint-dta
Version: 1.0
Validation: DRAFT

References

1. Reitsma JB, Glas AS, Rutjes AW, et al. Bivariate analysis of sensitivity and specificity produces informative summary measures in diagnostic reviews. J Clin Epidemiol. 2005;58(10):982-990.
2. Macaskill P, Gatsonis C, Deeks JJ, Harbord RM, Takwoingi Y. Cochrane Handbook for Systematic Reviews of Diagnostic Test Accuracy. Cochrane; 2023.
3. Borenstein M, Hedges LV, Higgins JPT, Rothstein HR. Introduction to Meta-Analysis. 2nd ed. Wiley; 2021.

AI Disclosure

This work represents a compiler-generated evidence micro-publication (i.e., a structured, pipeline-based synthesis output). AI is used as a constrained synthesis engine operating on structured inputs and predefined rules, rather than as an autonomous author. Deterministic components of the pipeline, together with versioned, reproducible evidence capsules (TruthCert), are designed to support transparent and auditable outputs. All results and text were reviewed and verified by the author, who takes full responsibility for the content. The workflow operationalises key transparency and reporting principles consistent with CONSORT-AI/SPIRIT-AI, including explicit input specification, predefined schemas, logged human-AI interaction, and reproducible outputs.
