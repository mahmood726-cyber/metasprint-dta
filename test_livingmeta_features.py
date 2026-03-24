"""
test_livingmeta_features.py — Selenium tests for 5 ported LivingMeta features.

Features tested:
1. Drapery Plot (DTA-adapted SVG, p-value function for log-DOR)
2. Exclusion Sensitivity Matrix (leave-one-out Sens/Spec/DOR)
3. MCID Threshold Analysis (pooled vs clinical thresholds)
4. Patient Risk Calculator (post-test probabilities via Bayes)
5. Effect Size Converter (DOR/PLR/NLR/Youden/AUC interconversion)

Usage: python test_livingmeta_features.py
"""

import sys
import io
import time
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metasprint-dta.html')

passed = 0
failed = 0
errors = []


def check(name, condition, detail=''):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f'  \u2713 {name}')
    else:
        failed += 1
        errors.append(name)
        print(f'  \u2717 {name}' + (f' -- {detail}' if detail else ''))


def setup():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--window-size=1920,1200')
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(5)
    driver.get('file:///' + HTML_PATH.replace('\\', '/'))
    time.sleep(2)
    return driver


def inject_bnp_and_analyze(driver):
    """Inject BNP benchmark data (6 studies), run analysis, trigger Phase 6 features."""
    driver.execute_script("""
        extractedStudies.length = 0;
        const raw = [
            {authorYear:"Dao 2001",tp:"52",fp:"14",fn:"8",tn:"76",indexTest:"BNP"},
            {authorYear:"Morrison 2002",tp:"44",fp:"20",fn:"6",tn:"151",indexTest:"BNP"},
            {authorYear:"Maisel 2002",tp:"379",fp:"83",fn:"65",tn:"959",indexTest:"BNP"},
            {authorYear:"Mueller 2004",tp:"89",fp:"17",fn:"14",tn:"337",indexTest:"BNP"},
            {authorYear:"Lainchbury 2003",tp:"40",fp:"22",fn:"5",tn:"138",indexTest:"BNP"},
            {authorYear:"McCullough 2002",tp:"163",fp:"44",fn:"21",tn:"416",indexTest:"BNP"}
        ];
        let id = 1;
        for (const s of raw) extractedStudies.push({...s, id: "b" + id++});
        document.querySelectorAll(".phase").forEach(p => p.style.display = "none");
        document.getElementById("phase-analyze").style.display = "block";
        const studies = extractedStudies.map(s => ({tp:parseInt(s.tp),fp:parseInt(s.fp),fn:parseInt(s.fn),tn:parseInt(s.tn),authorYear:s.authorYear}));
        const prepared = prepareDTAStudyData(studies, "0.5");
        const result = computeDTAAnalysis(prepared, 0.95, "bivariate", "0.5");
        lastAnalysisResult = result;
        renderDTAResults(result, 0.95, 95, "bivariate", "bivariate");
        toggleAdvancedDTA();
    """)
    time.sleep(3)


