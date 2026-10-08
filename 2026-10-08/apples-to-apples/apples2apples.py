#!/usr/bin/env python3
"""
Apples2Apples — run a reverse auction for medical Good Faith Estimates
BEFORE care happens, instead of fighting the claims process after it.

The pitch in one paragraph
--------------------------
In the United States, the price of a scan is a secret until after you've
had it. The No Surprises Act gives uninsured and self-pay patients a legal
right to a written Good Faith Estimate (GFE) from every provider, on
request, before scheduled care — but almost nobody uses it, because
calling eight imaging centers, repeating your CPT code eight times, and
begging for a number in writing is a part-time job. Apples2Apples is the
agent that does that job: it reads your plan, decomposes your procedure
into billable CPT codes, finds the in-network options near you, drafts
the outreach, collects the bids, and ranks them the way a marketplace
would — apples to apples, same code, same coverage, lowest real price
to *you* wins.

Pipeline
--------
1. INTAKE     — your plan snapshot (insurer, deductible remaining,
                coinsurance, out-of-pocket max remaining, location,
                radius). Taken from a JSON file; nothing is scraped and
                no credential is ever asked for.
2. DECOMPOSE  — plain-language procedure -> billable CPT code candidates
                (with the usual gotchas: combined codes, -26/-TC splits).
3. SCAN       — candidate sites near you. In this demo the site list is
                illustrative; in production this is where published
                price-transparency files and insurer network data feed in.
4. OUTREACH   — one email draft + one 60-second call script per site,
                asking for a written GFE. DRAFTS ONLY: this program has
                no send function, by design. A human reviews, approves,
                and sends each message themselves.
5. AUCTION    — returned bids (or illustrative demo bids) ranked by
                expected PATIENT SHARE under your plan — not by the
                sticker price, because the sticker price is fiction.
6. CALCULATE  — a procedure calculator per bid: benchmark comparison,
                insurer share, your share, and savings vs. what you
                actually paid last time.
7. PACKET     — a paper-trail file: intake, drafts, bids, timestamps and
                the recommendation, kept together so that if a final bill
                ever lands $400+ over a written GFE, the federal dispute
                process has everything it needs — and if it lands under
                that, the written bid is still your negotiation anchor.

Pricing methodology (stated, not hidden)
----------------------------------------
medicare_ref  = the best sourced all-in Medicare allowed amount for the
                CPT (hospital-outpatient total when sourced, else the
                Physician Fee Schedule global rate).
fair band     = 1.0x - 2.0x medicare_ref. Commercial contracts for
                imaging commonly land in this window; UCSF's own
                published cash prices for several MRI codes fall below
                it. A negotiation heuristic, not a legal standard.
Every number in BENCHMARKS comes from the public sources listed in
benchmarks.md (accessed 2026-10-07). Where a value could not be sourced
it is None and the tool says so rather than inventing one.

Legal framing, kept honest
--------------------------
The federal GFE right (45 CFR 149.610) covers uninsured and self-pay
patients; providers must deliver a written estimate within 3 business
days of a request for care scheduled at least 3 business days out, and a
final bill $400 or more over the GFE for the same provider can go to the
federal Patient-Provider Dispute Resolution process. Insured patients
don't get the same federal right — for them the lever is the insurer's
own written cost estimate plus in-network price competition, which is
exactly what the outreach drafts ask for. This tool is an information
and negotiation aid, not legal or medical advice.

Usage
-----
  python3 apples2apples.py --list-cpts
  python3 apples2apples.py --procedure "chin mri"
  python3 apples2apples.py --intake demo/intake-michael-70540.json \
      --bids demo/bids-illustrative.json --packet paper-trail-70540.md
"""

import argparse
import json
import sys
from datetime import datetime, timezone

ACCESSED = "2026-10-07"

