#!/usr/bin/env python
"""End-to-end test: OA Discovery for Ultrasound in Appendicitis.
Runs the full pipeline, captures results, and compares against known published data.

Published reference: Defined (2019) BMJ systematic review:
  Pooled Sens ~86%, Spec ~81% (adults), k=37 studies
Al-Khayal (2007): Sens 83.7%, Spec 95.9%
van Randen (2008): Sens 78%, Spec 83%
"""
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

# Dismiss onboarding
driver.execute_script("""
    const ob = document.getElementById('onboardingOverlay');
    if (ob) ob.style.display = 'none';
    localStorage.setItem('msa-dta-onboarded', '1');
""")
time.sleep(0.5)

print('='*70)
print('  OA Discovery E2E: Ultrasound for Appendicitis')
print('='*70)

# Navigate to Discover tab and open OA panel
driver.execute_script("switchPhase('discover')")
time.sleep(0.5)
driver.execute_script("toggleOAPanel()")
time.sleep(0.3)

# Enter search
driver.execute_script("""
    document.getElementById('oaCondition').value = 'appendicitis';
    document.getElementById('oaIndexTest').value = 'ultrasound';
""")

print('\n[1] Starting OA Discovery search...')
print('    Condition: appendicitis')
print('    Index test: ultrasound')

# Run search
driver.execute_script("runOADiscovery()")

# Wait for completion
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
print(f'    {"NCT ID":<15} {"N":>5} {"Sens":>7} {"Spec":>7} {"TP":>4} {"FP":>4} {"FN":>4} {"TN":>4} {"Method":<15} {"Conf":<6}  Title')
print('    ' + '-'*110)
for r in extractable:
    bc = r['backCalc']
    sens_str = f"{r['sens']*100:.1f}%" if r['sens'] else '?'
    spec_str = f"{r['spec']*100:.1f}%" if r['spec'] else '?'
    print(f"    {r['nctId']:<15} {r['enrollment']:>5} {sens_str:>7} {spec_str:>7} {bc['tp']:>4} {bc['fp']:>4} {bc['fn']:>4} {bc['tn']:>4} {bc['method']:<15} {bc['confidence']:<6}  {r['title'][:50]}")

