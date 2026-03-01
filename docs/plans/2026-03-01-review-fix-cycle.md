# MetaSprint DTA: 3-Persona Review + Fix Cycle

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Comprehensive multi-persona code review of metasprint-dta.html (21,544 lines, 203/203 tests passing), fix all P0/P1 issues, verify tests, commit.

**Architecture:** Three sequential review agents each read targeted sections of the single HTML file, produce classified findings (P0/P1/P2). Findings are deduplicated, then all P0/P1 are fixed in a single editing pass. Final verification re-runs full test suite + safety checks.

**Tech Stack:** Selenium + Python tests, Chrome headless, vanilla JS single-file HTML app.

---

## Baseline Health (pre-review)

| Check | Result |
|-------|--------|
| Div balance | 719/719 OK |
| Script tags | 1 open / 1 close |
| Duplicate functions | None |
| localStorage | Safe wrappers (Safari Private Mode guard) |
| Tests | 203/203 PASS (6 suites) |

---

## Task 1: Persona 1 — DTA Statistician Review

**Focus:** Statistical correctness of all DTA methods.

Launch an agent that reads these sections and checks for issues:

**Core pooling (lines 7435-7960):**
- `wilsonCI()` — correct formula? Alpha handling?
- `improvedBivariatePool()` — logit transforms, CC, DL tau², RE weights, CI (t vs z), DOR = exp(mu1+mu2)
- `hsrocModel()` — Lambda/Theta parameterization, AUC via Phi (not logistic), prediction region chi2_2
- `metaRegression()` — logDOR on moderator, permutation test, Knapp-Hartung SE adjustment

**Advanced DTA (lines 9007-9700):**
- Crosshairs plot — Wilson CIs for study-level Sens/Spec, FPR inversion
- L'Abbe plot — iso-DOR curves, correct DOR formula
- Galbraith plot — z-scores and precision, radial axis
- Fagan nomogram — Bayes theorem PLR/NLR → post-test probability
- Rho sensitivity — bivariate repool with rho=-0.9..0.9
- Bootstrap CIs — percentile method, N=2000, correct resampling

**Insights DTA (lines 17900-20600):**
- `_getDTAInsightsData()` — correct field mapping from lastAnalysisResult
- Mizan — Youden J = Sens+Spec-1, clinical role interpretation, PLR/NLR thresholds
- Shura multiverse — 27 specs (3×3×3), DOR sorted, correct CC/exclusion application
- Hikmah — NND = 1/J, PPV/NPV Bayes formulas with prevalence
- Taqwa — cell consistency (TP+FN=diseased, TN+FP=healthy), plausibility flags
- Fitrah — Q&A pattern accuracy (AUC thresholds, LR interpretation)
- Ihsan — icon array TP/FP/FN/TN math at given prevalence
- Rahma — plain-language summary correctness

**Other analysis (lines 8700-8995):**
- GRADE domains — QUADAS-2 mapping, SoF table (TP/FP/FN/TN per 1000)
- Cumulative meta-analysis — subset pooling correctness
- Deeks' funnel test — regression of 1/sqrt(ESS) on logDOR

**Classification:**
- P0: Wrong formula, sign error, off-by-one, hardcoded z=1.96, `||` dropping zero
- P1: Missing guard, edge case crash (k=1, k=2), questionable threshold
- P2: Style, minor imprecision, documentation

**Step 1: Run review agent**

Launch agent with full DTA statistics focus. Produce numbered findings like:
```
STAT-01 [P0]: description (file:line)
STAT-02 [P1]: description (file:line)
```

**Step 2: Record findings in this plan's output section**

---

## Task 2: Persona 2 — Security & Code Quality Review

**Focus:** XSS, injection, structural integrity, performance.

Launch an agent that checks:

**XSS / Injection (whole file):**
- All `.innerHTML =` assignments — is user input escaped via `escapeHtml()`?
- `escapeHtml()` function (line 1840) — does it escape quotes for attribute contexts?
- Any `eval()`, `new Function()`, or `document.write()`?
- URL construction — any unvalidated user input in URLs?

**Structural integrity:**
- Div balance (already verified: 719/719)
- No literal `</script>` inside the `<script>` block
- Element ID uniqueness — any duplicate IDs across 21K lines?
- Event listener cleanup — modal close paths remove keydown/keyup listeners?

**Performance:**
- Regex patterns — any catastrophic backtracking risk (nested quantifiers on large input)?
- Memory leaks — Blob URLs created without `revokeObjectURL()`?
- Unbounded loops — any `while(true)` without break condition?
- DOM thrashing — innerHTML in tight loops?

