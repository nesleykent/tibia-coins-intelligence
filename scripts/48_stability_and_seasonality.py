"""Does the relationship hold in every season, every window and every regime?

Four gaps in how this study has argued, each named in review and each addressed here.

The report tests day-of-week and month effects and calls that seasonality. It is not: a month
dummy on a panel that spans three calendar years mixes the seasonal pattern with whatever the
level was doing in those particular months, and the game runs recurring events - double
experience, rapid respawn, loot weekends - whose timing is the obvious candidate for an annual
cycle. Section 1 separates within-year seasonality from the trend and tests the events jointly.

The report estimates one coefficient per relationship on the whole sample and never asks
whether it is the same coefficient throughout. Section 2 re-estimates the central reversion
parameter in rolling windows and asks whether its variation exceeds what sampling noise alone
would produce.

The forecast comparison is entirely statistical: a Diebold-Mariano test against a random walk,
reported as won or lost. A model can lose that test and still cut the average error a reader
would actually pay. Section 3 reports the economic size of the errors alongside the test.

And the whole study pools stress with calm. Section 4 splits out new-world launches, the
largest drawdowns and the highest-volatility days, and re-estimates in each.

    python scripts/48_stability_and_seasonality.py
"""
from __future__ import annotations

import json
import pathlib
import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
MIN_XW = 10

R = json.loads((P / "results.json").read_text())
THR = R["advanced"]["tar"]["threshold_pct"] / 100

pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date", "created"])
bw = pd.read_csv(P / "world_summary.csv")
conv = set(bw.query("converged").world)
d = pan[pan.world.isin(conv)][["world", "date", "price_gp", "created"]].dropna(
    subset=["price_gp"]).copy()
d["logp"] = np.log(d.price_gp)
n_on = d.groupby("date").world.transform("size")
d["dev"] = (d.logp - d.groupby("date").logp.transform("mean")).where(n_on >= MIN_XW)
d = d.dropna(subset=["dev"]).sort_values(["world", "date"]).reset_index(drop=True)
g = d.groupby("world", observed=True)
d["ret"] = g.logp.diff()
d["dev_lag"] = g.dev.shift(1)
d["d_dev"] = g.dev.diff()
d["age_days"] = (d.date - d.created).dt.days
print(f"panel: {len(d):,} world-days, {d.world.nunique()} worlds, "
      f"{d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d} "
      f"({(d.date.max() - d.date.min()).days / 365.25:.1f} years)")

RES = {}


def fe_ols(frame, y, xs, absorb=("world",)):
    """Within-group OLS with standard errors clustered on the first absorbed dimension."""
    f = frame[[y] + xs + list(absorb)].replace([np.inf, -np.inf], np.nan).dropna()
    if len(f) < 200:
        return None
    dm = f.copy()
    for a in absorb:
        dm[[y] + xs] = dm[[y] + xs] - dm.groupby(a)[[y] + xs].transform("mean")
    X = np.column_stack([np.ones(len(f))] + [dm[x].values for x in xs])
    yv = dm[y].values
    b, *_ = np.linalg.lstsq(X, yv, rcond=None)
    r = yv - X @ b
    XtX = np.linalg.pinv(X.T @ X)
    meat = np.zeros_like(XtX)
    for _, ix in f.groupby(absorb[0]).indices.items():
        Xg, rg = X[ix], r[ix]
        meat += np.outer(Xg.T @ rg, Xg.T @ rg)
    V = XtX @ meat @ XtX
    se = np.sqrt(np.diag(V))
    ss = np.sum((yv - yv.mean()) ** 2)
    return {"names": xs, "coef": b[1:], "se": se[1:], "t": b[1:] / se[1:],
            "p": 2 * (1 - stats.norm.cdf(np.abs(b[1:] / se[1:]))),
            "n": len(f), "r2_within": float(1 - np.sum(r ** 2) / ss)}


# ============================================================ 1. seasonality, properly
# A month dummy on a multi-year panel confounds the season with the level in that month. Adding
# a year fixed effect leaves only what recurs, which is the thing the word seasonality means.
print("\n" + "=" * 78)
d["month"] = d.date.dt.month
d["dow"] = d.date.dt.dayofweek
d["year"] = d.date.dt.year
for m in range(2, 13):
    d[f"m{m}"] = (d.month == m).astype(float)
for w in range(1, 7):
    d[f"w{w}"] = (d.dow == w).astype(float)

month_cols = [f"m{m}" for m in range(2, 13)]
naive = fe_ols(d, "ret", month_cols, absorb=("world",))
within = fe_ols(d, "ret", month_cols, absorb=("world", "year"))
rows = []
for label, r in (("month only, world FE", naive), ("month, world and year FE", within)):
    if r is None:
        continue
    # A joint test on the eleven month dummies, which is the question a reader has.
    w_stat = float(np.sum((r["coef"] / r["se"]) ** 2))
    rows.append({"specification": label, "n": r["n"], "r2_within": r["r2_within"],
                 "joint_chi2": w_stat, "df": len(month_cols),
                 "joint_p": float(1 - stats.chi2.cdf(w_stat, len(month_cols))),
                 "max_abs_t": float(np.max(np.abs(r["t"]))),
                 "largest_month_pct": float(r["coef"][int(np.argmax(np.abs(r["coef"])))] * 100)})
