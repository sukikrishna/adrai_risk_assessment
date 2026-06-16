"""
Download all open-source datasets for the AI infrastructure risk assessment framework.

Runs each sub-folder's download.py in sequence. All datasets correspond to risk
variables in the NeurIPS 2026 paper:

  R_j = w1*F_j + w2*G_j + w3*R_res_j + w4*C_j + w5*O_j

Usage:
  python data/download_all.py

Requirements:
  pip install openpyxl   (for Excel extraction — needed for eGRID, EIA, EIA-860M)

Each script saves:
  - A national / full dataset file
  - A Nebraska-filtered subset (state FIPS = 31, for case study)
"""

import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent

SCRIPTS = [
    ("F_j  Financial / Opacity",      BASE / "financial_opacity/sec_edgar/download.py"),
    ("G_j  Geographic Vulnerability",  BASE / "geographic_vulnerability/fema_nri/download.py"),
    ("G_j  Geographic Vulnerability",  BASE / "geographic_vulnerability/noaa/download.py"),
    ("R_j  Resource Stress (eGRID)",   BASE / "resource_stress/epa_egrid/download.py"),
    ("R_j  Resource Stress (Aqueduct)",BASE / "resource_stress/wri_aqueduct/download.py"),
    ("R_j  Resource Stress (EIA)",     BASE / "resource_stress/eia/download.py"),
    ("C_j  Community / Public Cost",   BASE / "community_public_cost/census_acs/download.py"),
    ("C_j  Community / Public Cost",   BASE / "community_public_cost/bls/download.py"),
    ("O_j  Market Mismatch",           BASE / "market_mismatch/eia_capacity/download.py"),
]


def run_script(label: str, script: Path) -> bool:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  {script.relative_to(BASE)}")
    print(f"{'='*60}")
    start = time.time()
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(script.parent),
        capture_output=False,
    )
    elapsed = time.time() - start
    status = "OK" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
    print(f"\n  [{status}] in {elapsed:.1f}s")
    return result.returncode == 0


def main():
    print("AI Infrastructure Risk Assessment — Dataset Download")
    print("=" * 60)
    print("Downloading open-source data for all 5 risk variables.\n")

    results = {}
    for label, script in SCRIPTS:
        if not script.exists():
            print(f"\n  SKIP (not found): {script}")
            results[str(script)] = "MISSING"
            continue
        ok = run_script(label, script)
        results[str(script)] = "OK" if ok else "FAILED"

    print(f"\n{'='*60}")
    print("Download Summary")
    print(f"{'='*60}")
    for script_path, status in results.items():
        rel = Path(script_path).relative_to(BASE)
        print(f"  {status:8s}  {rel}")

    failed = [k for k, v in results.items() if v == "FAILED"]
    if failed:
        print(f"\n{len(failed)} script(s) reported errors — check output above.")
    else:
        print("\nAll downloads completed.")


if __name__ == "__main__":
    main()
