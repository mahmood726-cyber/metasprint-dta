"""
test_dta_advanced.py — Tests for Phase 1-3 statistical completeness features.

Validates: Crosshairs plot, L'Abbe plot, Galbraith plot, Fagan nomogram SVG,
Rho sensitivity table, Bootstrap CIs, Meta-regression.

Uses BNP dataset (k=6) from existing test suites.
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
driver = webdriver.Chrome(options=opts)
driver.get(html_path)
time.sleep(3)

# Dismiss onboarding overlay and modal
driver.execute_script('''
    var overlay = document.getElementById('onboardOverlay');
    if (overlay) overlay.style.display = 'none';
    var modal = document.querySelector('.onboard-modal');
    if (modal) modal.style.display = 'none';
    // Remove any other overlays
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
        var p = createEmptyProject('Advanced Test ' + Date.now());
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

# Navigate to Analyze and run (use JS click to bypass any overlays)
driver.execute_script('document.querySelector(\'[data-phase="analyze"]\').click()')
time.sleep(0.5)
driver.execute_script('document.getElementById("methodSelect").value = "bivariate"')
driver.execute_script('document.getElementById("confLevelSelect").value = "0.95"')
time.sleep(0.2)
driver.execute_script('runAnalysis()')
time.sleep(4)

result = driver.execute_script('return lastAnalysisResult')
check('Analysis completed', result is not None, f'k={result.get("k") if result else "?"}')

# Expand advanced DTA section if collapsed
driver.execute_script('''
    var sec = document.getElementById('advancedDTASection');
    if (sec) sec.style.display = 'block';
''')
time.sleep(0.5)

# =============================================
# PHASE 1: Visualization Tests
# =============================================

# Test 1: Crosshairs plot
ch_html = driver.execute_script('return document.getElementById("advCrosshairsContainer")?.innerHTML || ""')
ch_svgs = driver.execute_script('return document.querySelectorAll("#advCrosshairsContainer svg").length')
check('Crosshairs: SVG rendered', ch_svgs >= 1, f'{ch_svgs} SVGs')
ch_circles = driver.execute_script('return document.querySelectorAll("#advCrosshairsContainer svg circle").length')
check('Crosshairs: study circles present', ch_circles >= 6, f'{ch_circles} circles')
ch_lines = driver.execute_script('return document.querySelectorAll("#advCrosshairsContainer svg line").length')
check('Crosshairs: CI crosshair lines present', ch_lines >= 12, f'{ch_lines} lines (expect >=12 for 6 studies x 2)')
# Summary diamond could be rect, polygon, or path depending on implementation
ch_diamond = driver.execute_script('''
    var rects = document.querySelectorAll("#advCrosshairsContainer svg rect").length;
    var polys = document.querySelectorAll("#advCrosshairsContainer svg polygon").length;
    var paths = document.querySelectorAll("#advCrosshairsContainer svg path").length;
    return rects + polys + paths;
''')
check('Crosshairs: summary diamond or frame present', ch_diamond >= 1, f'{ch_diamond} shapes')

# Test 2: L'Abbe plot
lb_svgs = driver.execute_script('return document.querySelectorAll("#advLabbeContainer svg").length')
check("L'Abbe: SVG rendered", lb_svgs >= 1)
lb_circles = driver.execute_script('return document.querySelectorAll("#advLabbeContainer svg circle").length')
check("L'Abbe: study bubbles present", lb_circles >= 6, f'{lb_circles} circles')
# Iso-DOR curves could be polyline or path
lb_curves = driver.execute_script('''
    var polylines = document.querySelectorAll("#advLabbeContainer svg polyline").length;
    var paths = document.querySelectorAll("#advLabbeContainer svg path").length;
    return polylines + paths;
''')
check("L'Abbe: iso-DOR curves present", lb_curves >= 2, f'{lb_curves} curves (polyline+path)')

# Test 3: Galbraith plot
gb_svgs = driver.execute_script('return document.querySelectorAll("#advGalbraithContainer svg").length')
check('Galbraith: SVG rendered', gb_svgs >= 1)
gb_circles = driver.execute_script('return document.querySelectorAll("#advGalbraithContainer svg circle").length')
check('Galbraith: study points present', gb_circles >= 6, f'{gb_circles} circles')
gb_lines = driver.execute_script('return document.querySelectorAll("#advGalbraithContainer svg line").length')
check('Galbraith: regression + CI bands', gb_lines >= 3, f'{gb_lines} lines')

# Test 4: Fagan nomogram (click Calculate)
fagan_btn = driver.execute_script('''
    var btns = document.querySelectorAll('#advFaganContainer button');
    for (var b of btns) { if (b.textContent.indexOf('Calculat') >= 0) { b.click(); return true; } }
    return false;
''')
time.sleep(0.5)
check('Fagan: Calculate button found and clicked', fagan_btn is True)
# Fagan SVG may be in faganResult or advFaganContainer
fagan_svg = driver.execute_script('''
    var inResult = document.querySelectorAll("#faganResult svg").length;
    var inContainer = document.querySelectorAll("#advFaganContainer svg").length;
    return inResult + inContainer;
''')
check('Fagan: SVG nomogram rendered', fagan_svg >= 1, f'{fagan_svg} SVGs')
fagan_text = driver.execute_script('''
    var t1 = document.getElementById("faganResult")?.textContent || "";
    var t2 = document.getElementById("advFaganContainer")?.textContent || "";
    return t1 + " " + t2;
''')
check('Fagan: post-test probabilities shown', 'ost-test' in fagan_text or 'test +' in fagan_text.lower() or '%' in fagan_text)

# =============================================
# PHASE 2: Sensitivity Analysis Tests
# =============================================

# Test 5: Rho sensitivity
rho_html = driver.execute_script('return document.getElementById("advRhoSensContainer")?.innerHTML || ""')
check('Rho sensitivity: container populated', len(rho_html) > 50, f'{len(rho_html)} chars')
rho_rows = driver.execute_script('return document.querySelectorAll("#advRhoSensContainer tr").length')
check('Rho sensitivity: table has rows', rho_rows >= 8, f'{rho_rows} rows (7 rho values + header)')
check('Rho sensitivity: mentions rho', 'rho' in rho_html.lower() or 'Rho' in rho_html or 'correlation' in rho_html.lower())

# Test 6: Bootstrap CIs
boot_html = driver.execute_script('return document.getElementById("advBootstrapContainer")?.innerHTML || ""')
check('Bootstrap: container populated', len(boot_html) > 50, f'{len(boot_html)} chars')
check('Bootstrap: mentions bootstrap', 'ootstrap' in boot_html or 'B=' in boot_html)
boot_rows = driver.execute_script('return document.querySelectorAll("#advBootstrapContainer tr").length')
check('Bootstrap: table has rows', boot_rows >= 4, f'{boot_rows} rows (header + Sens/Spec/DOR)')
check('Bootstrap: mentions seed', 'seed' in boot_html.lower() or '42' in boot_html)

# =============================================
# PHASE 3: Meta-Regression Test
# =============================================

# Test 7: Meta-regression (threshold as covariate)
mr_html = driver.execute_script('return document.getElementById("advMetaRegressionContainer")?.innerHTML || ""')
check('Meta-regression: container populated', len(mr_html) > 30, f'{len(mr_html)} chars')
has_content = 'slope' in mr_html.lower() or 'p-value' in mr_html.lower() or 'covariate' in mr_html.lower() or 'No numeric' in mr_html
check('Meta-regression: shows results or explains no covariate', has_content)
if 'slope' in mr_html.lower():
    mr_svg = driver.execute_script('return document.querySelectorAll("#advMetaRegressionContainer svg").length')
    check('Meta-regression: bubble plot SVG', mr_svg >= 1, f'{mr_svg} SVGs')

# =============================================
# Console error check
# =============================================
logs = driver.get_log('browser')
severe = [l for l in logs if l['level'] == 'SEVERE' and 'favicon' not in l['message'].lower()]
check('No SEVERE JS console errors', len(severe) == 0,
      f'{len(severe)} errors' + (f': {severe[0]["message"][:80]}' if severe else ''))

# --- Teardown ---
driver.quit()

# Summary
print(f'\n  {total} tests: {passed} passed, {failed} failed')
sys.exit(0 if failed == 0 else 1)
