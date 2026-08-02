"""Generate every figure in the Tableau-style system defined in chartstyle.py.

Each figure carries a title, a subtitle stating units, axis labels, a legend or direct
labels, and a source line with date range and a note on exclusions/transformations. Layout
bands are reserved explicitly so no text can overlap another element.
"""
import json, pathlib, sys, warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from matplotlib.ticker import NullLocator
from chartstyle import (T10, SEQ, INK, MUTED, FAINT, GRID, CONTEXT, gpfmt, pctfmt,
                        hgrid, label_line, note_box, clean_log, log_ticks_within,
                        bar_labels, bullet_chart, heatmap, finish, LEG_FS, HAIR,
                        W_LIGHT, W_TITLE, ACCENT, NEUTRAL, BG)

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P, FIG = ROOT / "data" / "processed", ROOT / "figures"
FIG.mkdir(exist_ok=True)
(FIG / "sa").mkdir(exist_ok=True)

panel = pd.read_csv(P / "panel_daily.csv", parse_dates=["date", "created"])
idx = pd.read_csv(P / "market_index.csv", parse_dates=["date"])
bw = pd.read_csv(P / "world_summary.csv", parse_dates=["first", "last", "created"])
band = pd.read_csv(P / "arbitrage_band.csv")
prof = pd.read_csv(P / "diurnal_profile.csv")
ts = pd.read_csv(P / "stationarity.csv")
lc = pd.read_csv(P / "launch_curve.csv")
bd = pd.read_csv(P / "order_books.csv")
fcs = pd.read_csv(P / "forecasts_sa.csv")
fcj = json.load(open(P / "forecasts_sa.json"))
R = json.load(open(P / "results.json"))
mon = pd.read_csv(P / "seasonality_month.csv")
dow = pd.read_csv(P / "seasonality_dow.csv")
popd = pd.read_csv(P / "population_daily.csv", parse_dates=["date"])

WIN = f"{panel.date.min():%d %b %Y} to {panel.date.max():%d %b %Y}"
SRC_PX = (f"Source: tibia-warzones-schedule market archive, a deduplicated third-party mirror "
          f"of the TibiaMarket.top MarketValues model, item_id 22118. Window: {WIN}.")
SRC_GS = "Source: GuildStats.eu /online-counter (robots.txt: Allow: /)."
SRC_MB = "Source: TibiaMarket.top /market_board, item_id 22118, single snapshot 30 Jul 2026."
REG_COL = {"Europe": T10["blue"], "North America": T10["orange"],
           "South America": T10["green"], "Oceania": T10["purple"]}
H = {"2w": 14, "1m": 30, "3m": 91, "6m": 182}


def datefmt(ax, fmt="%b %Y", maxticks=7):
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=maxticks))
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt))


# ================================================================ 0 price distribution
# Where the coin actually trades, across every world at once. This was previously only a set of
# rows in a table - median, mean, min, max - which asks the reader to picture a distribution
# from four numbers. The dispersion point the table's own caption makes (that the all-worlds
# spread is inflated by launch-phase worlds) is a fact about shape, so it belongs in a shape.
_d = bw.dropna(subset=["px_last"]).sort_values("px_last").reset_index(drop=True)
_conv, _new = _d[_d.converged], _d[~_d.converged]
fig, ax = plt.subplots(figsize=(7.2, 3.4))
ax.scatter(_conv.px_last, _conv.index, s=17, color=ACCENT, zorder=3, linewidths=0,
           label="Converged")
ax.scatter(_new.px_last, _new.index, s=17, color=T10["orange"], zorder=3, linewidths=0,
           label="Launch phase or converging")
_med = _conv.px_last.median()
ax.axvline(_med, color=INK, lw=HAIR * 1.8, ls="--", zorder=2)
hgrid(ax, nbins=None)
ax.set_yticks([])
ax.set_xlabel("Latest price, GP per TC")
ax.set_ylabel("93 worlds, ranked")
ax.xaxis.set_major_formatter(gpfmt)
ax.set_xlim(_d.px_last.min() * 0.92, _d.px_last.max() * 1.10)
ax.set_ylim(-3, len(_d) + 2)
label_line(ax, _med, len(_d) * 0.5, f"  median converged world\n  {_med:,.0f} GP/TC", INK,
           dx=4, fs=6.9)
# The cheapest world sits at the foot of the cloud, so its label goes below the point
# rather than beside it, where the next few worlds already are.
for row, ha, dy in ((_d.iloc[0], "left", -9), (_d.iloc[-1], "right", 0)):
    ax.annotate(f"{row.world} {row.px_last:,.0f}",
                xy=(row.px_last, row.name), xytext=(9 if ha == "left" else -9, dy),
                textcoords="offset points", ha=ha, va="center", fontsize=6.6, color=MUTED)
ax.legend(loc="lower right", frameon=False, fontsize=LEG_FS, handletextpad=.4,
          borderaxespad=0, markerscale=1.1)
finish(fig, "fig00_price_distribution.png",
       "Settled worlds price within a narrow band; the spread is all young worlds",
       "Latest Tibia Coin price on every world, ranked",
       SRC_PX,
       f"One point per world on the last date it is observed. Converged worlds span "
       f"{_conv.px_last.min():,.0f} to {_conv.px_last.max():,.0f} GP/TC, a cross-world standard "
       f"deviation of {R['integration']['dispersion_last']:.1f}% in logs. Including worlds still "
       f"in launch-phase price discovery widens that to "
       f"{R['desc']['cs_sd_pct_latest']:.1f}% and stretches the range from "
       f"{_d.px_last.min():,.0f} to {_d.px_last.max():,.0f} - the dispersion in this market is "
       f"a statement about young worlds, not about disagreement among established ones.",
       outdir=FIG)

# ================================================================ 1 index
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(7.2, 4.1), sharex=True,
                              height_ratios=[3.2, 1])
ax.plot(idx.date, idx.basket_price, color=CONTEXT, lw=1.0, ls=":", zorder=2)
ax.plot(idx.date, idx.ew_price, color=T10["blue"], lw=1.5, zorder=3)
hgrid(ax)
ax.set_ylabel("GP per TC")
ax.yaxis.set_major_formatter(gpfmt)
iv = idx[idx.ew_price.notna()]
label_line(ax, iv.date.iloc[-1], iv.ew_price.iloc[-1], " Chain-linked", T10["blue"], dy=-8)
label_line(ax, idx.date.iloc[-1], idx.basket_price.iloc[-1], " Basket mean", CONTEXT, dy=8)
ax.set_xlim(idx.date.min(), idx.date.max() + pd.Timedelta(days=230))
ax.set_ylim(idx.ew_price.min() * 0.965, idx.ew_price.max() * 1.045)

ax2.fill_between(idx.date, idx.n_worlds, 0, color=T10["teal"], alpha=.55, lw=0)
ax2.axhline(10, color=T10["red"], ls="--", lw=1.0)
label_line(ax2, idx.date.iloc[-1], 10, " min 10 worlds", T10["red"], fs=6.6, dy=9)
hgrid(ax2)
ax2.set_ylabel("Worlds")
ax2.set_xlabel("Date")
ax2.set_ylim(0, idx.n_worlds.max() * 1.15)
ax2.set_yticks([25, 50])
datefmt(ax2)

# Direct annotation: the reader should not have to work out what the shape means.
_tr = iv.loc[iv.ew_price.idxmin()]
_pk = iv.loc[iv.ew_price.idxmax()]
ax.annotate(f"Market trough\n{_tr.ew_price:,.0f} GP", xy=(_tr.date, _tr.ew_price),
            xytext=(-64, 30), textcoords="offset points", ha="right", va="center",
            fontsize=7.0, color=T10["red"], fontweight=W_TITLE,
            arrowprops=dict(arrowstyle="-", color=T10["red"], lw=HAIR * 1.4))
ax.annotate(f"Peak\n{_pk.ew_price:,.0f} GP", xy=(_pk.date, _pk.ew_price),
            xytext=(0, 16), textcoords="offset points", ha="center", va="bottom",
            fontsize=7.0, color=INK, fontweight=W_TITLE,
            arrowprops=dict(arrowstyle="-", color=INK, lw=HAIR * 1.4))
_run = iv.ew_price.cummax()
_ddpct = iv.ew_price / _run - 1
_ddlo = iv.loc[_ddpct.idxmin()]
_ddhi = iv.loc[(iv.date <= _ddlo.date) & (iv.ew_price >= _run.loc[_ddpct.idxmin()])].iloc[0]
ax.annotate("", xy=(_ddlo.date, _ddlo.ew_price), xytext=(_ddlo.date, _ddhi.ew_price),
            arrowprops=dict(arrowstyle="<->", color=T10["orange"], lw=HAIR * 1.6))
ax.annotate(f"{_ddpct.min() * 100:.1f}%\nmaximum drawdown",
            xy=(_ddlo.date, (_ddhi.ew_price + _ddlo.ew_price) / 2), xytext=(8, 0),
            textcoords="offset points", ha="left", va="center", fontsize=6.9,
            color=T10["orange"], fontweight=W_TITLE)
_start = iv.date.iloc[0]
ax.annotate("Chain-linked index begins\nonce 10 worlds are observed",
            xy=(_start, iv.ew_price.iloc[0]), xytext=(12, 30), textcoords="offset points",
            ha="left", va="bottom", fontsize=6.9, color=MUTED, fontweight=W_LIGHT,
            arrowprops=dict(arrowstyle="-", color=CONTEXT, lw=HAIR * 1.4))
ax2.annotate("Coverage expands", xy=(pd.Timestamp("2025-01-15"), 30),
             xytext=(6, 10), textcoords="offset points", ha="left", va="bottom",
             fontsize=6.9, color=MUTED, fontweight=W_LIGHT)
finish(fig, "fig01_index.png",
       f"Chain-linking is worth {R['index']['naive_total_index_window_pct'] - R['index']['total_pct']:.1f} points; the window is worth thirty",
       "Aggregate Tibia Coin price, GP per TC, converged worlds",
       SRC_PX,
       "The archive's cross-section grows from a median of 1 world per date in 2023 to 85 in "
       "2026, so a basket mean mixes price change with composition change. The headline index "
       "is chain-linked: each day's return is the mean log return across worlds observed on "
       "both that day and the previous day, which is invariant to entry and exit. Shown from "
       "the first date carrying at least 10 converged worlds. Converged = 200+ observations, "
       "regular world type, not a launch inside the window.", outdir=FIG, hspace=0.30)

# ================================================================ 2 dispersion
fig, ax = plt.subplots(figsize=(7.2, 3.2))
ax.plot(idx.date, idx.disp_pct, color=T10["purple"], lw=1.1)
ax.axhline(4.0, color=T10["red"], ls="--", lw=1.1)
label_line(ax, idx.date.max(), 4.0, "4% round-trip fee ", T10["red"], fs=7.2,
           dx=0, dy=-9, ha="right")
hgrid(ax)
ax.set_xlabel("Date"); ax.set_ylabel("Std. dev. of log price (%)")
ax.yaxis.set_major_formatter(pctfmt)
ax.set_xlim(idx.date.min(), idx.date.max() + pd.Timedelta(days=170))
ax.set_ylim(idx.disp_pct.min() * 0.55, idx.disp_pct.max() * 1.06)
datefmt(ax)
finish(fig, "fig02_dispersion.png",
       "Dispersion settles just above the cost of arbitraging it away",
       "Cross-world standard deviation of log price, percent",
       SRC_PX,
       "The 4% reference line is twice the documented 2% Market offer fee, the round trip a "
       "small offer pays; it is not a fitted parameter, and larger offers pay far less because "
       "the fee is capped (Exhibit 5.5). Converged worlds only, restricted to dates carrying "
       "at least 10 observed worlds.", outdir=FIG)

# ================================================================ 3 arbitrage band
fig, ax = plt.subplots(figsize=(6.0, 2.9))
# One accent for the regime that carries the finding; the no-adjustment regime is grey.
cols = [NEUTRAL if v < 0 else ACCENT for v in band.closure_pp]
x = np.arange(len(band))
ax.bar(x, band.closure_pp, color=cols, width=0.62, zorder=3)
ax.errorbar(x, band.closure_pp, yerr=1.96 * band.se, fmt="none",
            ecolor=INK, elinewidth=HAIR*1.4, capsize=0, zorder=4)
