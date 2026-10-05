# DRAFT — do not publish (waits for Michael's explicit approval)

Love is a channel business. I ran Stanford's "How Couples Meet and Stay Together" data — 2,787 couples, tracked from first meeting to 2022 — to test whether how you met predicts whether you last.

Raw answer: brutally yes. Five years in, 92% of couples who met through friends are still together. For couples who met online: 74.7%. One year in, 11.4% of online couples are already done, vs. 2.1% for friend-met couples.

Adjusted answer: the gap flips. Online couples in the sample are older (started at 34.5 on average vs. 25.6), far less often married, mostly newer. Hold who people are constant in an XGBoost model and predicted breakup risk is lowest for online (2.1%) and highest for through-friends (6.8%). The door wasn't doing the work. The sort was.

And the model barely works at all: AUC 0.59. Five years out, whether an established couple splits is close to unpredictable from demographics — age and relationship length swamp every "how we met" variable in the SHAP ranking.

Meanwhile the friend who used to introduce you is being disintermediated on schedule: friends brokered 41.2% of relationships that started in the 1970s, 26.0% in the 2010s. Online passed friends around 2013.

Apps optimize for matches. Retention is decided by who shows up. Same lesson as every marketplace I've ever worked on.

Full build: github.com/mzhou-ds/passion-projects — 2026-10-05/love-is-a-channel

— Musing with Mike
