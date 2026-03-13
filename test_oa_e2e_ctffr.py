#!/usr/bin/env python
"""End-to-end test: OA Discovery for CT-FFR in Coronary Artery Disease.
Published reference: Li et al (2016): Sens 89%, Spec 71% (k=5)
Gonzalez-Doncel (2022): Sens 88%, Spec 80%
"""
import sys, os, json, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

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

def run_topic(condition, index_test):
    driver.execute_script("switchPhase('discover')")
    time.sleep(0.3)
    # Reset extracted studies
    driver.execute_script("extractedStudies = [];")

    driver.execute_script(f"""
        document.getElementById('oaCondition').value = {json.dumps(condition)};
        document.getElementById('oaIndexTest').value = {json.dumps(index_test)};
    """)

    driver.execute_script("runOADiscovery()")
    for i in range(120):
        time.sleep(2)
        status = driver.execute_script("return document.getElementById('oaStatus').textContent")
        btn_disabled = driver.execute_script("return document.getElementById('oaSearchBtn').disabled")
        if i % 10 == 0 and i > 0:
            print(f'    [{i*2}s] {status[:80]}')
        if not btn_disabled and ('Done' in status or 'Error' in status):
            break

    results = driver.execute_script("""
        return oaDiscoveredStudies.map(t => ({
            title: (t.title || '').substring(0, 70),
            match: t._indexTestMatch || 'unknown',
            isReview: !!t._isReview,
            selected: !!t._selected,
            enrollment: t.enrollment || 0,
            sens: (t.ctgovMetrics || t.abstractMetrics || {}).sensitivity,
            spec: (t.ctgovMetrics || t.abstractMetrics || {}).specificity,
            backCalc: t.backCalc || t.direct2x2 || null,
            hasDTA: !!(t.abstractMetrics && (t.abstractMetrics.sensitivity != null))
        }));
    """)

    total = len(results)
    extractable = [r for r in results if r['backCalc']]
    matched = [r for r in extractable if r['match'] == 'match' and not r['isReview']]
    selected = [r for r in results if r['selected']]

    print(f'\n    Total: {total} | DTA metrics: {sum(1 for r in results if r["hasDTA"])} | Extractable: {len(extractable)} | Matched: {len(matched)} | Auto-selected: {len(selected)}')

    print(f'\n    {"Rel":<10} {"Sel":>3} {"N":>5} {"Sens":>7} {"Spec":>7} {"Method":<15} Title')
    print(f'    {"-"*105}')
    for r in extractable:
        bc = r['backCalc']
        sens_str = f"{r['sens']*100:.1f}%" if r['sens'] else '?'
        spec_str = f"{r['spec']*100:.1f}%" if r['spec'] else '?'
        tag = 'review' if r['isReview'] else r['match']
        sel = 'Y' if r['selected'] else ' '
        print(f"    {tag:<10} [{sel}] {r['enrollment']:>5} {sens_str:>7} {spec_str:>7} {bc['method']:<15} {r['title'][:55]}")

    # Import auto-selected and run analysis
    if len(selected) >= 4:
        driver.execute_script("importOAStudies();")
        time.sleep(1)
        study_count = driver.execute_script("return extractedStudies.length")
        print(f'\n    Imported {study_count} studies, running bivariate...')

        driver.execute_script("switchPhase('analyze')")
        time.sleep(1)
        driver.execute_script("""
            const btn = document.querySelector('#analyzeMainBtn') || document.querySelector('[onclick*="runAnalysis"]');
            if (btn) btn.click();
        """)
        time.sleep(5)

        summary = driver.execute_script("""
            const el = document.getElementById('analysisSummary');
            return el ? el.innerText.substring(0, 600) : 'No summary';
        """)
        # Extract key values
        for line in summary.split('\n'):
            l = line.strip()
            if l and any(k in l for k in ['Pooled Sens', 'Sens 95%', 'Pooled Spec', 'Spec 95%', 'DOR', 'Method']):
                print(f'    {l}')
    elif len(selected) > 0:
        driver.execute_script("importOAStudies();")
        time.sleep(0.5)
        study_count = driver.execute_script("return extractedStudies.length")
        print(f'\n    Imported {study_count} studies (need >= 4 for bivariate)')
    else:
        print(f'\n    No auto-selected studies')

    return {'total': total, 'extractable': len(extractable), 'matched': len(matched), 'selected': len(selected)}

# ============================
print('='*70)
print('  Multi-Topic Screening Validation')
print('='*70)

topics = [
    ("coronary artery disease", "CT-FFR", "Li 2016: Sens 89%, Spec 71%; Gonzalez-Doncel 2022: Sens 88%, Spec 80%"),
    ("prostate cancer", "PSMA PET", "Perera 2019: Sens 75%, Spec 99%; Jeet 2023 BCR: Sens 84%, Spec 97%"),
    ("appendicitis", "ultrasound", "D'Souza 2023: Sens 81%, Spec 87%; EP-POCUS 2018: Sens 84%, Spec 91%"),
]

for condition, test, reference in topics:
    print(f'\n{"="*70}')
    print(f'  {condition} + {test}')
    print(f'  Published: {reference}')
    print(f'{"="*70}')
    stats = run_topic(condition, test)

print(f'\n{"="*70}')
print(f'  All topics complete.')
print(f'{"="*70}')

driver.quit()
