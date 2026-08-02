"""Forecasts for the South American worlds at 2w / 1m / 3m / 6m.

Model: bootstrapped random walk with shrunk, capped drift and NO imposed level mean
reversion (Section 15 rejects stationarity of the level on essentially every world, so a
model that pulls the level back to a trailing mean would impose structure the data reject).

  log P(T+h) = log P(T) + h*mu_shrunk + sum of h resampled daily innovations

Innovations are drawn by moving-block bootstrap (block length 10 days) from the world's own
demeaned daily log returns, which preserves volatility clustering and the short-horizon
negative autocorrelation induced by measurement noise.

Drift treatment:
  mu_raw     = mean daily log return over the trailing 365 days
  shrinkage  = mu^2 / (mu^2 + se^2)   (empirical-Bayes weight; noisy drift -> shrunk to 0)
  mu_shrunk  = clip(shrinkage * mu_raw, +/- DRIFT_CAP)

Because the drift is heavily shrunk, the median forecast is, by construction, very close to
the current price. That is the intended behaviour, not a defect: the informative output is
the width of the prediction interval, not the central path.

Benchmarks: random walk (no drift) and seasonal naive (m = 7), evaluated on rolling origins.
"""
import json, pathlib, sys
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = np.random.default_rng(20260730)

HORIZONS = {"2w": 14, "1m": 30, "3m": 91, "6m": 182}
NSIM, BLOCK, DRIFT_CAP = 5000, 10, 0.0004      # cap |drift| at 0.04%/day (~15.4%/yr)
QS = [5, 10, 25, 50, 75, 90, 95]

panel = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
meta = pd.read_csv(P / "world_metadata.csv")
SA = sorted(meta.loc[meta.region == "South America", "world"])
print(f"South American worlds: {len(SA)}")


def get_series(w, upto=None):
    g = panel[panel.world == w].sort_values("date")
    if upto is not None:
        g = g[g.date <= upto]
    s = g.set_index("date")["price_gp"].asfreq("D").interpolate(limit=2)
    return s.dropna()


def drift(rets):
    r = rets[-365:] if len(rets) > 365 else rets
    if len(r) < 30:
        return 0.0, 0.0, 0.0
    mu, se = float(np.mean(r)), float(np.std(r, ddof=1) / np.sqrt(len(r)))
    shrink = mu ** 2 / (mu ** 2 + se ** 2) if (mu or se) else 0.0
    return float(np.clip(shrink * mu, -DRIFT_CAP, DRIFT_CAP)), mu, shrink


def block_boot(resid, h, nsim):
    """Moving-block bootstrap: nsim paths of length h drawn from `resid`."""
    n = len(resid)
    nb = int(np.ceil(h / BLOCK))
    starts = RNG.integers(0, max(n - BLOCK, 1), size=(nsim, nb))
    off = np.arange(BLOCK)
    idx = (starts[:, :, None] + off[None, None, :]).reshape(nsim, -1)[:, :h] % n
    return resid[idx]


MIN_OBS_FORECAST = 60      # launch-phase worlds are reported with an explicit caveat


def forecast(w, upto=None):
    s = get_series(w, upto)
    if len(s) < MIN_OBS_FORECAST:
        return None
    r_all = np.diff(np.log(s.values))
    r_all = r_all[np.isfinite(r_all)]
    mu, mu_raw, shrink = drift(r_all)
    # Innovations are drawn from the trailing year only, matching the drift window. A world
    # that went through a violent launch-phase convergence would otherwise have that episode
    # resampled into its forward interval long after the world had settled.
    r = r_all[-365:] if len(r_all) > 365 else r_all
    resid = r - r.mean()
    P0 = float(s.iloc[-1])
    out = {"world": w, "last_price": P0, "last_date": str(s.index[-1].date()),
           "mu_daily": mu, "mu_raw_daily": mu_raw, "shrinkage": shrink,
           "sigma_daily_pct": float(np.std(r, ddof=1) * 100), "n_obs": len(s),
           "n_innov": len(r)}
    for lab, h in HORIZONS.items():
        paths = block_boot(resid, h, NSIM)
        term = np.log(P0) + mu * h + paths.sum(axis=1)
        px = np.exp(term)
        q = np.percentile(px, QS)
        out[lab] = {f"p{p}": float(v) for p, v in zip(QS, q)}
        out[lab]["mean"] = float(px.mean())
        out[lab]["width_80_pct"] = float((q[5] - q[1]) / P0 * 100)
        out[lab]["prob_up"] = float((px > P0).mean())
    return out


