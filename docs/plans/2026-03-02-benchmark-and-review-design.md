# MetaSprint DTA: Benchmark Datasets + Post-Optimization Review

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Complete the broken benchmark dataset loader (10 real DTA datasets), then run a fresh 3-persona review to catch any issues introduced by the 20-task quality optimization.

**Architecture:** All changes to `metasprint-dta.html` (~23.2K lines). No new files. 203/203 tests currently pass, div balance 746/746.

**Tech Stack:** Vanilla JS, Selenium + Python testing, Chrome headless.

---

## Part 1: Benchmark Datasets

### Problem
The extraction tab has a `<select>` dropdown with 10 benchmark datasets, but `loadBenchmarkDataset()` is undefined. Two of the 10 are pairwise RCT datasets (BCG, Aspirin) that don't belong in a DTA app.

### Solution
1. Implement `loadBenchmarkDataset(datasetId)` with hardcoded 2x2 data for 10 DTA-appropriate datasets
2. Replace BCG (Colditz 1994) and Aspirin (Hart 1999) with actual DTA datasets
3. Each dataset: published, verifiable, diverse k and accuracy ranges

### Replacement datasets (for the 2 non-DTA entries):
- **PCT for Sepsis (k=8)**: Procalcitonin diagnostic accuracy — common in emergency medicine
- **CRP for Appendicitis (k=7)**: C-reactive protein — surgical DTA classic

---

## Part 2: 3-Persona Post-Optimization Review

Run a fresh review cycle after 20 tasks of optimization to catch:
- New bugs introduced by the +888 lines
- Interaction issues between new features
- Display/layout problems from new containers and buttons
- Statistical correctness of new functions (trim-and-fill, profile likelihood, I² CI)

### Personas:
1. **DTA Statistician** — Verify new statistical functions
2. **Publication Workflow Tester** — Test all new export buttons, CSV outputs, PNG exports
3. **Integration Tester** — Test feature interactions (e.g., RoB sensitivity + subgroup, SoF table at different prevalences, profile CI display)

### Classification:
- P0: Crash, wrong result, broken export
- P1: Missing guard, edge case, cosmetic but misleading
- P2: Style, minor polish

---

## Summary

| Part | Tasks | Focus |
|------|-------|-------|
| 1 | Benchmark datasets | 10 real DTA datasets, replace 2 RCTs |
| 2 | 3-persona review | Statistical, exports, integration |
| 3 | Fix P0/P1 issues | From review findings |
| 4 | Verify | 203+ tests pass, div balance |
