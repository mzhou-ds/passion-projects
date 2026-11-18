# The Ghost Job Market: a third of tech's open roles aren't real

**Build #72 — tech-industry — November 18, 2026**

## The question

Every jobs report says tech hiring is back. The boards certainly look busy: Databricks alone lists 897 open roles, Stripe 789, Anthropic 657. But a posting is not a vacancy. Some listings are evergreen pipelines that never close. Some are three years old. So I counted the whole posted market, live, and asked a simpler question: how much of it is actually hiring right now?

## The census

On November 18, 2026 I pulled every open posting from the public Greenhouse job boards of 40 tech companies, 8,371 roles in total, with title, location, department, posting text, and first-published date. Greenhouse is the applicant tracking system for a big slice of mid-stage and late-stage tech, so this is a real census of one large corner of the market, not a sample. It is not the whole market: Google, Meta, Amazon, Apple, and Microsoft run their own systems and are not in here, and neither are companies on Lever, Ashby, or Workday. The 40 boards that are in here range from Anthropic and Databricks to Airbnb, Stripe, Figma, and GitLab.

Then I classified every posting four ways: function, seniority, remote vs hybrid vs on-site, and whether it is a people-manager seat. I also measured posting age from the first-published date. A posting open more than 90 days is a ghost: either the role is evergreen, the req is frozen, or nobody is really hiring for it.

## What I found

### 1. 31% of the posted market is stale

2,595 of the 8,371 postings have been open more than 90 days. 15.5% have been open more than six months. The median posting is 50 days old. Strip out the ghosts and the live market is 5,776 roles, not 8,371.

The staleness is not evenly spread, and that is the point. Scale AI has 55.7% of its board open 90+ days. Databricks is at 52.2%, Vercel 51.7%. Databricks is still listing an Account Executive role first published 1,071 days ago, nearly three years. At the other end, Dropbox is at 9.8% and SoFi at 11.8%. The biggest boards are the stalest ones, which means the companies that look like they are hiring the most are the ones most overstating it. If you are counting openings to judge the market, discount the big boards by about half.

Data science is the stalest function of all: 40.5% of DS postings are ghosts. The posted DS market looks like 733 roles. The live one is 436.

### 2. Tech is hiring sellers almost three times as fast as data scientists

Engineering is still the biggest function at 37.6% of postings. But the number two function is not product or data. It is sales and business development at 23.6%, nearly 2,000 roles. Data and AI is 8.8%. Design is 1.6%, about 134 roles across 40 companies. The ratio tells the story of this market: for every data scientist these companies want, they want 2.7 sellers. The build phase is over and the sell phase is on. Anyone reading the boards as a proxy for where tech is investing should notice that the money is going into distribution, not into more builders.

### 3. The bottom rung of the ladder is gone

Junior roles are 1.5% of postings. New grad roles are 0.5%. Internships are 2.8%. Add them up and entry level is 4.8% of the market, 403 roles. Senior, staff, and principal roles are 36.0%, 3,012 roles. That is 7.5 senior-or-above seats for every entry-level seat. The industry is hiring people who can already do the job and almost nobody it has to train. That is a slow-moving problem: a market that only hires seniors eventually runs out of seniors.

### 4. Remote didn't die. It consolidated.

Overall, 19.5% of postings are remote, 6.8% hybrid, 73.7% on-site. That average hides a split. Eight boards are 82% to 100% remote: Dropbox and Twilio at 100%, Affirm at 98.6%, Instacart at 97.6%, GitLab at 91.3%, Coinbase at 89.5%, Reddit at 82.3%. Eighteen boards are under 5% remote, including Figma, Lyft, MongoDB, Cloudflare, and Scale AI at 0%. Remote is now a company-level identity, not a market-wide option. Among US-tagged postings, 53.3% are remote, because the remote-first companies list their roles as US-remote while the office companies list a city. If you want remote, you do not filter by it. You pick the eight companies.

### 5. AI is a skill sprinkled into jobs, not a job family

Only 5.8% of postings are AI roles by title or department. But 16.6% mention AI work in the description. Anthropic is the outlier at 22.1% AI-titled, about 145 roles, and Scale AI at 25.1%. Databricks is the revealing contrast: 3.2% of its 897 postings are AI-titled, but 19.4% mention AI work. The company that sells the picks and shovels for AI barely hires AI-titled people. It hires engineers and expects AI to be part of the job. The market is not creating a new AI profession at scale. It is adding AI to the existing ones.

