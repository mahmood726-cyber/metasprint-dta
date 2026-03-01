# MetaSprint DTA: Quality Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every aspect of metasprint-dta.html publication-quality for the highest-standard DTA meta-analyses, validated against R mada.

**Architecture:** All JS changes to `metasprint-dta.html` (~21.9K lines). New files: `validate_vs_mada.R` (R validation), `test_r_validation.py` (cross-validation test). R 4.5.2 + mada 0.5.12 at `C:\Program Files\R\R-4.5.2\bin\Rscript.exe`.

**Tech Stack:** Vanilla JS, inline SVG, Canvas (PNG), Selenium + Python testing, R mada cross-validation.

**Baseline:** 203/203 tests pass, div balance 723/723.

---

## Tier 1: Statistical Rigor

---

## Task 1: R Cross-Validation Suite

**The problem:** No R validation exists. The bivariate GLMM claims to match mada::reitsma() but this has never been tested programmatically.

**Files:**
- Create: `validate_vs_mada.R`
- Create: `test_r_validation.py`

**What to implement:**

`validate_vs_mada.R`:
```r
library(mada)
library(jsonlite)

# BNP dataset (Doust 2004, k=6) — matches loadDemoData() in app
bnp <- data.frame(
  TP = c(52, 44, 379, 89, 40, 163),
  FP = c(14, 20, 83, 17, 22, 44),
  FN = c(8, 6, 65, 14, 5, 21),
  TN = c(76, 151, 959, 337, 138, 416)
)

# hs-Troponin dataset (k=5)
trop <- data.frame(
  TP = c(45, 98, 72, 33, 156),
  FP = c(12, 25, 18, 8, 40),
  FN = c(5, 10, 8, 3, 15),
  TN = c(88, 167, 102, 56, 289)
)

# CTCA dataset (k=4, includes fn=0 edge case)
ctca <- data.frame(
  TP = c(30, 65, 22, 88),
  FP = c(8, 15, 5, 22),
  FN = c(2, 5, 0, 7),
  TN = c(60, 115, 73, 183)
)

validate_dataset <- function(data, name) {
  fit <- reitsma(data)
  s <- summary(fit)
  sens_est <- s$coefficients["tsens.", "Estimate"]
  spec_est <- s$coefficients["tfpr.", "Estimate"]
  # Convert from logit scale
  pooled_sens <- plogis(sens_est)
  pooled_spec <- 1 - plogis(spec_est)  # tfpr is logit(FPR), so Spec = 1-FPR
  # CIs from vcov
  se_sens <- s$coefficients["tsens.", "Std. Error"]
  se_spec <- s$coefficients["tfpr.", "Std. Error"]
  z <- qnorm(0.975)
  sens_ci <- plogis(c(sens_est - z*se_sens, sens_est + z*se_sens))
  spec_ci <- 1 - plogis(c(spec_est + z*se_spec, spec_est - z*se_spec))
  # DOR
  dor <- exp(sens_est + (-spec_est))  # logit(Sens) + logit(Spec) = logit(Sens) - logit(FPR)
  # tau2
  tau2 <- fit$Psi  # variance-covariance of random effects
  # AUC from sroc curve
  sroc_auc <- AUC(fit)
  list(
    dataset = name,
    k = nrow(data),
    pooled_sens = pooled_sens,
    pooled_spec = pooled_spec,
    sens_ci_lo = sens_ci[1], sens_ci_hi = sens_ci[2],
    spec_ci_lo = spec_ci[1], spec_ci_hi = spec_ci[2],
    dor = dor,
    auc = sroc_auc,
    mu1 = sens_est, mu2 = -spec_est,
    se_mu1 = se_sens, se_mu2 = se_spec,
    tau2_11 = tau2[1,1], tau2_22 = tau2[2,2]
  )
}

results <- list(
  bnp = validate_dataset(bnp, "BNP"),
  trop = validate_dataset(trop, "hs-Troponin"),
  ctca = validate_dataset(ctca, "CTCA")
)
cat(toJSON(results, auto_unbox=TRUE, pretty=TRUE))
```

