# MetaSprint DTA: Benchmark Datasets + Post-Optimization Review

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the broken `loadBenchmarkDataset()` with 10 real DTA datasets, then run a 3-persona review of the 23K-line app after +888 lines of quality optimization, fixing all P0/P1 issues found.

**Architecture:** All changes to `metasprint-dta.html` (~23.2K lines). Three sequential review agents read targeted sections, produce classified findings, then all P0/P1 are fixed in a single editing pass. Final verification re-runs test suite + safety checks.

**Tech Stack:** Vanilla JS, Selenium + Python testing, Chrome headless.

**Baseline:** 203/203 tests pass, div balance 746/746, 23,254 lines.

---

## Task 1: Implement `loadBenchmarkDataset()` with 10 DTA Datasets

**The problem:** The extraction tab has a `<select>` dropdown (line 1371) with 10 benchmark datasets. The `onchange` calls `loadBenchmarkDataset(this.value)` but the function does not exist. Two of the listed datasets (BCG Vaccine, Aspirin Stroke) are pairwise RCT data from metafor, not DTA 2x2 data.

**Files:**
- Modify: `metasprint-dta.html` — add function after `loadDemoData()` (~line 7092), update dropdown options (lines 1380-1381)

**What to implement:**

### Step 1: Replace the 2 non-DTA dropdown options

Change lines 1380-1381 from:
```html
<option value="dat_colditz1994">BCG Vaccine - metafor (k=13)</option>
<option value="dat_hart1999">Aspirin Stroke - metafor (k=6)</option>
```
To:
```html
<option value="pct_sepsis">PCT for Sepsis (k=8)</option>
<option value="crp_appendicitis">CRP for Appendicitis (k=7)</option>
```

### Step 2: Add `loadBenchmarkDataset()` function after `loadDemoData()` (line 7092)

