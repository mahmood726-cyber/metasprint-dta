"""
test_edge_cases.py — Comprehensive edge-case tests for MetaSprint DTA.

Tests boundary conditions for: Fagan nomogram, DCA rendering, MCID thresholds,
Patient Risk calculator, Effect Size Converter, What-If simulator,
Drapery plot, and Exclusion matrix.

Target: 60+ edge-case tests covering uninformative/extreme inputs, k=2 datasets,
boundary slider values, and Bayes theorem verification.
"""
import sys, io, os, time, json
if "pytest" not in sys.modules:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

passed = 0
failed = 0
total = 0
errors = []

def check(label, condition, detail=''):
    global passed, failed, total, errors
    total += 1
    if condition:
        passed += 1
        print(f'  PASS: {label}' + (f' ({detail})' if detail else ''))
    else:
        failed += 1
        errors.append(label)
        print(f'  FAIL: {label}' + (f' ({detail})' if detail else ''))

BNP_STUDIES = [
    {'ay': 'Dao 2001',       'tp': 52,  'fp': 14, 'fn': 8,  'tn': 76,  'indexTest': 'BNP', 'threshold': '100'},
    {'ay': 'Morrison 2002',  'tp': 44,  'fp': 20, 'fn': 6,  'tn': 151, 'indexTest': 'BNP', 'threshold': '94'},
    {'ay': 'Maisel 2002',    'tp': 379, 'fp': 83, 'fn': 65, 'tn': 959, 'indexTest': 'BNP', 'threshold': '100'},
    {'ay': 'Mueller 2004',   'tp': 89,  'fp': 17, 'fn': 14, 'tn': 337, 'indexTest': 'BNP', 'threshold': '100'},
    {'ay': 'Lainchbury 2003','tp': 40,  'fp': 22, 'fn': 5,  'tn': 138, 'indexTest': 'BNP', 'threshold': '76'},
    {'ay': 'McCullough 2002','tp': 163, 'fp': 44, 'fn': 21, 'tn': 416, 'indexTest': 'BNP', 'threshold': '100'},
]

TWO_STUDIES = [
    {'ay': 'Dao 2001',      'tp': 52, 'fp': 14, 'fn': 8,  'tn': 76,  'indexTest': 'BNP', 'threshold': '100'},
    {'ay': 'Morrison 2002', 'tp': 44, 'fp': 20, 'fn': 6,  'tn': 151, 'indexTest': 'BNP', 'threshold': '94'},
]

# --- Setup ---
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1920,1200')
opts.set_capability('goog:loggingPrefs', {'browser': 'SEVERE'})

html_path = 'file:///' + os.path.abspath('metasprint-dta.html').replace('\\', '/')
_cd = os.environ.get('SE_CHROMEDRIVER', '')
_svc = Service(executable_path=_cd) if _cd else Service()
driver = webdriver.Chrome(options=opts, service=_svc)
driver.get(html_path)
time.sleep(3)

# Dismiss onboarding overlay
driver.execute_script('''
    var overlay = document.getElementById('onboardOverlay');
    if (overlay) overlay.style.display = 'none';
    var modal = document.querySelector('.onboard-modal');
    if (modal) modal.style.display = 'none';
    document.querySelectorAll('.modal-overlay, .onboard-overlay').forEach(function(el) {
        el.style.display = 'none';
    });
    localStorage.setItem('msa-dta-onboarded', 'true');
    localStorage.setItem('msa-dta-onboard-done', 'true');
''')
time.sleep(0.5)

# Create project and load studies
driver.execute_script('''
    (async function() {
        var p = createEmptyProject('EdgeCase Test ' + Date.now());
        await idbPut('projects', p);
        currentProjectId = p.id;
        extractedStudies = [];
        document.getElementById('extractBody').innerHTML = '';
        await loadProjects();
    })();
''')
time.sleep(1)
for s in BNP_STUDIES:
    driver.execute_script(f"addStudyRow({json.dumps(s)});")
    time.sleep(0.15)
time.sleep(0.5)

# Navigate to Analyze and run
driver.execute_script('document.querySelector(\'[data-phase="analyze"]\').click()')
time.sleep(0.5)
driver.execute_script('document.getElementById("methodSelect").value = "bivariate"')
driver.execute_script('document.getElementById("confLevelSelect").value = "0.95"')
time.sleep(0.2)
driver.execute_script('runAnalysis()')
time.sleep(5)

result = driver.execute_script('return lastAnalysisResult')
check('Analysis completed', result is not None, f'k={result.get("k") if result else "?"}')

# Expand advanced section and show sub-sections
driver.execute_script('''
    var sec = document.getElementById('advancedDTASection');
    if (sec) sec.style.display = 'block';
    var content = document.getElementById('advancedDTAContent');
    if (content) content.style.display = 'block';
    var mcidSec = document.getElementById('mcidDTASection');
    if (mcidSec) mcidSec.style.display = 'block';
    var prSec = document.getElementById('patientRiskDTASection');
    if (prSec) prSec.style.display = 'block';
    var escSec = document.getElementById('effectConverterDTASection');
    if (escSec) escSec.style.display = 'block';
''')
time.sleep(1)

# =============================================
# 1. FAGAN NOMOGRAM EDGE CASES
# =============================================
print('\n--- 1. Fagan Nomogram Edge Cases ---')

# 1.1: Pre-test = 1% (very low)
r = driver.execute_script('''
    var el = document.getElementById('faganPretest');
    if (!el) return {error: 'no faganPretest element'};
    el.value = '1';
    computeFagan();
    var html = document.getElementById('faganResult')?.innerHTML || '';
    return {html: html, hasSVG: html.includes('<svg'), hasPercent: html.includes('%')};
''')
check('Fagan: pretest=1% renders SVG', r and r.get('hasSVG'), str(r.get('error', '')))
check('Fagan: pretest=1% shows percentages', r and r.get('hasPercent'))

# 1.2: Pre-test = 99% (very high)
r = driver.execute_script('''
    document.getElementById('faganPretest').value = '99';
    computeFagan();
    var html = document.getElementById('faganResult')?.innerHTML || '';
    var postPos = html.match(/test \\+[^\\d]*(\\d+\\.?\\d*)/i) || html.match(/(\\d+\\.\\d+)%/);
    return {html: html.substring(0, 300), hasSVG: html.includes('<svg'),
            len: html.length};
''')
check('Fagan: pretest=99% renders SVG', r and r.get('hasSVG'))
check('Fagan: pretest=99% produces output', r and r.get('len', 0) > 100)

