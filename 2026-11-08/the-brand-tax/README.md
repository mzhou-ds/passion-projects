# The Brand Tax: What the Same Molecules Cost When You Buy the Story

**Build #62 — Musing with Mike — 2026-11-08 — biohacking**

The biohacker stack is six molecules: creatine, magnesium glycinate, vitamin D3,
omega-3, zinc, and nicotinamide riboside. Buy them as bulk powder and generic
capsules and the whole stack costs **$2.21 a day, $806 a year**. Buy the same six
molecules as an all-Thorne premium stack and it costs **$5.33 a day, $1,944 a
year**. Buy them as gummies and it costs **$11.41 a day, $4,166 a year** — 5.2
times the cheap stack, for the same active ingredients. The gummy stack is also
50 gummies a day, 35 of them fish oil.

## The novelty case, stated before building

Everyone knows supplements are marked up. Nobody had measured the cost per
*trial dose* across the whole staple stack at once. The price on the bottle is
per serving, and the serving is the unit the industry engineers. Set the serving
below the dose the trials used and the bottle looks cheap while lasting a week
at the real dose. Shrink the dose into a gummy and the price per gram explodes,
because a gummy can only hold so much active ingredient. This build measures
both tricks at once, on real listings, with the dose taken from the evidence
rather than the label. It would surprise someone who knows this field, because
the tax is not a gentle premium. It is a 5x spread on identical molecules, and
the single worst product in the set costs 31.6 times the cheapest way to buy
the same dose.

## Findings

**1. The same six molecules cost $806 a year or $4,166 a year, and the only
difference is the story.** The cheapest stack (BulkSupplements creatine,
Pure Encapsulations magnesium, NOW vitamin D3, NOW fish oil, NOW zinc, Tru
Niagen 150 mg) runs $2.21 a day. The all-Thorne premium stack runs $5.33 a
day. The all-gummy stack runs $11.41 a day. NR dominates the cheap stack at
$1.20 a day, more than half the total. Everything else in the cheap stack
combined costs about a dollar a day. See `charts/04_stack_cost.png`.

**2. The serving is the swindle: 14 of 40 products put less than a trial dose
in one serving.** The median product needs exactly one serving a day, but the
tail is where the money is. Thorne's own magnesium powder is 200 mg a scoop
against a 400 mg trial dose, so the premium powder needs two scoops a day and
costs $1.73 a day. Every magnesium gummy is 100 mg a serving, so four servings
a day, eight gummies. The standard 1,000 mg fish oil softgel holds 300 mg of
EPA+DHA, so the bottle's "one a day" is a third of a dose. See
`charts/03_dose_gap.png`.

**3. The gummy tax is the biggest single markup in the set, and fish oil is
where it detonates.** Gummies cost a median 7.8 times the cheapest way to buy
the same compound, against 3.5 times for premium brands and 1.0 times for
bulk. The extreme case is Nature Made fish oil gummies: 57 mg of EPA+DHA per
two-gummy serving against a 1,000 mg trial dose. That is 17.5 servings, 35
gummies, and $6.74 a day, against $0.21 a day for the same dose as a NOW
softgel. A 31.6x markup, on the number one pharmacist-recommended brand.
See `charts/02_markup_by_tier.png`.

**4. The premium brand is sometimes the cheapest way to buy the dose, which
is the tell.** Pure Encapsulations magnesium is the cheapest magnesium in the
set at $0.50 a day, beating every gummy and beating Thorne's own powder,
because its capsule is honestly dosed at 120 mg elemental. The price is not
the signal. The dose per serving is. The same inversion shows up inside
single brands: Life Extension's 100 mg NR bottle costs $1.62 per 300 mg dose,
more than its own 300 mg bottle at $1.22. The weaker bottle is the worse deal.

**5. NR is the one compound where the brand tax barely exists, and the reason
is a patent.** NR runs $1.20 to $2.00 a day across all six products, a 1.7x
spread, the tightest in the set. Niagen is patented and licensed, so there is
no real generic tier. The molecule is the brand. Everywhere a generic exists,
the spread is 8x to 32x.

**6. Vitamin D is nearly free and zinc is nearly free, which reframes the
whole stack.** NOW vitamin D3 at 2,000 IU costs $0.039 a day, $14 a year.
NOW zinc picolinate at 50 mg a capsule costs $0.027 a day, and one capsule is
3.3 times the trial dose, so a $10.70 bottle lasts 400 days. The stack's cost
is NR plus creatine plus magnesium. The rest is a rounding error, which is
exactly why nobody prices it per dose: there is no margin in telling you that.

## How it was measured

Six compounds, 40 products, all real listings fetched 2026-11-08 through the
Meta product catalog, with serving sizes and doses per serving verified against
each product's own label (brand site, retailer listing, or the NIH Dietary
Supplement Label Database). Trial doses are the doses the evidence used:
creatine 5 g/day (Kreider et al. 2017, JISSN position stand), magnesium 400 mg
elemental/day (NIH ODS RDA for adult men), vitamin D3 2,000 IU/day (VITAL
trial), omega-3 1,000 mg EPA+DHA/day, zinc 15 mg/day, NR 300 mg/day (Trammell
et al. 2016). Magnesium is counted as elemental mg and omega-3 as EPA+DHA mg,
not total oil weight. Cost per trial dose is price divided by total active in
the container divided by the trial dose. The stacks each buy one product per
compound at trial dose: cheapest is the lowest cost per dose in each compound,
premium is all Thorne, gummy is the cheapest gummy in each compound (NR has no
gummy, so Life Extension 300 mg fills that slot).

## What this does not claim

Prices are one day's listings from the catalog's retailers, and they move.
Subscription pricing, which several brands push hard, is not in here. The
analysis takes no position on bioavailability differences between forms: a
premium brand may be worth paying for if its testing or sourcing matters to
you, and NSF Certified for Sport has real value for tested athletes. The claim
is narrower and checkable: per milligram of the named active ingredient, at
the dose the trials used, the price spread is 5x across stacks and up to 32x
within a compound. Purity testing is not in the price math.

## Reproduce it

```bash
python3 src/build_data.py   # joins the raw catalog JSONs to the verified spec -> data/products.csv
python3 src/analyze.py      # metrics, stacks, charts, output/results.json
python3 src/make_explorer.py
```

Requirements: `pandas`, `matplotlib`, `numpy` (see `requirements.txt`).
Raw catalog results are in `data/raw/`; the verified table with sources is
`data/products.csv`; open `explorer.html` for a sortable table of all 40
products.

## Sources

- Prices and listings: Meta product catalog, fetched 2026-11-08
  (`data/raw/*.json`); serving sizes verified on thorne.com, bulksupplements.com,
  naturemade.com, and retailer listings, plus the NIH Dietary Supplement Label
  Database for BulkSupplements creatine.
- Trial doses: Kreider et al. 2017 (JISSN creatine position stand); NIH Office
  of Dietary Supplements magnesium RDA; Manson et al. 2019 (VITAL, NEJM);
  Trammell et al. 2016 (NR pharmacokinetics).
- Thorne ResveraCel: 415 mg nicotinamide riboside hydrogen malate per serving,
  equivalent to ~300 mg NR (Thorne reformulation note).