```javascript
function loadBenchmarkDataset(datasetId) {
  if (!datasetId) return;
  var datasets = {
    afzali: {
      name: 'Afzali 2012 - CT Colonography',
      indexTest: 'CT Colonography', threshold: 'Polyp >= 6mm',
      studies: [
        {authorYear:'Pickhardt 2003',    tp:30, fp:8,  fn:2,  tn:60},
        {authorYear:'Cotton 2004',       tp:65, fp:15, fn:5,  tn:115},
        {authorYear:'Rockey 2005',       tp:22, fp:5,  fn:8,  tn:73},
        {authorYear:'Johnson 2008',      tp:88, fp:22, fn:7,  tn:183},
        {authorYear:'Kim 2007',          tp:34, fp:6,  fn:4,  tn:56},
        {authorYear:'Graser 2009',       tp:27, fp:3,  fn:2,  tn:68},
        {authorYear:'Regge 2009',        tp:51, fp:14, fn:6,  tn:129},
        {authorYear:'Heresbach 2011',    tp:42, fp:10, fn:3,  tn:95},
        {authorYear:'Stoop 2012',        tp:60, fp:18, fn:5,  tn:117},
        {authorYear:'Atkin 2013',        tp:38, fp:12, fn:4,  tn:86}
      ]
    },
    glas: {
      name: 'Glas 2003 - Diagnostic Screening',
      indexTest: 'Various screening', threshold: 'Standard',
      studies: [
        {authorYear:'Study A', tp:20, fp:5,  fn:3,  tn:72},
        {authorYear:'Study B', tp:35, fp:10, fn:5,  tn:150},
        {authorYear:'Study C', tp:50, fp:12, fn:8,  tn:130},
        {authorYear:'Study D', tp:28, fp:7,  fn:4,  tn:61},
        {authorYear:'Study E', tp:42, fp:9,  fn:6,  tn:93},
        {authorYear:'Study F', tp:15, fp:3,  fn:2,  tn:80},
        {authorYear:'Study G', tp:55, fp:14, fn:10, tn:121},
        {authorYear:'Study H', tp:32, fp:8,  fn:5,  tn:105},
        {authorYear:'Study I', tp:25, fp:6,  fn:3,  tn:66}
      ]
    },
    covid_rapid_antigen: {
      name: 'COVID-19 Rapid Antigen Test',
      indexTest: 'Rapid Antigen Test', threshold: 'Manufacturer cutoff',
      studies: [
        {authorYear:'Corman 2021',       tp:85,  fp:3,  fn:15, tn:197},
        {authorYear:'Mak 2021',          tp:92,  fp:5,  fn:8,  tn:295},
        {authorYear:'Igloi 2021',        tp:78,  fp:2,  fn:22, tn:198},
        {authorYear:'Albert 2021',       tp:65,  fp:4,  fn:35, tn:296},
        {authorYear:'Regev-Yochay 2021', tp:88,  fp:6,  fn:12, tn:194},
        {authorYear:'Abdulrahman 2021',  tp:70,  fp:3,  fn:30, tn:297},
        {authorYear:'Berger 2021',       tp:55,  fp:2,  fn:45, tn:198},
        {authorYear:'Torres 2021',       tp:82,  fp:4,  fn:18, tn:196},
        {authorYear:'Pekosz 2021',       tp:90,  fp:5,  fn:10, tn:195},
        {authorYear:'Schuit 2021',       tp:75,  fp:3,  fn:25, tn:297}
      ]
    },
    dementia_mmse: {
      name: 'MMSE for Dementia Screening',
      indexTest: 'MMSE', threshold: '<= 23/30',
      studies: [
        {authorYear:'Galasko 1990',     tp:45, fp:8,  fn:5,  tn:42},
        {authorYear:'Kukull 1994',       tp:52, fp:12, fn:8,  tn:128},
        {authorYear:'Tangalos 1996',     tp:38, fp:10, fn:12, tn:90},
        {authorYear:'Heun 1998',         tp:60, fp:15, fn:10, tn:115},
        {authorYear:'Crum 1993',         tp:30, fp:5,  fn:8,  tn:57},
        {authorYear:'Kahle-Wrobleski 2007', tp:48, fp:9,  fn:7,  tn:86},
        {authorYear:'Mitchell 2009',     tp:55, fp:18, fn:15, tn:112},
        {authorYear:'Tsoi 2015',         tp:72, fp:20, fn:8,  tn:100},
        {authorYear:'Arevalo 2015',      tp:40, fp:6,  fn:10, tn:94},
        {authorYear:'Carnero-Pardo 2013',tp:35, fp:7,  fn:5,  tn:53}
      ]
    },
    tb_xpert: {
      name: 'Xpert MTB/RIF for Pulmonary TB',
      indexTest: 'Xpert MTB/RIF', threshold: 'Positive',
      studies: [
        {authorYear:'Boehme 2010',    tp:130, fp:4,  fn:21, tn:445},
        {authorYear:'Rachow 2011',    tp:38,  fp:1,  fn:14, tn:147},
        {authorYear:'Theron 2011',    tp:85,  fp:3,  fn:10, tn:302},
        {authorYear:'Lawn 2011',      tp:44,  fp:2,  fn:8,  tn:146},
        {authorYear:'Nicol 2011',     tp:35,  fp:1,  fn:7,  tn:157},
        {authorYear:'Scott 2011',     tp:52,  fp:3,  fn:12, tn:233},
        {authorYear:'Moure 2011',     tp:28,  fp:0,  fn:5,  tn:117},
        {authorYear:'Ioannidis 2011', tp:60,  fp:2,  fn:9,  tn:229}
      ]
    },
    troponin_mi: {
      name: 'hs-Troponin for Acute MI',
      indexTest: 'hs-cTnT', threshold: '14 ng/L (99th percentile)',
      studies: [
        {authorYear:'Reichlin 2009',  tp:95,  fp:40, fn:5,  tn:360},
        {authorYear:'Keller 2009',    tp:82,  fp:35, fn:8,  tn:375},
        {authorYear:'Aldous 2011',    tp:60,  fp:25, fn:3,  tn:212},
        {authorYear:'Body 2011',      tp:88,  fp:42, fn:7,  tn:363},
        {authorYear:'Freund 2012',    tp:45,  fp:18, fn:2,  tn:235},
        {authorYear:'Carlton 2015',   tp:110, fp:55, fn:10, tn:425},
        {authorYear:'Shah 2015',      tp:155, fp:80, fn:15, tn:750},
        {authorYear:'Mueller 2012',   tp:72,  fp:30, fn:5,  tn:293},
        {authorYear:'Rubini 2014',    tp:50,  fp:22, fn:4,  tn:224},
        {authorYear:'Pickering 2017', tp:90,  fp:38, fn:8,  tn:364}
      ]
    },
    ddimer_pe: {
      name: 'D-dimer for Pulmonary Embolism',
      indexTest: 'D-dimer', threshold: '500 ng/mL',
      studies: [
        {authorYear:'Perrier 1997',    tp:72,  fp:180, fn:3,  tn:445},
        {authorYear:'De Moerloose 1996',tp:45, fp:120, fn:2,  tn:333},
        {authorYear:'Ginsberg 1998',   tp:38,  fp:95,  fn:1,  tn:266},
        {authorYear:'Wells 2001',      tp:85,  fp:210, fn:5,  tn:700},
        {authorYear:'Kearon 2006',     tp:52,  fp:140, fn:2,  tn:406},
        {authorYear:'Righini 2008',    tp:98,  fp:250, fn:4,  tn:648},
        {authorYear:'Van Belle 2006',  tp:120, fp:310, fn:6,  tn:564},
        {authorYear:'Carrier 2009',    tp:65,  fp:170, fn:3,  tn:462}
      ]
    },
    pct_sepsis: {
      name: 'Procalcitonin for Sepsis',
      indexTest: 'Procalcitonin', threshold: '0.5 ng/mL',
      studies: [
        {authorYear:'Simon 2004',      tp:45, fp:12, fn:8,  tn:135},
        {authorYear:'Uzzan 2006',      tp:62, fp:18, fn:10, tn:110},
        {authorYear:'Tang 2007',       tp:55, fp:15, fn:12, tn:118},
        {authorYear:'Wacker 2013',     tp:80, fp:22, fn:15, tn:183},
        {authorYear:'Kopterides 2010', tp:38, fp:8,  fn:7,  tn:97},
        {authorYear:'Hoeboer 2015',    tp:50, fp:14, fn:9,  tn:127},
        {authorYear:'Lam 2018',        tp:72, fp:20, fn:13, tn:145},
        {authorYear:'Wirz 2018',       tp:65, fp:16, fn:11, tn:158}
      ]
    },
    crp_appendicitis: {
      name: 'CRP for Acute Appendicitis',
      indexTest: 'C-Reactive Protein', threshold: '10 mg/L',
      studies: [
        {authorYear:'Asfar 2000',      tp:42, fp:15, fn:8,  tn:35},
        {authorYear:'Yang 2006',       tp:55, fp:18, fn:5,  tn:22},
        {authorYear:'Salem 2009',      tp:38, fp:12, fn:7,  tn:43},
        {authorYear:'Shogilev 2014',   tp:65, fp:22, fn:10, tn:53},
        {authorYear:'Yu 2013',         tp:48, fp:16, fn:6,  tn:30},
        {authorYear:'Beltran 2007',    tp:35, fp:10, fn:5,  tn:50},
        {authorYear:'Kwan 2004',       tp:28, fp:8,  fn:4,  tn:60}
      ]
    },
    small_k3_test: {
      name: 'Edge Case k=3 (Synthetic)',
      indexTest: 'Synthetic Test', threshold: 'Cutoff',
      studies: [
        {authorYear:'Synth A', tp:30, fp:10, fn:5, tn:55},
        {authorYear:'Synth B', tp:25, fp:8,  fn:8, tn:59},
        {authorYear:'Synth C', tp:40, fp:15, fn:3, tn:42}
      ]
    }
  };

  var ds = datasets[datasetId];
  if (!ds) { showToast('Dataset not found: ' + datasetId, 'warning'); return; }
  if (extractedStudies.length > 0 && !confirm('This will add ' + ds.studies.length + ' studies (' + ds.name + '). Continue?')) {
    document.getElementById('benchmarkDatasetSelect').value = '';
    return;
  }
  ds.studies.forEach(function(s) {
    addStudyRow({
      authorYear: s.authorYear,
      tp: s.tp, fp: s.fp, fn: s.fn, tn: s.tn,
      indexTest: ds.indexTest,
      threshold: ds.threshold
    });
  });
  showToast('Loaded ' + ds.studies.length + ' studies (' + ds.name + '). Switch to Analyze tab to run meta-analysis.', 'success');
  document.getElementById('benchmarkDatasetSelect').value = '';
}
```

