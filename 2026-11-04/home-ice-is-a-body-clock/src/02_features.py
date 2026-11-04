"""Build game-level features from data/games_raw.csv.

For every regular-season game (and, separately, every playoff game):
- rest days for each team (capped at 7: beyond a week you are just rested),
  back-to-back flags, and the rest differential;
- the visitor's timezone shift (game venue UTC offset minus the visitor's
  home-arena offset on that date, taken from the visitor's nearest home
  game, so DST and Arizona's non-observance are handled by the data);
- miles the visitor traveled since its previous game (haversine between
  arenas);
- which game of a road trip this is for the visitor;
- pre-game Elo ratings (K=20, reset each season, venue-blind so Elo does
  not absorb the home edge it is meant to control for). Playoff games
  use end-of-regular-season Elo, frozen.

Outputs: data/games_features.csv, data/playoff_features.csv.
"""

import math
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent.parent
ARENAS = {
    "ANA": (33.807, -117.876), "BOS": (42.366, -71.062), "BUF": (42.875, -78.876),
    "CAR": (35.803, -78.722), "CBJ": (39.969, -83.006), "CGY": (51.037, -114.001),
    "CHI": (41.881, -87.674), "COL": (39.901, -105.065), "DAL": (32.790, -96.810),
    "DET": (42.341, -83.055), "EDM": (53.546, -113.074), "FLA": (26.159, -80.178),
    "LAK": (34.043, -118.267), "MIN": (44.944, -93.101), "MTL": (45.496, -73.569),
    "NJD": (40.733, -74.171), "NSH": (36.159, -86.778), "NYI": (40.722, -73.723),
    "NYR": (40.751, -73.990), "OTT": (45.296, -75.927), "PHI": (39.901, -75.172),
    "PIT": (40.443, -79.989), "SEA": (47.622, -122.354), "SJS": (37.133, -121.901),
    "STL": (38.626, -90.202), "TBL": (27.942, -82.451), "TOR": (43.643, -79.379),
    "UTA": (40.768, -111.901), "VAN": (49.278, -123.108), "VGK": (36.102, -115.178),
    "WPG": (49.892, -97.143), "WSH": (38.897, -77.020), "ARI": (33.531, -112.261),
}


def parse_offset(s):
    """'+HH:MM'/'-HH:MM' -> float hours. Returns None on garbage."""
    try:
        sign = -1 if str(s).startswith("-") else 1
        h, m = str(s)[-5:].split(":")
        return sign * (int(h) + int(m) / 60)
    except Exception:
        return None