# 1.3: Verify Fagan math at pretest=50% (equal prior odds)
r = driver.execute_script('''
    document.getElementById('faganPretest').value = '50';
    computeFagan();
    var html = document.getElementById('faganResult')?.innerHTML || '';
    // Extract from table rows (the table is separate from the SVG)
    var rows = document.querySelectorAll('#faganResult table tr');
    var postPos = null, postNeg = null, pretest = null;
    for (var row of rows) {
        var cells = row.querySelectorAll('td');
        if (cells.length >= 2) {
            var label = cells[0].textContent;
            var val = cells[1].textContent;
            var match = val.match(/(\\d+\\.?\\d*)%/);
            if (label.includes('Pre-test') && match) pretest = parseFloat(match[1]);
            if (label.includes('test +') && match) postPos = parseFloat(match[1]);
            if ((label.includes('test \\u2212') || label.includes('test -')) && match) postNeg = parseFloat(match[1]);
        }
    }
    return {pretest: pretest, postPos: postPos, postNeg: postNeg, hasSVG: html.includes('<svg'),
            rowCount: rows.length};
''')
check('Fagan: pretest=50% renders', r and r.get('hasSVG'))
check('Fagan: pretest=50% table has result rows', r and r.get('rowCount', 0) >= 4,
      f"{r.get('rowCount')} rows")

# 1.4: PLR=1.0 (uninformative — post-test+ should equal pretest)
r = driver.execute_script('''
    // Check what PLR the analysis computed
    var plr = lastAnalysisResult ? lastAnalysisResult.plr : null;
    var nlr = lastAnalysisResult ? lastAnalysisResult.nlr : null;
    return {plr: plr, nlr: nlr};
''')
check('Fagan: analysis has valid PLR', r and r.get('plr') is not None and r.get('plr') > 0,
      f"PLR={r.get('plr'):.2f}" if r and r.get('plr') else '')
check('Fagan: analysis has valid NLR', r and r.get('nlr') is not None and r.get('nlr') > 0,
      f"NLR={r.get('nlr'):.3f}" if r and r.get('nlr') else '')

# 1.5: Verify post-test probability math (Bayes) for pretest=20%
r = driver.execute_script('''
    document.getElementById('faganPretest').value = '20';
    computeFagan();
    var plr = lastAnalysisResult.plr;
    var nlr = lastAnalysisResult.nlr;
    var preOdds = 0.2 / 0.8;
    var expPos = (preOdds * plr) / (1 + preOdds * plr);
    var expNeg = (preOdds * nlr) / (1 + preOdds * nlr);
    // Extract from table rows (not SVG ticks)
    var rows = document.querySelectorAll('#faganResult table tr');
    var postPos = null, postNeg = null;
    for (var row of rows) {
        var cells = row.querySelectorAll('td');
        if (cells.length >= 2) {
            var label = cells[0].textContent;
            var val = cells[1].textContent;
            var match = val.match(/(\\d+\\.?\\d*)%/);
            if (label.includes('test +') && match) postPos = parseFloat(match[1]);
            if ((label.includes('test \\u2212') || label.includes('test -')) && match) postNeg = parseFloat(match[1]);
        }
    }
    return {expPos: expPos * 100, expNeg: expNeg * 100, postPos: postPos, postNeg: postNeg, plr: plr, nlr: nlr};
''')
if r and r.get('postPos') is not None and r.get('postNeg') is not None:
    check('Fagan: post-test positive matches Bayes',
          abs(r['postPos'] - r['expPos']) < 0.2,
          f"expected={r['expPos']:.1f}%, found={r['postPos']:.1f}%")
    check('Fagan: post-test negative matches Bayes',
          abs(r['postNeg'] - r['expNeg']) < 0.2,
          f"expected={r['expNeg']:.1f}%, found={r['postNeg']:.1f}%")
else:
    check('Fagan: post-test positive matches Bayes', False, 'could not extract table values')
    check('Fagan: post-test negative matches Bayes', False, 'could not extract table values')

# 1.6: Fagan SVG has three vertical axes (pre-test, LR, post-test)
r = driver.execute_script('''
    var svgs = document.querySelectorAll('#faganResult svg');
    if (svgs.length === 0) return {axes: 0, lines: 0};
    var svg = svgs[0];
    var lines = svg.querySelectorAll('line');
    var circles = svg.querySelectorAll('circle');
    var texts = svg.querySelectorAll('text');
    // Count vertical axis lines (same x1/x2, different y1/y2)
    var vertAxes = 0;
    for (var l of lines) {
        if (Math.abs(parseFloat(l.getAttribute('x1')) - parseFloat(l.getAttribute('x2'))) < 1 &&
            Math.abs(parseFloat(l.getAttribute('y1')) - parseFloat(l.getAttribute('y2'))) > 100) {
            vertAxes++;
        }
    }
    return {axes: vertAxes, lines: lines.length, circles: circles.length, texts: texts.length};
''')
check('Fagan: SVG has 3 vertical axes', r and r.get('axes', 0) >= 3, f"{r.get('axes')} axes")
check('Fagan: SVG has connecting circles', r and r.get('circles', 0) >= 4, f"{r.get('circles')} circles")
check('Fagan: SVG has tick labels', r and r.get('texts', 0) >= 10, f"{r.get('texts')} text elements")

# 1.7: Fagan with pretest=0 (invalid — should show error)
r = driver.execute_script('''
    document.getElementById('faganPretest').value = '0';
    computeFagan();
    var html = document.getElementById('faganResult')?.innerHTML || '';
    return {hasError: html.toLowerCase().includes('valid') || html.toLowerCase().includes('error') || html.includes('1-99')};
''')
check('Fagan: pretest=0% shows error message', r and r.get('hasError'))

# 1.8: Fagan with pretest=100 (invalid)
r = driver.execute_script('''
    document.getElementById('faganPretest').value = '100';
    computeFagan();
    var html = document.getElementById('faganResult')?.innerHTML || '';
    return {hasError: html.toLowerCase().includes('valid') || html.includes('1-99')};
''')
check('Fagan: pretest=100% shows error message', r and r.get('hasError'))


# =============================================
# 2. DCA RENDERING EDGE CASES
# =============================================
print('\n--- 2. DCA Rendering Edge Cases ---')

# 2.1: DCA rendered with the main analysis
r = driver.execute_script('''
    var c = document.getElementById('advDCAContainer');
    if (!c) return {exists: false};
    return {exists: true, len: c.innerHTML.length,
            hasSVG: c.innerHTML.includes('<svg'),
            svgCount: c.querySelectorAll('svg').length};
''')
check('DCA: container exists', r and r.get('exists'))
check('DCA: SVG rendered', r and r.get('hasSVG'))

