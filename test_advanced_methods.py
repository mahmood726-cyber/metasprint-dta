"""
test_advanced_methods.py — Permanent Selenium test suite for Tier 1+2 advanced methods.

Tests all 10 ported features + V2 preprocessing + UI integration.
Runs headless Chrome against metasprint-dta.html.

Usage: python test_advanced_methods.py
"""

import sys
import io
import time
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metasprint-dta.html')

# BNP benchmark dataset (6 studies)
BNP_JS = """[
    {tp:52,fp:14,fn:8,tn:76},{tp:44,fp:20,fn:6,tn:151},
    {tp:379,fp:83,fn:65,tn:959},{tp:89,fp:17,fn:14,tn:337},
    {tp:40,fp:22,fn:5,tn:138},{tp:163,fp:44,fn:21,tn:416}
]"""

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


def prepare_studies(driver):
    """Inject BNP benchmark and prepare study data."""
    return driver.execute_script(f"""
        const raw = {BNP_JS};
        return prepareDTAStudyData(raw, "0.5");
    """)


def test_preprocessing(driver):
    """Test V2 text preprocessing patterns."""
    print('\n--- V2 Text Preprocessing ---')

    r = driver.execute_script("""
        const t = {};
        // European decimal comma
        const t1 = extractDTAFromAbstract("Sensitivity was 89,5% (95% CI: 82,1-96,3%) and specificity 92,0%.");
        t.euroSens = t1 && Math.abs(t1.sensitivity - 0.895) < 0.01;

        // OCR Cl → CI
        const t2 = extractDTAFromAbstract("Sensitivity was 87% (95% Cl: 80-93%) and specificity 91%.");
        t.ocrCI = t2 && t2.sensLCI != null && Math.abs(t2.sensLCI - 0.80) < 0.01;

        // OCR Cl safe for chloride
        const s1 = preprocessDTAText("(Cl concentration was 102 mmol/L)");
        t.clSafe = s1.includes("Cl concentration");

        // Greek question mark
        const t3 = extractDTAFromAbstract("Sensitivity 87%\\u037e specificity 92%.");
        t.greekQM = t3 && Math.abs(t3.sensitivity - 0.87) < 0.01;

        // CI comma pair NOT corrupted
        const s2 = preprocessDTAText("HR 0.85 (95% CI 0.72, 0.96)");
        t.ciPairSafe = s2.includes("0.72, 0.96");

        // Decimal-only format
        const t4 = extractDTAFromAbstract("Sensitivity was 0.89 (0.82-0.94) and specificity 0.92.");
        t.decimal = t4 && Math.abs(t4.sensitivity - 0.89) < 0.01;

        // "to" CI delimiter
        const t5 = extractDTAFromAbstract("Sensitivity was 85% (95% CI 78 to 92%). Specificity 90%.");
        t.ciTo = t5 && t5.sensLCI != null && Math.abs(t5.sensLCI - 0.78) < 0.01;

        return t;
    """)

    check('Euro decimal comma', r.get('euroSens'))
    check('OCR Cl->CI with digit context', r.get('ocrCI'))
    check('Chloride Cl preserved', r.get('clSafe'))
    check('Greek question mark normalized', r.get('greekQM'))
    check('CI comma pair not corrupted', r.get('ciPairSafe'))
    check('Decimal-only format (0.89)', r.get('decimal'))
    check('"to" CI delimiter', r.get('ciTo'))


