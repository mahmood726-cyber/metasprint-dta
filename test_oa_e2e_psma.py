#!/usr/bin/env python
"""End-to-end test: OA Discovery for PSMA PET/CT in prostate cancer.
Runs the full pipeline, captures results, and compares against known published data."""
import sys, os, json, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Setup
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--disable-gpu')
opts.add_argument('--no-sandbox')
opts.add_argument('--window-size=1400,900')
driver = webdriver.Chrome(options=opts)

html_path = os.path.join(os.path.dirname(__file__), 'metasprint-dta.html')
driver.get('file:///' + html_path.replace('\\', '/'))
time.sleep(3)

# Dismiss onboarding
driver.execute_script("""
    const ob = document.getElementById('onboardingOverlay');
    if (ob) ob.style.display = 'none';
    localStorage.setItem('msa-dta-onboarded', '1');
""")
time.sleep(0.5)

print('='*60)
print('  OA Discovery E2E: PSMA PET for Prostate Cancer')
print('='*60)

# Navigate to Discover tab and open OA panel
driver.execute_script("switchPhase('discover')")
time.sleep(0.5)
driver.execute_script("toggleOAPanel()")
time.sleep(0.3)

# Enter search
driver.execute_script("""
    document.getElementById('oaCondition').value = 'prostate cancer';
    document.getElementById('oaIndexTest').value = 'PSMA PET';
""")

print('\n[1] Starting OA Discovery search...')
print('    Condition: prostate cancer')
print('    Index test: PSMA PET')

# Run search
driver.execute_script("runOADiscovery()")

# Wait for completion (poll status, max 120s)
for i in range(120):
    time.sleep(2)
    status = driver.execute_script("return document.getElementById('oaStatus').textContent")
    btn_disabled = driver.execute_script("return document.getElementById('oaSearchBtn').disabled")
    if i % 5 == 0:
        print(f'    [{i*2}s] {status[:100]}')
    if not btn_disabled and 'Done' in status:
        break
    if not btn_disabled and 'Error' in status:
        print(f'    ERROR: {status}')
        break

print(f'\n[2] Search complete: {status[:120]}')

# Get results
results = driver.execute_script("""
    return oaDiscoveredStudies.map(t => ({
        nctId: t.nctId || '',
        title: (t.title || '').substring(0, 80),
        sources: t.sources || [t.source],
        enrollment: t.enrollment || 0,
        hasResults: !!t.hasResults,
        dtaScore: t.dtaScore || 0,
        hasCTgovMetrics: !!(t.ctgovMetrics && (t.ctgovMetrics.sensitivity != null || t.ctgovMetrics.specificity != null)),
        hasAbstractMetrics: !!(t.abstractMetrics && (t.abstractMetrics.sensitivity != null || t.abstractMetrics.specificity != null)),
        sens: (t.ctgovMetrics || t.abstractMetrics || {}).sensitivity,
        spec: (t.ctgovMetrics || t.abstractMetrics || {}).specificity,
        backCalc: t.backCalc || t.direct2x2 || null
    }));
""")

print(f'\n[3] Total studies found: {len(results)}')
print(f'    With CT.gov results: {sum(1 for r in results if r["hasResults"])}')
print(f'    With CT.gov DTA metrics: {sum(1 for r in results if r["hasCTgovMetrics"])}')
print(f'    With abstract DTA metrics: {sum(1 for r in results if r["hasAbstractMetrics"])}')
print(f'    With extractable 2x2: {sum(1 for r in results if r["backCalc"])}')

# Show all studies with extracted data
extractable = [r for r in results if r['backCalc']]
print(f'\n[4] Extractable studies ({len(extractable)}):')
print(f'    {"NCT ID":<15} {"N":>5} {"Sens":>7} {"Spec":>7} {"TP":>4} {"FP":>4} {"FN":>4} {"TN":>4} {"Method":<15} {"Conf":<6}')
print('    ' + '-'*80)
for r in extractable:
    bc = r['backCalc']
    sens_str = f"{r['sens']*100:.1f}%" if r['sens'] else '?'
    spec_str = f"{r['spec']*100:.1f}%" if r['spec'] else '?'
    print(f"    {r['nctId']:<15} {r['enrollment']:>5} {sens_str:>7} {spec_str:>7} {bc['tp']:>4} {bc['fp']:>4} {bc['fn']:>4} {bc['tn']:>4} {bc['method']:<15} {bc['confidence']:<6}")

# Show all studies with CT.gov results (even without DTA metrics)
with_results = [r for r in results if r['hasResults']]
print(f'\n[5] Studies with CT.gov results ({len(with_results)}):')
for r in with_results:
    has_dta = 'DTA' if r['hasCTgovMetrics'] else 'no-DTA'
    print(f"    {r['nctId']:<15} N={r['enrollment']:<5} {has_dta:>6}  {r['title'][:60]}")

# Import extractable studies and run analysis
if extractable:
    print(f'\n[6] Importing {len(extractable)} studies...')
    driver.execute_script("""
        // Select all extractable
        oaDiscoveredStudies.forEach(t => {
            if (t.backCalc || t.direct2x2) t._selected = true;
        });
        importOAStudies();
    """)
    time.sleep(1)

    # Check extract tab
    study_count = driver.execute_script("return extractedStudies.length")
    print(f'    Extracted studies in table: {study_count}')

    # Show the studies
    studies = driver.execute_script("""
        return extractedStudies.map(s => ({
            name: s.authorYear,
            tp: parseInt(s.tp), fp: parseInt(s.fp), fn: parseInt(s.fn), tn: parseInt(s.tn),
            sens: parseInt(s.tp) / Math.max(1, parseInt(s.tp) + parseInt(s.fn)),
            spec: parseInt(s.tn) / Math.max(1, parseInt(s.tn) + parseInt(s.fp))
        }));
    """)

    print(f'\n[7] Imported 2x2 data:')
    print(f'    {"Study":<45} {"TP":>4} {"FP":>4} {"FN":>4} {"TN":>4}  {"Sens":>7} {"Spec":>7}')
    print('    ' + '-'*85)
    for s in studies:
        print(f"    {s['name'][:44]:<45} {s['tp']:>4} {s['fp']:>4} {s['fn']:>4} {s['tn']:>4}  {s['sens']*100:>6.1f}% {s['spec']*100:>6.1f}%")

    # Try to run bivariate analysis
    print(f'\n[8] Running bivariate GLMM analysis...')
    driver.execute_script("switchPhase('analyze')")
    time.sleep(1)

    # Check if analysis can run (need at least 4 studies for bivariate)
    if study_count >= 4:
        try:
            driver.execute_script("""
                const btn = document.querySelector('#analyzeMainBtn') || document.querySelector('[onclick*="runAnalysis"]');
                if (btn) btn.click();
            """)
            time.sleep(5)

            # Check for results
            summary = driver.execute_script("""
                const el = document.getElementById('analysisSummary');
                return el ? el.innerText.substring(0, 500) : 'No summary found';
            """)
            print(f'    Analysis summary:\n    {summary[:300]}')
        except Exception as e:
            print(f'    Analysis error: {e}')
    else:
        print(f'    Need >= 4 studies for bivariate GLMM, got {study_count}')

print(f'\n{"="*60}')
print(f'  E2E test complete.')
print(f'{"="*60}')

driver.quit()