`test_r_validation.py`:
```python
"""Cross-validate MetaSprint DTA against R mada::reitsma()"""
import subprocess, json, sys, os, time
from selenium import webdriver
from selenium.webdriver.common.by import By

RSCRIPT = r'C:\Program Files\R\R-4.5.2\bin\Rscript.exe'
HTML_PATH = os.path.join(os.path.dirname(__file__), 'metasprint-dta.html')

def get_r_reference():
    """Run R validation script, return parsed JSON."""
    r_script = os.path.join(os.path.dirname(__file__), 'validate_vs_mada.R')
    result = subprocess.run([RSCRIPT, r_script], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print("R stderr:", result.stderr, file=sys.stderr)
        raise RuntimeError(f"R script failed: {result.returncode}")
    # Parse JSON from stdout (skip library loading messages)
    lines = result.stdout.strip().split('\n')
    json_start = next(i for i, l in enumerate(lines) if l.strip().startswith('{'))
    return json.loads('\n'.join(lines[json_start:]))

def get_app_results(driver, dataset):
    """Load dataset in app and extract pooled results."""
    # Load demo data (BNP) or enter custom data
    if dataset == 'bnp':
        driver.execute_script("loadDemoData()")
    else:
        # Enter custom data via JS
        studies = DATASETS[dataset]
        for s in studies:
            driver.execute_script(f"addStudyRow({{authorYear:'{s[0]}',tp:{s[1]},fp:{s[2]},fn:{s[3]},tn:{s[4]}}})")
    time.sleep(0.5)
    # Run analysis
    driver.execute_script("switchPhase('analyze')")
    time.sleep(0.5)
    driver.execute_script("document.querySelector('#analyzeBtn')?.click() || runAnalysis()")
    time.sleep(2)
    # Extract results
    return driver.execute_script("return lastAnalysisResult")

# Tolerance
SENS_SPEC_TOL = 0.005  # probability scale
DOR_TOL_PCT = 0.05     # 5% relative
CI_TOL = 0.01          # probability scale

def compare(app_val, r_val, tol, label):
    diff = abs(app_val - r_val)
    status = "PASS" if diff <= tol else "FAIL"
    print(f"  {label}: app={app_val:.4f} R={r_val:.4f} diff={diff:.4f} [{status}]")
    return status == "PASS"
```

**Step 1:** Create `validate_vs_mada.R` with the 3 benchmark datasets
**Step 2:** Test R script runs: `& "C:\Program Files\R\R-4.5.2\bin\Rscript.exe" validate_vs_mada.R`
**Step 3:** Create `test_r_validation.py` with Selenium + R comparison
**Step 4:** Run cross-validation, record tolerances
**Step 5:** Commit: `feat: add R mada cross-validation suite (3 datasets)`

---

## Task 2: I-squared Confidence Intervals

**The problem:** I² is reported as a point estimate only. Reviewers expect confidence intervals.

**Files:**
- Modify: `metasprint-dta.html` — after `improvedBivariatePool()` (~line 7540)

**What to implement:**

Add `I2ConfidenceInterval(Q, k, confLevel)` function:
```javascript
function I2ConfidenceInterval(Q, k, confLevel) {
  // Higgins & Thompson 2002, Eq. 7-8 (test-based CI)
  if (k < 3) return { I2: 0, I2_lo: 0, I2_hi: 0 };
  const df = k - 1;
  const I2 = Math.max(0, (Q - df) / Q * 100);
  const alpha = 1 - (confLevel ?? 0.95);
  // Method: invert the Q distribution
  // Q ~ chi2(df) under null. Under alternative, Q/lambda ~ chi2_df where lambda = 1 + tau2*C
  // Simpler: use the large-sample approximation (Higgins 2002)
  const seLogQ = Math.sqrt(2 * df) / Q; // approximate
  const z = normalQuantile(1 - alpha / 2);
  // Lower bound: use chi2 quantile
  const Q_hi = chi2Quantile(1 - alpha / 2, df);
  const Q_lo = chi2Quantile(alpha / 2, df);
  const I2_lo = Math.max(0, (Q - Q_hi) / Q * 100);
  const I2_hi = Math.min(100, Q > Q_lo ? (Q - Q_lo) / Q * 100 : 0);
  return { I2, I2_lo, I2_hi };
}
```

Wire into `improvedBivariatePool()` return object — add `I2_sens_CI` and `I2_spec_CI`.

Update display in analysis summary (line ~8900) to show "I² = X% (Y% to Z%)".

**Step 1:** Add `I2ConfidenceInterval` function after line ~7540
**Step 2:** Call it in `improvedBivariatePool` for both Q_sens and Q_spec
**Step 3:** Update summary HTML to display I² with CI
**Step 4:** Run tests, verify div balance
**Step 5:** Commit: `feat: add I² confidence intervals (Higgins-Thompson)`

---

## Task 3: Prediction Intervals for Pooled Sens/Spec

**The problem:** CI shows uncertainty of the average. PI shows where a new study's result might fall. Cochrane requires both.

**Files:**
- Modify: `metasprint-dta.html` — in `improvedBivariatePool()` return and summary display

**What to implement:**

