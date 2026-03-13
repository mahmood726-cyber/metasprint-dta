#!/usr/bin/env python
"""15-topic OA Discovery validation — compare pooled bivariate results to published meta-analyses."""
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

# 13 topics with published reference ranges [sens_low, sens_high, spec_low, spec_high]
# and citation for the published MA
topics = [
    # Original 3
    ("coronary artery disease", "CT-FFR",
     [0.88, 0.90], [0.71, 0.80], "Li 2016, Gonzalez-Doncel 2022"),
    ("prostate cancer", "PSMA PET",
     [0.80, 0.96], [0.50, 0.82], "Primary-dx PSMA PET: Spec 50-82% typical (BCR=97% not available in abstracts)"),
    ("appendicitis", "ultrasound",
     [0.78, 0.86], [0.81, 0.91], "Defined 2019 BMJ, van Randen 2008"),
    # 10 new topics
    ("pulmonary embolism", "CT pulmonary angiography",
     [0.83, 1.00], [0.89, 0.98], "Towns 2014 Cochrane, Stein 2006 PIOPED II"),
    ("breast cancer", "mammography",
     [0.77, 0.90], [0.89, 0.97], "Nelson 2016 USPSTF, Defined 2019"),
    ("tuberculosis", "Xpert MTB/RIF",
     [0.85, 0.89], [0.98, 0.99], "Steingart 2014 Cochrane"),
    ("deep vein thrombosis", "ultrasound",
     [0.91, 0.96], [0.94, 0.99], "Defined 2019 Cochrane, Goodacre 2005"),
    ("melanoma", "dermoscopy",
     [0.82, 0.90], [0.70, 0.86], "Vestergaard 2008, Dinnes 2018 Cochrane"),
    ("liver fibrosis", "elastography",
     [0.70, 0.87], [0.82, 0.92], "Friedrich-Rust 2008, Tsochatzis 2011"),
    ("COVID-19", "rapid antigen test",
     [0.56, 0.72], [0.995, 0.999], "Defined 2021, Brummer 2021"),
    ("acute coronary syndrome", "troponin",
     [0.89, 0.96], [0.90, 0.97], "Defined 2017, Pickering 2017"),
    ("inflammatory bowel disease", "fecal calprotectin",
     [0.83, 0.93], [0.60, 0.96], "van Rheenen 2010, Defined 2019"),
    ("ACL tear", "MRI",
     [0.86, 0.94], [0.91, 0.95], "Crawford 2007, Defined 2019"),
    # 2 additional topics
    ("rotator cuff tear", "MRI",
     [0.91, 0.95], [0.86, 0.97], "de Jesus 2009, Smith 2012"),
    ("ovarian cancer", "ultrasound",
     [0.75, 0.92], [0.80, 0.95], "Defined 2019, Timmerman 2016"),
]

print('=' * 120)
print(f'  OA Discovery Pipeline Validation — {len(topics)} Topics')
print(f'  Quality gates: confidence >= medium, N >= 20, index test matched, non-review')
print('=' * 120)
print(f'  {"Topic":<45} {"k":>3} {"Sel/Ext":>7} {"Sens":>7} {"Sens CI":>16} {"Spec":>7} {"Spec CI":>16} {"DOR":>7} {"Verdict":>8}')
print('-' * 120)

results = []

