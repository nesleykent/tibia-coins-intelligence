"""Main analysis engine. Writes results.json + supporting CSVs consumed by the report."""
import json, pathlib, sys, warnings
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.stattools import adfuller, kpss, acf
from statsmodels.stats.diagnostic import acorr_ljungbox

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from econ import ols, fmt, nw_hac

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"
R = {}

panel = pd.read_csv(P / "panel_daily.csv", parse_dates=["date", "created"])
meta = pd.read_csv(P / "world_metadata.csv", parse_dates=["created", "first_obs", "last_obs"])
cal = pd.read_csv(P / "event_calendar.csv", parse_dates=["date"])
pop = pd.read_csv(P / "population_daily.csv", parse_dates=["date"])
merge = pd.read_csv(P / "world_merge_register.csv", parse_dates=["merge_date"])
# Population sources, and why they are not interchangeable.
#   TibiaVIP "Total" is the world's full character roster. It is the population measure.
#   The GuildStats census counts only indexed, higher-level characters: it never exceeds the
#   TibiaVIP total, and the share it captures falls from ~79% on a world created this year to
#   ~4% on Antica. That coverage rate is strongly age-dependent, so using the census as
#   population would inject measurement error correlated with world age and with the BattlEye
#   cohort. It is retained instead as a measure of the ACTIVE, high-level sub-population.
# The two sources agree almost exactly where they overlap (guild counts: Pearson 0.9997,
# 72/93 exact matches, all 93 within +/-3; region 93/93), so this is a definitional
# difference rather than a disagreement about the underlying tibia.com data.
census = pd.read_csv(P / "world_census.csv")
vip = pd.read_csv(ROOT / "data" / "raw" / "tibiavip_worlds.tsv", sep="\t", header=None,
                  names=["world", "vip_online", "vip_total", "vip_guilds",
                         "vip_region", "vip_prot"])

panel = panel.merge(cal, on="date", how="left")
# Concurrent players online is an ACTIVITY flow, not a population stock. It is named and
# treated as such throughout; the population stock enters the cross-section separately below.
panel = panel.merge(pop.rename(columns={"players_online_avg": "activity_online"}),
                    on=["world", "date"], how="left")
panel["log_activity"] = np.log(panel["activity_online"].where(panel["activity_online"] > 0))

CONV = panel[panel["converged"]].copy()
R["window"] = {"start": str(panel.date.min().date()), "end": str(panel.date.max().date()),
               "n_worlds": int(panel.world.nunique()), "n_world_days": int(len(panel)),
               "n_converged": int(CONV.world.nunique()),
               "n_launch": int(meta.launch_in_window.sum()),
               "n_merge_dest_in_window": int((meta.created_in_window & meta.is_merge_destination).sum())}

# ============================================================ 12. descriptives
last = panel.sort_values("date").groupby("world").tail(1)
R["desc"] = {
    "price_latest_median": float(last.price_gp.median()),
    "price_latest_min": float(last.price_gp.min()),
    "price_latest_max": float(last.price_gp.max()),
    "price_latest_mean": float(last.price_gp.mean()),
    "cs_sd_pct_latest": float(np.log(last.price_gp).std() * 100),
    "ret_sd_daily_pct": float(CONV.ret.std() * 100),
    "ret_sd_ann_pct": float(CONV.ret.std() * np.sqrt(365) * 100),
    "median_obs_per_world": float(panel.groupby("world").size().median()),
}
by_world = (panel.groupby("world")
            .agg(n_obs=("price_gp", "size"), first=("date", "min"), last=("date", "max"),
                 px_first=("price_gp", "first"), px_last=("price_gp", "last"),
                 px_med=("price_gp", "median"), px_min=("price_gp", "min"),
                 px_max=("price_gp", "max"), vol=("ret", lambda s: s.std() * 100),
                 sold=("tc_sold", "median"), bought=("tc_bought", "median"),
                 lots_sold=("txn_sold", "median"))
            .reset_index())
by_world = by_world.merge(meta[["world", "region", "pvp_type", "battleye_protected", "battleye_date",
                                "transfer_type", "created", "is_merge_destination",
                                "launch_in_window", "premium_only", "record_online",
                                "guilds", "people_in_guilds", "ach_points"]], on="world")
by_world["converged"] = by_world["world"].isin(CONV.world.unique())
# Activity: mean concurrent players online over the trailing year (a flow).
by_world["activity_year"] = by_world["world"].map(
    pop[pop.date > pop.date.max() - pd.Timedelta(days=365)].groupby("world")["players_online_avg"].mean())
# Population: the true resident character count from the GuildStats census (a stock).
# Guild membership is retained as a corroborating partial stock.
by_world = by_world.merge(
    census[["world", "population", "premium_accounts", "free_accounts", "premium_share",
            "mean_level", "median_level", "chars_level_100plus", "pct_level_100plus"]]
    .rename(columns={"population": "active_chars"}), on="world", how="left")
by_world = by_world.merge(vip[["world", "vip_total", "vip_guilds"]], on="world", how="left")
by_world["population"] = by_world["vip_total"]          # full character roster
by_world["active_share"] = by_world["active_chars"] / by_world["population"]
by_world["guilded_share"] = by_world["people_in_guilds"] / by_world["population"]
by_world["total_ret_pct"] = (by_world.px_last / by_world.px_first - 1) * 100
by_world.to_csv(P / "world_summary.csv", index=False)

# ============================================================ 13. indices
# The archive's cross-sectional coverage grows over the window (a median of 1 world per date
# in 2023 rising to 85 in 2026), so a level index built from a changing basket confounds price
# change with composition change. The headline index is therefore CHAIN-LINKED: each day's
# index return is the mean return across worlds observed on both that day and the previous
# day, which is invariant to entry and exit. The naive basket mean is retained for comparison.
MIN_XW = 10          # minimum worlds on a date for any cross-world statistic

piv = CONV.pivot_table(index="date", columns="world", values="log_price")
idx = pd.DataFrame({"date": piv.index})
idx["n_worlds"] = piv.notna().sum(axis=1).values
idx["basket_log"] = piv.mean(axis=1).values
idx["basket_price"] = np.exp(idx["basket_log"])

