"""Fetch the ATUS 2003-2025 multi-year microdata (Activity, Who, Respondent).

BLS serves these from www.bls.gov/tus/data/datafiles/. Some networks get an
Akamai 403 from that host; if the direct download fails, download the three
zips in a regular browser from
https://www.bls.gov/tus/data/datafiles-0325.htm and drop them in data/raw/.

Files are ~120 MB total. Extracted CSVs land in data/raw/ and are git-ignored
(see the repo .gitignore conventions); this script is the refetch path.
"""
import pathlib
import sys
import urllib.request
import zipfile

BASE = "https://www.bls.gov/tus/data/datafiles/"
FILES = {
    "atusact-0325.zip": "atusact_0325",
    "atuswho-0325.zip": "atuswho_0325",
    "atusresp-0325.zip": "atusresp_0325",
    "atusrost-0325.zip": "atusrost_0325",
}
RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    for name, stem in FILES.items():
        dest = RAW / name
        if not dest.exists():
            print(f"downloading {name} ...")
            req = urllib.request.Request(BASE + name, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as f:
                    f.write(r.read())
            except Exception as e:  # noqa: BLE001
                print(f"FAILED {name}: {e}\nDownload it in a browser from "
                      "https://www.bls.gov/tus/data/datafiles-0325.htm instead.")
                return 1
        with zipfile.ZipFile(dest) as z:
            z.extractall(RAW)
        print(f"ok: {stem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