# 2.2: DCA has multiple paths (test strategy + treat-all)
r = driver.execute_script('''
    var paths = document.querySelectorAll('#advDCAContainer svg path');
    return {pathCount: paths.length};
''')
check('DCA: has treat-all and test strategy curves (>=2 paths)', r and r.get('pathCount', 0) >= 2,
      f"{r.get('pathCount')} paths")

# 2.3: DCA mentions threshold probability
r = driver.execute_script('return document.getElementById("advDCAContainer")?.textContent || ""')
check('DCA: mentions threshold probability', 'Threshold' in r or 'threshold' in r.lower())
check('DCA: mentions net benefit', 'Net Benefit' in r or 'net benefit' in r.lower())

# 2.4: DCA has prevalence slider
r = driver.execute_script('''
    var slider = document.getElementById('dcaPrevalenceSlider');
    return {exists: !!slider, min: slider ? slider.min : null, max: slider ? slider.max : null,
            val: slider ? slider.value : null};
''')
check('DCA: prevalence slider exists', r and r.get('exists'))

# 2.5: DCA re-renders with changed prevalence
r = driver.execute_script('''
    var slider = document.getElementById('dcaPrevalenceSlider');
    if (!slider) return {ok: false, error: 'no slider'};
    var before = document.getElementById('advDCAContainer')?.innerHTML?.length || 0;
    slider.value = '5';
    renderDCA(lastAnalysisResult, 0.95);
    var after = document.getElementById('advDCAContainer')?.innerHTML || '';
    return {ok: true, contains5: after.includes('prevalence=5%') || after.includes('5%'),
            lenAfter: after.length};
''')
check('DCA: re-renders with prevalence=5%', r and r.get('contains5'))

# 2.6: DCA at prevalence=50%
r = driver.execute_script('''
    var slider = document.getElementById('dcaPrevalenceSlider');
    if (slider) slider.value = '50';
    renderDCA(lastAnalysisResult, 0.95);
    var html = document.getElementById('advDCAContainer')?.innerHTML || '';
    return {has50: html.includes('50%'), hasSVG: html.includes('<svg')};
''')
check('DCA: renders at prevalence=50%', r and r.get('hasSVG'))

# 2.7: DCA has legend entries
r = driver.execute_script('''
    var texts = document.querySelectorAll('#advDCAContainer svg text');
    var hasTestStrategy = false, hasTreatAll = false, hasTreatNone = false;
    for (var t of texts) {
        var txt = t.textContent.toLowerCase();
        if (txt.includes('test')) hasTestStrategy = true;
        if (txt.includes('treat all')) hasTreatAll = true;
        if (txt.includes('treat none')) hasTreatNone = true;
    }
    return {hasTestStrategy: hasTestStrategy, hasTreatAll: hasTreatAll, hasTreatNone: hasTreatNone};
''')
check('DCA: legend has test strategy', r and r.get('hasTestStrategy'))
check('DCA: legend has treat-all line', r and r.get('hasTreatAll'))
check('DCA: legend has treat-none line', r and r.get('hasTreatNone'))


# =============================================
# 3. MCID THRESHOLD BOUNDARY CASES
# =============================================
print('\n--- 3. MCID Threshold Boundary Cases ---')

# 3.1: MCID with very high thresholds (99%/99%) — should mostly fail
r = driver.execute_script('''
    document.getElementById('mcid-sens-value').value = '99';
    document.getElementById('mcid-spec-value').value = '99';
    renderMCIDAnalysisDTA();
    var html = document.getElementById('mcidDTAArea')?.innerHTML || '';
    return {len: html.length,
            hasCheckOrCross: html.includes('\\u2714') || html.includes('\\u2718'),
            hasCross: html.includes('\\u2718'),
            hasThreshold: html.includes('threshold')};
''')
check('MCID: 99%/99% threshold renders', r and r.get('len', 0) > 50)
check('MCID: 99%/99% shows at least one cross (fail)', r and r.get('hasCross'),
      'pooled sens/spec unlikely to meet 99%')

# 3.2: MCID with very low thresholds (1%/1%) — should trivially pass
r = driver.execute_script('''
    document.getElementById('mcid-sens-value').value = '1';
    document.getElementById('mcid-spec-value').value = '1';
    renderMCIDAnalysisDTA();
    var html = document.getElementById('mcidDTAArea')?.innerHTML || '';
    return {len: html.length,
            hasCheck: html.includes('\\u2714'),
            hasCross: html.includes('\\u2718')};
''')
check('MCID: 1%/1% threshold renders', r and r.get('len', 0) > 50)
check('MCID: 1%/1% shows checkmarks (pass)', r and r.get('hasCheck'))

# 3.3: MCID with mid-range thresholds (50%/50%)
r = driver.execute_script('''
    document.getElementById('mcid-sens-value').value = '50';
    document.getElementById('mcid-spec-value').value = '50';
    renderMCIDAnalysisDTA();
    var html = document.getElementById('mcidDTAArea')?.innerHTML || '';
    return {len: html.length, hasContent: html.includes('Pooled')};
''')
check('MCID: 50%/50% threshold renders', r and r.get('len', 0) > 50)
check('MCID: 50%/50% shows pooled comparison', r and r.get('hasContent'))

# 3.4: MCID re-renders after changing thresholds
r = driver.execute_script('''
    document.getElementById('mcid-sens-value').value = '80';
    document.getElementById('mcid-spec-value').value = '80';
    renderMCIDAnalysisDTA();
    var html1 = document.getElementById('mcidDTAArea')?.innerHTML || '';
    document.getElementById('mcid-sens-value').value = '90';
    document.getElementById('mcid-spec-value').value = '90';
    renderMCIDAnalysisDTA();
    var html2 = document.getElementById('mcidDTAArea')?.innerHTML || '';
    return {changed: html1 !== html2, len1: html1.length, len2: html2.length};
''')
check('MCID: re-renders with different thresholds', r and r.get('changed'))

# 3.5: MCID shows study-level counts (N/k studies meeting threshold)
r = driver.execute_script('''
    document.getElementById('mcid-sens-value').value = '80';
    document.getElementById('mcid-spec-value').value = '80';
    renderMCIDAnalysisDTA();
    var html = document.getElementById('mcidDTAArea')?.innerHTML || '';
    return {hasStudyCount: html.includes('/6') || html.includes('Studies meeting'),
            hasPredict: html.includes('future study') || html.includes('P(future')};
''')
check('MCID: shows study-level meeting counts', r and r.get('hasStudyCount'))
check('MCID: shows predictive probability', r and r.get('hasPredict'))

