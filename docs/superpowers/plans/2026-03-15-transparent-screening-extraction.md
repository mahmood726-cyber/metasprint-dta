# Transparent Screening + Traceable Extraction — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every inclusion/exclusion decision and every extracted number transparent and traceable to source text.

**Architecture:** Three layers: (1) extraction source tracking in `extractDTAFromAbstract()`, (2) screening checklist population during auto-selection, (3) UI rendering in results table, tooltips, highlights, and detail row.

**Tech Stack:** Pure JavaScript, HTML. No new dependencies.

---

## Task 1: Extraction Source Tracking

**Files:**
- Modify: `metasprint-dta.html:5130-5600` (`extractDTAFromAbstract()`)

- [ ] **Step 1: Add `_sources` object to extraction result**

At the top of `extractDTAFromAbstract()` after `const result = {};`, add:
```javascript
result._sources = {};
```

- [ ] **Step 2: Track sensitivity extraction source**

In the sensitivity extraction loop (~line 5120), after `result.sensitivity = parseFloat(sensM[1])`, add:
```javascript
result._sources.sensitivity = {
  value: result.sensitivity, sourceText: sensM[0],
  charStart: sensM.index, method: 'direct'
};
```
Apply same pattern for the fullback sensitivity search (~line 5137).

- [ ] **Step 3: Track specificity extraction source**

Same pattern in specificity loop (~line 5162):
```javascript
result._sources.specificity = {
  value: result.specificity, sourceText: specM[0],
  charStart: specM.index, method: 'direct'
};
```

- [ ] **Step 4: Track PPV/NPV extraction sources**

In PPV patterns loop (~line 5346):
```javascript
result._sources.ppv = { value: result.ppv, sourceText: ppvM[0], charStart: ppvM.index, method: 'direct' };
```
Same for NPV (~line 5362).

- [ ] **Step 5: Track AUC extraction source**

In AUC patterns loop (~line 5430):
```javascript
result._sources.auc = { value: result.auc, sourceText: aucM[0], charStart: aucM.index, method: 'direct' };
```

- [ ] **Step 6: Track LR+/LR- extraction sources**

In LR plus/minus loops (~lines 5449, 5460):
```javascript
result._sources.lrPlus = { value: result.lrPlus, sourceText: m[0], charStart: m.index, method: 'direct' };
result._sources.lrMinus = { value: result.lrMinus, sourceText: m[0], charStart: m.index, method: 'direct' };
```

- [ ] **Step 7: Track DOR extraction source**

In DOR patterns loop (~line 5471):
```javascript
result._sources.dor = { value: result.dor, sourceText: m[0], charStart: m.index, method: 'direct' };
```

- [ ] **Step 8: Track derived values**

For DOR-to-sens/spec derivation (~line 5467):
```javascript
result._sources.specificity = { value: result.specificity, method: 'derived_from_dor',
  inputs: ['dor', 'sensitivity'], formula: 'Spec = DOR*(1-Sens) / (Sens + DOR*(1-Sens))' };
```

For LR-to-sens/spec derivation (~line 5485):
```javascript
result._sources.sensitivity = { value: result.sensitivity, method: 'derived_from_lr',
  inputs: ['lrPlus', 'lrMinus'], formula: 'Spec=(LR+-1)/(LR+-LR-), Sens=LR+*(1-Spec)' };
result._sources.specificity = { value: result.specificity, method: 'derived_from_lr',
  inputs: ['lrPlus', 'lrMinus'], formula: 'Spec=(LR+-1)/(LR+-LR-)' };
```

For PPV+NPV+prev derivation (~line 5379):
```javascript
result._sources.sensitivity = { value: result.sensitivity, method: 'derived_from_ppv_npv',
  inputs: ['ppv', 'npv', 'prevalence'], formula: 'Iterative grid search over Sens/Spec to match PPV+NPV' };
```

- [ ] **Step 9: Track combined/respectively/other format sources**

For combined sens/spec pattern (~line 5194), fraction pattern (~line 5243), and other specialized patterns, add same `_sources` tracking with `sourceText: match[0]`.

- [ ] **Step 10: Run existing tests**

```bash
python test_oa_discovery.py
```
Expected: 74/74 PASS (no regression — `_sources` is additive)

