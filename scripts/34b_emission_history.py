"""Extend the GP-emission series over the 2022-2025 archive, one world at a time.

The last ingest fixed the wrong half of the problem. Processing world by world and deleting as
it went kept peak disk to a single world, which was right - but it wrote only daily totals and
threw away the per-creature counts, and those are exactly what reconstructing GP needs. So the
monetary series stayed at eight months while the activity series reached three and a half
years, and closing that gap meant downloading the archive again.

This stage makes that the last download. It fetches one world at a time, runs the same
emission reconstruction 34_gold_emission.py uses, appends the daily GP rows, and deletes the
world before moving on. What survives is the derived series - roughly 90 MB for the full span -
rather than the 600-800 MB the per-creature detail would cost or the 17 GB the raw archive
does. Nothing needs the network again afterwards.

Only the worlds that carry a price are fetched, and only those are needed: a world with no
price series cannot enter any test that joins emission to a return.

    python scripts/34b_emission_history.py [--keep] [--worlds N]
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
OUT = P / "gold_emission_daily.csv"
WORK = pathlib.Path("/tmp/tibia-ks-hist-sparse")
REPO = "https://github.com/tibiamaps/tibia-kill-stats-from-2022-08-23-to-2025-12-04.git"
KEEP = "--keep" in sys.argv
LIMIT = None
if "--worlds" in sys.argv:
    LIMIT = int(sys.argv[sys.argv.index("--worlds") + 1])

# Reuse the reconstruction rather than restating it: two definitions of emission would be worse
# than no second series at all.
_spec = importlib.util.spec_from_file_location("_ge", ROOT / "scripts" / "34_gold_emission.py")
_ge = importlib.util.module_from_spec(_spec)
# A dataclass in that module resolves its own type through sys.modules, so the module has to
# be registered before it executes or the decorator fails on an unregistered name.
sys.modules["_ge"] = _ge
try:
    _spec.loader.exec_module(_ge)
except SystemExit:
    pass


def _load_catalogue() -> None:
    """Populate the module globals scan_world reads.

    scan_world resolves every creature through MODELS, ALIASES, BOSSES and CLASSIFICATIONS,
    and only main() sets them. Calling it on a freshly imported module leaves all four empty,
    every creature misses the catalogue, and the scan returns rows whose emission is zero -
    silently, because a zero is a valid number. That is what happened on the first run.
    """
    items, loot_creatures, models, cache = _ge.parse_loot_cache()
    _ge.MODELS = models
    _ge.ALIASES = _ge.aliases()
    _ge.CLASSIFICATIONS = _ge.creature_classifications()
    boss_names = json.loads((ROOT / "data" / "raw" / "boss_names.json").read_text())
    _ge.BOSSES = {_ge.norm(_ge.ALIASES.get(_ge.norm(n), n)) for n in boss_names}
    _ge.BOSSES.update(k for k, v in _ge.CLASSIFICATIONS.items() if v.get("is_boss", False))
    if not _ge.MODELS:
        raise SystemExit("creature catalogue is empty; the scan would emit zeros")
    print(f"[SPARSE] catalogue loaded: {len(_ge.MODELS):,} loot models, "
          f"{len(_ge.BOSSES):,} bosses")


_load_catalogue()

# Worlds that carry a price. A world with no price cannot enter a test that joins emission to
# a return, so fetching it would be pure cost.
pan = pd.read_csv(P / "panel_daily.csv", usecols=["world", "date"], parse_dates=["date"])
priced = sorted({w.lower() for w in pan.world.unique()})
print(f"[SPARSE] {len(priced)} priced worlds to fetch")

existing = pd.read_csv(OUT) if OUT.exists() else pd.DataFrame()
have = (set(zip(existing.world, pd.to_datetime(existing.date).dt.strftime("%Y-%m-%d")))
        if len(existing) else set())
print(f"[SPARSE] {len(existing):,} emission rows already present")


def sh(*args, **kw):
    return subprocess.run(args, cwd=kw.get("cwd"), check=True,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if not (WORK / ".git").exists():
    shutil.rmtree(WORK, ignore_errors=True)
    WORK.parent.mkdir(parents=True, exist_ok=True)
    print("[SPARSE] cloning the tree without blobs")
    # --filter=blob:none fetches the directory structure and pulls file contents only when a
    # path is checked out. That is what makes one-world-at-a-time possible over the network.
    sh("git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", REPO, str(WORK))
    sh("git", "sparse-checkout", "set", "--no-cone", cwd=WORK)

targets = priced[:LIMIT] if LIMIT else priced
rows, done, skipped = [], 0, 0
for w in targets:
    wdir = WORK / "data" / w
    try:
        sh("git", "sparse-checkout", "set", "--no-cone", f"data/{w}/*", cwd=WORK)
        if not wdir.is_dir():
            skipped += 1
            continue
        daily, _totals = _ge.scan_world(wdir)
        # A world that reports kills but no modelled kills means the catalogue did not load.
        # Failing here is better than writing a structurally empty series that looks fine.
        if daily and sum(r.get("total_kills", 0) for r in daily) > 0 \
                and sum(r.get("modeled_kills_all", 0) for r in daily) == 0:
            raise SystemExit(f"{w}: kills present but nothing modelled - catalogue not loaded")
        fresh = [r for r in daily
                 if (r.get("world"), str(r.get("date"))[:10]) not in have]
        rows.extend(fresh)
        done += 1
        if not KEEP:
            shutil.rmtree(wdir, ignore_errors=True)
        if done % 10 == 0:
            print(f"  {done}/{len(targets)} worlds, {len(rows):,} new emission rows")
    except subprocess.CalledProcessError:
        skipped += 1
    except Exception as e:
        print(f"  ! {w}: {type(e).__name__}")

print(f"[SPARSE] {done} worlds read, {skipped} unavailable, {len(rows):,} new rows")

if rows:
    add = pd.DataFrame(rows)
    # build_daily merges on date, so both sides must be datetime. Stringifying here is what
    # made the first run fall back to writing the underived union.
    add["date"] = pd.to_datetime(add.date)
    if len(existing):
        existing["date"] = pd.to_datetime(existing.date)
    both = pd.concat([existing, add], ignore_index=True) if len(existing) else add
    # Keep exactly the columns scan_world emits. build_daily merges population, world metadata
    # and events itself, so leaving a previous build's copies in place collides on the join and
    # the merge silently produces suffixed columns the function then cannot find. The fresh
    # rows are raw scan output, so their column set is the definition.
    raw_cols = list(add.columns)
    both = both[[c for c in raw_cols if c in both.columns]]
    both = (both.drop_duplicates(subset=["world", "date"])
                .sort_values(["world", "date"]).reset_index(drop=True))
    # The published table is the built one, so run the same derivation over the union.
    try:
        built = _ge.build_daily(both.copy())
    except Exception as e:
        print(f"  ! build_daily failed ({type(e).__name__}); writing the raw union")
        built = both
    built.to_csv(OUT, index=False)
    print(f"[SPARSE] {OUT.relative_to(ROOT)}: {len(built):,} world-days, "
          f"{built.world.nunique()} worlds, {built.date.min()} to {built.date.max()}")
    print(f"[SPARSE] file is {OUT.stat().st_size / 1e6:.1f} MB")

if not KEEP:
    shutil.rmtree(WORK, ignore_errors=True)
    print(f"[SPARSE] removed {WORK}")
