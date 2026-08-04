"""Ingest the Tibia Coin price archive into a tidy snapshot-level table.

Source: github.com/nesleykent/tibia-warzones-schedule
        data/market/world/<World>/<world>_tibia_coins.json
Item:   Tibia Coin, item_id 22118.

Output: data/processed/snapshots_raw.parquet  (one row per raw snapshot)
No cleaning is applied here beyond typing; -1 sentinels are preserved so that
the cleaning stage (03) is auditable in isolation.
"""
import json, os, pathlib, sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]

# The price history is the one input this project cannot regenerate, and its path used to point
# at a scratchpad directory belonging to a session that no longer exists. Nothing failed loudly:
# the archive was simply unreachable, so every re-run rebuilt the same frozen panel and the
# published end date never moved. Take the path from the command line, then the environment,
# then a conventional clone location, and fail with the clone command when none exists.
#
#     git clone --depth 1 --filter=blob:none --sparse \
#         https://github.com/nesleykent/tibia-warzones-schedule /tmp/tibia-warzones
#     cd /tmp/tibia-warzones && git sparse-checkout set data/market/world
CANDIDATES = [
    *(pathlib.Path(a) for a in sys.argv[1:] if not a.startswith("-")),
    *([pathlib.Path(os.environ["TIBIA_PRICE_ARCHIVE"])]
      if os.environ.get("TIBIA_PRICE_ARCHIVE") else []),
    pathlib.Path("/tmp/tibia-warzones/data/market/world"),
    pathlib.Path(
        "/private/tmp/claude-501/-Users-nesleykent-Code-Tibia-Coins/"
        "8add2f59-46e0-4dd2-9edd-8ce0dbeb3d2d/scratchpad/repo/data/market/world"
    ),
]
ARCHIVE = next((c for c in CANDIDATES if c.is_dir()), None)
if ARCHIVE is None:
    raise SystemExit(
        "price archive not found. Clone it and re-run:\n"
        "  git clone --depth 1 --filter=blob:none --sparse "
        "https://github.com/nesleykent/tibia-warzones-schedule /tmp/tibia-warzones\n"
        "  cd /tmp/tibia-warzones && git sparse-checkout set data/market/world\n"
        "Or set TIBIA_PRICE_ARCHIVE to an existing checkout."
    )
print(f"[INGEST] price archive: {ARCHIVE}")
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

rows = []
meta = []
for wdir in sorted(ARCHIVE.iterdir()):
    if not wdir.is_dir():
        continue
    f = wdir / f"{wdir.name.lower()}_tibia_coins.json"
    if not f.exists():
        cands = list(wdir.glob("*_tibia_coins.json"))
        if not cands:
            print("NO FILE", wdir.name)
            continue
        f = cands[0]
    d = json.load(open(f))
    flat = [r for grp in d["snapshots"] for r in grp]
    for r in flat:
        r["world"] = wdir.name
    rows.extend(flat)
    meta.append({"world": wdir.name, "status": d.get("status"),
                 "last_run_at": d.get("last_run_at"), "n_snapshots": len(flat)})

df = pd.DataFrame(rows)
df["ts"] = pd.to_datetime(df["time"], unit="s", utc=True)
df["date"] = df["ts"].dt.floor("D").dt.tz_localize(None)

assert (df["id"] == 22118).all(), "non-Tibia-Coin rows present"

num = [c for c in df.columns if c not in
       ("world", "ts", "date", "total_immediate_profit_info", "is_full_data", "id")]
for c in num:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.sort_values(["world", "ts"]).reset_index(drop=True)
df.to_parquet(OUT / "snapshots_raw.parquet", index=False)
pd.DataFrame(meta).to_csv(OUT / "archive_manifest.csv", index=False)

print("worlds        :", df["world"].nunique())
print("snapshots     :", len(df))
print("date range    :", df["date"].min().date(), "->", df["date"].max().date())
print("world-days    :", df.groupby(["world", "date"]).ngroups)
print("is_full_data  :", df["is_full_data"].value_counts().to_dict())
print("\nsentinel share (-1) by field:")
for c in sorted(num):
    if c in ("time",):
        continue
    print(f"  {c:<26} {(df[c] == -1).mean():6.1%}")
