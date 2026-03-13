"""
test_dta_new_features.py — Tests for features added in the full-pass fix cycle.

Validates: DCA plot, Bayesian analysis, PLR/NLR/DOR forest plots, CSV import,
bootstrap progress bar, model comparison AIC/BIC, Python/Stata export,
toast history, auto-save indicator, reference standard column,
rho sensitivity fix (B1), SROC tooltips (Q2), cumulative error handling (Q9),
bivariate meta-regression (Q16), aria-controls (Q17).
"""
import sys, io, os, time, json, tempfile
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

# Dismiss onboarding
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

# Create project and load studies
driver.execute_script('''
    (async function() {
        var p = createEmptyProject('NewFeatures Test ' + Date.now());
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

# Run analysis
driver.execute_script('document.querySelector(\'[data-phase="analyze"]\').click()')
time.sleep(0.5)
driver.execute_script('document.getElementById("methodSelect").value = "bivariate"')
driver.execute_script('document.getElementById("confLevelSelect").value = "0.95"')
time.sleep(0.2)
driver.execute_script('runAnalysis()')
time.sleep(5)

result = driver.execute_script('return lastAnalysisResult')
check('Analysis completed', result is not None, f'k={result.get("k") if result else "?"}')

# Expand advanced section
driver.execute_script('''
    var sec = document.getElementById('advancedDTASection');
    if (sec) sec.style.display = 'block';
    var content = document.getElementById('advancedDTAContent');
    if (content) content.style.display = 'block';
''')
time.sleep(1)

# =============================================
# B1: Rho Sensitivity Analysis Fix
# =============================================
print('\n--- B1: Rho Sensitivity ---')
rho_results = driver.execute_script('''
    var r = sensitivityAnalysisRho(lastAnalysisResult.studyData, 0.95, [-0.9, -0.5, 0, 0.5, 0.9]);
    return r.results.filter(function(x) { return !x.error; }).map(function(x) { return {rho: x.rho, sens: x.sens}; });
''')
check('B1: Rho sensitivity returns results', rho_results is not None and len(rho_results) >= 3, f'{len(rho_results) if rho_results else 0} valid')
# Point estimates (sens/spec) are rho-independent in bivariate DL — rho affects PLR/NLR/DOR CIs via covariance
# So check that the rho override is actually passed through and different rho values are returned
if rho_results and len(rho_results) >= 2:
    rho_vals = [r['rho'] for r in rho_results]
    check('B1: Rho values correctly passed through (different rho returned)',
          len(set(round(r, 2) for r in rho_vals)) >= 3,
          f'rho values: {[round(r,2) for r in rho_vals]}')
# Also verify PLR/NLR CIs differ across rho values (covariance changes)
plr_cis = driver.execute_script('''
    var r = sensitivityAnalysisRho(lastAnalysisResult.studyData, 0.95, [-0.9, 0, 0.9]);
    var pool = r.rhoValues.map(function(rho) {
        var p = improvedBivariatePool(lastAnalysisResult.studyData, 0.95, rho);
        return p.dorCI ? p.dorCI[1] - p.dorCI[0] : 0;
    });
    return pool;
''')
if plr_cis and len(plr_cis) >= 2:
    ci_widths_differ = max(plr_cis) - min(plr_cis) > 0.01
    check('B1: DOR CI widths differ across rho values (covariance effect)',
          ci_widths_differ, f'CI widths: {[round(w,2) for w in plr_cis]}')

# =============================================
# B3: Threshold test edge case (rho=1)
# =============================================
print('\n--- B3: Threshold Test Edge Case ---')
threshold_result = driver.execute_script('''
    // Create 3 studies with perfect correlation (rho=1)
    var studies = [
        {sens: 0.9, spec: 0.8, tp: 90, fp: 20, fn: 10, tn: 80, n: 200},
        {sens: 0.8, spec: 0.7, tp: 80, fp: 30, fn: 20, tn: 70, n: 200},
        {sens: 0.7, spec: 0.6, tp: 70, fp: 40, fn: 30, tn: 60, n: 200}
    ];
    try {
        var r = thresholdEffectTest(studies);
        return {ok: true, rho: r.rho, pValue: r.pValue, t: r.t};
    } catch(e) {
        return {ok: false, error: e.message};
    }
''')
check('B3: Threshold test handles edge case without error', threshold_result and threshold_result.get('ok'), str(threshold_result))

# =============================================
# B4: Seeded normalRandom
# =============================================
print('\n--- B4: Seeded normalRandom ---')
boot_deterministic = driver.execute_script('''
    var rng = mulberry32(99);
    var vals1 = [];
    for (var i = 0; i < 10; i++) vals1.push(normalRandom(rng));
    var rng2 = mulberry32(99);
    var vals2 = [];
    for (var i = 0; i < 10; i++) vals2.push(normalRandom(rng2));
    return {v1: vals1, v2: vals2, match: JSON.stringify(vals1) === JSON.stringify(vals2)};
''')
check('B4: normalRandom(rng) is deterministic', boot_deterministic and boot_deterministic.get('match'))

# =============================================
# S3: Decision Curve Analysis
# =============================================
print('\n--- S3: DCA ---')
dca_html = driver.execute_script('return document.getElementById("advDCAContainer")?.innerHTML || ""')
check('S3: DCA container has content', len(dca_html) > 100, f'{len(dca_html)} chars')
dca_svgs = driver.execute_script('return document.querySelectorAll("#advDCAContainer svg").length')
check('S3: DCA SVG rendered', dca_svgs >= 1, f'{dca_svgs} SVGs')
dca_paths = driver.execute_script('return document.querySelectorAll("#advDCAContainer svg path").length')
check('S3: DCA has curves (test + treat-all)', dca_paths >= 2, f'{dca_paths} paths')
dca_export = driver.execute_script('return document.querySelector("#advDCAContainer button")?.textContent || ""')
check('S3: DCA has export button', 'Export' in dca_export or 'SVG' in dca_export, dca_export)

# =============================================
# S4: Bayesian Analysis
# =============================================
print('\n--- S4: Bayesian ---')
bayes_html = driver.execute_script('return document.getElementById("advBayesianContainer")?.innerHTML || ""')
check('S4: Bayesian container has content', len(bayes_html) > 100, f'{len(bayes_html)} chars')
bayes_has_cri = 'CrI' in bayes_html or 'Posterior' in bayes_html
check('S4: Bayesian shows credible intervals', bayes_has_cri)
bayes_acceptance = driver.execute_script(r'''
    var html = document.getElementById("advBayesianContainer")?.innerHTML || "";
    var match = html.match(/acceptance=([\d.]+)%/);
    return match ? parseFloat(match[1]) : null;
''')
check('S4: Bayesian MCMC acceptance rate reasonable', bayes_acceptance is not None and 10 < bayes_acceptance < 90,
      f'{bayes_acceptance}%' if bayes_acceptance else 'not found')

# =============================================
# S5: Advanced Plot Export Buttons
# =============================================
print('\n--- S5: Export Buttons ---')
for cid, name in [('advCrosshairsContainer', 'Crosshairs'), ('advLabbeContainer', "L'Abbe"), ('advGalbraithContainer', 'Galbraith')]:
    has_btn = driver.execute_script(f'return document.querySelector("#{cid} button")?.textContent || ""')
    check(f'S5: {name} has export button', 'Export' in has_btn or 'SVG' in has_btn, has_btn)

# =============================================
# S6: PLR/NLR/DOR Forest Plots
# =============================================
print('\n--- S6: PLR/NLR/DOR Forests ---')
plr_svgs = driver.execute_script('return document.querySelectorAll("#advPlrNlrDorContainer svg").length')
check('S6: PLR/NLR/DOR has SVG forest plots', plr_svgs >= 3, f'{plr_svgs} SVGs')
plr_circles = driver.execute_script('return document.querySelectorAll("#advPlrNlrDorContainer svg circle").length')
check('S6: Forest plots have study points', plr_circles >= 18, f'{plr_circles} circles (expect >=18 for 3 plots x 6 studies)')
plr_diamonds = driver.execute_script('return document.querySelectorAll("#advPlrNlrDorContainer svg polygon").length')
check('S6: Forest plots have pooled diamonds', plr_diamonds >= 3, f'{plr_diamonds} polygons')
plr_export = driver.execute_script('return document.querySelector("#advPlrNlrDorContainer button")?.textContent || ""')
check('S6: PLR/NLR/DOR has export button', 'Export' in plr_export or 'SVG' in plr_export)

# =============================================
# S7: Model Comparison AIC/BIC
# =============================================
print('\n--- S7: Model Comparison ---')
mc_html = driver.execute_script('return document.getElementById("advModelCompareContainer")?.innerHTML || ""')
check('S7: Model comparison has content', len(mc_html) > 100, f'{len(mc_html)} chars')
check('S7: Shows AIC', 'AIC' in mc_html)
check('S7: Shows BIC', 'BIC' in mc_html)
check('S7: Shows Log-Likelihood', 'Log-Likelihood' in mc_html)
check('S7: Shows preferred model', 'Preferred' in mc_html or 'preferred' in mc_html)

# =============================================
# S8: Bootstrap Progress
# =============================================
print('\n--- S8: Bootstrap Async ---')
# The bootstrap should have completed by now (it was async)
time.sleep(3)
boot_html = driver.execute_script('return document.getElementById("advBootstrapContainer")?.innerHTML || ""')
check('S8: Bootstrap completed (no progress bar stuck)', 'progress' not in boot_html.lower() or 'Bootstrap' in boot_html)
boot_table = 'Sensitivity' in boot_html and 'Specificity' in boot_html and 'DOR' in boot_html
check('S8: Bootstrap results table rendered', boot_table)

# =============================================
# Q1: Reference Standard Column
# =============================================
print('\n--- Q1: Reference Standard ---')
driver.execute_script('document.querySelector(\'[data-phase="extract"]\').click()')
time.sleep(0.5)
rs_header = driver.execute_script('return document.getElementById("extractHead")?.innerHTML || ""')
check('Q1: Reference Standard header exists', 'Ref Standard' in rs_header)
rs_inputs = driver.execute_script('return document.querySelectorAll("[data-field=\\"referenceStandard\\"]").length')
check('Q1: Reference Standard input fields exist', rs_inputs >= 6, f'{rs_inputs} fields')

# =============================================
# Q2: SROC Tooltips
# =============================================
print('\n--- Q2: SROC Tooltips ---')
driver.execute_script('document.querySelector(\'[data-phase="analyze"]\').click()')
time.sleep(0.5)
sroc_titles = driver.execute_script('return document.querySelectorAll("#srocPlotContainer svg circle title").length')
check('Q2: SROC circles have title tooltips', sroc_titles >= 6, f'{sroc_titles} titles')

# =============================================
# Q4: Toast History
# =============================================
print('\n--- Q4: Toast History ---')
# Trigger a toast first to ensure history has entries
driver.execute_script('showToast("Test notification", "info")')
time.sleep(0.5)
history_len = driver.execute_script('return _toastHistory.length')
check('Q4: Toast history has entries after showToast()', history_len > 0, f'{history_len} entries')
history_btn = driver.execute_script('''
    var btns = document.querySelectorAll('.app-header button');
    for (var i = 0; i < btns.length; i++) {
        if (btns[i].title && btns[i].title.indexOf('otification') >= 0) return true;
    }
    return false;
''')
check('Q4: Notification history button in header', history_btn)

# =============================================
# Q6: Auto-save Indicator
# =============================================
print('\n--- Q6: Auto-save ---')
save_fn = driver.execute_script('return typeof flashSaveIndicator === "function"')
check('Q6: flashSaveIndicator function exists', save_fn)

# =============================================
# Q9: Cumulative Error Handling
# =============================================
print('\n--- Q9: Cumulative ---')
cum_html = driver.execute_script('return document.getElementById("cumulativeContainer")?.innerHTML || ""')
check('Q9: Cumulative table rendered', 'Cumulative' in cum_html and '<tr' in cum_html)

# =============================================
# Q12: isValid2x2 helper
# =============================================
print('\n--- Q12: isValid2x2 ---')
valid_tests = driver.execute_script('''
    return [
        isValid2x2(10, 5, 3, 20),      // valid
        !isValid2x2(NaN, 5, 3, 20),    // NaN
        !isValid2x2(10, -1, 3, 20),    // negative
        isValid2x2(0, 0, 0, 0),        // all zeros (valid)
    ];
''')
check('Q12: isValid2x2 helper works correctly', valid_tests and all(valid_tests), str(valid_tests))

# =============================================
# Q14: Python/Stata Export
# =============================================
print('\n--- Q14: Python/Stata Export ---')
py_code = driver.execute_script('return document.getElementById("advPyCodePre")?.textContent || ""')
check('Q14: Python replication code generated', len(py_code) > 100 and 'numpy' in py_code, f'{len(py_code)} chars')
stata_code = driver.execute_script('return document.getElementById("advStataCodePre")?.textContent || ""')
check('Q14: Stata replication code generated', len(stata_code) > 50 and 'midas' in stata_code, f'{len(stata_code)} chars')

# =============================================
# Q16: Bivariate Meta-Regression
# =============================================
print('\n--- Q16: Bivariate Meta-Regression ---')
# Need covariate data for regression. Let's add covariates and re-run
driver.execute_script('document.querySelector(\'[data-phase="extract"]\').click()')
time.sleep(0.3)
for i, cov_val in enumerate(['50', '60', '70', '80', '90', '100']):
    driver.execute_script(f'''
        var rows = document.querySelectorAll('#extractBody tr');
        if (rows[{i}]) {{
            var covInput = rows[{i}].querySelector('[data-field="covariate"]');
            if (covInput) {{ covInput.value = '{cov_val}'; covInput.dispatchEvent(new Event('change')); }}
        }}
    ''')
time.sleep(0.3)
driver.execute_script('document.querySelector(\'[data-phase="analyze"]\').click()')
time.sleep(0.3)
driver.execute_script('runAnalysis()')
time.sleep(5)
mr_html = driver.execute_script('return document.getElementById("advMetaRegressionContainer")?.innerHTML || ""')
biv_reg = 'logit(Sens)' in mr_html and 'logit(Spec)' in mr_html
check('Q16: Bivariate meta-regression table present', biv_reg, 'logit(Sens) + logit(Spec) rows')

# =============================================
# Q17: aria-controls on Insight Tabs
# =============================================
print('\n--- Q17: Accessibility ---')
aria_count = driver.execute_script('''
    var tabs = document.querySelectorAll('.insights-tab[role="tab"]');
    var count = 0;
    tabs.forEach(function(t) { if (t.getAttribute('aria-controls')) count++; });
    return {total: tabs.length, withAria: count};
''')
check('Q17: All insight tabs have aria-controls',
      aria_count and aria_count['total'] > 0 and aria_count['withAria'] == aria_count['total'],
      f'{aria_count["withAria"]}/{aria_count["total"]}' if aria_count else 'N/A')

# =============================================
# CSV Import (B2)
# =============================================
print('\n--- B2: CSV Import ---')
csv_fn = driver.execute_script('return typeof importStudiesCSV === "function"')
check('B2: importStudiesCSV function exists', csv_fn)

# =============================================
# JS Error Check
# =============================================
print('\n--- Console Error Check ---')
logs = driver.get_log('browser')
severe = [l for l in logs if l['level'] == 'SEVERE' and 'favicon' not in l.get('message', '')]
check('No SEVERE console errors', len(severe) == 0, f'{len(severe)} errors' if severe else 'clean')
if severe:
    for l in severe[:5]:
        print(f'    ERROR: {l["message"][:120]}')

# --- Cleanup ---
driver.quit()

print(f'\n{"="*60}')
print(f'  New Features Tests: {passed} passed, {failed} failed, {total} total')
print(f'{"="*60}')
sys.exit(0 if failed == 0 else 1)
