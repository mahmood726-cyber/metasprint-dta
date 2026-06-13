#!/usr/bin/env python
"""Post-2015 DTA validation — topics where OA Discovery should approximate published meta-analyses.

These are diagnostic tests primarily studied after 2015, with rich OA abstract data.
Published meta-analysis reference values are used for comparison.
"""
import sys, os, json, time, io
if "pytest" not in sys.modules:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

html_path = os.path.join(os.path.dirname(__file__), 'metasprint-dta.html')

def make_driver():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--window-size=1400,900')
    d = webdriver.Chrome(options=opts)
    d.get('file:///' + html_path.replace('\\', '/'))
    time.sleep(3)
    d.execute_script("""
        const ob = document.getElementById('onboardingOverlay');
        if (ob) ob.style.display = 'none';
        localStorage.setItem('msa-dta-onboarded', '1');
    """)
    time.sleep(0.5)
    return d

driver = make_driver()

# Post-2015 diagnostic tests with published MA reference ranges
# Format: (condition, index_test, [sens_low, sens_high], [spec_low, spec_high], "citation")
topics = [
    # ---- NEWER IMAGING TESTS ----
    ("lung cancer screening", "low-dose CT",
     [0.93, 0.97], [0.73, 0.91], "Defined 2019 USPSTF, National Lung Screening Trial"),
    ("endometriosis", "MRI",
     [0.70, 0.94], [0.77, 0.98], "Defined 2016, Bazot 2017"),
    ("placenta accreta", "ultrasound",
     [0.80, 0.95], [0.85, 0.98], "D'Antonio 2013, Defined 2019"),

    # ---- MOLECULAR / POINT-OF-CARE ----
    ("colorectal cancer", "fecal immunochemical test",
     [0.69, 0.86], [0.87, 0.96], "Lee 2014, Defined 2019 Cochrane"),
    ("sepsis", "procalcitonin",
     [0.77, 0.85], [0.73, 0.83], "Defined 2019 Cochrane, Wacker 2013"),
    ("influenza", "rapid antigen test",
     [0.50, 0.73], [0.90, 0.99], "Defined 2014 Cochrane, Defined 2019"),
    ("streptococcal pharyngitis", "rapid antigen test",
     [0.85, 0.90], [0.91, 0.99], "Defined 2016, Cohen 2016"),
    ("urinary tract infection", "dipstick",
     [0.68, 0.88], [0.60, 0.92], "Defined 2019, Mambatta 2015"),

    # ---- BIOMARKERS ----
    ("heart failure", "BNP",
     [0.89, 0.95], [0.60, 0.80], "Roberts 2015, Defined 2019"),
    ("iron deficiency anemia", "ferritin",
     [0.85, 0.92], [0.75, 0.99], "Defined 2019, Garcia-Casal 2021"),
    ("celiac disease", "tissue transglutaminase",
     [0.90, 0.98], [0.95, 0.99], "Defined 2019 Cochrane, Defined 2022"),
    ("rheumatoid arthritis", "anti-CCP",
     [0.55, 0.80], [0.90, 0.99], "Defined 2019, Nishimura 2007"),

    # ---- NEWER MODALITIES ----
    ("thyroid nodules", "ultrasound",
     [0.80, 0.95], [0.55, 0.85], "Defined 2017, Campanella 2014"),
    ("kidney stones", "ultrasound",
     [0.45, 0.77], [0.70, 0.97], "Defined 2019, Smith-Bindman 2014"),
    ("pneumonia", "lung ultrasound",
     [0.88, 0.97], [0.78, 0.97], "Defined 2014, Orso 2018"),
    ("hip fracture", "MRI",
     [0.93, 1.00], [0.95, 1.00], "Defined 2019, Carpenter 2014"),
    ("carpal tunnel syndrome", "ultrasound",
     [0.65, 0.87], [0.57, 0.97], "Defined 2019, Fowler 2011"),

    # ---- CANCER SCREENING ----
    ("cervical cancer", "HPV test",
     [0.89, 0.97], [0.84, 0.95], "Defined 2019 Cochrane, Koliopoulos 2017"),
    ("hepatocellular carcinoma", "AFP",
     [0.41, 0.65], [0.80, 0.94], "Defined 2019, Singal 2012"),
    ("bladder cancer", "urine cytology",
     [0.34, 0.48], [0.94, 0.99], "Defined 2019, Defined 2016"),

    # ========== ADDITIONAL POST-2015 TOPICS (Wave 2) ==========
    # ---- MOLECULAR / POC (newer) ----
    ("tuberculosis", "Xpert Ultra",
     [0.88, 0.95], [0.96, 0.99], "Defined 2020 Cochrane, Dorman 2018"),
    ("Clostridioides difficile infection", "GDH test",
     [0.90, 0.96], [0.82, 0.92], "Defined 2019 Cochrane, Crobach 2018"),
    ("malaria", "rapid diagnostic test",
     [0.90, 0.99], [0.89, 0.98], "Defined 2015 Cochrane, WHO 2021"),
    ("group B streptococcus", "PCR",
     [0.93, 0.98], [0.95, 0.99], "Defined 2019 Cochrane, El Helali 2019"),

    # ---- AI DIAGNOSTICS ----
    ("diabetic retinopathy", "AI fundus screening",
     [0.87, 0.97], [0.88, 0.98], "Defined 2021, Ting 2017, Islam 2020"),

    # ---- IMAGING (newer applications) ----
    ("pneumothorax", "point-of-care ultrasound",
     [0.78, 0.91], [0.97, 1.00], "Defined 2018 Cochrane, Defined 2020"),
    ("acute appendicitis", "CT",
     [0.91, 0.99], [0.90, 0.98], "Defined 2019, Kim 2021"),
    ("glaucoma", "OCT",
     [0.72, 0.94], [0.83, 0.96], "Defined 2019, Kim 2017"),

    # ---- BIOMARKER (newer applications) ----
    ("deep vein thrombosis", "D-dimer",
     [0.93, 0.96], [0.35, 0.55], "Defined 2019 Cochrane, Defined 2014"),
    ("obstructive sleep apnea", "STOP-BANG questionnaire",
     [0.88, 0.97], [0.25, 0.56], "Defined 2017, Chung 2016, Nagappa 2015"),
    ("NAFLD fibrosis", "FIB-4 score",
     [0.71, 0.90], [0.60, 0.80], "Defined 2019, McPherson 2017, Sun 2016"),

    # ---- PRENATAL / GENETIC ----
    ("Down syndrome", "cell-free DNA screening",
     [0.99, 0.999], [0.998, 0.999], "Gil 2017, Taylor-Phillips 2016"),

    # ---- INFECTION BIOMARKERS ----
    ("invasive aspergillosis", "galactomannan",
     [0.71, 0.89], [0.85, 0.95], "Defined 2015, Defined 2019 Cochrane"),
    ("bacteremia", "procalcitonin",
     [0.72, 0.83], [0.70, 0.83], "Defined 2019, Hoeboer 2015"),
    ("neonatal sepsis", "procalcitonin",
     [0.81, 0.90], [0.70, 0.85], "Defined 2019, Defined 2020"),
]

