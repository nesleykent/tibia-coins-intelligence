"""Neural sequence models: an LSTM and a small time-series transformer.

Earlier sections declined to fit these on the grounds that 238 daily observations per world is
far short of what they need. That reasoning is sound but it is an argument, not evidence, and
the brief asks for the models. They are fitted here so the claim can be checked rather than
asserted - and so that if they do work, the study finds out.

The design is deliberately modest, because the alternative is to tune until something looks
good on the test set. Both models see the same 30-day windows of the same features, are trained
with early stopping on a validation slice carved from the end of the training window, and are
evaluated on exactly the folds 18_predict.py used. No hyperparameter search is run; the
architectures are the smallest that could plausibly work at this sample size.

    python scripts/24_deep.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from scipy import stats

warnings.filterwarnings("ignore")
torch.manual_seed(12345)
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
DEV = "cpu"
LOOK = 30          # days of history each sequence sees
H = 7
FOLDS = 4
EPOCHS = 60

d = pd.read_csv(P / "fundamentals_panel.csv", parse_dates=["date"])
meta = json.load(open(P / "fundamentals_meta.json"))
# A compact feature set: sequence models on this sample cannot absorb 140 channels, and the
# selection is the economically named block rather than a search over which ones help.
SEQ = [c for c in ["ret", "ret_sd14", "mom30", "rel_premium", "rel_premium_z", "xw_disp",
                   "breadth_up", "log_monsters_killed", "g7_monsters_killed",
                   "log_players_online_avg", "boss_share", "idx_activity", "turnover_imb",
                   "days_to_event", "dow_sin", "dow_cos"] if c in d.columns]
d = d[d.converged].sort_values(["world", "date"]).reset_index(drop=True)
TGT = f"y_rel{H}"
_new = {}
print(f"panel {len(d):,} rows, {d.world.nunique()} worlds, {len(SEQ)} sequence channels")


def build(frame):
    """Stack per-world sliding windows; a window never spans two worlds."""
    X, y, dt = [], [], []
    for _, g in frame.groupby("world", sort=False):
        g = g.sort_values("date")
        a = g[SEQ].to_numpy().astype(np.float32)
        t = g[TGT].to_numpy().astype(np.float32)
        dates = g.date.values
        ok = np.isfinite(a).all(axis=1)
        for i in range(LOOK, len(g)):
            if not np.isfinite(t[i]) or not ok[i - LOOK:i].all():
                continue
            X.append(a[i - LOOK:i])
            y.append(t[i])
            dt.append(dates[i])
    if not X:
        return None
    return np.stack(X), np.array(y), np.array(dt)


class LSTMNet(nn.Module):
    def __init__(self, n_in, hidden=32):
        super().__init__()
        self.rnn = nn.LSTM(n_in, hidden, num_layers=1, batch_first=True)
        self.head = nn.Sequential(nn.Dropout(0.2), nn.Linear(hidden, 1))

    def forward(self, x):
        o, _ = self.rnn(x)
        return self.head(o[:, -1]).squeeze(-1)


class TSTransformer(nn.Module):
    """A single encoder block with learned positional embeddings - the smallest transformer
    that is still a transformer, which is what this sample size can support."""

    def __init__(self, n_in, dmodel=32, heads=4):
        super().__init__()
        self.proj = nn.Linear(n_in, dmodel)
        self.pos = nn.Parameter(torch.zeros(1, LOOK, dmodel))
        layer = nn.TransformerEncoderLayer(dmodel, heads, dim_feedforward=64, dropout=0.2,
                                           batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, num_layers=1)
        self.head = nn.Linear(dmodel, 1)

    def forward(self, x):
        h = self.enc(self.proj(x) + self.pos)
        return self.head(h.mean(dim=1)).squeeze(-1)


def train_eval(Model, Xtr, ytr, Xte, yte):
    n_val = max(64, int(len(Xtr) * 0.15))
    Xv, yv = Xtr[-n_val:], ytr[-n_val:]
    Xf, yf = Xtr[:-n_val], ytr[:-n_val]
    mu, sd = Xf.reshape(-1, Xf.shape[-1]).mean(0), Xf.reshape(-1, Xf.shape[-1]).std(0) + 1e-8
    ysd = yf.std() + 1e-9
    to = lambda a: torch.tensor((a - mu) / sd, dtype=torch.float32, device=DEV)
    Xf_, Xv_, Xte_ = to(Xf), to(Xv), to(Xte)
    yf_ = torch.tensor(yf / ysd, dtype=torch.float32, device=DEV)
    yv_ = torch.tensor(yv / ysd, dtype=torch.float32, device=DEV)

    net = Model(Xtr.shape[-1]).to(DEV)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-4)
    lossf = nn.MSELoss()
    best, best_state, patience = np.inf, None, 0
    idx = np.arange(len(Xf_))
    for ep in range(EPOCHS):
        net.train()
        np.random.shuffle(idx)
        for s in range(0, len(idx), 256):
            b = idx[s:s + 256]
            opt.zero_grad()
            lossf(net(Xf_[b]), yf_[b]).backward()
            nn.utils.clip_grad_norm_(net.parameters(), 1.0)
            opt.step()
        net.eval()
        with torch.no_grad():
            v = lossf(net(Xv_), yv_).item()
        if v < best - 1e-5:
            best, best_state, patience = v, {k: t.clone() for k, t in net.state_dict().items()}, 0
        else:
            patience += 1
            if patience >= 8:
                break
    if best_state:
        net.load_state_dict(best_state)
    net.eval()
    with torch.no_grad():
        return net(Xte_).cpu().numpy() * ysd


def dm(e1, e2, h=H):
    dd = e1 ** 2 - e2 ** 2
    dd = dd[np.isfinite(dd)]
    if len(dd) < 30:
        return np.nan
    lags = max(1, h - 1)
    s = dd.var(ddof=0) + 2 * sum((1 - k / (lags + 1)) * np.cov(dd[k:], dd[:-k], ddof=0)[0, 1]
                                 for k in range(1, lags + 1))
    return float(dd.mean() / np.sqrt(s / len(dd))) if s > 0 else np.nan


built = build(d)
if built is None:
    raise SystemExit("no sequences could be built")
X, y, dt = built
print(f"sequences: {len(X):,} windows of {LOOK} days")

order = np.argsort(dt)
X, y, dt = X[order], y[order], dt[order]
udates = np.unique(dt)
edges = np.linspace(int(len(udates) * 0.5), len(udates), FOLDS + 1).astype(int)

rows = []
for k in range(FOLDS):
    tr_end, te_end = edges[k], edges[k + 1]
    if te_end - tr_end < 3:
        continue
    # Purge the horizon so a training label cannot overlap the test window.
    tr_mask = dt < udates[max(0, tr_end - H)]
    te_mask = (dt >= udates[tr_end]) & (dt < udates[min(te_end, len(udates) - 1)])
    if tr_mask.sum() < 800 or te_mask.sum() < 100:
        continue
    Xtr, ytr, Xte, yte = X[tr_mask], y[tr_mask], X[te_mask], y[te_mask]
    for name, Model in (("LSTM", LSTMNet), ("Transformer", TSTransformer)):
        pred = train_eval(Model, Xtr, ytr, Xte, yte)
        e, e_rw = pred - yte, -yte
        rows.append({"fold": k, "model": name, "n_train": int(len(Xtr)),
                     "n_test": int(len(Xte)),
                     "rmse": float(np.sqrt(np.mean(e ** 2))),
                     "r2_oos": float(1 - np.sum(e ** 2) / np.sum(yte ** 2)),
                     "dir_acc": float(np.mean(np.sign(pred) == np.sign(yte))),
                     "dm_t_vs_rw": dm(e_rw, e)})
        print(f"  fold {k} {name:12} R² {rows[-1]['r2_oos']:+.4f}  "
              f"dir {rows[-1]['dir_acc']:.3f}")
    rows.append({"fold": k, "model": "RandomWalk", "n_train": int(len(Xtr)),
                 "n_test": int(len(Xte)),
                 "rmse": float(np.sqrt(np.mean(yte ** 2))), "r2_oos": 0.0,
                 "dir_acc": 0.0, "dm_t_vs_rw": np.nan})

deep = pd.DataFrame(rows)
deep.to_csv(P / "deep_models.csv", index=False)
agg = []
for m, g in deep.groupby("model"):
    z = g.dm_t_vs_rw.dropna().values
    zc = z.sum() / np.sqrt(len(z)) if len(z) else np.nan
    agg.append({"model": m, "r2_oos": g.r2_oos.mean(), "dir_acc": g.dir_acc.mean(),
                "rmse": g.rmse.mean(), "folds": len(g),
                "folds_better": int((g.dm_t_vs_rw > 0).sum()),
                "dm_z": float(zc) if np.isfinite(zc) else np.nan,
                "dm_p": float(2 * (1 - stats.norm.cdf(abs(zc)))) if np.isfinite(zc) else np.nan})
ds = pd.DataFrame(agg).sort_values("r2_oos", ascending=False)
ds.to_csv(P / "deep_summary.csv", index=False)
print("\n[DEEP]"); print(ds.to_string(index=False))

_new["deep_models"] = {"summary": ds.to_dict("records"), "lookback": LOOK,
                      "channels": SEQ, "n_sequences": int(len(X)), "folds": FOLDS,
                      "epochs_max": EPOCHS}
# Re-read here, not at import: a long stage must not overwrite work that
# finished while it was running.
RES = json.load(open(P / "fundamentals_results.json"))
RES |= _new
json.dump(RES, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[DEEP] written: deep_models, deep_summary")
