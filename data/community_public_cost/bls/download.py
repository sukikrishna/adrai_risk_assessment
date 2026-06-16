"""
Bureau of Labor Statistics (BLS) — employment and wage data by state and county.

Supports C_j (Community / Public Cost Risk) in the AI infrastructure risk framework.
Indicators: employment levels, wages, labor market conditions, industry mix.
Cited in paper as BLSData.

Downloads via BLS Public API (no key required, 500 req/day, 25 series/request):
  1. BLS LAUS — state-level unemployment for Nebraska
  2. BLS QCEW — Nebraska employment by industry (via API)
  3. BLS CPI — consumer price index for regional context

Direct file downloads (FEMA/BLS bulk files are often blocked):
  Falls back gracefully with manual instructions if blocked.
"""

import csv
import io
import json
import time
import urllib.request
import urllib.parse
import zipfile
from pathlib import Path

OUT_DIR = Path(__file__).parent

NEBRASKA_FIPS_PREFIX = "31"
NEBRASKA_STATE_CODE = "NE"

BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# LAUS series for Nebraska state and key counties
# Series format: LAUCN{FIPS5}{measure}
# Measures: 03=unemployment rate, 04=unemployment, 05=employment, 06=labor force
# Nebraska state: LASST310000000000003 (unemployment rate)
# Nebraska counties use LAUCN31{county_fips3}0000000000{measure}
# Top Nebraska counties by population
LAUS_SERIES = {
    "NE_state_unemp_rate": "LASST310000000000003",
    "NE_state_employed": "LASST310000000000005",
    "NE_state_labor_force": "LASST310000000000006",
    # Douglas County (Omaha)
    "Douglas_unemp_rate": "LAUCN3104500000000003",
    "Douglas_employment": "LAUCN3104500000000005",
    # Lancaster County (Lincoln)
    "Lancaster_unemp_rate": "LAUCN3110900000000003",
    "Lancaster_employment": "LAUCN3110900000000005",
    # Sarpy County (suburban Omaha)
    "Sarpy_unemp_rate": "LAUCN3115300000000003",
    # Hall County (Grand Island)
    "Hall_unemp_rate": "LAUCN3108100000000003",
    # Madison County (Norfolk)
    "Madison_unemp_rate": "LAUCN3111900000000003",
    # Lincoln County (North Platte)
    "Lincoln_unemp_rate": "LAUCN3111100000000003",
    # Dawson County (Lexington — rural/meatpacking)
    "Dawson_unemp_rate": "LAUCN3104700000000003",
    # Buffalo County (Kearney)
    "Buffalo_unemp_rate": "LAUCN3101900000000003",
}

# BLS OES (Occupational Employment and Wages) - Nebraska state aggregate
OES_SERIES = {
    "NE_all_occupations_mean_wage": "OEUS3100000000000000M01",
    "NE_computer_occupations_mean_wage": "OEUS3100000015000000M01",
}

# QCEW direct file (fallback — BLS may block)
QCEW_URLS = [
    "https://www.bls.gov/cew/data/files/2023/csv/2023_annual_singlefile.zip",
    "https://www.bls.gov/cew/data/files/2022/csv/2022_annual_singlefile.zip",
]


