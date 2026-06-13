"""
generate_figures.py — Generate 5 F1000 manuscript figures as PNG screenshots.

Figures:
1. Dashboard overview (landing page)
2. OA Discovery Pipeline (search results with screening badges)
3. Analysis results (SROC + forest + summary)
4. Advanced methods (influence diagnostics + Copas + P-curve)
5. Transparency (detail row with evidence chain + screening checklist)

Usage: python generate_figures.py
Requires: selenium, Chrome
"""

import sys
import io
import time
import os

if "pytest" not in sys.modules:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(SCRIPT_DIR, 'metasprint-dta.html')
FIG_DIR = os.path.join(SCRIPT_DIR, 'figures')

def setup():
    opts = Options()
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--window-size=1920,1200')
    opts.add_argument('--force-device-scale-factor=1.5')
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(10)
    driver.get('file:///' + HTML_PATH.replace('\\', '/'))
    time.sleep(3)
    # Dismiss onboarding
    driver.execute_script("""
        var ob = document.getElementById('onboardingOverlay');
        if (ob) ob.style.display = 'none';
        localStorage.setItem('msa-dta-onboarded', '1');
    """)
    time.sleep(0.5)
    return driver


def fig1_dashboard(driver):
    """Figure 1: Dashboard overview."""
    print('  Generating Figure 1: Dashboard overview...')
    driver.execute_script("""
        document.querySelectorAll('.phase').forEach(p => p.style.display = 'none');
        document.getElementById('phase-dashboard').style.display = 'block';
    """)
    time.sleep(1)
    driver.save_screenshot(os.path.join(FIG_DIR, 'figure01_dashboard.png'))
    print('    Saved: figure01_dashboard.png')


def fig2_discovery(driver):
    """Figure 2: OA Discovery with search results and screening badges."""
    print('  Generating Figure 2: OA Discovery Pipeline...')
    driver.execute_script("""
        document.querySelectorAll('.phase').forEach(p => p.style.display = 'none');
        document.getElementById('phase-discover').style.display = 'block';
        // Open OA panel
        var body = document.getElementById('oaBody');
        if (body && !body.classList.contains('open')) document.getElementById('oaToggle').click();
    """)
    time.sleep(0.5)

    # Run a search
    driver.execute_script("""
        document.getElementById('oaCondition').value = 'appendicitis';
        document.getElementById('oaIndexTest').value = 'ultrasound';
        document.getElementById('oaSearchBtn').click();
    """)
    time.sleep(20)

    # Scroll to results
    driver.execute_script("""
        var area = document.getElementById('oaResultsArea');
        if (area) area.scrollIntoView({behavior: 'instant'});
    """)
    time.sleep(1)
    driver.save_screenshot(os.path.join(FIG_DIR, 'figure02_oa_discovery.png'))
    print('    Saved: figure02_oa_discovery.png')


def fig3_analysis(driver):
    """Figure 3: Analysis results (SROC + forest + pooled)."""
    print('  Generating Figure 3: Analysis results...')

    # Import studies and run analysis
    driver.execute_script("""
        // Add benchmark BNP studies
        extractedStudies.length = 0;
        const raw = [
            {authorYear:'Dao 2001',tp:'52',fp:'14',fn:'8',tn:'76',indexTest:'BNP'},
            {authorYear:'Morrison 2002',tp:'44',fp:'20',fn:'6',tn:'151',indexTest:'BNP'},
            {authorYear:'Maisel 2002',tp:'379',fp:'83',fn:'65',tn:'959',indexTest:'BNP'},
            {authorYear:'Mueller 2004',tp:'89',fp:'17',fn:'14',tn:'337',indexTest:'BNP'},
            {authorYear:'Lainchbury 2003',tp:'40',fp:'22',fn:'5',tn:'138',indexTest:'BNP'},
            {authorYear:'McCullough 2002',tp:'163',fp:'44',fn:'21',tn:'416',indexTest:'BNP'}
        ];
        let id = 1;
        for (const s of raw) extractedStudies.push({...s, id: 'fig_' + id++});

        // Show analyze tab
        document.querySelectorAll('.phase').forEach(p => p.style.display = 'none');
        document.getElementById('phase-analyze').style.display = 'block';

        // Run analysis directly
        const studies = extractedStudies.map(s => ({tp:parseInt(s.tp),fp:parseInt(s.fp),fn:parseInt(s.fn),tn:parseInt(s.tn),authorYear:s.authorYear}));
        const prepared = prepareDTAStudyData(studies, '0.5');
        const result = computeDTAAnalysis(prepared, 0.95, 'bivariate', '0.5');
        lastAnalysisResult = result;
        renderDTAResults(result, 0.95, 95, 'bivariate', 'bivariate');
    """)
    time.sleep(4)

    # Scroll to top of results
    driver.execute_script("""
        var summary = document.getElementById('analysisSummary');
        if (summary) summary.scrollIntoView({behavior: 'instant'});
    """)
    time.sleep(1)
    driver.save_screenshot(os.path.join(FIG_DIR, 'figure03_analysis_results.png'))
    print('    Saved: figure03_analysis_results.png')


def fig4_advanced(driver):
    """Figure 4: Advanced methods (influence + Copas + P-curve + GRADE)."""
    print('  Generating Figure 4: Advanced methods...')

    # Toggle advanced section open
    driver.execute_script("""
        if (typeof toggleAdvancedDTA === 'function') toggleAdvancedDTA();
        // Scroll to influence diagnostics
        var infl = document.getElementById('advInfluenceContainer');
        if (infl) infl.scrollIntoView({behavior: 'instant'});
    """)
    time.sleep(2)
    driver.save_screenshot(os.path.join(FIG_DIR, 'figure04_advanced_methods.png'))
    print('    Saved: figure04_advanced_methods.png')


def fig5_transparency(driver):
    """Figure 5: Transparency (detail row with evidence chain + checklist)."""
    print('  Generating Figure 5: Transparency features...')

    # Go back to Discover tab and open a detail row
    driver.execute_script("""
        document.querySelectorAll('.phase').forEach(p => p.style.display = 'none');
        document.getElementById('phase-discover').style.display = 'block';
        var body = document.getElementById('oaBody');
        if (body && !body.classList.contains('open')) document.getElementById('oaToggle').click();

        // Click first study row to open detail
        var firstRow = document.querySelector('#oaResultsBody tr.oa-row-clickable');
        if (firstRow) firstRow.click();
    """)
    time.sleep(2)

    # Scroll to detail row
    driver.execute_script("""
        var detail = document.querySelector('.oa-detail-row');
        if (detail) detail.scrollIntoView({behavior: 'instant', block: 'start'});
    """)
    time.sleep(1)
    driver.save_screenshot(os.path.join(FIG_DIR, 'figure05_transparency.png'))
    print('    Saved: figure05_transparency.png')


def main():
    print('=' * 60)
    print('  MetaSprint DTA — Figure Generation')
    print('=' * 60)

    driver = setup()

    try:
        fig1_dashboard(driver)
        fig2_discovery(driver)
        fig3_analysis(driver)
        fig4_advanced(driver)
        fig5_transparency(driver)
    finally:
        driver.quit()

    print()
    print('  All 5 figures saved to figures/')
    files = os.listdir(FIG_DIR)
    for f in sorted(files):
        size = os.path.getsize(os.path.join(FIG_DIR, f))
        print(f'    {f} ({size//1024} KB)')
    print('=' * 60)


if __name__ == '__main__':
    main()
