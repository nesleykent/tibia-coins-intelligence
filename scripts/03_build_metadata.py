"""Build world metadata, merge register, event calendar and population panel.

Outputs (data/processed/):
  world_metadata.csv        93 worlds x attributes incl. documented creation date
  world_merge_register.csv  77 merges, 196 predecessor worlds
  world_transfers.csv       character world transfers (GuildStats)
  event_calendar.csv        daily global event flags + update windows
  population_daily.csv      daily players-online average per world (GuildStats dataAll)
  population_summary.csv    per-world period stats + 04:45 UTC snapshot + bias factor
"""
import json, re, pathlib, warnings
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

WORLDS = json.load(open(RAW / "world_list.json"))


def dparse(s):
    s = s.strip()
    for f in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return pd.Timestamp(pd.to_datetime(s, format=f))
        except Exception:
            pass
    return pd.NaT


# ---------------------------------------------------------------- merges
soup = BeautifulSoup(open(RAW / "gs_merge.html", encoding="utf-8", errors="replace").read(), "lxml")

# Each merge is a card: header (rank, destination, merge date, region flag) followed by a
# "Merged worlds" block of <div> rows, each holding two <span>s (predecessor, created date).
# Parsed from the DOM rather than flattened text: the last card abuts the page footer, and
# one predecessor carries a malformed source date ("16-00-2004", Tenebra) that must be kept
# as a named predecessor with a missing date rather than truncating the card.
merge_rows = []
for label in soup.find_all("div", string=re.compile(r"^\s*Merged worlds\s*$")):
    card = label.find_parent(
        lambda t: t.name == "div" and t.find("span", string=re.compile(r"^\s*#\d+\s*$")))
    if card is None:
        continue
    name_span = card.find("span", class_=re.compile("text-guild-green"))
    dest = name_span.get_text(strip=True)
    hdr_dates = [s.get_text(strip=True) for s in card.find_all("span")
                 if re.fullmatch(r"\d{2,4}-\d{2}-\d{2,4}", s.get_text(strip=True))]
    ddate = dparse(hdr_dates[0]) if hdr_dates else pd.NaT
    img = card.find("img", alt=True)
    reg = img["alt"] if img else None

    for row in label.find_next_sibling("div").find_all("div", recursive=False):
        spans = row.find_all("span")
        if len(spans) != 2:
            continue
        merge_rows.append({"merge_world": dest, "merge_date": ddate, "region": reg,
                           "predecessor": spans[0].get_text(strip=True),
                           "predecessor_created": dparse(spans[1].get_text(strip=True))})

merge = pd.DataFrame(merge_rows)
merge.to_csv(OUT / "world_merge_register.csv", index=False)
print(f"merges: {merge.merge_world.nunique()} destinations, "
      f"{len(merge)} predecessor links, {merge.predecessor.nunique()} distinct predecessors")

# ---------------------------------------------------------------- GuildStats worlds
gw = pd.read_html(RAW / "gs_worlds.html")[0]
gw.columns = ["rank", "world", "gs_updated", "gs_location", "avg_ppl_guild", "guilds",
              "ach_points", "sex_ratio", "people_in_guilds", "wars", "gs_type",
              "gs_battleye", "record_online_raw", "created"]
gw["created"] = pd.to_datetime(gw["created"], errors="coerce")
gw["record_online"] = (gw["record_online_raw"].astype(str)
                       .str.extract(r"^([\d,]+)")[0].str.replace(",", "").astype(float))
gw["record_date"] = pd.to_datetime(
    gw["record_online_raw"].astype(str).str.extract(r"Record at ([\d\-: ]+)")[0], errors="coerce")

# ---------------------------------------------------------------- TibiaData
td = json.load(open(RAW / "tibiadata_worlds.json"))["worlds"]
tdw = pd.DataFrame(td["regular_worlds"])
tdw = tdw.rename(columns={"name": "world", "location": "region", "players_online": "snapshot_online"})
tdw["snapshot_ts_utc"] = "04:45"

meta = tdw.merge(gw[["world", "created", "record_online", "record_date", "guilds",
                     "people_in_guilds", "ach_points"]], on="world", how="outer")

# merge flags
first_merge = merge.groupby("merge_world")["merge_date"].max()
meta["is_merge_destination"] = meta["world"].isin(merge["merge_world"])
meta["merge_date"] = meta["world"].map(first_merge)
preds = merge.groupby("merge_world")["predecessor"].apply(lambda s: "; ".join(sorted(s)))
meta["predecessor_worlds"] = meta["world"].map(preds)
meta["n_predecessors"] = meta["world"].map(merge.groupby("merge_world")["predecessor"].size())

