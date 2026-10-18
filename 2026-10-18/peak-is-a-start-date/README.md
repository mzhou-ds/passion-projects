# The Peak Is a Start Date — strength doesn't expire at 26, it expires about seven years after you start

**Musing with Mike · daily build #42 · 2026-10-18 · topic: fitness**

Every gym conversation about aging runs on one chart: strength peaks in your mid-20s and fades from there. That chart has a flaw nobody prices in. It is not a picture of a life. It is a collage — one group of people at 24, a different, smaller, stranger group at 60 — and it confuses *who is still in the room* with *what happens to a person*.

This build follows the same people instead. From the OpenIPF archive (IPF-affiliate, mostly drug-tested powerlifting), I rebuilt **181,299 careers** from 495,732 raw full-power meet entries (1990–2026), segmented so a career only continues while reported age stays consistent with the calendar — which breaks most same-name collisions. Then I asked three questions the collage cannot answer: when does a lifter actually peak, how fast do they fade after *their own* peak, and what actually makes them stop showing up?

**Try it:** open [`explorer.html`](explorer.html) — enter the age you started and get your career clock: likely peak age, typical years to peak, and what lifters who started when you did actually held onto at 60.

## Findings

**1. Your peak is scheduled by your start date, not your birthdate.** Among 2,774 careers with 5+ meets spanning 8+ years, regressing peak age on age at first competition gives a slope of **0.885 (95% CI 0.876–0.894)** — the peak moves almost one-for-one with the start. Start at 20–24 and the median peak lands at 29.5. Start at 35–39, peak at 43. Start at 45–49, peak at **51.5**. Start somewhere in your 50s and the median lifter peaks at **57.5**, three and a half years in. Women are even more start-driven (slope 0.927) than men (0.870). Restricting to careers that look finished (last meet in 2022 or earlier, so the peak is not still ahead of them) barely moves it: 0.876. The famous peak at 24–26 is mostly the age of the people who happened to start as teenagers, photographed early. See `charts/01_peak_vs_start.png`.

**2. The honest tax on starting late is height and speed, not timing.** Late starters peak later, but lower and slower. Median career-best Goodlift slides from ~93 for teenage starters to ~71 for 50-something starters, and early-career improvement runs at **5.0% per year for teenagers vs 1.7% per year for lifters who start in their 50s** (career years 0–3, annual-best Goodlift). Biology does not cancel the appointment. It lowers the ceiling and slows the climb. Anyone selling a 55-year-old beginner a 25-year-old's trajectory is lying; anyone telling him the window already closed is also lying. See `charts/06_velocity.png`.

**3. After your own peak, decline is a slope, not a cliff.** Lifters observed five years past their personal best still hold a median **94.7%** of it (annual best, n=2,808 careers). Ten years past peak: **91.0%**. Fifteen: 89.2% (n=42, thinner ice). That is roughly half a percent to a percent a year — a leak, not a collapse. See `charts/03_post_peak.png`.

**4. The two curves answer different questions, and the gap is the story.** The cross-section says a 60-year-old holds 77.4% of what a 24-year-old holds, and a 70-year-old just 68.9%. The same lifters, measured against *their own* peaks: still-competing long-career lifters at 60 hold **95.8%**, at 70 **91.7%**. Both numbers are true. The first describes the room — who starts, who leaves, which birth cohorts ever got access to a platform. The second describes a person who stays. Quoting the first as your personal forecast is like pricing your house off a chart of who still owns one. See `charts/02_two_curves.png`.

**5. Bad meets don't kill careers. Careers just end.** In a 201,426-meet panel (each meet followed for 3 years), 28.6% of meets are a lifter's last for at least three years. After a personal record, the exit rate is 27.8%. After a disaster — more than 10% below your best — it is 33.1%. A five-point gap for the worst day of your career. An XGBoost model of exit (AUC 0.68) with SHAP importances ranks the meet result near the bottom: meets competed so far, strength level, age, and the gap since your last meet all matter more. People rarely quit because of one bad platform day. They drift: longer gaps, life, a career that has run its length. The practical read cuts against every "bounce back" speech — retention is a scheduling and identity problem, not a motivation-after-failure problem. See `charts/04_exit_by_outcome.png`, `charts/05_exit_shap.png`.

**6. A third of long careers are still peaking when the data runs out.** 33.3% of the long careers hit their best within their final observed year. The record literally cannot see their decline yet. That cuts in favor of the headline, not against it: measured peaks are, if anything, *earlier* than true peaks for active lifters — which makes a slope of 0.885 a conservative estimate of how much the start date runs the show.

## The market read

Fitness sells to the young as if strength were a wasting asset and to the old as if it were a recovery product. The career data says the actual product for anyone over 35 is *time-to-peak*: a 45-year-old beginner is not buying maintenance, he is buying a peak around 51 that he has not reached yet, at a predictable improvement rate, with a slow leak afterwards if he stays. Gyms, coaches, and apps that frame masters training as decline management are mispricing their own customer. The scarce thing is not youth. It is an uninterrupted decade — and the exit model says what interrupts it is drift, not failure.

## Method

- `src/download.py` — pulls the OpenIPF bulk CSV (`openipf-2026-10-17`, rev `c7782562`).
- `src/analyze.py` — one pipeline: filters to Raw, full-power (SBD) entries with a total, Goodlift points, and a reported age, 1990+ (495,732 entries); builds careers as Name+Sex+Country segments, splitting whenever |Δage − Δyears| > 2.5; computes the cross-sectional curve, the peak-age regression (bootstrap CIs, 500 draws), post-peak and at-age retention on annual-best Goodlift, a 3-year exit panel with XGBoost (400 trees, depth 3) + SHAP, and early-career velocity by start-age band.
- `src/charts.py` — all six charts from `output/results.json` and the derived career table.
- `data/careers.parquet` — the derived entry-level career dataset. Raw download is git-ignored; `download.py` refetches it. `output/long_careers.csv` — the 2,774 long careers with first/peak/last dates.
- Goodlift points adjust for sex and bodyweight, so a lifter gaining weight between meets is not credited with phantom strength.

Reproduce: `pip install -r requirements.txt && python src/download.py && python src/analyze.py && python src/charts.py`.

## Caveats, stated flatly

These are competitors, not the general public: people who enter drug-tested powerlifting meets are selected for health, stubbornness, and access, and the lifters still competing at 60 are the survivors of their cohort — finding 4 says so in numbers rather than hiding it. Name-based careers can still merge two same-name lifters in one country when their ages happen to stay calendar-consistent, and can split one lifter who changes country or name; the segmentation rule cuts both errors down, it does not erase them. Reported ages in the archive are sometimes age-class midpoints, which adds noise the medians mostly absorb. Cross-sectional and within-lifter retention are both descriptive; nothing here randomizes anyone into starting at 45. And powerlifting strength is one narrow slice of fitness — it says nothing direct about VO2 max, joints, or metabolic health, all of which have their own clocks.

## Sources

- OpenIPF / OpenPowerlifting bulk data, IPF affiliates edition, 2026-10-17: https://openpowerlifting.gitlab.io/opl-csv/bulk-csv.html — public domain. *"This project uses data from the OpenPowerlifting project, https://www.openpowerlifting.org."*
- Build #4 in this repo (`2026-09-11/strength-in-numbers`) — the cross-sectional standards and age curve this build re-examines longitudinally.
- Goodlift points: IPF's bodyweight/sex scoring system, successor to Wilks — see the OpenPowerlifting project documentation.