dlog = piv.diff()
valid_pair = piv.notna() & piv.shift(1).notna()
idx["chain_ret"] = dlog.where(valid_pair).mean(axis=1).values
idx["n_pairs"] = valid_pair.sum(axis=1).values
first_ok = int(np.argmax(idx["n_worlds"].values >= MIN_XW))
cr = idx["chain_ret"].copy()
cr.iloc[:first_ok + 1] = np.nan
base = float(idx["basket_price"].iloc[first_ok])
idx["ew_log"] = np.log(base) + cr.fillna(0).cumsum()
idx.loc[:first_ok, "ew_log"] = np.nan
idx["ew_price"] = np.exp(idx["ew_log"])
idx["index_valid"] = idx["n_worlds"] >= MIN_XW
qty = CONV.pivot_table(index="date", columns="world", values="txn_sold").reindex_like(piv)
w = qty.div(qty.sum(axis=1), axis=0)
idx["vw_log"] = (piv * w).sum(axis=1, min_count=1).values
idx["vw_price"] = np.exp(idx["vw_log"])
idx["disp_pct"] = (piv.std(axis=1) * 100).where(idx["n_worlds"].values >= MIN_XW).values
idx["breadth_up"] = (piv.diff() > 0).sum(axis=1).values / idx["n_worlds"]
idx.to_csv(P / "market_index.csv", index=False)

iv = idx[idx.index_valid & idx.ew_price.notna()]
span_days = (iv.date.iloc[-1] - iv.date.iloc[0]).days
R["index"] = {
    "min_worlds_required": MIN_XW,
    "index_start": str(iv.date.iloc[0].date()), "index_end": str(iv.date.iloc[-1].date()),
    "first_ew": float(iv.ew_price.iloc[0]), "last_ew": float(iv.ew_price.iloc[-1]),
    "total_pct": float((iv.ew_price.iloc[-1] / iv.ew_price.iloc[0] - 1) * 100),
    "cagr_pct": float(((iv.ew_price.iloc[-1] / iv.ew_price.iloc[0]) **
                       (365.25 / span_days) - 1) * 100),
    "peak": float(iv.ew_price.max()), "peak_date": str(iv.loc[iv.ew_price.idxmax(), "date"].date()),
    "trough": float(iv.ew_price.min()), "trough_date": str(iv.loc[iv.ew_price.idxmin(), "date"].date()),
    "mean_disp_pct": float(idx.disp_pct.mean()),
    "vw_last": float(idx.vw_price.dropna().iloc[-1]),
    "coverage_by_year": {int(y): {"world_days": int(g.size), "worlds": int(g.nunique())}
                         for y, g in panel.groupby(panel.date.dt.year)["world"]},
    "median_worlds_per_date_by_year": {
        int(y): float(v) for y, v in
        panel.groupby([panel.date.dt.year, "date"]).world.nunique().groupby(level=0).median().items()},
}
dd = idx.set_index("date")["ew_price"]
R["index"]["max_drawdown_pct"] = float(((dd / dd.cummax()) - 1).min() * 100)
R["index"]["max_dd_date"] = str(((dd / dd.cummax()) - 1).idxmin().date())

# ============================================================ 14/15. trend + TS properties
ts_rows = []
for wname, g in CONV.groupby("world"):
    s = g.set_index("date")["log_price"].asfreq("D").interpolate(limit=1).dropna()
    if len(s) < 250:
        continue
    try:
        a = adfuller(s, autolag="AIC")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            kp = kpss(s, regression="c", nlags="auto")
        r = s.diff().dropna()
        lb = acorr_ljungbox(r, lags=[10], return_df=True)
        ts_rows.append({"world": wname, "adf_stat": a[0], "adf_p": a[1],
                        "kpss_stat": kp[0], "kpss_p": kp[1],
                        "lb_stat": float(lb["lb_stat"].iloc[0]), "lb_p": float(lb["lb_pvalue"].iloc[0]),
                        "ret_sd_pct": r.std() * 100, "ret_ac1": r.autocorr(1),
                        "n": len(s)})
    except Exception:
        pass
ts = pd.DataFrame(ts_rows)
ts.to_csv(P / "stationarity.csv", index=False)
R["stationarity"] = {
    "n": len(ts),
    "adf_reject_5pct": int((ts.adf_p < 0.05).sum()),
    "adf_p_min": float(ts.adf_p.min()), "adf_p_max": float(ts.adf_p.max()),
    "adf_p_median": float(ts.adf_p.median()),
    "kpss_reject_5pct": int((ts.kpss_p < 0.05).sum()),
    "lb_reject_5pct": int((ts.lb_p < 0.05).sum()),
    "mean_ac1": float(ts.ret_ac1.mean()),
}

# ============================================================ 16. seasonality
CONV["dow"] = CONV["date"].dt.dayofweek
CONV["month"] = CONV["date"].dt.month
dow = CONV.groupby("dow")["ret"].agg(["mean", "std", "size"])
dow["mean_pct"] = dow["mean"] * 100
dow["t"] = dow["mean"] / (dow["std"] / np.sqrt(dow["size"]))
dow.to_csv(P / "seasonality_dow.csv")
mon = CONV.groupby("month")["ret"].agg(["mean", "std", "size"])
mon["mean_pct"] = mon["mean"] * 100
mon["t"] = mon["mean"] / (mon["std"] / np.sqrt(mon["size"]))
mon.to_csv(P / "seasonality_month.csv")
r_dow = ols(CONV.assign(**{f"dow{i}": (CONV.dow == i).astype(float) for i in range(1, 7)}),
            "ret", [f"dow{i}" for i in range(1, 7)], fe=["world"], cluster=["world", "date"])
R["seasonality"] = {
    "dow_pct": {int(k): float(v) for k, v in dow["mean_pct"].items()},
    "dow_joint_maxabs_t": float(np.nanmax(np.abs(r_dow["t"]))),
    "month_pct": {int(k): float(v) for k, v in mon["mean_pct"].items()},
    "best_month": int(mon["mean_pct"].idxmax()), "worst_month": int(mon["mean_pct"].idxmin()),
}

