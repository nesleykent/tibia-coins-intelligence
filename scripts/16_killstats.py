"""Ingest per-world kill statistics into a daily fundamentals panel.

The report's binding constraint, stated in Section 6.1.3, is that no series measuring gold
creation exists. Kill statistics are the closest observable proxy: monsters killed is what
generates loot and gold, player deaths are what destroys it, and the mix of creatures killed
says what kind of hunting is happening. This stage turns roughly 22,000 daily files into a
panel that can be joined to the price panel.

Aggregation happens on ingest. The raw files are ~5 GB and carry one row per race per world per
day; nothing downstream needs that resolution, so only the aggregates survive.

Source: github.com/tibiamaps/tibia-kill-stats, a daily capture of the official per-world kill
statistics page. Boss names come from the same repository's Bosstiary categories.

    python scripts/16_killstats.py [path-to-clone]
"""
import json, pathlib, sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P, RAW = ROOT / "data" / "processed", ROOT / "data" / "raw"
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/tibia-kill-stats") / "data"
OUT = P / "kill_stats_daily.csv"
MIX = P / "kill_stats_mix.csv"
TOP_RACES = 40
RACE_PREFIX = "race::"   # intermediate only; dropped before writing           # how many creature types the hunting-mix block tracks
BOSSES = set(json.loads((RAW / "boss_names.json").read_text())) \
    if (RAW / "boss_names.json").exists() else set()

# Entries whose "race" is a bracketed category rather than a creature: these are the buckets the
# kill-statistics page uses for deaths not attributable to one monster. They carry player deaths
# but never monster kills, so they must not enter the kill aggregates.
PSEUDO = ("(", "[")


def read_world(wdir):
    """Aggregate every daily file for one world."""
    rows = []
    for f in sorted(wdir.glob("20*.json")):
        try:
            d = json.loads(f.read_text())["killstatistics"]
        except Exception:
            continue
        killed = players = boss = races = deep = 0
        top = []
        per_race = {}
        for e in d.get("entries", []):
            race = e.get("race", "")
            k = e.get("last_day_killed", 0) or 0
            p = e.get("last_day_players_killed", 0) or 0
            players += p
            if race.startswith(PSEUDO):
                continue
            killed += k
            if k > 0:
                races += 1
                top.append(k)
                per_race[race] = k
                if race in BOSSES:
                    boss += k
        top = np.array(sorted(top, reverse=True), dtype=float)
        # Concentration of the day's hunting across creature types. A market where everyone
        # farms the same few spawns looks different from one spread across the map.
        hhi = float(((top / top.sum()) ** 2).sum()) if top.size and top.sum() else np.nan
        rows.append({"world": d.get("world", wdir.name.title()), "date": f.stem,
                     **{f"race::{r}": v for r, v in per_race.items()},
                     "monsters_killed": killed, "players_killed": players,
                     "boss_kills": boss, "races_hunted": races,
                     "hunt_hhi": hhi,
                     "top10_share": float(top[:10].sum() / top.sum()) if top.size else np.nan})
    return rows


if __name__ == "__main__":
    if not SRC.exists():
        raise SystemExit(f"kill-stats clone not found at {SRC}; pass the path as an argument")
    worlds = sorted(d for d in SRC.iterdir() if d.is_dir() and not d.name.startswith("_"))
    print(f"reading {len(worlds)} worlds from {SRC}")
    with ProcessPoolExecutor() as ex:
        out = [r for batch in ex.map(read_world, worlds) for r in batch]

    ks = pd.DataFrame(out)
    ks["date"] = pd.to_datetime(ks.date)
    ks = ks.sort_values(["world", "date"]).reset_index(drop=True)

    # The page reports the trailing day, so a row dated D describes activity on D-1. Shifting it
    # here means every downstream use is already aligned and cannot accidentally look ahead.
    ks["date"] = ks.date - pd.Timedelta(days=1)

    # A world that reports zero kills for a whole day is a scrape failure, not a quiet world.
    dead = ks.monsters_killed == 0
    print(f"dropping {int(dead.sum())} world-days reporting no kills at all")
    ks = ks[~dead]

    # The by-monster resolution, kept as shares rather than counts so a busy world and a quiet
    # one are comparable. Only the globally most-hunted creatures are tracked: the tail is
    # thousands of races that almost never appear and would be noise.
    rcols = [c for c in ks.columns if c.startswith("race::")]
    totals = ks[rcols].sum().sort_values(ascending=False)
    keep = list(totals.head(TOP_RACES).index)
    mix = ks[["world", "date"]].copy()
    denom = ks[rcols].sum(axis=1).replace(0, np.nan)
    for c in keep:
        mix[c.replace("race::", "mix_")] = ks[c] / denom
    mix.to_csv(MIX, index=False)
    print(f"[MIX] {len(keep)} creature shares written to {MIX.name}; "
          f"top three: {', '.join(c.replace('race::', '') for c in keep[:3])}")
    ks = ks.drop(columns=rcols)

    ks.to_csv(OUT, index=False)
    span = f"{ks.date.min():%Y-%m-%d} to {ks.date.max():%Y-%m-%d}"
    print(f"[KILLSTATS] {len(ks):,} world-days, {ks.world.nunique()} worlds, {span}")
    print(f"  median monsters killed per world-day: {ks.monsters_killed.median():,.0f}")
    print(f"  median player deaths per world-day:   {ks.players_killed.median():,.0f}")
    print(f"  median boss kills per world-day:      {ks.boss_kills.median():,.0f}")
    print(f"  written to {OUT.relative_to(ROOT)}")
