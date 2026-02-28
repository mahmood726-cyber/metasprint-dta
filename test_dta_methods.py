"""
test_dta_methods.py — Compare bivariate GLMM vs HSROC methods on same data.

Tests method agreement, HSROC-specific outputs (AUC, Lambda, Theta),
Deeks funnel, threshold effect, LOO, and confidence level changes.
"""
import sys, io, os, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

passed = 0
failed = 0
total = 0

def check(label, condition, detail=''):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f'  PASS: {label}' + (f' ({detail})' if detail else ''))
    else:
        failed += 1
        print(f'  FAIL: {label}' + (f' ({detail})' if detail else ''))

def approx(a, b, tol=0.05):
    if a is None or b is None: return False
    return abs(a - b) < tol

# BNP dataset for consistency
BNP_STUDIES = [
    {'ay': 'Dao 2001',       'tp': 52,  'fp': 14, 'fn': 8,  'tn': 76,  'indexTest': 'BNP', 'threshold': '100 pg/mL'},
    {'ay': 'Morrison 2002',  'tp': 44,  'fp': 20, 'fn': 6,  'tn': 151, 'indexTest': 'BNP', 'threshold': '94 pg/mL'},
    {'ay': 'Maisel 2002',    'tp': 379, 'fp': 83, 'fn': 65, 'tn': 959, 'indexTest': 'BNP', 'threshold': '100 pg/mL'},
    {'ay': 'Mueller 2004',   'tp': 89,  'fp': 17, 'fn': 14, 'tn': 337, 'indexTest': 'BNP', 'threshold': '100 pg/mL'},
    {'ay': 'Lainchbury 2003','tp': 40,  'fp': 22, 'fn': 5,  'tn': 138, 'indexTest': 'BNP', 'threshold': '76 pg/mL'},
    {'ay': 'McCullough 2002','tp': 163, 'fp': 44, 'fn': 21, 'tn': 416, 'indexTest': 'BNP', 'threshold': '100 pg/mL'},
]

def load_studies(driver):
    """Load BNP studies into a fresh project."""
    driver.execute_script('''
        (async function() {
            var p = createEmptyProject('Method Comparison ' + Date.now());
            await idbPut('projects', p);
            currentProjectId = p.id;
            extractedStudies = [];
            document.getElementById('extractBody').innerHTML = '';
            await loadProjects();
        })();
    ''')
    time.sleep(1)
    for s in BNP_STUDIES:
        js = f"addStudyRow({json.dumps(s)});"
        driver.execute_script(js)
        time.sleep(0.15)
    time.sleep(0.5)

def run_method(driver, method, conf='0.95'):
    """Set method and conf level, run analysis, return result."""
    driver.find_element(By.CSS_SELECTOR, '[data-phase="analyze"]').click()
    time.sleep(0.3)
    # Set method
    driver.execute_script(f'document.getElementById("methodSelect").value = "{method}"')
    # Set confidence level (must match option value exactly: "0.90", "0.95", "0.99")
    driver.execute_script(f'document.getElementById("confLevelSelect").value = "{conf}"')
    time.sleep(0.2)
    driver.execute_script('runAnalysis()')
    time.sleep(2)
    return driver.execute_script('return lastAnalysisResult')

# --- Setup ---
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1400,900')
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
driver = webdriver.Chrome(options=opts)
driver.implicitly_wait(3)