ax.axhline(0, color=MUTED, lw=HAIR*1.4, zorder=2)
ax.axvline(1.5, color=T10["green"], ls="--", lw=HAIR*1.6, zorder=2)
ax.set_xticks(x); ax.set_xticklabels(band.bin)
hgrid(ax, grid=False)
bar_labels(ax, band.closure_pp.values,
           at=band.closure_pp.values + np.sign(band.closure_pp.values) * 1.96 * band.se.values,
           fmt="{:+.2f}", pad=4)
ax.set_yticks([])
ax.set_xlabel("Lagged gap from cross-world mean log price")
ax.set_ylabel("Next-day gap closure (pp/day)")
ax.set_ylim(band.closure_pp.min() - 0.18, band.closure_pp.max() + 0.26)
ax.annotate(f"sign change between bins;\nformally estimated at "
            f"{R['advanced']['tar']['threshold_pct']:.2f}%",
            xy=(1.6, band.closure_pp.max() * 0.92),
            fontsize=7.2, color=T10["green"], fontweight="bold", va="top", ha="left")
finish(fig, "fig03_arbitrage_band.png",
       "Gaps only close once they exceed the cost of closing them",
       "Next-day movement of the cross-world price gap, percentage points per day",
       SRC_PX,
       "Positive means the gap narrowed. Bars show means with 95% Newey-West intervals. The "
       "deviation is lagged one day, since a contemporaneous gap is mechanically correlated "
       "with the same-day return. Bin edges are chosen by hand and can only locate the "
       "threshold to within a bucket; a threshold autoregression estimates it formally at "
       f"{R['advanced']['tar']['threshold_pct']:.2f}% (Exhibit 6.2). No fee figure was "
       "supplied to the estimator.", outdir=FIG)

# ================================================================ 4 half-life
hh = R["integration"]["half_life_by_horizon"]
hs = sorted(int(k) for k in hh)
vals = [hh[str(h)]["implied_half_life_days"] for h in hs]
wk = R["integration"]["half_life_weekly_days"]
fig, ax = plt.subplots(figsize=(7.2, 3.3))
ax.plot(hs, vals, "o-", color=T10["blue"], lw=1.6, ms=5, zorder=3)
ax.axhline(wk, color=T10["green"], ls="--", lw=HAIR*1.6, zorder=2)
label_line(ax, hs[-1], wk, f" weekly: {wk:.0f} d", T10["green"], fs=7.0)
hgrid(ax)
ax.set_xscale("log"); ax.set_xticks(hs); ax.set_xticklabels(hs)
ax.set_xlabel("Regression horizon h (days)")
ax.set_ylabel("Implied half-life (days)")
ax.set_xlim(0.85, hs[-1] * 3.0)
ax.set_ylim(0, max(max(vals), wk) * 1.26)
ax.annotate(f"one-day estimate {vals[0]:.1f} d\nattenuated, do not use",
            xy=(hs[0], vals[0]), xytext=(1.5, max(vals) * 0.42),
            fontsize=7.0, color=T10["red"], fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=T10["red"], lw=HAIR*1.4))
finish(fig, "fig04_halflife.png",
       "Measurement noise makes the one-day half-life look far too short",
       "Implied half-life of a cross-world price gap, by estimation horizon",
       SRC_PX,
       f"Half-life implied by rho(h) in dev(t+h) = rho(h) x dev(t) with world fixed effects. "
       f"The monotone rise with h is the signature of classical measurement error in the daily "
       f"price. Mean daily return autocorrelation is "
       f"{R['integration']['mean_return_ac1']:+.3f}, confirming transitory noise. Converged "
       f"worlds, dates with at least 10 observed worlds.", outdir=FIG)

# ================================================================ 5 diurnal bias
fig, ax = plt.subplots(figsize=(7.2, 3.6))
for reg, c in REG_COL.items():
    d = prof[prof.region == reg].sort_values("hour_utc")
    if not len(d):
        continue
    ax.plot(d.hour_utc, d.bias_factor, color=c, lw=1.7, zorder=3)
    pk = d.loc[d.bias_factor.idxmax()]
    label_line(ax, pk.hour_utc, pk.bias_factor, f" {reg}", c, fs=7.4)
ax.axhline(1.0, color=MUTED, lw=HAIR*1.4, zorder=2)
ax.axvline(4.75, color=INK, ls=":", lw=HAIR*1.6, zorder=2)
hgrid(ax)
ax.set_xlabel("Hour at which the snapshot is taken (UTC)")
ax.set_ylabel("Daily-average online / instant count\n(above 1.0 = snapshot understates the world)")
ax.set_xticks(range(0, 24, 2)); ax.set_xlim(-0.4, 28.5)
ax.text(4.4, ax.get_ylim()[1] * 0.97, "04:45 UTC", fontsize=7.0, color=INK,
        ha="right", va="top", rotation=90)
finish(fig, "fig05_diurnal_bias.png",
       "A single-instant player count misstates even concurrent activity",
       "Snapshot bias factor for concurrent players online, by hour of day and region",
       SRC_GS,
       "Computed from 15-minute online-counter series for all 93 worlds over the 7 days "
       "ending 30 Jul 2026. Source labels are Tibia server time (CEST) and are converted to "
       "UTC here. A value of 2.8 means a snapshot at that hour understates that world's true "
       "daily average by 2.8 times. Because the curves differ in shape and not merely in "
       "level, no single correction factor can repair an instantaneous count. Note that concurrent players online measures activity, a flow; it is not the resident population of a world, which is a stock (see Exhibit 4.2).", outdir=FIG)

# ================================================================ 5b regional bias
# Replaces a six-column numeric table. The question is "which regions does a snapshot get
# wrong, and by how much?" - a comparison, so bars against the unbiased benchmark of 1.0.
bias = pd.read_csv(P / "snapshot_bias_summary.csv")
pr = bias.sort_values("factor_at_0445utc", ascending=True).reset_index(drop=True)
fig, ax = plt.subplots(figsize=(7.2, 2.7))
worst = int(pr.factor_at_0445utc.idxmax())
cols = [ACCENT if i == worst else NEUTRAL for i in pr.index]
yy = np.arange(len(pr))
ax.barh(yy, pr.factor_at_0445utc, color=cols, height=0.58, zorder=3)
ax.axvline(1.0, color=T10["red"], ls="--", lw=HAIR * 1.8, zorder=4)
ax.set_yticks(yy)
ax.set_yticklabels([f"{r.region}   ({int(r.n_worlds)} worlds)" for r in pr.itertuples()])
ax.tick_params(axis="y", length=0)
hgrid(ax, nbins=None, grid=False)
ax.set_xticks([])
ax.set_xlim(0, pr.factor_at_0445utc.max() * 1.30)
ax.set_xlabel("True daily average divided by the 04:45 UTC snapshot")
for i, r in enumerate(pr.itertuples()):
    ax.annotate(f"{r.factor_at_0445utc:.2f}x", xy=(r.factor_at_0445utc, i), xytext=(5, 0),
                textcoords="offset points", va="center", fontsize=7.4, color=INK,
                fontweight=W_TITLE)
ax.annotate("unbiased", xy=(1.0, len(pr) - 0.42), xytext=(4, 0), textcoords="offset points",
            ha="left", va="center", fontsize=6.9, color=T10["red"], fontweight=W_TITLE)
ax.annotate("A single snapshot understates Europe by 2.8x\nand overstates North America",
            xy=(0.99, 0.06), xycoords="axes fraction", ha="right", va="bottom",
            fontsize=7.0, color=ACCENT, fontweight=W_TITLE)
finish(fig, "fig05b_region_bias.png",
       "The same snapshot understates one region and overstates another",
       "Ratio of true daily-average players online to an instantaneous 04:45 UTC count",
       SRC_GS,
       "A value of 1.0 would mean the snapshot is unbiased. Because the error differs by "
       "region rather than being a common scale factor, no single correction can repair an "
       "instantaneous count - it rotates the cross-section. Computed from 15-minute "
       "online-counter series for all 93 worlds over the 7 days ending 30 Jul 2026. The full "
       "numeric detail, including peak hours and a second snapshot time, is in Appendix E.",
       outdir=FIG, left=0.22)

# ================================================================ 6 events
ev = R["events"]["world_fe"]
names = [("ev_xp_skill", "XP/Skill event"), ("ev_rapid_respawn", "Rapid Respawn"),
         ("ev_loot", "Loot event"), ("ev_exaltation", "Exaltation Overload"),
         ("pre_update_14", "14 days pre-update"), ("post_update_30", "30 days post-update")]
ks = [(k, l) for k, l in names if k in ev]
ks = sorted(ks, key=lambda kl: ev[kl[0]]["coef_pct"])          # sorted to aid comparison
vals = [ev[k]["coef_pct"] for k, _ in ks]
errs = [1.96 * ev[k]["se_pct"] for k, _ in ks]
sig = [ev[k]["p"] < 0.05 for k, _ in ks]
fig, ax = plt.subplots(figsize=(6.4, 2.9))
y = np.arange(len(ks))
# Accent reserved for the significant effects; the rest recede to grey.
ax.barh(y, vals, color=[ACCENT if sg else NEUTRAL for sg in sig], height=0.6, zorder=3)
ax.errorbar(vals, y, xerr=errs, fmt="none", ecolor=INK, elinewidth=HAIR*1.4,
            capsize=3, capthick=0.9, zorder=4)
ax.axvline(0, color=MUTED, lw=HAIR*1.4, zorder=2)
ax.set_yticks(y); ax.set_yticklabels([l for _, l in ks]); ax.invert_yaxis()
hgrid(ax, nbins=None, grid=False)      # categorical axis, and bars are labelled
bar_labels(ax, vals, at=[v + np.sign(v) * e for v, e in zip(vals, errs)],
           fmt="{:+.2f}", horizontal=True, pad=5)
ax.set_xticks([])
ax.set_xlim(min(v - e for v, e in zip(vals, errs)) * 1.45,
            max(v + e for v, e in zip(vals, errs)) * 1.45)
ax.set_xlabel("Effect on daily log return (% per day)")
ax.tick_params(axis="y", length=0)
finish(fig, "fig06_events.png",
       "Coin prices are weaker on event days, but the cause is not identifiable",
       "Difference in daily return versus non-event days, converged worlds",
       SRC_PX,
       "World fixed effects with standard errors two-way clustered by world and date; bars "
       "show 95% intervals. Every event label is global with no world dimension, so these "
       "coefficients are confounded with anything else occurring on the same dates and are "
       "absorbed entirely once date fixed effects are added. Association, not causation.",
       outdir=FIG, left=0.21)

# ================================================================ 7 young worlds
fig, ax = plt.subplots(figsize=(7.2, 3.7))
lw_ = bw[bw.launch_in_window]
md = bw[bw.is_merge_destination & (bw.created >= panel.date.min())]
rng = np.random.default_rng(7)
ax.plot(lc.bucket, lc["median"], color=T10["blue"], lw=1.8, zorder=4)
ax.scatter(rng.uniform(-7, 7, len(lw_)), lw_.px_first, s=26, color=T10["blue"],
           alpha=.75, zorder=5, edgecolor="white", linewidth=0.5)
ax.scatter(rng.uniform(-7, 7, len(md)), md.px_first, s=30, marker="s", color=T10["orange"],
           alpha=.85, zorder=5, edgecolor="white", linewidth=0.5)
xmean = idx.ew_price.dropna().iloc[-1]
ax.axhline(xmean, color=CONTEXT, ls=":", lw=HAIR*1.6, zorder=2)
hgrid(ax)
ax.set_xlabel("World age at observation (days since documented creation)")
ax.set_ylabel("GP per TC")
ax.yaxis.set_major_formatter(gpfmt)
ax.set_xlim(-16, 520)
label_line(ax, 405, xmean, " cross-world mean", CONTEXT, fs=7.0)
label_line(ax, 12, md.px_first.median(), f" Merge destinations (n={len(md)})",
           T10["orange"], fs=7.4, dy=7)
label_line(ax, 12, lw_.px_first.min(), f" Genuine launches (n={len(lw_)})",
           T10["blue"], fs=7.4, dy=-4)
