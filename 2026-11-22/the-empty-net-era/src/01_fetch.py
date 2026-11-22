#!/usr/bin/env python3
"""
Fetch NHL play-by-play for every regular-season game, 2015-16 through 2026-27,
and extract per-game empty-net / goalie-pull features.

Sources: NHL public API (api-web.nhle.com), no key required.
  GET https://api-web.nhle.com/v1/gamecenter/{season}02{game:04d}/play-by-play

Key facts validated 2026-11-22 before the full run:
  - A goal with no `goalieInNetId` in its details is an empty-net goal.
  - `situationCode` is 4 chars: [awayGoalie 1/0][awaySkaters][homeSkaters][homeGoalie 1/0].
    '1551' = 5v5 both goalies in; '1560' = home goalie pulled, 6v5.
  - The API emits no explicit 'goalie-pulled' play type, so pull intervals are
    derived from situationCode transitions in period 3.
  - Game IDs run contiguously 0001..N per season; the run stops a season after
    15 consecutive non-OFF games (shortened / in-progress seasons).

Outputs (appended incrementally, flushed per game so a crash loses nothing):
  data/game_features.csv  - one row per game
  data/player_goals.csv   - one row per player-season (goals, ENGs)
  data/player_names.json  - playerId -> name map
  data/fetch_log.txt      - per-season counts
"""
import csv
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE = "https://api-web.nhle.com/v1/gamecenter/{}02{:04d}/play-by-play"
SEASONS = list(range(2015, 2027))  # 2015 = 2015-16 ... 2026 = 2026-27 (partial)
MAX_GAME_NO = 1350
STOP_AFTER_NON_OFF = 15
WORKERS = 6
MAX_RETRIES = 4

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
os.makedirs(DATA, exist_ok=True)

GAME_FIELDS = [
    "game_id", "season", "game_date", "home_abbrev", "away_abbrev",
    "home_score", "away_score",
    "goals_reg", "goals_ot", "goals_so", "goals_total",
    "eng_total", "eng_by_home", "eng_by_away", "eng_ot",
    "score_diff_end3",            # home - away score entering period 3 (i.e. after 2nd)
    # Endgame pull = pulling team trailing AND <= 6:00 left in period 3.
    # (Goalie-out intervals outside that are almost always delayed-penalty pulls.)
    "first_eg_pull_time_rem",     # seconds remaining in period 3 at first endgame pull
    "first_eg_pull_team",         # 'home' / 'away'
    "first_eg_pull_diff",         # pulling team's goal differential at pull (negative = trailing)
    "num_eg_pulls",               # number of distinct endgame pull intervals in period 3
    "num_pulls_all",              # all goalie-out intervals in period 3 (incl. delayed-penalty)
    "sixv5_time_eg",              # seconds with a goalie out during endgame pulls
    "sixv5_gf_eg",                # goals by the 6-skater team during endgame pulls
    "sixv5_ga_eg",                # goals by the 5-skater team during endgame pulls (= ENGs)
    "sixv5_time_all",             # seconds with a goalie out, all period-3 intervals
    "dp_pull_time_sec",           # seconds of non-endgame (delayed-penalty) goalie-out time
    "pull_intervals_json",        # [[start_rem, dur, team, diff, gf, ga], ...] all period-3 intervals
    "pp_time_sec",                # total seconds of 5v4 / 5v3 (both goalies in), regulation
    "pp_goals",                   # goals by the team with the man advantage
    "pull_tie",                   # 1 if a trailing team's first endgame pull ended tied, else 0
    "pull_eng_against",          # 1 if the pulling team conceded an ENG during its first endgame pull
]

_lock = threading.Lock()
_player_names = {}
_player_goals = {}  # (season, player_id) -> [goals, engs]
_game_rows = []


def parse_time(t):
    """'MM:SS' elapsed in period -> seconds."""
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def sit_parse(sit):
    """situationCode -> (away_goalie_in, away_skaters, home_skaters, home_goalie_in)."""
    if not sit or len(sit) != 4:
        return None
    try:
        return (sit[0] == "1", int(sit[1]), int(sit[2]), sit[3] == "1")
    except ValueError:
        return None


def fetch_game(season, num):
    gid = f"{season}02{num:04d}"
    url = BASE.format(season, num)
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=25)
            if r.status_code == 404:
                return None, "404"
            if r.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json(), None
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
    return None, "failed"