- [ ] **Step 11: Commit**

```bash
git add metasprint-dta.html
git commit -m "feat: extraction source tracking — _sources with match text and positions"
```

---

## Task 2: Screening Checklist Population

**Files:**
- Modify: `metasprint-dta.html:6335-6370` (auto-selection in `renderOAResultsTable()`)
- Modify: `metasprint-dta.html:6155-6210` (`toggleOASelectAll()` / quality gate logic)

- [ ] **Step 1: Add screening checklist builder function**

Add before `renderOAResultsTable()` (~line 6310):
```javascript
function buildScreeningChecklist(t) {
  const data = t.backCalc || t.direct2x2;
  const metrics = t.ctgovMetrics || t.abstractMetrics || {};
  const checklist = {};

  // 1. Index test match
  checklist.indexTestMatch = {
    pass: t._indexTestMatch === 'match',
    reason: t._indexTestMatch === 'match' ? 'Matched index test'
      : t._indexTestMatch === 'partial' ? 'Partial match only'
      : 'No match for index test'
  };

  // 2. Not a review
  checklist.notReview = {
    pass: !t._isReview,
    reason: t._isReview ? 'Systematic review or meta-analysis' : 'Primary study'
  };

  // 3. Data extracted
  const hasSens = metrics.sensitivity != null;
  const hasSpec = metrics.specificity != null;
  const hasData = data != null;
  checklist.dataExtracted = {
    pass: hasData,
    reason: hasData
      ? 'Sens ' + (hasSens ? (metrics.sensitivity * 100).toFixed(0) + '%' : 'derived') +
        ', Spec ' + (hasSpec ? (metrics.specificity * 100).toFixed(0) + '%' : 'derived') +
        ' (' + (data?.method || 'unknown') + ')'
      : 'No extractable sensitivity/specificity data'
  };

  // 4. Quality gate
  if (data) {
    const conf = data.confidence || 'low';
    const totalCells = (data.tp||0) + (data.fp||0) + (data.fn||0) + (data.tn||0);
    const n = Math.max(t.enrollment||0, totalCells);
    const nDis = (data.tp||0) + (data.fn||0);
    const nNonDis = (data.fp||0) + (data.tn||0);
    const minArm = Math.min(nDis, nNonDis);
    const hasMultiTestWarn = metrics._multiTestWarning;
    const isPrevEst = data.method === 'prevalence-est';
    const qualityOk = !hasMultiTestWarn && (
      (conf === 'high' || conf === 'medium') ||
      (conf === 'low' && n >= (isPrevEst ? 50 : 30) && minArm >= 10)
    );
    checklist.qualityGate = {
      pass: qualityOk || !!t._edgeRelaxed,
      reason: qualityOk ? conf + ' confidence, N=' + n
        : t._edgeRelaxed ? 'Edge-relaxed (promoted to meet k>=2)'
        : hasMultiTestWarn ? 'Multi-test ambiguity in abstract'
        : 'Low confidence, N=' + n + (isPrevEst ? ' (prevalence-est needs N>=50)' : ' (needs N>=30, minArm>=10)')
    };
  } else {
    checklist.qualityGate = { pass: false, reason: 'No 2x2 data available' };
  }

  // 5. No sub-indication conflict
  checklist.noConflict = {
    pass: !t._subIndicationConflict,
    reason: t._subIndicationConflict
      ? 'Sub-indication conflict: ' + t._subIndicationConflict
      : 'No sub-indication conflict'
  };

  return checklist;
}
```

- [ ] **Step 2: Populate checklist during rendering**

In `renderOAResultsTable()` loop (~line 6322), after `const isReview = !!t._isReview;`:
```javascript
t._screeningChecklist = buildScreeningChecklist(t);
```

- [ ] **Step 3: Run tests**

```bash
python test_oa_discovery.py
```
Expected: 74/74 PASS

- [ ] **Step 4: Commit**

```bash
git add metasprint-dta.html
git commit -m "feat: screening checklist — 5 criteria pass/fail per study"
```

---

## Task 3: UI — Screening Column + Number Tooltips

**Files:**
- Modify: `metasprint-dta.html:1446-1463` (table header)
- Modify: `metasprint-dta.html:6335-6440` (table row rendering)

