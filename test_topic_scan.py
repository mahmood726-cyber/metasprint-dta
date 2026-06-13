#!/usr/bin/env python
"""Scan multiple DTA topics through the OA pipeline to find the best one for validation."""
import sys, os, time, io, json
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
driver.execute_script("switchPhase('discover')")
time.sleep(0.5)
driver.execute_script("toggleOAPanel()")
time.sleep(0.3)

topics = [
    ("coronary artery disease", "CT-FFR"),
    ("diabetic retinopathy", "artificial intelligence screening"),
    ("pulmonary embolism", "CT pulmonary angiography"),
    ("breast cancer", "contrast-enhanced mammography"),
    ("appendicitis", "ultrasound"),
    ("tuberculosis", "Xpert MTB/RIF"),
    ("melanoma", "dermoscopy"),
    ("liver fibrosis", "elastography"),
    ("deep vein thrombosis", "ultrasound"),
    ("COVID-19", "rapid antigen test"),
]

print("=" * 90)
print(f"  {'Condition':<30} {'Index Test':<30} {'Total':>6} {'DTA':>5} {'2x2':>5} {'CTgov':>6} {'Hi-C':>5}")
print("=" * 90)

results = []
for condition, test in topics:
    driver.execute_script(f"""
        document.getElementById('oaCondition').value = {json.dumps(condition)};
        document.getElementById('oaIndexTest').value = {json.dumps(test)};
    """)
    driver.execute_script("runOADiscovery()")

    for i in range(90):
        time.sleep(2)
        status = driver.execute_script("return document.getElementById('oaStatus').textContent")
        btn_disabled = driver.execute_script("return document.getElementById('oaSearchBtn').disabled")
        if not btn_disabled and ('Done' in status or 'Error' in status):
            break

    stats = driver.execute_script("""
        const s = oaDiscoveredStudies;
        return {
            total: s.length,
            withDTA: s.filter(x => x.abstractMetrics || x.ctgovMetrics).length,
            with2x2: s.filter(x => x.backCalc || x.direct2x2).length,
            withCTgovResults: s.filter(x => x.ctgovMetrics && (x.ctgovMetrics.sensitivity != null)).length,
            highConf: s.filter(x => (x.backCalc || x.direct2x2 || {}).confidence === 'high').length,
            methods: {}
        };
    """)

    # Count methods
    methods = driver.execute_script("""
        const counts = {};
        oaDiscoveredStudies.forEach(t => {
            const d = t.direct2x2 || t.backCalc;
            if (d) counts[d.method] = (counts[d.method] || 0) + 1;
        });
        return counts;
    """)

    row = {**stats, 'condition': condition, 'test': test, 'methods': methods}
    results.append(row)

    method_str = ', '.join(f'{k}:{v}' for k, v in (methods or {}).items())
    print(f"  {condition:<30} {test:<30} {stats['total']:>6} {stats['withDTA']:>5} {stats['with2x2']:>5} {stats['withCTgovResults']:>6} {stats['highConf']:>5}  {method_str}")

print("=" * 90)
print("\nBest candidates (sorted by extractable 2x2 count):")
results.sort(key=lambda x: (-x['highConf'], -x['with2x2'], -x['withDTA']))
for i, r in enumerate(results[:5]):
    print(f"  {i+1}. {r['condition']} + {r['test']}: {r['with2x2']} extractable ({r['highConf']} high-conf), {r['total']} total")

driver.quit()
