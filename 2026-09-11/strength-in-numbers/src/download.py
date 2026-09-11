"""Download the exact OpenPowerlifting revision used by this project.

Fetches the IPF-affiliate bulk CSV (revision 2026-09-05, published 2026-09-04)
into data/. ~68 MB download, ~328 MB unzipped.
"""
import os
import urllib.request
import zipfile

URL = ("https://openpowerlifting.gitlab.io/opl-csv/files/openipf-latest.zip")
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

dest = os.path.join(DATA, "openipf-latest.zip")
print(f"Downloading {URL} ...")
urllib.request.urlretrieve(URL, dest)
print(f"  saved {os.path.getsize(dest) / 1e6:.0f} MB")
with zipfile.ZipFile(dest) as z:
    z.extractall(DATA)
print("  extracted. Run: python3 src/prepare.py")