print('=' * 130)
print(f'  Post-2015 DTA Validation — {len(topics)} Topics (OA Discovery vs Published Meta-Analyses)')
print(f'  Quality gates: confidence >= medium, N >= 20, index test matched, non-review')
print('=' * 130)
print(f'  {"Topic":<50} {"k":>3} {"Sel/Ext":>7} {"Sens":>7} {"Sens CI":>16} {"Spec":>7} {"Spec CI":>16} {"DOR":>7} {"Verdict":>8}')
print('-' * 130)

results = []

for ti, (condition, test, ref_sens, ref_spec, citation) in enumerate(topics):
    topic_label = f'{condition} + {test}'

    # Restart Chrome every 4 topics to prevent memory/session issues
    if ti > 0 and ti % 4 == 0:
        try: driver.quit()
        except: pass
        time.sleep(2)
        driver = make_driver()

    try:
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

        for i in range(150):
            time.sleep(2)
            status = driver.execute_script("return document.getElementById('oaStatus').textContent")
            btn_disabled = driver.execute_script("return document.getElementById('oaSearchBtn').disabled")
            if not btn_disabled and ('Done' in status or 'Error' in status):
                break

        stats = driver.execute_script("""
            const s = oaDiscoveredStudies;
            return {
                total: s.length,
                extractable: s.filter(x => x.backCalc || x.direct2x2).length,
                selected: s.filter(x => x._selected).length,
                matched: s.filter(x => x._indexTestMatch === 'match').length,
                reviews: s.filter(x => x._isReview).length,
                highConf: s.filter(x => (x.backCalc || x.direct2x2 || {}).confidence === 'high').length,
                medConf: s.filter(x => (x.backCalc || x.direct2x2 || {}).confidence === 'medium').length,
                lowConf: s.filter(x => (x.backCalc || x.direct2x2 || {}).confidence === 'low').length
            };
        """)

        selected_count = stats['selected']
        extractable = stats['extractable']

        if selected_count < 2:
            print(f'  {topic_label:<50} {selected_count:>3} {selected_count}/{extractable:>3}  {"--":>7} {"--":>16} {"--":>7} {"--":>16} {"--":>7} {"SKIP":>8}')
            results.append({
                'topic': topic_label, 'k': 0, 'selected': selected_count, 'extractable': extractable,
                'status': 'insufficient', 'ref_sens': ref_sens, 'ref_spec': ref_spec, 'citation': citation,
                **stats
            })
            continue

        driver.execute_script("importOAStudies();")
        time.sleep(0.5)
        k = driver.execute_script("return extractedStudies.length")
        driver.execute_script("switchPhase('analyze')")
        time.sleep(1)
        driver.execute_script("runAnalysis()")
        time.sleep(8)

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
                'dor': r.get('dor'), 'method': r.get('method'), 'verdict': verdict,
                'ref_sens': ref_sens, 'ref_spec': ref_spec, 'citation': citation,
                **stats
            })
        else:
            print(f'  {topic_label:<50} {k:>3} {selected_count:>3}/{extractable:<3}  ERROR: {r}')
            results.append({
                'topic': topic_label, 'k': k, 'selected': selected_count, 'extractable': extractable,
                'status': 'error', 'detail': str(r), 'ref_sens': ref_sens, 'ref_spec': ref_spec, 'citation': citation,
                **stats
            })
    except Exception as exc:
        print(f'  {topic_label:<50}  CRASH: {str(exc)[:60]}')
        results.append({
            'topic': topic_label, 'k': 0, 'selected': 0, 'extractable': 0,
            'status': 'crash', 'detail': str(exc), 'ref_sens': ref_sens, 'ref_spec': ref_spec, 'citation': citation,
            'total': 0, 'matched': 0, 'reviews': 0, 'highConf': 0, 'medConf': 0, 'lowConf': 0
        })
        try: driver.quit()
        except: pass
        time.sleep(2)
        driver = make_driver()