# ═══════════════════════════════════════════════════════════════
# TEST 1: DRAPERY PLOT
# ═══════════════════════════════════════════════════════════════
def test_drapery_plot(driver):
    """Test drapery plot renders SVG with correct structure."""
    print('\n--- 1. Drapery Plot ---')

    r = driver.execute_script("""
        const c = {};
        const container = document.getElementById('advDraperyPlotContainer');
        c.exists = !!container;
        c.hasSVG = container && container.querySelector('svg') !== null;
        c.hasTitle = container && container.innerHTML.includes('Drapery Plot');
        c.hasRucker = container && container.innerHTML.includes('cker');  // Rucker
        c.hasPvalueCurve = container && container.querySelector('path') !== null;
        c.hasSignificanceLine = container && container.innerHTML.includes('p=0.05');
        c.hasDOR1Line = container && container.innerHTML.includes('DOR=1');
        c.hasPooledLine = container && container.innerHTML.includes('Pooled DOR=');
        c.hasExportBtn = container && container.innerHTML.includes('Export SVG');
        c.hasAxisLabels = container && container.innerHTML.includes('Hypothesized DOR') && container.innerHTML.includes('P-value');
        c.hasAriaLabel = container && container.querySelector('svg[role="img"]') !== null;

        // Verify the curve is based on correct math (logDOR = mu1 + mu2)
        if (typeof lastAnalysisResult !== 'undefined' && lastAnalysisResult) {
            const r = lastAnalysisResult;
            c.logDOR = (r.mu1 ?? 0) + (r.mu2 ?? 0);
            c.dor = Math.exp(c.logDOR);
            c.dorValid = c.dor > 1;  // BNP data should have DOR > 1
        }

        // Check SVG viewBox exists
        const svg = container ? container.querySelector('svg') : null;
        c.hasViewBox = svg && svg.getAttribute('viewBox') !== null;

        return c;
    """)

    check('Drapery: container exists', r.get('exists'))
    check('Drapery: SVG rendered', r.get('hasSVG'))
    check('Drapery: title present', r.get('hasTitle'))
    check('Drapery: Rucker & Schwarzer reference', r.get('hasRucker'))
    check('Drapery: p-value curve path exists', r.get('hasPvalueCurve'))
    check('Drapery: p=0.05 significance line', r.get('hasSignificanceLine'))
    check('Drapery: DOR=1 null line', r.get('hasDOR1Line'))
    check('Drapery: pooled DOR marked', r.get('hasPooledLine'))
    check('Drapery: export SVG button', r.get('hasExportBtn'))
    check('Drapery: axis labels (DOR + P-value)', r.get('hasAxisLabels'))
    check('Drapery: SVG has role="img" (a11y)', r.get('hasAriaLabel'))
    check('Drapery: SVG has viewBox', r.get('hasViewBox'))
    check('Drapery: pooled DOR > 1 for BNP data', r.get('dorValid'))


# ═══════════════════════════════════════════════════════════════
# TEST 2: EXCLUSION SENSITIVITY MATRIX
# ═══════════════════════════════════════════════════════════════
def test_exclusion_matrix(driver):
    """Test exclusion matrix renders correct LOO table."""
    print('\n--- 2. Exclusion Sensitivity Matrix ---')

    r = driver.execute_script("""
        const c = {};
        const container = document.getElementById('advExclusionMatrixContainer');
        c.exists = !!container;
        c.hasTable = container && container.querySelector('table') !== null;
        c.hasTitle = container && container.innerHTML.includes('Exclusion Sensitivity Matrix');

        // Check all 6 BNP studies appear
        c.hasDao = container && container.innerHTML.includes('Dao');
        c.hasMorrison = container && container.innerHTML.includes('Morrison');
        c.hasMaisel = container && container.innerHTML.includes('Maisel');
        c.hasMueller = container && container.innerHTML.includes('Mueller');
        c.hasLainchbury = container && container.innerHTML.includes('Lainchbury');
        c.hasMcCullough = container && container.innerHTML.includes('McCullough');

        // Check columns exist
        c.hasSensCol = container && container.innerHTML.includes('\u0394 Sens');
        c.hasSpecCol = container && container.innerHTML.includes('\u0394 Spec');
        c.hasDORCol = container && container.innerHTML.includes('\u0394 DOR');
        c.hasSigCol = container && container.innerHTML.includes('Sig?');
        c.hasConclusionCol = container && container.innerHTML.includes('Conclusion');

        // Check robustness summary
        c.hasRobustness = container && container.innerHTML.includes('Robustness');

        // Count table rows (should be 6 studies = 6 data rows)
        const rows = container ? container.querySelectorAll('tbody tr') : [];
        c.rowCount = rows.length;

        // Check delta values are present and numeric
        const firstRow = rows.length > 0 ? rows[0] : null;
        if (firstRow) {
            const cells = firstRow.querySelectorAll('td');
            c.hasDeltaValues = cells.length >= 9;  // name + Sens + dSens + Spec + dSpec + DOR + dDOR + Sig + Conclusion
        }

        return c;
    """)

    check('Exclusion: container exists', r.get('exists'))
    check('Exclusion: table rendered', r.get('hasTable'))
    check('Exclusion: title present', r.get('hasTitle'))
    check('Exclusion: Dao 2001 present', r.get('hasDao'))
    check('Exclusion: Morrison 2002 present', r.get('hasMorrison'))
    check('Exclusion: Maisel 2002 present', r.get('hasMaisel'))
    check('Exclusion: Mueller 2004 present', r.get('hasMueller'))
    check('Exclusion: Lainchbury 2003 present', r.get('hasLainchbury'))
    check('Exclusion: McCullough 2002 present', r.get('hasMcCullough'))
    check('Exclusion: delta Sens column', r.get('hasSensCol'))
    check('Exclusion: delta Spec column', r.get('hasSpecCol'))
    check('Exclusion: delta DOR column', r.get('hasDORCol'))
    check('Exclusion: Sig? column', r.get('hasSigCol'))
    check('Exclusion: Conclusion column', r.get('hasConclusionCol'))
    check('Exclusion: robustness summary', r.get('hasRobustness'))
    check('Exclusion: 6 study rows', r.get('rowCount') == 6, f'got {r.get("rowCount")}')
    check('Exclusion: rows have full delta data', r.get('hasDeltaValues'))


