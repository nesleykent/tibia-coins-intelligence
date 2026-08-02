"""Does gold production drive the price, or does behaviour?

The report has treated gold supply as the leading candidate for the price level throughout, on
theoretical grounds, and has never tested it directly. The objection that prompted this stage is
exact: creatures drop gold, so kill statistics *are* a gold-production series, and if the supply
channel were the driver the elasticity of the coin's gold price to production would be visible
and large. Measuring it is a direct test that the study skipped.

The elasticity is estimated three ways, because a supply channel makes three distinct
predictions that a demand channel does not. Production should move the price with a positive
sign - more gold chasing a coin whose euro value is fixed means more gold per coin. It should
act on the accumulated stock, not only the daily flow, since gold persists. And its explanatory
power should survive alongside demand-side variables rather than vanish next to them.

Against that, the demand block: how much is being bought, how engaged the players are, whether
an event is running, and the price's own recent history - which is behaviour, not production.

    python scripts/28_supply_demand.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

d = pd.read_csv(P / "fundamentals_panel.csv", parse_dates=["date"])
ks = pd.read_csv(P / "kill_stats_daily.csv", parse_dates=["date"])
d = d[d.converged].merge(ks[["world", "date", "monsters_killed", "players_killed",
                             "boss_kills"]], on=["world", "date"], how="left")
d = d.sort_values(["world", "date"]).reset_index(drop=True)
g = d.groupby("world", observed=True)

# Gold persists, so the stock is what a supply story is about. The panel starts mid-history, so
# this is the accumulation observed within the window - a proxy for the flow's cumulative effect,
# not the world's whole monetary base.
d["cum_kills"] = g.monsters_killed.cumsum()
d["log_cum"] = np.log(d.cum_kills.clip(lower=1))
d["log_kills"] = np.log(d.monsters_killed.clip(lower=1))
d["dlog_kills"] = g.log_kills.diff()
d["dlog_cum"] = g.log_cum.diff()
d["dlogp"] = g.logp.diff()
print(f"panel: {len(d):,} world-days, {d.world.nunique()} worlds")

RES = {}


def fe_ols(frame, y, xs, cluster="world"):
    """Within-world OLS with standard errors clustered by world."""
    f = frame[[y] + xs + [cluster]].replace([np.inf, -np.inf], np.nan).dropna()
    if len(f) < 200:
        return None
    dm = f.groupby(cluster)[[y] + xs].transform(lambda s: s - s.mean())
    X = np.column_stack([np.ones(len(f))] + [dm[x].values for x in xs])
    yv = dm[y].values
    b, *_ = np.linalg.lstsq(X, yv, rcond=None)
    r = yv - X @ b
    XtX_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros_like(XtX_inv)
    for _, idx in f.groupby(cluster).indices.items():
        Xg, rg = X[idx], r[idx]
        meat += np.outer(Xg.T @ rg, Xg.T @ rg)
    V = XtX_inv @ meat @ XtX_inv
    se = np.sqrt(np.diag(V))
    ss_tot = np.sum((yv - yv.mean()) ** 2)
    return {"coef": b[1:], "se": se[1:], "names": xs, "n": len(f),
            "r2_within": float(1 - np.sum(r ** 2) / ss_tot),
            "t": b[1:] / se[1:],
            "p": 2 * (1 - stats.norm.cdf(np.abs(b[1:] / se[1:])))}


# ============================================================ 1. the supply elasticity
# The direct question. If gold production drives the coin's gold price, these coefficients are
# positive and large. A daily flow and an accumulated stock are both tried, at several horizons,
# because a supply effect need not arrive within a day.
rows = []
for h in (1, 7, 30):
    d[f"fwd{h}"] = g.logp.shift(-h) - d.logp
    for var, label in (("dlog_kills", "gold production, daily flow"),
                       ("dlog_cum", "gold production, accumulated stock")):
        d[f"x_{var}_{h}"] = g[var].rolling(h).sum().reset_index(level=0, drop=True).shift(1)
        r = fe_ols(d, f"fwd{h}", [f"x_{var}_{h}"])
        if r:
            rows.append({"horizon": h, "channel": label, "elasticity": float(r["coef"][0]),
                         "se": float(r["se"][0]), "t": float(r["t"][0]),
                         "p": float(r["p"][0]), "r2_within": r["r2_within"], "n": r["n"]})
sup = pd.DataFrame(rows)
sup.to_csv(P / "supply_elasticity.csv", index=False)
print("\n[SUPPLY] elasticity of the forward gold price to gold production")
print(sup.round(5).to_string(index=False))
RES["supply_elasticity"] = sup.to_dict("records")

# ============================================================ 2. supply against demand
# A horse race at seven days. Blocks are entered alone and then together, so a variable that
# only appears to matter until its rival is present is exposed.
SUPPLY = ["x_dlog_kills_7", "boss_share", "deaths_pp"]
DEMAND = [c for c in ["g7_players_online_avg", "turnover_imb", "log_active_traders",
                      "ev_any", "idx_premium_demand", "w_engagement"] if c in d.columns]
BEHAV = [c for c in ["ret_lag1", "mom30", "ret_sd14", "rel_premium", "breadth_up"]
         if c in d.columns]
blocks = {"supply only": SUPPLY, "demand only": DEMAND, "behaviour only": BEHAV,
          "supply + demand": SUPPLY + DEMAND,
          "all three": SUPPLY + DEMAND + BEHAV}
hr = []
for label, xs in blocks.items():
    r = fe_ols(d, "fwd7", xs)
    if r:
        hr.append({"block": label, "k": len(xs), "r2_within": r["r2_within"], "n": r["n"]})
race = pd.DataFrame(hr)
race.to_csv(P / "supply_demand_race.csv", index=False)
print("\n[HORSE RACE] within-world R² on the seven-day forward return")
print(race.round(5).to_string(index=False))
RES["horse_race"] = race.to_dict("records")

full = fe_ols(d, "fwd7", SUPPLY + DEMAND + BEHAV)
if full:
    coefs = pd.DataFrame({"variable": full["names"], "coef": full["coef"],
                          "se": full["se"], "t": full["t"], "p": full["p"]})
    coefs["block"] = ["supply" if v in SUPPLY else "demand" if v in DEMAND else "behaviour"
                      for v in coefs.variable]
    coefs = coefs.sort_values("p")
    coefs.to_csv(P / "supply_demand_coefs.csv", index=False)
    print("\n[JOINT MODEL] every variable, clustered by world")
    print(coefs.round(5).to_string(index=False))
    RES["joint_coefficients"] = coefs.to_dict("records")
    RES["n_significant_by_block"] = (coefs[coefs.p < 0.05].groupby("block").size()
                                     .to_dict())

# ============================================================ 3. does the stock cointegrate
# The level question. If accumulated gold sets the price level, the two should move together
# over the window rather than drift apart.
co = []
for w, gg in d.groupby("world"):
    gg = gg.dropna(subset=["logp", "log_cum"])
    if len(gg) < 150:
        continue
    x, y = gg.log_cum.values, gg.logp.values
    b = np.polyfit(x, y, 1)
    resid = y - np.polyval(b, x)
    # Engle-Granger step two: a stationary residual means the two share a trend.
    dr = np.diff(resid)
    lr = resid[:-1]
    beta = np.polyfit(lr, dr, 1)[0]
    tstat = beta / (np.std(dr - np.polyval(np.polyfit(lr, dr, 1), lr))
                    / (np.std(lr) * np.sqrt(len(lr))) + 1e-12)
    co.append({"world": w, "slope": float(b[0]), "adf_like_t": float(tstat),
               "corr": float(np.corrcoef(x, y)[0, 1])})
cod = pd.DataFrame(co)
cod.to_csv(P / "gold_stock_cointegration.csv", index=False)
print(f"\n[LEVEL] price against accumulated gold production, {len(cod)} worlds")
print(f"  median slope {cod.slope.median():+.3f}; "
      f"positive on {(cod.slope > 0).sum()} of {len(cod)} worlds")
print(f"  median correlation {cod['corr'].median():+.3f}")
RES["gold_stock"] = {"n_worlds": int(len(cod)),
                     "median_slope": float(cod.slope.median()),
                     "n_positive_slope": int((cod.slope > 0).sum()),
                     "median_corr": float(cod["corr"].median()),
                     "share_reject_no_cointegration":
                         float((cod.adf_like_t < -2.86).mean())}

out = json.load(open(P / "fundamentals_results.json"))
out["supply_vs_demand"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[SUPPLY-DEMAND] written: supply_elasticity, supply_demand_race, "
      "supply_demand_coefs, gold_stock_cointegration")
