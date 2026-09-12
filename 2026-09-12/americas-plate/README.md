# The Protein Atlas — what 7,756 USDA foods reveal about protein, leucine, and nutrient density

**Musing with Mike · daily build #5 · 2026-09-12 · topic: nutrition**

"High protein" is on every label, but protein *per calorie* is what matters when
you're trying to hit 150 g of protein without blowing past your calorie budget.
This project ranks all 7,756 foods in the USDA's reference database by protein
density, tests the protein-leverage hypothesis in food-composition data, maps
leucine (the muscle-protein-synthesis trigger) across the food supply, scores
every food on overall nutrient density, and names the sugar bombs, sodium traps,
and fiber gaps — plus a special look at where soy foods land against meat.

**Try it:** open [`explorer.html`](explorer.html) — search any food to see its
protein-density percentile, leucine content, macro split, and nutrient-density
score against all 7,756 foods.

## Findings

**1. Fish owns the protein-density leaderboard.**
Excluding protein powders, the most protein-dense real foods are cod, shrimp,
and tuna at **~24 g protein per 100 kcal** — 12 of the top 18 are fish or
shellfish. The single densest entry overall is soy protein isolate (27.5 g/100
kcal). Fun trap: dry gelatin ranks #3 by density but is an *incomplete*
protein (no tryptophan) — density is not quality. See `charts/02_*`.

**2. By category, the median vegetable beats the median fast food.**
Median g protein / 100 kcal: finfish & shellfish **16.9**, beef **13.7**,
poultry **13.6**, lamb/game **13.1**, pork **13.0** — then a cliff: legumes
**6.6**, dairy & egg **6.3**, vegetables **5.1** vs. fast food **4.6** and
sweets **1.1**. The median food in the whole database delivers just **4.6 g**
per 100 kcal. See `charts/01_*`.

**3. Protein leverage is real — once you compare like with like.**
Across all 7,530 foods, the share of calories from protein barely predicts
energy density (Spearman **r = −0.22**) because water content dominates. But
within protein-food categories (meat, fish, dairy, legumes; n=3,149) the
leverage pattern is unmistakable: **r = −0.54** — more protein per calorie
reliably means fewer calories per bite. See `charts/03_*`.

**4. Leucine: 140 calories of lean beef flips the muscle-building switch.**
~3 g of leucine per meal maximally triggers muscle protein synthesis. Lean
top-round beef delivers **2,145 mg leucine / 100 kcal** — just **140 kcal** to
hit 3 g; haddock is right behind at 143 kcal. The plant outlier: spirulina at
1,958 mg/100 kcal (153 kcal to 3 g). See `charts/04_*`.

**5. Nutrient density is a leafy-green landslide.**
Using an NRF-style score (9 nutrients to encourage minus sugar, sodium, and
saturated fat, per 100 kcal): raw spinach scores **571**, and leafy greens
sweep the entire top 25. Category medians: vegetables **124**, legumes **59**,
breakfast cereals **56** (fortification is doing heavy lifting), fish **48** —
vs. sweets **−23** and fats/oils **−13**. See `charts/05_*`.

**6. Sugar bombs and sodium traps.**
The worst offenders pack ~28 g sugar per 100 kcal — essentially 100% of their
calories from sugar (fruit punch drinks, syrups, jam); the median food has
**0.8 g**. Sodium per 100 kcal by category median: soups/sauces/gravies **726
mg**, sausages & luncheon meats **373 mg**, restaurant and fast foods **~220
mg**. See `charts/06_*`.

**7. The fiber gap is stark.**
Only **17.3%** of foods deliver ≥3 g fiber per 100 g, and the median food has
essentially **zero** fiber per 100 kcal. Legumes and breakfast cereals are the
lone bright spots. See `charts/08_*`.

**8. Soy vs. meat: closer than the memes suggest.**
Median g protein / 100 kcal: seitan **20.3** (beats chicken breast at 14.2),
tofu **11.1**, tempeh **10.4**, edamame **10.1**, natto **9.2** vs. salmon
**14.8** and lean beef **13.7**. Soy lands at ~75% of meat's protein density —
but only ~65–70% of its leucine density (tofu 816 vs. salmon 1,209 mg/100
kcal), so plant-based lifters need a bit more total protein to match the
leucine trigger. See `charts/07_*`.

## Data

- **Source:** USDA FoodData Central, **SR Legacy** release 2018-04 (the final
  Standard Reference release) — 7,793 foods, 644,125 nutrient records.
  Downloaded from https://fdc.nal.usda.gov/download-datasets.
- **License:** public domain (U.S. Government work).
- **Scope note:** SR Legacy is a *reference* database of generic foods
  ("Chicken, breast, roasted"), not branded products — values are compositional
  averages, and the release is frozen at 2018.

## Methods

1. `src/download.py` — fetches the SR Legacy CSV zip into `data/`.
2. `src/prepare.py` — pivots the long nutrient table to one row per food with
   25 nutrients of interest (per 100 g), attaches the 25 food categories, and
   writes `output/foods_wide.csv`.
3. `src/analyze.py` — per-100-kcal derivations (protein, fiber, sugar,
   saturated fat, sodium, leucine); NRF-style nutrient-density score (9
   beneficial nutrients as capped %DV minus sugar/sodium/sat-fat %DV, per 100
   kcal, FDA Daily Values); protein-leverage correlations; category medians;
   the soy-vs-meat spotlight. Writes the derived tables, `findings.txt`, and
   `summary.json`.
4. `src/charts.py` — the eight charts in `charts/`.
5. `src/explorer.py` — builds the interactive search explorer.

`output/` holds the derived tables (leaderboards, category summaries,
`summary.json`). The raw download and the two large intermediate matrices are
intentionally not committed (see `.gitignore`); run the pipeline above to
reproduce everything from scratch.

## Caveats

- Per-100-kcal rankings favor very lean foods. Leaderboards use a 25 kcal/100 g
  floor (excludes ~0 kcal drinks where trace protein explodes the ratio) and
  exclude spices/herbs, whose serving sizes make the metric meaningless.
- Protein isolate can exceed 25 g/100 kcal because soy protein's Atwater energy
  factor is below 4 kcal/g — the ratio uses labeled kcal, not 4×protein.
- NRF adaptation: folate stands in for vitamin E (sparse in this release);
  missing nutrient values are treated as 0, which is conservative.
- This is food *composition*, not dietary *intake* — it describes foods, not
  what anyone actually eats.

## Layout

```
2026-09-12/americas-plate/
├── README.md            — this file
├── explorer.html        — interactive "how protein-dense is this food?" search
├── charts/              — 8 PNG charts
├── output/              — derived CSV tables + summary.json + findings.txt
├── src/                 — download / prepare / analyze / charts / explorer
└── data/                — raw download (not committed; see src/download.py)
```