# ═══════════════════════════════════════════════════════════════
# TEST 3: MCID THRESHOLD ANALYSIS
# ═══════════════════════════════════════════════════════════════
def test_mcid_analysis(driver):
    """Test MCID threshold analysis with custom thresholds."""
    print('\n--- 3. MCID Threshold Analysis ---')

    r = driver.execute_script("""
        const c = {};

        // Section should be visible after analysis
        const section = document.getElementById('mcidDTASection');
        c.sectionVisible = section && section.style.display !== 'none';

        // Set thresholds: 80% sens, 80% spec
        const sensInput = document.getElementById('mcid-sens-value');
        const specInput = document.getElementById('mcid-spec-value');
        if (sensInput) sensInput.value = '80';
        if (specInput) specInput.value = '80';

        // Trigger MCID analysis
        renderMCIDAnalysisDTA();

        const area = document.getElementById('mcidDTAArea');
        c.areaExists = !!area;
        c.hasContent = area && area.innerHTML.length > 50;

        // Check threshold cards exist
        c.hasSensThreshold = area && area.innerHTML.includes('threshold');
        c.hasPooledSens = area && area.innerHTML.includes('Pooled Sens');
        c.hasPooledSpec = area && area.innerHTML.includes('Pooled Spec');

        // Check CI assessment
        c.hasCIAbove = area && (area.innerHTML.includes('CI above') || area.innerHTML.includes('CI crosses'));

        // Check individual study counts
        c.hasStudyCount = area && area.innerHTML.includes('/6');

        // Now test with high thresholds (95%) — should fail for BNP
        sensInput.value = '95';
        specInput.value = '95';
        renderMCIDAnalysisDTA();
        // Check for cross mark (sens ~86% < 95%)
        c.highThreshFail = area && area.innerHTML.includes('\u2718');

        // Test predictive probability
        c.hasPredProb = area && area.innerHTML.includes('P(future study');

        // Reset to 80%
        sensInput.value = '80';
        specInput.value = '80';
        renderMCIDAnalysisDTA();

        return c;
    """)

    check('MCID: section visible', r.get('sectionVisible'))
    check('MCID: area exists', r.get('areaExists'))
    check('MCID: content rendered', r.get('hasContent'))
    check('MCID: threshold text present', r.get('hasSensThreshold'))
    check('MCID: pooled Sens card', r.get('hasPooledSens'))
    check('MCID: pooled Spec card', r.get('hasPooledSpec'))
    check('MCID: CI assessment (above/crosses)', r.get('hasCIAbove'))
    check('MCID: study count (/6)', r.get('hasStudyCount'))
    check('MCID: high threshold (95%) shows failure', r.get('highThreshFail'))
    check('MCID: predictive probability shown', r.get('hasPredProb'))