# Import extractable studies and run analysis
if extractable:
    # Count auto-selected (matched index test, non-review)
    auto_selected = driver.execute_script("""
        return oaDiscoveredStudies.filter(t => t._selected).length;
    """)
    matched = [r for r in results if r['backCalc'] and driver.execute_script(
        f"return oaDiscoveredStudies[{results.index(r)}]._indexTestMatch") == 'match']
    print(f'\n[5] Auto-selected: {auto_selected} studies (matched index test, non-review)')
    print(f'    Matched studies:')
    for r in extractable:
        idx = results.index(r)
        match_status = driver.execute_script(f"return oaDiscoveredStudies[{idx}]._indexTestMatch")
        is_review = driver.execute_script(f"return oaDiscoveredStudies[{idx}]._isReview")
        selected = driver.execute_script(f"return oaDiscoveredStudies[{idx}]._selected")
        tag = 'SELECTED' if selected else ('review' if is_review else match_status)
        print(f"      [{tag:<10}] {r['title'][:65]}")

    print(f'\n    Importing auto-selected studies...')
    driver.execute_script("importOAStudies();")
    time.sleep(1)

    study_count = driver.execute_script("return extractedStudies.length")
    print(f'    Extracted studies in table: {study_count}')

    studies = driver.execute_script("""
        return extractedStudies.map(s => ({
            name: s.authorYear,
            tp: parseInt(s.tp), fp: parseInt(s.fp), fn: parseInt(s.fn), tn: parseInt(s.tn),
            sens: parseInt(s.tp) / Math.max(1, parseInt(s.tp) + parseInt(s.fn)),
            spec: parseInt(s.tn) / Math.max(1, parseInt(s.tn) + parseInt(s.fp))
        }));
    """)

    print(f'\n[6] Imported 2x2 data:')
    print(f'    {"Study":<50} {"TP":>4} {"FP":>4} {"FN":>4} {"TN":>4}  {"Sens":>7} {"Spec":>7}')
    print('    ' + '-'*90)
    for s in studies:
        print(f"    {s['name'][:49]:<50} {s['tp']:>4} {s['fp']:>4} {s['fn']:>4} {s['tn']:>4}  {s['sens']*100:>6.1f}% {s['spec']*100:>6.1f}%")

    # Run bivariate analysis
    print(f'\n[7] Running bivariate GLMM analysis...')
    driver.execute_script("switchPhase('analyze')")
    time.sleep(1)

    if study_count >= 4:
        try:
            driver.execute_script("""
                const btn = document.querySelector('#analyzeMainBtn') || document.querySelector('[onclick*="runAnalysis"]');
                if (btn) btn.click();
            """)
            time.sleep(5)

            summary = driver.execute_script("""
                const el = document.getElementById('analysisSummary');
                return el ? el.innerText.substring(0, 800) : 'No summary found';
            """)
            print(f'    Analysis summary:')
            for line in summary.split('\n'):
                if line.strip():
                    print(f'    {line.strip()}')

            # Extract key numbers for comparison
            pooled = driver.execute_script("""
                try {
                    const r = lastBivariateResult || {};
                    return {
                        sensMu: r.sensMu, specMu: r.specMu,
                        sensCI: r.sensCI, specCI: r.specCI,
                        dor: r.dor, dorCI: r.dorCI
                    };
                } catch(e) { return null; }
            """)

            if pooled and pooled.get('sensMu'):
                print(f'\n[8] COMPARISON WITH PUBLISHED META-ANALYSES:')
                print(f'    {"Source":<40} {"Sens":>10} {"Spec":>10}')
                print(f'    {"-"*65}')
                sens_pct = pooled["sensMu"] * 100
                spec_pct = pooled["specMu"] * 100
                sens_ci = pooled.get("sensCI", [None, None])
                spec_ci = pooled.get("specCI", [None, None])
                sens_ci_str = f'[{sens_ci[0]*100:.1f}, {sens_ci[1]*100:.1f}]' if sens_ci and sens_ci[0] else ''
                spec_ci_str = f'[{spec_ci[0]*100:.1f}, {spec_ci[1]*100:.1f}]' if spec_ci and spec_ci[0] else ''
                print(f'    {"OA Discovery (this run)":<40} {sens_pct:>6.1f}% {sens_ci_str:>12}  {spec_pct:>6.1f}% {spec_ci_str:>12}')
                print(f'    {"Published: Defined 2019 BMJ (k=37)":<40} {"86.0%":>10} {"81.0%":>10}')
                print(f'    {"Published: van Randen 2008 (k=24)":<40} {"78.0%":>10} {"83.0%":>10}')
                print(f'    {"Published: Al-Khayal 2007":<40} {"83.7%":>10} {"95.9%":>10}')

                # Check if our estimates are in a reasonable range
                sens_ok = 50 < sens_pct < 100
                spec_ok = 50 < spec_pct < 100
                print(f'\n    Sensitivity in plausible range (50-100%): {"YES" if sens_ok else "NO"} ({sens_pct:.1f}%)')
                print(f'    Specificity in plausible range (50-100%): {"YES" if spec_ok else "NO"} ({spec_pct:.1f}%)')
        except Exception as e:
            print(f'    Analysis error: {e}')
    else:
        print(f'    Need >= 4 studies for bivariate GLMM, got {study_count}')

# Also test the provenance panel
print(f'\n[9] Testing provenance panel...')
driver.execute_script("switchPhase('discover')")
time.sleep(0.5)

detail_test = driver.execute_script("""
    const row = document.querySelector('#oaResultsBody tr.oa-row-clickable');
    if (!row) return { error: 'no clickable row' };
    row.click();
    const detail = document.querySelector('.oa-detail-panel');
    if (!detail) return { error: 'no detail panel' };
    return {
        hasAbstract: detail.querySelector('.oa-abstract-text') !== null,
        hasHighlight: detail.innerHTML.includes('<mark'),
        hasProvTable: detail.querySelector('.oa-prov-table') !== null,
        hasLinks: detail.querySelector('.oa-links') !== null,
        linkCount: detail.querySelectorAll('.oa-links a').length
    };
""")
if isinstance(detail_test, dict) and not detail_test.get('error'):
    print(f'    Provenance panel: abstract={detail_test["hasAbstract"]}, highlights={detail_test["hasHighlight"]}, provenance={detail_test["hasProvTable"]}, links={detail_test["linkCount"]}')
else:
    print(f'    Provenance panel: {detail_test}')

print(f'\n{"="*70}')
print(f'  E2E test complete.')
print(f'{"="*70}')

driver.quit()
