"""Compare estimation scopes: global, regional, per-world, hierarchical and multi-task.

Section 6.6 fits one model to all 61 worlds at once. That is a choice, not a neutral default,
and it embeds an assumption worth testing: that the mapping from fundamentals to next week's
relative price is the same on Antica as on Belobra. Three things could be true instead. Worlds
may differ enough that a model per world does better despite having a sixtieth of the data.
Regions may be the natural grouping. Or the truth may be in between, which is what a
hierarchical model expresses - a global fit plus a shrunk per-world correction.

The comparison uses the same walk-forward protocol as 18_predict.py so the numbers are directly
comparable to the global row, and every scope is tested against the random walk and against the
global model.

    python scripts/20_hierarchy.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge

warnings.filterwarnings("ignore")
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
print(f"panel: {len(d):,} world-days, {d.world.nunique()} worlds, {len(FEATS)} features")


def folds_for(h):
    n = len(dates)
    edges = np.linspace(int(n * 0.45), n, FOLDS + 1).astype(int)
    for i in range(FOLDS):
        if edges[i + 1] - edges[i] >= 5:
            yield dates[:edges[i] - h], dates[edges[i]:edges[i + 1]]


def rf():
    return RandomForestRegressor(n_estimators=250, min_samples_leaf=40, max_features=0.4,
                                 random_state=RNG, n_jobs=-1)


def prep(frame, med=None):
    f = frame.copy()
    if med is None:
        med = f[FEATS].median()
    f[FEATS] = f[FEATS].fillna(med)
    return f, med


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


rows = []
for h in HORIZONS:
    tgt = f"y_rel{h}"
    dh = d[FEATS + [tgt, "world", "region", "date"]].dropna(subset=[tgt])
    for k, (tr_dates, te_dates) in enumerate(folds_for(h)):
        tr_raw = dh[dh.date.isin(tr_dates)]
        te_raw = dh[dh.date.isin(te_dates)]
        if len(tr_raw) < 500 or len(te_raw) < 50:
            continue
        tr, med = prep(tr_raw)
        te, _ = prep(te_raw, med)
        y = te[tgt].values
        pred = {}

        # Global: one model, every world.
        g = rf().fit(tr[FEATS].values, tr[tgt].values)
        pred["global"] = g.predict(te[FEATS].values)

        # Regional: one model per region, which assumes worlds in a region share a mapping.
        pr = np.full(len(te), np.nan)
        for reg, idx in te.groupby("region").groups.items():
            trr = tr[tr.region == reg]
            if len(trr) < 200:
                continue
            m = rf().fit(trr[FEATS].values, trr[tgt].values)
            pr[te.index.get_indexer(idx)] = m.predict(te.loc[idx, FEATS].values)
        pred["regional"] = np.where(np.isnan(pr), pred["global"], pr)

        # Per-world: maximum flexibility, minimum data - about 150 training rows each.
        pw = np.full(len(te), np.nan)
        for w, idx in te.groupby("world").groups.items():
            trw = tr[tr.world == w]
            if len(trw) < 80:
                continue
            m = RandomForestRegressor(n_estimators=150, min_samples_leaf=8,
                                      max_features=0.4, random_state=RNG,
                                      n_jobs=-1).fit(trw[FEATS].values, trw[tgt].values)
            pw[te.index.get_indexer(idx)] = m.predict(te.loc[idx, FEATS].values)
        pred["per_world"] = np.where(np.isnan(pw), pred["global"], pw)

        # Hierarchical: the global fit plus a per-world correction on its residual, shrunk
        # toward zero by how little data that world has. This is the partial-pooling estimator
        # written out rather than assumed - lambda is the shrinkage weight.
        res_tr = tr[tgt].values - g.predict(tr[FEATS].values)
        hier = pred["global"].copy()
        LAMBDA = 100.0
        for w, idx in te.groupby("world").groups.items():
            trw = tr[tr.world == w]
            if len(trw) < 80:
                continue
            rw = res_tr[tr.world.values == w]
            corr = Ridge(alpha=50.0).fit(trw[FEATS].values, rw)
            shrink = len(trw) / (len(trw) + LAMBDA)
            pos = te.index.get_indexer(idx)
            hier[pos] += shrink * corr.predict(te.loc[idx, FEATS].values)
        pred["hierarchical"] = hier

        # Multi-task: one shared model that is told which task each row belongs to. The world
        # identity is target-encoded - its mean and spread of the target - computed on the
        # training fold alone so the encoding cannot carry test information.
        enc = tr.groupby("world")[tgt].agg(["mean", "std", "size"])
        prior, kappa = tr[tgt].mean(), 50.0
        enc["smooth"] = ((enc["mean"] * enc["size"] + prior * kappa)
                         / (enc["size"] + kappa))          # shrunk toward the pooled mean
        for f, col in (("world_te", "smooth"), ("world_sd", "std")):
            tr[f] = tr.world.map(enc[col]).astype(float)
            te[f] = te.world.map(enc[col]).astype(float).fillna(
                prior if f == "world_te" else tr[f].median())
        mt_feats = FEATS + ["world_te", "world_sd"]
        m = rf().fit(tr[mt_feats].values, tr[tgt].values)
        pred["multi_task"] = m.predict(te[mt_feats].values)

        e_rw = -y
        e_gl = pred["global"] - y
        for name, yh in pred.items():
            e = yh - y
            rows.append({
                "horizon": h, "fold": k, "scope": name, "n_test": int(len(te)),
                "rmse": float(np.sqrt(np.mean(e ** 2))),
                "r2_oos": float(1 - np.sum(e ** 2) / np.sum(y ** 2)),
                "dir_acc": float(np.mean(np.sign(yh) == np.sign(y))),
                "dm_t_vs_rw": dm(e_rw, e, h),
                "dm_t_vs_global": dm(e_gl, e, h) if name != "global" else np.nan})
    print(f"[HIERARCHY] horizon {h}d done")

cv = pd.DataFrame(rows)
cv.to_csv(P / "hierarchy_comparison.csv", index=False)


def stouffer(z):
    z = z.dropna().values
    if not len(z):
        return np.nan, np.nan
    zc = z.sum() / np.sqrt(len(z))
    return float(zc), float(2 * (1 - stats.norm.cdf(abs(zc))))


agg = []
for (h, sc), g in cv.groupby(["horizon", "scope"]):
    z_rw, p_rw = stouffer(g.dm_t_vs_rw)
    z_gl, p_gl = stouffer(g.dm_t_vs_global)
    agg.append({"horizon": h, "scope": sc, "rmse": g.rmse.mean(),
                "r2_oos": g.r2_oos.mean(), "dir_acc": g.dir_acc.mean(),
                "dm_z_vs_rw": z_rw, "dm_p_vs_rw": p_rw,
                "dm_z_vs_global": z_gl, "dm_p_vs_global": p_gl,
                "folds": int(len(g)),
                "folds_better_than_global": int((g.dm_t_vs_global > 0).sum())})
summary = pd.DataFrame(agg).sort_values(["horizon", "r2_oos"], ascending=[True, False])
summary.to_csv(P / "hierarchy_summary.csv", index=False)
print(summary.to_string(index=False))

best = summary.loc[summary.groupby("horizon").r2_oos.idxmax()]
RES = {}
RES["hierarchy"] = {
    "summary": summary.to_dict("records"),
    "best_scope_by_horizon": {int(r.horizon): r.scope for _, r in best.iterrows()},
    "n_scopes": int(summary.scope.nunique()),
    "any_scope_beats_global": bool((summary.dm_p_vs_global < 0.05).any()
                                   and (summary.dm_z_vs_global > 0).any()),
}
# Re-read at write time so a stage that finished while this one ran is kept.
_prev = json.load(open(P / "fundamentals_results.json"))
_prev |= RES
json.dump(_prev, open(P / "fundamentals_results.json", "w"), indent=1,
          default=str)
print("\n[HIERARCHY] written: hierarchy_comparison, hierarchy_summary")