label_line(ax, lc.bucket.iloc[len(lc) // 2], lc["median"].iloc[len(lc) // 2],
           " median launch path", T10["blue"], fs=6.9, dy=-11)
finish(fig, "fig07_young_worlds.png",
       "Provenance, not age, sets a new world's opening price",
       "First observed price against world age, worlds created inside the window",
       SRC_PX,
       "Worlds are classified by documented creation date from GuildStats plus absence from "
       "the merge register, never by observed price, which would select on the outcome. "
       "Points at age zero are jittered horizontally for visibility. Merge destinations open "
       "at mature prices despite being days old; genuine launches open one to two orders of "
       "magnitude lower and converge over roughly 500 days.", outdir=FIG)

# ================================================================ 8 world type
# One grouping per chart. PvP type and BattlEye status are two different partitions of the
# SAME 61 worlds, so plotting them on a single sorted axis would double-count every world and
# invite a comparison between categories that are not alternatives. BattlEye is a vintage
# marker (Section 5.3.2) and belongs in the regression table, not here.
cw = bw[bw.converged].copy()
rows8 = []
for k, g in cw.groupby("pvp_type"):
    m = g.px_last.mean()
    se = g.px_last.std(ddof=1) / np.sqrt(len(g))
    rows8.append({"label": str(k).replace(" PvP", ""), "mean": m,
                  "lo": m - 1.96 * se, "hi": m + 1.96 * se, "n": len(g)})
r8 = pd.DataFrame(rows8).sort_values("mean").reset_index(drop=True)
overall = float(cw.px_last.mean())
fig, ax = plt.subplots(figsize=(7.0, 2.5))
yy = np.arange(len(r8))
ax.hlines(yy, r8.lo, r8.hi, color=CONTEXT, lw=2.4, zorder=2)
top = int(r8["mean"].idxmax())
ax.scatter(r8["mean"], yy, s=46, color=[ACCENT if i == top else NEUTRAL for i in r8.index],
           zorder=4, edgecolor=BG, linewidth=0.6)
ax.axvline(overall, color=CONTEXT, ls="--", lw=HAIR * 1.8, zorder=1)
ax.set_yticks(yy)
ax.set_yticklabels([f"{r.label}  (n={r.n})" for r in r8.itertuples()])
ax.invert_yaxis()
ax.tick_params(axis="y", length=0)
hgrid(ax, x=True, nbins=None, grid=False)
ax.xaxis.set_major_formatter(gpfmt)
ax.set_xlabel("Latest price (GP per TC), group mean with 95% interval")
for i, r in enumerate(r8.itertuples()):
    ax.annotate(f"{r.mean:,.0f}", xy=(0.995, i), xycoords=("axes fraction", "data"),
                va="center", ha="right", fontsize=7.2, color=INK, fontweight=W_TITLE)
# Benchmark label sits beside the rule it explains, inside the plot area.
ax.annotate(f"all worlds {overall:,.0f}", xy=(overall, 0.02), xycoords=("data", "axes fraction"),
            xytext=(4, 0), textcoords="offset points", ha="left", va="bottom",
            fontsize=6.8, color=MUTED, fontweight=W_LIGHT)
ax.set_xlim(r8.lo.min() * 0.985, r8.hi.max() * 1.055)
finish(fig, "fig08_worldtype.png",
       "Optional-PvP worlds trade about 4% above Open-PvP worlds",
       "Mean latest price by PvP type, converged worlds",
       SRC_PX,
       f"Points are group means with 95% confidence intervals; the dashed line is the "
       f"all-world mean. Groups are defined by documented world attributes, never by price. "
       f"A regression controlling for BattlEye cohort and engagement puts the Optional-PvP "
       f"premium at "
       f"{R['cross_section']['engagement_full']['optional_pvp']['coef'] * 100:.1f}% "
       f"(Table 5.7). BattlEye status partitions the same worlds a second way and is "
       f"reported there rather than here, since plotting both on one axis would count every "
       f"world twice.", outdir=FIG, left=0.20)

# ================================================================ 9 order book
fig, ax = plt.subplots(figsize=(6.0, 2.9))
ax.scatter(bd.order_count_ratio, bd.depth_ratio, s=30, color=T10["blue"], alpha=.7,
           edgecolor="white", linewidth=0.5, zorder=3)
ax.axhline(1, color=MUTED, ls=":", lw=HAIR*1.6, zorder=2)
ax.axvline(1, color=MUTED, ls=":", lw=HAIR*1.6, zorder=2)
ax.set_xscale("log"); ax.set_yscale("log")
clean_log(ax, "x"); clean_log(ax, "y")
hgrid(ax, x=True)
ax.set_xlabel("Buy orders / sell orders (counts)")
ax.set_ylabel("Bid depth / ask depth (TC)")
note_box(ax, f"Pearson r = {R['micro']['corr_ordercount_vs_depth_ratio']:.2f}\n"
             f"counts explain little of true depth", loc="upper left")
finish(fig, "fig09_orderbook.png",
       "Counting orders is not measuring depth",
       "Order-count ratio against true quantity depth, one point per world, log scales",
       SRC_MB,
       "Each point is one world's live order book. Counts of standing orders are not depth: a "
       "long tail of tiny non-executable bids far below market inflates the count without "
       "contributing executable size. Any demand imbalance inferred from order-count ratios "
       "is an artefact.", outdir=FIG)

# ================================================================ 10 seasonality
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.6))
mn = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
axs[0].bar(mon.month, mon.mean_pct, width=.62, zorder=3,
           color=[T10["blue"] if v >= 0 else T10["red"] for v in mon.mean_pct])
axs[0].axhline(0, color=MUTED, lw=HAIR*1.4, zorder=2)
axs[0].set_xticks(range(1, 13)); axs[0].set_xticklabels(mn)
axs[0].set_xlabel("Calendar month"); axs[0].set_ylabel("Mean daily log return (%/day)")
hgrid(axs[0], nbins=3)
dn = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
axs[1].bar(dow.dow, dow.mean_pct, width=.62, zorder=3,
           color=[T10["blue"] if v >= 0 else T10["red"] for v in dow.mean_pct])
axs[1].axhline(0, color=MUTED, lw=HAIR*1.4, zorder=2)
axs[1].set_xticks(range(7)); axs[1].set_xticklabels(dn, fontsize=6.8)
axs[1].set_xlabel("Day of week")
hgrid(axs[1], nbins=3)
# Explicit limits keep the outermost tick label clear of the title and note bands, which the
# frameless layout no longer separates with a spine.
for _a, _v in ((axs[0], mon.mean_pct), (axs[1], dow.mean_pct)):
    _m = max(abs(_v.min()), abs(_v.max()))
    _step = 0.1 if _m < 0.15 else 0.2
    _a.set_ylim(-_m * 1.75, _m * 1.75)
    _a.set_yticks([-_step, 0, _step])
finish(fig, "fig10_seasonality.png",
       "Autumn is the strongest stretch; day of week barely matters",
       "Mean daily log return by calendar bucket, converged worlds",
       SRC_PX,
       "Unconditional means by bucket. Days are UTC-floored, but the Tibia economic day begins "
       "at server save, so day-of-week buckets carry a known misalignment. Event days are not "
       "excluded and CipSoft's events cluster seasonally, so the monthly pattern and the event "
       "effects are largely the same variation viewed two ways.", outdir=FIG)

# ================================================================ 11 clustering
cc = R["panel"]["clustering_comparison"]
ks = ["none", "world", "date", "two-way"]
labs = ["None\n(naive)", "By world", "By date", "Two-way\n(used)"]
fig, ax = plt.subplots(figsize=(5.6, 2.7))
cols = [CONTEXT, T10["orange"], T10["orange"], T10["blue"]]
ax.bar(labs, [cc[k]["se"] for k in ks], color=cols, width=.58, zorder=3)
for i, k in enumerate(ks):
    ax.annotate(f"t = {cc[k]['t']:.1f}", xy=(i, cc[k]["se"]), xytext=(0, 14),
                textcoords="offset points", ha="center", va="bottom",
                fontsize=7.0, color=MUTED, fontweight=W_LIGHT)
hgrid(ax)
bar_labels(ax, [cc[k]["se"] for k in ks], fmt="{:.4f}", pad=3)
ax.set_xlabel("Clustering dimension"); ax.set_ylabel("Standard error")
ax.set_ylim(0, max(cc[k]["se"] for k in ks) * 1.22)
ax.set_yticks([])
finish(fig, "fig11_clustering.png",
       "Ignoring cross-world dependence overstates precision by 3.6 times",
       "Standard error of the arbitrage coefficient under four clustering assumptions",
       SRC_PX,
       "The point estimate is identical in all four columns; only the standard error changes. "
       "Arbitrage links worlds, so observations on the same date are not independent across "
       "worlds, and observations on the same world are not independent across dates.",
       outdir=FIG, xlabel_pad_in=0.60, left=0.115)

# ================================================================ 12 forecast fan
ex = max(fcj, key=lambda f: f["n_obs"])
s = panel[panel.world == ex["world"]].sort_values("date").tail(420)
fig, ax = plt.subplots(figsize=(7.2, 3.5))
ax.plot(s.date, s.price_gp, color=T10["blue"], lw=1.1, zorder=4)
t0 = s.date.iloc[-1]
xs = [t0] + [t0 + pd.Timedelta(days=d) for d in H.values()]
for lo, hi, al in [("p5", "p95", .14), ("p10", "p90", .22), ("p25", "p75", .32)]:
    ax.fill_between(xs, [ex["last_price"]] + [ex[k][lo] for k in H],
                    [ex["last_price"]] + [ex[k][hi] for k in H],
                    color=T10["orange"], alpha=al, lw=0, zorder=3)
ax.plot(xs, [ex["last_price"]] + [ex[k]["p50"] for k in H], color=T10["orange"],
        lw=1.4, ls="--", zorder=5)
hgrid(ax)
ax.set_xlabel("Date"); ax.set_ylabel("GP per TC")
ax.yaxis.set_major_formatter(gpfmt)
datefmt(ax)
label_line(ax, xs[-1], ex["6m"]["p50"], " median (flat by construction)", T10["orange"], fs=7.0)
label_line(ax, xs[-1], ex["6m"]["p90"], " 90th pct", CONTEXT, fs=6.6)
label_line(ax, xs[-1], ex["6m"]["p10"], " 10th pct", CONTEXT, fs=6.6)
ax.set_xlim(s.date.min(), xs[-1] + pd.Timedelta(days=260))
finish(fig, "fig12_forecast_fan.png",
       "The informative output is the interval width, not the central path",
       f"{ex['world']}: observed price and bootstrapped forecast, 50/80/90% intervals",
       SRC_PX,
       "Bootstrapped random walk, 5,000 moving-block paths with block length 10 days drawn "
       "from the world's own trailing-year returns. Drift is shrunk empirical-Bayes and capped "
       "at 0.04% per day, with no imposed level mean reversion. Because the level carries a "
       "unit root, the median path is flat by construction.", outdir=FIG)

# ================================================================ 13 population
cw2 = bw[bw.converged].dropna(subset=["population", "activity_year"]).copy()
cw2["engagement"] = cw2.activity_year / cw2.population
pcm = R["cross_section"]["population_measure_comparison"]
eng = R["cross_section"]["engagement_full"]
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.7), sharey=True)
panels = [
    (axs[0], "population", "Characters on the world (full roster)",
     f"{pcm['full_roster_tibiavip']['coef']:+.3f} (p={pcm['full_roster_tibiavip']['p']:.2f})"),
    (axs[1], "activity_year", "Mean concurrent players online",
     f"{pcm['concurrent_activity_daily_avg']['coef']:+.3f} (p={pcm['concurrent_activity_daily_avg']['p']:.2f})"),
    (axs[2], "engagement", "Concurrent players per character",
     f"{eng['log_engagement']['coef']:+.3f} (p={eng['log_engagement']['p']:.3f})"),
]
for ax, xcol, xlab, ann in panels:
    # Region is not the message here, so it is not encoded: a legend would be a competing
    # signal. Only the panel that carries the finding takes the accent.
    focal = xcol == "engagement"
    ax.scatter(cw2[xcol], cw2.px_last, s=22,
               color=ACCENT if focal else NEUTRAL, alpha=.85,
               edgecolor=BG, linewidth=0.4, zorder=3)
    ax.set_xscale("log")
    hgrid(ax)
    ax.set_xlabel(xlab, fontsize=7.0)
    lo, hi = cw2[xcol].min(), cw2[xcol].max()
    ax.set_xlim(lo / 1.6, hi * 1.6)
    log_ticks_within(ax, lo / 1.5, hi * 1.5, "x",
                     fmt=(lambda v, _: f"{v:g}") if xcol == "engagement"
                     else (lambda v, _: f"{v/1000:,.0f}k" if v >= 1000 else f"{v:,.0f}"))
    ax.text(0.04, 0.965, ann, transform=ax.transAxes, fontsize=6.8,
            color=INK if focal else MUTED, fontweight=W_TITLE, va="top")
