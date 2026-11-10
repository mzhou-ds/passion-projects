"""Google Trends pulls for the poppy gap.

Requires pytrends (pip install pytrends). Run with a venv if your system
python is externally managed. Google rate-limits aggressively: sleeps are
deliberate, and a 429 means wait an hour, not retry in a loop.

Queries (all 2025-10-15 .. 2025-11-20, the remembrance window):
  1. "remembrance day" vs "veterans day" in Canada
  2. same pair in the United States
  3. "veterans day sale" vs "remembrance day sale" in the United States
  4. same pair in Canada
Outputs: data/trends_day_terms_{ca,us}.csv, data/trends_sale_terms_{us,ca}.csv
(Google's 0-100 index within each query; not comparable across queries.)
"""
import time

import pandas as pd
from pytrends.request import TrendReq

WINDOW = "2025-10-15 2025-11-20"


def pull(kw_list, geo, path):
    pytrends = TrendReq(hl="en-US", tz=480)
    pytrends.build_payload(kw_list, cat=0, timeframe=WINDOW, geo=geo, gprop="")
    df = pytrends.interest_over_time()
    df = df.drop(columns=[c for c in df.columns if c == "isPartial"], errors="ignore")
    df.to_csv(path)
    print(f"wrote {path}: {len(df)} rows")
    time.sleep(25)


def main():
    pull(["remembrance day", "veterans day"], "CA", "data/trends_day_terms_ca.csv")
    pull(["remembrance day", "veterans day"], "US", "data/trends_day_terms_us.csv")
    pull(["veterans day sale", "remembrance day sale"], "US", "data/trends_sale_terms_us.csv")
    pull(["veterans day sale", "remembrance day sale"], "CA", "data/trends_sale_terms_ca.csv")


if __name__ == "__main__":
    main()
