#!/usr/bin/env python
"""Selenium tests for OA Discovery pipeline in MetaSprint DTA."""
import sys, os, json, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

passed = failed = 0
def check(name, cond, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print(f'  \u2713 {name}')
    else:
        failed += 1
        print(f'  \u2717 {name} {("— " + str(detail)) if detail else ""}')

# Setup
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--disable-gpu')
opts.add_argument('--no-sandbox')
opts.add_argument('--window-size=1400,900')
driver = webdriver.Chrome(options=opts)

html_path = os.path.join(os.path.dirname(__file__), 'metasprint-dta.html')
driver.get('file:///' + html_path.replace('\\', '/'))
time.sleep(2)

# Dismiss onboarding if present
driver.execute_script("""
    const ob = document.getElementById('onboardingOverlay');
    if (ob) ob.style.display = 'none';
    localStorage.setItem('msa-dta-onboarded', '1');
""")
time.sleep(0.5)

print('\n--- OA Discovery: UI Rendering ---')

# Test 1: Panel exists
panel = driver.execute_script("return document.getElementById('oaDiscoveryPanel') !== null")
check('OA Discovery panel exists', panel)

# Test 2: Panel starts collapsed
body_open = driver.execute_script("return document.getElementById('oaBody').classList.contains('open')")
check('Panel starts collapsed', not body_open)

# Test 3: Toggle opens panel
driver.execute_script("toggleOAPanel()")
time.sleep(0.3)
body_open = driver.execute_script("return document.getElementById('oaBody').classList.contains('open')")
check('Toggle opens panel', body_open)

# Test 4: Search inputs exist
cond_exists = driver.execute_script("return document.getElementById('oaCondition') !== null")
test_exists = driver.execute_script("return document.getElementById('oaIndexTest') !== null")
btn_exists = driver.execute_script("return document.getElementById('oaSearchBtn') !== null")
check('Search inputs exist', cond_exists and test_exists and btn_exists)

# Test 5: Results area initially hidden
area_hidden = driver.execute_script("return document.getElementById('oaResultsArea').style.display === 'none'")
check('Results area initially hidden', area_hidden)

print('\n--- OA Discovery: Back-Calculator ---')

# Test 6: Algebraic method (OSPREY example)
result = driver.execute_script("""
    const r = backCalc2x2(0.419, 0.979, 252, { ppv: 0.867, npv: 0.838 });
    return r;
""")
check('Algebraic: returns result', result is not None)
if result:
    check('Algebraic: TP=26', result['tp'] == 26, f"got {result['tp']}")
    check('Algebraic: FP=4', result['fp'] == 4, f"got {result['fp']}")
    check('Algebraic: FN=36', result['fn'] == 36, f"got {result['fn']}")
    check('Algebraic: TN=186', result['tn'] == 186, f"got {result['tn']}")
    check('Algebraic: method=algebraic', result['method'] == 'algebraic', f"got {result['method']}")
    check('Algebraic: confidence=high', result['confidence'] == 'high', f"got {result['confidence']}")
    total = result['tp'] + result['fp'] + result['fn'] + result['tn']
    check('Algebraic: sum=252', total == 252, f"got {total}")

# Test 7: CI-width method
result2 = driver.execute_script("""
    const r = backCalc2x2(0.419, 0.979, 252, {
        sensLCI: 0.2965, sensUCI: 0.5422,
        specLCI: 0.9452, specUCI: 0.9937
    });
    return r;
""")
check('CI-width: returns result', result2 is not None)
if result2:
    check('CI-width: method=ci-width', result2['method'] == 'ci-width', f"got {result2['method']}")
    check('CI-width: TP reasonable (15-55 range)', 15 <= result2['tp'] <= 55, f"got {result2['tp']}")
    check('CI-width: sum close to 252', abs(result2['tp'] + result2['fp'] + result2['fn'] + result2['tn'] - 252) <= 30,
          f"got {result2['tp'] + result2['fp'] + result2['fn'] + result2['tn']}")

# Test 8: Prevalence fallback
result3 = driver.execute_script("""
    const r = backCalc2x2(0.85, 0.92, 200);
    return r;
""")
check('Prevalence fallback: returns result', result3 is not None)
if result3:
    check('Prevalence fallback: method=prevalence-est', result3['method'] == 'prevalence-est', f"got {result3['method']}")
    check('Prevalence fallback: confidence=low', result3['confidence'] == 'low', f"got {result3['confidence']}")
    check('Prevalence fallback: sum=200', result3['tp'] + result3['fp'] + result3['fn'] + result3['tn'] == 200)

# Test 9: Null inputs return null
result4 = driver.execute_script("return backCalc2x2(null, 0.9, 100)")
check('Null sensitivity returns null', result4 is None)

# Test 10: Percentage inputs auto-normalize
result5 = driver.execute_script("""
    const r = backCalc2x2(85, 92, 200, { ppv: 90, npv: 88 });
    return r;
""")
check('Percentage inputs normalize correctly', result5 is not None and result5['method'] == 'algebraic')

print('\n--- OA Discovery: Abstract Extraction ---')

# Test 11: Extract from typical DTA abstract
abResult = driver.execute_script("""
    return extractDTAFromAbstract(
        'The sensitivity was 85.2% (95% CI 78.1-91.3%) and specificity was 92.0% (95% CI 88.0-95.0%). ' +
        'The positive predictive value was 88.5% and negative predictive value was 90.1%. ' +
        'Among 450 patients with suspected disease...'
    );
""")
check('Abstract extraction: returns result', abResult is not None)
if abResult:
    check('Abstract: sensitivity ~0.852', abResult.get('sensitivity') is not None and abs(abResult['sensitivity'] - 0.852) < 0.01,
          f"got {abResult.get('sensitivity')}")
    check('Abstract: specificity ~0.92', abResult.get('specificity') is not None and abs(abResult['specificity'] - 0.92) < 0.01,
          f"got {abResult.get('specificity')}")
    check('Abstract: sensLCI ~0.781', abResult.get('sensLCI') is not None and abs(abResult['sensLCI'] - 0.781) < 0.01,
          f"got {abResult.get('sensLCI')}")
    check('Abstract: ppv ~0.885', abResult.get('ppv') is not None and abs(abResult['ppv'] - 0.885) < 0.01,
          f"got {abResult.get('ppv')}")
    check('Abstract: totalN=450', abResult.get('totalN') == 450, f"got {abResult.get('totalN')}")

# Test 12: Direct TP/FP/FN/TN extraction
directResult = driver.execute_script("""
    return extractDTAFromAbstract(
        'There were 45 true positives, 5 false positives, 8 false negatives, and 142 true negatives.'
    );
""")
check('Direct 2x2: extracts TP/FP/FN/TN', directResult is not None and directResult.get('directTP') == 45)
if directResult:
    check('Direct 2x2: FP=5', directResult.get('directFP') == 5)
    check('Direct 2x2: FN=8', directResult.get('directFN') == 8)
    check('Direct 2x2: TN=142', directResult.get('directTN') == 142)

# Test 13: Empty/irrelevant abstract returns null
nullResult = driver.execute_script("return extractDTAFromAbstract('This study examined treatment outcomes.')")
check('Irrelevant abstract returns null', nullResult is None)

print('\n--- OA Discovery: Deduplication ---')

# Test 14: Dedup merges by NCT ID
dedupResult = driver.execute_script("""
    const ct = [{ nctId: 'NCT001', title: 'Test A', hasResults: true, source: 'ctgov' }];
    const pm = [{ nctId: 'NCT001', title: 'Test A trial', pmid: '12345', abstract: 'some text', source: 'pubmed' }];
    const oa = [{ doi: 'xxx', title: 'Test A trial results', source: 'openalex' }];
    const result = deduplicateOAResults(ct, pm, oa);
    return { count: result.length, first: result[0] };
""")
check('Dedup: merges CT.gov+PubMed by NCT', dedupResult['count'] <= 2)
if dedupResult.get('first'):
    check('Dedup: enriches with PMID', dedupResult['first'].get('pmid') == '12345')
    check('Dedup: enriches with abstract', dedupResult['first'].get('abstract') == 'some text')

# Test 15: DTA trial scoring
score1 = driver.execute_script("""
    return scoreDTATrial({ title: 'Diagnostic accuracy of troponin', abstract: 'sensitivity and specificity of the test with reference standard biopsy', hasResults: true });
""")
score2 = driver.execute_script("""
    return scoreDTATrial({ title: 'A systematic review and meta-analysis', abstract: 'We searched databases for eligible studies' });
""")
check('Scoring: DTA study scores high', score1 >= 70, f"got {score1}")
check('Scoring: Review scores low', score2 <= 40, f"got {score2}")

print('\n--- OA Discovery: Import Bridge ---')

# Test 16: Import mock studies
driver.execute_script("""
    // Setup project — use the actual let-scoped variables, not window
    currentProjectId = currentProjectId || 'test-project';
    extractedStudies = extractedStudies || [];

    // Stub saveStudy to avoid IDB errors in test
    window._origSaveStudy = typeof saveStudy === 'function' ? saveStudy : null;
    saveStudy = function(s) { /* no-op in test */ };

    // Stub switchPhase to avoid side effects
    window._origSwitchPhase = typeof switchPhase === 'function' ? switchPhase : null;
    switchPhase = function(p) { /* no-op in test */ };

    // Mock discovered studies
    oaDiscoveredStudies = [
        { title: 'Study Alpha', year: 2023, nctId: 'NCT111', pmid: '111', doi: '',
          backCalc: { tp: 26, fp: 4, fn: 36, tn: 186, method: 'algebraic', confidence: 'high' },
          sources: ['ctgov', 'pubmed'], _selected: true },
        { title: 'Study Beta', year: 2024, nctId: 'NCT222', pmid: '', doi: '',
          backCalc: { tp: 50, fp: 10, fn: 15, tn: 125, method: 'ci-width', confidence: 'medium' },
          sources: ['ctgov'], _selected: true },
        { title: 'Study Gamma', year: 2022, nctId: '', pmid: '333', doi: '',
          backCalc: null, _selected: false }
    ];
""")

before_count = driver.execute_script("return extractedStudies.length")
driver.execute_script("""
    document.getElementById('oaIndexTest').value = 'Troponin';
    importOAStudies();
""")
time.sleep(0.5)
after_count = driver.execute_script("return extractedStudies.length")
check('Import: adds 2 studies (not 3 — no backCalc for Gamma)', after_count - before_count == 2,
      f"before={before_count}, after={after_count}")

# Check imported study structure
last = driver.execute_script("return extractedStudies[extractedStudies.length - 1]")
check('Import: has tp/fp/fn/tn as strings', last.get('tp') == '50' and last.get('tn') == '125')
check('Import: has indexTest', last.get('indexTest') == 'Troponin')
check('Import: notes contain method', 'ci-width' in (last.get('notes') or ''))
check('Import: notes contain NCT', 'NCT222' in (last.get('notes') or ''))

# Test 17: OA panel keyboard accessibility
driver.execute_script("""
    const toggle = document.getElementById('oaToggle');
    toggle.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
""")
check('Panel header has tabindex', driver.execute_script("return document.getElementById('oaToggle').tabIndex") == 0)

print('\n--- OA Discovery: Reconstruct Abstract ---')

# Test 18: OpenAlex inverted index reconstruction
abstract = driver.execute_script("""
    return reconstructOAAbstract({
        'The': [0, 5], 'test': [1], 'showed': [2], 'high': [3], 'accuracy': [4],
        'sensitivity': [6], 'was': [7], '90%': [8]
    });
""")
check('Reconstruct abstract from inverted index', abstract == 'The test showed high accuracy The sensitivity was 90%',
      f"got: {abstract}")

# Test 19: NCT extraction from text
nct = driver.execute_script("return extractNCTFromText('This trial (NCT04054661) evaluated...')")
check('NCT extraction from text', nct == 'NCT04054661', f"got {nct}")

nct2 = driver.execute_script("return extractNCTFromText('No trial number here')")
check('NCT extraction returns null for no match', nct2 is None)

print('\n--- OA Discovery: Example Topics Dropdown ---')

# Test 20: Dropdown exists with optgroups
dropdown_exists = driver.execute_script("return document.getElementById('oaExampleTopics') !== null")
check('Example topics dropdown exists', dropdown_exists)

option_count = driver.execute_script("return document.getElementById('oaExampleTopics').options.length")
check('Dropdown has 48+ options (plus placeholder)', option_count >= 49, f"got {option_count}")

optgroup_count = driver.execute_script("return document.getElementById('oaExampleTopics').querySelectorAll('optgroup').length")
check('Dropdown has category optgroups', optgroup_count >= 9, f"got {optgroup_count}")

# Test 21: Selecting a topic fills both inputs
driver.execute_script("applyOAExampleTopic('sepsis|procalcitonin')")
cond_val = driver.execute_script("return document.getElementById('oaCondition').value")
test_val = driver.execute_script("return document.getElementById('oaIndexTest').value")
check('Example topic fills condition', cond_val == 'sepsis', f"got '{cond_val}'")
check('Example topic fills index test', test_val == 'procalcitonin', f"got '{test_val}'")

# Test 22: Dropdown resets after selection
sel_val = driver.execute_script("return document.getElementById('oaExampleTopics').value")
check('Dropdown resets after selection', sel_val == '', f"got '{sel_val}'")

# Test 23: Empty selection does not clear inputs
driver.execute_script("""
    document.getElementById('oaCondition').value = 'test condition';
    document.getElementById('oaIndexTest').value = 'test index';
    applyOAExampleTopic('');
""")
cond_after = driver.execute_script("return document.getElementById('oaCondition').value")
check('Empty selection preserves inputs', cond_after == 'test condition')

# =============================================
# Summary
# =============================================
driver.quit()

print(f'\n{"=" * 50}')
print(f'  OA Discovery Tests: {passed} passed, {failed} failed')
print(f'{"=" * 50}')
sys.exit(1 if failed > 0 else 0)