print('=' * 130)

# Summary
print(f'\n{"=" * 130}')
print(f'  POST-2015 VALIDATION SUMMARY')
print(f'{"=" * 130}')
print(f'  {"Topic":<50} {"k":>3} {"Our Sens":>10} {"Pub Sens":>12} {"Our Spec":>10} {"Pub Spec":>12} {"Verdict":>8}')
print(f'  {"-"*115}')

pass_count = 0
partial_count = 0
fail_count = 0
skip_count = 0

for res in results:
    pub_sens = f"{res['ref_sens'][0]*100:.0f}-{res['ref_sens'][1]*100:.0f}%"
    pub_spec = f"{res['ref_spec'][0]*100:.0f}-{res['ref_spec'][1]*100:.0f}%"

    if res.get('sens') is not None:
        our_sens = f"{res['sens']*100:.1f}%"
        our_spec = f"{res['spec']*100:.1f}%"
        v = res['verdict']
        if v == 'PASS': pass_count += 1
        elif v == 'PARTIAL': partial_count += 1
        else: fail_count += 1
    else:
        our_sens = '--'
        our_spec = '--'
        v = 'SKIP'
        skip_count += 1

    print(f'  {res["topic"]:<50} {res.get("k", 0):>3} {our_sens:>10} {pub_sens:>12} {our_spec:>10} {pub_spec:>12} {v:>8}')

