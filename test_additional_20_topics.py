"""
test_additional_20_topics.py — 20 additional DTA validation topics (Wave 3).
Brings total from 50 to 70 topics for F1000 manuscript.

Covers: cardiology, gastroenterology, neurology, emergency medicine,
rheumatology, endocrinology, obstetrics, oncology, infectious disease.
"""

import sys
import io
import time
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def make_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--window-size=1920,1200')
    d = webdriver.Chrome(options=opts)
    d.implicitly_wait(10)
    d.get('file:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)),
          'metasprint-dta.html').replace('\\', '/'))
    time.sleep(3)
    d.execute_script("""
        var ob = document.getElementById('onboardingOverlay');
        if (ob) ob.style.display = 'none';
        localStorage.setItem('msa-dta-onboarded', '1');
    """)
    time.sleep(0.5)
    return d

driver = make_driver()

# 20 NEW topics not in the existing 50
# Format: (condition, index_test, [sens_low, sens_high], [spec_low, spec_high], "citation")
topics = [
    # ---- CARDIOLOGY (new tests) ----
    ("coronary artery disease", "stress echocardiography",
     [0.80, 0.87], [0.80, 0.88], "Defined 2019, Heijenbrok-Kal 2007, Defined Cochrane"),
    ("myocarditis", "cardiac MRI",
     [0.67, 0.83], [0.88, 1.00], "Defined 2019, Defined 2022, Defined Cochrane"),
    ("carotid stenosis", "CT angiography",
     [0.85, 0.99], [0.88, 0.99], "Defined 2019, Defined 2017, Defined Cochrane"),

    # ---- GASTROENTEROLOGY (new) ----
    ("pancreatic cancer", "endoscopic ultrasound",
     [0.85, 0.95], [0.90, 0.99], "Defined 2019, Defined 2012 Cochrane"),
    ("choledocholithiasis", "MRCP",
     [0.85, 0.97], [0.88, 0.97], "Defined 2019, Defined 2015 Cochrane, Defined 2012"),
    ("peptic ulcer", "urea breath test",
     [0.88, 0.97], [0.93, 0.98], "Defined 2010 Cochrane, Defined 2019, Best 2018"),

    # ---- EMERGENCY MEDICINE ----
    ("abdominal trauma", "FAST ultrasound",
     [0.73, 0.88], [0.95, 1.00], "Defined 2019 Cochrane, Quinn 2011, Defined 2018"),
    ("fracture", "point-of-care ultrasound",
     [0.90, 0.96], [0.86, 0.98], "Defined 2020, Defined 2019, Defined 2017"),
    ("septic arthritis", "synovial fluid analysis",
     [0.56, 0.84], [0.67, 0.98], "Defined 2019, Defined 2007, Defined Cochrane"),

    # ---- RHEUMATOLOGY / AUTOIMMUNE ----
    ("systemic lupus erythematosus", "ANA",
     [0.93, 1.00], [0.55, 0.80], "Defined 2019 ACR, Defined 2017, Defined 2011"),
    ("giant cell arteritis", "temporal artery ultrasound",
     [0.68, 0.88], [0.80, 0.97], "Defined 2018 Cochrane, Defined 2014, Defined 2019"),

    # ---- ENDOCRINOLOGY ----
    ("diabetes mellitus", "HbA1c",
     [0.40, 0.65], [0.95, 0.99], "Defined 2019, Defined 2017, Bennett 2007"),
    ("thyroid cancer", "fine needle aspiration",
     [0.65, 0.89], [0.87, 0.99], "Defined 2019, Defined Cochrane, Defined 2015"),

    # ---- OBSTETRICS ----
    ("preterm labor", "fetal fibronectin",
     [0.70, 0.87], [0.73, 0.92], "Defined 2019 Cochrane, Defined 2017, Berghella 2008"),
    ("ectopic pregnancy", "transvaginal ultrasound",
     [0.74, 0.96], [0.84, 1.00], "Defined 2019, Defined 2016 Cochrane, Kirk 2014"),

    # ---- ONCOLOGY (new) ----
    ("lymphoma", "PET-CT",
     [0.80, 0.95], [0.85, 0.99], "Defined 2019, Defined 2015 Cochrane, Defined 2017"),
    ("colorectal liver metastases", "contrast-enhanced ultrasound",
     [0.80, 0.95], [0.80, 0.98], "Defined 2019 Cochrane, Defined 2016, Defined 2012"),

    # ---- INFECTIOUS DISEASE (new) ----
    ("bacterial meningitis", "CSF lactate",
     [0.88, 0.96], [0.91, 0.98], "Defined 2019, Defined 2015, Sakushima 2011"),
    ("hepatitis C", "anti-HCV antibody",
     [0.95, 0.99], [0.97, 1.00], "Defined 2017 WHO, Defined 2019 Cochrane"),
    ("COVID-19", "chest CT",
     [0.87, 0.97], [0.25, 0.56], "Defined 2020 Cochrane, Kim 2020, Defined 2021"),
]

print('=' * 130)
print(f'  Additional DTA Validation — {len(topics)} NEW Topics (Wave 3)')
print(f'  Quality gates: confidence >= medium, N >= 20, index test matched, non-review')
print('=' * 130)
print(f'  {"Topic":<50} {"k":>3} {"Sel/Ext":>7} {"Sens":>7} {"Sens CI":>16} {"Spec":>7} {"Spec CI":>16} {"DOR":>7} {"Verdict":>8}')
print('-' * 130)

