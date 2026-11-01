# Working notes — Build #55 (2026-11-01, culture)

## Topic
culture (Canada vs US). Carried forward from the Oct 31 run, which died at
scaffolding: only `src/fetch_osm.py` existed (uncommitted) and no data had
been fetched. That stub was moved into today's dated folder and the empty
Oct 31 directory removed. No build shipped on Oct 31; this is the Nov 1 build.

## Question
Can you taste the 49th parallel? Using OpenStreetMap `cuisine` tags on every
`amenity=restaurant` in 8 Canadian and 8 US city cores, measure how restaurant
menus differ across the border, net of plain geographic distance.

## Novelty case (stated before building, per the Oct 16 bar)
The settled take is "Canadians eat poutine, Americans eat burgers," plus the
vague sense that Vancouver and Seattle are basically one city. Nobody has
measured the border in menu space: pairwise cuisine-profile distance between
cities, regressed on kilometres plus a cross-border dummy, and per-cuisine
permeability (which cuisines cross the border freely, which stop dead).
If the border adds menu distance beyond what geography predicts, and if some
cuisines are walls while others are sieves, that is a measurement nobody has
made, and it would surprise someone who knows the field: it turns a cultural
vibe into a number, and it names exactly where the border bites.
Honest risks: OSM tags are crowd-mapped, so coverage varies by city; all
results are shares among *tagged* restaurants, and coverage is reported
alongside every finding. The headline follows the data, not the hypothesis.

## Design
- 16 city cores (CA: Vancouver, Toronto, Montreal, Calgary, Edmonton, Ottawa,
  Winnipeg, Halifax; US: San Francisco, Los Angeles, New York, Seattle, Boston,
  Chicago, Houston, Portland), same fetch script, tags only.
- City x cuisine matrix from `cuisine` tags (split on `;`), grouped into
  families (chinese incl. regional subtypes, japanese incl. sushi/ramen, etc.).
- Metrics: Shannon entropy of cuisine shares, top cuisines, family shares,
  Chinese-subtype specificity (share of Chinese-family places tagged with a
  regional subtype rather than generic "chinese").
- Border test: cosine distance between city cuisine vectors vs haversine km,
  OLS with a cross-border dummy + permutation test; LOOCV country classifier
  from cuisine vectors (n=16, so reported with its permutation null, not
  oversold).
- Charts: diversity by city, family-share heatmap, menu-distance vs km
  scatter, permeability (CA/US share ratios), Chinese specificity.
