"""Stream the OFF bulk CSV export, reservoir-sample US products.

Reads /tmp/off_products.csv.gz (1.27GB, tab-separated), keeps a uniform
reservoir of US products with usable NOVA/Nutri-Score data, and writes
/tmp/off_us_sample.tsv with only the columns we need.

Usage: python3 01b_sample_bulk.py   (run after the bulk download finishes)
"""
import csv
import gzip
import io
import os
import random
import sys

csv.field_size_limit(sys.maxsize)

# Full bulk export assembled via parallel range requests (see download_bulk.py).
SRC_PARTS = ["/home/hatch/workspace/tmp_off/off_products.csv.gz"]
OUT = "data/off_us_sample.tsv"
RESERVOIR = 60000

WANT = [
    "code", "product_name", "brands", "categories_tags", "labels_tags",
    "nutriscore_grade", "nova_group",
    "energy-kcal_100g", "proteins_100g", "carbohydrates_100g", "sugars_100g",
    "fat_100g", "saturated-fat_100g", "fiber_100g", "sodium_100g", "salt_100g",
]
NUTRIENT_COLS = WANT[7:]


class _Chain(io.RawIOBase):
    """Chain part files into one logical byte stream (no extra disk)."""
    def __init__(self, paths):
        self._files = [open(p, "rb") for p in paths]
        self._i = 0

    def readable(self):
        return True

    def readinto(self, b):
        while self._i < len(self._files):
            n = self._files[self._i].readinto(b)
            if n:
                return n
            self._files[self._i].close()
            self._i += 1
        return 0


def main():
    random.seed(42)
    reservoir = []
    n_us = n_eligible = n_rows = 0
    stream = _Chain(SRC_PARTS)
    try:
        with gzip.open(stream, mode="rt", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f, delimiter="\t")
            header = next(reader)
            idx = {c: header.index(c) for c in WANT}
            cidx = header.index("countries_tags")
            for row in reader:
                n_rows += 1
                if len(row) <= max(idx.values()):
                    continue
                if "en:united-states" not in (row[cidx] or ""):
                    continue
                n_us += 1
                vals = [row[idx[c]] for c in WANT]
                rec = dict(zip(WANT, vals))
                nova_ok = rec["nova_group"] in ("1", "2", "3", "4")
                nutri_ok = (rec["nutriscore_grade"] or "").strip().lower() in "abcde"
                filled = sum(1 for c in NUTRIENT_COLS if (rec[c] or "").strip())
                if not ((nova_ok or nutri_ok) and filled >= 3):
                    continue
                n_eligible += 1
                if len(reservoir) < RESERVOIR:
                    reservoir.append(rec)
                else:
                    j = random.randrange(n_eligible)
                    if j < RESERVOIR:
                        reservoir[j] = rec
                if n_eligible % 20000 == 0:
                    print(f"rows={n_rows:,} US={n_us:,} eligible={n_eligible:,}", flush=True)
    except EOFError:
        pass  # truncated gzip stream: stop at the last complete row
    print(f"rows scanned: {n_rows:,}; US: {n_us:,}; eligible: {n_eligible:,}")

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=WANT, delimiter="\t")
        w.writeheader()
        w.writerows(reservoir)
    print(f"US products scanned: {n_us:,}; eligible: {n_eligible:,}; sampled: {len(reservoir):,} -> {OUT}")


if __name__ == "__main__":
    main()
