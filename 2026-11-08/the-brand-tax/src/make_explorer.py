"""Generate explorer.html: a sortable table of all 40 products plus the three stacks."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "data" / "products.csv")
stats = json.loads((ROOT / "output" / "results.json").read_text())

df = df.sort_values(["compound", "cost_per_trial_dose"])
df["cost_per_trial_dose"] = df["cost_per_trial_dose"].round(3)
df["cost_per_month"] = df["cost_per_month"].round(2)
df["servings_per_day"] = df["servings_per_day"].round(2)
df["dose_gap_pct"] = df["dose_gap_pct"].round(0).astype(int)

rows = ""
for _, r in df.iterrows():
    rows += (
        f"<tr><td>{r['compound']}</td><td>{r['brand']}</td>"
        f"<td>{r['product']}</td><td>{r['form']}</td><td>{r['tier']}</td>"
        f"<td>${r['price_usd']:.2f}</td><td>{int(r['servings_per_container'])}</td>"
        f"<td>{int(r['dose_per_serving']):,} {r['dose_unit']}</td>"
        f"<td>{int(r['dose_gap_pct'])}%</td><td>{r['servings_per_day']}</td>"
        f"<td>${r['cost_per_trial_dose']:.3f}</td><td>${r['cost_per_month']:.2f}</td>"
        f"<td><a href=\"{r['url']}\">listing</a></td></tr>\n"
    )

stack_cards = ""
for name, s in stats["stacks"].items():
    items = "".join(f"<li>{c}: {p}</li>" for c, p in s["products"].items())
    stack_cards += (
        f"<div class='card'><h3>{name}</h3>"
        f"<p class='big'>${s['per_day']:.2f}/day &middot; ${s['per_month']:.0f}/mo &middot; "
        f"${s['per_year']:,.0f}/yr</p><ul>{items}</ul></div>\n"
    )

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>The Brand Tax — explorer</title>
<style>
body {{ font-family: system-ui, sans-serif; max-width: 1100px; margin: 2em auto; padding: 0 1em; color: #222; }}
h1 {{ font-size: 1.6em; }} .sub {{ color: #555; }}
.cards {{ display: flex; gap: 1em; flex-wrap: wrap; }}
.card {{ border: 1px solid #ccc; border-radius: 8px; padding: 1em; flex: 1; min-width: 280px; }}
.card .big {{ font-size: 1.25em; font-weight: bold; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.85em; margin-top: 1.5em; }}
th, td {{ border-bottom: 1px solid #ddd; padding: 6px 8px; text-align: left; }}
th {{ cursor: pointer; background: #f5f5f5; position: sticky; top: 0; }}
tr:hover {{ background: #fafafa; }}
input {{ padding: 6px; width: 320px; margin-top: 1em; }}
</style></head><body>
<h1>The Brand Tax</h1>
<p class="sub">40 products, 6 staple biohacker compounds. Every price is a real listing
fetched 2026-11-08. Cost per trial dose = price &divide; (total active in the
container &divide; trial dose). Click a column header to sort; type to filter.</p>
<div class="cards">{stack_cards}</div>
<input id="q" placeholder="Filter products, brands, compounds..." oninput="filterTable()">
<table id="t"><thead><tr>
<th onclick="sortTable(0)">Compound</th><th onclick="sortTable(1)">Brand</th>
<th onclick="sortTable(2)">Product</th><th onclick="sortTable(3)">Form</th>
<th onclick="sortTable(4)">Tier</th><th onclick="sortTable(5)">Price</th>
<th onclick="sortTable(6)">Servings</th><th onclick="sortTable(7)">Dose/serving</th>
<th onclick="sortTable(8)">Dose vs trial</th><th onclick="sortTable(9)">Servings/day</th>
<th onclick="sortTable(10)">$/trial dose</th><th onclick="sortTable(11)">$/month</th><th>Listing</th>
</tr></thead><tbody>{rows}</tbody></table>
<script>
let dir = 1;
function sortTable(c) {{
  const t = document.getElementById("t"), rows = [...t.tBodies[0].rows];
  rows.sort((a, b) => {{
    const x = a.cells[c].textContent.replace(/[$,%]/g, ""), y = b.cells[c].textContent.replace(/[$,%]/g, "");
    const nx = parseFloat(x), ny = parseFloat(y);
    return dir * (isNaN(nx) || isNaN(ny) ? x.localeCompare(y) : nx - ny);
  }});
  dir *= -1; rows.forEach(r => t.tBodies[0].appendChild(r));
}}
function filterTable() {{
  const q = document.getElementById("q").value.toLowerCase();
  document.querySelectorAll("#t tbody tr").forEach(r =>
    r.style.display = r.textContent.toLowerCase().includes(q) ? "" : "none");
}}
</script>
<p class="sub">Trial doses: creatine 5 g, magnesium 400 mg elemental, vitamin D3 2,000 IU,
omega-3 1,000 mg EPA+DHA, zinc 15 mg, NR 300 mg. Sources and verification notes
are in data/products.csv and the README.</p>
</body></html>
"""
(ROOT / "explorer.html").write_text(html)
print("wrote explorer.html")
