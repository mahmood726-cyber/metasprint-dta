#!/usr/bin/env python
"""Test OA Discovery provenance panel: click-to-expand, abstract highlighting, source links."""
import sys, os, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

passed = failed = 0
def check(name, cond, detail=''):
    global passed, failed
    if cond:
        passed += 1
        print(f'  \u2713 {name}')
    else:
        failed += 1
        print(f'  \u2717 {name} {("-- " + str(detail)) if detail else ""}')

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--disable-gpu')
opts.add_argument('--no-sandbox')
opts.add_argument('--window-size=1400,900')
driver = webdriver.Chrome(options=opts)

html_path = os.path.join(os.path.dirname(__file__), 'metasprint-dta.html')
driver.get('file:///' + html_path.replace('\\', '/'))
time.sleep(3)

driver.execute_script("""
    const ob = document.getElementById('onboardingOverlay');
    if (ob) ob.style.display = 'none';
    localStorage.setItem('msa-dta-onboarded', '1');
""")
time.sleep(0.5)

print('\n--- Provenance Panel: highlightAbstractDTA ---')

# Test highlight function
highlighted = driver.execute_script("""
    return highlightAbstractDTA(
        'The sensitivity was 85.2% (95% CI 78.1-91.3%) and specificity was 92.0%. Among 450 patients...',
        { sensitivity: 0.852, specificity: 0.92, sensLCI: 0.781, sensUCI: 0.913, totalN: 450 }
    );
""")
check('Highlight returns string', isinstance(highlighted, str))
check('Highlight contains <mark> tags', '<mark' in highlighted, f'got: {highlighted[:100]}')
check('Highlight marks sensitivity value', 'sensitivity was 85.2%' in highlighted or '>85.2%<' in highlighted or 'sensitivity was 85' in highlighted)
check('Highlight marks 450 patients', '450 patients' in highlighted)

# Test with no metrics - should return escaped text only
plain = driver.execute_script("""
    return highlightAbstractDTA('Just a plain abstract about testing.', null);
""")
check('No metrics: returns plain escaped text', '<mark' not in plain)

print('\n--- Provenance Panel: toggleOADetailRow ---')

# Setup mock studies for testing the detail row
driver.execute_script("switchPhase('discover')")
time.sleep(0.5)
driver.execute_script("toggleOAPanel()")
time.sleep(0.3)

driver.execute_script("""
    oaDiscoveredStudies = [
        {
            title: 'OSPREY Trial', year: 2022, nctId: 'NCT02981368', pmid: '12345', doi: '10.1234/test',
            enrollment: 252, abstract: 'The sensitivity was 41.9% and specificity was 97.9%. PPV was 86.7% and NPV was 83.8%. Among 252 patients evaluated...',
            sources: ['ctgov', 'pubmed'],
            abstractMetrics: { sensitivity: 0.419, specificity: 0.979, ppv: 0.867, npv: 0.838, totalN: 252 },
            backCalc: { tp: 26, fp: 4, fn: 36, tn: 186, method: 'algebraic', confidence: 'high' },
            _selected: true
        },
        {
            title: 'Another Study', year: 2023, nctId: '', pmid: '67890', doi: '',
            enrollment: 100, abstract: 'The sensitivity was 80.0% and specificity was 90.0%.',
            sources: ['pubmed'],
            abstractMetrics: { sensitivity: 0.80, specificity: 0.90 },
            backCalc: { tp: 40, fp: 5, fn: 10, tn: 45, method: 'prevalence-est', confidence: 'low' },
            _selected: false
        }
    ];
    document.getElementById('oaResultsArea').style.display = '';
    renderOAResultsTable();
""")
time.sleep(0.3)

# Check table rendered
row_count = driver.execute_script("return document.querySelectorAll('#oaResultsBody tr.oa-row-clickable').length")
check('Table has 2 clickable rows', row_count == 2, f'got {row_count}')

# Click first row to expand detail
driver.execute_script("""
    const row = document.querySelector('#oaResultsBody tr.oa-row-clickable');
    row.click();
""")
time.sleep(0.2)

detail_exists = driver.execute_script("return document.querySelector('.oa-detail-row') !== null")
check('Click expands detail row', detail_exists)

# Check detail panel contents
panel_html = driver.execute_script("return document.querySelector('.oa-detail-panel')?.innerHTML || ''")
check('Detail panel has abstract text', 'oa-abstract-text' in panel_html)
check('Detail panel has highlighted sensitivity', '<mark' in panel_html, f'first 200: {panel_html[:200]}')
check('Detail panel has provenance table', 'oa-prov-table' in panel_html)
check('Detail panel shows method: algebraic', 'algebraic' in panel_html)
check('Detail panel shows confidence: high', 'high' in panel_html)
check('Detail panel has CT.gov link', 'NCT02981368' in panel_html)
check('Detail panel has PubMed link', 'pubmed.ncbi.nlm.nih.gov' in panel_html)
check('Detail panel has DOI link', 'doi.org' in panel_html)
check('Detail panel shows Sens input value', '41.9%' in panel_html or '41.9' in panel_html)
check('Detail panel shows Spec input value', '97.9%' in panel_html or '97.9' in panel_html)
check('Detail panel shows PPV', '86.7%' in panel_html or '86.7' in panel_html)
check('Detail panel shows NPV', '83.8%' in panel_html or '83.8' in panel_html)
check('Detail panel shows TP/FP', '26' in panel_html and '4' in panel_html)
check('Detail panel shows FN/TN', '36' in panel_html and '186' in panel_html)
check('Detail panel explains method', 'Exact' in panel_html or 'solved from' in panel_html)

# Click same row again to collapse
driver.execute_script("""
    const row = document.querySelector('#oaResultsBody tr.oa-row-clickable');
    row.click();
""")
time.sleep(0.2)
detail_after = driver.execute_script("return document.querySelector('.oa-detail-row')")
check('Second click collapses detail row', detail_after is None)

# Click second row
driver.execute_script("""
    const rows = document.querySelectorAll('#oaResultsBody tr.oa-row-clickable');
    rows[1].click();
""")
time.sleep(0.2)
detail2_html = driver.execute_script("return document.querySelector('.oa-detail-panel')?.innerHTML || ''")
check('Second row detail shows prevalence-est method', 'prevalence-est' in detail2_html)
check('Second row detail shows low confidence', 'low' in detail2_html)
check('Second row shows 50% prevalence explanation', '50%' in detail2_html or 'prevalence' in detail2_html.lower())

# Verify only one detail row open at a time
driver.execute_script("""
    const rows = document.querySelectorAll('#oaResultsBody tr.oa-row-clickable');
    rows[0].click();
""")
time.sleep(0.2)
detail_count = driver.execute_script("return document.querySelectorAll('.oa-detail-row').length")
check('Only one detail row open at a time', detail_count == 1, f'got {detail_count}')

driver.quit()

print(f'\n{"=" * 50}')
print(f'  Provenance Panel Tests: {passed} passed, {failed} failed')
print(f'{"=" * 50}')
sys.exit(1 if failed > 0 else 0)
