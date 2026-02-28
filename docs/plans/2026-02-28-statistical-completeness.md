# MetaSprint DTA: Statistical Completeness Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fill all placeholder advanced analysis containers with production-quality DTA methods and validate against R `mada` package, making MetaSprint DTA rival standalone DTA tools.

**Architecture:** All methods are pure JS functions added to the single `metasprint-dta.html` file (~19,605 lines). Each method populates an existing empty `<div>` container via `renderAdvancedDTA()`. New visualizations use inline SVG (matching existing SROC/forest pattern). R validation via a new `test_dta_advanced.py` Selenium suite that compares app outputs against pre-computed `mada` reference values stored in `dta_bivariate_reference.py`.

**Tech Stack:** Vanilla JS (no deps), inline SVG, Selenium + Python for testing, R `mada` for gold standard values.

---

## Phase 1: DTA-Specific Visualizations (4 tasks)

These fill the existing empty containers `advCrosshairsContainer`, `advLabbeContainer`, `advGalbraithContainer`, and upgrade `advFaganContainer` from table to SVG nomogram.

### Task 1: Crosshairs Plot

The crosshairs plot is THE signature DTA visualization (Cochrane DTA Handbook Fig 10.3). Each study is a point at (1-Spec, Sens) with horizontal and vertical CI bars forming a crosshair. The summary point and SROC curve overlay give clinical context.

**Files:**
- Modify: `metasprint-dta.html` — add `renderCrosshairsPlot()`, wire into `renderAdvancedDTA()` at the `advCrosshairsContainer` block (~line 9140)
- Test: `test_dta_advanced.py` (new file, created in Task 8)

**Step 1: Add `renderCrosshairsPlot(result, confLevel)` function**

Insert before the `renderAdvancedDTA` function (before line 9018). The function:

```javascript
function renderCrosshairsPlot(result, confLevel) {
  const el = document.getElementById('advCrosshairsContainer');
  if (!el || !result || !result.studyData) return;
  const studies = result.studyData;
  const k = studies.length;
  const alpha = 1 - (confLevel ?? 0.95);
  // Each study: point at (FPR=1-spec, sens) with CI crosshairs
  const W = 500, H = 420, pad = { top: 30, right: 30, bottom: 50, left: 60 };
  const plotW = W - pad.left - pad.right, plotH = H - pad.top - pad.bottom;
  const sx = x => pad.left + x * plotW;  // x = FPR (0..1)
  const sy = y => pad.top + (1 - y) * plotH; // y = sens (0..1)

  let svg = `<svg viewBox="0 0 ${W} ${H}" style="max-width:520px;font-family:system-ui,sans-serif">`;
  // Axes
  svg += `<rect x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="none" stroke="var(--border)" stroke-width="0.5"/>`;
  // Grid lines at 0.2 intervals
  for (let v = 0; v <= 1; v += 0.2) {
    svg += `<line x1="${sx(v)}" y1="${pad.top}" x2="${sx(v)}" y2="${pad.top + plotH}" stroke="var(--border)" stroke-width="0.3" stroke-dasharray="3,3"/>`;
    svg += `<line x1="${pad.left}" y1="${sy(v)}" x2="${pad.left + plotW}" y2="${sy(v)}" stroke="var(--border)" stroke-width="0.3" stroke-dasharray="3,3"/>`;
    svg += `<text x="${sx(v)}" y="${pad.top + plotH + 16}" text-anchor="middle" font-size="10" fill="var(--text-muted)">${v.toFixed(1)}</text>`;
    svg += `<text x="${pad.left - 8}" y="${sy(v) + 4}" text-anchor="end" font-size="10" fill="var(--text-muted)">${v.toFixed(1)}</text>`;
  }
  // Axis labels
  svg += `<text x="${W / 2}" y="${H - 4}" text-anchor="middle" font-size="12" fill="var(--text)">1 - Specificity (FPR)</text>`;
  svg += `<text x="14" y="${H / 2}" text-anchor="middle" font-size="12" fill="var(--text)" transform="rotate(-90,14,${H / 2})">Sensitivity</text>`;
  // Diagonal (chance line)
  svg += `<line x1="${sx(0)}" y1="${sy(0)}" x2="${sx(1)}" y2="${sy(1)}" stroke="var(--text-muted)" stroke-width="0.5" stroke-dasharray="4,4"/>`;

  // Study crosshairs
  studies.forEach((s, i) => {
    const fpr = 1 - s.spec;
    const sens = s.sens;
    // Wilson CI for sens and spec
    const sensCI = s.sensCI || wilsonCI(s.tp, s.tp + s.fn, alpha);
    const specCI = s.specCI || wilsonCI(s.tn, s.tn + s.fp, alpha);
    const fprCI = [1 - specCI[1], 1 - specCI[0]]; // reverse for FPR
    // Crosshair bars
    svg += `<line x1="${sx(fprCI[0])}" y1="${sy(sens)}" x2="${sx(fprCI[1])}" y2="${sy(sens)}" stroke="var(--primary)" stroke-width="1" opacity="0.6"/>`;
    svg += `<line x1="${sx(fpr)}" y1="${sy(sensCI[0])}" x2="${sx(fpr)}" y2="${sy(sensCI[1])}" stroke="var(--primary)" stroke-width="1" opacity="0.6"/>`;
    // Point
    const r = Math.max(3, Math.min(8, 2 + Math.sqrt(s.n || 50) / 4));
    svg += `<circle cx="${sx(fpr)}" cy="${sy(sens)}" r="${r}" fill="var(--primary)" opacity="0.7"/>`;
  });

  // Summary point (pooled)
  if (result.pooledSens != null && result.pooledSpec != null) {
    const sfpr = 1 - result.pooledSpec;
    const ssens = result.pooledSens;
    svg += `<rect x="${sx(sfpr) - 6}" y="${sy(ssens) - 6}" width="12" height="12" fill="var(--danger)" transform="rotate(45,${sx(sfpr)},${sy(ssens)})" opacity="0.9"/>`;
  }
  svg += `</svg>`;
  el.innerHTML = '<h4 style="margin-bottom:8px">Crosshairs Plot (Sensitivity vs 1-Specificity)</h4>' + svg;
}
```

**Step 2: Wire into `renderAdvancedDTA()`**

In the `renderAdvancedDTA()` function, after the Fagan nomogram block (after line ~9129), add:

```javascript
// Crosshairs plot
renderCrosshairsPlot(result, confLevel);
```

**Step 3: Run existing tests to verify no regression**

Run: `python run_dta_tests.py`
Expected: 156/156 PASS

**Step 4: Commit**

```bash
git add metasprint-dta.html
git commit -m "feat(dta): add crosshairs plot (Cochrane DTA Fig 10.3)"
```

---

### Task 2: L'Abbe Plot (DTA Adaptation)

In DTA, the L'Abbe plot shows each study's sensitivity (y-axis) vs specificity (x-axis) — revealing the diagnostic accuracy landscape. High-accuracy tests cluster in the top-right corner.

**Files:**
- Modify: `metasprint-dta.html` — add `renderLabbePlot()`, wire into `renderAdvancedDTA()` at `advLabbeContainer`

**Step 1: Add `renderLabbePlot(result, confLevel)` function**

Insert adjacent to `renderCrosshairsPlot`. The function:

```javascript
function renderLabbePlot(result, confLevel) {
  const el = document.getElementById('advLabbeContainer');
  if (!el || !result || !result.studyData) return;
  const studies = result.studyData;
  const W = 460, H = 420, pad = { top: 30, right: 30, bottom: 50, left: 60 };
  const plotW = W - pad.left - pad.right, plotH = H - pad.top - pad.bottom;
  const sx = x => pad.left + x * plotW;  // x = specificity
  const sy = y => pad.top + (1 - y) * plotH; // y = sensitivity

  let svg = `<svg viewBox="0 0 ${W} ${H}" style="max-width:480px;font-family:system-ui,sans-serif">`;
  // Frame + grid
  svg += `<rect x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="none" stroke="var(--border)" stroke-width="0.5"/>`;
  for (let v = 0; v <= 1; v += 0.2) {
    svg += `<line x1="${sx(v)}" y1="${pad.top}" x2="${sx(v)}" y2="${pad.top + plotH}" stroke="var(--border)" stroke-width="0.3" stroke-dasharray="3,3"/>`;
    svg += `<line x1="${pad.left}" y1="${sy(v)}" x2="${pad.left + plotW}" y2="${sy(v)}" stroke="var(--border)" stroke-width="0.3" stroke-dasharray="3,3"/>`;
    svg += `<text x="${sx(v)}" y="${pad.top + plotH + 16}" text-anchor="middle" font-size="10" fill="var(--text-muted)">${v.toFixed(1)}</text>`;
    svg += `<text x="${pad.left - 8}" y="${sy(v) + 4}" text-anchor="end" font-size="10" fill="var(--text-muted)">${v.toFixed(1)}</text>`;
  }
  svg += `<text x="${W / 2}" y="${H - 4}" text-anchor="middle" font-size="12" fill="var(--text)">Specificity</text>`;
  svg += `<text x="14" y="${H / 2}" text-anchor="middle" font-size="12" fill="var(--text)" transform="rotate(-90,14,${H / 2})">Sensitivity</text>`;

  // Study bubbles (sized by sample)
  studies.forEach(s => {
    const r = Math.max(4, Math.min(12, 3 + Math.sqrt(s.n || 50) / 3));
    svg += `<circle cx="${sx(s.spec)}" cy="${sy(s.sens)}" r="${r}" fill="var(--primary)" opacity="0.6" stroke="var(--primary)" stroke-width="1"/>`;
  });
  // Summary diamond
  if (result.pooledSens != null && result.pooledSpec != null) {
    svg += `<rect x="${sx(result.pooledSpec) - 7}" y="${sy(result.pooledSens) - 7}" width="14" height="14" fill="var(--danger)" transform="rotate(45,${sx(result.pooledSpec)},${sy(result.pooledSens)})" opacity="0.9"/>`;
  }
  // Iso-DOR curves (DOR = 5, 20, 100)
  [5, 20, 100].forEach((dor, idx) => {
    const pts = [];
    for (let sp = 0.01; sp <= 0.99; sp += 0.01) {
      const se = (dor * sp) / (1 - sp + dor * sp); // from DOR = se*sp/((1-se)*(1-sp))
      if (se >= 0 && se <= 1) pts.push(`${sx(sp).toFixed(1)},${sy(se).toFixed(1)}`);
    }
    if (pts.length > 2) {
      svg += `<polyline points="${pts.join(' ')}" fill="none" stroke="var(--text-muted)" stroke-width="0.7" stroke-dasharray="${idx === 1 ? '0' : '4,3'}" opacity="0.5"/>`;
      // Label
      const midPt = pts[Math.floor(pts.length * 0.7)].split(',');
      svg += `<text x="${midPt[0]}" y="${parseFloat(midPt[1]) - 5}" font-size="9" fill="var(--text-muted)">DOR=${dor}</text>`;
    }
  });
  svg += `</svg>`;
  el.innerHTML = `<h4 style="margin-bottom:8px">L'Abb${'e'} Plot (Sensitivity vs Specificity)</h4>` + svg +
    '<p style="font-size:0.78rem;color:var(--text-muted);margin-top:4px">Dashed curves = iso-DOR lines. Studies above/right = better accuracy.</p>';
}
```

**Step 2: Wire into `renderAdvancedDTA()`**

```javascript
renderLabbePlot(result, confLevel);
```

**Step 3: Run tests**

Run: `python run_dta_tests.py`
Expected: 156/156 PASS

**Step 4: Commit**

```bash
git add metasprint-dta.html
git commit -m "feat(dta): add L'Abbe plot with iso-DOR curves"
```

---

### Task 3: Galbraith (Radial) Plot for DOR

The Galbraith plot shows standardized log(DOR) vs precision (1/SE). Points far from the regression band are heterogeneity outliers. Standard DTA visualization per Deeks et al. 2005.

**Files:**
- Modify: `metasprint-dta.html` — add `renderGalbraithPlot()`, wire into `renderAdvancedDTA()` at `advGalbraithContainer`

**Step 1: Add `renderGalbraithPlot(result)` function**

```javascript
function renderGalbraithPlot(result) {
  const el = document.getElementById('advGalbraithContainer');
  if (!el || !result || !result.studyData) return;
  const studies = result.studyData;
  const k = studies.length;
  if (k < 3) { el.innerHTML = '<p style="color:var(--text-muted)">Need >= 3 studies for Galbraith plot</p>'; return; }

  // Each study: x = 1/SE(logDOR), y = logDOR/SE(logDOR)
  const pts = studies.map(s => {
    const lnDOR = Math.log(Math.max(0.01, (s.sens * s.spec) / (Math.max(0.001, (1 - s.sens) * (1 - s.spec)))));
    // SE of logDOR = sqrt(1/tp + 1/fp + 1/fn + 1/tn) with CC
    const cc = (s.tp === 0 || s.fp === 0 || s.fn === 0 || s.tn === 0) ? 0.5 : 0;
    const se = Math.sqrt(1 / (s.tp + cc) + 1 / (s.fp + cc) + 1 / (s.fn + cc) + 1 / (s.tn + cc));
    return { x: 1 / se, y: lnDOR / se, label: s.authorYear || '', se, lnDOR };
  }).filter(p => isFinite(p.x) && isFinite(p.y));
  if (pts.length < 3) { el.innerHTML = '<p style="color:var(--text-muted)">Insufficient data</p>'; return; }

  const xMax = Math.max(...pts.map(p => p.x)) * 1.15;
  const yMin = Math.min(...pts.map(p => p.y)) - 0.5;
  const yMax = Math.max(...pts.map(p => p.y)) + 0.5;

  const W = 500, H = 380, pad = { top: 30, right: 30, bottom: 50, left: 60 };
  const plotW = W - pad.left - pad.right, plotH = H - pad.top - pad.bottom;
  const sx = x => pad.left + (x / xMax) * plotW;
  const sy = y => pad.top + ((yMax - y) / (yMax - yMin)) * plotH;

  // Pooled logDOR (from FE)
  const wFE = pts.map(p => p.x * p.x); // w = 1/se^2 = (1/se)^2
  const sumW = wFE.reduce((a, b) => a + b, 0);
  const pooledLnDOR = pts.reduce((s, p, i) => s + wFE[i] * p.lnDOR, 0) / sumW;

  let svg = `<svg viewBox="0 0 ${W} ${H}" style="max-width:520px;font-family:system-ui,sans-serif">`;
  svg += `<rect x="${pad.left}" y="${pad.top}" width="${plotW}" height="${plotH}" fill="none" stroke="var(--border)" stroke-width="0.5"/>`;

  // Y-axis ticks
  const yStep = Math.max(1, Math.ceil((yMax - yMin) / 6));
  for (let v = Math.ceil(yMin); v <= yMax; v += yStep) {
    svg += `<line x1="${pad.left}" y1="${sy(v)}" x2="${pad.left + plotW}" y2="${sy(v)}" stroke="var(--border)" stroke-width="0.3" stroke-dasharray="3,3"/>`;
    svg += `<text x="${pad.left - 8}" y="${sy(v) + 4}" text-anchor="end" font-size="10" fill="var(--text-muted)">${v.toFixed(0)}</text>`;
  }
  // X-axis ticks
  const xStep = Math.max(0.5, Math.ceil(xMax / 5 * 2) / 2);
  for (let v = 0; v <= xMax; v += xStep) {
    svg += `<text x="${sx(v)}" y="${pad.top + plotH + 16}" text-anchor="middle" font-size="10" fill="var(--text-muted)">${v.toFixed(1)}</text>`;
  }
  svg += `<text x="${W / 2}" y="${H - 4}" text-anchor="middle" font-size="12" fill="var(--text)">Precision (1/SE)</text>`;
  svg += `<text x="14" y="${H / 2}" text-anchor="middle" font-size="12" fill="var(--text)" transform="rotate(-90,14,${H / 2})">Standardized log(DOR)</text>`;

  // Regression line through origin with slope = pooled lnDOR
  svg += `<line x1="${sx(0)}" y1="${sy(0)}" x2="${sx(xMax)}" y2="${sy(pooledLnDOR * xMax)}" stroke="var(--danger)" stroke-width="1.5"/>`;
  // +/- 1.96 bands (95% CI)
  svg += `<line x1="${sx(0)}" y1="${sy(1.96)}" x2="${sx(xMax)}" y2="${sy(pooledLnDOR * xMax + 1.96)}" stroke="var(--danger)" stroke-width="0.7" stroke-dasharray="4,3" opacity="0.6"/>`;
  svg += `<line x1="${sx(0)}" y1="${sy(-1.96)}" x2="${sx(xMax)}" y2="${sy(pooledLnDOR * xMax - 1.96)}" stroke="var(--danger)" stroke-width="0.7" stroke-dasharray="4,3" opacity="0.6"/>`;

  // Study points
  pts.forEach(p => {
    svg += `<circle cx="${sx(p.x)}" cy="${sy(p.y)}" r="4" fill="var(--primary)" opacity="0.7"/>`;
  });
  svg += `</svg>`;
  el.innerHTML = '<h4 style="margin-bottom:8px">Galbraith (Radial) Plot — log(DOR)</h4>' + svg +
    '<p style="font-size:0.78rem;color:var(--text-muted);margin-top:4px">Points outside dashed bands (z = +/-1.96) are potential heterogeneity outliers. Solid line = pooled log(DOR).</p>';
}
```

**Step 2: Wire into `renderAdvancedDTA()`**

```javascript
renderGalbraithPlot(result);
```

**Step 3: Run tests, commit**

```bash
python run_dta_tests.py  # expect 156/156
git add metasprint-dta.html
git commit -m "feat(dta): add Galbraith (radial) plot for log(DOR)"
```

---

### Task 4: Fagan Nomogram SVG Visualization

Upgrade the Fagan nomogram from text table to the classic three-vertical-line SVG (pre-test probability | likelihood ratio | post-test probability). This is the #1 clinical utility visualization in DTA.

**Files:**
- Modify: `metasprint-dta.html` — replace the table output in `computeFagan()` with SVG nomogram

**Step 1: Replace `computeFagan()` body (line 9143-9172)**

The new function renders an SVG with three vertical log-scale axes connected by lines:

```javascript
function computeFagan() {
  const pretestInput = document.getElementById('faganPretest');
  const resultDiv = document.getElementById('faganResult');
  if (!pretestInput || !resultDiv) return;
  const pretest = parseFloat(pretestInput.value) / 100;
  if (!isFinite(pretest) || pretest <= 0 || pretest >= 1) {
    resultDiv.innerHTML = '<span style="color:var(--danger)">Enter a valid pre-test probability (1-99%)</span>';
    return;
  }
  const plrEl = document.querySelector('#summaryCards [data-stat="plr"]');
  const nlrEl = document.querySelector('#summaryCards [data-stat="nlr"]');
  const plr = plrEl ? parseFloat(plrEl.textContent) : null;
  const nlr = nlrEl ? parseFloat(nlrEl.textContent) : null;
  if (!isFinite(plr) || !isFinite(nlr)) {
    resultDiv.innerHTML = '<span style="color:var(--danger)">Run analysis first to compute pooled likelihood ratios</span>';
    return;
  }
  const pretestOdds = pretest / (1 - pretest);
  const posttestPos = (pretestOdds * plr) / (1 + pretestOdds * plr);
  const posttestNeg = (pretestOdds * nlr) / (1 + pretestOdds * nlr);

  // SVG Nomogram — 3 vertical axes
  const W = 360, H = 340, xLeft = 60, xMid = 180, xRight = 300;
  const yTop = 30, yBot = 310;
  const probToY = p => yTop + (yBot - yTop) * (1 - (Math.log(p / (1 - p)) - Math.log(0.01 / 0.99)) / (Math.log(0.99 / 0.01) - Math.log(0.01 / 0.99)));
  const lrToY = lr => {
    const logLR = Math.log10(Math.max(0.01, Math.min(100, lr)));
    return yTop + (yBot - yTop) * (1 - (logLR - Math.log10(0.01)) / (Math.log10(100) - Math.log10(0.01)));
  };
  let svg = `<svg viewBox="0 0 ${W} ${H}" style="max-width:380px;font-family:system-ui,sans-serif">`;
  // Three vertical axes
  [xLeft, xMid, xRight].forEach(x => {
    svg += `<line x1="${x}" y1="${yTop}" x2="${x}" y2="${yBot}" stroke="var(--border)" stroke-width="1"/>`;
  });
  // Axis labels
  svg += `<text x="${xLeft}" y="${yTop - 10}" text-anchor="middle" font-size="10" font-weight="600" fill="var(--text)">Pre-test</text>`;
  svg += `<text x="${xMid}" y="${yTop - 10}" text-anchor="middle" font-size="10" font-weight="600" fill="var(--text)">LR</text>`;
  svg += `<text x="${xRight}" y="${yTop - 10}" text-anchor="middle" font-size="10" font-weight="600" fill="var(--text)">Post-test</text>`;
  // Probability ticks (both sides)
  [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 0.9, 0.95, 0.99].forEach(p => {
    const y = probToY(p);
    [xLeft, xRight].forEach(x => {
      svg += `<line x1="${x - 4}" y1="${y}" x2="${x + 4}" y2="${y}" stroke="var(--text-muted)" stroke-width="0.7"/>`;
      svg += `<text x="${x === xLeft ? x - 8 : x + 8}" y="${y + 3}" text-anchor="${x === xLeft ? 'end' : 'start'}" font-size="8" fill="var(--text-muted)">${(p * 100).toFixed(p < 0.1 ? 0 : 0)}%</text>`;
    });
  });
  // LR ticks (center)
  [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100].forEach(lr => {
    const y = lrToY(lr);
    svg += `<line x1="${xMid - 4}" y1="${y}" x2="${xMid + 4}" y2="${y}" stroke="var(--text-muted)" stroke-width="0.7"/>`;
    svg += `<text x="${xMid + 8}" y="${y + 3}" font-size="8" fill="var(--text-muted)">${lr}</text>`;
  });

  // Lines: pretest → PLR → post-test(+) in red
  const yPre = probToY(pretest), yPLR = lrToY(plr), yPostPos = probToY(posttestPos);
  svg += `<line x1="${xLeft}" y1="${yPre}" x2="${xMid}" y2="${yPLR}" stroke="var(--danger)" stroke-width="1.5"/>`;
  svg += `<line x1="${xMid}" y1="${yPLR}" x2="${xRight}" y2="${yPostPos}" stroke="var(--danger)" stroke-width="1.5"/>`;
  // Lines: pretest → NLR → post-test(-) in green
  const yNLR = lrToY(nlr), yPostNeg = probToY(posttestNeg);
  svg += `<line x1="${xLeft}" y1="${yPre}" x2="${xMid}" y2="${yNLR}" stroke="var(--success)" stroke-width="1.5"/>`;
  svg += `<line x1="${xMid}" y1="${yNLR}" x2="${xRight}" y2="${yPostNeg}" stroke="var(--success)" stroke-width="1.5"/>`;
  // Dots at endpoints
  svg += `<circle cx="${xLeft}" cy="${yPre}" r="4" fill="var(--primary)"/>`;
  svg += `<circle cx="${xRight}" cy="${yPostPos}" r="4" fill="var(--danger)"/>`;
  svg += `<circle cx="${xRight}" cy="${yPostNeg}" r="4" fill="var(--success)"/>`;
  svg += `</svg>`;

  // Text summary below
  let html = svg;
  html += '<table style="font-size:0.82rem;border-collapse:collapse;margin-top:8px">';
  html += '<tr><td style="padding:2px 8px">Pre-test probability</td><td style="font-weight:600">' + (pretest * 100).toFixed(1) + '%</td></tr>';
  html += '<tr><td style="padding:2px 8px">PLR</td><td style="font-weight:600">' + plr.toFixed(2) + '</td></tr>';
  html += '<tr><td style="padding:2px 8px;color:var(--danger)">Post-test probability (test +)</td><td style="font-weight:600;color:var(--danger)">' + (posttestPos * 100).toFixed(1) + '%</td></tr>';
  html += '<tr><td style="padding:2px 8px">NLR</td><td style="font-weight:600">' + nlr.toFixed(3) + '</td></tr>';
  html += '<tr><td style="padding:2px 8px;color:var(--success)">Post-test probability (test -)</td><td style="font-weight:600;color:var(--success)">' + (posttestNeg * 100).toFixed(1) + '%</td></tr>';
  html += '</table>';
  resultDiv.innerHTML = html;
}
```

**Step 2: Run tests, commit**

```bash
python run_dta_tests.py  # 156/156
git add metasprint-dta.html
git commit -m "feat(dta): upgrade Fagan nomogram to SVG three-line visualization"
```

---

## Phase 2: Sensitivity Analyses (2 tasks)

### Task 5: Rho (Correlation) Sensitivity Analysis

Tests how robust the pooled estimates are to the assumed correlation between logit(Sens) and logit(Spec). Fixes rho at values from -0.9 to 0.9, re-pools, shows stability.

**Files:**
- Modify: `metasprint-dta.html` — add `renderRhoSensitivity()`, wire into `renderAdvancedDTA()` at `advRhoSensContainer`

**Step 1: Add `renderRhoSensitivity(result, confLevel)` function**

```javascript
function renderRhoSensitivity(result, confLevel) {
  const el = document.getElementById('advRhoSensContainer');
  if (!el || !result || !result.studyData) return;
  const studies = result.studyData;
  const k = studies.length;
  if (k < 3) { el.innerHTML = '<p style="color:var(--text-muted)">Need >= 3 studies for rho sensitivity</p>'; return; }

  const alpha = 1 - (confLevel ?? 0.95);
  const rhoValues = [-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9];
  const rows = [];
  for (const rhoFixed of rhoValues) {
    // Re-run bivariate with forced rho
    const r = improvedBivariatePool(studies, confLevel);
    if (!r) continue;
    // The bivariate model estimates rho empirically. For sensitivity, we
    // use the empirical point estimates (mu1, mu2) but adjust the DOR CI
    // based on the fixed rho value.
    const seMu1 = r.seMu1, seMu2 = r.seMu2;
    const covFixed = rhoFixed * seMu1 * seMu2;
    const seDOR = Math.sqrt(seMu1 ** 2 + seMu2 ** 2 + 2 * covFixed);
    const critVal = r.critValue;
    const dorCI = [Math.exp(r.mu1 + r.mu2 - critVal * seDOR), Math.exp(r.mu1 + r.mu2 + critVal * seDOR)];
    rows.push({
      rho: rhoFixed,
      sens: r.pooledSens,
      spec: r.pooledSpec,
      dor: r.dor,
      dorLo: dorCI[0],
      dorHi: dorCI[1],
      isEstimated: Math.abs(rhoFixed - (r.rho ?? 0)) < 0.05
    });
  }
  if (rows.length === 0) { el.innerHTML = ''; return; }

  let html = '<h4 style="margin-bottom:8px">Correlation (rho) Sensitivity Analysis</h4>';
  html += '<p style="font-size:0.78rem;color:var(--text-muted);margin-bottom:6px">Shows how the DOR confidence interval changes under different assumed correlations between logit(Sens) and logit(Spec). Estimated rho is highlighted.</p>';
  html += '<table style="width:100%;font-size:0.8rem;border-collapse:collapse"><thead><tr style="border-bottom:2px solid var(--border)">';
  html += '<th style="padding:3px 6px">rho</th><th>DOR</th><th>95% CI</th><th>CI Width</th></tr></thead><tbody>';
  rows.forEach(r => {
    const bg = r.isEstimated ? 'background:rgba(var(--primary-rgb,59,130,246),0.1)' : '';
    const mark = r.isEstimated ? ' *' : '';
    html += `<tr style="border-bottom:1px solid var(--border);${bg}">`;
    html += `<td style="padding:3px 6px;text-align:center">${r.rho.toFixed(1)}${mark}</td>`;
    html += `<td style="text-align:center">${r.dor.toFixed(2)}</td>`;
    html += `<td style="text-align:center">[${r.dorLo.toFixed(2)}, ${r.dorHi.toFixed(2)}]</td>`;
    html += `<td style="text-align:center">${(r.dorHi - r.dorLo).toFixed(2)}</td></tr>`;
  });
  html += '</tbody></table>';
  html += '<p style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">* = estimated rho from data. Point estimates (Sens/Spec/DOR) are invariant; only CI width changes.</p>';
  el.innerHTML = html;
}
```

**Step 2: Wire + test + commit**

```bash
python run_dta_tests.py  # 156/156
git add metasprint-dta.html
git commit -m "feat(dta): add rho sensitivity analysis for DOR CI robustness"
```

---

### Task 6: Bootstrap Confidence Intervals

Non-parametric bootstrap: resample k studies with replacement B=2000 times, refit bivariate model, report percentile CIs. Uses seeded PRNG (xoshiro128**) for determinism.

**Files:**
- Modify: `metasprint-dta.html` — add `renderBootstrapCI()`, wire into `renderAdvancedDTA()` at `advBootstrapContainer`

**Step 1: Add `renderBootstrapCI(result, confLevel)` function**

This function MUST use the existing seeded PRNG (`xoshiro128ss` or similar) already in the app for determinism. Check for existing PRNG first.

```javascript
function renderBootstrapCI(result, confLevel) {
  const el = document.getElementById('advBootstrapContainer');
  if (!el || !result || !result.studyData) return;
  const studies = result.studyData;
  const k = studies.length;
  if (k < 4) { el.innerHTML = '<p style="color:var(--text-muted)">Need >= 4 studies for bootstrap</p>'; return; }

  const alpha = 1 - (confLevel ?? 0.95);
  const B = 2000;
  // Seeded PRNG for determinism
  let seed = 42;
  function nextRand() {
    seed = (seed * 1664525 + 1013904223) & 0x7fffffff;
    return seed / 0x7fffffff;
  }

  const bootSens = [], bootSpec = [], bootDOR = [];
  for (let b = 0; b < B; b++) {
    // Resample with replacement
    const sample = [];
    for (let i = 0; i < k; i++) {
      sample.push(studies[Math.floor(nextRand() * k)]);
    }
    const r = improvedBivariatePool(sample, confLevel);
    if (r && isFinite(r.pooledSens) && isFinite(r.pooledSpec)) {
      bootSens.push(r.pooledSens);
      bootSpec.push(r.pooledSpec);
      bootDOR.push(r.dor);
    }
  }
  if (bootSens.length < B * 0.5) { el.innerHTML = '<p style="color:var(--warning)">Too many bootstrap failures</p>'; return; }

  bootSens.sort((a, b) => a - b);
  bootSpec.sort((a, b) => a - b);
  bootDOR.sort((a, b) => a - b);
  const lo = Math.floor(bootSens.length * alpha / 2);
  const hi = Math.floor(bootSens.length * (1 - alpha / 2));
  const pct = (arr, idx) => arr[Math.min(idx, arr.length - 1)];

  let html = '<h4 style="margin-bottom:8px">Bootstrap CIs (B=' + bootSens.length + ', seed=42)</h4>';
  html += '<table style="font-size:0.82rem;border-collapse:collapse"><thead><tr style="border-bottom:2px solid var(--border)">';
  html += '<th style="padding:3px 8px">Parameter</th><th>Model CI</th><th>Bootstrap Percentile CI</th></tr></thead><tbody>';
  const confPct = Math.round((confLevel ?? 0.95) * 100);
  html += '<tr style="border-bottom:1px solid var(--border)"><td style="padding:3px 8px">Sensitivity</td>';
  html += '<td style="text-align:center">[' + (result.sensCI[0] * 100).toFixed(1) + ', ' + (result.sensCI[1] * 100).toFixed(1) + ']</td>';
  html += '<td style="text-align:center">[' + (pct(bootSens, lo) * 100).toFixed(1) + ', ' + (pct(bootSens, hi) * 100).toFixed(1) + ']</td></tr>';
  html += '<tr style="border-bottom:1px solid var(--border)"><td style="padding:3px 8px">Specificity</td>';
  html += '<td style="text-align:center">[' + (result.specCI[0] * 100).toFixed(1) + ', ' + (result.specCI[1] * 100).toFixed(1) + ']</td>';
  html += '<td style="text-align:center">[' + (pct(bootSpec, lo) * 100).toFixed(1) + ', ' + (pct(bootSpec, hi) * 100).toFixed(1) + ']</td></tr>';
  html += '<tr style="border-bottom:1px solid var(--border)"><td style="padding:3px 8px">DOR</td>';
  html += '<td style="text-align:center">[' + result.dorCI[0].toFixed(2) + ', ' + result.dorCI[1].toFixed(2) + ']</td>';
  html += '<td style="text-align:center">[' + pct(bootDOR, lo).toFixed(2) + ', ' + pct(bootDOR, hi).toFixed(2) + ']</td></tr>';
  html += '</tbody></table>';
  html += '<p style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">Deterministic seed ensures identical results on re-run. Large discrepancy suggests model assumptions may not hold.</p>';
  el.innerHTML = html;
}
```

**Step 2: Wire + test + commit**

```bash
python run_dta_tests.py  # 156/156
git add metasprint-dta.html
git commit -m "feat(dta): add bootstrap percentile CIs (B=2000, seed=42)"
```

---

## Phase 3: Meta-Regression (1 task)

### Task 7: DTA Meta-Regression

Univariate random-effects meta-regression of log(DOR) on a study-level covariate (e.g., threshold value, year, index test type). Uses DL estimator with moment-based tau2 adjustment for the covariate.

**Files:**
- Modify: `metasprint-dta.html` — add `runDTAMetaRegression()`, wire into `advMetaRegressionContainer` in `renderAdvancedDTA()`

**Step 1: Add `runDTAMetaRegression(result, confLevel)` function**

```javascript
function runDTAMetaRegression(result, confLevel) {
  const el = document.getElementById('advMetaRegressionContainer');
  if (!el || !result || !result.studyData) return;
  const studies = result.studyData;
  const k = studies.length;
  if (k < 5) { el.innerHTML = '<p style="color:var(--text-muted)">Need >= 5 studies for meta-regression</p>'; return; }

  // Find numeric covariate: use threshold field, or year from authorYear
  let covName = '', covValues = [];
  // Try threshold
  const thresholds = studies.map(s => parseFloat(s.threshold));
  if (thresholds.filter(v => isFinite(v)).length >= k * 0.8) {
    covName = 'Threshold';
    covValues = thresholds.map(v => isFinite(v) ? v : null);
  } else {
    // Fall back to year
    const years = studies.map(s => {
      const m = (s.authorYear || '').match(/(\d{4})/);
      return m ? parseInt(m[1]) : null;
    });
    if (years.filter(v => v !== null).length >= k * 0.8) {
      covName = 'Publication Year';
      covValues = years;
    }
  }
  if (!covName || covValues.filter(v => v !== null).length < 4) {
    el.innerHTML = '<h4 style="margin-bottom:8px">Meta-Regression</h4>' +
      '<p style="font-size:0.82rem;color:var(--text-muted)">No numeric covariate detected. Add a "threshold" column to your extraction table, or ensure authorYear includes publication years.</p>';
    return;
  }

  // Prepare: logDOR and SE(logDOR) per study
  const data = [];
  for (let i = 0; i < k; i++) {
    if (covValues[i] === null) continue;
    const s = studies[i];
    const cc = (s.tp === 0 || s.fp === 0 || s.fn === 0 || s.tn === 0) ? 0.5 : 0;
    const lnDOR = Math.log(Math.max(0.01, ((s.tp + cc) * (s.tn + cc)) / ((s.fp + cc) * (s.fn + cc))));
    const seLnDOR = Math.sqrt(1 / (s.tp + cc) + 1 / (s.fp + cc) + 1 / (s.fn + cc) + 1 / (s.tn + cc));
    data.push({ y: lnDOR, se: seLnDOR, x: covValues[i], label: s.authorYear || '' });
  }
  if (data.length < 4) { el.innerHTML = '<p style="color:var(--text-muted)">Insufficient data</p>'; return; }

  // Weighted least squares (FE first)
  const n = data.length;
  const w = data.map(d => 1 / (d.se * d.se));
  const sumW = w.reduce((a, b) => a + b, 0);
  const sumWX = data.reduce((s, d, i) => s + w[i] * d.x, 0);
  const sumWY = data.reduce((s, d, i) => s + w[i] * d.y, 0);
  const sumWXX = data.reduce((s, d, i) => s + w[i] * d.x * d.x, 0);
  const sumWXY = data.reduce((s, d, i) => s + w[i] * d.x * d.y, 0);
  const det = sumW * sumWXX - sumWX * sumWX;
  if (Math.abs(det) < 1e-10) { el.innerHTML = '<p style="color:var(--text-muted)">Singular design matrix</p>'; return; }
  const beta0 = (sumWXX * sumWY - sumWX * sumWXY) / det;
  const beta1 = (sumW * sumWXY - sumWX * sumWY) / det;
  const seBeta1 = Math.sqrt(sumW / det);

  // Q_resid for tau2 estimation (method of moments)
  const Qresid = data.reduce((s, d, i) => s + w[i] * Math.pow(d.y - beta0 - beta1 * d.x, 2), 0);
  const dfResid = n - 2;
  const C = sumW - (sumWXX * sumW - sumWX * sumWX) > 0 ? sumW - (sumW * sumWXX - sumWX * sumWX) / sumW : sumW;
  const tau2 = Math.max(0, (Qresid - dfResid) / C);

  // RE regression weights
  const wRE = data.map(d => 1 / (d.se * d.se + tau2));
  const sumWRE = wRE.reduce((a, b) => a + b, 0);
  const sumWX_RE = data.reduce((s, d, i) => s + wRE[i] * d.x, 0);
  const sumWY_RE = data.reduce((s, d, i) => s + wRE[i] * d.y, 0);
  const sumWXX_RE = data.reduce((s, d, i) => s + wRE[i] * d.x * d.x, 0);
  const sumWXY_RE = data.reduce((s, d, i) => s + wRE[i] * d.x * d.y, 0);
  const detRE = sumWRE * sumWXX_RE - sumWX_RE * sumWX_RE;
  const b0RE = (sumWXX_RE * sumWY_RE - sumWX_RE * sumWXY_RE) / detRE;
  const b1RE = (sumWRE * sumWXY_RE - sumWX_RE * sumWY_RE) / detRE;
  const seB1RE = Math.sqrt(sumWRE / detRE);
  const alpha = 1 - (confLevel ?? 0.95);
  const critVal = n >= 30 ? normalQuantile(1 - alpha / 2) : tQuantile(1 - alpha / 2, Math.max(1, n - 2));
  const tStat = b1RE / seB1RE;
  // p-value from t-distribution (two-sided)
  const pValue = 2 * (1 - _tCDF(Math.abs(tStat), Math.max(1, n - 2)));

  // Render
  let html = '<h4 style="margin-bottom:8px">Meta-Regression: log(DOR) ~ ' + escapeHtml(covName) + '</h4>';
  html += '<table style="font-size:0.82rem;border-collapse:collapse"><tbody>';
  html += '<tr><td style="padding:2px 8px">Slope (beta1)</td><td style="font-weight:600">' + b1RE.toFixed(4) + '</td></tr>';
  html += '<tr><td style="padding:2px 8px">SE(slope)</td><td>' + seB1RE.toFixed(4) + '</td></tr>';
  html += '<tr><td style="padding:2px 8px">t-statistic</td><td>' + tStat.toFixed(3) + '</td></tr>';
  html += '<tr><td style="padding:2px 8px">p-value</td><td style="font-weight:600;color:' + (pValue < 0.05 ? 'var(--danger)' : 'var(--success)') + '">' + pValue.toFixed(4) + '</td></tr>';
  html += '<tr><td style="padding:2px 8px">tau2 (residual)</td><td>' + tau2.toFixed(4) + '</td></tr>';
  html += '<tr><td style="padding:2px 8px">R2 analogue</td><td>' + (result.heterogeneity && result.heterogeneity.tau2_sens > 0 ? ((1 - tau2 / ((result.heterogeneity.tau2_sens + result.heterogeneity.tau2_spec) / 2)) * 100).toFixed(1) + '%' : 'N/A') + '</td></tr>';
  html += '</tbody></table>';

  // Bubble scatter plot
  const xMin = Math.min(...data.map(d => d.x)), xMax = Math.max(...data.map(d => d.x));
  const yMin = Math.min(...data.map(d => d.y)) - 0.3, yMax = Math.max(...data.map(d => d.y)) + 0.3;
  const xRange = xMax - xMin || 1;
  const PW = 400, PH = 260, pp = { top: 20, right: 20, bottom: 45, left: 55 };
  const pw = PW - pp.left - pp.right, ph = PH - pp.top - pp.bottom;
  const scX = v => pp.left + ((v - xMin) / xRange) * pw;
  const scY = v => pp.top + ((yMax - v) / (yMax - yMin)) * ph;
  html += `<svg viewBox="0 0 ${PW} ${PH}" style="max-width:420px;margin-top:8px;font-family:system-ui,sans-serif">`;
  html += `<rect x="${pp.left}" y="${pp.top}" width="${pw}" height="${ph}" fill="none" stroke="var(--border)" stroke-width="0.5"/>`;
  // Regression line
  html += `<line x1="${scX(xMin)}" y1="${scY(b0RE + b1RE * xMin)}" x2="${scX(xMax)}" y2="${scY(b0RE + b1RE * xMax)}" stroke="var(--danger)" stroke-width="1.5"/>`;
  // Points
  data.forEach((d, i) => {
    const r = Math.max(3, Math.min(8, 2 + Math.sqrt(wRE[i]) * 2));
    html += `<circle cx="${scX(d.x)}" cy="${scY(d.y)}" r="${r}" fill="var(--primary)" opacity="0.6"/>`;
  });
  html += `<text x="${PW / 2}" y="${PH - 4}" text-anchor="middle" font-size="11" fill="var(--text)">${escapeHtml(covName)}</text>`;
  html += `<text x="12" y="${PH / 2}" text-anchor="middle" font-size="11" fill="var(--text)" transform="rotate(-90,12,${PH / 2})">log(DOR)</text>`;
  html += `</svg>`;

  el.innerHTML = html;
}
```

**Step 2: Wire: in `renderAdvancedDTA()`, replace the existing meta-regression stub with:**

```javascript
runDTAMetaRegression(result, confLevel);
```

**Step 3: Test + commit**

```bash
python run_dta_tests.py  # 156/156
git add metasprint-dta.html
git commit -m "feat(dta): add meta-regression of log(DOR) on study covariates"
```

---

## Phase 4: R Validation (2 tasks)

### Task 8: Create R Gold Standard Reference Values

Run the 3 test datasets through R `mada` package and store the exact outputs for comparison.

**Files:**
- Create: `r_validation/validate_dta.R`
- Modify: `dta_bivariate_reference.py` — add R-validated golden values

**Step 1: Write the R validation script**

Create `r_validation/validate_dta.R`:

```r
# MetaSprint DTA — R mada validation script
# Run: Rscript r_validation/validate_dta.R
library(mada)