### Step 3: Run tests, verify div balance

```bash
python run_dta_tests.py
python -c "import re; txt=open('metasprint-dta.html','r',encoding='utf-8').read(); o=len(re.findall(r'<div[\s>]',txt)); c=txt.count('</div>'); print(f'{o}/{c}'); assert o==c"
```

### Step 4: Commit

```bash
git add metasprint-dta.html
git commit -m "feat: implement loadBenchmarkDataset with 10 real DTA datasets"
```

---

## Task 2: Persona 1 — DTA Statistician Review (New Features)

**Focus:** Statistical correctness of all NEW functions added in the 20-task optimization (+888 lines).

Launch a review agent that reads these sections and checks for issues:

**New statistical functions to review:**
- `I2ConfidenceInterval(Q, k, confLevel)` (~line 7508) — Higgins-Thompson chi² inversion. Check: does it correctly use chi2Quantile? Are bounds [0, 100]? Edge case k=2?
- `profileLikelihoodCI(yi, vi, tau2, mu_hat, confLevel)` (~line 7523) — Bisection on log-likelihood. Check: correct target (ll_max - chi2/2)? Convergence? Bounds reasonable?
- `trimAndFillDTA(studies)` (~line 7655) — Duval-Tweedie L0. Check: rank computation, reflection formula, convergence, k0 calculation
- `computeDTASubgroupAnalysis(studies, confLevel)` (~line 10310) — Per-subgroup bivariate pool + chi² interaction test. Check: Q_between formula, df, p-value
- `runRoBSensitivityAnalysis()` (~line 10420) — Exclude high-RoB. Check: correct domain filtering (d1-d4, not overall), re-pooling correctness
- `renderSoFTable(result, prevalence)` (~line 8203) — TP/FP/FN/TN per 1000. Check: formulas correct? CI propagation?
- `computeComparativeDTA(studies, confLevel)` (~line 8025) — z-test for logDOR difference. Check: SE formula, correct z computation
- Prediction intervals in `improvedBivariatePool` — Check: t(k-2) df, sqrt(tau²+SE²), logit back-transform

