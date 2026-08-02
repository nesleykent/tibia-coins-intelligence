"""The models, baselines, targets and validation schemes 18_predict.py left out.

Four additions, each closing a gap rather than adding decoration.

Models: ordinary least squares with no regularisation, CatBoost, and a structural time series.
OLS matters because it shows what the regularisation in Ridge and ElasticNet was buying.

Baselines: ARIMA and Prophet. These are univariate time-series forecasters and belong beside
the random walk rather than beside the fundamentals models - the question they answer is
whether anything in the price's own history was left on the table.

Validation: a rolling window alongside the expanding one. An expanding window keeps every old
observation; a rolling window forgets. If the relationship drifts, the rolling window wins, and
the difference between them is evidence about stability rather than a tuning choice.

Targets: the two volatility questions that were built in 17_features.py and never fitted -
expected realised volatility, and whether the coming week lands in the top quartile.

    python scripts/21_models_extra.py
"""
import json, logging, pathlib, warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import roc_auc_score
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.structural import UnobservedComponents
from catboost import CatBoostRegressor

warnings.filterwarnings("ignore")
logging.getLogger("prophet").setLevel(logging.CRITICAL)
logging.getLogger("cmdstanpy").setLevel(logging.CRITICAL)

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = 12345
FOLDS = 6
HORIZONS = (1, 7, 30)

d = pd.read_csv(P / "fundamentals_panel.csv", parse_dates=["date"])
meta = json.load(open(P / "fundamentals_meta.json"))
FEATS = [c for c in meta["features"] if c in d.columns]
d = d[d.converged].sort_values(["date", "world"]).reset_index(drop=True)
dates = np.sort(d.date.unique())
RES = {}
print(f"panel: {len(d):,} world-days, {d.world.nunique()} worlds, {len(FEATS)} features")


def folds_for(h, scheme):
    """Expanding keeps all history; rolling keeps a fixed window of it."""
    n = len(dates)
    edges = np.linspace(int(n * 0.45), n, FOLDS + 1).astype(int)
    width = edges[0]
    for i in range(FOLDS):
        if edges[i + 1] - edges[i] < 5:
            continue
        end = edges[i] - h
        start = 0 if scheme == "expanding" else max(0, end - width)
        yield dates[start:end], dates[edges[i]:edges[i + 1]]


def dm(e1, e2, h):
    dd = (e1 ** 2 - e2 ** 2)
    dd = dd[np.isfinite(dd)]
    if len(dd) < 30:
        return np.nan
    lags = max(1, h - 1)
    s = dd.var(ddof=0) + 2 * sum(
        (1 - k / (lags + 1)) * np.cov(dd[k:], dd[:-k], ddof=0)[0, 1]
        for k in range(1, lags + 1))
    return float(dd.mean() / np.sqrt(s / len(dd))) if s > 0 else np.nan


def stouffer(z):
    z = pd.Series(z).dropna().values
    if not len(z):
        return np.nan, np.nan
    zc = z.sum() / np.sqrt(len(z))
    return float(zc), float(2 * (1 - stats.norm.cdf(abs(zc))))


# ============================================================ 1. extra models, both schemes
rows = []
for scheme in ("expanding", "rolling"):
    for h in HORIZONS:
        for kind in ("ret", "rel"):
            tgt = f"y_{kind}{h}"
            dh = d[FEATS + [tgt, "date"]].dropna(subset=[tgt])
            for k, (tr_dates, te_dates) in enumerate(folds_for(h, scheme)):
                tr = dh[dh.date.isin(tr_dates)].copy()
                te = dh[dh.date.isin(te_dates)].copy()
                if len(tr) < 500 or len(te) < 50:
                    continue
                med = tr[FEATS].median()
                tr[FEATS], te[FEATS] = tr[FEATS].fillna(med), te[FEATS].fillna(med)
                X, y = tr[FEATS].values, tr[tgt].values
                Xt, yt = te[FEATS].values, te[tgt].values
                mu, sd = X.mean(0), X.std(0) + 1e-9

                fits = {
                    "OLS": LinearRegression().fit((X - mu) / sd, y).predict((Xt - mu) / sd),
                    "CatBoost": CatBoostRegressor(
                        iterations=400, depth=5, learning_rate=0.03, l2_leaf_reg=6,
                        random_seed=RNG, verbose=0, allow_writing_files=False
                    ).fit(X, y).predict(Xt),
                    "RandomForest": RandomForestRegressor(
                        n_estimators=250, min_samples_leaf=40, max_features=0.4,
                        random_state=RNG, n_jobs=-1).fit(X, y).predict(Xt),
                }
                e_rw = -yt
                for name, yh in fits.items():
                    e = yh - yt
                    rows.append({"scheme": scheme, "target": kind, "horizon": h, "fold": k,
                                 "model": name,
                                 "rmse": float(np.sqrt(np.mean(e ** 2))),
                                 "r2_oos": float(1 - np.sum(e ** 2) / np.sum(yt ** 2)),
                                 "dir_acc": float(np.mean(np.sign(yh) == np.sign(yt))),
                                 "dm_t_vs_rw": dm(e_rw, e, h)})
    print(f"[EXTRA] {scheme} window done")

