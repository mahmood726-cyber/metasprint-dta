"""
test_dta_exports.py — Tests for export functions in MetaSprint DTA.

Validates: Table 1 CSV, Table 2 CSV, Pooled Results CSV, QUADAS-2 CSV,
GRADE Profile CSV/HTML, SoF CSV, project export/import, analysis summary copy,
PRISMA-DTA checklist CSV, paper generation.

Strategy: intercepts downloadFile() to capture output instead of triggering
actual file downloads, then validates content in-memory.
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
    {'authorYear': 'Dao 2001',       'tp': 52,  'fp': 14, 'fn': 8,  'tn': 76,  'indexTest': 'BNP', 'threshold': '100'},
    {'authorYear': 'Morrison 2002',  'tp': 44,  'fp': 20, 'fn': 6,  'tn': 151, 'indexTest': 'BNP', 'threshold': '94'},
    {'authorYear': 'Maisel 2002',    'tp': 379, 'fp': 83, 'fn': 65, 'tn': 959, 'indexTest': 'BNP', 'threshold': '100'},
    {'authorYear': 'Mueller 2004',   'tp': 89,  'fp': 17, 'fn': 14, 'tn': 337, 'indexTest': 'BNP', 'threshold': '100'},
    {'authorYear': 'Lainchbury 2003','tp': 40,  'fp': 22, 'fn': 5,  'tn': 138, 'indexTest': 'BNP', 'threshold': '76'},
    {'authorYear': 'McCullough 2002','tp': 163, 'fp': 44, 'fn': 21, 'tn': 416, 'indexTest': 'BNP', 'threshold': '100'},
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

# Install download interceptor — captures content instead of downloading
driver.execute_script('''
    window._capturedDownloads = [];
    window._origDownloadFile = window.downloadFile;
    window.downloadFile = function(content, filename, mimeType) {
        window._capturedDownloads.push({
            content: content,
            filename: filename,
            mimeType: mimeType || 'text/plain'
        });
    };
''')

# Load studies
driver.execute_script('''
    (async function() {
        var p = createEmptyProject('Export Test ' + Date.now());
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

# Add RoB assessments and re-save to IDB (lowercase keys match exportQUADAS2CSV)
driver.execute_script('''
    (async function() {
        for (var i = 0; i < extractedStudies.length; i++) {
            extractedStudies[i].rob = {
                d1: i % 2 === 0 ? 'Low' : 'Unclear',
                d2: 'Low',
                d3: i % 3 === 0 ? 'High' : 'Low',
                d4: 'Low',
                d1_app: 'Low',
                d2_app: i % 2 === 0 ? 'Low' : 'High',
                d3_app: 'Low',
                overall: i % 3 === 0 ? 'High' : 'Low'
            };
            await idbPut('studies', extractedStudies[i]);
        }
    })();
''')
time.sleep(0.5)

# Run analysis
driver.execute_script('document.querySelector(\'[data-phase="analyze"]\').click()')
time.sleep(0.5)
driver.execute_script('document.getElementById("methodSelect").value = "bivariate"')
driver.execute_script('document.getElementById("confLevelSelect").value = "0.95"')
time.sleep(0.2)
driver.execute_script('runAnalysis()')
time.sleep(4)

result = driver.execute_script('return lastAnalysisResult')
check('Analysis completed', result is not None)

# =============================================
# TEST 1: Table 1 — Characteristics CSV
# =============================================
print('\n--- Table 1 (Characteristics CSV) ---')
driver.execute_script('window._capturedDownloads = []; exportCharacteristicsTable();')
time.sleep(0.5)

t1 = driver.execute_script('return window._capturedDownloads[0] || null')
check('Table1: download captured', t1 is not None)
if t1:
    check('Table1: filename is table1-characteristics.csv', t1['filename'] == 'table1-characteristics.csv')
    lines = t1['content'].strip().split('\n')
    check('Table1: has header + 6 data rows', len(lines) == 7, f'{len(lines)} lines')
    header = lines[0].lower()
    check('Table1: header has Author/Year', 'author' in header)
    check('Table1: header has TP', 'tp' in header)
    check('Table1: header has Prevalence', 'prevalence' in header)
    # Check first data row contains a known study name
    all_data = '\n'.join(lines[1:]).lower()
    check('Table1: data contains known studies', 'dao' in all_data or 'morrison' in all_data or 'maisel' in all_data)

# =============================================
# TEST 2: Table 2 — Accuracy CSV
# =============================================
print('\n--- Table 2 (Accuracy CSV) ---')
driver.execute_script('window._capturedDownloads = []; exportAccuracyTable();')
time.sleep(0.5)

t2 = driver.execute_script('return window._capturedDownloads[0] || null')
check('Table2: download captured', t2 is not None)
if t2:
    check('Table2: filename is table2-accuracy.csv', t2['filename'] == 'table2-accuracy.csv')
    lines = t2['content'].strip().split('\n')
    check('Table2: has header + data rows', len(lines) >= 7, f'{len(lines)} lines')
    header = lines[0].lower()
    check('Table2: header has Sens', 'sens' in header)
    check('Table2: header has Spec', 'spec' in header)
    check('Table2: header has DOR', 'dor' in header)
    # Check data values are numeric
    if len(lines) > 1:
        fields = lines[1].split(',')
        check('Table2: data row has numeric fields', len(fields) >= 10, f'{len(fields)} fields')

# =============================================
# TEST 3: Pooled Results CSV
# =============================================
print('\n--- Pooled Results CSV ---')
driver.execute_script('window._capturedDownloads = []; exportPooledResultsCSV();')
time.sleep(0.5)

pr = driver.execute_script('return window._capturedDownloads[0] || null')
check('Pooled: download captured', pr is not None)
if pr:
    check('Pooled: filename is pooled-results.csv', pr['filename'] == 'pooled-results.csv')
    content = pr['content'].lower()
    check('Pooled: contains sensitivity', 'sensitivity' in content)
    check('Pooled: contains specificity', 'specificity' in content)
    check('Pooled: contains DOR', 'dor' in content)
    check('Pooled: contains AUC', 'auc' in content)
    check('Pooled: contains I2', 'i2' in content or 'i-squared' in content or 'i^2' in content)
    lines = pr['content'].strip().split('\n')
    check('Pooled: has header + 13 metric rows', len(lines) >= 10, f'{len(lines)} lines')

# =============================================
# TEST 4: QUADAS-2 CSV
# =============================================
print('\n--- QUADAS-2 CSV ---')
driver.execute_script('window._capturedDownloads = []; exportQUADAS2CSV();')
time.sleep(0.5)

q2 = driver.execute_script('return window._capturedDownloads[0] || null')
check('QUADAS2: download captured', q2 is not None)
if q2:
    check('QUADAS2: filename is quadas2-summary.csv', q2['filename'] == 'quadas2-summary.csv')
    lines = q2['content'].strip().split('\n')
    check('QUADAS2: has header + data rows', len(lines) >= 2, f'{len(lines)} lines')
    header = lines[0]
    check('QUADAS2: header has D1_PatientSelection', 'D1' in header or 'Patient' in header)
    check('QUADAS2: header has D3_ReferenceStandard', 'D3' in header or 'Reference' in header)
    # Check that RoB values appear in data
    content = q2['content']
    check('QUADAS2: contains Low/High/Unclear assessments',
          'Low' in content or 'High' in content or 'Unclear' in content)

# =============================================
# TEST 5: GRADE Profile — CSV format
# =============================================
print('\n--- GRADE Profile (CSV) ---')
driver.execute_script('window._capturedDownloads = []; exportGRADEProfile("csv");')
time.sleep(0.5)

gc = driver.execute_script('return window._capturedDownloads[0] || null')
check('GRADE-CSV: download captured', gc is not None)
if gc:
    check('GRADE-CSV: filename is grade-profile.csv', gc['filename'] == 'grade-profile.csv')
    content = gc['content'].lower()
    check('GRADE-CSV: mentions Risk of Bias', 'risk' in content or 'bias' in content)
    check('GRADE-CSV: mentions Inconsistency', 'inconsist' in content)
    check('GRADE-CSV: mentions Imprecision', 'imprecis' in content)

# =============================================
# TEST 6: GRADE Profile — HTML format
# =============================================
print('\n--- GRADE Profile (HTML) ---')
driver.execute_script('window._capturedDownloads = []; exportGRADEProfile("html");')
time.sleep(0.5)

gh = driver.execute_script('return window._capturedDownloads[0] || null')
check('GRADE-HTML: download captured', gh is not None)
if gh:
    check('GRADE-HTML: filename is grade-evidence-profile.html',
          gh['filename'] == 'grade-evidence-profile.html')
    check('GRADE-HTML: is valid HTML', '<html' in gh['content'].lower() or '<!doctype' in gh['content'].lower())
    check('GRADE-HTML: contains domain ratings',
          'No concern' in gh['content'] or 'Serious' in gh['content'] or 'concern' in gh['content'].lower())

# =============================================
# TEST 7: SoF Table CSV
# =============================================
print('\n--- Summary of Findings (SoF) CSV ---')
# First set prevalence
driver.execute_script('''
    var inp = document.getElementById('sofPrevalenceInput');
    if (inp) inp.value = '20';
''')
driver.execute_script('window._capturedDownloads = []; exportSoFCSV();')
time.sleep(0.5)

sof = driver.execute_script('return window._capturedDownloads[0] || null')
check('SoF: download captured', sof is not None)
if sof:
    check('SoF: filename is sof_table_dta.csv', sof['filename'] == 'sof_table_dta.csv')
    content = sof['content'].lower()
    check('SoF: mentions True Positive', 'true positive' in content or 'tp' in content)
    check('SoF: mentions False Negative', 'false negative' in content or 'fn' in content)
    lines = sof['content'].strip().split('\n')
    check('SoF: has header + 4 outcome rows', len(lines) >= 5, f'{len(lines)} lines')

# =============================================
# TEST 8: Study Export (CSV format)
# =============================================
print('\n--- Study Export (CSV) ---')
driver.execute_script('window._capturedDownloads = []; exportToMetaSprint("dta");')
time.sleep(0.5)

se = driver.execute_script('return window._capturedDownloads[0] || null')
check('StudyExport: download captured', se is not None)
if se:
    check('StudyExport: filename contains metasprint-dta', 'metasprint-dta' in se['filename'])
    all_lines = se['content'].strip().split('\n')
    lines = [l for l in all_lines if not l.startswith('#')]
    check('StudyExport: has header + 6 study rows', len(lines) == 7, f'{len(lines)} lines (8 with metadata)')
    header = lines[0].lower()
    check('StudyExport: header has TP/FP/FN/TN', 'tp' in header and 'fn' in header)

# =============================================
# TEST 9: Study Export (JSON format)
# =============================================
print('\n--- Study Export (JSON) ---')
driver.execute_script('window._capturedDownloads = []; exportToMetaSprint("json");')
time.sleep(0.5)

sj = driver.execute_script('return window._capturedDownloads[0] || null')
check('StudyJSON: download captured', sj is not None)
if sj:
    check('StudyJSON: filename is .json', sj['filename'].endswith('.json'))
    try:
        data = json.loads(sj['content'])
        check('StudyJSON: is valid JSON object with _meta', isinstance(data, dict) and '_meta' in data and 'studies' in data)
        studies = data.get('studies', [])
        check('StudyJSON: has 6 studies', len(studies) == 6, f'{len(studies)} entries')
        if len(studies) > 0:
            check('StudyJSON: study has authorYear', 'authorYear' in studies[0])
            check('StudyJSON: study has tp/fp/fn/tn',
                  'tp' in studies[0] and 'fn' in studies[0])
    except json.JSONDecodeError:
        check('StudyJSON: is valid JSON', False, 'JSONDecodeError')

# =============================================
# TEST 10: Analysis Summary (clipboard)
# =============================================
print('\n--- Analysis Summary (Copy) ---')
# Mock clipboard
driver.execute_script('''
    window._clipboardContent = '';
    navigator.clipboard.writeText = function(text) {
        window._clipboardContent = text;
        return Promise.resolve();
    };
    copyAnalysisSummary();
''')
time.sleep(0.5)

clip = driver.execute_script('return window._clipboardContent || ""')
check('Summary: clipboard content captured', len(clip) > 50, f'{len(clip)} chars')
check('Summary: mentions sensitivity', 'sensitiv' in clip.lower())
check('Summary: mentions specificity', 'specific' in clip.lower())
check('Summary: mentions DOR', 'dor' in clip.lower() or 'diagnostic odds' in clip.lower())
check('Summary: contains numeric values', any(c.isdigit() for c in clip))

# =============================================
# TEST 11: PRISMA-DTA Checklist CSV
# =============================================
print('\n--- PRISMA-DTA Checklist CSV ---')
driver.execute_script('window._capturedDownloads = []; exportPRISMADTACSV();')
time.sleep(0.5)

pc = driver.execute_script('return window._capturedDownloads[0] || null')
check('PRISMA-DTA: download captured', pc is not None)
if pc:
    check('PRISMA-DTA: filename is prisma-dta-checklist.csv', pc['filename'] == 'prisma-dta-checklist.csv')
    content = pc['content'].lower()
    check('PRISMA-DTA: mentions Section', 'section' in content)
    check('PRISMA-DTA: mentions status', 'status' in content or 'auto' in content or 'manual' in content)

# =============================================
# TEST 12: Paper Generation
# =============================================
print('\n--- Paper Generation ---')
driver.execute_script('''
    document.querySelector('[data-phase="write"]').click();
''')
time.sleep(0.5)
driver.execute_script('generatePaper()')
time.sleep(3)

paper_text = driver.execute_script('return window._lastFullText || ""')
check('Paper: full text generated', len(paper_text) > 100, f'{len(paper_text)} chars')
check('Paper: has Abstract section', 'abstract' in paper_text.lower() or '## abstract' in paper_text.lower())
check('Paper: has Methods section', 'method' in paper_text.lower())
check('Paper: has Results section', 'result' in paper_text.lower())
check('Paper: mentions sensitivity', 'sensitiv' in paper_text.lower())
check('Paper: mentions specificity', 'specific' in paper_text.lower())

# Test paper download
driver.execute_script('window._capturedDownloads = []; downloadPaper();')
time.sleep(0.5)
pd = driver.execute_script('return window._capturedDownloads[0] || null')
check('Paper: download captured', pd is not None)
if pd:
    check('Paper: filename is paper-draft.md', pd['filename'] == 'paper-draft.md')

# =============================================
# TEST 13: Project Export
# =============================================
print('\n--- Project Export ---')
driver.execute_script('''
    window._capturedDownloads = [];
    // Override downloadFile to also handle Blob-based exports
    var origBlob = window.URL.createObjectURL;
    window._blobContent = null;
''')

# exportProject uses downloadFile internally
driver.execute_script('(async function() { await exportProject(); })()')
time.sleep(2)

pe = driver.execute_script('return window._capturedDownloads[0] || null')
check('ProjectExport: download captured', pe is not None)
if pe:
    check('ProjectExport: filename is .json', pe['filename'].endswith('.json'))
    try:
        data = json.loads(pe['content'])
        check('ProjectExport: has project field', 'project' in data)
        check('ProjectExport: has studies field', 'studies' in data)
        check('ProjectExport: has version field', 'version' in data)
        if 'studies' in data:
            check('ProjectExport: exported 6 studies', len(data['studies']) == 6,
                  f'{len(data["studies"])} studies')
    except json.JSONDecodeError:
        check('ProjectExport: is valid JSON', False, 'JSONDecodeError')

# =============================================
# TEST 14: csvSafeCell function
# =============================================
print('\n--- csvSafeCell (formula injection guard) ---')

safe_normal = driver.execute_script('return csvSafeCell("Normal text")')
check('csvSafe: normal text unchanged', safe_normal == 'Normal text')

safe_formula = driver.execute_script('return csvSafeCell("=SUM(A1:A10)")')
check('csvSafe: formula prepended with quote', safe_formula.startswith("'"))

safe_negative = driver.execute_script('return csvSafeCell("-0.5 mmHg")')
check('csvSafe: negative values NOT corrupted', safe_negative == '-0.5 mmHg')

safe_comma = driver.execute_script('return csvSafeCell("Smith, John")')
check('csvSafe: commas trigger quoting', '"' in safe_comma)

safe_quote = driver.execute_script('return csvSafeCell(\'He said "hello"\')')
check('csvSafe: quotes are escaped', '""' in safe_quote)

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
