"""Probability-weighted scenarios with price levels, derived rather than asserted.

A consulting report has to answer what the client should do tomorrow, and a refusal to give
levels is not an answer. The objection is fair. What is not acceptable is inventing the numbers,
so the levels and the probabilities here come from the same bootstrapped predictive distribution
the report already uses for its forecasts, and the scenario labels are attached afterwards to
regions of that distribution rather than chosen first and justified later.

The construction: resample historical index returns in blocks, so volatility clustering and fat
tails survive; propagate the current level forward; read the probability of each band directly
off the simulated paths. A band's probability is then a computed quantity, and the levels that
define it are chosen at round numbers a reader can act on.

Triggers and invalidation conditions are drawn from what the report establishes, not from
plausible-sounding mechanisms. In particular Section 6.6.9b finds that gold production does not
drive the price, so "gold inflation accelerates" is not available as a trigger; what is
available is the demand and attention side, dispersion, and the fee schedule.

    python scripts/29_scenarios.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = np.random.RandomState(20260731)
N_PATHS = 40000
BLOCK = 10                       # days per resampled block, to keep volatility clustering

R = json.load(open(P / "results.json"))
idx = pd.read_csv(P / "market_index.csv", parse_dates=["date"])
iv = idx.dropna(subset=["ew_price"]).sort_values("date")
lvl = float(iv.ew_price.iloc[-1])
rets = np.diff(np.log(iv.ew_price.values))
asof = iv.date.iloc[-1]
print(f"index at {lvl:,.0f} GP/TC on {asof:%Y-%m-%d}; {len(rets)} daily returns")

# Drift: the shrunk, capped estimate the report already uses, not the raw sample mean, because
# a 2.5-year sample mean on a unit-root series is mostly noise.
mu_raw = rets.mean()
se = rets.std() / np.sqrt(len(rets))
shrink = mu_raw ** 2 / (mu_raw ** 2 + se ** 2)
CAP = R["forecast"]["drift_cap_daily"]
mu = float(np.clip(mu_raw * shrink, -CAP, CAP))
print(f"drift: raw {mu_raw * 100:+.4f}%/day, shrunk and capped to {mu * 100:+.4f}%/day")


def simulate(h):
    """Block bootstrap of the index level h days ahead."""
    n_blocks = int(np.ceil(h / BLOCK))
    out = np.empty(N_PATHS)
    dev = rets - mu_raw                      # centre, then add the shrunk drift back
    for i in range(N_PATHS):
        starts = RNG.randint(0, len(dev) - BLOCK, size=n_blocks)
        path = np.concatenate([dev[s:s + BLOCK] for s in starts])[:h]
        out[i] = lvl * np.exp(path.sum() + mu * h)
    return out


HORIZONS = {"1 month": 30, "3 months": 91, "6 months": 182}
sims = {k: simulate(v) for k, v in HORIZONS.items()}
for k, v in sims.items():
    q = np.percentile(v, [10, 25, 50, 75, 90])
    print(f"  {k:>9}: p10 {q[0]:,.0f}  p25 {q[1]:,.0f}  median {q[2]:,.0f}  "
          f"p75 {q[3]:,.0f}  p90 {q[4]:,.0f}")

# Bands at round numbers, chosen to straddle the current level, with probabilities read off the
# simulation rather than assigned.
BANDS = [("Below 35,000", -np.inf, 35000),
         ("35,000 to 38,000", 35000, 38000),
         ("38,000 to 41,000", 38000, 41000),
         ("41,000 to 44,000", 41000, 44000),
         ("Above 44,000", 44000, np.inf)]
rows = []
for label, lo, hi in BANDS:
    row = {"band": label, "low": lo, "high": hi}
    for k, v in sims.items():
        row[k] = float(((v >= lo) & (v < hi)).mean())
    rows.append(row)
bands = pd.DataFrame(rows)
bands.to_csv(P / "scenario_bands.csv", index=False)
print("\n[BANDS] probability of the index finishing in each range")
print(bands.set_index("band")[list(HORIZONS)].map(lambda x: f"{x:.0%}").to_string())

# Three scenarios over three months, defined as contiguous regions of the same distribution so
# the probabilities sum to one and no region is double counted.
h3 = sims["3 months"]
CUT_LO, CUT_HI = 37000, 42000
scen = [
    {"scenario": "Base", "range": f"{CUT_LO:,} to {CUT_HI:,} GP/TC",
     "probability": float(((h3 >= CUT_LO) & (h3 < CUT_HI)).mean())},
    {"scenario": "Upside", "range": f"above {CUT_HI:,} GP/TC",
     "probability": float((h3 >= CUT_HI).mean())},
    {"scenario": "Downside", "range": f"below {CUT_LO:,} GP/TC",
     "probability": float((h3 < CUT_LO).mean())},
]
for s in scen:
    m = ((h3 >= CUT_LO) & (h3 < CUT_HI)) if s["scenario"] == "Base" else \
        (h3 >= CUT_HI) if s["scenario"] == "Upside" else (h3 < CUT_LO)
    s["conditional_median"] = float(np.median(h3[m])) if m.sum() else np.nan
sc = pd.DataFrame(scen)
sc.to_csv(P / "scenarios.csv", index=False)
print("\n[SCENARIOS] three months ahead")
print(sc.assign(probability=sc.probability.map("{:.0%}".format)).to_string(index=False))

# Levels a reader can act on: where the distribution says a move is unusual rather than normal.
# Percentiles at every horizon, so the report never has to hardcode a band.
pct_by_h = {k: {f"p{q}": float(np.percentile(v, q)) for q in (10, 25, 50, 75, 90)}
            for k, v in sims.items()}
for k, v in sims.items():
    pct_by_h[k]["prob_below_current"] = float((v < lvl).mean())

levels = {
    "current": lvl,
    "p10_3m": float(np.percentile(h3, 10)),
    "p25_3m": float(np.percentile(h3, 25)),
    "p75_3m": float(np.percentile(h3, 75)),
    "p90_3m": float(np.percentile(h3, 90)),
    "one_sd_month": float(np.std(np.log(sims["1 month"] / lvl))),
    "prob_below_current_3m": float((h3 < lvl).mean()),
}
# The arbitrage level that would matter: the cross-world gap at which the trade clears its cost.
band_pct = R["advanced"]["tar"]["threshold_pct"]
rt_small, rt_large = 4.0, R["fees"]["roundtrip_largest_decile_pct"]
levels["arb_break_even_gap_pct_large"] = rt_large
levels["arb_break_even_gap_pct_small"] = rt_small
levels["arb_act_gap_pct"] = float(max(rt_small, 2 * band_pct))
print(f"\n[LEVELS] 3-month p10 {levels['p10_3m']:,.0f} | p25 {levels['p25_3m']:,.0f} | "
      f"p75 {levels['p75_3m']:,.0f} | p90 {levels['p90_3m']:,.0f}")
print(f"[LEVELS] probability the index is below today's level in 3 months: "
      f"{levels['prob_below_current_3m']:.0%}")

out = json.load(open(P / "fundamentals_results.json"))
out["scenarios"] = {"as_of": str(asof.date()), "level": lvl, "n_paths": N_PATHS,
                    "percentiles": pct_by_h,
                    "block": BLOCK, "drift_daily_pct": mu * 100,
                    "bands": bands.to_dict("records"), "scenarios": sc.to_dict("records"),
                    "levels": levels, "horizons": HORIZONS}
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[SCENARIOS] written: scenario_bands, scenarios")