def haversine_miles(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    x = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 3958.8 * math.asin(math.sqrt(x))


def main():
    g = pd.read_csv(HERE / "data" / "games_raw.csv", parse_dates=["date"])
    g = g.sort_values(["date", "game_id"]).reset_index(drop=True)

    # Per-team chronological game lists (all game types: preseason games are
    # genuinely the previous game for a season opener).
    team_games = {}
    for team in sorted(set(g["home"]) | set(g["away"])):
        team_games[team] = g[(g["home"] == team) | (g["away"] == team)].sort_values(
            ["date", "game_id"]).reset_index(drop=True)

    # Visitor home-arena UTC offset on a date: offset of the visitor's
    # nearest home game (DST-safe, Arizona-safe).
    home_offsets = {}
    for team, grp in team_games.items():
        home_games = grp[grp["home"] == team][["date", "venue_utc_offset"]].copy()
        home_games["off"] = home_games["venue_utc_offset"].map(parse_offset)
        home_offsets[team] = home_games.dropna(subset=["off"])

    def home_offset_on(team, date):
        hg = home_offsets[team]
        if hg.empty:
            return None
        idx = (hg["date"] - date).abs().idxmin()
        return hg.loc[idx, "off"]

    def team_context(team, game_id):
        """Previous game, rest, trip length for `team` before `game_id`."""
        grp = team_games[team]
        pos = grp.index[grp["game_id"] == game_id]
        if len(pos) == 0 or pos[0] == 0:
            return None
        i = pos[0]
        prev = grp.loc[i - 1]
        row = grp.loc[i]
        rest = (row["date"] - prev["date"]).days
        # Road-trip length: consecutive away games ending at this game.
        trip = 0
        j = i
        while j >= 0:
            r = grp.loc[j]
            if r["home"] == team:
                break
            trip += 1
            j -= 1
        prev_venue = ARENAS[prev["home"]]  # previous game was at prev home team's arena
        return {"rest": rest, "prev_venue": prev_venue, "trip": trip,
                "prev_was_away": prev["home"] != team}

    def build(game_type):
        rows = []
        sub = g[(g["game_type"] == game_type) & (g["neutral_site"] == 0)]
        for _, r in sub.iterrows():
            hc = team_context(r["home"], r["game_id"])
            ac = team_context(r["away"], r["game_id"])
            if hc is None or ac is None:
                continue
            home_rest = min(hc["rest"], 7)
            away_rest = min(ac["rest"], 7)
            venue_off = parse_offset(r["venue_utc_offset"])
            away_home_off = home_offset_on(r["away"], r["date"])
            tz_shift = (venue_off - away_home_off) if (venue_off is not None and away_home_off is not None) else 0.0
            rows.append({
                "game_id": r["game_id"], "season": r["season"], "date": r["date"].date(),
                "home": r["home"], "away": r["away"],
                "home_win": int(r["home_score"] > r["away_score"]),
                "home_rest": home_rest, "away_rest": away_rest,
                "rest_diff": home_rest - away_rest,
                "home_b2b": int(home_rest == 1), "away_b2b": int(away_rest == 1),
                "tz_shift": tz_shift, "abs_tz": abs(tz_shift),
                "eastward": int(tz_shift > 0),
                "travel_miles": haversine_miles(ac["prev_venue"], ARENAS[r["home"]]),
                "trip_game": ac["trip"],
            })
        return pd.DataFrame(rows)

    reg = build(2)
    po = build(3)

    # Elo: sequential within each season over regular-season games.
    def add_elo(df, frozen=None):
        elos = dict(frozen) if frozen else {}
        out, end = [], {}
        for _, r in df.sort_values(["date", "game_id"]).iterrows():
            eh = elos.get(r["home"], 1500.0)
            ea = elos.get(r["away"], 1500.0)
            out.append(eh - ea)
            exp_h = 1 / (1 + 10 ** (-(eh - ea) / 400))
            s = r["home_win"]
            elos[r["home"]] = eh + 20 * (s - exp_h)
            elos[r["away"]] = ea + 20 * ((1 - s) - (1 - exp_h))
        df = df.copy()
        df["elo_diff"] = out
        return df, elos

    reg_by_season, frozen = [], {}
    for season, grp in reg.groupby("season"):
        grp2, end = add_elo(grp)
        reg_by_season.append(grp2)
        frozen[season] = end
    reg = pd.concat(reg_by_season).sort_values(["date", "game_id"])

    po_by_season = []
    for season, grp in po.groupby("season"):
        grp = grp.copy()
        fr = frozen.get(season, {})
        grp["elo_diff"] = [fr.get(h, 1500.0) - fr.get(a, 1500.0)
                           for h, a in zip(grp["home"], grp["away"])]
        po_by_season.append(grp)
    po = pd.concat(po_by_season).sort_values(["date", "game_id"]) if po_by_season else po

    reg.to_csv(HERE / "data" / "games_features.csv", index=False)
    po.to_csv(HERE / "data" / "playoff_features.csv", index=False)
    print(f"regular-season: {len(reg)} games, home win rate {reg.home_win.mean():.3f}")
    print(f"playoff: {len(po)} games, home win rate {po.home_win.mean():.3f}")
    print(reg.head(3).to_string())


if __name__ == "__main__":
    main()