seas = pd.DataFrame(rows)
print("[SEASONALITY] month-of-year effects on the daily return")
print(seas.round(4).to_string(index=False))
RES["month_effects"] = seas.to_dict("records")

# Day of week, on the same footing.
dowr = fe_ols(d, "ret", [f"w{w}" for w in range(1, 7)], absorb=("world", "year"))
if dowr:
    w_stat = float(np.sum((dowr["coef"] / dowr["se"]) ** 2))
    RES["day_of_week"] = {"joint_chi2": w_stat, "df": 6,
                          "joint_p": float(1 - stats.chi2.cdf(w_stat, 6)),
                          "max_abs_t": float(np.max(np.abs(dowr["t"]))),
                          "r2_within": dowr["r2_within"]}
    print(f"[SEASONALITY] day-of-week joint chi2 {w_stat:.1f} on 6 df, "
          f"p = {RES['day_of_week']['joint_p']:.3f}")

# Recurring in-game events, tested jointly rather than one at a time. The event flags live in
# the fundamentals panel, which is shorter, so this runs on the overlap.
try:
    fp = pd.read_csv(P / "fundamentals_panel.csv", parse_dates=["date"])
    ev_cols = [c for c in fp.columns if c.startswith("ev_") and c != "ev_any"]
    # Drop events that never fire in this window: a constant column makes the design singular
    # and turns the joint statistic into NaN rather than into an answer.
    _dropped = [c for c in ev_cols if fp[c].nunique(dropna=True) < 2]
    ev_cols = [c for c in ev_cols if c not in _dropped]
    ed = d.merge(fp[["world", "date"] + ev_cols], on=["world", "date"], how="inner")
    er = fe_ols(ed, "ret", ev_cols, absorb=("world", "year"))
    if er:
        w_stat = float(np.sum((er["coef"] / er["se"]) ** 2))
        RES["events"] = {
            "n": er["n"], "n_events_tested": len(ev_cols),
            "events_never_observed": _dropped,
            "joint_chi2": w_stat, "df": len(ev_cols),
            "joint_p": float(1 - stats.chi2.cdf(w_stat, len(ev_cols))),
            "per_event": [{"event": n, "coef_pct": float(c * 100), "t": float(t),
                           "p": float(p)}
                          for n, c, t, p in zip(er["names"], er["coef"], er["t"], er["p"])],
        }
        print(f"[EVENTS] {len(ev_cols)} recurring events, joint chi2 {w_stat:.1f}, "
              f"p = {RES['events']['joint_p']:.3f} on {er['n']:,} world-days")
except FileNotFoundError:
    pass

# ============================================================ 2. is the coefficient stable
# The central relationship in this study is reversion of a world's deviation toward the
# cross-world mean. One number for three and a half years is an assumption, not a finding.
print("\n" + "=" * 78)
WIN, STEP = 180, 30
full = fe_ols(d, "d_dev", ["dev_lag"])
roll = []
dates = np.sort(d.date.unique())
for start in range(0, len(dates) - WIN, STEP):
    win = d[(d.date >= dates[start]) & (d.date < dates[min(start + WIN, len(dates) - 1)])]
    r = fe_ols(win, "d_dev", ["dev_lag"])
    if r:
        roll.append({"start": str(pd.Timestamp(dates[start]).date()),
                     "end": str(pd.Timestamp(dates[min(start + WIN, len(dates) - 1)]).date()),
                     "n": r["n"], "coef": float(r["coef"][0]), "se": float(r["se"][0]),
                     "t": float(r["t"][0])})
rw = pd.DataFrame(roll)
rw.to_csv(P / "rolling_reversion.csv", index=False)
print(f"[STABILITY] reversion coefficient in {len(rw)} rolling {WIN}-day windows")
print(f"  full sample {full['coef'][0]:+.4f} (se {full['se'][0]:.4f})")
print(f"  rolling     min {rw.coef.min():+.4f}  median {rw.coef.median():+.4f}  "
      f"max {rw.coef.max():+.4f}")
# If the parameter were constant, the spread of rolling estimates would be the spread sampling
# noise alone produces. Comparing the two is the test.
_obs_var = float(rw.coef.var(ddof=1))
_noise_var = float((rw.se ** 2).mean())
RES["stability"] = {
    "window_days": WIN, "step_days": STEP, "n_windows": int(len(rw)),
    "full_sample_coef": float(full["coef"][0]), "full_sample_se": float(full["se"][0]),
    "rolling_min": float(rw.coef.min()), "rolling_median": float(rw.coef.median()),
    "rolling_max": float(rw.coef.max()),
    "observed_variance": _obs_var, "sampling_variance": _noise_var,
    "variance_ratio": _obs_var / _noise_var if _noise_var else np.nan,
    "sign_stable": bool((rw.coef < 0).all() or (rw.coef > 0).all()),
    "share_significant": float((rw.t.abs() > 2).mean()),
}
print(f"  variance of estimates {_obs_var:.2e} against sampling variance {_noise_var:.2e} "
      f"- ratio {RES['stability']['variance_ratio']:.1f}")
