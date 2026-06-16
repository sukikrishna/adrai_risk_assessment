# Data: AI Infrastructure Risk Assessment

This directory contains open-source datasets supporting the five risk components defined in the paper's composite risk formula:

```
R_j = w1·F_j + w2·G_j + w3·R_res_j + w4·C_j + w5·O_j
```

Each subfolder corresponds to one risk variable and holds a `download.py` script that fetches the relevant public data. National-scope files and Nebraska-filtered subsets (the paper's case study, FIPS = 31, 93 counties) are saved side by side. Run `python download_all.py` from this directory to refresh everything.

---

## Folder structure

```
data/
├── financial_opacity/          F_j  — Financial / Opacity Risk
│   └── sec_edgar/
├── geographic_vulnerability/   G_j  — Geographic Vulnerability Risk
│   ├── fema_nri/
│   └── noaa/
├── resource_stress/            R_res_j — Resource Stress Risk
│   ├── epa_egrid/
│   ├── wri_aqueduct/
│   └── eia/
├── community_public_cost/      C_j  — Community / Public Cost Risk
│   ├── census_acs/
│   └── bls/
├── market_mismatch/            O_j  — Market Mismatch / Operational Fragility
│   └── eia_capacity/
└── download_all.py             Orchestrator — runs all 9 scripts in sequence
```

---

## F_j — Financial Opacity (`financial_opacity/`)

Captures asymmetric information risk: extent to which AI infrastructure investment is opaque to the public and regulators.

### `sec_edgar/`

| File | Description | Rows |
|---|---|---|
| `edgar_filings_index.csv` | Most recent 10-K filing metadata for 10 major hyperscalers / data center operators (Amazon, Microsoft, Google, Meta, Apple, Oracle, Equinix, Digital Realty, Nvidia, Intel). Columns: `company, cik, form, filing_date, accession_number, filing_url, sic`. | 26 |
| `company_tickers_all.json` | Full SEC EDGAR company ticker registry (10,415 companies) — useful for expanding coverage to additional data center operators. | — |

**Source:** SEC EDGAR public API (`https://data.sec.gov/submissions/`)

**Paper variable:** Feeds the opacity scoring component of F_j; actual disclosure-quality scoring requires reading the 10-K text (links in `filing_url`).

---

## G_j — Geographic Vulnerability (`geographic_vulnerability/`)

Captures exposure to physical hazards: extreme weather, natural disasters, and climate-related risks at the county level.

### `fema_nri/` ⚠️ Manual download required

FEMA's National Risk Index provides composite and per-hazard risk scores for all ~3,000 US counties. `download.py` tries automated download but FEMA's portal (`hazards.fema.gov`) blocks automated requests. See `MANUAL_DOWNLOAD_INSTRUCTIONS.txt`.

**To get the data:** Download `NRI_Table_Counties.zip` from the [FEMA RAPT tool](https://www.fema.gov/emergency-managers/practitioners/resilience-analysis-and-planning-tool), place it here, and re-run `download.py`. The script will then extract a Nebraska-only CSV (~93 rows).

**Key columns once downloaded:** `COUNTY, STATEABBRV, RISK_SCORE, RISK_RATNG, DRGT_RISKS, HRCN_RISKS, TRND_RISKS, HWAV_RISKS, WFIR_RISKS` (per-hazard scores relevant to data center siting).

### `noaa/`

NOAA Storm Events Database — all recorded significant weather/storm events.

| File | Description | Rows |
|---|---|---|
| `StormEvents_..._d2021_..._nebraska.csv` | All NE storm events, 2021 | 1,611 |
| `StormEvents_..._d2022_..._nebraska.csv` | All NE storm events, 2022 | 2,195 |
| `StormEvents_..._d2023_..._nebraska.csv` | All NE storm events, 2023 | 2,335 |
| `StormEvents_..._nebraska_infrastructure_relevant.csv` | Subset filtered to event types most relevant to data center operations: drought, heat wave, flood, tornado, wildfire, ice storm, high wind, thunderstorm, hail, winter storm, blizzard | varies |
| `StormEvents_..._d{year}_....csv.gz` | Full national compressed files (raw) | ~500k/yr |

**Key columns:** `EVENT_TYPE, STATE, CZ_NAME` (county), `BEGIN_DATE_TIME, END_DATE_TIME, DAMAGE_PROPERTY, DAMAGE_CROPS, DEATHS_DIRECT, BEGIN_LAT, BEGIN_LON`.

**Source:** NOAA NCEI (`https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/`)

---

## R_res_j — Resource Stress (`resource_stress/`)

Captures constraints on the two main physical inputs to data center operations: electricity and water.

### `epa_egrid/`

EPA Emissions & Generation Resource Integrated Database (eGRID) 2022 — plant-level and regional electricity generation, emissions, and fuel mix.

| File | Description | Rows |
|---|---|---|
| `egrid2022_plant_national.csv` | All US power plants. Key columns: `PNAME, PSTATABB, LAT, LON, PLPRMFL` (primary fuel), `PLNGENAN` (annual net generation MWh), `PLCO2AN` (annual CO₂ tons). | 11,973 |
| `egrid2022_plant_nebraska_relevant.csv` | Nebraska plants only. Subregions: MROW (MRO West), SPPN, SPPS. | 1,325 |
| `egrid2022_subregion_national.csv` | Grid subregion aggregates — capacity factor, emission rates, generation mix. | 27 |
| `egrid2022_subregion_nebraska_relevant.csv` | Nebraska subregion rows. | 1 |
| `egrid2022_state_national.csv` | State-level aggregates (all 50 states + DC). | 52 |
| `egrid2022_state_nebraska_relevant.csv` | Nebraska state row. | 1 |
| `egrid2022_us_total_national.csv` | National totals row. | 1 |
| `egrid2022_data.xlsx` | Raw source workbook (15.6 MB). Sheets: PLNT22, SRL22, ST22, US22. Row 1 = variable codes; Row 2+ = data. | — |

**Source:** EPA eGRID 2022 (`https://www.epa.gov/system/files/documents/2024-01/egrid2022_data.xlsx`)

### `wri_aqueduct/` ⚠️ Manual download required

WRI Aqueduct 4.0 — global baseline water risk indicators at the watershed level. Key indicators for data centers: `bws` (baseline water stress), `gtd` (groundwater table decline, relevant for Nebraska's Ogallala Aquifer).

See `MANUAL_DOWNLOAD_INSTRUCTIONS.txt` and `aqueduct40_dataset_metadata.json` for variable descriptions. Download from [wri.org/data/aqueduct-global-maps-40-data](https://www.wri.org/data/aqueduct-global-maps-40-data).

### `eia/`

EIA plant-level and state-level electricity data.

| File | Description | Rows (NE) |
|---|---|---|
| `eia860_plant_nebraska.csv` | EIA Form 860 (2022) plant roster for Nebraska: location, utility, balancing authority, sector. | 135 |
| `eia860_generator_nebraska.csv` | Generator-level detail: fuel type, nameplate capacity (MW), operating status, online year. | 309 |
| `annual_generation_state_nebraska.csv` | State-level annual net generation by energy source and producer type, all years back to 1990. | 919 |
| `existcapacity_annualx_nebraska.csv` | Existing installed capacity (MW) by fuel type, Nebraska, all years. | 778 |
| `annual_generation_state_national.csv` | Same as above, all 50 states (64,417 rows). | — |
| `existcapacity_annualx_national.csv` | Capacity by fuel, all states. | — |
| `eia860.zip` / `eia923.zip` | Raw source ZIPs (EIA-860 2022, EIA-923 2022). | — |

**Source:** EIA Form 860 archive (`https://www.eia.gov/electricity/data/eia860/`), EIA state data tables.

---

## C_j — Community / Public Cost (`community_public_cost/`)

Captures the distributional and fiscal burden on local communities from hosting large AI infrastructure.

### `census_acs/` ⚠️ API key required

ACS 5-Year Estimates provide county-level socioeconomic indicators. The Census API now requires a free key.

**To get the data:**
1. Register at [api.census.gov/data/key_signup.html](https://api.census.gov/data/key_signup.html)
2. Run: `CENSUS_API_KEY=<your_key> python census_acs/download.py`

This will fetch Nebraska's 93 counties with variables including: median household income, Gini coefficient, median home value, median rent, employment rate, poverty rate, and housing unit counts.

See `CENSUS_API_KEY_REQUIRED.txt` for full instructions.

### `bls/`

Bureau of Labor Statistics labor market data for Nebraska.

| File | Description | Rows |
|---|---|---|
| `bls_laus_nebraska_api.csv` | LAUS (Local Area Unemployment Statistics) via BLS API v2. Unemployment rate, labor force, employment, unemployment level. Covers Nebraska state + 8 major counties (Douglas, Lancaster, Sarpy, Hall, Buffalo, Dodge, Madison, Platte). Columns: `series_id, series_name, year, period, period_name, value`. | 252 |
| `bls_series_catalog.json` | Series ID → human-readable name mapping for all fetched series. | — |

**Source:** BLS Public API v2 (`https://api.bls.gov/publicAPI/v2/timeseries/data/`). No key required; 500 requests/day limit.

**Note:** BLS QCEW (county-level employment by industry, useful for estimating existing industrial load and labor market tightness) is not available via automated download. See `QCEW_MANUAL_DOWNLOAD.txt` for instructions.

---

## O_j — Market Mismatch (`market_mismatch/`)

Captures the risk that AI infrastructure investment outpaces grid capacity and market fundamentals, creating stranded assets or ratepayer cost overruns.

### `eia_capacity/`

| File | Description | Rows (NE) |
|---|---|---|
| `eia860m_operating_nebraska.csv` | Currently operating generators in Nebraska (EIA-860M Dec 2023). Columns: plant name, state, county, balancing authority, fuel type, nameplate capacity (MW), online date. | 305 |
| `eia860m_planned_nebraska.csv` | Planned new generation capacity — proposed additions. | 17 |
| `eia860m_retired_nebraska.csv` | Recently retired generators — reduces reserve margin. | 58 |
| `eia860m_canceled_or_postponed_nebraska.csv` | Canceled or postponed projects. | 3 |
| `avgprice_annual_nebraska.csv` | Average retail electricity price (cents/kWh) by sector (residential, commercial, industrial, transportation) for Nebraska, all years. | 50 |
| `avgprice_annual_national.csv` | Same, all states (3,603 rows). | — |
| `eia860m_latest.xlsx` | Raw EIA-860M workbook (9.6 MB). Sheets: Operating, Planned, Retired, Canceled or Postponed. | — |
| `market_mismatch_data_note.json` | Connects each dataset to specific O_j indicators in the paper. | — |

**Source:** EIA Form 860M archive (`https://www.eia.gov/electricity/data/eia860m/`), EIA average retail price file.

---

## Reproducing the data

```bash
# One-time setup
python -m venv data/.venv
source data/.venv/bin/activate     # Windows: data\.venv\Scripts\activate
pip install openpyxl xlrd

# Download everything (automated sources only)
cd data
python download_all.py
```

For datasets requiring manual steps (FEMA NRI, WRI Aqueduct, Census ACS, BLS QCEW), follow the instructions in the respective `MANUAL_DOWNLOAD_INSTRUCTIONS.txt` or `*_REQUIRED.txt` files.

---

## Coverage summary

| Risk variable | Dataset | Status |
|---|---|---|
| F_j | SEC EDGAR 10-K index | ✅ Downloaded |
| G_j | FEMA National Risk Index | ⚠️ Manual download |
| G_j | NOAA Storm Events 2021–2023 | ✅ Downloaded |
| R_res_j | EPA eGRID 2022 | ✅ Downloaded |
| R_res_j | WRI Aqueduct 4.0 | ⚠️ Manual download |
| R_res_j | EIA-860 plants & generators | ✅ Downloaded |
| R_res_j | EIA state generation & capacity | ✅ Downloaded |
| C_j | US Census ACS 5-Year (county) | ⚠️ Requires free API key |
| C_j | BLS LAUS (unemployment) | ✅ Downloaded |
| C_j | BLS QCEW (employment by industry) | ⚠️ Manual download |
| O_j | EIA-860M capacity additions/retirements | ✅ Downloaded |
| O_j | EIA retail electricity prices | ✅ Downloaded |
