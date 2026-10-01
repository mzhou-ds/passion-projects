"""Robust parallel download of the OFF bulk CSV via S3 range requests.

Splits the 1.27GB file into N chunks, downloads each with resume-on-failure,
then concatenates. Usage: python3 download_bulk.py
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor

import requests

URL = "https://openfoodfacts-ds.s3.eu-west-3.amazonaws.com/en.openfoodfacts.org.products.csv.gz"
OUT = "/tmp/off_products.csv.gz"
NCHUNKS = 16
UA = "MusingWithMike/1.0 (nutrition-research)"


def total_size():
    r = requests.head(URL, headers={"User-Agent": UA}, timeout=30, allow_redirects=True)
    return int(r.headers["Content-Length"])


def fetch_chunk(i, start, end):
    part = f"/tmp/off_part_{i:02d}"
    done = os.path.getsize(part) if os.path.exists(part) else 0
    while done < (end - start):
        try:
            h = {"User-Agent": UA, "Range": f"bytes={start + done}-{end - 1}"}
            with requests.get(URL, headers=h, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(part, "ab") as f:
                    for c in r.iter_content(1 << 20):
                        if c:
                            f.write(c)
                            done += len(c)
            break
        except Exception as e:  # noqa: BLE001
            print(f"chunk {i}: {e} — resuming at {done}", flush=True)
            time.sleep(5)
    print(f"chunk {i}: done ({done} bytes)", flush=True)


def main():
    size = total_size()
    print(f"total size: {size / 1e9:.2f} GB")
    step = size // NCHUNKS
    ranges = [(i * step, (i + 1) * step if i < NCHUNKS - 1 else size) for i in range(NCHUNKS)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(lambda t: fetch_chunk(*t),
                    [(i, s, e) for i, (s, e) in enumerate(ranges)]))
    with open(OUT, "wb") as out:
        for i in range(NCHUNKS):
            part = f"/tmp/off_part_{i:02d}"
            with open(part, "rb") as f:
                out.write(f.read())
            os.remove(part)
    print(f"assembled {OUT}: {os.path.getsize(OUT)} bytes")


if __name__ == "__main__":
    main()
