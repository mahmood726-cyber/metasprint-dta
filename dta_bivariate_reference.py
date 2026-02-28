"""
dta_bivariate_reference.py — Hand-calculated bivariate DL pooling for DTA meta-analysis.

Mirrors the MetaSprint DTA app's improvedBivariatePool() algorithm exactly:
  1. logit transform of sens/spec with 0.5 continuity correction
  2. Inverse-variance FE pooling → Cochran Q → DerSimonian-Laird tau²
  3. Random-effects weighted mean on logit scale
  4. invLogit back to probability scale
  5. CI via t-quantile (df=k-2) for k<30, z for k≥30
"""
import math

# ---------- transforms ----------
def logit(p):
    p = max(1e-10, min(1 - 1e-10, p))
    return math.log(p / (1 - p))

def invlogit(x):
    if x > 500: return 1.0
    if x < -500: return 0.0
    return 1.0 / (1.0 + math.exp(-x))

# ---------- distributions ----------
def _normal_cdf(x):
    """Abramowitz-Stegun approximation of Phi(x)."""
    if x < -8: return 0.0
    if x > 8: return 1.0
    t = 1.0 / (1.0 + 0.2316419 * abs(x))
    d = 0.3989422804014327
    p = d * math.exp(-x * x / 2.0) * (
        0.3193815 * t - 0.3565638 * t**2 + 1.781478 * t**3
        - 1.8212560 * t**4 + 1.3302744 * t**5
    )
    return 1.0 - p if x > 0 else p

def _normal_quantile(p):
    """Rational approximation of the normal quantile (Beasley-Springer-Moro)."""
    if p <= 0: return -8.0
    if p >= 1: return 8.0
    if abs(p - 0.5) < 1e-15: return 0.0
    r = p - 0.5
    if abs(r) <= 0.425:
        q = r
        e = 0.180625 - q * q
        num = (((((((2.5090809287301226727e+3 * e + 3.3430575583588128105e+4) * e +
              6.7265770927008700853e+4) * e + 4.5921953931549871457e+4) * e +
              1.3731693765509461125e+4) * e + 1.9715909503065514427e+3) * e +
              1.3314166764078226174e+2) * e + 3.3871328727963666080e+0)
        den = (((((((5.2264952788528545610e+3 * e + 2.8729085735721942674e+4) * e +
              3.9307895800092710610e+4) * e + 2.1213794301586595867e+4) * e +
              5.3941960214247511077e+3) * e + 6.8718700749205790830e+2) * e +
              4.2313330701600911252e+1) * e + 1.0)
        return q * num / den
    else:
        if r < 0:
            e = p
        else:
            e = 1 - p
        e = math.sqrt(-math.log(e))
        if e <= 5.0:
            e -= 1.6
            num = (((((((7.7454501427834140764e-4 * e + 2.2723844989269184187e-2) * e +
                  7.2235882297810915132e-1) * e + 1.3381091059679600000e+0) * e +
                  1.8256478520684735442e+0) * e + -1.0000000000000000000e+0 *
                  (-1.8256478520684735442e+0)) * e + 0.0) * e + 0.0)
            # Simplified: use a well-known constant set
            num = (((((((7.7454501427834140764e-4 * e + 0.0227238449892691842) * e +
                  0.7223588229781091513) * e + 1.3381091059679600000) * e) + 0.0) * e + 0.0) * e + 0.0)
        # Fallback: Newton-Raphson from a good starting point
        x = -math.log(2 * e) if r < 0 else math.log(2 * e)
        # Use inverse error function approach
        if r < 0:
            x = -math.sqrt(2) * _erfinv(1 - 2 * p)
        else:
            x = math.sqrt(2) * _erfinv(2 * p - 1)
        return x

def _erfinv(x):
    """Approximation of inverse error function."""
    sgn = 1 if x >= 0 else -1
    x = abs(x)
    if x >= 1: return sgn * 8.0
    lnx = math.log(1 - x * x)
    tt1 = 2.0 / (math.pi * 0.147) + lnx / 2.0
    tt2 = lnx / 0.147
    return sgn * math.sqrt(-tt1 + math.sqrt(tt1 * tt1 - tt2))

