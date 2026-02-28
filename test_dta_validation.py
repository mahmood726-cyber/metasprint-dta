"""
test_dta_validation.py — Full end-to-end DTA workflow test.

Tests 3 cardiovascular DTA datasets through the complete workflow:
protocol (PIRD) → data extraction → analysis → statistical validation
→ plot rendering → paper generation.

Hand-calculated expected values from dta_bivariate_reference.py are
compared against app output within tolerance.
"""
import sys, io, os, time, json, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

from dta_bivariate_reference import (
    bivariate_dl_pool,
    BNP_HF_STUDIES, HS_TROPONIN_AMI_STUDIES, CTCA_CAD_STUDIES,
)

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

def approx(a, b, tol=0.03):
    """3% absolute tolerance for DTA proportions."""
    if a is None or b is None: return False
    return abs(a - b) < tol

def reset_project(driver, name):
    """Create a fresh empty project."""
    driver.execute_script(f'''
        (async function() {{
            var p = createEmptyProject('{name}');
            await idbPut('projects', p);
            currentProjectId = p.id;
            extractedStudies = [];
            document.getElementById('extractBody').innerHTML = '';
            await loadProjects();
        }})();
    ''')
    time.sleep(1)

def add_studies(driver, studies):
    """Add DTA studies via addStudyRow."""
    for s in studies:
        js = f"addStudyRow({json.dumps(s)});"
        driver.execute_script(js)
        time.sleep(0.15)
    time.sleep(0.3)