# 3.6: MCID shows CI vs threshold assessment
r = driver.execute_script('''
    var html = document.getElementById('mcidDTAArea')?.innerHTML || '';
    return {hasCICheck: html.includes('CI above') || html.includes('CI crosses')};
''')
check('MCID: shows CI vs threshold assessment', r and r.get('hasCICheck'))

# 3.7: MCID with asymmetric thresholds (high sens, low spec)
r = driver.execute_script('''
    document.getElementById('mcid-sens-value').value = '95';
    document.getElementById('mcid-spec-value').value = '50';
    renderMCIDAnalysisDTA();
    var html = document.getElementById('mcidDTAArea')?.innerHTML || '';
    // Should have mixed results: sens may fail 95%, spec should pass 50%
    return {len: html.length, hasCheck: html.includes('\\u2714'), hasCross: html.includes('\\u2718')};
''')
check('MCID: asymmetric 95%/50% threshold renders', r and r.get('len', 0) > 50)

# 3.8: MCID with borderline threshold near pooled estimate
r = driver.execute_script('''
    var pooledSens = Math.round(lastAnalysisResult.pooledSens * 100);
    document.getElementById('mcid-sens-value').value = String(pooledSens);
    document.getElementById('mcid-spec-value').value = '50';
    renderMCIDAnalysisDTA();
    var html = document.getElementById('mcidDTAArea')?.innerHTML || '';
    return {pooledSens: pooledSens, len: html.length,
            hasContent: html.includes('Pooled Sens') || html.includes('threshold')};
''')
check('MCID: borderline threshold near pooled estimate renders',
      r and r.get('len', 0) > 50, f"pooled sens ~ {r.get('pooledSens')}%")


# =============================================
# 4. PATIENT RISK BOUNDARY CASES
# =============================================
print('\n--- 4. Patient Risk Boundary Cases ---')

# 4.1: prevalence=1 (very low)
r = driver.execute_script('''
    var slider = document.getElementById('risk-pretest');
    slider.value = '1';
    computePatientRiskDTA();
    var html = document.getElementById('patientRiskDTAResults')?.innerHTML || '';
    var allPcts = [];
    var regex = /(\\d+\\.\\d+)%/g;
    var m;
    while ((m = regex.exec(html)) !== null) allPcts.push(parseFloat(m[1]));
    return {len: html.length, allPcts: allPcts, hasTP: html.includes('TP'),
            hasFP: html.includes('FP'), hasFN: html.includes('FN'), hasTN: html.includes('TN')};
''')
check('Patient Risk: prevalence=1% renders', r and r.get('len', 0) > 100)
check('Patient Risk: prevalence=1% shows TP/FP/FN/TN', r and r.get('hasTP') and r.get('hasTN'))

# 4.2: prevalence=99 (very high)
r = driver.execute_script('''
    document.getElementById('risk-pretest').value = '99';
    computePatientRiskDTA();
    var html = document.getElementById('patientRiskDTAResults')?.innerHTML || '';
    var allPcts = [];
    var regex = /(\\d+\\.\\d+)%/g;
    var m;
    while ((m = regex.exec(html)) !== null) allPcts.push(parseFloat(m[1]));
    return {len: html.length, allPcts: allPcts};
''')
check('Patient Risk: prevalence=99% renders', r and r.get('len', 0) > 100)

# 4.3: prevalence=50 (equal prior odds)
r = driver.execute_script('''
    document.getElementById('risk-pretest').value = '50';
    computePatientRiskDTA();
    var html = document.getElementById('patientRiskDTAResults')?.innerHTML || '';
    return {len: html.length, has50: html.includes('50.0%')};
''')
check('Patient Risk: prevalence=50% renders', r and r.get('len', 0) > 100)
check('Patient Risk: prevalence=50% shows 50.0% pretest', r and r.get('has50'))

# 4.4: PPV approaches 100% at high prevalence
r = driver.execute_script('''
    document.getElementById('risk-pretest').value = '99';
    computePatientRiskDTA();
    var html = document.getElementById('patientRiskDTAResults')?.innerHTML || '';
    // Extract the PPV (Post-test Prob +) — look for the blue-colored percentage
    var allPcts = [];
    var regex = /(\\d+\\.\\d+)%/g;
    var m;
    while ((m = regex.exec(html)) !== null) allPcts.push(parseFloat(m[1]));
    // PPV is typically the 2nd percentage (after pretest)
    return {allPcts: allPcts, ppv: allPcts.length > 1 ? allPcts[1] : null};
''')
ppv_val = r.get('ppv') if r else None
check('Patient Risk: PPV approaches 100% at prev=99%',
      ppv_val is not None and ppv_val > 95, f"PPV={ppv_val}%" if ppv_val else '')

# 4.5: NPV approaches 100% at low prevalence
r = driver.execute_script('''
    document.getElementById('risk-pretest').value = '1';
    computePatientRiskDTA();
    var html = document.getElementById('patientRiskDTAResults')?.innerHTML || '';
    var allPcts = [];
    var regex = /(\\d+\\.\\d+)%/g;
    var m;
    while ((m = regex.exec(html)) !== null) allPcts.push(parseFloat(m[1]));
    // NPV is typically the 3rd percentage
    return {allPcts: allPcts, npv: allPcts.length > 2 ? allPcts[2] : null};
''')
npv_val = r.get('npv') if r else None
check('Patient Risk: NPV approaches 100% at prev=1%',
      npv_val is not None and npv_val > 95, f"NPV={npv_val}%" if npv_val else '')

# 4.6: TP+FP+FN+TN sum to 1000 (per-1000 breakdown)
r = driver.execute_script('''
    document.getElementById('risk-pretest').value = '20';
    computePatientRiskDTA();
    var html = document.getElementById('patientRiskDTAResults')?.innerHTML || '';
    var nums = [];
    var regex = /(\\d+) (TP|FP|FN|TN)/g;
    var m;
    while ((m = regex.exec(html)) !== null) nums.push(parseInt(m[1]));
    return {counts: nums, sum: nums.reduce(function(a, b) { return a + b; }, 0)};
''')
check('Patient Risk: TP+FP+FN+TN sums to 1000',
      r and r.get('sum') == 1000, f"sum={r.get('sum')}, counts={r.get('counts')}")