- [ ] **Step 1: Add "Screen" column header**

In the `<thead>` (~line 1447-1461), add after the Conf column header:
```html
<th scope="col" style="width:50px" title="Screening checklist: pass count / 5 criteria">Screen</th>
```
Update `colspan` references from 12 to 13 in the empty row (line 6318) and detail row (line 6505).

- [ ] **Step 2: Render screening badge in each row**

In `renderOAResultsTable()` after the Conf cell rendering, add:
```javascript
const tdScreen = document.createElement('td');
const cl = t._screeningChecklist;
if (cl) {
  const passCount = [cl.indexTestMatch, cl.notReview, cl.dataExtracted, cl.qualityGate, cl.noConflict]
    .filter(c => c.pass).length;
  const color = passCount === 5 ? 'var(--success)' : passCount >= 3 ? '#f59e0b' : 'var(--danger)';
  const failedReasons = [cl.indexTestMatch, cl.notReview, cl.dataExtracted, cl.qualityGate, cl.noConflict]
    .filter(c => !c.pass).map(c => c.reason).join('; ');
  tdScreen.innerHTML = '<span style="font-size:0.75rem;font-weight:600;color:' + color + '" title="' +
    escapeHtml(failedReasons || 'All criteria passed') + '">' + passCount + '/5</span>';
}
tr.appendChild(tdScreen);
```

- [ ] **Step 3: Add tooltips to Sens/Spec number cells**

In the Sens/Spec cell rendering section (~line 6380-6400), add `title` attributes:
```javascript
const sensTooltip = metrics._sources?.sensitivity
  ? escapeHtml(metrics._sources.sensitivity.sourceText || '') + ' [' + (metrics._sources.sensitivity.method || 'direct') + ']'
  : '';
// Apply: tdSens.title = sensTooltip;
```
Same pattern for Spec, TP, FP, FN, TN cells using back-calc method as tooltip.

- [ ] **Step 4: Run tests**

```bash
python test_oa_discovery.py
```
Expected: 74/74 PASS

- [ ] **Step 5: Commit**

```bash
git add metasprint-dta.html
git commit -m "feat: screening badge column + number tooltips in OA results table"
```

---

## Task 4: Enhanced Abstract Highlighting

**Files:**
- Modify: `metasprint-dta.html:6457-6485` (`highlightAbstractDTA()`)

- [ ] **Step 1: Color-code highlights by extraction type**