# ------------------------------------------------------------------ forecasts
# Launch-phase worlds are still in price discovery: their level is trending toward the
# cross-world mean, so a flat-median random walk is least appropriate there. They are
# forecast and reported, but flagged, with the size of the remaining gap recorded.
launch = set(meta.loc[meta.launch_in_window.fillna(False), "world"])
xmean = pd.read_csv(P / "market_index.csv", parse_dates=["date"])
xmean_last = float(xmean.ew_price.iloc[-1])

fc = []
for w in SA:
    f = forecast(w)
    if not f:
        continue
    f["launch_phase"] = w in launch
    f["crossworld_mean_gp"] = xmean_last
    f["gap_to_crossworld_mean_pct"] = (xmean_last / f["last_price"] - 1) * 100
    fc.append(f)
json.dump(fc, open(P / "forecasts_sa.json", "w"), indent=1)
print(f"forecast worlds: {len(fc)}/{len(SA)} | launch-phase flagged: "
      f"{sum(f['launch_phase'] for f in fc)}")

rows = []
for f in fc:
    r = {"world": f["world"], "last_price": f["last_price"], "launch_phase": f["launch_phase"],
         "gap_to_mean_pct": f["gap_to_crossworld_mean_pct"],
         "sigma_daily_pct": f["sigma_daily_pct"], "mu_daily_pct": f["mu_daily"] * 100}
    for lab in HORIZONS:
        r[f"{lab}_p50"] = f[lab]["p50"]
        r[f"{lab}_p10"] = f[lab]["p10"]
        r[f"{lab}_p90"] = f[lab]["p90"]
        r[f"{lab}_w80"] = f[lab]["width_80_pct"]
    rows.append(r)
fcs = pd.DataFrame(rows)
fcs.to_csv(P / "forecasts_sa.csv", index=False)

# ------------------------------------------------------------------ backtest
end = panel.date.max()
origins = [end - pd.Timedelta(days=d) for d in range(200, 760, 40)]
conv_worlds = sorted(panel.loc[panel.converged, "world"].unique())
bt_worlds = sorted(set(SA) | set(conv_worlds))
bt = []
for w in bt_worlds:
    full = get_series(w)
    for o in origins:
        hist = full[full.index <= o]
        if len(hist) < 200:
            continue
        f = forecast(w, upto=o)
        if not f:
            continue
        for lab, h in HORIZONS.items():
            tgt = o + pd.Timedelta(days=h)
            if tgt not in full.index:
                continue
            actual = float(full.loc[tgt])
            P0 = float(hist.iloc[-1])
            sn = float(hist.iloc[-7]) if len(hist) >= 7 else P0     # seasonal naive, m=7
            bt.append({"world": w, "origin": o, "h": lab, "actual": actual,
                       "model": f[lab]["p50"], "rw": P0, "snaive": sn,
                       "is_sa": w in set(SA),
                       "in80": f[lab]["p10"] <= actual <= f[lab]["p90"],
                       "in90": f[lab]["p5"] <= actual <= f[lab]["p95"]})
bt = pd.DataFrame(bt)
bt.to_csv(P / "forecast_backtest.csv", index=False)


