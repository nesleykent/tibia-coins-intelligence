"""Advanced econometrics: Band-TAR, panel cointegration/VECM, spatial models, IV.

Each block replaces a manual or descriptive procedure in the base study with a formal
estimator, and each reports what it can and cannot identify.
"""
import json, pathlib, sys, warnings
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.vector_ar.vecm import coint_johansen

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from econ import ols

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = np.random.default_rng(20260730)

R = json.load(open(P / "results.json"))
conv = pd.read_csv(P / "converged_panel.csv", parse_dates=["date"])
conv = conv.sort_values(["world", "date"]).reset_index(drop=True)
ADV = {}


# ============================================================ helpers
def within(y, g):
    """Demean y by group codes g (fast fixed-effect absorption)."""
    y = np.asarray(y, float)
    cnt = np.bincount(g)
    s = np.bincount(g, weights=y)
    return y - (s / cnt)[g]


def ols_np(X, y):
    XtX = X.T @ X
    b = np.linalg.solve(XtX, X.T @ y)
    r = y - X @ b
    return b, float(r @ r), r


# ============================================================ 1. Band-TAR
# Obstfeld & Taylor's threshold model of the law of one price under transaction costs:
#     dev(t) = rho_in  * dev(t-1)              if |dev(t-1)| <= gamma
#     dev(t) = rho_out * dev(t-1)              if |dev(t-1)| >  gamma
# Inside the band arbitrage is unprofitable and the deviation should behave as a random walk
# (rho_in ~ 1); outside it, trade should pull the deviation back (rho_out < 1). The threshold
# gamma is estimated by Hansen's grid search - the value minimising the residual sum of
# squares - rather than imposed, so the transaction-cost band is recovered from prices alone.
d = conv.dropna(subset=["dev", "dev_lag"]).copy()
g_codes = pd.factorize(d["world"])[0]
y = within(d["dev"].values, g_codes)
x = d["dev_lag"].values
ax = np.abs(x)

# Search from well down in the distribution: a grid that starts too high returns a
# boundary solution and the reported minimum is then an artefact of the grid, not an
# estimate. The lower bound is checked against the realised argmin below.
grid = np.quantile(ax, np.linspace(0.02, 0.90, 260))
grid = np.unique(np.round(grid, 6))


def tar_ssr(gamma, xv, axv, yv, gc):
    inb = (axv <= gamma).astype(float)
    X = np.column_stack([within(xv * inb, gc), within(xv * (1 - inb), gc)])
    _, ssr, _ = ols_np(X, yv)
    return ssr


ssrs = np.array([tar_ssr(gm, x, ax, y, g_codes) for gm in grid])
gam = float(grid[np.argmin(ssrs)])
ssr_tar = float(ssrs.min())

inb = (ax <= gam).astype(float)
Xhat = np.column_stack([within(x * inb, g_codes), within(x * (1 - inb), g_codes)])
b_tar, _, res_tar = ols_np(Xhat, y)
n, k = Xhat.shape
# Standard errors clustered by world (deviations are serially dependent within a world).
XtXi = np.linalg.pinv(Xhat.T @ Xhat)
S = pd.DataFrame(Xhat * res_tar[:, None]).groupby(g_codes).sum().to_numpy()
G = S.shape[0]
V = XtXi @ (S.T @ S) @ XtXi * (G / (G - 1)) * ((n - 1) / (n - k - d["world"].nunique()))
se_tar = np.sqrt(np.diag(V))

# Linear (no-threshold) benchmark and Hansen's LR confidence interval for gamma.
Xlin = within(x, g_codes)[:, None]
_, ssr_lin, _ = ols_np(Xlin, y)
lr = n * (ssrs - ssr_tar) / ssr_tar
ci_mask = lr <= 7.35                       # Hansen (2000) 95% critical value
ci = (float(grid[ci_mask].min()), float(grid[ci_mask].max()))

