"""
U.S. Census Bureau American Community Survey (ACS) 5-Year Estimates.

Supports C_j (Community / Public Cost Risk) in the AI infrastructure risk framework.
Indicators: baseline population vulnerability, housing affordability, income,
employment, poverty — used to quantify distributional impact of data center deployment.
Cited in paper as USCensusACS.

Uses the free Census API (api.census.gov). No API key required for basic queries.
Downloads 2022 ACS 5-Year county-level estimates for all US counties,
then filters to Nebraska (state FIPS = 31).
"""

import csv
import json
import time
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).parent

CENSUS_API_BASE = "https://api.census.gov/data/2022/acs/acs5"
NEBRASKA_FIPS = "31"

# Variables and their labels
ACS_VARIABLES = {
    "B01003_001E": "total_population",
    "B19013_001E": "median_household_income",
    "B19083_001E": "gini_index",
    "B25077_001E": "median_home_value",
    "B25064_001E": "median_gross_rent",
    "B23025_003E": "labor_force",
    "B23025_004E": "employed_civilian",
    "B23025_005E": "unemployed_civilian",
    "B17001_002E": "population_below_poverty",
    "B25001_001E": "total_housing_units",
    "B25002_003E": "vacant_housing_units",
    "B08303_001E": "total_commuters",
    "B16010_001E": "population_25_plus",
    "B15003_022E": "bachelors_degree",
    "B15003_023E": "masters_degree",
    "B15003_025E": "doctorate_degree",
    "C17002_001E": "ratio_income_to_poverty_total",
    "C17002_002E": "ratio_income_to_poverty_under_0_5",
}


def get_api_key() -> str:
    """Return Census API key from environment or empty string."""
    import os
    return os.environ.get("CENSUS_API_KEY", "")


def build_api_url(state_fips: str, variables: list[str]) -> str:
    get_vars = "NAME," + ",".join(variables)
    key = get_api_key()
    key_param = f"&key={key}" if key else ""
    return f"{CENSUS_API_BASE}?get={get_vars}&for=county:*&in=state:{state_fips}{key_param}"


