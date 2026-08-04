"""Collect per-world raw pages: GuildStats online-counter + TibiaMarket market_board.

One request per world per source, sequential with a polite delay.
GuildStats robots.txt is `Allow: /` (verified 2026-07-30).
"""
import json, os, sys, time, pathlib
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
P = ROOT / "data" / "processed"
# The world list used to be read from a scratchpad directory belonging to a since-deleted
# session, so collection failed with FileNotFoundError on any machine but the one that wrote it.
# The repository already tracks the list this script itself produces, and the world metadata
# behind it, so read those and keep the scratchpad only as a last resort.
ARCHIVE = pathlib.Path(
    "/private/tmp/claude-501/-Users-nesleykent-Code-Tibia-Coins/"
    "8add2f59-46e0-4dd2-9edd-8ce0dbeb3d2d/scratchpad/repo/data/market/world"
)
# --refresh ignores the on-disk cache. Without it `get()` returns "cached" for every file that
# already exists, so re-running collection to update prices fetched nothing at all.
REFRESH = "--refresh" in sys.argv
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

def world_list() -> list[str]:
    listed = RAW / "world_list.json"
    if listed.exists():
        names = json.load(open(listed))
        if names:
            return sorted(names)
    meta = P / "world_metadata.csv"
    if meta.exists():
        import csv
        with meta.open(newline="") as handle:
            names = [row["world"] for row in csv.DictReader(handle) if row.get("world")]
        if names:
            return sorted(names)
    if ARCHIVE.is_dir():
        return sorted(p.name for p in ARCHIVE.iterdir() if p.is_dir())
    raise SystemExit(
        "no world list: expected data/raw/world_list.json or data/processed/world_metadata.csv"
    )


worlds = world_list()
(RAW / "guildstats_oc").mkdir(parents=True, exist_ok=True)
(RAW / "market_board").mkdir(parents=True, exist_ok=True)
json.dump(worlds, open(RAW / "world_list.json", "w"), indent=1)

s = requests.Session()
s.headers["User-Agent"] = UA


def get(url, dest, delay, is_json=False):
    if dest.exists() and dest.stat().st_size > 2000 and not REFRESH:
        return "cached"
    for attempt in range(3):
        try:
            r = s.get(url, timeout=45)
            if r.status_code == 200 and len(r.content) > 500:
                if is_json:
                    r.json()  # validate
                dest.write_bytes(r.content)
                time.sleep(delay)
                return "ok"
            last = f"HTTP {r.status_code} len={len(r.content)}"
        except Exception as e:
            last = repr(e)[:80]
        time.sleep(2 + 3 * attempt)
    return "FAIL " + last


fails = []
for i, w in enumerate(worlds, 1):
    a = get(f"https://guildstats.eu/online-counter?world={w}",
            RAW / "guildstats_oc" / f"{w}.html", 1.2)
    b = get(f"https://api.tibiamarket.top/market_board?server={w}&item_id=22118",
            RAW / "market_board" / f"{w}.json", 0.5, is_json=True)
    if a.startswith("FAIL"):
        fails.append((w, "oc", a))
    if b.startswith("FAIL"):
        fails.append((w, "board", b))
    print(f"[{i:>3}/93] {w:<12} oc={a:<10} board={b}", flush=True)

print("\nFAILURES:", len(fails))
for f in fails:
    print("  ", f)
