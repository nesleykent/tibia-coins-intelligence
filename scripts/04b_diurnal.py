"""Diurnal population profile: how a single-instant player count misstates the daily average.

Uses the GuildStats `dataWeek` series (7 days x 15-minute resolution, 672 points per world).
Timestamp labels are Tibia server time (Europe/Berlin). Verified: Antica's page fetched at
18:45 UTC carries a final label of 20:45, i.e. label = UTC + 2 during CEST.

For each world we compute r(h) = (mean count at hour h) / (mean count over the whole week).
r(h) is exactly the multiplicative bias of a snapshot taken at hour h. Aggregating r(h) by
region shows whether the bias is a common scale factor (harmless to a log-population slope)
or a region-dependent rotation of the cross-section (not harmless).

Output: diurnal_profile.csv, snapshot_bias_by_hour.csv
"""
import json, re, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
WORLDS = json.load(open(RAW / "world_list.json"))
meta = pd.read_csv(OUT / "world_metadata.csv")
region = dict(zip(meta["world"], meta["region"]))

ARR = r"const\s+dataWeek\s*=\s*\{\s*labels:\s*(\[.*?\]),\s*values:\s*(\[.*?\])"
rows = []
for w in WORLDS:
    h = (RAW / "guildstats_oc" / f"{w}.html").read_text(encoding="utf-8", errors="replace")
    m = re.search(ARR, h, re.S)
    if not m:
        continue
    lab, val = json.loads(m.group(1)), json.loads(m.group(2))
    n = min(len(lab), len(val))
    for L, v in zip(lab[:n], val[:n]):
        t = re.search(r"(\d{2}):(\d{2})$", L)
        if t and v is not None and v >= 0:
            rows.append({"world": w, "hour_server": int(t.group(1)), "players": float(v)})

d = pd.DataFrame(rows)
d["region"] = d["world"].map(region)
d["hour_utc"] = (d["hour_server"] - 2) % 24          # CEST -> UTC

wk_mean = d.groupby("world")["players"].mean()
d["rel"] = d["players"] / d["world"].map(wk_mean)

prof = (d.groupby(["region", "hour_utc"])["rel"].mean().rename("instant_over_dailyavg")
        .reset_index())
prof["bias_factor"] = 1.0 / prof["instant_over_dailyavg"]   # dailyavg / instant
prof.to_csv(OUT / "diurnal_profile.csv", index=False)

wprof = d.groupby(["world", "hour_utc"])["rel"].mean().reset_index()
wprof["bias_factor"] = 1.0 / wprof["rel"]
wprof.to_csv(OUT / "snapshot_bias_by_hour.csv", index=False)

print("Peak hour and snapshot-bias factor (daily average / instantaneous count) by region")
print("week of", "7d ending 2026-07-30, 15-min resolution\n")
pk = prof.loc[prof.groupby("region")["instant_over_dailyavg"].idxmax()]
n_by_reg = d.groupby("region")["world"].nunique()
out = []
for _, r in pk.iterrows():
    reg = r["region"]
    sub = prof[prof.region == reg].set_index("hour_utc")["bias_factor"]
    out.append({"region": reg, "n_worlds": int(n_by_reg[reg]),
                "peak_hour_utc": int(r["hour_utc"]),
                "peak_hour_server": int((r["hour_utc"] + 2) % 24),
                "factor_at_0445utc": round(float(sub.loc[4]), 3),
                "factor_at_1843utc": round(float(sub.loc[18]), 3),
                "trough_factor": round(float(sub.max()), 3),
                "peak_factor": round(float(sub.min()), 3)})
res = pd.DataFrame(out).sort_values("factor_at_0445utc", ascending=False)
print(res.to_string(index=False))
res.to_csv(OUT / "snapshot_bias_summary.csv", index=False)
print("\nEurope/North America distortion ratio at 04:45 UTC: "
      f"{res.set_index('region').loc['Europe','factor_at_0445utc'] / res.set_index('region').loc['North America','factor_at_0445utc']:.2f}x")
