# Insights DTA Adaptation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adapt all 15 Insights sub-tabs from pairwise meta-analysis logic to DTA-native (sensitivity, specificity, DOR, PLR/NLR, threshold effect) so every tab produces meaningful output for diagnostic accuracy reviews.

**Architecture:** Each tab already has init/render functions in `metasprint-dta.html` (20,400 lines). We replace pairwise-specific logic with DTA equivalents inside existing functions. No new containers needed — all target elements exist. A shared helper `_getDTAInsightsData()` extracts the common DTA fields (pooledSens, pooledSpec, DOR, PLR, NLR, I2, rho, studyData) from `lastAnalysisResult` once, used by all tabs.

**Tech Stack:** Vanilla JS, inline SVG/Canvas, Selenium + Python testing.

---

## Task 1: Shared DTA Insights Helper + Mizan (Sens vs Spec Trade-off)

The Mizan tab currently shows "not applicable for DTA". Replace with a threshold optimization visualization: as threshold increases, sensitivity decreases and specificity increases. Show the trade-off visually.

**Files:**
- Modify: `metasprint-dta.html` — replace `initMizan()` body (~line 18136)

**What to implement:**

1. Add helper `_getDTAInsightsData()` that returns `{sens, spec, sensCI, specCI, plr, nlr, dor, dorCI, I2_sens, I2_spec, tau2_sens, tau2_spec, rho, k, studies, deeksP}` from `lastAnalysisResult`. Return null if no DTA result.

2. Replace the Mizan DTA branch. Instead of "not applicable", render:
   - A **Sens-Spec trade-off scale** on the canvas: left pan = Sensitivity (green), right pan = Specificity (blue)
   - Pan heights proportional to pooled values (higher = better)
   - Center fulcrum with "Threshold" label
   - Below canvas: **Youden Index** = Sens + Spec - 1 (optimal threshold summary)
   - **Clinical interpretation**: If Sens > Spec → "screening test (rules out disease)", if Spec > Sens → "confirmatory test (rules in disease)", if balanced → "general-purpose test"
   - Show PLR/NLR as secondary indicators: PLR > 10 = strong rule-in, NLR < 0.1 = strong rule-out

**Step 1: Implement**

Replace the DTA branch in `initMizan()` (the section that checks for DTA mode and shows placeholder). The new code should:

```javascript
// Inside initMizan(), replace the DTA placeholder branch:
const dtaData = _getDTAInsightsData();
if (!dtaData) { /* show no-data message */ return; }

const canvas = document.getElementById('mizanCanvas');
const ctx = canvas.getContext('2d');
const W = canvas.width, H = canvas.height;
ctx.clearRect(0, 0, W, H);

// Draw balance scale
const midX = W / 2, topY = 60;
// Fulcrum triangle
ctx.beginPath();
ctx.moveTo(midX - 20, H - 40);
ctx.lineTo(midX + 20, H - 40);
ctx.lineTo(midX, H - 70);
ctx.closePath();
ctx.fillStyle = '#6b7280';
ctx.fill();

// Beam (tilted by sens-spec difference)
const tilt = (dtaData.sens - dtaData.spec) * 0.3; // radians
ctx.save();
ctx.translate(midX, H - 70);
ctx.rotate(-tilt);
ctx.beginPath();
ctx.moveTo(-180, 0);
ctx.lineTo(180, 0);
ctx.strokeStyle = '#374151';
ctx.lineWidth = 3;
ctx.stroke();

// Left pan (Sensitivity) - green
const sensHeight = dtaData.sens * 120;
ctx.fillStyle = 'rgba(34, 197, 94, 0.3)';
ctx.strokeStyle = '#22c55e';
ctx.lineWidth = 2;
ctx.beginPath();
ctx.arc(-150, 10, 50, 0, Math.PI);
ctx.fill();
ctx.stroke();
ctx.fillStyle = '#166534';
ctx.font = 'bold 16px system-ui';
ctx.textAlign = 'center';
ctx.fillText((dtaData.sens * 100).toFixed(1) + '%', -150, 40);
ctx.font = '12px system-ui';
ctx.fillText('Sensitivity', -150, 58);

// Right pan (Specificity) - blue
ctx.fillStyle = 'rgba(59, 130, 246, 0.3)';
ctx.strokeStyle = '#3b82f6';
ctx.beginPath();
ctx.arc(150, 10, 50, 0, Math.PI);
ctx.fill();
ctx.stroke();
ctx.fillStyle = '#1e40af';
ctx.font = 'bold 16px system-ui';
ctx.fillText((dtaData.spec * 100).toFixed(1) + '%', 150, 40);
ctx.font = '12px system-ui';
ctx.fillText('Specificity', 150, 58);

ctx.restore();

// Fulcrum label
ctx.fillStyle = 'var(--text, #111)';
ctx.font = '11px system-ui';
ctx.textAlign = 'center';
ctx.fillText('Threshold Trade-off', midX, H - 20);

// Summary div
const summaryEl = document.getElementById('mizanSummary');
if (summaryEl) {
  const youden = dtaData.sens + dtaData.spec - 1;
  const role = dtaData.sens > dtaData.spec + 0.05
    ? 'Screening test (high sensitivity rules OUT disease)'
    : dtaData.spec > dtaData.sens + 0.05
      ? 'Confirmatory test (high specificity rules IN disease)'
      : 'Balanced diagnostic test';
  const plrStr = dtaData.plr >= 10 ? 'Strong rule-in (PLR >= 10)' :
                 dtaData.plr >= 5  ? 'Moderate rule-in (PLR 5-10)' : 'Weak rule-in (PLR < 5)';
  const nlrStr = dtaData.nlr <= 0.1 ? 'Strong rule-out (NLR <= 0.1)' :
                 dtaData.nlr <= 0.2 ? 'Moderate rule-out (NLR 0.1-0.2)' : 'Weak rule-out (NLR > 0.2)';
  summaryEl.innerHTML =
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px">' +
    '<div style="padding:10px;border:1px solid var(--border);border-radius:8px">' +
      '<div style="font-weight:600;font-size:0.9rem">Youden Index (J)</div>' +
      '<div style="font-size:1.4rem;font-weight:700;color:' + (youden > 0.5 ? 'var(--success)' : 'var(--warning)') + '">' + youden.toFixed(3) + '</div>' +
      '<div style="font-size:0.78rem;color:var(--text-muted)">Range: 0 (useless) to 1 (perfect)</div>' +
    '</div>' +
    '<div style="padding:10px;border:1px solid var(--border);border-radius:8px">' +
      '<div style="font-weight:600;font-size:0.9rem">Clinical Role</div>' +
      '<div style="font-size:0.85rem;margin-top:4px">' + role + '</div>' +
      '<div style="font-size:0.78rem;color:var(--text-muted);margin-top:4px">' + plrStr + ' | ' + nlrStr + '</div>' +
    '</div></div>';
}
```

**Step 2: Run tests, commit**

```bash
python run_dta_tests.py  # 181/181
git commit -m "feat(insights): adapt Mizan to DTA threshold trade-off visualization"
```

---

## Task 2: Shura Multiverse (DTA-native)

Currently runs pairwise multiverse (DL/REML × Wald/HKSJ × exclusions). Replace with DTA multiverse: Model (bivariate/HSROC) × CC method (0.5/reciprocal/none) × Exclusion (all/drop-largest/drop-smallest) = 3×3×3 = 27 specifications.

**Files:**
- Modify: `metasprint-dta.html` — replace `runShuraMultiverse()` (~line 18284)

**What to implement:**

Replace the body of `runShuraMultiverse()`:
- Generate specs: `{model: 'bivariate'|'hsroc', cc: '0.5'|'reciprocal'|'exclude', exclusion: 'all'|'drop-largest'|'drop-smallest'}`
- For each spec:
  - Apply CC method to studies
  - Apply exclusion (remove study with largest/smallest N)
  - Run `improvedBivariatePool()` or `hsrocModel()`
  - Record: pooledSens, pooledSpec, DOR, I2_sens