def test_enhanced_extraction(driver):
    """Test AUC/PPV/NPV CI extraction and validation."""
    print('\n--- Enhanced Extraction Patterns ---')

    r = driver.execute_script("""
        const t = {};
        // AUC with CI
        const t1 = extractDTAFromAbstract("AUROC 0.89 (95% CI 0.82-0.94). Sensitivity 85%, specificity 90%.");
        t.aucVal = t1 && Math.abs(t1.auc - 0.89) < 0.01;
        t.aucCI = t1 && t1.aucLCI != null && Math.abs(t1.aucLCI - 0.82) < 0.01;

        // C-statistic
        const t2 = extractDTAFromAbstract("C-statistic 0.91 (0.85-0.96). Sensitivity 88%, specificity 87%.");
        t.cstat = t2 && Math.abs(t2.auc - 0.91) < 0.01;

        // PPV with CI
        const t3 = extractDTAFromAbstract("PPV 85% (95% CI 78-91%), NPV 94% (95% CI 90-97%). Sensitivity 90%, specificity 88%.");
        t.ppvCI = t3 && t3.ppvLCI != null && Math.abs(t3.ppvLCI - 0.78) < 0.01;
        t.npvCI = t3 && t3.npvLCI != null && Math.abs(t3.npvLCI - 0.90) < 0.01;

        // CI containment warning
        const t4 = extractDTAFromAbstract("Sensitivity was 50% (95% CI 80-96%). Specificity 90%.");
        t.ciWarn = t4 && t4._warnings && t4._warnings.some(w => w.includes("outside CI"));

        // LR plausibility
        const t5 = extractDTAFromAbstract("Sensitivity 80%, specificity 90%. LR+ = 0.5.");
        t.lrWarn = t5 && t5._warnings && t5._warnings.some(w => w.includes("LR+ < 1"));

        // CI bounds ordering
        const t6 = extractDTAFromAbstract("Sensitivity 85% (95% CI 92-78%). Specificity 90%.");
        t.ciOrder = t6 && t6.sensLCI <= t6.sensUCI;

        return t;
    """)

    check('AUC value extraction', r.get('aucVal'))
    check('AUC CI extraction', r.get('aucCI'))
    check('C-statistic as AUC', r.get('cstat'))
    check('PPV CI extraction', r.get('ppvCI'))
    check('NPV CI extraction', r.get('npvCI'))
    check('CI containment warning', r.get('ciWarn'))
    check('LR plausibility warning', r.get('lrWarn'))
    check('CI bounds auto-ordered', r.get('ciOrder'))


def test_influence_diagnostics(driver):
    """Test Cook's D and DFBETAS."""
    print('\n--- Influence Diagnostics ---')

    r = driver.execute_script(f"""
        const prepared = prepareDTAStudyData({BNP_JS}, "0.5");
        const infl = computeInfluenceDiagnostics(prepared, 0.95);
        if (!infl || infl.error) return {{error: infl?.error || 'null'}};
        return {{
            k: infl.k, threshold: infl.threshold,
            nInfluential: infl.nInfluential,
            maxCooksD: infl.maxCooksD,
            diagLen: infl.diagnostics.length,
            firstDFBS: infl.diagnostics[0]?.dfbetaSens,
            firstDFBP: infl.diagnostics[0]?.dfbetaSpec,
            firstCooksD: infl.diagnostics[0]?.cooksD,
            hasSensChange: infl.diagnostics[0]?.sensChange != null
        }};
    """)

    check('Returns result', r and 'error' not in r)
    check('k = 6', r.get('k') == 6)
    check('Threshold = 2/sqrt(6)', r.get('threshold') is not None and abs(r['threshold'] - 2 / 6**0.5) < 0.001)
    check('6 diagnostic entries', r.get('diagLen') == 6)
    check('DFBETA sens computed', r.get('firstDFBS') is not None)
    check('DFBETA spec computed', r.get('firstDFBP') is not None)
    check("Cook's D uses p=2 (reasonable range)", r.get('firstCooksD') is not None and 0 < r['firstCooksD'] < 10)
    check('Sens change tracked', r.get('hasSensChange'))


def test_copas_model(driver):
    """Test Copas selection model."""
    print('\n--- Copas Selection Model ---')

    r = driver.execute_script(f"""
        const prepared = prepareDTAStudyData({BNP_JS}, "0.5");
        const biv = improvedBivariatePool(prepared, 0.95);
        const copas = copasSelectionModel(prepared, biv);
        if (!copas || copas.error) return {{error: copas?.error || 'null'}};
        return {{
            converged: copas.converged, iterations: copas.iterations,
            adjSens: copas.adjusted.sens, adjSpec: copas.adjusted.spec,
            unadjSens: copas.unadjusted.sens, unadjSpec: copas.unadjusted.spec,
            sensChange: copas.adjusted.sensChange,
            downWeighted: copas.selection.downWeighted,
            expectedUnpub: copas.selection.expectedUnpublished
        }};
    """)

    check('Converged', r.get('converged') == True)
    check('Adjusted sens valid', 0 < (r.get('adjSens') or 0) < 1)
    check('Adjusted spec valid', 0 < (r.get('adjSpec') or 0) < 1)
    check('Sens change small (<15%)', abs(r.get('sensChange') or 99) < 0.15)
    check('Down-weighted count >= 0', r.get('downWeighted') is not None and r['downWeighted'] >= 0)