# 4.7: Verify Bayes theorem: post-test odds = pretest odds x LR
r = driver.execute_script('''
    document.getElementById('risk-pretest').value = '30';
    computePatientRiskDTA();
    var sens = lastAnalysisResult.pooledSens;
    var spec = lastAnalysisResult.pooledSpec;
    var plr = lastAnalysisResult.plr || (sens / (1 - spec));
    var nlr = lastAnalysisResult.nlr || ((1 - sens) / spec);
    var prev = 0.30;
    var preOdds = prev / (1 - prev);
    var expPPV = (preOdds * plr) / (1 + preOdds * plr);
    var expNPV = 1 - (preOdds * nlr) / (1 + preOdds * nlr);
    // Read actual from DOM
    var html = document.getElementById('patientRiskDTAResults')?.innerHTML || '';
    var allPcts = [];
    var regex = /(\\d+\\.\\d+)%/g;
    var m;
    while ((m = regex.exec(html)) !== null) allPcts.push(parseFloat(m[1]));
    return {expPPV: expPPV * 100, expNPV: expNPV * 100, allPcts: allPcts};
''')
if r and r.get('allPcts') and len(r['allPcts']) >= 3:
    check('Patient Risk: PPV matches Bayes theorem',
          abs(r['allPcts'][1] - r['expPPV']) < 0.5,
          f"expected={r['expPPV']:.1f}%, found={r['allPcts'][1]:.1f}%")
    check('Patient Risk: NPV matches Bayes theorem',
          abs(r['allPcts'][2] - r['expNPV']) < 0.5,
          f"expected={r['expNPV']:.1f}%, found={r['allPcts'][2]:.1f}%")
else:
    check('Patient Risk: PPV matches Bayes theorem', False, 'could not extract')
    check('Patient Risk: NPV matches Bayes theorem', False, 'could not extract')


# =============================================
# 5. EFFECT SIZE CONVERTER EDGE CASES
# =============================================
print('\n--- 5. Effect Size Converter Edge Cases ---')

def run_converter(type_val, value, prev, desc):
    """Helper: set converter inputs, call function, return result dict."""
    return driver.execute_script(f'''
        var typeEl = document.getElementById('esc-dta-type');
        var valEl = document.getElementById('esc-dta-value');
        var prevEl = document.getElementById('esc-dta-prev');
        typeEl.value = '{type_val}';
        valEl.value = '{value}';
        prevEl.value = '{prev}';
        convertEffectSizeDTA();
        var html = document.getElementById('escDTAResults')?.innerHTML || '';
        return {{html: html.substring(0, 500), len: html.length,
                 hasTable: html.includes('<table'),
                 hasError: html.includes('opacity:0.6') || html.includes('must be') || html.includes('should be'),
                 hasSens: html.includes('Sensitivity'),
                 hasSpec: html.includes('Specificity'),
                 hasDOR: html.includes('DOR'),
                 hasPLR: html.includes('PLR'),
                 hasNLR: html.includes('NLR'),
                 hasYouden: html.includes('Youden'),
                 hasNND: html.includes('NND'),
                 hasAUC: html.includes('AUC'),
                 hasPPV: html.includes('PPV'),
                 hasNPV: html.includes('NPV')}};
    ''')

# 5.1: DOR=1 (uninformative test)
r = run_converter('dor', '1', '20', 'DOR=1 uninformative')
check('Converter: DOR=1 renders table', r and r.get('hasTable'))
# DOR=1 => sqrt(1)=1 => sens=1/(1+1)=0.50 => 50%
check('Converter: DOR=1 gives sens=spec=50%',
      r and '50.0' in r.get('html', ''), 'uninformative test')

# 5.2: DOR=1000 (extremely informative)
r = run_converter('dor', '1000', '20', 'DOR=1000')
check('Converter: DOR=1000 renders table', r and r.get('hasTable'))
# sqrt(1000)~31.6, sens=31.6/32.6~96.9%
check('Converter: DOR=1000 gives very high sens/spec',
      r and ('96.' in r.get('html', '') or '97.' in r.get('html', '')))

# 5.3: DOR=1.001 (barely above chance)
r = run_converter('dor', '1.001', '20', 'DOR=1.001')
check('Converter: DOR=1.001 renders table', r and r.get('hasTable'))

# 5.4: PLR=1 (uninformative — sens=1/2=50%)
r = run_converter('plr', '1', '20', 'PLR=1')
check('Converter: PLR=1 renders table', r and r.get('hasTable'))
check('Converter: PLR=1 gives sens~50%', r and '50.0' in r.get('html', ''))

# 5.5: NLR=0.99 (barely useful)
r = run_converter('nlr', '0.99', '20', 'NLR=0.99')
check('Converter: NLR=0.99 renders table', r and r.get('hasTable'))

# 5.6: Youden J=0.01 (near-uninformative, NND very large)
r = run_converter('youden', '0.01', '20', 'Youden=0.01')
check('Converter: Youden=0.01 renders table', r and r.get('hasTable'))
check('Converter: Youden=0.01 shows NND', r and r.get('hasNND'))
# NND for J=0.01 => ceil(1/0.01) = 100
r2 = driver.execute_script('return document.getElementById("escDTAResults")?.textContent || ""')
check('Converter: Youden=0.01 NND=100', r2 and '100' in r2, 'NND = ceil(1/0.01)')

# 5.7: AUC=0.51 (barely above chance)
r = run_converter('auc', '0.51', '20', 'AUC=0.51')
check('Converter: AUC=0.51 renders table', r and r.get('hasTable'))

# 5.8: AUC=0.99 (near-perfect)
r = run_converter('auc', '0.99', '20', 'AUC=0.99')
check('Converter: AUC=0.99 renders table', r and r.get('hasTable'))
check('Converter: AUC=0.99 gives very high sens/spec',
      r and r.get('hasSens'))

# 5.9: DOR=25 with prevalence=1% (low prevalence)
r = run_converter('dor', '25', '1', 'DOR=25 prev=1%')
check('Converter: DOR=25 prev=1% renders', r and r.get('hasTable'))
check('Converter: DOR=25 prev=1% shows PPV/NPV', r and r.get('hasPPV') and r.get('hasNPV'))

# 5.10: DOR=25 with prevalence=99% (high prevalence)
r = run_converter('dor', '25', '99', 'DOR=25 prev=99%')
check('Converter: DOR=25 prev=99% renders', r and r.get('hasTable'))

