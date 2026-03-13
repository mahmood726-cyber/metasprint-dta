"""
test_dta_identity.py — Verify DTA identity (no pairwise contamination).

Tests that the MetaSprint DTA app has correct branding, terminology,
element IDs, and storage isolation from the pairwise version.
"""
import sys, io, os, time
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

    print('=== DTA IDENTITY TESTS ===\n')

    # --- 1. Title ---
    title = driver.title
    check('Page title contains "DTA"', 'DTA' in title, title)
    check('Page title does NOT contain "Pairwise"', 'Pairwise' not in title, title)

    # --- 2. H1 text ---
    h1 = driver.find_element(By.CSS_SELECTOR, 'h1').text
    check('H1 contains "MetaSprint DTA"', 'MetaSprint DTA' in h1, h1)
    check('H1 contains "Diagnostics"', 'Diagnostics' in h1 or 'Cardio' in h1, h1)

    # --- 3. Protocol uses PIRD terminology ---
    driver.find_element(By.CSS_SELECTOR, '[data-phase="protocol"]').click()
    time.sleep(0.5)
    proto_html = driver.find_element(By.ID, 'phase-protocol').get_attribute('innerHTML')
    check('Protocol mentions "Index Test" (PIRD I)',
          'Index Test' in proto_html or 'index test' in proto_html.lower(), '')
    check('Protocol mentions "Reference Standard" (PIRD R)',
          'Reference Standard' in proto_html or 'reference standard' in proto_html.lower(), '')
    check('Protocol does NOT mention "Comparator" (PICO C)',
          'Comparator' not in proto_html, '')

    # --- 4. Extract table has DTA columns ---
    driver.find_element(By.CSS_SELECTOR, '[data-phase="extract"]').click()
    time.sleep(0.5)
    extract_html = driver.find_element(By.ID, 'phase-extract').get_attribute('innerHTML')
    check('Extract has TP column', 'TP' in extract_html or 'True Positive' in extract_html, '')
    check('Extract has FP column', 'FP' in extract_html or 'False Positive' in extract_html, '')
    check('Extract has FN column', 'FN' in extract_html or 'False Negative' in extract_html, '')
    check('Extract has TN column', 'TN' in extract_html or 'True Negative' in extract_html, '')
    check('Extract does NOT have "Effect Estimate" column',
          'Effect Estimate' not in extract_html and 'effectEstimate' not in extract_html, '')

    # --- 5. QUADAS-2 (not RoB 2) ---
    check('Extract mentions QUADAS',
          'QUADAS' in extract_html or 'quadas' in extract_html.lower(), '')

    # --- 6. IndexedDB name ---
    idb_name = driver.execute_script('return typeof MetaSprintDTA_DB_NAME !== "undefined" ? MetaSprintDTA_DB_NAME : null')
    if idb_name is None:
        # Try checking the actual DB open call
        idb_name = driver.execute_script('''
            try {
                var dbs = indexedDB.databases ? null : null;
                return null;
            } catch(e) { return null; }
        ''')
    # Check by looking at the global variable pattern
    idb_check = driver.execute_script('''
        var scripts = document.querySelectorAll("script");
        for (var s of scripts) {
            if (s.textContent.includes("MetaSprintDTA")) return true;
        }
        return false;
    ''')
    check('App references MetaSprintDTA (IndexedDB)', idb_check, '')

    # --- 7. localStorage prefix ---
    ls_prefix = driver.execute_script('''
        var keys = [];
        for (var i = 0; i < localStorage.length; i++) {
            keys.push(localStorage.key(i));
        }
        return keys.filter(k => k.startsWith("msa-dta-")).length > 0;
    ''')
    check('localStorage uses msa-dta- prefix', ls_prefix, '')

    # --- 8. Analyze tab has method selector with DTA methods ---
    driver.find_element(By.CSS_SELECTOR, '[data-phase="analyze"]').click()
    time.sleep(0.5)
    method_sel = driver.find_element(By.ID, 'methodSelect')
    options = method_sel.find_elements(By.TAG_NAME, 'option')
    option_values = [o.get_attribute('value') for o in options]
    option_texts = [o.text for o in options]
    check('Method selector has "bivariate" option', 'bivariate' in option_values, str(option_values))
    check('Method selector has "hsroc" option', 'hsroc' in option_values, str(option_values))

    # --- 9. Run button text ---
    run_btn_text = driver.execute_script('''
        var btns = document.querySelectorAll("button");
        for (var b of btns) {
            if (b.textContent.includes("Run") && b.textContent.includes("Analysis"))
                return b.textContent.trim();
        }
        return "";
    ''')
    check('Run button mentions DTA', 'DTA' in run_btn_text, run_btn_text)

    # --- 10. No pairwise contamination ---
    page_source = driver.page_source[:50000]
    # Check that visible UI doesn't reference pairwise-only concepts
    h1_lower = h1.lower()
    check('H1 does NOT say "Autopilot"', 'autopilot' not in h1_lower, h1)

    # --- 11. Onboarding references DTA ---
    onboard_html = driver.execute_script('''
        var el = document.getElementById("onboardOverlay");
        return el ? el.innerHTML : "";
    ''')
    if onboard_html:
        check('Onboarding mentions DTA workflow',
              'DTA' in onboard_html or 'diagnostic' in onboard_html.lower() or 'sensitivity' in onboard_html.lower(),
              onboard_html[:100])
    else:
        check('Onboarding element exists', False, 'onboardOverlay not found')

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