def test_nnd_with_ci(driver):
    """Test NND with delta method CIs."""
    print('\n--- NND with CIs ---')

    r = driver.execute_script(f"""
        const prepared = prepareDTAStudyData({BNP_JS}, "0.5");
        const biv = improvedBivariatePool(prepared, 0.95);
        const nnd = computeNNDWithCI(biv.pooledSens, biv.pooledSpec, biv.sensCI, biv.specCI, 0.95);
        return nnd;
    """)

    check('NND computed', r.get('nnd') is not None)
    check('Youden > 0', (r.get('youden') or 0) > 0)
    check('CI exists', r.get('nndCI') is not None)
    check('CI lower >= 1', r.get('nndCI') and r['nndCI'][0] >= 1)
    check('CI upper > lower', r.get('nndCI') and r['nndCI'][1] > r['nndCI'][0])


def test_text_generators(driver):
    """Test results and methods text generation."""
    print('\n--- Text Generators ---')

    r = driver.execute_script(f"""
        const prepared = prepareDTAStudyData({BNP_JS}, "0.5");
        const biv = improvedBivariatePool(prepared, 0.95);
        const t = {{}};

        // Results text with 95% CI
        const rt95 = generateResultsText(biv, 6, 3025, 0.95);
        t.rtHasSens = rt95.includes("sensitivity");
        t.rtHasSpec = rt95.includes("specificity");
        t.rtHas95 = rt95.includes("95% CI");
        t.rtLen = rt95.length;

        // Results text with 90% CI
        const rt90 = generateResultsText(biv, 6, 3025, 0.90);
        t.rtHas90 = rt90.includes("90% CI");
        t.rtNo95 = !rt90.includes("95% CI");

        // Null CI safe
        const rtNull = generateResultsText({{pooledSens: 0.9, pooledSpec: 0.85}}, 5, 1000);
        t.nullSafe = rtNull.length > 50;

        // Methods text
        const mt = generateMethodsText(6, "bivariate", "0.5");
        t.mtHasReitsma = mt.includes("Reitsma");
        t.mtMomentBased = mt.includes("moment-based");
        t.mtNoDL = !mt.includes("DerSimonian-Laird");
        t.mtHasDeeks = mt.includes("Deeks");

        return t;
    """)

    check('Results: has sensitivity', r.get('rtHasSens'))
    check('Results: has specificity', r.get('rtHasSpec'))
    check('Results: has 95% CI', r.get('rtHas95'))
    check('Results: length > 200', (r.get('rtLen') or 0) > 200)
    check('Results: 90% CI when confLevel=0.90', r.get('rtHas90'))
    check('Results: no 95% when confLevel=0.90', r.get('rtNo95'))
    check('Results: null CI safe', r.get('nullSafe'))
    check('Methods: cites Reitsma', r.get('mtHasReitsma'))
    check('Methods: says moment-based', r.get('mtMomentBased'))
    check('Methods: no DerSimonian-Laird', r.get('mtNoDL'))
    check('Methods: cites Deeks', r.get('mtHasDeeks'))


