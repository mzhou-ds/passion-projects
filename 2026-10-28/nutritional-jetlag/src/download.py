"""Download NHANES dietary recall + demographics + body measures XPT files.

Cycles 2007-08 through 2017-18 (suffixes E-J). Files land in data/raw/.
The CDC site serves them from the Public/{start-year}/DataFiles path.
"""
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw")
os.makedirs(RAW, exist_ok=True)

CYCLES = {  # start year -> file suffix
    2007: "E",
    2009: "F",
    2011: "G",
    2013: "H",
    2015: "I",
    2017: "J",
}
FILES = ["DR1IFF", "DR2IFF", "DEMO", "BMX"]

BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{name}_{sfx}.xpt"


def main():
    for year, sfx in CYCLES.items():
        for name in FILES:
            fname = f"{name}_{sfx}.xpt"
            dest = os.path.join(RAW, fname)
            if os.path.exists(dest) and os.path.getsize(dest) > 100_000:
                print("skip", fname)
                continue
            url = BASE.format(year=year, name=name, sfx=sfx)
            print("get", url)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            print("  ->", os.path.getsize(dest) // 1_000_000, "MB")


if __name__ == "__main__":
    main()
