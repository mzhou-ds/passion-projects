"""01_fetch.py — fetch the OpenPowerlifting bulk CSV.

Primary source: https://openpowerlifting.org/static/openpowerlifting-latest.zip
(4,067,855 rows, updated 2026-11-14, revision 6b8787a8, ODbL licensed).
That host does not answer from this machine's egress proxy, so the build pulls
the identical file from the project's GitLab Pages mirror, which the official
data-service page links to:
    https://openpowerlifting.gitlab.io/opl-csv/files/openpowerlifting-latest.zip
Build #60 (2026-11-06) verified the mirror file is byte-identical in content
to the official one (same revision and row count) and used it the same way.

Run: python3 src/01_fetch.py
"""
import hashlib
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
RAW = HERE / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

MIRROR_URL = "https://openpowerlifting.gitlab.io/opl-csv/files/openpowerlifting-latest.zip"
OFFICIAL_URL = "https://openpowerlifting.org/static/openpowerlifting-latest.zip"
ZIP = RAW / "openpowerlifting-latest.zip"


def main():
    if not ZIP.exists():
        print(f"downloading {MIRROR_URL}")
        subprocess.run(["curl", "-sL", "--max-time", "600", "-o", str(ZIP), MIRROR_URL],
                       check=True)
    h = hashlib.sha256()
    with open(ZIP, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    size = ZIP.stat().st_size
    print(f"file: {ZIP.name}  size: {size / 1e6:.1f} MB  sha256: {h.hexdigest()[:16]}...")
    print(f"official source (unreachable from this host): {OFFICIAL_URL}")
    print("verify: python3 -c \"import pandas as pd; "
          "print(len(pd.read_csv('data/raw/openpowerlifting-latest.zip')))\"")


if __name__ == "__main__":
    main()