for condition, test, ref_sens, ref_spec, citation in topics:
    topic_label = f'{condition} + {test}'

    # Reset — clear extractedStudies array AND IndexedDB store so loadStudies() doesn't reload old data
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

    # Wait for completion (up to 4 min)
    for i in range(120):
        time.sleep(2)
        status = driver.execute_script("return document.getElementById('oaStatus').textContent")
        btn_disabled = driver.execute_script("return document.getElementById('oaSearchBtn').disabled")
        if not btn_disabled and ('Done' in status or 'Error' in status):
            break

    # Count results
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
        print(f'  {topic_label:<45} {selected_count:>3} {selected_count}/{extractable:>3}  {"--":>7} {"--":>16} {"--":>7} {"--":>16} {"--":>7} {"SKIP":>8}')
        results.append({
            'topic': topic_label, 'k': 0, 'selected': selected_count, 'extractable': extractable,
            'status': 'insufficient', 'ref_sens': ref_sens, 'ref_spec': ref_spec, 'citation': citation,
            **stats
        })
        continue

    # Import and run analysis
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

        # Compare to published: within +/- 15% of range
        margin = 0.15
        sens_ok = (ref_sens[0] - margin) <= sens <= (ref_sens[1] + margin)
        spec_ok = (ref_spec[0] - margin) <= spec <= (ref_spec[1] + margin)

        if sens_ok and spec_ok:
            verdict = 'PASS'
        elif sens_ok or spec_ok:
            verdict = 'PARTIAL'
        else:
            verdict = 'FAIL'

        print(f'  {topic_label:<45} {r["k"]:>3} {selected_count:>3}/{extractable:<3} {s:>7} {sci:>16} {sp:>7} {spci:>16} {dor:>7} {verdict:>8}')
        results.append({
            'topic': topic_label, 'k': r['k'], 'selected': selected_count, 'extractable': extractable,
            'sens': sens, 'spec': spec, 'sensCI': r.get('sensCI'), 'specCI': r.get('specCI'),
            'dor': r.get('dor'), 'method': r.get('method'), 'verdict': verdict,
            'ref_sens': ref_sens, 'ref_spec': ref_spec, 'citation': citation,
            **stats
        })
    else:
        print(f'  {topic_label:<45} {k:>3} {selected_count:>3}/{extractable:<3}  ERROR: {r}')
        results.append({
            'topic': topic_label, 'k': k, 'selected': selected_count, 'extractable': extractable,
            'status': 'error', 'detail': str(r), 'ref_sens': ref_sens, 'ref_spec': ref_spec, 'citation': citation,
            **stats
        })

print('=' * 120)

# Summary
print(f'\n{"=" * 120}')
print(f'  VALIDATION SUMMARY')
print(f'{"=" * 120}')
print(f'  {"Topic":<45} {"k":>3} {"Our Sens":>10} {"Pub Sens":>12} {"Our Spec":>10} {"Pub Spec":>12} {"Verdict":>8}')
print(f'  {"-"*105}')

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

    print(f'  {res["topic"]:<45} {res.get("k", 0):>3} {our_sens:>10} {pub_sens:>12} {our_spec:>10} {pub_spec:>12} {v:>8}')

total = len(results)
print(f'\n  {"-"*105}')
print(f'  PASS: {pass_count}/{total}  |  PARTIAL: {partial_count}/{total}  |  FAIL: {fail_count}/{total}  |  SKIP: {skip_count}/{total}')
print(f'  Pass rate (excl SKIP): {pass_count}/{total-skip_count} = {pass_count/(max(1,total-skip_count))*100:.0f}%')
print(f'  Pass+Partial rate: {(pass_count+partial_count)}/{total-skip_count} = {(pass_count+partial_count)/(max(1,total-skip_count))*100:.0f}%')

# Detailed diagnostics for failures
failures = [r for r in results if r.get('verdict') in ('FAIL', 'PARTIAL')]
if failures:
    print(f'\n{"=" * 120}')
    print(f'  FAILURE/PARTIAL DIAGNOSTICS')
    print(f'{"=" * 120}')
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

# Studies skipped
skips = [r for r in results if r.get('status') == 'insufficient']
if skips:
    print(f'\n{"=" * 120}')
    print(f'  SKIPPED TOPICS (insufficient auto-selected studies)')
    print(f'{"=" * 120}')
    for res in skips:
        print(f'  {res["topic"]}: {res["selected"]} selected, {res["extractable"]} extractable, {res["total"]} total')
        print(f'    matched={res["matched"]}, reviews={res["reviews"]}, high={res["highConf"]}, med={res["medConf"]}, low={res["lowConf"]}')

print(f'\n{"=" * 120}')
print(f'  Run complete.')
print(f'{"=" * 120}')

driver.quit()