In `improvedBivariatePool()`, after computing `sensCI` and `specCI`, add:
```javascript
// Prediction interval: mu +/- t(k-2) * sqrt(tau2 + se2)
const piCrit = k >= 3 ? tQuantile(1 - alpha / 2, Math.max(1, k - 2)) : critValue;
const piSens_logit = [mu1 - piCrit * Math.sqrt(tau2_1 + seMu1 * seMu1), mu1 + piCrit * Math.sqrt(tau2_1 + seMu1 * seMu1)];
const piSpec_logit = [mu2 - piCrit * Math.sqrt(tau2_2 + seMu2 * seMu2), mu2 + piCrit * Math.sqrt(tau2_2 + seMu2 * seMu2)];
const sensPredInt = [invLogit(piSens_logit[0]), invLogit(piSens_logit[1])];
const specPredInt = [invLogit(piSpec_logit[0]), invLogit(piSpec_logit[1])];
```

Add `sensPredInt` and `specPredInt` to return object.

Update summary display to show PI below CI: "PI: X% to Y%".

Add dashed lines for PI in forest plots (both separate and coupled).

**Step 1:** Add PI calculation in `improvedBivariatePool`
**Step 2:** Add to return object
**Step 3:** Update summary HTML
**Step 4:** Add PI dashed lines to `renderDTAForestPlot`
**Step 5:** Run tests, verify div balance
**Step 6:** Commit: `feat: add prediction intervals for pooled sensitivity and specificity`

---

## Task 4: Sensitivity Analysis Gating (Exclude High-RoB)

**The problem:** No way to see how results change when excluding high-risk-of-bias studies.

**Files:**
- Modify: `metasprint-dta.html` — add button + comparison table near analysis results

**What to implement:**

Add a "Sensitivity: Exclude High-RoB" button in the analysis section. When clicked:
1. Get QUADAS-2 assessments via `getRoBAssessments()`
2. Filter studies where no domain is "high"
3. Re-run `computeDTAAnalysis()` on the filtered subset
4. Display comparison table:

```
| | Full (k=N) | Low/Unclear RoB (k=M) | Change |
|---|---|---|---|
| Pooled Sens | X% (CI) | Y% (CI) | +/-Z% |
| Pooled Spec | X% (CI) | Y% (CI) | +/-Z% |
| DOR | X (CI) | Y (CI) | +/-Z |
```

Add container `<div id="robSensitivityContainer">` after the subgroup container.

**Step 1:** Add HTML container and button
**Step 2:** Implement `runRoBSensitivityAnalysis()` function
**Step 3:** Add comparison table renderer
**Step 4:** Run tests, verify div balance
**Step 5:** Commit: `feat: add risk-of-bias sensitivity analysis (exclude high-RoB studies)`

---

## Task 5: Trim-and-Fill for Publication Bias

**The problem:** Deeks' test only detects asymmetry. Trim-and-fill also estimates adjusted effect.

**Files:**
- Modify: `metasprint-dta.html` — add after Deeks' test section

**What to implement:**

Add `trimAndFill(studies)` function implementing Duval-Tweedie L0 estimator:
```javascript
function trimAndFill(studies) {
  if (studies.length < 5) return null;
  // Work on logDOR scale
  const yi = studies.map(s => s.logDOR);
  const vi = studies.map(s => {
    const a = 1/(s.tp+0.5) + 1/(s.fp+0.5) + 1/(s.fn+0.5) + 1/(s.tn+0.5);
    return a;
  });
  const k = yi.length;
  // Step 1: Estimate center (DL pooled logDOR)
  const wi = vi.map(v => 1/v);
  const sumW = wi.reduce((a,b) => a+b, 0);
  let mu0 = wi.reduce((s,w,i) => s + w*yi[i], 0) / sumW;
  // Step 2: L0 estimator — rank-based
  // Count studies on the "less significant" side
  let k0 = 0;
  for (let iter = 0; iter < 20; iter++) {
    const devs = yi.map(y => y - mu0);
    const absDevs = devs.map(Math.abs);
    const ranks = absDevs.map((d, i) => ({ d, i, sign: devs[i] >= 0 ? 1 : -1 }))
      .sort((a, b) => a.d - b.d)
      .map((r, rank) => ({ ...r, rank: rank + 1 }));
    // T+ = sum of ranks on positive side
    const Tplus = ranks.filter(r => r.sign > 0).reduce((s, r) => s + r.rank, 0);
    const Tminus = ranks.filter(r => r.sign < 0).reduce((s, r) => s + r.rank, 0);
    // k0 = estimated number of missing studies (on the side with fewer)
    const T = Math.min(Tplus, Tminus);
    const missingSide = Tplus < Tminus ? 1 : -1; // impute on lighter side
    const newK0 = Math.max(0, Math.round((4 * T - k * (k + 1)) / (2 * k - 1)));
    if (newK0 === k0 && iter > 0) break;
    k0 = newK0;
    if (k0 === 0) break;
    // Step 3: Impute k0 studies by reflecting the most extreme from heavy side
    const sorted = devs.map((d, i) => ({ d, i, absD: Math.abs(d) }))
      .filter(r => Math.sign(r.d) !== missingSide || r.d === 0)
      .sort((a, b) => b.absD - a.absD);
    const imputed = sorted.slice(0, k0).map(r => ({
      logDOR: mu0 - devs[r.i], // reflect
      variance: vi[r.i]
    }));
    // Re-estimate mu0 with augmented data
    const allYi = [...yi, ...imputed.map(im => im.logDOR)];
    const allVi = [...vi, ...imputed.map(im => im.variance)];
    const allWi = allVi.map(v => 1/v);
    const allSumW = allWi.reduce((a,b) => a+b, 0);
    mu0 = allWi.reduce((s,w,i) => s + w*allYi[i], 0) / allSumW;
  }
  return {
    k0, // number of imputed studies
    adjustedLogDOR: mu0,
    adjustedDOR: Math.exp(mu0),
    originalDOR: Math.exp(wi.reduce((s,w,i) => s + w*yi[i], 0) / sumW)
  };
}
```