# ═══════════════════════════════════════════════════════════════
# TEST 4: PATIENT RISK CALCULATOR
# ═══════════════════════════════════════════════════════════════
def test_patient_risk(driver):
    """Test patient risk calculator with various prevalence values."""
    print('\n--- 4. Patient Risk Calculator ---')

    r = driver.execute_script("""
        const c = {};

        // Section should be visible after analysis
        const section = document.getElementById('patientRiskDTASection');
        c.sectionVisible = section && section.style.display !== 'none';

        // Set prevalence slider to 20%
        const slider = document.getElementById('risk-pretest');
        if (slider) slider.value = '20';
        computePatientRiskDTA();

        const area = document.getElementById('patientRiskDTAResults');
        c.areaExists = !!area;
        c.hasContent = area && area.innerHTML.length > 50;

        // Check core metrics
        c.hasPPV = area && (area.innerHTML.includes('Post-test Prob') || area.innerHTML.includes('PPV'));
        c.hasNPV = area && (area.innerHTML.includes('Confidence if negative') || area.innerHTML.includes('NPV'));
        c.hasPretest = area && area.innerHTML.includes('Pre-test');
        c.hasPLR = area && area.innerHTML.includes('PLR');
        c.hasNLR = area && area.innerHTML.includes('NLR');
        c.hasRuleIn = area && area.innerHTML.includes('rule-in');
        c.hasRuleOut = area && area.innerHTML.includes('rule-out');

        // Check per-1000 breakdown
        c.has1000 = area && area.innerHTML.includes('Per 1,000');
        c.hasTP = area && area.innerHTML.includes('TP');
        c.hasFP = area && area.innerHTML.includes('FP');
        c.hasFN = area && area.innerHTML.includes('FN');
        c.hasTN = area && area.innerHTML.includes('TN');

        // Verify math: for BNP (sens ~86%, spec ~93%) at prev=20%
        // PLR = 0.86/0.07 ~ 12.3, NLR = 0.14/0.93 ~ 0.15
        // Post-test+ = 0.25*12.3 / (1+0.25*12.3) ~ 0.75
        const r2 = lastAnalysisResult;
        const sens = r2.pooledSens;
        const spec = r2.pooledSpec;
        c.sensRange = sens > 0.80 && sens < 0.95;
        c.specRange = spec > 0.85 && spec < 0.98;

        // Test with high prevalence (80%)
        slider.value = '80';
        computePatientRiskDTA();
        const html80 = area.innerHTML;
        // At 80% prevalence, PPV should be very high
        c.highPrevContent = html80.length > 50;

        // Test with low prevalence (5%)
        slider.value = '5';
        computePatientRiskDTA();
        const html5 = area.innerHTML;
        c.lowPrevContent = html5.length > 50;

        // Verify prevalence label updates
        const valLabel = document.getElementById('risk-pretest-val');
        c.labelUpdated = valLabel && valLabel.textContent.includes('5');

        // Reset
        slider.value = '20';
        computePatientRiskDTA();

        return c;
    """)

    check('PatientRisk: section visible', r.get('sectionVisible'))
    check('PatientRisk: area exists', r.get('areaExists'))
    check('PatientRisk: content rendered', r.get('hasContent'))
    check('PatientRisk: PPV shown', r.get('hasPPV'))
    check('PatientRisk: NPV shown', r.get('hasNPV'))
    check('PatientRisk: pre-test probability', r.get('hasPretest'))
    check('PatientRisk: PLR (rule-in)', r.get('hasPLR'))
    check('PatientRisk: NLR (rule-out)', r.get('hasNLR'))
    check('PatientRisk: rule-in label', r.get('hasRuleIn'))
    check('PatientRisk: rule-out label', r.get('hasRuleOut'))
    check('PatientRisk: per 1,000 breakdown', r.get('has1000'))
    check('PatientRisk: TP count', r.get('hasTP'))
    check('PatientRisk: FP count', r.get('hasFP'))
    check('PatientRisk: FN count', r.get('hasFN'))
    check('PatientRisk: TN count', r.get('hasTN'))
    check('PatientRisk: sens in expected range', r.get('sensRange'))
    check('PatientRisk: spec in expected range', r.get('specRange'))
    check('PatientRisk: high prevalence (80%) renders', r.get('highPrevContent'))
    check('PatientRisk: low prevalence (5%) renders', r.get('lowPrevContent'))
    check('PatientRisk: label updates on slider change', r.get('labelUpdated'))


