"""
01_fetch.py - pull every raw input for The Canadian Discount.

Sources (all public, no API keys):
  - IMF World Economic Outlook via the DataMapper API
    (GDP per capita in current US$, GDP per capita at PPP, population,
     total GDP in current US$, real GDP growth; actuals + IMF forecasts)
  - FRED (St. Louis Fed) fredgraph CSV endpoint
    (World Bank constant-dollar GDP per capita, population growth,
     CAD per USD daily, WTI oil, BIS real house price indices,
     unemployment, and BEA state GDP + Census state population)
  - Statistics Canada WDS full-table CSVs
    36-10-0222 (provincial GDP, expenditure-based, current prices)
    17-10-0005 (population estimates by province)
  - This repo's 2026-09-24 build (same-grandparents-different-deal):
    harmonized diaspora income extracts from the 2021 Canadian Census
    (98-10-0331) and ACS 2023, reused with provenance noted in the output.

Outputs land in ../data/. Every fetch is defensive: a failed source is
logged and skipped, never silently replaced with invented numbers.
"""
import io
import json
import os
import time
import zipfile

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RAW = os.path.join(DATA, "raw")
os.makedirs(RAW, exist_ok=True)

S = requests.Session()
S.headers.update({"User-Agent": "musing-with-mike daily build (contact via github mzhou-ds)"})


def get_retry(url, timeout=60, tries=4):
    last = None
    for i in range(tries):
        try:
            r = S.get(url, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:  # proxy drops happen; back off and retry
            last = e
            time.sleep(3 * (i + 1))
    raise last


def fred(series_id, start="1999-01-01"):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start}"
    r = get_retry(url, timeout=30)
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = ["date", series_id]
    df["date"] = pd.to_datetime(df["date"])
    df[series_id] = pd.to_numeric(df[series_id], errors="coerce")
    return df.dropna()


# ---------------------------------------------------------------- IMF WEO
def fetch_imf():
    inds = ["NGDPDPC", "PPPPC", "LP", "NGDPD", "NGDP_RPCH"]
    url = "https://www.imf.org/external/datamapper/api/v1/" + "/".join(inds) + "/CAN/USA"
    r = get_retry(url, timeout=60)
    vals = r.json()["values"]
    rows = []
    for ind, by_country in vals.items():
        for ctry, series in (by_country or {}).items():
            if ctry not in ("CAN", "USA") or not series:
                continue
            for year, v in series.items():
                rows.append({"indicator": ind, "country": ctry, "year": int(year), "value": v})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DATA, "imf_weo.csv"), index=False)
    print(f"IMF: {len(df)} rows, years {df.year.min()}-{df.year.max()}")
    return df


# ---------------------------------------------------------------- FRED core
FRED_CORE = [
    "NYGDPPCAPKDCAN", "NYGDPPCAPKDUSA",   # GDP pc, constant 2015 US$ (World Bank)
    "SPPOPGROWCAN", "SPPOPGROWUSA",       # population growth % (World Bank)
    "DEXCAUS",                            # CAD per USD, daily
    "DCOILWTICO",                         # WTI crude, daily
    "QCAN628BIS", "QUSN628BIS",           # BIS real house price index, quarterly
    "LRUNTTTTCAM156S",                    # Canada unemployment, monthly
    "UNRATE",                             # US unemployment, monthly
]

STATES = ["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN",
          "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
          "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT",
          "VT","VA","WA","WV","WI","WY"]


def fetch_fred():
    out = {}
    for sid in FRED_CORE:
        try:
            out[sid] = fred(sid)
            print(f"FRED {sid}: {len(out[sid])} rows, last {out[sid].date.max().date()}")
        except Exception as e:
            print(f"FRED {sid}: FAILED {e}")
        time.sleep(0.15)
    core = None
    for sid, df in out.items():
        core = df if core is None else core.merge(df, on="date", how="outer")
    core.to_csv(os.path.join(DATA, "fred_core.csv"), index=False)

    # states: nominal GDP (millions $) and population (thousands).
    # Fetched in parallel: 102 sequential requests through the proxy
    # timed out in practice; 8 workers finish in about a minute.
    from concurrent.futures import ThreadPoolExecutor

    def one_state(st):
        try:
            m = fred(f"{st}NGSP", start="2018-01-01").merge(
                fred(f"{st}POP", start="2018-01-01"), on="date")
            m["state"] = st
            return m
        except Exception as e:
            print(f"state {st}: FAILED {e}")
            return None

    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = [r for r in ex.map(one_state, STATES) if r is not None]
    if rows:
        sdf = pd.concat(rows)
        sdf.to_csv(os.path.join(DATA, "fred_states.csv"), index=False)
        print(f"FRED states: {len(sdf)} rows, {sdf.state.nunique()} states")
    return out