def fetch_acs(url: str) -> list[list]:
    print(f"  Fetching: {url[:100]}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def write_csv(rows: list[list], fieldnames: list[str], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fieldnames)
        writer.writerows(rows)


def rename_headers(raw_headers: list[str]) -> list[str]:
    """Replace Census variable codes with human-readable names."""
    result = []
    for h in raw_headers:
        result.append(ACS_VARIABLES.get(h, h))
    return result


def fetch_state_acs(state_fips: str, var_batch: list[str]) -> list[list] | None:
    url = build_api_url(state_fips, var_batch)
    try:
        return fetch_acs(url)
    except Exception as e:
        print(f"    Batch failed: {e}")
        return None


def _write_api_key_instructions() -> None:
    instr_path = OUT_DIR / "CENSUS_API_KEY_REQUIRED.txt"
    with open(instr_path, "w") as f:
        f.write("""U.S. Census ACS Data — API Key Required
==========================================

As of 2026, the Census Bureau requires a free API key for all data API requests.

Steps to get and use your key:
  1. Sign up at: https://api.census.gov/data/key_signup.html  (instant, free)
  2. Check email for your key
  3. Re-run this script with your key:
       CENSUS_API_KEY=your_key_here python download.py

This will download:
  - ACS 5-Year county estimates for all US counties (national baseline)
  - Nebraska county subset (93 counties, state FIPS = 31)

Key variables pulled for C_j (Community / Public Cost Risk):
  B01003_001E  Total population
  B19013_001E  Median household income
  B23025_005E  Unemployed civilians
  B17001_002E  Population below poverty level
  B25077_001E  Median home value
  B25064_001E  Median gross rent
  B19083_001E  Gini index (income inequality)

Alternative: Manual download
  1. Visit: https://data.census.gov/
  2. Search 'ACS 5-Year county' for Nebraska
  3. Download CSV and place in this directory
""")
    print(f"  Instructions written -> {instr_path.name}")


def main():
    print("Downloading U.S. Census ACS 5-Year county estimates (2022)...")
    if not get_api_key():
        print("  NOTE: Census API now requires a free key.")
        print("  Get one at: https://api.census.gov/data/key_signup.html")
        print("  Re-run with: CENSUS_API_KEY=<your_key> python download.py")
        _write_api_key_instructions()
        return

    var_keys = list(ACS_VARIABLES.keys())
    # Census API handles ~50 vars per request; split into batches of 15 to be safe
    BATCH_SIZE = 15
    var_batches = [var_keys[i:i+BATCH_SIZE] for i in range(0, len(var_keys), BATCH_SIZE)]

    # All 50 states + DC FIPS codes
    all_state_fips = [
        "01","02","04","05","06","08","09","10","11","12","13","15","16","17","18",
        "19","20","21","22","23","24","25","26","27","28","29","30","31","32","33",
        "34","35","36","37","38","39","40","41","42","44","45","46","47","48","49",
        "50","51","53","54","55","56",
    ]

    print(f"  Fetching {len(all_state_fips)} states × {len(var_batches)} variable batches...")
    national_rows = {}  # county_key -> merged row dict

    for state_fips in all_state_fips:
        merged_for_state = {}
        for batch in var_batches:
            data = fetch_state_acs(state_fips, batch)
            if not data or len(data) < 2:
                continue
            raw_headers = data[0]
            for row in data[1:]:
                row_dict = dict(zip(raw_headers, row))
                county_key = (row_dict.get("state", ""), row_dict.get("county", ""))
                if county_key not in merged_for_state:
                    merged_for_state[county_key] = {"NAME": row_dict.get("NAME", "")}
                merged_for_state[county_key].update(row_dict)
            time.sleep(0.05)

        national_rows.update(merged_for_state)

    if not national_rows:
        api_key = get_api_key()
        if not api_key:
            print("\n  Census API now requires a free API key.")
            print("  Get one at: https://api.census.gov/data/key_signup.html (instant, free)")
            print("  Then re-run with: CENSUS_API_KEY=your_key python download.py")
            _write_api_key_instructions()
            return

        print("  No data returned despite API key. Trying simplified Nebraska-only query...")
        core_vars = ["B01003_001E", "B19013_001E", "B23025_005E", "B17001_002E"]
        data = fetch_state_acs(NEBRASKA_FIPS, core_vars)
        if data and len(data) > 1:
            friendly = rename_headers(data[0])
            ne_path = OUT_DIR / "acs5_2022_counties_nebraska.csv"
            write_csv(data[1:], friendly, ne_path)
            print(f"  Nebraska (core vars): {len(data)-1} counties -> {ne_path.name}")
        else:
            print("\n  Census API unavailable even with key.")
            print("  Try: https://data.census.gov/ for manual download")
        return

    # Build friendly headers from available keys
    all_keys = set()
    for row in national_rows.values():
        all_keys.update(row.keys())
    friendly_map = {k: ACS_VARIABLES.get(k, k) for k in all_keys}

    all_rows_list = list(national_rows.values())
    fieldnames = [friendly_map[k] for k in all_keys]

    # Save national
    nat_path = OUT_DIR / "acs5_2022_counties_national.csv"
    with open(nat_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_keys), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows_list)
    print(f"  National: {len(all_rows_list)} counties -> {nat_path.name}")

    # Filter Nebraska
    ne_rows = [r for r in all_rows_list if r.get("state", "") == NEBRASKA_FIPS]
    ne_path = OUT_DIR / "acs5_2022_counties_nebraska.csv"
    with open(ne_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_keys), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ne_rows)
    print(f"  Nebraska: {len(ne_rows)} counties -> {ne_path.name}")

    # Save variable codebook
    codebook_path = OUT_DIR / "variable_codebook.json"
    with open(codebook_path, "w", encoding="utf-8") as f:
        json.dump({
            "source": "U.S. Census Bureau ACS 5-Year Estimates 2022",
            "api_base": CENSUS_API_BASE,
            "variables": ACS_VARIABLES,
            "risk_variable": "C_j (Community / Public Cost Risk)",
            "key_indicators": {
                "median_household_income": "Baseline economic capacity of host community",
                "median_home_value": "Housing affordability pressure proxy",
                "unemployed_civilian": "Labor market slack / data center employment impact",
                "population_below_poverty": "Distributional vulnerability",
                "gini_index": "Income inequality (equity concern)",
            },
        }, f, indent=2)
    print(f"  Variable codebook: {codebook_path.name}")


if __name__ == "__main__":
    main()