# ============================================================ 17. event studies
EV = ["ev_xp_skill", "ev_rapid_respawn", "ev_loot", "ev_exaltation"]
WIN = ["pre_update_14", "pre_update_30", "pre_update_7", "post_update_14", "post_update_30"]
ev_res = {}
EVCOLS = EV + ["pre_update_14", "post_update_30"]
for spec, fe in [("world_fe", ["world"]), ("world_date_fe", ["world", "date"])]:
    if "date" in fe:
        # Every event flag is global (no world dimension), so after absorbing date fixed
        # effects each flag is identically zero: the coefficients are NOT identified. Verify
        # that directly and report it as such rather than reporting numerical noise.
        from econ import absorb
        Z = absorb(CONV.dropna(subset=["ret"] + EVCOLS), EVCOLS, fe)
        resid_sd = {c: float(Z[c].std()) for c in EVCOLS}
        ev_res[spec] = {"identified": False,
                        "max_residual_sd_after_absorbing_date_fe": max(resid_sd.values()),
                        "residual_sd": resid_sd,
                        "note": "All event indicators are global; date fixed effects absorb "
                                "them completely. No event coefficient is identified in this "
                                "specification."}
        continue
    r = ols(CONV, "ret", EVCOLS, fe=fe, cluster=["world", "date"])
    ev_res[spec] = {n: {"coef_pct": float(b * 100), "se_pct": float(s * 100), "p": float(p)}
                    for n, (b, s, p) in r["coef"].items()}
    ev_res[spec]["_n"] = r["n"]
# raw contrasts
raw = {}
for e in EV:
    a, b = CONV.loc[CONV[e] == 1, "ret"], CONV.loc[CONV[e] == 0, "ret"]
    m1, s1 = nw_hac(a.dropna().values)
    raw[e] = {"on_pct": float(a.mean() * 100), "off_pct": float(b.mean() * 100),
              "diff_pct": float((a.mean() - b.mean()) * 100),
              "t": float(stats.ttest_ind(a.dropna(), b.dropna(), equal_var=False).statistic),
              "p": float(stats.ttest_ind(a.dropna(), b.dropna(), equal_var=False).pvalue),
              "n_on": int(a.notna().sum())}
ev_res["raw_contrast"] = raw
# H4: alternative pre-update windows
altw = {}
for lo in [7, 14, 21, 30]:
    col = f"pre_update_{lo}" if f"pre_update_{lo}" in CONV.columns else None
    if col is None:
        continue
    r = ols(CONV, "ret", [col], fe=["world"], cluster=["world", "date"])
    b, s, p = r["coef"][col]
    altw[f"pre_{lo}d"] = {"coef_pct": float(b * 100), "se_pct": float(s * 100), "p": float(p)}
for hi in [14, 30]:
    col = f"post_update_{hi}"
    r = ols(CONV, "ret", [col], fe=["world"], cluster=["world", "date"])
    b, s, p = r["coef"][col]
    altw[f"post_{hi}d"] = {"coef_pct": float(b * 100), "se_pct": float(s * 100), "p": float(p)}
ev_res["alt_windows"] = altw
R["events"] = ev_res

# ============================================================ 18/19. integration + arbitrage
CONV = CONV.sort_values(["world", "date"])
# A "deviation from the cross-world mean" is only meaningful once enough worlds are observed
# on a date. Dates carrying fewer than MIN_XW converged worlds are excluded from every
# cross-world statistic; in early 2023 the archive often observes a single world per date.
n_on_date = CONV.groupby("date")["world"].transform("nunique")
dmean = CONV.groupby("date")["log_price"].transform("mean")
CONV["dev"] = (CONV["log_price"] - dmean).where(n_on_date >= MIN_XW)
R["window"]["dates_dropped_thin_cross_section"] = int((n_on_date < MIN_XW).sum())
R["window"]["xw_start"] = str(CONV.loc[CONV.dev.notna(), "date"].min().date())
CONV["dev_lag"] = CONV.groupby("world")["dev"].shift(1)
CONV["absdev"] = CONV["dev"].abs()
CONV["absdev_lag"] = CONV["absdev"].shift(1).where(CONV.groupby("world")["date"].diff().dt.days == 1)
CONV["closure_pp"] = (CONV["absdev_lag"] - CONV["absdev"]) * 100      # +ve = gap narrowed

bins = [0, 2, 4, 6, 10, np.inf]
labels = ["0-2%", "2-4%", "4-6%", "6-10%", ">10%"]
CONV["gap_bin"] = pd.cut(CONV["absdev_lag"] * 100, bins=bins, labels=labels, right=False)


def band_table(d):
    out = []
    for lab in labels:
        s = d.loc[d.gap_bin == lab, "closure_pp"].dropna()
        if len(s) < 30:
            out.append({"bin": lab, "n": len(s), "closure_pp": np.nan, "se": np.nan, "p": np.nan})
            continue
        m, se = nw_hac(s.values)
        out.append({"bin": lab, "n": int(len(s)), "closure_pp": float(m), "se": float(se),
                    "p": float(2 * stats.norm.sf(abs(m / se))) if se and se > 0 else np.nan})
    return pd.DataFrame(out)


band = band_table(CONV)
band.to_csv(P / "arbitrage_band.csv", index=False)
R["arbitrage"] = {"pooled": band.to_dict("records")}

# H3: sub-sample stability of the threshold
subs = {}
CONV["yr"] = CONV["date"].dt.year
for name, mask in [
    ("2023", CONV.yr == 2023), ("2024", CONV.yr == 2024),
    ("2025", CONV.yr == 2025), ("2026", CONV.yr == 2026),
    ("Europe", CONV.region == "Europe"), ("North America", CONV.region == "North America"),
    ("South America", CONV.region == "South America"),
    ("Open PvP", CONV.pvp_type == "Open PvP"), ("Optional PvP", CONV.pvp_type == "Optional PvP"),
    ("large worlds", CONV.activity_online > CONV.activity_online.median()),
    ("small worlds", CONV.activity_online <= CONV.activity_online.median()),
]:
    t = band_table(CONV[mask])
    # threshold = first bin whose lower edge exceeds the sign change from - to +
    pos = t.dropna(subset=["closure_pp"])
    thr = None
    for i in range(len(pos)):
        if pos.iloc[i]["closure_pp"] > 0:
            thr = pos.iloc[i]["bin"]
            break
    subs[name] = {"table": t.to_dict("records"), "first_positive_bin": thr,
                  "n": int(mask.sum())}
R["arbitrage"]["subsamples"] = subs

