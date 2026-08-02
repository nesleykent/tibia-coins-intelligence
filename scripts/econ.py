"""Estimation utilities: fixed-effect absorption and multi-way clustered standard errors.

Two-way (world and date) clustering follows Cameron, Gelbach & Miller (2011):
    V = V_world + V_date - V_(world x date)
with the small-sample correction G/(G-1) * (N-1)/(N-K) applied per dimension. The result is
projected to the nearest positive semi-definite matrix if the subtraction leaves a negative
eigenvalue (a known finite-sample possibility with the CGM estimator).

Fixed effects are absorbed by alternating within-transformations rather than dummy
expansion: world+date FE would otherwise need ~1,390 dummy columns.
"""
import numpy as np
import pandas as pd
from scipy import stats


def absorb(df, cols, fe_cols, tol=1e-10, maxiter=200):
    """Demean `cols` with respect to the fixed effects in `fe_cols` (alternating projections)."""
    X = df[cols].astype(float).copy()
    if not fe_cols:
        return X
    for _ in range(maxiter):
        max_shift = 0.0
        for fe in fe_cols:
            m = X.groupby(df[fe].values).transform("mean")
            max_shift = max(max_shift, float(np.abs(m.to_numpy()).max()))
            X = X - m
        if max_shift < tol:
            break
    return X


def _meat(X, u, g):
    """Sum over clusters of (X_g' u_g)(X_g' u_g)'."""
    Xu = X * u[:, None]
    df = pd.DataFrame(Xu)
    S = df.groupby(np.asarray(g)).sum().to_numpy()
    return S.T @ S, S.shape[0]


def _psd(V):
    w, Q = np.linalg.eigh((V + V.T) / 2)
    if (w < 0).any():
        w = np.clip(w, 0, None)
        V = Q @ np.diag(w) @ Q.T
    return V


def ols(df, y, xs, fe=(), cluster=(), add_const=True):
    """OLS with absorbed FE and (multi-way) clustered SEs. Returns a tidy result dict."""
    d = df.dropna(subset=[y] + list(xs) + list(fe) + list(cluster)).copy()
    cols = [y] + list(xs)
    Z = absorb(d, cols, list(fe))
    yv = Z[y].to_numpy()
    X = Z[list(xs)].to_numpy()
    names = list(xs)
    if add_const and not fe:
        X = np.column_stack([np.ones(len(X)), X])
        names = ["const"] + names

    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ (X.T @ yv)
    u = yv - X @ beta
    n, k = X.shape
    k_eff = k + sum(d[f].nunique() for f in fe)          # FE consume degrees of freedom

    if not cluster:
        s2 = (u @ u) / max(n - k_eff, 1)
        V = s2 * XtX_inv
        G_report = None
    else:
        parts, Gs = [], []
        for dim in cluster:
            M, G = _meat(X, u, d[dim].to_numpy())
            c = (G / max(G - 1, 1)) * ((n - 1) / max(n - k_eff, 1))
            parts.append(c * XtX_inv @ M @ XtX_inv)
            Gs.append(G)
        V = sum(parts)
        if len(cluster) > 1:                              # subtract the intersection terms
            inter = d[list(cluster)].astype(str).agg("|".join, axis=1).to_numpy()
            M, G = _meat(X, u, inter)
            c = (G / max(G - 1, 1)) * ((n - 1) / max(n - k_eff, 1))
            V = V - c * XtX_inv @ M @ XtX_inv
        V = _psd(V)
        G_report = Gs

    se = np.sqrt(np.diag(V))
    dof = (min(Gs) - 1) if cluster else max(n - k_eff, 1)
    t = beta / np.where(se > 0, se, np.nan)
    p = 2 * stats.t.sf(np.abs(t), dof)
    tss = float(((yv - yv.mean()) ** 2).sum())
    return {"names": names, "beta": beta, "se": se, "t": t, "p": p, "n": n,
            "r2_within": 1 - float(u @ u) / tss if tss > 0 else np.nan,
            "clusters": G_report, "dof": dof,
            "coef": {nm: (b, s, pp) for nm, b, s, pp in zip(names, beta, se, p)}}


def fmt(res, keep=None):
    rows = []
    for nm, b, s, t, p in zip(res["names"], res["beta"], res["se"], res["t"], res["p"]):
        if keep and nm not in keep:
            continue
        rows.append({"term": nm, "coef": b, "se": s, "t": t, "p": p,
                     "sig": "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""})
    return pd.DataFrame(rows)


def nw_hac(x, lags=None):
    """Newey-West HAC standard error of a sample mean (for serially correlated series)."""
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return np.nan, np.nan
    if lags is None:
        lags = int(np.floor(4 * (n / 100) ** (2 / 9)))
    e = x - x.mean()
    g0 = (e @ e) / n
    s = g0
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        s += 2 * w * (e[L:] @ e[:-L]) / n
    return x.mean(), np.sqrt(max(s, 0) / n)
