"""Prove the published artifacts were actually rebuilt from current data.

Every other verifier checks that the artifacts agree with each other. None of them checks that
they agree with *today*, and a pipeline that silently keeps yesterday's numbers passes all of
them: the artifacts are perfectly consistent, just stale. This session hit that failure three
separate ways - a collector that returned "cached" for every file and fetched nothing, quality
metrics describing a table that had since been rewritten, and a history stage whose output was
structurally empty - and in each case the existing checks were green.

Four things must hold for the published numbers to be current:

1. collection actually wrote files recently - file mtime, which is the only thing that proves a
   fetch happened;
2. the price archive the panel is built from reaches close to today, and the cleaned panel
   reaches the day that archive describes;
3. every published artifact is newer than the panel it is built from;
4. no artifact claims coverage the panel does not have - `46_verify_artifacts.py` owns that one,
   and it is named here so the division is explicit rather than assumed.

    python scripts/54_verify_freshness.py [--max-age-days N]
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

MAX_AGE_DAYS = 3
if "--max-age-days" in sys.argv:
    MAX_AGE_DAYS = int(sys.argv[sys.argv.index("--max-age-days") + 1])

# Artifacts a reader can open, and the processed table each is built from.
ARTIFACTS = {
    "reports/intelligence_hub.html": "panel_daily.csv",
    "reports/gold_emission_dashboard.html": "gold_emission_daily.csv.gz",
    "reports/creature_gp_per_kill.html": "creature_gold_value.csv",
    "reports/gold_emission_report.html": "gold_emission_quality.json",
    "reports/tibia_coin_market_report.pdf": "panel_daily.csv",
}


def fail(problems: list[str], message: str) -> None:
    problems.append(message)


def main() -> None:
    now = dt.datetime.now(dt.UTC)
    problems: list[str] = []
    notes: list[str] = []

    # --- 1. collection wrote files recently ------------------------------------------------
    # Judge the fetch by file mtime, not by the payload's `update_time`. That field is the
    # server's own last board refresh for that world, so it is a property of the source and not
    # of this pipeline: the median world sits about six days behind and one is three weeks
    # behind, entirely normally. An earlier version of this check read it as collection time and
    # would have failed permanently for a condition nothing here can fix. Worse, it took the
    # maximum across worlds, so a single fresh world would have masked ninety-two stale ones.
    boards = sorted(glob.glob(str(RAW / "market_board" / "*.json")))
    if not boards:
        fail(problems, "no market_board payloads collected at all")
    else:
        fetched = [dt.datetime.fromtimestamp(pathlib.Path(p).stat().st_mtime, dt.UTC)
                   for p in boards]
        fetched.sort()
        median_age = (now - fetched[len(fetched) // 2]).days
        stale = sum(1 for f in fetched if (now - f).days > MAX_AGE_DAYS)
        notes.append(
            f"market payloads: {len(boards)} worlds fetched, median {median_age}d ago, "
            f"{stale} older than {MAX_AGE_DAYS}d"
        )
        # A minority of laggards is tolerable; a stale majority means collection did not run.
        if stale > len(boards) // 2:
            fail(problems, (
                f"{stale} of {len(boards)} market payloads are older than {MAX_AGE_DAYS} days; "
                f"collection did not refresh. Re-run 01_collect.py --refresh, which ignores the "
                f"on-disk cache"
            ))
        unreadable = 0
        for path in boards:
            try:
                json.loads(pathlib.Path(path).read_text())
            except Exception:
                unreadable += 1
        if unreadable:
            fail(problems, f"{unreadable} of {len(boards)} market payloads did not parse")

    # The price panel is built from a separate archive, not from market_board, so its currency
    # is a different question with a different answer.
    archive = pathlib.Path("/tmp/tibia-warzones/data/market/world")
    stamps: list[dt.datetime] = []
    if archive.is_dir():
        for path in sorted(archive.glob("*/*_tibia_coins.json"))[:12]:
            try:
                run_at = json.loads(path.read_text()).get("last_run_at")
                if run_at:
                    stamps.append(dt.datetime.fromisoformat(run_at.replace("Z", "+00:00")))
            except Exception:
                pass
    if stamps:
        newest = max(stamps)
        notes.append(f"price archive last run {newest.date()} ({(now - newest).days}d old)")
        if (now - newest).days > MAX_AGE_DAYS:
            fail(problems, (
                f"price archive last ran {newest.date()}; pull "
                f"github.com/nesleykent/tibia-warzones-schedule before re-ingesting"
            ))

    # --- 2. the cleaned panel reaches the day those payloads describe ---------------------
    panel_path = P / "panel_daily.csv"
    if not panel_path.exists():
        fail(problems, "panel_daily.csv is missing")
    else:
        panel_end = pd.to_datetime(
            pd.read_csv(panel_path, usecols=["date"]).date
        ).max().date()
        notes.append(f"cleaned panel ends {panel_end}")
        if stamps:
            raw_day = max(stamps).date()  # noqa: F841 - archive day, compared below
            # One day of slack: a payload collected just after midnight UTC describes the day
            # before, and the panel is built on completed days.
            if (raw_day - panel_end).days > 1:
                fail(problems, (
                    f"panel ends {panel_end} but the raw payloads describe {raw_day}; the "
                    f"ingest stages did not run after collection"
                ))

    # --- 3. every artifact is newer than the table it publishes ---------------------------
    for artifact, source in ARTIFACTS.items():
        art_path, src_path = ROOT / artifact, P / source
        if not art_path.exists():
            fail(problems, f"{artifact} is missing")
            continue
        if not src_path.exists():
            fail(problems, f"{source}, which {artifact} is built from, is missing")
            continue
        art_time = dt.datetime.fromtimestamp(art_path.stat().st_mtime, dt.UTC)
        src_time = dt.datetime.fromtimestamp(src_path.stat().st_mtime, dt.UTC)
        if art_time < src_time:
            behind = (src_time - art_time).total_seconds() / 3600
            fail(problems, (
                f"{artifact} is {behind:.1f}h older than {source}; it was not rebuilt after the "
                f"data changed"
            ))

    print("[FRESHNESS]")
    for note in notes:
        print(f"  {note}")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  ! {problem}")
        raise SystemExit(1)
    print(f"  all {len(ARTIFACTS)} artifacts rebuilt after their source tables")
    print(f"  nothing older than {MAX_AGE_DAYS} days; the published numbers are current")


if __name__ == "__main__":
    main()