def test_pcurve(driver):
    """Test P-curve analysis."""
    print('\n--- P-Curve Analysis ---')

    r = driver.execute_script(f"""
        const prepared = prepareDTAStudyData({BNP_JS}, "0.5");
        const pc = pCurveAnalysis(prepared);
        if (!pc || pc.error) return {{error: pc?.error || 'null'}};
        return {{
            nSig: pc.nSignificant, nTotal: pc.nTotal,
            nBelow: pc.nBelow025, binomP: pc.binomialP,
            ksD: pc.ksStatistic,
            hasInterp: pc.interpretation != null && pc.interpretation.length > 10,
            hasCaveat: pc.caveat != null && pc.caveat.includes("exploratory")
        }};
    """)

    check('Returns result', r and 'error' not in r)
    check('nSignificant > 0', (r.get('nSig') or 0) > 0)
    check('Binomial p valid', r.get('binomP') is not None and 0 <= r['binomP'] <= 1)
    check('KS statistic > 0', (r.get('ksD') or 0) > 0)
    check('Has interpretation', r.get('hasInterp'))
    check('Has DTA caveat', r.get('hasCaveat'))


def test_profile_likelihood(driver):
    """Test bivariate profile likelihood CIs."""
    print('\n--- Profile Likelihood CIs ---')

    r = driver.execute_script(f"""
        const prepared = prepareDTAStudyData({BNP_JS}, "0.5");
        const pl = bivariateProfileLikelihoodCI(prepared, 0.95);
        if (!pl) return {{error: 'null'}};
        return {{
            method: pl.method,
            sensProb: pl.sensitivity?.prob,
            sensCILo: pl.sensitivity?.probCI?.[0],
            sensCIHi: pl.sensitivity?.probCI?.[1],
            specProb: pl.specificity?.prob,
            specCILo: pl.specificity?.probCI?.[0],
            specCIHi: pl.specificity?.probCI?.[1]
        }};
    """)

    check('Returns result', r and 'error' not in r)
    check('Method = profile_likelihood_conditional', r.get('method') == 'profile_likelihood_conditional')
    check('Sens prob valid', 0 < (r.get('sensProb') or 0) < 1)
    check('Sens CI lo < hi', (r.get('sensCILo') or 1) < (r.get('sensCIHi') or 0))
    check('Spec prob valid', 0 < (r.get('specProb') or 0) < 1)
    check('Spec CI lo < hi', (r.get('specCILo') or 1) < (r.get('specCIHi') or 0))


def test_whatif(driver):
    """Test what-if simulator."""
    print('\n--- What-If Simulator ---')

    r = driver.execute_script("""
        const wi = whatIfSimulator({sensitivity: 0.87, specificity: 0.90, prevalence: 0.15, population: 10000});
        return {
            tp: wi.counts.tp, fp: wi.counts.fp, fn: wi.counts.fn, tn: wi.counts.tn,
            ppv: wi.rates.ppv, npv: wi.rates.npv, plr: wi.rates.plr, nlr: wi.rates.nlr,
            postPos: wi.fagan.postTestPosProb, postNeg: wi.fagan.postTestNegProb,
            nb: wi.impact.netBenefit,
            noNaN: isFinite(wi.rates.plr) && isFinite(wi.fagan.postTestPosProb)
        };
    """)

    check('TP reasonable', 1000 < (r.get('tp') or 0) < 2000)
    check('PPV valid', 0 < (r.get('ppv') or 0) < 1)
    check('PLR > 1', (r.get('plr') or 0) > 1)
    check('NLR < 1', 0 < (r.get('nlr') or 1) < 1)
    check('Post-test pos > prevalence', (r.get('postPos') or 0) > 0.15)
    check('Post-test neg < prevalence', (r.get('postNeg') or 1) < 0.15)
    check('No NaN values', r.get('noNaN'))

    # Edge case: spec near 1.0
    r2 = driver.execute_script("""
        const wi = whatIfSimulator({sensitivity: 0.95, specificity: 0.999, prevalence: 0.1});
        return { noNaN: isFinite(wi.rates.plr) && isFinite(wi.fagan.postTestPosProb) };
    """)
    check('No NaN at spec=0.999', r2.get('noNaN'))