# ---------------------------------------------------------------------------
# Benchmark table. Sourced public figures, accessed 2026-10-07; full
# citations in benchmarks.md. None = not captured from a source.
# ---------------------------------------------------------------------------
BENCHMARKS = {
    "70540": {
        "description": "MRI orbit, face and/or neck, without contrast",
        "aliases": ["chin mri", "face mri", "neck mri", "jaw mri", "tmj mri"],
        "mpfs_national": 224,
        "medicare_hopd_total": None,
        "facility_published_cash": None,
        "cash_market": "$499 published cash at a freestanding center; "
                       "~$350-$493 national payer averages; ~$863 hospital direct-pay",
    },
    "70551": {
        "description": "MRI brain (incl. brain stem), without contrast",
        "aliases": ["brain mri", "mri brain", "head mri"],
        "mpfs_national": 200,
        "medicare_hopd_total": None,
        "facility_published_cash": 432,
        "cash_market": "RadNet San Francisco lists $550 cash; SF Bay Area hospital "
                       "median cash for brain MRI $2,440",
    },
    "70552": {
        "description": "MRI brain (incl. brain stem), with contrast only",
        "aliases": ["brain mri with contrast"],
        "mpfs_national": 270,
        "medicare_hopd_total": None,
        "facility_published_cash": None,
        "cash_market": "RadNet San Francisco lists $700 cash",
    },
    "70553": {
        "description": "MRI brain (incl. brain stem), without then with contrast",
        "aliases": ["brain mri with and without contrast", "brain mri w/wo"],
        "mpfs_national": 317,
        "medicare_hopd_total": 672,
        "facility_published_cash": 652,
        "cash_market": "SF-Oakland-Fremont hospital cash $2,810-$6,946 (median $5,499); "
                       "Bay Area independent imaging median negotiated $371",
    },
    "72141": {
        "description": "MRI cervical spine (neck), without contrast",
        "aliases": ["cervical mri", "neck mri", "cervical spine mri"],
        "mpfs_national": 191,
        "medicare_hopd_total": 434,
        "facility_published_cash": None,
        "cash_market": "Published national commercial averages $265.76-$449.69",
    },
    "72148": {
        "description": "MRI lumbar spine (low back), without contrast",
        "aliases": ["lumbar mri", "low back mri", "lumbar spine mri"],
        "mpfs_national": 199,
        "medicare_hopd_total": 242,
        "facility_published_cash": 487,
        "cash_market": "California hospital median discounted cash $2,614; "
                       "national hospital cash median $1,173",
    },
    "72197": {
        "description": "MRI pelvis, without then with contrast",
        "aliases": ["pelvis mri", "pelvic mri"],
        "mpfs_national": 334,
        "medicare_hopd_total": 356,
        "facility_published_cash": None,
        "cash_market": "National hospital cash median $2,487 (middle 50% $1,419-$3,758)",
    },
    "73721": {
        "description": "MRI any joint of lower extremity (knee/hip/ankle), without contrast",
        "aliases": ["knee mri", "joint mri", "ankle mri", "hip mri"],
        "mpfs_national": 204,
        "medicare_hopd_total": 447,
        "facility_published_cash": 330,
        "cash_market": "National hospital cash median $1,809 (middle 50% $1,052-$2,869); "
                       "typical commercial $250-$400",
    },
}

FAIR_LOW_MULT = 1.0
FAIR_HIGH_MULT = 2.0

# Plain-language procedure -> CPT decomposition. The point of this table is
# the billing gotchas, not coverage: every entry names the code a scheduler
# should confirm with the ordering provider before anyone quotes a price.
DECOMPOSITION = {
    "chin mri": [("70540", "face/neck MRI without contrast; confirm the study "
                           "isn't a dedicated TMJ protocol")],
    "jaw mri": [("70540", "same study as chin/face; TMJ-specific orders may "
                          "decompose differently")],
    "brain mri": [("70551", "without contrast. If the order says with AND "
                            "without, the correct single code is 70553 — "
                            "billing 70551+70552 separately is unbundling")],
    "brain mri with and without contrast": [("70553", "combined code; do not "
                                             "accept separate 70551/70552 lines")],
    "neck mri": [("72141", "cervical spine. A soft-tissue neck study is 70540 "
                           "instead — confirm which one was ordered")],
    "low back mri": [("72148", "lumbar spine without contrast")],
    "knee mri": [("73721", "lower-extremity joint without contrast; watch for "
                           "a separate -26 professional-component bill")],
    "pelvis mri": [("72197", "without then with contrast")],
}