# Bootstrap test that a threshold exists at all: resample residuals under the linear null and
# recompute the best attainable SSR improvement.
f_obs = (ssr_lin - ssr_tar) / (ssr_tar / (n - k))
B = 300
f_boot = np.empty(B)
_, _, res_lin = ols_np(Xlin, y)
for b in range(B):
    yb = Xlin @ np.linalg.solve(Xlin.T @ Xlin, Xlin.T @ y) + RNG.permutation(res_lin)
    yb = within(yb, g_codes)
    s_b = np.array([tar_ssr(gm, x, ax, yb, g_codes) for gm in grid[::4]])
    _, ssr_lin_b, _ = ols_np(Xlin, yb)
    f_boot[b] = (ssr_lin_b - s_b.min()) / (s_b.min() / (n - k))
p_boot = float((f_boot >= f_obs).mean())

hl_in = float(np.log(0.5) / np.log(abs(b_tar[0]))) if 0 < abs(b_tar[0]) < 1 else np.inf
hl_out = float(np.log(0.5) / np.log(abs(b_tar[1]))) if 0 < abs(b_tar[1]) < 1 else np.inf
ADV["tar"] = {
    "threshold_pct": gam * 100,
    "threshold_ci_pct": [ci[0] * 100, ci[1] * 100],
    "rho_inside": float(b_tar[0]), "se_inside": float(se_tar[0]),
    "rho_outside": float(b_tar[1]), "se_outside": float(se_tar[1]),
    "t_inside_vs_unity": float((b_tar[0] - 1) / se_tar[0]),
    "t_outside_vs_unity": float((b_tar[1] - 1) / se_tar[1]),
    "half_life_inside_days": hl_in, "half_life_outside_days": hl_out,
    "share_inside_band": float(inb.mean()),
    "n": int(n), "n_worlds": int(d["world"].nunique()),
    "F_threshold": float(f_obs), "p_bootstrap": p_boot, "n_bootstrap": B,
    "ssr_linear": ssr_lin, "ssr_tar": ssr_tar,
    "fee_roundtrip_pct": 4.0,
    "grid_min_pct": float(grid.min() * 100), "grid_max_pct": float(grid.max() * 100),
    "at_grid_boundary": bool(np.argmin(ssrs) <= 1 or np.argmin(ssrs) >= len(grid) - 2),
    "abs_dev_pctiles": {q: float(np.quantile(ax, q / 100) * 100)
                        for q in (5, 25, 50, 75, 95)},
}
pd.DataFrame({"gamma_pct": grid * 100, "ssr": ssrs, "lr": lr}).to_csv(
    P / "tar_grid.csv", index=False)

# Band-TAR in Obstfeld-Taylor form: outside the band the deviation is pulled back toward the
# EDGE of the band, not toward zero, and inside it there is no adjustment at all.
def band_tar_ssr(gamma, xv, yv, gc):
    out = np.sign(xv) * np.maximum(np.abs(xv) - gamma, 0.0)
    X = within(out, gc)[:, None]
    _, ssr, _ = ols_np(X, yv)
    return ssr


dy = within(d["dev"].values - d["dev_lag"].values, g_codes)
b_ssr = np.array([band_tar_ssr(gm, x, dy, g_codes) for gm in grid])
gam_b = float(grid[np.argmin(b_ssr)])
Xb = within(np.sign(x) * np.maximum(ax - gam_b, 0.0), g_codes)[:, None]
bb, _, _ = ols_np(Xb, dy)
ADV["tar_band"] = {
    "threshold_pct": gam_b * 100, "adjustment_outside": float(bb[0]),
    "half_life_outside_days": float(np.log(0.5) / np.log(1 + bb[0]))
    if -1 < bb[0] < 0 else np.nan,
    # The pull-to-the-edge form drives the threshold to the bottom of the search grid, i.e.
    # it is a boundary solution and the threshold is NOT identified in this specification.
    # The adjustment speed is still informative; the threshold from it is not.
    "at_grid_boundary": bool(np.argmin(b_ssr) <= 1),
}

# The daily deviation carries transitory measurement error (Section 15.2). Noise manufactures
# apparent reversion at small deviations, which biases the estimated threshold DOWNWARD.
# Re-estimating on weekly averages cuts the noise variance roughly sevenfold; if the threshold
# rises toward the round-trip fee, measurement error is the explanation.
wk = (conv.dropna(subset=["dev"]).set_index("date").groupby("world")["dev"]
      .resample("W").mean().reset_index())
