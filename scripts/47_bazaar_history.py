"""Collect the Char Bazaar's full published history, and size it against the Market properly.

Two problems with how this study treated the Bazaar, both fixed here.

The first is coverage. The report compared CipSoft's official annual Bazaar total - all 93
worlds, all 365 days - against the sum of Market volume over the world-days this study happens
to observe, which in 2025 is 35 worlds on a typical day out of 93. Dividing a complete total by
a partial one and calling the quotient a venue ratio overstates it roughly twofold. The ratio
here is computed on comparable coverage: observed mean volume per world-day, scaled to the full
world count and calendar.

The second is that the Bazaar was described as a single annual number with no time series. It
is not. NabBot publishes a year page from 2020 onward, each carrying an annual TC total and a
monthly breakdown of auctions created and completed. That is six annual observations of value
and sixty-five monthly observations of activity - still not the daily series that would let the
venue enter the forecasting work, but far more than one number, and enough to say whether the
venue is growing, shrinking or flat.

Value is published annually only; the monthly series covers auction counts. Monthly TC is
therefore an estimate, formed by holding the year's mean price per completed auction constant
across its months, and is labelled as such wherever it is used.

    python scripts/47_bazaar_history.py            # refreshes the cache, then reports
"""
from __future__ import annotations

import json
import pathlib
import re
import time
import urllib.error
import urllib.request

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P, RAW = ROOT / "data" / "processed", ROOT / "data" / "raw"
CACHE = RAW / "char_bazaar_history.json"
YEARS = range(2020, 2027)
UA = "tibia-coins-research/1.0 (research; github.com/nesleykent/tibia-coins-intelligence)"

MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def fetch_year(year: int) -> dict | None:
    """Pull one year page and lift the auctions block out of its RSC payload."""
    url = f"https://nabbot.xyz/stats/{year}/all"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError):
        return None
    pl = "".join(re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S))
    pl = pl.encode().decode("unicode_escape", errors="ignore")
    if '"auctions":{' not in pl:
        return None                       # the Bazaar predates this year's statistics page
    i = pl.index('"auctions":{') + 11
    depth = 0
    for j in range(i, len(pl)):
        if pl[j] == "{":
            depth += 1
        elif pl[j] == "}":
            depth -= 1
            if depth == 0:
                break
    a = json.loads(pl[i:j + 1])
    months = a.get("perMonth", [])
    # The monthly counts must reconcile with the annual total, or the page is mid-update and
    # the year should not be trusted.
    if months and sum(m["created"] for m in months) != a["total"]:
        return None
    return {
        "year": year, "scope": "all worlds",
        "auctions_created": a["total"], "auctions_completed": a["totalCompleted"],
        "tc_exchanged": a["totalExchanged"], "tc_commission": a["totalComission"],
        "tc_fees": a["totalFees"], "tc_cancel_fees": a["totalCancelFees"],
        "highest_tc": a["mostExpensive"][0]["value"] if a.get("mostExpensive") else None,
        "months": [{"month": m["name"], "created": m["created"], "completed": m["successful"]}
                   for m in months],
        "partial_year": len(months) < 12,
    }


def collect() -> list[dict]:
    out = []
    for y in YEARS:
        got = fetch_year(y)
        if got:
            out.append(got)
            print(f"  {y}: {got['tc_exchanged']:>13,} TC over "
                  f"{got['auctions_completed']:>7,} completed auctions"
                  + ("  (partial year)" if got["partial_year"] else ""))
        else:
            print(f"  {y}: no auction statistics published")
        time.sleep(1.5)                   # the page is a courtesy, not an API
    return out


print("[BAZAAR] collecting the published year pages")
years = collect()
if years:
    CACHE.write_text(json.dumps(years, indent=1))
elif CACHE.exists():
    years = json.loads(CACHE.read_text())
    print("[BAZAAR] network unavailable; using the cache")
else:
    raise SystemExit("no Bazaar data and no cache")

full = [y for y in years if not y["partial_year"]]
hist = pd.DataFrame([{
    "year": y["year"], "auctions_created": y["auctions_created"],
    "auctions_completed": y["auctions_completed"], "tc_exchanged": y["tc_exchanged"],
    "mean_tc_per_auction": y["tc_exchanged"] / max(1, y["auctions_completed"]),
    "completion_rate": y["auctions_completed"] / max(1, y["auctions_created"]),
    "partial_year": y["partial_year"],
} for y in years])
hist.to_csv(P / "bazaar_history.csv", index=False)
print("\n[HISTORY] the Bazaar as a series, not a single number")
print(hist.assign(tc_exchanged=hist.tc_exchanged.map("{:,.0f}".format),
                  mean_tc_per_auction=hist.mean_tc_per_auction.map("{:,.0f}".format),
                  completion_rate=hist.completion_rate.map("{:.0%}".format))
      .to_string(index=False))