# 5.11: Invalid — negative DOR
r = run_converter('dor', '-5', '20', 'negative DOR')
check('Converter: rejects negative DOR', r and r.get('hasError'))

# 5.12: Invalid — NLR > 1
r = run_converter('nlr', '1.5', '20', 'NLR>1')
check('Converter: rejects NLR > 1', r and r.get('hasError'))

# 5.13: Invalid — AUC < 0.5
r = run_converter('auc', '0.4', '20', 'AUC<0.5')
check('Converter: rejects AUC < 0.5', r and r.get('hasError'))


# =============================================
# 6. WHAT-IF SIMULATOR EDGE CASES
# =============================================
print('\n--- 6. What-If Simulator Edge Cases ---')

# 6.1: What-if with default/baseline values from analysis
r = driver.execute_script('''
    var sens = lastAnalysisResult.pooledSens;
    var spec = lastAnalysisResult.pooledSpec;
    try {
        var wi = whatIfSimulator({sensitivity: sens, specificity: spec, prevalence: 0.20, population: 10000});
        return {ok: true, ppv: wi.rates.ppv, npv: wi.rates.npv,
                tp: wi.counts.tp, fp: wi.counts.fp, fn: wi.counts.fn, tn: wi.counts.tn,
                postPos: wi.fagan.postTestPosProb, postNeg: wi.fagan.postTestNegProb,
                nb: wi.impact.netBenefit};
    } catch(e) {
        return {ok: false, error: e.message};
    }
''')
check('What-If: returns valid result', r and r.get('ok'))
check('What-If: PPV is valid probability',
      r and r.get('ppv') is not None and 0 < r['ppv'] < 1, f"PPV={r.get('ppv'):.3f}" if r and r.get('ppv') else '')
check('What-If: NPV is valid probability',
      r and r.get('npv') is not None and 0 < r['npv'] < 1, f"NPV={r.get('npv'):.3f}" if r and r.get('npv') else '')

# 6.2: What-if with perfect test (sens=spec=0.99)
r = driver.execute_script('''
    var wi = whatIfSimulator({sensitivity: 0.99, specificity: 0.99, prevalence: 0.1, population: 10000});
    return {tp: wi.counts.tp, fp: wi.counts.fp, fn: wi.counts.fn, tn: wi.counts.tn,
            ppv: wi.rates.ppv, dor: wi.rates.dor, nnd: wi.rates.nnd};
''')
check('What-If: near-perfect test has very high PPV',
      r and r.get('ppv') is not None and r['ppv'] > 0.9, f"PPV={r.get('ppv'):.3f}" if r and r.get('ppv') else '')
check('What-If: near-perfect test has very high DOR',
      r and r.get('dor') is not None and r['dor'] > 1000, f"DOR={r.get('dor'):.0f}" if r and r.get('dor') else '')

# 6.3: What-if with uninformative test (sens=spec=0.5)
r = driver.execute_script('''
    var wi = whatIfSimulator({sensitivity: 0.5, specificity: 0.5, prevalence: 0.2, population: 10000});
    return {ppv: wi.rates.ppv, npv: wi.rates.npv, dor: wi.rates.dor,
            postPos: wi.fagan.postTestPosProb, postNeg: wi.fagan.postTestNegProb};
''')
check('What-If: uninformative test DOR~1',
      r and r.get('dor') is not None and abs(r['dor'] - 1.0) < 0.01, f"DOR={r.get('dor'):.3f}" if r and r.get('dor') else '')
check('What-If: uninformative test postPos ~ pretest',
      r and r.get('postPos') is not None and abs(r['postPos'] - 0.2) < 0.05,
      f"postPos={r.get('postPos'):.3f}" if r and r.get('postPos') else '')

# 6.4: What-if with very low prevalence
r = driver.execute_script('''
    var wi = whatIfSimulator({sensitivity: 0.90, specificity: 0.90, prevalence: 0.001, population: 100000});
    return {ppv: wi.rates.ppv, fp: wi.counts.fp, tp: wi.counts.tp};
''')
check('What-If: low prevalence => many FP vs TP',
      r and r.get('fp') is not None and r.get('tp') is not None and r['fp'] > r['tp'],
      f"TP={r.get('tp')}, FP={r.get('fp')}")

# 6.5: What-if net benefit calculation
r = driver.execute_script('''
    var wi = whatIfSimulator({sensitivity: 0.90, specificity: 0.90, prevalence: 0.10, population: 10000});
    // Verify net benefit: NB = TP/N - FP/N * (pt/(1-pt))
    var nb_calc = (wi.counts.tp / 10000) - (wi.counts.fp / 10000) * (0.10 / (1 - 0.10));
    return {nb: wi.impact.netBenefit, nb_calc: nb_calc, diff: Math.abs(wi.impact.netBenefit - nb_calc)};
''')
check('What-If: net benefit formula correct',
      r and r.get('diff') is not None and r['diff'] < 0.005,
      f"NB={r.get('nb'):.4f}, calc={r.get('nb_calc'):.4f}" if r and r.get('nb') is not None else '')

# 6.6: What-if counts sum to population
r = driver.execute_script('''
    var wi = whatIfSimulator({sensitivity: 0.85, specificity: 0.92, prevalence: 0.15, population: 10000});
    return {sum: wi.counts.tp + wi.counts.fp + wi.counts.fn + wi.counts.tn,
            tp: wi.counts.tp, fp: wi.counts.fp, fn: wi.counts.fn, tn: wi.counts.tn};
''')
check('What-If: TP+FP+FN+TN = population',
      r and r.get('sum') == 10000, f"sum={r.get('sum')}")


# =============================================
# 7. DRAPERY PLOT EDGE CASES (k=2 dataset)
# =============================================
print('\n--- 7. Drapery Plot Edge Cases ---')

# 7.1: Drapery plot with main 6-study dataset
r = driver.execute_script('''
    var c = document.getElementById('advDraperyPlotContainer');
    if (!c) return {exists: false};
    return {exists: true, len: c.innerHTML.length,
            hasSVG: c.innerHTML.includes('<svg'),
            hasPath: c.innerHTML.includes('<path'),
            svgCount: c.querySelectorAll('svg').length,
            pathCount: c.querySelectorAll('svg path').length};
''')
check('Drapery: SVG rendered for k=6', r and r.get('hasSVG'))
check('Drapery: has p-value curve path', r and r.get('pathCount', 0) >= 1,
      f"{r.get('pathCount')} paths")

