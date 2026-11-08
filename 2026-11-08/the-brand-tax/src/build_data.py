"""Build the curated products table for The Brand Tax (build #62).

Reads the raw Meta Catalog search results in data/raw/ and joins them to a
hand-verified spec. Every row's servings-per-container and dose-per-serving
was verified against the product's own label (brand site, retailer listing,
or the NIH Dietary Supplement Label Database) on 2026-11-08. Prices are the
catalog prices fetched the same day; where a sale price was listed it is
used and flagged.

Trial doses (the dose the evidence actually used):
  creatine       5,000 mg/day   Kreider et al. 2017, JISSN position stand (3-5 g/day maintenance)
  magnesium      400 mg elemental/day   NIH ODS RDA for adult men (400-420 mg)
  vitamin D3     2,000 IU/day   VITAL trial dose (Manson et al. 2019, NEJM)
  omega-3        1,000 mg EPA+DHA/day   AHA / standard supplement dose
  zinc           15 mg/day   common trial dose (e.g. Prasad et al.); RDA is 11 mg
  NR             300 mg/day   Trammell et al. 2016; Tru Niagen's clinically studied dose

Key unit rule: magnesium is counted as ELEMENTAL mg (what the label's
"magnesium (as magnesium glycinate)" line states), and omega-3 as EPA+DHA
mg, not total fish-oil mg. NR in Thorne ResveraCel is 415 mg of the
hydrogen-malate salt, equivalent to ~300 mg NR (per Thorne's own
reformulation note and independent label reads).
"""
import json
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# spec: (raw_file, product_id, compound, form, tier, servings, dose_per_serving,
#        dose_unit, gummies_per_serving, notes)
SPEC = [
    # ---- creatine, trial dose 5,000 mg/day ----
    ("creatine.json", "26951378707871183", "creatine", "powder", "bulk", 100, 5000, "mg", None, "500 g bag; label: 2 tsp (about 5 g) per serving, 100 servings"),
    ("creatine.json", "27495906640085152", "creatine", "powder", "bulk", 100, 5000, "mg", None, "500 g; listing states 5 g per serving"),
    ("creatine.json", "27670445599254100", "creatine", "powder", "premium", 90, 5000, "mg", None, "Thorne label: 1 scoop, 5 g creatine monohydrate, 90 servings"),
    ("creatine.json", "27583406737938956", "creatine", "gummy", "premium", 30, 5000, "mg", 4, "Legion: 4-gummy serving, 5 g creatine"),
    ("creatine.json", "35012709518373702", "creatine", "gummy", "premium", 15, 4500, "mg", 3, "Create: 1.5 g per gummy, 3 per serving = 4.5 g; 45 ct"),
    ("creatine.json", "28602459716013373", "creatine", "gummy", "mainstream", 35, 5000, "mg", 3, "ON: 3 gummies = 5 g; 105 ct"),
    ("creatine.json", "27795348826794647", "creatine", "gummy", "mainstream", 24, 5000, "mg", 5, "Swanson: 1 g per gummy, 120 ct; serving = 5 gummies"),
    ("creatine.json", "28797959076474813", "creatine", "gummy", "mainstream", 20, 5000, "mg", 5, "MTN OPS: 1 g per gummy, 100 ct; serving = 5 gummies"),
    ("creatine.json", "25437527232590064", "creatine", "gummy", "premium", 30, 3000, "mg", 3, "MaryRuth's: 3 g per serving (3 gummies); 90 ct"),
    # ---- magnesium glycinate, trial dose 400 mg ELEMENTAL/day ----
    ("magnesium.json", "28736356072627757", "magnesium", "capsule", "premium", 180, 120, "mg", None, "Pure Encapsulations: 120 mg elemental Mg per capsule, 180 ct"),
    ("magnesium.json", "24624527723857933", "magnesium", "powder", "premium", 60, 200, "mg", None, "Thorne label: 1 scoop, 200 mg Mg as bisglycinate, 60 servings"),
    ("magnesium.json", "28194448776859674", "magnesium", "gummy", "mainstream", 20, 100, "mg", 2, "Nature Made: 100 mg per 2-gummy serving; 40 gummies"),
    ("magnesium.json", "27020353167650773", "magnesium", "gummy", "mainstream", 30, 100, "mg", 2, "Nature's Bounty: 100 mg per 2-gummy serving; 60 ct"),
    # ---- vitamin D3, trial dose 2,000 IU/day ----
    ("vitamind.json", "5114481811984293", "vitamin_d3", "softgel", "bulk", 120, 2000, "IU", None, "NOW D-3 2000 IU, 120 softgels"),
    ("vitamind.json", "3361755723936912", "vitamin_d3", "softgel", "bulk", 240, 2000, "IU", None, "NOW D-3 2000 IU, 240 softgels"),
    ("vitamind.json", "10021158474668679", "vitamin_d3", "softgel", "bulk", 250, 2000, "IU", None, "Piping Rock D3 2000 IU, 250 softgels"),
    ("vitamind.json", "27502794766022110", "vitamin_d3", "softgel", "mainstream", 90, 2000, "IU", None, "Nature Made D3 2000 IU softgels, 90 ct"),
    ("vitamind.json", "27547901801469684", "vitamin_d3", "capsule", "premium", 60, 5000, "IU", None, "Thorne D-5,000: 5,000 IU per capsule, 60 servings"),
    ("vitamind.json", "5853698038037050", "vitamin_d3", "gummy", "mainstream", 45, 2000, "IU", 2, "Nature Made D3 gummies: 2,000 IU per 2-gummy serving; 90 ct"),
    ("vitamind.json", "5236716186410406", "vitamin_d3", "gummy", "premium", 35, 2000, "IU", 2, "MegaFood D3 gummies: 2,000 IU per 2-gummy serving; 70 ct"),
    # ---- omega-3, trial dose 1,000 mg EPA+DHA/day ----
    ("omega3.json", "24621595890849805", "omega3", "softgel", "bulk", 500, 300, "mg", None, "NOW: 180 EPA + 120 DHA = 300 mg EPA+DHA per softgel; 500 ct"),
    ("omega3.json", "27744073845202837", "omega3", "softgel", "bulk", 90, 300, "mg", None, "21st Century: 180 EPA + 120 DHA per softgel; 90 ct"),
    ("omega3.json", "25992141953815812", "omega3", "softgel", "premium", 60, 700, "mg", None, "Nootropics Depot: 400 EPA + 300 DHA per softgel; 60 ct"),
    ("omega3.json", "8960210133990553", "omega3", "softgel", "premium", 30, 1100, "mg", 2, "Nordic Ultimate Omega: 650 EPA + 450 DHA per 2-softgel serving; 60 ct"),
    ("omega3.json", "27804465129190781", "omega3", "softgel", "premium", 90, 695, "mg", None, "Thorne Super EPA label: 425 EPA + 270 DHA per gelcap; 90 ct"),
    ("omega3.json", "27953476147624581", "omega3", "softgel", "premium", 30, 1000, "mg", None, "Metagenics EPA-DHA 1000: 1,000 mg EPA+DHA per softgel; 30 ct"),
    ("omega3.json", "27779739841686699", "omega3", "gummy", "mainstream", 45, 57, "mg", 2, "Nature Made fish oil gummies: 57 mg EPA+DHA per 2-gummy serving; 90 ct"),
    # ---- zinc picolinate, trial dose 15 mg/day ----
    ("zinc.json", "4764875483635868", "zinc", "capsule", "bulk", 120, 50, "mg", None, "NOW Zinc Picolinate 50 mg, 120 veg caps"),
    ("zinc.json", "3276467372479094", "zinc", "capsule", "bulk", 60, 50, "mg", None, "NOW Zinc Picolinate 50 mg, 60 veg caps"),
    ("zinc.json", "37739401059036718", "zinc", "capsule", "premium", 60, 15, "mg", None, "Thorne Zinc Picolinate 15 mg, 60 caps"),
    ("zinc.json", "29878097008471824", "zinc", "capsule", "premium", 180, 30, "mg", None, "Thorne Zinc Picolinate 30 mg, 180 caps"),
    ("zinc.json", "29186195950986088", "zinc", "gummy", "mainstream", 35, 30, "mg", 2, "Nature's Bounty zinc gummies: 15 mg per gummy, 2 per serving; 70 ct"),
    ("zinc.json", "3974442429319751", "zinc", "gummy", "mainstream", 120, 11, "mg", 1, "Nature's Way zinc gummies: 11 mg per 1-gummy serving; 120 ct"),
    ("zinc.json", "27791830163814443", "zinc", "gummy", "mainstream", 60, 15, "mg", 1, "Trace zinc gummies: 15 mg per gummy; 60 ct"),
    # ---- nicotinamide riboside, trial dose 300 mg/day ----
    ("nr.json", "27879901401644073", "nr", "capsule", "brand", 30, 300, "mg", None, "Tru Niagen 300 mg, 30 caps"),
    ("nr.json", "24041108508888446", "nr", "capsule", "brand", 90, 300, "mg", None, "Tru Niagen 300 mg, 90 caps"),
    ("nr.json", "26679997195017506", "nr", "capsule", "brand", 120, 150, "mg", None, "Tru Niagen 150 mg, 120 ct; 2 caps = 300 mg"),
    ("nr.json", "26143839821891833", "nr", "capsule", "premium", 30, 300, "mg", None, "Life Extension NAD+ Cell Regenerator 300 mg, 30 caps"),
    ("nr.json", "24622172684057141", "nr", "capsule", "premium", 30, 100, "mg", None, "Life Extension NAD+ Cell Regenerator 100 mg, 30 caps"),
    ("nr.json", "24260141283569481", "nr", "capsule", "premium", 30, 300, "mg", None, "Thorne ResveraCel: 415 mg NR hydrogen malate per serving ~= 300 mg NR; 30 servings"),
]

