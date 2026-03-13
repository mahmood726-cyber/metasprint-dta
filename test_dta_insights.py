"""
test_dta_insights.py — Tests for DTA-adapted Insights sub-tabs.

Validates: Mizan (trade-off), Shura (multiverse), Hikmah (NND/PPV/NPV),
Taqwa (integrity), Fitrah (Q&A), Ihsan (icon array + dot plot), Rahma (summary).

Uses BNP dataset (k=6) from existing test suites.
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

BNP_STUDIES = [
    {'ay': 'Dao 2001',       'tp': 52,  'fp': 14, 'fn': 8,  'tn': 76,  'indexTest': 'BNP', 'threshold': '100'},
    {'ay': 'Morrison 2002',  'tp': 44,  'fp': 20, 'fn': 6,  'tn': 151, 'indexTest': 'BNP', 'threshold': '94'},
    {'ay': 'Maisel 2002',    'tp': 379, 'fp': 83, 'fn': 65, 'tn': 959, 'indexTest': 'BNP', 'threshold': '100'},
    {'ay': 'Mueller 2004',   'tp': 89,  'fp': 17, 'fn': 14, 'tn': 337, 'indexTest': 'BNP', 'threshold': '100'},
    {'ay': 'Lainchbury 2003','tp': 40,  'fp': 22, 'fn': 5,  'tn': 138, 'indexTest': 'BNP', 'threshold': '76'},
    {'ay': 'McCullough 2002','tp': 163, 'fp': 44, 'fn': 21, 'tn': 416, 'indexTest': 'BNP', 'threshold': '100'},
]

# --- Setup ---
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1400,900')
opts.set_capability('goog:loggingPrefs', {'browser': 'SEVERE'})

html_path = 'file:///' + os.path.abspath('metasprint-dta.html').replace('\\', '/')
_cd = os.environ.get('SE_CHROMEDRIVER', '')
_svc = Service(executable_path=_cd) if _cd else Service()
driver = webdriver.Chrome(options=opts, service=_svc)
driver.get(html_path)
time.sleep(3)

# Dismiss onboarding overlay and modal
driver.execute_script('''
    var overlay = document.getElementById('onboardOverlay');
    if (overlay) overlay.style.display = 'none';
    var modal = document.querySelector('.onboard-modal');
    if (modal) modal.style.display = 'none';
    document.querySelectorAll('.modal-overlay, .onboard-overlay').forEach(function(el) {
        el.style.display = 'none';
    });
    localStorage.setItem('msa-dta-onboarded', 'true');
    localStorage.setItem('msa-dta-onboard-done', 'true');
''')
time.sleep(0.5)

# Load studies and run bivariate analysis
driver.execute_script('''
    (async function() {
        var p = createEmptyProject('Insights Test ' + Date.now());
        await idbPut('projects', p);
        currentProjectId = p.id;
        extractedStudies = [];
        document.getElementById('extractBody').innerHTML = '';
        await loadProjects();
    })();
''')
time.sleep(1)
for s in BNP_STUDIES:
    driver.execute_script(f"addStudyRow({json.dumps(s)});")
    time.sleep(0.15)
time.sleep(0.5)

# Navigate to Analyze and run
driver.execute_script('document.querySelector(\'[data-phase="analyze"]\').click()')
time.sleep(0.5)
driver.execute_script('document.getElementById("methodSelect").value = "bivariate"')
driver.execute_script('document.getElementById("confLevelSelect").value = "0.95"')
time.sleep(0.2)
driver.execute_script('runAnalysis()')
time.sleep(4)

result = driver.execute_script('return lastAnalysisResult')
check('Analysis completed', result is not None, f'k={result.get("k") if result else "?"}')

# Navigate to Insights phase
driver.execute_script('document.querySelector(\'[data-phase="insights"]\').click()')
time.sleep(1)

# =============================================
# TEST 1: Mizan — Sens vs Spec Trade-off
# =============================================
print('\n--- Mizan (Trade-off Scale) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="mizan"]');
    if (tab) tab.click();
''')
time.sleep(1)

# Check canvas has been drawn (non-blank)
mizan_drawn = driver.execute_script('''
    var c = document.getElementById('mizanCanvas');
    if (!c) return false;
    var ctx = c.getContext('2d');
    var data = ctx.getImageData(0, 0, c.width, c.height).data;
    for (var i = 3; i < data.length; i += 4) {
        if (data[i] > 0) return true;
    }
    return false;
''')
check('Mizan: canvas has drawn content', mizan_drawn is True)

mizan_summary = driver.execute_script('return document.getElementById("mizanSummary")?.innerHTML ?? ""')
check('Mizan: summary mentions Youden', 'youden' in mizan_summary.lower() or 'Youden' in mizan_summary, f'{len(mizan_summary)} chars')
check('Mizan: summary mentions clinical role', 'role' in mizan_summary.lower() or 'screen' in mizan_summary.lower() or 'confirm' in mizan_summary.lower() or 'balanc' in mizan_summary.lower())

# =============================================
# TEST 2: Shura — DTA Multiverse
# =============================================
print('\n--- Shura (DTA Multiverse) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="shura"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Run Multiverse button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-shura button');
    for (var b of btns) {
        if (b.textContent.indexOf('Run') >= 0 || b.textContent.indexOf('Multiv') >= 0) { b.click(); break; }
    }
''')
time.sleep(3)

# Check for DTA multiverse results
shura_content = driver.execute_script('return document.getElementById("insight-shura")?.textContent ?? ""')
check('Shura: mentions specification or model', 'spec' in shura_content.lower() or 'model' in shura_content.lower() or 'bivariate' in shura_content.lower())

shura_rows = driver.execute_script('''
    var tables = document.querySelectorAll('#insight-shura table');
    var maxRows = 0;
    tables.forEach(function(t) { maxRows = Math.max(maxRows, t.querySelectorAll('tr').length); });
    return maxRows;
''')
check('Shura: table has specification rows', shura_rows >= 5, f'{shura_rows} rows')

# =============================================
# TEST 3: Hikmah — NND + PPV/NPV
# =============================================
print('\n--- Hikmah (NND + PPV/NPV) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="hikmah"]');
    if (tab) tab.click();
''')
time.sleep(1)

# The DTA mode auto-computes on init, check for results
hikmah_content = driver.execute_script('return document.getElementById("insight-hikmah")?.textContent ?? ""')
check('Hikmah: mentions PPV or NPV', 'ppv' in hikmah_content.lower() or 'npv' in hikmah_content.lower() or 'predictive' in hikmah_content.lower())
check('Hikmah: mentions NND or Youden', 'nnd' in hikmah_content.lower() or 'youden' in hikmah_content.lower() or 'diagnos' in hikmah_content.lower())

# Check if icon array is rendered (colored circles or icon persons)
hikmah_icons = driver.execute_script('''
    var el = document.getElementById('insight-hikmah');
    if (!el) return 0;
    // Count icon-like elements - check multiple patterns
    var circles = el.querySelectorAll('[style*="border-radius"], .icon-person');
    if (circles.length > 0) return circles.length;
    // Also check for any divs with background colors typical of TP/FP/FN/TN
    var colored = el.querySelectorAll('[style*="#22c55e"], [style*="#ef4444"], [style*="#f59e0b"], [style*="#9ca3af"]');
    return colored.length;
''')
check('Hikmah: icon array rendered', hikmah_icons >= 10, f'{hikmah_icons} icons')

# =============================================
# TEST 4: Taqwa — DTA Integrity Checks
# =============================================
print('\n--- Taqwa (DTA Integrity) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="taqwa"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Run Checks button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-taqwa button');
    for (var b of btns) {
        if (b.textContent.indexOf('Run') >= 0 || b.textContent.indexOf('Check') >= 0) { b.click(); break; }
    }
''')
time.sleep(1)

taqwa_content = driver.execute_script('return document.getElementById("taqwaResults")?.textContent ?? ""')
check('Taqwa: shows integrity check results', len(taqwa_content) > 20, f'{len(taqwa_content)} chars')
check('Taqwa: mentions cell or consistency or plausibility or adequacy',
      'cell' in taqwa_content.lower() or 'consist' in taqwa_content.lower() or
      'plausib' in taqwa_content.lower() or 'adequa' in taqwa_content.lower() or
      'sample' in taqwa_content.lower() or 'sensitiv' in taqwa_content.lower())

# =============================================
# TEST 5: Fitrah — DTA Q&A
# =============================================
print('\n--- Fitrah (DTA Q&A) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="fitrah"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Type "sensitivity" and run query
driver.execute_script('''
    document.getElementById('fitrahQuery').value = 'sensitivity';
    runFitrahQuery();
''')
time.sleep(0.5)

fitrah_answer = driver.execute_script('return document.getElementById("fitrahAnswer")?.textContent ?? ""')
check('Fitrah: sensitivity query returns answer', len(fitrah_answer) > 20, f'{len(fitrah_answer)} chars')
check('Fitrah: answer contains percentage', '%' in fitrah_answer)

# Test another DTA query
driver.execute_script('''
    document.getElementById('fitrahQuery').value = 'What are the likelihood ratios?';
    runFitrahQuery();
''')
time.sleep(0.3)
fitrah_lr = driver.execute_script('return document.getElementById("fitrahAnswer")?.textContent ?? ""')
check('Fitrah: LR query returns answer', 'lr' in fitrah_lr.lower() or 'likelihood' in fitrah_lr.lower() or 'plr' in fitrah_lr.lower() or 'rule' in fitrah_lr.lower())

# =============================================
# TEST 6: Ihsan — DTA Icon Array + Dot Plot
# =============================================
print('\n--- Ihsan (Icon Array + Dot Plot) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="ihsan"]');
    if (tab) tab.click();
''')
time.sleep(1)

# Check dot plot canvas
ihsan_dotplot = driver.execute_script('''
    var c = document.getElementById('ihsanDotPlot');
    if (!c) return false;
    var ctx = c.getContext('2d');
    var data = ctx.getImageData(0, 0, c.width, c.height).data;
    for (var i = 3; i < data.length; i += 4) {
        if (data[i] > 0) return true;
    }
    return false;
''')
check('Ihsan: dot plot canvas has content', ihsan_dotplot is True)

# Check icon array container
ihsan_icons = driver.execute_script('''
    var el = document.getElementById('ihsanIconArray');
    if (!el) return '';
    return el.textContent;
''')
check('Ihsan: icon array has content', len(ihsan_icons) > 20, f'{len(ihsan_icons)} chars')

# Check for DTA-specific content (TP/FP/FN/TN or True Positive etc)
ihsan_html = driver.execute_script('return document.getElementById("ihsanIconArray")?.innerHTML ?? ""')
check('Ihsan: shows DTA diagnostic categories',
      'true positive' in ihsan_html.lower() or 'false negative' in ihsan_html.lower() or
      'correctly' in ihsan_html.lower() or 'missed' in ihsan_html.lower() or
      'false alarm' in ihsan_html.lower() or 'TP' in ihsan_html)

# =============================================
# TEST 7: Rahma — DTA Plain-Language Summary
# =============================================
print('\n--- Rahma (DTA Summary) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="rahma"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Generate button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-rahma button');
    for (var b of btns) {
        if (b.textContent.indexOf('Generat') >= 0 || b.textContent.indexOf('Summar') >= 0) { b.click(); break; }
    }
''')
time.sleep(1)

rahma_output = driver.execute_script('return document.getElementById("rahmaOutput")?.textContent ?? ""')
check('Rahma: summary generated', len(rahma_output) > 50, f'{len(rahma_output)} chars')
check('Rahma: mentions sensitivity', 'sensitiv' in rahma_output.lower())
check('Rahma: mentions specificity', 'specific' in rahma_output.lower())

# Check readability score
rahma_readability = driver.execute_script('return document.getElementById("rahmaReadability")?.textContent ?? ""')
check('Rahma: readability score shown', 'grade' in rahma_readability.lower() or 'flesch' in rahma_readability.lower() or 'readab' in rahma_readability.lower())

# =============================================
# Console error check
# =============================================
print('\n--- Console Errors ---')
logs = driver.get_log('browser')
severe = [l for l in logs if l['level'] == 'SEVERE' and 'favicon' not in l['message'].lower()]
check('No SEVERE JS console errors', len(severe) == 0,
      f'{len(severe)} errors' + (f': {severe[0]["message"][:100]}' if severe else ''))

# --- Teardown ---
driver.quit()

# Summary
print(f'\n  {total} tests: {passed} passed, {failed} failed')
sys.exit(0 if failed == 0 else 1)