- Draw specification curve on canvas:
  - X-axis: specification index (sorted by DOR)
  - Y-axis: DOR (log scale)
  - CI segments per specification
  - Null line at DOR=1
- Summary table below with all specs
- Highlight the default specification (bivariate, 0.5 CC, all studies)

---

## Task 3: Hikmah (NND + PPV/NPV Calculator)

Replace NNT calculator with DTA-specific clinical utility: NND (Number Needed to Diagnose) and PPV/NPV at user-specified prevalence.

**Files:**
- Modify: `metasprint-dta.html` — replace `computeHikmahNNT()` (~line 18552) content

**What to implement:**

- **NND** = 1 / (Sens - (1 - Spec)) = 1 / Youden_J
- **PPV** = (Sens × Prev) / (Sens × Prev + (1-Spec) × (1-Prev))
- **NPV** = (Spec × (1-Prev)) / ((1-Sens) × Prev + Spec × (1-Prev))
- Icon array: 100 patients at given prevalence → show TP (green), FP (orange), FN (red), TN (gray)
- Prevalence slider (1-50%)
- Table: Prevalence | PPV | NPV | TP | FP | FN | TN per 1000

---

## Task 4: Taqwa (DTA Integrity Checks)

Replace GRIM/mean checks with DTA-specific integrity checks.

**Files:**
- Modify: `metasprint-dta.html` — replace `runTaqwaChecks()` (~line 19179) content

**What to implement:**

Three DTA-specific checks:
1. **Cell consistency**: TP+FN must equal total diseased; TN+FP must equal total healthy. Flag mismatches.
2. **Sensitivity/Specificity plausibility**: Flag if Sens=1.00 or Spec=1.00 (zero-cell, needs CC). Flag if both <0.50 (worse than chance).
3. **Sample size adequacy**: Flag studies with N < 30 (underpowered DTA). Flag if diseased < 10 or healthy < 10 (unstable estimates).

Keep existing funding bias check (still relevant for DTA).

---

## Task 5: Fitrah (DTA Q&A Engine)

Add DTA-specific queries to the keyword engine.

**Files:**
- Modify: `metasprint-dta.html` — extend `runFitrahQuery()` (~line 18658)

**What to implement:**

Add these DTA-specific Q&A patterns:
- "threshold effect" → Report Spearman rho between Sens and 1-Spec, significance
- "SROC" / "AUC" → Report AUC value, interpretation (>0.9 excellent, >0.8 good, >0.7 fair)
- "likelihood ratio" / "PLR" / "NLR" → Report PLR/NLR with clinical interpretation
- "sensitivity" → Report pooled Sens with CI, interpretation
- "specificity" → Report pooled Spec with CI, interpretation
- "DOR" → Report DOR with CI, interpretation
- "ruling in" / "rule in" → Report Spec and PLR (high PLR = good rule-in)
- "ruling out" / "rule out" → Report Sens and NLR (low NLR = good rule-out)
- "prevalence" / "PPV" / "NPV" → Report PPV/NPV at 10% and 20% prevalence
- "number needed" / "NND" → Report NND = 1/Youden

Also update the suggestion buttons to show DTA-specific questions.

---

## Task 6: Ihsan (DTA Icon Array + Dot Plots)

Replace pairwise icon array with DTA 2×2 diagnostic grid, and adapt quantile dot plot for sensitivity/specificity.

**Files:**
- Modify: `metasprint-dta.html` — update `drawIhsanIconArray()` (~line 18882) and `drawQuantileDotPlot()` (~line 18761)

**What to implement:**

**Icon array (DTA adaptation):**
- User picks prevalence (default 20%)
- Show 100 patients:
  - `Prev * 100` diseased → Sens fraction are TP (green checkmark), rest FN (red X)
  - `(1-Prev) * 100` healthy → Spec fraction are TN (gray), rest FP (orange !)
- Summary: "Of 100 patients at 20% prevalence: 18 correctly identified, 2 missed, 64 correctly cleared, 16 false alarms"