Display: "Trim-and-fill: K imputed studies. Adjusted DOR = X (original = Y)."

Add imputed points (hollow circles) to the Deeks' funnel plot.

**Step 1:** Add `trimAndFill` function near Deeks' test
**Step 2:** Wire into analysis results after Deeks' test
**Step 3:** Add display HTML
**Step 4:** Add imputed points to funnel SVG
**Step 5:** Run tests, verify div balance
**Step 6:** Commit: `feat: add Duval-Tweedie trim-and-fill for publication bias`

---

## Task 6: Summary of Findings (SoF) Table

**The problem:** GRADE-DTA requires a formal SoF table. Currently only a certainty badge exists.

**Files:**
- Modify: `metasprint-dta.html` — after GRADE computation section

**What to implement:**

Add `renderSoFTable(result, gradeResult, prevalence)` function that creates a structured table:

Columns: Outcome at prevalence X% | Effect per 1000 | 95% CI | Participants (studies) | Certainty | What happens

Rows:
- True positives: `round(prevalence * sens * 1000)`
- False negatives: `round(prevalence * (1-sens) * 1000)`
- True negatives: `round((1-prevalence) * spec * 1000)`
- False positives: `round((1-prevalence) * (1-spec) * 1000)`

Add "Export SoF CSV" button alongside.

Add prevalence input (default 20%, configurable).

**Step 1:** Add SoF table renderer function
**Step 2:** Add container and prevalence input in analysis results section
**Step 3:** Wire into analysis display
**Step 4:** Add CSV export for SoF data
**Step 5:** Run tests, verify div balance
**Step 6:** Commit: `feat: add GRADE-DTA Summary of Findings table with CSV export`

---

## Task 7: Comprehensive R Code Export

**The problem:** R code only generates basic reitsma() call. Missing forest, LOO, subgroup, Deeks' replication.

**Files:**
- Modify: `metasprint-dta.html` — R code generation section (~line 9966)

**What to implement:**

Extend the R code generation to produce a complete analysis script:
```r
# MetaSprint DTA — Complete R mada replication
library(mada)
# Data
TP <- c(...)
FP <- c(...)
FN <- c(...)
TN <- c(...)
labels <- c(...)
dat <- data.frame(TP=TP, FP=FP, FN=FN, TN=TN, row.names=labels)

# 1. Bivariate model
fit <- reitsma(dat)
summary(fit)

# 2. SROC plot with confidence and prediction regions
plot(fit, sroclwd=2, main="SROC Curve")
points(fpr(fit), sens(fit), pch=2)

# 3. Forest plots
forest(fit, main="Coupled Forest Plot")

# 4. Leave-one-out sensitivity analysis
loo_results <- data.frame(study=character(), sens=numeric(), spec=numeric(), stringsAsFactors=FALSE)
for(i in 1:nrow(dat)) {
  fit_loo <- reitsma(dat[-i, ])
  s <- summary(fit_loo)
  loo_results <- rbind(loo_results, data.frame(
    study=rownames(dat)[i],
    sens=plogis(s$coefficients["tsens.", "Estimate"]),
    spec=1-plogis(s$coefficients["tfpr.", "Estimate"])
  ))
}
print(loo_results)

# 5. Threshold effect test
cor.test(qlogis(dat$TP/(dat$TP+dat$FN)), qlogis(dat$FP/(dat$FP+dat$TN)), method="spearman")
```

Also add subgroup code if subgroups exist, and a "Download .R file" button.

**Step 1:** Expand R code template with LOO, forest, threshold test
**Step 2:** Add subgroup code generation (conditional)
**Step 3:** Add "Download .R file" button alongside clipboard copy
**Step 4:** Run tests, commit: `feat: expand R code export (LOO, forest, threshold, download)`

---

## Task 8: Profile Likelihood CIs (k < 10)

**The problem:** Wald CIs can be inaccurate when k is small or Sens/Spec near 0/1.

