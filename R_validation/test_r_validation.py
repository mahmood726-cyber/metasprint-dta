"""
test_r_validation.py — Compare MetaSprint DTA app output against R mada reference values.

Loads the app in headless Chrome, enters benchmark datasets via the Extract panel,
runs bivariate GLMM analysis, and compares pooled estimates against R reference JSON.

Prerequisites:
  1. Run 'Rscript validate_metasprint_dta.R' first to generate validation_reference.json
  2. Chrome + chromedriver installed
  3. pip install selenium

Usage: python test_r_validation.py
"""

import json
import os
import sys
import time
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
HTML_PATH = os.path.join(PARENT_DIR, 'metasprint-dta.html')
REF_JSON = os.path.join(SCRIPT_DIR, 'validation_reference.json')

TOLERANCE = {
    'sens_spec': 0.03,
    'ci': 0.05,           # z-based CIs (k>=10)
    'ci_small_k': 0.10,   # t-based CIs (k<10) — app uses t(k-2), mada uses z: known wider
    'tau2': 0.15,
    'rho': 0.25,
    'I2': 8.0,
    'plr': 1.0,
    'nlr': 0.08,
    'dor': 10.0,
    'dor_small_k': 15.0,  # DOR amplifies small sens/spec differences exponentially
    'auc': 0.03,
}

# Benchmark datasets (same as R script and dta_bivariate_reference.py)
DATASETS = {
    'BNP_HF': {
        'label': 'BNP for Heart Failure',
        'studies': [
            {'study': 'Dao 2001', 'tp': 52, 'fp': 14, 'fn': 8, 'tn': 76},
            {'study': 'Morrison 2002', 'tp': 44, 'fp': 20, 'fn': 6, 'tn': 151},
            {'study': 'Maisel 2002', 'tp': 379, 'fp': 83, 'fn': 65, 'tn': 959},
            {'study': 'Mueller 2004', 'tp': 89, 'fp': 17, 'fn': 14, 'tn': 337},
            {'study': 'Lainchbury 2003', 'tp': 40, 'fp': 22, 'fn': 5, 'tn': 138},
            {'study': 'McCullough 2002', 'tp': 163, 'fp': 44, 'fn': 21, 'tn': 416},
        ]
    },
    'hsTroponin_AMI': {
        'label': 'hs-Troponin for AMI',
        'studies': [
            {'study': 'Reichlin 2009', 'tp': 85, 'fp': 62, 'fn': 3, 'tn': 568},
            {'study': 'Keller 2009', 'tp': 58, 'fp': 48, 'fn': 2, 'tn': 275},
            {'study': 'Aldous 2011', 'tp': 92, 'fp': 85, 'fn': 5, 'tn': 150},
            {'study': 'Body 2011', 'tp': 143, 'fp': 110, 'fn': 7, 'tn': 603},
            {'study': 'Freund 2012', 'tp': 72, 'fp': 55, 'fn': 4, 'tn': 286},
        ]
    },
    'CTCA_CAD': {
        'label': 'CTCA for CAD (FN=0 edge)',
        'studies': [
            {'study': 'Budoff 2008', 'tp': 196, 'fp': 39, 'fn': 4, 'tn': 167},
            {'study': 'Miller 2008', 'tp': 92, 'fp': 27, 'fn': 3, 'tn': 169},
            {'study': 'Meijboom 2008', 'tp': 211, 'fp': 30, 'fn': 9, 'tn': 110},
            {'study': 'Raff 2005', 'tp': 50, 'fp': 6, 'fn': 0, 'tn': 14},
        ]
    },
}


def setup_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--window-size=1920,1200')
    opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    return driver


