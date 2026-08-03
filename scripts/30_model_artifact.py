"""Fit, persist and expose the predictive model as something a reader can actually run.

Every model in this study so far has been fitted, scored and discarded. That is enough to answer
a research question and not enough to hand over. This stage produces three artefacts: the fitted
model, the metadata needed to reproduce and audit it, and a callable that turns a current panel
row into a prediction with a calibrated interval.

What is shipped is deliberately the modest one. Section 6.6.7a establishes that the forecastable
quantity is a world's deviation from the cross-world mean, not the price level, and Section 6.6
that the level is beaten out of sample only at one and seven days, by a few percent of
variance, and not at all by thirty. So the artefact predicts the deviation,
carries a conformal interval whose coverage was measured rather than assumed, and refuses to
emit a level forecast at all.

    python scripts/30_model_artifact.py            # fit and save
    python scripts/30_model_artifact.py --predict  # score the latest observation per world
"""
import json, pathlib, pickle, sys

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

ROOT = pathlib.Path(__file__).resolve().parents[1]
P, MODELS = ROOT / "data" / "processed", ROOT / "models"
MODELS.mkdir(exist_ok=True)
ART = MODELS / "deviation_model.pkl"
RNG, H, MIN_XW = 12345, 7, 10

R = json.load(open(P / "results.json"))
THR = R["advanced"]["tar"]["threshold_pct"] / 100

FEATURES = ["dev_l", "absdev", "outside", "dev_x_out", "dev_sq", "mom5", "mom21",
            "vol14", "dev_ma21", "dev_sd21", "xw_disp", "dev_rank"]


def build_panel():
    """The feature frame the model expects, from the cleaned price panel alone."""
    pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
    bw = pd.read_csv(P / "world_summary.csv")
    d = pan[pan.world.isin(set(bw.query("converged").world))][
        ["world", "date", "price_gp"]].dropna().copy()
    d["logp"] = np.log(d.price_gp)
    n_on = d.groupby("date").world.transform("size")
    d["dev"] = (d.logp - d.groupby("date").logp.transform("mean")).where(n_on >= MIN_XW)
    d = d.dropna(subset=["dev"]).sort_values(["world", "date"]).reset_index(drop=True)
    g = d.groupby("world", observed=True)
    d["y"] = g.dev.shift(-H) - d.dev
    d["dev_l"] = g.dev.shift(1)
    d["absdev"] = d.dev_l.abs()
    d["outside"] = (d.absdev > THR).astype(float)
    d["dev_x_out"] = d.dev_l * d.outside
    d["dev_sq"] = d.dev_l * d.absdev
    d["mom5"] = g.logp.shift(1) - g.logp.shift(6)
    d["mom21"] = g.logp.shift(1) - g.logp.shift(22)
    d["vol14"] = g.logp.diff().shift(1).rolling(14).std().reset_index(level=0, drop=True)
    d["dev_ma21"] = g.dev.shift(1).rolling(21).mean().reset_index(level=0, drop=True)
    d["dev_sd21"] = g.dev.shift(1).rolling(21).std().reset_index(level=0, drop=True)
    d["xw_disp"] = d.groupby("date").dev_l.transform("std")
    d["dev_rank"] = d.groupby("date").dev_l.rank(pct=True)
    return d


def fit_and_save():
    d = build_panel()
    fit = d.dropna(subset=FEATURES + ["y"])
    dates = np.sort(fit.date.unique())
    cut = int(len(dates) * 0.85)
    # Held back purely to calibrate the interval; the model never sees it during fitting.
    cal_from = dates[cut]
    tr = fit[fit.date < dates[cut - H]]
    cal = fit[fit.date >= cal_from]
    m = RandomForestRegressor(n_estimators=400, min_samples_leaf=40, max_features=0.6,
                              random_state=RNG, n_jobs=-1).fit(tr[FEATURES].values, tr.y.values)
    resid = np.abs(cal.y.values - m.predict(cal[FEATURES].values))
    q = {str(a): float(np.quantile(resid, 1 - a)) for a in (0.5, 0.2, 0.1)}
    cov = {str(a): float(np.mean(resid <= np.quantile(resid, 1 - a))) for a in (0.5, 0.2, 0.1)}

    art = {"model": m, "features": FEATURES, "horizon_days": H, "band_threshold": THR,
           "conformal_halfwidth": q, "calibration_coverage": cov,
           "feature_medians": fit[FEATURES].median().to_dict(),
           "trained_to": str(pd.Timestamp(tr.date.max()).date()),
           "calibrated_from": str(pd.Timestamp(cal_from).date()),
           "n_train": int(len(tr)), "n_calibration": int(len(cal)),
           "target": f"change in a world's deviation from the cross-world mean, {H} days "
                     f"ahead, in log points",
           "refuses": "level forecasts - Section 6.6.2 finds the level unforecastable"}
    with open(ART, "wb") as f:
        pickle.dump(art, f)
    print(f"[MODEL] trained on {len(tr):,} rows to {art['trained_to']}, "
          f"calibrated on {len(cal):,} from {art['calibrated_from']}")
    for a in ("0.5", "0.2", "0.1"):
        print(f"  {(1 - float(a)) * 100:.0f}% interval: +/-{q[a] * 100:.2f} log points "
              f"(measured coverage {cov[a]:.1%})")
    print(f"[MODEL] saved to {ART.relative_to(ROOT)} ({ART.stat().st_size / 1024:.0f} KB)")
    return art


def predict_latest():
    """Score every world's most recent observation and rank by expected convergence."""
    with open(ART, "rb") as f:
        art = pickle.load(f)
    d = build_panel()
    last = (d.dropna(subset=art["features"]).sort_values("date")
            .groupby("world").tail(1).copy())
    yhat = art["model"].predict(last[art["features"]].values)
    hw = art["conformal_halfwidth"]["0.2"]
    out = pd.DataFrame({
        "world": last.world.values, "as_of": last.date.dt.date.values,
        "price_gp": last.price_gp.values,
        "deviation_pct": last.dev_l.values * 100,
        "outside_band": last.outside.values.astype(bool),
        "predicted_change_pct": yhat * 100,
        "low80_pct": (yhat - hw) * 100, "high80_pct": (yhat + hw) * 100})
    out = out.sort_values("predicted_change_pct")
    out.to_csv(P / "latest_predictions.csv", index=False)
    print(f"\n[PREDICT] {art['horizon_days']}-day change in relative position, 80% interval "
          f"+/-{hw * 100:.2f} points, {len(out)} worlds")
    print(out.head(5).round(3).to_string(index=False))
    print("  ...")
    print(out.tail(5).round(3).to_string(index=False))
    print("\nThis predicts relative position only. The report gives no level forecast.")
    return out


if __name__ == "__main__":
    if "--predict" in sys.argv and ART.exists():
        predict_latest()
    else:
        fit_and_save()
        predict_latest()
