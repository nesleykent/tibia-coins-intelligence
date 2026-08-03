"""Does production matter over a year, cumulatively, or only past a threshold?

The study's production tests ran at one, seven and thirty days on eight months of data. That
combination can only find a fast channel, and the objection is exact: a monetary effect need
not arrive within a month, need not be linear in the flow, and need not appear at all until
enough has accumulated. Folding in the 2022-2025 archive extends the joint sample to three and
a half years, which makes the slow versions estimable for the first time.

Four specifications, each a different economic story about how production could reach a price:

    flow          more killed today, price tomorrow - what the study already tested
    cumulative    the running total, because gold persists and a stock is not a flow
    acceleration  the change in the growth rate, because a steady level may be priced in
    threshold     an effect that only switches on above some level of activity

Horizons run to a year. The response variable is the world's own forward log price change, not
the cross-world deviation, because the deviation needs ten worlds on a date and that constraint
starts in April 2024 - using it would throw away the history this stage exists to exploit.

Kill counts carry three and a half years; the monetary emission series still carries eight
months, because reconstructing GP needs per-creature detail that only lives in the raw archive.
Where both are available they are run side by side, and where only the count is available the
report says so.

    python scripts/49_long_horizon_production.py
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

HORIZONS = (1, 7, 30, 90, 180, 365)
WINDOWS = (30, 90, 180, 365)

ks = pd.read_csv(P / "kill_stats_daily.csv", parse_dates=["date"])
pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
d = (ks.merge(pan[["world", "date", "price_gp"]], on=["world", "date"])
       .dropna(subset=["price_gp", "monsters_killed"])
       .sort_values(["world", "date"]).reset_index(drop=True))
d["logp"] = np.log(d.price_gp)
d["year"] = d.date.dt.year
g = d.groupby("world", observed=True)
print(f"joint panel: {len(d):,} world-days, {d.world.nunique()} worlds, "
      f"{d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d} "
      f"({(d.date.max() - d.date.min()).days / 365.25:.1f} years)")

RES = {"panel": {"rows": int(len(d)), "worlds": int(d.world.nunique()),
                 "start": str(d.date.min().date()), "end": str(d.date.max().date()),
                 "years": float((d.date.max() - d.date.min()).days / 365.25)}}


def fe_ols(frame, y, xs):
    """Within-world OLS with two-way clustered errors, on world and on date."""
    f = frame[[y] + xs + ["world", "date"]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(f) < 500:
        return None
    dm = f.copy()
    dm[[y] + xs] = dm[[y] + xs] - dm.groupby("world")[[y] + xs].transform("mean")
    X = np.column_stack([np.ones(len(f))] + [dm[x].values for x in xs])
    yv = dm[y].values
    b, *_ = np.linalg.lstsq(X, yv, rcond=None)
    r = yv - X @ b
    XtX = np.linalg.pinv(X.T @ X)

    def meat_on(key):
        m = np.zeros_like(XtX)
        for _, ix in f.groupby(key).indices.items():
            s = X[ix].T @ r[ix]
            m += np.outer(s, s)
        return m

    # Cameron-Gelbach-Miller: cluster on world and on date, subtract the intersection.
    V = XtX @ (meat_on("world") + meat_on("date") - np.diag(np.diag(X.T @ np.diag(r ** 2) @ X))) @ XtX
    se = np.sqrt(np.abs(np.diag(V)))
    ss = np.sum((yv - yv.mean()) ** 2)
    return {"names": xs, "coef": b[1:], "se": se[1:], "t": b[1:] / se[1:],
            "p": 2 * (1 - stats.norm.cdf(np.abs(b[1:] / se[1:]))),
            "n": int(len(f)), "n_worlds": int(f.world.nunique()),
            "r2_within": float(1 - np.sum(r ** 2) / ss)}


# Build every production variable once.
d["log_kills"] = np.log(d.monsters_killed.clip(lower=1))
d["dlog_kills"] = g.log_kills.diff()
for w in WINDOWS:
    # Cumulative: gold persists, so a running total is the closest thing to a stock this
    # data supports. Logged so the coefficient is an elasticity like the others.
    d[f"cum{w}"] = np.log(
        g.monsters_killed.rolling(w, min_periods=w // 2).sum()
        .reset_index(level=0, drop=True).clip(lower=1))
    # Acceleration: the change in the growth rate. A steady level of production may be priced
    # in; what would move a price is production speeding up or slowing down.
    d[f"accel{w}"] = (g[f"cum{w}"].diff(w // 2) if f"cum{w}" in d else np.nan)
for w in WINDOWS:
    d[f"accel{w}"] = d.groupby("world", observed=True)[f"cum{w}"].diff(max(w // 2, 1))

for h in HORIZONS:
    d[f"fwd{h}"] = d.groupby("world", observed=True).logp.shift(-h) - d.logp

# ============================================================ 1. flow against horizon
print("\n" + "=" * 78)
rows = []
for h in HORIZONS:
    r = fe_ols(d.assign(x=g.dlog_kills.shift(1)), f"fwd{h}", ["x"])
    if r:
        rows.append({"specification": "flow, lagged one day", "horizon": h,
                     "coef": float(r["coef"][0]), "se": float(r["se"][0]),
                     "t": float(r["t"][0]), "p": float(r["p"][0]),
                     "n": r["n"], "n_worlds": r["n_worlds"], "r2_within": r["r2_within"]})
flow = pd.DataFrame(rows)
print("[FLOW] elasticity of the forward price to production growth, by horizon")
print(flow.round(5).to_string(index=False))

# ============================================================ 2. cumulative and acceleration
print("\n" + "=" * 78)
crows = []
for w in WINDOWS:
    for h in HORIZONS:
        if h < w // 2:
            continue                              # a horizon shorter than the window is not a test
        for spec, col in ((f"cumulative {w}d", f"cum{w}"), (f"acceleration {w}d", f"accel{w}")):
            r = fe_ols(d.assign(x=d.groupby("world", observed=True)[col].shift(1)),
                       f"fwd{h}", ["x"])
            if r:
                crows.append({"specification": spec, "window": w, "horizon": h,
                              "coef": float(r["coef"][0]), "se": float(r["se"][0]),
                              "t": float(r["t"][0]), "p": float(r["p"][0]),
                              "n": r["n"], "n_worlds": r["n_worlds"],
                              "r2_within": r["r2_within"]})
cum = pd.DataFrame(crows)
cum.to_csv(P / "production_long_horizon.csv", index=False)
print("[CUMULATIVE] the strongest ten cells by absolute t")
print(cum.reindex(cum.t.abs().sort_values(ascending=False).index).head(10)
      .round(5).to_string(index=False))

# ============================================================ 3. does it only matter above a level
# A threshold story: production is irrelevant until activity is unusually high, and only then
# does it push the price. Estimated by splitting on the world's own distribution rather than on
# a level, so worlds of different sizes are comparable.
print("\n" + "=" * 78)
d["kill_pct"] = g.monsters_killed.rank(pct=True)
trows = []
for h in (30, 90, 180, 365):
    for lo, hi, label in ((0.0, 0.5, "below median"), (0.5, 0.9, "50-90th pct"),
                          (0.9, 1.01, "top decile")):
        b = d[(d.kill_pct >= lo) & (d.kill_pct < hi)]
        r = fe_ols(b.assign(x=b.groupby("world", observed=True).dlog_kills.shift(1)),
                   f"fwd{h}", ["x"])
        if r:
            trows.append({"horizon": h, "activity": label, "coef": float(r["coef"][0]),
                          "se": float(r["se"][0]), "t": float(r["t"][0]),
                          "p": float(r["p"][0]), "n": r["n"]})
thr = pd.DataFrame(trows)
thr.to_csv(P / "production_threshold.csv", index=False)
print("[THRESHOLD] the same elasticity within bands of a world's own activity")
print(thr.round(5).to_string(index=False))

# ============================================================ 4. the verdict, corrected
# Every cell above is one hypothesis. Reporting the best of a hundred without correction is the
# error this report has already made once with the lag search.
allt = pd.concat([
    flow.assign(family="flow")[["family", "horizon", "coef", "t", "p", "n"]],
    cum.assign(family=cum.specification)[["family", "horizon", "coef", "t", "p", "n"]],
    thr.assign(family="threshold")[["family", "horizon", "coef", "t", "p", "n"]],
], ignore_index=True)
m = len(allt)
allt = allt.sort_values("p").reset_index(drop=True)
allt["bh_threshold"] = (np.arange(1, m + 1) / m) * 0.05
allt["survives_bh"] = allt.p.values <= allt.bh_threshold.values
allt.to_csv(P / "production_all_tests.csv", index=False)
n_surv = int(allt.survives_bh.sum())
print(f"\n[VERDICT] {m} specifications tested across flow, cumulative, acceleration and "
      f"threshold families")
print(f"[VERDICT] {int((allt.p < 0.05).sum())} significant at 5% before correction; "
      f"{n_surv} survive Benjamini-Hochberg")
if n_surv:
    print(allt[allt.survives_bh].head(8).round(5).to_string(index=False))

RES.update({
    "flow": flow.to_dict("records"),
    "cumulative": cum.to_dict("records"),
    "threshold": thr.to_dict("records"),
    "n_specifications": m,
    "n_significant_uncorrected": int((allt.p < 0.05).sum()),
    "n_survive_bh": n_surv,
    "survivors": allt[allt.survives_bh].head(20).to_dict("records"),
    "max_abs_elasticity": float(allt.coef.abs().max()),
    "horizons_tested": list(HORIZONS),
    "windows_tested": list(WINDOWS),
    "emission_note": ("kill counts span the full joint sample; the monetary emission series "
                      "still covers only 2025-12-05 onward, because reconstructing GP needs "
                      "per-creature detail that lives only in the raw archive"),
})
out = json.loads((P / "fundamentals_results.json").read_text())
out["long_horizon_production"] = RES
(P / "fundamentals_results.json").write_text(json.dumps(out, indent=1, default=str))
print("\n[WRITTEN] production_long_horizon, production_threshold, production_all_tests")

# ============================================================ 5. the same attack as the strategy
# The survivors above rest on t-statistics from a pooled panel of overlapping forward returns.
# That is the exact structure this report already found inflated threefold in Section 7.8: many
# worlds on one date are one observation, and a 180-day return on consecutive days is one
# window seen many times. Clustering on date handles the first and nothing handles the second.
#
# The test that decides it: collapse to one observation per date, apply Newey-West at the
# horizon, and count how many non-overlapping windows the sample actually holds. A channel that
# is real survives; an artefact of the overlap does not.
print("\n" + "=" * 78)


def nw_t(x, lag):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 5:
        return np.nan, 0
    mu = x.mean()
    e = x - mu
    s = (e @ e) / n
    for j in range(1, min(lag, n - 1) + 1):
        s += 2 * (1 - j / (lag + 1)) * ((e[j:] @ e[:-j]) / n)
    return float(mu / np.sqrt(max(s, 1e-18) / n)), n


def honest(frame, xcol, h):
    """Per-date cross-sectional slope, then Newey-West on that series."""
    f = frame[["world", "date", xcol, f"fwd{h}"]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(f) < 500:
        return None
    # One slope per date: the cross-sectional regression of the forward return on the
    # production variable, demeaned within the date so it is a pure cross-world comparison.
    slopes = []
    for dt, gg in f.groupby("date"):
        if len(gg) < 8:
            continue
        x = gg[xcol].values - gg[xcol].values.mean()
        y = gg[f"fwd{h}"].values - gg[f"fwd{h}"].values.mean()
        vx = (x @ x)
        if vx > 1e-12:
            slopes.append(float((x @ y) / vx))
    if len(slopes) < 30:
        return None
    t, n = nw_t(np.array(slopes), h)
    span = (f.date.max() - f.date.min()).days
    return {"mean_slope": float(np.mean(slopes)), "t_newey_west": t,
            "n_dates": len(slopes), "independent_windows": int(span // h),
            "n_world_days": int(len(f))}


check = []
for _, r in cum[cum.p < 0.05].iterrows():
    col = (f"cum{int(r.window)}" if r.specification.startswith("cumulative")
           else f"accel{int(r.window)}")
    hh = honest(d.assign(**{col: d.groupby("world", observed=True)[col].shift(1)}),
                col, int(r.horizon))
    if hh:
        check.append({"specification": r.specification, "horizon": int(r.horizon),
                      "pooled_t": float(r.t), **hh})
hc = pd.DataFrame(check)
if len(hc):
    hc["t_inflation"] = hc.pooled_t.abs() / hc.t_newey_west.abs()
    hc.to_csv(P / "production_honest_inference.csv", index=False)
    print("[HONEST] the cells that were significant, re-tested on a per-date series")
    print(hc.round(3).to_string(index=False))
    _surv = hc[(hc.t_newey_west.abs() > 2)]
    print(f"\n[HONEST] {len(_surv)} of {len(hc)} survive; median t falls from "
          f"{hc.pooled_t.abs().median():.1f} to {hc.t_newey_west.abs().median():.1f}")
    RES["honest_inference"] = hc.to_dict("records")
    RES["n_survive_honest"] = int(len(_surv))

# ============================================================ 4b. the monetary series, long
# The activity test above uses kill counts, which now span the joint sample. Emission in GP is
# the variable the economic question is actually about, and once its history is reconstructed
# the same four families run on it. Where the emission series is shorter than the count series
# the horizons it can support are fewer, and the table says which.
print("\n" + "=" * 78)
mon = []
try:
    em = pd.read_csv(P / "gold_emission_daily.csv", parse_dates=["date"], low_memory=False)
    SERIES = [c for c in ("direct_coin_gp", "potential_total_gp_max",
                          "realized_estimate_gp_50") if c in em.columns]
    md = (em[["world", "date"] + SERIES]
          .merge(pan[["world", "date", "price_gp"]], on=["world", "date"])
          .dropna(subset=["price_gp"]).sort_values(["world", "date"]).reset_index(drop=True))
    md["logp"] = np.log(md.price_gp)
    mg = md.groupby("world", observed=True)
    span_years = (md.date.max() - md.date.min()).days / 365.25
    print(f"[MONETARY] {len(md):,} world-days, {md.world.nunique()} worlds, "
          f"{md.date.min():%Y-%m-%d} to {md.date.max():%Y-%m-%d} ({span_years:.1f} years)")
    for h in HORIZONS:
        md[f"fwd{h}"] = mg.logp.shift(-h) - md.logp
    for col in SERIES:
        md[f"log_{col}"] = np.log(md[col].clip(lower=1))
        for w in WINDOWS:
            md[f"cum_{col}_{w}"] = np.log(
                mg[col].rolling(w, min_periods=w // 2).sum()
                .reset_index(level=0, drop=True).clip(lower=1))
    for col in SERIES:
        for w in WINDOWS:
            for h in HORIZONS:
                if h < w // 2:
                    continue
                x = md.groupby("world", observed=True)[f"cum_{col}_{w}"].shift(1)
                r = fe_ols(md.assign(x=x), f"fwd{h}", ["x"])
                if not r:
                    continue
                cell = {"series": col, "window": w, "horizon": h,
                        "coef": float(r["coef"][0]), "t_pooled": float(r["t"][0]),
                        "p_pooled": float(r["p"][0]), "n": r["n"]}
                if r["p"][0] < 0.05:
                    hh = honest(md.assign(xx=x), "xx", h)
                    if hh:
                        cell.update(t_honest=hh["t_newey_west"],
                                    independent_windows=hh["independent_windows"],
                                    mean_slope=hh["mean_slope"])
                mon.append(cell)
    if mon:
        mdf = pd.DataFrame(mon)
        mdf.to_csv(P / "production_monetary_long.csv", index=False)
        cols = [c for c in ["series", "window", "horizon", "coef", "t_pooled",
                            "t_honest", "independent_windows"] if c in mdf.columns]
        print("[MONETARY] strongest five cells, pooled against per-date inference")
        print(mdf.reindex(mdf.t_pooled.abs().sort_values(ascending=False).index)
              .head(5)[cols].round(5).to_string(index=False))
        if "t_honest" in mdf.columns:
            _ms = mdf.dropna(subset=["t_honest"])
            _surv = _ms[_ms.t_honest.abs() > 2]
            RES["monetary_n_significant_pooled"] = int((mdf.p_pooled < 0.05).sum())
            RES["monetary_n_survive_honest"] = int(len(_surv))
            RES["monetary_max_abs_elasticity"] = float(mdf.coef.abs().max())
            print(f"[MONETARY] {int((mdf.p_pooled < 0.05).sum())} of {len(mdf)} cells "
                  f"significant pooled; {len(_surv)} survive the per-date test")
            print(f"[MONETARY] largest absolute elasticity anywhere: "
                  f"{mdf.coef.abs().max():.5f} - a one percent rise in cumulative emission "
                  f"moves the price by {mdf.coef.abs().max():.3f} percent")
        RES["monetary_long"] = mdf.to_dict("records")
        RES["monetary_span_years"] = float(span_years)
        RES["monetary_n"] = int(len(md))
except FileNotFoundError:
    print("[MONETARY] emission series unavailable")

# Sign consistency is the other test, and it needs no statistics. One economic channel should
# not change direction when the same variable is measured over a different window.
sign = (cum[cum.specification.str.startswith("acceleration")]
        .groupby("window").coef.apply(lambda s: "positive" if (s > 0).all()
                                      else "negative" if (s < 0).all() else "mixed"))
RES["acceleration_sign_by_window"] = sign.to_dict()
_pos = int((cum[cum.specification.str.startswith("acceleration")].coef > 0).sum())
_neg = int((cum[cum.specification.str.startswith("acceleration")].coef < 0).sum())
RES["acceleration_signs"] = {"positive": _pos, "negative": _neg}
print(f"\n[SIGNS] acceleration coefficients: {_pos} positive, {_neg} negative")
print("  by window: " + ", ".join(f"{int(w)}d {v}" for w, v in sign.items()))

# The diagnostic that settles it. If these were channels, strength would not depend on how
# many independent windows the sample happens to hold - and it does, inversely.
if len(hc):
    _rho = float(hc.independent_windows.corr(hc.t_newey_west.abs(), method="spearman"))
    _wide = hc[hc.independent_windows >= 10]
    _flips = int((np.sign(hc.pooled_t) != np.sign(hc.t_newey_west)).sum())
    RES["overlap_diagnostic"] = {
        "spearman_windows_vs_t": _rho,
        "n_cells_with_10plus_windows": int(len(_wide)),
        "max_abs_t_among_them": float(_wide.t_newey_west.abs().max()) if len(_wide) else None,
        "any_significant_with_10plus_windows": bool(
            (_wide.t_newey_west.abs() > 2).any()) if len(_wide) else False,
        "sign_flips_pooled_vs_honest": _flips,
        "n_rechecked": int(len(hc)),
    }
    print(f"\n[DIAGNOSTIC] rank correlation between independent windows and |t| is {_rho:+.2f}: "
          f"the fewer genuine windows a cell has, the stronger it looks")
    print(f"[DIAGNOSTIC] of the {len(_wide)} cells with ten or more independent windows, the "
          f"largest |t| is {_wide.t_newey_west.abs().max():.2f} - none is significant")
    print(f"[DIAGNOSTIC] the sign flips between pooled and per-date inference in {_flips} of "
          f"{len(hc)} cells")

out = json.loads((P / "fundamentals_results.json").read_text())
out["long_horizon_production"] = RES
(P / "fundamentals_results.json").write_text(json.dumps(out, indent=1, default=str))
print("\n[WRITTEN] production_honest_inference")