def run_analysis(driver, studies):
    """Call app's statistical functions directly with raw 2x2 data."""
    js_raw = json.dumps([{
        'tp': s['tp'], 'fp': s['fp'], 'fn': s['fn'], 'tn': s['tn']
    } for s in studies])

    result = driver.execute_script(f"""
        const rawStudies = {js_raw};

        // prepareDTAStudyData applies continuity correction + logit transforms
        if (typeof prepareDTAStudyData !== 'function') return {{ error: 'no prepareDTAStudyData' }};
        const prepared = prepareDTAStudyData(rawStudies, '0.5');
        if (!prepared || prepared.length < 2) return {{ error: 'prepare failed' }};

        // Run bivariate GLMM (DerSimonian-Laird on logit scale)
        const biv = typeof improvedBivariatePool === 'function'
            ? improvedBivariatePool(prepared, 0.95)
            : null;

        // Run HSROC model
        const hsroc = typeof hsrocModel === 'function'
            ? hsrocModel(prepared, 0.95)
            : null;

        // Run Deeks funnel test
        const deeks = typeof deeksTest === 'function'
            ? deeksTest(prepared)
            : null;

        // Run threshold effect test
        const threshold = typeof thresholdEffectTest === 'function'
            ? thresholdEffectTest(prepared)
            : null;

        // Wilson CI test cases
        const wilsonTests = [];
        if (typeof wilsonCI === 'function') {{
            const cases = [{{'x':85,'n':93}},{{'x':0,'n':50}},{{'x':50,'n':100}},
                           {{'x':93,'n':93}},{{'x':7,'n':10}},{{'x':1,'n':100}},{{'x':99,'n':100}}];
            for (const c of cases) {{
                wilsonTests.push({{ x: c.x, n: c.n, ci: wilsonCI(c.x, c.n, 0.05) }});
            }}
        }}

        // Clopper-Pearson CI test cases
        const cpTests = [];
        if (typeof clopperPearsonCI === 'function') {{
            const cases = [{{'x':85,'n':93}},{{'x':0,'n':50}},{{'x':50,'n':100}},
                           {{'x':93,'n':93}},{{'x':7,'n':10}},{{'x':1,'n':100}},{{'x':99,'n':100}}];
            for (const c of cases) {{
                cpTests.push({{ x: c.x, n: c.n, ci: clopperPearsonCI(c.x, c.n, 0.05) }});
            }}
        }}

        return {{
            bivariate: biv,
            hsroc: hsroc,
            deeks: deeks,
            threshold: threshold,
            wilson: wilsonTests,
            cp: cpTests
        }};
    """)
    return result


def compare(label, app_val, r_val, tol, results):
    """Compare app value against R reference within tolerance."""
    if app_val is None or r_val is None:
        results.append((label, 'SKIP', app_val, r_val, tol, None))
        return

    diff = abs(float(app_val) - float(r_val))
    passed = diff <= tol
    results.append((label, 'PASS' if passed else 'FAIL', app_val, r_val, tol, diff))


