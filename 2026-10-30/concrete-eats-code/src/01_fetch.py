"""Fetch annual XBRL facts from SEC EDGAR companyfacts (public, no key).
Companies: MSFT, Alphabet, Meta, Amazon, NVIDIA.
Tags: revenue, R&D, capex (payments for PP&E), depreciation.
Annual rows only: form 10-K, fp FY, latest filing per fiscal year.
Saves data/edgar_annual.csv + data/edgar_raw.json (audit trail).
SEC requires a descriptive User-Agent; respects rate limits with sleep.
"""
import json, time, requests, pandas as pd, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data")
os.makedirs(OUT, exist_ok=True)

# Amazon is deliberately EXCLUDED: its filings carry no standard R&D tag
# (it reports "technology and content" under a non-standard mapping) and its
# capex mixes fulfillment warehouses with data centers, so it would corrupt
# a hyperscaler data-center comparison. The exclusion is documented in the
# README rather than papered over with a proxy.
COMPANIES = {
    "MSFT": 789019, "GOOGL": 1652044, "META": 1326801,
    "NVDA": 1045810,
}
REV_TAGS = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
            "SalesRevenueNet", "SalesRevenueGoodsNet"]
RD_TAGS = ["ResearchAndDevelopmentExpense"]
CAPEX_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment"]
DEPR_TAGS = ["DepreciationDepletionAndAmortization", "Depreciation"]

# Per-company tag overrides (same line item, different XBRL tag).
OVERRIDES = {"NVDA": {"capex": ["PaymentsToAcquireProductiveAssets"]}}

HEADERS = {"User-Agent": "MusingWithMike research mzhou-ds@research.example",
           "Accept-Encoding": "gzip, deflate", "Host": "data.sec.gov"}

def annual_series(facts, tags):
    """Union across candidate tags, keyed by period end date.

    Issuers switch XBRL tags mid-history and even skip a year on one tag
    (Alphabet reported 2022 revenue only under
    RevenueFromContractWithCustomerExcludingAssessedTax, not Revenues).
    Picking one tag therefore drops real years. Instead, merge every
    candidate tag: for each end date keep the latest-filed entry, with
    earlier-listed tags winning ties (values agree when both report).
    """
    best = {}  # end -> (entry, tag)
    for t in tags:
        if t not in facts["us-gaap"]:
            continue
        for e in facts["us-gaap"][t]["units"].get("USD", []):
            if e.get("form") != "10-K" or e.get("fp") != "FY":
                continue
            end = e.get("end")
            if end is None or "val" not in e:
                continue
            if end not in best or e.get("filed", "") > best[end][0].get("filed", ""):
                best[end] = (e, t)
    return ",".join(sorted({t for _, t in best.values()})), {k: v[0] for k, v in best.items()}

rows, raw = [], {}
for ticker, cik in COMPANIES.items():
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    d = r.json()
    raw[ticker] = {"entityName": d["entityName"], "cik": d["cik"]}
    facts = d["facts"]["us-gaap"]
    series = {}
    for name, tags in [("revenue", REV_TAGS), ("rnd", RD_TAGS),
                       ("capex", CAPEX_TAGS), ("depr", DEPR_TAGS)]:
        tags = OVERRIDES.get(ticker, {}).get(name, tags)
        tag, best = annual_series(d["facts"], tags)
        series[name] = best
        raw[ticker][name + "_tag"] = tag
    ends = sorted(set(series["revenue"]) & set(series["rnd"]) & set(series["capex"]))
    for end in ends:
        rows.append({
            "ticker": ticker,
            "period_end": end,
            "cal_year": int(end[:4]),
            "revenue": series["revenue"][end]["val"] / 1e9,
            "rnd": series["rnd"][end]["val"] / 1e9,
            "capex": series["capex"][end]["val"] / 1e9,
            "depr": (series["depr"][end]["val"] / 1e9) if end in series["depr"] else None,
        })
    print(ticker, d["entityName"], "periods:", min(ends), "-", max(ends), "n=", len(ends))
    time.sleep(0.25)

df = pd.DataFrame(rows).sort_values(["ticker", "cal_year"])
df.to_csv(os.path.join(OUT, "edgar_annual.csv"), index=False)
json.dump(raw, open(os.path.join(OUT, "edgar_raw.json"), "w"), indent=1)
print(df.groupby("ticker")["cal_year"].agg(["min", "max", "count"]))
print("saved", len(df), "rows")