# ---------------------------------------------------------------- StatCan
def statcan_table(table, keep):
    url = f"https://www150.statcan.gc.ca/n1/tbl/csv/{table}-eng.zip"
    r = get_retry(url, timeout=120)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = [n for n in z.namelist() if n.endswith(".csv") and "MetaData" not in n][0]
    chunks = []
    with z.open(name) as f:
        for chunk in pd.read_csv(f, chunksize=200_000, low_memory=False):
            chunks.append(keep(chunk))
    df = pd.concat(chunks)
    print(f"StatCan {table}: kept {len(df)} rows")
    return df


def fetch_statcan():
    def keep_gdp(df):
        m = (df["Prices"] == "Current prices") & \
            (df["Estimates"] == "Gross domestic product at market prices")
        return df.loc[m, ["REF_DATE", "GEO", "VALUE"]].rename(
            columns={"REF_DATE": "year", "GEO": "geo", "VALUE": "gdp_m_cad"})

    gdp = statcan_table("36100222", keep_gdp)
    gdp.to_csv(os.path.join(DATA, "statcan_prov_gdp.csv"), index=False)

    def keep_pop(df):
        m = (df["Gender"] == "Total - gender") & (df["Age group"] == "All ages")
        return df.loc[m, ["REF_DATE", "GEO", "VALUE"]].rename(
            columns={"REF_DATE": "year", "GEO": "geo", "VALUE": "pop"})

    pop = statcan_table("17100005", keep_pop)
    pop.to_csv(os.path.join(DATA, "statcan_prov_pop.csv"), index=False)


# ---------------------------------------------------------------- diaspora (reuse)
def fetch_diaspora():
    base = os.path.join(HERE, "..", "..", "..", "2026-09-24",
                        "same-grandparents-different-deal", "data")
    out = {"provenance": "Reused from this repo's 2026-09-24 build: StatCan 2021 Census "
                         "table 98-10-0331 (income reference year 2020) and US Census "
                         "ACS 2023 5-year (B20017D / B19013D via Census Reporter extracts)."}
    try:
        inc = pd.read_csv(os.path.join(base, "statcan_income_filtered.csv"))
        m = (inc["Generation status (4)"] == "Total - Generation status") & \
            (inc["Age (15B)"] == "25 to 54 years") & \
            (inc["Gender (3)"] == "Total - Gender") & \
            (inc["Highest certificate, diploma or degree (16)"].str.startswith("Total"))
        sub = inc[m]
        stats = {}
        for _, row in sub.iterrows():
            stats.setdefault(row["GEO"], {})[row["Income statistics (17)"]] = {
                "chinese": row["Chinese[4]"],
                "not_vismin": row["Not a visible minority[15]"],
            }
        out["canada_chinese_25_54"] = stats
        us = json.load(open(os.path.join(base, "us_indicators.json")))
        out["us"] = {k: us[k] for k in ["us_median_hh_asian", "us_medearn_asian",
                                        "us_median_hh_total", "us_medearn_total",
                                        "us_chinese_pop"]}
        metro = json.load(open(os.path.join(base, "us_metro.json")))
        out["us_metro_asian_hh"] = metro
        print("diaspora: OK", list(stats.keys()))
    except Exception as e:
        print(f"diaspora: FAILED {e}")
    json.dump(out, open(os.path.join(DATA, "diaspora.json"), "w"), indent=1)


if __name__ == "__main__":
    fetch_imf()
    fetch_fred()
    fetch_statcan()
    fetch_diaspora()
    print("fetch done")
