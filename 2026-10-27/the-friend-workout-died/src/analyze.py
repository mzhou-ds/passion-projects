"""Working Out Alone — who was in the room for America's exercise, 2003-2025.

Data: BLS American Time Use Survey (ATUS) multi-year microdata 2003-2025,
Activity + Who + Respondent files. One diary day per respondent, survey
weights TUFINLWGT. Who codes (ATUS interview dictionary):
  18/19 alone · 20 spouse · 21 unmarried partner · 22 own household child
  23 grandchild · 24 parent · 25 brother/sister · 26 other related person
  27 foster child · 28 housemate/roommate · 29 roomer/boarder
  30 other nonrelative · 40 own nonhousehold child <18
  51 parents (nonhousehold) · 52 other nonhousehold family <18
  53 other nonhousehold family 18+ · 54 friends · 56 neighbors/acquaintances
  57 other nonhousehold children <18 · 58 other nonhousehold adults
  59 boss/manager · 60 people I supervise · 61 co-workers · 62 customers

Exercise sets (ATUS lexicon, tier 13 = Sports, Exercise, Recreation):
  FITNESS (purposeful exercise): aerobics 130101, biking 130104, climbing
  130108, dancing 130109, gymnastics 130115, hiking 130116, martial arts
  130119, running 130124, skiing/skating/snowboard 130125, cardio equipment
  130128, walking 130131, water sports 130132, weightlifting 130133,
  working out unspecified 130134, yoga 130136.
  SPORT (organized/competitive play) and BROAD (all 1301xx) are robustness sets.
"""
import glob
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

FITNESS = {130101, 130104, 130108, 130109, 130115, 130116, 130119, 130124,
           130125, 130128, 130131, 130132, 130133, 130134, 130136}
SPORT = {130102, 130103, 130107, 130113, 130114, 130117, 130120, 130121,
         130122, 130123, 130126, 130127, 130130, 130135}
LABELS = {
    130101: "Aerobics", 130104: "Biking", 130108: "Climbing/caving",
    130109: "Dancing", 130115: "Gymnastics", 130116: "Hiking",
    130119: "Martial arts", 130124: "Running", 130125: "Ski/skate/snowboard",
    130128: "Cardio equipment", 130131: "Walking", 130132: "Water sports",
    130133: "Weightlifting", 130134: "Working out, unspec.",
    130136: "Yoga",
}
ERAS = [(2003, 2007, "2003-07"), (2008, 2012, "2008-12"),
        (2013, 2019, "2013-19"), (2021, 2025, "2021-25")]


def find_file(pat):
    hits = sorted(glob.glob(str(RAW / pat)))
    assert hits, f"missing {pat} in {RAW} — run src/download.py"
    return hits[0]


def load():
    act = pd.read_csv(find_file("atusact*.dat"),
                      usecols=["TUCASEID", "TUACTIVITY_N", "TUACTDUR",
                               "TUSTARTTIM", "TRCODEP", "TEWHERE"],
                      dtype={"TRCODEP": str}, low_memory=False)
    who = pd.read_csv(find_file("atuswho*.dat"),
                      usecols=["TUCASEID", "TUACTIVITY_N", "TUWHO_CODE"])
    resp = pd.read_csv(find_file("atusresp*.dat"),
                       usecols=["TUCASEID", "TULINENO", "TUYEAR", "TUDIARYDAY",
                                "TUFNWGTP"],
                       low_memory=False)
    rost = pd.read_csv(find_file("atusrost*.dat"),
                       usecols=["TUCASEID", "TULINENO", "TEAGE", "TESEX"])
    for df in (act, who, resp, rost):
        df.columns = [c.upper() for c in df.columns]
    act["TRCODE"] = act["TRCODEP"].astype(int)
    resp = resp.rename(columns={"TUFNWGTP": "TUFINLWGT"})
    resp = resp.merge(rost, on=["TUCASEID", "TULINENO"], how="left")
    return act, who, resp