wk["dev_lag"] = wk.groupby("world")["dev"].shift(1)
wk = wk.dropna(subset=["dev", "dev_lag"])
gw = pd.factorize(wk["world"])[0]
yw = within(wk["dev"].values, gw)
xw_ = wk["dev_lag"].values
axw = np.abs(xw_)
grid_w = np.unique(np.round(np.quantile(axw, np.linspace(0.02, 0.90, 200)), 6))
ssr_w = np.array([tar_ssr(gm, xw_, axw, yw, gw) for gm in grid_w])
gam_w = float(grid_w[np.argmin(ssr_w)])
inw = (axw <= gam_w).astype(float)
Xw = np.column_stack([within(xw_ * inw, gw), within(xw_ * (1 - inw), gw)])
bw_, ssr_wmin, _ = ols_np(Xw, yw)
lr_w = len(yw) * (ssr_w - ssr_wmin) / ssr_wmin
ci_w = grid_w[lr_w <= 7.35]
ADV["tar_weekly"] = {
    "threshold_pct": gam_w * 100,
    "threshold_ci_pct": [float(ci_w.min() * 100), float(ci_w.max() * 100)],
    "rho_inside": float(bw_[0]), "rho_outside": float(bw_[1]),
    "n": int(len(yw)), "share_inside_band": float(inw.mean()),
}
print(f"[TAR] band-TAR threshold {gam_b*100:.2f}%, adjustment {bb[0]:+.4f}/day")
print(f"[TAR] weekly-frequency threshold {gam_w*100:.2f}% "
      f"(95% CI {ci_w.min()*100:.2f}-{ci_w.max()*100:.2f}), "
      f"rho_in {bw_[0]:.4f} rho_out {bw_[1]:.4f}")
print(f"[TAR] threshold {gam*100:.2f}% (95% CI {ci[0]*100:.2f}-{ci[1]*100:.2f}) | "
      f"rho_in {b_tar[0]:.4f} rho_out {b_tar[1]:.4f} | bootstrap p={p_boot:.3f}")

# ============================================================ 2. Panel cointegration / VECM
# Each world's log price is I(1) (Section 15). If the spread between a world and the
# cross-world mean is stationary, the two are cointegrated with the vector (1, -1) and the
# system is a VECM whose error-correction term is exactly the deviation used throughout.
pu = []
for w, gdf in conv.dropna(subset=["dev"]).groupby("world"):
    s = gdf.set_index("date")["dev"].asfreq("D").interpolate(limit=2).dropna()
    if len(s) < 200:
        continue
    try:
        st, pv = adfuller(s, autolag="AIC")[:2]
        pu.append({"world": w, "adf_stat": st, "adf_p": pv, "n": len(s)})
    except Exception:
        pass
pu = pd.DataFrame(pu)
# Choi/Fisher inverse-normal combination of the per-world tests.
z = float(np.sum(stats.norm.ppf(pu.adf_p.clip(1e-12, 1 - 1e-12))) / np.sqrt(len(pu)))
ADV["cointegration"] = {
    "n_worlds": int(len(pu)),
    "reject_unit_root_in_deviation_5pct": int((pu.adf_p < 0.05).sum()),
    "share_reject": float((pu.adf_p < 0.05).mean()),
    "fisher_choi_Z": z, "fisher_choi_p": float(stats.norm.cdf(z)),
    "median_adf_p": float(pu.adf_p.median()),
}
pu.to_csv(P / "panel_unitroot_deviation.csv", index=False)

# Johansen rank test on a small system of the largest worlds, to establish cointegration
# rank formally rather than assuming the (1, -1) vector.
piv = conv.pivot_table(index="date", columns="world", values="log_price")
big = conv.groupby("world").day_sold_txn.median().nlargest(5).index.tolist()
sub = piv[big].dropna()
joh = None
if len(sub) > 300:
    jr = coint_johansen(sub.values, det_order=0, k_ar_diff=1)
    rank = int(sum(jr.lr1 > jr.cvt[:, 1]))       # trace statistic vs 95% critical value
    joh = {"worlds": big, "n_obs": int(len(sub)), "rank": rank, "n_series": len(big),
           "trace_stats": [float(v) for v in jr.lr1],
           "crit_95": [float(v) for v in jr.cvt[:, 1]]}
