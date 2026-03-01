# MetaSprint DTA: User Experience Improvement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Address the highest-impact findings from a 2-persona user review (medical student + experienced meta-analyst) to lower the barrier to entry and close competitive gaps with R mada / RevMan.

**Architecture:** All changes to `metasprint-dta.html` (21.6K lines). No new files except test additions.

**Tech Stack:** Vanilla JS, inline SVG, Selenium + Python testing.

**Source findings:** 28 student findings (13 friction, 4 missing, 11 good) + 25 expert findings (3 critical-missing, 7 nice-missing, 13 strengths, 2 concerns).

---

## Priority Classification

### Tier 1: Quick Start & Onboarding (highest user impact, lowest effort)
These address the #1 barrier identified by both personas: new users can't find their way to running an analysis.

### Tier 2: Dark Mode SVG Export Fix (blocks publication use)
Exported SVGs contain CSS variables that don't render outside the app.

### Tier 3: Coupled Forest Plot (publication standard)
Cochrane DTA reviews require paired sens/spec forest plots on a shared study axis.

### Tier 4: DTA-Specific Subgroup Analysis (expert feature gap)
The meta-analyst's #3 missing feature — re-run bivariate per subgroup with interaction test.

### Tier 5: SROC Interpretation Text (student learning gap)
Students don't know how to read the SROC curve.

---

## Task 1: Quick Start Modal — "I Already Have My Data"

**The problem (STUDENT-02, STUDENT-05):** The onboarding modal dumps users into a 40-day sprint dashboard. A student with 8 studies in hand has to discover tab 5 (Extract) on their own.

**Files:**
- Modify: `metasprint-dta.html` — onboarding modal (~line 892) and its dismiss handler

**What to implement:**

Add two buttons to the onboarding overlay:
1. **"Quick Analysis"** (primary) — dismisses modal, switches directly to the Extract tab, shows a toast "Enter your 2x2 data below, or click Load Demo Data"
2. **"Full Sprint"** (secondary/outline) — current behavior, lands on Dashboard

Also add a persistent "Quick Start" chip/banner at the top of the Extract tab that says:
"Enter TP/FP/FN/TN for each study below, or Load Demo Data. Then switch to the Analyze tab."

**Step 1: Read onboarding modal HTML**
**Step 2: Add the two-button layout**
**Step 3: Wire Quick Analysis button to switchPhase('extract') + toast**
**Step 4: Add Quick Start banner to Extract tab**
**Step 5: Run tests, commit**

---

## Task 2: Insights Tab — Add English Subtitles to Arabic Names

**The problem (STUDENT-04):** 15 sub-tabs with Arabic names are opaque. Tooltips require hover and don't work on touch.

**Files:**
- Modify: `metasprint-dta.html` — insight tab buttons (~lines 1551-1565)

**What to implement:**

Change each tab button from just the Arabic name to "Arabic: English" format, with the English in smaller text:

```
Tawakkul → "Tawakkul: Trust"
Mizan → "Mizan: Balance"
Shura → "Shura: Robustness"
Hikmah → "Hikmah: Clinical"
Fitrah → "Fitrah: Q&A"
Ihsan → "Ihsan: Visuals"
Amanah → "Amanah: Gaps"
Taqwa → "Taqwa: Integrity"
Dhulm → "Dhulm: Equity"
Rahma → "Rahma: Summary"
Tabayyun → "Tabayyun: Verify"
```

Keep Living, Conflicts, Radar, Registry as-is (already English).

Format: `<span class="insight-tab-label"><strong>Tawakkul</strong><br><span style="font-size:0.7rem;opacity:0.7">Trust</span></span>`

Also add CSS for `.insights-tab` to handle the two-line layout without overflow.

**Step 1: Update button content**
**Step 2: Adjust CSS for two-line tabs**
**Step 3: Run tests, commit**

---

## Task 3: SVG Export — Resolve CSS Variables to Hex Colors

**The problem (EXPERT-04):** Exported SVGs contain `fill="var(--primary)"` which renders as black in Illustrator, Inkscape, and journal production systems.

**Files:**
- Modify: `metasprint-dta.html` — SVG export functions (~lines 17253-17277)

**What to implement:**

In the SVG export function, before creating the Blob:
1. Parse the SVG string
2. Get computed styles for all CSS variables used (`--primary`, `--text`, `--text-muted`, `--border`, `--danger`, `--success`, `--warning`, `--info`)
3. Replace all `var(--xxx)` occurrences with the resolved hex/rgb values
4. Then create the Blob from the resolved SVG

```javascript
function resolveCSSSVG(svgString) {
  const style = getComputedStyle(document.documentElement);
  const vars = ['primary','text','text-muted','border','danger','success','warning','info','bg','surface'];
  let resolved = svgString;
  vars.forEach(v => {
    const val = style.getPropertyValue('--' + v).trim();
    if (val) resolved = resolved.replaceAll('var(--' + v + ')', val);
  });
  return resolved;
}
```

Apply this in all SVG export paths (SROC, forest sens, forest spec, Deeks funnel, plus any future exports).

**Step 1: Add resolveCSSSVG helper**
**Step 2: Wire it into all export functions**
**Step 3: Test export in dark mode (should produce dark-theme colors)**
**Step 4: Run tests, commit**

---

## Task 4: Coupled Forest Plot (Paired Sens/Spec on Shared Axis)

**The problem (EXPERT-02):** Cochrane DTA reviews show a coupled forest plot where sensitivity (left) and specificity (right) share a common study axis. Currently the app renders them as separate SVGs.

**Files:**
- Modify: `metasprint-dta.html` — add `renderCoupledForestPlot()` function near existing forest plot code (~line 8590)

