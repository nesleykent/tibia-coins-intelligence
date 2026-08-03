"""Fold the 2022-2025 kill-statistics archive in without keeping it on disk.

The archive is 4 GB compressed and 17 GB unpacked - 1,195 daily files for each of 152 world
directories. Keeping that around to run one aggregation is the wrong trade: what the study
actually needs is a 10 MB table of daily totals, and the JSON behind it is never read again.

So this stage works a world at a time and reclaims the space as it goes. Aggregate one world
directory, append its rows, delete the directory, move to the next. Peak extra usage is one
world rather than the whole archive, and a run that is interrupted can be resumed because the
completed worlds are already gone and already written.

The same aggregation rules as 16_killstats.py apply, and they are imported from it rather than
restated, so the two archives cannot drift into different definitions.

    python scripts/16b_killstats_history.py [path-to-clone] [--keep]

--keep leaves the source directories in place, for a machine with room to spare.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
OUT = P / "kill_stats_daily.csv"
MIX = P / "kill_stats_mix.csv"
SRC = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-")
                   else "/tmp/tibia-kill-stats-hist") / "data"
KEEP = "--keep" in sys.argv

# Reuse the aggregation from the current-archive stage. Restating it here would let the two
# archives drift into different definitions of a kill.
_spec = importlib.util.spec_from_file_location(
    "_ks", ROOT / "scripts" / "16_killstats.py")
_ks = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_ks)               # its work sits behind a __main__ guard
except SystemExit:
    pass
read_world = _ks.read_world

if not SRC.is_dir():
    raise SystemExit(f"archive not found at {SRC}; clone it first, or pass the path")

existing = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame()
have = set(zip(existing.world, existing.date)) if len(existing) else set()
print(f"[HISTORY] {len(existing):,} rows already aggregated")

worlds = sorted(w for w in SRC.iterdir() if w.is_dir() and not w.name.startswith("_"))
print(f"[HISTORY] {len(worlds)} world directories at {SRC}")

new_rows, done, freed = [], 0, 0
for w in worlds:
    try:
        size = sum(f.stat().st_size for f in w.glob("20*.json"))
        rows = [r for r in read_world(w) if (r["world"], r["date"]) not in have]
        new_rows.extend(rows)
        done += 1
        if not KEEP:
            shutil.rmtree(w, ignore_errors=True)
            freed += size
        if done % 20 == 0:
            print(f"  {done}/{len(worlds)} worlds, {len(new_rows):,} new rows, "
                  f"{freed / 1e9:.1f} GB reclaimed")
    except Exception as e:                        # one unreadable world must not lose the rest
        print(f"  ! {w.name}: {type(e).__name__}")

print(f"[HISTORY] {done} worlds read, {len(new_rows):,} new rows, "
      f"{freed / 1e9:.1f} GB reclaimed")

if new_rows:
    add = pd.DataFrame(new_rows)
    both = pd.concat([existing, add], ignore_index=True) if len(existing) else add
    both = both.drop_duplicates(subset=["world", "date"]).sort_values(["world", "date"])
    # Write the mix first, since it is the only consumer of the per-race counts, then drop
    # them: stored densely they are 1,607 columns that are empty on almost every row.
    race_cols = [c for c in both.columns if c.startswith("race::")]
    if race_cols:
        tot = both[race_cols].sum().sort_values(ascending=False)
        top = list(tot.head(_ks.TOP_RACES).index)
        mix = both[["world", "date"] + top].copy()
        denom = both[race_cols].sum(axis=1).replace(0, pd.NA)
        for c in top:
            mix[c] = mix[c] / denom
        mix.columns = ["world", "date"] + [c.replace("race::", "share_") for c in top]
        mix.to_csv(MIX, index=False)
        print(f"[HISTORY] {MIX.relative_to(ROOT)}: {len(mix):,} rows, {len(top)} creature shares")
        both = both.drop(columns=race_cols)
    both.to_csv(OUT, index=False)
    span = f"{both.date.min()} to {both.date.max()}"
    print(f"[HISTORY] {OUT.relative_to(ROOT)}: {len(both):,} world-days, "
          f"{both.world.nunique()} worlds, {span}")
    print(f"[HISTORY] file is {OUT.stat().st_size / 1e6:.1f} MB")

if not KEEP:
    # The clone itself, once every world directory is gone, is only its git objects.
    root = SRC.parent
    if root.exists() and not any(p.is_dir() for p in SRC.iterdir()) if SRC.exists() else True:
        shutil.rmtree(root, ignore_errors=True)
        print(f"[HISTORY] removed {root}")
