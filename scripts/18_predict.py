"""Test whether fundamentals make the Tibia Coin price predictable.

The report already establishes what price history alone can do: the level carries a unit root
(Section 4.4) and a model fitted to price history loses to a random walk out of sample
(Section 6.4.3). This stage asks the different question - whether observing the economy that
produces gold changes that verdict - and it is built so that the answer can be negative.

Three things protect the answer from being flattering by construction.

Validation is by date, never by row. The panel is 61 worlds moving together, so a random split
would let a model see Tuesday on one world while predicting Tuesday on another. Folds expand
forward in time and every world enters or leaves a fold together.

Folds are purged. A 30-day forward return observed on the last training day overlaps the first
30 days of the test period, so the horizon is cut out between train and test.

Every model is scored against the same baselines, and the comparison is tested rather than
eyeballed: Diebold-Mariano with a Newey-West correction, against the random walk.

    python scripts/18_predict.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.inspection import permutation_importance
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import roc_auc_score
from statsmodels.tsa.stattools import grangercausalitytests
import lightgbm as lgb
import xgboost as xgb

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = 12345

d = pd.read_csv(P / "fundamentals_panel.csv", parse_dates=["date"])
meta = json.load(open(P / "fundamentals_meta.json"))
FEATS = [c for c in meta["features"] if c in d.columns]

# Converged worlds only. Launch-phase worlds are still discovering a price, and their returns
# are a convergence path rather than a market signal - Section 5.4 makes that case.
d = d[d.converged].sort_values(["date", "world"]).reset_index(drop=True)
print(f"panel: {len(d):,} world-days, {d.world.nunique()} converged worlds, "
      f"{d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d}")

RES = (json.load(open(P / "fundamentals_results.json"))
       if (P / "fundamentals_results.json").exists() else {})
RES |= {"panel": {"rows": int(len(d)), "worlds": int(d.world.nunique()),
                 "start": str(d.date.min().date()), "end": str(d.date.max().date()),
                 "n_features": len(FEATS)}}

# ============================================================ 1. leading indicators
# Does any fundamental move before the price, and at what lag? Mutual information catches
# nonlinear dependence that a correlation would miss; Granger asks the directional question on
# the market aggregate, where a common trend is what a leading indicator would have to lead.
mkt = (d.groupby("date")
         .agg(ret=("ret", "mean"),
              **{f: (f, "mean") for f in
                 ["log_monsters_killed", "log_players_killed", "log_boss_kills",
                  "log_players_online_avg", "log_kills_pp", "boss_share", "deaths_pp",
                  "g7_monsters_killed", "g30_monsters_killed", "turnover_7", "xw_disp"]})
         .dropna())
print(f"market aggregate series: {len(mkt)} days")

lead = []
for f in [c for c in mkt.columns if c != "ret"]:
    best = {"feature": f, "best_lag": None, "best_p": 1.0}
    for lagn in (1, 2, 3, 5, 7, 14):
        try:
            t = grangercausalitytests(mkt[["ret", f]].dropna(), maxlag=[lagn])
            p = t[lagn][0]["ssr_ftest"][1]
        except Exception:
            continue
        if p < best["best_p"]:
            best.update(best_lag=lagn, best_p=float(p))
    lead.append(best)
lead = pd.DataFrame(lead).sort_values("best_p")
# Many tests, one question: control the false-discovery rate rather than reading raw p-values.
m = len(lead)
lead["bh_threshold"] = (np.arange(1, m + 1) / m) * 0.05
lead["survives_bh"] = lead.best_p.values <= lead.bh_threshold.values
lead.to_csv(P / "leading_indicators.csv", index=False)
RES["granger"] = {"n_tested": int(m), "n_survive_bh_5pct": int(lead.survives_bh.sum()),
                  "table": lead.to_dict("records")}
print(f"[GRANGER] {int(lead.survives_bh.sum())} of {m} fundamentals survive Benjamini-Hochberg")

sub = d.dropna(subset=["y_ret1"])[FEATS + ["y_ret1"]].dropna()
mi = mutual_info_regression(sub[FEATS].values, sub.y_ret1.values, random_state=RNG)
mi_df = (pd.DataFrame({"feature": FEATS, "mutual_info": mi})
         .sort_values("mutual_info", ascending=False).reset_index(drop=True))
mi_df.to_csv(P / "mutual_information.csv", index=False)
RES["mutual_information_top"] = mi_df.head(15).to_dict("records")

# ============================================================ 2. walk-forward comparison
FOLDS = 6
dates = np.sort(d.date.unique())


def folds_for(h):
    """Expanding-origin folds with the forecast horizon purged from the join."""
    n = len(dates)
    start = int(n * 0.45)
    edges = np.linspace(start, n, FOLDS + 1).astype(int)
    for i in range(FOLDS):
        tr_end, te_end = edges[i], edges[i + 1]
        if te_end - tr_end < 5:
            continue
        yield (dates[:tr_end - h], dates[tr_end:te_end])


def models():
    return {
        "Ridge": Ridge(alpha=5.0),
        "ElasticNet": ElasticNet(alpha=1e-4, l1_ratio=0.5, max_iter=5000),
        "RandomForest": RandomForestRegressor(
            n_estimators=250, min_samples_leaf=40, max_features=0.4,
            random_state=RNG, n_jobs=-1),
        "XGBoost": xgb.XGBRegressor(
            n_estimators=350, max_depth=4, learning_rate=0.03, subsample=0.8,
            colsample_bytree=0.6, reg_lambda=2.0, random_state=RNG, n_jobs=-1,
            verbosity=0),
        "LightGBM": lgb.LGBMRegressor(
            n_estimators=350, num_leaves=15, learning_rate=0.03, subsample=0.8,
            colsample_bytree=0.6, min_child_samples=40, random_state=RNG,
            n_jobs=-1, verbose=-1),
    }


def dm_test(e1, e2, h):
    """Diebold-Mariano on squared errors, Newey-West at the forecast horizon."""
    dd = e1 ** 2 - e2 ** 2
    dd = dd[np.isfinite(dd)]
    n = len(dd)
    if n < 30:
        return np.nan, np.nan
    dbar = dd.mean()
    g0 = dd.var(ddof=0)
    lags = max(1, h - 1)
    s = g0 + 2 * sum((1 - k / (lags + 1)) * np.cov(dd[k:], dd[:-k], ddof=0)[0, 1]
                     for k in range(1, lags + 1))
    if s <= 0:
        return np.nan, np.nan
    t = dbar / np.sqrt(s / n)
    return float(t), float(2 * (1 - stats.norm.cdf(abs(t))))


rows, preds = [], []
for h, kind in [(h, k) for h in meta["horizons"] for k in ("ret", "rel")]:
    tgt = f"y_{kind}{h}"
    cols = FEATS + [tgt, "ret", "world", "date"]
    dh = d[cols].dropna(subset=[tgt])
    for k, (tr_dates, te_dates) in enumerate(folds_for(h)):
        tr = dh[dh.date.isin(tr_dates)].copy()
        te = dh[dh.date.isin(te_dates)].copy()
        med = tr[FEATS].median()
        tr[FEATS] = tr[FEATS].fillna(med)
        te[FEATS] = te[FEATS].fillna(med)
        tr = tr.dropna(subset=[tgt])
        te = te.dropna(subset=[tgt])
        if len(tr) < 500 or len(te) < 50:
            continue
        Xtr, ytr = tr[FEATS].values, tr[tgt].values
        Xte, yte = te[FEATS].values, te[tgt].values
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
        Ztr, Zte = (Xtr - mu) / sd, (Xte - mu) / sd

        # Baselines. The random walk predicts no change, which under a unit root is the
        # theoretically correct forecast and the one to beat.
        base = {"RandomWalk": np.zeros(len(te)),
                "Naive": te.ret.values * h,
                "MovingAvg": tr[tgt].mean() * np.ones(len(te))}
        fitted = {}
        for name, mdl in models().items():
            X1, X2 = (Ztr, Zte) if name in ("Ridge", "ElasticNet") else (Xtr, Xte)
            mdl.fit(X1, ytr)
            fitted[name] = mdl.predict(X2)

        e_rw = base["RandomWalk"] - yte
        for name, yh in {**base, **fitted}.items():
            e = yh - yte
            t, p = dm_test(e_rw, e, h) if name != "RandomWalk" else (np.nan, np.nan)
            rows.append({
                "horizon": h, "target": kind, "fold": k, "model": name,
                "n_test": int(len(te)),
                "rmse": float(np.sqrt(np.mean(e ** 2))),
                "mae": float(np.mean(np.abs(e))),
                "r2_oos": float(1 - np.sum(e ** 2) / np.sum((yte - 0) ** 2)),
                "dir_acc": float(np.mean(np.sign(yh) == np.sign(yte))),
                "dm_t_vs_rw": t, "dm_p_vs_rw": p})
            if name in ("LightGBM", "RandomWalk"):
                preds.append(pd.DataFrame({"horizon": h, "target": kind, "fold": k,
                                           "model": name,
                                           "world": te.world.values, "date": te.date.values,
                                           "y": yte, "yhat": yh}))
    print(f"[WALK-FORWARD] {kind} horizon {h}d done")

cv = pd.DataFrame(rows)
cv.to_csv(P / "model_comparison.csv", index=False)
pd.concat(preds).to_csv(P / "model_predictions.csv", index=False)

summary = (cv.groupby(["target", "horizon", "model"])
             .agg(rmse=("rmse", "mean"), mae=("mae", "mean"), r2_oos=("r2_oos", "mean"),
                  dir_acc=("dir_acc", "mean"), dm_t=("dm_t_vs_rw", "mean"),
                  folds=("fold", "count"))
             .reset_index())
def stouffer(g):
    z = g.dm_t_vs_rw.dropna().values
    if not len(z):
        return pd.Series({"dm_z": np.nan, "dm_p": np.nan, "folds_better": 0})
    zc = z.sum() / np.sqrt(len(z))
    return pd.Series({"dm_z": float(zc),
                      "dm_p": float(2 * (1 - stats.norm.cdf(abs(zc)))),
                      "folds_better": int((z > 0).sum())})


comb = (cv.groupby(["target", "horizon", "model"])[["dm_t_vs_rw"]]
          .apply(stouffer).reset_index())
summary = summary.merge(comb, on=["target", "horizon", "model"], how="left")
fam = summary.dropna(subset=["dm_p"]).query("model != 'RandomWalk'").copy()
fam = fam.sort_values("dm_p").reset_index(drop=True)
k = len(fam)
fam["bh_threshold"] = (fam.index + 1) / k * 0.05
fam["beats_rw"] = (fam.dm_z > 0) & (fam.dm_p <= fam.bh_threshold)
summary = summary.merge(
    fam[["target", "horizon", "model", "bh_threshold", "beats_rw"]],
    on=["target", "horizon", "model"], how="left")
summary["beats_rw"] = summary.beats_rw.fillna(False)
# Skill that is present early and absent late is not the same as skill. Record the per-fold
# path for the best model at each horizon so the average cannot stand alone.
stab = []
for h in meta["horizons"]:
    g = cv[(cv.target == "rel") & (cv.model == "RandomForest")
           & (cv.horizon == h)].sort_values("fold")
    if len(g) < 3:
        continue
    rho, prho = stats.spearmanr(g.fold, g.r2_oos)
    stab.append({"horizon": h, "mean_r2": float(g.r2_oos.mean()),
                 "median_r2": float(g.r2_oos.median()),
                 "first_fold_r2": float(g.r2_oos.iloc[0]),
                 "last_fold_r2": float(g.r2_oos.iloc[-1]),
                 "mean_excl_first": float(g.r2_oos.iloc[1:].mean()),
                 "trend_rho": float(rho), "trend_p": float(prho),
                 "folds": int(len(g)), "folds_positive": int((g.r2_oos > 0).sum())})
RES["fold_stability"] = stab
print("\n[STABILITY] per-fold R2 path of the best relative-return model")
print(pd.DataFrame(stab).round(4).to_string(index=False))

RES["n_comparisons"] = int(k)
RES["n_beating_rw_after_bh"] = int(summary.beats_rw.sum())
RES["best_uncorrected"] = fam.query("dm_z > 0").head(1).to_dict("records")
print(f"\n[MULTIPLE TESTING] {k} model-vs-random-walk comparisons; "
      f"{int(summary.beats_rw.sum())} survive Benjamini-Hochberg at 5%")
summary.to_csv(P / "model_summary.csv", index=False)
RES["model_summary"] = summary.to_dict("records")
print(summary.to_string(index=False))

# ============================================================ 3. classification targets
clf_rows = []
for h in meta["horizons"]:
    for tgt in (f"y_up{h}", f"y_dn{h}"):
        dh = d[FEATS + [tgt, "date"]].dropna(subset=[tgt])
        if dh[tgt].nunique() < 2:
            continue
        for k, (tr_dates, te_dates) in enumerate(folds_for(h)):
            tr, te = dh[dh.date.isin(tr_dates)].copy(), dh[dh.date.isin(te_dates)].copy()
            med = tr[FEATS].median()
            tr[FEATS] = tr[FEATS].fillna(med)
            te[FEATS] = te[FEATS].fillna(med)
            if len(tr) < 500 or len(te) < 50 or te[tgt].nunique() < 2:
                continue
            m = lgb.LGBMClassifier(n_estimators=300, num_leaves=15, learning_rate=0.03,
                                   min_child_samples=40, random_state=RNG, n_jobs=-1,
                                   verbose=-1)
            m.fit(tr[FEATS].values, tr[tgt].values)
            p = m.predict_proba(te[FEATS].values)[:, 1]
            clf_rows.append({"horizon": h, "target": tgt, "fold": k,
                             "base_rate": float(te[tgt].mean()),
                             "auc": float(roc_auc_score(te[tgt].values, p)),
                             "brier": float(np.mean((p - te[tgt].values) ** 2)),
                             "brier_base": float(np.mean(
                                 (tr[tgt].mean() - te[tgt].values) ** 2))})
clf = pd.DataFrame(clf_rows)
clf.to_csv(P / "classification_results.csv", index=False)
if len(clf):
    cs = (clf.groupby(["horizon", "target"])
            .agg(auc=("auc", "mean"), brier=("brier", "mean"),
                 brier_base=("brier_base", "mean"), base_rate=("base_rate", "mean"),
                 folds=("fold", "count")).reset_index())
    cs["skill_vs_base"] = 1 - cs.brier / cs.brier_base
    cs.to_csv(P / "classification_summary.csv", index=False)
    RES["classification"] = cs.to_dict("records")
    print(cs.to_string(index=False))

# ============================================================ 4. what the model uses
dh = d[FEATS + ["y_ret1", "date"]].dropna(subset=["y_ret1"])
dh[FEATS] = dh[FEATS].fillna(dh[FEATS].median())
cut = dates[int(len(dates) * 0.7)]
tr, te = dh[dh.date < cut], dh[dh.date >= cut]
final = lgb.LGBMRegressor(n_estimators=400, num_leaves=15, learning_rate=0.03,
                          min_child_samples=40, random_state=RNG, n_jobs=-1, verbose=-1)
final.fit(tr[FEATS].values, tr.y_ret1.values)
pi = permutation_importance(final, te[FEATS].values, te.y_ret1.values,
                            n_repeats=10, random_state=RNG, n_jobs=-1,
                            scoring="neg_mean_squared_error")
imp = (pd.DataFrame({"feature": FEATS, "perm_importance": pi.importances_mean,
                     "perm_sd": pi.importances_std,
                     "gain": final.booster_.feature_importance("gain")})
       .sort_values("perm_importance", ascending=False).reset_index(drop=True))
imp.to_csv(P / "feature_importance.csv", index=False)
RES["importance_top"] = imp.head(20).to_dict("records")

json.dump(RES, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[PREDICT] written: model_comparison, model_summary, classification_summary, "
      "leading_indicators, mutual_information, feature_importance")