def test_bootstrap(driver):
    """Test bootstrap BCa CIs."""
    print('\n--- Bootstrap BCa ---')

    r = driver.execute_script(f"""
        const prepared = prepareDTAStudyData({BNP_JS}, "0.5");
        const bs = bootstrapBCa(prepared, 0.95, 200);
        if (!bs || bs.error) return {{error: bs?.error || 'null'}};
        return {{
            nBoot: bs.nBoot, nSuccess: bs.nSuccessful,
            sensBias: bs.sens.bias,
            sensBCaLo: bs.sens.bcaCI[0], sensBCaHi: bs.sens.bcaCI[1],
            specBCaLo: bs.spec.bcaCI[0], specBCaHi: bs.spec.bcaCI[1],
            percLo: bs.sens.percentileCI[0], percHi: bs.sens.percentileCI[1]
        }};
    """)

    check('Returns result', r and 'error' not in r)
    check('nSuccessful > 150', (r.get('nSuccess') or 0) > 150)
    check('Bias small (<5%)', abs(r.get('sensBias') or 99) < 0.05)
    check('BCa sens CI ordered', (r.get('sensBCaLo') or 1) < (r.get('sensBCaHi') or 0))
    check('BCa spec CI ordered', (r.get('specBCaLo') or 1) < (r.get('specBCaHi') or 0))
    check('BCa CI finite (no NaN)', r.get('sensBCaLo') is not None and r.get('sensBCaHi') is not None)
    check('Percentile CI exists', r.get('percLo') is not None)


def test_lasso(driver):
    """Test LASSO meta-regression."""
    print('\n--- LASSO Meta-Regression ---')

    r = driver.execute_script(f"""
        const prepared = prepareDTAStudyData({BNP_JS}, "0.5");
        const raw = {BNP_JS};
        const withMod = prepared.map((s, i) => ({{...s, sampleSize: raw[i].tp + raw[i].fp + raw[i].fn + raw[i].tn}}));
        const la = lassoMetaRegression(withMod, [{{field: "sampleSize", label: "Sample Size"}}], {{lambda: 0.1}});
        if (!la || la.error) return {{error: la?.error || 'null'}};
        return {{
            nStudies: la.nStudies, nCov: la.nCovariates,
            intercept: la.intercept,
            nSelected: la.nSelected,
            coeffLen: la.coefficients.length,
            firstBeta: la.coefficients[0]?.beta,
            firstName: la.coefficients[0]?.name
        }};
    """)

    check('Returns result', r and 'error' not in r)
    check('nStudies = 6', r.get('nStudies') == 6)
    check('Intercept computed', r.get('intercept') is not None)
    check('Coefficients exist', (r.get('coeffLen') or 0) > 0)
    check('First coef name = Sample Size', r.get('firstName') == 'Sample Size')