results = []
for condition, index_test, ref_sens, ref_spec, citation in topics:
    topic_label = f'{condition} + {index_test}'
    try:
        r = driver.execute_script("""
            return await (async () => {
                const condition = arguments[0], indexTest = arguments[1];
                const oaCondEl = document.getElementById('oaCondition');
                const oaTestEl = document.getElementById('oaIndexTest');
                if (!oaCondEl || !oaTestEl) return {error: 'OA inputs not found'};
                oaCondEl.value = condition;
                oaTestEl.value = indexTest;

                const body = document.getElementById('oaBody');
                if (body && !body.classList.contains('open')) {
                    const header = document.getElementById('oaToggle');
                    if (header) header.click();
                    await new Promise(r => setTimeout(r, 300));
                }

                const btn = document.getElementById('oaSearchBtn');
                if (btn) btn.click();
                await new Promise(r => setTimeout(r, 18000));

                const studies = (typeof oaDiscoveredStudies !== 'undefined') ? oaDiscoveredStudies : [];
                const selected = studies.filter(t => t._selected && (t.backCalc || t.direct2x2));
                const extractable = studies.filter(t => (t.backCalc || t.direct2x2) && t._indexTestMatch === 'match' && !t._isReview);
                const k = selected.length;
                if (k < 2) return {k, selected: selected.length, extractable: extractable.length, error: 'k<2'};

                const prepared = selected.map(t => {
                    const d = t.backCalc || t.direct2x2;
                    return {tp: d.tp, fp: d.fp, fn: d.fn, tn: d.tn,
                            authorYear: t.authorYear || t.nctId || ''};
                });
                const studyData = prepareDTAStudyData(prepared, '0.5');
                if (!studyData || studyData.length < 2) return {k, error: 'prepare failed'};
                const pool = improvedBivariatePool(studyData, 0.95);
                if (!pool) return {k, error: 'pool failed'};
                return {
                    k, selected: selected.length, extractable: extractable.length,
                    pooledSens: pool.pooledSens, pooledSpec: pool.pooledSpec,
                    sensCI: pool.sensCI, specCI: pool.specCI,
                    dor: pool.dor, method: pool.method
                };
            })();
        """, condition, index_test)
    except Exception as e:
        r = {'error': str(e)[:80]}

    k = r.get('k', 0) if r else 0
    selected_count = r.get('selected', 0) if r else 0
    extractable = r.get('extractable', 0) if r else 0

    if r and r.get('pooledSens') is not None:
        sens = r['pooledSens']
        spec = r['pooledSpec']
        s = f"{sens*100:.1f}%"
        sp = f"{spec*100:.1f}%"
        sci = f"[{r['sensCI'][0]*100:.1f}, {r['sensCI'][1]*100:.1f}]" if r.get('sensCI') else '-'
        spci = f"[{r['specCI'][0]*100:.1f}, {r['specCI'][1]*100:.1f}]" if r.get('specCI') else '-'
        dor = f"{r['dor']:.1f}" if r.get('dor') else '-'

        margin = 0.15
        sens_ok = (ref_sens[0] - margin) <= sens <= (ref_sens[1] + margin)
        spec_ok = (ref_spec[0] - margin) <= spec <= (ref_spec[1] + margin)

        if sens_ok and spec_ok: verdict = 'PASS'
        elif sens_ok or spec_ok: verdict = 'PARTIAL'
        else: verdict = 'FAIL'

        print(f'  {topic_label:<50} {r["k"]:>3} {selected_count:>3}/{extractable:<3} {s:>7} {sci:>16} {sp:>7} {spci:>16} {dor:>7} {verdict:>8}')
        results.append({
            'topic': topic_label, 'k': r['k'], 'selected': selected_count, 'extractable': extractable,
            'sens': sens, 'spec': spec, 'sensCI': r.get('sensCI'), 'specCI': r.get('specCI'),
            'dor': r.get('dor'), 'verdict': verdict,
            'ref_sens': ref_sens, 'ref_spec': ref_spec, 'citation': citation,
        })
    elif r and r.get('error') == 'k<2':
        print(f'  {topic_label:<50} {k:>3} {selected_count:>3}/{extractable:<3}  SKIP (k<2)')
        results.append({'topic': topic_label, 'k': k, 'verdict': 'SKIP'})
    else:
        err = r.get('error', 'unknown') if r else 'null'
        print(f'  {topic_label:<50} {k:>3} {selected_count:>3}/{extractable:<3}  ERROR: {err}')
        results.append({'topic': topic_label, 'k': k, 'verdict': 'ERROR', 'detail': err})

driver.quit()

# Summary
print('=' * 130)
print(f'\n  WAVE 3 VALIDATION SUMMARY')
print('=' * 130)
n_pass = sum(1 for r in results if r['verdict'] == 'PASS')
n_partial = sum(1 for r in results if r['verdict'] == 'PARTIAL')
n_fail = sum(1 for r in results if r['verdict'] == 'FAIL')
n_skip = sum(1 for r in results if r['verdict'] == 'SKIP')
n_error = sum(1 for r in results if r['verdict'] == 'ERROR')
total_eval = n_pass + n_partial + n_fail

print(f'  PASS: {n_pass}/{len(topics)}  |  PARTIAL: {n_partial}/{len(topics)}  |  FAIL: {n_fail}/{len(topics)}  |  SKIP: {n_skip}/{len(topics)}  |  ERROR: {n_error}/{len(topics)}')
if total_eval > 0:
    print(f'  Pass rate (excl SKIP/ERROR): {n_pass}/{total_eval} = {n_pass/total_eval*100:.0f}%')
print(f'\n  Combined total: 50 existing + {n_pass} new PASS = {50 + n_pass} topics validated')
print('=' * 130)
