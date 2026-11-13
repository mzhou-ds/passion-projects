"""Join 2025-26 shift charts to play-by-play and build the analysis tables.

For every regulation 5v5 shot attempt, record the on-ice skaters' shift age
(seconds since that shift started) for the attacking and defending teams.
Also build the 5v5 exposure table: seconds of game time spent at each
defending/attacking mean-shift-age bucket, so rates per 60 are honest
denominators rather than raw counts.

Strength is derived from the shift charts themselves (5 skaters a side),
not from the situation code. Overtime excluded (3v3, different dynamics).
"""
import json, os, math, bisect
from collections import defaultdict
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

def clock(s):
    m, sec = s.split(":")
    return int(m) * 60 + int(sec)

BUCKETS = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60),
           (60, 70), (70, 80), (80, 90), (90, 999)]
def bucket(age):
    for i, (lo, hi) in enumerate(BUCKETS):
        if lo <= age < hi:
            return i
    return 9

class TeamPeriod:
    """Sweep-line over one team's shifts in one period."""
    def __init__(self, shifts):
        # shifts: list of (start, end, playerId)
        pts = sorted(set([s for s, _, _ in shifts] + [e for _, e, _ in shifts]))
        self.pts = pts
        self.intervals = []  # (start, end, tuple_of_shift_starts, tuple_of_playerIds)
        starts = sorted(shifts, key=lambda x: x[0])
        ends = sorted(shifts, key=lambda x: x[1])
        active = {}  # playerId -> start
        si = ei = 0
        for a, b in zip(pts[:-1], pts[1:]):
            while si < len(starts) and starts[si][0] <= a:
                _, _, pid = starts[si]
                active[pid] = starts[si][0]
                si += 1
            while ei < len(ends) and ends[ei][1] <= a:
                _, _, pid = ends[ei]
                active.pop(pid, None)
                ei += 1
            if b > a:
                self.intervals.append((a, b, tuple(sorted(active.values())),
                                       tuple(sorted(active.keys()))))
        self.starts = [iv[0] for iv in self.intervals]

    def at(self, t):
        i = bisect.bisect_right(self.starts, t) - 1
        if i < 0 or t >= self.intervals[i][1]:
            return None
        return self.intervals[i]

def at_event(tp, t):
    """On-ice state during the second the event happened.

    Shift charts end a skater's shift at the exact second of a goal or a
    penalty call, so querying at t returns the fresh post-event line.
    t - 0.5 keeps shifts ending at t (the line that was actually on the ice)
    and excludes shifts starting at t (the line jumping on after the whistle).
    """
    if tp is None:
        return None
    iv = tp.at(t - 0.5)
    return iv if iv is not None else tp.at(t)