def companion_table(who):
    """One row per activity episode with companion flags."""
    w = who[who["TUWHO_CODE"] > 0].copy()
    g = w.groupby(["TUCASEID", "TUACTIVITY_N"])["TUWHO_CODE"].agg(list)
    rows = pd.DataFrame({"codes": g})
    c = rows["codes"]
    rows["alone"] = c.apply(lambda s: set(s) <= {18, 19})
    rows["friend"] = c.apply(lambda s: 54 in s)
    rows["partner"] = c.apply(lambda s: bool({20, 21} & set(s)))
    rows["hh_family"] = c.apply(lambda s: bool({22, 23, 24, 25, 26, 27, 28, 29, 30} & set(s)))
    rows["nonhh_family"] = c.apply(lambda s: bool({40, 51, 52, 53} & set(s)))
    rows["other_people"] = c.apply(lambda s: bool({55, 56, 57, 58, 59, 60, 61, 62, 63} & set(s)))
    rows["n_code_groups"] = c.apply(len)

    def primary(r):
        if r["alone"]:
            return "Alone"
        if r["friend"]:
            return "Friends"
        if r["partner"]:
            return "Spouse/partner"
        if r["hh_family"] or r["nonhh_family"]:
            return "Family"
        return "Other people"
    rows["companion"] = rows.apply(primary, axis=1)
    return rows.reset_index()


def wratio(df, num_mask, den_mask, wcol="TUFINLWGT"):
    d = df[den_mask]
    if d[wcol].sum() == 0:
        return np.nan
    return float((d.loc[num_mask.loc[d.index], wcol] * 1.0).sum() / d[wcol].sum()) \
        if False else float(d.loc[num_mask[d.index], wcol].sum() / d[wcol].sum())


def wshare(df, mask):
    """Weighted share of rows in df satisfying mask (mask aligned to df)."""
    w = df["TUFINLWGT"]
    return float(w[mask].sum() / w.sum())


def wmean(df, col, mask=None):
    d = df if mask is None else df[mask]
    return float(np.average(d[col], weights=d["TUFINLWGT"]))


def cluster_ratio_se(df, value_col, wcol="TUFINLWGT"):
    """Cluster-robust (respondent) SE for a weighted ratio sum(w*v)/sum(w),
    v in {0,1} at episode level, clusters = respondents."""
    g = df.groupby("TUCASEID").apply(
        lambda x: pd.Series({"a": (x[wcol] * x[value_col]).sum(), "b": x[wcol].sum()}),
        include_groups=False)
    r = g["a"].sum() / g["b"].sum()
    u = g["a"] - r * g["b"]
    n = len(g)
    var = (n / (n - 1)) * (u ** 2).sum() / (g["b"].sum() ** 2)
    return float(r), float(np.sqrt(var))


def era_of(y):
    for lo, hi, lab in ERAS:
        if lo <= y <= hi:
            return lab
    return None


