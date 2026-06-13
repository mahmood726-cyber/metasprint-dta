// ============================================================
// dgp-dta.mjs -- Known-truth DGP for DIAGNOSTIC TEST ACCURACY meta-analysis.
//
// dta-meta-analysis-pro is mada::reitsma-validated on its point outputs. That
// proves the formulas; it does NOT show whether the pooled CI actually RECOVERS
// the true sensitivity/specificity under bivariate between-study heterogeneity.
// This DGP supplies that test.
//
// Generative model (the standard bivariate logit-normal RE model the app
// assumes):
//   (uA_i, uB_i) ~ N(0, Sigma),  Sigma = [[tauA^2, rho*tauA*tauB],
//                                         [rho*tauA*tauB, tauB^2]]
//   sens_i = expit(logit(Se) + uA_i),  spec_i = expit(logit(Sp) + uB_i)
//   nDis_i, nHealthy_i ~ log-uniform;  TP ~ Bin(nDis, sens_i),
//   TN ~ Bin(nHealthy, spec_i),  FN = nDis-TP,  FP = nHealthy-TN.
//
// ESTIMAND (stated): a logit RE pool targets the MEDIAN = expit(mean logit), so
// the honest recovery targets are Se = expit(muA) and Sp = expit(muB).
//
// Seeded -> reproducible. Standalone (no deps).
// ============================================================

export const SCENARIOS = ['het_low', 'het_mod', 'het_high', 'het_corr'];

export function makeRng(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function randn(rng) {
  let u1 = rng(), u2 = rng();
  if (u1 < 1e-12) u1 = 1e-12;
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}
const expit = (x) => 1 / (1 + Math.exp(-x));
const logit = (p) => Math.log(p / (1 - p));

// heterogeneity presets: [tauA, tauB, rho]
const PRESET = {
  het_low:  [0.25, 0.25, 0.0],
  het_mod:  [0.5,  0.5,  0.0],
  het_high: [0.8,  0.8,  0.0],
  het_corr: [0.5,  0.5, -0.5],   // negative Se/Sp correlation (typical threshold effect)
};

function drawN(rng, nLo, nHi) {
  const lo = Math.log(nLo), hi = Math.log(nHi);
  return Math.max(10, Math.round(Math.exp(lo + (hi - lo) * rng())));
}
function rbinom(rng, n, p) {
  let x = 0;
  for (let i = 0; i < n; i++) if (rng() < p) x++;
  return x;
}

export function generate(SeTrue, SpTrue, k, scenario, rng,
                         { nDisLo = 20, nDisHi = 300, nHealLo = 20, nHealHi = 400 } = {}) {
  const muA = logit(SeTrue), muB = logit(SpTrue);
  const [tauA, tauB, rho] = PRESET[scenario] || PRESET.het_mod;
  const studies = [];
  for (let i = 0; i < k; i++) {
    const z1 = randn(rng), z2 = randn(rng);
    const uA = tauA * z1;
    const uB = tauB * (rho * z1 + Math.sqrt(1 - rho * rho) * z2);
    const sens = expit(muA + uA);
    const spec = expit(muB + uB);
    const nDis = drawN(rng, nDisLo, nDisHi);
    const nHeal = drawN(rng, nHealLo, nHealHi);
    const tp = rbinom(rng, nDis, sens);
    const tn = rbinom(rng, nHeal, spec);
    studies.push({ study: `s${i}`, tp, fn: nDis - tp, tn, fp: nHeal - tn });
  }
  return { studies, SeTrue, SpTrue, info: { k, tauA, tauB, rho } };
}