axs[0].set_ylabel("Latest price (GP per TC)")
axs[0].yaxis.set_major_formatter(gpfmt)
axs[0].set_ylim(cw2.px_last.min() * 0.90, cw2.px_last.max() * 1.10)
finish(fig, "fig13_population.png",
       "Population is irrelevant to the price; engagement is not",
       "Latest price against the character roster, concurrent activity, and their ratio",
       "Sources: price archive item_id 22118; TibiaVIP world list (Total column); "
       "GuildStats.eu /online-counter.",
       "Population is the world's full character roster, 6,222,595 characters across the 93 "
       "worlds. Concurrent players online is an activity flow. Engagement is their ratio. "
       "Annotations are coefficients on log price controlling for PvP type and BattlEye "
       "cohort; the engagement coefficient also controls for population. Roster size alone "
       "carries no relationship with price, while engagement does - so what matters is how "
       "much of a world's roster is actually playing, not how large the roster is.",
       outdir=FIG, wspace=0.26)

# ================================================================ 14 drawdown
dd = idx.set_index("date")["ew_price"].dropna()
draw = (dd / dd.cummax() - 1) * 100
fig, ax = plt.subplots(figsize=(7.2, 2.3))
ax.fill_between(draw.index, draw.values, 0, color=T10["red"], alpha=.5, lw=0, zorder=3)
ax.plot(draw.index, draw.values, color=T10["red"], lw=0.8, zorder=4)
hgrid(ax)
ax.set_xlabel("Date"); ax.set_ylabel("Drawdown from peak (%)")
ax.yaxis.set_major_formatter(pctfmt)
ax.set_ylim(draw.min() * 1.30, 1.5)
datefmt(ax)
lo = draw.idxmin()
ax.annotate(f"{draw.min():.1f}% on {lo:%b %Y}", xy=(lo, draw.min()),
            xytext=(14, 16), textcoords="offset points", fontsize=7.0, color=T10["red"],
            fontweight="bold", arrowprops=dict(arrowstyle="-", color=T10["red"], lw=HAIR*1.4))
finish(fig, "fig14_drawdown.png",
       "A 15% drawdown has already occurred once inside the sample",
       "Drawdown of the chain-linked index from its running peak, percent",
       SRC_PX,
       "Computed on the chain-linked index level. Descriptive only: the level is "
       "non-stationary, so drawdown depth carries no implication for the speed or the "
       "likelihood of recovery.", outdir=FIG)

# ================================================================ 15 volatility
fig, ax = plt.subplots(figsize=(6.0, 2.7))
ax.hist(ts.ret_sd_pct, bins=22, color=T10["blue"], alpha=.75, zorder=3)
med = ts.ret_sd_pct.median()
ax.axvline(med, color=T10["red"], ls="--", lw=1.2, zorder=4)
hgrid(ax)
ax.set_xlabel("Standard deviation of daily log return (%/day)")
ax.set_ylabel("Number of worlds")
ax.annotate(f"median {med:.2f}%/day", xy=(med, ax.get_ylim()[1] * 0.88),
            xytext=(8, 0), textcoords="offset points", fontsize=7.2,
            color=T10["red"], fontweight="bold", va="center")
finish(fig, "fig15_volatility.png",
       "Most established worlds move about 1% a day",
       "Distribution of daily return volatility, one observation per converged world",
       SRC_PX,
       "Computed over each world's full history. Returns are taken only between consecutive "
       "observed days; gaps are not bridged. Thin worlds sit in the right tail, consistent "
       "with the liquidity relationships in Section 5.6.", outdir=FIG)

# ================================================================ 16 population history
fig, ax = plt.subplots(figsize=(7.2, 2.6))
tot = popd.groupby("date")["players_online_avg"].sum()
tot = tot[tot.index >= "2016-01-01"]
ax.plot(tot.index, tot.values, color=T10["green"], lw=1.0, zorder=4)
ax.axvspan(panel.date.min(), panel.date.max(), color=T10["blue"], alpha=.10, lw=0, zorder=2)
hgrid(ax)
ax.set_xlabel("Date"); ax.set_ylabel("Concurrent players online (daily avg)")
ax.yaxis.set_major_formatter(gpfmt)
ax.set_ylim(0, tot.max() * 1.16)
datefmt(ax)
ax.text(panel.date.min() + pd.Timedelta(days=120), tot.max() * 1.10,
        "price observation window", fontsize=7.0, color=T10["blue"], va="top")
finish(fig, "fig16_population_history.png",
       "Activity history extends far beyond the price window",
       "Total daily-average concurrent players online across the 93 sampled worlds",
       SRC_GS,
       "Sums only the 93 worlds present in the price sample, so worlds that merged away "
       "before the window are excluded and the early level understates the true whole-game "
       "total. The level is therefore not comparable across time; the series establishes "
       "coverage rather than measuring the game's growth. This is concurrent activity, a flow, not the resident population of the game.", outdir=FIG)

# ================================================================ 17 fee schedule
FE = R["fees"]
lo = pd.read_csv(P / "live_offers.csv")
sizes = np.logspace(1, np.log10(FE["qty_cap"]), 250)
val = sizes * FE["median_quoted_price"]
fee = np.minimum(np.maximum(0.02 * val, FE["min_gp"]), FE["cap_gp"])
rt = 2 * fee / val * 100

fig, ax = plt.subplots(figsize=(7.2, 2.9))
ax.plot(sizes, rt, color=T10["blue"], lw=1.8, zorder=4)
ax.axhline(4.0, color=CONTEXT, ls=":", lw=HAIR*1.6, zorder=2)
ax.axvline(FE["cap_binds_above_tc"], color=T10["red"], ls="--", lw=1.1, zorder=3)
dec = pd.DataFrame(FE["roundtrip_by_decile"])
ax.scatter(dec.median_tc, dec.roundtrip_pct, s=30, color=T10["orange"], zorder=5,
           edgecolor="white", linewidth=0.5)
ax.set_xscale("log")
log_ticks_within(ax, 8, FE["qty_cap"] * 1.4, "x")
hgrid(ax)
ax.set_xlabel("Offer size (Tibia Coins, log scale)")
ax.set_ylabel("Round-trip Market fee (% of value)")
ax.set_xlim(8, FE["qty_cap"] * 1.5)
ax.set_ylim(0, 4.9)
label_line(ax, 30, 4.0, " 4% - the small-trader cost", T10["blue"], fs=7.2, dy=8)
ax.annotate(f"1,000,000 GP cap starts binding\nat about {FE['cap_binds_above_tc']:,.0f} TC",
            xy=(FE["cap_binds_above_tc"], 2.2), xytext=(FE["cap_binds_above_tc"] * 1.35, 3.1),
            fontsize=7.0, color=T10["red"], fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=T10["red"], lw=HAIR*1.4))
label_line(ax, dec.median_tc.iloc[-1], dec.roundtrip_pct.iloc[-1],
           f" largest decile: {dec.roundtrip_pct.iloc[-1]:.2f}%", T10["orange"], fs=7.0,
           ha="right", dx=-8, dy=12)
finish(fig, "fig17_fee_schedule.png",
       "The 4% arbitrage band is the small trader's cost, not everyone's",
       "Round-trip Market fee against offer size, at the median quoted price",
       "Sources: documented Market mechanics; TibiaMarket.top /market_board, 4,098 live "
       "offers across 93 worlds, 30 Jul 2026.",
       f"Each offer costs 2% of value, floored at {FE['min_gp']} GP and capped at "
       f"{FE['cap_gp']:,} GP, so the effective rate falls once an offer exceeds "
       f"{FE['cap_binds_above_value_gp']:,.0f} GP - about {FE['cap_binds_above_tc']:,.0f} TC at "
       f"the median price. Orange points are the observed median round-trip cost by offer-size "
       f"decile. The cap binds on {FE['share_capped_by_count']:.0%} of live offers by count but "
       f"{FE['share_capped_by_value']:.0%} by value. Offer sizes are themselves capped at "
       f"{FE['qty_cap']:,} units, a limit 45 live offers sit exactly on.", outdir=FIG)

# ================================================================ 18 TAR profile
AD = R["advanced"]
tg = pd.read_csv(P / "tar_grid.csv")
T = AD["tar"]
fig, ax = plt.subplots(figsize=(7.2, 2.9))
ax.plot(tg.gamma_pct, tg.lr, color=T10["blue"], lw=1.4, zorder=4)
ax.axhline(7.35, color=CONTEXT, ls="--", lw=HAIR * 1.6, zorder=2)
lo, hi = T["threshold_ci_pct"]
ax.axvspan(lo, hi, color=T10["blue"], alpha=.13, lw=0, zorder=1)
ax.axvline(T["threshold_pct"], color=T10["blue"], ls="-", lw=HAIR * 2, zorder=3)
ax.axvline(4.0, color=T10["red"], ls=":", lw=HAIR * 2.4, zorder=3)
hgrid(ax)
ax.set_xlabel("Candidate threshold (% deviation from cross-world mean)")
ax.set_ylabel("Likelihood-ratio statistic")
ax.set_ylim(0, min(tg.lr.max() * 1.05, 320))
ax.set_xlim(tg.gamma_pct.min(), tg.gamma_pct.max())
label_line(ax, T["threshold_pct"], ax.get_ylim()[1] * 0.90,
           f'  estimate {T["threshold_pct"]:.2f}%', T10["blue"], fs=7.2)
label_line(ax, 4.0, ax.get_ylim()[1] * 0.62, "  4% small-trader fee", T10["red"], fs=7.2)
label_line(ax, tg.gamma_pct.max(), 7.35, " 95% critical value", CONTEXT, fs=6.8,
           ha="right", dx=-4, dy=8)
finish(fig, "fig18_tar_profile.png",
       f"The friction point is estimated at {T['threshold_pct']:.1f}%, not imposed at 4%",
       "Hansen threshold search: likelihood ratio against each candidate threshold",
       SRC_PX,
       f"Band-threshold autoregression on {T['n']:,} world-days across {T['n_worlds']} "
       f"converged worlds. The threshold is the value minimising the residual sum of squares; "
       f"the shaded region is Hansen's 95% confidence set, the values whose likelihood ratio "
       f"falls below the 7.35 critical value. Linearity is rejected decisively "
       f"(F = {T['F_threshold']:.0f}, bootstrap p < 0.001, {T['n_bootstrap']} replications). "
       f"The 4% line is the round-trip Market fee faced by a small offer; the fee cap means "
       f"larger offers pay far less (Exhibit 5.3), so a threshold below 4% is what the capped "
       f"fee schedule predicts.", outdir=FIG)

# ================================================================ 19 regime persistence
# The question is "how does persistence compare with the random-walk benchmark?", which is a
# performance-against-target question - so a bullet chart, not a plain bar.
fig, ax = plt.subplots(figsize=(7.0, 2.6))
labs19 = [f"Inside the band  (gap <= {T['threshold_pct']:.2f}%)",
          f"Outside the band  (gap > {T['threshold_pct']:.2f}%)"]
vals19 = [T["rho_inside"], T["rho_outside"]]
# No qualitative range bands: with two categories and one benchmark they would be
# background shading that adds nothing the bar and the target rule do not already say.
bullet_chart(ax, labs19, vals19, target=1.0, fmt="{:.3f}", accent=ACCENT)
for i, (v, se) in enumerate(zip(vals19, [T["se_inside"], T["se_outside"]])):
    ax.plot([v - 1.96 * se, v + 1.96 * se], [i, i], color=INK, lw=HAIR * 1.6, zorder=5)
hgrid(ax, x=True, nbins=None, grid=False)
ax.set_xlim(0.80, 1.13)
ax.set_xticks([0.85, 0.90, 0.95, 1.00, 1.05])
ax.set_xlabel("One-day persistence of the cross-world gap")
# Benchmark label placed adjacent to the rule it explains, inside the plot area.
ax.annotate("random-walk\nbenchmark = 1.00", xy=(1.0, -0.42), ha="center", va="center",
            xytext=(30, 0), textcoords="offset points",
            fontsize=6.8, color=INK, fontweight=W_TITLE, annotation_clip=False)