# Half-life of the deviation.
# The daily price is a noisy estimate of the true daily level (mean of executed trades on a
# thin book), so a one-day AR(1) suffers classical attenuation: the estimated persistence is
# biased toward zero and the implied half-life is biased short. Two diagnostics and two
# corrections are reported rather than a single number.
hl = ols(CONV.assign(dev_lag2=CONV.dev_lag), "dev", ["dev_lag2"], fe=["world"], cluster=["world", "date"])
b_hl = hl["coef"]["dev_lag2"][0]

hl_h = {}
for h in [1, 2, 5, 10, 20, 30, 60]:
    d2 = CONV.copy()
    d2["dev_fwd"] = d2.groupby("world")["dev"].shift(-h)
    d2["dgap"] = d2.groupby("world")["date"].shift(-h) - d2["date"]
    d2 = d2[d2["dgap"] == pd.Timedelta(days=h)]
    rh = ols(d2, "dev_fwd", ["dev"], fe=["world"], cluster=["world", "date"])
    bh = rh["coef"]["dev"][0]
    hl_h[h] = {"rho_h": float(bh), "n": rh["n"],
               "implied_half_life_days": float(h * np.log(0.5) / np.log(abs(bh)))
               if 0 < abs(bh) < 1 else np.nan}

# weekly-averaged deviations: averaging 7 daily observations cuts the noise variance ~7x
wk = (CONV.set_index("date").groupby("world")["dev"].resample("W").mean().reset_index()
      .rename(columns={"dev": "dev_w"}))
wk["dev_w_lag"] = wk.groupby("world")["dev_w"].shift(1)
rw = ols(wk, "dev_w", ["dev_w_lag"], fe=["world"], cluster=["world"])
bw = rw["coef"]["dev_w_lag"][0]

R["integration"] = {
    "ar1_dev": float(b_hl),
    "half_life_days": float(np.log(0.5) / np.log(abs(b_hl))) if 0 < abs(b_hl) < 1 else np.nan,
    "half_life_by_horizon": hl_h,
    "ar1_weekly": float(bw),
    "half_life_weekly_days": float(7 * np.log(0.5) / np.log(abs(bw))) if 0 < abs(bw) < 1 else np.nan,
    "mean_return_ac1": float(ts.ret_ac1.mean()),
    "mean_dispersion_pct": float(idx.disp_pct.mean()),
    "median_dispersion_pct": float(idx.disp_pct.median()),
    "dispersion_last": float(idx.disp_pct.iloc[-1]),
}
rr = CONV.pivot_table(index="date", columns="world", values="ret")
cc = rr.corr().where(~np.eye(rr.shape[1], dtype=bool))
R["integration"]["mean_pairwise_ret_corr"] = float(np.nanmean(cc.values))
lp = piv.corr().where(~np.eye(piv.shape[1], dtype=bool))
R["integration"]["mean_pairwise_level_corr"] = float(np.nanmean(lp.values))