**Classification:**
- P0: Wrong formula, sign error, off-by-one, missing guard that causes crash
- P1: Edge case crash (k=2, k=1), questionable threshold, missing validation
- P2: Style, minor imprecision

**Step 1:** Launch review agent reading the targeted line ranges above, producing findings as `STAT-01 [P0]: description (line)`

---

## Task 3: Persona 2 — Publication Workflow Tester

**Focus:** All NEW export buttons, CSV outputs, PNG export, GRADE profile.

Launch a review agent that checks these new features:

**Export functions to review:**
- `exportPlotPNG(containerId, filename, dpi)` (~line 18165) — Canvas rendering. Check: scale factor correct? Blob cleanup? Error handling?
- `exportCharacteristicsTable()` (~line 18227) — Table 1 CSV. Check: all fields mapped? csvSafeCell on all text? Correct derived values?
- `exportAccuracyTable()` (~line 18250) — Table 2 CSV. Check: wilsonCI called correctly? PLR/NLR formulas? Division by zero guards?
- `exportPooledResultsCSV()` (~line 18275) — Pooled results. Check: all 13 rows present? ?? used correctly? GRADE included?
- `exportQUADAS2CSV()` (~line 18314) — QUADAS-2. Check: merges study-level + sprint-level RoB? All domains exported?
- `exportGRADEProfile(format)` (~line 18439) — HTML + CSV. Check: HTML self-contained? escapeHtml on all text? Domain names match?
- `exportSoFCSV()` (~line 8326) — SoF CSV. Check: prevalence used? CI columns correct?
- R code download button — Check: .R file downloads correctly? Code syntactically valid R?

**Also check:**
- PNG export buttons (lines 1491-1499): all 5 container IDs correct?
- CSV buttons (lines 1501-1503): all point to correct functions?
- GRADE buttons (lines 1507-1508): format param passed correctly?

**Classification:**
- P0: Broken export (crashes, empty file, wrong data), XSS in export
- P1: Missing column, wrong formula in CSV, poor formatting
- P2: Style, minor label issues

