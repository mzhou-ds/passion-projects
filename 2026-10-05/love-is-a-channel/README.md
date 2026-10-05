# Love is a channel business

**The door you met through predicts whether you last — until you notice who's standing in the doorway. Then the door almost stops mattering.**
*Musing with Mike · 2026-10-05 · Topic: relationships*

Every marketplace guy learns the same lesson eventually: acquisition channels don't just deliver volume, they deliver different people. Cheap channel, expensive churn. I spent a career watching that play out at Lyft, DoorDash, and Patreon. So I asked the obvious question about the highest-stakes marketplace there is: does how couples meet predict whether they stay together?

The answer is yes — loudly, in the raw data. And then mostly no, once you adjust for who arrives through each door. Both halves are interesting. The first half built an industry. The second half is what the industry doesn't want to hear.

**Interactive version:** open `site/index.html` — pick a meeting channel, a decade, and an age, and see the model's five-year survival estimate plus the full channel scorecard.

## What I built

| # | Question | Data | Script |
|---|----------|------|--------|
| 1 | How did the "how we met" mix change, 1940s→2017? | HCMST 2017–2022 public v2.2, 2,787 couples with a coded meeting story and start year | `src/fetch_hcmst.py`, `src/analyze.py` §1 |
| 2 | Do couples who met different ways actually last different lengths of time? | Same couples: relationship start → breakup (retrospective) or last survey wave (2017/2020/2022), hand-rolled Kaplan–Meier + log-rank | `src/analyze.py` §2 |
| 3 | Once you account for who people are, does the channel still matter? | XGBoost + SHAP predicting breakup by 2022 among 1,031 couples partnered in 2017 and re-interviewed in 2022; counterfactual "channel premium" via g-computation with bootstrap CIs | `src/analyze.py` §4 |
| 4 | What happened to the friend who used to introduce you? | "Met through friends" share and survival across seven decades, plus the friend flag inside the ML model | `src/analyze.py` §1, §3, §4 |

Reproduce: `python3 src/fetch_hcmst.py && python3 src/analyze.py` (downloads the 4 MB public file from Stanford; Kaplan–Meier and the log-rank test are implemented by hand in `analyze.py` — no lifelines dependency).

## Findings

**1. The internet didn't grow the market. It ate the intermediaries.** Among relationships that started in the 1970s, 41.2% of couples met through friends and 11.3% through family. By the 2010s: friends 26.0%, family 5.1%, and online 33.2% — up from 1.6% in the 1990s. On a smoothed annual series, online passed family around 2000 and passed friends around 2013. School (11.7%) and work (12.2%) barely moved. This is a textbook disintermediation curve: the platform took the two human brokers — your friends, your family — and left the institutions standing.

**2. Raw, the channel gap is enormous.** Kaplan–Meier survival from the day the relationship starts: five years in, 92.0% of couples who met through friends are still together, and 95.0% of couples who met through family. For couples who met online: 74.7%. One year in, 11.4% of online couples have already broken up, versus 2.1% for friend-met couples. By year five it's 28.5% vs. 8.2% broken up. The log-rank test comparing online to friends isn't close (z = 9.82, p < 1e-15). If you stopped here, you'd write the headline everyone already believes: apps produce disposable relationships.

**3. Adjusted, the gap flips — and that's the finding.** The couples aren't comparable. Online couples in this sample started at an average age of 34.5 (friends: 25.6), only 36% were married at the 2017 baseline (friends: 67%), and 23% are same-sex couples in a sample that oversamples them. So I fit an XGBoost model on the couples we can watch prospectively — partnered in 2017, re-interviewed in 2022 — and asked: same people, different door? Holding age, cohort, education, education gap, marital status, and relationship age fixed, predicted breakup risk by 2022 is *lowest* for online at 2.1% (95% CI 1.8–4.5) and *highest* for through-friends at 6.8% (4.4–7.5). The raw rates in that same prospective sample tell the same story before any adjustment (online 2.8% broke up, friends 7.2%). Among couples who have already survived to a stable baseline, the app couples are not the fragile ones.

Why does the raw curve scream the opposite? Selection on both ends. The retrospective curve is full of relationships that already ended — and a dating market's recent, unmarried, not-yet-tested relationships dominate the online cell. Meanwhile the prospective sample only contains online couples who had already made it to 2017, which filters out exactly the early breakups that drag the raw curve down. The channel isn't magic in either direction. It's a sorting machine, and the sort explains most of the outcome.

**4. The model honestly can't predict breakups — and channel is a minor reason why.** Test AUC is 0.59 for XGBoost and 0.60 for a plain logistic regression, on a 5.2% base breakup rate. Five years out, whether an established couple splits is close to unpredictable from demographics and meeting story — the model barely beats a coin flip with good PR. SHAP says the signal that does exist lives in *who and when*, not *where*: age at start (mean |SHAP| 1.06), the relationship's age in 2017 (0.58), and the year the relationship started (0.50) dominate. The meeting-channel dummies are small (largest: bar/social at 0.19; online at 0.02 as a dummy, 0.13 as a flag). One exception, noted below. If you're building a retention model for couples, "how they met" is a rounding error next to "how old they were and how long it's already lasted."

