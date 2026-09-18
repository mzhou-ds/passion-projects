"""Part 4: Edmonton's championship window, 2026-27 through 2030-31.

Method
  1. Each skater's baseline = last-3-season 5v5 ON-ICE xGF/60 (MoneyPuck
     OnIce_F_xGoals): the team's chance-creation rate with him on the ice.
     TOI-weighted mean of on-ice rates ~= team xGF/60 by construction, so the
     level is structural; a small kappa calibration absorbs residual bias.
  2. Age-adjust with delta-method aging curves; weight by expected 5v5 TOI
     (players keep roughly their historical minutes).
  3. Team 5v5 xGA/60 = league mean + defensive effect scaled by D-corps age.
  4. Goaltending: Jarry's actual last-3yr 5v5 GSAA/60 (~average).
  5. Special teams: elite PP while 97/29/2 share PP1; league-average PK.
  6. All nine features -> Cup-finalist XGBoost -> P(Cup Final) per season.
  7. Cap ledger per season vs announced/projected ceilings.

Scenarios
  A "Pay the captain": McDavid re-signs summer 2028 (8 x $17M).
  B "The Decision": McDavid walks; Oilers sign a star UFA winger ($11M).
"""
import numpy as np
import pandas as pd
import pickle
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW = "data/raw"
CAP = {2026: 104.0, 2027: 113.5, 2028: 121.5, 2029: 130.0, 2030: 139.0}  # 28+: ~+7%/yr assumed
SEASONS = [2026, 2027, 2028, 2029, 2030]

# ---------------- baselines ----------------
def load_skaters():
    frames = []
    for s in (2023, 2024, 2025):
        d = pd.read_csv(f"{RAW}/mp_{s}_skaters.csv",
                        usecols=["name", "team", "position", "situation",
                                 "icetime", "OnIce_F_xGoals"])
        d = d[d["situation"] == "5on5"]
        d["s"] = s
        frames.append(d)
    sk = pd.concat(frames, ignore_index=True)
    sk = sk[np.isfinite(sk["OnIce_F_xGoals"])]
    sk["onice"] = sk["OnIce_F_xGoals"] / (sk["icetime"] / 3600.0)
    g = sk.groupby(["name", "position"]).apply(
        lambda x: pd.Series({
            "base": np.average(x["onice"], weights=x["icetime"]),
            "toi": x["icetime"].sum() / 3.0}),          # avg 5v5 sec/season
        include_groups=False).reset_index()
    return g

BASE = load_skaters()
PRIOR = {p: BASE[(BASE["position"].isin(p)) & (BASE["toi"] > 30000)]["base"].median()
         for p in [("C", "L", "R"), ("D",)]}

def base_of(name, pos_hint):
    """Shrunk on-ice xGF/60 baseline + expected 5v5 TOI/season."""
    key = ("C", "L", "R") if pos_hint != "D" else ("D",)
    prior = PRIOR[key]
    hit = BASE[BASE["name"].str.lower() == name.lower()]
    if len(hit):
        r = hit.iloc[0]
        if np.isfinite(r["base"]):
            w = min(1.0, r["toi"] / 45000.0)   # ~750 5v5 min/season = full weight
            toi = r["toi"] if r["toi"] > 30000 else None
            return w * r["base"] + (1 - w) * prior, r["position"], toi
    return prior, pos_hint, None

# ---------------- age curves ----------------
AC = pd.read_csv("data/processed/age_curve.csv")
AC = AC[AC["metric"] == "xG60"].set_index(["pos", "age"])["factor"].to_dict()

def age_factor(pos, age):
    key = "D" if pos == "D" else "F"
    return AC[(key, int(np.clip(round(age), 19, 39)))]

