#!/usr/bin/env python3
"""Join the Canada and US extracts and compute the comparison.

Measures
--------
Canada (2021 Census, 25% sample):
  retention_mt[geo][gen] = Chinese mother tongue / Chinese visible minority
      -- share of the heritage population whose first language learned (and
         still understood) is a Chinese language.
  homeuse_given_mt[geo][gen] = share of Chinese-MT persons speaking any
      non-official language at home.
  retention_home[geo][gen] = retention_mt * homeuse_given_mt
      -- derived share of the heritage population still using a non-official
         language at home (approximation: assumes home use is ~0 among
         Chinese-origin persons without Chinese MT; the MT table cannot test
         this directly, so it is labelled a derived estimate).
United States (ACS 2022 1-year PUMS):
  retention_home[nat] = share of Chinese-ancestry persons (ANC1P/ANC2P=706)
      speaking a Chinese language at home (LANP in 1970/2000/2030/2050),
      PWGTP-weighted. Nativity: Native vs Foreign-born (ACS cannot split
      2nd vs 3rd generation: no parental birthplace variable).

The honest comparison is retention_home (CA derived) vs retention_home (US),
plus retention_mt (CA) as the stricter "first language survived" measure.

Also: enclave test -- retention vs co-ethnic density by CMA (CA) and state
(US; state totals from a second PUMS pass over ST+PWGTP).
"""
import csv
import zipfile
from collections import defaultdict

import pandas as pd

ret = pd.read_csv("data/ca_retention.csv")
vm = pd.read_csv("data/ca_vm.csv")
home = pd.read_csv("data/ca_homeuse.csv")
age_ca = pd.read_csv("data/ca_age.csv")
split = pd.read_csv("data/ca_mt_split.csv")
us = pd.read_csv("data/us_retention.csv")
us_age = pd.read_csv("data/us_age.csv")
us_state = pd.read_csv("data/us_state.csv")

# --- Canada headline: retention_mt and derived retention_home ---
vm_tot = vm[vm.age == "Total - Age"].set_index(["geography", "generation"])["chinese_visible_minority"]
ret_idx = ret.set_index(["geography", "generation"])
home_idx = home.set_index(["geography", "generation"])

rows = []
for (geo, gen), r in ret_idx.iterrows():
    denom = vm_tot.loc[(geo, gen)]
    mt_share = r["chinese_mt"] / denom
    hu = home_idx.loc[(geo, gen), "share"]
    rows.append({
        "geography": geo, "generation": gen,
        "chinese_visible_minority": int(denom),
        "chinese_mt": int(r["chinese_mt"]),
        "retention_mt": round(mt_share, 4),
        "homeuse_given_mt": round(hu, 4),
        "retention_home_derived": round(mt_share * hu, 4),
        "chinese_share_of_pop": round(denom / r["population_total"], 4),
    })
ca = pd.DataFrame(rows)
ca.to_csv("data/ca_comparison.csv", index=False)
print(ca[ca.geography == "Canada"].to_string(index=False))

# --- Canada age gradient: retention_mt by age group ---
age_vm = vm.set_index(["geography", "generation", "age"])["chinese_visible_minority"]
age_ret_idx = age_ca.set_index(["geography", "generation", "age"])
arows = []
for (geo, gen, age), r in age_ret_idx.iterrows():
    denom = age_vm.loc[(geo, gen, age)]
    arows.append({"geography": geo, "generation": gen, "age": age,
                  "chinese_vm": int(denom), "chinese_mt": int(r["chinese_mt"]),
                  "retention_mt": round(r["chinese_mt"] / denom, 4) if denom else None})
ca_age = pd.DataFrame(arows)
ca_age.to_csv("data/ca_age_retention.csv", index=False)
print()
print("Canada 2nd-gen retention_mt by age:")
print(ca_age[(ca_age.geography == "Canada") & (ca_age.generation == "Second generation")].to_string(index=False))
print()
print("Canada 1st-gen retention_mt by age:")
print(ca_age[(ca_age.geography == "Canada") & (ca_age.generation == "First generation")].to_string(index=False))
print()
print("Canada 3rd+ retention_mt by age:")
print(ca_age[(ca_age.geography == "Canada") & (ca_age.generation == "Third generation or more")].to_string(index=False))