def main():
    act, who, resp = load()
    comp = companion_table(who)
    rcols = ["TUCASEID", "TUYEAR", "TEAGE", "TESEX", "TUFINLWGT", "TUDIARYDAY"]
    rcols = [c for c in rcols if c in resp.columns]
    resp = resp[rcols].copy()
    resp["weekend"] = resp["TUDIARYDAY"].isin([1, 7])

    ex = act[(act["TRCODE"] >= 130100) & (act["TRCODE"] < 130200)].copy()
    ex = ex.merge(comp, on=["TUCASEID", "TUACTIVITY_N"], how="left")
    ex = ex.merge(resp, on="TUCASEID", how="left")
    # a handful of episodes have no usable who record (refused / not asked);
    # drop them so every companion flag is a clean bool
    ex = ex[ex["alone"].notna()].copy()
    for f in ["alone", "friend", "partner", "hh_family", "nonhh_family",
              "other_people"]:
        ex[f] = ex[f].astype(bool)
    ex = ex[ex["TUYEAR"] != 2020]  # pandemic collection break; kept out of trends
    ex["set"] = np.where(ex["TRCODE"].isin(FITNESS), "fitness",
                         np.where(ex["TRCODE"].isin(SPORT), "sport", "other1301"))
    ex["hour"] = pd.to_datetime(ex["TUSTARTTIM"], format="%H:%M:%S",
                                 errors="coerce").dt.hour
    ex["at_home"] = ex["TEWHERE"] == 1
    ex["at_gym"] = ex["TEWHERE"] == 31
    ex["era"] = ex["TUYEAR"].apply(era_of)
    ex["ageband"] = pd.cut(ex["TEAGE"], [14, 24, 34, 44, 54, 64, 120],
                           labels=["15-24", "25-34", "35-44", "45-54", "55-64", "65+"])
    ex.to_parquet(ROOT / "data" / "episodes.parquet", index=False)

    fit = ex[ex["set"] == "fitness"].copy()
    R = {"n_respondents": int(resp["TUCASEID"].nunique()),
         "n_fitness_episodes": int(len(fit)),
         "years": [int(fit["TUYEAR"].min()), int(fit["TUYEAR"].max())]}

    # ---- yearly series (fitness) ----
    ys = []
    for y, d in fit.groupby("TUYEAR"):
        ys.append({"year": int(y),
                   "participation_note": None,
                   "alone_share_min": wshare(d.assign(x=d["alone"] * d["TUACTDUR"]),
                                             d["alone"] * d["TUACTDUR"] > -1) if False else
                                      float((d.loc[d["alone"], "TUFINLWGT"] * d.loc[d["alone"], "TUACTDUR"]).sum()
                                            / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
                   "alone_share_ep": wshare(d, d["alone"]),
                   "friend_share_min": float((d.loc[d["friend"], "TUFINLWGT"] * d.loc[d["friend"], "TUACTDUR"]).sum()
                                             / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
                   "partner_share_min": float((d.loc[d["partner"], "TUFINLWGT"] * d.loc[d["partner"], "TUACTDUR"]).sum()
                                              / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
                   "mean_dur_alone": wmean(d, "TUACTDUR", d["alone"]),
                   "mean_dur_social": wmean(d, "TUACTDUR", ~d["alone"])})
    yearly = pd.DataFrame(ys)
    yearly.to_csv(OUT / "yearly.csv", index=False)
    R["yearly"] = ys

    # participation + minutes per capita by year (respondent level)
    fit_resp = fit.groupby("TUCASEID")["TUACTDUR"].sum().rename("fitmin")
    rr = resp[resp["TUYEAR"] != 2020].set_index("TUCASEID").join(fit_resp)
    rr["fitmin"] = rr["fitmin"].fillna(0)
    part = rr.groupby("TUYEAR").apply(
        lambda d: pd.Series({
            "participation": float(d.loc[d["fitmin"] > 0, "TUFINLWGT"].sum() / d["TUFINLWGT"].sum()),
            "min_per_capita": float((d["fitmin"] * d["TUFINLWGT"]).sum() / d["TUFINLWGT"].sum())}),
        include_groups=False).reset_index()
    part.to_csv(OUT / "participation.csv", index=False)
    R["participation"] = part.to_dict("records")

    # ---- era table: fitness + robustness sets ----
    era_rows = []
    for setname, d0 in [("fitness", fit), ("sport", ex[ex["set"] == "sport"]),
                        ("broad1301", ex)]:
        for lab in [e[2] for e in ERAS]:
            d = d0[d0["era"] == lab]
            if len(d) < 200:
                continue
            era_rows.append({
                "set": setname, "era": lab, "n_episodes": int(len(d)),
                "alone_share_min": float((d.loc[d["alone"], "TUFINLWGT"] * d.loc[d["alone"], "TUACTDUR"]).sum()
                                         / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
                "alone_share_ep": wshare(d, d["alone"]),
                "friend_share_min": float((d.loc[d["friend"], "TUFINLWGT"] * d.loc[d["friend"], "TUACTDUR"]).sum()
                                          / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
                "partner_share_min": float((d.loc[d["partner"], "TUFINLWGT"] * d.loc[d["partner"], "TUACTDUR"]).sum()
                                           / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
                "family_share_min": float((d.loc[d["hh_family"] | d["nonhh_family"], "TUFINLWGT"]
                                           * d.loc[d["hh_family"] | d["nonhh_family"], "TUACTDUR"]).sum()
                                          / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
                "mean_dur": wmean(d, "TUACTDUR"),
                "mean_dur_alone": wmean(d, "TUACTDUR", d["alone"]),
                "mean_dur_social": wmean(d, "TUACTDUR", ~d["alone"]),
                "home_share_min": float((d.loc[d["at_home"], "TUFINLWGT"] * d.loc[d["at_home"], "TUACTDUR"]).sum()
                                        / (d["TUFINLWGT"] * d["TUACTDUR"]).sum())})
    era_df = pd.DataFrame(era_rows)
    era_df.to_csv(OUT / "era_table.csv", index=False)
    R["era_table"] = era_rows

    # headline SEs: alone share of minutes, first vs last era (fitness)
    ses = {}
    for lab in ["2003-07", "2021-25"]:
        d = fit[fit["era"] == lab].copy()
        d["a"] = d["TUFINLWGT"] * d["TUACTDUR"] * d["alone"]
        d["b"] = d["TUFINLWGT"] * d["TUACTDUR"]
        g = d.groupby("TUCASEID")[["a", "b"]].sum()
        r = g["a"].sum() / g["b"].sum()
        u = g["a"] - r * g["b"]
        se = float(np.sqrt((len(g) / (len(g) - 1)) * (u ** 2).sum()) / g["b"].sum())
        ses[lab] = {"alone_share_min": float(r), "se": se, "n_resp": int(len(g))}
    R["headline_ses"] = ses

    # ---- the gym itself: share of fitness minutes at a gym/health club,
    # and who is with you there (TEWHERE = 31) ----
    gym = []
    for lab in [e[2] for e in ERAS]:
        d = fit[fit["era"] == lab]
        gd = d[d["at_gym"]]
        gym.append({
            "era": lab, "n_gym_episodes": int(len(gd)),
            "gym_share_min": float((gd["TUFINLWGT"] * gd["TUACTDUR"]).sum()
                                   / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
            "gym_alone_share_min": float((gd.loc[gd["alone"], "TUFINLWGT"] * gd.loc[gd["alone"], "TUACTDUR"]).sum()
                                         / (gd["TUFINLWGT"] * gd["TUACTDUR"]).sum()) if len(gd) else None,
            "gym_friend_share_min": float((gd.loc[gd["friend"], "TUFINLWGT"] * gd.loc[gd["friend"], "TUACTDUR"]).sum()
                                          / (gd["TUFINLWGT"] * gd["TUACTDUR"]).sum()) if len(gd) else None,
            "away_nongym_alone_share_min": float(
                (d.loc[(~d["at_home"]) & (~d["at_gym"]) & d["alone"], "TUFINLWGT"]
                 * d.loc[(~d["at_home"]) & (~d["at_gym"]) & d["alone"], "TUACTDUR"]).sum()
                / (d.loc[(~d["at_home"]) & (~d["at_gym"]), "TUFINLWGT"]
                   * d.loc[(~d["at_home"]) & (~d["at_gym"]), "TUACTDUR"]).sum())})
    R["gym"] = gym
    pd.DataFrame(gym).to_csv(OUT / "gym.csv", index=False)

    # ---- by activity (fitness codes) ----
    ba = []
    for code, d in fit.groupby("TRCODE"):
        if len(d) < 300:
            continue
        e1 = d[d["era"] == "2003-07"]
        e4 = d[d["era"] == "2021-25"]
        ba.append({"code": int(code), "label": LABELS.get(int(code), str(code)),
                   "n": int(len(d)),
                   "alone_min_all": float((d.loc[d["alone"], "TUFINLWGT"] * d.loc[d["alone"], "TUACTDUR"]).sum()
                                          / (d["TUFINLWGT"] * d["TUACTDUR"]).sum()),
                   "alone_min_0307": float((e1.loc[e1["alone"], "TUFINLWGT"] * e1.loc[e1["alone"], "TUACTDUR"]).sum()
                                           / (e1["TUFINLWGT"] * e1["TUACTDUR"]).sum()) if len(e1) > 50 else None,
                   "alone_min_2125": float((e4.loc[e4["alone"], "TUFINLWGT"] * e4.loc[e4["alone"], "TUACTDUR"]).sum()
                                           / (e4["TUFINLWGT"] * e4["TUACTDUR"]).sum()) if len(e4) > 50 else None,
                   "dur_alone": wmean(d, "TUACTDUR", d["alone"]),
                   "dur_social": wmean(d, "TUACTDUR", ~d["alone"]),
                   "friend_min": float((d.loc[d["friend"], "TUFINLWGT"] * d.loc[d["friend"], "TUACTDUR"]).sum()
                                       / (d["TUFINLWGT"] * d["TUACTDUR"]).sum())})
    ba_df = pd.DataFrame(ba).sort_values("n", ascending=False)
    ba_df.to_csv(OUT / "by_activity.csv", index=False)
    R["by_activity"] = ba_df.to_dict("records")

    # ---- companion class durations + counts (fitness, pooled) ----
    cc = []
    for name, d in fit.groupby("companion"):
        cc.append({"companion": name, "n": int(len(d)),
                   "share_ep": wshare(fit, fit["companion"] == name),
                   "mean_dur": wmean(d, "TUACTDUR"),
                   "median_dur": float(d["TUACTDUR"].median())})
    R["companion_classes"] = sorted(cc, key=lambda z: -z["share_ep"])

    # ---- demographics: alone share by age band x era, sex x era ----
    demo = []
    for dim in ["ageband", "TESEX"]:
        for key, d in fit.groupby(dim, observed=True):
            for lab in ["2003-07", "2021-25"]:
                dd = d[d["era"] == lab]
                if len(dd) < 200:
                    continue
                demo.append({"dim": dim, "group": str(key), "era": lab, "n": int(len(dd)),
                             "alone_share_min": float((dd.loc[dd["alone"], "TUFINLWGT"] * dd.loc[dd["alone"], "TUACTDUR"]).sum()
                                                      / (dd["TUFINLWGT"] * dd["TUACTDUR"]).sum()),
                             "friend_share_min": float((dd.loc[dd["friend"], "TUFINLWGT"] * dd.loc[dd["friend"], "TUACTDUR"]).sum()
                                                       / (dd["TUFINLWGT"] * dd["TUACTDUR"]).sum()),
                             "partner_share_min": float((dd.loc[dd["partner"], "TUFINLWGT"] * dd.loc[dd["partner"], "TUACTDUR"]).sum()
                                                        / (dd["TUFINLWGT"] * dd["TUACTDUR"]).sum())})
    pd.DataFrame(demo).to_csv(OUT / "demographics.csv", index=False)
    R["demographics"] = demo

    # ---- time of day ----
    fit["hourblock"] = pd.cut(fit["hour"], [-1, 5, 8, 11, 15, 18, 21, 24],
                              labels=["<6a", "6-8a", "9-11a", "12-3p", "4-6p", "7-9p", "10p+"])
    hod = []
    for key, d in fit.groupby("hourblock", observed=True):
        hod.append({"block": str(key), "n": int(len(d)),
                    "alone_share_ep": wshare(d, d["alone"]),
                    "share_of_episodes": wshare(fit, fit["hourblock"] == key)})
    R["time_of_day"] = hod

    # ---- home vs away ----
    hw = []
    for lab in [e[2] for e in ERAS]:
        d = fit[fit["era"] == lab]
        for where, dd in [("home", d[d["at_home"]]), ("away", d[~d["at_home"]])]:
            hw.append({"era": lab, "where": where, "n": int(len(dd)),
                       "alone_share_min": float((dd.loc[dd["alone"], "TUFINLWGT"] * dd.loc[dd["alone"], "TUACTDUR"]).sum()
                                                / (dd["TUFINLWGT"] * dd["TUACTDUR"]).sum()) if len(dd) else None})
    R["home_away"] = hw

    # ---- social spillover: same-day socializing minutes by exercise type ----
    soc = act[(act["TRCODE"] >= 120100) & (act["TRCODE"] < 120200)].groupby("TUCASEID")["TUACTDUR"].sum()
    day = fit.groupby("TUCASEID").agg(any_alone=("alone", "max"), any_social=("alone", lambda s: (~s).max()))
    day = day.join(resp.set_index("TUCASEID")[["TUFINLWGT"]]).join(soc.rename("socmin"))
    day["socmin"] = day["socmin"].fillna(0)
    day["kind"] = np.where(day["any_social"], "had social exercise", "exercise all alone")
    R["spillover"] = {k: wmean(d, "socmin") for k, d in day.groupby("kind")}

    # ---- decomposition: how much of the alone-share rise is *where* exercise
    # happens (home share up) vs *how* each place changed? Kitagawa/Oaxaca
    # two-fold split on location (home vs away), era 2003-07 -> 2021-25 ----
    def loc_stats(d):
        out = {}
        for where, dd in [("home", d[d["at_home"]]), ("away", d[~d["at_home"]])]:
            tot = (d["TUFINLWGT"] * d["TUACTDUR"]).sum()
            out[where] = {
                "share": float((dd["TUFINLWGT"] * dd["TUACTDUR"]).sum() / tot),
                "alone": float((dd.loc[dd["alone"], "TUFINLWGT"] * dd.loc[dd["alone"], "TUACTDUR"]).sum()
                               / (dd["TUFINLWGT"] * dd["TUACTDUR"]).sum())}
        return out
    s1 = loc_stats(fit[fit["era"] == "2003-07"])
    s4 = loc_stats(fit[fit["era"] == "2021-25"])
    comp_eff = sum((s4[w]["share"] - s1[w]["share"]) * s1[w]["alone"] for w in s1)
    within_eff = sum(s4[w]["share"] * (s4[w]["alone"] - s1[w]["alone"]) for w in s1)
    R["decomposition"] = {"era1": s1, "era4": s4,
                          "composition_pp": float(comp_eff * 100),
                          "within_pp": float(within_eff * 100),
                          "total_pp": float((comp_eff + within_eff) * 100)}

    (OUT / "results.json").write_text(json.dumps(R, indent=1, default=str))
    print(json.dumps({k: R[k] for k in ["n_respondents", "n_fitness_episodes", "headline_ses"]}, indent=1))
    print(era_df[era_df["set"] == "fitness"].to_string())


if __name__ == "__main__":
    main()