print(f"  sign stable across every window: {RES['stability']['sign_stable']}; "
      f"significant in {RES['stability']['share_significant']:.0%}")

# ============================================================ 3. how large are the errors
# A Diebold-Mariano test says which model is more accurate. It does not say whether the
# difference is worth anything, and a reader holding coins cares about the second question.
print("\n" + "=" * 78)
idx = pd.read_csv(P / "market_index.csv", parse_dates=["date"])
iv = idx.dropna(subset=["ew_price"]).sort_values("date").reset_index(drop=True)
lv = np.log(iv.ew_price.values)
level = float(iv.ew_price.iloc[-1])
err = []
for h in (7, 30, 91):
    if len(lv) <= h + 200:
        continue
    actual = lv[h:] - lv[:-h]
    rw_f = np.zeros_like(actual)                       # random walk: no change
    # A drift model, the only alternative the report's own forecast section entertains.
    # i + 2, not i + 1: one observation has no difference to average, and the NaN
    # that produces propagates into every error statistic for this model.
    drift = np.array([np.mean(np.diff(lv[:i + 2])) * h for i in range(len(actual))])
    for name, f in (("random walk", rw_f), ("shrunk drift", drift)):
        e = f - actual
        err.append({
            "horizon": h, "model": name,
            "rmse_log": float(np.sqrt(np.mean(e ** 2))),
            "mae_log": float(np.mean(np.abs(e))),
            "median_abs_log": float(np.median(np.abs(e))),
            "mae_gp": float(np.mean(np.abs(e)) * level),
            "mae_pct_of_level": float(np.mean(np.abs(e)) * 100),
            "share_within_2pct": float(np.mean(np.abs(e) < 0.02)),
            "share_within_5pct": float(np.mean(np.abs(e) < 0.05)),
        })
ed = pd.DataFrame(err)
ed.to_csv(P / "forecast_error_magnitude.csv", index=False)
print("[MAGNITUDE] what the forecast error costs, not just which model wins")
print(ed.round(4).to_string(index=False))
RES["error_magnitude"] = ed.to_dict("records")
_rw7 = ed[(ed.horizon == 7) & (ed.model == "random walk")].iloc[0]
print(f"  at 7 days the random walk is wrong by {_rw7.mae_pct_of_level:.1f}% on average, "
      f"about {_rw7.mae_gp:,.0f} GP per coin")

# ============================================================ 4. stress against calm
# Every relationship above is estimated on the pool. If it changes when the market is under
# strain, the pooled number is an average of two different regimes.
print("\n" + "=" * 78)
d["vol21"] = g.ret.rolling(21).std().reset_index(level=0, drop=True)
d["is_launch"] = (d.age_days < 540).astype(int)
_vhi = d.vol21.quantile(0.9)
_dd = iv.set_index("date").ew_price
_peak = _dd.cummax()
_draw = (_dd / _peak - 1)
_stress_dates = set(_draw[_draw < -0.05].index)
d["in_drawdown"] = d.date.isin(_stress_dates).astype(int)

splits = [
    ("all observations", d),
    ("launch phase", d[d.is_launch == 1]),
    ("mature worlds", d[d.is_launch == 0]),
    ("top-decile volatility", d[d.vol21 >= _vhi]),
    ("calm volatility", d[d.vol21 < _vhi]),
    ("index in drawdown", d[d.in_drawdown == 1]),
    ("index at or near a high", d[d.in_drawdown == 0]),
]
srows = []
for label, frame in splits:
    r = fe_ols(frame, "d_dev", ["dev_lag"])
    if r:
        srows.append({"regime": label, "n": r["n"], "coef": float(r["coef"][0]),
                      "se": float(r["se"][0]), "t": float(r["t"][0]),
                      "half_life_days": (float(np.log(0.5) / np.log(1 + r["coef"][0]))
                                         if -1 < r["coef"][0] < 0 else np.nan)})
sd = pd.DataFrame(srows)
sd.to_csv(P / "regime_splits.csv", index=False)
print("[STRESS] the reversion coefficient by regime")
print(sd.round(4).to_string(index=False))
RES["regime_splits"] = sd.to_dict("records")
_base = sd[sd.regime == "all observations"].coef.iloc[0]
RES["stress_summary"] = {
    "pooled_coef": float(_base),
    "range": [float(sd.coef.min()), float(sd.coef.max())],
    "sign_stable": bool((sd.coef < 0).all()),
    "widest_gap_vs_pooled": float((sd.coef - _base).abs().max()),
}
print(f"  pooled {_base:+.4f}; across regimes {sd.coef.min():+.4f} to {sd.coef.max():+.4f}; "
      f"sign stable: {RES['stress_summary']['sign_stable']}")

out = json.loads((P / "fundamentals_results.json").read_text())
out["stability_seasonality"] = RES
(P / "fundamentals_results.json").write_text(json.dumps(out, indent=1, default=str))
print("\n[WRITTEN] rolling_reversion, forecast_error_magnitude, regime_splits")
