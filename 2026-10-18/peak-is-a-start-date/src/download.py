#!/usr/bin/env python3
"""Download the OpenIPF bulk CSV (IPF affiliates) into data/. ~65 MB zip."""
import os, urllib.request, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
URL = "https://openpowerlifting.gitlab.io/opl-csv/files/openipf-latest.zip"
os.makedirs(DATA, exist_ok=True)
dest = os.path.join(DATA, "openipf-latest.zip")
if not os.path.exists(dest):
    urllib.request.urlretrieve(URL, dest)
    print("downloaded", dest)
with zipfile.ZipFile(dest) as z:
    z.extractall(DATA)
print("extracted to", DATA)
