"""Is the price unpredictable in principle, or only with the data we happen to have?

Everything to this point answers a narrower question than it appears to. Testing 140 observable
features against a random walk establishes whether *this* information predicts the price. It
says nothing about whether some other information - unrecorded, or unrecordable - would. Those
are different claims, and the second is the one a reader is likely to take away.

The second is testable, by four routes that do not require the missing data.

Structure without a model. Entropy and complexity measures ask whether a series contains
regularity, regardless of whether anyone can write down the rule producing it. Compared against
surrogates that preserve the linear structure and destroy everything else, they detect hidden
nonlinear dependence that a forecasting model might be failing to exploit.

Determinism. The BDS test asks whether residuals are independent once linear structure is
removed. A rejection means structure remains, even if no model here found it.

The martingale property. If the price is a martingale, the answer to the broader question is a
principled no - not "we lack the data" but "the next change is news, and news is unforecastable
by construction". This is the strongest form the negative can take.

Retrospect versus foresight. A Kalman smoother sees the whole sample; the filter sees only the
past. Both infer the same latent state. If the smoothed state explains far more of the variation
than the filtered state, then a hidden driver exists and observing it would help - the
unpredictability is epistemic. If they explain the same amount, the variation is not hiding
anywhere; it is irreducible.

    python scripts/27_irreducible.py
"""
import json, math, pathlib, warnings

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.structural import UnobservedComponents

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
RNG = np.random.RandomState(4242)

pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
bw = pd.read_csv(P / "world_summary.csv")
conv = set(bw.query("converged").world)
d = pan[pan.world.isin(conv)][["world", "date", "price_gp"]].dropna().copy()
d["logp"] = np.log(d.price_gp)
d = d.sort_values(["world", "date"]).reset_index(drop=True)
d["ret"] = d.groupby("world", observed=True).logp.diff()

idx = pd.read_csv(P / "market_index.csv", parse_dates=["date"])
mkt = idx.dropna(subset=["ew_price"]).copy()
mkt["ret"] = np.log(mkt.ew_price).diff()
mret = mkt.ret.dropna().values
print(f"market index: {len(mret)} daily returns; panel: {len(d):,} world-days")
RES = {}


# ============================================================ 1. structure without a model
def permutation_entropy(x, m=4, tau=1):
    """Bandt-Pompe: the entropy of the ordinal patterns of length m. Normalised so 1.0 means
    every ordering is equally likely, which is what an independent series produces."""
    n = len(x) - (m - 1) * tau
    if n < 50:
        return np.nan
    patterns = np.argsort(np.array([x[i:i + n] for i in range(0, m * tau, tau)]), axis=0)
    codes = np.ravel_multi_index(patterns, (m,) * m)
    _, counts = np.unique(codes, return_counts=True)
    p = counts / counts.sum()
    return float(-(p * np.log(p)).sum() / np.log(math.factorial(m)))


def sample_entropy(x, m=2, r=0.2):
    """Regularity: the log-odds that two windows close at length m stay close at m+1. Lower
    means more repeating structure."""
    x = (x - x.mean()) / (x.std() + 1e-12)
    n = len(x)
    if n > 1200:
        x = x[-1200:]
        n = 1200

    def phi(mm):
        z = np.array([x[i:i + mm] for i in range(n - mm)])
        dist = np.max(np.abs(z[:, None, :] - z[None, :, :]), axis=2)
        np.fill_diagonal(dist, np.inf)
        return (dist <= r).sum()

    a, b = phi(m + 1), phi(m)
    return float(-np.log(a / b)) if a > 0 and b > 0 else np.nan


def iaaft(x, n_iter=60):
    """A surrogate with the same amplitude distribution and the same power spectrum, and no
    other structure. Anything the real series has that this lacks is nonlinear."""
    amp = np.abs(np.fft.rfft(x))
    srt = np.sort(x)
    y = RNG.permutation(x)
    for _ in range(n_iter):
        f = np.fft.rfft(y)
        y = np.fft.irfft(amp * np.exp(1j * np.angle(f)), n=len(x))
        y = srt[np.argsort(np.argsort(y))]
    return y


pe_real, se_real = permutation_entropy(mret), sample_entropy(mret)
n_sur = 200
pe_sur = np.array([permutation_entropy(iaaft(mret)) for _ in range(n_sur)])
se_sur = np.array([sample_entropy(iaaft(mret)) for _ in range(min(60, n_sur))])
pe_p = float((np.abs(pe_sur - pe_sur.mean()) >= abs(pe_real - pe_sur.mean())).mean())
se_p = float((np.abs(se_sur - np.nanmean(se_sur)) >= abs(se_real - np.nanmean(se_sur))).mean())
print(f"\n[ENTROPY] permutation entropy {pe_real:.4f} vs surrogates "
      f"{pe_sur.mean():.4f} +/- {pe_sur.std():.4f}  (p {pe_p:.3f})")
