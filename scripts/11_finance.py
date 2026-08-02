"""Financial-economics analyses: microstructure decomposition, efficiency tests, volatility,
variance decomposition, price discovery, forecast evaluation and specification diagnostics.

Each block exists to connect a theoretical construct to something measurable in this panel.
"""
import json, pathlib, sys, warnings
import numpy as np
from scipy.stats import spearmanr
import pandas as pd
from scipy import stats
from statsmodels.regression.quantile_regression import QuantReg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from econ import ols, absorb

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = np.random.default_rng(20260730)

R = json.load(open(P / "results.json"))
conv = pd.read_csv(P / "converged_panel.csv", parse_dates=["date"]).sort_values(["world", "date"])
idx = pd.read_csv(P / "market_index.csv", parse_dates=["date"])
bd = pd.read_csv(P / "order_books.csv")
bt = pd.read_csv(P / "forecast_backtest.csv", parse_dates=["origin"])
FIN = {}

# ============================================================ 1. Roll effective spread
# Roll (1984): with a constant effective spread s and no information asymmetry, transaction
# prices bounce between bid and ask, so successive returns carry a negative autocovariance of
# exactly -(s/2)^2. Inverting gives s = 2*sqrt(-gamma1). Section 15.2 already documented that
# autocovariance as "measurement noise"; Roll's model says it is not noise in the measurement
# but a structural consequence of trading against a spread.
roll = []
for w, g in conv.groupby("world"):
    r = g.sort_values("date")["ret"].dropna().values
    if len(r) < 200:
        continue
    g1 = float(np.cov(r[1:], r[:-1])[0, 1])
    roll.append({"world": w, "gamma1": g1, "n": len(r),
                 "roll_spread_pct": 2 * np.sqrt(-g1) * 100 if g1 < 0 else np.nan,
                 "ac1": float(np.corrcoef(r[1:], r[:-1])[0, 1])})
roll = pd.DataFrame(roll)
roll.to_csv(P / "roll_spread.csv", index=False)
bdm = bd.merge(roll, on="world", how="inner")
FIN["roll"] = {
    "n_worlds": int(len(roll)),
    "n_negative_gamma1": int((roll.gamma1 < 0).sum()),
    "median_roll_spread_pct": float(roll.roll_spread_pct.median()),
    "iqr": [float(roll.roll_spread_pct.quantile(.25)), float(roll.roll_spread_pct.quantile(.75))],
    "median_quoted_spread_pct": float(bd.quoted_spread_pct.median()),
    "median_executed_gap_pct": float(conv.executed_gap_pct.median()),
    "corr_roll_vs_quoted": float(bdm[["roll_spread_pct", "quoted_spread_pct"]]
                                 .corr(method="spearman").iloc[0, 1]),
    # Report the test, not just the coefficient: a rank correlation this small on this many
    # worlds is indistinguishable from no relationship, and the text should say so.
    "corr_roll_vs_quoted_p": float(spearmanr(
        *bdm[["roll_spread_pct", "quoted_spread_pct"]].dropna().values.T).pvalue),
    "corr_roll_vs_quoted_n": int(bdm[["roll_spread_pct", "quoted_spread_pct"]]
                                 .dropna().shape[0]),
    "share_of_quoted": float(roll.roll_spread_pct.median() / bd.quoted_spread_pct.median()),
}
print(f"[ROLL] implied effective spread {FIN['roll']['median_roll_spread_pct']:.2f}% vs quoted "
      f"{FIN['roll']['median_quoted_spread_pct']:.2f}% "
      f"({FIN['roll']['share_of_quoted']:.0%} of quoted); "
      f"negative autocovariance on {FIN['roll']['n_negative_gamma1']}/{len(roll)} worlds")