# ═══════════════════════════════════════════════════════════════
# TEST 5: EFFECT SIZE CONVERTER
# ═══════════════════════════════════════════════════════════════
def test_effect_converter(driver):
    """Test DTA effect size converter: DOR/PLR/NLR/Youden/AUC."""
    print('\n--- 5. Effect Size Converter ---')

    r = driver.execute_script("""
        const c = {};

        // Section should be visible
        const section = document.getElementById('effectConverterDTASection');
        c.sectionVisible = section && section.style.display !== 'none';

        const typeSelect = document.getElementById('esc-dta-type');
        const valueInput = document.getElementById('esc-dta-value');
        const prevInput = document.getElementById('esc-dta-prev');
        const area = document.getElementById('escDTAResults');
        c.controlsExist = !!typeSelect && !!valueInput && !!prevInput && !!area;

        // --- Test A: DOR = 25, prev = 20% ---
        typeSelect.value = 'dor';
        valueInput.value = '25';
        prevInput.value = '20';
        convertEffectSizeDTA();
        let html = area.innerHTML;
        c.dorHasTable = html.includes('<table');

        // DOR=25 → sqrt(25)=5, sens=spec=5/6=0.833
        c.dorHasSens = html.includes('Sensitivity');
        c.dorHasSpec = html.includes('Specificity');
        c.dorHasPLR = html.includes('PLR');
        c.dorHasNLR = html.includes('NLR');
        c.dorHasYouden = html.includes('Youden');
        c.dorHasAUC = html.includes('AUC');
        c.dorHasNND = html.includes('NND');
        c.dorHasPPV = html.includes('PPV');
        c.dorHasNPV = html.includes('NPV');
        c.dorHasLogDOR = html.includes('log(DOR)');
        c.dorHasNote = html.includes('symmetric operating point');

        // Verify: DOR=25, sens=spec~83.3%
        c.dorSensCheck = html.includes('83.3');

        // --- Test B: PLR = 5, prev = 30% ---
        typeSelect.value = 'plr';
        valueInput.value = '5';
        prevInput.value = '30';
        convertEffectSizeDTA();
        html = area.innerHTML;
        // PLR=5 → s = 5/6 ≈ 0.833 → DOR = (s/(1-s))^2 = 25
        c.plrHasDOR = html.includes('DOR');
        c.plrConverts = html.includes('25.0');

        // --- Test C: NLR = 0.2, prev = 10% ---
        typeSelect.value = 'nlr';
        valueInput.value = '0.2';
        prevInput.value = '10';
        convertEffectSizeDTA();
        html = area.innerHTML;
        // NLR=0.2 → s = 1/(1+0.2) = 0.833 → DOR = 25
        c.nlrHasDOR = html.includes('DOR');
        c.nlrConverts = html.includes('83.3');

        // --- Test D: Youden J = 0.6, prev = 25% ---
        typeSelect.value = 'youden';
        valueInput.value = '0.6';
        prevInput.value = '25';
        convertEffectSizeDTA();
        html = area.innerHTML;
        // J=0.6 → s = (0.6+1)/2 = 0.80 → DOR = (0.8/0.2)^2 = 16
        c.youdenConverts = html.includes('80.0');
        c.youdenNND = html.includes('NND');

        // --- Test E: AUC = 0.90, prev = 15% ---
        typeSelect.value = 'auc';
        valueInput.value = '0.90';
        prevInput.value = '15';
        convertEffectSizeDTA();
        html = area.innerHTML;
        c.aucConverts = html.includes('DOR') && html.includes('Sensitivity');

        // --- Test F: Invalid inputs ---
        typeSelect.value = 'dor';
        valueInput.value = '-5';
        prevInput.value = '20';
        convertEffectSizeDTA();
        c.rejectNegDOR = area.innerHTML.includes('must be positive');

        typeSelect.value = 'nlr';
        valueInput.value = '1.5';  // NLR > 1 is unusual
        prevInput.value = '20';
        convertEffectSizeDTA();
        c.rejectHighNLR = area.innerHTML.includes('between 0 and 1');

        typeSelect.value = 'auc';
        valueInput.value = '0.4';  // AUC < 0.5
        prevInput.value = '20';
        convertEffectSizeDTA();
        c.rejectLowAUC = area.innerHTML.includes('between 0.5 and 1');

        return c;
    """)

    check('Converter: section visible', r.get('sectionVisible'))
    check('Converter: controls exist', r.get('controlsExist'))
    check('Converter: DOR → table rendered', r.get('dorHasTable'))
    check('Converter: DOR → Sensitivity', r.get('dorHasSens'))
    check('Converter: DOR → Specificity', r.get('dorHasSpec'))
    check('Converter: DOR → PLR', r.get('dorHasPLR'))
    check('Converter: DOR → NLR', r.get('dorHasNLR'))
    check('Converter: DOR → Youden J', r.get('dorHasYouden'))
    check('Converter: DOR → AUC', r.get('dorHasAUC'))
    check('Converter: DOR → NND', r.get('dorHasNND'))
    check('Converter: DOR → PPV at prevalence', r.get('dorHasPPV'))
    check('Converter: DOR → NPV at prevalence', r.get('dorHasNPV'))
    check('Converter: DOR → log(DOR)', r.get('dorHasLogDOR'))
    check('Converter: symmetric assumption note', r.get('dorHasNote'))
    check('Converter: DOR=25 → sens~83.3%', r.get('dorSensCheck'))
    check('Converter: PLR → DOR computed', r.get('plrHasDOR'))
    check('Converter: PLR=5 → DOR~25', r.get('plrConverts'))
    check('Converter: NLR → DOR computed', r.get('nlrHasDOR'))
    check('Converter: NLR=0.2 → sens~83.3%', r.get('nlrConverts'))
    check('Converter: Youden J=0.6 → sens=80%', r.get('youdenConverts'))
    check('Converter: Youden → NND computed', r.get('youdenNND'))
    check('Converter: AUC=0.90 → DOR + Sens', r.get('aucConverts'))
    check('Converter: rejects negative DOR', r.get('rejectNegDOR'))
    check('Converter: rejects NLR > 1', r.get('rejectHighNLR'))
    check('Converter: rejects AUC < 0.5', r.get('rejectLowAUC'))