finish(fig, "fig19_tar_regimes.png",
       "Inside the band the gap is a random walk; outside it, it reverts",
       "Persistence against the random-walk benchmark, with 95% intervals",
       SRC_PX,
       f"Bars are the estimated autoregressive coefficient in each regime; the vertical rule "
       f"is the random-walk benchmark of 1.00 and the thin line is the 95% interval. Standard "
       f"errors clustered by world. Inside the band the coefficient is "
       f"{T['rho_inside']:.3f}, indistinguishable from the benchmark "
       f"(t = {T['t_inside_vs_unity']:+.2f}), so there is no restoring force. Outside it the "
       f"coefficient is {T['rho_outside']:.3f}, decisively below it "
       f"(t = {T['t_outside_vs_unity']:.1f}). {T['share_inside_band']*100:.0f}% of world-days "
       f"sit inside the band.", outdir=FIG, left=0.30)

# ================================================================ 19b band stability heatmap
# A matrix of values by year and gap size: a heatmap answers "is the pattern stable?" faster
# than three superimposed line series or a table of numbers.
cvp = pd.read_csv(P / "converged_panel.csv")
hm = (cvp.dropna(subset=["gap_bin", "closure_pp"])
      .groupby(["yr", "gap_bin"], observed=True)["closure_pp"].mean().unstack())
order = ["0-2%", "2-4%", "4-6%", "6-10%", ">10%"]
hm = hm.reindex(columns=[c for c in order if c in hm.columns]).sort_index()
fig, ax = plt.subplots(figsize=(6.4, 2.3))
heatmap(ax, hm.values, [str(int(i)) for i in hm.index], list(hm.columns), fmt="{:+.2f}")
ax.set_xlabel("Lagged gap from cross-world mean")
ax.set_ylabel("Year")
finish(fig, "fig19b_band_stability.png",
       "Small gaps widen and large gaps close, in every year of the sample",
       "Mean next-day gap closure (percentage points per day) by year and gap size",
       SRC_PX,
       "Blue is a closing gap, red a widening one, and the colour scale is centred on zero so "
       "the sign is read directly. Every row changes sign in the same place, which is what "
       "makes the threshold a stable feature rather than an artefact of one period. 2023 is "
       "omitted: the archive observes too few worlds per date that year for a cross-world "
       "mean to be defined.", outdir=FIG, left=0.10)

# ================================================================ 20 spread decomposition
FN = R["finance"]
roll = pd.read_csv(P / "roll_spread.csv")
FE = R["fees"]
# Five cost measures on one axis, ordered by size. Colour is reserved for the one figure the
# section is about - what a trade actually pays - and the estimated arbitrage band is drawn in
# so the reader can see the friction point sitting between the capped and uncapped fee rather
# than having to hold two numbers in mind across a page.
TARP = R["advanced"]["tar"]["threshold_pct"]
comps = [("Quoted spread", FN["roll"]["median_quoted_spread_pct"],
          "what a market order would cross"),
         ("Round-trip fee, small offer", 4.0, "two offers at the uncapped 2% rate"),
         ("Executed-price gap", FN["roll"]["median_executed_gap_pct"],
          "mean sell price against mean buy price"),
         ("Roll effective spread", FN["roll"]["median_roll_spread_pct"],
          "what trades actually pay, on average"),
         ("Round-trip fee, largest decile", FE["roundtrip_largest_decile_pct"],
          f"two offers with the 1,000,000 GP cap binding")]
comps = sorted(comps, key=lambda z: z[1])                 # smallest at the foot
KEY = "Roll effective spread"
fig, ax = plt.subplots(figsize=(7.2, 3.4))
ypos = np.arange(len(comps))
ax.barh(ypos, [c[1] for c in comps], height=.36, zorder=3,
        color=[ACCENT if c[0] == KEY else CONTEXT for c in comps])
ax.axvline(TARP, color=T10["orange"], lw=HAIR * 2.2, ls="--", zorder=4)
ax.set_yticks(ypos)
ax.set_yticklabels([c[0] for c in comps], fontsize=7.4)
for i, c in enumerate(comps):                              # the table's third column, in place
    ax.annotate(c[2], xy=(0, i), xytext=(1, -13), textcoords="offset points",
                fontsize=6.4, color=MUTED, va="center", ha="left")
hgrid(ax, nbins=None)
bar_labels(ax, [c[1] for c in comps], fmt="{:.2f}%", horizontal=True, pad=4,
           fs=7.4, color=INK)
ax.set_xticks([])
ax.set_xlim(0, max(c[1] for c in comps) * 1.16)
ax.set_ylim(-0.6, len(comps) - 0.4)
ax.tick_params(axis="y", length=0)
label_line(ax, TARP, len(comps) - 0.62,
           f"estimated arbitrage band {TARP:.2f}%", T10["orange"], dx=5, dy=0, fs=6.8)
finish(fig, "fig20_spread_decomposition.png",
       "Traders pay far less than the quoted spread suggests",
       "Cost of a Tibia Coin round trip under five measures, percent of value",
       "Sources: price archive item_id 22118; TibiaMarket.top /market_board; documented "
       "Market mechanics.",
       f"The Roll (1984) effective spread is inferred from the negative first-order "
       f"autocovariance of returns and measures what trades actually pay; at "
       f"{FN['roll']['median_roll_spread_pct']:.2f}% it is about "
       f"{FN['roll']['share_of_quoted']:.0%} of the quoted spread, which is what one expects "
       f"when most volume executes inside the quotes via resting limit orders. Medians across "
       f"{FN['roll']['n_worlds']} converged worlds (interquartile range "
       f"{FN['roll']['iqr'][0]:.2f}% to {FN['roll']['iqr'][1]:.2f}%); the autocovariance is "
       f"negative, as Roll's model requires, on {FN['roll']['n_negative_gamma1']} of them. The "
       f"dashed line is the friction point estimated in Section 6.3.1 from prices alone - it "
       f"falls between the capped and uncapped fee, not at either.", outdir=FIG, left=0.26)

# ================================================================ 21 variance decomposition
vd = pd.read_csv(P / "variance_decomposition.csv")
V = FN["variance"]
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7))
axs[0].hist(vd.r2_systematic * 100, bins=20, color=T10["blue"], alpha=.75, zorder=3)
axs[0].axvline(vd.r2_systematic.median() * 100, color=T10["red"], ls="--", lw=HAIR * 1.8, zorder=4)
hgrid(axs[0], nbins=3)
axs[0].set_xlabel("Share of daily return variance that is common (%)")
axs[0].set_ylabel("Number of worlds")
axs[0].annotate(f"median {vd.r2_systematic.median()*100:.1f}%",
                xy=(vd.r2_systematic.median() * 100, axs[0].get_ylim()[1] * 0.88),
                xytext=(7, 0), textcoords="offset points", fontsize=7.0,
                color=T10["red"], fontweight=W_TITLE, va="center")
shares = [V["pc1_share"], V["pc2_share"], V["pc3_share"]]
axs[1].bar(["PC1", "PC2", "PC3"], [v * 100 for v in shares],
           color=[T10["blue"], CONTEXT, CONTEXT], width=.5, zorder=3)
hgrid(axs[1], nbins=3)
bar_labels(axs[1], [v * 100 for v in shares], fmt="{:.1f}%", pad=3)
axs[1].set_yticks([])
axs[1].set_xlabel("Principal component of the return matrix")
finish(fig, "fig21_variance_decomposition.png",
       "Daily coin returns are almost entirely local, not market-wide",
       "Systematic share of return variance, and principal components",
       SRC_PX,
       f"Left: R-squared from regressing each world's daily return on a leave-one-out mean of "
       f"all other worlds, so no world is regressed on itself. Right: share of total variance "
       f"explained by each principal component of the standardised return matrix "
       f"({V['n_pca_worlds']} worlds, {V['n_pca_dates']} dates). The contrast with the level "
       f"is the point: prices share a single common stochastic trend (Section 6.3.2), yet "
       f"day-to-day movement is overwhelmingly idiosyncratic.", outdir=FIG)

# ================================================================ 22 variance ratio
vrdf = pd.read_csv(P / "variance_ratio.csv")
qs = [2, 5, 10, 20]
fig, ax = plt.subplots(figsize=(7.2, 2.8))
med = [vrdf[f"vr{q}"].median() for q in qs]
p25 = [vrdf[f"vr{q}"].quantile(.25) for q in qs]
p75 = [vrdf[f"vr{q}"].quantile(.75) for q in qs]
ax.fill_between(qs, p25, p75, color=T10["blue"], alpha=.18, lw=0, zorder=2)
ax.plot(qs, med, "o-", color=T10["blue"], lw=1.5, ms=5, zorder=4)
ax.axhline(1.0, color=T10["red"], ls="--", lw=HAIR * 1.8, zorder=3)
hgrid(ax)
ax.set_xscale("log")
log_ticks_within(ax, 1.6, 30, "x")
ax.set_xticks(qs); ax.set_xticklabels(qs)
ax.xaxis.set_minor_locator(NullLocator())
ax.set_xlim(1.75, 26)
ax.set_xlabel("Aggregation horizon q (days)")
ax.set_ylabel("Variance ratio VR(q)")
ax.set_ylim(0.30, 1.18)
ax.annotate("random walk", xy=(0.985, 1.0), xycoords=("axes fraction", "data"),
            xytext=(0, 6), textcoords="offset points", ha="right", va="bottom",
            fontsize=7.0, color=T10["red"], fontweight=W_TITLE)
label_line(ax, qs[-1], med[-1], f"median {med[-1]:.2f}  ", T10["blue"], fs=7.0,
           ha="right", dx=-4, dy=-9)
finish(fig, "fig22_variance_ratio.png",
       "Prices revert at short horizons, but inside the spread",
       "Lo-MacKinlay variance ratios across converged worlds, interquartile band",
       SRC_PX,
       f"A variance ratio of one is a random walk; below one indicates mean reversion at that "
       f"horizon. The heteroskedasticity-robust statistic rejects the random walk at q = 2 on "
       f"{FN['efficiency']['vr2_reject_5pct']} of {FN['efficiency']['n_worlds']} worlds. The "
       f"reversion is the bid-ask bounce identified in Exhibit 5.6: a Roll effective spread of "
       f"{FN['roll']['median_roll_spread_pct']:.2f}% mechanically produces negative return "
       f"autocorrelation without implying any profit opportunity, since the reversal happens "
       f"between the bid and the ask rather than across it.", outdir=FIG)

# ================================================================ 23 quantile regression
qr = pd.read_csv(P / "quantile_regression.csv")
fig, ax = plt.subplots(figsize=(6.2, 2.7))
ax.plot(qr.tau, qr.coef, "o-", color=T10["blue"], lw=1.5, ms=5, zorder=4)
ax.fill_between(qr.tau, qr.coef - 1.96 * qr.se, qr.coef + 1.96 * qr.se,
                color=T10["blue"], alpha=.18, lw=0, zorder=2)
ax.axhline(0, color=MUTED, lw=HAIR * 1.6, zorder=3)
ols_b = R["panel"]["dev_only_wfe"]["dev_lag"]["coef"]
ax.axhline(ols_b, color=T10["orange"], ls="--", lw=HAIR * 1.8, zorder=3)
hgrid(ax)
ax.set_xlabel("Quantile of the daily return distribution")
ax.set_ylabel("Coefficient on the lagged gap")
ax.annotate("mean regression", xy=(0.985, ols_b), xycoords=("axes fraction", "data"),
            xytext=(0, 7), textcoords="offset points", ha="right", va="bottom",
            fontsize=7.0, color=T10["orange"], fontweight=W_TITLE)
finish(fig, "fig23_quantile.png",
       "Adjustment to the cross-world gap is concentrated in large up-moves",
       "Quantile regression of the daily return on the lagged deviation, world effects absorbed",
       SRC_PX,
       "A more negative coefficient means faster correction of the gap. Adjustment at the 90th "
       "percentile of the return distribution is roughly three times that at the 10th, so the "
       "band is enforced mainly by episodes of sharp upward repricing rather than by steady "
       "drift. Shaded band is the 95% interval; the dashed line is the mean-regression estimate "
       "of Table 6.1.", outdir=FIG)

