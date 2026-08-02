"""Regimes and explainability for the fundamentals study.

Two questions remain after 18_predict.py. Whether the market moves between states that a single
model would blur together - a Hidden Markov model and a change-point search answer that from
different directions, and agreeing is more convincing than either alone. And what the one model
that beat the random walk is actually using, which SHAP answers at the level of individual
predictions rather than as an average over the whole sample.

    python scripts/19_regimes.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
import ruptures as rpt
import shap
from hmmlearn.hmm import GaussianHMM
from sklearn.ensemble import RandomForestRegressor

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = 12345

d = pd.read_csv(P / "fundamentals_panel.csv", parse_dates=["date"])
meta = json.load(open(P / "fundamentals_meta.json"))
FEATS = [c for c in meta["features"] if c in d.columns]
d = d[d.converged].sort_values(["date", "world"]).reset_index(drop=True)
RES = {}

# ============================================================ 1. market states
# The state variables are chosen to span the dimensions the report already treats as distinct:
# how the level is moving, how violently, how much the worlds disagree, and how much of the
# economy is running.
mkt = (d.groupby("date")
         .agg(ret=("ret", "mean"), disp=("xw_disp", "mean"), vol=("ret_sd14", "mean"),
              kills=("g7_monsters_killed", "mean"), online=("log_players_online_avg", "mean"),
              turnover=("turnover_7", "mean"))
         .dropna())
X = ((mkt - mkt.mean()) / mkt.std()).values
print(f"market state series: {len(mkt)} days, {X.shape[1]} state variables")

best = None
for k in (2, 3, 4):
    hm = GaussianHMM(n_components=k, covariance_type="full", n_iter=400,
                     random_state=RNG).fit(X)
    bic = -2 * hm.score(X) + (k * k + 2 * k * X.shape[1]) * np.log(len(X))
    print(f"  HMM k={k}: loglik {hm.score(X):,.0f}  BIC {bic:,.0f}")
    if best is None or bic < best[1]:
        best = (hm, bic, k)
hmm, _, K = best
mkt["state"] = hmm.predict(X)

# Name the states by what they are rather than by their index, so the table reads without a key.
prof = mkt.groupby("state").agg(days=("ret", "size"), ret=("ret", "mean"),
                                vol=("vol", "mean"), disp=("disp", "mean"),
                                kills=("kills", "mean"), turnover=("turnover", "mean"))
prof["label"] = [
    ("expansion" if r.ret > 0 else "contraction") + (", high volatility" if r.vol >
     prof.vol.median() else ", calm")
    for _, r in prof.iterrows()]
prof = prof.reset_index()
mkt.reset_index().to_csv(P / "market_states.csv", index=False)
prof.to_csv(P / "regime_profile.csv", index=False)
print(prof.to_string(index=False))

trans = pd.DataFrame(hmm.transmat_,
                     index=[f"from_{i}" for i in range(K)],
                     columns=[f"to_{i}" for i in range(K)])
trans.to_csv(P / "regime_transitions.csv")
persist = float(np.mean(np.diag(hmm.transmat_)))

# A change-point search on the same series, as an independent check on the HMM's dating.
algo = rpt.Pelt(model="rbf", min_size=14).fit(X)
sweep = {}
for pen in (2, 4, 6, 8, 10, 12):
    sweep[pen] = [b for b in algo.predict(pen=pen) if b < len(mkt)]
    print(f"  PELT pen={pen:>2}: {len(sweep[pen])} change points")
PEN = 4
bkps = sweep[PEN]
cp_dates = [str(mkt.index[b].date()) for b in bkps]
hmm_switch = set(np.where(np.diff(mkt.state.values) != 0)[0] + 1)
agree = sum(1 for b in bkps if any(abs(b - s) <= 7 for s in hmm_switch))
print(f"[REGIMES] HMM chose k={K}, mean persistence {persist:.2f}; "
      f"{len(bkps)} change points, {agree} within a week of an HMM switch")

RES["regimes"] = {
    "k": int(K), "persistence": persist,
    "profile": prof.to_dict("records"),
    "change_points": cp_dates, "pelt_penalty": PEN,
    "pelt_sweep": {int(k): len(v) for k, v in sweep.items()},
    "n_change_points": len(bkps),
    "n_agreeing_with_hmm": int(agree),
    "expected_duration_days": {int(i): float(1 / (1 - hmm.transmat_[i, i]))
                               for i in range(K)},
}

# Does the one model that beat a random walk do so evenly, or only in some states?
pred = pd.read_csv(P / "model_predictions.csv", parse_dates=["date"])
pr = pred.query("target == 'rel' and horizon == 7")
if len(pr):
    pr = pr.merge(mkt.reset_index()[["date", "state"]], on="date", how="left")
    by = (pr.pivot_table(index=["state"], columns="model",
                         values=["y", "yhat"], aggfunc="size")
          if False else
          pr.groupby(["state", "model"]).apply(
              lambda g: np.sqrt(np.mean((g.yhat - g.y) ** 2)), include_groups=False)
            .rename("rmse").reset_index())
    by.to_csv(P / "regime_skill.csv", index=False)
    RES["regimes"]["skill_by_state"] = by.to_dict("records")
    print(by.to_string(index=False))

# ============================================================ 2. what the model uses
# SHAP on the model that survived correction, fitted on the first 70% and explained on the rest.
tgt = "y_rel7"
dh = d[FEATS + [tgt, "date"]].dropna()
dates = np.sort(dh.date.unique())
cut = dates[int(len(dates) * 0.7)]
tr, te = dh[dh.date < cut], dh[dh.date >= cut]
rf = RandomForestRegressor(n_estimators=250, min_samples_leaf=40, max_features=0.4,
                           random_state=RNG, n_jobs=-1).fit(tr[FEATS].values, tr[tgt].values)
sample = te.sample(min(1500, len(te)), random_state=RNG)
sv = shap.TreeExplainer(rf).shap_values(sample[FEATS].values, check_additivity=False)
shap_df = (pd.DataFrame({"feature": FEATS, "mean_abs_shap": np.abs(sv).mean(0)})
           .sort_values("mean_abs_shap", ascending=False).reset_index(drop=True))
shap_df.to_csv(P / "shap_importance.csv", index=False)
RES["shap_top"] = shap_df.head(20).to_dict("records")

# Group the features so the answer is about kinds of information, not individual columns.
def family(f):
    if f.startswith(("ret_", "mom", "vol_", "px_z", "dist_ma")):
        return "price history"
    if f.startswith(("log_monsters", "log_players_killed", "log_boss", "log_races",
                     "g7_", "g30_", "boss_share", "hunt_", "top10_", "deaths_", "death_")):
        return "kill statistics"
    if "online" in f:
        return "activity"
    if f.startswith(("log_day_", "log_active", "turnover")):
        return "liquidity"
    if f.startswith(("xw_", "rel_", "breadth", "beta_")):
        return "cross-world"
    if f.startswith(("dow_", "doy_", "is_week", "month")):
        return "seasonality"
    if f.startswith(("ev_", "n_events", "update_", "days_to", "event_")):
        return "events"
    return "structure"


shap_df["family"] = shap_df.feature.map(family)
fam = (shap_df.groupby("family").mean_abs_shap.sum()
       .sort_values(ascending=False) / shap_df.mean_abs_shap.sum())
RES["shap_by_family"] = {k: float(v) for k, v in fam.items()}
print("\nshare of explained variation by feature family:")
print((fam * 100).round(1).to_string())

# Re-read at write time so a stage that finished while this one ran is kept.
_prev = json.load(open(P / "fundamentals_results.json"))
_prev |= RES
json.dump(_prev, open(P / "fundamentals_results.json", "w"), indent=1,
          default=str)
print("\n[REGIMES] written: market_states, regime_profile, regime_transitions, "
      "shap_importance")
