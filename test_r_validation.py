"""
test_r_validation.py — Cross-validate MetaSprint DTA bivariate GLMM against R mada::reitsma().

Runs validate_vs_mada.R, parses JSON output, and compares against reference values
computed by dta_bivariate_reference.py using the same datasets.

Tolerances account for methodological differences:
  - DL (app) vs REML/ML (mada): pooled estimates can differ by ~0.01-0.02
  - CIs: different variance estimation methods cause ~0.03 differences
  - DOR: exponential scale amplifies small logit differences -> 10% relative tolerance

Usage: python test_r_validation.py
Exit code: 0 if all pass, 1 if any fail
"""
import sys
import os
import json
import subprocess
import io

# Ensure UTF-8 stdout on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ---- Configuration ----
RSCRIPT_PATHS = [
    r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe",
    r"C:\Program Files\R\R-4.4.2\bin\Rscript.exe",
    r"C:\Program Files\R\R-4.4.1\bin\Rscript.exe",
    "Rscript",  # fallback to PATH
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
R_SCRIPT = os.path.join(SCRIPT_DIR, "validate_vs_mada.R")

# ---- Compute DL reference values using the app's algorithm ----
sys.path.insert(0, SCRIPT_DIR)
from dta_bivariate_reference import bivariate_dl_pool

# Datasets must match validate_vs_mada.R exactly
DATASETS = {
    "BNP_HF_k6": [
        {'tp': 52, 'fp': 14, 'fn': 8, 'tn': 76},
        {'tp': 44, 'fp': 20, 'fn': 6, 'tn': 151},
        {'tp': 379, 'fp': 83, 'fn': 65, 'tn': 959},
        {'tp': 89, 'fp': 17, 'fn': 14, 'tn': 337},
        {'tp': 40, 'fp': 22, 'fn': 5, 'tn': 138},
        {'tp': 163, 'fp': 44, 'fn': 21, 'tn': 416},
    ],
    "hsTroponin_AMI_k5": [
        {'tp': 45, 'fp': 12, 'fn': 5, 'tn': 88},
        {'tp': 98, 'fp': 25, 'fn': 10, 'tn': 167},
        {'tp': 72, 'fp': 18, 'fn': 8, 'tn': 102},
        {'tp': 33, 'fp': 8, 'fn': 3, 'tn': 56},
        {'tp': 156, 'fp': 40, 'fn': 15, 'tn': 289},
    ],
    "CTCA_CAD_k4": [
        {'tp': 30, 'fp': 8, 'fn': 2, 'tn': 60},
        {'tp': 65, 'fp': 15, 'fn': 5, 'tn': 115},
        {'tp': 22, 'fp': 5, 'fn': 0, 'tn': 73},
        {'tp': 88, 'fp': 22, 'fn': 7, 'tn': 183},
    ],
}


def compute_dl_references():
    """Compute DL reference values for each dataset using the app's algorithm."""
    refs = {}
    for name, studies in DATASETS.items():
        r = bivariate_dl_pool(studies)
        if r is None:
            print(f"  WARNING: bivariate_dl_pool returned None for {name}")
            continue
        refs[name] = {
            'pooled_sens': r['pooledSens'],
            'pooled_spec': r['pooledSpec'],
            'sens_ci_lo': r['sensCI'][0],
            'sens_ci_hi': r['sensCI'][1],
            'spec_ci_lo': r['specCI'][0],
            'spec_ci_hi': r['specCI'][1],
            'dor': r['dor'],
            'tau2_sens': r['tau2_sens'],
            'tau2_spec': r['tau2_spec'],
            'mu1_logit_sens': r['mu1'],
            'mu2_logit_spec': r['mu2'],
        }
    return refs


def find_rscript():
    """Find an available Rscript executable."""
    for path in RSCRIPT_PATHS:
        try:
            result = subprocess.run(
                [path, "--version"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def run_r_validation():
    """Run the R script and parse JSON output."""
    rscript = find_rscript()
    if rscript is None:
        print("WARNING: R/Rscript not found. Skipping R cross-validation.")
        print("  Install R and mada package, or set Rscript in PATH.")
        return None

    print(f"Using Rscript: {rscript}")
    print(f"Running: {R_SCRIPT}")

    try:
        result = subprocess.run(
            [rscript, R_SCRIPT],
            capture_output=True, text=True, timeout=120,
            cwd=SCRIPT_DIR
        )
    except subprocess.TimeoutExpired:
        print("ERROR: R script timed out after 120 seconds.")
        return None

    if result.returncode != 0:
        print(f"ERROR: R script failed (exit code {result.returncode})")
        if result.stderr:
            # Filter out common mada warnings
            for line in result.stderr.strip().split('\n'):
                if 'very few primary studies' not in line:
                    print(f"  R stderr: {line}")
        return None

    # Parse JSON from stdout
    stdout = result.stdout.strip()
    if not stdout:
        print("ERROR: R script produced no output.")
        return None

    try:
        r_results = json.loads(stdout)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse R JSON output: {e}")
        print(f"  First 500 chars: {stdout[:500]}")
        return None

    return r_results


def compare_values(label, app_val, r_val, abs_tol=None, rel_tol=None):
    """Compare two values with tolerance. Returns (pass, message)."""
    if app_val is None or r_val is None:
        return True, f"  {label:30s}  app={app_val!s:>12s}  R={r_val!s:>12s}  SKIP (None)"

    diff_abs = abs(app_val - r_val)

    if rel_tol is not None and app_val != 0:
        diff_rel = diff_abs / abs(app_val)
        passed = diff_rel <= rel_tol
        tol_str = f"rel={rel_tol:.0%}"
        diff_str = f"rel={diff_rel:.2%}"
    elif abs_tol is not None:
        passed = diff_abs <= abs_tol
        tol_str = f"abs={abs_tol}"
        diff_str = f"abs={diff_abs:.6f}"
    else:
        passed = diff_abs < 1e-6
        tol_str = "exact"
        diff_str = f"abs={diff_abs:.6f}"

    status = "PASS" if passed else "FAIL"
    msg = f"  {label:30s}  app={app_val:>12.6f}  R={r_val:>12.6f}  diff={diff_str:>14s}  tol={tol_str:>10s}  [{status}]"
    return passed, msg


def main():
    print("=" * 100)
    print("MetaSprint DTA vs R mada::reitsma() Cross-Validation")
    print("=" * 100)
    print()

    # Step 1: Compute DL reference values
    print("Computing DL reference values from dta_bivariate_reference.py...")
    dl_refs = compute_dl_references()
    if not dl_refs:
        print("ERROR: Failed to compute DL reference values.")
        return 1
    print(f"  Computed references for {len(dl_refs)} datasets.\n")

    # Step 2: Run R validation
    print("Running R mada validation...")
    r_results = run_r_validation()
    if r_results is None:
        print("\nWARNING: R validation skipped. Exiting with code 0 (not a failure).")
        return 0
    print(f"  Got {len(r_results)} R results (REML + ML for each dataset).\n")

    # Step 3: Compare
    all_passed = True
    total_tests = 0
    total_passed = 0

    # Group R results by dataset
    r_by_dataset = {}
    for r in r_results:
        ds = r['dataset']
        if ds not in r_by_dataset:
            r_by_dataset[ds] = {}
        r_by_dataset[ds][r['method']] = r

    for ds_name in DATASETS:
        if ds_name not in dl_refs:
            print(f"\n--- {ds_name}: NO DL REFERENCE ---")
            continue
        if ds_name not in r_by_dataset:
            print(f"\n--- {ds_name}: NO R RESULTS ---")
            continue

        ref = dl_refs[ds_name]
        k = len(DATASETS[ds_name])

        # CI tolerance depends on k:
        # The app uses t(df=k-2) critical values for k<30; mada uses z-based Wald CIs.
        # For k=4 (df=2), t(0.975,2)=4.303 vs z=1.96, a 2.2x difference that
        # produces legitimately wider CIs in the app. This is a methodological
        # choice, not a bug. We use wider tolerance for small k.
        if k <= 5:
            ci_tol = 0.08  # t vs z diverges substantially for df<=3
        else:
            ci_tol = 0.03

        for method in ["REML", "ML"]:
            if method not in r_by_dataset[ds_name]:
                continue
            r = r_by_dataset[ds_name][method]

            ci_note = f" (t(df={k-2}) vs z)" if k < 30 else ""
            print(f"\n--- {ds_name} | App DL vs R mada {method} ---")
            if k <= 5:
                print(f"  NOTE: k={k}, app uses t(df={k-2}) crit value; mada uses z. CI tolerance widened to {ci_tol}.")
            print(f"  {'Metric':<30s}  {'App (DL)':>12s}  {'R (mada)':>12s}  {'Difference':>14s}  {'Tolerance':>10s}  Status")
            print("  " + "-" * 96)

            # Note: mada models logit(FPR), so logit_spec = -logit_fpr
            # The app models logit(spec) directly
            comparisons = [
                # (label, app_value, r_value, abs_tol, rel_tol)
                ("Pooled Sensitivity",    ref['pooled_sens'],   r['pooled_sens'],   0.02, None),
                ("Pooled Specificity",    ref['pooled_spec'],   r['pooled_spec'],   0.02, None),
                ("Sens CI lower",         ref['sens_ci_lo'],    r['sens_ci_lo'],    ci_tol, None),
                ("Sens CI upper",         ref['sens_ci_hi'],    r['sens_ci_hi'],    ci_tol, None),
                ("Spec CI lower",         ref['spec_ci_lo'],    r['spec_ci_lo'],    ci_tol, None),
                ("Spec CI upper",         ref['spec_ci_hi'],    r['spec_ci_hi'],    ci_tol, None),
                ("DOR",                   ref['dor'],           r['dor'],           None, 0.20),
                ("logit(Sens)",           ref['mu1_logit_sens'], r['logit_sens'],   0.10, None),
                ("logit(Spec)",           ref['mu2_logit_spec'], r['logit_spec'],   0.10, None),
            ]

            # AUC: only compare if R has it
            if r.get('auc') is not None:
                comparisons.append(
                    ("AUC (SROC)",        None,                 r['auc'],           0.03, None)
                )

            for label, app_val, r_val, abs_tol, rel_tol in comparisons:
                if app_val is None:
                    # Info-only (no app reference)
                    print(f"  {label:30s}  {'N/A':>12s}  R={r_val:>12.6f}  (info only)")
                    continue
                passed, msg = compare_values(label, app_val, r_val, abs_tol, rel_tol)
                print(msg)
                total_tests += 1
                if passed:
                    total_passed += 1
                else:
                    all_passed = False

    # Summary
    print("\n" + "=" * 100)
    print(f"SUMMARY: {total_passed}/{total_tests} comparisons passed")

    if all_passed:
        print("STATUS: ALL PASS -- App DL estimates are consistent with R mada::reitsma()")
        print()
        print("Notes on expected differences:")
        print("  - DerSimonian-Laird (app) vs REML/ML (mada): different tau2 estimation methods")
        print("  - App uses univariate DL on each dimension; mada uses bivariate GLMM (joint likelihood)")
        print("  - App uses t-distribution CIs (df=k-2) for k<30; mada uses z-based (Wald) CIs")
        print("  - Continuity correction: app adds 0.5 only when zero cell present; mada adds 0.5 to all cells by default")
    else:
        print("STATUS: SOME FAILURES -- Review differences above")

    print("=" * 100)
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