def test_ui_integration(driver):
    """Test UI panel rendering after analysis."""
    print('\n--- UI Integration ---')

    driver.execute_script(f"""
        extractedStudies.length = 0;
        const raw = [
            {{authorYear:"Dao 2001",tp:"52",fp:"14",fn:"8",tn:"76",indexTest:"BNP"}},
            {{authorYear:"Morrison 2002",tp:"44",fp:"20",fn:"6",tn:"151",indexTest:"BNP"}},
            {{authorYear:"Maisel 2002",tp:"379",fp:"83",fn:"65",tn:"959",indexTest:"BNP"}},
            {{authorYear:"Mueller 2004",tp:"89",fp:"17",fn:"14",tn:"337",indexTest:"BNP"}},
            {{authorYear:"Lainchbury 2003",tp:"40",fp:"22",fn:"5",tn:"138",indexTest:"BNP"}},
            {{authorYear:"McCullough 2002",tp:"163",fp:"44",fn:"21",tn:"416",indexTest:"BNP"}}
        ];
        let id = 1;
        for (const s of raw) extractedStudies.push({{...s, id: "b" + id++}});
        document.querySelectorAll(".phase").forEach(p => p.style.display = "none");
        document.getElementById("phase-analyze").style.display = "block";
        const studies = extractedStudies.map(s => ({{tp:parseInt(s.tp),fp:parseInt(s.fp),fn:parseInt(s.fn),tn:parseInt(s.tn),authorYear:s.authorYear}}));
        const prepared = prepareDTAStudyData(studies, "0.5");
        const result = computeDTAAnalysis(prepared, 0.95, "bivariate", "0.5");
        lastAnalysisResult = result;
        renderDTAResults(result, 0.95, 95, "bivariate", "bivariate");
        toggleAdvancedDTA();
    """)
    time.sleep(3)

    r = driver.execute_script("""
        const c = {};
        const infl = document.getElementById("advInfluenceContainer");
        c.inflDFBETA = infl && infl.innerHTML.includes("DFBETA");
        c.inflStudy = infl && infl.innerHTML.includes("Dao");
        c.inflScope = infl && infl.innerHTML.includes('scope="col"');

        const pub = document.getElementById("advPubBiasContainer");
        c.copas = pub && pub.innerHTML.includes("Copas");
        c.copasScope = pub && pub.innerHTML.includes('scope="row"');
        c.pcurve = pub && pub.innerHTML.includes("P-Curve");
        c.pcurveLabel = pub && (pub.innerHTML.includes("(significant)") || pub.innerHTML.includes("(flat)") || pub.innerHTML.includes("Inconclusive"));

        const nnd = document.getElementById("nndContainer");
        c.nndCI = nnd && nnd.innerHTML.includes("CI");

        c.autoMRBtn = !!document.querySelector("button[onclick*=renderAutoMethodsResults]");

        // Test auto methods+results rendering
        document.querySelectorAll(".phase").forEach(p => p.style.display = "none");
        document.getElementById("phase-write").style.display = "block";
        renderAutoMethodsResults();
        const autoOut = document.getElementById("autoMethodsResultsOutput");
        c.autoMethods = autoOut && autoOut.innerHTML.includes("Reitsma");
        c.autoResults = autoOut && autoOut.innerHTML.includes("sensitivity");
        c.autoCopy = autoOut && autoOut.innerHTML.includes("Copy");

        return c;
    """)

    check('Influence: DFBETA table', r.get('inflDFBETA'))
    check('Influence: study names', r.get('inflStudy'))
    check('Influence: th scope=col', r.get('inflScope'))
    check('Copas rendered', r.get('copas'))
    check('Copas: th scope=row', r.get('copasScope'))
    check('P-curve rendered', r.get('pcurve'))
    check('P-curve: text label (not color-only)', r.get('pcurveLabel'))
    check('NND with CI', r.get('nndCI'))
    check('Auto M+R button exists', r.get('autoMRBtn'))
    check('Auto Methods: Reitsma', r.get('autoMethods'))
    check('Auto Results: sensitivity', r.get('autoResults'))
    check('Auto: Copy buttons', r.get('autoCopy'))


