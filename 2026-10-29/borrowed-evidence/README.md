# Borrowed Evidence: Your Biohack Was Tested on Someone Else

**Build #53, Musing with Mike, 2026-10-29. Topic: biohacking.**

## The novelty case, stated before building

The familiar stat in biohacking is a trial count: "creatine has hundreds of
studies," "rapamycin has decades of research." Nobody had measured, across
the whole biohacker stack at once, how many of those registered trials
actually enrolled healthy people like the buyer. If most of them are
disease-treatment trials in older patients, then trial counts systematically
overstate the evidence for a healthy 30-year-old, and supplement marketing
gets to count every one of them. That is the measurement this build makes,
straight from the registry, and it would surprise someone who knows this
field, because the borrowed part is not a footnote. For the biggest names
it is most of the literature.

## What I did

I pulled every registered trial I could match by intervention name from
ClinicalTrials.gov (public API v2, fetched 2026-10-29) for 12 interventions
a biohacker would recognize: creatine, cold water immersion, sauna,
photobiomodulation, intermittent fasting, time-restricted eating, ketogenic
diet, rapamycin, nicotinamide riboside, NMN, ashwagandha, methylene blue.
Search-term noise was filtered out by requiring the intervention name itself
to appear in the trial's arms (this drops, for example, creatinine-clearance
studies that a raw "creatine" search sweeps in). That left 1,907 trials.

Two registry fields do the work. The first is the trial's own
healthy-volunteer flag: False means the trial does not accept healthy
volunteers at all. The second is a stricter cut built for this project:
a "young-healthy" trial accepts healthy volunteers, enrolls adults, and
sets its minimum age at 40 or under. That is the closest the registry gets
to "tested on someone like you."

## Findings

**1. Two thirds of the biohacker literature excludes healthy people
entirely.** Across all 1,907 trials, 68.9 percent do not accept healthy
volunteers. Only 25.9 percent meet the young-healthy cut. Strip out
rapamycin, whose pagination was capped, and it is still 60.9 percent
patient-only and 32.8 percent young-healthy. The "hundreds of studies"
pitch is, in the main, a pitch about sick people.

**2. Rapamycin is the extreme case, and it explains the trick.** 93.9
percent of its 460 matched trials exclude healthy volunteers, and only
4.3 percent are young-healthy. Its top conditions are kidney
transplantation, lymphoma, and advanced cancer. Rapamycin is a transplant
and oncology drug with a longevity side hustle. When a longevity influencer
cites "decades of rapamycin research," most of those decades were spent
keeping transplanted kidneys alive at doses no biohacker takes. The count
is real. The transfer is the fiction.

**3. The same pattern holds, softer, across the metabolic canon.**
Ketogenic diet: 73.8 percent patient-only, with obesity and epilepsy as
the top conditions. Keto was a medical treatment before it was a lifestyle,
and its literature still is one. Methylene blue: 75.4 percent
patient-only, led by septic shock and breast cancer surgery, where it is
used as a dye and a drug, not a brain tonic. Photobiomodulation: 65.9
percent patient-only, led by oral mucositis and head and neck cancer.
Nicotinamide riboside: 62.2 percent patient-only, and 27.8 percent of its
trials set a minimum age of 50, so even its healthy-volunteer trials skew
old.

**4. There are two honest exceptions, and they prove the rule.**
Cold water immersion is 14.7 percent patient-only and 79.4 percent
young-healthy: it was studied in athletes from the start, so its evidence
actually looks like its buyers. Ashwagandha is 26.3 percent patient-only
and 71.1 percent young-healthy, studied mostly for stress and sleep in
working-age adults. When a biohack is genuinely tested on healthy people,
it shows up immediately in this measure. Most of them just are not.

**5. The bigger the literature, the more borrowed it is.**
Across the 12 interventions, the correlation between log trial count and
young-healthy share is negative 0.77. Longevity drugs as a category are
84.8 percent patient-only and 11.4 percent young-healthy. Size is not
evidence of transfer. If anything, in this market, size is evidence of a
long prior life as a drug.

**6. The boom did not fix it.** Trial starts for these interventions
(excluding rapamycin) rose from dozens a year in the early 2010s to more
than 150 a year by 2023. But the young-healthy share has sat around
one-third since 2011 (41.9 percent in 2011-15 on a small base, 33.5 percent
in 2016-20, 32.7 percent in 2021 onward). The industry scaled up trial
volume without scaling up trials on healthy young people.

**7. Even the good evidence is small.** Median enrollment is around 40
participants whether a trial accepts healthy volunteers or not, and
healthy-volunteer trials complete slightly more often (57.6 percent vs
47.4 percent). So the honest version of most biohacker claims is not
"proven" or "debunked." It is "tested, in small groups, mostly on people
who are not you."

## The operator takeaway

Before buying a biohack on its study count, ask for the second number:
how many of those studies enrolled healthy people in your age band, at
something like the dose being sold? A brand that cannot answer that is
selling someone else's evidence. A brand that can, like the cold plunge
and ashwagandha literatures here, has a real advantage it should be
advertising. If you run a supplement company, publishing your
young-healthy share is the cheapest credibility move in the market,
because almost nobody else can pass the test.

## What this does not show

Trial counts are not effect sizes, and this build does not say whether
any of these interventions work. A patient-only trial can still be
informative about mechanism, and some interventions (rapamycin above all)
genuinely cannot be tested first in healthy people at drug doses. The
claim is narrower and, I think, harder to dodge: the evidence being
marketed to healthy buyers was mostly not produced on healthy buyers.
Also note the registry's healthy-volunteer flag is sponsor-reported and
"accepts healthy volunteers" does not mean "only healthy volunteers,"
which is why this build reports both the strict patient-only share and
the stricter young-healthy share rather than pretending the middle
group is clean.

## Reproduce it

```
pip install -r requirements.txt
python3 src/fetch_trials.py   # ClinicalTrials.gov API v2, no key needed
python3 src/analyze.py        # data/summary.csv, data/top_conditions.json
python3 src/charts.py         # charts/*.png
```

`data/trials.csv` is the matched trial-level pull (1,907 rows);
`data/trials_enriched.csv` adds the derived flags. Rapamycin was capped
at five pages of pagination (460 matched trials), so its counts are a
sample of its full registry footprint, and the trend chart excludes it for
that reason. Start years in 2026 include trials scheduled to start.

## Sources

ClinicalTrials.gov API v2, queried by intervention name 2026-10-29.
All figures in this README are computed from `data/trials.csv` by
`src/analyze.py`; no external market or survey data was used.

## Charts

- `charts/01_patient_share.png`: patient-only share by intervention
- `charts/02_young_healthy.png`: young-healthy share by intervention
- `charts/03_trend.png`: trial starts per year, rapamycin excluded
- `charts/04_size_vs_transfer.png`: literature size vs young-healthy share
- `charts/05_category.png`: patient-only and young-healthy share by category

`explorer.html` is a sortable table of the per-intervention summary.