def medicare_ref(bm):
    """Best all-in Medicare allowed reference available from sourced data."""
    if bm.get("medicare_hopd_total"):
        return bm["medicare_hopd_total"], "Medicare hospital-outpatient total"
    if bm.get("mpfs_national"):
        return bm["mpfs_national"], "Medicare MPFS global"
    return None, "none"


def fmt(n):
    if n is None:
        return "n/a (not captured from a source)"
    return f"${n:,.0f}" if abs(n - round(n)) < 0.005 else f"${n:,.2f}"


def patient_share(allowed, deductible_remaining, coinsurance_pct, oop_remaining=None):
    """Expected patient share of an allowed amount under a plan snapshot.

    Deductible first, then coinsurance on the remainder, capped by the
    out-of-pocket maximum still remaining. Returns (patient, insurer).
    """
    allowed = float(allowed)
    ded = min(float(deductible_remaining or 0), allowed)
    coins = (allowed - ded) * (float(coinsurance_pct or 0) / 100.0)
    patient = ded + coins
    if oop_remaining is not None:
        patient = min(patient, float(oop_remaining))
    return round(patient, 2), round(allowed - patient, 2)


def decompose(procedure_text):
    """Map a plain-language procedure to [(cpt, note)] using DECOMPOSITION."""
    q = (procedure_text or "").lower().strip()
    for phrase, rows in DECOMPOSITION.items():
        if phrase in q or q in phrase:
            return rows
    # fall back to the benchmark alias table
    for code, bm in BENCHMARKS.items():
        if q in bm["description"].lower() or any(q in a or a in q for a in bm["aliases"]):
            return [(code, "matched from benchmark alias table; confirm with ordering provider")]
    return []


def email_draft(intake, bm, cpt, site):
    return (
        f"Subject: Written Good Faith Estimate request — CPT {cpt} "
        f"({bm['description']})\n\n"
        f"Hello {site['name']} team,\n\n"
        f"I am pricing CPT {cpt} ({bm['description']}) before booking, under my "
        f"{intake.get('insurer', '[insurer]')} plan. Please send me a written "
        f"Good Faith Estimate that includes:\n"
        f"  - every CPT/HCPCS code you expect to bill, including add-ons;\n"
        f"  - facility, technical, and professional (radiologist) fees, and "
        f"whether the radiologist bills separately;\n"
        f"  - the plan allowed amount if you are in-network, and my expected "
        f"patient share after my deductible and coinsurance.\n\n"
        f"I am comparing written estimates from several in-network centers "
        f"this week and will book on the written number. Please reply in "
        f"writing within 3 business days. Thank you."
    )


def call_script(intake, bm, cpt, site):
    return (
        f"\"Hi, I'm calling {site['name']} before booking. I'm pricing CPT "
        f"{cpt} — {bm['description'].lower()} — under my "
        f"{intake.get('insurer', '[insurer]')} plan, and I'm comparing written "
        f"Good Faith Estimates from a few in-network centers this week. Could "
        f"you email me your written estimate, with the full CPT stack and my "
        f"expected patient share after deductible and coinsurance? I need it "
        f"in writing to compare apples to apples. Thank you.\""
    )