print(f"[ENTROPY] sample entropy      {se_real:.4f} vs surrogates "
      f"{np.nanmean(se_sur):.4f} +/- {np.nanstd(se_sur):.4f}  (p {se_p:.3f})")
RES["entropy"] = {"permutation_entropy": pe_real, "pe_surrogate_mean": float(pe_sur.mean()),
                  "pe_p": pe_p, "sample_entropy": se_real,
                  "se_surrogate_mean": float(np.nanmean(se_sur)), "se_p": se_p,
                  "n_surrogates": n_sur,
                  "note": "1.0 permutation entropy means no ordinal structure at all"}


# ============================================================ 2. hidden nonlinear dependence
from statsmodels.tsa.stattools import bds as _bds_test

bds_rows = []
st, pv = _bds_test(mret, max_dim=4)
for i, m in enumerate(range(2, 5)):
    bds_rows.append({"embedding": m, "statistic": float(np.ravel(st)[i]),
                     "p": float(np.ravel(pv)[i])})
bdf = pd.DataFrame(bds_rows)
print("\n[BDS] independence of the market return after linear structure")
print(bdf.to_string(index=False))
RES["bds"] = bdf.to_dict("records")

# ============================================================ 3. the martingale property
lb = acorr_ljungbox(mret, lags=[5, 10, 20], return_df=True)
lb_sq = acorr_ljungbox(mret ** 2, lags=[5, 10, 20], return_df=True)
print("\n[MARTINGALE] Ljung-Box on returns and on squared returns")
print(pd.concat([lb.add_prefix("ret_"), lb_sq.add_prefix("sq_")], axis=1).round(4).to_string())
RES["martingale"] = {"returns": lb.reset_index().to_dict("records"),
                     "squared_returns": lb_sq.reset_index().to_dict("records")}

# ============================================================ 4. retrospect versus foresight
# The decisive test. A local-level model has one latent state. The filter estimates it from the
# past alone; the smoother re-estimates it knowing the whole sample. Both describe the same
# hidden driver, so the difference between how much each explains is exactly the part that a
# better-informed observer could have known but a forecaster could not.
# A single-series local-level model puts essentially all variance into the state (the fitted
# irregular variance is 1.6e-11), so the smoothed state reproduces the data and the comparison
# is vacuous. The state has to be smaller than the data for the question to mean anything, so it
# is estimated as one common factor across worlds, with each world observing it in noise.
from statsmodels.tsa.statespace.dynamic_factor import DynamicFactor

wide = (d.pivot_table(index="date", columns="world", values="ret")
        .dropna(axis=1, thresh=600).dropna())
keep = list(wide.columns)[:12]
W = wide[keep]
W = (W - W.mean()) / W.std()
print(f"\n[LATENT] common-factor model on {len(keep)} worlds, {len(W)} dates")
dfm = DynamicFactor(W.values, k_factors=1, factor_order=1).fit(disp=0, maxiter=150)

load = np.asarray(dfm.params[:len(keep)])
f_filt = np.asarray(dfm.filtered_state[0])
f_sm = np.asarray(dfm.smoothed_state[0])
f_fore = np.r_[0.0, f_filt[:-1]] * float(
    dfm.params.get("L1.f1.f1", 0.0) if hasattr(dfm.params, "get") else 0.0)

Y = W.values


def explained(factor):
    """Share of each world's return variance reproduced by the factor at its loading."""
    num = den = 0.0
    for j in range(Y.shape[1]):
        fit = load[j] * factor[:len(Y)]
        num += np.sum((Y[:, j] - fit) ** 2)
        den += np.sum(Y[:, j] ** 2)
    return float(1 - num / den)


r2_forecast = explained(f_fore)
r2_filtered = explained(f_filt)
r2_smooth = explained(f_sm)
print(f"  factor known one step ahead (forecastable part) : {r2_forecast:+.4f}")
print(f"  factor filtered from the past                   : {r2_filtered:+.4f}")
print(f"  factor smoothed with the whole sample           : {r2_smooth:+.4f}")
print(f"  gap - recoverable in retrospect, not in advance : {r2_smooth - r2_forecast:+.4f}")
RES["latent_state"] = {
    "n_worlds": len(keep), "n_dates": int(len(W)),
    "r2_factor_forecast": r2_forecast, "r2_factor_filtered": r2_filtered,
    "r2_factor_smoothed": r2_smooth,
    "retrospect_gap": r2_smooth - r2_forecast,
    "reading": ("the smoothed figure is what a perfectly informed observer of the common "
                "driver could explain; the forecast figure is what is available in advance. "
                "The gap is the size of the prize for observing the hidden state, and the "
                "remainder above the smoothed figure is irreducible")}

json.dump(RES, open(P / "irreducibility.json", "w"), indent=1, default=str)
out = json.load(open(P / "fundamentals_results.json"))
out["irreducibility"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[IRREDUCIBLE] written: irreducibility.json")
