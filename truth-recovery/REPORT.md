# Truth-recovery yardstick — metasprint-dta

**Verdict: the primary REML interval recovers true Se/Sp well (conservative at
tiny k) + an HONEST NEGATIVE: the engine's own profile-likelihood CI under-covers,
so it should NOT be promoted to the primary interval.**

## Method
Wires the app's OWN `improvedBivariatePool` (engine.mjs, verbatim — REML τ², rho,
profile-likelihood CI for k<10) to the known-truth bivariate DTA DGP and measures
how often each CI covers the TRUE Se/Sp. Three intervals compared: the shipped
primary Wald-t CI; a genuine-HKSJ interval (Q/(k−1) inflation, floored); and the
engine's own profile-likelihood CI. Se=0.85, Sp=0.80, k∈{4,8}, 500 reps/cell.

## Results

### Mean coverage of true Se / Sp (k<10)
| method            | mean cov(Se) | mean cov(Sp) |
|-------------------|-------------:|-------------:|
| primary (Wald-t)  |  0.968 | 0.961 |
| genuine HKSJ      |  0.973 | 0.966 |
| **profile-LL**    |  **0.876** | **0.871** |

### Per-cell coverage of true Se
| scenario  | k | primary | HKSJ | profile-LL |
|-----------|---|--------:|-----:|-----------:|
| het_low   | 4 | 0.996 | 0.996 | 0.882 |
| het_mod   | 4 | 0.986 | 0.990 | 0.846 |
| het_high  | 8 | 0.946 | 0.952 | 0.884 |
| het_corr  | 8 | 0.942 | 0.950 | 0.886 |

## Findings (all measured)
1. **The primary CI recovers truth at/above nominal — conservative at tiny k.**
   Unlike the sibling `dta-meta-analysis-pro` (whose DL-based interval *under*-
   covered), metasprint-dta uses **REML** (larger τ²) plus the wide `t_{k-2}`
   critical value, so at k=4 it **over-covers** (0.97–1.00) and settles to
   near-nominal (0.94–0.96) by k=8. It errs on the safe side. (The `ciMethod:
   'HKSJ-t'` label is still a misnomer — like dta-pro it only swaps z→`t_{k-2}`
   with the ordinary RE SE, no HKSJ variance inflation — but here the practical
   effect is conservatism, not under-coverage.)
2. **genuine HKSJ adds nothing here.** Because the REML primary already
   covers/over-covers, the HKSJ inflation only makes it marginally more
   conservative (+0.5pp). The fix that helped dta-pro is unnecessary here — the
   right move is method-specific, which is exactly why each engine must be
   measured rather than patched by analogy.
3. **HONEST NEGATIVE — the profile-likelihood CI under-covers (0.876/0.871).** The
   engine computes a univariate profile-likelihood CI for k<10 but does not use it
   as the primary. Measured, it is **anti-conservative** — it conditions on the
   (point-estimated, downward-biased) τ² and ignores τ² uncertainty, so it is too
   narrow and misses the true Se/Sp ~12% of the time. → **do not promote the
   profile-LL CI to the primary interval** for small k; if it is surfaced, label it
   as an optimistic/lower-bound width, not a calibrated 95% CI.

## What did NOT transfer
The bivariate DTA selection DGP transferred directly (same family as dta-pro);
NPE/conformal machinery does not apply. Engine run unchanged; no dependency added.

## Reproduce
```
node truth-recovery/harness.mjs --reps 500
node --test truth-recovery/test-truth-recovery.mjs
```
