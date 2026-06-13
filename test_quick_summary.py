#!/usr/bin/env python
"""Quick run of 3 topics — extract pooled bivariate results from auto-selected only."""
import sys, os, json, time, io
if "pytest" not in sys.modules:
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

topics = [
    ("coronary artery disease", "CT-FFR"),
    ("prostate cancer", "PSMA PET"),
    ("appendicitis", "ultrasound"),
]

print('='*100)
print(f'  {"Topic":<40} {"k":>3} {"Sens":>8} {"Sens CI":>16} {"Spec":>8} {"Spec CI":>16} {"DOR":>8}')
print('='*100)

all_results = []

for condition, test in topics:
    # Reset — clear extractedStudies array AND IndexedDB so loadStudies() doesn't reload old data
    driver.execute_script("""
        extractedStudies.forEach(s => idbDelete('studies', s.id));
        extractedStudies = [];
        lastAnalysisResult = null;
        switchPhase('discover');
    """)
    time.sleep(0.3)

    driver.execute_script(f"""
        document.getElementById('oaCondition').value = {json.dumps(condition)};
        document.getElementById('oaIndexTest').value = {json.dumps(test)};
    """)
    driver.execute_script("runOADiscovery()")

    for i in range(120):
        time.sleep(2)
        status = driver.execute_script("return document.getElementById('oaStatus').textContent")
        btn_disabled = driver.execute_script("return document.getElementById('oaSearchBtn').disabled")
        if not btn_disabled and ('Done' in status or 'Error' in status):
            break

    selected_count = driver.execute_script("return oaDiscoveredStudies.filter(t => t._selected).length")
    total_extractable = driver.execute_script("return oaDiscoveredStudies.filter(t => t.backCalc || t.direct2x2).length")

    if selected_count < 2:
        print(f'  {condition + " + " + test:<40} {selected_count:>3} auto-selected ({total_extractable} extractable) — need >= 2')
        all_results.append({'topic': f'{condition} + {test}', 'k': selected_count, 'status': 'insufficient'})
        continue

    driver.execute_script("importOAStudies();")
    time.sleep(0.5)
    k = driver.execute_script("return extractedStudies.length")

    driver.execute_script("switchPhase('analyze')")
    time.sleep(1)
    driver.execute_script("runAnalysis()")
    time.sleep(8)  # give bivariate GLMM time

    r = driver.execute_script("""
        try {
            const r = lastAnalysisResult || {};
            return {
                k: extractedStudies.length,
                pooledSens: r.pooledSens,
                pooledSpec: r.pooledSpec,
                sensCI: r.sensCI,
                specCI: r.specCI,
                dor: r.dor,
                dorCI: r.dorCI,
                method: r.method || 'unknown'
            };
        } catch(e) { return { error: e.message }; }
    """)

    if r and r.get('pooledSens') is not None:
        s = f"{r['pooledSens']*100:.1f}%"
        sp = f"{r['pooledSpec']*100:.1f}%"
        sci = f"[{r['sensCI'][0]*100:.1f}, {r['sensCI'][1]*100:.1f}]" if r.get('sensCI') else '-'
        spci = f"[{r['specCI'][0]*100:.1f}, {r['specCI'][1]*100:.1f}]" if r.get('specCI') else '-'
        dor = f"{r['dor']:.1f}" if r.get('dor') else '-'
        print(f'  {condition + " + " + test:<40} {r["k"]:>3} {s:>8} {sci:>16} {sp:>8} {spci:>16} {dor:>8}')
        all_results.append({
            'topic': f'{condition} + {test}', 'k': r['k'],
            'sens': r['pooledSens'], 'spec': r['pooledSpec'],
            'sensCI': r.get('sensCI'), 'specCI': r.get('specCI'),
            'dor': r.get('dor'), 'method': r.get('method')
        })
    else:
        print(f'  {condition + " + " + test:<40}  Error or no result: {r}')
        all_results.append({'topic': f'{condition} + {test}', 'k': k, 'status': 'error', 'detail': str(r)})

print('='*100)
print(f'\n  Published reference values:')
print(f'  {"CT-FFR (Li 2016 / Gonzalez-Doncel 2022)":<48} {"89%":>8} {"":>16} {"71-80%":>8}')
print(f'  {"PSMA PET (Perera 2019 / Jeet 2023)":<48} {"75-84%":>8} {"":>16} {"97-99%":>8}')
print(f'  {"US appendicitis (Defined 2019 / van Randen 2008)":<48} {"81-86%":>8} {"":>16} {"81-87%":>8}')
print('='*100)

# Summary comparison
print(f'\n  VALIDATION SUMMARY:')
refs = {
    'coronary artery disease + CT-FFR': {'sens': (0.88, 0.89), 'spec': (0.71, 0.80)},
    'prostate cancer + PSMA PET': {'sens': (0.75, 0.84), 'spec': (0.97, 0.99)},
    'appendicitis + ultrasound': {'sens': (0.78, 0.86), 'spec': (0.81, 0.91)},
}
for res in all_results:
    if res.get('sens') is not None:
        ref = refs.get(res['topic'], {})
        sens_range = ref.get('sens', (0, 1))
        spec_range = ref.get('spec', (0, 1))
        sens_ok = sens_range[0] - 0.15 <= res['sens'] <= sens_range[1] + 0.15
        spec_ok = spec_range[0] - 0.15 <= res['spec'] <= spec_range[1] + 0.15
        sens_pct = res['sens'] * 100
        spec_pct = res['spec'] * 100
        s_check = 'OK' if sens_ok else 'OUTSIDE'
        p_check = 'OK' if spec_ok else 'OUTSIDE'
        print(f'  {res["topic"]:<40} Sens {sens_pct:5.1f}% [{s_check}]  Spec {spec_pct:5.1f}% [{p_check}]  k={res["k"]} ({res["method"]})')

driver.quit()