**What to implement:**

A new `renderCoupledForestPlot(result)` function that produces a single SVG:
- Center column: study labels (shared)
- Left panel: sensitivity forest (0-100% scale, pointing left)
- Right panel: specificity forest (0-100% scale, pointing right)
- Pooled diamonds at bottom of each panel
- Each study on the same Y row across both panels
- Width: ~900px total (450 per panel + 100 center labels)

Wire it into the results display alongside the existing separate forests. Add an SVG export button for it.

**Step 1: Implement renderCoupledForestPlot**
**Step 2: Add to results display (new container below existing forests)**
**Step 3: Add export button**
**Step 4: Add Selenium test (verify SVG has correct number of study rows)**
**Step 5: Run tests, commit**

---

## Task 5: DTA-Specific Subgroup Analysis

**The problem (EXPERT-01):** The meta-analyst needs separate bivariate pools per subgroup with a test for interaction. The current subgroup analysis uses pairwise data, not 2x2 DTA data.

**Files:**
- Modify: `metasprint-dta.html` — add `computeDTASubgroupAnalysis()` near existing subgroup code (~line 10033)

**What to implement:**

1. Group studies by the `subgroup` field (from extraction table)
2. For each subgroup with k >= 2 studies:
   - Run `improvedBivariatePool()` (or current method) on that subset
   - Store: pooled sens, spec, DOR, CIs, I², k
3. Test for subgroup differences:
   - Chi-squared test on logDOR: Q_between = sum(w_j * (logDOR_j - logDOR_overall)^2)
   - df = number_of_subgroups - 1
   - p-value from chi2 distribution
4. Display as a table: Subgroup | k | Sens (CI) | Spec (CI) | DOR (CI) | I²
5. Show Q_between test result below the table
6. Add a "Run Subgroup Analysis" button in the Advanced DTA section

**Step 1: Implement computeDTASubgroupAnalysis**
**Step 2: Add UI button and results container**
**Step 3: Add Selenium test**
**Step 4: Run tests, commit**

---

## Task 6: SROC Curve Interpretation Text

**The problem (STUDENT-27):** The SROC plot has no inline explanation. A student doesn't know what the curve, ellipses, or summary point mean.

**Files:**
- Modify: `metasprint-dta.html` — after SROC plot rendering (~line 8807)

**What to implement:**

Add an interpretation paragraph below the SROC plot:

```html
<div class="sroc-interpretation" style="font-size:0.82rem;color:var(--text-muted);margin-top:8px;max-width:520px">
  <strong>Reading this plot:</strong> Each circle is a study, plotted at its sensitivity (y-axis)
  vs. false positive rate (x-axis). Studies in the top-left corner perform best.
  The <span style="color:var(--danger)">red diamond</span> is the pooled summary point.
  The <span style="color:var(--danger)">dashed curve</span> shows how sensitivity and specificity
  trade off across different thresholds.
  [If confidence region shown]: The inner ellipse is the 95% confidence region for the summary point.
  [If prediction region shown]: The outer ellipse is the 95% prediction region showing where
  a future study's result might fall.
</div>
```

Conditionally show the ellipse explanations based on the toggle state.

**Step 1: Add interpretation div**
**Step 2: Wire visibility to toggle states**
**Step 3: Run tests, commit**

---

## Task 7: Protocol PIRD/PICO Sync

**The problem (STUDENT-01, STUDENT-21):** Protocol tab uses PIRD labels but Search uses PICO IDs. Data doesn't sync between them.

**Files:**
- Modify: `metasprint-dta.html` — Protocol and Search sections

**What to implement:**

1. Add `input` event listeners on `protP`, `protI`, `protR`, `protD` that copy values to `picoP`, `picoI`, `picoC`, `picoO` respectively
2. Ensure bidirectional sync (if user edits picoP, copy to protP)
3. Standardize visible labels to PIRD (Population, Index test, Reference standard, Diagnosis) since this is the correct DTA framework. Keep PICO IDs internally for backward compat.

**Step 1: Add sync listeners**
**Step 2: Fix any label mismatches**
**Step 3: Run tests, commit**

---

## Task 8: Add Inline SROC Interpretation to Analyze Results + SROC Export Button

**Already covered by Task 6. This task adds SVG export for the coupled forest plot if not covered in Task 4.**

*Merged into Tasks 4 and 6.*

---

## Summary

| Task | Target User | Category | Est. Lines Changed |
|------|-------------|----------|-------------------|
| 1 | Student | Onboarding | ~40 |
| 2 | Student | Navigation | ~30 |
| 3 | Expert | Export | ~20 |
| 4 | Expert | Visualization | ~120 |
| 5 | Expert | Statistics | ~80 |
| 6 | Student | Education | ~20 |
| 7 | Student | Data flow | ~30 |

**Total:** 7 tasks, ~340 lines of changes.

**Findings NOT addressed (intentional):**
- REML bivariate GLMM (EXPERT-04): Major algorithmic change, needs iterative optimization. R code export already allows verification against mada::reitsma(). Deferred to v2.
- Comparative DTA (EXPERT-01): Requires entirely new statistical framework (indirect comparison of index tests). Out of scope.
- Bayesian bivariate model (EXPERT-01): Requires MCMC in browser (JAGS/Stan port). Out of scope.
- RevMan XML import (EXPERT-01): Niche format, CSV import exists as workaround.
- Video tutorial (STUDENT-25): Requires external production, not an in-app code change.
- 40-day sprint simplification (STUDENT-02): Architectural decision — the sprint framework is a core design feature, not a bug. Quick Start (Task 1) is the right mitigation.
