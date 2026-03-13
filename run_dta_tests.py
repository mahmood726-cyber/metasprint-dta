"""
run_dta_tests.py — Master test runner for MetaSprint DTA test suite.

Runs all test suites in order with retry logic for transient Selenium failures.
Prints per-suite pass/fail/duration summary table.
Exit code 0 if all pass, 1 otherwise.
"""
import sys, io, os, time, subprocess, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PYTHON = sys.executable

SUITES = [
    {
        'name': 'Identity (DTA branding)',
        'script': 'test_dta_identity.py',
        'requires_browser': True,
        'slow': False,
    },
    {
        'name': '2x2 Input Validation',
        'script': 'test_dta_2x2_input.py',
        'requires_browser': True,
        'slow': False,
    },
    {
        'name': 'Method Comparison (Biv vs HSROC)',
        'script': 'test_dta_methods.py',
        'requires_browser': True,
        'slow': False,
    },
    {
        'name': 'End-to-End Validation (3 datasets)',
        'script': 'test_dta_validation.py',
        'requires_browser': True,
        'slow': True,
    },
    {
        'name': 'Advanced Features (Viz + Sensitivity + Regression)',
        'script': 'test_dta_advanced.py',
        'requires_browser': True,
        'slow': False,
    },
    {
        'name': 'Insights DTA Adaptation (8 tabs)',
        'script': 'test_dta_insights.py',
        'requires_browser': True,
        'slow': False,
    },
    {
        'name': 'New Features (B1-B4, S3-S8, Q1-Q17)',
        'script': 'test_dta_new_features.py',
        'requires_browser': True,
        'slow': False,
    },
    {
        'name': 'Improvements v2 (P0-P2 fixes + features)',
        'script': 'test_dta_improvements_v2.py',
        'requires_browser': True,
        'slow': False,
    },
    {
        'name': 'Extended Insights (8 tabs)',
        'script': 'test_dta_insights_extended.py',
        'requires_browser': True,
        'slow': False,
    },
    {
        'name': 'Export Functions (CSV/JSON/HTML)',
        'script': 'test_dta_exports.py',
        'requires_browser': True,
        'slow': False,
    },
]

TRANSIENT_RETRIES = 1
TIMEOUT_SECONDS = 300

def parse_summary(output):
    """Extract pass/fail counts from standalone Selenium script output."""
    passed = 0
    failed = 0
    # Try structured summary line: "N tests: P passed, F failed"
    m = re.search(r'(\d+)\s+tests?:\s*(\d+)\s+passed,?\s*(\d+)\s+failed', output)
    if m:
        passed = int(m.group(2))
        failed = int(m.group(3))
    else:
        # Fallback: count PASS/FAIL lines
        passed = len(re.findall(r'^\s*PASS:', output, re.MULTILINE))
        failed = len(re.findall(r'^\s*FAIL:', output, re.MULTILINE))
    return passed, failed

def find_chromedriver():
    """Find cached chromedriver path."""
    import glob
    home = os.path.expanduser('~')
    paths = sorted(glob.glob(os.path.join(home, '.cache', 'selenium', 'chromedriver', 'win64', '*', 'chromedriver.exe')))
    return paths[-1] if paths else None

def check_browser():
    """Check if Chrome/chromedriver is available."""
    cd_path = find_chromedriver()
    if cd_path:
        os.environ['SE_CHROMEDRIVER'] = cd_path
    try:
        check_code = (
            'import os; from selenium import webdriver; '
            'from selenium.webdriver.chrome.options import Options; '
            'from selenium.webdriver.chrome.service import Service; '
            'o=Options(); o.add_argument("--headless=new"); '
            'cd=os.environ.get("SE_CHROMEDRIVER",""); '
            'svc=Service(executable_path=cd) if cd else Service(); '
            'd=webdriver.Chrome(options=o, service=svc); d.quit(); print("OK")'
        )
        result = subprocess.run(
            [PYTHON, '-c', check_code],
            capture_output=True, text=True, timeout=60,
            env={**os.environ}
        )
        return 'OK' in result.stdout
    except Exception as e:
        print(f'  Browser check failed: {e}')
        return False

def run_suite(suite):
    """Run a single test suite with optional retry."""
    script = suite['script']
    retries = TRANSIENT_RETRIES if suite.get('requires_browser') else 0
    attempt = 0

    while True:
        attempt += 1
        t0 = time.time()
        try:
            result = subprocess.run(
                [PYTHON, script],
                capture_output=True, text=True,
                timeout=TIMEOUT_SECONDS,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            output = result.stdout + result.stderr
            duration = time.time() - t0
            p, f = parse_summary(output)

            if result.returncode == 0 or attempt > retries:
                return p, f, duration, result.returncode, output
            else:
                print(f'    Retry {attempt}/{retries} for {script} (exit={result.returncode})')
                time.sleep(1.5)

        except subprocess.TimeoutExpired:
            duration = time.time() - t0
            if attempt > retries:
                return 0, 1, duration, -1, f'TIMEOUT after {TIMEOUT_SECONDS}s'
            print(f'    Timeout retry {attempt}/{retries} for {script}')
            time.sleep(1.5)

        except Exception as e:
            duration = time.time() - t0
            if attempt > retries:
                return 0, 1, duration, -1, str(e)
            time.sleep(1.5)

def main():
    quick = '--quick' in sys.argv

    print('=' * 64)
    print('  MetaSprint DTA — End-to-End Test Suite')
    print('=' * 64)
    print()

    # Browser check
    print('  Checking browser runtime...')
    if not check_browser():
        print('  ERROR: Chrome/chromedriver not available. Aborting.')
        sys.exit(1)
    print('  Browser: OK\n')

    results = []
    total_pass = 0
    total_fail = 0
    total_time = 0

    for suite in SUITES:
        if quick and suite.get('slow'):
            print(f'  SKIP  {suite["name"]} (--quick mode)')
            results.append((suite['name'], 0, 0, 0, 'SKIP'))
            continue

        print(f'  RUN   {suite["name"]}...')
        p, f, dur, exit_code, output = run_suite(suite)
        total_pass += p
        total_fail += f
        total_time += dur

        status = 'PASS' if exit_code == 0 else 'FAIL'
        results.append((suite['name'], p, f, dur, status))
        print(f'  {status}  {suite["name"]} ({p} passed, {f} failed, {dur:.1f}s)')

        # Show failures if any
        if f > 0:
            for line in output.split('\n'):
                if 'FAIL:' in line:
                    print(f'        {line.strip()}')
        print()

    # Summary table
    print('=' * 64)
    print(f'  {"Suite":<42} {"Pass":>5} {"Fail":>5} {"Time":>6} {"Status":>6}')
    print('-' * 64)
    for name, p, f, dur, status in results:
        time_str = f'{dur:.1f}s' if status != 'SKIP' else '-'
        print(f'  {name:<42} {p:>5} {f:>5} {time_str:>6} {status:>6}')
    print('-' * 64)
    print(f'  {"TOTAL":<42} {total_pass:>5} {total_fail:>5} {total_time:>5.1f}s')
    print('=' * 64)

    if total_fail > 0:
        print(f'\n  RESULT: {total_fail} FAILURE(S)')
    else:
        print(f'\n  RESULT: ALL {total_pass} TESTS PASSED')

    sys.exit(0 if total_fail == 0 else 1)

if __name__ == '__main__':
    main()