ADV["cointegration"]["johansen"] = joh

# Panel VECM (error-correction form), pooled with world fixed effects:
#   d p(i,t) = alpha_i + lambda * ecm(i,t-1) + short-run terms + e
ecm = conv.dropna(subset=["ret", "dev_lag"]).copy()
ecm["d_mean"] = ecm.groupby("date")["ret"].transform("mean")
ecm["d_mean_lag"] = ecm.groupby("world")["d_mean"].shift(1)
ecm["ret_lag"] = ecm.groupby("world")["ret"].shift(1)
m1 = ols(ecm, "ret", ["dev_lag"], fe=["world"], cluster=["world", "date"])
m2 = ols(ecm, "ret", ["dev_lag", "ret_lag", "d_mean", "d_mean_lag"],
         fe=["world"], cluster=["world", "date"])
lam = m2["coef"]["dev_lag"][0]
ADV["vecm"] = {
    "ec_only": {k: {"coef": float(a), "se": float(b), "p": float(c)}
                for k, (a, b, c) in m1["coef"].items()} | {"_n": m1["n"]},
    "full": {k: {"coef": float(a), "se": float(b), "p": float(c)}
             for k, (a, b, c) in m2["coef"].items()} | {"_n": m2["n"]},
    "adjustment_speed": float(lam),
    "half_life_days": float(np.log(0.5) / np.log(1 + lam)) if -1 < lam < 0 else np.nan,
}
print(f"[VECM] EC speed {lam:+.4f}/day -> half-life "
      f"{ADV['vecm']['half_life_days']:.1f}d | deviation stationary on "
      f"{ADV['cointegration']['reject_unit_root_in_deviation_5pct']}/{len(pu)} worlds"
      + (f" | Johansen rank {joh['rank']}/{joh['n_series']}" if joh else ""))

# ============================================================ 3. Spatial econometrics
# There is no physical distance between worlds: region is a server-location label, and coins
# move at the account level regardless of it. What a spatial model tests here is whether
# shocks propagate more strongly between worlds that share an attribute than between worlds
# that do not - a real question about market segmentation, not about geography.
meta = conv.groupby("world").agg(region=("region", "first"), pvp=("pvp_type", "first")).reset_index()
ws = meta.world.tolist()
idx_of = {w: i for i, w in enumerate(ws)}
N = len(ws)


def rownorm(W):
    s = W.sum(axis=1, keepdims=True)
    return np.divide(W, s, out=np.zeros_like(W), where=s > 0)


_reg = np.asarray(meta.region.astype(str))
_pvp = np.asarray(meta.pvp.astype(str))
same_region = (_reg[:, None] == _reg[None, :]).astype(float)
same_pvp = (_pvp[:, None] == _pvp[None, :]).astype(float)
np.fill_diagonal(same_region, 0)
np.fill_diagonal(same_pvp, 0)
W_reg, W_pvp = rownorm(same_region), rownorm(same_pvp)
W_all = rownorm(1 - np.eye(N))

rp = conv.pivot_table(index="date", columns="world", values="ret").reindex(columns=ws)
rp = rp.dropna(thresh=int(0.6 * N))


def morans_I(Wm, M):
    """Average Moran's I of daily returns across dates, with a permutation p-value."""
    vals = []
    Mv = M.values
    for row in Mv:
        ok = ~np.isnan(row)
        if ok.sum() < 10:
            continue
        z_ = row[ok] - row[ok].mean()
        Ws = rownorm(Wm[np.ix_(ok, ok)])
        denom = (z_ ** 2).sum()
        if denom == 0:
            continue
        vals.append(float(z_ @ (Ws @ z_) / denom))
    return float(np.mean(vals)), len(vals)


mi_reg, nd = morans_I(same_region, rp)
mi_pvp, _ = morans_I(same_pvp, rp)
mi_all, _ = morans_I(1 - np.eye(N), rp)
perm = []
for _ in range(200):
    sh = rp.copy()
    cols = RNG.permutation(sh.columns.values)
    sh.columns = cols
    sh = sh.reindex(columns=ws)
    perm.append(morans_I(same_region, sh)[0])