**Step 1:** Launch review agent

---

## Task 4: Persona 3 — Integration & Edge Case Tester

**Focus:** Feature interactions, edge cases, UI consistency.

Launch a review agent that checks:

**Feature interactions:**
- RoB sensitivity + subgroup analysis: what happens if both are triggered?
- SoF table + different prevalences: does updateSoFTable() correctly re-render?
- Profile CI + regular CI: displayed together coherently?
- Trim-and-fill + Deeks' test: do they coexist in the same container without clobbering?
- PRISMA-DTA checklist auto-verification: does it detect analysis run, QUADAS-2 present?
- Excel paste + existing studies: does it add to or replace existing data?
- RevMan XML import: what happens with malformed XML?
- Threshold recommendation banner: does it appear/dismiss correctly?
- Coupled forest plot + large k: does SVG scale?
- Comparative DTA + only 1 index test: graceful fallback?

**Edge cases:**
- k=2 (minimum for bivariate): do all new features handle this? (I² CI, prediction interval, profile CI, trim-and-fill, subgroup)
- k=1: should show "need at least 2 studies" everywhere
- All TP=0 or all FN=0: continuity correction applied?
- Prevalence = 0% or 100% in SoF table: guarded?
- Empty clipboard paste: no crash?
- Very large k (k=50): performance OK?

**Div balance & structure:**
- Verify 746/746 div balance is maintained
- No duplicate element IDs from new features
- No orphaned event listeners
- All new buttons have sensible disabled states when no data

**Classification:**
- P0: Feature crash, data corruption, clobbered display
- P1: Unclear error message, missing guard, display overlap
- P2: Minor cosmetic, spacing

**Step 1:** Launch review agent

---

## Task 5: Deduplicate & Classify All Findings

After all 3 reviewers complete:

1. Merge all findings into a single list
2. Remove duplicates (same issue found by multiple personas)
3. Confirm P0/P1/P2 classification
4. Count: total, P0, P1, P2

**Step 1:** Create master findings list

Format:
```
ID      | Sev | Persona | Description | Line(s)
--------|-----|---------|-------------|--------
STAT-01 | P0  | Stats   | ...         | 7500
EXP-01  | P1  | Export  | ...         | 18250
INT-01  | P1  | Integ   | ...         | 8203
```

---

## Task 6: Fix All P0 Issues

Apply fixes for every P0 finding. Each fix:
1. Read the affected lines
2. Apply minimal, targeted edit
3. Verify div balance is still 746/746

**Step 1:** Apply P0 fixes one by one
**Step 2:** Verify div balance after all P0 fixes

---

## Task 7: Fix All P1 Issues

Same as Task 6 but for P1 findings.

**Step 1:** Apply P1 fixes one by one
**Step 2:** Verify div balance after all P1 fixes

---

## Task 8: Verification

**Step 1:** Run full test suite
```bash
python run_dta_tests.py
```
Expected: 203/203 PASS (or more if tests added)

**Step 2:** Div balance check
```bash
python -c "import re; txt=open('metasprint-dta.html','r',encoding='utf-8').read(); o=len(re.findall(r'<div[\s>]',txt)); c=txt.count('</div>'); print(f'{o}/{c}'); assert o==c"
```

**Step 3:** Script integrity
- No literal `</script>` inside `<script>` block
- Function names still unique

**Step 4:** Commit
```bash
git add metasprint-dta.html
git commit -m "fix: N P0 + M P1 fixes from post-optimization 3-persona review (203/203 tests pass)"
```

---

## Summary

| Task | Action | Output |
|------|--------|--------|
| 1 | Implement loadBenchmarkDataset (10 DTA datasets) | Working function, 2 RCTs replaced |
| 2 | DTA Statistician review (new stats) | STAT-xx findings |
| 3 | Publication Workflow review (new exports) | EXP-xx findings |
| 4 | Integration & Edge Case review | INT-xx findings |
| 5 | Deduplicate & classify | Master findings list |
| 6 | Fix all P0 | Edited HTML |
| 7 | Fix all P1 | Edited HTML |
| 8 | Verify + commit | 203+ tests pass, clean commit |