Replace the existing `highlightAbstractDTA()` function with:
```javascript
function highlightAbstractDTA(text, metrics) {
  if (!text || !metrics) return escapeHtml(text || '');
  let html = escapeHtml(text);
  const sources = metrics._sources || {};
  const patterns = [];

  // Direct extraction highlights (yellow)
  const directColor = '#fff3cd';
  // Derivation source highlights (blue)
  const derivedSourceColor = '#b3d9ff';

  // For each metric, determine if direct or source-for-derivation
  const addPattern = (key, labelText, value, reBuilder) => {
    const src = sources[key];
    if (value == null) return;
    const pct = value > 1 ? value : value * 100;
    const isDirect = !src || src.method === 'direct';
    const isDerivedSource = !isDirect && src.inputs;
    // If this metric was derived, highlight the INPUT values instead
    if (src && src.method && src.method !== 'direct') {
      // Mark as derived — no text highlight, badge shown in provenance
      return;
    }
    const color = directColor;
    const re = reBuilder(pct);
    patterns.push({ re, label: labelText, color,
      tooltip: 'Extracted: ' + labelText + ' = ' + pct.toFixed(1) + '%' + (src?.sourceText ? ' from: "' + src.sourceText.substring(0, 60) + '"' : '') });
  };

  addPattern('sensitivity', 'Sens', metrics.sensitivity, pct =>
    new RegExp('(sensitiv\\w*\\s*(?:was\\s*|of\\s*|[=:]\\s*)?)(' + pct.toFixed(1).replace('.', '\\.') + '|' + Math.round(pct) + ')(%|\\s*%)', 'gi'));
  addPattern('specificity', 'Spec', metrics.specificity, pct =>
    new RegExp('(specific\\w*\\s*(?:was\\s*|of\\s*|[=:]\\s*)?)(' + pct.toFixed(1).replace('.', '\\.') + '|' + Math.round(pct) + ')(%|\\s*%)', 'gi'));
  addPattern('ppv', 'PPV', metrics.ppv, pct =>
    new RegExp('((?:positive predictive|ppv)\\s*(?:value\\s*)?(?:was\\s*|of\\s*|[=:]\\s*)?)(' + pct.toFixed(1).replace('.', '\\.') + '|' + Math.round(pct) + ')(%|\\s*%)', 'gi'));
  addPattern('npv', 'NPV', metrics.npv, pct =>
    new RegExp('((?:negative predictive|npv)\\s*(?:value\\s*)?(?:was\\s*|of\\s*|[=:]\\s*)?)(' + pct.toFixed(1).replace('.', '\\.') + '|' + Math.round(pct) + ')(%|\\s*%)', 'gi'));

  // Highlight LR values if they were used for derivation
  if (sources.sensitivity?.method === 'derived_from_lr' || sources.specificity?.method === 'derived_from_lr') {
    if (metrics.lrPlus != null && sources.lrPlus?.sourceText) {
      const val = metrics.lrPlus;
      patterns.push({ re: new RegExp('((?:lr\\s*\\+|positive\\s+likelihood)\\s*[=:]?\\s*)(' + val.toFixed(1).replace('.', '\\.') + ')', 'gi'),
        label: 'LR+', color: derivedSourceColor,
        tooltip: 'Source for derived Sens/Spec: LR+ = ' + val.toFixed(2) });
    }
    if (metrics.lrMinus != null && sources.lrMinus?.sourceText) {
      const val = metrics.lrMinus;
      patterns.push({ re: new RegExp('((?:lr\\s*[-\\u2013]|negative\\s+likelihood)\\s*[=:]?\\s*)(' + val.toFixed(2).replace('.', '\\.') + ')', 'gi'),
        label: 'LR-', color: derivedSourceColor,
        tooltip: 'Source for derived Sens/Spec: LR- = ' + val.toFixed(3) });
    }
  }

  // N pattern
  if (metrics.totalN) {
    patterns.push({ re: new RegExp('(' + metrics.totalN + ')(\\s*(?:patients|subjects|participants|individuals|cases))', 'gi'),
      label: 'N', color: directColor, tooltip: 'Extracted: N = ' + metrics.totalN });
  }

  for (const p of patterns) {
    html = html.replace(p.re, (m) =>
      '<mark style="background:' + p.color + ';cursor:help" title="' + escapeHtml(p.tooltip) + '">' + m + '</mark>');
  }
  return html;
}
```

- [ ] **Step 2: Run tests**

```bash
python test_oa_discovery.py
```
Expected: 74/74 PASS

- [ ] **Step 3: Commit**

```bash
git add metasprint-dta.html
git commit -m "feat: color-coded abstract highlighting (yellow=direct, blue=derivation source)"
```

---

## Task 5: Evidence Chain + Checklist in Detail Row

**Files:**
- Modify: `metasprint-dta.html:6488-6571` (`toggleOADetailRow()`)

- [ ] **Step 1: Add screening checklist to detail row**

In `toggleOADetailRow()`, after the source links div (~line 6562), add:
```javascript
// Screening checklist
const cl = study._screeningChecklist;
if (cl) {
  panelHtml += '<div class="oa-detail-section" style="margin-top:12px">';
  panelHtml += '<h4>Screening Checklist</h4>';
  panelHtml += '<table class="oa-prov-table"><tbody>';
  const criteria = [
    ['Index test match', cl.indexTestMatch],
    ['Not a review', cl.notReview],
    ['Data extracted', cl.dataExtracted],
    ['Quality gate', cl.qualityGate],
    ['No sub-indication conflict', cl.noConflict]
  ];
  for (const [label, c] of criteria) {
    const icon = c.pass ? '<span style="color:var(--success)">&#10003;</span>' : '<span style="color:var(--danger)">&#10007;</span>';
    panelHtml += '<tr><td>' + icon + ' ' + escapeHtml(label) + '</td><td>' + escapeHtml(c.reason) + '</td></tr>';
  }
  panelHtml += '</tbody></table></div>';
}
```