# ---- Market fee schedule, measured against the live order books -------------
# Documented mechanic: each offer costs 2% of its value, floored at 20 GP and CAPPED at
# 1,000,000 GP. The cap makes the effective rate fall with offer size, so "the round-trip
# fee" is not a single number: it is 4% only for offers small enough that the cap does not
# bind. Quantified here so Section 19 can state which traders face which cost.
# Coins also trade in lots: an offer is placed in multiples of 25 units, so no quantity between
# them exists and the smallest possible trade is 25 TC. The constraint is verified against the
# live book below rather than assumed, and it matters because a threshold expressed in coins is
# only reachable at the next lot boundary above it.
FEE_RATE, FEE_CAP, FEE_MIN, QTY_CAP, LOT = 0.02, 1_000_000, 20, 64_000, 25
lo = pd.read_csv(P / "live_offers.csv")
_off_lot = int((lo.amount % LOT != 0).sum())
assert _off_lot == 0, f"{_off_lot} of {len(lo)} live offers are not multiples of {LOT}"
lo["fee_uncapped"] = FEE_RATE * lo.value
lo["fee_actual"] = np.minimum(np.maximum(lo.fee_uncapped, FEE_MIN), FEE_CAP)
lo["eff_rate_pct"] = lo.fee_actual / lo.value * 100
bind_value = FEE_CAP / FEE_RATE
med_px = float(lo.price.median())
dec = lo.assign(d=pd.qcut(lo.amount, 10, labels=False, duplicates="drop")).groupby("d")
R["fees"] = {
    "rate_pct": FEE_RATE * 100, "cap_gp": FEE_CAP, "min_gp": FEE_MIN,
    "qty_cap": QTY_CAP,
    "max_offer_observed_tc": int(lo.amount.max()),
    "offers_at_qty_cap": int((lo.amount == QTY_CAP).sum()),
    "offers_above_qty_cap": int((lo.amount > QTY_CAP).sum()),
    "cap_binds_above_value_gp": float(bind_value),
    "cap_binds_above_tc": float(bind_value / med_px),
    # The exact threshold is not a tradeable size. Rounding up to the next lot gives the
    # smallest offer a trader can actually place at which the cap bites.
    "lot_size": LOT,
    "offers_on_lot": int((lo.amount % LOT == 0).sum()),
    "min_trade_tc": LOT,
    "min_trade_value_gp": float(LOT * med_px),
    "cap_binds_at_lot_tc": float(-(-(bind_value / med_px) // LOT) * LOT),
    "n_at_fee_floor": int((lo.fee_uncapped < FEE_MIN).sum()),
    "share_at_fee_floor": float((lo.fee_uncapped < FEE_MIN).mean()),
    "min_offer_value_gp": float(lo.value.min()),
    "median_quoted_price": med_px,
    "share_capped_by_count": float((lo.fee_uncapped > FEE_CAP).mean()),
    "share_capped_by_value": float(lo.loc[lo.fee_uncapped > FEE_CAP, "value"].sum() / lo.value.sum()),
    "share_capped_by_tc": float(lo.loc[lo.fee_uncapped > FEE_CAP, "amount"].sum() / lo.amount.sum()),
    "n_offers": int(len(lo)),
    "roundtrip_by_decile": [
        {"median_tc": float(a), "roundtrip_pct": float(2 * b)}
        for a, b in zip(dec.amount.median(), dec.eff_rate_pct.median())],
    "roundtrip_small_pct": 4.0,
    "roundtrip_largest_decile_pct": float(2 * dec.eff_rate_pct.median().iloc[-1]),
}
R["arbitrage"]["fee_roundtrip_pct"] = 4.0
print(f"[FEES] lot size {LOT} TC verified on {len(lo):,} live offers; cap binds above "
      f"{bind_value / med_px:,.0f} TC, reachable at {R['fees']['cap_binds_at_lot_tc']:,.0f} TC")

# ============================================================ 20. world type / region / population
xw = by_world[by_world.converged].copy()
xw["log_px"] = np.log(xw.px_last)
xw["optional_pvp"] = (xw.pvp_type == "Optional PvP").astype(float)
xw["be_release"] = (xw.battleye_date.astype(str) == "release").astype(float)
xw["age_y"] = (panel.date.max() - xw.created).dt.days / 365.25
xw["log_pop"] = np.log(xw.population)          # resident stock
xw["log_act"] = np.log(xw.activity_year)       # concurrent flow
xw["log_ach"] = np.log(xw.ach_points)          # cumulative stock, corroborating
xw["log_guilded"] = np.log(xw.people_in_guilds)  # partial stock, corroborating
xw["log_active"] = np.log(xw.active_chars)     # indexed high-level characters
xw["active_share"] = xw.active_share           # share of the roster still active
xw["premium_share"] = xw.premium_share         # share of characters on premium accounts
xw["mean_level"] = xw.mean_level
xw["log_lvl"] = np.log(xw.mean_level)
# Engagement: concurrent players per resident character. Population counts every character
# ever created on the world, including long-dormant ones; activity counts who actually logs
# in. Their ratio separates a world's headcount from how live that headcount is.
xw["engagement"] = xw.activity_year / xw.population
xw["log_engagement"] = np.log(xw.engagement)
xw["premium"] = xw.premium_only.astype(float)
for reg in ["North America", "South America", "Oceania"]:
    xw[f"reg_{reg[:2]}"] = (xw.region == reg).astype(float)
regs = [c for c in xw.columns if c.startswith("reg_")]

models = {}
models["type_only"] = ols(xw, "log_px", ["optional_pvp", "be_release"], cluster=[])
models["type_age"] = ols(xw, "log_px", ["optional_pvp", "be_release", "age_y"], cluster=[])
models["type_age_pop"] = ols(xw, "log_px", ["optional_pvp", "be_release", "age_y", "log_pop"], cluster=[])
models["type_age_pop_act"] = ols(xw, "log_px",
                                 ["optional_pvp", "be_release", "age_y", "log_pop", "log_act"],
                                 cluster=[])
models["census"] = ols(xw, "log_px",
                       ["optional_pvp", "be_release", "log_pop", "premium_share", "log_lvl"],
                       cluster=[])
models["engagement"] = ols(xw, "log_px",
                           ["optional_pvp", "be_release", "log_engagement"], cluster=[])
models["engagement_full"] = ols(xw, "log_px",
                                ["optional_pvp", "be_release", "log_engagement", "log_pop",
                                 "premium_share"], cluster=[])
models["roster_vs_active"] = ols(xw, "log_px",
                                 ["optional_pvp", "be_release", "log_pop", "active_share"],
                                 cluster=[])
models["full"] = ols(xw, "log_px",
                     ["optional_pvp", "be_release", "age_y", "log_pop", "log_act",
                      "premium_share", "log_lvl", "premium"] + regs, cluster=[])
R["cross_section"] = {k: {n: {"coef": float(b), "se": float(s), "p": float(p)}
                          for n, (b, s, p) in v["coef"].items()} | {"_n": v["n"], "_r2": v["r2_within"]}
                      for k, v in models.items()}
# BattlEye / vintage confounding
a = xw.loc[xw.be_release == 1, "age_y"]
b = xw.loc[xw.be_release == 0, "age_y"]
R["cross_section"]["be_age_confound"] = {
    "median_age_release": float(a.median()), "median_age_retrofit": float(b.median()),
    "mw_p": float(stats.mannwhitneyu(a, b).pvalue), "n_release": int(len(a)), "n_retrofit": int(len(b))}

# panel population term with the true daily series (H1)
pan = CONV.dropna(subset=["log_activity"]).copy()
pan["log_qty_lag"] = np.log(pan.groupby("world")["txn_sold"].shift(1).where(lambda s: s > 0))
pan["log_act_lag"] = pan.groupby("world")["log_activity"].shift(1)
panel_specs = {}
panel_specs["dev_only_wfe"] = ols(pan, "ret", ["dev_lag"], fe=["world"], cluster=["world", "date"])
panel_specs["dev_only_wdfe"] = ols(pan, "ret", ["dev_lag"], fe=["world", "date"], cluster=["world", "date"])
panel_specs["dev_qty"] = ols(pan, "ret", ["dev_lag", "log_qty_lag"], fe=["world"], cluster=["world", "date"])
panel_specs["dev_qty_pop"] = ols(pan, "ret", ["dev_lag", "log_qty_lag", "log_act_lag"],
                                 fe=["world"], cluster=["world", "date"])
panel_specs["dev_qty_pop_wdfe"] = ols(pan, "ret", ["dev_lag", "log_qty_lag", "log_act_lag"],
                                      fe=["world", "date"], cluster=["world", "date"])
# one-way vs two-way clustering comparison (H2)
cmp_cl = {}
for nm, cl in [("none", []), ("world", ["world"]), ("date", ["date"]), ("two-way", ["world", "date"])]:
    rr2 = ols(pan, "ret", ["dev_lag"], fe=["world"], cluster=cl)
    b, s, p = rr2["coef"]["dev_lag"]
    cmp_cl[nm] = {"coef": float(b), "se": float(s), "p": float(p), "t": float(b / s)}
R["panel"] = {k: {n: {"coef": float(b), "se": float(s), "p": float(p)}
                  for n, (b, s, p) in v["coef"].items()} | {"_n": v["n"], "_clusters": v["clusters"]}
              for k, v in panel_specs.items()}
R["panel"]["clustering_comparison"] = cmp_cl

# level-on-population cross-section using corrected vs snapshot measures
sm = pd.read_csv(P / "population_summary.csv")
xw2 = xw.merge(sm[["world", "snapshot_online"]], on="world", how="left")
xw2["log_snap"] = np.log(xw2.snapshot_online.where(xw2.snapshot_online > 0))
pop_cmp = {}
for nm, col in [("full_roster_tibiavip", "log_pop"),
                ("active_chars_census", "log_active"),
                ("guild_membership_stock", "log_guilded"),
                ("achievement_points_stock", "log_ach"),
                ("concurrent_activity_daily_avg", "log_act"),
                ("concurrent_activity_instant", "log_snap")]:
    rr3 = ols(xw2, "log_px", [col, "optional_pvp", "be_release"], cluster=[])
    b, s, p = rr3["coef"][col]
    pop_cmp[nm] = {"coef": float(b), "se": float(s), "p": float(p), "n": rr3["n"]}
R["cross_section"]["population_measure_comparison"] = pop_cmp
R["cross_section"]["engagement_stats"] = {
    "median": float((xw.activity_year / xw.population).median()),
    "min": float((xw.activity_year / xw.population).min()),
    "max": float((xw.activity_year / xw.population).max()),
    "spearman_pop_vs_activity_levels": [float(v) for v in
        stats.spearmanr(xw.population, xw.activity_year)],
}
R["cross_section"]["census"] = {
    "roster_total": int(vip.vip_total.sum()),
    "roster_median": float(vip.vip_total.median()),
    "roster_min": float(vip.vip_total.min()),
    "roster_max": float(vip.vip_total.max()),
    "active_total": int(census.population.sum()),
    "median_active_share": float(by_world.active_share.median()),
    "active_share_min": float(by_world.active_share.min()),
    "active_share_max": float(by_world.active_share.max()),
    "spearman_activeshare_vs_age": [float(v) for v in stats.spearmanr(
        by_world.active_share, (panel.date.max() - by_world.created).dt.days, nan_policy="omit")],
    "guild_agreement_pearson": float(np.corrcoef(by_world.vip_guilds.fillna(0),
                                                 by_world.guilds.fillna(0))[0, 1]),
    "guild_exact_matches": int((by_world.vip_guilds == by_world.guilds).sum()),
    "total_characters": int(census.population.sum()),
    "median_population": float(vip.vip_total.median()),
    "min_population": float(vip.vip_total.min()),
    "max_population": float(vip.vip_total.max()),
    "median_premium_share": float(census.premium_share.median()),
    "premium_share_range": [float(census.premium_share.min()), float(census.premium_share.max())],
    "median_guilded_share": float(by_world.guilded_share.median()),
    "median_mean_level": float(census.mean_level.median()),
    "spearman_pop_vs_guilded": [float(v) for v in
        stats.spearmanr(by_world.population, by_world.people_in_guilds, nan_policy="omit")],
    "spearman_roster_vs_active": [float(v) for v in stats.spearmanr(
        by_world.population, by_world.active_chars, nan_policy="omit")],
}
rat = (xw.population / xw.activity_year)
R["cross_section"]["stock_vs_flow"] = {
    "spearman_pop_vs_activity": [float(v) for v in stats.spearmanr(xw.population, xw.activity_year)],
    "residents_per_concurrent_median": float(rat.median()),
    "residents_per_concurrent_by_region": {k: float(v) for k, v in
                                           rat.groupby(xw.region).median().items()},
    "population_median": float(xw.population.median()),
    "activity_median": float(xw.activity_year.median()),
}

# ============================================================ 21. young worlds
launch = panel[panel.launch_in_window].copy()
launch["age_d"] = (launch.date - launch.created).dt.days
lc = (launch[launch.age_d.between(0, 400)]
      .assign(bucket=lambda d: (d.age_d // 10) * 10)
      .groupby("bucket")["price_gp"].agg(["median", "size"]).reset_index())
lc.to_csv(P / "launch_curve.csv", index=False)
mdest = meta[meta.created_in_window & meta.is_merge_destination]
lfirst = meta[meta.launch_in_window]
R["young"] = {
    "n_launch": int(len(lfirst)), "n_merge_dest": int(len(mdest)),
    "launch_first_price_median": float(by_world[by_world.launch_in_window].px_first.median()),
    "launch_first_price_min": float(by_world[by_world.launch_in_window].px_first.min()),
    "launch_first_price_max": float(by_world[by_world.launch_in_window].px_first.max()),
    "mergedest_first_price_median": float(by_world[by_world.world.isin(mdest.world)].px_first.median()),
    "mergedest_first_price_min": float(by_world[by_world.world.isin(mdest.world)].px_first.min()),
    "mergedest_first_price_max": float(by_world[by_world.world.isin(mdest.world)].px_first.max()),
    "mergedest_median_age_at_first_obs": float(mdest.age_at_first_obs_days.median()),
    "launch_median_age_at_first_obs": float(lfirst.age_at_first_obs_days.median()),
    "mw_p": float(stats.mannwhitneyu(by_world[by_world.launch_in_window].px_first,
                                     by_world[by_world.world.isin(mdest.world)].px_first).pvalue),
}
# convergence: days until within 5% of cross-world mean
convd = []
for wname, g in launch.groupby("world"):
    g = g.sort_values("date")
    dm = idx.set_index("date")["ew_log"].reindex(g.date).values
    gap = np.abs(g.log_price.values - dm)
    ok = np.where(gap < 0.05)[0]
    if len(ok):
        convd.append({"world": wname, "days_to_5pct": int(g.age_d.values[ok[0]]),
                      "first_price": float(g.price_gp.iloc[0])})
cvd = pd.DataFrame(convd)
cvd.to_csv(P / "launch_convergence.csv", index=False)
R["young"]["median_days_to_within_5pct"] = float(cvd.days_to_5pct.median()) if len(cvd) else np.nan
R["young"]["n_converged_launches"] = int(len(cvd))

# ============================================================ 22. merge / transfers
tr = pd.read_csv(P / "world_transfers.csv", parse_dates=["change_date"])
R["merge"] = {
    "n_merges": int(merge.merge_world.nunique()),
    "n_predecessors": int(len(merge)),
    "first": str(merge.merge_date.min().date()), "last": str(merge.merge_date.max().date()),
    "pre_merge_obs_available": 0,
    "transfers_n": int(len(tr)),
    "transfers_window": f"{tr.change_date.min().date()} to {tr.change_date.max().date()}",
    "transfers_days": int((tr.change_date.max() - tr.change_date.min()).days + 1),
    "transfer_top_dest": tr.current_world.value_counts().head(8).to_dict(),
    "transfer_top_origin": tr.former_world.value_counts().head(8).to_dict(),
}
# net flow vs price level
nf = (tr.current_world.value_counts().rename("inflow").to_frame()
      .join(tr.former_world.value_counts().rename("outflow"), how="outer").fillna(0))
nf["net"] = nf.inflow - nf.outflow
nf = nf.join(by_world.set_index("world")[["px_last", "region"]], how="inner")
if len(nf) > 5:
    rho, pv = stats.spearmanr(nf.net, np.log(nf.px_last))
    R["merge"]["transfer_net_vs_price_spearman"] = {"rho": float(rho), "p": float(pv), "n": int(len(nf))}
nf.reset_index(names="world").to_csv(P / "transfer_flows.csv", index=False)

# merge-wave price behaviour of successors (2025-11-06 wave)
wave = merge[merge.merge_date == merge.merge_date.max()].merge_world.unique().tolist()
wv = panel[panel.world.isin(wave)].sort_values(["world", "date"])
R["merge"]["wave_2025_11_06"] = {
    "worlds": wave,
    "first_price_median": float(wv.groupby("world").price_gp.first().median()),
    "first_obs_dates": {w: str(g.date.min().date()) for w, g in wv.groupby("world")},
}

# ============================================================ 23. microstructure
boards = []
for f in sorted((ROOT / "data" / "raw" / "market_board").glob("*.json")):
    d = json.load(open(f))
    s = pd.DataFrame(d["sellers"]); b = pd.DataFrame(d["buyers"])
    rec = {"world": f.stem, "n_sell_orders": len(s), "n_buy_orders": len(b),
           "update_time": d.get("update_time")}
    if len(s):
        rec |= {"best_ask": s.price.min(), "ask_depth_tc": s.amount.sum(),
                "anon_sell": (s.name_ if False else (s["name"] == "Anonymous").mean())}
    if len(b):
        rec |= {"best_bid": b.price.max(), "bid_depth_tc": b.amount.sum(),
                "anon_buy": (b["name"] == "Anonymous").mean(),
                "buy_orders_below_2000": int((b.price < 2000).sum()),
                "buy_depth_below_2000": int(b.loc[b.price < 2000, "amount"].sum())}
    boards.append(rec)
bd = pd.DataFrame(boards)
bd["mid"] = (bd.best_ask + bd.best_bid) / 2
bd["quoted_spread_pct"] = (bd.best_ask - bd.best_bid) / bd["mid"] * 100
bd["order_count_ratio"] = bd.n_buy_orders / bd.n_sell_orders
bd["depth_ratio"] = bd.bid_depth_tc / bd.ask_depth_tc
bd.to_csv(P / "order_books.csv", index=False)
R["micro"] = {
    "n_worlds": int(len(bd)),
    "quoted_spread_median_pct": float(bd.quoted_spread_pct.median()),
    "quoted_spread_iqr": [float(bd.quoted_spread_pct.quantile(.25)), float(bd.quoted_spread_pct.quantile(.75))],
    "executed_gap_median_pct": float(CONV.executed_gap_pct.median()),
    "executed_gap_mean_pct": float(CONV.executed_gap_pct.mean()),
    "median_buy_orders": float(bd.n_buy_orders.median()),
    "median_sell_orders": float(bd.n_sell_orders.median()),
    "median_orders_below_2000": float(bd.buy_orders_below_2000.median()),
    "share_buy_orders_below_2000": float((bd.buy_orders_below_2000 / bd.n_buy_orders).median()),
    "anon_share_buy": float(bd.anon_buy.median()), "anon_share_sell": float(bd.anon_sell.median()),
    "median_bid_depth_tc": float(bd.bid_depth_tc.median()),
    "median_ask_depth_tc": float(bd.ask_depth_tc.median()),
    "corr_ordercount_vs_depth_ratio": float(bd[["order_count_ratio", "depth_ratio"]].corr().iloc[0, 1]),
    "day_lowest_buy_median": float(panel.day_lowest_buy.median()),
    "antica_spread_pct": float(bd.loc[bd.world == "Antica", "quoted_spread_pct"].iloc[0]),
    "antica_ask": float(bd.loc[bd.world == "Antica", "best_ask"].iloc[0]),
    "antica_bid": float(bd.loc[bd.world == "Antica", "best_bid"].iloc[0]),
    "antica_executed_gap": float(CONV.loc[CONV.world == "Antica", "executed_gap_pct"].median()),
}
# liquidity vs volatility / spread
liq = by_world[by_world.converged].dropna(subset=["sold", "vol"])
R["micro"]["spearman_turnover_vol"] = [float(x) for x in stats.spearmanr(liq.sold, liq.vol)]
bdc = bd.merge(by_world[["world", "vol", "sold", "converged", "population", "activity_year", "premium_share"]], on="world")
bdc = bdc[bdc.converged]
R["micro"]["spearman_spread_turnover"] = [float(x) for x in
    stats.spearmanr(bdc.quoted_spread_pct, bdc.sold, nan_policy="omit")]
R["micro"]["spearman_spread_pop"] = [float(x) for x in
    stats.spearmanr(bdc.quoted_spread_pct, bdc.population, nan_policy="omit")]

# turnover: report sides separately (never summed)
R["micro"]["turnover"] = {
    # Transaction counts, not coins. The coin figure is bounded below at 25x the count.
    "median_sold_per_day": float(CONV.txn_sold.median()),
    "median_bought_per_day": float(CONV.txn_bought.median()),
    "total_sold_window": float(CONV.txn_sold.sum()),
    "total_bought_window": float(CONV.txn_bought.sum()),
    "lot_size": 25,
    "median_tc_sold_per_day": float(CONV.tc_sold.median()),
    "median_tc_bought_per_day": float(CONV.tc_bought.median()),
    "total_tc_sold_window": float(CONV.tc_sold.sum()),
    "total_tc_bought_window": float(CONV.tc_bought.sum()),
    "units_note": ("day_sold and day_bought are counts of 25-coin lots, so coin volume is "
                   "25x the field; order-book amounts are already coins"),
}

# ============================================================ 24. technical indicators
tech_rows = []
for wname, g in panel.groupby("world"):
    g = g.sort_values("date").set_index("date")["price_gp"].asfreq("D").interpolate(limit=1)
    if g.notna().sum() < 120:
        continue
    ma50, ma200 = g.rolling(50).mean(), g.rolling(200).mean()
    d = g.diff()
    up = d.clip(lower=0).rolling(14).mean()
    dn = (-d.clip(upper=0)).rolling(14).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    sd = g.rolling(20).std()
    tech_rows.append({"world": wname, "price": g.dropna().iloc[-1],
                      "ma50": ma50.dropna().iloc[-1] if ma50.notna().any() else np.nan,
                      "ma200": ma200.dropna().iloc[-1] if ma200.notna().any() else np.nan,
                      "rsi14": rsi.dropna().iloc[-1] if rsi.notna().any() else np.nan,
                      "bb_z": float((g.iloc[-1] - g.rolling(20).mean().iloc[-1]) / sd.iloc[-1])
                      if sd.notna().any() and sd.iloc[-1] > 0 else np.nan})
tech = pd.DataFrame(tech_rows)
tech["above_ma50"] = tech.price > tech.ma50
tech["above_ma200"] = tech.price > tech.ma200
tech["golden_cross"] = tech.ma50 > tech.ma200
tech.to_csv(P / "technicals.csv", index=False)
R["technical"] = {
    "n": int(len(tech)),
    "pct_above_ma50": float(tech.above_ma50.mean() * 100),
    "pct_above_ma200": float(tech.above_ma200.mean() * 100),
    "pct_golden_cross": float(tech.golden_cross.mean() * 100),
    "median_rsi": float(tech.rsi14.median()),
    "n_rsi_over70": int((tech.rsi14 > 70).sum()), "n_rsi_under30": int((tech.rsi14 < 30).sum()),
}

# ============================================================ 25. valuation anchors
imeta = json.load(open(ROOT / "data" / "raw" / "tm_item_metadata.json"))
im = pd.DataFrame(imeta) if isinstance(imeta, list) else pd.DataFrame(imeta.get("items", []))
tc = im[im["id"] == 22118] if "id" in im.columns else pd.DataFrame()
R["valuation"] = {"tc_metadata": tc.to_dict("records")[0] if len(tc) else {},
                  "n_items_metadata": int(len(im))}
npc = None
if "npc_buy" in im.columns:
    def _mx(v):
        try:
            return max([x.get("price", 0) for x in v]) if isinstance(v, list) and v else np.nan
        except Exception:
            return np.nan
    im["npc_sell_max"] = im["npc_sell"].apply(_mx) if "npc_sell" in im.columns else np.nan
    im["npc_buy_max"] = im["npc_buy"].apply(_mx)
    npc = im[["id", "name", "npc_buy_max", "npc_sell_max"]].dropna(subset=["npc_buy_max"])
    npc.to_csv(P / "npc_prices.csv", index=False)
    R["valuation"]["n_items_with_npc_buy"] = int(len(npc))

# ============================================================ 30. robustness
rob = {}
alt = CONV.copy()
for nm, col in [("headline_mean_executed", "price_gp"), ("quantity_weighted", "price_vw"),
                ("order_book_mid", "price_book_mid"), ("sell_side_only", "px_sell")]:
    a = alt.dropna(subset=[col]).copy()
    a["lp"] = np.log(a[col])
    a["dv"] = a["lp"] - a.groupby("date")["lp"].transform("mean")
    a["dvl"] = a.groupby("world")["dv"].shift(1)
    a["rt"] = a.groupby("world")["lp"].diff()
    r4 = ols(a, "rt", ["dvl"], fe=["world"], cluster=["world", "date"])
    b, s, p = r4["coef"]["dvl"]
    rob[nm] = {"coef": float(b), "se": float(s), "p": float(p), "n": r4["n"],
               "mean_dev_from_headline_pct": float(((a[col] - a.price_gp).abs() / a.price_gp * 100).mean())}
rob["outlier_filter"] = {}
R["robustness"] = rob

# subsample stability of the deviation coefficient
ss = {}
for nm, m in [("2023", CONV.yr == 2023), ("2024", CONV.yr == 2024), ("2025", CONV.yr == 2025),
              ("2026", CONV.yr == 2026), ("Europe", CONV.region == "Europe"),
              ("North America", CONV.region == "North America"),
              ("South America", CONV.region == "South America")]:
    sub = CONV[m]
    if sub.world.nunique() < 3 or len(sub) < 500:
        continue
    r5 = ols(sub, "ret", ["dev_lag"], fe=["world"], cluster=["world", "date"])
    b, s, p = r5["coef"]["dev_lag"]
    ss[nm] = {"coef": float(b), "se": float(s), "p": float(p), "n": r5["n"]}
R["robustness"]["dev_subsamples"] = ss

CONV.to_csv(P / "converged_panel.csv", index=False)
json.dump(R, open(P / "results.json", "w"), indent=1, default=str)

print("=" * 70)
print("window:", R["window"])
print("\nARBITRAGE BAND (pooled, converged worlds)")
print(band.to_string(index=False))
print("\nhalf-life (days):", round(R["integration"]["half_life_days"], 1),
      "| AR(1)", round(R["integration"]["ar1_dev"], 4),
      "| mean dispersion %", round(R["integration"]["mean_dispersion_pct"], 2))
print("\nSTATIONARITY:", R["stationarity"])
print("\nCLUSTERING COMPARISON (dev_lag, world FE):")
for k, v in cmp_cl.items():
    print(f"  {k:<9} coef {v['coef']:+.4f}  se {v['se']:.4f}  t {v['t']:+.2f}  p {v['p']:.3g}")
print("\nEVENTS (world FE):", json.dumps(ev_res["world_fe"], indent=1, default=str)[:600])
print("\nCROSS-SECTION full:", json.dumps(R["cross_section"]["type_age_pop"], indent=1, default=str))
print("\nPOP MEASURE COMPARISON:", json.dumps(pop_cmp, indent=1))
print("\nMICRO:", json.dumps({k: R["micro"][k] for k in list(R["micro"])[:12]}, indent=1, default=str))