def test_transparency(driver):
    """Test screening checklist, evidence chain, and demographics."""
    print('\n--- Transparency Features ---')

    r = driver.execute_script("""
        const t = {};
        // Demographics from abstract
        const r1 = extractDTAFromAbstract("We enrolled 250 patients (mean age 65.3 +/- 12.1 years, 58% female). Sensitivity was 89%, specificity 92%.");
        t.demoAge = r1._demographics && Math.abs(r1._demographics.ageMean - 65.3) < 0.1;
        t.demoAgeSD = r1._demographics && Math.abs(r1._demographics.ageSD - 12.1) < 0.1;
        t.demoPctFemale = r1._demographics && r1._demographics.pctFemale === '58.0';
        t.demoPopPediatric = extractDTAFromAbstract("A pediatric cohort of 100 children. Sensitivity 85%, specificity 90%.")._demographics?.population === 'pediatric';

        // Source tracking
        const r2 = extractDTAFromAbstract("Sensitivity was 89% (95% CI: 80-96%) and specificity was 92%.");
        t.hasSources = r2._sources != null;
        t.sensSrcText = r2._sources?.sensitivity?.sourceText?.includes('89%');
        t.sensSrcMethod = r2._sources?.sensitivity?.method === 'direct';
        t.specSrcMethod = r2._sources?.specificity?.method === 'direct';

        // Derived source tracking
        const r3 = extractDTAFromAbstract("LR+ was 8.5 and LR- was 0.12.");
        t.derivedSens = r3._sources?.sensitivity?.method === 'derived_from_lr';
        t.derivedFormula = r3._sources?.sensitivity?.formula?.includes('LR+');

        // Screening checklist
        t.checklistFn = typeof buildScreeningChecklist === 'function';
        const mockStudy = {_indexTestMatch: 'match', _isReview: false, backCalc: {tp:50,fp:10,fn:5,tn:100,method:'algebraic',confidence:'high'}, ctgovMetrics: {sensitivity:0.9,specificity:0.9}};
        const cl = buildScreeningChecklist(mockStudy);
        t.clPassAll = cl && [cl.indexTestMatch,cl.notReview,cl.dataExtracted,cl.qualityGate,cl.noConflict].every(c => c.pass);
        t.clHasReasons = cl && cl.dataExtracted.reason.includes('Sens');

        // Review excluded
        const mockReview = {_indexTestMatch: 'match', _isReview: true};
        const cl2 = buildScreeningChecklist(mockReview);
        t.clReviewFails = cl2 && !cl2.notReview.pass;
        t.clReviewReason = cl2 && cl2.notReview.reason.includes('review');

        // RoB transparency
        const robR = _inferProvisionalOverallRoB({tp:'52',fp:'14',fn:'8',tn:'76',indexTest:'BNP'});
        t.robReturnsReasons = robR.reasons && robR.reasons.length >= 4;
        t.robOverall = robR.overall === 'some' || robR.overall === 'high';

        // GRADE transparency
        const prepared = prepareDTAStudyData([{tp:52,fp:14,fn:8,tn:76},{tp:44,fp:20,fn:6,tn:151},{tp:379,fp:83,fn:65,tn:959},{tp:89,fp:17,fn:14,tn:337}], '0.5');
        const biv = improvedBivariatePool(prepared, 0.95);
        const grade = computeGRADE(biv, prepared);
        t.gradeHasReasons = grade?.reasons != null;
        t.gradeRobReason = grade?.reasons?.riskOfBias?.length > 5;
        t.gradeInconReason = grade?.reasons?.inconsistency?.length > 5;
        t.gradeLabel = grade?.label != null;

        return t;
    """)

    check('Demographics: age mean', r.get('demoAge'))
    check('Demographics: age SD', r.get('demoAgeSD'))
    check('Demographics: % female', r.get('demoPctFemale'))
    check('Demographics: pediatric detection', r.get('demoPopPediatric'))
    check('Sources: _sources populated', r.get('hasSources'))
    check('Sources: sens source text', r.get('sensSrcText'))
    check('Sources: sens method=direct', r.get('sensSrcMethod'))
    check('Sources: spec method=direct', r.get('specSrcMethod'))
    check('Sources: derived from LR', r.get('derivedSens'))
    check('Sources: derived formula', r.get('derivedFormula'))
    check('Checklist: function exists', r.get('checklistFn'))
    check('Checklist: all pass for good study', r.get('clPassAll'))
    check('Checklist: has reasons', r.get('clHasReasons'))
    check('Checklist: review fails notReview', r.get('clReviewFails'))
    check('Checklist: review reason text', r.get('clReviewReason'))
    check('RoB: returns reasons array', r.get('robReturnsReasons'))
    check('RoB: overall is some or high', r.get('robOverall'))
    check('GRADE: has reasons object', r.get('gradeHasReasons'))
    check('GRADE: RoB reason text', r.get('gradeRobReason'))
    check('GRADE: inconsistency reason', r.get('gradeInconReason'))
    check('GRADE: has label', r.get('gradeLabel'))


def main():
    global passed, failed

    print('=' * 70)
    print('  MetaSprint DTA — Advanced Methods Test Suite')
    print('=' * 70)

    driver = setup()

    try:
        test_preprocessing(driver)
        test_enhanced_extraction(driver)
        test_influence_diagnostics(driver)
        test_copas_model(driver)
        test_nnd_with_ci(driver)
        test_text_generators(driver)
        test_pcurve(driver)
        test_profile_likelihood(driver)
        test_whatif(driver)
        test_bootstrap(driver)
        test_lasso(driver)
        test_ui_integration(driver)
        test_transparency(driver)
    finally:
        driver.quit()

    print()
    print('=' * 70)
    print(f'  Advanced Methods Tests: {passed} passed, {failed} failed')
    print('=' * 70)

    if errors:
        print(f'\n  Failures:')
        for e in errors:
            print(f'    - {e}')

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