def normal_quantile(p):
    """Normal quantile via well-known z-values for common p, else approximation."""
    common = {0.975: 1.959964, 0.95: 1.644854, 0.995: 2.575829, 0.005: -2.575829}
    if p in common:
        return common[p]
    return _normal_quantile(p)

def _t_quantile(p, df):
    """Approximate t-quantile via Wilson-Hilferty chi-squared inversion."""
    if df <= 0:
        return normal_quantile(p)
    if df > 300:
        return normal_quantile(p)
    z = normal_quantile(p)
    # Hill's approximation for t-quantile
    g1 = (z**3 + z) / (4 * df)
    g2 = (5 * z**5 + 16 * z**3 + 3 * z) / (96 * df**2)
    g3 = (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / (384 * df**3)
    g4 = (79 * z**9 + 776 * z**7 + 1482 * z**5 - 1920 * z**3 - 945 * z) / (92160 * df**4)
    return z + g1 + g2 + g3 + g4

def t_quantile(p, df):
    """t-distribution quantile. Falls back to well-known values for small df."""
    # Hand-verified t critical values for common df and p=0.975
    t975 = {
        1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706,
        6: 2.4469, 7: 2.3646, 8: 2.3060, 9: 2.2622, 10: 2.2281,
        11: 2.2010, 12: 2.1788, 13: 2.1604, 14: 2.1448, 15: 2.1314,
        16: 2.1199, 17: 2.1098, 18: 2.1009, 19: 2.0930, 20: 2.0860,
    }
    if abs(p - 0.975) < 1e-6 and df in t975:
        return t975[df]
    if abs(p - 0.025) < 1e-6 and df in t975:
        return -t975[df]
    return _t_quantile(p, df)

# ---------- core pooling ----------
def prepare_dta_data(studies):
    """Apply 0.5 continuity correction and compute logit(sens), logit(spec), variances.
    Mirrors the app's prepareDTAStudyData(studies, '0.5')."""
    data = []
    for s in studies:
        tp, fp, fn, tn = s['tp'], s['fp'], s['fn'], s['tn']
        has_zero = tp == 0 or fp == 0 or fn == 0 or tn == 0
        cc = 0.5 if has_zero else 0
        tpc, fpc, fnc, tnc = tp + cc, fp + cc, fn + cc, tn + cc
        sens = tpc / (tpc + fnc)
        spec = tnc / (tnc + fpc)
        y1 = logit(sens)
        y2 = logit(spec)
        v1 = 1.0 / tpc + 1.0 / fnc
        v2 = 1.0 / tnc + 1.0 / fpc
        data.append({'y1': y1, 'y2': y2, 'v1': v1, 'v2': v2,
                     'sens': sens, 'spec': spec, 'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn})
    return data

def bivariate_dl_pool(studies, conf_level=0.95):
    """DerSimonian-Laird random-effects bivariate pooling on logit scale.
    Mirrors the app's improvedBivariatePool() exactly."""
    data = prepare_dta_data(studies)
    n = len(data)
    if n < 2:
        return None
    alpha = 1 - conf_level

    # --- Sensitivity dimension ---
    w1 = [1.0 / d['v1'] for d in data]
    sumW1 = sum(w1)
    mu1_fe = sum(d['y1'] * w for d, w in zip(data, w1)) / sumW1
    Q1 = sum(w * (d['y1'] - mu1_fe)**2 for d, w in zip(data, w1))
    C1 = sumW1 - sum(w**2 for w in w1) / sumW1
    tau2_1 = max(0, (Q1 - (n - 1)) / C1) if C1 > 0 else 0

    # --- Specificity dimension ---
    w2 = [1.0 / d['v2'] for d in data]
    sumW2 = sum(w2)
    mu2_fe = sum(d['y2'] * w for d, w in zip(data, w2)) / sumW2
    Q2 = sum(w * (d['y2'] - mu2_fe)**2 for d, w in zip(data, w2))
    C2 = sumW2 - sum(w**2 for w in w2) / sumW2
    tau2_2 = max(0, (Q2 - (n - 1)) / C2) if C2 > 0 else 0

    # --- RE pooling ---
    w1_re = [1.0 / (d['v1'] + tau2_1) for d in data]
    w2_re = [1.0 / (d['v2'] + tau2_2) for d in data]
    sumW1_re = sum(w1_re)
    sumW2_re = sum(w2_re)
    mu1 = sum(d['y1'] * w for d, w in zip(data, w1_re)) / sumW1_re
    mu2 = sum(d['y2'] * w for d, w in zip(data, w2_re)) / sumW2_re
    seMu1 = math.sqrt(1.0 / sumW1_re)
    seMu2 = math.sqrt(1.0 / sumW2_re)

    # --- Critical value: t for k<30, z for k>=30 (matches app) ---
    if n >= 30:
        crit = normal_quantile(1 - alpha / 2)
    else:
        crit = t_quantile(1 - alpha / 2, max(1, n - 2))

    # --- Back-transform ---
    pooledSens = invlogit(mu1)
    pooledSpec = invlogit(mu2)
    sensCI = [invlogit(mu1 - crit * seMu1), invlogit(mu1 + crit * seMu1)]
    specCI = [invlogit(mu2 - crit * seMu2), invlogit(mu2 + crit * seMu2)]

    # --- Derived measures ---
    sensLR = max(0.001, min(0.999, pooledSens))
    specLR = max(0.001, min(0.999, pooledSpec))
    plr = sensLR / (1 - specLR)
    nlr = (1 - sensLR) / specLR
    dor = (sensLR * specLR) / ((1 - sensLR) * (1 - specLR))

    # --- Heterogeneity ---
    I2_sens = max(0, (Q1 - (n - 1)) / Q1 * 100) if Q1 > (n - 1) else 0
    I2_spec = max(0, (Q2 - (n - 1)) / Q2 * 100) if Q2 > (n - 1) else 0

    return {
        'pooledSens': pooledSens, 'pooledSpec': pooledSpec,
        'sensCI': sensCI, 'specCI': specCI,
        'plr': plr, 'nlr': nlr, 'dor': dor,
        'I2_sens': I2_sens, 'I2_spec': I2_spec,
        'tau2_sens': tau2_1, 'tau2_spec': tau2_2,
        'mu1': mu1, 'mu2': mu2, 'seMu1': seMu1, 'seMu2': seMu2,
        'critValue': crit, 'k': n,
    }


# ---------- test datasets ----------
BNP_HF_STUDIES = [
    {'ay': 'Dao 2001',       'tp': 52,  'fp': 14, 'fn': 8,  'tn': 76,  'indexTest': 'BNP', 'threshold': '100 pg/mL'},
    {'ay': 'Morrison 2002',  'tp': 44,  'fp': 20, 'fn': 6,  'tn': 151, 'indexTest': 'BNP', 'threshold': '94 pg/mL'},
    {'ay': 'Maisel 2002',    'tp': 379, 'fp': 83, 'fn': 65, 'tn': 959, 'indexTest': 'BNP', 'threshold': '100 pg/mL'},
    {'ay': 'Mueller 2004',   'tp': 89,  'fp': 17, 'fn': 14, 'tn': 337, 'indexTest': 'BNP', 'threshold': '100 pg/mL'},
    {'ay': 'Lainchbury 2003','tp': 40,  'fp': 22, 'fn': 5,  'tn': 138, 'indexTest': 'BNP', 'threshold': '76 pg/mL'},
    {'ay': 'McCullough 2002','tp': 163, 'fp': 44, 'fn': 21, 'tn': 416, 'indexTest': 'BNP', 'threshold': '100 pg/mL'},
]

HS_TROPONIN_AMI_STUDIES = [
    {'ay': 'Reichlin 2009',  'tp': 85,  'fp': 62,  'fn': 3,  'tn': 568, 'indexTest': 'hs-cTnT', 'threshold': '14 ng/L'},
    {'ay': 'Keller 2009',    'tp': 58,  'fp': 48,  'fn': 2,  'tn': 275, 'indexTest': 'hs-cTnI', 'threshold': '40 ng/L'},
    {'ay': 'Aldous 2011',    'tp': 92,  'fp': 85,  'fn': 5,  'tn': 150, 'indexTest': 'hs-cTnT', 'threshold': '14 ng/L'},
    {'ay': 'Body 2011',      'tp': 143, 'fp': 110, 'fn': 7,  'tn': 603, 'indexTest': 'hs-cTnI', 'threshold': '40 ng/L'},
    {'ay': 'Freund 2012',    'tp': 72,  'fp': 55,  'fn': 4,  'tn': 286, 'indexTest': 'hs-cTnT', 'threshold': '14 ng/L'},
]

CTCA_CAD_STUDIES = [
    {'ay': 'Budoff 2008',    'tp': 196, 'fp': 39, 'fn': 4,  'tn': 167, 'indexTest': 'CTCA 64-slice', 'threshold': '>50% stenosis'},
    {'ay': 'Miller 2008',    'tp': 92,  'fp': 27, 'fn': 3,  'tn': 169, 'indexTest': 'CTCA 64-slice', 'threshold': '>50% stenosis'},
    {'ay': 'Meijboom 2008',  'tp': 211, 'fp': 30, 'fn': 9,  'tn': 110, 'indexTest': 'CTCA 64-slice', 'threshold': '>50% stenosis'},
    {'ay': 'Raff 2005',      'tp': 50,  'fp': 6,  'fn': 0,  'tn': 14,  'indexTest': 'CTCA 64-slice', 'threshold': '>50% stenosis'},
]

if __name__ == '__main__':
    print('=== BNP for Heart Failure (k=6) ===')
    r = bivariate_dl_pool(BNP_HF_STUDIES)
    print(f"  Pooled Sens: {r['pooledSens']:.4f}  [{r['sensCI'][0]:.4f}, {r['sensCI'][1]:.4f}]")
    print(f"  Pooled Spec: {r['pooledSpec']:.4f}  [{r['specCI'][0]:.4f}, {r['specCI'][1]:.4f}]")
    print(f"  PLR={r['plr']:.2f}  NLR={r['nlr']:.3f}  DOR={r['dor']:.1f}")
    print(f"  I2_sens={r['I2_sens']:.1f}%  I2_spec={r['I2_spec']:.1f}%")

    print('\n=== hs-Troponin for AMI (k=5) ===')
    r = bivariate_dl_pool(HS_TROPONIN_AMI_STUDIES)
    print(f"  Pooled Sens: {r['pooledSens']:.4f}  [{r['sensCI'][0]:.4f}, {r['sensCI'][1]:.4f}]")
    print(f"  Pooled Spec: {r['pooledSpec']:.4f}  [{r['specCI'][0]:.4f}, {r['specCI'][1]:.4f}]")
    print(f"  PLR={r['plr']:.2f}  NLR={r['nlr']:.3f}  DOR={r['dor']:.1f}")

    print('\n=== CTCA for CAD (k=4, has fn=0) ===')
    r = bivariate_dl_pool(CTCA_CAD_STUDIES)
    print(f"  Pooled Sens: {r['pooledSens']:.4f}  [{r['sensCI'][0]:.4f}, {r['sensCI'][1]:.4f}]")
    print(f"  Pooled Spec: {r['pooledSpec']:.4f}  [{r['specCI'][0]:.4f}, {r['specCI'][1]:.4f}]")
    print(f"  PLR={r['plr']:.2f}  NLR={r['nlr']:.3f}  DOR={r['dor']:.1f}")
    print(f"  critValue={r['critValue']:.4f} (t with df={r['k']-2})")