**localStorage:**
- Keys unique to DTA variant (not inherited from pairwise MetaSprint)?
- Safe wrappers used consistently (line 1894-1901)?

**Code quality:**
- Dead code — unreachable branches, commented-out blocks
- Error handling — catch blocks that swallow errors silently
- `|| fallback` patterns that drop valid zero (should be `??`)

**Classification:**
- P0: XSS, injection, data corruption, `</script>` in JS, ID collision
- P1: Missing escaping in low-risk path, dead code, performance risk
- P2: Style, minor cleanup

**Step 1: Run review agent**

```
SEC-01 [P0]: description (file:line)
```

---

## Task 3: Persona 3 — UX & Clinical Workflow Review

**Focus:** Accessibility, dark mode, clinical accuracy, user experience.

Launch an agent that checks:

**Accessibility (whole file):**
- All interactive elements — keyboard support (Enter/Space)?
- `role="application"` — only on genuinely interactive widgets?
- Tab order — logical flow through main tabs?
- `aria-label` on icon-only buttons?
- Focus management — modals trap focus? Return focus on close?

**Dark mode (CSS variables, lines 1-200):**
- All text/background combos — WCAG AA contrast (4.5:1)?
- Hardcoded colors in JS-generated SVG/Canvas — do they respect theme?
- CSS variables used consistently, or are there inline hex colors?

**Clinical interpretation accuracy (Insights tabs):**
- Mizan: PLR > 10 "strong rule-in" — is this threshold correct per evidence?
- Hikmah: PPV/NPV at prevalence — clinical interpretation appropriate?
- Rahma: Plain-language summary — readability appropriate? No misleading claims?
- Fitrah: Q&A responses — clinically accurate interpretation of DOR, LR, AUC?
- GRADE: Domain mapping to QUADAS-2 — correct for DTA?

**UX flow:**
- Error messages — clear and actionable?
- Empty states — all containers show appropriate "no data" messages?
- Loading states — any long operations without feedback?
- Mobile/responsive — tabs scrollable? Tables wrap?

**Classification:**
- P0: Clinically misleading interpretation, inaccessible critical control
- P1: Missing keyboard support, poor contrast, confusing flow
- P2: Minor UX polish, cosmetic

**Step 1: Run review agent**

```
UX-01 [P0]: description (file:line)
```

---

## Task 4: Deduplicate & Classify All Findings

After all 3 reviewers complete:

1. Merge all findings into a single list
2. Remove duplicates (same issue found by multiple personas)
3. Confirm P0/P1/P2 classification
4. Count: total, P0, P1, P2

**Step 1: Create master findings list**

Format:
```
ID      | Sev | Persona | Description | Line(s)
--------|-----|---------|-------------|--------
STAT-01 | P0  | Stats   | ...         | 7500
SEC-01  | P1  | Sec     | ...         | 1840
UX-01   | P1  | UX      | ...         | 18153
```

---

## Task 5: Fix All P0 Issues

Apply fixes for every P0 finding. Each fix:
1. Read the affected lines
2. Apply minimal, targeted edit
3. Verify div balance is still 719/719

**Step 1: Apply P0 fixes one by one**
**Step 2: Verify div balance after all P0 fixes**

---

## Task 6: Fix All P1 Issues

Same as Task 5 but for P1 findings.

**Step 1: Apply P1 fixes one by one**
**Step 2: Verify div balance after all P1 fixes**

---

## Task 7: Verification

**Step 1: Run full test suite**
```bash
python run_dta_tests.py
```
Expected: 203/203 PASS (or more if tests added)

**Step 2: Div balance check**
```python
import re
with open('metasprint-dta.html','r',encoding='utf-8') as f: txt=f.read()
opens = len(re.findall(r'<div[\s>]', txt))
closes = txt.count('</div>')
assert opens == closes, f'Div mismatch: {opens} vs {closes}'
```

**Step 3: Script integrity**
- No literal `</script>` inside `<script>` block
- Function names still unique

**Step 4: Commit**
```bash
git add metasprint-dta.html
git commit -m "fix: N P0 + M P1 fixes from 3-persona DTA review (203/203 tests pass)"
```

---

## Summary

| Task | Action | Output |
|------|--------|--------|
| 1 | DTA Statistician review | STAT-xx findings |
| 2 | Security & Code Quality review | SEC-xx findings |
| 3 | UX & Clinical Workflow review | UX-xx findings |
| 4 | Deduplicate & classify | Master findings list |
| 5 | Fix all P0 | Edited HTML |
| 6 | Fix all P1 | Edited HTML |
| 7 | Verify + commit | 203+ tests pass, clean commit |
