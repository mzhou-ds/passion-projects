"""Write game-day resale snapshot (scraped 2026-09-26 morning PT) to data/resale_prices.csv."""
import csv

# All prices USD. "from" = cheapest listed ask observed on each platform.
# GameTime and TickPick show all-in prices (no added fees). Others are list prices before fees.
ROWS = [
    # platform, ticket_type, from_price, avg_price, n_listings, pricing_note, url
    ("GameTime", "2-Day GA", 464, None, None, "all-in pricing",
     "https://gametime.co/concert/2026-portola-music-festival-2-day-pass-9-26-9-27-tickets/9-26-2026-san-francisco-ca-pier-80/events/6a1f7e95c2a6013526163dd8"),
    ("GameTime", "Saturday GA", 364, None, None, "all-in pricing", ""),
    ("GameTime", "Sunday GA", 361, None, None, "all-in pricing", ""),
    ("TickPick", "2-Day GA", 451, None, None, "no buyer fees; high ask $3096 (VIP/Captain's Club)",
     "https://www.tickpick.com/buy-portola-music-festival-2-day-pass-tickets-pier-80-san-francisco-9-26-26-3am/8038426/"),
    ("TickPick", "Saturday GA", 376, None, None, "no buyer fees; high ask $658",
     "https://www.tickpick.com/buy-portola-music-festival-saturday-tickets-pier-80-san-francisco-9-26-26-1pm/8038427/"),
    ("TickPick", "Sunday GA", 339, None, None, "no buyer fees; high ask $1274",
     "https://www.tickpick.com/buy-portola-music-festival-sunday-tickets-pier-80-san-francisco-9-27-26-12pm/8038428/"),
    ("Fest Seats", "2-Day GA", 310, None, None, "resale aggregator; fees added at checkout",
     "https://festseats.com/festivals/portola-music-festival-tickets"),
    ("ConcertFix", "2-Day GA", 419, None, 35, "GA from $419 to $939 VIP; fees added at checkout",
     "https://concertfix.com/tours/portola-music-festival-2-day-pass+pier-80-san-francisco+san-francisco-ca"),
    ("SF.events aggregator", "2-Day GA", 374, 888, 35, "aggregator from/avg across marketplaces",
     "https://san-francisco.events/festivals/portola-music-festival/"),
    ("SF.events aggregator", "Saturday GA", 277, 462, 37, "", ""),
    ("SF.events aggregator", "Sunday GA", 306, 799, 33, "", ""),
    # primary market (official site via AXS) for comparison
    ("PRIMARY (portolamusicfestival.com)", "2-Day GA", 399.95, None, None,
     "face was $379.95 at on-sale; current tier $399.95 (Magnetic Mag, Sep 18); AXS fees added at checkout", ""),
    ("PRIMARY (portolamusicfestival.com)", "Saturday GA", 269.95, None, None,
     "face was $249.95 at on-sale; current tier $269.95", ""),
    ("PRIMARY (portolamusicfestival.com)", "Sunday GA", 269.95, None, None,
     "face was $249.95 at on-sale; current tier $269.95", ""),
    ("PRIMARY (portolamusicfestival.com)", "2-Day VIP", 729.95, None, None,
     "face was $699.95 at on-sale", ""),
]

with open("data/resale_prices.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["platform", "ticket_type", "from_price_usd", "avg_price_usd",
                "n_listings", "pricing_note", "url"])
    w.writerows(ROWS)
print(f"wrote {len(ROWS)} rows")
