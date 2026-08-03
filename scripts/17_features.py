"""Build the feature matrix for the fundamentals study.

The question this serves is narrow and specific: does the Tibia Coin price become predictable
once the economy that produces gold is observed, rather than only the price history? Section 4.4
of the report establishes that the level carries a unit root and Section 6.4.3 that a
price-history model loses to a random walk out of sample. This stage assembles the fundamentals
that were unavailable when those conclusions were drawn.

Two disciplines govern everything here.

Leakage. Every feature is computed from information dated strictly before the day it labels.
Rolling statistics are shifted by one day after they are computed, cross-sectional aggregates
are built from the same lagged frame, and the targets are forward returns. A leak in a panel
this wide is easy to introduce and produces spectacular, meaningless results, so the shift is
applied once, centrally, and asserted afterwards.

Alignment. The kill-statistics page reports the trailing day, and 16_killstats.py has already
shifted its dates back by one to reflect that. Nothing here shifts them again.

    python scripts/17_features.py
"""
import json, pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

HORIZONS = (1, 7, 30)
MOVE = 0.02                      # the move size the classification targets ask about

px = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])[
    ["world", "date", "price_gp", "day_sold", "day_bought", "active_traders"]]
ks = pd.read_csv(P / "kill_stats_daily.csv", parse_dates=["date"])
pop = pd.read_csv(P / "population_daily.csv", parse_dates=["date"])
cal = pd.read_csv(P / "event_calendar.csv", parse_dates=["date"])
bw = pd.read_csv(P / "world_summary.csv", parse_dates=["created", "battleye_date"])
mix = pd.read_csv(P / "kill_stats_mix.csv", parse_dates=["date"])
obk = pd.read_csv(P / "order_books.csv")
mreg = pd.read_csv(P / "world_merge_register.csv", parse_dates=["merge_date"])

d = (px.merge(ks, on=["world", "date"], how="inner")
       .merge(pop, on=["world", "date"], how="left")
       .merge(cal, on="date", how="left")
       .merge(bw[["world", "region", "pvp_type", "battleye_protected", "battleye_date",
                  "created", "is_merge_destination", "converged", "transfer_type",
                  "premium_only", "record_online", "guilds", "people_in_guilds",
                  "ach_points", "active_chars", "premium_accounts", "premium_share",
                  "mean_level", "chars_level_100plus", "population", "activity_year"]],
              on="world", how="left")
       .merge(mix, on=["world", "date"], how="left")
       .sort_values(["world", "date"]).reset_index(drop=True))
print(f"joined panel: {len(d):,} world-days, {d.world.nunique()} worlds, "
      f"{d.date.min():%Y-%m-%d} to {d.date.max():%Y-%m-%d}")

d["logp"] = np.log(d.price_gp)
d["ret"] = d.groupby("world", observed=True).logp.diff()
g = d.groupby("world", observed=True)

# ---------------------------------------------------------------- targets
# Forward log returns and the events defined on them. These are the only forward-looking
# quantities in the file.
for h in HORIZONS:
    d[f"y_ret{h}"] = g.logp.shift(-h) - d.logp
    d[f"y_up{h}"] = (d[f"y_ret{h}"] > MOVE).astype(float)
    d[f"y_dn{h}"] = (d[f"y_ret{h}"] < -MOVE).astype(float)
# The relative target. Section 5.2 finds that cross-world *relative* pricing mean-reverts inside
# a band while the common level does not, so a study that only predicts world-level returns tests
# the wrong quantity. This subtracts the market's own forward move, leaving the part the report's
# own results say should carry signal.
# Demeaned within the converged universe, which is the universe the models are fitted on.
# Subtracting the all-worlds mean instead leaves the converged subset with a non-zero average -
# here -2.2% at 30 days - and a constant predictor then scores R2 = 0.36 against a random walk
# purely by reproducing that offset. The benchmark has to be centred on the same sample.
_conv = d.converged.fillna(False).astype(bool)
for h in HORIZONS:
    mkt_h = (d[_conv].groupby("date")[f"y_ret{h}"].mean()
             .reindex(d.date.values).to_numpy())
    d[f"y_rel{h}"] = d[f"y_ret{h}"] - mkt_h