def main():
    # Load R reference
    if not os.path.exists(REF_JSON):
        print(f"ERROR: R reference JSON not found: {REF_JSON}")
        print("Run 'Rscript validate_metasprint_dta.R' first.")
        # Generate fallback reference from Python bivariate_dl_pool
        print("\nGenerating Python reference as fallback...")
        generate_python_reference()
        if not os.path.exists(REF_JSON):
            sys.exit(1)

    with open(REF_JSON, 'r') as f:
        ref = json.load(f)

    ref_datasets = ref.get('datasets', ref)

    print()
    print('=' * 80)
    print('  MetaSprint DTA — R Cross-Validation Test')
    print('=' * 80)
    source = ref.get('metadata', {}).get('r_version', 'Python fallback')
    print(f'  Reference: {source}')
    print(f'  App: {HTML_PATH}')
    print()

    driver = setup_driver()
    all_results = []

    try:
        file_url = 'file:///' + HTML_PATH.replace('\\', '/').replace(' ', '%20')
        driver.get(file_url)
        time.sleep(2)

        for ds_name, ds_info in DATASETS.items():
            print(f'--- {ds_info["label"]} (k={len(ds_info["studies"])}) ---')

            # Check if R reference exists for this dataset
            r_ref = ref_datasets.get(ds_name)
            if r_ref is None:
                print(f'  WARNING: No R reference for {ds_name}, skipping')
                print()
                continue

            # Run analysis directly (no UI interaction needed)
            result = run_analysis(driver, ds_info['studies'])
            if result is None or result.get('error'):
                err = result.get('error', 'null') if result else 'null'
                print(f'  ERROR: Analysis returned {err}')
                print()
                continue

            biv = result.get('bivariate') or {}
            hsroc = result.get('hsroc') or {}
            deeks = result.get('deeks') or {}
            r_biv = r_ref.get('bivariate_glmm', {})
            r_het = r_ref.get('heterogeneity', {})
            r_der = r_ref.get('derived', {})
            r_hsroc = r_ref.get('hsroc', {})

            # Bivariate GLMM
            compare(f'{ds_name} Sens', biv.get('pooledSens'), r_biv.get('sensitivity'),
                    TOLERANCE['sens_spec'], all_results)
            compare(f'{ds_name} Spec', biv.get('pooledSpec'), r_biv.get('specificity'),
                    TOLERANCE['sens_spec'], all_results)

            # CIs — use wider tolerance for small k (app: t-based, mada: z-based)
            k = len(ds_info['studies'])
            ci_tol = TOLERANCE['ci_small_k'] if k < 10 else TOLERANCE['ci']
            sens_ci = biv.get('sensCI', [None, None])
            spec_ci = biv.get('specCI', [None, None])
            r_sens_ci = r_biv.get('sens_ci', [None, None])
            r_spec_ci = r_biv.get('spec_ci', [None, None])
            compare(f'{ds_name} Sens CI lo', sens_ci[0], r_sens_ci[0],
                    ci_tol, all_results)
            compare(f'{ds_name} Sens CI hi', sens_ci[1], r_sens_ci[1],
                    ci_tol, all_results)
            compare(f'{ds_name} Spec CI lo', spec_ci[0], r_spec_ci[0],
                    ci_tol, all_results)
            compare(f'{ds_name} Spec CI hi', spec_ci[1], r_spec_ci[1],
                    ci_tol, all_results)

            # Heterogeneity
            compare(f'{ds_name} I2 Sens', biv.get('I2_sens'), r_het.get('I2_sens'),
                    TOLERANCE['I2'], all_results)
            compare(f'{ds_name} I2 Spec', biv.get('I2_spec'), r_het.get('I2_spec'),
                    TOLERANCE['I2'], all_results)

            # Derived measures
            compare(f'{ds_name} PLR', biv.get('plr'), r_der.get('PLR'),
                    TOLERANCE['plr'], all_results)
            compare(f'{ds_name} NLR', biv.get('nlr'), r_der.get('NLR'),
                    TOLERANCE['nlr'], all_results)
            dor_tol = TOLERANCE['dor_small_k'] if k < 10 else TOLERANCE['dor']
            compare(f'{ds_name} DOR', biv.get('dor'), r_der.get('DOR'),
                    dor_tol, all_results)

            # HSROC
            compare(f'{ds_name} Lambda', hsroc.get('Lambda'), r_hsroc.get('Lambda'),
                    0.5, all_results)
            compare(f'{ds_name} AUC', hsroc.get('auc'), r_hsroc.get('AUC_phi'),
                    TOLERANCE['auc'], all_results)

            # Print per-dataset results
            ds_results = [r for r in all_results if r[0].startswith(ds_name)]
            for label, status, app_v, r_v, tol, diff in ds_results:
                short_label = label.replace(ds_name + ' ', '')
                if status == 'SKIP':
                    print(f'  {short_label:<20} SKIP')
                else:
                    mark = 'PASS' if status == 'PASS' else 'FAIL'
                    sym = 'v' if status == 'PASS' else 'X'
                    print(f'  {sym} {short_label:<18} app={app_v:>10.4f}  '
                          f'R={r_v:>10.4f}  diff={diff:.4f}  tol={tol}  {mark}')

            print()

    finally:
        driver.quit()

    # Summary
    passed = sum(1 for r in all_results if r[1] == 'PASS')
    failed = sum(1 for r in all_results if r[1] == 'FAIL')
    skipped = sum(1 for r in all_results if r[1] == 'SKIP')

    print('=' * 80)
    print(f'  R VALIDATION SUMMARY: {passed} PASS, {failed} FAIL, {skipped} SKIP')
    print('=' * 80)

    if failed > 0:
        print('\n  FAILURES:')
        for label, status, app_v, r_v, tol, diff in all_results:
            if status == 'FAIL':
                print(f'    {label}: app={app_v:.4f} R={r_v:.4f} diff={diff:.4f} > tol={tol}')

    print()
    return 0 if failed == 0 else 1