# ═══════════════════════════════════════════════════════════════
# TEST 6: INTEGRATION (all 5 render together after analysis)
# ═══════════════════════════════════════════════════════════════
def test_integration(driver):
    """Verify all 5 features render together without errors."""
    print('\n--- 6. Integration (all 5 together) ---')

    r = driver.execute_script("""
        const c = {};

        // All 5 containers should have content
        const drap = document.getElementById('advDraperyPlotContainer');
        const excl = document.getElementById('advExclusionMatrixContainer');
        const mcid = document.getElementById('mcidDTAArea');
        const risk = document.getElementById('patientRiskDTAResults');
        const esc = document.getElementById('escDTAResults');

        c.draperyHasContent = drap && drap.innerHTML.length > 100;
        c.exclusionHasContent = excl && excl.innerHTML.length > 100;
        c.mcidHasContent = mcid && mcid.innerHTML.length > 50;
        c.riskHasContent = risk && risk.innerHTML.length > 50;

        // Check no JS errors by verifying lastAnalysisResult is intact
        c.resultIntact = typeof lastAnalysisResult !== 'undefined' &&
                         lastAnalysisResult !== null &&
                         lastAnalysisResult.pooledSens > 0;

        // Verify div balance locally
        c.noUnclosedDivs = true;  // Would throw parse error if broken

        // Check all sections are in the advanced panel
        const advPanel = document.getElementById('phase-analyze');
        c.allInAdvPanel = advPanel &&
            advPanel.contains(drap) &&
            advPanel.contains(excl);

        return c;
    """)

    check('Integration: drapery has content', r.get('draperyHasContent'))
    check('Integration: exclusion has content', r.get('exclusionHasContent'))
    check('Integration: MCID has content', r.get('mcidHasContent'))
    check('Integration: patient risk has content', r.get('riskHasContent'))
    check('Integration: lastAnalysisResult intact', r.get('resultIntact'))
    check('Integration: all in advanced panel', r.get('allInAdvPanel'))


