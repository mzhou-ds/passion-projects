# The Border on the Menu

**Can you taste the 49th parallel?** Yes, and a model can do it perfectly.

This build takes every restaurant in 16 city cores, 8 Canadian and 8 American,
and asks whether their menus know which side of the border they are on. The
answer is that menus do not drift gently with distance. They jump at the
border. Vancouver and Seattle sit 191 km apart on the same coast, and their
menus are further apart than Boston and New York, which are 302 km apart.
Vancouver's most common cuisine is Japanese, at 21.4% of tagged restaurants.
Seattle's is Italian, then American, then Mexican. Same ocean, different dinner.

## What I found

**A classifier tastes the border.** Given only a city's cuisine shares, a
logistic regression names the right country for all 16 cities when each city
is held out in turn. Shuffled labels average 44.5%. That is not a vibe, it is
a measurement with a permutation p-value of 0.0005.

**Distance barely matters, the border does.** Across all 120 city pairs, the
average menu distance is 0.077 within a country and 0.142 across it. In a
regression, crossing the border adds 0.065 to menu distance while a full
standard deviation of kilometres adds just 0.006. The border coefficient
survives 5,000 permutations with p under 0.0002.

**Some cuisines cross, some stop.** Mexican food is the wall: 3.2% of
Canadian tagged restaurants against 11.4% in the US. Indian and Vietnamese
lean the other way, roughly twice as common in Canada. Italian is the control
that crossed freely, 15.7% in Canada and 16.0% in the US. Even "American" food
leans south, 8.2% against 13.7%.

**Two ideas I had were wrong, and that is part of the finding.** I expected
Canadian menus to be more diverse. They are not: mean cuisine entropy is 3.70
in Canada and 3.76 in the US. I expected Chinese menus to be more regionally
specific north of the border, the diaspora detail I would notice as a
Canadian-born Chinese kid. They are not: 4.7% of Canadian Chinese-family
restaurants carry a regional tag like Sichuan or dim sum, against 5.8% in the
US. And the national dish is a rounding error: "Canadian" tags show up on
0.68% of Canadian restaurants and 0.01% of American ones. French tags are as
common in US cities as Canadian ones, so Montreal does not make French food
Canadian either.

## Data and method

35,619 restaurants in fixed city-core boxes, 26,972 with a cuisine tag
(75.7% coverage). The original plan was the Overpass API, but on 2026-11-01
all four public mirrors timed out even on a tiny test query, so the data
comes from BBBike city extracts for 12 cities and Geofabrik province/state
extracts for Edmonton (Alberta), Winnipeg (Manitoba), Boston (Massachusetts),
and Houston (Texas). BBBike has no extracts for those four cities, which is
why the province files were needed. Every element was clipped to the same
core boxes with pyosmium, so the comparison is downtown menus, not whole
metros.

Cuisine tags were split on semicolons and grouped into families (sushi and
ramen count as Japanese, Sichuan and dim sum count as Chinese, and so on).
City similarity is cosine distance over cuisine-family shares. The border
test is an OLS regression of pairwise distance on kilometres plus a
cross-border dummy, with a permutation test on the border coefficient, plus
the leave-one-city-out country classifier above.

## Reproduce

```
pip install -r requirements.txt
python3 src/download_pbf.py     # BBBike + Geofabrik extracts (2.5 GB, not shipped)
python3 src/extract_pbf.py      # clip to core boxes -> data/raw/osm_<city>.json
python3 src/02_analysis.py      # city stats, pairwise distances, border tests
python3 src/03_charts.py        # charts/
```

The raw extracts are not in the repo (2.5 GB). The clipped per-city JSONs in
`data/raw/` are, so the analysis and charts run without re-downloading
anything. `src/fetch_osm.py` is the original Overpass fetcher, kept for the
record; it did not work on the day.

## Charts

- `charts/border_scatter.png`: menu distance vs kilometres, same-country vs cross-border pairs
- `charts/permeability.png`: Canada/US share ratios by cuisine, the walls and the sieves
- `charts/heatmap.png`: cuisine shares by city
- `charts/diversity.png`: cuisine entropy by city
- `charts/chinese_specificity.png`: regional-tag share of Chinese restaurants by city

## Caveats

OpenStreetMap tags are crowd-mapped. Coverage runs from 61% in Halifax to 86%
in Seattle, and every share here is a share of tagged restaurants, not of all
restaurants. Tagging habits could differ by city, which is a real limitation,
but the border effect is large, consistent across pairs, and survives
permutation testing, so it is unlikely to be a tagging artifact alone.