# ============================================================ 2. Variance decomposition
# How much of a world's return variance is the common factor and how much is local? Estimated
# with a leave-one-out market return so a world is never regressed on itself.
rp = conv.pivot_table(index="date", columns="world", values="ret")
rp = rp.loc[rp.notna().sum(axis=1) >= 10]
vd = []
for w in rp.columns:
    y = rp[w]
    mkt = rp.drop(columns=[w]).mean(axis=1)
    ok = y.notna() & mkt.notna()
    if ok.sum() < 200:
        continue
    b, a = np.polyfit(mkt[ok], y[ok], 1)
    r2 = float(np.corrcoef(mkt[ok], y[ok])[0, 1] ** 2)
    resid = y[ok] - (a + b * mkt[ok])
    vd.append({"world": w, "beta": float(b), "r2_systematic": r2,
               "idio_sd_pct": float(resid.std() * 100),
               "total_sd_pct": float(y[ok].std() * 100), "n": int(ok.sum())})
vd = pd.DataFrame(vd)
vd.to_csv(P / "variance_decomposition.csv", index=False)

X = rp.dropna(thresh=int(0.8 * rp.shape[1])).ffill(limit=2).dropna(axis=1)
Xc = (X - X.mean()) / X.std()
Xc = Xc.dropna(axis=1)
ev = np.linalg.eigvalsh(np.cov(Xc.values.T))[::-1]
FIN["variance"] = {
    "n_worlds": int(len(vd)),
    "median_r2_systematic": float(vd.r2_systematic.median()),
    "mean_r2_systematic": float(vd.r2_systematic.mean()),
    "median_beta": float(vd.beta.median()),
    "median_idio_sd_pct": float(vd.idio_sd_pct.median()),
    "median_total_sd_pct": float(vd.total_sd_pct.median()),
    "pc1_share": float(ev[0] / ev.sum()), "pc2_share": float(ev[1] / ev.sum()),
    "pc3_share": float(ev[2] / ev.sum()),
    "n_pca_worlds": int(Xc.shape[1]), "n_pca_dates": int(Xc.shape[0]),
}
print(f"[VARIANCE] systematic share median R2={FIN['variance']['median_r2_systematic']:.3f}; "
      f"PC1 explains {FIN['variance']['pc1_share']:.1%} of return variance")