def extract(d, season):
    """Extract per-game features from one play-by-play payload."""
    plays = d.get("plays", [])
    game_date = d.get("gameDate", "")
    home = d.get("homeTeam", {})
    away = d.get("awayTeam", {})
    row = {
        "game_id": d.get("id"),
        "season": season,
        "game_date": game_date,
        "home_abbrev": home.get("abbrev", ""),
        "away_abbrev": away.get("abbrev", ""),
        "home_score": home.get("score"),
        "away_score": away.get("score"),
        "goals_reg": 0, "goals_ot": 0, "goals_so": 0,
        "eng_total": 0, "eng_by_home": 0, "eng_by_away": 0, "eng_ot": 0,
        "score_diff_end3": None,
        "first_eg_pull_time_rem": None, "first_eg_pull_team": "",
        "first_eg_pull_diff": None, "num_eg_pulls": 0, "num_pulls_all": 0,
        "sixv5_time_eg": 0, "sixv5_gf_eg": 0, "sixv5_ga_eg": 0,
        "sixv5_time_all": 0, "dp_pull_time_sec": 0, "pull_intervals_json": "",
        "pp_time_sec": 0, "pp_goals": 0,
        "pull_tie": None, "pull_eng_against": None,
    }
    # roster -> names (firstName/lastName are locale dicts in the new API:
    # {'default': 'Auston', 'cs': 'Auston', ...} — take the 'default' form)
    for spot in d.get("rosterSpots", []):
        pid = spot.get("playerId")
        if pid and pid not in _player_names:
            def _nm(v):
                if isinstance(v, dict):
                    return v.get("default", "")
                return v or ""
            _player_names[pid] = f"{_nm(spot.get('firstName'))} {_nm(spot.get('lastName'))}".strip()

    home_goals = 0
    away_goals = 0
    # Walk plays in order; track goalie-out intervals in period 3 and PP time in regulation.
    prev_t = None          # (period, seconds elapsed)
    prev_sit = None
    pull_open = None       # dict for the currently open pull interval in period 3
    pull_intervals = []    # (start_rem, end_rem, team, diff_at_pull, gf, ga)
    pp_open_since = None   # (period, sec) start of current PP interval
    pp_team = None         # 'home'/'away' team with the advantage

    def close_pull(period, sec):
        nonlocal pull_open
        if pull_open is None:
            return
        end_rem = 1200 - sec if period == 3 else 0
        pull_open["end_rem"] = end_rem
        pull_open["dur"] = pull_open["start_rem"] - end_rem
        pull_intervals.append(pull_open)
        pull_open = None

    def close_pp(period, sec):
        nonlocal pp_open_since, pp_team
        if pp_open_since is None:
            return
        p0, s0 = pp_open_since
        if p0 == period:
            row["pp_time_sec"] += sec - s0
        pp_open_since = None
        pp_team = None

    for p in plays:
        pd = p.get("periodDescriptor", {})
        period = pd.get("number", 0)
        ptype = pd.get("periodType", "")
        t = p.get("timeInPeriod")
        if t is None:
            continue
        sec = parse_time(t)
        sit = sit_parse(p.get("situationCode"))
        is_goal = p["typeDescKey"] == "goal"
        det = p.get("details", {}) if is_goal else {}

        # score entering period 3: capture before the first period-3 play is processed
        if period == 3 and row["score_diff_end3"] is None:
            row["score_diff_end3"] = home_goals - away_goals

        # --- goal bookkeeping ---
        if is_goal:
            scorer = det.get("scoringPlayerId")
            team = det.get("eventOwnerTeamId")
            is_home_goal = (team == home.get("id"))
            if ptype == "REG":
                row["goals_reg"] += 1
            elif ptype == "OT":
                row["goals_ot"] += 1
            else:
                row["goals_so"] += 1
            eng = "goalieInNetId" not in det
            if eng and ptype == "REG":
                row["eng_total"] += 1
                if is_home_goal:
                    row["eng_by_home"] += 1
                else:
                    row["eng_by_away"] += 1
            if eng and ptype == "OT":
                row["eng_ot"] += 1
            if scorer and ptype in ("REG", "OT"):
                # Shootout-deciding goals are type 'goal' with periodType 'SO'
                # but are not real goals: exclude them from player totals.
                key = (season, scorer)
                with _lock:
                    g = _player_goals.setdefault(key, [0, 0])
                    g[0] += 1
                    if eng and ptype == "REG":
                        g[1] += 1
            if is_home_goal:
                home_goals += 1
            else:
                away_goals += 1
            # goals during a pull interval / PP interval
            if pull_open is not None and period == 3:
                pulling = pull_open["team"]
                if (pulling == "home") == is_home_goal:
                    pull_open["gf"] += 1
                else:
                    pull_open["ga"] += 1
            if pp_team is not None and ptype == "REG":
                if (pp_team == "home") == is_home_goal:
                    row["pp_goals"] += 1

        # --- interval transitions (use state BEFORE this play's own effect where
        #     it matters: a goal happens while the previous situation is in force) ---
        if period == 3 and ptype == "REG" and sit is not None:
            goalie_out = not (sit[0] and sit[3])
            if goalie_out and pull_open is None:
                team = "home" if not sit[3] else "away"
                diff = (home_goals - away_goals) if team == "home" else (away_goals - home_goals)
                pull_open = {
                    "start_rem": 1200 - sec, "end_rem": None, "dur": 0,
                    "team": team, "diff": diff, "gf": 0, "ga": 0,
                }
                row["num_pulls_all"] += 1
            elif not goalie_out and pull_open is not None:
                close_pull(period, sec)
        if period != 3 and pull_open is not None:
            close_pull(period, sec)

        # PP intervals: both goalies in, 5v4 or 5v3, regulation only
        if ptype == "REG" and sit is not None:
            both_in = sit[0] and sit[3]
            adv = None
            if both_in:
                # sit = (awayGoalie, awaySkaters, homeSkaters, homeGoalie)
                if sit[1] == 5 and sit[2] in (3, 4):
                    adv = "away"   # away has 5 skaters, home is short
                elif sit[2] == 5 and sit[1] in (3, 4):
                    adv = "home"   # home has 5 skaters, away is short
            if adv is not None and pp_open_since is None:
                pp_open_since = (period, sec)
                pp_team = adv
            elif adv is None and pp_open_since is not None:
                close_pp(period, sec)
            elif adv is not None and pp_team != adv:
                close_pp(period, sec)
                pp_open_since = (period, sec)
                pp_team = adv
        # period changes close open intervals
        if prev_t is not None and period != prev_t[0]:
            if pull_open is not None:
                close_pull(prev_t[0], 1200)
            if pp_open_since is not None:
                close_pp(prev_t[0], 1200)
        prev_t = (period, sec)
        prev_sit = sit

    # close anything still open at end of game
    if pull_open is not None:
        close_pull(3, 1200)
    if pp_open_since is not None:
        close_pp(prev_t[0] if prev_t else 3, 1200)

    # Official score counts at most one shootout goal; play-by-play lists every SO attempt.
    row["goals_total"] = row["goals_reg"] + row["goals_ot"] + (1 if row["goals_so"] > 0 else 0)

    # Endgame classification: trailing at the pull AND <= 6:00 left in period 3.
    eg = [iv for iv in pull_intervals if iv["diff"] < 0 and iv["start_rem"] <= 360]
    row["num_eg_pulls"] = len(eg)
    row["sixv5_time_eg"] = sum(iv["dur"] for iv in eg)
    row["sixv5_gf_eg"] = sum(iv["gf"] for iv in eg)
    row["sixv5_ga_eg"] = sum(iv["ga"] for iv in eg)
    row["sixv5_time_all"] = sum(iv["dur"] for iv in pull_intervals)
    row["dp_pull_time_sec"] = row["sixv5_time_all"] - row["sixv5_time_eg"]
    row["pull_intervals_json"] = json.dumps(
        [[iv["start_rem"], iv["dur"], iv["team"], iv["diff"], iv["gf"], iv["ga"]]
         for iv in pull_intervals]
    )
    if eg:
        first = eg[0]
        row["first_eg_pull_time_rem"] = first["start_rem"]
        row["first_eg_pull_team"] = first["team"]
        row["first_eg_pull_diff"] = first["diff"]
        # pull outcome: did the first endgame pull (trailing by 1 or 2) end tied?
        # Tie requires the pulling team's net goals during the pull to cover the deficit.
        if first["diff"] in (-1, -2):
            row["pull_tie"] = 1 if (first["gf"] - first["ga"]) >= -first["diff"] else 0
            row["pull_eng_against"] = 1 if first["ga"] >= 1 else 0
    return row