ex = pd.DataFrame(rows)
ex.to_csv(P / "extra_models.csv", index=False)
agg = []
for (sch, tk, h, mdl), g in ex.groupby(["scheme", "target", "horizon", "model"]):
    z, pv = stouffer(g.dm_t_vs_rw)
    agg.append({"scheme": sch, "target": tk, "horizon": h, "model": mdl,
                "r2_oos": g.r2_oos.mean(), "dir_acc": g.dir_acc.mean(),
                "dm_z": z, "dm_p": pv, "folds": len(g),
                "folds_better": int((g.dm_t_vs_rw > 0).sum())})
ex_sum = pd.DataFrame(agg).sort_values(["target", "horizon", "r2_oos"],
                                       ascending=[True, True, False])
ex_sum.to_csv(P / "extra_models_summary.csv", index=False)
print(ex_sum.query("target == 'rel'").to_string(index=False))

# Does forgetting old data help? If the relationship were drifting, rolling would win.
cmp = (ex_sum.pivot_table(index=["target", "horizon", "model"], columns="scheme",
                          values="r2_oos").reset_index())
cmp["rolling_minus_expanding"] = cmp["rolling"] - cmp["expanding"]
cmp.to_csv(P / "window_scheme_comparison.csv", index=False)
ok = cmp[cmp.model != "OLS"]
rf_cmp = cmp[cmp.model == "RandomForest"]
RES["window_scheme"] = {
    "median_rolling_minus_expanding": float(ok.rolling_minus_expanding.median()),
    "n_rolling_better": int((ok.rolling_minus_expanding > 0).sum()),
    "n_compared": int(len(ok)),
    "rf_rolling_better": int((rf_cmp.rolling_minus_expanding > 0).sum()),
    "rf_compared": int(len(rf_cmp)),
    "excluded": "OLS, which diverges and would dominate any average",
    "table": cmp.to_dict("records")}
print(f"\n[WINDOW] excluding OLS, rolling beats expanding in "
      f"{int((ok.rolling_minus_expanding > 0).sum())} of {len(ok)}; "
      f"median difference {ok.rolling_minus_expanding.median():+.4f} R². "
      f"For the best model it is {int((rf_cmp.rolling_minus_expanding > 0).sum())} "
      f"of {len(rf_cmp)}.")

# ============================================================ 2. univariate baselines
# ARIMA, Prophet and a structural time series are fitted per world on its own return history,
# which is the only information they are entitled to. Prophet is slow, so it runs on a fixed
# random sample of worlds and the sample is recorded.
try:
    from prophet import Prophet
    HAVE_PROPHET = True
except Exception:
    HAVE_PROPHET = False

worlds = sorted(d.world.unique())
rs = np.random.RandomState(RNG)
PSAMPLE = sorted(rs.choice(worlds, size=min(12, len(worlds)), replace=False))
uni_rows = []
h = 7
tgt = f"y_ret{h}"
for w in worlds:
    g = d[d.world == w][["date", "logp", "ret", tgt]].dropna(subset=[tgt]).sort_values("date")
    if len(g) < 150:
        continue
    cut = int(len(g) * 0.7)
    tr, te = g.iloc[:cut - h], g.iloc[cut:]
    if len(te) < 20:
        continue
    y = te[tgt].values
    out = {"RandomWalk": np.zeros(len(te))}
    try:
        a = ARIMA(tr.logp.values, order=(1, 1, 1)).fit()
        f = a.forecast(steps=len(te) + h)
        out["ARIMA"] = np.array([f[min(i + h, len(f) - 1)] for i in range(len(te))]) \
            - te.logp.values
    except Exception:
        pass
    try:
        uc = UnobservedComponents(tr.logp.values, level="local linear trend").fit(disp=0)
        f = uc.forecast(steps=len(te) + h)
        out["StructuralTS"] = np.array([f[min(i + h, len(f) - 1)] for i in range(len(te))]) \
            - te.logp.values
    except Exception:
        pass
    if HAVE_PROPHET and w in PSAMPLE:
        try:
            pm = Prophet(daily_seasonality=False, weekly_seasonality=True,
                         yearly_seasonality=False, uncertainty_samples=0)
            pm.fit(pd.DataFrame({"ds": tr.date.values, "y": tr.logp.values}))
            fc = pm.predict(pd.DataFrame({"ds": te.date.values}))
            out["Prophet"] = fc.yhat.values - te.logp.values
        except Exception:
            pass
    e_rw = out["RandomWalk"] - y
    for name, yh in out.items():
        e = yh - y
        uni_rows.append({"world": w, "model": name, "n_test": len(te),
                         "rmse": float(np.sqrt(np.mean(e ** 2))),
                         "r2_oos": float(1 - np.sum(e ** 2) / np.sum(y ** 2)),
                         "dm_t_vs_rw": dm(e_rw, e, h) if name != "RandomWalk" else np.nan})
