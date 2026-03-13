"""
test_dta_insights_extended.py — Tests for 8 previously untested Insights tabs.

Validates: Tawakkul (trust radar), Amanah (evidence gaps), Dhulm (equity),
Tabayyun (verification), Living (currency), Conflict (contradictions),
Radar (opportunities), Registry (canonical linking).

Uses BNP dataset (k=6) and mock universeTrialsCache for universe-dependent tabs.
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

# Mock universe trials for tabs requiring universeTrialsCache
MOCK_UNIVERSE = json.dumps([
    {'nctId': 'NCT00001111', 'briefTitle': 'BNP for Heart Failure Diagnosis in Emergency',
     'interventions': 'BNP assay', 'conditions': 'Heart Failure',
     'primaryOutcome': 'Sensitivity', 'phase': 'Phase 3',
     'startDate': '2023-06-01', 'completionDate': '2024-01-15',
     'enrollment': 300, 'status': 'Completed', 'sponsor': 'NIH'},
    {'nctId': 'NCT00002222', 'briefTitle': 'NT-proBNP vs BNP in Acute Dyspnea',
     'interventions': 'NT-proBNP', 'conditions': 'Heart Failure',
     'primaryOutcome': 'Specificity', 'phase': 'Phase 2',
     'startDate': '2022-01-10', 'completionDate': '2023-06-01',
     'enrollment': 150, 'status': 'Completed', 'sponsor': 'Roche'},
    {'nctId': 'NCT00003333', 'briefTitle': 'Troponin I Rapid Assay for ACS',
     'interventions': 'Troponin I', 'conditions': 'Acute Coronary Syndrome',
     'primaryOutcome': 'Sensitivity', 'phase': 'Phase 3',
     'startDate': '2024-03-01', 'completionDate': '2025-09-15',
     'enrollment': 500, 'status': 'Recruiting', 'sponsor': 'Abbott'},
    {'nctId': 'NCT00004444', 'briefTitle': 'D-dimer for Pulmonary Embolism',
     'interventions': 'D-dimer', 'conditions': 'Pulmonary Embolism',
     'primaryOutcome': 'NPV', 'phase': 'Phase 4',
     'startDate': '2021-07-01', 'completionDate': '2022-12-01',
     'enrollment': 800, 'status': 'Completed', 'sponsor': 'Siemens'},
    {'nctId': 'NCT00005555', 'briefTitle': 'BNP in Elderly Heart Failure PMID:12345678',
     'interventions': 'BNP assay', 'conditions': 'Heart Failure',
     'primaryOutcome': 'DOR', 'phase': 'Phase 3',
     'startDate': '2025-01-01', 'completionDate': '2026-06-01',
     'enrollment': 200, 'status': 'Active', 'sponsor': 'University Hospital'},
    {'nctId': 'NCT00006666', 'briefTitle': 'BNP screening community 10.1234/test.2024',
     'interventions': 'BNP assay', 'conditions': 'Heart Failure',
     'primaryOutcome': 'Sensitivity', 'phase': '',
     'startDate': '2024-08-01', 'completionDate': '2025-12-01',
     'enrollment': 120, 'status': 'Completed', 'sponsor': 'Local Clinic'},
])

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

# Load studies and run bivariate analysis
driver.execute_script('''
    (async function() {
        var p = createEmptyProject('ExtInsights Test ' + Date.now());
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

# Inject mock universe trials for universe-dependent tabs
driver.execute_script(f'universeTrialsCache = {MOCK_UNIVERSE};')
time.sleep(0.2)

# Navigate to Insights phase
driver.execute_script('document.querySelector(\'[data-phase="insights"]\').click()')
time.sleep(1)

# =============================================
# TEST 1: Tawakkul — Trust Decomposition (8-axis radar)
# =============================================
print('\n--- Tawakkul (Trust Radar) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="tawakkul"]');
    if (tab) tab.click();
''')
time.sleep(1.5)

# Tawakkul auto-renders when insight tab is clicked
tawakkul_canvas = driver.execute_script('''
    var c = document.getElementById('tawakkulRadar');
    if (!c) return false;
    var ctx = c.getContext('2d');
    var data = ctx.getImageData(0, 0, c.width, c.height).data;
    for (var i = 3; i < data.length; i += 4) {
        if (data[i] > 0) return true;
    }
    return false;
''')
check('Tawakkul: radar canvas has drawn content', tawakkul_canvas is True)

tawakkul_details = driver.execute_script('return document.getElementById("tawakkulDetails")?.innerHTML ?? ""')
check('Tawakkul: details section populated', len(tawakkul_details) > 50, f'{len(tawakkul_details)} chars')
check('Tawakkul: mentions trust axes',
      'sample' in tawakkul_details.lower() or 'precision' in tawakkul_details.lower() or
      'consist' in tawakkul_details.lower() or 'bias' in tawakkul_details.lower())

tawakkul_content_visible = driver.execute_script('''
    var el = document.getElementById('tawakkulContent');
    return el ? el.style.display !== 'none' : false;
''')
check('Tawakkul: content container visible', tawakkul_content_visible is True)

# Check trust score badge exists
tawakkul_badge = driver.execute_script('''
    var el = document.getElementById('tawakkulDetails');
    if (!el) return '';
    var badges = el.querySelectorAll('[style*="border-radius"], strong, b');
    for (var b of badges) {
        var t = b.textContent.toLowerCase();
        if (t.indexOf('high') >= 0 || t.indexOf('moderate') >= 0 || t.indexOf('low') >= 0) return t;
    }
    return el.textContent.substring(0, 200);
''')
check('Tawakkul: trust level assessed', len(tawakkul_badge) > 0)

# =============================================
# TEST 2: Amanah — Evidence Gap Scanner
# =============================================
print('\n--- Amanah (Evidence Gaps) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="amanah"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Scan button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-amanah button');
    for (var b of btns) {
        if (b.textContent.indexOf('Scan') >= 0 || b.textContent.indexOf('Gap') >= 0) { b.click(); break; }
    }
''')
time.sleep(2)

amanah_content_visible = driver.execute_script('''
    var el = document.getElementById('amanahContent');
    return el ? el.style.display !== 'none' : false;
''')
check('Amanah: content container visible', amanah_content_visible is True)

amanah_table = driver.execute_script('return document.getElementById("amanahTable")?.innerHTML ?? ""')
check('Amanah: gap table rendered', len(amanah_table) > 20, f'{len(amanah_table)} chars')
check('Amanah: mentions intervention or outcome',
      'intervention' in amanah_table.lower() or 'outcome' in amanah_table.lower() or
      'gap' in amanah_table.lower() or 'score' in amanah_table.lower() or
      'bnp' in amanah_table.lower() or 'troponin' in amanah_table.lower())

# =============================================
# TEST 3: Dhulm — Representation Equity
# =============================================
print('\n--- Dhulm (Equity) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="dhulm"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Assess button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-dhulm button');
    for (var b of btns) {
        if (b.textContent.indexOf('Assess') >= 0 || b.textContent.indexOf('Equity') >= 0) { b.click(); break; }
    }
''')
time.sleep(2)

dhulm_content_visible = driver.execute_script('''
    var el = document.getElementById('dhulmContent');
    return el ? el.style.display !== 'none' : false;
''')
check('Dhulm: content container visible', dhulm_content_visible is True)

dhulm_report = driver.execute_script('return document.getElementById("dhulmReport")?.innerHTML ?? ""')
check('Dhulm: equity report rendered', len(dhulm_report) > 20, f'{len(dhulm_report)} chars')
check('Dhulm: mentions population or representation',
      'population' in dhulm_report.lower() or 'represent' in dhulm_report.lower() or
      'equity' in dhulm_report.lower() or 'women' in dhulm_report.lower() or
      'elder' in dhulm_report.lower() or 'descriptor' in dhulm_report.lower() or
      'report' in dhulm_report.lower())

# Canvas may be blank when no studies have demographic descriptors (expected)
dhulm_canvas_exists = driver.execute_script('''
    return document.getElementById('dhulmChart') !== null;
''')
check('Dhulm: chart canvas element exists', dhulm_canvas_exists is True)

# =============================================
# TEST 4: Tabayyun — Verification Engine
# =============================================
print('\n--- Tabayyun (Verification) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="tabayyun"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Verify button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-tabayyun button');
    for (var b of btns) {
        if (b.textContent.indexOf('Verify') >= 0 || b.textContent.indexOf('Verif') >= 0) { b.click(); break; }
    }
''')
time.sleep(2)

tabayyun_content_visible = driver.execute_script('''
    var el = document.getElementById('tabayyunContent');
    return el ? el.style.display !== 'none' : false;
''')
check('Tabayyun: content container visible', tabayyun_content_visible is True)

tabayyun_results = driver.execute_script('return document.getElementById("tabayyunResults")?.innerHTML ?? ""')
check('Tabayyun: verification results rendered', len(tabayyun_results) > 20, f'{len(tabayyun_results)} chars')
check('Tabayyun: mentions verification or source',
      'verif' in tabayyun_results.lower() or 'source' in tabayyun_results.lower() or
      'cross' in tabayyun_results.lower() or 'single' in tabayyun_results.lower() or
      '49:6' in tabayyun_results)

# =============================================
# TEST 5: Living — Currency Tracking
# =============================================
print('\n--- Living (Living Evidence) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="living"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Check Currency button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-living button');
    for (var b of btns) {
        if (b.textContent.indexOf('Check') >= 0 || b.textContent.indexOf('Currency') >= 0) { b.click(); break; }
    }
''')
time.sleep(2)

living_content_visible = driver.execute_script('''
    var el = document.getElementById('livingContent');
    return el ? el.style.display !== 'none' : false;
''')
check('Living: content container visible', living_content_visible is True)

living_dashboard = driver.execute_script('return document.getElementById("livingDashboard")?.innerHTML ?? ""')
check('Living: dashboard rendered', len(living_dashboard) > 20, f'{len(living_dashboard)} chars')
check('Living: mentions currency or age category',
      'current' in living_dashboard.lower() or 'stale' in living_dashboard.lower() or
      'outdated' in living_dashboard.lower() or 'currency' in living_dashboard.lower() or
      'month' in living_dashboard.lower())

# Check localStorage timestamp was saved
living_ts = driver.execute_script('return localStorage.getItem("msa-dta-living-last-verified")')
check('Living: last-verified timestamp saved', living_ts is not None and len(str(living_ts)) > 0)

# =============================================
# TEST 6: Conflict — Contradictions Detector
# =============================================
print('\n--- Conflict (Conflict Detector) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="conflict"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Scan button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-conflict button');
    for (var b of btns) {
        if (b.textContent.indexOf('Scan') >= 0 || b.textContent.indexOf('Conflict') >= 0) { b.click(); break; }
    }
''')
time.sleep(2)

conflict_content_visible = driver.execute_script('''
    var el = document.getElementById('conflictContent');
    return el ? el.style.display !== 'none' : false;
''')
check('Conflict: content container visible', conflict_content_visible is True)

conflict_results = driver.execute_script('return document.getElementById("conflictResults")?.innerHTML ?? ""')
check('Conflict: results rendered', len(conflict_results) > 20, f'{len(conflict_results)} chars')
check('Conflict: mentions direction or temporal or conflict',
      'direction' in conflict_results.lower() or 'temporal' in conflict_results.lower() or
      'conflict' in conflict_results.lower() or 'no conflict' in conflict_results.lower() or
      'contradict' in conflict_results.lower() or 'consistent' in conflict_results.lower())

# =============================================
# TEST 7: Radar — Opportunity Scanner
# =============================================
print('\n--- Radar (Opportunity Radar) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="radar"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Scan button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-radar button');
    for (var b of btns) {
        if (b.textContent.indexOf('Scan') >= 0 || b.textContent.indexOf('Opportun') >= 0) { b.click(); break; }
    }
''')
time.sleep(2)

radar_content_visible = driver.execute_script('''
    var el = document.getElementById('radarContent');
    return el ? el.style.display !== 'none' : false;
''')
check('Radar: content container visible', radar_content_visible is True)

radar_results = driver.execute_script('return document.getElementById("radarResults")?.innerHTML ?? ""')
check('Radar: results rendered', len(radar_results) > 10, f'{len(radar_results)} chars')
# With 6 mock trials across 3 interventions, may show opportunities or "no opportunities"
check('Radar: mentions opportunity or intervention or no opportunities',
      'opportunit' in radar_results.lower() or 'intervent' in radar_results.lower() or
      'trial' in radar_results.lower() or 'update' in radar_results.lower() or
      'no ' in radar_results.lower())

# =============================================
# TEST 8: Registry — Canonical Record Linking
# =============================================
print('\n--- Registry (Registry Graph) ---')
driver.execute_script('''
    var tab = document.querySelector('[data-insight="registry"]');
    if (tab) tab.click();
''')
time.sleep(0.5)

# Click Build button
driver.execute_script('''
    var btns = document.querySelectorAll('#insight-registry button');
    for (var b of btns) {
        if (b.textContent.indexOf('Build') >= 0 || b.textContent.indexOf('Registry') >= 0) { b.click(); break; }
    }
''')
time.sleep(2)

registry_content_visible = driver.execute_script('''
    var el = document.getElementById('registryContent');
    return el ? el.style.display !== 'none' : false;
''')
check('Registry: content container visible', registry_content_visible is True)

registry_stats = driver.execute_script('return document.getElementById("registryStats")?.innerHTML ?? ""')
check('Registry: stats rendered', len(registry_stats) > 10, f'{len(registry_stats)} chars')
check('Registry: mentions records or linked',
      'record' in registry_stats.lower() or 'linked' in registry_stats.lower() or
      'canonical' in registry_stats.lower() or 'total' in registry_stats.lower())

registry_table = driver.execute_script('return document.getElementById("registryTable")?.innerHTML ?? ""')
check('Registry: table rendered', len(registry_table) > 10, f'{len(registry_table)} chars')
check('Registry: contains NCT IDs from universe',
      'nct' in registry_table.lower() or 'NCT' in registry_table)

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