# Dataset 1: BNP for Heart Failure (k=6)
bnp <- data.frame(
  TP = c(97, 88, 137, 101, 43, 263),
  FP = c(32, 26, 65, 22, 16, 66),
  FN = c(3, 12, 7, 5, 6, 37),
  TN = c(68, 74, 228, 123, 35, 234)
)
fit_bnp <- reitsma(bnp)
s_bnp <- summary(fit_bnp)
cat("=== BNP Dataset (Bivariate Reitsma) ===\n")
cat(sprintf("Sensitivity: %.6f [%.6f, %.6f]\n", s_bnp$coefficients["tsens","Estimate"],
    s_bnp$coefficients["tsens","ci.lb"], s_bnp$coefficients["tsens","ci.ub"]))
cat(sprintf("Specificity: %.6f [%.6f, %.6f]\n", s_bnp$coefficients["tfpr","Estimate"],
    s_bnp$coefficients["tfpr","ci.lb"], s_bnp$coefficients["tfpr","ci.ub"]))
cat(sprintf("AUC: %.6f\n", AUC(fit_bnp)))
cat(sprintf("DOR: %.6f\n", exp(s_bnp$coefficients["tsens","Estimate"] + s_bnp$coefficients["tfpr","Estimate"])))

# Dataset 2: hs-Troponin for AMI (k=5)
trop <- data.frame(
  TP = c(85, 117, 66, 140, 141),
  FP = c(152, 225, 120, 224, 295),
  FN = c(6, 3, 4, 10, 9),
  TN = c(475, 433, 226, 574, 555)
)
fit_trop <- reitsma(trop)
s_trop <- summary(fit_trop)
cat("\n=== hs-Troponin Dataset (Bivariate Reitsma) ===\n")
cat(sprintf("Sensitivity: %.6f [%.6f, %.6f]\n", s_trop$coefficients["tsens","Estimate"],
    s_trop$coefficients["tsens","ci.lb"], s_trop$coefficients["tsens","ci.ub"]))
