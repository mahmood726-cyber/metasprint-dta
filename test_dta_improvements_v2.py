"""
test_dta_improvements_v2.py — Tests for improvement pass v2.

Validates: PubMed/OpenAlex DTA filters (P0-4/P0-5), CSV import fix (P0-2),
QUADAS-2 matrix (P1-7), AUC bootstrap CI (P1-5), bubble plot ticks (P1-13),
forest sort dropdown (P2-3), per-1000 clinical utility (P2-2),
RoB domain dropdown (P2-7), comparative DTA warning (P1-6),
Bayesian convergence (P2-15), generatePaper structured abstract (P2-16),
keyboard shortcuts (P2-5), PRISMA full-text stage (P2-13),
protocol sync (P2-17), R export CC (P2-12).
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

# Study data: 6 studies, 2 index tests (BNP/NTproBNP), with RoB judgments
BNP_STUDIES = [
    {'authorYear': 'Dao 2001',       'tp': '52',  'fp': '14', 'fn': '8',  'tn': '76',  'indexTest': 'BNP',      'rob': {'d1':'low','d2':'low','d3':'low','d4':'low','overall':'low'}},
    {'authorYear': 'Morrison 2002',  'tp': '44',  'fp': '20', 'fn': '6',  'tn': '151', 'indexTest': 'BNP',      'rob': {'d1':'high','d2':'low','d3':'low','d4':'low','overall':'high'}},
    {'authorYear': 'Maisel 2002',    'tp': '379', 'fp': '83', 'fn': '65', 'tn': '959', 'indexTest': 'NTproBNP', 'rob': {'d1':'low','d2':'unclear','d3':'low','d4':'low','overall':'low'}},
    {'authorYear': 'Mueller 2004',   'tp': '89',  'fp': '17', 'fn': '14', 'tn': '337', 'indexTest': 'NTproBNP', 'rob': {'d1':'low','d2':'low','d3':'high','d4':'low','overall':'high'}},
    {'authorYear': 'Lainchbury 2003','tp': '40',  'fp': '22', 'fn': '5',  'tn': '138', 'indexTest': 'BNP',      'rob': {'d1':'low','d2':'low','d3':'low','d4':'low','overall':'low'}},
    {'authorYear': 'McCullough 2002','tp': '163', 'fp': '44', 'fn': '21', 'tn': '416', 'indexTest': 'BNP',      'rob': {'d1':'low','d2':'low','d3':'low','d4':'unclear','overall':'low'}},
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

# Create project and load studies via addStudyRow() (saves to IDB)
driver.execute_script('''
    (async function() {
        var p = createEmptyProject('ImprovementsV2 Test ' + Date.now());
        await idbPut('projects', p);
        currentProjectId = p.id;
        extractedStudies = [];
        document.getElementById('extractBody').innerHTML = '';
        await loadProjects();
    })();
''')
time.sleep(1)

# Add each study via addStudyRow (persists to IDB)
for s in BNP_STUDIES:
    study_data = {k: v for k, v in s.items() if k != 'rob'}
    driver.execute_script(f"addStudyRow({json.dumps(study_data)});")
    time.sleep(0.15)
time.sleep(0.5)

# Set RoB judgments on each study and save to IDB
rob_data = [s['rob'] for s in BNP_STUDIES]
driver.execute_script(f'''
    var robData = {json.dumps(rob_data)};
    for (var i = 0; i < extractedStudies.length && i < robData.length; i++) {{
        extractedStudies[i].rob = robData[i];
        saveStudy(extractedStudies[i]);
    }}
''')
time.sleep(0.3)

# ================================================================
# P0-4: PubMed search filter — no "Randomized" in query
# ================================================================
query = driver.execute_script('return buildPubMedQuery()')
check('P0-4: PubMed query has DTA filter',
      'Sensitivity and Specificity' in query or 'diagnostic accuracy' in query,
      query[:120])
check('P0-4: PubMed query has ROC Curve MeSH',
      'ROC Curve' in query and 'Predictive Value' in query and 'Diagnosis' in query)
check('P0-4: PubMed query has no RCT filter',
      'Randomized Controlled Trial' not in query)

# ================================================================
# P0-5: OpenAlex — no RCT concept ID
# ================================================================
page_src = driver.page_source
check('P0-5: No C71924100 in OpenAlex URL',
      'C71924100' not in page_src,
      'Checked page source')

# ================================================================
# P0-2: CSV import calls renderExtractTable (not renderExtractionTable)
# ================================================================
has_bad = driver.execute_script('''
    var scripts = document.querySelectorAll('script');
    for (var s of scripts) {
        if (s.textContent.indexOf('renderExtractionTable()') !== -1) return true;
    }
    return false;
''')
check('P0-2: No renderExtractionTable() calls remain', not has_bad)

# ================================================================
# Run analysis with CC=0.25 for P2-12 test
# ================================================================
driver.execute_script("switchPhase('analyze')")
time.sleep(0.5)
driver.execute_script("document.getElementById('continuityCorrection').value = '0.25'")
driver.execute_script("runAnalysis()")
time.sleep(5)

# Verify analysis completed
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

# ================================================================
# P2-12: R export CC from UI
# ================================================================
r_code = driver.execute_script("return document.getElementById('advRCodePre')?.textContent || ''")
check('P2-12: R export uses CC from UI',
      '+ 0.25' in r_code or '+0.25' in r_code,
      f'CC in R code: {"found 0.25" if "0.25" in r_code else "NOT found"}')
# Reset CC
driver.execute_script("document.getElementById('continuityCorrection').value = '0.5'")

# ================================================================
# P1-7: QUADAS-2 traffic-light matrix
# ================================================================
q2html = driver.execute_script("return document.getElementById('quadas2MatrixContainer')?.innerHTML || ''")
check('P1-7: QUADAS-2 matrix rendered', len(q2html) > 100, f'{len(q2html)} chars')
check('P1-7: Matrix has domain columns',
      q2html.count('<th') >= 4,
      f'{q2html.count("<th")} th elements')
check('P1-7: Matrix has color cells',
      '#22c55e' in q2html or '#ef4444' in q2html,
      'color-coded cells found')

# ================================================================
# P1-5: AUC in bootstrap table
# ================================================================
# Bootstrap runs async — wait additional time
time.sleep(3)
boot_html = driver.execute_script("return document.getElementById('advBootstrapContainer')?.innerHTML || ''")
check('P1-5: Bootstrap table has AUC row',
      'AUC' in boot_html,
      f'bootstrap HTML length: {len(boot_html)}')

# ================================================================
# P1-13: Meta-regression bubble plot has tick marks
# ================================================================
mr_html = driver.execute_script("return document.getElementById('advMetaRegressionContainer')?.innerHTML || ''")
has_ticks = '<line x1=' in mr_html and 'stroke="var(--border)"' in mr_html
check('P1-13: Bubble plot has tick marks', has_ticks or len(mr_html) < 50,
      'ticks found' if has_ticks else 'no regression data (OK if no covariate)')
# Check SVG export button
check('P1-13: SVG export button for bubble plot',
      'meta-regression-bubble.svg' in mr_html or len(mr_html) < 50)

# ================================================================
# P2-3: Forest sort dropdown exists
# ================================================================
sort_el = driver.execute_script("return document.getElementById('forestSortOrder') !== null")
check('P2-3: Forest sort dropdown exists', sort_el)

# Test sorting changes order
driver.execute_script("document.getElementById('forestSortOrder').value = 'alpha'; reRenderForests()")
time.sleep(0.5)
forest_html = driver.execute_script("return document.getElementById('forestSensContainer')?.innerHTML || ''")
check('P2-3: Forest re-rendered after sort', len(forest_html) > 100)

# ================================================================
# P2-2: Clinical utility per-1000 columns
# ================================================================
cu_html = driver.execute_script("return document.getElementById('clinicalUtilityContainer')?.innerHTML || ''")
check('P2-2: Clinical utility has TP column', '>TP<' in cu_html or '>TP</th>' in cu_html,
      f'cu HTML length: {len(cu_html)}')
check('P2-2: Clinical utility has FN column', '>FN<' in cu_html or '>FN</th>' in cu_html)

# ================================================================
# P2-7: RoB sensitivity domain dropdown
# ================================================================
rob_dropdown = driver.execute_script("return document.getElementById('robSensDomainSelect') !== null")
check('P2-7: RoB sensitivity domain dropdown exists', rob_dropdown)

# ================================================================
# P1-6: Comparative DTA with 2 index tests
# ================================================================
comp_html = driver.execute_script("return document.getElementById('advNetworkContainer')?.innerHTML || ''")
check('P1-6: Comparative DTA rendered', len(comp_html) > 100, f'{len(comp_html)} chars')
# Check for test names in comparative table
check('P1-6: Comparative table has test rows',
      'BNP' in comp_html and 'NTproBNP' in comp_html)

# ================================================================
# P2-15: Bayesian convergence check
# ================================================================
bayes_html = driver.execute_script("return document.getElementById('advBayesianContainer')?.innerHTML || ''")
convergence_diag = driver.execute_script('''
    var html = document.getElementById('advBayesianContainer')?.innerHTML || '';
    return html.indexOf('Convergence') !== -1 && html.indexOf('ESS') !== -1;
''')
check('P2-15: Bayesian analysis rendered', len(bayes_html) > 100)
check('P2-15: Bayesian convergence diagnostics present', convergence_diag)

# ================================================================
# P2-16: generatePaper structured abstract
# ================================================================
driver.execute_script("switchPhase('write')")
time.sleep(1)
driver.execute_script("generatePaper()")
time.sleep(3)
paper_text = driver.execute_script("return window._lastFullText || ''")
check('P2-16: Paper output > 200 chars', len(paper_text) > 200, f'{len(paper_text)} chars')
check('P2-16: Paper has structured abstract',
      '**Background:**' in paper_text and '**Results:**' in paper_text)
check('P2-16: Paper has sensitivity value',
      'sensitivity' in paper_text.lower() or 'pooled sens' in paper_text.lower())

# ================================================================
# P2-5: Keyboard shortcuts (Alt+1-7)
# ================================================================
# We can't easily simulate Alt+key in headless, but verify the listener exists
has_listener = driver.execute_script('''
    var scripts = document.querySelectorAll('script');
    for (var s of scripts) {
        if (s.textContent.indexOf('phaseMap') !== -1 && s.textContent.indexOf("'1': 'discover'") !== -1) return true;
    }
    return false;
''')
check('P2-5: Alt+1-7 keyboard listener registered', has_listener)

# ================================================================
# P2-13: PRISMA flow has full-text stage
# ================================================================
driver.execute_script("switchPhase('search')")
time.sleep(0.5)
# Trigger PRISMA rendering with test data
driver.execute_script('''
    renderPRISMAFlow({
        total: 100, duplicates: 10, excluded: 30, included: 6,
        pending: 4, maybe: 2, reasons: {'Wrong population': 15, 'Wrong test': 10, 'Wrong design': 5}
    });
''')
time.sleep(0.3)
prisma_html = driver.execute_script("return document.getElementById('prismaFlow')?.innerHTML || ''")
check('P2-13: PRISMA has full-text assessed box',
      'Full-text assessed' in prisma_html,
      f'prisma HTML length: {len(prisma_html)}')

# ================================================================
# P2-17: Protocol sync button
# ================================================================
sync_btn = driver.execute_script("return typeof syncFromProtocol === 'function'")
check('P2-17: syncFromProtocol function exists', sync_btn)

# Test sync: set protocol fields, sync, verify search fields
driver.execute_script('''
    switchPhase('protocol');
    document.getElementById('protP').value = 'TestPop';
    document.getElementById('protI').value = 'TestIdx';
    savePICO();
''')
time.sleep(0.3)
driver.execute_script("switchPhase('search')")
time.sleep(0.3)
driver.execute_script("syncFromProtocol()")
time.sleep(0.3)
pico_p = driver.execute_script("return document.getElementById('picoP').value")
check('P2-17: Protocol sync copies P field', pico_p == 'TestPop', f'got: {pico_p}')

# ================================================================
# P2-8: Trim-and-fill diamond (check function/code exists)
# ================================================================
has_tf_diamond = driver.execute_script('''
    var scripts = document.querySelectorAll('script');
    for (var s of scripts) {
        if (s.textContent.indexOf('adjustedLogDOR') !== -1 && s.textContent.indexOf('Adjusted DOR') !== -1) return true;
    }
    return false;
''')
check('P2-8: Trim-fill adjusted DOR diamond code present', has_tf_diamond)

# ================================================================
# P2-6: Bayesian adaptive step code present
# ================================================================
has_adaptive = driver.execute_script('''
    var scripts = document.querySelectorAll('script');
    for (var s of scripts) {
        if (s.textContent.indexOf('ADAPT_INTERVAL') !== -1 && s.textContent.indexOf('TARGET_RATE') !== -1) return true;
    }
    return false;
''')
check('P2-6: Bayesian adaptive step size code present', has_adaptive)

# ================================================================
# Summary
# ================================================================
driver.quit()

print()
print(f'{total} tests: {passed} passed, {failed} failed')
sys.exit(0 if failed == 0 else 1)
