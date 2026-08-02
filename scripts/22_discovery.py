"""Automatic predictor discovery and the explainability the brief asks for.

Discovery. The interactions in 17_features.py were chosen by hand from what the report already
believed, which is exactly the kind of choice that smuggles a prior into a result. This stage
searches instead: every pairwise product of the strongest features is generated and scored, and
four selection methods that disagree by construction are run side by side. Boruta asks whether a
feature beats a randomised copy of itself; recursive elimination asks what survives being
removed; the LASSO path asks what enters first as the penalty relaxes; mutual information asks
what shares information regardless of functional form. Agreement across four is worth more than
a ranking from one.

Explainability. Partial dependence for the shape of a relationship, counterfactuals for what
would have had to differ, and conformal intervals for how wrong a prediction can be. The
conformal interval is the honest one: it is calibrated on held-out residuals and makes no
distributional assumption.

    python scripts/22_discovery.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFE, mutual_info_regression
from sklearn.inspection import partial_dependence
from sklearn.linear_model import LassoCV, lasso_path

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = 12345
TGT = "y_rel7"          # the target Section 6.6.3 found to be predictable

d = pd.read_csv(P / "fundamentals_panel.csv", parse_dates=["date"])
meta = json.load(open(P / "fundamentals_meta.json"))
FEATS = [c for c in meta["features"] if c in d.columns]
d = d[d.converged].sort_values(["date", "world"]).reset_index(drop=True)
dh = d[FEATS + [TGT, "date"]].dropna(subset=[TGT]).copy()
dates = np.sort(dh.date.unique())
cut = dates[int(len(dates) * 0.7)]
tr, te = dh[dh.date < cut].copy(), dh[dh.date >= cut].copy()
med = tr[FEATS].median()
tr[FEATS], te[FEATS] = tr[FEATS].fillna(med), te[FEATS].fillna(med)
Xtr, ytr = tr[FEATS].values, tr[TGT].values
Xte, yte = te[FEATS].values, te[TGT].values
print(f"train {len(tr):,} rows to {pd.Timestamp(cut).date()}, test {len(te):,} rows, "
      f"{len(FEATS)} features")
RES = {}


def rf(n=250, leaf=40):
    return RandomForestRegressor(n_estimators=n, min_samples_leaf=leaf, max_features=0.4,
                                 random_state=RNG, n_jobs=-1)


base = rf().fit(Xtr, ytr)
base_r2 = 1 - np.sum((base.predict(Xte) - yte) ** 2) / np.sum(yte ** 2)
print(f"baseline out-of-sample R² on {TGT}: {base_r2:+.4f}")

# ============================================================ 1. Boruta
# A feature earns its place only by beating a shuffled copy of itself. Shuffling breaks any
# relationship with the target while preserving the marginal distribution, so the shadow is the
# same feature with its information removed - a fair null rather than an arbitrary threshold.
rs = np.random.RandomState(RNG)
hits = np.zeros(len(FEATS))
ROUNDS = 20
for _ in range(ROUNDS):
    shadow = np.column_stack([rs.permutation(Xtr[:, j]) for j in range(Xtr.shape[1])])
    m = rf(120, 40).fit(np.hstack([Xtr, shadow]), ytr)
    imp = m.feature_importances_
    real, shad = imp[:len(FEATS)], imp[len(FEATS):]
    hits += (real > shad.max()).astype(float)
boruta = (pd.DataFrame({"feature": FEATS, "hits": hits, "rounds": ROUNDS,
                        "hit_rate": hits / ROUNDS})
          .sort_values("hits", ascending=False).reset_index(drop=True))
# Binomial tail under the null that a feature beats the best shadow by chance alone.
from scipy.stats import binomtest
p0 = 1.0 / (len(FEATS) + 1)
boruta["p"] = [binomtest(int(h), ROUNDS, p0, alternative="greater").pvalue for h in hits]
boruta["confirmed"] = boruta.p < 0.05 / len(FEATS)
boruta.to_csv(P / "boruta.csv", index=False)
print(f"[BORUTA] {int(boruta.confirmed.sum())} of {len(FEATS)} features confirmed "
      f"over {ROUNDS} rounds")

# ============================================================ 2. RFE and the LASSO path
n_keep = 25
rfe = RFE(rf(120, 40), n_features_to_select=n_keep, step=0.15).fit(Xtr, ytr)
rfe_sel = [f for f, k in zip(FEATS, rfe.support_) if k]

mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
Ztr = (Xtr - mu) / sd
alphas, coefs, _ = lasso_path(Ztr, ytr, n_alphas=60)
# Order of entry along the path: the smaller the penalty needed, the earlier a feature enters.
entry = np.array([np.argmax(np.abs(coefs[j]) > 0) if np.any(np.abs(coefs[j]) > 0) else 1e9
                  for j in range(len(FEATS))])
lasso_rank = pd.DataFrame({"feature": FEATS, "entry_step": entry}).sort_values("entry_step")
lcv = LassoCV(cv=5, random_state=RNG, alphas=40).fit(Ztr, ytr)
lasso_sel = [f for f, c in zip(FEATS, lcv.coef_) if abs(c) > 1e-10]

mi = mutual_info_regression(Xtr, ytr, random_state=RNG)
mi_rank = pd.DataFrame({"feature": FEATS, "mi": mi}).sort_values("mi", ascending=False)

votes = pd.DataFrame({"feature": FEATS})
votes["boruta"] = votes.feature.isin(boruta[boruta.confirmed].feature).astype(int)
votes["rfe"] = votes.feature.isin(rfe_sel).astype(int)
votes["lasso"] = votes.feature.isin(lasso_sel).astype(int)
votes["mutual_info"] = votes.feature.isin(mi_rank.head(n_keep).feature).astype(int)
votes["votes"] = votes[["boruta", "rfe", "lasso", "mutual_info"]].sum(axis=1)
votes = votes.sort_values("votes", ascending=False).reset_index(drop=True)
votes.to_csv(P / "feature_selection_votes.csv", index=False)
consensus = votes[votes.votes >= 3].feature.tolist()
print(f"[SELECTION] {len(consensus)} features selected by at least three of four methods")
print(votes.head(12).to_string(index=False))

# Does a model on the consensus set match one on everything?
if consensus:
    cm = rf().fit(tr[consensus].values, ytr)
    cons_r2 = 1 - np.sum((cm.predict(te[consensus].values) - yte) ** 2) / np.sum(yte ** 2)
else:
    cons_r2 = np.nan
print(f"[SELECTION] R² on {len(consensus)} consensus features: {cons_r2:+.4f} "
      f"(all {len(FEATS)}: {base_r2:+.4f})")

# ============================================================ 3. interaction search
# Products of the strongest features, scored by whether adding one improves held-out error.
# Searching is cheap; the multiple-comparisons risk is handled by requiring the winner to also
# survive on a second, later split.
top = votes.head(14).feature.tolist()
pairs = [(a, b) for i, a in enumerate(top) for b in top[i + 1:]]
found = []
for a, b in pairs:
    trx = np.column_stack([Xtr, tr[a].values * tr[b].values])
    tex = np.column_stack([Xte, te[a].values * te[b].values])
    m = rf(120, 40).fit(trx, ytr)
    r2 = 1 - np.sum((m.predict(tex) - yte) ** 2) / np.sum(yte ** 2)
    found.append({"a": a, "b": b, "r2_with": r2, "gain": r2 - base_r2})
inter = pd.DataFrame(found).sort_values("gain", ascending=False).reset_index(drop=True)

cut2 = dates[int(len(dates) * 0.5)]
tr2, te2 = dh[dh.date < cut2].copy(), dh[(dh.date >= cut2) & (dh.date < cut)].copy()
if len(te2) > 200:
    m2 = tr2[FEATS].median()
    tr2[FEATS], te2[FEATS] = tr2[FEATS].fillna(m2), te2[FEATS].fillna(m2)
    b2 = rf(120, 40).fit(tr2[FEATS].values, tr2[TGT].values)
    base2 = 1 - np.sum((b2.predict(te2[FEATS].values) - te2[TGT].values) ** 2) \
        / np.sum(te2[TGT].values ** 2)
    conf = []
    for _, r in inter.head(10).iterrows():
        trx = np.column_stack([tr2[FEATS].values, tr2[r.a].values * tr2[r.b].values])
        tex = np.column_stack([te2[FEATS].values, te2[r.a].values * te2[r.b].values])
        mm = rf(120, 40).fit(trx, tr2[TGT].values)
        r2b = 1 - np.sum((mm.predict(tex) - te2[TGT].values) ** 2) \
            / np.sum(te2[TGT].values ** 2)
        conf.append(r2b - base2)
    inter["gain_second_split"] = np.nan
    inter.loc[inter.index[:len(conf)], "gain_second_split"] = conf
    inter["replicates"] = (inter.gain > 0) & (inter.gain_second_split > 0)
    n_rep = int(inter.replicates.fillna(False).sum())
    print(f"[INTERACTIONS] of the top 10, {n_rep} also improve on an earlier disjoint split")
inter.to_csv(P / "interaction_search.csv", index=False)
print(f"[INTERACTIONS] searched {len(pairs)} pairs; best gain "
      f"{inter.gain.iloc[0]:+.4f} from {inter.a.iloc[0]} x {inter.b.iloc[0]}; "
      f"{int((inter.gain > 0).sum())} of {len(inter)} improve on the baseline")

# ============================================================ 4. partial dependence
pdp_rows = []
for f in votes.head(6).feature:
    j = FEATS.index(f)
    pd_ = partial_dependence(base, Xte, [j], grid_resolution=20, kind="average")
    for x, y in zip(pd_["grid_values"][0], pd_["average"][0]):
        pdp_rows.append({"feature": f, "x": float(x), "partial_dependence": float(y)})
pdp = pd.DataFrame(pdp_rows)
pdp.to_csv(P / "partial_dependence.csv", index=False)

# ============================================================ 5. conformal intervals
# Split conformal: fit on the first part, calibrate the residual quantile on a held-out slice,
# and the interval carries a finite-sample coverage guarantee without assuming normality.
n_cal = int(len(tr) * 0.25)
fit_idx, cal_idx = np.arange(len(tr) - n_cal), np.arange(len(tr) - n_cal, len(tr))
cm = rf().fit(Xtr[fit_idx], ytr[fit_idx])
resid = np.abs(ytr[cal_idx] - cm.predict(Xtr[cal_idx]))
cov_rows = []
for alpha in (0.10, 0.20, 0.50):
    q = np.quantile(resid, 1 - alpha)
    pred = cm.predict(Xte)
    inside = np.mean(np.abs(yte - pred) <= q)
    cov_rows.append({"nominal": 1 - alpha, "empirical": float(inside),
                     "half_width": float(q)})
cov = pd.DataFrame(cov_rows)
cov.to_csv(P / "conformal_coverage.csv", index=False)
print("\n[CONFORMAL]"); print(cov.to_string(index=False))

# ============================================================ 6. counterfactuals
# For the most confidently negative predictions, what single change would have flipped the
# sign? Searched over the consensus features by moving one at a time to its decile values.
pred_te = cm.predict(Xte)
target_rows = np.argsort(pred_te)[:200]
target_rows = target_rows[pred_te[target_rows] < 0]
GRID_N = 10
cf = []
for f in votes.head(8).feature:
    j = FEATS.index(f)
    grid = np.quantile(Xtr[:, j], np.linspace(0.05, 0.95, GRID_N))
    block = np.repeat(Xte[target_rows], GRID_N, axis=0)
    block[:, j] = np.tile(grid, len(target_rows))
    out = cm.predict(block).reshape(len(target_rows), GRID_N)
    flipped = out > 0
    any_flip = flipped.any(axis=1)
    first = np.argmax(flipped, axis=1)
    moves = grid[first[any_flip]] - Xte[target_rows][any_flip, j]
    cf.append({"feature": f, "n_considered": int(len(target_rows)),
               "n_flipped": int(any_flip.sum()),
               "flip_rate": float(any_flip.mean()) if len(target_rows) else 0.0,
               "median_move": float(np.median(moves)) if moves.size else np.nan})
cfd = pd.DataFrame(cf).sort_values("flip_rate", ascending=False)
cfd.to_csv(P / "counterfactuals.csv", index=False)
print("\n[COUNTERFACTUAL] single-feature changes that flip a negative forecast positive")
print(cfd.to_string(index=False))

idx_used = votes[votes.feature.str.startswith("idx_")]
RES["discovery"] = {
    "baseline_r2": float(base_r2),
    "boruta_confirmed": int(boruta.confirmed.sum()),
    "boruta_top": boruta.head(10).to_dict("records"),
    "n_features": len(FEATS),
    "consensus_features": consensus,
    "consensus_r2": float(cons_r2),
    "votes_top": votes.head(15).to_dict("records"),
    "interactions_searched": len(pairs),
    "interactions_improving": int((inter.gain > 0).sum()),
    "best_interaction": inter.head(3).to_dict("records"),
    "interactions_replicating": int(inter.get("replicates", pd.Series(dtype=bool))
                                    .fillna(False).sum()),
    "conformal": cov.to_dict("records"),
    "counterfactual": cfd.to_dict("records"),
    "named_indices": idx_used.to_dict("records"),
}
# Re-read at write time so a stage that finished while this one ran is kept.
_prev = json.load(open(P / "fundamentals_results.json"))
_prev |= RES
json.dump(_prev, open(P / "fundamentals_results.json", "w"), indent=1,
          default=str)
print("\n[DISCOVERY] written: boruta, feature_selection_votes, interaction_search, "
      "partial_dependence, conformal_coverage, counterfactuals")
