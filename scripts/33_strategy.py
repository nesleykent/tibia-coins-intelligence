"""Does any version of the cross-world trade clear its cost, or does none?

Section 6.6.10 reports the average net return across every signal that clears the band, and
that average is negative by a hair. An average across all signals is not a strategy. A trader
takes the strongest signals, not all of them, and holds long enough to amortise a cost that is
paid once per round trip rather than once per day. Neither variation has been tested, and until
they are, the claim that the market offers nothing is weaker than the report states it.

Three things are varied here, each of which could rescue the trade:

    signal strength   only the top decile of deviations, not every observation past the band
    holding period    7 to 91 days, against a round trip whose cost does not grow with time
    model ranking     a walk-forward model's predicted convergence, not the raw deviation

The point of the exercise is symmetric. If the strongest decile held for a quarter clears the
fee, the report owes the reader a strategy. If it does not, then a much stronger statement is
available than the one currently made: not that the average signal fails, but that the best
signal fails at every horizon, which is what closes the question.

    python scripts/33_strategy.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG, MIN_XW = 12345, 10
HORIZONS = (7, 14, 21, 30, 60, 91)

R = json.load(open(P / "results.json"))
THR = R["advanced"]["tar"]["threshold_pct"] / 100
FEE = R["fees"]["rate_pct"] / 100
SMALL_RT = 2 * FEE                                  # two 2% legs, no cap relief
LARGE_RT = R["fees"]["roundtrip_largest_decile_pct"] / 100

pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
bw = pd.read_csv(P / "world_summary.csv")
d = pan[pan.world.isin(set(bw.query("converged").world))][
    ["world", "date", "price_gp"]].dropna().copy()
d["logp"] = np.log(d.price_gp)
n_on = d.groupby("date").world.transform("size")
d["dev"] = (d.logp - d.groupby("date").logp.transform("mean")).where(n_on >= MIN_XW)
d = d.dropna(subset=["dev"]).sort_values(["world", "date"]).reset_index(drop=True)
g = d.groupby("world", observed=True)
d["dev_lag"] = g.dev.shift(1)
d["absdev"] = d.dev_lag.abs()
print(f"panel: {len(d):,} world-days, {d.world.nunique()} worlds, "
      f"{d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d}")

def by_date(frame, col="net", date_col="date"):
    """Collapse a pooled panel to one observation per date.

    The deviations this study trades are each world's log price minus the SAME cross-world
    mean, so two worlds qualifying on one day are not two independent observations - they are
    two views of one day, mechanically linked through the mean they are measured against.
    Averaging within the date is what makes the series a time series, which is the only thing
    a Newey-West correction knows how to handle.
    """
    return frame.groupby(date_col)[col].mean().sort_index().values


def independent_windows(frame, h, date_col="date"):
    """How many non-overlapping h-day windows the sample actually spans.

    Dividing row count by the horizon counts cross-sectional replication as independent time
    and overstates the sample roughly threefold here. The calendar span is the bound that
    matters.
    """
    span = (frame[date_col].max() - frame[date_col].min()).days
    return int(span // h)


def nw_t(x, lag):
    """Newey-West t against zero, for a mean estimated on overlapping windows.

    Pass a per-date series, not a pooled panel: see by_date above.
    """
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n, mu = len(x), x.mean()
    e = x - mu
    gamma0 = (e @ e) / n
    s = gamma0
    for j in range(1, min(lag, n - 1) + 1):
        gj = (e[j:] @ e[:-j]) / n
        s += 2 * (1 - j / (lag + 1)) * gj
    se = np.sqrt(max(s, 1e-18) / n)
    return float(mu / se), float(se)

RES = {}

# ============================================================ 1. strength and holding period
# The trade: sell the world trading rich, buy the world trading cheap, unwind H days later. The
# round trip is paid once whichever H is chosen, so a longer hold is the cheapest way to raise
# the gross return per unit of cost. If the cost is the only thing standing in the way, some
# horizon on this grid clears it.
rows = []
for h in HORIZONS:
    d[f"fwd{h}"] = g.dev.shift(-h) - d.dev
    sig = d.dropna(subset=[f"fwd{h}", "dev_lag"]).copy()
    sig["gross"] = -np.sign(sig.dev_lag) * sig[f"fwd{h}"]
    past = sig[sig.absdev > THR]
    if len(past) < 100:
        continue
    # Deciles of signal strength within the qualifying set: decile 10 is the widest gap.
    past = past.assign(dec=pd.qcut(past.absdev, 10, labels=False, duplicates="drop") + 1)
    for dec in sorted(past.dec.unique()):
        b = past[past.dec == dec]
        for label, cost in (("small offer", SMALL_RT), ("above the fee cap", LARGE_RT)):
            net = b.gross - cost
            rows.append({
                "horizon": h, "decile": int(dec), "cost_basis": label,
                "n": len(b), "mean_abs_dev_pct": float(b.absdev.mean() * 100),
                "gross_pct": float(b.gross.mean() * 100), "cost_pct": cost * 100,
                "net_pct": float(net.mean() * 100),
                "share_profitable": float((net > 0).mean()),
                # Both are reported because the difference is the point: the naive t treats
                # every world-day as an independent observation, which overstates the sample
                # roughly threefold, and the corrected one runs on the per-date series.
                "t_naive": float(stats.ttest_1samp(net, 0).statistic) if len(net) > 30 else np.nan,
                "t_stat": (nw_t(by_date(b.assign(net=b.gross - cost)), h)[0]
                           if len(net) > 30 else np.nan),
                "independent_windows": independent_windows(b, h)})
grid = pd.DataFrame(rows)
grid.to_csv(P / "strategy_grid.csv", index=False)

best = grid[grid.cost_basis == "above the fee cap"].sort_values("net_pct", ascending=False)
print("\n[GRID] best five cells, cheapest cost basis, by mean net return")
print(best.head(5)[["horizon", "decile", "n", "gross_pct", "net_pct", "share_profitable",
                    "t_stat"]].round(3).to_string(index=False))
print("\n[GRID] top decile at every horizon, cheapest cost basis")
top = grid[(grid.cost_basis == "above the fee cap") & (grid.decile == grid.decile.max())]
print(top[["horizon", "n", "mean_abs_dev_pct", "gross_pct", "net_pct", "share_profitable",
           "t_stat"]].round(3).to_string(index=False))

pos = best[(best.net_pct > 0) & (best.t_stat > 2)]
RES["grid"] = grid.to_dict("records")
RES["n_cells"] = int(len(grid))
RES["n_cells_positive_net"] = int((grid.net_pct > 0).sum())
RES["n_cells_significant"] = int(len(pos))
RES["best_cell"] = best.iloc[0].to_dict()

# ============================================================ 2. does holding longer help at all
# Cost is fixed per round trip, so net return must rise with the horizon if gross does. Whether
# it rises fast enough is the whole question, and the crossing point - if there is one - is the
# minimum holding period a trader would need.
hz = (grid[(grid.cost_basis == "above the fee cap") & (grid.decile == grid.decile.max())]
      .sort_values("horizon"))
cross = hz[hz.net_pct > 0]
RES["holding_period"] = {
    "gross_by_horizon": {int(r.horizon): float(r.gross_pct) for _, r in hz.iterrows()},
    "net_by_horizon": {int(r.horizon): float(r.net_pct) for _, r in hz.iterrows()},
    "first_profitable_horizon": int(cross.horizon.iloc[0]) if len(cross) else None,
    "gross_growth_7_to_91": float(hz.gross_pct.iloc[-1] / max(1e-9, hz.gross_pct.iloc[0])),
}
print(f"\n[HOLD] gross on the top decile grows from {hz.gross_pct.iloc[0]:.3f}% at 7 days to "
      f"{hz.gross_pct.iloc[-1]:.3f}% at {int(hz.horizon.iloc[-1])} days against a flat "
      f"{LARGE_RT * 100:.3f}% cost")
print(f"[HOLD] first horizon with a positive net on the top decile: "
      f"{RES['holding_period']['first_profitable_horizon']}")

# ============================================================ 3. rank by model, not by gap
# The deviation is a crude signal. A model that also sees momentum, dispersion and the world's
# own history may rank the same opportunities better. Walk-forward so the ranking at each date
# uses only what was knowable then.
FEATS = ["dev_lag", "absdev", "mom5", "mom21", "vol14", "dev_ma21", "dev_sd21", "xw_disp",
         "dev_rank"]
d["mom5"] = g.logp.shift(1) - g.logp.shift(6)
d["mom21"] = g.logp.shift(1) - g.logp.shift(22)
d["vol14"] = g.logp.diff().shift(1).rolling(14).std().reset_index(level=0, drop=True)
d["dev_ma21"] = g.dev.shift(1).rolling(21).mean().reset_index(level=0, drop=True)
d["dev_sd21"] = g.dev.shift(1).rolling(21).std().reset_index(level=0, drop=True)
d["xw_disp"] = d.groupby("date").dev_lag.transform("std")
d["dev_rank"] = d.groupby("date").dev_lag.rank(pct=True)

mrows = []
for h in (7, 30, 91):
    fit = d.dropna(subset=FEATS + [f"fwd{h}"]).copy()
    fit["gross"] = -np.sign(fit.dev_lag) * fit[f"fwd{h}"]
    dates = np.sort(fit.date.unique())
    folds = np.array_split(dates[int(len(dates) * 0.4):], 5)
    preds = []
    for k, test_dates in enumerate(folds):
        # Purge the horizon so no training row overlaps the test window.
        tr = fit[fit.date < pd.Timestamp(test_dates[0]) - pd.Timedelta(days=h)]
        te = fit[fit.date.isin(test_dates)]
        if len(tr) < 500 or len(te) < 50:
            continue
        m = RandomForestRegressor(n_estimators=300, min_samples_leaf=40, max_features=0.6,
                                  random_state=RNG, n_jobs=-1).fit(tr[FEATS].values,
                                                                   tr.gross.values)
        preds.append(te.assign(pred=m.predict(te[FEATS].values)))
    if not preds:
        continue
    pr = pd.concat(preds)
    pr["dec"] = pr.groupby("date").pred.rank(pct=True)
    for cut, name in ((0.9, "top decile"), (0.8, "top quintile"), (0.0, "all signals")):
        b = pr[pr.dec >= cut] if cut else pr
        net = b.gross - LARGE_RT
        mrows.append({"horizon": h, "selection": name, "n": len(b),
                      "gross_pct": float(b.gross.mean() * 100),
                      "net_pct": float(net.mean() * 100),
                      "share_profitable": float((net > 0).mean()),
                      "t_stat": float(stats.ttest_1samp(net, 0).statistic)})
mod = pd.DataFrame(mrows)
mod.to_csv(P / "strategy_model_ranked.csv", index=False)
print("\n[MODEL] walk-forward ranking, cheapest cost basis, net of the round trip")
print(mod.round(3).to_string(index=False))
RES["model_ranked"] = mod.to_dict("records")
RES["model_best_net_pct"] = float(mod.net_pct.max())
RES["model_any_significant"] = bool(((mod.net_pct > 0) & (mod.t_stat > 2)).any())

# ============================================================ 4. the verdict, stated as a number
# What a trader would need the gross to be, against what it is. This is the number that decides
# whether the report can offer a strategy, and it is reported either way.
tops = grid[grid.cost_basis == "above the fee cap"]
RES["verdict"] = {
    "cells_tested": int(len(tops)),
    "cells_net_positive": int((tops.net_pct > 0).sum()),
    "cells_net_positive_and_significant": int(((tops.net_pct > 0) & (tops.t_stat > 2)).sum()),
    "best_net_pct": float(tops.net_pct.max()),
    "best_cell": tops.loc[tops.net_pct.idxmax(), ["horizon", "decile", "n", "gross_pct",
                                                  "net_pct", "t_stat"]].to_dict(),
    "cost_pct": LARGE_RT * 100,
    "required_gross_pct": LARGE_RT * 100,
}
print(f"\n[VERDICT] {RES['verdict']['cells_net_positive']} of {RES['verdict']['cells_tested']} "
      f"strength-by-horizon cells clear the round trip; "
      f"{RES['verdict']['cells_net_positive_and_significant']} do so significantly. "
      f"Best cell nets {RES['verdict']['best_net_pct']:+.3f}%")

out = json.load(open(P / "fundamentals_results.json"))
out["strategy"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[STRATEGY] written: strategy_grid, strategy_model_ranked")

# ============================================================ 5. attack the result
# The numbers above are strong enough to be suspicious, and three things could manufacture them.
#
#   Overlap. Daily observations of an h-day forward return share h-1 days of data, so a naive
#   t-statistic is inflated by roughly the square root of the horizon. Newey-West with h lags,
#   and an effective sample size, replace it.
#
#   Selection on noise. Entering at t on a signal measured at t-1 selects worlds whose price is
#   momentarily off, and part of the "convergence" is then just that day's measurement error
#   unwinding. Delaying entry by a day removes the shared observation.
#
#   A few worlds or one episode. A strategy that works on three worlds in one quarter is not a
#   strategy. Stability is checked by year and by world.
print("\n" + "=" * 78)
ATT = {}





att = []
for h in HORIZONS:
    sig = d.dropna(subset=[f"fwd{h}", "dev_lag"]).copy()
    sig["gross"] = -np.sign(sig.dev_lag) * sig[f"fwd{h}"]
    past = sig[sig.absdev > THR]
    past = past.assign(dec=pd.qcut(past.absdev, 10, labels=False, duplicates="drop") + 1)
    b = past[past.dec == past.dec.max()]
    net = (b.gross - LARGE_RT).values
    t_naive = float(stats.ttest_1samp(net, 0).statistic)
    t_nw, se = nw_t(by_date(b.assign(net=b.gross - LARGE_RT)), h)
    att.append({"horizon": h, "n": len(net), "n_effective": independent_windows(b, h),
                "net_pct": float(net.mean() * 100), "t_naive": t_naive, "t_newey_west": t_nw,
                "inflation": float(t_naive / t_nw) if t_nw else np.nan})
atd = pd.DataFrame(att)
print("[OVERLAP] naive against Newey-West, top decile")
print(atd.round(3).to_string(index=False))
ATT["overlap"] = atd.to_dict("records")

# Delayed entry: signal from t-1, position opened at t+1, so the selection day is never the
# entry day. If the edge is measurement error unwinding, it dies here.
dly = []
for h in (7, 30, 91):
    sig = d.copy()
    sig["entry"] = g.dev.shift(-1)                       # open one day after the signal date
    sig["exit"] = g.dev.shift(-1 - h)
    sig["gross"] = -np.sign(sig.dev_lag) * (sig.exit - sig.entry)
    b = sig.dropna(subset=["gross"])
    b = b[b.absdev > THR]
    b = b.assign(dec=pd.qcut(b.absdev, 10, labels=False, duplicates="drop") + 1)
    b = b[b.dec == b.dec.max()]
    net = (b.gross - LARGE_RT).values
    t_nw, _ = nw_t(by_date(b.assign(net=b.gross - LARGE_RT)), h)
    dly.append({"horizon": h, "n": len(net), "net_pct": float(net.mean() * 100),
                "t_newey_west": t_nw, "share_profitable": float((net > 0).mean())})
dld = pd.DataFrame(dly)
print("\n[DELAYED ENTRY] one day between signal and execution")
print(dld.round(3).to_string(index=False))
ATT["delayed_entry"] = dld.to_dict("records")

# Concentration: by year, and how many worlds carry it.
h = 91
sig = d.dropna(subset=[f"fwd{h}", "dev_lag"]).copy()
sig["gross"] = -np.sign(sig.dev_lag) * sig[f"fwd{h}"]
b = sig[sig.absdev > THR]
b = b.assign(dec=pd.qcut(b.absdev, 10, labels=False, duplicates="drop") + 1)
b = b[b.dec == b.dec.max()].copy()
b["net"] = b.gross - LARGE_RT
b["year"] = b.date.dt.year
by_year = b.groupby("year").net.agg(["size", "mean"]).reset_index()
by_year["mean_pct"] = by_year["mean"] * 100
by_world = b.groupby("world").net.mean().sort_values(ascending=False)
print(f"\n[CONCENTRATION] {h}-day top decile, {b.world.nunique()} distinct worlds, "
      f"{(by_world > 0).sum()} of {len(by_world)} profitable on average")
print(by_year[["year", "size", "mean_pct"]].round(3).to_string(index=False))
ATT["by_year"] = by_year[["year", "size", "mean_pct"]].to_dict("records")
ATT["n_worlds_used"] = int(b.world.nunique())
ATT["n_worlds_profitable"] = int((by_world > 0).sum())
ATT["worst_year_net_pct"] = float(by_year.mean_pct.min())
ATT["top5_world_share"] = float(b[b.world.isin(by_world.head(5).index)].shape[0] / len(b))

# The short leg. Convergence is a relative quantity, and capturing it cleanly needs a position
# that profits when the rich world falls. Tibia has no mechanism for that, so the long-only
# version is what a player can actually run: buy on the cheap world instead of a random one.
lo = []
for h in (7, 30, 91):
    sig = d.copy()
    sig[f"absfwd{h}"] = g.logp.shift(-h) - sig.logp     # actual gold return of holding coins
    s = sig.dropna(subset=[f"absfwd{h}", "dev_lag"])
    cheap = s[s.dev_lag < -THR]
    rich = s[s.dev_lag > THR]
    allw = s
    # The recommendation is a difference in means, so it needs inference. The comparison is
    # made date by date - a cheap world against the same day's cross-world average - so the
    # market move common to both cancels and what is left is the selection effect alone.
    daily = (s.groupby("date")
              .apply(lambda x: (x.loc[x.dev_lag < -THR, f"absfwd{h}"].mean()
                                - x[f"absfwd{h}"].mean()) if (x.dev_lag < -THR).any() else np.nan)
              .dropna())
    t_nw, se = nw_t(daily.values, h)
    lo.append({"horizon": h,
               "cheap_world_pct": float(cheap[f"absfwd{h}"].mean() * 100),
               "any_world_pct": float(allw[f"absfwd{h}"].mean() * 100),
               "rich_world_pct": float(rich[f"absfwd{h}"].mean() * 100),
               "cheap_minus_any_pct": float((cheap[f"absfwd{h}"].mean()
                                             - allw[f"absfwd{h}"].mean()) * 100),
               "daily_paired_pct": float(daily.mean() * 100),
               "t_newey_west": t_nw,
               "n_dates": int(len(daily)),
               "n_dates_effective": int((daily.index.max() - daily.index.min()).days // h),
               "share_dates_positive": float((daily > 0).mean()),
               "n_cheap": len(cheap)})
lod = pd.DataFrame(lo)
print("\n[LONG ONLY] gold return of simply holding coins, by where they were bought")
print(lod.round(3).to_string(index=False))
ATT["long_only"] = lod.to_dict("records")

RES["attack"] = ATT
out = json.load(open(P / "fundamentals_results.json"))
out["strategy"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[ATTACK] written into strategy block")

# ============================================================ 6. how often does it actually occur
# A mean return per signal says nothing about how much of it a player can collect. If the top
# decile is one persistently cheap world sitting there for months, the 2,138 observations are
# not 2,138 opportunities - they are a handful of episodes counted daily. Episodes are runs of
# consecutive days a world spends in the qualifying set, and they are the unit a player trades.
h = 91
sig = d.dropna(subset=[f"fwd{h}", "dev_lag"]).copy()
sig["gross"] = -np.sign(sig.dev_lag) * sig[f"fwd{h}"]
q = sig[sig.absdev > THR]
cut = q.absdev.quantile(0.9)
q = sig[sig.absdev >= cut].sort_values(["world", "date"]).copy()

# A run breaks when a world drops out of the set for more than a week.
q["gap_days"] = q.groupby("world", observed=True).date.diff().dt.days.fillna(999)
q["episode"] = (q.gap_days > 7).groupby(q.world).cumsum()
ep = (q.groupby(["world", "episode"])
        .agg(start=("date", "min"), end=("date", "max"), days=("date", "size"),
             mean_dev=("absdev", "mean"), gross=("gross", "mean")).reset_index())
span_months = (d.date.max() - d.date.min()).days / 30.44
OCC = {
    "n_signal_days": int(len(q)),
    "n_episodes": int(len(ep)),
    "n_worlds": int(ep.world.nunique()),
    "median_episode_days": float(ep.days.median()),
    "episodes_per_month": float(len(ep) / span_months),
    "median_worlds_qualifying_per_day": float(q.groupby("date").size().median()),
    "share_days_with_any_signal": float(q.date.nunique() / d.date.nunique()),
    "episode_mean_gross_pct": float(ep.gross.mean() * 100),
    "episode_share_profitable": float((ep.gross - LARGE_RT > 0).mean()),
}
# Episodes are NOT independent, which the data says plainly: a median of 22 of the 177 start
# within any 91-day window, and the whole span holds only 9 non-overlapping quarters. Three
# figures are reported because they bracket the honest answer - assuming independence, then
# correcting for overlap in episode order, then the blunt version that keeps only genuinely
# disjoint windows.
ep = ep.sort_values("start")
_epnet = (ep.gross - LARGE_RT).values
_gap = ep.start.diff().dt.days.dropna().median()
_lag = int(round(h / max(_gap, 1)))
OCC["episode_t_naive"] = nw_t(_epnet, 1)[0]
OCC["episode_t_overlap_corrected"] = nw_t(_epnet, _lag)[0]
ep["_bin"] = ((ep.start - ep.start.min()).dt.days // h)
_binned = ep.groupby("_bin").apply(lambda g: (g.gross - LARGE_RT).mean()).values
OCC["episode_t_disjoint"] = nw_t(_binned, 1)[0]
OCC["episode_disjoint_windows"] = int(len(_binned))
OCC["episode_median_overlapping"] = int(
    np.median([((ep.start >= d) & (ep.start < d + pd.Timedelta(days=h))).sum()
               for d in ep.start]))
OCC["episode_t"] = OCC["episode_t_overlap_corrected"]
print("\n[OCCURRENCE] the top decile as episodes rather than as daily observations")
print(f"  {OCC['n_signal_days']:,} signal-days collapse to {OCC['n_episodes']} episodes across "
      f"{OCC['n_worlds']} worlds")
print(f"  median episode lasts {OCC['median_episode_days']:.0f} days; "
      f"{OCC['episodes_per_month']:.1f} new episodes per month")
print(f"  a qualifying world exists on {OCC['share_days_with_any_signal']:.0%} of days, "
      f"median {OCC['median_worlds_qualifying_per_day']:.0f} worlds at a time")
print(f"  per episode: gross {OCC['episode_mean_gross_pct']:+.2f}%, profitable on "
      f"{OCC['episode_share_profitable']:.0%}")
print(f"  t = {OCC['episode_t_naive']:.1f} assuming independence, "
      f"{OCC['episode_t_overlap_corrected']:.1f} corrected for overlap, "
      f"{OCC['episode_t_disjoint']:.1f} on {OCC['episode_disjoint_windows']} disjoint windows "
      f"(median {OCC['episode_median_overlapping']} episodes share any {h}-day window)")

# How much money can this actually absorb? An edge is worth what it can be sized at, and a
# world clearing a few thousand coins a day caps that hard. The bound taken here is one
# fee-cap lot per episode - the smallest order that reaches the cheap execution - which is
# already a large share of a day's volume on the world in question.
_ws = pd.read_csv(P / "world_summary.csv")
_daily_tc = float(pan_tc.median()) if (pan_tc := pd.read_csv(P / "panel_daily.csv")
                                       .query("world in @_ws.query('converged').world").tc_sold
                                       ).size else float("nan")
CAP_LOT = R["fees"]["cap_binds_at_lot_tc"]
px = float(pd.read_csv(P / "market_index.csv").ew_price.dropna().iloc[-1])
per_month_tc = OCC["episodes_per_month"] * CAP_LOT
CAPY = {
    "lot_tc": CAP_LOT,
    "episodes_per_month": OCC["episodes_per_month"],
    "tc_per_month": per_month_tc,
    "gp_per_month": per_month_tc * px,
    "lot_share_of_world_daily_volume": CAP_LOT / _daily_tc,
    "net_pct_30d": float(grid[(grid.horizon == 30) & (grid.decile == grid.decile.max()) &
                              (grid.cost_basis == "above the fee cap")].net_pct.iloc[0]),
}
CAPY["expected_gp_per_month"] = CAPY["gp_per_month"] * CAPY["net_pct_30d"] / 100
print(f"\n[CAPACITY] one fee-cap lot ({CAP_LOT:,.0f} TC) per episode, "
      f"{OCC['episodes_per_month']:.1f} episodes a month")
print(f"  deployable {per_month_tc:,.0f} TC/month = {CAPY['gp_per_month']:,.0f} GP")
print(f"  one lot is {CAPY['lot_share_of_world_daily_volume']:.0%} of a world's daily volume")
print(f"  expected profit at the 30-day net of {CAPY['net_pct_30d']:.2f}%: "
      f"{CAPY['expected_gp_per_month']:,.0f} GP/month")
RES["capacity"] = CAPY
RES["occurrence"] = OCC
ep.to_csv(P / "strategy_episodes.csv", index=False)

out = json.load(open(P / "fundamentals_results.json"))
out["strategy"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("[OCCURRENCE] written: strategy_episodes")

# ============================================================ 7. a true holdout
# Everything above characterises the full history, including the decile cutoff itself. That is
# an in-sample description, and this report has criticised weaker claims made the same way. So:
# split the history once, take the cutoff and nothing else from the training period, and score
# the final stretch having never looked at it. If the edge is a property of the sample rather
# than of the market, it dies here.
print("\n" + "=" * 78)
dates = np.sort(d.date.unique())
split = pd.Timestamp(dates[int(len(dates) * 0.70)])
print(f"[HOLDOUT] train to {split:%Y-%m-%d}, test after - "
      f"{(d.date > split).mean():.0%} of world-days held out")

hold = []
for h in (7, 30, 91):
    sig = d.dropna(subset=[f"fwd{h}", "dev_lag"]).copy()
    sig["gross"] = -np.sign(sig.dev_lag) * sig[f"fwd{h}"]
    tr = sig[sig.date <= split - pd.Timedelta(days=h)]     # purge the horizon at the boundary
    te = sig[sig.date > split]
    if len(tr) < 500 or len(te) < 100:
        continue
    # The only thing carried across the split is the cutoff, fitted on training data alone.
    cutoff = tr.loc[tr.absdev > THR, "absdev"].quantile(0.9)
    for label, frame in (("train", tr), ("holdout", te)):
        b = frame[frame.absdev >= cutoff]
        if len(b) < 30:
            continue
        net = (b.gross - LARGE_RT).values
        t_nw, _ = nw_t(by_date(b.assign(net=b.gross - LARGE_RT)), h)
        hold.append({"horizon": h, "period": label, "cutoff_pct": float(cutoff * 100),
                     "n": len(net), "n_effective": independent_windows(b, h),
                     "net_pct": float(net.mean() * 100), "t_newey_west": t_nw,
                     "share_profitable": float((net > 0).mean())})
hd = pd.DataFrame(hold)
hd.to_csv(P / "strategy_holdout.csv", index=False)
print(hd.round(3).to_string(index=False))

_ho = hd[hd.period == "holdout"]
HOLD = {
    "split_date": str(split.date()),
    "rows": hd.to_dict("records"),
    "holdout_positive_at_all_horizons": bool((_ho.net_pct > 0).all()),
    "holdout_min_net_pct": float(_ho.net_pct.min()),
    "holdout_min_t": float(_ho.t_newey_west.min()),
    "decay_vs_train": {int(r.horizon): float(
        r.net_pct - hd[(hd.horizon == r.horizon) & (hd.period == "train")].net_pct.iloc[0])
        for _, r in _ho.iterrows()},
}
print(f"\n[HOLDOUT] positive at every horizon out of sample: "
      f"{HOLD['holdout_positive_at_all_horizons']}; weakest net "
      f"{HOLD['holdout_min_net_pct']:+.3f}% at t = {HOLD['holdout_min_t']:.1f}")
print(f"[HOLDOUT] change against the training period: "
      + ", ".join(f"{k}d {v:+.2f}pp" for k, v in HOLD["decay_vs_train"].items()))
RES["holdout"] = HOLD

out = json.load(open(P / "fundamentals_results.json"))
out["strategy"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("[HOLDOUT] written: strategy_holdout")

# ============================================================ 8. is the edge regime-dependent
# The holdout paid more than the training period, which is the wrong direction for comfort. The
# obvious explanation is that gaps were wider in the holdout, since the trade is paid out of
# dispersion. If so the edge is not a constant to be assumed but a function of something a
# reader can observe today, which is a more useful thing to report either way.
print("\n" + "=" * 78)
disp = d.groupby("date").dev.std().rename("disp")
d2 = d.join(disp, on="date")
tr_disp = float(disp[disp.index <= split].mean())
te_disp = float(disp[disp.index > split].mean())
print(f"[REGIME] mean cross-world dispersion: train {tr_disp:.4f}, holdout {te_disp:.4f} "
      f"({te_disp / tr_disp - 1:+.0%})")

# Does the payoff scale with dispersion observable on the day the trade is opened?
reg = []
for h in (7, 30):
    sig = d2.dropna(subset=[f"fwd{h}", "dev_lag", "disp"]).copy()
    sig["gross"] = -np.sign(sig.dev_lag) * sig[f"fwd{h}"]
    cutoff = sig.loc[sig.absdev > THR, "absdev"].quantile(0.9)
    b = sig[sig.absdev >= cutoff].copy()
    b["disp_q"] = pd.qcut(b.disp, 3, labels=["low", "mid", "high"])
    for q, g_ in b.groupby("disp_q", observed=True):
        net = (g_.gross - LARGE_RT).values
        t_nw, _ = nw_t(by_date(g_.assign(net=g_.gross - LARGE_RT)), h)
        reg.append({"horizon": h, "dispersion": str(q),
                    "mean_disp_pct": float(g_.disp.mean() * 100),
                    "n": len(net), "n_effective": independent_windows(g_, h),
                    "net_pct": float(net.mean() * 100), "t_newey_west": t_nw,
                    "share_profitable": float((net > 0).mean())})
rg = pd.DataFrame(reg)
rg.to_csv(P / "strategy_regime.csv", index=False)
print("\n[REGIME] the same trade, split by the dispersion observable when it is opened")
print(rg.round(3).to_string(index=False))

_now = float(disp.iloc[-1])
_pct_now = float((disp < _now).mean())
REG = {
    "train_mean_disp": tr_disp, "holdout_mean_disp": te_disp,
    "holdout_vs_train": te_disp / tr_disp - 1,
    "rows": rg.to_dict("records"),
    "current_disp": _now,
    "current_percentile": _pct_now,
    "monotone_in_dispersion": bool(
        all(rg[rg.horizon == h].sort_values("mean_disp_pct").net_pct.is_monotonic_increasing
            for h in (7, 30))),
}
print(f"\n[REGIME] dispersion today {_now * 100:.2f}%, the "
      f"{_pct_now:.0%} percentile of its own history")
print(f"[REGIME] net rises monotonically with dispersion at both horizons: "
      f"{REG['monotone_in_dispersion']}")
RES["regime"] = REG

out = json.load(open(P / "fundamentals_results.json"))
out["strategy"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("[REGIME] written: strategy_regime")

# ============================================================ 9. normalise the signal
# The edge falls as dispersion rises, which is the opposite of what a "wider gaps pay more"
# story predicts and points at a different reading: what reverts is not a large gap but an
# ANOMALOUS one. A 10% gap where the typical gap is 5% is an outlier; the same 10% where the
# typical gap is 11% is just the regime. If that is right, dividing the deviation by prevailing
# dispersion should select better than the raw deviation does.
print("\n" + "=" * 78)
d2["z"] = d2.dev_lag / d2.disp                      # gaps in units of the day's own dispersion
cmp_rows = []
for h in (7, 30, 91):
    sig = d2.dropna(subset=[f"fwd{h}", "dev_lag", "disp"]).copy()
    sig["gross"] = -np.sign(sig.dev_lag) * sig[f"fwd{h}"]
    sig["absz"] = sig.z.abs()
    for name, col in (("raw deviation", "absdev"), ("dispersion-normalised", "absz")):
        cut = sig[col].quantile(0.9)
        b = sig[sig[col] >= cut]
        net = (b.gross - LARGE_RT).values
        t_nw, _ = nw_t(by_date(b.assign(net=b.gross - LARGE_RT)), h)
        cmp_rows.append({"horizon": h, "selector": name, "n": len(net),
                         "n_effective": independent_windows(b, h),
                         "net_pct": float(net.mean() * 100), "t_newey_west": t_nw,
                         "share_profitable": float((net > 0).mean())})
cp = pd.DataFrame(cmp_rows)
cp.to_csv(P / "strategy_selector.csv", index=False)
print("[SELECTOR] top decile chosen by raw gap against gap-over-dispersion")
print(cp.round(3).to_string(index=False))

_imp = {}
for h in (7, 30, 91):
    a = float(cp[(cp.horizon == h) & (cp.selector == "raw deviation")].net_pct.iloc[0])
    bb = float(cp[(cp.horizon == h) & (cp.selector == "dispersion-normalised")].net_pct.iloc[0])
    _imp[h] = bb - a
SEL = {"rows": cp.to_dict("records"), "improvement_pp": _imp,
       "better_at_all_horizons": bool(all(v > 0 for v in _imp.values()))}
print(f"\n[SELECTOR] normalising improves the net by "
      + ", ".join(f"{k}d {v:+.2f}pp" for k, v in _imp.items()))
print(f"[SELECTOR] better at every horizon: {SEL['better_at_all_horizons']}")
RES["selector"] = SEL

out = json.load(open(P / "fundamentals_results.json"))
out["strategy"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("[SELECTOR] written: strategy_selector")

# ============================================================ 10. is the regime effect just time
# Dispersion fell over the sample, so "low dispersion" and "late in the sample" are confounded.
# If the tercile result is really a time trend, then the finding is "the trade got better" and
# calling it a regime effect is dressing up a drift. The test: run the same tercile split inside
# the training period alone, where the holdout cannot contribute, and then inside the holdout
# alone. A genuine regime effect appears in both.
print("\n" + "=" * 78)
conf = []
for label, frame in (("train only", d2[d2.date <= split]), ("holdout only", d2[d2.date > split])):
    for h in (7, 30):
        sig = frame.dropna(subset=[f"fwd{h}", "dev_lag", "disp"]).copy()
        if len(sig) < 400:
            continue
        sig["gross"] = -np.sign(sig.dev_lag) * sig[f"fwd{h}"]
        cutoff = sig.loc[sig.absdev > THR, "absdev"].quantile(0.9)
        b = sig[sig.absdev >= cutoff].copy()
        if len(b) < 60:
            continue
        # Terciles computed WITHIN the period, so the split is about relative calm, not level.
        b["disp_q"] = pd.qcut(b.disp, 3, labels=["low", "mid", "high"], duplicates="drop")
        for q, gq in b.groupby("disp_q", observed=True):
            net = (gq.gross - LARGE_RT).values
            if len(net) < 20:
                continue
            t_nw, _ = nw_t(by_date(gq.assign(net=gq.gross - LARGE_RT)), h)
            conf.append({"period": label, "horizon": h, "dispersion": str(q),
                         "mean_disp_pct": float(gq.disp.mean() * 100), "n": len(net),
                         "net_pct": float(net.mean() * 100), "t_newey_west": t_nw})
cf = pd.DataFrame(conf)
cf.to_csv(P / "strategy_regime_within.csv", index=False)
print("[CONFOUND] the same tercile split, run inside each period separately")
print(cf.round(3).to_string(index=False))

def _slope(sub):
    """Does net fall as dispersion rises, within this period and horizon?"""
    o = sub.sort_values("mean_disp_pct")
    return float(o.net_pct.iloc[0] - o.net_pct.iloc[-1])       # low minus high

gaps = {}
for (per, h), sub in cf.groupby(["period", "horizon"]):
    if len(sub) >= 2:
        gaps[f"{per} {h}d"] = _slope(sub)
CONF = {"rows": cf.to_dict("records"), "low_minus_high_pp": gaps,
        "holds_in_both_periods": bool(gaps and all(v > 0 for v in gaps.values()))}
print(f"\n[CONFOUND] low-minus-high dispersion payoff, by period and horizon:")
for k, v in gaps.items():
    print(f"    {k:<18} {v:+.2f}pp")
print(f"[CONFOUND] the calm-pays-more pattern holds inside both periods: "
      f"{CONF['holds_in_both_periods']}")
RES["regime_confound"] = CONF

out = json.load(open(P / "fundamentals_results.json"))
out["strategy"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("[CONFOUND] written: strategy_regime_within")
