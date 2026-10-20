"""Download NHANES laboratory + demographic files for the two cycles used.

Cycles: 2015-2016 (suffix I) and 2017-2018 (suffix J). Files needed carry the
nine PhenoAge inputs (Levine et al. 2018):
  albumin, alkaline phosphatase, creatinine   -> BIOPRO (standard biochemistry)
  glucose (fasting subsample)                 -> GLU
  hs-CRP                                      -> HSCRP
  lymphocyte %, MCV, RDW, WBC                 -> CBC
  age, sex                                    -> DEMO

Raw XPT files land in data/raw/ and are git-ignored (~10 MB total); this
script refetches them from CDC.
"""
import os
import urllib.request

BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{name}.XPT"
CYCLES = {2015: "I", 2017: "J"}
FILES = ["DEMO", "BIOPRO", "CBC", "HSCRP", "GLU"]

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")


def main():
    os.makedirs(RAW, exist_ok=True)
    for year, suffix in CYCLES.items():
        for name in FILES:
            fname = f"{name}_{suffix}.XPT"
            dest = os.path.join(RAW, fname)
            if os.path.exists(dest) and os.path.getsize(dest) > 10_000:
                print("cached", fname)
                continue
            url = BASE.format(year=year, name=fname[:-4])
            print("fetch", url)
            urllib.request.urlretrieve(url, dest)
    print("done ->", RAW)


if __name__ == "__main__":
    main()