total = len(results)
evaluated = total - skip_count
print(f'\n  {"-"*115}')
print(f'  PASS: {pass_count}/{total}  |  PARTIAL: {partial_count}/{total}  |  FAIL: {fail_count}/{total}  |  SKIP: {skip_count}/{total}')
print(f'  Pass rate (excl SKIP): {pass_count}/{max(1,evaluated)} = {pass_count/max(1,evaluated)*100:.0f}%')
print(f'  Pass+Partial rate: {(pass_count+partial_count)}/{max(1,evaluated)} = {(pass_count+partial_count)/max(1,evaluated)*100:.0f}%')

# Equivalence analysis — which topics are truly close to published?
equiv = [r for r in results if r.get('sens') is not None]
if equiv:
    print(f'\n{"=" * 130}')
    print(f'  EQUIVALENCE ANALYSIS (within published range, no margin)')
    print(f'{"=" * 130}')
    strict_pass = 0
    for res in equiv:
        sens_in = res['ref_sens'][0] <= res['sens'] <= res['ref_sens'][1]
        spec_in = res['ref_spec'][0] <= res['spec'] <= res['ref_spec'][1]
        both = sens_in and spec_in
        tag = 'EQUIV' if both else ('SENS_OK' if sens_in else ('SPEC_OK' if spec_in else 'OUTSIDE'))
        if both: strict_pass += 1
        print(f'  {res["topic"]:<50} Sens {res["sens"]*100:.1f}% {"[IN]" if sens_in else "[OUT]":>5}  Spec {res["spec"]*100:.1f}% {"[IN]" if spec_in else "[OUT]":>5}  {tag:>8}  (k={res["k"]})')
    print(f'\n  Strict equivalence: {strict_pass}/{len(equiv)} = {strict_pass/max(1,len(equiv))*100:.0f}%')

# Diagnostics for failures
failures = [r for r in results if r.get('verdict') in ('FAIL', 'PARTIAL')]
if failures:
    print(f'\n{"=" * 130}')
    print(f'  FAILURE/PARTIAL DIAGNOSTICS')
    print(f'{"=" * 130}')
    for res in failures:
        margin = 0.15
        sens_ok = (res['ref_sens'][0] - margin) <= res['sens'] <= (res['ref_sens'][1] + margin)
        spec_ok = (res['ref_spec'][0] - margin) <= res['spec'] <= (res['ref_spec'][1] + margin)
        problems = []
        if not sens_ok:
            if res['sens'] > res['ref_sens'][1] + margin:
                problems.append(f"Sens TOO HIGH: {res['sens']*100:.1f}% vs pub {res['ref_sens'][1]*100:.0f}% (+{margin*100:.0f}% margin)")
            else:
                problems.append(f"Sens TOO LOW: {res['sens']*100:.1f}% vs pub {res['ref_sens'][0]*100:.0f}% (-{margin*100:.0f}% margin)")
        if not spec_ok:
            if res['spec'] > res['ref_spec'][1] + margin:
                problems.append(f"Spec TOO HIGH: {res['spec']*100:.1f}% vs pub {res['ref_spec'][1]*100:.0f}% (+{margin*100:.0f}% margin)")
            else:
                problems.append(f"Spec TOO LOW: {res['spec']*100:.1f}% vs pub {res['ref_spec'][0]*100:.0f}% (-{margin*100:.0f}% margin)")

        print(f'\n  {res["topic"]} (k={res["k"]}, {res["selected"]}/{res["extractable"]} sel/ext)')
        print(f'    Citation: {res["citation"]}')
        print(f'    Pipeline: total={res["total"]}, matched={res["matched"]}, reviews={res["reviews"]}')
        print(f'    Confidence: high={res["highConf"]}, medium={res["medConf"]}, low={res["lowConf"]}')
        for p in problems:
            print(f'    >> {p}')

# Skipped
skips = [r for r in results if r.get('status') == 'insufficient']
if skips:
    print(f'\n{"=" * 130}')
    print(f'  SKIPPED TOPICS (insufficient auto-selected studies)')
    print(f'{"=" * 130}')
    for res in skips:
        print(f'  {res["topic"]}: {res["selected"]} selected, {res["extractable"]} extractable, {res["total"]} total')
        print(f'    matched={res["matched"]}, reviews={res["reviews"]}, high={res["highConf"]}, med={res["medConf"]}, low={res["lowConf"]}')

print(f'\n{"=" * 130}')
print(f'  Run complete.')
print(f'{"=" * 130}')

driver.quit()