- [ ] **Step 2: Add evidence chain to detail row**

After the screening checklist, add:
```javascript
// Evidence chain
const sources = (study.abstractMetrics || study.ctgovMetrics || {})._sources;
if (sources) {
  panelHtml += '<div class="oa-detail-section" style="margin-top:12px">';
  panelHtml += '<h4>Evidence Chain</h4>';
  panelHtml += '<table class="oa-prov-table"><thead><tr><th scope="col">Metric</th><th scope="col">Value</th><th scope="col">Source</th></tr></thead><tbody>';
  for (const [key, src] of Object.entries(sources)) {
    if (!src || key.startsWith('_')) continue;
    const val = src.value != null ? (src.value > 1 ? src.value.toFixed(1) + '%' : (src.value * 100).toFixed(1) + '%') : '-';
    let srcText = '';
    if (src.method === 'direct') {
      srcText = '<span style="color:var(--success)">&larr;</span> "' + escapeHtml((src.sourceText || '').substring(0, 80)) + '" <span style="color:var(--text-muted)">[Abstract]</span>';
    } else if (src.method && src.method.startsWith('derived')) {
      const badge = '<span style="background:#b3d9ff;padding:1px 5px;border-radius:3px;font-size:0.72rem">Derived</span>';
      srcText = badge + ' ' + escapeHtml(src.formula || src.method);
    }
    panelHtml += '<tr><td>' + escapeHtml(key) + '</td><td>' + val + '</td><td style="font-size:0.78rem">' + srcText + '</td></tr>';
  }
  // Back-calculated 2x2 chain
  if (data) {
    const bcMethod = data.method === 'algebraic' ? 'Algebraic (Sens+Spec+PPV+NPV+N)' :
      data.method === 'ci-width' ? 'CI-width estimation' :
      data.method === 'prevalence-est' ? 'Prevalence-based partitioning' :
      data.method === 'direct' ? 'Directly from abstract' : data.method;
    panelHtml += '<tr><td>TP/FP/FN/TN</td><td>' + data.tp + '/' + data.fp + '/' + data.fn + '/' + data.tn +
      '</td><td style="font-size:0.78rem"><span style="color:var(--success)">&larr;</span> Back-calculated: ' + escapeHtml(bcMethod) + '</td></tr>';
  }
  panelHtml += '</tbody></table></div>';
}
```

- [ ] **Step 3: Add derived value badges to provenance table**

In the existing provenance metrics section (~line 5531), for each metric check if derived:
```javascript
const derivedBadge = (key) => {
  const src = (metrics._sources || {})[key];
  if (src && src.method && src.method !== 'direct') {
    return ' <span style="background:#b3d9ff;padding:1px 4px;border-radius:3px;font-size:0.7rem;cursor:help" title="' +
      escapeHtml(src.formula || src.method) + '">Derived</span>';
  }
  return '';
};
```
Append `derivedBadge('sensitivity')` after the Sensitivity value, etc.

- [ ] **Step 4: Run tests**

```bash
python test_oa_discovery.py
python test_advanced_methods.py
```
Expected: 74/74 + 88/88 PASS

- [ ] **Step 5: Commit**

```bash
git add metasprint-dta.html
git commit -m "feat: evidence chain + screening checklist in detail row"
```

---

## Task 6: Selenium Tests for Transparency Features

**Files:**
- Create: `test_transparency.py`

- [ ] **Step 1: Write transparency test suite**

Test: screening checklist renders, tooltips exist, highlights appear, evidence chain shows, derived badges show.

Key assertions:
- After search, every study has `_screeningChecklist` with 5 criteria
- Main table has "Screen" column with N/5 badge
- Detail row has checklist with pass/fail icons
- Abstract has `<mark>` tags for extracted values
- Sens/Spec cells have `title` attributes with source text
- Evidence chain table has rows for each extracted metric

- [ ] **Step 2: Run full test suite**

```bash
python test_oa_discovery.py
python test_advanced_methods.py
python test_transparency.py
```
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add test_transparency.py metasprint-dta.html
git commit -m "test: transparency feature tests — screening + extraction traceability"
```
