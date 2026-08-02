"""Ingest the Tibia Coin price archive into a tidy snapshot-level table.

Source: github.com/nesleykent/tibia-warzones-schedule
        data/market/world/<World>/<world>_tibia_coins.json
Item:   Tibia Coin, item_id 22118.

Output: data/processed/snapshots_raw.parquet  (one row per raw snapshot)
No cleaning is applied here beyond typing; -1 sentinels are preserved so that
the cleaning stage (03) is auditable in isolation.
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARCHIVE = pathlib.Path(
    "/private/tmp/claude-501/-Users-nesleykent-Code-Tibia-Coins/"
    "8add2f59-46e0-4dd2-9edd-8ce0dbeb3d2d/scratchpad/repo/data/market/world"
)
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