cat(sprintf("Specificity: %.6f [%.6f, %.6f]\n", s_trop$coefficients["tfpr","Estimate"],
    s_trop$coefficients["tfpr","ci.lb"], s_trop$coefficients["tfpr","ci.ub"]))

# Dataset 3: CTCA for CAD (k=4, has zero cell)
ctca <- data.frame(
  TP = c(59, 163, 94, 70),
  FP = c(13, 60, 30, 7),
  FN = c(0, 3, 0, 0),
  TN = c(153, 364, 176, 57)
)
fit_ctca <- reitsma(ctca)
s_ctca <- summary(fit_ctca)
cat("\n=== CTCA Dataset (Bivariate Reitsma) ===\n")
cat(sprintf("Sensitivity: %.6f [%.6f, %.6f]\n", s_ctca$coefficients["tsens","Estimate"],
    s_ctca$coefficients["tsens","ci.lb"], s_ctca$coefficients["tsens","ci.ub"]))
cat(sprintf("Specificity: %.6f [%.6f, %.6f]\n", s_ctca$coefficients["tfpr","Estimate"],
    s_ctca$coefficients["tfpr","ci.lb"], s_ctca$coefficients["tfpr","ci.ub"]))

cat("\n=== Validation Complete ===\n")
```

**Step 2: Run R script and capture values**

Run: `Rscript r_validation/validate_dta.R`

Record the exact output values (these go into Step 3).

**Step 3: Add R reference values to `dta_bivariate_reference.py`**

Add a `R_MADA_REFERENCE` dictionary after the existing datasets:

```python
# Gold standard values from R mada::reitsma()
# Generated by r_validation/validate_dta.R
R_MADA_REFERENCE = {
    'bnp': {
        'sens': None,      # Fill from R output
        'sens_lo': None,
        'sens_hi': None,
        'spec': None,
        'spec_lo': None,
        'spec_hi': None,
        'auc': None,
    },
    'troponin': {
        'sens': None,      # Fill from R output
        'sens_lo': None,
        'sens_hi': None,
        'spec': None,
        'spec_lo': None,
        'spec_hi': None,
    },
    'ctca': {
        'sens': None,      # Fill from R output
        'sens_lo': None,
        'sens_hi': None,
        'spec': None,
        'spec_lo': None,
        'spec_hi': None,
    }
}
```

**Step 4: Commit**

```bash
git add r_validation/ dta_bivariate_reference.py
git commit -m "feat(dta): add R mada validation script and gold standard values"
```

**Important note:** The MetaSprint DTA bivariate model uses DerSimonian-Laird moment estimation, while R's `mada::reitsma()` uses REML by default. Tolerance should be 3-5% for point estimates. If discrepancies are larger, check whether the model type matches or add `method="DL"` to the R call if available.

---

### Task 9: Create Selenium Tests for Advanced Features

**Files:**
- Create: `test_dta_advanced.py`
- Modify: `run_dta_tests.py` — add new suite to runner

**Step 1: Create `test_dta_advanced.py`**

```python
"""
test_dta_advanced.py — Tests for advanced DTA features added in statistical
completeness phase. Validates: crosshairs plot, L'Abbe plot, Galbraith plot,
Fagan nomogram, rho sensitivity, bootstrap CIs, meta-regression.

Uses BNP dataset (k=6) from dta_bivariate_reference.py.
"""
import sys, os, io, time, unittest
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BNP_STUDIES = [
    {'author': 'Dao 2001', 'tp': 97, 'fp': 32, 'fn': 3, 'tn': 68},
    {'author': 'Morrison 2002', 'tp': 88, 'fp': 26, 'fn': 12, 'tn': 74},
    {'author': 'Maisel 2002', 'tp': 137, 'fp': 65, 'fn': 7, 'tn': 228},
    {'author': 'Mueller 2004', 'tp': 101, 'fp': 22, 'fn': 5, 'tn': 123},
    {'author': 'Lainchbury 2003', 'tp': 43, 'fp': 16, 'fn': 6, 'tn': 35},
    {'author': 'McCullough 2002', 'tp': 263, 'fp': 66, 'fn': 37, 'tn': 234},
]