# ---------------- rosters ----------------
# (name, pos, age in 2026-27, aav $M)
CORE_2627 = [
    ("Connor McDavid", "C", 29, 12.5), ("Leon Draisaitl", "C", 30, 14.0),
    ("Zach Hyman", "F", 34, 5.5), ("Ryan Nugent-Hopkins", "F", 33, 5.125),
    ("Vasily Podkolzin", "F", 25, 2.95), ("Trent Frederic", "F", 28, 3.85),
    ("Mattias Janmark", "F", 34, 1.45), ("Matt Savoie", "F", 23, 0.8867),
    ("Isaac Howard", "F", 22, 0.9725), ("Josh Samanski", "F", 24, 0.975),
    ("Connor Clattenburg", "F", 21, 0.9283),
    ("Evan Bouchard", "D", 27, 10.5), ("Darnell Nurse", "D", 31, 9.25),
    ("Jake Walman", "D", 30, 7.0), ("Mattias Ekholm", "D", 36, 4.0),
    ("Ty Emberson", "D", 26, 1.3),
]
FILL_TOI = {"F": 32000, "D": 40000}   # ~4th-line / 3rd-pair 5v5 sec per season

def build_rosters(scenario):
    R = {}
    ros = [dict(name=n, pos=p, age=a, aav=v) for n, p, a, v in CORE_2627]
    ros += [dict(name="FILL F (FA)", pos="F", age=27, aav=2.0),
            dict(name="FILL D (FA)", pos="D", age=27, aav=2.0)]
    campbell = {2026: 2.6, 2027: 1.5}
    R[2026] = (ros, campbell[2026], dict(goalie="Tristan Jarry", gsaa=0.024, gaav=6.875))
    # 2027-28: Janmark, Emberson walk; RFAs re-signed
    ros = [r for r in ros if r["name"] not in
           ("Mattias Janmark", "Ty Emberson", "FILL F (FA)", "FILL D (FA)")]
    for r in ros:
        r["age"] += 1
        if r["name"] == "Matt Savoie": r["aav"] = 1.6
        if r["name"] == "Josh Samanski": r["aav"] = 1.2
    ros += [dict(name="FILL F (FA)", pos="F", age=27, aav=2.2),
            dict(name="FILL F2 (FA)", pos="F", age=28, aav=2.2),
            dict(name="FILL D (FA)", pos="D", age=27, aav=2.5)]
    R[2027] = (ros, campbell[2027], dict(goalie="Tristan Jarry", gsaa=0.024, gaav=6.875))
    # 2028-29: the McDavid summer
    ros = [{**r, "age": r["age"] + 1} for r in ros
           if r["name"] not in ("FILL F (FA)", "FILL F2 (FA)", "FILL D (FA)")]
    for r in ros:
        if r["name"] == "Isaac Howard": r["aav"] = 3.0
        if r["name"] == "Connor Clattenburg": r["aav"] = 1.5
    if scenario == "A":
        ros = [r for r in ros if r["name"] != "Connor McDavid"]
        ros.append(dict(name="Connor McDavid", pos="C", age=31, aav=17.0))
    else:
        ros = [r for r in ros if r["name"] != "Connor McDavid"]
        ros.append(dict(name="STAR WINGER (UFA)", pos="F", age=28, aav=11.0))
    ros.append(dict(name="Zach Hyman", pos="F", age=36, aav=4.0))
    ros += [dict(name="FILL F (FA)", pos="F", age=27, aav=2.5),
            dict(name="FILL F2 (FA)", pos="F", age=28, aav=2.5),
            dict(name="FILL D (FA)", pos="D", age=28, aav=3.0)]
    R[2028] = (ros, 0.0, dict(goalie="Tristan Jarry", gsaa=0.020, gaav=6.0))
    # 2029-30: Ekholm retires; Bouchard re-signs 8x$12M; RNH 3x$5M
    ros = [{**r, "age": r["age"] + 1} for r in ros
           if r["name"] not in ("Mattias Ekholm", "FILL F (FA)", "FILL F2 (FA)",
                                "FILL D (FA)", "Evan Bouchard",
                                "Ryan Nugent-Hopkins")]
    ros.append(dict(name="Evan Bouchard", pos="D", age=30, aav=12.0))
    ros.append(dict(name="Ryan Nugent-Hopkins", pos="F", age=36, aav=5.0))
    ros += [dict(name="FILL F (FA)", pos="F", age=27, aav=2.8),
            dict(name="FILL D (FA)", pos="D", age=27, aav=3.2),
            dict(name="FILL D2 (FA)", pos="D", age=29, aav=3.2)]
    R[2029] = (ros, 0.0, dict(goalie="Tristan Jarry", gsaa=0.015, gaav=6.0))
    # 2030-31: Nurse walks at 35; Hyman's 2yr deal done
    ros = [{**r, "age": r["age"] + 1} for r in ros
           if r["name"] not in ("Darnell Nurse", "Zach Hyman", "FILL F (FA)",
                                "FILL D (FA)", "FILL D2 (FA)")]
    ros += [dict(name="FILL D (FA)", pos="D", age=28, aav=4.5),
            dict(name="FILL D2 (FA)", pos="D", age=27, aav=3.5),
            dict(name="FILL F (FA)", pos="F", age=27, aav=3.0)]
    R[2030] = (ros, 0.0, dict(goalie="Tristan Jarry", gsaa=0.010, gaav=6.0))
    return R

