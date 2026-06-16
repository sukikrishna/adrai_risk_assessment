"""
SEC EDGAR filings index for major hyperscaler and data center companies.

Supports F_j (Financial / Opacity Risk) in the AI infrastructure risk framework.
Indicators: ownership intermediation, reliance on private markets, disclosure availability.
"""

import csv
import json
import time
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).parent

# CIK numbers for key hyperscalers and data center REITs cited in the paper
COMPANIES = {
    "Amazon.com Inc": "0001018724",
    "Microsoft Corp": "0000789019",
    "Alphabet Inc (Google)": "0001652044",
    "Meta Platforms Inc": "0001326801",
    "Digital Realty Trust Inc": "0001297996",
    "Equinix Inc": "0001101239",
    "Iron Mountain Inc": "0001020569",
    "CoreWeave Inc": "0002074662",
    "Oracle Corp": "0001341439",
    "NTT Global Data Centers": "0001043505",
}

HEADERS = {"User-Agent": "adrai-risk-research sukanyakrishna@g.harvard.edu"}


def get_company_submissions(cik: str) -> dict:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def extract_filings(data: dict, form_type: str = "10-K", count: int = 3) -> list:
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    descriptions = recent.get("primaryDocument", [])

    results = []
    for form, date, acc, doc in zip(forms, dates, accessions, descriptions):
        if form == form_type:
            acc_fmt = acc.replace("-", "")
            results.append({
                "form": form,
                "filing_date": date,
                "accession_number": acc,
                "filing_url": f"https://www.sec.gov/Archives/edgar/data/{int(data['cik'])}/{acc_fmt}/{doc}",
                "index_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={data['cik']}&type=10-K",
            })
        if len(results) >= count:
            break
    return results


def main():
    print("Downloading SEC EDGAR filing index for data center / hyperscaler companies...")
    rows = []

    for name, cik in COMPANIES.items():
        try:
            data = get_company_submissions(cik)
            company_name = data.get("name", name)
            filings = extract_filings(data)
            for f in filings:
                rows.append({
                    "company": company_name,
                    "cik": cik,
                    "form": f["form"],
                    "filing_date": f["filing_date"],
                    "accession_number": f["accession_number"],
                    "filing_url": f["filing_url"],
                    "index_url": f["index_url"],
                    "sic": data.get("sic", ""),
                    "sic_description": data.get("sicDescription", ""),
                    "state_of_incorporation": data.get("stateOfIncorporation", ""),
                })
            print(f"  {company_name}: {len(filings)} 10-K filings found")
            time.sleep(0.15)  # respect EDGAR rate limit (10 req/sec)
        except Exception as e:
            print(f"  {name} (CIK {cik}): ERROR - {e}")

    out_path = OUT_DIR / "edgar_filings_index.csv"
    if rows:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\nSaved {len(rows)} filing records to {out_path}")
    else:
        print("No records downloaded.")

    # Also save the full company submissions metadata
    print("\nDownloading company metadata (tickers, SIC codes)...")
    ticker_url = "https://www.sec.gov/files/company_tickers.json"
    req = urllib.request.Request(ticker_url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        tickers = json.loads(r.read())

    ticker_path = OUT_DIR / "company_tickers_all.json"
    with open(ticker_path, "w", encoding="utf-8") as f:
        json.dump(tickers, f, indent=2)
    print(f"Saved {len(tickers)} company tickers to {ticker_path}")


if __name__ == "__main__":
    main()