**Quantile dot plot (DTA adaptation):**
- Instead of one pooled effect, show TWO rows of dots:
  - Row 1: Sensitivity (20 dots from normal(logit(sens), SE_sens), back-transformed)
  - Row 2: Specificity (20 dots from normal(logit(spec), SE_spec), back-transformed)
- Color: dots left of 0.5 red, right of 0.5 green

---

## Task 7: Dhulm (DTA-aware Equity)

Replace hardcoded demographics with actual study metadata parsing.

**Files:**
- Modify: `metasprint-dta.html` — update `_estimateRepresentation()` (~line 19327)

**What to implement:**

- Parse study-level covariates from `extractedStudies`:
  - Look for `covariate` or `notes` fields mentioning: "female", "women", "elderly", "pediatric", "rural", etc.
  - Count studies with each keyword
- If no covariates available, report "Equity data not extractable from 2×2 tables alone — add population descriptors to covariate columns"
- Show which studies have population descriptors vs which don't
- Compute "Reporting Equity Score" = fraction of studies with any demographic covariate
- Replace hardcoded bars with actual data-driven bars where available

---

## Task 8: Rahma (DTA Plain-Language Summary)

Generate DTA-specific patient-facing summaries in plain language.

**Files:**
- Modify: `metasprint-dta.html` — update `_generateEnglishSummary()` and equivalents

**What to implement:**

English template:
```
"We looked at [k] studies testing [index test name from protocol] for [condition from protocol].

The test correctly identifies [Sens%] of people who have the condition (sensitivity),
and correctly clears [Spec%] of people who don't have it (specificity).

What this means at a [prevalence]% disease rate:
- If you test positive, there is a [PPV%] chance you actually have the condition.
- If you test negative, there is a [NPV%] chance you are truly clear.

[If PLR > 10]: This test is very good at confirming the condition when the result is positive.
[If NLR < 0.1]: This test is very good at ruling out the condition when the result is negative.

Confidence: [GRADE level]. The results were [consistent/variable] across studies (I² = [value]).
"
```

Compute Flesch-Kincaid grade level estimate. Target: 8th grade or below.

---

## Task 9: Selenium Tests for Insights

**Files:**
- Modify: `test_dta_advanced.py` — add Insights section tests

**What to implement:**

Add tests checking that after analysis, navigating to Insights tab and clicking each sub-tab renders non-empty content:
- Mizan: canvas has content (non-blank), summary mentions "Youden"
- Shura: after clicking Run, table has rows, mentions "specification"
- Hikmah: after entering prevalence and clicking, shows PPV/NPV
- Taqwa: after clicking Run, shows integrity check results
- Fitrah: typing "sensitivity" and clicking shows answer with "%"
- Ihsan: dot plot canvas rendered
- Rahma: English summary contains "sensitivity" and "specificity"

7 new tests.

**Step 1: Add tests, run, commit**

```bash
python run_dta_tests.py  # all pass
git commit -m "test(insights): add Selenium tests for DTA-adapted Insights tabs"
```

---

## Task 10: Final Verification

1. Div balance check (HTML + JS)
2. No `</script>` in JS
3. Full test suite pass
4. Commit

---

## Summary

| Task | Tab | Adaptation |
|------|-----|------------|
| 1 | Mizan | Sens vs Spec trade-off scale + Youden Index |
| 2 | Shura | 27-spec DTA multiverse (model × CC × exclusion) |
| 3 | Hikmah | NND + PPV/NPV calculator with icon array |
| 4 | Taqwa | 2×2 cell consistency + plausibility + adequacy |
| 5 | Fitrah | 10+ DTA-specific Q&A patterns |
| 6 | Ihsan | DTA icon grid (TP/FP/FN/TN per 100) + dual dot plot |
| 7 | Dhulm | Data-driven equity from study covariates |
| 8 | Rahma | DTA plain-language summary template |
| 9 | Tests | 7 new Selenium tests for Insights |
| 10 | Verify | Div balance + full suite |

**Tabs not modified (already DTA-functional):** Tawakkul, Amanah, Tabayyun, Living, Conflict, Radar, Registry — these 7 tabs work with universe/study data and don't depend on pairwise-specific logic.