OVERRIDES = {}   # name -> on-ice xGF/60 baseline override

def roster_xgf(roster):
    num = den = 0.0
    for r in roster:
        b, pos, toi = base_of(r["name"], r["pos"])
        if r["name"] in OVERRIDES:
            b = OVERRIDES[r["name"]]
        w = toi if toi else FILL_TOI["F" if r["pos"] != "D" else "D"]
        num += w * b * age_factor(pos, r["age"]) / age_factor(pos, r["age"] - 2)
        den += w
    return num / den

def roster_ddef(roster):
    num = den = 0.0
    for r in roster:
        if r["pos"] == "D":
            _, _, toi = base_of(r["name"], "D")
            w = toi if toi else FILL_TOI["D"]
            ddef = 1.0 if r["age"] <= 30 else 1.03 ** (r["age"] - 30)
            num += w * ddef
            den += w
    return num / den

def calibrate():
    ratios = []
    for s in (2023, 2024, 2025):
        sk = pd.read_csv(f"{RAW}/mp_{s}_skaters.csv")
        sk = sk[(sk["situation"] == "5on5") & (sk["team"] == "EDM")]
        top = sk.nlargest(18, "icetime")
        ros = [dict(name=r["name"], pos=r["position"], age=27) for _, r in top.iterrows()]
        raw = roster_xgf(ros)   # age factor = 1 at ref age
        tm = pd.read_csv(f"{RAW}/mp_{s}_teams.csv")
        row = tm[(tm["name"] == "EDM") & (tm["situation"] == "5on5")].iloc[0]
        actual = row["xGoalsFor"] / (row["iceTime"] / 3600.0)
        ratios.append(actual / raw)
        print(f"  {s}: raw={raw:.3f} actual={actual:.3f} ratio={ratios[-1]:.3f}")
    return float(np.mean(ratios))

