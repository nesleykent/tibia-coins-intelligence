"""Do the scenario bands actually cover at the rate they claim?

Section 7.5.3 states a probability for each price range, and those probabilities come from a
block bootstrap rather than from judgement. That makes them checkable, and unchecked they are
worth little: an interval that says 80% and covers 55% is worse than no interval, because it
invites a position size the evidence does not support.

The test walks the history. At each origin, only data up to that day is used to simulate the
distribution forward; the realised level is then compared with the bands that simulation
produced. Coverage is counted across origins, so the answer is out-of-sample by construction.

Two failure modes are worth separating. An interval can be too narrow, which understates risk,
or too wide, which wastes capital. The calibration curve below shows which, at each nominal
level, and the horizon at which it starts to break.

    python scripts/32_scenario_backtest.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = np.random.RandomState(99)
N_PATHS, BLOCK = 4000, 10
HORIZONS = (30, 91, 182)
NOMINAL = (0.5, 0.8, 0.9)

R = json.load(open(P / "results.json"))
CAP = R["forecast"]["drift_cap_daily"]
idx = pd.read_csv(P / "market_index.csv", parse_dates=["date"])
iv = idx.dropna(subset=["ew_price"]).sort_values("date").reset_index(drop=True)
lv = np.log(iv.ew_price.values)
print(f"index history: {len(lv)} days, {iv.date.iloc[0]:%Y-%m-%d} to {iv.date.iloc[-1]:%Y-%m-%d}")

MIN_HIST = 180


def simulate(hist, h, n=N_PATHS):
    """The same construction 29_scenarios.py uses, on a truncated history."""
    r = np.diff(hist)
    if len(r) < BLOCK * 3:
        return None
    mu_raw = r.mean()
    se = r.std() / np.sqrt(len(r))
    mu = float(np.clip(mu_raw * (mu_raw ** 2 / (mu_raw ** 2 + se ** 2)), -CAP, CAP))
    dev = r - mu_raw
    nb = int(np.ceil(h / BLOCK))
    starts = RNG.randint(0, len(dev) - BLOCK, size=(n, nb))
    paths = np.stack([np.concatenate([dev[s:s + BLOCK] for s in row])[:h] for row in starts])
    return hist[-1] + paths.sum(axis=1) + mu * h


rows = []
for h in HORIZONS:
    origins = range(MIN_HIST, len(lv) - h, 5)          # every fifth day, to keep it tractable
    for t in origins:
        sim = simulate(lv[:t + 1], h)
        if sim is None:
            continue
        actual = lv[t + h]
        for a in NOMINAL:
            lo, hi = np.quantile(sim, [(1 - a) / 2, 1 - (1 - a) / 2])
            rows.append({"horizon": h, "origin": t, "nominal": a,
                         "covered": bool(lo <= actual <= hi),
                         "width_pct": float((np.exp(hi) / np.exp(lo) - 1) * 100),
                         "actual_pctile": float((sim < actual).mean())})
    print(f"  horizon {h}d: {len(list(origins))} origins tested")

bt = pd.DataFrame(rows)
bt.to_csv(P / "scenario_backtest.csv", index=False)

cov = (bt.groupby(["horizon", "nominal"])
         .agg(coverage=("covered", "mean"), median_width_pct=("width_pct", "median"),
              n_origins=("covered", "size")).reset_index())
cov["error"] = cov.coverage - cov.nominal
print("\n[COVERAGE] realised against nominal, walking the history")
print(cov.assign(nominal=cov.nominal.map("{:.0%}".format),
                 coverage=cov.coverage.map("{:.1%}".format),
                 error=cov.error.map("{:+.1%}".format)).to_string(index=False))

# A calibrated simulator puts the realised outcome uniformly across its own percentiles. A
# clustered histogram is the tell: piled in the middle means the bands are too wide, piled at
# the tails means too narrow.
pit = []
for h in HORIZONS:
    v = bt[(bt.horizon == h) & (bt.nominal == 0.8)].actual_pctile.values
    if len(v) < 20:
        continue
    edges = np.linspace(0, 1, 11)
    counts, _ = np.histogram(v, bins=edges)
    expect = len(v) / 10
    chi2 = float(((counts - expect) ** 2 / expect).sum())
    pit.append({"horizon": h, "n": len(v), "chi2_uniform": chi2,
                "mean_pctile": float(v.mean()),
                "share_in_middle_50pct": float(((v > .25) & (v < .75)).mean())})
pt = pd.DataFrame(pit)
print("\n[CALIBRATION] where the realised outcome falls in its own forecast distribution")
print(pt.round(3).to_string(index=False))

verdict = []
for _, r in cov.iterrows():
    if abs(r.error) <= 0.10:
        verdict.append("well calibrated")
    elif r.error < 0:
        verdict.append("too narrow - understates risk")
    else:
        verdict.append("too wide - overstates risk")
cov["verdict"] = verdict
cov.to_csv(P / "scenario_coverage.csv", index=False)

RES = {"coverage": cov.to_dict("records"), "pit": pt.to_dict("records"),
       "n_origins_total": int(bt.origin.nunique()), "paths_per_origin": N_PATHS,
       "worst_error": float(cov.loc[cov.error.abs().idxmax(), "error"]),
       "worst_at": f"{int(cov.loc[cov.error.abs().idxmax(), 'horizon'])}d "
                   f"{cov.loc[cov.error.abs().idxmax(), 'nominal']:.0%} band",
       "well_calibrated": int((cov.error.abs() <= 0.10).sum()), "n_tested": int(len(cov))}
out = json.load(open(P / "fundamentals_results.json"))
out["scenario_backtest"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print(f"\n[BACKTEST] {RES['well_calibrated']} of {RES['n_tested']} band-horizon pairs land "
      f"within ten points of nominal; worst is the {RES['worst_at']} at "
      f"{RES['worst_error']:+.1%}")