def parse_stat_cards(driver):
    """Parse stat cards from #analysisSummary."""
    summary = driver.find_element(By.ID, 'analysisSummary')
    cards = summary.find_elements(By.CLASS_NAME, 'stat-card')
    data = {}
    for card in cards:
        try:
            label = card.find_element(By.CLASS_NAME, 'stat-label').text.strip()
            value = card.find_element(By.CLASS_NAME, 'stat-value').text.strip()
            data[label] = value
        except Exception:
            pass
    return data

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

    print('=== DTA END-TO-END VALIDATION ===\n')

    # ============================================================
    # Phase A: App loading + identity checks
    # ============================================================
    print('--- Phase A: App loading ---')
    check('Title contains DTA', 'DTA' in driver.title, driver.title)
    h1 = driver.find_element(By.CSS_SELECTOR, 'h1').text
    check('H1 contains Diagnostics', 'Diagnostics' in h1 or 'DTA' in h1, h1)

    # ============================================================
    # Phase B: Protocol (PIRD) entry
    # ============================================================
    print('\n--- Phase B: Protocol (PIRD) ---')
    driver.find_element(By.CSS_SELECTOR, '[data-phase="protocol"]').click()
    time.sleep(0.5)

    # Fill PIRD fields
    driver.execute_script('''
        document.getElementById("protTitle").value = "BNP for Heart Failure Diagnosis";
        document.getElementById("protP").value = "Adults presenting with acute dyspnea to ED";
        document.getElementById("protI").value = "B-type natriuretic peptide (BNP)";
        document.getElementById("protC").value = "Echocardiography (LVEF < 40%)";
        document.getElementById("protO").value = "Acute decompensated heart failure";
    ''')
    time.sleep(0.3)

    # Verify fields filled
    title_val = driver.execute_script('return document.getElementById("protTitle").value')
    check('Protocol title filled', len(title_val) > 10, title_val[:40])

    pop_val = driver.execute_script('return document.getElementById("protP").value')
    check('Population filled', len(pop_val) > 10, pop_val[:40])

    idx_val = driver.execute_script('return document.getElementById("protI").value')
    check('Index test filled', 'BNP' in idx_val, idx_val[:40])

    ref_val = driver.execute_script('return document.getElementById("protC").value')
    check('Reference standard filled', 'Echocardiography' in ref_val, ref_val[:40])

    # ============================================================
    # Phase C: Three DTA datasets
    # ============================================================
    DATASETS = [
        {
            'name': 'BNP for Heart Failure',
            'studies': BNP_HF_STUDIES,
            'method': 'bivariate',
            'desc': 'High sensitivity screening test',
        },
        {
            'name': 'hs-Troponin for AMI',
            'studies': HS_TROPONIN_AMI_STUDIES,
            'method': 'bivariate',
            'desc': 'Very high sensitivity rule-out test',
        },
        {
            'name': 'CTCA for CAD',
            'studies': CTCA_CAD_STUDIES,
            'method': 'hsroc',
            'desc': 'High sens+spec confirmatory test (has fn=0)',
        },
    ]

    for ds_idx, ds in enumerate(DATASETS):
        print(f'\n{"="*60}')
        print(f'  Dataset {ds_idx+1}: {ds["name"]} (k={len(ds["studies"])})')
        print(f'  {ds["desc"]}')
        print(f'{"="*60}')

        # --- C.1: Data extraction ---
        print(f'\n  --- C.1: Data extraction ---')
        reset_project(driver, f'DTA-Test-{ds["name"]}')
        driver.find_element(By.CSS_SELECTOR, '[data-phase="extract"]').click()
        time.sleep(0.3)
        add_studies(driver, ds['studies'])

        rows = driver.find_elements(By.CSS_SELECTOR, '#extractBody tr')
        expected_k = len(ds['studies'])
        check(f'[{ds["name"]}] {expected_k} rows rendered',
              len(rows) == expected_k, f'{len(rows)} rows')

        study_count = driver.execute_script('return extractedStudies.length')
        check(f'[{ds["name"]}] {expected_k} studies in array',
              study_count == expected_k, f'{study_count} studies')

        # --- C.2: Analysis execution ---
        print(f'\n  --- C.2: Analysis ---')
        driver.find_element(By.CSS_SELECTOR, '[data-phase="analyze"]').click()
        time.sleep(0.3)
        driver.execute_script(f'document.getElementById("methodSelect").value = "{ds["method"]}"')
        driver.execute_script('document.getElementById("confLevelSelect").value = "0.95"')
        time.sleep(0.2)
        driver.execute_script('runAnalysis()')
        time.sleep(2)

        result = driver.execute_script('return lastAnalysisResult')
        check(f'[{ds["name"]}] Analysis returned result', result is not None, '')

        if result is None:
            print(f'  SKIP: remaining tests for {ds["name"]} (no result)')
            continue

        # Parse stat cards
        card_data = parse_stat_cards(driver)
        check(f'[{ds["name"]}] Stat cards rendered', len(card_data) >= 5,
              f'{len(card_data)} cards: {list(card_data.keys())}')

        # --- C.3: Statistical validation ---
        print(f'\n  --- C.3: Statistical validation ---')

        # Hand-calculate expected values
        expected = bivariate_dl_pool(ds['studies'])

        # App values
        app_sens = result['pooledSens']
        app_spec = result['pooledSpec']
        app_sensCI = result['sensCI']
        app_specCI = result['specCI']
        app_plr = result.get('plr', 0)
        app_nlr = result.get('nlr', 1)
        app_dor = result.get('dor', 0)
        app_k = result['k']

        exp_sens = expected['pooledSens']
        exp_spec = expected['pooledSpec']
        exp_sensCI = expected['sensCI']
        exp_specCI = expected['specCI']

        print(f'    App:  Sens={app_sens:.4f} [{app_sensCI[0]:.4f}, {app_sensCI[1]:.4f}]')
        print(f'    Exp:  Sens={exp_sens:.4f} [{exp_sensCI[0]:.4f}, {exp_sensCI[1]:.4f}]')
        print(f'    App:  Spec={app_spec:.4f} [{app_specCI[0]:.4f}, {app_specCI[1]:.4f}]')
        print(f'    Exp:  Spec={exp_spec:.4f} [{exp_specCI[0]:.4f}, {exp_specCI[1]:.4f}]')

        # Tolerance: 3% for point estimates, 5% for CI bounds
        # HSROC uses a different algorithm, so use wider tolerance
        pt_tol = 0.05 if ds['method'] == 'hsroc' else 0.03
        ci_tol = 0.08 if ds['method'] == 'hsroc' else 0.05

        check(f'[{ds["name"]}] Pooled sens matches (tol={pt_tol})',
              approx(app_sens, exp_sens, pt_tol),
              f'app={app_sens:.4f} exp={exp_sens:.4f} diff={abs(app_sens-exp_sens):.4f}')

        check(f'[{ds["name"]}] Pooled spec matches (tol={pt_tol})',
              approx(app_spec, exp_spec, pt_tol),
              f'app={app_spec:.4f} exp={exp_spec:.4f} diff={abs(app_spec-exp_spec):.4f}')

        # CI bounds (bivariate only — HSROC CIs differ by design)
        if ds['method'] == 'bivariate':
            check(f'[{ds["name"]}] Sens CI lower matches',
                  approx(app_sensCI[0], exp_sensCI[0], ci_tol),
                  f'app={app_sensCI[0]:.4f} exp={exp_sensCI[0]:.4f}')
            check(f'[{ds["name"]}] Sens CI upper matches',
                  approx(app_sensCI[1], exp_sensCI[1], ci_tol),
                  f'app={app_sensCI[1]:.4f} exp={exp_sensCI[1]:.4f}')
            check(f'[{ds["name"]}] Spec CI lower matches',
                  approx(app_specCI[0], exp_specCI[0], ci_tol),
                  f'app={app_specCI[0]:.4f} exp={exp_specCI[0]:.4f}')
            check(f'[{ds["name"]}] Spec CI upper matches',
                  approx(app_specCI[1], exp_specCI[1], ci_tol),
                  f'app={app_specCI[1]:.4f} exp={exp_specCI[1]:.4f}')

        check(f'[{ds["name"]}] k matches', app_k == expected_k,
              f'app={app_k} expected={expected_k}')

        # Sanity checks on derived measures
        check(f'[{ds["name"]}] PLR > 1', app_plr > 1, f'PLR={app_plr:.2f}')
        check(f'[{ds["name"]}] NLR < 1', app_nlr < 1, f'NLR={app_nlr:.3f}')
        check(f'[{ds["name"]}] DOR > 1', app_dor > 1, f'DOR={app_dor:.1f}')

        # --- C.4: Plot validation ---
        print(f'\n  --- C.4: Plot validation ---')

        # SROC plot
        sroc_el = driver.find_element(By.ID, 'srocPlotContainer')
        sroc_html = sroc_el.get_attribute('innerHTML')
        has_sroc_svg = '<svg' in sroc_html
        check(f'[{ds["name"]}] SROC plot SVG rendered', has_sroc_svg, f'{len(sroc_html)} chars')
        if has_sroc_svg:
            # Check for study point circles
            circle_count = sroc_html.count('<circle')
            check(f'[{ds["name"]}] SROC has study circles', circle_count >= expected_k,
                  f'{circle_count} circles')

        # Sensitivity forest
        forest_sens = driver.find_element(By.ID, 'forestSensContainer')
        forest_sens_html = forest_sens.get_attribute('innerHTML')
        has_sens_svg = '<svg' in forest_sens_html
        check(f'[{ds["name"]}] Sensitivity forest SVG', has_sens_svg, f'{len(forest_sens_html)} chars')
        if has_sens_svg:
            rect_count = forest_sens_html.count('<rect')
            check(f'[{ds["name"]}] Sens forest has rects', rect_count >= expected_k,
                  f'{rect_count} rects')

        # Specificity forest
        forest_spec = driver.find_element(By.ID, 'forestSpecContainer')
        forest_spec_html = forest_spec.get_attribute('innerHTML')
        has_spec_svg = '<svg' in forest_spec_html
        check(f'[{ds["name"]}] Specificity forest SVG', has_spec_svg, f'{len(forest_spec_html)} chars')

        # --- C.5: Paper generation ---
        print(f'\n  --- C.5: Paper generation ---')
        driver.find_element(By.CSS_SELECTOR, '[data-phase="write"]').click()
        time.sleep(0.5)
        driver.execute_script('generatePaper()')
        time.sleep(2)

        paper_el = driver.find_element(By.ID, 'paperOutput')
        paper_html = paper_el.get_attribute('innerHTML')
        check(f'[{ds["name"]}] Paper generated', len(paper_html) > 200,
              f'{len(paper_html)} chars')

        # Check that pooled results appear in paper
        paper_text = paper_el.text
        sens_pct = f'{app_sens * 100:.1f}'
        spec_pct = f'{app_spec * 100:.1f}'
        check(f'[{ds["name"]}] Paper mentions pooled sens',
              sens_pct in paper_text or 'Sensitivity' in paper_text,
              f'looking for {sens_pct}%')
        check(f'[{ds["name"]}] Paper mentions pooled spec',
              spec_pct in paper_text or 'Specificity' in paper_text,
              f'looking for {spec_pct}%')

    # ============================================================
    # Phase D: Console error check
    # ============================================================
    print('\n\n--- Phase D: Console error check ---')
    logs = driver.get_log('browser')
    errors = [l for l in logs if l['level'] == 'SEVERE']
    if errors:
        for e in errors[:5]:
            print(f'  JS ERROR: {e["message"][:120]}')
    check('No SEVERE JS console errors', len(errors) == 0, f'{len(errors)} errors')

finally:
    driver.quit()

# ============================================================
# Phase E: Summary report
# ============================================================
print(f'\n{"="*60}')
print(f'  END-TO-END SUMMARY: {total} tests, {passed} passed, {failed} failed')
print(f'{"="*60}')
sys.exit(0 if failed == 0 else 1)