def main():
    print("calibrating...")
    kappa = calibrate()
    print(f"kappa={kappa:.3f}")

    tm = pd.read_csv(f"{RAW}/mp_2025_teams.csv")
    t5 = tm[tm["situation"] == "5on5"]
    lg_xga = (t5["xGoalsAgainst"] / (t5["iceTime"] / 3600.0)).mean()
    edm = t5[t5["name"] == "EDM"].iloc[0]
    edm_xga = edm["xGoalsAgainst"] / (edm["iceTime"] / 3600.0)
    delta_2025 = edm_xga - lg_xga
    scored = pd.read_csv("data/processed/cup_model_scored.csv")
    a, b = np.polyfit(scored["xGshare"], scored["corsi"], 1)
    lg_pp = (tm[tm["situation"] == "5on4"]["xGoalsFor"] /
             (tm[tm["situation"] == "5on4"]["iceTime"] / 3600.0)).mean()
    lg_pk = (tm[tm["situation"] == "4on5"]["xGoalsAgainst"] /
             (tm[tm["situation"] == "4on5"]["iceTime"] / 3600.0)).mean()
    edm_pp = float((tm[(tm["situation"] == "5on4") & (tm["name"] == "EDM")]["xGoalsFor"] /
                    (tm[(tm["situation"] == "5on4") & (tm["name"] == "EDM")]["iceTime"] / 3600.0)).mean())
    ddef_2025 = roster_ddef([dict(name=n, pos="D", age=a)
                             for n, a in [("Evan Bouchard", 26), ("Darnell Nurse", 30),
                                          ("Jake Walman", 29), ("Mattias Ekholm", 35),
                                          ("Ty Emberson", 25), ("Brett Kulak", 32)]])
    print(f"lg 5v5 xGA/60={lg_xga:.2f} EDM delta={delta_2025:+.2f} ddef_2025={ddef_2025:.3f}")

    model = pickle.load(open("data/processed/cup_model.pkl", "rb"))
    feats = model["feats"]
    mcd_onice, _, _ = base_of("Connor McDavid", "C")
    OVERRIDES["STAR WINGER (UFA)"] = round(0.90 * mcd_onice, 3)
    print(f"McDavid on-ice xGF60={mcd_onice:.2f} -> star UFA={OVERRIDES['STAR WINGER (UFA)']:.2f}")

    rows = []
    for scenario in ("A", "B"):
        R = build_rosters(scenario)
        for s in SEASONS:
            roster, dead, g = R[s]
            xgf = kappa * roster_xgf(roster)
            xga = lg_xga + delta_2025 * (roster_ddef(roster) / ddef_2025)
            gsaa = g["gsaa"]
            pp = edm_pp if any(r["name"] == "Connor McDavid" for r in roster) else lg_pp
            xgshare = xgf / (xgf + xga)
            f = dict(xGF60=xgf, xGA60=xga, xGshare=xgshare, corsi=a + b * xgshare,
                     GSAA60=gsaa, finish5v5=1.0, PPxGF60=pp, PKxGA60=lg_pk,
                     GD60=xgf - (xga - gsaa))
            p = float(model["model"].predict_proba(
                pd.DataFrame([[f[k] for k in feats]], columns=feats))[0, 1])
            cap_hit = sum(r["aav"] for r in roster) + dead + g["gaav"]
            rows.append(dict(scenario=scenario, season=f"{s}-{str(s+1)[2:]}",
                             xGF60=round(xgf, 2), xGA60=round(xga, 2),
                             xGshare=round(xgshare, 3), GSAA60=round(gsaa, 3),
                             p_final=round(p, 3),
                             cap_hit=round(cap_hit, 1), cap_max=CAP[s],
                             space=round(CAP[s] - cap_hit, 1)))
    df = pd.DataFrame(rows)
    scales = []
    for s in (2023, 2024, 2025):
        t = pd.read_csv(f"{RAW}/mp_{s}_teams.csv")
        a5 = t[(t["name"] == "EDM") & (t["situation"] == "5on5")].iloc[0]
        al = t[(t["name"] == "EDM") & (t["situation"] == "all")].iloc[0]
        gp = a5["games_played"]
        scales.append((al["goalsFor"] / gp) / (a5["goalsFor"] / (a5["iceTime"] / 3600.0)))
    sc = float(np.mean(scales))
    df["pts"] = df.apply(
        lambda r: round(164 * (r["xGF60"] * sc) ** 2 /
                        ((r["xGF60"] * sc) ** 2 + ((r["xGA60"] - r["GSAA60"]) * sc) ** 2), 1),
        axis=1)
    df.to_csv("data/processed/window_forecast.csv", index=False)
    print(df.to_string(index=False))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    for scn, ls, lab in [("A", "-", "A: McDavid re-signs 8x$17M"),
                         ("B", "--", "B: McDavid walks; $11M star UFA")]:
        d = df[df["scenario"] == scn]
        ax1.plot(d["season"], d["p_final"], marker="o", ls=ls, lw=2, label=lab)
    ax1.axhline(2 / 32, color="gray", ls=":", label="average team (2/32)")
    ax1.set_ylabel("P(Cup Final) — model")
    ax1.set_title("Edmonton's championship window, 2026-27 to 2030-31")
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)
    for scn, ls in [("A", "-"), ("B", "--")]:
        d = df[df["scenario"] == scn]
        ax2.plot(d["season"], d["space"], marker="o", ls=ls, lw=2)
    ax2.axhline(0, color="red", ls=":")
    ax2.set_ylabel("cap space ($M)")
    ax2.set_xlabel("season")
    ax2.set_title("Cap space vs rising ceiling (2028-31 ceilings assumed +~7%/yr)")
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("figures/04_window.png", dpi=130)
    print("saved figures/04_window.png")

if __name__ == "__main__":
    main()