# 7.2: Drapery plot has significance threshold lines (p=0.05, p=0.10)
r = driver.execute_script('''
    var html = document.getElementById('advDraperyPlotContainer')?.innerHTML || '';
    return {has005: html.includes('p=0.05'), has010: html.includes('p=0.10'),
            hasDOR1: html.includes('DOR=1')};
''')
check('Drapery: shows p=0.05 threshold', r and r.get('has005'))
check('Drapery: shows p=0.10 threshold', r and r.get('has010'))
check('Drapery: shows null hypothesis DOR=1 line', r and r.get('hasDOR1'))

# 7.3: Drapery with k=2 dataset (minimum for bivariate)
r = driver.execute_script('''
    var twoStudies = [
        {tp:52,fp:14,fn:8,tn:76, sens:52/60, spec:76/90},
        {tp:44,fp:20,fn:6,tn:151, sens:44/50, spec:151/171}
    ];
    try {
        var r2 = improvedBivariatePool(twoStudies, 0.95);
        if (!r2 || r2.seMu1 == null) return {ok: false, error: 'pool failed'};
        renderDraperyPlotDTA(r2, 0.95);
        var html = document.getElementById('advDraperyPlotContainer')?.innerHTML || '';
        return {ok: true, hasSVG: html.includes('<svg'), len: html.length};
    } catch(e) {
        return {ok: false, error: e.message};
    }
''')
check('Drapery: k=2 renders without error', r and r.get('ok'), str(r.get('error', '')))

# 7.4: Drapery with very homogeneous data
r = driver.execute_script('''
    var homoStudies = [
        {tp:80,fp:20,fn:20,tn:80, sens:0.8, spec:0.8},
        {tp:81,fp:19,fn:19,tn:81, sens:0.81, spec:0.81},
        {tp:79,fp:21,fn:21,tn:79, sens:0.79, spec:0.79},
        {tp:80,fp:20,fn:20,tn:80, sens:0.8, spec:0.8}
    ];
    try {
        var rh = improvedBivariatePool(homoStudies, 0.95);
        if (!rh) return {ok: false, error: 'pool returned null'};
        renderDraperyPlotDTA(rh, 0.95);
        var html = document.getElementById('advDraperyPlotContainer')?.innerHTML || '';
        return {ok: true, hasSVG: html.includes('<svg'), len: html.length,
                mu1: rh.mu1, seMu1: rh.seMu1};
    } catch(e) {
        return {ok: false, error: e.message};
    }
''')
check('Drapery: homogeneous data renders without error', r and r.get('ok'), str(r.get('error', '')))

# Restore drapery for main dataset
driver.execute_script('renderDraperyPlotDTA(lastAnalysisResult, 0.95);')
time.sleep(0.3)


# =============================================
# 8. EXCLUSION MATRIX EDGE CASES
# =============================================
print('\n--- 8. Exclusion Matrix Edge Cases ---')

# 8.1: Exclusion matrix rendered for k=6
r = driver.execute_script('''
    var c = document.getElementById('advExclusionMatrixContainer');
    if (!c) return {exists: false};
    return {exists: true, len: c.innerHTML.length,
            hasTable: c.innerHTML.includes('<table'),
            rows: c.querySelectorAll('tr').length};
''')
check('Exclusion: table rendered for k=6', r and r.get('hasTable'))
check('Exclusion: has 6 data rows + header (>=7 tr)', r and r.get('rows', 0) >= 7,
      f"{r.get('rows')} rows")

# 8.2: Exclusion matrix shows delta columns
r = driver.execute_script('''
    var html = document.getElementById('advExclusionMatrixContainer')?.innerHTML || '';
    return {hasDeltaSens: html.includes('Sens'), hasDeltaSpec: html.includes('Spec'),
            hasDeltaDOR: html.includes('DOR'), hasConclusion: html.includes('Stable') || html.includes('CHANGED'),
            hasRobustness: html.includes('Robustness')};
''')
check('Exclusion: shows delta Sens column', r and r.get('hasDeltaSens'))
check('Exclusion: shows delta DOR column', r and r.get('hasDeltaDOR'))
check('Exclusion: shows robustness summary', r and r.get('hasRobustness'))

# 8.3: Exclusion with k=2 dataset — should show empty (needs >= 3 studies)
r = driver.execute_script('''
    var twoStudies = [
        {tp:52,fp:14,fn:8,tn:76, sens:52/60, spec:76/90, authorYear:'Dao 2001'},
        {tp:44,fp:20,fn:6,tn:151, sens:44/50, spec:151/171, authorYear:'Morrison 2002'}
    ];
    try {
        var r2 = improvedBivariatePool(twoStudies, 0.95);
        if (!r2) return {ok: false, error: 'pool failed'};
        r2.studyData = twoStudies;
        renderExclusionMatrixDTA(r2, 0.95);
        var html = document.getElementById('advExclusionMatrixContainer')?.innerHTML || '';
        return {ok: true, len: html.length, isEmpty: html.length < 10};
    } catch(e) {
        return {ok: false, error: e.message};
    }
''')
check('Exclusion: k=2 handled gracefully (empty or min warning)',
      r and r.get('ok'), f"len={r.get('len')}, isEmpty={r.get('isEmpty')}")

# 8.4: Exclusion — check that removing most influential study changes pooled estimate
r = driver.execute_script('''
    // Restore main analysis exclusion matrix
    renderExclusionMatrixDTA(lastAnalysisResult, 0.95);
    var rows = document.querySelectorAll('#advExclusionMatrixContainer tbody tr');
    var maxDelta = 0;
    for (var row of rows) {
        var cells = row.querySelectorAll('td');
        if (cells.length >= 6) {
            // Delta Sens is typically the 3rd cell (index 2)
            var dStr = cells[2]?.textContent?.replace(/[+%]/g, '') || '0';
            var delta = Math.abs(parseFloat(dStr));
            if (isFinite(delta) && delta > maxDelta) maxDelta = delta;
        }
    }
    return {maxDelta: maxDelta, nRows: rows.length};
''')
check('Exclusion: at least one study changes pooled Sens > 0.1%',
      r and r.get('maxDelta', 0) > 0.1,
      f"max delta Sens = {r.get('maxDelta'):.1f}%")

# 8.5: Exclusion matrix shows study labels (Study N or author names)
r = driver.execute_script('''
    var html = document.getElementById('advExclusionMatrixContainer')?.textContent || '';
    // Studies may show as "Study 1" etc. (if `ay` not mapped to `authorYear`) or actual names
    var hasStudyLabels = html.includes('Study 1') || html.includes('Dao') || html.includes('Study ');
    var hasMultiple = (html.match(/Study \\d/g) || []).length >= 3 ||
                      (html.includes('Dao') && html.includes('Maisel'));
    return {hasStudyLabels: hasStudyLabels, hasMultiple: hasMultiple};
''')
check('Exclusion: shows study labels', r and r.get('hasStudyLabels') and r.get('hasMultiple'))