### 6. The manager seat, honestly measured

This one started as the headline and the data corrected it. Manager seats are not scarce in engineering and data: 13.4% of engineering postings and 11.5% of data postings are people-manager seats, about one per 6.5 and 7.7 IC postings. That is roughly a normal span of control. Where the seat is genuinely scarce is product: 2.5% of product postings are Director-of-Product or above, one per 38.8 PM postings. Product leadership is filled internally or by network, almost never by posting.

For data leadership specifically, the count is small in absolute terms: 84 manager seats across 40 companies, and only 2 of them are literally titled "Data Science Manager". Most hide under engineering titles: Engineering Manager for ML, Manager of ML Engineering, Senior Manager of Infrastructure Data Science. If you search the boards for "Data Science Manager", you miss nearly all of them. The seat exists. It is just filed under a different name.

## What this means if you are job hunting

Discount every board by a third before you believe it, and by half at Databricks, Scale AI, and Vercel. Aim at the live roles, which are the ones posted in the last 90 days. If you want remote, target the remote-first eight, not the market. If you want a first management seat in data, search "Engineering Manager, ML" and "Manager, ML Engineering", not "Data Science Manager". And if you are early career, the posted market has almost nothing for you, which is a fact worth knowing before you spend months applying into it.

## Charts

- `charts/01_function_mix.png` — function mix of all 8,371 postings
- `charts/02_ghost_index.png` — share of postings open 90+ days, by company
- `charts/03_age_buckets.png` — posting age distribution
- `charts/04_remote_bimodal.png` — remote share by company, showing the bimodal split
- `charts/05_seniority_ladder.png` — seniority mix
- `charts/06_ai_strict_vs_broad.png` — AI-titled roles vs AI mentioned in the description, top 10 companies
- `charts/07_manager_ladder.png` — manager seats per 100 IC postings, by function
- `charts/08_top_metros.png` — top hiring metros (San Francisco still #1 at ~1,063 postings)

## Data and reproduction

- `data/jobs_classified.csv` — all 8,371 postings with classifications (function, AI flags, manager flag, remote class, seniority, age in days)
- `data/company_table.csv` — per-company aggregates (40 boards, minimum 30 postings)
- `data/summary.json` — headline statistics
- `data/board_status.json` — which boards responded and which 404'd
- `src/fetch_greenhouse.py` — pulls the public Greenhouse Job Board API (no auth), one call per board
- `src/analyze.py` — classifiers and statistics
- `src/charts.py` — all charts

Run `python3 src/fetch_greenhouse.py`, then `python3 src/analyze.py`, then `python3 src/charts.py`. Requirements in `requirements.txt`.

## Limitations, stated plainly

- **Coverage.** 40 companies on Greenhouse only. No Google, Meta, Amazon, Apple, Microsoft, Netflix, or Uber, and no Lever/Ashby/Workday shops (OpenAI, Snowflake, Palantir, Notion, DoorDash). The census describes the Greenhouse corner of tech, which skews mid-stage and late-stage.
- **Ghost is a proxy.** "Open 90+ days" means the posting is old, not that the role is fake. Some are evergreen pipelines, some are frozen reqs, some are just slow. The 1,071-day Databricks posting is almost certainly evergreen, but the cutoff is a judgment call. The pattern across companies is the finding, not any single posting.
- **Remote is location-based.** A posting counts as remote when its listed location says so, or its text says the role is remote. Hybrid is undercounted: many hybrid roles list only a city.
- **Manager is title-based.** Director, VP, Head of, and Manager titles count as people-manager seats, except for well-known IC titles (Product Manager, Program Manager, Account Manager, and similar). Some "Manager" titles are ICs and some "Lead" roles manage people; both edge cases are small relative to the counts.
- **AI is two definitions.** Strict means the title or department is AI/ML. Broad means the description mentions AI work. The gap between them is itself a finding, and both numbers are reported.
- **Snapshot.** One day, November 18, 2026. Boards change daily. The ghost index is a point-in-time measure, and the honest follow-up is to re-run it monthly and watch which boards get fresher.

## Sources

- Greenhouse Job Board API, `boards-api.greenhouse.io/v1/boards/{slug}/jobs`, public and unauthenticated, accessed November 18, 2026. 40 boards, 8,371 postings. Companies whose boards returned 404 (moved ATS or no public board) are listed in `data/board_status.json` with the working set in `src/fetch_greenhouse.py`.
