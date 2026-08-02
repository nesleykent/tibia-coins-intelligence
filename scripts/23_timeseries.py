"""The time-series model classes the study had not tested.

Four gaps, each a distinct hypothesis about why the price might be forecastable.

SARIMAX asks whether seasonality plus exogenous fundamentals help a classical model - it is the
direct test of "ARIMA with the economy attached", and it separates the contribution of the
seasonal terms from the contribution of the regressors by fitting both with and without them.

Markov-switching autoregression asks whether the dynamics themselves change. 19_regimes.py
detects states but does not forecast with them; this fits an autoregression whose coefficients
switch between regimes and forecasts through the estimated transition matrix.

A latent factor model asks whether the 93 worlds are driven by a small number of common shocks
that a per-world model cannot see. Factors are extracted from the returns panel by principal
components on the training window only, then used as predictors.

GARCH is fitted in Section 7.1 as a description. Here it forecasts, so that the machine-learning
volatility result has a proper benchmark rather than only the unconditional mean.

    python scripts/23_timeseries.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
from arch import arch_model
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from statsmodels.tsa.regime_switching.markov_autoregression import MarkovAutoregression
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = 12345
H = 7

d = pd.read_csv(P / "fundamentals_panel.csv", parse_dates=["date"])
meta = json.load(open(P / "fundamentals_meta.json"))
FEATS = [c for c in meta["features"] if c in d.columns]
d = d[d.converged].sort_values(["date", "world"]).reset_index(drop=True)
_new = {}
print(f"panel: {len(d):,} world-days, {d.world.nunique()} worlds")

# Exogenous regressors for the classical models: a small, economically named set rather than all
# 140, because a state-space model with 140 regressors on 160 training days cannot be estimated.
EXOG = [c for c in ["log_monsters_killed", "log_players_online_avg", "g7_monsters_killed",
                    "idx_activity", "rel_premium", "turnover_7", "ev_any"] if c in d.columns]
print(f"exogenous set for the classical models: {EXOG}")


def dm(e1, e2, h=H):
    dd = (e1 ** 2 - e2 ** 2)
    dd = dd[np.isfinite(dd)]
    if len(dd) < 20:
        return np.nan
    lags = max(1, h - 1)
    s = dd.var(ddof=0) + 2 * sum((1 - k / (lags + 1)) * np.cov(dd[k:], dd[:-k], ddof=0)[0, 1]
                                 for k in range(1, lags + 1))
    return float(dd.mean() / np.sqrt(s / len(dd))) if s > 0 else np.nan


# ============================================================ 1. per-world classical models
fails = {}
rows = []
for w, g in d.groupby("world"):
    g = g.sort_values("date").reset_index(drop=True)
    g = g.dropna(subset=["logp"])
    if len(g) < 160:
        continue
    cut = int(len(g) * 0.7)
    tr, te = g.iloc[:cut], g.iloc[cut:]
    if len(te) < 25:
        continue
    y_true = (te.logp.shift(-H) - te.logp).dropna()
    if len(y_true) < 20:
        continue
    idx = y_true.index
    out = {"RandomWalk": np.zeros(len(idx))}

    ex_tr = tr[EXOG].ffill().bfill().fillna(0).values
    ex_te = te[EXOG].ffill().bfill().fillna(0).values

    def fc(model_kw, use_exog):
        """Fit on the training window, then forecast H ahead from each test point."""
        m = SARIMAX(tr.logp.values, exog=ex_tr if use_exog else None,
                    **model_kw).fit(disp=0, maxiter=80)
        preds = []
        for i in range(len(te)):
            hist = np.concatenate([tr.logp.values, te.logp.values[:i]])
            ex_h = (np.vstack([ex_tr, ex_te[:i]]) if use_exog else None)
            r = m.apply(hist, exog=ex_h, refit=False)
            f = r.forecast(steps=H, exog=(np.repeat(ex_te[i:i + 1], H, axis=0)
                                          if use_exog else None))
            preds.append(f[-1] - hist[-1])
        return np.array(preds)[:len(idx)]

    for label, kw, ux in (
            ("SARIMA", dict(order=(1, 1, 1), seasonal_order=(1, 0, 1, 7)), False),
            ("SARIMAX", dict(order=(1, 1, 1), seasonal_order=(1, 0, 1, 7)), True)):
        try:
            out[label] = fc(kw, ux)
        except Exception:
            pass

    # Markov-switching autoregression on returns: two regimes, switching mean and variance.
    try:
        ms = MarkovAutoregression(tr.ret.dropna().values, k_regimes=2, order=1,
                                  switching_ar=False, switching_variance=True).fit()
        names = list(ms.model.param_names)
        const_ix = [i for i, n in enumerate(names) if n.startswith("const")]
        mu = np.asarray(ms.params)[const_ix]
        pi_now = np.asarray(ms.smoothed_marginal_probabilities)[-1]
        pi_next = pi_now @ ms.regime_transition[:, :, 0].T
        out["MarkovSwitch"] = np.full(len(idx), float(H * (pi_next @ mu)))
        assert abs(out["MarkovSwitch"][0]) < 1.0, "implausible regime-switching forecast"
    except Exception as e:
        fails["MarkovSwitch"] = fails.get("MarkovSwitch", 0) + 1

    yt = y_true.values
    e_rw = out["RandomWalk"] - yt
    for name, yh in out.items():
        yh = np.asarray(yh)[:len(yt)]
        e = yh - yt
        rows.append({"world": w, "model": name, "n_test": len(yt),
                     "rmse": float(np.sqrt(np.mean(e ** 2))),
                     "r2_oos": float(1 - np.sum(e ** 2) / np.sum(yt ** 2)),
                     "dm_t_vs_rw": dm(e_rw, e) if name != "RandomWalk" else np.nan})
if fails:
    print(f"[CLASSICAL] fits that failed, by model: {fails}")
cls = pd.DataFrame(rows)
cls.to_csv(P / "classical_models.csv", index=False)
cs = (cls.groupby("model").agg(rmse=("rmse", "mean"), r2_median=("r2_oos", "median"),
                               worlds=("world", "nunique"),
                               worlds_better=("dm_t_vs_rw", lambda s: int((s > 0).sum())))
        .reset_index().sort_values("rmse"))
cs.to_csv(P / "classical_summary.csv", index=False)
print("\n[CLASSICAL]"); print(cs.to_string(index=False))

# ============================================================ 2. latent cross-world factors
# Common shocks the worlds share. Components are estimated on the training window only and then
# applied forward, so the factor construction cannot see the test period.
wide = d.pivot_table(index="date", columns="world", values="ret").sort_index()
wide = wide.dropna(axis=1, thresh=int(len(wide) * 0.8)).fillna(0.0)
dates = wide.index.values
cut = int(len(dates) * 0.7)
Z = (wide - wide.iloc[:cut].mean()) / wide.iloc[:cut].std().replace(0, np.nan)
Z = Z.fillna(0.0)
_, sv, Vt = np.linalg.svd(Z.iloc[:cut].values, full_matrices=False)
K = 5
fac = pd.DataFrame(Z.values @ Vt[:K].T, index=wide.index,
                   columns=[f"factor{i + 1}" for i in range(K)])
var_share = (sv ** 2 / (sv ** 2).sum())[:K]
fac.to_csv(P / "latent_factors.csv")
print(f"\n[FACTORS] {K} components explain "
      f"{', '.join(f'{v:.1%}' for v in var_share)} of training-window return variance "
      f"({var_share.sum():.1%} together)")

fd = d.merge(fac.shift(1).reset_index(), on="date", how="left")
FCOLS = list(fac.columns)
tgt = f"y_rel{H}"
sub = fd[FEATS + FCOLS + [tgt, "date"]].dropna(subset=[tgt])
cutd = dates[cut]
tr, te = sub[sub.date < cutd].copy(), sub[sub.date >= cutd].copy()
med = tr[FEATS + FCOLS].median()
tr[FEATS + FCOLS], te[FEATS + FCOLS] = (tr[FEATS + FCOLS].fillna(med),
                                        te[FEATS + FCOLS].fillna(med))


def rf():
    return RandomForestRegressor(n_estimators=250, min_samples_leaf=40, max_features=0.4,
                                 random_state=RNG, n_jobs=-1)


yt = te[tgt].values
r2 = {}
for label, cols in (("without factors", FEATS), ("with factors", FEATS + FCOLS)):
    m = rf().fit(tr[cols].values, tr[tgt].values)
    e = m.predict(te[cols].values) - yt
    r2[label] = float(1 - np.sum(e ** 2) / np.sum(yt ** 2))
print(f"[FACTORS] out-of-sample R² {r2['without factors']:+.4f} without, "
      f"{r2['with factors']:+.4f} with")

# ============================================================ 3. GARCH as a volatility benchmark
# Section 7.1 fits GARCH descriptively. Here it forecasts, so the machine-learning volatility
# result of Section 6.6.5 is measured against the standard tool rather than against a mean.
grows, gfails = [], 0
for w, g in d.groupby("world"):
    g = g.sort_values("date").dropna(subset=["ret", "y_vol7"])
    if len(g) < 160:
        continue
    c = int(len(g) * 0.7)
    tr_r, te_g = g.ret.values[:c] * 100, g.iloc[c:]
    try:
        am = arch_model(tr_r, vol="GARCH", p=1, q=1, dist="t").fit(disp="off")
        f = am.forecast(horizon=H, reindex=False)
        sig = np.sqrt(f.variance.values[-1].mean()) / 100 * np.sqrt(365)
    except Exception:
        gfails += 1
        continue
    yv = te_g.y_vol7.values
    base = g.y_vol7.values[:c].mean()
    grows.append({"world": w, "garch_rmse": float(np.sqrt(np.mean((sig - yv) ** 2))),
                  "mean_rmse": float(np.sqrt(np.mean((base - yv) ** 2))),
                  "n": len(yv)})
if gfails:
    print(f"[GARCH] {gfails} worlds failed to fit")
gv = pd.DataFrame(grows)
gv.to_csv(P / "garch_volatility_forecast.csv", index=False)
if len(gv):
    print(f"\n[GARCH] volatility forecast RMSE {gv.garch_rmse.mean():.4f} against "
          f"{gv.mean_rmse.mean():.4f} for the training mean, over {len(gv)} worlds; "
          f"GARCH better on {int((gv.garch_rmse < gv.mean_rmse).sum())}")

_new["classical_models"] = {
    "summary": cs.to_dict("records"), "exog": EXOG, "horizon": H,
    "n_worlds": int(cls.world.nunique())}
_new["latent_factors"] = {
    "k": K, "variance_share": [float(v) for v in var_share],
    "cumulative_share": float(var_share.sum()),
    "r2_without": r2["without factors"], "r2_with": r2["with factors"]}
if len(gv):
    _new["garch_forecast"] = {
        "garch_rmse": float(gv.garch_rmse.mean()), "mean_rmse": float(gv.mean_rmse.mean()),
        "n_worlds": int(len(gv)),
        "n_garch_better": int((gv.garch_rmse < gv.mean_rmse).sum())}
# Re-read here, not at import: a long stage must not overwrite work that
# finished while it was running.
RES = json.load(open(P / "fundamentals_results.json"))
RES |= _new
json.dump(RES, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[TIMESERIES] written: classical_summary, latent_factors, garch_volatility_forecast")