# Realised volatility over the next week, and whether it lands in the top quartile.
d["y_vol7"] = (g.ret.shift(-7).rolling(7, min_periods=5).std()
               .reset_index(level=0, drop=True) * np.sqrt(365))
d["y_hivol7"] = (d.y_vol7 > d.y_vol7.quantile(.75)).astype(float)
TARGETS = [c for c in d.columns if c.startswith("y_")]

# ---------------------------------------------------------------- features
F = {}


def roll(col, w, how="mean"):
    s = d.groupby("world", observed=True)[col]
    r = s.rolling(w, min_periods=max(2, w // 2))
    return getattr(r, how)().reset_index(level=0, drop=True)


# Price history: lags, momentum, dispersion, and the exponentially weighted views of each.
for L in (1, 2, 3, 5, 7, 14, 21):
    F[f"ret_lag{L}"] = g.ret.shift(L - 1)
for w in (7, 14, 30):
    F[f"ret_mean{w}"] = roll("ret", w, "mean")
    F[f"ret_sd{w}"] = roll("ret", w, "std")
    F[f"mom{w}"] = d.logp - g.logp.shift(w)
for hl in (3, 7, 14):
    F[f"ret_ew{hl}"] = (d.groupby("world", observed=True).ret
                        .transform(lambda s: s.ewm(halflife=hl, min_periods=3).mean()))
    F[f"vol_ew{hl}"] = (d.groupby("world", observed=True).ret
                        .transform(lambda s: s.ewm(halflife=hl, min_periods=3).std()))
F["ret_skew30"] = roll("ret", 30, "skew")
F["px_z30"] = (d.logp - roll("logp", 30)) / roll("logp", 30, "std").replace(0, np.nan)
F["dist_ma30"] = d.logp - roll("logp", 30)
F["dist_ma90"] = d.logp - roll("logp", 90)

# Fundamentals. Levels are per-world and vary by orders of magnitude, so everything enters in
# logs or as a ratio; growth rates carry the news.
d["kills_pp"] = d.monsters_killed / d.players_online_avg.clip(lower=1)
d["deaths_pp"] = d.players_killed / d.players_online_avg.clip(lower=1)
d["boss_share"] = d.boss_kills / d.monsters_killed.clip(lower=1)
for c in ("monsters_killed", "players_killed", "boss_kills", "races_hunted",
          "players_online_avg", "kills_pp"):
    F[f"log_{c}"] = np.log(d[c].clip(lower=1))
    for w in (7, 30):
        F[f"g{w}_{c}"] = np.log(d[c].clip(lower=1)) - np.log(
            g[c].shift(w).clip(lower=1))
F["boss_share"] = d.boss_share
F["hunt_hhi"] = d.hunt_hhi
F["top10_share"] = d.top10_share
F["deaths_pp"] = d.deaths_pp
F["death_ratio"] = d.players_killed / d.monsters_killed.clip(lower=1) * 1e4

# Latent economic indices. The fundamentals are collinear by construction - a busier world kills
# more of everything - so the useful signal is what remains after scale is removed. These are
# the first principal components of the standardised growth blocks, formed later in the file
# once the frame is assembled.

# Named economic indices. The brief asks for these by name, and they are constructed rather
# than discovered: each is a stated combination of primitives already in the panel, so they add
# no information - they add an interpretation, which is what makes them testable. If an index
# earns its place in a model, the combination it encodes is the thing that matters.
_act = pd.DataFrame({
    "kills": np.log(d.monsters_killed.clip(lower=1)),
    "online": np.log(d.players_online_avg.clip(lower=1)),
    "breadth": np.log(d.races_hunted.clip(lower=1)),
    "trade": np.log(d.day_sold.fillna(0).clip(lower=0) + 1)})
_actz = ((_act - _act.mean()) / _act.std().replace(0, np.nan)).fillna(0)
# Economic activity: the common factor across how much is being killed, by how many, how
# widely, and how much is then traded.
_u, _sv, _vt = np.linalg.svd(_actz.values - _actz.values.mean(0), full_matrices=False)
F["idx_activity"] = _actz.values @ _vt[0] * np.sign(_vt[0].sum())
# Inflation pressure: gold production growing faster than the players among whom it is shared.
# Positive means more gold per head arriving, which is the mechanism Section 6.1.3 names.
F["idx_inflation_pressure"] = (
    (np.log(d.monsters_killed.clip(lower=1)) - np.log(g.monsters_killed.shift(7).clip(lower=1)))
    - (np.log(d.players_online_avg.clip(lower=1))
       - np.log(g.players_online_avg.shift(7).clip(lower=1))))
# Premium demand: coins absorbed per active player. Coins are bought with gold, so this is the
# demand side of the same transaction the kill statistics describe the supply side of.
F["idx_premium_demand"] = (d.day_bought.fillna(0)
                           / d.players_online_avg.clip(lower=1))
F["idx_premium_demand_7"] = roll("day_bought", 7) / d.players_online_avg.clip(lower=1)

# Liquidity and turnover, from the executed side of the panel.
for c in ("day_sold", "day_bought", "active_traders"):
    F[f"log_{c}"] = np.log(d[c].fillna(0).clip(lower=0) + 1)
    F[f"has_{c}"] = d[c].notna().astype(float)
F["turnover_imb"] = ((d.day_sold - d.day_bought)
                     / (d.day_sold + d.day_bought).replace(0, np.nan))
F["turnover_7"] = roll("day_sold", 7) + roll("day_bought", 7)

# Calendar. Cyclic encodings so December sits next to January rather than eleven months away.
dow, doy, mon = d.date.dt.dayofweek, d.date.dt.dayofyear, d.date.dt.month
F["dow_sin"], F["dow_cos"] = np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)
F["doy_sin"], F["doy_cos"] = np.sin(2 * np.pi * doy / 365), np.cos(2 * np.pi * doy / 365)
F["is_weekend"] = (dow >= 5).astype(float)
F["month"] = mon.astype(float)

# Events, as flags and as distance. A market that anticipates an event responds before it
# starts, so the signed distance to the nearest one is the feature that can show it.
for c in ("ev_xp_skill", "ev_rapid_respawn", "ev_loot", "ev_exaltation", "ev_double_reward",
          "ev_any", "n_events", "update_release"):
    F[c] = d[c].fillna(0).astype(float)
ev_dates = np.sort(cal.loc[cal.ev_any > 0, "date"].unique())
up_dates = np.sort(cal.loc[cal.update_release > 0, "date"].unique())


def signed_distance(dates, marks):
    """Days to the nearest mark; negative before it, positive after."""
    if not len(marks):
        return np.full(len(dates), np.nan)
    i = np.searchsorted(marks, dates)
    prev = np.where(i > 0, (dates - marks[np.clip(i - 1, 0, len(marks) - 1)])
                    / np.timedelta64(1, "D"), np.inf)
    nxt = np.where(i < len(marks), (dates - marks[np.clip(i, 0, len(marks) - 1)])
                   / np.timedelta64(1, "D"), -np.inf)
    return np.where(np.abs(prev) <= np.abs(nxt), prev, nxt)


F["days_to_event"] = signed_distance(d.date.values, ev_dates)
F["days_to_update"] = signed_distance(d.date.values, up_dates)
F["event_soon"] = (F["days_to_event"].clip(-14, 0) / -14.0)

# Structure: where a world is in its own life, and what kind of world it is.
F["world_age"] = (d.date - d.created).dt.days.astype(float)
F["log_age"] = np.log1p(F["world_age"].clip(lower=0))
F["is_merge_dest"] = d.is_merge_destination.astype(float)
F["battleye"] = d.battleye_protected.astype(float)
F["optional_pvp"] = (d.pvp_type == "Optional PvP").astype(float)
for r in ("Europe", "North America", "South America"):
    F[f"region_{r.split()[0].lower()}"] = (d.region == r).astype(float)


# Order book. A single snapshot, so these cannot vary through time - they enter as what they
# are, standing characteristics of a world's market rather than a daily signal.
obk = obk.assign(oc_ratio=obk.order_count_ratio.replace([np.inf, -np.inf], np.nan))
_ob = d[["world"]].merge(
    obk[["world", "quoted_spread_pct", "depth_ratio", "oc_ratio", "bid_depth_tc",
         "ask_depth_tc", "anon_buy", "n_buy_orders", "n_sell_orders"]],
    on="world", how="left")
for c in ("quoted_spread_pct", "depth_ratio", "oc_ratio", "anon_buy"):
    F[f"ob_{c}"] = _ob[c].values
F["ob_log_bid_depth"] = np.log(_ob.bid_depth_tc.clip(lower=1)).values
F["ob_log_ask_depth"] = np.log(_ob.ask_depth_tc.clip(lower=1)).values
F["ob_book_imb"] = ((_ob.n_buy_orders - _ob.n_sell_orders)
                    / (_ob.n_buy_orders + _ob.n_sell_orders).replace(0, np.nan)).values

# World metadata beyond the handful already used. These are the roster and composition measures
# Section 5.3 shows to matter cross-sectionally; they are static per world, so they can separate
# worlds but never time.
for c in ("record_online", "guilds", "people_in_guilds", "ach_points", "active_chars",
          "premium_accounts", "population", "activity_year"):
    F[f"w_log_{c}"] = np.log(d[c].astype(float).clip(lower=1))
F["w_premium_share"] = d.premium_share.astype(float)
F["w_mean_level"] = d.mean_level.astype(float)
F["w_pct_lvl100"] = (d.chars_level_100plus / d.active_chars.clip(lower=1)).astype(float)
F["w_engagement"] = (d.players_online_avg / d.population.clip(lower=1)).astype(float)
F["w_premium_only"] = d.premium_only.astype(float)
# World type in full rather than as one binary, and transfer policy alongside it.
for t in sorted(x for x in d.pvp_type.dropna().unique()):
    F[f"pvp_{t.split()[0].lower()}"] = (d.pvp_type == t).astype(float)
for t in sorted(x for x in d.transfer_type.dropna().unique()):
    F[f"xfer_{str(t).split()[0].lower()}"] = (d.transfer_type == t).astype(float)

# Merges and BattlEye as timing, not just as flags. A merge is an event with a date; how long
# ago it happened is what a market would respond to.
_mg = (mreg.groupby("merge_world").merge_date.max().rename("last_merge")
       .reset_index().rename(columns={"merge_world": "world"}))
_m = d[["world", "date"]].merge(_mg, on="world", how="left")
_dsm = (_m.date - _m.last_merge).dt.days.astype(float)
F["never_merged"] = _dsm.isna().astype(float)
F["days_since_merge"] = _dsm.fillna(9999)
F["merged_recently"] = (_dsm.between(0, 90)).astype(float)
_dsb = (d.date - pd.to_datetime(d.battleye_date, errors="coerce")).dt.days.astype(float)
F["never_battleye"] = _dsb.isna().astype(float)
F["days_since_battleye"] = _dsb.fillna(9999)

# The update windows the calendar already carries, which the first pass ignored.
for c in ("pre_update_7", "pre_update_14", "pre_update_30", "post_update_14",
          "post_update_30"):
    F[c] = d[c].fillna(0).astype(float)

# Hunting mix. The by-monster resolution is 40 creature shares that move together - a world that
# swings toward one high-level spawn swings away from others - so the useful form is a handful
# of latent axes rather than 40 collinear columns.
mixc = [c for c in d.columns if c.startswith("mix_")]
if mixc:
    M = d[mixc].astype(float)
    M = M.fillna(M.median())
    Z = ((M - M.mean()) / M.std().replace(0, np.nan)).fillna(0).values
    # Components from the covariance of the standardised shares; three axes carry the bulk.
    _, _, Vt = np.linalg.svd(Z - Z.mean(0), full_matrices=False)
    for i in range(3):
        F[f"huntmix_pc{i + 1}"] = Z @ Vt[i]
    F["mix_boss_heavy"] = d.boss_share
    print(f"hunting mix: {len(mixc)} creature shares -> 3 latent axes")

FEAT = pd.DataFrame(F, index=d.index)
# ---------------------------------------------------------------- cross-sectional
# Built from lagged inputs so a world's own future never reaches its features through the
# cross-section. Relative premium is the quantity Section 5.2 shows to be predictable.
lag = pd.DataFrame({"world": d.world, "date": d.date,
                    "logp": g.logp.shift(1), "ret": g.ret.shift(1),
                    "kills": np.log(g.monsters_killed.shift(1).clip(lower=1))})
xs = lag.groupby("date")
FEAT["xw_med_logp"] = xs.logp.transform("median")
FEAT["rel_premium"] = lag.logp - FEAT["xw_med_logp"]
FEAT["rel_premium_z"] = FEAT["rel_premium"] / xs.logp.transform("std").replace(0, np.nan)
FEAT["xw_disp"] = xs.logp.transform("std")
FEAT["breadth_up"] = xs.ret.transform(lambda s: (s > 0).mean())
FEAT["xw_ret"] = xs.ret.transform("mean")
FEAT["beta_gap"] = lag.ret - FEAT["xw_ret"]
FEAT["xw_kills"] = xs.kills.transform("mean")
FEAT["rel_kills"] = lag.kills - FEAT["xw_kills"]

# Interactions worth naming: the report's own findings say activity matters conditional on
# world type, and that events act through hunting rather than directly.
FEAT["kills_x_event"] = FEAT["g7_monsters_killed"] * FEAT["ev_any"]
FEAT["kills_x_pvp"] = FEAT["g7_monsters_killed"] * FEAT["optional_pvp"]
FEAT["premium_x_disp"] = FEAT["rel_premium"] * FEAT["xw_disp"]
FEAT["vol_x_breadth"] = FEAT["ret_sd14"] * FEAT["breadth_up"]

# ---------------------------------------------------------------- the single shift
# Everything above is computed on the day it describes. One shift moves the whole block back by
# a day, so a row labelled D carries only what was knowable at the end of D-1.
NO_SHIFT = {"dow_sin", "dow_cos", "doy_sin", "doy_cos", "is_weekend", "month",
            "world_age", "log_age", "is_merge_dest", "battleye", "optional_pvp",
            "region_europe", "region_north", "region_south",
            "days_to_event", "days_to_update", "event_soon"}
shift_cols = [c for c in FEAT.columns if c not in NO_SHIFT]
FEAT[shift_cols] = FEAT.groupby(d.world, observed=True)[shift_cols].shift(1)

out = pd.concat([d[["world", "date", "price_gp", "logp", "ret", "converged", "region",
                    "pvp_type"]], FEAT, d[TARGETS]], axis=1)

# ---------------------------------------------------------------- leakage assertion
# A feature that has seen the future correlates with a forward return far more strongly than
# anything in this market plausibly could. Checking is cheap; being wrong is not.
chk = out[out.converged].dropna(subset=["y_ret1"])
worst = max(((c, abs(chk[c].corr(chk.y_ret1))) for c in FEAT.columns
             if chk[c].notna().sum() > 500), key=lambda kv: kv[1])
print(f"strongest |corr(feature, next-day return)|: {worst[0]} = {worst[1]:.3f}")
assert worst[1] < 0.25, f"{worst[0]} looks like a leak at r={worst[1]:.3f}"

out.to_csv(P / "fundamentals_panel.csv", index=False,
          float_format="%.7g")   # float32 precision; halves the file
meta = {"n_rows": int(len(out)), "n_worlds": int(out.world.nunique()),
        "start": str(out.date.min().date()), "end": str(out.date.max().date()),
        "n_features": len(FEAT.columns), "features": sorted(FEAT.columns),
        "targets": TARGETS, "horizons": list(HORIZONS), "move_threshold": MOVE,
        "n_converged": int(out[out.converged].world.nunique()),
        "max_abs_corr_feature_vs_next_return": float(worst[1]),
        "max_abs_corr_feature": worst[0]}
json.dump(meta, open(P / "fundamentals_meta.json", "w"), indent=1)
print(f"[FEATURES] {len(FEAT.columns)} features, {len(TARGETS)} targets, "
      f"{len(out):,} rows -> fundamentals_panel.csv")