def main():
    report = json.load(open(os.path.join(RAW, "fetch_report.json")))
    bad = set(report["failed_shifts"]) | set(report["failed_pbp"]) | set(report["empty_shifts"])
    gids = [g for g in range(2025020001, 2025021313) if g not in bad]

    shot_rows, pen_rows, exp_rows = [], [], []
    player_shift_rows = []
    strength_counter = defaultdict(int)
    unmatched = 0
    pos_map = defaultdict(lambda: defaultdict(int))  # playerId -> positionCode -> games
    goalies = set()
    for gid in gids:  # first pass: positions, so goalies can be excluded from shifts
        pbp0 = json.load(open(os.path.join(RAW, f"pbp_{gid}.json")))
        for rs in pbp0.get("rosterSpots", []):
            pos_map[rs["playerId"]][rs.get("positionCode", "?")] += 1
    for pid, c in pos_map.items():
        if max(c.items(), key=lambda kv: kv[1])[0] == "G":
            goalies.add(pid)
    print("goalies identified:", len(goalies))

    for gi, gid in enumerate(gids):
        shifts_d = json.load(open(os.path.join(RAW, f"shifts_{gid}.json")))["data"]
        pbp = json.load(open(os.path.join(RAW, f"pbp_{gid}.json")))
        home_id, away_id = pbp["homeTeam"]["id"], pbp["awayTeam"]["id"]
        teams = {home_id: pbp["homeTeam"]["abbrev"], away_id: pbp["awayTeam"]["abbrev"]}

        # shifts by (team, period)
        by_tp = defaultdict(list)
        for s in shifts_d:
            if s.get("typeCode") != 517 or s["playerId"] in goalies:
                continue
            by_tp[(s["teamId"], s["period"])].append(
                (clock(s["startTime"]), clock(s["endTime"]), s["playerId"]))
            player_shift_rows.append((gid, s["playerId"], s["firstName"], s["lastName"],
                                      s["teamAbbrev"], s["period"],
                                      clock(s["endTime"]) - clock(s["startTime"])))
        tps = {}
        for k, v in by_tp.items():
            tps[k] = TeamPeriod(v)

        # ---- exposure sweep (5v5 only, periods 1-3) ----
        for period in (1, 2, 3):
            th = tps.get((home_id, period)); ta = tps.get((away_id, period))
            if th is None or ta is None:
                continue
            # union of breakpoints from both teams
            pts = sorted(set(th.pts) | set(ta.pts))
            for a, b in zip(pts[:-1], pts[1:]):
                m = (a + b) / 2
                ih = th.at(m); ia = ta.at(m)
                if ih is None or ia is None:
                    continue
                nh, na = len(ih[2]), len(ia[2])
                if nh != 5 or na != 5:
                    continue
                dur = b - a
                for tid, iv, oiv in ((home_id, ih, ia), (away_id, ia, ih)):
                    ages = [m - s for s in iv[2]]
                    oages = [m - s for s in oiv[2]]
                    mean_age = sum(ages) / len(ages)
                    opp_age = sum(oages) / len(oages)
                    n_fresh = sum(1 for x in ages if x <= 5)
                    exp_rows.append((gid, period, tid, bucket(mean_age), dur,
                                     1 if n_fresh >= 2 else 0, mean_age,
                                     opp_age, bucket(opp_age), n_fresh))

        # ---- events ----
        score = {home_id: 0, away_id: 0}
        last_shot = {}  # (team, period) -> time of last shot attempt
        for p in sorted(pbp["plays"], key=lambda x: x["sortOrder"]):
            pdsc = p["periodDescriptor"]
            if pdsc["periodType"] != "REG" or pdsc["number"] not in (1, 2, 3):
                continue
            t = clock(p["timeInPeriod"])
            det = p.get("details", {}) or {}
            kind = p["typeDescKey"]
            if kind == "goal":
                owner = det.get("eventOwnerTeamId")
                if owner in score:
                    score[owner] += 1
            if kind not in ("shot-on-goal", "missed-shot", "blocked-shot", "goal"):
                if kind == "penalty" and det.get("committedByPlayerId") \
                        and det.get("typeCode") in ("MIN", "MAJ"):
                    owner = det.get("eventOwnerTeamId")
                    if owner is None:
                        continue
                    th = tps.get((owner, pdsc["number"]))
                    other = away_id if owner == home_id else home_id
                    to = tps.get((other, pdsc["number"]))
                    if th is None or to is None:
                        unmatched += 1; continue
                    ih, io = at_event(th, t), at_event(to, t)
                    if ih is None or io is None or len(ih[2]) != 5 or len(io[2]) != 5:
                        strength_counter[(len(ih[2]) if ih else -1,
                                          len(io[2]) if io else -1)] += 1
                        continue
                    ages = [t - s for s in ih[2]]
                    pen_rows.append((gid, pdsc["number"], owner, t,
                                     sum(ages) / 5, bucket(sum(ages) / 5),
                                     det.get("descKey"), det.get("duration")))
                continue
            owner = det.get("eventOwnerTeamId")
            if owner is None:
                unmatched += 1; continue
            other = away_id if owner == home_id else home_id
            ta = tps.get((owner, pdsc["number"])); td = tps.get((other, pdsc["number"]))
            if ta is None or td is None:
                unmatched += 1; continue
            ia, idf = at_event(ta, t), at_event(td, t)
            if ia is None or idf is None:
                unmatched += 1; continue
            na, nd = len(ia[2]), len(idf[2])
            strength_counter[(na, nd)] += 1
            if na != 5 or nd != 5:
                continue
            a_ages = [t - s for s in ia[2]]
            d_ages = [t - s for s in idf[2]]
            x, y = det.get("xCoord"), det.get("yCoord")
            if x is None or y is None:
                dist = ang = None
            else:
                dist = math.sqrt((89 - abs(x)) ** 2 + y ** 2)
                ang = math.degrees(math.atan2(abs(y), max(89 - abs(x), 1)))
            prev = last_shot.get((owner, pdsc["number"]))
            rebound = 1 if (prev is not None and (t - prev) <= 4) else 0
            last_shot[(owner, pdsc["number"])] = t
            shooter = det.get("shootingPlayerId") or det.get("scoringPlayerId")
            shooter_age = None
            if shooter in ia[3]:
                idx = ia[3].index(shooter)
                shooter_age = t - ia[2][idx]
            shot_rows.append((gid, pdsc["number"], t, owner, other,
                              kind == "goal", det.get("shotType", "unknown"),
                              dist, ang, rebound,
                              sum(a_ages) / 5, sum(d_ages) / 5,
                              max(d_ages), sum(1 for a in d_ages if a > 60),
                              sum(1 for a in d_ages if a <= 5),
                              bucket(sum(d_ages) / 5), bucket(sum(a_ages) / 5),
                              score[owner] - score[other], shooter_age))
        if (gi + 1) % 300 == 0:
            print(f"{gi+1}/{len(gids)} games parsed", flush=True)

    shots = pd.DataFrame(shot_rows, columns=[
        "game_id", "period", "t", "att_team", "def_team", "is_goal", "shot_type",
        "dist", "angle", "rebound", "att_mean_age", "def_mean_age", "def_max_age",
        "def_n_over60", "def_n_fresh", "def_bucket", "att_bucket", "score_diff",
        "shooter_age"])
    pens = pd.DataFrame(pen_rows, columns=[
        "game_id", "period", "t", "team", "mean_age", "bucket", "infraction", "duration"])
    exp = pd.DataFrame(exp_rows, columns=[
        "game_id", "period", "team", "bucket", "seconds", "change_state", "mean_age",
        "opp_mean_age", "opp_bucket", "n_fresh"])
    players = pd.DataFrame(player_shift_rows, columns=[
        "game_id", "player_id", "first", "last", "team", "period", "duration"])

    shots.to_csv(os.path.join(DATA, "shots_5v5.csv"), index=False)
    pens.to_csv(os.path.join(DATA, "penalties_5v5.csv"), index=False)
    exp.to_csv(os.path.join(DATA, "exposure_5v5.csv"), index=False)
    players.to_csv(os.path.join(DATA, "player_shifts.csv"), index=False)
    pos_rows = [(pid, max(c.items(), key=lambda kv: kv[1])[0])
                for pid, c in pos_map.items()]
    pd.DataFrame(pos_rows, columns=["player_id", "position"]).to_csv(
        os.path.join(DATA, "player_positions.csv"), index=False)

    print("shots 5v5:", len(shots), "| goals:", int(shots.is_goal.sum()))
    print("penalties 5v5:", len(pens))
    print("exposure rows:", len(exp), "| 5v5 hours:",
          round(exp.seconds.sum() / 3600, 1))
    print("unmatched events:", unmatched)
    print("strength distribution (att, def) top 8:",
          sorted(strength_counter.items(), key=lambda kv: -kv[1])[:8])
    print("shots with coords:", shots.dist.notna().sum(),
          "| missing:", shots.dist.isna().sum())
    json.dump({"shots": len(shots), "goals": int(shots.is_goal.sum()),
               "penalties": len(pens), "exposure_rows": len(exp),
               "unmatched": unmatched,
               "strength_top": [[list(k), v] for k, v in
                                sorted(strength_counter.items(), key=lambda kv: -kv[1])[:8]]},
              open(os.path.join(DATA, "parse_report.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
