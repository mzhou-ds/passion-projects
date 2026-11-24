"""01_fetch.py — download NHANES 2011-2014 exam files + NCHS linked mortality.

Sources (all public, no auth):
- NHANES XPT files: https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{2011|2013}/DataFiles/{FILE}.xpt
  (the old .../Nhanes/2011-2012/FILE.XPT path now returns a CDC 404 page)
- Public-use linked mortality files (follow-up through Dec 31, 2019):
  https://ftp.cdc.gov/pub/health_statistics/nchs/datalinkage/linked_mortality/
  NHANES_2011_2012_MORT_2019_PUBLIC.dat, NHANES_2013_2014_MORT_2019_PUBLIC.dat
  + SAS_ReadInProgramAllSurveys.sas (column layout)

Idempotent: skips files that already exist and are non-empty.
"""
import os
import urllib.request

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW, exist_ok=True)

XPT_2011 = ["MGX_G", "DEMO_G", "BMX_G", "BPX_G", "SMQ_G", "PAQ_G", "MCQ_G"]
XPT_2013 = ["MGX_H", "DEMO_H", "BMX_H", "BPX_H", "SMQ_H", "PAQ_H", "MCQ_H"]

URLS = {}
for f in XPT_2011:
    URLS[f"{f}.xpt"] = f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2011/DataFiles/{f}.xpt"
for f in XPT_2013:
    URLS[f"{f}.xpt"] = f"https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2013/DataFiles/{f}.xpt"
for f in ["NHANES_2011_2012_MORT_2019_PUBLIC.dat",
          "NHANES_2013_2014_MORT_2019_PUBLIC.dat",
          "SAS_ReadInProgramAllSurveys.sas"]:
    URLS[f] = ("https://ftp.cdc.gov/pub/health_statistics/nchs/datalinkage/"
               f"linked_mortality/{f}")

for name, url in URLS.items():
    path = os.path.join(RAW, name)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        print(f"skip {name} ({os.path.getsize(path):,} bytes)")
        continue
    print(f"fetch {name} ...")
    urllib.request.urlretrieve(url, path)
    print(f"  -> {os.path.getsize(path):,} bytes")
print("done.")