# ---------------------------------------------------------------- first observation
snaps = pd.read_parquet(OUT / "snapshots_raw.parquet",
                        columns=["world", "date", "day_average_sell", "day_average_buy", "day_sold", "day_bought"])
fo = snaps.groupby("world")["date"].agg(first_obs="min", last_obs="max")
nobs = snaps.groupby(["world", "date"]).size().groupby("world").size().rename("n_world_days")
meta = meta.merge(fo, left_on="world", right_index=True, how="left")
meta = meta.merge(nobs, left_on="world", right_index=True, how="left")

WIN_START, WIN_END = snaps["date"].min(), snaps["date"].max()
meta["created_in_window"] = meta["created"] >= WIN_START
meta["launch_in_window"] = meta["created_in_window"] & ~meta["is_merge_destination"]
meta["age_at_first_obs_days"] = (meta["first_obs"] - meta["created"]).dt.days
meta["age_years_at_window_end"] = (WIN_END - meta["created"]).dt.days / 365.25

meta = meta.sort_values("world").reset_index(drop=True)
meta.to_csv(OUT / "world_metadata.csv", index=False)
print(f"metadata: {len(meta)} worlds | launches in window: {int(meta.launch_in_window.sum())} "
      f"| merge destinations in window: {int((meta.created_in_window & meta.is_merge_destination).sum())}")
print("  window:", WIN_START.date(), "->", WIN_END.date())

# ---------------------------------------------------------------- transfers
tr = pd.read_html(RAW / "gs_transfer.html")[0]
tr.columns = ["rank", "name", "level", "vocation", "former_world", "current_world", "change_date"]
tr["change_date"] = pd.to_datetime(tr["change_date"], errors="coerce")
tr.drop(columns=["rank"]).to_csv(OUT / "world_transfers.csv", index=False)
print(f"transfers: {len(tr)} records, {tr.change_date.min().date()} -> {tr.change_date.max().date()}")

# ---------------------------------------------------------------- event calendar
ev = json.load(open(RAW / "tm_events.json"))
erows = []
for d in ev:
    for e in d["events"]:
        erows.append({"date": pd.Timestamp(d["date"]).normalize(), "event": e.lstrip("*").strip()})
edf = pd.DataFrame(erows).drop_duplicates()

cal = pd.DataFrame({"date": pd.date_range(WIN_START, WIN_END, freq="D")})
XP = {"XP/Skill Event", "Skill Event", "Double XP Event"}
cal["ev_xp_skill"] = cal["date"].isin(edf.loc[edf.event.isin(XP), "date"]).astype(int)
cal["ev_rapid_respawn"] = cal["date"].isin(edf.loc[edf.event.eq("Rapid Respawn"), "date"]).astype(int)
cal["ev_loot"] = cal["date"].isin(edf.loc[edf.event.eq("Loot Event"), "date"]).astype(int)
cal["ev_exaltation"] = cal["date"].isin(edf.loc[edf.event.eq("Exaltation Overload"), "date"]).astype(int)
cal["ev_double_reward"] = cal["date"].isin(edf.loc[edf.event.eq("Double Daily Reward Month"), "date"]).astype(int)
cal["ev_any"] = cal["date"].isin(edf["date"]).astype(int)
cal["n_events"] = cal["date"].map(edf.groupby("date").size()).fillna(0).astype(int)

news = json.load(open(RAW / "tibiadata_news.json"))["news"]
upat = re.compile(r"^(Summer|Winter) Update (20\d\d)\s*$")
updates = sorted(pd.Timestamp(x["date"]) for x in news
                 if x["category"] == "development" and upat.match(x["news"].strip()))
updates_in = [u for u in updates if WIN_START <= u <= WIN_END]
cal["update_release"] = cal["date"].isin(updates_in).astype(int)
for lo, hi, name in [(-14, -1, "pre_update_14"), (-30, -1, "pre_update_30"),
                     (1, 30, "post_update_30"), (1, 14, "post_update_14"), (-7, -1, "pre_update_7")]:
    flag = np.zeros(len(cal), dtype=int)
    for u in updates_in:
        m = (cal["date"] >= u + pd.Timedelta(days=lo)) & (cal["date"] <= u + pd.Timedelta(days=hi))
        flag |= m.values.astype(int)
    cal[name] = flag

cal.to_csv(OUT / "event_calendar.csv", index=False)
edf.to_csv(OUT / "event_calendar_long.csv", index=False)
print(f"events: {len(cal)} days | XP/Skill {cal.ev_xp_skill.sum()} | Rapid Respawn "
      f"{cal.ev_rapid_respawn.sum()} | updates {cal.update_release.sum()} "
      f"({', '.join(str(u.date()) for u in updates_in)})")