perm = np.array(perm)
ADV["spatial"] = {
    "expected_I_under_null": float(-1.0 / (N - 1)),
    "morans_I_region": mi_reg, "morans_I_pvp": mi_pvp, "morans_I_allworlds": mi_all,
    "n_dates": nd, "n_worlds": N,
    "perm_mean": float(perm.mean()), "perm_sd": float(perm.std()),
    "perm_p_region": float((perm >= mi_reg).mean()),
}

# Spatial-lag (SAR) panel model of daily returns. OLS on a spatial lag is inconsistent
# because W*ret is simultaneously determined, so the spatial lag is instrumented by the
# spatial lag of the pre-determined deviation (Kelejian-Prucha style).
sp = conv.dropna(subset=["ret", "dev_lag"]).copy()
rmat = conv.pivot_table(index="date", columns="world", values="ret").reindex(columns=ws)
dmat = conv.pivot_table(index="date", columns="world", values="dev_lag").reindex(columns=ws)


def spatial_lag(M, Wm):
    A = M.to_numpy()
    ok = ~np.isnan(A)
    Af = np.where(ok, A, 0.0)
    num = Af @ Wm.T
    den = ok.astype(float) @ Wm.T
    out = np.divide(num, den, out=np.full_like(num, np.nan), where=den > 1e-12)
    return pd.DataFrame(out, index=M.index, columns=M.columns)


for nm, Wm in [("region", W_reg), ("allworlds", W_all)]:
    wl = spatial_lag(rmat, Wm).stack().rename(f"Wret_{nm}")
    wd = spatial_lag(dmat, Wm).stack().rename(f"Wdev_{nm}")
    sp = sp.merge(wl.reset_index().rename(columns={"level_1": "world"}), on=["date", "world"], how="left")
    sp = sp.merge(wd.reset_index().rename(columns={"level_1": "world"}), on=["date", "world"], how="left")

sar = {}
for nm in ["region", "allworlds"]:
    s2 = sp.dropna(subset=[f"Wret_{nm}", f"Wdev_{nm}", "ret", "dev_lag"]).copy()
    # First stage: instrument the endogenous spatial lag with the spatial lag of dev_lag.
    fs = ols(s2, f"Wret_{nm}", [f"Wdev_{nm}", "dev_lag"], fe=["world"], cluster=["world"])
    s2["Wret_hat"] = np.nan
    from econ import absorb
    Z = absorb(s2, [f"Wret_{nm}", f"Wdev_{nm}", "dev_lag"], ["world"])
    Xz = np.column_stack([Z[f"Wdev_{nm}"], Z["dev_lag"]])
    bz = np.linalg.lstsq(Xz, Z[f"Wret_{nm}"].to_numpy(), rcond=None)[0]
    s2["Wret_hat"] = Xz @ bz
    second = ols(s2, "ret", ["Wret_hat", "dev_lag"], fe=["world"], cluster=["world", "date"])
    b, se, pv = second["coef"]["Wret_hat"]
    fstat = float((bz[0] / (np.std(Z[f"Wdev_{nm}"]) and 1)) ** 2) if False else None
    fs_b, fs_se, fs_p = fs["coef"][f"Wdev_{nm}"]
    sar[nm] = {"rho": float(b), "se": float(se), "p": float(pv), "n": second["n"],
               "first_stage_coef": float(fs_b), "first_stage_se": float(fs_se),
               "first_stage_t": float(fs_b / fs_se), "first_stage_F": float((fs_b / fs_se) ** 2),
               "dev_lag": {"coef": float(second["coef"]["dev_lag"][0]),
                           "se": float(second["coef"]["dev_lag"][1]),
                           "p": float(second["coef"]["dev_lag"][2])},
               # Stock-Yogo rule of thumb: a first stage below F=10 leaves the second-stage
               # estimate uninterpretable, however precise it looks.
               "weak_instrument": bool((fs_b / fs_se) ** 2 < 10)}
ADV["spatial"]["sar"] = sar
print(f"[SPATIAL] Moran's I within-region {mi_reg:.4f} vs all-worlds {mi_all:.4f} "
      f"(permutation p={ADV['spatial']['perm_p_region']:.3f}) | "
      f"SAR rho region {sar['region']['rho']:+.3f} (p={sar['region']['p']:.3g})")