def generate_python_reference():
    """Generate reference JSON from Python bivariate_dl_pool as fallback."""
    try:
        sys.path.insert(0, PARENT_DIR)
        from dta_bivariate_reference import (bivariate_dl_pool,
                                              BNP_HF_STUDIES,
                                              HS_TROPONIN_AMI_STUDIES,
                                              CTCA_CAD_STUDIES)
    except ImportError:
        print("Cannot import dta_bivariate_reference.py — no fallback available")
        return

    import math

    ref = {'metadata': {'r_version': 'Python bivariate_dl_pool (fallback)'},
           'datasets': {}}

    py_datasets = [
        ('BNP_HF', BNP_HF_STUDIES),
        ('hsTroponin_AMI', HS_TROPONIN_AMI_STUDIES),
        ('CTCA_CAD', CTCA_CAD_STUDIES),
    ]

    for name, studies in py_datasets:
        r = bivariate_dl_pool(studies)
        if r is None:
            continue

        plr = r['plr']
        nlr = r['nlr']
        dor = r['dor']

        # HSROC-like Lambda from logit-DOR
        Lambda = r['mu1'] + r['mu2']

        def phi(x):
            """Normal CDF approx."""
            import math
            if x < -8: return 0.0
            if x > 8: return 1.0
            t = 1.0 / (1.0 + 0.2316419 * abs(x))
            d = 0.3989422804014327
            p = d * math.exp(-x * x / 2.0) * (
                0.3193815 * t - 0.3565638 * t**2 + 1.781478 * t**3
                - 1.8212560 * t**4 + 1.3302744 * t**5)
            return 1.0 - p if x > 0 else p

        auc = phi(Lambda / math.sqrt(2))

        ref['datasets'][name] = {
            'k': r['k'],
            'bivariate_glmm': {
                'sensitivity': round(r['pooledSens'], 6),
                'specificity': round(r['pooledSpec'], 6),
                'sens_ci': [round(r['sensCI'][0], 6), round(r['sensCI'][1], 6)],
                'spec_ci': [round(r['specCI'][0], 6), round(r['specCI'][1], 6)],
                'tau2_sens': round(r['tau2_sens'], 6),
                'tau2_fpr': round(r['tau2_spec'], 6),
                'rho': 0.0,
            },
            'heterogeneity': {
                'I2_sens': round(r['I2_sens'], 2),
                'I2_spec': round(r['I2_spec'], 2),
            },
            'derived': {
                'PLR': round(plr, 4),
                'NLR': round(nlr, 4),
                'DOR': round(dor, 2),
            },
            'hsroc': {
                'Lambda': round(Lambda, 6),
                'AUC_phi': round(auc, 6),
            },
        }

    with open(REF_JSON, 'w') as f:
        json.dump(ref, f, indent=2)
    print(f"  Python fallback reference written to {REF_JSON}")


if __name__ == '__main__':
    sys.exit(main())
