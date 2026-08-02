"""Maximise statistical predictability, with the economic filter applied only afterwards.

The report's framing had the order wrong. It reasoned from a distinction - statistical
predictability need not be economic predictability - to a decision not to build models aimed at
beating a random walk. That is the wrong way round: the distinction is only meaningful once the
statistical side has been pushed as far as it will go, because otherwise a weak result is
indistinguishable from a weak effort.

So this stage does the opposite. It takes the quantity the threshold model says is predictable,
tunes against it honestly, ensembles, and reports the largest out-of-sample R-squared the data
will yield - with no reference to whether the result could be traded. The economic question is
asked separately, in 25_arbitrage.py, and is allowed to reach whatever answer it reaches.

Tuning uses a time-series split inside the training window. The test period is touched once, at
the end, by the configuration the training window selected.

    python scripts/26_maximise.py
"""
import itertools, json, pathlib, warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import RidgeCV
import lightgbm as lgb
import xgboost as xgb
from catboost import CatBoostRegressor

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = 12345
MIN_XW, H = 10, 7

R = json.load(open(P / "results.json"))
THR = R["advanced"]["tar"]["threshold_pct"] / 100

pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
bw = pd.read_csv(P / "world_summary.csv")
d = pan[pan.world.isin(set(bw.query("converged").world))][
    ["world", "date", "price_gp", "day_sold", "day_bought"]].dropna(subset=["price_gp"]).copy()
d["logp"] = np.log(d.price_gp)
n_on = d.groupby("date").world.transform("size")
d["dev"] = (d.logp - d.groupby("date").logp.transform("mean")).where(n_on >= MIN_XW)
d = d.dropna(subset=["dev"]).sort_values(["world", "date"]).reset_index(drop=True)
g = d.groupby("world", observed=True)

# The target is the quantity the threshold model identifies, not a pooled return.
d["y"] = g.dev.shift(-H) - d.dev

# Predictors, all strictly lagged. Deliberately richer than 25_arbitrage.py's five, because the
# question here is how much signal exists rather than how simply it can be stated.
d["dev_l"] = g.dev.shift(1)
for L in (2, 3, 5, 10, 21):
    d[f"dev_l{L}"] = g.dev.shift(L)
for w in (5, 10, 21, 63):
    d[f"dev_ma{w}"] = g.dev.shift(1).rolling(w).mean().reset_index(level=0, drop=True)
    d[f"dev_sd{w}"] = g.dev.shift(1).rolling(w).std().reset_index(level=0, drop=True)
d["ret1"] = g.logp.diff().shift(1)
d["mom5"] = g.logp.shift(1) - g.logp.shift(6)
d["mom21"] = g.logp.shift(1) - g.logp.shift(22)
d["vol14"] = g.logp.diff().shift(1).rolling(14).std().reset_index(level=0, drop=True)
d["absdev"] = d.dev_l.abs()
d["outside"] = (d.absdev > THR).astype(float)
d["dev_x_out"] = d.dev_l * d.outside
d["dev_sq"] = d.dev_l * d.absdev                       # signed square: pull grows with distance
d["xw_disp"] = d.groupby("date").dev_l.transform("std")
d["dev_rank"] = d.groupby("date").dev_l.rank(pct=True)
d["turn"] = np.log1p(d[["day_sold", "day_bought"]].fillna(0).sum(axis=1)).groupby(
    d.world).shift(1)
d["dow"] = d.date.dt.dayofweek
FEATS = [c for c in d.columns if c.startswith(("dev_l", "dev_ma", "dev_sd", "mom", "ret1",
                                               "vol", "absdev", "outside", "dev_x", "dev_sq",
                                               "xw_disp", "dev_rank", "turn", "dow"))]
sub = d.dropna(subset=["y"] + FEATS).copy()
dates = np.sort(sub.date.unique())
cut_tr = dates[int(len(dates) * 0.6)]
tr_all, te = sub[sub.date < cut_tr], sub[sub.date >= cut_tr]
print(f"target: {H}-day change in the cross-world deviation")
print(f"{len(FEATS)} predictors | train {len(tr_all):,} to {pd.Timestamp(cut_tr).date()} "
      f"| test {len(te):,}")


def r2(p, y):
    return float(1 - np.sum((p - y) ** 2) / np.sum(y ** 2))


# ---- tuning inside the training window only ------------------------------------------------
inner = np.sort(tr_all.date.unique())
i_cut = inner[int(len(inner) * 0.75)]
itr, iva = tr_all[tr_all.date < i_cut], tr_all[tr_all.date >= i_cut]
print(f"tuning split: {len(itr):,} fit / {len(iva):,} validate")

