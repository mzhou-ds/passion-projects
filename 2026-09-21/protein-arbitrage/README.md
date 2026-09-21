# The Protein Arbitrage: What 30 Grams Actually Costs in America

**One-line summary:** Dried beans ($0.50), chicken legs ($0.68), and eggs ($0.90) are the cheapest proteins in the U.S. grocery store. A Costco rotisserie chicken is cheaper per gram of protein than a raw chicken you cook yourself. And the price of protein has almost nothing to do with how much protein is in the food.

## The setup

Every fitness macro calculator tells you to eat 150g+ of protein a day. Nobody tells you what that costs. So I joined the two most authoritative public datasets in American food — the Bureau of Labor Statistics' Average Price Data (monthly, U.S. city average, via FRED) and the USDA's FoodData Central nutrition database — and priced 27 foods by the dollar cost of 30 grams of protein, roughly one scoop of whey.

## What I found

**1. The league table has a clear winner, and it's not close.**

Dried beans: **$0.50 per 30g protein**. Chicken legs: **$0.68**. Whole chicken: **$0.72**. Low-fat milk: **$0.87**. Eggs: **$0.90**. The prestige proteins — boneless chicken breast ($1.23), cheddar ($1.73), ground beef ($2.67), sirloin ($4.68) — cost 2–9x more per gram. The single most expensive "protein" in the store is yogurt at **$6.04 per 30g** — twelve times the cost of beans. (BLS tracks plain yogurt at $1.58 per 8oz; at 3.5g protein per 100g, the math is brutal.)

At 160g of protein a day, that's **$80/month** on beans vs **$196/month** on chicken breast vs **$749/month** on sirloin. Your protein source is a bigger budget decision than your rent increase.

**2. The rotisserie paradox: Costco sells cooked chicken for less than raw chicken costs.**

Costco's $4.99 rotisserie chicken (price unchanged since 2009, confirmed by 2026 reporting) works out to roughly **$0.54 per 30g of protein**. Buy a raw whole bird at the BLS national average ($2.01/lb) and roast it yourself: about **$0.88 per 30g** after bone and cooking loss. The cooked bird is ~40% cheaper than the raw one.

This is the loss-leader business model made visible in protein terms. Costco disclosed it was willing to eat $30–40M a year in margin to hold the $4.99 price (then-CFO Galanti, 2015), built a $450M poultry plant in Nebraska to control the supply chain, and sells ~157M birds a year. The chicken isn't the product — foot traffic is. For the shopper, the takeaway is simple: the cheapest animal protein in America is the one Costco loses money on.

**3. Eggs are the most volatile protein in America.**

Indexing each food's cost-per-30g to January 2020: eggs spiked to **3.3x** in early 2023 (avian flu) and **4.2x** in early 2025, then fell back. Every other protein stayed within roughly ±50% of its 2020 level the entire six years. If you meal-prep on eggs, your protein budget has a volatility problem no other food has. (Also: at $0.90/30g today, eggs are merely back to being a fair deal — the "cheap eggs" era is over.)

**4. You're not paying for protein. You're paying for the package.**

A hedonic regression on log(cost per 30g protein) — protein density, fat content, category, bone-in flag — explains 51% of price variation (R² = 0.51). The punchline: **protein density itself has essentially zero effect on price**. What matters is the category: pantry staples, eggs, poultry, and dairy are all dramatically cheaper than beef, holding nutrition constant. The market doesn't price the nutrient. It prices the animal, the cut, and the brand story around it. That is a mispricing, and it's the whole game: identical grams, wildly different dollars, for reasons that have nothing to do with the grams.

**5. The efficient frontier.**

Plotting cost against protein density (grams per 100 kcal), six foods are unbeaten on both axes: flour, dried beans, chicken legs, whole chicken, eggs, and chicken breast. Chicken breast is the density king (18.8g/100kcal) — that's what the premium buys you: protein without the calories, not protein without the cost. Everything else is dominated: there is always something cheaper *and* denser.

## Charts

- `charts/01_league_table.png` — cost per 30g protein for all 27 foods
- `charts/02_frontier.png` — efficient frontier with k-means value tiers
- `charts/03_protein_inflation.png` — protein-cost inflation since Jan 2020
- `charts/04_price_drivers.png` — hedonic regression: what drives protein prices

## Methods

1. `src/fetch_bls_prices.py` — pulls 36 BLS Average Price series (APU0000 + item code) from FRED's `fredgraph.csv` endpoint (no API key), 1980–Aug 2026. Saves `data/bls_prices_panel.csv`.
2. `src/build_table.py` — maps each BLS item to a USDA SR Legacy food (fdc_id), extracts protein/energy/fat per 100g, converts BLS pricing units to grams (lb = 453.6g, dozen large eggs = 600g, gallon milk = 3,899g at 1.03 g/ml, 8oz yogurt = 226.8g), computes cost per 30g protein. Saves `data/protein_table.csv`.
3. `src/analyze.py` — league table, k-means value tiers (from-scratch numpy implementation), Pareto frontier, inflation index, OLS hedonic regression (from-scratch), monthly budget table, rotisserie math. Saves charts + `output/`.

Dependencies: `pandas`, `numpy`, `matplotlib`, `requests` (see `requirements.txt`).

## Sources

- Prices: U.S. Bureau of Labor Statistics, Average Price Data, U.S. city average, via FRED (series APU0000xxxx), retrieved 2026-09-21. Latest observation: August 2026.
- Nutrition: USDA Agricultural Research Service, FoodData Central SR Legacy (April 2018), public domain.
- Costco $4.99 rotisserie: company statements and 2026 press coverage (Tasting Table; Medium, Sep 2026); Galanti 2015 margin comment widely reported.
- BLS item-code documentation: `ap.item` from BLS time-series flat files.

## Caveats (read these before citing a number)

- Prices are **national averages**; your city and store will differ. This is a ranking, not a shopping list.
- Bone-in items (chicken legs, whole chicken, pork chops) are priced per pound **including bone**, so their true protein cost is higher — but even assuming 30% bone, legs remain the cheapest meat protein. Flagged in `protein_table.csv`.
- BLS discontinued several series: tuna (Sep 2017), peanut butter (Dec 2017), frankfurters, bologna. Shown greyed-out with their last price, excluded from the current ranking.
- Round steak and sirloin nutrition use select/all-grades raw cuts (choice-grade raw wasn't in SR Legacy); protein differences are ~1g/100g.
- Ice cream is priced per half-gallon (volume); converted at 0.60 g/ml. It's a contrast item, not a protein recommendation.
- Milk by the gallon assumes 1.03 g/ml density. Eggs assume 50g per large egg.