class TestDTAAdvanced(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        opts = Options()
        opts.add_argument('--headless=new')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--window-size=1400,900')
        opts.set_capability('goog:loggingPrefs', {'browser': 'SEVERE'})
        cls.driver = webdriver.Chrome(options=opts)
        html_path = os.path.abspath('metasprint-dta.html')
        cls.driver.get('file:///' + html_path.replace('\\', '/'))
        time.sleep(3)
        # Enter studies and run analysis
        cls._enter_studies_and_analyze(cls.driver)

    @classmethod
    def _enter_studies_and_analyze(cls, driver):
        # Navigate to Extract tab
        for tab in driver.find_elements(By.CSS_SELECTOR, '.nav-tab, [data-tab]'):
            if 'Extract' in tab.text or 'extract' in tab.get_attribute('data-tab') or '':
                tab.click()
                break
        time.sleep(1)
        # Add BNP studies
        for s in BNP_STUDIES:
            driver.execute_script("""
                if (typeof addStudyRow === 'function') {
                    addStudyRow({
                        authorYear: arguments[0],
                        tp: arguments[1], fp: arguments[2],
                        fn: arguments[3], tn: arguments[4]
                    });
                }
            """, s['author'], s['tp'], s['fp'], s['fn'], s['tn'])
        time.sleep(0.5)
        # Navigate to Analyze tab
        for tab in driver.find_elements(By.CSS_SELECTOR, '.nav-tab, [data-tab]'):
            if 'Analyze' in tab.text or 'analy' in (tab.get_attribute('data-tab') or '').lower():
                tab.click()
                break
        time.sleep(1)
        # Run bivariate analysis
        driver.execute_script("""
            if (typeof document.getElementById('methodSelect') !== 'undefined') {
                var sel = document.getElementById('methodSelect');
                if (sel) sel.value = 'bivariate';
            }
        """)
        run_btn = None
        for btn in driver.find_elements(By.TAG_NAME, 'button'):
            if 'Run' in btn.text and ('Analy' in btn.text or 'Meta' in btn.text):
                run_btn = btn
                break
        if run_btn:
            run_btn.click()
        time.sleep(4)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_crosshairs_plot_rendered(self):
        """Crosshairs plot SVG should exist in advCrosshairsContainer"""
        el = self.driver.find_element(By.ID, 'advCrosshairsContainer')
        svg = el.find_elements(By.TAG_NAME, 'svg')
        self.assertTrue(len(svg) >= 1, 'Crosshairs SVG not found')
        circles = svg[0].find_elements(By.TAG_NAME, 'circle')
        self.assertGreaterEqual(len(circles), 6, f'Expected >= 6 circles, got {len(circles)}')

    def test_labbe_plot_rendered(self):
        """L'Abbe plot should have SVG with study circles and iso-DOR curves"""
        el = self.driver.find_element(By.ID, 'advLabbeContainer')
        svg = el.find_elements(By.TAG_NAME, 'svg')
        self.assertTrue(len(svg) >= 1, "L'Abbe SVG not found")
        polylines = svg[0].find_elements(By.TAG_NAME, 'polyline')
        self.assertGreaterEqual(len(polylines), 2, 'Expected iso-DOR curves')

    def test_galbraith_plot_rendered(self):
        """Galbraith plot should have SVG with regression line and points"""
        el = self.driver.find_element(By.ID, 'advGalbraithContainer')
        svg = el.find_elements(By.TAG_NAME, 'svg')
        self.assertTrue(len(svg) >= 1, 'Galbraith SVG not found')
        lines = svg[0].find_elements(By.TAG_NAME, 'line')
        self.assertGreaterEqual(len(lines), 3, 'Expected regression + CI bands')

    def test_fagan_nomogram(self):
        """Fagan should render SVG nomogram after clicking Calculate"""
        btn = None
        for b in self.driver.find_elements(By.TAG_NAME, 'button'):
            if 'Calculate' in b.text:
                try:
                    b.click()
                    btn = b
                    break
                except:
                    pass
        time.sleep(1)
        el = self.driver.find_element(By.ID, 'faganResult')
        self.assertIn('Post-test', el.text, 'Fagan output should show post-test probabilities')

    def test_rho_sensitivity_table(self):
        """Rho sensitivity should show table with 7 rho values"""
        el = self.driver.find_element(By.ID, 'advRhoSensContainer')
        self.assertIn('rho', el.text.lower() or el.get_attribute('innerHTML').lower())
        rows = el.find_elements(By.TAG_NAME, 'tr')
        self.assertGreaterEqual(len(rows), 7, f'Expected >= 7 rho rows, got {len(rows)}')

    def test_bootstrap_ci_table(self):
        """Bootstrap CIs should show Sensitivity, Specificity, DOR rows"""
        el = self.driver.find_element(By.ID, 'advBootstrapContainer')
        text = el.text
        self.assertIn('Bootstrap', text)
        self.assertIn('Sensitivity', text)
        self.assertIn('DOR', text)

    def test_no_severe_console_errors(self):
        """No SEVERE JS console errors"""
        logs = self.driver.get_log('browser')
        severe = [l for l in logs if l['level'] == 'SEVERE'
                  and 'favicon' not in l['message'].lower()]
        self.assertEqual(len(severe), 0, f'SEVERE JS errors: {severe[:3]}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
```

**Step 2: Add to `run_dta_tests.py`**

In the `SUITES` list, add:

```python
{'name': 'Advanced Features', 'module': 'test_dta_advanced', 'class': 'TestDTAAdvanced'},
```

**Step 3: Run full suite**

Run: `python run_dta_tests.py`
Expected: All suites PASS including new Advanced Features suite.

**Step 4: Commit**

```bash
git add test_dta_advanced.py run_dta_tests.py
git commit -m "test(dta): add Selenium tests for advanced visualizations and analyses"
```

---

## Phase 5: Div Balance + Final Verification (1 task)

### Task 10: Final Safety Check

**Files:**
- All modified files

**Step 1: Div balance verification**

```bash
python -c "
import re
with open('metasprint-dta.html', 'r', encoding='utf-8') as f:
    content = f.read()
script_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL)
scripts = script_pattern.findall(content)
js_open = sum(len(re.findall(r'<div[\s>]', s)) for s in scripts)
js_close = sum(len(re.findall(r'</div>', s)) for s in scripts)
html_only = script_pattern.sub('', content)
html_open = len(re.findall(r'<div[\s>]', html_only))
html_close = len(re.findall(r'</div>', html_only))
total_open = js_open + html_open
total_close = js_close + html_close
assert html_open == html_close, f'HTML div imbalance: {html_open} vs {html_close}'
print(f'PASS: {total_open}/{total_close} divs balanced ({html_open} HTML + {js_open} JS)')
"
```

Expected: `PASS: NNN/NNN divs balanced`

**Step 2: Check for `</script>` in JS**

```bash
python -c "
import re
with open('metasprint-dta.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()
in_script = False
issues = []
for i, line in enumerate(lines, 1):
    if re.search(r'<script', line, re.IGNORECASE): in_script = True
    if in_script and '</script>' in line and not re.search(r'^\s*</script>', line):
        issues.append(f'Line {i}: {line.rstrip()[:100]}')
    if re.search(r'</script>', line, re.IGNORECASE) and in_script: in_script = False
assert len(issues) == 0, f'Found </script> in JS: {issues}'
print('PASS: No </script> inside script blocks')
"
```

**Step 3: Run full test suite**

```bash
python run_dta_tests.py
```

Expected: ALL suites PASS (156 original + new advanced tests).

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore(dta): statistical completeness phase complete — all verifications pass"
```

---

## Summary

| Task | Feature | Container | Type |
|------|---------|-----------|------|
| 1 | Crosshairs plot | `advCrosshairsContainer` | SVG viz |
| 2 | L'Abbe plot | `advLabbeContainer` | SVG viz |
| 3 | Galbraith plot | `advGalbraithContainer` | SVG viz |
| 4 | Fagan nomogram SVG | `advFaganContainer` | SVG upgrade |
| 5 | Rho sensitivity | `advRhoSensContainer` | Table |
| 6 | Bootstrap CIs | `advBootstrapContainer` | Table |
| 7 | Meta-regression | `advMetaRegressionContainer` | Table + SVG |
| 8 | R gold standard | `r_validation/` | Reference data |
| 9 | Selenium tests | `test_dta_advanced.py` | Test suite |
| 10 | Final verification | — | Safety check |

**Estimated containers filled:** 7 of 12 empty advanced containers.
**Remaining (out of scope for this phase):** `advDCAContainer`, `advCEAContainer`, `advPowerContainer`, `advEquivContainer`, `advBayesianContainer`, `advCopulaContainer` — these require substantially more complex implementations (Bayesian MCMC, cost-effectiveness modeling, formal power analysis) and are candidates for a future phase.
