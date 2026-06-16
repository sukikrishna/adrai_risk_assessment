"""
WRI Aqueduct 4.0 — baseline water risk indicators at watershed level.

Supports R_res_j / W_j (Water Risk) in the AI infrastructure risk framework.
Key indicators: water depletion (S_basin), water stress, interannual variability,
seasonal variability, groundwater table decline. Cited in paper as kuzma2023aqueduct.

Nebraska sits primarily over the Ogallala/High Plains Aquifer (HPA), which falls
in the Missouri River basin. Aqueduct 4.0 provides HydroSHEDS basin-level scores.

WRI Aqueduct 4.0 data: https://www.wri.org/data/aqueduct-global-maps-40-data
The data is hosted on WRI's servers; this script attempts known download URLs
and provides manual instructions if automated download fails.
"""

import csv
import io
import json
import urllib.request
import zipfile
from pathlib import Path

OUT_DIR = Path(__file__).parent

# Known WRI Aqueduct 4.0 file locations (try in order)
AQUEDUCT_URLS = [
    # Annual baseline CSV (lighter than the GDB)
    "https://files.wri.org/d8/s3fs-public/2023-09/Aqueduct40_Y2023D07M05_baseline_annual.zip",
    "https://files.wri.org/d8/s3fs-public/aqueduct40_baseline_annual_y2023m07d05.zip",
    "https://files.wri.org/d8/s3fs-public/2023-09/Aqueduct40_baseline_annual.zip",
]

# WRI country code for US = 840 (UN numeric)
US_COUNTRY_CODE = "840"


def try_download(urls: list[str], out_path: Path) -> bool:
    for url in urls:
        print(f"  Trying: {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"  Downloaded {len(data) / 1e6:.1f} MB -> {out_path.name}")
            return True
        except Exception as e:
            print(f"    Failed: {e}")
    return False


def extract_and_filter(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path) as z:
        csv_files = [n for n in z.namelist() if n.endswith(".csv")]
        print(f"  CSV files in zip: {csv_files}")

        for csv_name in csv_files:
            with z.open(csv_name) as cf:
                content = cf.read().decode("utf-8-sig")

            # Save national (US) subset
            reader = csv.DictReader(io.StringIO(content))
            all_rows = list(reader)
            fieldnames = reader.fieldnames or []

            # Save full file
            full_path = OUT_DIR / csv_name
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Full file saved: {full_path.name} ({len(all_rows)} basins)")

            # US subset (country_un = 840)
            us_rows = [r for r in all_rows if r.get("country_un", "").strip() == US_COUNTRY_CODE]
            if us_rows:
                us_path = OUT_DIR / csv_name.replace(".csv", "_us.csv")
                with open(us_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(us_rows)
                print(f"  US basins: {len(us_rows)} -> {us_path.name}")

            # Nebraska basin IDs overlap with HydroSHEDS level-6 basins in Missouri River watershed
            # The HYBAS_ID range for Nebraska basins is approximately 7080461700-7080461900
            # Filter by known Nebraska/Plains keywords or pfaf_id prefix for Missouri basin (7)
            ne_rows = [
                r for r in us_rows
                if str(r.get("name", "")).upper() in {"MISSOURI", "PLATTE", "REPUBLICAN",
                                                        "LOUP", "NIOBRARA", "ELKHORN"}
                or str(r.get("pfaf_id", "")).startswith("74")  # Missouri basin HydroSHEDS prefix
            ]
            if ne_rows:
                ne_path = OUT_DIR / csv_name.replace(".csv", "_nebraska_basins.csv")
                with open(ne_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(ne_rows)
                print(f"  Nebraska-relevant basins: {len(ne_rows)} -> {ne_path.name}")


def write_instructions() -> None:
    instructions = OUT_DIR / "MANUAL_DOWNLOAD_INSTRUCTIONS.txt"
    with open(instructions, "w", encoding="utf-8") as f:
        f.write("""WRI Aqueduct 4.0 — Manual Download Instructions
================================================

Automated download was not successful. Please download manually:

1. Visit: https://www.wri.org/data/aqueduct-global-maps-40-data
2. Click 'Download Data' for 'Aqueduct 4.0 — Baseline Water Risk — Annual'
3. Select CSV format (the GDB is large; CSV is sufficient for tabular analysis)
4. Place the downloaded file in this directory:
   data/resource_stress/wri_aqueduct/

5. Re-run this script to generate US and Nebraska-filtered subsets:
   python download.py

Alternatively, use the WRI Aqueduct Water Risk Atlas API:
   https://www.wri.org/applications/aqueduct/water-risk-atlas/

Key variables for AI infrastructure risk assessment (W_j):
  - bws_raw / bws_score: baseline water stress (S_basin proxy)
  - bwd_raw / bwd_score: baseline water depletion
  - iav_raw / iav_score: interannual variability
  - sev_raw / sev_score: seasonal variability
  - gtd_raw / gtd_score: groundwater table decline (critical for Ogallala)
  - rfr_raw / rfr_score: riverine flood risk
  - drr_raw / drr_score: drought risk
""")
    print(f"  Instructions written to {instructions.name}")


def main():
    print("Downloading WRI Aqueduct 4.0 baseline water risk data...")
    zip_path = OUT_DIR / "aqueduct40_baseline_annual.zip"

    success = try_download(AQUEDUCT_URLS, zip_path)

    if success:
        extract_and_filter(zip_path)
    else:
        print("\n  Could not automatically download WRI Aqueduct data.")
        write_instructions()

        # Save a metadata JSON noting the variables and source
        meta = {
            "dataset": "WRI Aqueduct 4.0",
            "version": "4.0 (2023)",
            "citation": "Kuzma et al. (2023). Aqueduct 4.0. https://doi.org/10.46830/writn.23.00061",
            "paper_citation_key": "kuzma2023aqueduct",
            "url": "https://www.wri.org/data/aqueduct-global-maps-40-data",
            "risk_variable": "R_res_j / W_j (water risk component)",
            "key_indicators": {
                "bws": "Baseline water stress (S_basin proxy)",
                "bwd": "Baseline water depletion",
                "iav": "Interannual variability",
                "sev": "Seasonal variability",
                "gtd": "Groundwater table decline (critical for Ogallala Aquifer)",
                "rfr": "Riverine flood risk",
                "drr": "Drought risk",
            },
            "nebraska_relevance": (
                "Nebraska overlies the Ogallala/High Plains Aquifer. "
                "Elevated bws and gtd scores flag long-term depletion risk (S_basin). "
                "Missouri and Platte River basins are the primary HydroSHEDS units."
            ),
        }
        meta_path = OUT_DIR / "aqueduct40_dataset_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        print(f"  Metadata saved to {meta_path.name}")


if __name__ == "__main__":
    main()