**Files:**
- Modify: `metasprint-dta.html` — after `improvedBivariatePool()` (~line 7555)

**What to implement:**

Add `profileLikelihoodCI(studies, paramIndex, confLevel)`:
```javascript
function profileLikelihoodCI(data, mu_hat, se_hat, paramIdx, confLevel) {
  // Compute profile likelihood CI by finding where -2*logLR = chi2(1, alpha)
  const alpha = 1 - (confLevel ?? 0.95);
  const chi2_crit = chi2Quantile(1 - alpha, 1); // 3.84 for 95%
  // Grid search + bisection
  const lo_start = mu_hat - 4 * se_hat;
  const hi_start = mu_hat + 4 * se_hat;
  // ... (bisection on log-likelihood ratio)
  // For bivariate DTA: the log-likelihood is sum of bivariate normal contributions
  // L(mu1, mu2 | data) = sum_i log(dnorm(y1i, mu1, sqrt(v1i + tau2_1))) + log(dnorm(y2i, mu2, sqrt(v2i + tau2_2)))
  // Profile: fix mu_paramIdx, maximize over the other
}
```

Apply only when k < 10. Add to return object as `sensCI_profile`, `specCI_profile`.

Display profile CIs in summary when available. Label as "Profile likelihood CI" vs "Wald CI".

**Step 1:** Implement profile likelihood computation
**Step 2:** Wire into bivariate pool for k < 10
**Step 3:** Update summary display
**Step 4:** Run tests, verify against R mada (which uses profile LR by default)
**Step 5:** Commit: `feat: add profile likelihood CIs for small-k analyses`

---

## Tier 2: Publication Workflow

---

## Task 9: PNG Export (300 DPI)

**The problem:** Journals require PNG/TIFF at 300 DPI. Only SVG export exists.

**Files:**
- Modify: `metasprint-dta.html` — export section (~line 1489)

**What to implement:**

Add `exportPlotPNG(containerId, filename, dpi)`:
```javascript
function exportPlotPNG(containerId, filename, dpi) {
  dpi = dpi ?? 300;
  const container = document.getElementById(containerId);
  if (!container) return;
  const svgEl = container.querySelector('svg');
  if (!svgEl) { showToast('No plot to export', 'warning'); return; }
  const serializer = new XMLSerializer();
  const svgStr = resolveCSSVarsInSVG(serializer.serializeToString(svgEl));
  const svgBlob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(svgBlob);
  const img = new Image();
  img.onload = function() {
    const scale = dpi / 96; // default screen DPI
    const canvas = document.createElement('canvas');
    canvas.width = img.width * scale;
    canvas.height = img.height * scale;
    const ctx = canvas.getContext('2d');
    ctx.scale(scale, scale);
    ctx.drawImage(img, 0, 0);
    canvas.toBlob(function(blob) {
      URL.revokeObjectURL(url);
      const pngUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = pngUrl; a.download = filename;
      document.body.appendChild(a); a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(pngUrl);
      showToast('PNG exported at ' + dpi + ' DPI', 'success');
    }, 'image/png');
  };
  img.src = url;
}
```

Add "Export PNG" buttons next to each existing SVG button.

**Step 1:** Add `exportPlotPNG` function near `exportPlotSVG`
**Step 2:** Add PNG export buttons for all 5 plots
**Step 3:** Test in browser (verify canvas renders correctly)
**Step 4:** Verify div balance
**Step 5:** Commit: `feat: add PNG export at 300 DPI for all plots`

---

## Task 10: Automated Table 1 (Study Characteristics)

**The problem:** Reviewers must manually create Table 1 in Word.

**Files:**
- Modify: `metasprint-dta.html` — export section

**What to implement:**

Add `exportCharacteristicsTable()`:
```javascript
function exportCharacteristicsTable() {
  if (!extractedStudies.length) { showToast('No studies', 'warning'); return; }
  const header = 'Author/Year,Index Test,Threshold,Population,N (Diseased),N (Healthy),Prevalence (%)';
  const rows = extractedStudies.filter(s => s.tp != null && s.tn != null).map(s => {
    const diseased = (s.tp ?? 0) + (s.fn ?? 0);
    const healthy = (s.tn ?? 0) + (s.fp ?? 0);
    const n = diseased + healthy;
    const prev = n > 0 ? ((diseased / n) * 100).toFixed(1) : '';
    return [
      csvSafeCell(s.authorYear || ''),
      csvSafeCell(s.indexTest || ''),
      csvSafeCell(s.threshold || ''),
      csvSafeCell(s.analysisPopulation || ''),
      diseased, healthy, prev
    ].join(',');
  });
  downloadFile(header + '\n' + rows.join('\n'), 'table1-characteristics.csv', 'text/csv');
  showToast('Table 1 exported', 'success');
}
```

Add button in export section.

