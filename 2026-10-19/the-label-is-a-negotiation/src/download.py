"""Download the USDA FoodData Central branded-food bulk CSVs (April 2025).

The full archive is ~440 MB compressed / ~3 GB raw. We keep only the three
files the analysis needs (branded_food.csv, food_nutrient.csv, food.csv for
descriptions, nutrient.csv for the codebook). Raw files are gitignored;
re-running this plus src/extract.py rebuilds data/products.parquet.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
URL = ("https://fdc.nal.usda.gov/fdc-datasets/"
       "FoodData_Central_branded_food_csv_2025-04-24.zip")
INNER = "FoodData_Central_branded_food_csv_2025-04-24"
KEEP = ["branded_food.csv", "food_nutrient.csv", "food.csv", "nutrient.csv"]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    zip_path = RAW / "branded.zip"
    if not zip_path.exists():
        subprocess.run(["curl", "-s", "-o", str(zip_path), "--max-time", "900", URL],
                       check=True)
    for name in KEEP:
        if not (RAW / name).exists():
            subprocess.run(["unzip", "-o", "-q", str(zip_path),
                            f"{INNER}/{name}", "-d", str(RAW)], check=True)
            (RAW / INNER / name).rename(RAW / name)
    try:
        (RAW / INNER).rmdir()
    except OSError:
        pass
    print("raw files ready in", RAW)

if __name__ == "__main__":
    main()
