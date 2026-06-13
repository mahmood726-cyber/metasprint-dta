// ============================================================
// harness.mjs -- Truth-recovery yardstick for metasprint-dta.
//
// Wires the app's OWN improvedBivariatePool (engine.mjs, verbatim) to the
// known-truth bivariate DTA DGP and measures how often each CI covers the TRUE
// Se / Sp. metasprint-dta is more advanced than dta-meta-analysis-pro (REML +
// rho + a PROFILE-LIKELIHOOD CI for k<10), so this compares THREE intervals:
//   - the shipped primary Wald-t CI (labelled "HKSJ-t" but, like dta-pro, only a
//     z->t_{k-2} swap with the ordinary RE SE -- no HKSJ variance inflation),
//   - a genuine-HKSJ interval (Q/(k-1) inflation, floored at 1),
//   - the engine's OWN profile-likelihood CI (computed for k<10 but NOT used as
//     the primary).
//
// Truth-first: every number printed comes from seeded simulation here.
// Run:  node truth-recovery/harness.mjs --reps 400
// ============================================================

import { improvedBivariatePool, invLogit, tQuantile, normalQuantile } from './engine.mjs';
import { generate, makeRng, SCENARIOS } from './dgp-dta.mjs';

const BASE_SEED = 20260613;

// Convert a 2x2 table to the engine's per-study logit inputs (0.5 cc on zeros).
function toStudy(s) {
  const hasZero = s.tp === 0 || s.fp === 0 || s.fn === 0 || s.tn === 0;
  const cc = hasZero ? 0.5 : 0;
  const tp = s.tp + cc, fp = s.fp + cc, fn = s.fn + cc, tn = s.tn + cc;
  const sens = tp / (tp + fn), spec = tn / (tn + fp);
  return { logitSens: Math.log(sens / (1 - sens)), varLogitSens: 1 / tp + 1 / fn,
           logitSpec: Math.log(spec / (1 - spec)), varLogitSpec: 1 / tn + 1 / fp };
}

// genuine-HKSJ interval on a logit axis from the same RE weights.
function hksjCI(studies2, axisKey, vKey, mu, tau2, k, crit) {
  const wRE = studies2.map(s => 1 / (s[vKey] + tau2));
  const sumWRE = wRE.reduce((a, b) => a + b, 0);
  const qRE = studies2.reduce((s, st, i) => s + wRE[i] * (st[axisKey] - mu) ** 2, 0);
  const seH = Math.sqrt(Math.max(1, qRE / (k - 1)) / sumWRE);
  return [invLogit(mu - crit * seH), invLogit(mu + crit * seH)];
}

const METHODS = ['primary (Wald-t)', 'genuine-HKSJ', 'profile-LL'];
const mean = (a) => a.reduce((x, y) => x + y, 0) / a.length;

export function runCell(SeTrue, SpTrue, k, scenario, reps, rng) {
  const acc = {};
  for (const m of METHODS) acc[m] = { covSe: 0, covSp: 0, wSe: 0, n: 0 };
  for (let r = 0; r < reps; r++) {
    const { studies } = generate(SeTrue, SpTrue, k, scenario, rng);
    const conv = studies.map(toStudy);
    let res; try { res = improvedBivariatePool(conv, 0.95); } catch { continue; }
    if (!res || !isFinite(res.pooledSens)) continue;
    const crit = res.critValue;
    const hkSe = hksjCI(conv, 'logitSens', 'varLogitSens', res.mu1, res.tau2_sens, k, crit);
    const hkSp = hksjCI(conv, 'logitSpec', 'varLogitSpec', res.mu2, res.tau2_spec, k, crit);
    const cis = {
      'primary (Wald-t)': { se: res.sensCI, sp: res.specCI },
      'genuine-HKSJ': { se: hkSe, sp: hkSp },
      'profile-LL': { se: res.sensCI_profile, sp: res.specCI_profile },
    };
    for (const m of METHODS) {
      const c = cis[m];
      if (!c.se || !c.sp || !isFinite(c.se[0]) || !isFinite(c.sp[0])) continue;
      const a = acc[m]; a.n++;
      a.wSe += c.se[1] - c.se[0];
      if (c.se[0] <= SeTrue && SeTrue <= c.se[1]) a.covSe++;
      if (c.sp[0] <= SpTrue && SpTrue <= c.sp[1]) a.covSp++;
    }
  }
  const out = {};
  for (const m of METHODS) {
    const a = acc[m];
    out[m] = a.n ? { covSe: +(a.covSe / a.n).toFixed(3), covSp: +(a.covSp / a.n).toFixed(3),
                     width: +(a.wSe / a.n).toFixed(3), n: a.n } : null;
  }
  return out;
}

export function runGrid({ reps = 400, ks = [4, 8], Se = 0.85, Sp = 0.80, scenarios = SCENARIOS } = {}) {
  const rng = makeRng(BASE_SEED);
  const grid = [];
  for (const scen of scenarios) for (const k of ks) grid.push({ scen, k, results: runCell(Se, Sp, k, scen, reps, rng) });
  return grid;
}

export function summarize(grid) {
  const out = {};
  for (const m of METHODS) {
    const cSe = [], cSp = [];
    for (const c of grid) if (c.results[m]) { cSe.push(c.results[m].covSe); cSp.push(c.results[m].covSp); }
    out[m] = { meanCovSe: cSe.length ? +mean(cSe).toFixed(3) : null, meanCovSp: cSp.length ? +mean(cSp).toFixed(3) : null };
  }
  return out;
}

const isMain = process.argv[1]?.endsWith('harness.mjs');
if (isMain) {
  const i = process.argv.indexOf('--reps');
  const reps = i >= 0 ? Number(process.argv[i + 1]) : 400;
  const t0 = Date.now();
  const grid = runGrid({ reps });
  const s = summarize(grid);
  console.log(`\n# Truth-recovery yardstick -- metasprint-dta`);
  console.log(`reps=${reps}/cell  Se=0.85 Sp=0.80  k in {4,8}  seed=${BASE_SEED}\n`);
  console.log('## Mean coverage of true Se / Sp (k<10, where the profile-LL CI is computed)\n');
  console.log('method             meanCovSe  meanCovSp');
  for (const m of METHODS) console.log(m.padEnd(18), String(s[m].meanCovSe).padStart(9), String(s[m].meanCovSp).padStart(10));
  console.log('\n## Per-cell coverage of true Se\n');
  console.log('scenario    k   primary  HKSJ   profile-LL');
  for (const c of grid) {
    const r = c.results;
    console.log(c.scen.padEnd(11), String(c.k).padStart(2),
      String(r['primary (Wald-t)'].covSe).padStart(8),
      String(r['genuine-HKSJ'].covSe).padStart(6),
      String(r['profile-LL'].covSe).padStart(8));
  }
  console.log(`\n(${((Date.now() - t0) / 1000).toFixed(1)}s)`);
}
