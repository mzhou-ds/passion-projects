#!/usr/bin/env python3
"""Download ATUS 2023 microdata zips from BLS (verified 2026-11-11).

BLS sits behind Akamai and rejects bare curl requests (403). A full
Chrome header set gets through. Source page:
https://www.bls.gov/tus/data/datafiles-2023.htm
Run: python3 fetch_atus.py  (writes zips into data/)
"""
import subprocess
import sys
from pathlib import Path

URLS = {
    # from https://www.bls.gov/tus/data/datafiles-2023.htm (verified 2026-11-11)
    "atusact-2023": "https://www.bls.gov/tus/datafiles/atusact-2023.zip",
    "atuswho-2023": "https://www.bls.gov/tus/datafiles/atuswho-2023.zip",
    "atusresp-2023": "https://www.bls.gov/tus/datafiles/atusresp-2023.zip",
    "atuscps-2023": "https://www.bls.gov/tus/datafiles/atuscps-2023.zip",
    "atusintcodebk23": "https://www.bls.gov/tus/dictionaries/atusintcodebk23.pdf",
}

HEADERS = [
    "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "-H", "Accept-Language: en-US,en;q=0.9",
    "-H", "Accept-Encoding: gzip, deflate, br",
    "-H", "Sec-Fetch-Dest: document",
    "-H", "Sec-Fetch-Mode: navigate",
    "-H", "Sec-Fetch-Site: none",
]

DATA = Path(__file__).resolve().parent.parent / "data"

def main():
    missing = [k for k, v in URLS.items() if not v]
    if missing:
        print("Missing URLs for:", ", ".join(missing))
        print("Fill them in from https://www.bls.gov/tus/datafiles-2023.htm")
        sys.exit(2)
    for name, url in URLS.items():
        ext = ".pdf" if url.endswith(".pdf") else ".zip"
        out = DATA / f"{name}{ext}"
        print(f"Downloading {name} ...", flush=True)
        r = subprocess.run(
            ["curl", "-sL", "--http1.1", "--tlsv1.2"] + HEADERS +
            ["-o", str(out), url],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"  FAILED: {r.stderr[:200]}")
            continue
        size = out.stat().st_size
        head = out.read_bytes()[:2]
        kind = "PK zip" if head == b"PK" else ("PDF" if head == b"%P" else "NOT A ZIP/PDF (probably HTML error page)")
        print(f"  {size/1e6:.2f} MB, {kind}")

if __name__ == "__main__":
    main()
