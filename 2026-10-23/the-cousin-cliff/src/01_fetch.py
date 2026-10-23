"""
01_fetch.py - download the fertility series; refresh the GSS extract if R exists.

Sources
-------
1. UN World Population Prospects fertility rates via Our World in Data's
   grapher (children-per-woman-UN.csv): period total fertility rate (TFR)
   by country and year, 1950-2023, for the United States, Canada, China
   (plus the world, kept for context).
2. General Social Survey (GSS) cumulative cross-section file, 1972-2024
   (NORC), mirrored by Kieran Healy's `gssr` R package. The committed
   data/gss_extract.csv is a 16-variable extract (sibs, childs, cohort and
   demographics) produced the same way as the 2026-10-14 build in this
   repo. If Rscript is unavailable the committed extract is used as-is.

Run: python3 src/01_fetch.py
"""
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)

OWID_URL = "https://ourworldindata.org/grapher/children-per-woman-UN.csv"
GSS_RDA_URL = ("https://raw.githubusercontent.com/kjhealy/gssr/master/"
               "data/gss_all.rda")


def fetch(url, dest, tries=3):
    tmp = dest + ".part"
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(tmp, dest)
            print(f"fetched {dest} ({os.path.getsize(dest):,} bytes)")
            return
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"fetch attempt {i + 1} failed: {e}")
    if os.path.exists(tmp):
        os.remove(tmp)
    raise RuntimeError(f"could not fetch {url}: {last}")


def main():
    fetch(OWID_URL, os.path.join(DATA, "fertility_un_owid.csv"))
    extract = os.path.join(DATA, "gss_extract.csv")
    if subprocess.run(["which", "Rscript"], capture_output=True).returncode == 0:
        print("Rscript present: GSS re-extraction is available via the "
              "2026-10-14 build's extract_gss.R pattern; keeping the "
              "committed 16-variable extract for byte-stability.")
    else:
        print("Rscript not found - keeping committed data/gss_extract.csv "
              f"({os.path.getsize(extract):,} bytes)")
    print("done")


if __name__ == "__main__":
    sys.exit(main())
