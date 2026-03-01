# MetaSprint DTA: Quality Optimization Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize every aspect of metasprint-dta.html for publication-quality DTA meta-analyses, closing gaps vs R mada/RevMan/Meta-DiSc. Priority: statistical rigor first, then publication workflow, then feature completeness.

**Architecture:** All changes to `metasprint-dta.html` (~21.9K lines). New files: R validation script, reference JSON. No external dependencies beyond R (already installed: R 4.5.2, mada 0.5.12).

**Tech Stack:** Vanilla JS, inline SVG, Canvas (PNG export), Selenium + Python testing, R mada cross-validation.

**Baseline:** 203/203 tests pass, div balance 723/723, 7 user improvements already shipped.

---

## Audit Summary (3-agent review)

| Domain | Score | Key Gaps |
|--------|-------|----------|
| Statistical methods | 91% | No R cross-validation, no profile likelihood CIs, no trim-and-fill, no I² CIs |
| Visualizations | 95% | No PNG export, no resolution options |
| Export/reporting | 80% | No Table 1/2 auto-generation, no GRADE profile export, no .R download |
| Quality assessment | 85% | No sensitivity gating (exclude high-RoB), no QUADAS-2 CSV export |
| Search/screen | 75% | No Excel paste, no full-text PDF, no multi-user (out of scope) |
| Reproducibility | 50% | TruthCert bridge inactive, no checksummed bundles |

---

## Tier 1: Statistical Rigor (Tasks 1-8)

### Task 1: R Validation Suite

Create `validate_vs_mada.R` that runs `mada::reitsma()` on 3 benchmark datasets and outputs JSON. Create `test_r_validation.py` that compares R output vs app output.

**R path:** `C:\Program Files\R\R-4.5.2\bin\Rscript.exe`
**Package:** mada 0.5.12 (confirmed installed)

**Datasets:** Afzali 2012 (k=10), Glas 2003 (k=9), COVID Rapid Antigen (k=10)

**Tolerance:** Pooled Sens/Spec ±0.005 (probability scale), DOR ±5%, CIs ±0.01

### Task 2: Profile Likelihood CIs

Add `profileLikelihoodCI(studies, param, confLevel)` that maximizes the bivariate log-likelihood while fixing one parameter. Returns tighter CIs than Wald, especially for k < 10 or Sens/Spec near boundaries.

Use when k < 10; fall back to Wald for k >= 10 (negligible difference).

### Task 3: Sensitivity Analysis Gating

Add "Exclude high-risk studies" button that re-runs `improvedBivariatePool()` on the low/unclear-RoB subset. Display comparison table: Full pool vs Restricted pool with change indicators.

### Task 4: Summary of Findings (SoF) Table

Auto-generate GRADE-DTA evidence profile with per-outcome certainty ratings. Render as interactive HTML table. Export as CSV. Columns: Outcome (TP/FP/FN/TN per 1000), Effect (Sens/Spec), Certainty, Downgrade reasons.

### Task 5: Prediction Intervals for Pooled Estimates

Add PI = mu ± t(k-2) * sqrt(tau² + SE²) for pooled Sens and Spec. Display in forest plots (dashed line) and summary stat cards.

### Task 6: I² Confidence Intervals

Add Higgins-Thompson CI for I² via Q-distribution: I²_lo = max(0, (Q - df - z*sqrt(2*df)) / Q), I²_hi = min(100, (Q - df + z*sqrt(2*df)) / Q). Display as "I² = X% (Y% to Z%)".

### Task 7: Trim-and-Fill for Publication Bias

Implement Duval-Tweedie L0 estimator on logDOR. Show number of imputed studies, adjusted pooled DOR, and funnel plot with imputed points. Supplement to (not replacement for) Deeks' test.

### Task 8: Comprehensive R Code Export

Extend R script to include full analysis replication:
- `forest(fit)`, `plot(fit)`, `summary(fit)`
- Leave-one-out: `for(i in 1:k) reitsma(data[-i,])`
- Subgroup code if subgroups present
- Deeks' test equivalent
- Download as `.R` file (not just clipboard)

---