# ============================================================ 3. Weak-form efficiency
# Lo-MacKinlay variance ratio with the heteroskedasticity-robust statistic. Under a random
# walk VR(q) = 1 for all q; VR < 1 indicates mean reversion at that horizon.
def variance_ratio(r, q):
    r = np.asarray(r, float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < q * 10:
        return np.nan, np.nan
    mu = r.mean()
    va = ((r - mu) ** 2).sum() / (n - 1)
    rq = np.convolve(r, np.ones(q), "valid")
    m = q * (n - q + 1) * (1 - q / n)
    vq = ((rq - q * mu) ** 2).sum() / m
    vr = vq / va
    # heteroskedasticity-consistent asymptotic variance (Lo & MacKinlay 1988, theorem 4)
    d = 0.0
    for j in range(1, q):
        # delta_j = sum_t (r_t-mu)^2 (r_{t-j}-mu)^2 / [sum_t (r_t-mu)^2]^2 ; the denominator
        # is NOT divided by n - doing so inflates the variance by a factor of n and makes the
        # test unable to reject anything.
        num = ((r[j:] - mu) ** 2 * (r[:-j] - mu) ** 2).sum()
        den = (((r - mu) ** 2).sum()) ** 2
        d += (2 * (q - j) / q) ** 2 * (num / den)
    z = (vr - 1) / np.sqrt(d) if d > 0 else np.nan
    return float(vr), float(z)


vr_rows = []
for w, g in conv.groupby("world"):
    r = g.sort_values("date")["ret"].dropna().values
    if len(r) < 300:
        continue
    rec = {"world": w, "n": len(r)}
    for q in (2, 5, 10, 20):
        vr, z = variance_ratio(r, q)
        rec[f"vr{q}"], rec[f"z{q}"] = vr, z
    vr_rows.append(rec)
vrdf = pd.DataFrame(vr_rows)
vrdf.to_csv(P / "variance_ratio.csv", index=False)
FIN["efficiency"] = {"n_worlds": int(len(vrdf))}
for q in (2, 5, 10, 20):
    FIN["efficiency"][f"vr{q}_median"] = float(vrdf[f"vr{q}"].median())
    FIN["efficiency"][f"vr{q}_reject_5pct"] = int((vrdf[f"z{q}"].abs() > 1.96).sum())
# index-level test
ridx = np.diff(np.log(idx.ew_price.dropna().values))
FIN["efficiency"]["index"] = {f"vr{q}": variance_ratio(ridx, q) for q in (2, 5, 10, 20)}
print(f"[EFFICIENCY] median VR(2)={FIN['efficiency']['vr2_median']:.3f}, "
      f"VR(20)={FIN['efficiency']['vr20_median']:.3f}; rejects at q=2 on "
      f"{FIN['efficiency']['vr2_reject_5pct']}/{len(vrdf)} worlds")

# ============================================================ 4. GARCH(1,1)
from arch import arch_model
gar = []
for w, g in conv.groupby("world"):
    r = g.sort_values("date")["ret"].dropna().values * 100
    if len(r) < 400:
        continue
    try:
        res = arch_model(r, vol="GARCH", p=1, q=1, mean="Constant", dist="t").fit(disp="off")
        a, b = float(res.params["alpha[1]"]), float(res.params["beta[1]"])
        gar.append({"world": w, "alpha": a, "beta": b, "persistence": a + b,
                    "nu": float(res.params.get("nu", np.nan)),
                    "half_life": float(np.log(0.5) / np.log(a + b)) if 0 < a + b < 1 else np.nan,
                    "aic": float(res.aic), "n": len(r)})
    except Exception:
        pass
gar = pd.DataFrame(gar)
gar.to_csv(P / "garch.csv", index=False)
FIN["garch"] = {
    "n_worlds": int(len(gar)),
    "median_alpha": float(gar.alpha.median()), "median_beta": float(gar.beta.median()),
    "median_persistence": float(gar.persistence.median()),
    "share_persistence_above_0.9": float((gar.persistence > 0.9).mean()),
    "median_vol_half_life_days": float(gar.half_life.median()),
    "median_nu": float(gar.nu.median()),
}
print(f"[GARCH] median persistence a+b={FIN['garch']['median_persistence']:.3f}, "
      f"vol half-life {FIN['garch']['median_vol_half_life_days']:.1f}d, "
      f"median t d.o.f. {FIN['garch']['median_nu']:.1f}")

# ============================================================ 5. Quantile regression
# Is adjustment to the cross-world gap symmetric, or concentrated in large moves? Estimated
# on world-demeaned data so the fixed effects are absorbed.
q_in = conv.dropna(subset=["ret", "dev_lag"]).copy()
Z = absorb(q_in, ["ret", "dev_lag"], ["world"])
qr_rows = []
for tau in (0.10, 0.25, 0.50, 0.75, 0.90):
    m = QuantReg(Z["ret"].values, np.column_stack([np.ones(len(Z)), Z["dev_lag"].values])).fit(q=tau)
    qr_rows.append({"tau": tau, "coef": float(m.params[1]), "se": float(m.bse[1]),
                    "t": float(m.tvalues[1])})
qr = pd.DataFrame(qr_rows)
qr.to_csv(P / "quantile_regression.csv", index=False)
FIN["quantile"] = qr.to_dict("records")
print("[QUANTILE] dev_lag coefficient by quantile: "
      + ", ".join(f"t={r.tau:.2f}:{r.coef:+.3f}" for r in qr.itertuples()))

# ============================================================ 6. Price discovery / lead-lag
# Do large worlds lead small ones? If price discovery happens where trading is deepest, the
# lagged return of the large-world group should predict the small-world group and not vice
# versa. Tested as a bivariate Granger causality on the two group indices.
med = conv.groupby("world").txn_sold.median()
big_w = med[med >= med.median()].index
small_w = med[med < med.median()].index
gi = pd.DataFrame({
    "big": conv[conv.world.isin(big_w)].groupby("date")["ret"].mean(),
    "small": conv[conv.world.isin(small_w)].groupby("date")["ret"].mean()}).dropna()


def granger(y, x, lags=3):
    df = pd.DataFrame({"y": y, "x": x})
    for L in range(1, lags + 1):
        df[f"yl{L}"] = df.y.shift(L)
        df[f"xl{L}"] = df.x.shift(L)
    df = df.dropna()
    yv = df.y.values
    Xr = np.column_stack([np.ones(len(df))] + [df[f"yl{L}"].values for L in range(1, lags + 1)])
    Xu = np.column_stack([Xr] + [df[f"xl{L}"].values for L in range(1, lags + 1)])
    def ssr(X):
        b = np.linalg.lstsq(X, yv, rcond=None)[0]
        e = yv - X @ b
        return float(e @ e)
    s_r, s_u = ssr(Xr), ssr(Xu)
    n, k = len(df), Xu.shape[1]
    F = ((s_r - s_u) / lags) / (s_u / (n - k))
    return float(F), float(stats.f.sf(F, lags, n - k)), n


f_bs, p_bs, n_g = granger(gi.small.values, gi.big.values)
f_sb, p_sb, _ = granger(gi.big.values, gi.small.values)
FIN["price_discovery"] = {
    "n_obs": n_g, "n_big": int(len(big_w)), "n_small": int(len(small_w)),
    "big_causes_small_F": f_bs, "big_causes_small_p": p_bs,
    "small_causes_big_F": f_sb, "small_causes_big_p": p_sb,
    "contemp_corr": float(gi.big.corr(gi.small)),
}
print(f"[DISCOVERY] large->small F={f_bs:.2f} (p={p_bs:.3g}); "
      f"small->large F={f_sb:.2f} (p={p_sb:.3g})")

# ============================================================ 7. Diebold-Mariano
dm = {}
for h in bt.h.unique():
    d0 = bt[bt.h == h]
    e_m = (np.log(d0.model / d0.actual)) ** 2
    e_r = (np.log(d0.rw / d0.actual)) ** 2
    dd = (e_m - e_r).values
    dd = dd[np.isfinite(dd)]
    mu = dd.mean()
    L = max(1, int(len(dd) ** (1 / 3)))
    g0 = np.var(dd, ddof=1)
    s = g0
    for k in range(1, L + 1):
        c = np.cov(dd[k:], dd[:-k])[0, 1]
        s += 2 * (1 - k / (L + 1)) * c
    se = np.sqrt(max(s, 1e-18) / len(dd))
    dm[h] = {"dm_stat": float(mu / se), "p": float(2 * stats.norm.sf(abs(mu / se))),
             "mean_loss_diff": float(mu), "n": int(len(dd))}
FIN["diebold_mariano"] = dm
print("[DM] " + "; ".join(f"{k}: DM={v['dm_stat']:+.2f} p={v['p']:.2f}" for k, v in dm.items()))

# ============================================================ 8. Alternative covariance
# Driscoll-Kraay standard errors are robust to cross-sectional dependence of unknown form,
# which is precisely what arbitrage induces here.
pan = conv.dropna(subset=["ret", "dev_lag"]).copy()
Zp = absorb(pan, ["ret", "dev_lag"], ["world"])
xv = Zp["dev_lag"].values[:, None]
yv = Zp["ret"].values
b = np.linalg.lstsq(xv, yv, rcond=None)[0]
res = yv - xv @ b
mom = pd.DataFrame({"d": pan["date"].values, "h": (xv[:, 0] * res)}).groupby("d")["h"].sum()
T = len(mom)
Lag = int(np.floor(4 * (T / 100) ** (2 / 9)))
g0 = float((mom ** 2).sum())
S = g0
for k in range(1, Lag + 1):
    c = float((mom.values[k:] * mom.values[:-k]).sum())
    S += 2 * (1 - k / (Lag + 1)) * c
XtXi = 1.0 / float(xv[:, 0] @ xv[:, 0])
se_dk = float(np.sqrt(XtXi * S * XtXi))
cc = R["panel"]["clustering_comparison"]
FIN["driscoll_kraay"] = {
    "coef": float(b[0]), "se": se_dk, "t": float(b[0] / se_dk),
    "lag": Lag, "n": int(len(yv)), "n_dates": T,
    "vs_twoway_se": cc["two-way"]["se"], "vs_naive_se": cc["none"]["se"],
}
print(f"[DK] dev_lag {b[0]:+.4f}, Driscoll-Kraay SE {se_dk:.4f} "
      f"(two-way {cc['two-way']['se']:.4f}, naive {cc['none']['se']:.4f})")

# ============================================================ 9. Diagnostics
bw = pd.read_csv(P / "world_summary.csv")
xw = bw[bw.converged].copy()
xw["optional_pvp"] = (xw.pvp_type == "Optional PvP").astype(float)
xw["be_release"] = (xw.battleye_date.astype(str) == "release").astype(float)
xw["log_pop"] = np.log(xw.population)
xw["log_act"] = np.log(xw.activity_year)
xw["log_eng"] = np.log(xw.activity_year / xw.population)
cols = ["optional_pvp", "be_release", "log_pop", "log_act"]
D = xw[cols].dropna()
vif = {}
for c in cols:
    others = [z for z in cols if z != c]
    A = np.column_stack([np.ones(len(D))] + [D[z].values for z in others])
    bb = np.linalg.lstsq(A, D[c].values, rcond=None)[0]
    e = D[c].values - A @ bb
    r2 = 1 - (e @ e) / ((D[c].values - D[c].values.mean()) ** 2).sum()
    vif[c] = float(1 / max(1 - r2, 1e-9))
resid_panel = res
lb_p = float(stats.chi2.sf(
    len(resid_panel) * sum(np.corrcoef(resid_panel[k:], resid_panel[:-k])[0, 1] ** 2
                           for k in range(1, 11)), 10))
bp_x = np.column_stack([np.ones(len(xv)), xv[:, 0]])
bpb = np.linalg.lstsq(bp_x, resid_panel ** 2, rcond=None)[0]
bp_fit = bp_x @ bpb
bp_r2 = 1 - ((resid_panel ** 2 - bp_fit) ** 2).sum() / (
    (resid_panel ** 2 - (resid_panel ** 2).mean()) ** 2).sum()
FIN["diagnostics"] = {
    "vif": vif, "max_vif": float(max(vif.values())),
    "ljung_box_resid_p": lb_p,
    "breusch_pagan_LM": float(len(resid_panel) * bp_r2),
    "breusch_pagan_p": float(stats.chi2.sf(len(resid_panel) * bp_r2, 1)),
    "resid_skew": float(stats.skew(resid_panel)),
    "resid_excess_kurtosis": float(stats.kurtosis(resid_panel)),
}
print(f"[DIAG] max VIF {FIN['diagnostics']['max_vif']:.2f}; "
      f"Breusch-Pagan p={FIN['diagnostics']['breusch_pagan_p']:.3g}; "
      f"residual excess kurtosis {FIN['diagnostics']['resid_excess_kurtosis']:.1f}")

# ============================================================ 10. Structural break
# Andrews supremum-Wald test for an unknown break in the mean daily return of the index.
ri = pd.Series(ridx)
n = len(ri)
lo_i, hi_i = int(0.15 * n), int(0.85 * n)
waldmax, kmax = -np.inf, None
for k in range(lo_i, hi_i):
    a, bq = ri.values[:k], ri.values[k:]
    if len(a) < 30 or len(bq) < 30:
        continue
    t = (a.mean() - bq.mean()) / np.sqrt(a.var(ddof=1) / len(a) + bq.var(ddof=1) / len(bq))
    if t ** 2 > waldmax:
        waldmax, kmax = t ** 2, k
bdates = idx.loc[idx.ew_price.notna(), "date"].values[1:]
FIN["structural_break"] = {
    "sup_wald": float(waldmax),
    "crit_95_andrews": 8.85,           # Andrews (1993), 1 parameter, 15% trimming
    "break_detected": bool(waldmax > 8.85),
    "break_date": str(pd.Timestamp(bdates[kmax]).date()) if kmax is not None else None,
    "n": int(n),
}
print(f"[BREAK] sup-Wald {waldmax:.2f} vs 8.85 -> "
      f"{'break at ' + str(FIN['structural_break']['break_date']) if FIN['structural_break']['break_detected'] else 'no break in drift'}")

R["finance"] = FIN
json.dump(R, open(P / "results.json", "w"), indent=1, default=str)
print("\nwritten to results.json under 'finance'")
