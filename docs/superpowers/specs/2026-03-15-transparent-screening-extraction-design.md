# Transparent Screening + Traceable Extraction

## Summary
Add full transparency to the OA Discovery Pipeline so every inclusion/exclusion decision and every extracted number is traceable to its source text with visual highlighting.

## 1. Screening Checklist

### Data model
Each study gets `t._screeningChecklist` populated during auto-selection:

```javascript
{
  indexTestMatch: { pass: boolean, reason: string },   // "Matched 'ultrasound'" or "No match for 'MRI'"
  notReview:      { pass: boolean, reason: string },   // "Primary study" or "Systematic review/meta-analysis"
  dataExtracted:  { pass: boolean, reason: string },   // "Sens 89%, Spec 92% from abstract" or "No extractable accuracy data"
  qualityGate:    { pass: boolean, reason: string },   // "High confidence, N=150" or "Low confidence, N=18 < 50 threshold"
  noConflict:     { pass: boolean, reason: string }    // "No sub-indication conflict" or "Excluded: non-IgA tTG"
}
```

### UI — main table
New column after "Conf": screening badge showing `"4/5"` (pass count / total).
- 5/5: green
- 3-4/5: amber
- 0-2/5: red
- Hover tooltip: lists failed criteria

### UI — detail row
Full checklist rendered as 5 rows with pass/fail icon and reason text.

### Where to populate
After the existing auto-selection logic (~line 5471-5477). The checklist captures WHY each criterion passed/failed, using the same conditions already evaluated.

## 2. Extraction Source Tracking

### Data model change
`extractDTAFromAbstract()` currently returns `{ sensitivity, specificity, ... }`. Enhanced to also return `_sources`:

```javascript
result._sources = {
  sensitivity: { value: 0.89, sourceText: "sensitivity was 89% (95% CI: 80-96%)", charStart: 142, charEnd: 183, method: 'direct' },
  specificity: { value: 0.92, sourceText: "specificity of 92%", charStart: 210, charEnd: 228, method: 'direct' },
  lrPlus:      { value: 8.5,  sourceText: "LR+ = 8.5", charStart: 305, charEnd: 315, method: 'direct' },
  // Derived values reference their sources:
  sensitivity_derived: { value: 0.89, method: 'derived_from_lr', inputs: ['lrPlus', 'lrMinus'], formula: 'Spec=(LR+-1)/(LR+-LR-), Sens=LR+*(1-Spec)' }
}
```

### Implementation
In `extractDTAFromAbstract()`, after each successful regex match, store:
- `match[0]` (full matched text)
- `match.index` (character position)
- The parsed value and normalization applied

This requires changing `text.match(pat)` calls to capture match objects with index info. Since `.match()` already provides `.index` on the first match, no regex change needed — just save the match object.

## 3. Abstract Highlighting (enhanced)

### Color coding
- **Yellow `<mark>`**: direct extraction (sens/spec/PPV/NPV/AUC found in text)
- **Blue `<mark style="background:#b3d9ff">`**: source value for a derivation (e.g., LR+ highlighted when sens was derived from LRs)
- **No highlight**: derived values not present in text

### Tooltips on highlights
Each `<mark>` gets a `title` attribute:
- Direct: `"Extracted: Sensitivity = 89% (normalized from 89)"`
- Source for derivation: `"Source for derived Sensitivity: LR+ = 8.5"`

### Derived value badges
In the provenance table, derived values get: `"89% Derived ⓘ"` where the ⓘ tooltip shows the derivation chain.

## 4. Number Tooltips in Table

Every Sens/Spec/TP/FP/FN/TN cell in the results table gets `title` showing:
- Source text snippet (up to 80 chars)
- Method: "Direct extraction" / "Back-calculated (algebraic)" / "Derived from LR+/LR-"

## 5. Evidence Chain (detail row)

New section in the detail row after the existing provenance table:

```
Evidence Chain
─────────────
Sensitivity: 89.0% ← "sensitivity was 89% (95% CI: 80-96%)" [Abstract]
Specificity: 92.0% ← "specificity of 92%" [Abstract]
PPV: 85.0% ← "PPV was 85%" [Abstract]
NPV: 94.0% ← "NPV 94% (95% CI 90-97%)" [Abstract]
TP: 34 ← Back-calculated (algebraic: sens=0.89, spec=0.92, PPV=0.85, NPV=0.94, N=150)
FP: 6 ← Back-calculated (algebraic)
FN: 4 ← Back-calculated (algebraic)
TN: 106 ← Back-calculated (algebraic)
```

## 6. Files Changed

| File | Function | Change |
|------|----------|--------|
| metasprint-dta.html | `extractDTAFromAbstract()` | Store match positions + source text in `_sources` |
| metasprint-dta.html | auto-selection (~5471) | Populate `_screeningChecklist` with reasons |
| metasprint-dta.html | `renderOAResultsTable()` | Add screening column + number tooltips |
| metasprint-dta.html | `highlightAbstractDTA()` | Color-code direct vs derived source highlighting |
| metasprint-dta.html | `toggleOADetailRow()` | Add evidence chain + screening checklist |

## 7. Not in scope
- Demographics extraction (age, sex) — separate feature
- Auto RoB/GRADE transparency — separate feature
- Full-text extraction — abstract only

## 8. Testing
- New Selenium tests: verify checklist renders, tooltips exist, highlights appear
- Regression: 74 existing OA unit tests must still pass
- Spot check: run 3 topics, verify every number in results table has tooltip with source text
