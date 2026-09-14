"""Part 1 — The Great Reshuffle: tech layoffs 2022-2026 (layoffs.fyi data).

Cleans the mirror dataset, builds the monthly layoff wave, industry/stage/
geography breakdowns, and the serial-layoffs ranking. Saves charts + a findings
summary consumed by the README.
"""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import json

BASE = "/home/hatch/workspace/passion-projects/2026-09-14/tech-pulse-2026"
plt.rcParams.update({"figure.dpi": 140, "font.size": 11, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})

# ---------- load & clean ----------
df = pd.read_csv(f"{BASE}/data/layoffs_clean_tb.csv", parse_dates=["date"])
df = df[df["date"] >= "2022-01-01"].copy()                       # analysis window
df = df.sort_values(["company", "date", "total_laid_off"],
                    na_position="last").drop_duplicates(["company", "date"], keep="last")
df["ym"] = df["date"].dt.to_period("M").dt.to_timestamp()

# headcount: prefer reported count; else estimate from percentage via company size if present
lay = df["total_laid_off"].copy()
need = lay.isna() & df["percentage_laid_off"].notna()
# no company-size column in this schema, so estimated rows stay NaN for headcount sums
reported = lay.notna().sum()
print(f"events: {len(df)}, with headcount: {reported} ({reported/len(df):.1%})")

monthly = df.groupby("ym").agg(events=("company", "size"),
                               headcount=("total_laid_off", "sum")).reset_index()
monthly["roll3"] = monthly["headcount"].rolling(3, min_periods=1).mean()
yearly = df.groupby(df["date"].dt.year).agg(events=("company", "size"),
                                            headcount=("total_laid_off", "sum"))

# ---------- chart 1: the wave ----------
fig, ax = plt.subplots(figsize=(11, 5))
ax.bar(monthly["ym"], monthly["headcount"] / 1e3, width=25, color="#4a6fa5", alpha=0.75, label="Monthly headcount")
ax.plot(monthly["ym"], monthly["roll3"] / 1e3, color="#c0392b", lw=2, label="3-month avg")
for x, lab in [("2022-11-01", "2022 correction\npeak"), ("2023-01-01", "Jan 2023:\nbig-tech cuts"),
               ("2024-01-01", "2024: 'efficiency'\nera"), ("2025-07-01", "2025: AI\nrestructuring")]:
    ax.axvline(pd.Timestamp(x), color="gray", ls="--", alpha=0.6)
ax.set_title("Tech layoffs, 2022–2026: the wave that never fully broke", fontsize=14, pad=12)
ax.set_ylabel("Employees laid off (thousands)")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(f"{BASE}/charts/01_layoff_wave_monthly.png")

# ---------- chart 2: industry mix, 2023 vs 2025 ----------
ind = (df[df["date"].dt.year.isin([2023, 2025])]
       .groupby(["industry", df["date"].dt.year])["total_laid_off"].sum().unstack(fill_value=0))
ind = ind.loc[ind.sum(axis=1).sort_values(ascending=False).head(12).index]
ind = ind.reindex(ind[2023].sort_values(ascending=True).index)
fig, ax = plt.subplots(figsize=(10, 6))
y = np.arange(len(ind)); w = 0.4
ax.barh(y - w/2, ind[2023]/1e3, w, label="2023", color="#4a6fa5")
ax.barh(y + w/2, ind[2025]/1e3, w, label="2025", color="#e67e22")
ax.set_yticks(y, ind.index); ax.set_xlabel("Employees laid off (thousands)")
ax.set_title("Who got cut: 2023 vs 2025 by industry", fontsize=14, pad=12)
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(f"{BASE}/charts/02_industry_2023_vs_2025.png")

# ---------- chart 3: serial layoffs ----------
serial = df.groupby("company").agg(events=("date", "size"),
                                   headcount=("total_laid_off", "sum")).reset_index()
serial = serial[serial["events"] >= 3].sort_values("events", ascending=False).head(12)
fig, ax = plt.subplots(figsize=(10, 5.5))
bars = ax.barh(serial["company"][::-1], serial["events"][::-1], color="#7d3c98", alpha=0.8)
ax.bar_label(bars, fmt="%d")
ax.set_title("Serial cutters: most separate layoff events, 2022–2026", fontsize=14, pad=12)
ax.set_xlabel("Layoff events")
fig.tight_layout(); fig.savefig(f"{BASE}/charts/03_serial_layoffs.png")

# ---------- chart 4: stage vs severity ----------
stage = df.dropna(subset=["percentage_laid_off"]).copy()
stage["percentage_laid_off"] = stage["percentage_laid_off"] * 100  # stored as fractions in source
order = ["Seed", "Series A", "Series B", "Series C", "Series D", "Series E+",
         "Private Equity", "Post-IPO", "Acquired", "Unknown"]
stage["stage_grp"] = stage["stage"].map({
    "Seed": "Seed", "Series A": "Series A", "Series B": "Series B",
    "Series C": "Series C", "Series D": "Series D", "Series E": "Series E+",
    "Series F": "Series E+", "Series G": "Series E+", "Series H": "Series E+",
    "Series I": "Series E+", "Series J": "Series E+", "Post-IPO": "Post-IPO",
    "Private Equity": "Private Equity", "Acquired": "Acquired"})
stage["stage_grp"] = stage["stage_grp"].fillna("Unknown")
agg = stage.groupby("stage_grp").agg(med_pct=("percentage_laid_off", "median"),
                                     n=("percentage_laid_off", "size")).reindex(order).dropna()
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(agg.index, agg["med_pct"], color="#16a085", alpha=0.85)
for i, (v, n) in enumerate(zip(agg["med_pct"], agg["n"])):
    ax.text(i, v + 1, f"{v:.0f}%\nn={n}", ha="center", fontsize=9)
ax.set_title("Median % of workforce cut, by funding stage", fontsize=14, pad=12)
ax.set_ylabel("% of workforce")
plt.xticks(rotation=30, ha="right")
fig.tight_layout(); fig.savefig(f"{BASE}/charts/04_stage_severity.png")

# ---------- findings ----------
totals = {int(k): int(v) for k, v in yearly["headcount"].fillna(0).items()}
findings = {
    "events_2022_2026": int(len(df)),
    "headcount_by_year": totals,
    "peak_month": str(monthly.loc[monthly["headcount"].idxmax(), "ym"].date()),
    "peak_month_headcount": int(monthly["headcount"].max()),
    "top_industry_total": ind.sum(axis=1).idxmax(),
    "serial_top": serial.iloc[0]["company"],
    "serial_top_events": int(serial.iloc[0]["events"]),
    "us_share_events": float((df["country"] == "United States").mean()),
}
with open(f"{BASE}/data/findings_layoffs.json", "w") as f:
    json.dump(findings, f, indent=2)
print(json.dumps(findings, indent=2))