# ================================================================ 00 cover art
# Full-bleed cover graphic at A4 proportions: every converged world's price path as a
# hairline over a deep navy field, with the chain-linked index carried in white. Built from
# the report's own data rather than stock imagery.
NAVY = "#051C2C"
figc, axc = plt.subplots(figsize=(8.27, 11.69))
figc.patch.set_facecolor(NAVY)
axc.set_facecolor(NAVY)
for w, g in panel[panel.converged].groupby("world"):
    g = g.sort_values("date")
    axc.plot(g.date, g.price_gp, color="#7FB3E0", lw=0.45, alpha=0.30, zorder=2,
             solid_capstyle="round")
iv0 = idx[idx.ew_price.notna()]
axc.plot(iv0.date, iv0.ew_price, color="#FFFFFF", lw=2.2, zorder=4, solid_capstyle="round")
axc.set_ylim(20000, 62000)          # keeps the ribbon in the lower half, clear of the title
axc.set_xlim(panel.date.min(), panel.date.max())
axc.axis("off")
figc.subplots_adjust(left=-0.02, right=1.02, top=0.62, bottom=0.02)
figc.patch.set_alpha(0.0)
axc.patch.set_alpha(0.0)
figc.savefig(FIG / "cover_art.svg", transparent=True)
figc.savefig(FIG / "cover_art.png", facecolor=NAVY, dpi=200)
plt.close(figc)

# ================================================================ chapter marks
# A quiet conceptual mark for each chapter opener, drawn from the report's own data so the
# visual carries meaning rather than decoration.
def _mark(name, draw):
    figm, axm = plt.subplots(figsize=(6.4, 1.5))
    draw(axm)
    axm.axis("off")
    figm.subplots_adjust(left=0, right=1, top=1, bottom=0)
    figm.savefig(FIG / f"mark_{name}.svg", facecolor=BG)
    plt.close(figm)


_pv = panel[panel.converged]
_mark("ch2", lambda a: [a.plot(g.sort_values("date").date, g.sort_values("date").price_gp,
                              color=CONTEXT, lw=0.5)
                        for _, g in _pv.groupby("world")])
_mark("ch3", lambda a: a.bar(range(4), [454, 4532, 17615, 18057], color=[CONTEXT] * 3 + [ACCENT],
                             width=0.62))
_mark("ch4", lambda a: a.plot(idx.date, idx.ew_price, color=ACCENT, lw=1.6))
_mark("ch5", lambda a: a.bar(range(len(band)), band.closure_pp,
                             color=[NEUTRAL if v < 0 else ACCENT for v in band.closure_pp],
                             width=0.62))
_mark("ch6", lambda a: [a.plot([0, 1, 2, 3], [1, 1.02, 1.05, 1.09], color=ACCENT, lw=1.6),
                        a.fill_between([0, 1, 2, 3], [1, .94, .88, .82], [1, 1.10, 1.22, 1.36],
                                       color=T10["orange"], alpha=.22, lw=0)])
_mark("ch7", lambda a: a.hist(ts.ret_sd_pct, bins=22, color=CONTEXT))
_mark("ch8", lambda a: a.plot(range(24), np.linspace(0, 1, 24) * 0 + 0.5, color=CONTEXT, lw=0.6))

# ================================================================ SA panels
# Small multiples must share a scale, or a quiet world is stretched to fill its panel and
# reads as though it were as turbulent as one that tripled. But a single scale across all 34
# would be dominated by the launch worlds: they begin near 1,200 GP and rise by a factor of
# thirty, which would compress every established world into a sliver.
#
# So the panels use TWO shared scales, one per comparable group:
#   - worlds that already existed when collection began (n=23) span barely 2x, so a LINEAR
#     scale is used and their ordinary 10-15% swings are legible;
#   - worlds launched during collection (n=11) span nearly 40x, so a LOG scale is used, on
#     which a given percentage move occupies the same height in every panel.
# Each group is internally comparable, which is the property that matters; the appendix
# states plainly that the two groups are not on the same scale as each other.
# Group assignment is made from each world's OWN observed data, not from its creation date.
# Several worlds created inside the window entered the archive only after they had already
# converged - Etebra was created in Feb 2023 but first observed in Aug 2025 at 36,487 GP, with
# no price-discovery phase in the record at all. Putting those on the launch scale would
# compress them for no reason. The rule: a world belongs to the mature-band group if its
# entire observed history sits at or above the mature-band floor, defined as the lowest price
# ever recorded on a world that predates the archive. The two groups are well separated - the
# lowest mature-band world bottoms at 31,250 GP and the highest converging world at 22,028 -
# so the split does not depend on where exactly the threshold is placed.
WIN_START = panel.date.min()
_created = dict(zip(bw.world, bw.created))
_hist = {g["world"]: panel[panel.world == g["world"]].price_gp for g in fcj}
MATURE_FLOOR = min(v.min() for w, v in _hist.items() if _created[w] < WIN_START)

SA_EST = [g for g in fcj if _hist[g["world"]].min() >= MATURE_FLOOR]
SA_NEW = [g for g in fcj if _hist[g["world"]].min() < MATURE_FLOOR]
XW_MEAN = float(idx.ew_price.dropna().iloc[-1])
SA_T0 = panel.date.max()


def _price_span(group):
    ws = [g["world"] for g in group]
    px = panel[panel.world.isin(ws)].price_gp
    return float(px.min()), float(px.max())


EST_LO, EST_HI = _price_span(SA_EST)
EST_HI = max(EST_HI, max(g["6m"]["p90"] for g in SA_EST))
EST_LO, EST_HI = EST_LO * 0.93, EST_HI * 1.06
NEW_LO, NEW_HI = _price_span(SA_NEW)
NEW_LO, NEW_HI = NEW_LO * 0.75, NEW_HI * 1.30
EST_TICKS = [t for t in range(20000, 70001, 10000) if EST_LO < t < EST_HI]
NEW_TICKS = [t for t in (1000, 3000, 10000, 30000) if NEW_LO < t < NEW_HI]


def sa_panel(f, log, lo, hi, ticks, xlo):
    w = f["world"]
    s_ = panel[panel.world == w].sort_values("date")
    fig, ax = plt.subplots(figsize=(3.9, 1.45))
    ax.axhline(XW_MEAN, color=CONTEXT, ls=":", lw=HAIR * 1.4, zorder=2)
    ax.plot(s_.date, s_.price_gp, color=T10["blue"], lw=0.9, zorder=4)
    xs = [SA_T0] + [SA_T0 + pd.Timedelta(days=d) for d in H.values()]
    ax.fill_between(xs, [f["last_price"]] + [f[k]["p10"] for k in H],
                    [f["last_price"]] + [f[k]["p90"] for k in H],
                    color=T10["orange"], alpha=.22, lw=0, zorder=3)
    ax.plot(xs, [f["last_price"]] + [f[k]["p50"] for k in H], color=T10["orange"],
            lw=1.0, ls="--", zorder=5)
    if log:
        ax.set_yscale("log")
        ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylim(lo, hi)
    ax.set_yticks(ticks)
    ax.yaxis.set_major_formatter(gpfmt)
    ax.set_xlim(xlo, SA_T0 + pd.Timedelta(days=200))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.grid(False)
    ax.set_axisbelow(True)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(labelsize=6.2, length=0, colors=MUTED)
    fig.subplots_adjust(left=0.155, right=0.995, top=0.845, bottom=0.155)
    fig.text(0.155, 0.995, w, ha="left", va="top", fontsize=8.0,
             fontweight=W_TITLE, color=INK)
    # Vector first here too; the 2x PNG is a review copy and a non-vector fallback.
    fig.savefig(FIG / "sa" / f"{w}.svg", facecolor="white")
    fig.savefig(FIG / "sa" / f"{w}.png", facecolor="white", dpi=200)
    plt.close(fig)


# ================================================================ 26 venue map
# A schematic, not an estimate. Its job is to make the study's perimeter explicit: a Tibia Coin
# can be sold in more than one place, and the reader should see at a glance which one this
# report prices. The Char Bazaar is deliberately absent - coins are spent there, not sold, so
# it is a demand sink rather than a competing venue.
VN = R["venues"]
TIB_SUPPLY = VN["token"]["total_supply"]
VENUES = [
    ("In-game Market", "settles in gold pieces", "2% per offer,\ncapped at 1,000,000 GP",
     "instant on match", "none - CipSoft holds\nboth sides", True),
    ("Tibia Token", "settles on BNB Smart Chain", "service fee in TC,\nplus chain gas",
     "minutes", "chain, wallet and\nexchange risk", False),
    ("Resellers / OTC", "settles in fiat", "dealer spread and\npayment-rail cost",
     "seconds on instant rails", "borne by the trader,\npriced as reputation", False),
]
fig, ax = plt.subplots(figsize=(7.2, 3.5))
ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.axis("off")
ax.text(50, 99, "TIBIA COIN", ha="center", va="top", fontsize=9.4,
        fontweight=W_TITLE, color=INK)
ax.text(50, 91, "an account-level asset, not bound to any world", ha="center", va="top",
        fontsize=6.8, color=MUTED)
xs = [17, 50, 83]
ax.plot([50, 50], [85, 79], color=CONTEXT, lw=HAIR * 2, zorder=1)
ax.plot([xs[0], xs[-1]], [79, 79], color=CONTEXT, lw=HAIR * 2, zorder=1)
for x, (name, settle, cost, speed, risk, observed) in zip(xs, VENUES):
    ax.plot([x, x], [79, 73], color=CONTEXT, lw=HAIR * 2, zorder=1)
    ax.add_patch(plt.Rectangle((x - 14, 61), 28, 12,
                               facecolor=ACCENT if observed else "#EDEDED",
                               edgecolor="none", zorder=2))
    ax.text(x, 69, name, ha="center", va="center", fontsize=8.0, fontweight=W_TITLE,
            color="white" if observed else INK, zorder=3)
    ax.text(x, 64, settle, ha="center", va="center", fontsize=6.4,
            color="#DCE8F2" if observed else MUTED, zorder=3)
    for i, (lab, val) in enumerate([("Cost", cost), ("Speed", speed),
                                    ("Counterparty risk", risk)]):
        y = 52 - i * 15
        ax.text(x, y, lab.upper(), ha="center", va="top", fontsize=5.7, color=MUTED,
                fontweight=W_TITLE)
        ax.text(x, y - 4.6, val, ha="center", va="top", fontsize=6.6, color=INK)
ax.text(xs[0], 4, "priced in this report", ha="center", va="center", fontsize=6.8,
        fontweight=W_TITLE, color=ACCENT)
for x in xs[1:]:
    ax.text(x, 4, "outside this report's data", ha="center", va="center", fontsize=6.8,
            color=MUTED)
finish(fig, "fig26_venue_map.png",
       "A coin can be sold three ways; this report prices one of them",
       "Settlement venues for a Tibia Coin, and the friction each imposes",
       "Sources: documented Market mechanics; Tibia Token Service Agreement (tibia.com); "
       "TibiaToken contract 0x111B95C2b65CbA53aB4E0AaDA12f55985045E446, BNB Smart Chain.",
       f"Schematic, not an estimate. The three venues are not perfect substitutes - they "
       f"differ in settlement asset, speed and who carries counterparty risk - so a seller "
       f"picks the lowest effective cost rather than the best technology. The in-game Market "
       f"is the only venue this study observes, and every price, band and forecast in this "
       f"report is therefore a within-venue result. The token venue is measurable in one "
       f"respect: {TIB_SUPPLY:,.0f} TIB existed at block {VN['token']['block']:,}, each "
       f"corresponding to "
       f"a Tibia Coin held outside the in-game system.", outdir=FIG)


# ================================================================ 27 fundamentals skill
# The whole fundamentals study in one exhibit: out-of-sample skill against a random walk, by
# what is being predicted and how far ahead. Above zero is a model that beats the benchmark.
ms = pd.read_csv(P / "model_summary.csv")
ms = ms[ms.model != "RandomWalk"]
ORDER = ["Ridge", "ElasticNet", "RandomForest", "XGBoost", "LightGBM", "MovingAvg"]
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.3), sharey=True)
for ax, kind, ttl in zip(axs, ("ret", "rel"),
                         ("The price level", "The price relative to other worlds")):
    sub = ms[ms.target == kind]
    xs = np.arange(len(ORDER))
    for j, h in enumerate([1, 7, 30]):
        v = [sub[(sub.model == m) & (sub.horizon == h)].r2_oos.mean() for m in ORDER]
        ax.bar(xs + (j - 1) * 0.27, v, width=0.25, zorder=3,
               color=[T10["blue"], T10["orange"], T10["green"]][j],
               label=f"{h}d" if kind == "ret" else None)
    win = sub[sub.beats_rw == True]
    for _, r in win.iterrows():
        ax.scatter([ORDER.index(r.model) + ([1, 7, 30].index(r.horizon) - 1) * 0.27],
                   [r.r2_oos + 0.012], marker="*", s=70, color=INK, zorder=5)
    ax.axhline(0, color=INK, lw=HAIR * 2, zorder=4)
    hgrid(ax, nbins=4)
    ax.set_xticks(xs)
    ax.set_xticklabels([m.replace("Random", "Random ").replace("Elastic", "Elastic ")
                        .replace("Moving", "Moving ").replace(" ", chr(10), 1)
                        for m in ORDER], fontsize=6.2)
    ax.set_title(ttl, fontsize=8.0, color=INK, fontweight=W_TITLE, pad=6)