def flush_game_rows():
    with _lock:
        path = os.path.join(DATA, "game_features.csv")
        new = not os.path.exists(path)
        with open(path, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=GAME_FIELDS)
            if new:
                w.writeheader()
            for r in _game_rows:
                w.writerow({k: r.get(k, "") for k in GAME_FIELDS})
        _game_rows.clear()


def flush_players():
    with open(os.path.join(DATA, "player_goals.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["season", "player_id", "player_name", "goals", "eng_goals"])
        for (season, pid), (g, e) in sorted(_player_goals.items()):
            w.writerow([season, pid, _player_names.get(pid, ""), g, e])
    with open(os.path.join(DATA, "player_names.json"), "w") as f:
        json.dump(_player_names, f)


def log(msg):
    with _lock:
        with open(os.path.join(DATA, "fetch_log.txt"), "a") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
        print(msg, flush=True)


def run_season(season):
    done = 0
    non_off = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {}
        # submit in waves so the stop rule can work
        nxt = 1
        in_flight = {}
        while nxt <= MAX_GAME_NO and non_off < STOP_AFTER_NON_OFF:
            while len(in_flight) < WORKERS * 2 and nxt <= MAX_GAME_NO:
                fut = ex.submit(fetch_game, season, nxt)
                in_flight[fut] = nxt
                nxt += 1
            # wait for at least one to finish
            for fut in as_completed(list(in_flight), timeout=120):
                num = in_flight.pop(fut)
                d, err = fut.result()
                if d is None or d.get("gameState") != "OFF":
                    non_off += 1
                    if non_off >= STOP_AFTER_NON_OFF:
                        break
                    continue
                non_off = 0
                row = extract(d, season)
                _game_rows.append(row)
                done += 1
                if done % 100 == 0:
                    flush_game_rows()
                    log(f"season {season}: {done} games")
                break  # go refill the wave
    flush_game_rows()
    log(f"season {season} DONE: {done} games")
    return done


def main():
    total = 0
    for season in SEASONS:
        total += run_season(season)
    flush_players()
    log(f"ALL DONE: {total} games")


if __name__ == "__main__":
    main()