def run(intake, bids):
    cpt = intake["cpt"]
    bm = BENCHMARKS[cpt]
    ref, ref_label = medicare_ref(bm)
    band = (ref * FAIR_LOW_MULT, ref * FAIR_HIGH_MULT) if ref else (None, None)
    ded = intake.get("deductible_remaining", 0)
    coins = intake.get("coinsurance_pct", 0)
    oop = intake.get("oop_remaining")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines, packet = [], []
    head = f"# Apples2Apples run — CPT {cpt} ({bm['description']})"
    lines.append(head)
    lines.append(f"Generated {now} · Benchmarks accessed {ACCESSED} (see benchmarks.md)")
    lines.append(f"Insurer: {intake.get('insurer')} · Location: {intake.get('location')} · "
                 f"Radius: {intake.get('radius_miles')} mi")
    lines.append(f"Plan snapshot: deductible remaining {fmt(ded)}, coinsurance {coins}%, "
                 f"out-of-pocket remaining {fmt(oop) if oop is not None else 'not specified'}")
    lines.append(f"Medicare reference ({ref_label}): {fmt(ref)} · Fair band: "
                 f"{fmt(band[0])}-{fmt(band[1])}")
    if bm.get("facility_published_cash"):
        lines.append(f"UCSF's own published cash price for this code: "
                     f"{fmt(bm['facility_published_cash'])}")
    if bm.get("cash_market"):
        lines.append(f"Cash market notes: {bm['cash_market']}")
    actual = intake.get("actual_patient_share")
    if actual:
        lines.append(f"What the patient actually paid at UCSF for this exam: {fmt(actual)}")
    lines.append("")

    # --- decomposition notes -------------------------------------------------
    decomp = decompose(intake.get("procedure_text", ""))
    if decomp:
        lines.append("## CPT decomposition")
        for code, note in decomp:
            lines.append(f"- **{code}** — {BENCHMARKS[code]['description']}: {note}")
        lines.append("")

    # --- outreach drafts ------------------------------------------------------
    lines.append("## Draft outreach — DRAFT ONLY, nothing is sent by this tool")
    packet.append(f"# Apples2Apples paper trail — CPT {cpt}")
    packet.append(f"Run generated {now}. Every message below is a DRAFT. "
                  "Sending stays a human decision, per clinic, every time.\n")
    for site in intake.get("clinics", []):
        dist = site.get("distance_mi", "?")
        net = site.get("network", "in-network to verify")
        lines.append(f"\n### {site['name']} ({dist} mi, {net})")
        em = email_draft(intake, bm, cpt, site)
        call = call_script(intake, bm, cpt, site)
        lines.append("EMAIL DRAFT")
        lines.append("> " + em.replace("\n", "\n> "))
        lines.append(f"\nCALL SCRIPT (60s): {call}")
        packet.append(f"## {site['name']} — outreach drafts")
        packet.append("EMAIL (draft, unsent):\n\n" + em + "\n")
        packet.append("CALL SCRIPT (draft, unsent):\n\n" + call + "\n")

    # --- auction ---------------------------------------------------------------
    lines.append("\n## Bid board — ranked by expected patient share under your plan")
    lines.append("| Rank | Site | Bid / basis | Est. insurer pays | Est. you pay | vs fair-band top |")
    lines.append("|---:|---|---:|---:|---:|---|")
    ranked = []
    for b in bids:
        if b.get("cash_price"):
            share = float(b["bid"])  # pre-negotiated cash: insurer out of the loop
            insurer_pays = 0.0
        else:
            share, insurer_pays = patient_share(b["bid"], ded, coins, oop)
        ranked.append((share, insurer_pays, b))
    ranked.sort(key=lambda r: r[0])
    for i, (share, insurer_pays, b) in enumerate(ranked, 1):
        basis = ("CASH (illustrative published price — not a quote)"
                 if b.get("cash_price") else
                 "ILLUSTRATIVE placeholder bid — not a quote") if b.get("illustrative") \
            else b.get("basis", "bid")
        vs = "n/a"
        if band[1]:
            vs = f"{'below' if share <= band[1] else 'above'} {fmt(band[1])}"
        lines.append(f"| {i} | {b['clinic']} | {fmt(b['bid'])} · {basis} | "
                     f"{fmt(insurer_pays)} | {fmt(share)} | {vs} |")
        packet.append(f"- BID {b['clinic']}: {fmt(b['bid'])} ({basis}); "
                      f"estimated patient share {fmt(share)}.")

    if ranked:
        best_share, _, best = ranked[0]
        rec = (f"\nRECOMMENDATION: {best['clinic']} — estimated patient share "
               f"{fmt(best_share)}")
        if actual:
            rec += (f", which is {fmt(actual - best_share)} below the "
                    f"{fmt(actual)} actually paid at UCSF for the identical exam")
        rec += (". Before booking: get this number confirmed as a written "
                "Good Faith Estimate with the full CPT stack, facility + "
                "professional fees itemized, and the deductible/coinsurance "
                "math shown. Keep every written reply with timestamps.")
        if actual and best_share < actual:
            rec += ("\nPaper trail: a final bill $400 or more over a written "
                    "GFE for the same provider can go to the federal "
                    "Patient-Provider Dispute Resolution process (for "
                    "uninsured/self-pay estimates); below that threshold, "
                    "the written bid is still the anchor for negotiation — "
                    "which is the entire reason to have one before care.")
        lines.append(rec)
        packet.append("\n## Recommendation\n" + rec)
    packet.append("\n## Decision log")
    packet.append(f"- {now}: intake run; drafts generated; NO outreach sent.")
    return "\n".join(lines) + "\n", "\n".join(packet) + "\n"