**Step 1:** Add function
**Step 2:** Add button
**Step 3:** Verify CSV output
**Step 4:** Commit: `feat: add automated Table 1 (study characteristics) CSV export`

---

## Task 11: Automated Table 2 (2x2 + Accuracy per Study)

**The problem:** No structured per-study accuracy table export.

**Files:**
- Modify: `metasprint-dta.html` — export section

**What to implement:**

Add `exportAccuracyTable()`:
```javascript
function exportAccuracyTable() {
  if (!lastAnalysisResult?.studyData) { showToast('Run analysis first', 'warning'); return; }
  const confLevel = lastAnalysisResult.confLevel ?? 0.95;
  const alpha = 1 - confLevel;
  const confPct = Math.round(confLevel * 100);
  const header = 'Study,TP,FP,FN,TN,Sens,' + confPct + '% CI Lo,' + confPct + '% CI Hi,Spec,' + confPct + '% CI Lo,' + confPct + '% CI Hi,PLR,NLR,DOR';
  const rows = lastAnalysisResult.studyData.map(s => {
    const nSens = s.tp + s.fn, nSpec = s.tn + s.fp;
    const ciSens = wilsonCI(s.tp, nSens, alpha);
    const ciSpec = wilsonCI(s.tn, nSpec, alpha);
    const plr = s.spec > 0 ? (s.sens / (1 - s.spec)).toFixed(2) : 'Inf';
    const nlr = s.sens < 1 ? ((1 - s.sens) / s.spec).toFixed(3) : '0';
    const dor = (s.fp > 0 && s.fn > 0) ? ((s.tp * s.tn) / (s.fp * s.fn)).toFixed(2) : 'Inf';
    return [
      csvSafeCell(s.authorYear || ''),
      s.tp, s.fp, s.fn, s.tn,
      (s.sens * 100).toFixed(1), (ciSens[0] * 100).toFixed(1), (ciSens[1] * 100).toFixed(1),
      (s.spec * 100).toFixed(1), (ciSpec[0] * 100).toFixed(1), (ciSpec[1] * 100).toFixed(1),
      plr, nlr, dor
    ].join(',');
  });
  downloadFile(header + '\n' + rows.join('\n'), 'table2-accuracy.csv', 'text/csv');
  showToast('Table 2 exported', 'success');
}
```

**Step 1:** Add function
**Step 2:** Add button in export section
**Step 3:** Commit: `feat: add automated Table 2 (per-study accuracy) CSV export`

---

## Task 12: Standardized Pooled Results CSV

**The problem:** No structured export of pooled analysis results.

**Files:**
- Modify: `metasprint-dta.html` — export section

**What to implement:**

Add `exportPooledResultsCSV()` that exports:
```
Metric,Estimate,CI_Lo,CI_Hi,PI_Lo,PI_Hi
Pooled Sensitivity (%),X,Y,Z,A,B
Pooled Specificity (%),X,Y,Z,A,B
DOR,X,Y,Z,,
PLR,X,,,
NLR,X,,,
AUC,X,,,
I2 Sensitivity (%),X,Y,Z
I2 Specificity (%),X,Y,Z
tau2 Sensitivity,X,,,
tau2 Specificity,X,,,
k,N,,,
rho,X,,,
GRADE Certainty,LABEL,,,
```

**Step 1:** Add function
**Step 2:** Add button
**Step 3:** Commit: `feat: add standardized pooled results CSV export`

---

## Task 13: QUADAS-2 Summary Export

**The problem:** No structured export of risk-of-bias judgments.

**Files:**
- Modify: `metasprint-dta.html` — export section

**What to implement:**

Add `exportQUADAS2CSV()`:
```javascript
function exportQUADAS2CSV() {
  const assessments = getRoBAssessments();
  if (!assessments?.length) { showToast('No QUADAS-2 assessments', 'warning'); return; }
  const header = 'Study,D1_PatientSelection,D2_IndexTest,D3_ReferenceStandard,D4_FlowTiming,App_PatientSelection,App_IndexTest,App_ReferenceStandard,Overall';
  const rows = assessments.map(a => {
    const study = extractedStudies.find(s => s.id === a.studyId);
    return [
      csvSafeCell((study?.authorYear || a.studyId)),
      a.d1 || '', a.d2 || '', a.d3 || '', a.d4 || '',
      a.d1_app || '', a.d2_app || '', a.d3_app || '',
      a.overall || ''
    ].join(',');
  });
  downloadFile(header + '\n' + rows.join('\n'), 'quadas2-summary.csv', 'text/csv');
  showToast('QUADAS-2 exported', 'success');
}
```

Also add proportional bar chart (% Low/Unclear/High per domain) as SVG.

**Step 1:** Add CSV export function
**Step 2:** Add bar chart renderer
**Step 3:** Add export buttons
**Step 4:** Commit: `feat: add QUADAS-2 summary CSV export and proportional bar chart`