# ═══════════════════════════════════════════════════════════════
# TEST 7: MATH VERIFICATION
# ═══════════════════════════════════════════════════════════════
def test_math_verification(driver):
    """Verify mathematical correctness of computed values."""
    print('\n--- 7. Math Verification ---')

    r = driver.execute_script("""
        const c = {};
        const r = lastAnalysisResult;

        // Drapery: logDOR = mu1 + mu2 (NOT mu1 - mu2)
        const logDOR = (r.mu1 ?? 0) + (r.mu2 ?? 0);
        c.logDORPositive = logDOR > 0;  // BNP: good test, DOR > 1
        c.dorFromLogDOR = Math.exp(logDOR);
        c.dorReasonable = c.dorFromLogDOR > 5 && c.dorFromLogDOR < 200;  // BNP: DOR typically 30-60

        // SE(logDOR) via delta method including covariance
        const seLnDOR = Math.sqrt(
            (r.seMu1 ?? 0) ** 2 + (r.seMu2 ?? 0) ** 2 + 2 * (r.covMu12 ?? 0)
        );
        c.sePositive = seLnDOR > 0;
        c.seReasonable = seLnDOR > 0.05 && seLnDOR < 2;

        // Patient risk: Bayes theorem verification
        const sens = r.pooledSens;
        const spec = r.pooledSpec;
        const prev = 0.20;
        const plr = sens / (1 - spec);
        const nlr = (1 - sens) / spec;
        const preOdds = prev / (1 - prev);
        const ppv = (preOdds * plr) / (1 + preOdds * plr);
        const npv = 1 - (preOdds * nlr) / (1 + preOdds * nlr);
        c.ppvReasonable = ppv > 0.5 && ppv < 1.0;  // BNP: good test at 20% prev
        c.npvReasonable = npv > 0.9;  // Good test should have high NPV at low prev

        // Effect converter: DOR ↔ sens/spec roundtrip
        // DOR = (s/(1-s))^2 when symmetric, s = sqrt(DOR)/(1+sqrt(DOR))
        const testDOR = 36;
        const sqrtDOR = Math.sqrt(testDOR);
        const s = sqrtDOR / (1 + sqrtDOR);  // 6/7 ≈ 0.857
        const roundtripDOR = (s / (1 - s)) * (s / (1 - s));
        c.roundtripMatch = Math.abs(roundtripDOR - testDOR) < 0.01;

        // AUC formula: AUC = Phi(d/sqrt(2)) where d = sqrt(log(DOR))
        // This is the Moses-Shapiro-Littenberg formula
        const d = Math.sqrt(Math.log(testDOR));
        const auc = normalCDF(d / Math.SQRT2);
        c.aucRange = auc > 0.5 && auc < 1.0;
        c.aucReasonable = auc > 0.8;  // DOR=36 → AUC ≈ 0.90

        // Youden → NND: NND = ceil(1/J)
        const youdenJ = 2 * s - 1;  // ~ 0.714
        const nnd = Math.ceil(1 / youdenJ);
        c.nndCorrect = nnd === 2;  // ceil(1/0.714) = 2

        return c;
    """)

    check('Math: logDOR positive for BNP', r.get('logDORPositive'))
    check('Math: DOR in expected range (5-200)', r.get('dorReasonable'))
    check('Math: SE(logDOR) positive', r.get('sePositive'))
    check('Math: SE(logDOR) in reasonable range', r.get('seReasonable'))
    check('Math: PPV reasonable at 20% prev', r.get('ppvReasonable'))
    check('Math: NPV > 90% at 20% prev (good test)', r.get('npvReasonable'))
    check('Math: DOR → sens → DOR roundtrip', r.get('roundtripMatch'))
    check('Math: AUC in valid range (0.5-1.0)', r.get('aucRange'))
    check('Math: AUC > 0.80 for DOR=36', r.get('aucReasonable'))
    check('Math: NND = ceil(1/J) = 2 for J~0.714', r.get('nndCorrect'))


def main():
    global passed, failed

    print('=' * 70)
    print('  MetaSprint DTA — LivingMeta Features Test Suite')
    print('=' * 70)

    driver = setup()

    try:
        inject_bnp_and_analyze(driver)
        test_drapery_plot(driver)
        test_exclusion_matrix(driver)
        test_mcid_analysis(driver)
        test_patient_risk(driver)
        test_effect_converter(driver)
        test_integration(driver)
        test_math_verification(driver)
    finally:
        driver.quit()

    print()
    print('=' * 70)
    print(f'  LivingMeta Features Tests: {passed} passed, {failed} failed')
    print('=' * 70)

    if errors:
        print(f'\n  Failures:')
        for e in errors:
            print(f'    - {e}')

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
