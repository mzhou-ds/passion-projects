# Build #62 working notes — The Brand Tax (biohacking, 2026-11-08)

## Topic
biohacking, per rotation.json (`next` was biohacking).

## Novelty case (written before building)
Everyone knows supplements are marked up. Nobody had measured cost per *trial
dose* across the whole staple stack at once. The serving is the unit the
industry engineers: set it below the trial dose and the bottle looks cheap
while lasting a week at the real dose; shrink the dose into a gummy and the
price per gram explodes because a gummy can only hold so much active
ingredient. The measurement is cost per trial dose for 6 compounds x 40 real
products, plus the serving-size gap and three full stacks. Surprise for an
expert: the spread is 5x across stacks and 32x within a compound, and the
cheapest magnesium is a premium brand because its capsule is honestly dosed.

## Alternatives considered and rejected
- Epigenetic clock disagreement on the same blood (GEO methylation + clock
  computation): high effort, heavy data, risky in one run.
- Reference-range lottery across labs: scraping risk, and journalists have
  covered the outline.
- openFDA warning letters per compound: feasible but legalistic, less operator.
- Cold plunge price per degree: fun but thin next to this.
- The brand tax won: real price data available same-day via catalog search,
  marketplace/ops lens, clearly distinct from build #21 protein arbitrage
  (macronutrient cost per gram) and build #53 borrowed evidence (registry).

## Data
- 6 catalog searches (creatine, magnesium, vitamin D3, omega-3, zinc, NR),
  ~50 products each, fetched 2026-11-08. Raw JSONs in data/raw/.
- 40 products curated; every servings/dose figure verified against the
  product's own label: thorne.com (creatine 90x5g; Mg bisglycinate 60x200mg;
  Super EPA 90x695mg EPA+DHA), bulksupplements.com + NIH DSLD (creatine 5g
  serving, 100 servings/500g), naturemade.com (fish oil gummies 90ct, 57mg per
  2-gummy serving), search-verified Nordic Ultimate Omega (30 servings,
  1100mg EPA+DHA) and Thorne ResveraCel (415mg NR hydrogen malate ~= 300mg NR).
- Dropped as unverifiable: BulkSupplements Mg glycinate powder (elemental mg
  per serving not on the fetched page), Revolution Nutrition creatine 500g
  (serving size unverified), Orgain creatine (serving size unverified), Nobi
  Mg 400mg (label ambiguous: chelate weight vs elemental), Vitafusion zinc
  gummies (gummies per serving unverified).

## Results (from output/results.json)
- Cheapest stack $2.21/day, $66/mo, $806/yr. Premium (all Thorne) $5.33/day,
  $160/mo, $1,944/yr. Gummy stack $11.41/day, $342/mo, $4,166/yr. Ratio 5.2x.
- Under-dosed servings 14/40 (35%). Median servings/day 1.0.
- Median markups: bulk 1.04x, premium 3.47x, gummy 7.84x. Max 31.6x (Nature
  Made fish oil gummies).
- Gummy stack = 50.1 gummies/day (omega-3 35.1, Mg 8, creatine 4, D3 2, zinc 1).

## Checks
- Stack math cross-checked by hand: cheapest 0.230+0.500+0.039+0.213+0.027+1.200
  = 2.21/day. Gummy 1.165+1.865+0.155+6.741+0.271+1.215 = 11.41/day.
- Caught and fixed two script bugs during the run: cheapest-stack brand pick
  ignored the globally cheapest NR (Tru Niagen 150mg $1.20 vs LE $1.22), and
  a leftover min-price filter picked the cheapest omega-3 bottle instead of
  the cheapest dose.
- Charts visually inspected: 01, 02, 03, 04, 05 all clean after fixes (log
  ticks, mathtext $ escaping, NR/zinc label disambiguation, dose-gap
  annotation placement).

## Rotation
Advance `next` to tech-industry after this build.
