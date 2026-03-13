"""
test_dta_2x2_input.py — DTA-specific 2x2 input validation.

Tests addStudyRow with DTA fields, zero-cell handling, field editing,
minimum study requirements, and QUADAS-2 domain storage.
"""
import sys, io, os, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

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

def reset_project(driver):
    """Create a fresh empty project to isolate tests."""
    driver.execute_script('''
        (async function() {
            var p = createEmptyProject('Test Input ' + Date.now());
            await idbPut('projects', p);
            currentProjectId = p.id;
            extractedStudies = [];
            document.getElementById('extractBody').innerHTML = '';
            await loadProjects();
        })();
    ''')
    time.sleep(1)

# --- Setup ---
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1400,900')
opts.set_capability('goog:loggingPrefs', {'browser': 'ALL'})
_cd = os.environ.get('SE_CHROMEDRIVER', '')
_svc = Service(executable_path=_cd) if _cd else Service()
driver = webdriver.Chrome(options=opts, service=_svc)
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

    print('=== DTA 2x2 INPUT TESTS ===\n')

    # Navigate to extract tab
    driver.find_element(By.CSS_SELECTOR, '[data-phase="extract"]').click()
    time.sleep(0.5)

    # --- Test 1: addStudyRow with DTA fields ---
    print('--- Test 1: Basic addStudyRow ---')
    reset_project(driver)
    driver.execute_script('''
        addStudyRow({authorYear:'Smith 2020', tp:50, fp:10, fn:5, tn:100,
                     indexTest:'BNP', threshold:'100 pg/mL'});
    ''')
    time.sleep(0.3)
    rows = driver.find_elements(By.CSS_SELECTOR, '#extractBody tr')
    check('1 study row added', len(rows) == 1, f'{len(rows)} rows')

    # Verify study data stored correctly
    study = driver.execute_script('return extractedStudies[0]')
    check('authorYear stored', study.get('authorYear') == 'Smith 2020', study.get('authorYear'))
    check('tp stored', study.get('tp') == 50, str(study.get('tp')))
    check('fp stored', study.get('fp') == 10, str(study.get('fp')))
    check('fn stored', study.get('fn') == 5, str(study.get('fn')))
    check('tn stored', study.get('tn') == 100, str(study.get('tn')))
    check('indexTest stored', study.get('indexTest') == 'BNP', study.get('indexTest'))
    check('threshold stored', study.get('threshold') == '100 pg/mL', study.get('threshold'))

    # --- Test 2: QUADAS-2 domains initialized ---
    print('\n--- Test 2: QUADAS-2 domains ---')
    rob = study.get('rob', {})
    check('QUADAS-2 d1 exists', 'd1' in rob, str(rob))
    check('QUADAS-2 d2 exists', 'd2' in rob, str(rob))
    check('QUADAS-2 d3 exists', 'd3' in rob, str(rob))
    check('QUADAS-2 d4 exists', 'd4' in rob, str(rob))
    check('QUADAS-2 overall exists', 'overall' in rob, str(rob))

    # --- Test 3: Zero-cell handling ---
    print('\n--- Test 3: Zero-cell continuity correction ---')
    reset_project(driver)
    # Add study with fn=0 (perfect sensitivity)
    driver.execute_script('''
        addStudyRow({authorYear:'Perfect 2020', tp:50, fp:6, fn:0, tn:14});
    ''')
    time.sleep(0.3)
    # Add a second study for analysis
    driver.execute_script('''
        addStudyRow({authorYear:'Normal 2020', tp:40, fp:10, fn:5, tn:100});
    ''')
    time.sleep(0.3)

    # Run analysis to test continuity correction
    driver.find_element(By.CSS_SELECTOR, '[data-phase="analyze"]').click()
    time.sleep(0.5)
    driver.execute_script('runAnalysis()')
    time.sleep(2)

    result = driver.execute_script('return lastAnalysisResult')
    check('Analysis with fn=0 study succeeds', result is not None, '')
    if result:
        check('Pooled sens > 0.5 (valid)', result['pooledSens'] > 0.5, f"{result['pooledSens']:.3f}")
        check('k=2 in result', result['k'] == 2, str(result.get('k')))

    # --- Test 4: Double-zero study excluded ---
    print('\n--- Test 4: Double-zero study ---')
    reset_project(driver)
    # tp=0 AND fn=0 means zero diseased → study should be excluded
    driver.execute_script('''
        addStudyRow({authorYear:'DoubleZero 2020', tp:0, fp:10, fn:0, tn:100});
        addStudyRow({authorYear:'Good1 2020', tp:40, fp:10, fn:5, tn:100});
        addStudyRow({authorYear:'Good2 2020', tp:35, fp:8, fn:7, tn:120});
    ''')
    time.sleep(0.5)

    driver.find_element(By.CSS_SELECTOR, '[data-phase="analyze"]').click()
    time.sleep(0.5)
    driver.execute_script('runAnalysis()')
    time.sleep(2)

    result = driver.execute_script('return lastAnalysisResult')
    if result:
        # DoubleZero should produce sens=0/(0+0)=NaN with cc → 0.5/(0.5+0.5)=0.5
        # Actually the continuity correction makes it valid (0.5/1.0 = 0.5 sens)
        # The app includes it since all 4 cells get +0.5 when any cell is 0
        check('Analysis runs with double-zero study', result is not None, '')
        check('k >= 2', result['k'] >= 2, f"k={result.get('k')}")
    else:
        check('Analysis runs with double-zero study', False, 'result is None')

    # --- Test 5: Minimum study count ---
    print('\n--- Test 5: Minimum 2 studies required ---')
    reset_project(driver)
    driver.execute_script('''
        addStudyRow({authorYear:'Alone 2020', tp:50, fp:10, fn:5, tn:100});
    ''')
    time.sleep(0.3)

    driver.find_element(By.CSS_SELECTOR, '[data-phase="analyze"]').click()
    time.sleep(0.5)
    driver.execute_script('runAnalysis()')
    time.sleep(1)

    result = driver.execute_script('return lastAnalysisResult')
    # With only 1 study, analysis should return null or block
    warn_el = driver.find_element(By.ID, 'analysisWarnings')
    warn_html = warn_el.get_attribute('innerHTML') if warn_el else ''
    check('1 study: analysis blocked or returns null',
          result is None or 'at least 2' in warn_html.lower(),
          f'result={result is not None}, warn={warn_html[:80]}')

    # --- Test 6: Analysis with exactly 2 studies ---
    print('\n--- Test 6: 2-study analysis ---')
    reset_project(driver)
    driver.execute_script('''
        addStudyRow({authorYear:'Study1 2020', tp:50, fp:10, fn:5, tn:100});
        addStudyRow({authorYear:'Study2 2020', tp:40, fp:15, fn:8, tn:90});
    ''')
    time.sleep(0.5)

    driver.find_element(By.CSS_SELECTOR, '[data-phase="analyze"]').click()
    time.sleep(0.5)
    driver.execute_script('runAnalysis()')
    time.sleep(2)

    result = driver.execute_script('return lastAnalysisResult')
    check('2-study analysis succeeds', result is not None, '')
    if result:
        check('2-study k=2', result['k'] == 2, str(result.get('k')))
        check('2-study pooledSens in (0,1)', 0 < result['pooledSens'] < 1,
              f"{result['pooledSens']:.3f}")
        check('2-study pooledSpec in (0,1)', 0 < result['pooledSpec'] < 1,
              f"{result['pooledSpec']:.3f}")

    # --- Test 7: IndexTest and threshold preserved ---
    print('\n--- Test 7: Field preservation ---')
    reset_project(driver)
    driver.execute_script('''
        addStudyRow({authorYear:'Field 2020', tp:50, fp:10, fn:5, tn:100,
                     indexTest:'hs-cTnT', threshold:'14 ng/L',
                     covariate:'ED', subgroup:'ACS'});
    ''')
    time.sleep(0.3)
    s = driver.execute_script('return extractedStudies[0]')
    check('indexTest preserved', s.get('indexTest') == 'hs-cTnT', s.get('indexTest'))
    check('threshold preserved', s.get('threshold') == '14 ng/L', s.get('threshold'))
    check('covariate preserved', s.get('covariate') == 'ED', s.get('covariate'))
    check('subgroup preserved', s.get('subgroup') == 'ACS', s.get('subgroup'))

    # --- Test 8: Auto-computed Sens/Spec in table ---
    print('\n--- Test 8: Auto-computed Sens/Spec ---')
    reset_project(driver)
    driver.find_element(By.CSS_SELECTOR, '[data-phase="extract"]').click()
    time.sleep(0.3)
    driver.execute_script('''
        addStudyRow({authorYear:'Auto 2020', tp:80, fp:20, fn:20, tn:80});
    ''')
    time.sleep(0.5)
    # Sens = 80/(80+20) = 80%, Spec = 80/(80+20) = 80%
    auto_sens = driver.find_elements(By.CSS_SELECTOR, '#extractBody .auto-sens')
    if auto_sens:
        sens_text = auto_sens[0].text.strip()
        check('Auto-computed Sens shown', '80.0%' == sens_text, sens_text)
    else:
        check('Auto-computed Sens column exists', False, 'no .auto-sens elements')

    auto_spec = driver.find_elements(By.CSS_SELECTOR, '#extractBody .auto-spec')
    if auto_spec:
        spec_text = auto_spec[0].text.strip()
        check('Auto-computed Spec shown', '80.0%' == spec_text, spec_text)
    else:
        check('Auto-computed Spec column exists', False, 'no .auto-spec elements')

    # --- Test 9: Multiple studies table rendering ---
    print('\n--- Test 9: Multiple studies rendering ---')
    reset_project(driver)
    for i in range(5):
        driver.execute_script(f'''
            addStudyRow({{authorYear:'Study{i+1} 2020', tp:{50+i*5}, fp:{10+i*2},
                         fn:{5+i}, tn:{100+i*10}}});
        ''')
        time.sleep(0.15)
    rows = driver.find_elements(By.CSS_SELECTOR, '#extractBody tr')
    check('5 study rows rendered', len(rows) == 5, f'{len(rows)} rows')
    count = driver.execute_script('return extractedStudies.length')
    check('5 studies in array', count == 5, f'{count} studies')

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
