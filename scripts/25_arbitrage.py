"""Attack the structure the report says exists, on its own terms.

The objection this answers is a fair one. Section 6.3.1 finds a threshold at 1.79% with
reversion outside it, and Section 5.2 calls relative pricing predictable - yet Section 6.6
predicts a pooled relative return with 140 features and reports an R-squared of 0.047. If the
structure is real, the forecasting exercise was aimed at the wrong quantity.

So this stage aims at the right one. The target is the deviation itself, defined exactly as
10_advanced.py defines it, over the full price history rather than the eight-month window the
kill statistics allow. It is modelled separately inside and outside the band, because the whole
content of a threshold model is that the two regimes differ. It is modelled pairwise as well as
against the mean, because arbitrage happens between two worlds and not against an index. And it
ends with a trading rule evaluated net of the documented fee, because a reversion smaller than
the cost of capturing it is not an opportunity.

    python scripts/25_arbitrage.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = 12345
MIN_XW = 10
H = 7

R = json.load(open(P / "results.json"))
THR = R["advanced"]["tar"]["threshold_pct"] / 100
FEE = R["fees"]["rate_pct"] / 100
CAP_TC = R["fees"]["cap_binds_at_lot_tc"]

pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
bw = pd.read_csv(P / "world_summary.csv")
conv = set(bw.query("converged").world)
d = pan[pan.world.isin(conv)][["world", "date", "price_gp"]].dropna().copy()
d["logp"] = np.log(d.price_gp)

# The deviation exactly as the threshold model defines it: log price less the cross-world mean,
# only on dates carrying enough worlds for that mean to be meaningful.
n_on_date = d.groupby("date").world.transform("size")
d["dev"] = (d.logp - d.groupby("date").logp.transform("mean")).where(n_on_date >= MIN_XW)
d = d.dropna(subset=["dev"]).sort_values(["world", "date"]).reset_index(drop=True)
g = d.groupby("world", observed=True)
d["dev_fwd"] = g.dev.shift(-H) - d.dev                # what the trade would capture
d["dev_lag"] = g.dev.shift(1)                         # what is knowable when the trade is put on
d["absdev"] = d.dev_lag.abs()
d["outside"] = (d.absdev > THR).astype(int)
print(f"deviation panel: {len(d):,} world-days, {d.world.nunique()} worlds, "
      f"{d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d}")
print(f"threshold {THR:.4f} in logs; {d.outside.mean():.1%} of observations lie outside it")

RES = {}

# ============================================================ 1. how much reversion is real
# A one-day autoregression on a noisy series overstates reversion, because measurement error in
# dev(t-1) pushes the coefficient down. The same regression at weekly and fortnightly spacing
# uses the same data with less noise per observation, so the gap between them measures the
# problem rather than assuming it away.
rev = []
for step, label in ((1, "daily"), (7, "weekly"), (14, "fortnightly")):
    s = d.copy()
    s["dev_prev"] = s.groupby("world").dev.shift(step)
    s["dev_next"] = s.groupby("world").dev.shift(-step)
    s = s.dropna(subset=["dev", "dev_prev", "dev_next"])
    x = s.dev.values
    y = s.dev_next.values
    beta = np.polyfit(x, y, 1)[0]
    rev.append({"spacing": label, "step_days": step, "rho": float(beta),
                "implied_weekly_reversion": float(1 - beta ** (7 / step)),
                "n": int(len(s))})
rv = pd.DataFrame(rev)
print("\n[REVERSION] persistence of the deviation at three samplings")
print(rv.to_string(index=False))
RES["reversion_by_spacing"] = rv.to_dict("records")

# ============================================================ 2. band-conditional forecasting
# Pooling the two regimes is what Section 6.6 did, and a threshold model says that is the one
# thing not to do. Each regime is fitted and scored separately, out of sample.
d["mom5"] = d.logp - g.logp.shift(5)
d["vol14"] = g.logp.diff().rolling(14).std().reset_index(level=0, drop=True)
d["dev_chg5"] = d.dev_lag - g.dev.shift(6)
FEATS = ["dev_lag", "absdev", "mom5", "vol14", "dev_chg5"]
sub = d.dropna(subset=FEATS + ["dev_fwd"]).copy()
dates = np.sort(sub.date.unique())
cut = dates[int(len(dates) * 0.6)]
tr, te = sub[sub.date < cut], sub[sub.date >= cut]
print(f"\ntrain {len(tr):,} to {pd.Timestamp(cut).date()}, test {len(te):,}")


def score(tr_, te_, cols, model="ols"):
    if len(tr_) < 300 or len(te_) < 100:
        return np.nan, np.nan, 0
    if model == "ols":
        X = np.column_stack([np.ones(len(tr_))] + [tr_[c].values for c in cols])
        b = np.linalg.lstsq(X, tr_.dev_fwd.values, rcond=None)[0]
        p = np.column_stack([np.ones(len(te_))] + [te_[c].values for c in cols]) @ b
    else:
        m = RandomForestRegressor(n_estimators=300, min_samples_leaf=50, max_features=0.6,
                                  random_state=RNG, n_jobs=-1).fit(tr_[cols].values,
                                                                   tr_.dev_fwd.values)
        p = m.predict(te_[cols].values)
    y = te_.dev_fwd.values
    r2 = 1 - np.sum((p - y) ** 2) / np.sum(y ** 2)
    da = float(np.mean(np.sign(p) == np.sign(y)))
    return float(r2), da, int(len(te_))


rows = []
for regime, m_tr, m_te in (("pooled", slice(None), slice(None)),
                           ("outside band", tr.outside == 1, te.outside == 1),
                           ("inside band", tr.outside == 0, te.outside == 0)):
    t_, e_ = (tr if isinstance(m_tr, slice) else tr[m_tr],
              te if isinstance(m_te, slice) else te[m_te])
    for mdl in ("ols", "rf"):
        for cols, cname in ((["dev_lag"], "deviation only"), (FEATS, "five features")):
            r2, da, n = score(t_, e_, cols, mdl)
            rows.append({"regime": regime, "model": mdl, "features": cname,
                         "r2_oos": r2, "dir_acc": da, "n_test": n})
band = pd.DataFrame(rows)
band.to_csv(P / "band_conditional.csv", index=False)
print("\n[BAND-CONDITIONAL] out-of-sample R² against predicting no change")
print(band.pivot_table(index=["regime", "features"], columns="model",
                       values="r2_oos").round(4).to_string())
RES["band_conditional"] = band.to_dict("records")

# ============================================================ 3. the world network
# Arbitrage is between two worlds. The pairwise gap is the quantity a trader actually faces, and
# it is not the same object as a deviation from an index.
piv = d.pivot_table(index="date", columns="world", values="logp").sort_index()
piv = piv.dropna(axis=1, thresh=int(len(piv) * 0.7))
cols = list(piv.columns)
print(f"\n[NETWORK] {len(cols)} worlds with continuous history -> "
      f"{len(cols) * (len(cols) - 1) // 2:,} pairs")
pair_rows = []
vals = piv.values
tr_n = int(len(piv) * 0.6)
for i in range(len(cols)):
    for j in range(i + 1, len(cols)):
        gap = vals[:, i] - vals[:, j]
        ok = np.isfinite(gap)
        if ok.sum() < 200:
            continue
        gl = np.roll(gap, 1)
        fwd = np.roll(gap, -H) - gap
        m = ok & np.roll(ok, 1) & np.roll(ok, -H)
        m[:1] = m[-H:] = False
        if m.sum() < 150:
            continue
        idx = np.where(m)[0]
        tr_m, te_m = idx[idx < tr_n], idx[idx >= tr_n]
        if len(tr_m) < 100 or len(te_m) < 50:
            continue
        b = np.polyfit(gl[tr_m], fwd[tr_m], 1)
        p = np.polyval(b, gl[te_m])
        y = fwd[te_m]
        pair_rows.append({"a": cols[i], "b": cols[j], "slope": float(b[0]),
                          "r2_oos": float(1 - np.sum((p - y) ** 2) / np.sum(y ** 2)),
                          "mean_abs_gap": float(np.nanmean(np.abs(gap))),
                          "n_test": int(len(te_m))})
pairs = pd.DataFrame(pair_rows)
pairs.to_csv(P / "pairwise_gaps.csv", index=False)
print(f"[NETWORK] {len(pairs):,} pairs modelled; median out-of-sample R² "
      f"{pairs.r2_oos.median():+.4f}; {(pairs.r2_oos > 0).mean():.1%} positive; "
      f"median convergence slope {pairs.slope.median():+.3f}")
RES["pairwise"] = {"n_pairs": int(len(pairs)),
                   "median_r2": float(pairs.r2_oos.median()),
                   "share_positive": float((pairs.r2_oos > 0).mean()),
                   "median_slope": float(pairs.slope.median()),
                   "best": pairs.nlargest(5, "r2_oos").to_dict("records")}

# ============================================================ 4. is it tradeable
# The decisive question. Enter when the deviation exceeds the band, hold H days, and pay the
# documented round trip. Gross is what the reversion delivers; net is what a trader keeps.
sig = te.dropna(subset=["dev_fwd"]).copy()
sig["side"] = -np.sign(sig.dev_lag)                    # sell the rich world, buy the cheap one
sig["gross"] = sig.side * sig.dev_fwd
trades = sig[sig.absdev > THR]
small_rt, large_rt = 2 * FEE, R["fees"]["roundtrip_largest_decile_pct"] / 100
res = {}
for label, cost in (("small offer", small_rt), ("above the fee cap", large_rt)):
    net = trades.gross - cost
    res[label] = {"n_trades": int(len(trades)),
                  "mean_gross_pct": float(trades.gross.mean() * 100),
                  "cost_pct": float(cost * 100),
                  "mean_net_pct": float(net.mean() * 100),
                  "share_profitable": float((net > 0).mean()),
                  "t_stat": float(stats.ttest_1samp(net, 0).statistic) if len(net) > 30 else np.nan}
print("\n[TRADING] entering only when the deviation exceeds the band")
for k, v in res.items():
    print(f"  {k:>18}: gross {v['mean_gross_pct']:+.3f}%  cost {v['cost_pct']:.2f}%  "
          f"net {v['mean_net_pct']:+.3f}%  profitable on {v['share_profitable']:.1%} "
          f"of {v['n_trades']:,} trades")
RES["trading_rule"] = res
RES["threshold_used_pct"] = float(THR * 100)
RES["share_outside_band"] = float(d.outside.mean())

out = json.load(open(P / "fundamentals_results.json"))
out["arbitrage_structure"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[ARBITRAGE] written: band_conditional, pairwise_gaps")