# --- Mandarin vs Cantonese by generation (Canada) ---
print()
print("Canada mother-tongue split by generation (share of Chinese MT):")
piv = split[split.geography == "Canada"].pivot(index="generation", columns="mother_tongue", values="count")
piv = piv.div(piv.sum(axis=1), axis=0).round(4)
print(piv[["Mandarin", "Yue (Cantonese)", "Min Nan (Chaochow, Teochow, Fukien, Taiwanese)"]].to_string())

# --- US state totals for enclave density ---
zf = zipfile.ZipFile("data/pums_2022_1yr.zip")
state_tot = defaultdict(float)
state_chi = defaultdict(float)
for fname in ["psam_pusa.csv", "psam_pusb.csv"]:
    with zf.open(fname) as fh:
        for chunk in pd.read_csv(fh, usecols=["ST", "PWGTP", "ANC1P", "ANC2P"],
                                 chunksize=300_000):
            w = chunk["PWGTP"].astype(float)
            for st, idx in chunk.groupby("ST").groups.items():
                state_tot[int(st)] += float(w.loc[idx].sum())
            chi = chunk[(chunk["ANC1P"] == 706) | (chunk["ANC2P"] == 706)]
            for st, idx in chi.groupby("ST").groups.items():
                state_chi[int(st)] += float(w.loc[idx].sum())
STATE_NAMES = {6: "California", 36: "New York", 48: "Texas", 53: "Washington",
               25: "Massachusetts", 34: "New Jersey", 17: "Illinois",
               12: "Florida", 39: "Ohio", 42: "Pennsylvania"}
srows = []
for st, tot in state_tot.items():
    srows.append({"state_fips": st, "state": STATE_NAMES.get(st, "Other"),
                  "state_pop": int(tot), "chinese_ancestry": int(state_chi.get(st, 0)),
                  "chinese_share": round(state_chi.get(st, 0) / tot, 5)})
st_df = pd.DataFrame(srows)
# aggregate "Other" states
other = st_df[st_df.state == "Other"]
st_df = st_df[st_df.state != "Other"]
st_df = pd.concat([st_df, pd.DataFrame([{
    "state_fips": 0, "state": "Other states",
    "state_pop": int(other.state_pop.sum()),
    "chinese_ancestry": int(other.chinese_ancestry.sum()),
    "chinese_share": round(other.chinese_ancestry.sum() / other.state_pop.sum(), 5)}])],
    ignore_index=True)
st_df.to_csv("data/us_state_totals.csv", index=False)
us_enclave = us_state.merge(st_df[["state", "chinese_share"]], on="state")
us_enclave.to_csv("data/us_enclave.csv", index=False)
print()
print(us_enclave[us_enclave.nativity == "Native"].sort_values("share", ascending=False).to_string(index=False))

# --- Canada enclave table: 2nd-gen retention vs Chinese share of CMA ---
ca_enc = ca[ca.generation == "Second generation"][["geography", "retention_mt",
    "retention_home_derived", "chinese_share_of_pop"]].sort_values("retention_mt", ascending=False)
print()
print("Canada 2nd-gen retention by CMA:")
print(ca_enc.to_string(index=False))

# --- Correlation: retention vs density ---
import numpy as np
for df, col, label in [(ca_enc, "retention_mt", "CA 2nd-gen MT retention vs Chinese share"),
                       (us_enclave[us_enclave.nativity == "Native"], "share", "US native home-use vs Chinese share")]:
    x = df["chinese_share_of_pop"] if "chinese_share_of_pop" in df else df["chinese_share"]
    y = df[col]
    print(f"{label}: n={len(df)}, Pearson r={np.corrcoef(x, y)[0,1]:.3f}")

# --- US comparison headline ---
print()
print(us.to_string(index=False))
print()
print("US native-born 5-17 vs 65+ retention:", 
      us_age[(us_age.nativity=='Native')&(us_age.age_group=='5-17')]['share'].values,
      us_age[(us_age.nativity=='Native')&(us_age.age_group=='65+')]['share'].values)