---

## Task 14: Blob URL Cleanup

**The problem:** Memory leak risk from unreleased Blob URLs.

**Files:**
- Modify: `metasprint-dta.html` — `downloadFile()` and any other Blob creators

**What to implement:**

The `downloadFile()` function (line 7019) already calls `URL.revokeObjectURL(url)`. Verify all other Blob URL creators also clean up. Search for `createObjectURL` and ensure each has a matching `revokeObjectURL`.

**Step 1:** Grep for all `createObjectURL` calls
**Step 2:** Verify each has matching `revokeObjectURL`
**Step 3:** Fix any that don't
**Step 4:** Commit: `fix: ensure Blob URL cleanup for all download operations`

---

## Task 15: GRADE Evidence Profile Export

**The problem:** GRADE certainty is computed but not exported as a formatted evidence profile.

**Files:**
- Modify: `metasprint-dta.html` — after GRADE section

**What to implement:**

Add `exportGRADEProfile()` that exports the full GRADE-DTA evidence profile as a self-contained HTML file and CSV:

HTML: interactive table with downgrade justifications, color-coded certainty.
CSV: columns for each domain rating and overall certainty.

**Step 1:** Add GRADE profile renderer
**Step 2:** Add HTML export (self-contained)
**Step 3:** Add CSV export
**Step 4:** Commit: `feat: add GRADE-DTA evidence profile HTML and CSV export`

---

## Tier 3: Feature Completeness

---

## Task 16: Comparative DTA (2+ Index Tests)

**The problem:** Cannot compare two index tests side-by-side.

**Files:**
- Modify: `metasprint-dta.html` — advanced DTA section

**What to implement:**

Add `computeComparativeDTA(studies, confLevel)`:
1. Group studies by `indexTest` field
2. Run `improvedBivariatePool()` on each test group
3. Compare pooled logDOR between tests using z-test: z = (logDOR1 - logDOR2) / sqrt(SE1² + SE2²)
4. Display side-by-side table with p-value for difference

Add UI: auto-detect when 2+ index tests exist, show "Compare Index Tests" button.

**Step 1:** Add `computeComparativeDTA` function
**Step 2:** Add comparison table renderer
**Step 3:** Add auto-detection and button
**Step 4:** Verify div balance
**Step 5:** Commit: `feat: add comparative DTA for 2+ index tests`

---

## Task 17: RevMan XML Import

**The problem:** Users with existing Cochrane DTA reviews in RevMan can't import data.

**Files:**
- Modify: `metasprint-dta.html` — import section near CSV import

**What to implement:**

Add `importRevManXML()`:
1. File input for `.rm5` files
2. Parse XML: find `<DICH_DATA>` elements, extract `EVENTS_1` (TP), `NOEVENTS_1` (FN), `EVENTS_2` (FP), `NOEVENTS_2` (TN)
3. Also parse study names from `<STUDY>` elements
4. Map to `addStudyRow()` calls
5. Show toast: "Imported N studies from RevMan file"

**Step 1:** Add file input button
**Step 2:** Add XML parser function
**Step 3:** Map to existing addStudyRow pathway
**Step 4:** Test with sample RevMan XML
**Step 5:** Commit: `feat: add RevMan 5 XML import for DTA reviews`

---

## Task 18: Interactive PRISMA-DTA Checklist

**The problem:** Users must compare against external 27-item PRISMA-DTA PDF.

**Files:**
- Modify: `metasprint-dta.html` — new panel in Write tab

**What to implement:**

Add expandable PRISMA-DTA checklist panel with 27 items. Each item has:
- Checkbox (manual toggle)
- Auto-fill indicator (green dot) for items the app can verify:
  - Title (item 1): check `protTitle` not empty
  - Protocol registered (item 5): check PROSPERO ID field
  - Search strategy (item 8): check search audit records
  - Flow diagram (item 13): check PRISMA SVG exists
  - Statistical methods (item 14): check analysis has been run
  - Risk of bias (item 19): check QUADAS-2 assessments exist

Export as CSV: Item, Description, Status (Auto/Manual/Not Done).

**Step 1:** Add checklist data array (27 items)
**Step 2:** Add panel renderer
**Step 3:** Add auto-fill logic
**Step 4:** Add CSV export
**Step 5:** Commit: `feat: add interactive PRISMA-DTA 27-item checklist`

---

## Task 19: Excel Paste Support

**The problem:** Users must create CSV files to import data. Copy-paste from Excel would be faster.

**Files:**
- Modify: `metasprint-dta.html` — extraction table

**What to implement:**