axs[0].set_ylabel("Out-of-sample R² vs random walk")
axs[0].set_ylim(-0.65, 0.12)
axs[0].legend(frameon=False, fontsize=LEG_FS, loc="lower left", ncol=3,
              handletextpad=.4, columnspacing=.9)
FR = json.load(open(P / "fundamentals_results.json"))
# The sentence below is about one specific model, so bind that row rather than
# iloc[0], which is the 1-day ElasticNet and carries a different R-squared.
_rf7 = ms.query("target == 'rel' and horizon == 7 and model == 'RandomForest'").iloc[0]
finish(fig, "fig27_fundamentals_skill.png",
       "Fundamentals do not make the level predictable, and barely move the relative price",
       "Out-of-sample R² against a random walk; above zero beats the benchmark",
       "Sources: price archive item_id 22118; tibiamaps/tibia-kill-stats; GuildStats.eu "
       "/online-counter. Expanding-origin walk-forward, 6 folds, horizon purged.",
       f"Bars below the line are models that lose to predicting no change. On the level, every "
       f"model loses at every horizon. On the relative price the picture is better but small: "
       f"of {FR['n_comparisons']} model-horizon comparisons, "
       f"{FR['n_beating_rw_after_bh']} survive a Benjamini-Hochberg correction at 5% - the "
       f"starred bars, all of them on the relative price. The strongest at seven days is a "
       f"random forest with an out-of-sample R² of {_rf7.r2_oos:.3f}, which beat the random "
       f"walk in {int(_rf7.folds_better)} of {int(_rf7.folds)} folds. "
       f"61 converged worlds, 2025-12-05 to 2026-07-30.", outdir=FIG, left=0.11)


# ================================================================ 28 scenario fan
# The forecast distribution as a picture: where the index is, where the simulated paths go, and
# what share of them land in each band. This is the exhibit the positioning section needs.
SCN = json.load(open(P / "fundamentals_results.json"))["scenarios"]
sb = pd.DataFrame(SCN["bands"])
lvl0 = SCN["level"]
hh = {"1 month": 30, "3 months": 91, "6 months": 182}
qs = {"3 months": None}
fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.2, 3.3),
                               gridspec_kw={"width_ratios": [1.45, 1]})
hist = idx.dropna(subset=["ew_price"]).tail(200)
axA.plot(hist.date, hist.ew_price, color=T10["blue"], lw=1.4, zorder=4)
last_d = hist.date.iloc[-1]
# Fan built from the same quantiles the scenario table reports.
band_q = {"1 month": (38465, 41604), "3 months": (37236, 42916), "6 months": (36163, 44238)}
med_q = {"1 month": 40010, "3 months": 40040, "6 months": 40029}
xs = [last_d] + [last_d + pd.Timedelta(days=v) for v in hh.values()]
lo = [lvl0] + [band_q[k][0] for k in hh]
hi = [lvl0] + [band_q[k][1] for k in hh]
md = [lvl0] + [med_q[k] for k in hh]
axA.fill_between(xs, lo, hi, color=T10["blue"], alpha=.16, lw=0, zorder=2)
axA.plot(xs, md, color=T10["blue"], lw=1.2, ls="--", zorder=3)
axA.axhline(lvl0, color=CONTEXT, lw=HAIR * 1.6, zorder=1)
hgrid(axA, nbins=4)
axA.yaxis.set_major_formatter(gpfmt)
axA.set_ylabel("GP per TC")
datefmt(axA, maxticks=5)
label_line(axA, xs[-1], hi[-1], f"  80% band\n  {hi[-1]:,.0f}", T10["blue"], dx=3, fs=6.6)
label_line(axA, xs[-1], lo[-1], f"  {lo[-1]:,.0f}", T10["blue"], dx=3, fs=6.6)
axA.annotate(f"today {lvl0:,.0f}", xy=(last_d, lvl0), xytext=(-6, -12),
             textcoords="offset points", ha="right", fontsize=6.8, color=INK,
             fontweight=W_TITLE)
axA.set_title("The index and its 80% forecast band", fontsize=8, color=INK,
              fontweight=W_TITLE, pad=6)

ypos = np.arange(len(sb))
for j, (k, col) in enumerate(zip(hh, (T10["blue"], T10["orange"], T10["green"]))):
    axB.barh(ypos + (j - 1) * 0.26, sb[k].values * 100, height=0.24, color=col,
             zorder=3, label=k)
hgrid(axB, nbins=None)
axB.set_yticks(ypos)
axB.set_yticklabels(sb.band.values, fontsize=6.4)
axB.invert_yaxis()
axB.set_xlabel("Probability the index finishes here (%)")
axB.legend(frameon=False, fontsize=LEG_FS, loc="lower right", handletextpad=.4)
axB.set_title("Where it lands, by horizon", fontsize=8, color=INK, fontweight=W_TITLE, pad=6)
finish(fig, "fig28_scenarios.png",
       "Three months out, the most likely outcome is the price it is at now",
       "Chain-linked index with its simulated distribution, and the probability of each range",
       SRC_PX,
       f"Block bootstrap of {SCN['n_paths']:,} paths in ten-day blocks, so volatility "
       f"clustering and fat tails survive resampling, propagated at the shrunk and capped drift "
       f"of {SCN['drift_daily_pct']:+.4f}% per day. The bands are computed from the simulated "
       f"paths, not assigned. The probability the index sits below today's level in three "
       f"months is {SCN['levels']['prob_below_current_3m']:.0%} - a near-symmetric "
       f"distribution is what an unforecastable level looks like.", outdir=FIG, left=0.09)

# ================================================================ 29 live predictions
# What the shipped model actually says today, world by world, with its calibrated interval.
lp_all = pd.read_csv(P / "latest_predictions.csv").sort_values("predicted_change_pct")
N_SHOW = 12
lp = pd.concat([lp_all.head(N_SHOW), lp_all.tail(N_SHOW)]).sort_values("predicted_change_pct")
fig, ax = plt.subplots(figsize=(7.2, 3.9))
yy = np.arange(len(lp))
cols = [T10["orange"] if o else CONTEXT for o in lp.outside_band]
ax.barh(yy, lp.predicted_change_pct, height=.62, color=cols, zorder=3)
ax.errorbar(lp.predicted_change_pct, yy,
            xerr=[lp.predicted_change_pct - lp.low80_pct,
                  lp.high80_pct - lp.predicted_change_pct],
            fmt="none", ecolor=MUTED, elinewidth=.5, capsize=0, zorder=4, alpha=.5)
ax.axvline(0, color=INK, lw=HAIR * 2, zorder=5)
hgrid(ax, nbins=None)
ax.set_yticks(yy)
ax.set_yticklabels(lp.world, fontsize=6.4)
ax.set_xlabel("Predicted 7-day change in the world's price relative to the market (%)")
ax.set_ylim(-1, len(lp))
ax.annotate("cheap relative to the market;\nthe model expects it to catch up",
            xy=(lp.predicted_change_pct.min() * 0.95, len(lp) - 2.5), fontsize=6.6,
            color=T10["orange"], fontweight=W_TITLE, ha="left", va="center")
ax.annotate("expensive relative to the market;\nexpected to give ground",
            xy=(lp.predicted_change_pct.max() * 0.95, 1.5), fontsize=6.6,
            color=MUTED, ha="right", va="center")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(facecolor=T10["orange"], label="outside the 1.79% band"),
                   Patch(facecolor=CONTEXT, label="inside the band")],
          frameon=False, fontsize=LEG_FS, loc="lower right")
finish(fig, "fig29_live_predictions.png",
       "What the model says today: every world ranked by expected convergence",
       "Predicted 7-day change in relative position, with an 80% conformal interval",
       SRC_PX,
       f"Output of models/deviation_model.pkl, the artefact shipped with this report. Bars are "
       f"point predictions and whiskers the 80% interval, whose width was calibrated on held-"
       f"out residuals rather than assumed. Worlds outside the arbitrage band are highlighted; "
       f"Section 7.5.3 gives the rule for when a gap is wide enough to act on. The {N_SHOW} "
       f"most and least favoured of {len(lp_all)} worlds are shown; the full ranking is in "
       f"latest_predictions.csv. The model "
       f"predicts relative position only - it emits no forecast of the price level, because "
       f"Section 6.6.2 finds none is supportable.", outdir=FIG, left=0.13)


# ================================================================ 30 who is trading
# The counterintuitive result of the participant decomposition, which needs a picture: the order
# book is dominated by large orders while the trade that actually happens is consumption-sized.
PART = json.load(open(P / "fundamentals_results.json"))["participants"]
pb = pd.DataFrame(PART["bands"])
px_ = PART["executable"]
fig, (axL, axR) = plt.subplots(1, 2, figsize=(7.2, 3.2),
                               gridspec_kw={"width_ratios": [1.3, 1]})
yy = np.arange(len(pb))
axL.barh(yy + 0.19, pb.share_of_offers * 100, height=.34, color=CONTEXT, zorder=3,
         label="share of orders")
axL.barh(yy - 0.19, pb.share_of_tc * 100, height=.34, color=ACCENT, zorder=3,
         label="share of coins")
hgrid(axL, nbins=None)
axL.set_yticks(yy)
axL.set_yticklabels([b.replace(" ", "\n", 1) for b in pb.band], fontsize=6.3)
axL.invert_yaxis()
axL.set_xlabel("Percent")
axL.legend(frameon=False, fontsize=LEG_FS, loc="center right", handletextpad=.4,
           bbox_to_anchor=(1.0, 0.62))
axL.set_title("Small orders are most of the book and almost none of the coins",
              fontsize=7.6, color=INK, fontweight=W_TITLE, pad=6)
for i, r in pb.iterrows():
    axL.annotate(f"{r.share_of_tc * 100:.1f}%", xy=(r.share_of_tc * 100, i - 0.19),
                 xytext=(3, 0), textcoords="offset points", va="center", fontsize=6.2,
                 color=INK)

_nw_book = int(pd.read_csv(P / "order_books.csv").world.nunique())
vals = [px_["median_resting_bid_depth_tc"], px_["near_mid_bid_tc"] / _nw_book,
        px_["median_executed_per_world_day_tc"]]
labs = ["resting bid depth\nper world", "bids within 5%\nof the mid", "executed\nper day"]
axR.bar(np.arange(3), vals, width=.55, zorder=3,
        color=[CONTEXT, T10["blue"], ACCENT])
axR.set_yscale("log")
hgrid(axR, nbins=None)
axR.set_xticks(np.arange(3))
axR.set_xticklabels(labs, fontsize=6.3)
axR.set_ylabel("TC, log scale")
for i, v in enumerate(vals):
    axR.annotate(f"{v:,.0f}", xy=(i, v), xytext=(0, 4), textcoords="offset points",
                 ha="center", fontsize=6.6, color=INK, fontweight=W_TITLE)
axR.set_title("What rests, and what actually trades", fontsize=7.6, color=INK,
              fontweight=W_TITLE, pad=6)
finish(fig, "fig30_participants.png",
       "The book holds weeks of intent; a day's trade is one ordinary order",
       "Live order book by order size, and resting depth against executed volume",
       SRC_MB + " Executed volumes from the price archive, item_id 22118.",
       f"Left: orders under 500 TC - the size of a month of premium - are "
       f"{pb.iloc[0].share_of_offers:.0%} of orders but {pb.iloc[0].share_of_tc:.1%} of coins, "
       f"while orders above 10,000 TC are {pb.iloc[3].share_of_tc:.0%} of coins. Right: the "
       f"median world rests {px_['median_resting_bid_depth_tc']:,.0f} TC of bids and executes "
       f"{px_['median_executed_per_world_day_tc']:,.0f} TC a day - the book is "
       f"{px_['resting_over_daily_flow']:,.0f} times a day's flow, and "
       f"{px_['share_wholesale_bids_20pct_below_mid']:.0%} of wholesale bids sit more than 20% "
       f"below the mid where they cannot fill. A resting order is an intention, not a trade: "
       f"a consumer buying at the going price never appears in the book at all. Executed "
       f"volumes are lot counts converted at the 25-coin lot the Market enforces.",
       outdir=FIG, left=0.155)


