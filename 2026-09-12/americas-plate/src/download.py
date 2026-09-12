"""Download the USDA FoodData Central SR Legacy release into data/.

Source: USDA FoodData Central, SR Legacy release 2018-04 (final release).
Public domain (U.S. Government work). No API key needed for the bulk CSV.
"""
import urllib.request
import zipfile
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(parents=True, exist_ok=True)

URL = "https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip"
ZIP = DATA / "FoodData_Central_sr_legacy_food_csv_2018-04.zip"
OUTDIR = DATA / "FoodData_Central_sr_legacy_food_csv_2018-04"


def main():
    if not ZIP.exists():
        print(f"Downloading {URL} ...")
        req = urllib.request.Request(URL, headers={"User-Agent": "MusingWithMike/1.0"})
        with urllib.request.urlopen(req, timeout=300) as r, open(ZIP, "wb") as f:
            f.write(r.read())
        print(f"  saved {ZIP.stat().st_size / 1e6:.1f} MB")
    else:
        print(f"Already have {ZIP.name} ({ZIP.stat().st_size / 1e6:.1f} MB)")
    if not OUTDIR.exists():
        print("Extracting ...")
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(DATA)
    print("Contents:", sorted(p.name for p in OUTDIR.glob("*.csv")))


if __name__ == "__main__":
    main()