try:
    html_path = os.path.normpath(os.path.abspath('metasprint-dta.html'))
    url = 'file:///' + html_path.replace(os.sep, '/').replace(' ', '%20')
    driver.get(url)
    time.sleep(2)

    # Dismiss onboarding
    driver.execute_script('''
        var m = document.getElementById("onboardOverlay");
        if (m) m.style.display = "none";
        try { localStorage.setItem("msa-dta-onboarded", "1"); } catch(e) {}
    ''')
    time.sleep(0.3)

    print('=== DTA METHOD COMPARISON TESTS ===\n')

    # --- Test 1 & 2: Bivariate GLMM ---
    print('--- Test 1: Bivariate GLMM ---')
    load_studies(driver)
    biv = run_method(driver, 'bivariate')
    check('Bivariate analysis succeeds', biv is not None, '')
    biv_sens = biv['pooledSens'] if biv else None
    biv_spec = biv['pooledSpec'] if biv else None
    if biv:
        check('Bivariate k=6', biv['k'] == 6, str(biv.get('k')))
        check('Bivariate pooledSens in (0.7, 1.0)',
              0.7 < biv['pooledSens'] < 1.0, f"{biv['pooledSens']:.3f}")
        check('Bivariate pooledSpec in (0.7, 1.0)',
              0.7 < biv['pooledSpec'] < 1.0, f"{biv['pooledSpec']:.3f}")
        check('Bivariate method label', biv.get('method') == 'Bivariate GLMM',
              biv.get('method'))
        check('Bivariate has I2_sens',
              biv.get('heterogeneity', {}).get('I2_sens') is not None, '')
        check('Bivariate has I2_spec',
              biv.get('heterogeneity', {}).get('I2_spec') is not None, '')
        check('Bivariate AUC is null', biv.get('auc') is None, str(biv.get('auc')))

    # --- Test 3 & 4: HSROC ---
    print('\n--- Test 2: HSROC ---')
    load_studies(driver)
    hsroc = run_method(driver, 'hsroc')
    check('HSROC analysis succeeds', hsroc is not None, '')
    hsroc_sens = hsroc['pooledSens'] if hsroc else None
    hsroc_spec = hsroc['pooledSpec'] if hsroc else None
    if hsroc:
        check('HSROC k=6', hsroc['k'] == 6, str(hsroc.get('k')))
        check('HSROC method label', hsroc.get('method') == 'HSROC', hsroc.get('method'))
        check('HSROC returns AUC', hsroc.get('auc') is not None, str(hsroc.get('auc')))
        if hsroc.get('auc') is not None:
            check('HSROC AUC in (0.5, 1.0)', 0.5 < hsroc['auc'] < 1.0,
                  f"{hsroc['auc']:.3f}")
        het = hsroc.get('heterogeneity', {})
        check('HSROC has Lambda', het.get('Lambda') is not None, str(het.get('Lambda')))
        check('HSROC has Theta', het.get('Theta') is not None, str(het.get('Theta')))
        check('HSROC has sigma2_alpha', het.get('sigma2_alpha') is not None,
              str(het.get('sigma2_alpha')))

    # --- Test 5: Methods agree within 5% ---
    print('\n--- Test 3: Method agreement ---')
    if biv_sens is not None and hsroc_sens is not None:
        check('Bivariate vs HSROC sens within 5%',
              approx(biv_sens, hsroc_sens, 0.05),
              f'biv={biv_sens:.3f} hsroc={hsroc_sens:.3f}')
        check('Bivariate vs HSROC spec within 5%',
              approx(biv_spec, hsroc_spec, 0.05),
              f'biv={biv_spec:.3f} hsroc={hsroc_spec:.3f}')
    else:
        check('Methods agreement (sens)', False, 'one or both methods failed')
        check('Methods agreement (spec)', False, 'one or both methods failed')

    # --- Test 6: Deeks funnel test ---
    print('\n--- Test 4: Deeks funnel ---')
    load_studies(driver)
    result = run_method(driver, 'bivariate')
    if result:
        deeks = result.get('deeks')
        check('Deeks test present', deeks is not None, '')
        if deeks and not deeks.get('warning'):
            check('Deeks slope is numeric', isinstance(deeks.get('slope'), (int, float)),
                  str(deeks.get('slope')))
            check('Deeks p-value is numeric', isinstance(deeks.get('pValue'), (int, float)),
                  str(deeks.get('pValue')))
            check('Deeks p-value in (0, 1)', 0 <= deeks['pValue'] <= 1,
                  f"p={deeks['pValue']:.3f}")
        elif deeks and deeks.get('warning'):
            check('Deeks has warning (k too small)', True, deeks['warning'][:60])

    # --- Test 7: Threshold effect ---
    print('\n--- Test 5: Threshold effect ---')
    if result:
        thresh = result.get('thresholdEffect')
        check('Threshold effect present', thresh is not None, '')
        if thresh:
            check('Threshold rho is numeric',
                  isinstance(thresh.get('rho'), (int, float)),
                  f"rho={thresh.get('rho')}")

    # --- Test 8: Confidence level change ---
    print('\n--- Test 6: Confidence level (90% vs 95%) ---')
    load_studies(driver)
    r95 = run_method(driver, 'bivariate', '0.95')
    load_studies(driver)
    r90 = run_method(driver, 'bivariate', '0.90')
    if r95 and r90:
        ci95_width_sens = r95['sensCI'][1] - r95['sensCI'][0]
        ci90_width_sens = r90['sensCI'][1] - r90['sensCI'][0]
        check('90% CI sens narrower than 95%', ci90_width_sens < ci95_width_sens,
              f'90%={ci90_width_sens:.4f} 95%={ci95_width_sens:.4f}')
        ci95_width_spec = r95['specCI'][1] - r95['specCI'][0]
        ci90_width_spec = r90['specCI'][1] - r90['specCI'][0]
        check('90% CI spec narrower than 95%', ci90_width_spec < ci95_width_spec,
              f'90%={ci90_width_spec:.4f} 95%={ci95_width_spec:.4f}')
        # Point estimates should be same
        check('Point estimates unchanged (sens)',
              approx(r95['pooledSens'], r90['pooledSens'], 0.001),
              f"95%={r95['pooledSens']:.4f} 90%={r90['pooledSens']:.4f}")
        check('Point estimates unchanged (spec)',
              approx(r95['pooledSpec'], r90['pooledSpec'], 0.001),
              f"95%={r95['pooledSpec']:.4f} 90%={r90['pooledSpec']:.4f}")

    # --- Test 9: LOO analysis ---
    print('\n--- Test 7: Leave-one-out ---')
    load_studies(driver)
    run_method(driver, 'bivariate')
    # LOO is triggered by a separate button/function, not by runAnalysis
    driver.execute_script('runDTALeaveOneOut()')
    time.sleep(2)
    loo_html = driver.execute_script('''
        var el = document.getElementById("looContainer");
        return el ? el.innerHTML : "";
    ''')
    check('LOO container has content', len(loo_html) > 10, f'{len(loo_html)} chars')

    # --- Test 10: Stat cards rendered correctly ---
    print('\n--- Test 8: Stat cards ---')
    summary = driver.find_element(By.ID, 'analysisSummary')
    cards = summary.find_elements(By.CLASS_NAME, 'stat-card')
    check('At least 6 stat cards', len(cards) >= 6, f'{len(cards)} cards')

    card_data = {}
    for card in cards:
        try:
            label = card.find_element(By.CLASS_NAME, 'stat-label').text.strip()
            value = card.find_element(By.CLASS_NAME, 'stat-value').text.strip()
            card_data[label] = value
        except Exception:
            pass

    check('Pooled Sens card exists', 'Pooled Sens' in card_data, str(list(card_data.keys())))
    check('Pooled Spec card exists', 'Pooled Spec' in card_data, str(list(card_data.keys())))
    check('PLR card exists', 'PLR' in card_data, str(list(card_data.keys())))
    check('NLR card exists', 'NLR' in card_data, str(list(card_data.keys())))
    check('DOR card exists', 'DOR' in card_data, str(list(card_data.keys())))

    # --- Console errors ---
    print('\n=== CONSOLE ERROR CHECK ===')
    logs = driver.get_log('browser')
    errors = [l for l in logs if l['level'] == 'SEVERE']
    if errors:
        for e in errors[:5]:
            print(f'  JS ERROR: {e["message"][:120]}')
    check('No SEVERE JS console errors', len(errors) == 0, f'{len(errors)} errors')

finally:
    driver.quit()

print(f'\n{total} tests: {passed} passed, {failed} failed')
sys.exit(0 if failed == 0 else 1)