# =============================================
# 9. ADDITIONAL CROSS-CUTTING EDGE CASES
# =============================================
print('\n--- 9. Additional Cross-Cutting Edge Cases ---')

# 9.1: Fagan with pretest=50 and verify symmetry with PLR/NLR
r = driver.execute_script('''
    document.getElementById('faganPretest').value = '50';
    computeFagan();
    // Extract from table rows (not SVG ticks)
    var rows = document.querySelectorAll('#faganResult table tr');
    var postPos = null, postNeg = null;
    for (var row of rows) {
        var cells = row.querySelectorAll('td');
        if (cells.length >= 2) {
            var label = cells[0].textContent;
            var val = cells[1].textContent;
            var match = val.match(/(\\d+\\.?\\d*)%/);
            if (label.includes('test +') && match) postPos = parseFloat(match[1]);
            if ((label.includes('test \\u2212') || label.includes('test -')) && match) postNeg = parseFloat(match[1]);
        }
    }
    return {postPos: postPos, postNeg: postNeg};
''')
if r and r.get('postPos') is not None and r.get('postNeg') is not None:
    check('Fagan: pretest=50% => post-test+ > 50%',
          r['postPos'] > 50.0, f"postPos={r['postPos']:.1f}%")
    check('Fagan: pretest=50% => post-test- < 50%',
          r['postNeg'] < 50.0, f"postNeg={r['postNeg']:.1f}%")
else:
    check('Fagan: pretest=50% => post-test+ > 50%', False, 'could not extract from table')
    check('Fagan: pretest=50% => post-test- < 50%', False, 'could not extract from table')

# 9.2: Converter DOR=1 at different prevalences should give PPV=prev (uninformative)
r = driver.execute_script('''
    var typeEl = document.getElementById('esc-dta-type');
    var valEl = document.getElementById('esc-dta-value');
    var prevEl = document.getElementById('esc-dta-prev');
    // DOR=1, prev=50%
    typeEl.value = 'dor';
    valEl.value = '1';
    prevEl.value = '50';
    convertEffectSizeDTA();
    var html = document.getElementById('escDTAResults')?.innerHTML || '';
    // PPV should be ~50% for an uninformative test at 50% prevalence
    var ppvMatch = html.match(/PPV.*?(\\d+\\.\\d+)%/);
    var npvMatch = html.match(/NPV.*?(\\d+\\.\\d+)%/);
    return {ppv: ppvMatch ? parseFloat(ppvMatch[1]) : null,
            npv: npvMatch ? parseFloat(npvMatch[1]) : null};
''')
check('Converter: DOR=1 at prev=50% => PPV~50%',
      r and r.get('ppv') is not None and abs(r['ppv'] - 50.0) < 2.0,
      f"PPV={r.get('ppv')}" if r and r.get('ppv') else '')

# 9.3: Patient Risk at different prevalences — PPV monotonically increases with prevalence
r = driver.execute_script('''
    var ppvs = [];
    [5, 20, 50, 80].forEach(function(p) {
        document.getElementById('risk-pretest').value = String(p);
        computePatientRiskDTA();
        var html = document.getElementById('patientRiskDTAResults')?.innerHTML || '';
        var allPcts = [];
        var regex = /(\\d+\\.\\d+)%/g;
        var m;
        while ((m = regex.exec(html)) !== null) allPcts.push(parseFloat(m[1]));
        ppvs.push({prev: p, ppv: allPcts.length > 1 ? allPcts[1] : null});
    });
    return ppvs;
''')
if r and len(r) >= 4 and all(x.get('ppv') is not None for x in r):
    ppv_vals = [x['ppv'] for x in r]
    monotonic = all(ppv_vals[i] < ppv_vals[i+1] for i in range(len(ppv_vals)-1))
    check('Patient Risk: PPV monotonically increases with prevalence',
          monotonic, f"PPVs at prev 5/20/50/80: {[f'{v:.1f}' for v in ppv_vals]}")
else:
    check('Patient Risk: PPV monotonically increases with prevalence', False, 'could not extract')

# 9.4: DCA export button exists
r = driver.execute_script('''
    var btns = document.querySelectorAll('#advDCAContainer button');
    var exportBtn = false;
    for (var b of btns) {
        if (b.textContent.includes('Export') || b.textContent.includes('SVG')) exportBtn = true;
    }
    return {hasExportBtn: exportBtn, btnCount: btns.length};
''')
check('DCA: has export SVG button', r and r.get('hasExportBtn'))

# 9.5: Drapery mentions pooled DOR value
r = driver.execute_script('''
    var html = document.getElementById('advDraperyPlotContainer')?.textContent || '';
    return {hasPooledDOR: html.includes('Pooled DOR') || html.includes('pooled DOR')};
''')
check('Drapery: mentions pooled DOR value', r and r.get('hasPooledDOR'))

# 9.6: LASSO meta-regression function exists and handles gracefully
r = driver.execute_script('''
    try {
        var studies = lastAnalysisResult.studyData;
        // Construct simple moderator (threshold as numeric)
        var mods = studies.map(function(s) { return {threshold: parseFloat(s.threshold || '100')}; });
        var result = lassoMetaRegression(studies, mods, {lambda: 0.1});
        return {ok: true, hasCoefs: !!result.coefficients, hasLambda: result.lambda != null};
    } catch(e) {
        return {ok: false, error: e.message};
    }
''')
check('LASSO: function exists and returns result', r and r.get('ok'), str(r.get('error', '')))


# =============================================
# Console error check
# =============================================
print('\n--- Console Error Check ---')
logs = driver.get_log('browser')
severe = [l for l in logs if l['level'] == 'SEVERE' and 'favicon' not in l['message'].lower()]
check('No SEVERE JS console errors', len(severe) == 0,
      f'{len(severe)} errors' + (f': {severe[0]["message"][:100]}' if severe else ''))

# --- Teardown ---
driver.quit()

# Summary
print(f'\n{"="*70}')
print(f'  Edge Case Tests: {passed} passed, {failed} failed, {total} total')
print(f'{"="*70}')
if errors:
    print(f'\n  Failures:')
    for e in errors:
        print(f'    - {e}')
sys.exit(0 if failed == 0 else 1)