## Tier 2: Publication Workflow (Tasks 9-15)

### Task 9: PNG Export (300 DPI)

Add Canvas-based SVG→PNG conversion. For each SVG plot:
1. Create offscreen Canvas at 3x SVG dimensions (300 DPI)
2. Draw SVG as image onto Canvas
3. Export as PNG via `canvas.toBlob('image/png')`
4. Add "Export PNG" buttons alongside existing SVG buttons

### Task 10: Automated Table 1 (Study Characteristics)

Generate structured table from extraction data: Author/Year, Population, Index Test, Threshold, N(diseased), N(healthy), Prevalence, Country (if entered). Export as CSV.

### Task 11: Automated Table 2 (2x2 + Accuracy)

Generate formatted table: Study, TP, FP, FN, TN, Sens (Wilson CI), Spec (Wilson CI), PLR, NLR, DOR. Export as CSV.

### Task 12: GRADE Evidence Profile Export

Render GRADE table with expandable domain justifications. Export as standalone HTML (self-contained, printable) and CSV.

### Task 13: Standardized Results CSV

Export pooled results: Pooled Sens (CI), Pooled Spec (CI), DOR (CI), PLR (CI), NLR (CI), AUC, I²_sens (CI), I²_spec (CI), tau²_sens, tau²_spec, k, rho, GRADE certainty.

### Task 14: Blob URL Cleanup

Audit all `URL.createObjectURL()` calls. Add `URL.revokeObjectURL()` in `downloadFile()` after a 60-second timeout (allows browser to complete download).

### Task 15: QUADAS-2 Summary Export

Export risk-of-bias judgments as CSV (Study, D1_RoB, D2_RoB, D3_RoB, D4_RoB, D1_App, D2_App, D3_App, Overall). Add proportional bar chart (% Low/Unclear/High per domain) as exportable SVG.

---

## Tier 3: Feature Completeness (Tasks 16-20)

### Task 16: Comparative DTA (2+ Index Tests)

For reviews comparing index tests: run bivariate separately per test, display side-by-side table (Sens, Spec, DOR with CIs). Add z-test for difference between pooled logDOR values. Not full network DTA, but covers the common use case.

### Task 17: RevMan XML Import

Parse RevMan 5 `.rm5` files (XML with `<DICH_DATA>` elements). Extract: study ID, TP/FP/FN/TN, QUADAS-2 judgments. Map to existing extraction table. Validate parsed counts.

### Task 18: Interactive PRISMA-DTA Checklist

Embed 27-item PRISMA-DTA checklist as toggleable panel. Auto-fill items the app can verify (protocol registered, search databases listed, flow diagram present, etc.). Export as CSV.

### Task 19: Excel Paste Support

Add `paste` event listener to extraction table. Parse tab-separated values from clipboard. Auto-detect columns by header matching (Study/TP/FP/FN/TN). Create study rows from pasted data.

### Task 20: Threshold Effect Auto-Recommendation

When Spearman rho p < 0.05, show dismissable banner: "Significant threshold effect detected (rho = X, p = Y). Consider using HSROC model for this analysis." Link to relevant Cochrane guidance.

---

## Summary

| Tier | Tasks | Est. Lines | Focus |
|------|-------|-----------|-------|
| 1 | 1-8 | ~400 | Statistical rigor |
| 2 | 9-15 | ~300 | Publication workflow |
| 3 | 16-20 | ~250 | Feature completeness |
| **Total** | **20** | **~950** | |

## Findings NOT addressed (intentional)

- **Full Bayesian bivariate (MCMC)**: Requires JAGS/Stan port to browser. Out of scope.
- **Multi-user screening**: Requires server-side architecture. Out of scope for single-file app.
- **Full-text PDF viewer**: Requires PDF.js integration (~500KB). Out of scope.
- **Network DTA (full indirect comparison)**: Requires multivariate random-effects framework. The Task 16 comparative DTA covers the common 2-test case instead.
- **IPD meta-analysis**: Requires individual patient data format. Different workflow entirely.
- **Cost-effectiveness analysis**: Requires health economics inputs (ICER, QALY). Specialized domain.
