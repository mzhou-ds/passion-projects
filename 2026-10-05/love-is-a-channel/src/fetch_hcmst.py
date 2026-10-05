#!/usr/bin/env python3
"""
Fetch the HCMST 2017-2022 public-use file from Stanford and build the
cleaned, analysis-ready couple-level extract used by analyze.py.

Source (public use, no registration required for this "small public" file):
  Landing page : https://data.stanford.edu/hcmst2017
  Direct file  : https://stacks.stanford.edu/file/druid:hg921sg6829/HCMST%202017%20to%202022%20small%20public%20version%202.2.dta

Citation: Rosenfeld, Michael J., Reuben J. Thomas, Sonia Hausen, et al.
"How Couples Meet and Stay Together 2017-2022" [computer file], public
version 2.2. Stanford, CA: Stanford University Libraries.

The raw .dta (~4 MB) is downloaded to data/raw/ and is NOT committed
(see .gitignore in this folder). Only the derived couple-level extract
(data/couples.csv, one row per respondent's current/most-recent partner)
and aggregates are committed.
"""
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent.parent
RAW = HERE / "data" / "raw"
OUT = HERE / "data" / "couples.csv"
URL = ("https://stacks.stanford.edu/file/druid:hg921sg6829/"
       "HCMST%202017%20to%202022%20small%20public%20version%202.2.dta")
DTA = RAW / "hcmst_2017_2022_public_v2_2.dta"


def download():
    RAW.mkdir(parents=True, exist_ok=True)
    if DTA.exists() and DTA.stat().st_size > 1_000_000:
        print(f"already have {DTA} ({DTA.stat().st_size/1e6:.1f} MB)")
        return
    print(f"downloading {URL}")
    subprocess.run(["curl", "-sL", URL, "-o", str(DTA)], check=True)
    print(f"saved {DTA} ({DTA.stat().st_size/1e6:.1f} MB)")


# ---------------------------------------------------------------- channel --
def build_channel(df: pd.DataFrame) -> pd.Series:
    """Mutually exclusive 'primary meeting channel' from the Q24 codes.

    Q24 is multi-code (couples can be coded friend AND school, etc.).
    Priority order is an analytic choice, stated here and in the README:
    online > friends > family > school > work > bar/social > church > other.
    Online wins ties because the research question is about the internet
    displacing intermediaries; every multi-coded couple is also counted
    in the 'any-code' descriptive table in analyze.py.
    """
    def eq(col, val=1):
        return (df[col] == val) if col in df else pd.Series(False, index=df.index)

    online = eq("w1_q24_met_online")
    friends = eq("w1_q24_met_through_friend")
    family = eq("w1_q24_met_through_family")
    school = eq("w1_q24_school") | eq("w1_q24_college")
    work = (eq("w1_q24_met_as_through_cowork") | eq("w1_q24_work_neighbors")
            | eq("w1_q24_R_cowork") | eq("w1_q24_P_cowork"))
    bar = (eq("w1_q24_bar_restaurant") | eq("w1_q24_party")
           | eq("w1_q24_public"))
    church = eq("w1_q24_church")

    ch = pd.Series("other", index=df.index, dtype=object)
    for mask, name in [(church, "church"), (bar, "bar_social"),
                       (work, "work"), (school, "school"),
                       (family, "family"), (friends, "friends"),
                       (online, "online")]:
        ch[mask] = name  # later (higher-priority) assignments overwrite
    # couples with no usable Q24 coding at all -> missing
    any_code = online | friends | family | school | work | bar | church
    ch[~any_code] = np.nan
    return ch