def main():
    ap = argparse.ArgumentParser(
        description="Apples2Apples — reverse-auction Good Faith Estimates before care. "
                    "Drafts outreach only; sends nothing.")
    ap.add_argument("--intake", help="intake JSON (insurer, cpt, plan snapshot, clinics)")
    ap.add_argument("--bids", help="bids JSON (returned or illustrative demo bids)")
    ap.add_argument("--procedure", help="plain-language procedure, e.g. 'chin mri' — "
                                      "prints the CPT decomposition and benchmark")
    ap.add_argument("--list-cpts", action="store_true")
    ap.add_argument("--out", default="-", help="report output path (default stdout)")
    ap.add_argument("--packet", help="also write the paper-trail packet to this path")
    a = ap.parse_args()

    if a.list_cpts:
        print(f"{'CPT':<7}{'Procedure':<58}{'Medicare ref':>13}{'Fair band':>16}")
        print("-" * 94)
        for code, bm in BENCHMARKS.items():
            ref, _ = medicare_ref(bm)
            band = f"{fmt(ref)}-{fmt(ref * 2)}" if ref else "n/a"
            print(f"{code:<7}{bm['description'][:56]:<58}{fmt(ref):>13}{band:>16}")
        print("\nFair band = 1.0x-2.0x Medicare reference. Sources: benchmarks.md "
              f"(accessed {ACCESSED}).")
        return 0

    if a.procedure and not a.intake:
        rows = decompose(a.procedure)
        if not rows:
            print(f"No decomposition for '{a.procedure}' in the built-in table. "
                  "Add the phrase to DECOMPOSITION in apples2apples.py.", file=sys.stderr)
            return 2
        for code, note in rows:
            bm = BENCHMARKS[code]
            ref, label = medicare_ref(bm)
            print(f"{a.procedure!r} -> CPT {code} — {bm['description']}")
            print(f"  note: {note}")
            print(f"  Medicare reference ({label}): {fmt(ref)}; "
                  f"fair band {fmt(ref)}-{fmt(ref * 2) if ref else 'n/a'}")
        return 0

    if not a.intake:
        ap.error("--intake is required (or use --procedure / --list-cpts)")
    intake = json.load(open(a.intake))
    bids = json.load(open(a.bids)) if a.bids else []
    report, packet = run(intake, bids)
    if a.out == "-":
        sys.stdout.write(report)
    else:
        open(a.out, "w").write(report)
    if a.packet:
        open(a.packet, "w").write(packet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
