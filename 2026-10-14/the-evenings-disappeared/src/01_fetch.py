"""
01_fetch.py - download the two source datasets and build data/gss_extract.csv.

Sources
-------
1. General Social Survey (GSS) cumulative cross-section file, 1972-2024
   (NORC at the University of Chicago), as mirrored by Kieran Healy's
   `gssr` R package (GitHub: kjhealy/gssr, file data/gss_all.rda, ~23 MB).
   The committed data/gss_extract.csv is a 48-variable extract of that file,
   produced by src/extract_gss.R (requires R). If R is unavailable the
   committed extract is used as-is and this step is a no-op for the GSS.
2. Our World in Data's ATUS extract, "time spent with relationships by age"
   (American Time Use Survey, pooled diary years), CSV from the OWID
   grapher: time-spent-with-relationships-by-age-us.

Run: python3 src/01_fetch.py
"""
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)

GSS_RDA_URL = ("https://raw.githubusercontent.com/kjhealy/gssr/master/"
               "data/gss_all.rda")
OWID_URL = ("https://ourworldindata.org/grapher/"
            "time-spent-with-relationships-by-age-us.csv")


def fetch(url, dest, tries=3):
    """Download to a temp file and atomically replace dest, so a network
    failure mid-download can never corrupt the committed copy."""
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
        except Exception as e:  # noqa: BLE001 - retry any transport error
            last = e
            print(f"fetch attempt {i + 1} failed: {e}")
    if os.path.exists(tmp):
        os.remove(tmp)
    raise RuntimeError(f"could not fetch {url}: {last}")


def main():
    fetch(OWID_URL, os.path.join(DATA, "atus_time_by_age_owid.csv"))

    extract = os.path.join(DATA, "gss_extract.csv")
    rda = os.path.join(DATA, "gss_all.rda")
    if subprocess.run(["which", "Rscript"], capture_output=True).returncode == 0:
        fetch(GSS_RDA_URL, rda)
        # extract_gss.R uses paths relative to the working directory,
        # so run it with cwd=data/ where the .rda was just downloaded.
        script = os.path.join(HERE, "extract_gss.R")
        subprocess.run(["Rscript", script], cwd=DATA, check=True)
        os.remove(rda)
        print(f"regenerated {extract}")
    else:
        print("Rscript not found - keeping committed data/gss_extract.csv "
              f"({os.path.getsize(extract):,} bytes)")
    print("done")


if __name__ == "__main__":
    sys.exit(main())