def bt_summary(d0):
    out = []
    for lab in HORIZONS:
        d = d0[d0.h == lab]
        if not len(d):
            continue
        row = {"horizon": lab, "n": len(d)}
        for m in ["model", "rw", "snaive"]:
            e = np.log(d[m] / d.actual)
            row[f"{m}_mape"] = float(np.mean(np.abs(d[m] / d.actual - 1)) * 100)
            row[f"{m}_rmsle"] = float(np.sqrt(np.mean(e ** 2)) * 100)
        row["cover80"] = float(d.in80.mean() * 100)
        row["cover90"] = float(d.in90.mean() * 100)
        out.append(row)
    return pd.DataFrame(out)


bs = bt_summary(bt)
bs_sa = bt_summary(bt[bt.is_sa])
bs.to_csv(P / "forecast_backtest_summary.csv", index=False)
bs_sa.to_csv(P / "forecast_backtest_summary_sa.csv", index=False)

res = json.load(open(P / "results.json"))
res["forecast"] = {
    "n_worlds": len(fc), "n_sim": NSIM, "block": BLOCK, "drift_cap_daily": DRIFT_CAP,
    "median_width80": {lab: float(fcs[f"{lab}_w80"].median()) for lab in HORIZONS},
    "median_width80_settled": {lab: float(fcs.loc[~fcs.launch_phase, f"{lab}_w80"].median())
                               for lab in HORIZONS},
    "n_launch_phase": int(fcs.launch_phase.sum()),
    "n_settled": int((~fcs.launch_phase).sum()),
    "max_width80_6m": float(fcs["6m_w80"].max()),
    "max_width80_6m_world": str(fcs.loc[fcs["6m_w80"].idxmax(), "world"]),
    "median_sigma_settled": float(fcs.loc[~fcs.launch_phase, "sigma_daily_pct"].median()),
    "median_sigma_launch": float(fcs.loc[fcs.launch_phase, "sigma_daily_pct"].median()),
    "median_drift_daily_pct": float(fcs.mu_daily_pct.median()),
    "max_abs_drift_daily_pct": float(fcs.mu_daily_pct.abs().max()),
    "median_sigma_daily_pct": float(fcs.sigma_daily_pct.median()),
    "backtest": bs.to_dict("records"), "backtest_sa": bs_sa.to_dict("records"),
    "median_p50_over_last": float(np.median(fcs["6m_p50"] / fcs.last_price)),
    # The median is near-flat only in the cross-section. Record the spread so the report can
    # say how far individual worlds depart from their current price rather than implying none do.
    "p50_dev_6m_pct": {
        "median": float(((fcs["6m_p50"] / fcs.last_price - 1) * 100).median()),
        "settled_abs_max": float(((fcs.loc[~fcs.launch_phase, "6m_p50"]
                                   / fcs.loc[~fcs.launch_phase, "last_price"] - 1) * 100)
                                 .abs().max()),
        "launch_abs_max": float(((fcs.loc[fcs.launch_phase, "6m_p50"]
                                  / fcs.loc[fcs.launch_phase, "last_price"] - 1) * 100)
                                .abs().max()),
        "n_over_5pct": int((((fcs["6m_p50"] / fcs.last_price - 1) * 100).abs() > 5).sum()),
    },
}
json.dump(res, open(P / "results.json", "w"), indent=1, default=str)

print("\nMedian 80% interval width (% of current price):")
for lab in HORIZONS:
    print(f"  {lab:>3}  {fcs[f'{lab}_w80'].median():5.1f}%")
print(f"\nDrift: median {fcs.mu_daily_pct.median():+.4f}%/day, "
      f"max |drift| {fcs.mu_daily_pct.abs().max():.4f}%/day (cap {DRIFT_CAP*100:.2f})")
print(f"Median 6m p50 / current price = {np.median(fcs['6m_p50'] / fcs.last_price):.4f}")
print("\nBACKTEST - all converged + SA worlds, 14 rolling origins (lower is better)")
print(bs.round(2).to_string(index=False))
print("\nBACKTEST - South American worlds only")
print(bs_sa.round(2).to_string(index=False))