# ============================================================ 4. Identification of events
# A global event indicator is a function of the date alone, so under date fixed effects it is
# annihilated: no instrument can recover it, because the variation does not exist in the data
# rather than being merely confounded. The identifiable object is the INTERACTION of a global
# event with a world characteristic, which varies within a date.
cal_cols = ["ev_xp_skill", "ev_rapid_respawn"]
iv = conv.dropna(subset=["ret", "dev_lag"]).copy()
iv["log_act"] = np.log(iv["activity_online"].where(iv["activity_online"] > 0))
iv["opt_pvp"] = (iv.pvp_type == "Optional PvP").astype(float)
iv = iv.dropna(subset=["log_act"])
iv["act_z"] = iv.groupby("date")["log_act"].transform(lambda s: (s - s.mean()) / s.std(ddof=0))

inter = {}
for c in cal_cols:
    iv[f"{c}_x_act"] = iv[c] * iv["act_z"]
    iv[f"{c}_x_pvp"] = iv[c] * iv["opt_pvp"]
    m = ols(iv, "ret", [f"{c}_x_act", f"{c}_x_pvp", "dev_lag"],
            fe=["world", "date"], cluster=["world", "date"])
    inter[c] = {k: {"coef": float(a) * (100 if "_x_" in k else 1),
                    "se": float(b) * (100 if "_x_" in k else 1), "p": float(p)}
                for k, (a, b, p) in m["coef"].items()} | {"_n": m["n"]}
ADV["identification"] = {"interactions_under_date_fe": inter}

# 2SLS: local gold-generation intensity is unobserved. It is proxied by activity, which is
# endogenous to price, and instrumented by the interaction of a global event with the world's
# activity rank - variation that is global in timing but world-specific in exposure.
iv2 = iv.dropna(subset=["ev_xp_skill_x_act", "ev_rapid_respawn_x_act"]).copy()
from econ import absorb as _absorb
Zc = _absorb(iv2, ["act_z", "ev_xp_skill_x_act", "ev_rapid_respawn_x_act", "ret", "dev_lag"],
             ["world", "date"])
Zi = np.column_stack([Zc["ev_xp_skill_x_act"], Zc["ev_rapid_respawn_x_act"], Zc["dev_lag"]])
bz2 = np.linalg.lstsq(Zi, Zc["act_z"].to_numpy(), rcond=None)[0]
fit = Zi @ bz2
resid_fs = Zc["act_z"].to_numpy() - fit
k_inst, n_iv = 2, len(iv2)
ss_tot = float(((Zc["act_z"] - Zc["act_z"].mean()) ** 2).sum())
f_first = float(((ss_tot - resid_fs @ resid_fs) / k_inst) / (resid_fs @ resid_fs / (n_iv - k_inst)))
iv2["act_hat"] = fit
m_iv = ols(iv2, "ret", ["act_hat", "dev_lag"], fe=["world", "date"], cluster=["world", "date"])
b_iv, se_iv, p_iv = m_iv["coef"]["act_hat"]
m_ols = ols(iv2, "ret", ["act_z", "dev_lag"], fe=["world", "date"], cluster=["world", "date"])
ADV["identification"]["iv_activity"] = {
    "iv_coef_pct": float(b_iv * 100), "iv_se_pct": float(se_iv * 100), "iv_p": float(p_iv),
    "ols_coef_pct": float(m_ols["coef"]["act_z"][0] * 100),
    "ols_se_pct": float(m_ols["coef"]["act_z"][1] * 100),
    "ols_p": float(m_ols["coef"]["act_z"][2]),
    "first_stage_F": f_first, "n": int(n_iv), "n_instruments": k_inst,
}
print(f"[IV] first-stage F={f_first:.1f} | activity effect OLS "
      f"{m_ols['coef']['act_z'][0]*100:+.4f}%/day vs IV {b_iv*100:+.4f}%/day (p={p_iv:.3g})")

R["advanced"] = ADV
json.dump(R, open(P / "results.json", "w"), indent=1, default=str)
print("\nwritten to results.json under 'advanced'")