**5. The friend effect is real, upstream, and shrinking.** Met-through-friends is one of the stronger features in the model (mean |SHAP| 0.38, fourth overall) — but read that against finding 3: in the adjusted premium, friends is the *worst* door, not the best. The reconciliation is that the friend flag is soaking up the effect of being young, unmarried, and early in the relationship — the profile of people whose friends are still introducing them. The friend network's real contribution shows up earlier in the funnel: it was the single largest meeting channel for four decades (53.1% of 1950s starts, still 41.2% in the 1970s) and has fallen to 26.0%. Your friends used to be the matching algorithm. They had context the swiping deck doesn't — they knew both sides, they'd met both families, they had reputational skin in the game. That channel is being disintermediated (finding 1), and nothing in the adjusted numbers says the replacement is worse at retention. What got lost isn't durability. It's the vetted introduction itself.

**6. Family is the quiet premium channel nobody can scale.** Met-through-family couples post the best raw survival in the study (95.0% still together at five years, 92.8% at ten) and a middling adjusted premium (4.5% breakup risk). They're also 5.1% of new relationships, down from 16.7% in the 1940s. Highest retention, no growth. Every marketplace has a channel like this — the one with the best unit economics that refuses to scale. Family introductions come with built-in approval and built-in monitoring. You cannot buy that with ad spend.

## The operator takeaway

Dating apps are a channel business with a mispriced metric. The platforms optimize the visible number — matches, messages, first dates — because that's what the top of the funnel reports weekly. The number that predicts whether any of it mattered is five-year retention, and this data says retention is driven by who the couple is (age, stage, marital intent) far more than by which door they walked through. An app can't change its users' ages. It *can* change who it serves: a funnel that selects for people at the life stage where relationships survive — and charges for that selection instead of for message volume — would be selling the thing that actually predicts the outcome. CAC math hides this because app-met couples look terrible in raw cohort curves (finding 2) and fine once you adjust (finding 3). Operators who read the raw curve will underprice the channel; operators who read only the adjusted one will overclaim credit. The truth a marketplace person should respect: you don't retain couples. You acquire couples who retain.

What I'd do differently as an operator: report retention by acquisition cohort the way this analysis does — raw *and* adjusted, side by side, every quarter. The gap between the two numbers is your selection effect, and it's the most honest measure of what your matching actually adds. If the adjusted gap between channels is zero, your algorithm is a directory, and you should price it like one.

## Caveats

- **Most-recent-partner sampling.** HCMST asks each respondent about a current or most recent partner. The retrospective survival curves therefore over-represent relationships that lasted (a 1970s start only appears if that partner is still the current/most recent one in 2017). Absolute survival levels run optimistic; channel *contrasts* are the defensible read, and the prospective 2017→2022 panel is the cleanest evidence here.
- **The prospective panel selects for stability.** Couples partnered in 2017 and re-interviewed in 2022 (n = 1,031 in the model) have already survived to baseline and agreed to stay in a panel. Base breakup rate is 5.2% over ~5 years — far below population relationship churn. The AUC of 0.59 is partly that selection: there is less variance left to explain.
- **Attrition.** Only about half of the 2017 partnered sample appears in the 2022 wave; breakup itself predicts attrition, so the premium estimates likely *understate* true breakup risk, plausibly unevenly across channels. The 60-rep bootstrap CIs capture sampling noise, not attrition bias.
- **Channel is a primary-code choice.** Q24 is multi-coded; I assign one primary channel with priority online > friends > family > school > work > bar/social > church. A couple who met at a friend-of-a-friend's party with a dating-app pre-screen lands in one cell. The "met through friends" flag is also analyzed separately (finding 5), so the friendship question doesn't hinge entirely on that hierarchy.
- **No friend-overlap or approval measures.** The public file has no "friends in common" count or parental-approval item. The friend-network analysis uses met-through-friends plus the survival contrast — stated as such, not dressed up.
- **Partner deaths in follow-up** cannot be separated from breakups in the wave-3 status variable for every case and are treated as censoring where identified at wave 1; any misclassification slightly inflates "breakup" at older ages.
- Same-sex couples are oversampled by design in HCMST (a feature for some questions); the model includes a same-sex indicator, but population-level channel shares are unweighted descriptive stats of this sample, not calibrated population estimates.

## Sources

- Rosenfeld, Michael J., Reuben J. Thomas, Sonia Hausen, et al. *How Couples Meet and Stay Together 2017–2022*, public version 2.2 [computer file]. Stanford, CA: Stanford University Libraries. https://data.stanford.edu/hcmst2017 (direct file URL and md5 in `data/PROVENANCE.md`).
- Rosenfeld, Michael J., Reuben J. Thomas, and Sonia Hausen. 2019. "Disintermediating your friends: How online dating in the United States displaces other ways of meeting." *PNAS* 116(36). The channel-shift framing and the friends/family displacement read follow their setup; the survival, ML, and premium analyses here are new.

## Layout

```
love-is-a-channel/
├── src/
│   ├── fetch_hcmst.py   # download public file -> derived couples.csv
│   └── analyze.py       # channel shift, KM + log-rank, XGBoost/SHAP, premiums, charts, site data
├── data/
│   ├── couples.csv                  # derived couple-level analytic extract
│   ├── channel_share_by_decade.csv  # aggregate shares behind chart 1
│   ├── findings.json                # every headline number in this README
│   └── PROVENANCE.md                # source URL, md5, citation
├── charts/                          # channel_shift, km_by_channel, shap_bar, shap_beeswarm, channel_premium
└── site/
    ├── index.html                   # interactive channel scorecard
    └── data.js                      # model grid + scorecard (generated)
```