uni = pd.DataFrame(uni_rows)
uni.to_csv(P / "univariate_baselines.csv", index=False)
us = (uni.groupby("model").agg(rmse=("rmse", "mean"), r2_oos=("r2_oos", "median"),
                               worlds=("world", "nunique"),
                               worlds_better=("dm_t_vs_rw", lambda s: int((s > 0).sum())))
        .reset_index().sort_values("rmse"))
us.to_csv(P / "univariate_summary.csv", index=False)
RES["univariate_baselines"] = {"table": us.to_dict("records"),
                               "prophet_sample": PSAMPLE, "horizon": h}
print("\n" + us.to_string(index=False))

# ============================================================ 3. the volatility targets
vol_rows = []
for target, is_clf in (("y_vol7", False), ("y_hivol7", True)):
    dh = d[FEATS + [target, "date"]].dropna(subset=[target])
    for k, (tr_dates, te_dates) in enumerate(folds_for(7, "expanding")):
        tr = dh[dh.date.isin(tr_dates)].copy()
        te = dh[dh.date.isin(te_dates)].copy()
        if len(tr) < 500 or len(te) < 50:
            continue
        med = tr[FEATS].median()
        tr[FEATS], te[FEATS] = tr[FEATS].fillna(med), te[FEATS].fillna(med)
        y, yt = tr[target].values, te[target].values
        if is_clf:
            if len(np.unique(yt)) < 2:
                continue
            m = RandomForestClassifier(n_estimators=300, min_samples_leaf=20,
                                       random_state=RNG, n_jobs=-1).fit(tr[FEATS].values, y)
            pr = m.predict_proba(te[FEATS].values)[:, 1]
            vol_rows.append({"target": target, "fold": k, "auc": float(roc_auc_score(yt, pr)),
                             "brier": float(np.mean((pr - yt) ** 2)),
                             "brier_base": float(np.mean((y.mean() - yt) ** 2)),
                             "base_rate": float(yt.mean())})
        else:
            m = RandomForestRegressor(n_estimators=300, min_samples_leaf=20,
                                      random_state=RNG, n_jobs=-1).fit(tr[FEATS].values, y)
            pr = m.predict(te[FEATS].values)
            base = y.mean()
            vol_rows.append({"target": target, "fold": k,
                             "rmse": float(np.sqrt(np.mean((pr - yt) ** 2))),
                             "rmse_base": float(np.sqrt(np.mean((base - yt) ** 2))),
                             "r2_vs_mean": float(1 - np.sum((pr - yt) ** 2)
                                                 / np.sum((yt - base) ** 2)),
                             "corr": float(np.corrcoef(pr, yt)[0, 1])})
vol = pd.DataFrame(vol_rows)
vol.to_csv(P / "volatility_targets.csv", index=False)
vs = vol.groupby("target").mean(numeric_only=True).drop(columns=["fold"]).reset_index()
if "brier" in vs.columns:
    vs["skill_vs_base"] = 1 - vs.brier / vs.brier_base
vs.to_csv(P / "volatility_summary.csv", index=False)
RES["volatility_targets"] = vs.to_dict("records")
print("\n" + vs.to_string(index=False))

# Re-read at write time so a stage that finished while this one ran is kept.
_prev = json.load(open(P / "fundamentals_results.json"))
_prev |= RES
json.dump(_prev, open(P / "fundamentals_results.json", "w"), indent=1,
          default=str)
print("\n[EXTRA] written: extra_models, window_scheme_comparison, univariate_summary, "
      "volatility_summary")