GRID = {
    "RandomForest": [dict(n_estimators=400, min_samples_leaf=lf, max_features=mf,
                          random_state=RNG, n_jobs=-1)
                     for lf, mf in itertools.product((20, 50, 120), (0.4, 0.7))],
    "LightGBM": [dict(n_estimators=600, num_leaves=nl, learning_rate=lr, min_child_samples=40,
                      subsample=0.8, colsample_bytree=0.7, random_state=RNG, n_jobs=-1,
                      verbose=-1)
                 for nl, lr in itertools.product((15, 31), (0.02, 0.05))],
    "XGBoost": [dict(n_estimators=600, max_depth=md, learning_rate=lr, subsample=0.8,
                     colsample_bytree=0.7, reg_lambda=2.0, random_state=RNG, n_jobs=-1,
                     verbosity=0)
                for md, lr in itertools.product((3, 5), (0.02, 0.05))],
    "CatBoost": [dict(iterations=600, depth=dp, learning_rate=lr, l2_leaf_reg=6,
                      random_seed=RNG, verbose=0, allow_writing_files=False)
                 for dp, lr in itertools.product((4, 6), (0.02, 0.05))],
}
CTOR = {"RandomForest": RandomForestRegressor, "LightGBM": lgb.LGBMRegressor,
        "XGBoost": xgb.XGBRegressor, "CatBoost": CatBoostRegressor}

best_cfg, tune_rows = {}, []
for name, grid in GRID.items():
    scores = []
    for cfg in grid:
        m = CTOR[name](**cfg).fit(itr[FEATS].values, itr.y.values)
        s = r2(m.predict(iva[FEATS].values), iva.y.values)
        scores.append((s, cfg))
        tune_rows.append({"model": name, "val_r2": s, **{k: v for k, v in cfg.items()
                                                         if k in ("min_samples_leaf",
                                                                  "max_features", "num_leaves",
                                                                  "learning_rate", "max_depth",
                                                                  "depth")}})
    scores.sort(key=lambda z: -z[0])
    best_cfg[name] = scores[0][1]
    print(f"  {name:13} best validation R² {scores[0][0]:+.4f}")
pd.DataFrame(tune_rows).to_csv(P / "tuning_grid.csv", index=False)

# ---- refit on the whole training window, score once on the test period ---------------------
preds, rows = {}, []
for name, cfg in best_cfg.items():
    m = CTOR[name](**cfg).fit(tr_all[FEATS].values, tr_all.y.values)
    preds[name] = m.predict(te[FEATS].values)
ridge = RidgeCV(alphas=np.logspace(-3, 3, 25))
mu, sd = tr_all[FEATS].values.mean(0), tr_all[FEATS].values.std(0) + 1e-9
ridge.fit((tr_all[FEATS].values - mu) / sd, tr_all.y.values)
preds["Ridge"] = ridge.predict((te[FEATS].values - mu) / sd)
preds["Ensemble"] = np.mean([preds[k] for k in
                             ("RandomForest", "LightGBM", "XGBoost", "CatBoost")], axis=0)
preds["RandomWalk"] = np.zeros(len(te))

y = te.y.values
out_mask = te.outside.values == 1
for name, p in preds.items():
    rows.append({"model": name, "r2_all": r2(p, y),
                 "r2_outside_band": r2(p[out_mask], y[out_mask]),
                 "r2_inside_band": r2(p[~out_mask], y[~out_mask]),
                 "dir_acc": float(np.mean(np.sign(p) == np.sign(y))),
                 "corr": float(np.corrcoef(p, y)[0, 1]) if p.std() > 0 else np.nan})
best = pd.DataFrame(rows).sort_values("r2_all", ascending=False)
best.to_csv(P / "max_predictability.csv", index=False)
print("\n[MAXIMISE] out-of-sample R² on the deviation, best configuration per model")
print(best.to_string(index=False))

top = best.iloc[0]
res = json.load(open(P / "fundamentals_results.json"))
res["max_predictability"] = {
    "target": f"{H}-day change in cross-world deviation",
    "n_features": len(FEATS), "n_train": int(len(tr_all)), "n_test": int(len(te)),
    "table": best.to_dict("records"),
    "best_model": top.model, "best_r2": float(top.r2_all),
    "best_r2_outside": float(top.r2_outside_band),
    "best_dir_acc": float(top.dir_acc),
    "tuned_on": "a 75/25 split inside the training window; the test period was scored once",
}
json.dump(res, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print(f"\n[MAXIMISE] best achievable: {top.model} at R² {top.r2_all:+.4f} "
      f"({top.dir_acc:.1%} directional), written to max_predictability.csv")