Add paste event listener to the extraction table:
```javascript
document.getElementById('phase-extract')?.addEventListener('paste', function(e) {
  const text = e.clipboardData?.getData('text/plain');
  if (!text || !text.includes('\t')) return; // Only handle tab-separated (Excel/Sheets)
  e.preventDefault();
  const rows = text.trim().split('\n').map(r => r.split('\t'));
  // Detect header row
  const headerRow = rows[0].map(h => h.trim().toLowerCase());
  const colMap = {};
  ['authorYear','study','tp','fp','fn','tn','indextest','threshold','subgroup'].forEach(field => {
    const idx = headerRow.findIndex(h => h === field || h === field.replace(/([A-Z])/g, ' $1').trim().toLowerCase());
    if (idx >= 0) colMap[field] = idx;
  });
  // Also try common aliases
  if (colMap.tp == null) colMap.tp = headerRow.findIndex(h => h === 'true positive' || h === 'true positives');
  // ... etc
  const dataRows = colMap.tp != null ? rows.slice(1) : rows; // skip header if detected
  let count = 0;
  for (const row of dataRows) {
    const tp = parseInt(row[colMap.tp ?? 2]);
    const fp = parseInt(row[colMap.fp ?? 3]);
    const fn = parseInt(row[colMap.fn ?? 4]);
    const tn = parseInt(row[colMap.tn ?? 5]);
    if (isNaN(tp) || isNaN(fp) || isNaN(fn) || isNaN(tn)) continue;
    addStudyRow({
      authorYear: row[colMap.authorYear ?? colMap.study ?? 0] || '',
      tp, fp, fn, tn,
      indexTest: row[colMap.indextest ?? ''] || '',
      threshold: row[colMap.threshold ?? ''] || '',
      subgroup: row[colMap.subgroup ?? ''] || ''
    });
    count++;
  }
  if (count > 0) showToast('Pasted ' + count + ' studies from clipboard', 'success');
});
```

**Step 1:** Add paste event listener
**Step 2:** Add header auto-detection
**Step 3:** Test with tab-separated paste
**Step 4:** Commit: `feat: add Excel/Sheets paste support for study data entry`

---

## Task 20: Threshold Effect Auto-Recommendation

**The problem:** When Spearman rho is significant, the app should suggest HSROC.

**Files:**
- Modify: `metasprint-dta.html` — after threshold effect test display

**What to implement:**

In the analysis results section, after displaying threshold effect results, check:
```javascript
if (result.thresholdEffect && result.thresholdEffect.pValue < 0.05 && result.method !== 'HSROC') {
  const banner = '<div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:var(--radius);padding:10px;margin-top:8px;font-size:0.82rem">' +
    '<strong>Threshold effect detected</strong> (Spearman rho = ' + result.thresholdEffect.rho.toFixed(2) +
    ', p = ' + result.thresholdEffect.pValue.toFixed(3) + '). ' +
    'Consider using the <strong>HSROC model</strong> which explicitly models threshold variation. ' +
    '<a href="https://training.cochrane.org/handbook/current/chapter-10" target="_blank" rel="noopener" style="color:var(--primary)">Cochrane Handbook Ch. 10</a>' +
    '<button onclick="this.parentElement.remove()" style="float:right;background:none;border:none;cursor:pointer;color:var(--text-muted)">&times;</button>' +
    '</div>';
  thresholdEl.insertAdjacentHTML('beforeend', banner);
}
```

**Step 1:** Add conditional banner after threshold test display
**Step 2:** Verify div balance
**Step 3:** Commit: `feat: add auto-recommendation for HSROC when threshold effect detected`

---

## Summary

| Tier | Task | Type | Est. Lines |
|------|------|------|-----------|
| 1 | 1. R cross-validation | Testing | ~150 (new files) |
| 1 | 2. I² confidence intervals | Statistics | ~30 |
| 1 | 3. Prediction intervals | Statistics | ~40 |
| 1 | 4. RoB sensitivity gating | Statistics | ~50 |
| 1 | 5. Trim-and-fill | Statistics | ~80 |
| 1 | 6. SoF table | Export | ~60 |
| 1 | 7. R code export (full) | Export | ~40 |
| 1 | 8. Profile likelihood CIs | Statistics | ~60 |
| 2 | 9. PNG export | Export | ~30 |
| 2 | 10. Table 1 (characteristics) | Export | ~20 |
| 2 | 11. Table 2 (accuracy) | Export | ~25 |
| 2 | 12. Pooled results CSV | Export | ~25 |
| 2 | 13. QUADAS-2 export | Export | ~40 |
| 2 | 14. Blob cleanup | Fix | ~5 |
| 2 | 15. GRADE profile export | Export | ~50 |
| 3 | 16. Comparative DTA | Feature | ~60 |
| 3 | 17. RevMan XML import | Feature | ~50 |
| 3 | 18. PRISMA-DTA checklist | Feature | ~80 |
| 3 | 19. Excel paste | Feature | ~40 |
| 3 | 20. Threshold auto-recommend | Feature | ~15 |
| **Total** | | | **~950** |
