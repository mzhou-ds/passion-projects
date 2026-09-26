"""Fetch the Portola 2026 lineup (billing order, from the official poster) to data/lineup.csv."""
import csv

# Billing order as printed on the official Portola 2026 poster
# (portolamusicfestival.com). Day splits per brooklynvegan/sfstation coverage.
LINEUP = [
    # (artist, billing_tier, day)
    ("ADÉLA", 5, "Sun"),
    ("Airwolf Paradise", 5, "Sun"),
    ("Azzecca", 5, "Sat"),
    ("Baby J", 5, "Sat"),
    ("Bassvictim", 4, "Sat"),
    ("Beltran b2b Ben Sterling", 5, "Sat"),
    ("Ben UFO", 4, "Sun"),
    ("Brunello", 5, "Sat"),
    ("Channel Tres", 4, "Sun"),
    ("Chloé Caillet", 5, "Sat"),
    ("Clearcast", 5, "Sat"),
    ("Daphni", 4, "Sun"),
    ("Dean Turnley", 5, "Sat"),
    ("DESPACIO", 3, "Both"),
    ("DJ Shadow", 3, "Sat"),
    ("DOG BLOOD", 1, "Sat"),
    ("ear", 5, "Sun"),
    ("erika b2b sfcowboy", 5, "Sat"),
    ("Fatboy Slim", 3, "Sat"),
    ("Fcukers", 4, "Sat"),
    ("Felly Fell", 5, "Sat"),
    ("Four Tet", 3, "Sun"),
    ("Gelli Haha", 5, "Sat"),
    ("Groove Armada", 3, "Sat"),
    ("horsegiirL", 4, "Sun"),
    ("jigitz", 5, "Sun"),
    ("JT", 4, "Sun"),
    ("Jyoty", 5, "Sat"),
    ("Kelela", 4, "Sun"),
    ("KETTAMA", 4, "Sat"),
    ("Marlon Hoffstadt", 5, "Sat"),
    ("Max Styler", 5, "Sat"),
    ("Melanie C", 4, "Sat"),
    ("MGNA Crrrta", 5, "Sun"),
    ("Mike D 5D", 3, "Sat"),
    ("Mind Enterprises", 5, "Sun"),
    ("Mochakk", 4, "Sat"),
    ("nate sib", 5, "Sun"),
    ("nimino", 5, "Sat"),
    ("Ninajirachi", 4, "Sun"),
    ("oskar med k", 5, "Sat"),
    ("Overmono", 3, "Sun"),
    ("Parcels", 4, "Sat"),
    ("Prospa", 5, "Sun"),
    ("Ranger Trucco b2b Alisha", 5, "Sun"),
    ("riria", 5, "Sat"),
    ("Robyn", 1, "Sat"),
    ("Sam Alfred", 5, "Sun"),
    ("SG Lewis", 4, "Sat"),
    ("Silva Bumpa", 5, "Sun"),
    ("Six Sex", 5, "Sun"),
    ("Skepta", 3, "Sat"),
    ("Soulwax", 2, "Sat"),
    ("Swedish House Mafia", 1, "Sun"),
    ("Tiësto", 2, "Sun"),
    ("Torren Foot", 5, "Sat"),
    ("Tove Lo", 3, "Sat"),
    ("Tricky", 4, "Sat"),
    ("underscores", 4, "Sun"),
    ("VTSS", 5, "Sat"),
    ("Zara Larsson", 2, "Sun"),
    ("ZULAN", 5, "Sat"),
    ("basspunk.", 5, "Sun"),
]

with open("data/lineup.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["artist", "billing_tier", "day", "poster_rank"])
    for i, (a, t, d) in enumerate(LINEUP, 1):
        w.writerow([a, t, d, i])

print(f"wrote {len(LINEUP)} artists")
