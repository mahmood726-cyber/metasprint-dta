// engine.mjs -- DTA bivariate core EXTRACTED VERBATIM from metasprint-dta.html
// (improvedBivariatePool + REML + profile-likelihood CI + helpers).

  const SAMPLE_SIZE_T_THRESHOLD = 30; // k threshold for t-distribution vs z-normal
  const RHO_BOUNDS = [-0.99, 0.99];   // correlation clamp range
  const CONVERGENCE_TOL = 1e-8;       // Newton-Raphson / bisection convergence
  const CONVERGENCE_TOL_COARSE = 1e-6;// profile likelihood bisection
  const BISECTION_MAX_ITER = 100;     // max iterations for bisection search
  const FIRTH_MAX_ITER = 25;          // Firth-corrected GLMM iterations
  const DENOMINATOR_GUARD = 1e-10;    // guard against division by near-zero
  const VARIANCE_FLOOR = 1e-6;        // minimum variance for Cholesky decomposition
  const VARIANCE_FLOOR_FINE = 1e-8;   // fine-grained variance floor (profile LL)

  function invLogit(x) { return 1 / (1 + Math.exp(-x)); }
  function normalQuantile(p) {
    if (p <= 0) return -Infinity;
    if (p >= 1) return Infinity;
    if (p === 0.5) return 0;
    const a = p < 0.5 ? p : 1 - p;
    const t = Math.sqrt(-2 * Math.log(a));
    const c0 = 2.515517, c1 = 0.802853, c2 = 0.010328;
    const d1 = 1.432788, d2 = 0.189269, d3 = 0.001308;
    let z = t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t);
    return p < 0.5 ? -z : z;
  }
  function lgamma(x) {
    const cof = [76.18009172947146, -86.50532032941677, 24.01409824083091,
      -1.231739572450155, 0.001208650973866179, -5.395239384953e-6];
    let y = x, tmp = x + 5.5;
    tmp -= (x + 0.5) * Math.log(tmp);
    let ser = 1.000000000190015;
    for (let j = 0; j < 6; j++) ser += cof[j] / ++y;
    return -tmp + Math.log(2.5066282746310005 * ser / x);
  }

  function betacf(a, b, x) {
    const MAXIT = 200, EPS = 3e-7;
    const qab = a + b, qap = a + 1, qam = a - 1;
    let c = 1, d = 1 - qab * x / qap;
    if (Math.abs(d) < 1e-30) d = 1e-30;
    d = 1 / d;
    let h = d;
    for (let m = 1; m <= MAXIT; m++) {
      const m2 = 2 * m;
      let aa = m * (b - m) * x / ((qam + m2) * (a + m2));
      d = 1 + aa * d; if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d;
      c = 1 + aa / c; if (Math.abs(c) < 1e-30) c = 1e-30;
      h *= d * c;
      aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
      d = 1 + aa * d; if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d;
      c = 1 + aa / c; if (Math.abs(c) < 1e-30) c = 1e-30;
      h *= d * c;
      if (Math.abs(d * c - 1) < EPS) break;
    }
    return h;
  }
  function I2ConfidenceInterval(Q, k, confLevel) {
    if (k < 2) return { I2: 0, I2_lo: 0, I2_hi: 0 };
    if (k === 2) { const I2 = Math.max(0, (Q - 1) / Q * 100); return { I2, I2_lo: null, I2_hi: null }; }
    const df = k - 1;
    const I2 = Math.max(0, (Q - df) / Q * 100);
    const alpha = 1 - (confLevel ?? 0.95);
    // Inversion of Q-test: I2 bounds from chi2 quantiles
    const Q_upper = chi2Quantile(1 - alpha / 2, df);
    const Q_lower = chi2Quantile(alpha / 2, df);
    const I2_lo = Q > Q_upper ? Math.max(0, (Q - Q_upper) / Q * 100) : 0;
    const I2_hi = Q > Q_lower ? Math.min(100, (Q - Q_lower) / Q * 100) : 0;
    return { I2, I2_lo, I2_hi };
  }
  function profileLikelihoodCI(yi, vi, tau2, mu_hat, confLevel) {
    var alpha = 1 - (confLevel ?? 0.95);
    var chi2Crit = chi2Quantile(1 - alpha, 1); // 3.84 for 95%
    var k = yi.length;
    if (k < 2) return [mu_hat, mu_hat]; // degenerate

    // Profile log-likelihood (normal marginal)
    function logLik(mu) {
      var ll = 0;
      for (var i = 0; i < k; i++) {
        var v = vi[i] + tau2;
        if (v <= 0) v = VARIANCE_FLOOR_FINE;
        ll += -0.5 * ((yi[i] - mu) * (yi[i] - mu) / v + Math.log(v));
      }
      return ll;
    }

    var ll_max = logLik(mu_hat);
    var target = ll_max - chi2Crit / 2; // -2*logLR = chi2 => logLR = -chi2/2

    // Bisection for lower bound: find mu_lo < mu_hat where logLik(mu_lo) = target
    var sePool = 1 / Math.sqrt(yi.reduce(function(s, _, i) { return s + 1 / (vi[i] + tau2); }, 0));
    var searchRange = Math.max(10, 5 * sePool);
    var lo = mu_hat - searchRange;
    var hi = mu_hat;
    for (var iter = 0; iter < 100; iter++) {
      var mid = (lo + hi) / 2;
      if (logLik(mid) > target) hi = mid;
      else lo = mid;
      if (Math.abs(hi - lo) < CONVERGENCE_TOL_COARSE) break;
    }
    var ci_lo = (lo + hi) / 2;

    // Bisection for upper bound: find mu_hi > mu_hat where logLik(mu_hi) = target
    lo = mu_hat;
    hi = mu_hat + searchRange;
    for (var iter2 = 0; iter2 < 100; iter2++) {
      var mid2 = (lo + hi) / 2;
      if (logLik(mid2) > target) lo = mid2;
      else hi = mid2;
      if (Math.abs(hi - lo) < CONVERGENCE_TOL_COARSE) break;
    }
    var ci_hi = (lo + hi) / 2;

    return [ci_lo, ci_hi];
  }

  // --- Bivariate DL pooling (matches R mada::reitsma) ---
  function improvedBivariatePool(studies, confLevel, rhoOverride) {
    confLevel = confLevel ?? 0.95;
    const n = studies.length;
    if (n < 2) return null;
    const alpha = 1 - confLevel;
    const data = studies.map(s => ({ y1: s.logitSens, y2: s.logitSpec, v1: s.varLogitSens, v2: s.varLogitSpec }));
    const w1 = data.map(d => 1 / d.v1), w2 = data.map(d => 1 / d.v2);
    const sumW1 = w1.reduce((a, b) => a + b, 0), sumW2 = w2.reduce((a, b) => a + b, 0);
    const mu1_fe = data.reduce((s, d, i) => s + d.y1 * w1[i], 0) / sumW1;
    const mu2_fe = data.reduce((s, d, i) => s + d.y2 * w2[i], 0) / sumW2;
    const Q1 = data.reduce((s, d, i) => s + w1[i] * Math.pow(d.y1 - mu1_fe, 2), 0);
    const Q2 = data.reduce((s, d, i) => s + w2[i] * Math.pow(d.y2 - mu2_fe, 2), 0);
    const C1 = sumW1 - w1.reduce((s, w) => s + w * w, 0) / sumW1;
    const C2 = sumW2 - w2.reduce((s, w) => s + w * w, 0) / sumW2;
    const tau2_1_DL = C1 > DENOMINATOR_GUARD ? Math.max(0, (Q1 - (n - 1)) / C1) : 0;
    const tau2_2_DL = C2 > DENOMINATOR_GUARD ? Math.max(0, (Q2 - (n - 1)) / C2) : 0;
    // REML estimation (Viechtbauer 2005) — more accurate than DL, Cochrane default since 2025
    const remlData1 = data.map(d => ({ yi: d.y1, vi: d.v1 }));
    const remlData2 = data.map(d => ({ yi: d.y2, vi: d.v2 }));
    const tau2_1 = n >= 3 ? estimateREML(remlData1) : tau2_1_DL;
    const tau2_2 = n >= 3 ? estimateREML(remlData2) : tau2_2_DL;
    const w1_re = data.map(d => 1 / (d.v1 + tau2_1)), w2_re = data.map(d => 1 / (d.v2 + tau2_2));
    const sumW1_re = w1_re.reduce((a, b) => a + b, 0), sumW2_re = w2_re.reduce((a, b) => a + b, 0);
    const mu1 = data.reduce((s, d, i) => s + d.y1 * w1_re[i], 0) / sumW1_re;
    const mu2 = data.reduce((s, d, i) => s + d.y2 * w2_re[i], 0) / sumW2_re;
    const seMu1 = 1 / Math.sqrt(sumW1_re), seMu2 = 1 / Math.sqrt(sumW2_re);
    const critValue = n >= SAMPLE_SIZE_T_THRESHOLD ? normalQuantile(1 - alpha / 2) : tQuantile(1 - alpha / 2, Math.max(1, n - 2));
    // Estimate rho from RE-weighted residuals (Reitsma et al. 2005)
    let rho = null;
    if (n > 2) {
      const r1 = data.map((d, i) => (d.y1 - mu1) * Math.sqrt(w1_re[i]));
      const r2 = data.map((d, i) => (d.y2 - mu2) * Math.sqrt(w2_re[i]));
      const mr1 = r1.reduce((a, b) => a + b, 0) / n, mr2 = r2.reduce((a, b) => a + b, 0) / n;
      let cov = 0, v1r = 0, v2r = 0;
      for (let i = 0; i < n; i++) { cov += (r1[i] - mr1) * (r2[i] - mr2); v1r += (r1[i] - mr1) ** 2; v2r += (r2[i] - mr2) ** 2; }
      if (v1r > 0 && v2r > 0) rho = Math.max(RHO_BOUNDS[0], Math.min(RHO_BOUNDS[1], cov / Math.sqrt(v1r * v2r)));
    }
    // Allow rho override for sensitivity analysis (B1 fix)
    if (rhoOverride != null) rho = Math.max(RHO_BOUNDS[0], Math.min(RHO_BOUNDS[1], rhoOverride));
    const I2_sens_obj = I2ConfidenceInterval(Q1, n, confLevel);
    const I2_spec_obj = I2ConfidenceInterval(Q2, n, confLevel);
    const I2_sens = I2_sens_obj.I2;
    const I2_spec = I2_spec_obj.I2;
    const pQ_sens = n > 1 ? 1 - chi2CDF(Q1, n - 1) : 1, pQ_spec = n > 1 ? 1 - chi2CDF(Q2, n - 1) : 1;
    const pooledSens = invLogit(mu1), pooledSpec = invLogit(mu2);
    const sensLR = Math.max(0.001, Math.min(0.999, pooledSens));
    const specLR = Math.max(0.001, Math.min(0.999, pooledSpec));
    // Prediction interval: mu +/- t(k-2) * sqrt(tau2 + SE2) -- Cochrane Handbook 10.10
    const piCrit = n >= 3 ? tQuantile(1 - alpha / 2, Math.max(1, n - 2)) : critValue;
    const sensPredInt = [invLogit(mu1 - piCrit * Math.sqrt(tau2_1 + seMu1 * seMu1)), invLogit(mu1 + piCrit * Math.sqrt(tau2_1 + seMu1 * seMu1))];
    const specPredInt = [invLogit(mu2 - piCrit * Math.sqrt(tau2_2 + seMu2 * seMu2)), invLogit(mu2 + piCrit * Math.sqrt(tau2_2 + seMu2 * seMu2))];
    // Profile likelihood CIs for small k (more accurate than Wald near boundaries)
    var sensCI_profile = null, specCI_profile = null;
    if (n < 10) {
      var yi_sens = data.map(function(d) { return d.y1; });
      var vi_sens = data.map(function(d) { return d.v1; });
      var yi_spec = data.map(function(d) { return d.y2; });
      var vi_spec = data.map(function(d) { return d.v2; });
      var plCI_sens = profileLikelihoodCI(yi_sens, vi_sens, tau2_1, mu1, confLevel);
      var plCI_spec = profileLikelihoodCI(yi_spec, vi_spec, tau2_2, mu2, confLevel);
      sensCI_profile = [invLogit(plCI_sens[0]), invLogit(plCI_sens[1])];
      specCI_profile = [invLogit(plCI_spec[0]), invLogit(plCI_spec[1])];
    }
    // PLR/NLR CIs via delta method on log scale
    const cov12 = (rho ?? 0) * seMu1 * seMu2;
    const seLogPLR = Math.sqrt(Math.max(0, (1 - pooledSens) ** 2 * seMu1 ** 2 + pooledSpec ** 2 * seMu2 ** 2 + 2 * (1 - pooledSens) * pooledSpec * cov12));
    const seLogNLR = Math.sqrt(Math.max(0, pooledSens ** 2 * seMu1 ** 2 + (1 - pooledSpec) ** 2 * seMu2 ** 2 + 2 * pooledSens * (1 - pooledSpec) * cov12));
    const plrVal = sensLR / (1 - specLR), nlrVal = (1 - sensLR) / specLR;
    const plrCI = [plrVal * Math.exp(-critValue * seLogPLR), plrVal * Math.exp(critValue * seLogPLR)];
    const nlrCI = [nlrVal * Math.exp(-critValue * seLogNLR), nlrVal * Math.exp(critValue * seLogNLR)];
    return {
      pooledSens, pooledSpec,
      plr: plrVal, nlr: nlrVal, plrCI, nlrCI,
      dor: (sensLR * specLR) / ((1 - sensLR) * (1 - specLR)),
      sensCI: [invLogit(mu1 - critValue * seMu1), invLogit(mu1 + critValue * seMu1)],
      specCI: [invLogit(mu2 - critValue * seMu2), invLogit(mu2 + critValue * seMu2)],
      sensPredInt, specPredInt,
      sensCI_profile, specCI_profile,
      dorCI: [Math.exp((mu1 + mu2) - critValue * Math.sqrt(Math.max(0, seMu1 ** 2 + seMu2 ** 2 + 2 * cov12))),
              Math.exp((mu1 + mu2) + critValue * Math.sqrt(Math.max(0, seMu1 ** 2 + seMu2 ** 2 + 2 * cov12)))],
      mu1, mu2, seMu1, seMu2, covMu12: cov12,
      tau2_sens: tau2_1, tau2_spec: tau2_2,
      heterogeneity: { Q_sens: Q1, Q_spec: Q2, I2_sens, I2_spec, I2_sens_CI: (I2_sens_obj.I2_lo != null ? [I2_sens_obj.I2_lo, I2_sens_obj.I2_hi] : null), I2_spec_CI: (I2_spec_obj.I2_lo != null ? [I2_spec_obj.I2_lo, I2_spec_obj.I2_hi] : null), pQ_sens, pQ_spec, tau2_sens: tau2_1, tau2_spec: tau2_2 },
      rho, k: n, critValue, ciMethod: n >= SAMPLE_SIZE_T_THRESHOLD ? 'z-normal' : 'HKSJ-t', method: n >= 3 ? 'Bivariate REML (Reitsma-type)' : 'Bivariate DL (Reitsma-type)',
      studyData: studies.map((s, i) => ({ ...s, wSens: w1_re[i], wSpec: w2_re[i], weightPctSens: (w1_re[i] / sumW1_re * 100).toFixed(1), weightPctSpec: (w2_re[i] / sumW2_re * 100).toFixed(1) }))
    };
  }
  function chi2Quantile(p, df) {
    if (df <= 0) return 0;
    const z = normalQuantile(p);
    // Wilson-Hilferty: chi2 ≈ df * (1 - 2/(9*df) + z*sqrt(2/(9*df)))^3
    const a = 1 - 2 / (9 * df);
    const b = Math.sqrt(2 / (9 * df));
    return Math.max(0, df * Math.pow(a + z * b, 3));
  }

  // --- t-distribution quantile (Hill's algorithm, two-tailed) ---
  function tQuantile(p, df) {
    if (df <= 0) return normalQuantile(p);
    if (df === 1) return Math.tan(Math.PI * (p - 0.5)); // Cauchy exact
    if (df === 2) {  // Exact formula for df=2
      const a = 2 * p - 1;
      // Guard: when p≈0 or p≈1, a*a rounds to 1 → division by zero
      const denom = 1 - a * a;
      if (denom < 1e-15) return a > 0 ? 1e15 : -1e15;
      return a * Math.sqrt(2 / denom);
    }
    if (df >= 200) return normalQuantile(p); // normal approximation
    // Hybrid: Newton-Raphson with bisection fallback for robustness
    const sign = p >= 0.5 ? 1 : -1;
    const pp = p >= 0.5 ? p : 1 - p;  // work with upper tail
    // Initial guess from normal quantile, corrected for heavy tails
    let x = normalQuantile(pp);
    // Cornish-Fisher correction for small df
    if (df < 30) {
      const g1 = 1 / (4 * df);
      x = x + (x * x * x + x) * g1;
    }
    // Newton-Raphson with clamped steps
    let converged = false;
    for (let i = 0; i < 30; i++) {
      const cdf = tCDFfn(x, df);
      const pdf = Math.pow(1 + x * x / df, -(df + 1) / 2) / (Math.sqrt(df) * betaFn(0.5, df / 2));
      if (pdf < 1e-15) break;
      const step = (cdf - pp) / pdf;
      const clampedStep = Math.abs(step) > Math.abs(x) * 0.5 + 1
        ? Math.sign(step) * (Math.abs(x) * 0.5 + 1) : step;
      x -= clampedStep;
      if (Math.abs(step) < 1e-10) { converged = true; break; }
    }
    // Bisection fallback if Newton didn't converge
    if (!converged) {
      let lo = normalQuantile(pp);
      let hi = Math.max(lo * 3, 50);  // generous upper bound
      // Ensure bracket: tCDF(hi) > pp
      while (tCDFfn(hi, df) < pp && hi < 1e6) hi *= 2;
      for (let i = 0; i < 80; i++) {
        const mid = (lo + hi) / 2;
        if (tCDFfn(mid, df) < pp) lo = mid; else hi = mid;
        if (hi - lo < 1e-10) break;
      }
      x = (lo + hi) / 2;
    }
    return sign * x;
  }

  function tCDFfn(t, df) {
    const x = df / (df + t * t);
    const p = 0.5 * regIncBeta(df / 2, 0.5, x);
    return t >= 0 ? 1 - p : p;
  }

  // Regularized incomplete beta function (continued fraction)
  function regIncBeta(a, b, x) {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    const lnBeta = lnGamma(a) + lnGamma(b) - lnGamma(a + b);
    const front = Math.exp(Math.log(x) * a + Math.log(1 - x) * b - lnBeta);
    // Lentz's continued fraction
    let f = 1e-30, c = 1e-30, d = 0;
    for (let m = 0; m <= 200; m++) {
      let num;
      if (m === 0) num = 1;
      else if (m % 2 === 0) {
        const k = m / 2;
        num = k * (b - k) * x / ((a + 2 * k - 1) * (a + 2 * k));
      } else {
        const k = (m - 1) / 2;
        num = -((a + k) * (a + b + k) * x) / ((a + 2 * k) * (a + 2 * k + 1));
      }
      d = 1 + num * d; if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d;
      c = 1 + num / c; if (Math.abs(c) < 1e-30) c = 1e-30;
      f *= c * d;
      if (Math.abs(c * d - 1) < 1e-10) break;
    }
    return front * f / a;
  }

  function lnGamma(z) {
    const c = [76.18009172947146, -86.50532032941677, 24.01409824083091,
              -1.231739572450155, 0.001208650973866179, -0.000005395239384953];
    let x = z, y = z, tmp = x + 5.5;
    tmp -= (x + 0.5) * Math.log(tmp);
    let ser = 1.000000000190015;
    for (let j = 0; j < 6; j++) ser += c[j] / ++y;
    return -tmp + Math.log(2.5066282746310005 * ser / x);
  }

  function betaFn(a, b) {
    return Math.exp(lnGamma(a) + lnGamma(b) - lnGamma(a + b));
  }

  function chi2CDF(x, df) {
    if (x <= 0 || df <= 0) return 0;
    return regIncGamma(df / 2, x / 2);
  }

  function regIncGamma(a, x) {
    if (x < 0 || a <= 0) return 0;
    if (x === 0) return 0;
    if (x < a + 1) {
      // Series expansion
      let sum = 1 / a, term = 1 / a;
      for (let n = 1; n < 200; n++) {
        term *= x / (a + n);
        sum += term;
        if (Math.abs(term) < 1e-10 * Math.abs(sum)) break;
      }
      return sum * Math.exp(-x + a * Math.log(x) - lnGamma(a));
    } else {
      // Continued fraction (Numerical Recipes, Press et al.)
      // Computes Q(a,x) = 1 - P(a,x) via Lentz's modified method
      let b = x + 1 - a;
      let c = 1e30;
      let d = 1 / b;
      let h = d;
      for (let i = 1; i <= 200; i++) {
        const an = -i * (i - a);
        b += 2;
        d = an * d + b; if (Math.abs(d) < 1e-30) d = 1e-30; d = 1 / d;
        c = b + an / c; if (Math.abs(c) < 1e-30) c = 1e-30;
        const del = c * d;
        h *= del;
        if (Math.abs(del - 1) < 1e-10) break;
      }
      return 1 - Math.exp(-x + a * Math.log(x) - lnGamma(a)) * h;
    }
  }
  function estimateREML(studyData, maxIter, tol) {
    maxIter = maxIter ?? 50;
    tol = tol ?? 1e-5;
    const k = studyData.length;
    if (k < 2) return 0;

    // Start from DL estimate
    const ws = studyData.map(d => 1 / d.vi);
    const sumW = ws.reduce((a, w) => a + w, 0);
    const muFE = ws.reduce((a, w, i) => a + w * studyData[i].yi, 0) / sumW;
    const Q = ws.reduce((a, w, i) => a + w * (studyData[i].yi - muFE) ** 2, 0);
    const C = sumW - ws.reduce((a, w) => a + w * w, 0) / sumW;
    // Guard: C=0 when all weights are equal (degenerate case); fall back to tau2=0
    let tau2 = C > 1e-15 ? Math.max(0, (Q - (k - 1)) / C) : 0;

    for (let iter = 0; iter < maxIter; iter++) {
      const w = studyData.map(d => 1 / (d.vi + tau2));
      const sW = w.reduce((a, b) => a + b, 0);
      const mu = w.reduce((s, wi, i) => s + wi * studyData[i].yi, 0) / sW;

      // REML score (Viechtbauer 2005, eq. 12; +1/sW term is the REML bias correction
      // that distinguishes REML from ML — accounts for uncertainty in estimating mu)
      const num = w.reduce((s, wi, i) =>
        s + wi * wi * ((studyData[i].yi - mu) ** 2 - studyData[i].vi), 0);
      const sW2 = w.reduce((s, wi) => s + wi * wi, 0);
      // Guard: sW2 or sW underflow to 0 when tau2 is extremely large (all weights ≈ 0)
      if (sW2 < 1e-30 || sW < 1e-30) break;

      const tau2New = Math.max(0, num / sW2 + 1 / sW);
      if (Math.abs(tau2New - tau2) < tol) { tau2 = tau2New; break; }
      tau2 = tau2New;
    }
    return tau2;
  }

export { improvedBivariatePool, estimateREML, profileLikelihoodCI, invLogit, tQuantile, normalQuantile };
