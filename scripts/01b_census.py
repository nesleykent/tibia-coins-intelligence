"""Collect the GuildStats per-world census: the true resident character population.

https://guildstats.eu/census?world=<World> renders a population breakdown whose underlying
figures are embedded as a JS literal `const censusData = {...}`. It carries the total
character count for the world plus splits by account type, vocation, level, gender and city.

This is a genuine population STOCK (characters resident on the world), unlike the
players-online counter, which is an activity FLOW.

Outputs: data/raw/census/<World>.html, data/processed/world_census.csv
"""
import json, pathlib, re, sys, time
import pandas as pd
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
(RAW / "census").mkdir(parents=True, exist_ok=True)
WORLDS = json.load(open(RAW / "world_list.json"))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

s = requests.Session()
s.headers["User-Agent"] = UA

BLOCK = r"%s:\s*\{\s*data:\s*(\[.*?\]),\s*total:\s*(\d+)"


def fetch(w):
    dest = RAW / "census" / f"{w}.html"
    if dest.exists() and dest.stat().st_size > 50_000:
        return dest.read_text(encoding="utf-8", errors="replace")
    for a in range(4):
        try:
            r = s.get(f"https://guildstats.eu/census?world={w}", timeout=45)
            if r.status_code == 200 and b"censusData" in r.content:
                dest.write_bytes(r.content)
                time.sleep(1.3)
                return r.text
        except Exception:
            pass
        time.sleep(4 * (a + 1))
    return None


def parse(w, h):
    rec = {"world": w}
    for key in ("cities", "vocations", "gender", "account", "levels"):
        m = re.search(BLOCK % key, h, re.S)
        if not m:
            continue
        try:
            data = json.loads(m.group(1).replace("&apos;", "'"))
        except Exception:
            data = []
        rec[f"{key}_total"] = int(m.group(2))
        if key == "account":
            for d in data:
                rec["free_accounts" if d["name"].startswith("Free") else "premium_accounts"] = d["count"]
        elif key == "gender":
            for d in data:
                rec[d["name"].lower()] = d["count"]
        elif key == "vocations":
            for d in data:
                rec["voc_" + d["name"].lower().replace(" ", "_")] = d["count"]
        elif key == "levels":
            lv = pd.DataFrame(data)
            if len(lv):
                n = lv["count"].sum()
                rec["mean_level"] = float((lv.level * lv["count"]).sum() / n)
                c = lv.sort_values("level")["count"].cumsum()
                rec["median_level"] = float(lv.sort_values("level").level[c >= n / 2].iloc[0])
                rec["chars_level_100plus"] = int(lv.loc[lv.level >= 100, "count"].sum())
                rec["chars_level_400plus"] = int(lv.loc[lv.level >= 400, "count"].sum())
    m = re.search(r"vocCombined:\s*(\{.*?\})", h, re.S)
    if m:
        for k, v in json.loads(m.group(1)).items():
            rec["vocgrp_" + k.lower()] = v
    return rec


rows, fails = [], []
for i, w in enumerate(WORLDS, 1):
    h = fetch(w)
    if not h:
        fails.append(w)
        print(f"[{i:>3}/93] {w:<12} FAIL", flush=True)
        continue
    r = parse(w, h)
    rows.append(r)
    print(f"[{i:>3}/93] {w:<12} population={r.get('account_total', 0):>7,}  "
          f"premium={r.get('premium_accounts', 0):>7,}", flush=True)

df = pd.DataFrame(rows)
df["population"] = df["account_total"]
df["premium_share"] = df["premium_accounts"] / df["population"]
df["pct_level_100plus"] = df["chars_level_100plus"] / df["population"]
df.to_csv(OUT / "world_census.csv", index=False)
print(f"\nworlds: {len(df)}  failures: {fails}")
print(f"total characters across sampled worlds: {df.population.sum():,}")
print(df[["population", "premium_share", "mean_level", "median_level"]].describe()
      .loc[["count", "min", "50%", "max"]].round(3).to_string())