TRIAL_DOSE = {
    "creatine": (5000, "mg"),
    "magnesium": (400, "mg"),
    "vitamin_d3": (2000, "IU"),
    "omega3": (1000, "mg"),
    "zinc": (15, "mg"),
    "nr": (300, "mg"),
}

# The catalog sometimes records the retailer as the brand, or no brand at
# all. These overrides come from the product name / label itself.
BRAND_OVERRIDE = {
    "28194448776859674": "Nature Made",
    "27744073845202837": "21st Century",
    "37739401059036718": "Thorne",
    "29186195950986088": "Nature's Bounty",
    "27791830163814443": "Trace",
    "24041108508888446": "Tru Niagen",
    "27502794766022110": "Nature Made",
}


def main():
    rows = []
    for fname, pid, compound, form, tier, servings, dose, unit, gummies_per_serving, notes in SPEC:
        raw = json.loads((RAW / fname).read_text())
        prod = next(p for p in raw["products"] if p["product_id"] == pid)
        price_raw = prod.get("sale_price") or prod.get("price")
        price = float(price_raw.replace("$", "").replace(",", "").strip())
        on_sale = bool(prod.get("sale_price"))
        url = prod.get("url", "")
        trial_dose, trial_unit = TRIAL_DOSE[compound]
        assert unit == trial_unit, (compound, unit, trial_unit)
        rows.append({
            "compound": compound,
            "brand": BRAND_OVERRIDE.get(pid, prod.get("brand") or "unknown"),
            "product": prod.get("name"),
            "form": form,
            "tier": tier,
            "price_usd": price,
            "on_sale": on_sale,
            "retailer": urlparse(url).netloc.replace("www.", ""),
            "url": url,
            "servings_per_container": servings,
            "dose_per_serving": dose,
            "dose_unit": unit,
            "gummies_per_serving": gummies_per_serving if gummies_per_serving is not None else pd.NA,
            "trial_dose": trial_dose,
            "trial_dose_unit": trial_unit,
            "verification_note": notes,
        })
    df = pd.DataFrame(rows)
    df["total_active"] = df["servings_per_container"] * df["dose_per_serving"]
    df["doses_per_container"] = df["total_active"] / df["trial_dose"]
    df["cost_per_trial_dose"] = df["price_usd"] / df["doses_per_container"]
    df["cost_per_month"] = df["cost_per_trial_dose"] * 30
    df["servings_per_day"] = df["trial_dose"] / df["dose_per_serving"]
    df["dose_gap_pct"] = 100 * df["dose_per_serving"] / df["trial_dose"]
    df.to_csv(ROOT / "data" / "products.csv", index=False)
    print(f"wrote {len(df)} products")
    print(df[["compound", "brand", "price_usd", "doses_per_container", "cost_per_trial_dose"]].to_string())


if __name__ == "__main__":
    main()