# Monthly activity, with TC estimated by holding the year's mean auction price constant.
mrows = []
for y in years:
    mean_tc = y["tc_exchanged"] / max(1, y["auctions_completed"])
    for m in y["months"]:
        mrows.append({"year": y["year"], "month": m["month"],
                      "month_num": MONTHS.index(m["month"]) + 1,
                      "created": m["created"], "completed": m["completed"],
                      "tc_estimated": m["completed"] * mean_tc})
mon = pd.DataFrame(mrows).sort_values(["year", "month_num"]).reset_index(drop=True)
mon.to_csv(P / "bazaar_monthly.csv", index=False)
print(f"\n[MONTHLY] {len(mon)} monthly observations of auction activity, "
      f"{mon.year.min()}-{mon.year.max()}")

# ---- the venue ratio, on comparable coverage ---------------------------------------------
pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
N_WORLDS = int(pan.world.nunique())
rows = []
for y in sorted(set(hist.year) & set(pan.date.dt.year.unique())):
    obs = pan[(pan.date.dt.year == y) & pan.tc_sold.notna()]
    if len(obs) < 500:
        continue
    days = obs.date.nunique()
    mean_wd = float(obs.tc_sold.mean())
    scaled = mean_wd * N_WORLDS * days
    baz = float(hist.loc[hist.year == y, "tc_exchanged"].iloc[0])
    # Compare like with like: the Bazaar total is for the whole year, so a partial calendar
    # on the Market side has to be scaled to the same span before the ratio means anything.
    baz_span = baz * days / 365
    rows.append({
        "year": y, "market_world_days_observed": len(obs),
        "market_world_days_possible": N_WORLDS * days,
        "coverage": len(obs) / (N_WORLDS * days),
        "market_tc_observed": float(obs.tc_sold.sum()),
        "market_tc_scaled": scaled,
        "bazaar_tc_year": baz, "bazaar_tc_same_span": baz_span,
        "ratio_naive": baz / float(obs.tc_sold.sum()),
        "ratio_comparable": baz_span / scaled,
    })
ven = pd.DataFrame(rows)
ven.to_csv(P / "venue_ratio_by_year.csv", index=False)
print("\n[RATIO] the Bazaar against the Market, naive and on comparable coverage")
print(ven.assign(coverage=ven.coverage.map("{:.0%}".format),
                 market_tc_scaled=ven.market_tc_scaled.map("{:,.0f}".format),
                 ratio_naive=ven.ratio_naive.map("{:.1f}x".format),
                 ratio_comparable=ven.ratio_comparable.map("{:.1f}x".format))[
          ["year", "coverage", "market_tc_scaled", "ratio_naive", "ratio_comparable"]]
      .to_string(index=False))

RES = {
    "years": years,
    "history": hist.to_dict("records"),
    "n_monthly_observations": int(len(mon)),
    "monthly_span": f"{mon.year.min()}-{mon.year.max()}",
    "value_is_annual_only": True,
    "monthly_tc_note": ("monthly TC is estimated by holding the year's mean price per "
                        "completed auction constant; only auction counts are published "
                        "monthly"),
    "ratio_by_year": ven.to_dict("records"),
    "ratio_comparable_latest": float(ven.ratio_comparable.iloc[-1]) if len(ven) else None,
    "ratio_naive_latest": float(ven.ratio_naive.iloc[-1]) if len(ven) else None,
    "coverage_latest": float(ven.coverage.iloc[-1]) if len(ven) else None,
    "peak_year": int(hist.loc[hist.tc_exchanged.idxmax(), "year"]),
    "peak_tc": float(hist.tc_exchanged.max()),
    "trough_year": int(hist.loc[hist[~hist.partial_year].tc_exchanged.idxmin(), "year"]),
    "trough_tc": float(hist[~hist.partial_year].tc_exchanged.min()),
}
res = json.loads((P / "results.json").read_text())
res.setdefault("venues", {})["bazaar_history"] = RES
(P / "results.json").write_text(json.dumps(res, indent=1, default=str))
print(f"\n[BAZAAR] written: bazaar_history, bazaar_monthly, venue_ratio_by_year")
