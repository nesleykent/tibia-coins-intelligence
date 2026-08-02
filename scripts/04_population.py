"""Parse GuildStats online-counter pages into a daily players-online panel.

Each page embeds Chart.js series as JS literals:
  const dataAll  = { labels: ["YYYY-MM-DD", ...], values: [n, ...] }   full daily history
  const dataYear = { ... }                                            trailing 365 days
plus per-period Max/Min/Average stat tiles (24h, week, month, year, all time).

Outputs: population_daily.csv, population_summary.csv
"""
import json, re, pathlib
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
WORLDS = json.load(open(RAW / "world_list.json"))

ARR = r"const\s+%s\s*=\s*\{\s*labels:\s*(\[.*?\]),\s*values:\s*(\[.*?\])"


def series(html, name):
    m = re.search(ARR % name, html, re.S)
    if not m:
        return None
    lab, val = json.loads(m.group(1)), json.loads(m.group(2))
    n = min(len(lab), len(val))
    return lab[:n], val[:n]


rows, summ = [], []
for w in WORLDS:
    f = RAW / "guildstats_oc" / f"{w}.html"
    if not f.exists():
        summ.append({"world": w, "status": "missing_page"})
        continue
    html = f.read_text(encoding="utf-8", errors="replace")

    s = series(html, "dataAll")
    if s:
        lab, val = s
        d = pd.DataFrame({"world": w, "date": pd.to_datetime(lab, errors="coerce"),
                          "players_online_avg": pd.to_numeric(val, errors="coerce")})
        rows.append(d.dropna(subset=["date"]))

    # stat tiles: "Max players"/"Min players"/"Average players" grouped per chart period
    soup = BeautifulSoup(html, "lxml")
    tiles = {}
    for tile in soup.find_all("div", attrs={"data-chart": True}):
        key = (tile["data-chart"], tile.get("data-type"))
        v = tile.find_all("div")
        nums = [x.get_text(strip=True) for x in v]
        tiles[key] = nums
    rec = {"world": w, "status": "ok"}
    for chart, per in [("chartYear", "year"), ("chartAll", "all"),
                       ("chart24h", "d24"), ("chartMonth", "month"), ("chartWeek", "week")]:
        for typ in ("max", "min"):
            t = tiles.get((chart, typ))
            if t and len(t) >= 2:
                rec[f"{per}_{typ}"] = pd.to_numeric(t[1].replace(",", ""), errors="coerce")
    summ.append(rec)

pop = pd.concat(rows, ignore_index=True)
pop = pop[pop["players_online_avg"] >= 0]
pop.to_csv(OUT / "population_daily.csv", index=False)

meta = pd.read_csv(OUT / "world_metadata.csv", parse_dates=["created"])
sm = pd.DataFrame(summ).merge(
    meta[["world", "region", "snapshot_online", "created"]], on="world", how="right")

# period aggregates from the true daily series
end = pop["date"].max()
g = pop.groupby("world")["players_online_avg"]
sm["daily_avg_all"] = sm["world"].map(g.mean())
sm["n_days_pop"] = sm["world"].map(g.size())
sm["pop_first_date"] = sm["world"].map(pop.groupby("world")["date"].min())
yr = pop[pop["date"] > end - pd.Timedelta(days=365)]
sm["daily_avg_year"] = sm["world"].map(yr.groupby("world")["players_online_avg"].mean())
sm["daily_avg_90d"] = sm["world"].map(
    pop[pop["date"] > end - pd.Timedelta(days=90)].groupby("world")["players_online_avg"].mean())

# D8 snapshot-bias factor: trailing-year daily average vs the 04:45 UTC instantaneous count
sm["bias_factor"] = sm["daily_avg_year"] / sm["snapshot_online"].replace(0, np.nan)
sm.to_csv(OUT / "population_summary.csv", index=False)

print(f"population panel: {pop.world.nunique()} worlds, {len(pop):,} world-days, "
      f"{pop.date.min().date()} -> {pop.date.max().date()}")
print("pages missing:", (pd.DataFrame(summ)["status"] == "missing_page").sum())
print("\nD8 snapshot-bias factor (trailing-year daily average / 04:45 UTC snapshot):")
b = sm.dropna(subset=["bias_factor"])
print(b.groupby("region")["bias_factor"].agg(n="size", median="median", mean="mean").round(3).to_string())