def main():
    download()
    md5 = hashlib.md5(DTA.read_bytes()).hexdigest()
    print("md5:", md5)

    df = pd.read_stata(DTA, convert_categoricals=False)
    print("raw shape:", df.shape)

    # keep respondents who have ever had a partner (status 1,2,3)
    df = df[df["w1_partnership_status"].isin([1, 2, 3])].copy()
    print("with current/past partner:", df.shape)

    out = pd.DataFrame(index=df.index)
    out["caseid"] = df["caseid_new"]
    out["weight"] = df["w1_weight_combo"]

    # --- timing -----------------------------------------------------------
    out["year_met"] = df["w1_q21a_year"]
    out["rel_start_year"] = df["w1_q21b_year"]
    out["rel_start_frac"] = df["w1_year_fraction_relstart"]
    out["met_frac"] = df["w1_year_fraction_met"]
    # relationship start falls back to year met when Q21B missing
    out["start_frac"] = out["rel_start_frac"].fillna(out["met_frac"])
    out["start_year"] = out["start_frac"].apply(
        lambda x: int(np.floor(x)) if pd.notna(x) else np.nan)

    out["age_resp_2017"] = df["w1_ppage"]
    out["age_at_start"] = out["age_resp_2017"] - (2017.55 - out["start_frac"])
    out["time_met_to_rel_yrs"] = df["w1_time_from_met_to_rel"]

    # --- channel ----------------------------------------------------------
    out["channel"] = build_channel(df)
    out["met_online"] = (df["w1_q24_met_online"] == 1).astype(float)
    out["met_via_app"] = (df["w1_q32_met_online_phone_apps"] == 1).astype(float)
    out["met_thru_friends"] = (df["w1_q24_met_through_friend"] == 1).astype(float)
    out["met_thru_family"] = (df["w1_q24_met_through_family"] == 1).astype(float)

    # --- status at baseline / follow-up -----------------------------------
    out["partnered_w1"] = df["w1_partnership_status"].isin([1, 2]).astype(int)
    out["married_w1"] = (df["w1_married"] == 1).astype(float)
    out["same_sex"] = (df["w1_same_sex_couple"] == 1).astype(float)
    out["in_w2"] = df["w2_partner_type"].isin([1, 2, 3]).astype(int)
    out["in_w3"] = df["w3_partner_type"].isin([1, 2, 3]).astype(int)
    out["unpartnered_w2"] = (df["w2_partner_type"] == 3).astype(int)
    out["unpartnered_w3"] = (df["w3_partner_type"] == 3).astype(int)

    # breakup years (retrospective w1 + prospective w2/w3)
    out["breakup_year_w1"] = df["w1_q21e_year"]
    out["partner_died_year_w1"] = df["w1_q21f_year"]
    out["breakup_year_w2"] = df["yr_breakup_combo"]
    out["breakup_year_w3"] = df["w3_breakup_year"]

    # --- covariates ---------------------------------------------------------
    out["educ_resp_cat"] = df["w1_ppeducat"]          # 1..4
    out["partner_yrsed"] = df["w1_partner_yrsed"]
    # map partner years-of-ed to the same rough 1..4 ladder
    out["educ_partner_cat"] = pd.cut(
        out["partner_yrsed"], bins=[-1, 11, 12, 15, 99],
        labels=[1, 2, 3, 4]).astype(float)
    out["educ_gap"] = (out["educ_resp_cat"] - out["educ_partner_cat"]).abs()
    out["mother_educ_gap"] = (
        df["w1_subject_mother_yrsed"] - df["w1_partner_mother_yrsed"]).abs()
    out["race_resp"] = df["w1_ppethm"]                  # 1..5 (see codebook)
    out["female"] = (df["w1_ppgender"] == 2).astype(float)
    out["times_married"] = df["w1_q17"]
    # cohabited before marriage (or cohab at all for the unmarried)
    cohab_frac = df["w1_year_fraction_first_cohab"]
    marry_frac = (df["w1_q21d_year"]
                  + (df["w1_q21d_month"].fillna(6) - 0.5) / 12)
    out["cohab_before_marriage"] = np.where(
        df["w1_married"] == 1,
        (cohab_frac < marry_frac).astype(float),
        (cohab_frac.notna()).astype(float))
    out.loc[cohab_frac.isna(), "cohab_before_marriage"] = np.nan

    # --- survival outcome: years from relationship start -------------------
    breakup_frac = pd.Series(np.nan, index=df.index)
    for col in ["breakup_year_w3", "breakup_year_w2", "breakup_year_w1"]:
        breakup_frac = breakup_frac.fillna(out[col] + 0.5)
    died = out["partner_died_year_w1"].notna() & out["breakup_year_w1"].isna()

    last_seen = np.where(out["in_w3"] == 1, 2022.6,
                np.where(out["in_w2"] == 1, 2020.6, 2017.55))
    out["broke_up"] = np.where(breakup_frac.notna() & ~died, 1, 0)
    end_frac = breakup_frac.copy()
    end_frac[out["broke_up"] == 0] = last_seen[out["broke_up"] == 0]
    # past partners who broke up before 2017 but have no follow-up: censor
    # at breakup is the event; if somehow no breakup year, drop below.
    out["duration_yrs"] = end_frac - out["start_frac"]
    out["end_frac"] = end_frac

    # prospective follow-up clock (months since the 2017 interview)
    fu_end = np.where(out["broke_up"] == 1,
                      np.minimum(breakup_frac, 2022.6), last_seen)
    out["fu_months"] = (fu_end - 2017.55) * 12
    out.loc[out["partnered_w1"] == 0, "fu_months"] = np.nan

    # sanity filters
    keep = (out["start_year"].between(1940, 2017)
            & out["duration_yrs"].between(0.05, 80)
            & out["age_at_start"].between(13, 75)
            & out["channel"].notna())
    out = out[keep].copy()
    print("analysis rows:", out.shape)
    print(out["channel"].value_counts(dropna=False).to_dict())

    out.to_csv(OUT, index=False)
    print("wrote", OUT)

    prov = HERE / "data" / "PROVENANCE.md"
    prov.write_text(f"""# Data provenance

- Dataset: How Couples Meet and Stay Together (HCMST) 2017-2022,
  public version 2.2 ("small public" file), Rosenfeld et al., Stanford.
- Landing page: https://data.stanford.edu/hcmst2017
- File downloaded: {URL}
- Raw .dta md5 (this run): `{md5}` — raw file is kept in `data/raw/`
  and git-ignored; re-download with `python3 src/fetch_hcmst.py`.
- Citation: Rosenfeld, Michael J., Reuben J. Thomas, Sonia Hausen,
  et al. 2019+. "How Couples Meet and Stay Together 2017-2022,"
  public version 2.2 [computer file]. Stanford, CA: Stanford
  University Libraries. https://data.stanford.edu/hcmst2017
- `couples.csv` here is a derived, de-identified analytic extract
  (one row per respondent's current or most recent partner) built by
  `src/fetch_hcmst.py`. No names or geography below national level.
""")
    print("wrote", prov)


if __name__ == "__main__":
    sys.exit(main())