def bls_api_request(series_ids: list[str], start_year: str = "2018", end_year: str = "2024") -> dict:
    """Query BLS public API v2. No key needed for up to 25 series."""
    payload = json.dumps({
        "seriesid": series_ids,
        "startyear": start_year,
        "endyear": end_year,
    }).encode("utf-8")
    req = urllib.request.Request(
        BLS_API_URL,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def fetch_laus_api() -> None:
    """Fetch Nebraska LAUS data via BLS API."""
    print("  Fetching Nebraska LAUS via BLS API...")
    series_ids = list(LAUS_SERIES.values())

    # BLS API: max 25 series per call
    chunks = [series_ids[i:i+25] for i in range(0, len(series_ids), 25)]
    all_data = {}
    for chunk in chunks:
        try:
            resp = bls_api_request(chunk)
            if resp.get("status") != "REQUEST_SUCCEEDED":
                print(f"  API warning: {resp.get('message', resp.get('status',''))}")
            for series in resp.get("Results", {}).get("series", []):
                all_data[series["seriesID"]] = series["data"]
            time.sleep(0.5)
        except Exception as e:
            print(f"  API request failed: {e}")

    if not all_data:
        print("  No data returned from BLS API")
        return

    # Invert series_id -> friendly name
    id_to_name = {v: k for k, v in LAUS_SERIES.items()}

    rows = []
    for series_id, data_points in all_data.items():
        name = id_to_name.get(series_id, series_id)
        for dp in data_points:
            rows.append({
                "series_id": series_id,
                "series_name": name,
                "year": dp.get("year"),
                "period": dp.get("period"),
                "period_name": dp.get("periodName"),
                "value": dp.get("value"),
                "footnotes": "; ".join(f.get("text", "") for f in dp.get("footnotes", []) if f),
            })

    out_path = OUT_DIR / "bls_laus_nebraska_api.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["series_id", "series_name", "year", "period",
                                               "period_name", "value", "footnotes"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"  LAUS Nebraska (API): {len(rows)} data points -> {out_path.name}")

    # Also save the series catalog
    catalog_path = OUT_DIR / "bls_series_catalog.json"
    with open(catalog_path, "w") as f:
        json.dump(LAUS_SERIES, f, indent=2)
    print(f"  Series catalog -> {catalog_path.name}")


def try_direct_qcew_download() -> None:
    """Try bulk QCEW download (may be blocked; graceful fallback)."""
    for url in QCEW_URLS:
        year = url.split("/")[-3]
        out_path = OUT_DIR / f"qcew_{year}_singlefile.zip"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            with open(out_path, "wb") as f:
                f.write(data)
            print(f"  QCEW downloaded: {out_path.name} ({len(data)/1e6:.0f} MB)")
            # Extract Nebraska
            with zipfile.ZipFile(out_path) as z:
                csv_files = [n for n in z.namelist() if n.endswith(".csv")]
                for csv_name in csv_files[:1]:
                    with z.open(csv_name) as cf:
                        content = cf.read().decode("latin-1")
                    reader = csv.DictReader(io.StringIO(content))
                    ne_rows = [r for r in reader
                               if r.get("area_fips", "").startswith(NEBRASKA_FIPS_PREFIX)
                               and len(r.get("area_fips", "")) == 5]
                    if ne_rows:
                        ne_path = OUT_DIR / f"qcew_{year}_nebraska.csv"
                        with open(ne_path, "w", newline="") as f:
                            writer = csv.DictWriter(f, fieldnames=ne_rows[0].keys())
                            writer.writeheader()
                            writer.writerows(ne_rows)
                        print(f"  QCEW Nebraska {year}: {len(ne_rows)} rows -> {ne_path.name}")
            return
        except Exception as e:
            print(f"  QCEW direct download failed ({year}): {e}")

    print("  QCEW bulk download unavailable.")
    print("  Visit: https://www.bls.gov/cew/downloadable-data.htm")
    instr_path = OUT_DIR / "QCEW_MANUAL_DOWNLOAD.txt"
    with open(instr_path, "w") as f:
        f.write("""BLS QCEW Manual Download Instructions
======================================
1. Visit: https://www.bls.gov/cew/downloadable-data.htm
2. Under 'Annual Data Files', select the most recent year
3. Download 'CSV — Single Files (all areas and ownerships)'
4. Extract and place in this directory
5. Re-run: python download.py

Key columns for C_j risk assessment:
  area_fips: county FIPS (31xxx = Nebraska)
  industry_code: NAICS sector
  avg_annual_pay: average wage in sector
  annual_avg_emplvl: average employment level
  total_annual_wages: total wage bill
""")
    print(f"  Instructions -> {instr_path.name}")


def main():
    print("Downloading BLS employment data...\n")

    print("1. BLS LAUS — Nebraska unemployment via public API...")
    fetch_laus_api()
    print()

    print("2. BLS QCEW — county employment by industry...")
    try_direct_qcew_download()

    print("\nBLS download complete.")


if __name__ == "__main__":
    main()