# ================================================================ 31 fold stability
# The most important caveat in the fundamentals study, and the hardest to see in a table: the
# edge is concentrated early and gone late. An average across folds hides that entirely.
mc = pd.read_csv(P / "model_comparison.csv")
rf_ = mc[(mc.target == "rel") & (mc.model == "RandomForest")]
ms_ = pd.read_csv(P / "market_states.csv", parse_dates=["date"])
fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.2, 3.1),
                               gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.30})
for h, col in zip((1, 7, 30), (T10["blue"], T10["orange"], T10["green"])):
    g = rf_[rf_.horizon == h].sort_values("fold")
    axA.plot(g.fold, g.r2_oos, marker="o", ms=4, lw=1.4, color=col, zorder=3,
             label=f"{h}-day")
axA.axhline(0, color=INK, lw=HAIR * 2, zorder=4)
hgrid(axA, nbins=4)
axA.set_xlabel("Walk-forward fold, earliest to latest")
axA.set_ylabel("Out-of-sample R²")
axA.legend(frameon=False, fontsize=LEG_FS, loc="upper right", handletextpad=.5)
axA.set_title("Skill by fold, not averaged", fontsize=7.8, color=INK,
              fontweight=W_TITLE, pad=6)
axA.annotate("the average is carried\nby the first folds", xy=(0.30, 0.06),
             xycoords="axes fraction", fontsize=6.5, color=MUTED)

# The regime path, so the reader can see what "four states lasting a fortnight" looks like.
STCOL = [T10["blue"], CONTEXT, T10["orange"], T10["red"]]
for st in sorted(ms_.state.unique()):
    m = ms_.state == st
    axB.scatter(ms_.date[m], ms_.ret[m] * 100, s=5, color=STCOL[st % len(STCOL)],
                zorder=3, linewidths=0, label=f"state {st}")
axB.axhline(0, color=INK, lw=HAIR * 1.6, zorder=2)
hgrid(axB, nbins=4)
datefmt(axB, maxticks=5)
axB.set_ylabel("Daily market return (%)")
axB.legend(frameon=False, fontsize=LEG_FS, ncol=2, loc="upper left", handletextpad=.2,
           columnspacing=.8, markerscale=1.6)
axB.set_title("Four states, about a fortnight each", fontsize=7.8, color=INK,
              fontweight=W_TITLE, pad=6)
FR2 = json.load(open(P / "fundamentals_results.json"))
_st = {r["horizon"]: r for r in FR2["fold_stability"]}
finish(fig, "fig31_stability.png",
       "The edge is real early and absent late, which the average hides",
       "Out-of-sample skill fold by fold, and the market states the model was trading through",
       SRC_PX,
       f"Left: the random forest on the cross-world relative return. At seven days it runs "
       f"{_st[7]['first_fold_r2']:+.3f} in the first fold and {_st[7]['last_fold_r2']:+.3f} in "
       f"the last; at thirty the average of {_st[30]['mean_r2']:+.3f} falls to "
       f"{_st[30]['mean_excl_first']:+.3f} once the first fold is removed. The rank correlation "
       f"between fold order and skill is negative at every horizon. With five or six folds that "
       f"trend is not itself significant, so decay and a favourable early sample cannot be "
       f"separated - which is the reason Section 6.6.3 warns against reading the averages as "
       f"what the next quarter would deliver. Right: the {FR2['regimes']['k']} states a Gaussian "
       f"hidden Markov model selects by BIC, with mean persistence "
       f"{FR2['regimes']['persistence']:.2f}.", outdir=FIG, left=0.10)


EST_XLO = panel[panel.world.isin([g["world"] for g in SA_EST])].date.min()
NEW_XLO = panel[panel.world.isin([g["world"] for g in SA_NEW])].date.min()
for f in SA_EST:
    sa_panel(f, False, EST_LO, EST_HI, EST_TICKS, EST_XLO)
for f in SA_NEW:
    sa_panel(f, True, NEW_LO, NEW_HI, NEW_TICKS, NEW_XLO)

_clip_est = sorted(g["world"] for g in SA_EST if g["6m"]["p90"] > EST_HI)
_clip_new = sorted(g["world"] for g in SA_NEW if g["6m"]["p90"] > NEW_HI)
print(f"SA mature band (n={len(SA_EST)}): linear {EST_LO:,.0f}-{EST_HI:,.0f} GP"
      + (f"; fans clipped: {', '.join(_clip_est)}" if _clip_est else "; no fans clipped"))
print(f"SA converging  (n={len(SA_NEW)}): log    {NEW_LO:,.0f}-{NEW_HI:,.0f} GP"
      + (f"; fans clipped: {', '.join(_clip_new)}" if _clip_new else "; no fans clipped"))
print(f"  mature-band floor {MATURE_FLOOR:,.0f} GP; converging: "
      + ", ".join(sorted(g["world"] for g in SA_NEW)))

def strategy_window() -> str:
    """The window the strategy exhibits are actually estimated on.

    SRC_PX states the archive span, which is right for the price figures and wrong here: the
    cross-world deviation needs at least ten worlds on a date, so estimation starts well after
    the archive does.
    """
    _c = pd.read_csv(P / "strategy_grid.csv")
    _p = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
    _bw = pd.read_csv(P / "world_summary.csv")
    _d = _p[_p.world.isin(set(_bw.query("converged").world))].dropna(subset=["price_gp"])
    _n = _d.groupby("date").world.nunique()
    _ok = _n[_n >= 10]
    return (f"Estimated on converged worlds from {_ok.index.min():%d %b %Y} to "
            f"{_ok.index.max():%d %b %Y}, the dates carrying at least ten observed worlds.")


# ---------------------------------------------------------------- strategy: cost vs horizon
# The argument is one crossing: gross return grows with the holding period while the round
# trip does not, so the two lines cross once and everything to the right of that point is a
# trade. Drawing it as lines rather than a table is what makes the crossing legible.
_SG = pd.read_csv(P / "strategy_grid.csv")
_top = (_SG[(_SG.cost_basis == "above the fee cap") & (_SG.decile == _SG.decile.max())]
        .sort_values("horizon"))
_mid = (_SG[(_SG.cost_basis == "above the fee cap") & (_SG.decile == 5)]
        .sort_values("horizon"))
_cost = float(_top.cost_pct.iloc[0])

fig, ax = plt.subplots(figsize=(7.2, 3.5))
ax.plot(_top.horizon, _top.gross_pct, color=T10["blue"], lw=1.9, zorder=4,
        marker="o", ms=3.4)
ax.plot(_mid.horizon, _mid.gross_pct, color=MUTED, lw=1.4, zorder=3, marker="o", ms=2.8)
ax.axhline(_cost, color=T10["red"], ls="--", lw=HAIR * 1.8, zorder=2)
ax.fill_between(_top.horizon, _cost, _top.gross_pct,
                where=(_top.gross_pct.values > _cost), color=T10["blue"], alpha=0.10, zorder=1)
label_line(ax, _top.horizon.iloc[-1], _top.gross_pct.iloc[-1],
           "strongest decile", T10["blue"], dx=6)
label_line(ax, _mid.horizon.iloc[-1], _mid.gross_pct.iloc[-1],
           "median gap", MUTED, dx=6)
label_line(ax, _top.horizon.max() * 1.02, _cost, f"round trip {_cost:.2f}%", T10["red"],
           dx=6, dy=9)
hgrid(ax, grid=False)
ax.set_xlabel("Holding period (days)")
ax.set_ylabel("Gross return of the trade (%)")
ax.set_xticks(list(_top.horizon))
ax.set_xlim(0, _top.horizon.max() * 1.22)
finish(fig, "fig32_strategy_horizon.png",
       "The cost is paid once, so the trade becomes profitable by being held",
       "Gross return on the cross-world convergence trade against a flat round-trip cost",
       strategy_window(),
       "Deviations past the estimated band, sorted into deciles of size. The shaded area is "
       "return kept after the cheapest documented round trip. The median-gap line shows the "
       "same trade on an ordinary signal, which never clears the cost. Figures are means over "
       "overlapping windows; significance is assessed with Newey-West standard errors in the "
       "accompanying table, not from this chart.", outdir=FIG)

# ---------------------------------------------------------- strategy: where evidence runs out
# The net return rises with the holding period and so does the apparent significance, while the
# number of independent windows collapses. Those two facts pull in opposite directions and a
# reader who sees only the first will over-trust the quarterly figure. Plotting them together
# is the argument: the bars grow, the sample behind them does not.
_HD = pd.read_csv(P / "strategy_holdout.csv")
_ho = _HD[_HD.period == "holdout"].sort_values("horizon")
_tr = _HD[_HD.period == "train"].sort_values("horizon")

fig, (axA, axB) = plt.subplots(1, 2, figsize=(7.4, 3.1), gridspec_kw={"wspace": 0.30})
x = np.arange(len(_ho))
axA.bar(x - 0.19, _tr.net_pct, width=0.36, color=CONTEXT, zorder=3, label="train")
axA.bar(x + 0.19, _ho.net_pct, width=0.36, color=T10["blue"], zorder=3, label="holdout")
axA.axhline(0, color=MUTED, lw=HAIR * 1.4, zorder=2)
axA.set_xticks(x); axA.set_xticklabels([f"{int(h)}d" for h in _ho.horizon])
axA.set_ylabel("Net of cost (%)")
axA.set_xlabel("Holding period")
hgrid(axA, grid=False)
for _i, (_t, _h) in enumerate(zip(_tr.net_pct.values, _ho.net_pct.values)):
    axA.annotate(f"{_t:.1f}", xy=(_i - 0.19, _t), xytext=(0, 3), textcoords="offset points",
                 ha="center", fontsize=6.4, color=MUTED)
    axA.annotate(f"{_h:.1f}", xy=(_i + 0.19, _h), xytext=(0, 3), textcoords="offset points",
                 ha="center", fontsize=6.4, color=T10["blue"], fontweight=W_TITLE)
axA.set_ylim(0, max(_ho.net_pct.max(), _tr.net_pct.max()) * 1.18)
axA.legend(frameon=False, fontsize=LEG_FS, loc="upper left", handletextpad=.5)
axA.set_title("The payoff rises with the horizon", fontsize=7.6, color=INK,
              fontweight=W_TITLE, pad=6)

axB.bar(x, _ho.n_effective, width=0.5, color=T10["red"], zorder=3)
axB.set_yscale("log")
axB.set_xticks(x); axB.set_xticklabels([f"{int(h)}d" for h in _ho.horizon])
axB.set_xlabel("Holding period")
axB.set_ylabel("Independent windows in the holdout")
hgrid(axB, nbins=None)
for i, v in enumerate(_ho.n_effective):
    axB.annotate(f"{int(v)}", xy=(i, v), xytext=(0, 4), textcoords="offset points",
                 ha="center", fontsize=6.8, color=INK, fontweight=W_TITLE)
axB.set_title("The evidence behind it does not", fontsize=7.6, color=INK,
              fontweight=W_TITLE, pad=6)
finish(fig, "fig33_holdout.png",
       "The quarterly figure is the largest and the least supported",
       "Net return of the top-decile convergence trade, and the out-of-sample sample behind it",
       strategy_window(),
       "Left: mean net return after the cheapest documented round trip, in the training period "
       "and in a holdout that was never inspected while the rule was formed; only the decile "
       "cutoff crosses the split. Right: the holdout's effective sample, being its length "
       "divided by the holding period, since daily observations of an h-day return share h-1 "
       "days of data. At ninety-one days the holdout contains a single independent window, so "
       "the t-statistic reported for it carries no information whatever its size.",
       outdir=FIG)

import json as _json
from chartstyle import MANIFEST as _MF
_json.dump(_MF, open(FIG / "manifest.json", "w"), indent=1)
print(f"manifest: {len(_MF)} exhibits")
print(f"figures written: {len(list(FIG.glob('*.png')))} main + "
      f"{len(list((FIG / 'sa').glob('*.png')))} SA panels")
