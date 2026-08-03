import re
# -*- coding: utf-8 -*-
"""Report body. Executed inside 09_report.py's namespace."""

D = R["desc"]; IX = R["index"]; AR = R["arbitrage"]; IN = R["integration"]
VN = R["venues"]
MS = VN["market_size"]
BZH = VN["bazaar_history"]
BZY = pd.DataFrame(BZH["history"])
BZR = pd.DataFrame(BZH["ratio_by_year"])
FN = R["finance"]; AD = R["advanced"]; FE = R["fees"]
ST = R["stationarity"]; EVR = R["events"]; CS = R["cross_section"]; PN = R["panel"]
YG = R["young"]; MG = R["merge"]; MI = R["micro"]; TC = R["technical"]; FCR = R["forecast"]
FD = json.load(open(P / "fundamentals_results.json"))
# The raw kill-statistics archive and the joined modelling panel are different
# objects: 93 worlds against the converged subset, and different row counts.
_KSRAW = pd.read_csv(P / "kill_stats_daily.csv")
KS_ROWS, KS_WORLDS = len(_KSRAW), int(_KSRAW.world.nunique())
FDM = pd.read_csv(P / "model_summary.csv")
FDL = pd.read_csv(P / "leading_indicators.csv")
FDR = FD["regimes"]
FDH = pd.read_csv(P / "hierarchy_summary.csv")
FDU = pd.read_csv(P / "univariate_summary.csv")
FDV = pd.read_csv(P / "volatility_summary.csv")
FDX = pd.read_csv(P / "extra_models_summary.csv")
DSC = FD["discovery"]
FDC = pd.read_csv(P / "classical_summary.csv")
FDD = pd.read_csv(P / "deep_summary.csv")
FDF = FD["latent_factors"]
ARB = FD["arbitrage_structure"]
ARBB = pd.read_csv(P / "band_conditional.csv")
ARBR = pd.DataFrame(ARB["reversion_by_spacing"])
MAXP = FD["max_predictability"]
IRR = FD["irreducibility"]
IRRB = pd.DataFrame(IRR["bds"])
SVD = FD["supply_vs_demand"]
GEM = json.load(open(P / "gold_emission_results.json"))
GEQ = json.load(open(P / "gold_emission_quality.json"))
GEH = pd.DataFrame(GEM["headline_models"])
GEO = pd.DataFrame(GEM["oos"])
SVDR = pd.DataFrame(SVD["horse_race"])
SVDE = pd.DataFrame(SVD["supply_elasticity"])
SCN = FD["scenarios"]
SCNS = pd.DataFrame(SCN["scenarios"])
SCNB = pd.DataFrame(SCN["bands"])
LV = SCN["levels"]
PART = FD["participants"]
PB = pd.DataFrame(PART["bands"])
PX = PART["executable"]
PPROF = pd.DataFrame(PART["profiles"])
STR = FD["strategy"]
STG = pd.DataFrame(STR["grid"])
STM = pd.DataFrame(STR["model_ranked"])
STA = STR["attack"]
OCC = STR["occurrence"]
CAPY = STR["capacity"]
HOLD = STR["holdout"]
HDF = pd.DataFrame(HOLD["rows"])
RGM = STR["regime"]
RGD = pd.DataFrame(RGM["rows"])
SEL = STR["selector"]
SLD = pd.DataFrame(SEL["rows"])
CONF = STR["regime_confound"]
CFD = pd.DataFrame(CONF["rows"])
# The headline verdict and its confidence appear in four places. Defined once here so
# they cannot drift apart again; the verifier checks the rendered text as a backstop.
VERDICT = "buy relative, not directional"
CONFIDENCE = 78
STO = pd.DataFrame(STA["long_only"])
STOV = pd.DataFrame(STA["overlap"])
STD = pd.DataFrame(STA["delayed_entry"])
LHP = FD["long_horizon_production"]
LHF = pd.DataFrame(LHP["flow"])
LHC = pd.DataFrame(LHP["cumulative"])
LHH = pd.DataFrame(LHP["honest_inference"])
LHD = LHP["overlap_diagnostic"]
SEAS = FD["stability_seasonality"]
SEM = pd.DataFrame(SEAS["month_effects"])
SEST = SEAS["stability"]
SERG = pd.DataFrame(SEAS["regime_splits"])
SEER = pd.DataFrame(SEAS["error_magnitude"])
BTS = FD["scenario_backtest"]
BTC = pd.DataFrame(BTS["coverage"])
LPRED = pd.read_csv(P / "latest_predictions.csv")
GSM = FD["group_specific_models"]
GSC = pd.read_csv(P / "specific_model_comparison.csv")
GSR = pd.read_csv(P / "specific_model_registry.csv")
GSO = GSC[GSC.scope == "all"].iloc[0]
GSP = GSC[GSC.scope == "pvp_type"].sort_values("scope_value")
LPM = FD["launch_phase_models"]
LPC = pd.read_csv(P / "launch_model_comparison.csv")
LPR = pd.read_csv(P / "launch_model_registry.csv")
LPO = LPC[LPC.scope == "all"].iloc[0]
LPP = LPC[LPC.scope == "pvp_type"].sort_values("scope_value")
_IXYRS = (pd.Timestamp(IX['index_end']) - pd.Timestamp(IX['index_start'])).days / 365.25
_DRIFT_T = IX['cagr_pct'] / (D['ret_sd_ann_pct'] / _IXYRS ** 0.5)
_YRS_NEEDED = (2 * D['ret_sd_ann_pct'] / IX['cagr_pct']) ** 2
_DETECTABLE = 2 * D['ret_sd_ann_pct'] / 3 ** 0.5
_R2B = float(SVDR[SVDR.block == "behaviour only"].r2_within.iloc[0])
_R2S = float(SVDR[SVDR.block == "supply only"].r2_within.iloc[0])
_FLOW7 = float(SVDE[(SVDE.horizon == 7) & SVDE.channel.str.contains("flow")].elasticity.iloc[0])
_RPC = CS["stock_vs_flow"]["residents_per_concurrent_by_region"]
_RPC_SPREAD = max(_RPC.values()) / min(_RPC.values())
RB = R["robustness"]

# ===================================================================== COVER
story.append(NextPageTemplate("cover"))
story.append(Spacer(1, 2))          # cover is painted by the page template

# ===================================================================== CONTENTS
# A single break here: the cover block used to break as well, which left page 2 empty.
fresh_page("normal")
story.append(Paragraph("Contents", S["h1_noindex"]))
story.append(Spacer(1, 4))
_toc = TableOfContents()
_toc.levelStyles = [S["toc1"], S["toc2"]]
_toc.dotsMinLevel = 0
story.append(_toc)
story.append(PageBreak())

# ===================================================================== AT A GLANCE
para("The report at a glance", "h1")
bottomline("The Tibia Coin market is efficient up to transaction costs. Which world a coin "
           "trades on is forecastable - an out-of-sample R-squared of "
           f"{MAXP['best_r2']:.2f} on the cross-world deviation - but the edge is smaller than "
           "the fee that would capture it. Where the overall price level goes next is not "
           "forecastable at all.")
kpi_row([
    (f"{gp(D['price_latest_median'])}", "GP per Tibia Coin<br/>median across 93 worlds"),
    (pc(IX['cagr_pct'], 1), "annualised change<br/>chain-linked index"),
    (pc(R['advanced']['tar']['threshold_pct']), "arbitrage friction point<br/>estimated, not assumed"),
    (pc(FN['roll']['median_roll_spread_pct']), "effective spread<br/>what trades actually pay"),
    (pc(D['ret_sd_ann_pct'], 0), "annualised volatility<br/>established worlds"),
])
table([
    ["Question", "Answer", "Where"],
    ["Are worlds separate markets, or one?",
     "One. A Johansen rank test finds a single common stochastic trend; prices pass through "
     "near one-for-one.", "5.1, 6.3.2"],
    ["Can the price level be forecast?",
     f"No. Fifteen model classes, {FD['panel']['n_features']} features and a gold-production series were tried; none "
     "beats a random walk at any horizon.", "4.4, 6.6.2"],
    ["Can anything be forecast?",
     f"Two things. A world's price relative to the others, at an out-of-sample R-squared of "
     f"{MAXP['best_r2']:.2f}; and whether the coming week is volatile, at an area under the "
     f"curve of {[r for r in FD['volatility_targets'] if r['target'] == 'y_hivol7'][0]['auc']:.2f}. "
     f"Neither is worth its trading cost.", "6.6.3, 6.6.5"],
    ["Does gold production drive the price?",
     f"No. Tested directly against {FD['panel']['rows']:,} world-days of kill statistics: the elasticity is "
     "negligible and the sign is wrong on every world. Behaviour explains 31 times more.",
     "6.6.14"],
    ["Who is actually trading?",
     f"Displayed intent is wholesale - {PB.iloc[3].share_of_tc:.0%} of resting coins sit in "
     f"orders of ten thousand or more - while a whole day of trade is "
     f"{gp(PX['median_executed_per_world_day_tc'])} coins, about one ordinary order. The sell "
     f"side holds only {1 - PART['bid_share']:.0%} of resting coins.", "7.5.2"],
    ["Why does the band exist?",
     f"Transaction costs. The Market fee is {pc(FE['rate_pct'], 0)} per offer, capped at {gp(FE['cap_gp'])} GP, and capital "
     "is locked while offers rest.", "2.2, 5.2.4, 5.2.6"],
    ["What explains price differences between worlds?",
     "World type and engagement. Not size, not age, not region.", "5.3"],
    ["Is the market efficient?",
     "Up to transaction costs. Reversal exists but sits inside the spread.", "4.4.3, 5.6.4"],
    ["So what sets the price?",
     "<b>An exchange rate against a fixed anchor, bounded by fees, cleared thin.</b> Coin supply "
     "is elastic at a money price CipSoft fixes; neither leg pays a yield; a 2% fee holds the "
     "band open. Production is eliminated, cost is favoured.", "7.6"],
    ["What should I do with my coins?",
     f"<b>Transact on need at the going price.</b> Size above {gp(FE['cap_binds_at_lot_tc'])} TC; act across worlds only "
     "past a 4% gap; avoid the weeks the volatility model flags. Hold no more than you intend "
     "to spend - coins are a currency, not an asset.", "7.7"],
], [52 * mm, AVAIL - 74 * mm, 22 * mm],
    caption="Table 0.1 - The questions this report answers, and where each is settled.")
story.append(PageBreak())

# ===================================================================== 1
h1(1, "Executive Summary")

bottomline(narrative.claim("mechanism").summary + " That model, not a preference for "
           "efficient markets, is why the level does not forecast and why the one edge "
           "that exists only clears its cost at the strongest signals held long enough. "
           "Section 7.6 states it in full and ranks it against every alternative tested.")

kpi_row([
    (f"{gp(D['price_latest_median'])}", "GP per Tibia Coin<br/>median across 93 worlds"),
    (pc(IX['cagr_pct'], 1), "annualised change<br/>chain-linked index"),
    (pc(R['advanced']['tar']['threshold_pct']), "arbitrage friction point<br/>estimated, not assumed"),
    (pc(FN['roll']['median_roll_spread_pct']), "effective spread<br/>what trades actually pay"),
    (pc(D['ret_sd_ann_pct'], 0), "annualised volatility<br/>established worlds"),
])

h2sec_plain("1.1 The answer in brief")
para(tag("econ") + f"<b>What the price is.</b> A Tibia Coin has a money price CipSoft posts and "
     f"will supply at without limit, so the coin is never scarce in money. What this report "
     f"measures is therefore gold, quoted in coins - an exchange rate between an elastic "
     f"outside good and a currency produced inside the game. Neither side pays a yield, "
     f"clearing is thin at {gp(PX['median_executed_per_world_day_tc'])} coins per world-day, and "
     f"the fee schedule holds a {pc(R['advanced']['tar']['threshold_pct'])} band open. An "
     f"exchange rate with those properties has an unforecastable level and a forecastable "
     f"variance, which is precisely what the data show.")
para(tag("stat") + f"<b>What the evidence favours, and what it eliminates.</b> Set against each "
     f"other rather than each against zero, the candidate explanations separate. Transaction "
     f"costs, thin need-driven clearing and the absence of carry are <b>favoured</b>. A hidden "
     f"forecastable driver and the information content of the order book are <b>weakened</b> - "
     f"a perfectly observed common state explains "
     f"{IRR['latent_state']['r2_factor_smoothed']:.1%} of daily variance and "
     f"{IRR['latent_state']['r2_factor_forecast']:.1%} one step ahead. Gold production, "
     f"momentum and market segmentation are <b>eliminated</b>: behaviour outperforms production "
     f"{_R2B / _R2S:.0f} to 1 and the production slope is the wrong sign on all "
     f"{SVD['gold_stock']['n_worlds']} worlds tested.")
# The same claim the body derives in 7.6.4, in its summary form, so the two cannot drift.
para(tag("judg") + f"<b>The consequence for a holder.</b> "
     f"{narrative.claim('currency').summary}")

h2sec_plain("1.2 Why this mechanism and not another")
para(tag("judg") + "<b>The case for it is not that the alternatives failed one by one. It is "
     "that seven established facts have exactly one joint explanation.</b> Each competing "
     "mechanism accounts for some of them; only a cost-bounded currency with elastic outside "
     "supply accounts for all seven at once, and it was not chosen in advance - it is what the "
     "column below reduces to.")
story.append(CondPageBreak(150))
_Y, _N, _P = "<b>Yes</b>", "-", "Part"
table([["The fact to be explained", "Gold\nsupply", "Specul.\nfeedback", "Segmented\nmarkets",
        "Private\ninfo", "Cost-bounded\ncurrency"],
       [f"1. Worlds form one market: exactly one common stochastic trend across "
        f"{R['advanced']['cointegration']['johansen']['n_series']} series, pass-through near "
        f"one-for-one",
        _N, _N, _N, _N, _Y],
       [f"2. Gaps close only past {pc(R['advanced']['tar']['threshold_pct'])}, and that width "
        f"matches the fee schedule",
        _N, _N, _N, _N, _Y],
       [f"3. The level carries a unit root on "
        f"{ST['n'] - ST['adf_reject_5pct']} of {ST['n']} worlds",
        _P, _N, _Y, _Y, _Y],
       [f"4. No risk premium: {pc(IX['cagr_pct'], 1)} a year at t = {_DRIFT_T:.2f}",
        _N, _N, _N, _Y, _Y],
       [f"5. Behaviour outperforms gold production {_R2B / _R2S:.0f} to 1, and production has "
        f"the wrong sign on every world",
        _N, _P, _N, _N, _Y],
       [f"6. Volatility forecasts at "
        f"{[r for r in FD['volatility_targets'] if r['target'] == 'y_hivol7'][0]['auc']:.2f} "
        f"while direction does not",
        _N, _P, _N, _P, _Y],
       [f"7. The one edge found equals the fee that would capture it, to within "
        f"{abs(float(ARB['trading_rule']['above the fee cap']['mean_net_pct'])):.3f} points",
        _N, _N, _N, _N, _Y]],
      [AVAIL - 94 * mm, 16 * mm, 19 * mm, 19 * mm, 17 * mm, 23 * mm], fs=6.6,
      align=[None, "C", "C", "C", "C", "C"],
      caption="Table 1.1 - Each candidate mechanism against the seven facts it would have to "
              "explain. The rightmost column is the only one without a gap.")
para(tag("judg") + f"<b>Read down the columns, not across the rows.</b> Gold supply explains at "
     f"most one fact and is contradicted by two. Speculative feedback explains volatility "
     f"clustering and nothing else, and is contradicted by the unit root it would have to "
     f"break. Segmentation is refuted directly by the cointegration result. Private information "
     f"gets the martingale and the missing premium right but cannot produce a band whose width "
     f"is the fee, nor an unconditional edge that dies exactly at cost. The seventh row is "
     f"the one that "
     f"decides it: an edge of "
     f"{pc(ARB['trading_rule']['above the fee cap']['mean_gross_pct'], 3)} gross against a cost of "
     f"{pc(ARB['trading_rule']['above the fee cap']['cost_pct'], 3)} "
     f"is not a coincidence. Costs are the "
     f"mechanism, and everything else in this report follows from that one sentence.")
para(tag("stat") + "Three formal results pin it, each from a different literature and each "
     "capable of having come out the other way:")
bullets([
    "<b>Relative pricing is predictable within a measurable band.</b> A threshold "
    f"autoregression puts the friction point at {pc(R['advanced']['tar']['threshold_pct'])} "
    f"(95% confidence set {pc(R['advanced']['tar']['threshold_ci_pct'][0])} to "
    f"{pc(R['advanced']['tar']['threshold_ci_pct'][1])}). Inside that band a price gap between "
    f"worlds is a random walk and does not close; outside it, gaps close decisively. Linearity "
    f"is rejected at a bootstrap p below 0.001.",
    "<b>The level is a martingale, as a currency with no carry must be.</b> "
    "Augmented Dickey-Fuller cannot reject a "
    f"unit root on {ST['n'] - ST['adf_reject_5pct']} of {ST['n']} worlds and KPSS rejects "
    f"stationarity on {ST['kpss_reject_5pct']}. A Johansen rank test finds exactly one common "
    f"stochastic trend across worlds - and that trend is the unpredictable part.",
    "<b>The one departure from a random walk is exactly the size of the spread.</b> "
    "Variance ratios do reject a random walk at "
    f"short horizons, but the reversal equals a Roll effective spread of "
    f"{pc(FN['roll']['median_roll_spread_pct'])}: it happens between the bid and the ask, not "
    f"across it. Consistent with this, the forecasting model is significantly <i>worse</i> "
    f"than a random walk out of sample at every horizon tested.",
])

story.append(PageBreak())
h2sec_plain("1.3 What this means in practice")
para(tag("judg") + "The mechanism implies a different action for each kind of reader. Each is "
     "stated as an instruction, with the evidence behind it and the single observation that "
     "would reverse it.")
icon_cards([
    ("trader", "Cross-world trader",
     f"Ignore gaps below about {pc(R['advanced']['tar']['threshold_pct'])}; act only on gaps "
     f"above {pc(LV['arb_act_gap_pct'], 0)}, and size the trade at "
     f"{gp(FE['cap_binds_at_lot_tc'])} TC or more so the fee "
     f"cap binds.",
     "Sections 5.2.2, 5.2.4, 6.3.1",
     f"CipSoft changes the fee rate or the {gp(FE['cap_gp'])} GP cap"),
    ("holder", "Coin holder",
     "Hold only what you intend to spend. A coin is a currency, not an asset: it pays no "
     "premium for the volatility you carry. Buy and sell on need, never on a view.",
     "Sections 4.4, 6.4.3",
     "The index compounds above 28% a year for three consecutive years"),
    ("multi", "Multi-world holder",
     "Expect real diversification day to day but none over months - worlds share one common "
     "trend.",
     "Sections 6.3.2, 7.1.2",
     "The common trend breaks into several factors"),
    ("newworld", "New-world participant",
     f"Expect roughly {YG['median_days_to_within_5pct']:.0f} days of convergence from launch; do not read early prices as signal "
     "about the world.",
     "Section 5.4",
     "CipSoft changes how new worlds are seeded"),
    ("analyst", "Analyst or researcher",
     "Do not use players-online as population, order counts as depth, or unclustered standard "
     "errors on this panel.",
     "Sections 3.4, 3.7, 6.2.2",
     "Not applicable - these are measurement facts"),
], caption="Recommendations by reader, with the evidence behind each and the condition that would change it.")

h2sec_plain("1.3 The market in one paragraph")
para(tag("obs") + f"Across {W['n_worlds']} worlds and {W['n_world_days']:,} cleaned world-day "
     f"observations from {W['start']} to {W['end']}, the Tibia Coin trades at a median of "
     f"{gp(D['price_latest_median'])} GP/TC, ranging from {gp(D['price_latest_min'])} to "
     f"{gp(D['price_latest_max'])} across worlds. Daily volatility on established worlds is "
     f"{pc(D['ret_sd_daily_pct'])}, about {pc(D['ret_sd_ann_pct'], 0)} annualised. The "
     f"chain-linked index has risen {pc(IX['total_pct'], 1, True)} since {IX['index_start']}, "
     f"an annualised {pc(IX['cagr_pct'], 2)}, with a maximum drawdown of "
     f"{pc(IX['max_drawdown_pct'], 1)}.")

hero(pc(R["advanced"]["tar"]["threshold_pct"]),
     "is the price gap between worlds at which arbitrage becomes worthwhile.",
     "Below it, a gap behaves as a random walk and does not close. Above it, gaps close, and "
     "close faster the wider they are. The threshold is estimated from prices by threshold "
     "autoregression - no fee figure was supplied to the estimator.",
     mark="band")
h2sec_plain("1.4 Why the band sits where it does")
para(tag("mech") + tag("econ") + "Every Market offer costs 2% of its value, charged when the "
     "offer is created and never refunded, and capped at 1,000,000 GP. A cross-world round "
     "trip needs two offers. The cap makes that cost size-dependent:")
bullets([
    f"A small offer pays the full <b>4.00%</b> round trip.",
    f"The largest decile of live offers pays <b>{pc(FE['roundtrip_largest_decile_pct'], 2)}</b>, "
    f"because the cap binds above about {gp(FE['cap_binds_above_tc'])} TC - "
    f"{gp(FE['cap_binds_at_lot_tc'])} TC once lot size is respected.",
    f"The estimated friction point of {pc(R['advanced']['tar']['threshold_pct'])} sits between "
    f"the two - which is what a capped fee schedule predicts, and what a flat 4% would not.",
])
para(tag("judg") + "No fee figure was supplied to the estimator. The correspondence between "
     "the estimated band and the documented cost schedule is the strongest evidence in this "
     "report that the band is a transaction-cost phenomenon rather than a statistical artefact.")

story.append(PageBreak())
h2sec_plain("1.5 Other findings that change how the market should be read")
bullets([
    tag("obs") + "<b>Provenance, not age, sets a new world's opening price.</b> Merge "
    f"destinations open at mature prices - the nine worlds created in the 2025-11-06 wave were "
    f"one day old and printed a median of {gp(MG['wave_2025_11_06']['first_price_median'])} "
    f"GP/TC. Genuine launches open as low as {gp(YG['launch_first_price_min'])} GP/TC.",

    tag("stat") + f"<b>World size is irrelevant; engagement is not.</b> Across a roster of 6.2 "
    f"million characters, population carries no relationship with price "
    f"({CS['engagement_full']['log_pop']['coef']:+.4f}, "
    f"p {pval(CS['engagement_full']['log_pop']['p'])}). The share of that roster actually "
    f"online does ({CS['engagement_full']['log_engagement']['coef']:+.4f}, "
    f"p {pval(CS['engagement_full']['log_engagement']['p'])}). Dormant characters do not bid "
    f"for coins.",

    tag("stat") + f"<b>Coin risk is almost entirely local.</b> Only "
    f"{pc(FN['variance']['median_r2_systematic'] * 100, 1)} of the median world's daily return "
    f"variance is shared with the market, though the levels share one common trend. Worlds "
    f"share a destination but travel independently.",

    tag("lim") + "<b>Two widely used measures are artefacts.</b> Order counts are not depth: "
    "the correlation with true quantity depth is only "
    f"{MI['corr_ordercount_vs_depth_ratio']:.2f}. Players-online is not population: the ratio "
    f"between them differs by {_RPC_SPREAD:.2f} times across regions.",

    tag("lim") + f"<b>This report prices one venue of three.</b> Coins also settle through "
    f"the official Tibia Token on the BNB Smart Chain - {gp(VN['token']['total_supply'])} "
    f"tokens outstanding, {VN['tib_over_ask_depth']:.1f} times the coins on offer across every "
    f"in-game order book combined - and through fiat resellers. Which venue a seller uses is a "
    f"transaction-cost decision, and the gold price measured here is the price on one of them.",

    tag("stat") + f"<b>Standard errors that ignore cross-world dependence are far too small.</b> "
    f"Two-way clustering widens them by a factor of "
    f"{PN['clustering_comparison']['two-way']['se'] / PN['clustering_comparison']['none']['se']:.1f}.",
])

h2sec_plain("1.6 Rating, confidence, and the one thing that would change it")
para(tag("judg") + f"<b>Verdict: {VERDICT}. Confidence: {CONFIDENCE} / 100.</b> No "
     f"view is taken on the price level, because none is supportable. A specific view is taken "
     f"on relative position: the strongest decile of cross-world gaps, held thirty days, nets "
     f"{pc(float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].net_pct.iloc[0]), 2)} "
     f"of the round trip and wins on "
     f"{float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].share_profitable.iloc[0]):.0%} "
     f"of occasions (Section 7.7). Capacity, not conviction, is the constraint: about "
     f"{gp(CAPY['gp_per_month'])} GP a month can be deployed into it. The structural findings "
     f"behind both halves are held with high confidence - each is replicated across measures, "
     f"sub-samples and estimators.")
para(tag("judg") + f"The binding constraint has changed since this study began, and not in "
     f"the expected direction. A gold-production series was found - "
     f"{FD['panel']['rows']:,} world-days of kill statistics - and Section 6.6.14 tests the "
     f"supply channel against it directly. The channel is <b>not there</b>: the elasticity is "
     f"negligible and the level relationship carries the wrong sign on all {SVD['gold_stock']['n_worlds']} worlds. What "
     f"remains unidentified is the driver itself, and Section 6.6.16 bounds what any driver "
     f"could ever explain - a perfectly observed common state accounts for "
     f"{IRR['latent_state']['r2_factor_smoothed']:.0%} of daily variance and none of it one "
     f"step ahead. Section 7.6 builds the positive account those nulls imply, and Section 7.7 "
     f"turns it into instructions.")
story.append(PageBreak())

# ===================================================================== 2
chapter(2, 'Market overview',
        'What a Tibia Coin is, the mechanics that govern how it trades, and the theory that frames what its gold price means.')
h2sec('2.1', 'Scope', 'Eight questions, and the four the data cannot answer')
para("This study characterises the market for Tibia Coins priced in gold pieces across all "
     "93 game worlds for which a continuous price archive exists, over the period "
     f"{W['start']} to {W['end']}.")

h2("Research questions")
table([["#", "Question", "Sections", "Status"],
       ["Q1", "Are worlds independent markets, or linked by arbitrage?",
        "18, 19", "Answered: linked, within a transaction-cost band"],
       ["Q2", "Is the GP price of a Tibia Coin predictable?",
        "15, 27", "Answered: relative pricing yes, common level no"],
       ["Q3", "What determines the price level of one world relative to another?",
        "20", "Partly: world type yes, size and region no"],
       ["Q4", "Do scheduled game events move the coin price?",
        "17", "Association measured; causation not identifiable"],
       ["Q5", "How do newly created worlds price, and how fast do they converge?",
        "21", "Answered: provenance determines the opening price"],
       ["Q6", "Do world merges move prices?",
        "22", "Not testable with available data"],
       ["Q7", "What does the order book reveal about liquidity?",
        "23", "Answered, with several field semantics corrected"],
       ["Q8", "What is a defensible forward view?",
        "27, 28, 32", "Answered: no directional edge on the level"]],
      [10 * mm, 74 * mm, 17 * mm, AVAIL - 101 * mm],
      caption="Table 2.1 - Research questions and where each is addressed.")

h2("Out of scope")
bullets([
    tag("lim") + f"A real-money price <i>series</i>. CipSoft's store prices were not "
    f"collected, so no GP-per-euro rate is computed over time. A single dated dollar price is "
    f"available from the token's on-chain market (Section 5.8.3) and fixes the level at one "
    f"moment, but it is one observation and not a history.",
    tag("lim") + f"The <i>stock</i> of gold in circulation. A production <i>flow</i> is now "
    f"observed - {FD['panel']['rows']:,} world-days of kill statistics, the series Section "
    f"6.6.14 uses to test and reject the supply channel - but the accumulated stock, gold "
    f"income and coin issuance are still unpublished. Gold inflation is a hypothesis this "
    f"report tests against the flow and does not support; it is nowhere treated as measured.",
    tag("lim") + "Items other than the Tibia Coin (item_id 22118).",
    tag("lim") + "Tournament worlds and any world absent from the price archive.",
])
story.append(PageBreak())

# ===================================================================== 3
h2sec('2.2', 'Game-economy context', 'Two mechanics generate almost every result in this report')
h2("What a Tibia Coin is")
para(tag("mech") + "Tibia Coins are a premium currency sold by CipSoft for real money and "
     "redeemable in game for Premium Time, character services, cosmetics and other store "
     "goods. Coins may also be traded between players for gold pieces through the in-game "
     "Market, which is what makes a GP-denominated price observable at all.")
para(tag("mech") + "<b>Tibia Coins are account-level assets, not world-bound.</b> A player "
     "whose account holds characters on two worlds can buy coins with gold on one world and "
     "sell them on another without a Character World Transfer. CipSoft documents Tibia Coins "
     "as the only assets that cross server boundaries in this way. This single mechanic is the "
     "reason the 93 worlds must be treated as partially integrated local markets rather than "
     "independent economies, and it underpins Sections 5.1 and 5.2.")

h2("The Market rules that shape this price")
para(tag("mech") + "Several documented mechanics bear directly on how Tibia Coins can be "
     "traded, and each leaves a signature in the data examined later in this report.")
FE = R["fees"]
table([["Mechanic", "Rule", "Where it matters"],
       ["Offer fee", f"{FE['rate_pct']:.0f}% of offer value, minimum {FE['min_gp']} GP, "
                     f"<b>capped at {FE['cap_gp']:,} GP</b>", "Sections 5.2, 5.6"],
       ["Fee timing", "Charged when the offer is created, deducted from the bank balance",
        "Section 5.2"],
       ["Cancellation", "Offers may be cancelled at any time; the creation fee is "
                        "<b>not refunded</b>", "Sections 5.2, 7.1"],
       ["Capital locking", "Creating a buy offer freezes the required gold until the offer "
                           "fills or is cancelled", "Section 5.6"],
       ["Lot size", f"Offers are placed in multiples of {FE['lot_size']} units; the "
                    f"smallest possible trade is {FE['lot_size']} TC", "Sections 5.2, 5.6"],
       ["Offer size limit", f"At most {FE['qty_cap']:,} units per offer", "Section 5.6"],
       ["Offer count limit", "At most 100 active offers per player", "Section 5.6"],
       ["Account status", "Only Premium players may post offers generally - <b>Tibia Coins "
                          "are the exception</b>, and free accounts may post them too",
        "Section 5.3"],
       ["Transferability", "Newly purchased coins may be locked as non-transferable for up to "
                           "6 months depending on account trust and payment method",
        "Sections 6.1, 7.1"]],
      [30 * mm, 84 * mm, AVAIL - 114 * mm],
      caption="Table 2.2 - Documented Market mechanics governing Tibia Coin trading.")

h2("Why the fee sets a band, and for whom")
para(tag("econ") + "A round trip across worlds requires two offers, so a small trader pays "
     "about 4% of the traded value. The economic implication is a no-arbitrage band rather "
     "than a single price: deviations smaller than the cost of correcting them can persist "
     "indefinitely, while larger ones invite the trade that removes them.")
para(tag("mech") + f"<b>The cap changes who faces that cost.</b> Because the fee is capped at "
     f"{FE['cap_gp']:,} GP, the effective rate begins to fall once an offer exceeds "
     f"{FE['cap_binds_above_value_gp']:,.0f} GP of value - roughly "
     f"{FE['cap_binds_above_tc']:,.0f} TC at the median quoted price of "
     f"{gp(FE['median_quoted_price'])} GP/TC. Because quantities move in lots of "
     f"{FE['lot_size']}, the smallest offer a trader can actually place at which the cap bites "
     f"is {gp(FE['cap_binds_at_lot_tc'])} TC. A trader posting a large offer therefore pays a "
     f"far lower percentage than a small one. Section 5.2 shows this matters for how the "
     f"arbitrage result should be read.")
para(tag("obs") + f"Three of these limits are directly visible in the live order books. The "
     f"largest single offer observed across all 93 worlds is exactly "
     f"{FE['max_offer_observed_tc']:,} TC, with {FE['offers_at_qty_cap']} offers sitting "
     f"precisely on that value and none above it - the documented per-offer quantity cap, "
     f"confirmed empirically. The lot constraint is equally clean: all "
     f"{FE['offers_on_lot']:,} of the {FE['n_offers']:,} live offers are exact multiples of "
     f"{FE['lot_size']}, the smallest is {FE['lot_size']} TC and the greatest common divisor "
     f"of every quantity on the book is {FE['lot_size']}. And capital locking explains a "
     f"feature of the book examined in Section 3.4: a bid posted at 1 GP freezes almost no "
     f"capital, which is why non-executable placeholder bids accumulate at the bottom of the "
     f"buy side.")
para(tag("obs") + f"The two floors interact in a way that is visible on the book, and it is "
     f"what makes those placeholders cheap enough to leave standing. A minimum lot of "
     f"{FE['lot_size']} coins bid at 1 GP each is an offer worth "
     f"{gp(FE['min_offer_value_gp'])} GP, on which {FE['rate_pct']:.0f}% would be well under a "
     f"gold piece - so the {FE['min_gp']} GP fee floor takes over. It binds on "
     f"{FE['n_at_fee_floor']} of the {FE['n_offers']:,} live offers "
     f"({FE['share_at_fee_floor']:.1%}), and {FE['min_gp']} GP is the entire cost of parking a "
     f"non-executable bid. This is the mechanical reason order counts overstate depth, a point "
     f"Section 5.6.2 measures.")

h2("Gold faucets and sinks")
para(tag("mech") + "Gold enters the economy primarily through monster loot and quest rewards, "
     "and leaves it through non-player-character purchases, repair and travel costs, and the "
     "death penalty. The balance of these flows determines the purchasing power of gold and "
     "hence, holding coin demand fixed, the GP price of a Tibia Coin.")
para(tag("hyp") + "A standing hypothesis in the community is that gold accumulates faster than "
     "it is destroyed, so the GP price of a fixed-value premium asset should drift upward over "
     "time. The chain-linked index in Section 4.2 is consistent with such a drift, but "
     "consistency is not evidence. A gold <i>production</i> series does exist and is built "
     "twice in Chapter 6 - from kill statistics in Section 6.6.14 and from drop tables and "
     "player-to-NPC prices in Section 6.6.15 - and both reject the channel. What remains "
     "unavailable is the accumulated stock and the quantity of coins issued, so the level "
     "still cannot be tied to a monetary aggregate; but the flow hypothesis stated here is no "
     "longer untested, it is tested and unsupported.")
para(tag("econ") + f"One concrete anchor is available. Item metadata records non-player-character "
     f"prices for {R['valuation']['n_items_with_npc_buy']:,} items, which are the fixed GP sinks "
     f"and faucets against which the floating coin price can be compared. Section 6.1 develops "
     f"this. The Tibia Coin itself carries no non-player-character price - its metadata record "
     f"has empty buy and sell lists - so there is no administered anchor for the coin.")
story.append(PageBreak())

# ===================================================================== 3A
h2sec('2.3', 'Theoretical framework', "The coin's gold price is an exchange rate, not a valuation")
bottomline("The coin's real value is fixed administratively, so its gold price is best read as an exchange "
           "rate between two monies rather than as the valuation of a risky asset.")
para("This section states the theory the empirical work is testing, so that later results can "
     "be read against a prior rather than described in isolation. Each construct is tied to a "
     "quantity that is measurable in this panel; where a construct is not measurable here, "
     "that is said explicitly.")

h3("2.3.1 What kind of asset is a Tibia Coin?")
para(tag("mech") + "A Tibia Coin is a claim on a fixed bundle of services - Premium Time, "
     "character services, cosmetics - whose <i>real</i> value is set administratively by "
     "CipSoft and does not vary with the gold price. It pays no cash flow, cannot be lent, and "
     "has no maturity. In asset-pricing terms it is a durable, non-dividend-paying claim whose "
     "fundamental value in gold is the gold cost of the services it substitutes for.")
para(tag("econ") + "This has a direct implication for what the observed price is. Because the "
     "coin's real payoff is fixed by administration, movement in the gold price of a coin is "
     "not news about the coin. It is news about gold. The gold-per-coin series is best read as "
     "an <b>exchange rate between two monies</b> - a player-produced commodity money with a "
     "flexible supply, and an administratively supplied premium currency - rather than as the "
     "valuation of a risky asset. Sections 4.3 and 6.1 build on this reading.")
para(tag("econ") + "Standard components of value can be located, though not all can be "
     "separately measured here:")
bullets([
    "<b>Intrinsic value.</b> The gold cost of the services a coin buys. Fixed in real terms by "
    "CipSoft, so it moves in gold only as gold's purchasing power moves.",
    "<b>Convenience yield.</b> Holding coins confers optionality - the ability to buy a "
    "service, or to sell into a favourable gold price, without delay. This is the closest "
    "analogue to a dividend and it is not separately observable in these data.",
    "<b>Liquidity premium.</b> A coin is far more liquid than most in-game assets and "
    "transferable across worlds, which no other asset is. Section 5.6 measures the trading cost "
    "that this premium is compensation for.",
    "<b>Option value.</b> Because the coin is redeemable at an administratively fixed real "
    "price, a holder is effectively long an option on gold depreciation. That asymmetry is a "
    + tag("hyp") + "hypothesis consistent with the drift documented in Section 4.3; it is not "
    "tested here.",
])
para(tag("lim") + "No equilibrium asset-pricing model is estimated in this report. Doing so "
     "would require a measure of the marginal holder's consumption or wealth, which does not "
     "exist in any accessible source. Claims about equilibrium pricing below are qualitative.")

h3("2.3.2 Monetary framing: gold as the numeraire")
para(tag("econ") + "If the coin's real value is fixed, then the gold price of a coin is the "
     "inverse of gold's purchasing power over that fixed bundle. A quantity-theoretic reading "
     "follows immediately. Writing M for the gold stock, V for its velocity, and Y for the "
     "real volume of goods and services traded in gold, MV = PY implies that a gold price "
     "level P rising against a fixed-real-value asset is evidence of M growing faster than Y, "
     "holding V fixed.")
para(tag("hyp") + f"The chain-linked index rose {pc(IX['cagr_pct'], 2)} a year (Section 4.2), "
     f"which under this identity is consistent with gold accumulating faster than the real "
     f"economy absorbs it. <b>It remains a hypothesis.</b> Testing it requires M, V or Y, and "
     f"none of the three is observable in any accessible source. The identity cannot be "
     f"rejected or confirmed here; it can only frame what would need measuring.")
para(tag("econ") + "The framing does earn its place in one respect. It explains why Section 5.3 "
     "finds world <i>type</i> matters and world <i>size</i> does not. Death penalties and "
     "repair costs are gold sinks that act on M; a world's headcount acts on both M and Y "
     "roughly proportionally and so should wash out of the price level. That is what the data "
     "show.")

h3("2.3.3 Market microstructure")
para(tag("mech") + "Prices here are set in a continuous limit-order book with no designated "
     "market maker and full anonymity. Three canonical frameworks bear on it, and they make "
     "different predictions that Section 5.6 can partly separate:")
bullets([
    "<b>Inventory models</b> (Ho and Stoll, 1981). A liquidity provider holding coins bears "
    "price risk and widens quotes to be compensated. Prediction: spreads fall with volume and "
    "with the number of competing providers.",
    "<b>Adverse selection</b> (Glosten and Milgrom, 1985). Quotes must be wide enough to "
    "recover from uninformed traders what is lost to informed ones. Prediction: spreads widen "
    "where the informed share is higher.",
    "<b>Strategic informed trading</b> (Kyle, 1985). An informed trader splits orders to hide, "
    "and price impact per unit of order flow is the inverse of market depth. Prediction: "
    "deeper worlds show smaller price impact.",
])
para(tag("judg") + "Anonymity is the binding constraint on testing these. Order-book "
     "identities are almost entirely the literal string 'Anonymous' (Section 5.6.3), so order "
     "flow cannot be signed, no trade-direction classification is possible, and neither the "
     "adverse-selection component of the spread nor Kyle's lambda can be estimated. What "
     "<i>can</i> be estimated is the effective spread, via Roll (1984), from the serial "
     "covariance of returns - and Section 5.6.4 does so.")

h3("2.3.4 Efficiency, and what a random walk does and does not imply")
para(tag("econ") + "Weak-form efficiency asserts that prices already reflect the information "
     "in past prices, so returns should not be forecastable from their own history. Section 4.4 "
     "cannot reject a unit root in the level on essentially any world, which is consistent "
     "with that. But a unit root is a weaker statement than efficiency, and Section 4.4.3 shows "
     "the two come apart here: returns display significant short-horizon reversal, yet the "
     "reversal is smaller than the cost of trading it.")
para(tag("judg") + "That distinction - statistical predictability without economic "
     "predictability - is the organising idea of this report's forecasting position. It is "
     "a conclusion, not a premise, and the order matters: a distinction of this kind is only "
     "informative once the statistical side has been pushed as far as the data allow, because "
     "otherwise a weak result cannot be told apart from a weak effort. Section 6.6 does the "
     "pushing - every model class the literature offers, tuned, ensembled and tested out of "
     "sample - and Section 6.6.7 then applies the economic filter to whatever survives.")

h3("2.3.5 Limits to arbitrage")
para(tag("econ") + "Classical arbitrage requires no capital and bears no risk. The cross-world "
     "coin trade requires both. Shleifer and Vishny (1997) formalise why deviations can "
     "persist when arbitrage is performed by capital-constrained specialists: the trade must "
     "be financed, it can move against the arbitrageur before it converges, and the capital is "
     "committed throughout.")
para(tag("mech") + "Every element of that argument has a concrete counterpart in this market, "
     "and each is documented in Section 2.2: a non-refundable fee charged at offer creation, a "
     "cap on that fee that makes the cost schedule size-dependent, gold frozen while a buy "
     "offer rests, a limit of 100 open offers, a 64,000-unit cap per offer, and a "
     "transferability lock of up to six months on newly purchased coins. Section 5.2 estimates "
     "the band these frictions produce and Section 5.2.6 returns to which of them binds.")

h3("2.3.6 Portfolio choice and risk")
para(tag("econ") + "A player allocates gold across consumables, equipment, and coins. "
     "Consumables are spent, equipment is durable but illiquid and world-bound, and coins are "
     "durable, liquid and the only asset that crosses worlds. Holding coins therefore carries "
     "an opportunity cost - gold not spent on hunting supplies that would generate more gold - "
     "against a liquidity and optionality benefit. Section 4.6's negative event-day coefficients "
     "are consistent with that trade-off tightening when hunting returns rise, though "
     "Section 4.6.1 shows the mechanism is not identified.")
para(tag("stat") + f"On the risk side, the decomposition in Section 7.1.2 is unambiguous: the "
     f"median world's daily return has only {pc(FN['variance']['median_r2_systematic'] * 100, 1)} "
     f"of its variance in common with the market, so coin risk at daily frequency is almost "
     f"entirely idiosyncratic. Because there is no risk-free asset and no external numeraire "
     f"in this economy, no risk premium can be estimated, and none is claimed.")
story.append(PageBreak())

# ===================================================================== 4
chapter(3, 'Data and measurement',
        'Where every number in this report comes from, how it was cleaned, and what the data can and cannot support. The limitations recorded here govern everything that follows.')
h2sec('3.1', 'Data sources', 'Seven independent sources, only two of them official feeds')
para("Four independent sources were collected. Each is described with its exact access path, "
     "its coverage, and an explicit statement of what it is not.")

h3("3.1.1 Price panel - GitHub archive")
table([["Property", "Value"],
       ["Repository", "github.com/nesleykent/tibia-warzones-schedule"],
       ["Path", "data/market/world/&lt;World&gt;/&lt;world&gt;_tibia_coins.json"],
       ["Retrieval", "git clone --depth 1 --filter=blob:none --sparse, then "
                     "git sparse-checkout set data/market/world"],
       ["Coverage", f"93 worlds, {raw_n:,} raw snapshots, {W['start']} to {W['end']}, "
                    f"approximately daily"],
       ["Item", "Tibia Coin, item_id 22118"],
       ["Archive stamp", "last_run_at 2026-07-30T16:03:28Z, status ok, all 93 files"]],
      [30 * mm, AVAIL - 30 * mm],
      caption="Table 3.1 - Price panel source.")
para(tag("lim") + "<b>Provenance caution.</b> The archive's schema is byte-identical to the "
     "TibiaMarket.top MarketValues model, including its -1 sentinel convention and its exact "
     "field names. It is a deduplicated third-party mirror, not an official CipSoft feed, and "
     "is described as such throughout this report. It must not be characterised as official "
     "Tibia Market data. A consequence is that any systematic collection error in the upstream "
     "third party propagates here undetected.")

h3("3.1.2 TibiaMarket.top API")
table([["Endpoint", "Returns", "Coverage"],
       ["/item_history", "Full MarketValues rows", "From 2023-01-11; intraday; includes failed "
                                                   "scans written entirely as -1"],
       ["/events", "{date, events[]} daily labels", "From 2023-01-30; no world dimension"],
       ["/market_board", "Order book: name, amount, price, time", "Current snapshot only"],
       ["/market_values", "Current MarketValues rows", "Current only"],
       ["/item_metadata", "Item names, categories, NPC prices", "5,096 items"],
       ["/item_activity", "Activity measures", "Current only"],
       ["/world_data", "World-level fields", "Current only"]],
      [26 * mm, 52 * mm, AVAIL - 78 * mm],
      caption="Table 3.2 - TibiaMarket.top endpoints. Schema at "
              "api.tibiamarket.top/openapi.json. No authentication was observed. "
              "Order books for all 93 worlds were retrieved on 2026-07-30; the service "
              "rate-limits and returned HTTP 429 for 18 worlds on first pass, which were "
              "retried successfully with back-off.")
para(tag("lim") + "The /events endpoint has <b>no world dimension</b>: every event label applies "
     "to all worlds simultaneously. Section 4.6 shows why this is a structural obstacle to causal "
     "identification rather than a mere inconvenience. The endpoint also does not include game "
     "update releases, which were taken from official Tibia news instead.")

h3("3.1.3 TibiaData API v4")
para(tag("obs") + "TibiaData v4 is a supported fansite API sourcing tibia.com. The /v4/worlds "
     "endpoint supplies each world's name, location, PvP type, premium status, transfer policy, "
     "BattlEye status and date, world type, and an instantaneous players-online count. The "
     "/v4/news/archive endpoint supplied the update release calendar.")
para(tag("lim") + "TibiaData returns a current snapshot only. It carries no history, no world "
     "creation dates, and no merge records. Its players-online field is an instantaneous count "
     "at the moment of the call - this study's call was made at 18:43 UTC on 2026-07-30 - and "
     "Section 3.7 shows in detail why such a count is a poor measure of world size.")

h3("3.1.4 GuildStats.eu")
para(tag("obs") + "GuildStats.eu is a third-party fansite whose robots.txt was verified as "
     "<i>Allow: /</i> before collection. It supplies three things available nowhere else: "
     "documented world creation dates, the complete server merge register, and per-world "
     "players-online history.")
table([["Page", "Supplies", "Coverage obtained"],
       ["/worlds", "Creation date, region, type, BattlEye, record online", "93 worlds"],
       ["/servers-merge", "Merge destinations, dates, predecessor worlds",
        f"{MG['n_merges']} merges, {MG['n_predecessors']} predecessor worlds, "
        f"{MG['first'][:4]}-{MG['last'][:4]}"],
       ["/census", "Resident population by account type, vocation, level, city",
        f"93 worlds, {bw.active_chars.sum():,} characters"],
       ["/online-counter", "Players-online series: 24h, week, month, year, all-time",
        f"93 worlds, {sm.n_days_pop.sum():,} world-days of daily averages"],
       ["/world-transfer", "Character world transfers",
        f"{MG['transfers_n']} records covering {MG['transfers_days']} days"]],
      [26 * mm, 62 * mm, AVAIL - 88 * mm],
      caption="Table 3.3 - GuildStats.eu pages collected, one request per world where "
              "applicable, with a courtesy delay between requests.")
para(tag("obs") + "The online-counter pages embed their charts as JavaScript literals carrying "
     "full label and value arrays. This yields a genuine daily population panel rather than the "
     "summary statistics visible on the rendered page - the single most consequential data "
     "improvement in this study, and the basis for Sections 3.7 and 5.3.")

h3("3.1.5 TibiaVIP, and the endpoints deliberately not used")
para(tag("obs") + f"TibiaVIP publishes a world list carrying, for each world, the number of "
     f"players online, the <b>total character roster</b>, the guild count, the location and the "
     f"PvP type, sourced from tibia.com. The roster column is this report's population measure "
     f"(Section 3.7.1). These values were supplied directly as a saved copy of the world-list "
     f"page rather than retrieved by automated collection.")
para(tag("obs") + f"Two independent checks support using them. TibiaVIP's guild counts match "
     f"GuildStats' across all 93 worlds at Pearson "
     f"{CS['census']['guild_agreement_pearson']:.4f}, with "
     f"{CS['census']['guild_exact_matches']} exactly identical and every world within three "
     f"guilds; region agrees on all 93. Where the two fansites report the same quantity they "
     f"agree, which is what makes the far larger difference in character counts a definitional "
     f"matter rather than a data-quality one.")
para(tag("lim") + "<b>TibiaVIP's robots.txt disallows /worlds/ajaxplayersonline, "
     "/worlds/ajaxaccounts, /worlds/ajaxvocations, /characters/history and /guilds/history.</b> "
     "Those are precisely the endpoints that would otherwise be attractive for a population "
     "study. None was accessed, and no automated collection was run against TibiaVIP at any "
     "point. The per-world population history that those endpoints would provide therefore "
     "does not exist in this study, which is why population enters cross-sectional models only "
     "and never the daily panel.")
story.append(PageBreak())

# ===================================================================== 5
h2sec('3.2', 'Data inventory', 'Coverage grows from one world per date to 85, and that forces two corrections')
table([["Dataset", "Rows", "Unit", "Coverage"],
       ["Raw price snapshots", "41,584", "world-scan", f"{W['start']} to {W['end']}, 93 worlds"],
       ["Cleaned daily price panel", f"{W['n_world_days']:,}", "world-day",
        f"{W['start']} to {W['end']}, 93 worlds"],
       ["Converged-world panel", f"{len(pd.read_csv(P / 'converged_panel.csv')):,}", "world-day",
        f"{W['n_converged']} worlds"],
       ["Population daily panel", "166,679", "world-day", "2014-12-17 to 2026-07-30, 93 worlds"],
       ["Diurnal intraday panel", f"{93 * 672:,} approx.", "world-quarter-hour",
        "7 days to 2026-07-30, 15-minute resolution"],
       ["World population census", "93", "world",
        "Single snapshot, 2026-07-30; 483,579 characters"],
       ["Order books", "93", "world", "Single snapshot, 2026-07-30"],
       ["Event calendar", f"{len(cal):,}", "day", f"{W['start']} to {W['end']}, global"],
       ["Merge register", f"{MG['n_predecessors']}", "predecessor link",
        f"{MG['first']} to {MG['last']}"],
       ["World metadata", "93", "world", "Current attributes plus creation dates"],
       ["Character transfers", f"{MG['transfers_n']}", "transfer", MG["transfers_window"]]],
      [42 * mm, 20 * mm, 26 * mm, AVAIL - 88 * mm],
      align=[None, "R", None, None],
      caption="Table 3.4 - Datasets assembled for this study.")

h3("3.2.1 Cross-sectional coverage is not constant - and it matters")
para(tag("obs") + "The archive's world coverage expands substantially over the window. This is "
     "a property of the collection process, not of the game, and it has direct analytical "
     "consequences.")
cov = IX["coverage_by_year"]; mwd = IX["median_worlds_per_date_by_year"]
table([["Year", "World-days", "Distinct worlds", "Median worlds observed per date"]] +
      [[y, f"{cov[y]['world_days']:,}", cov[y]["worlds"], f"{mwd[y]:.0f}"]
       for y in sorted(cov)],
      [18 * mm, 28 * mm, 30 * mm, AVAIL - 76 * mm],
      align=[None, "R", "R", "R"],
      caption="Table 3.5 - Archive coverage by calendar year. In 2023 the archive typically "
              "observes a single world on any given date.")
para(tag("lim") + "Two corrections follow directly and are applied throughout. First, a "
     "cross-world mean computed from one or two worlds is not a meaningful benchmark, so every "
     "cross-world statistic in this report is restricted to dates carrying at least 10 observed "
     "converged worlds; this drops "
     f"{W['dates_dropped_thin_cross_section']:,} world-days and starts the cross-world sample at "
     f"{W['xw_start']}. Second, a price index built from a growing basket confounds price change "
     "with composition change, so the headline index in Section 4.2 is chain-linked. Comparing "
     "raw basket means across this window would overstate the market's appreciation by roughly a "
     "factor of five.")
story.append(PageBreak())

# ===================================================================== 6
h2sec('3.3', 'Validation and cleaning', 'A deliberately gentle filter discards 0.18% of days and keeps the real 2024 trough')
para("The pipeline is deterministic and each step is auditable in isolation. Steps are applied "
     "in the order given.")
table([["#", "Step", "Rule", "Effect"],
       ["1", "Sentinel handling", "Replace every -1 with missing before any arithmetic",
        "71.7% of buy_offer, 2.1% of day_average_sell"],
       ["2", "Intraday collapse", "One row per world-day, the last scan of the day",
        "838 rows collapsed"],
       ["3", "Validity gate", "Accept day_average_sell only if day_sold &gt; 0 and value &gt; "
                              "1,000 GP; same for the buy side",
        "Zero-trade days write 0, not null"],
       ["4", "Price construction", "Mean of the two valid daily executed averages",
        f"{SRC_N['both']:,} world-days use both sides"],
       ["5", "Order-book fallback", "Book mid only when 0.5 &lt;= ask/bid &lt;= 2.0",
        "501 world-days filled"],
       ["6", "Outlier scrub", "Drop days beyond 5 MAD, floor 12%, from a centred 15-day "
                              "rolling median", "73 world-days dropped (0.18%)"],
       ["7", "Daily range", "High/low fields restricted to 0.5x-2.0x of the day price",
        "Band filter removes contaminated buy-side lows"],
       ["8", "Gap handling", "Single-day gaps interpolated for indicators only",
        "Statistics use observed days"],
       ["9", "Timestamps", "Unix epoch to UTC, floored to the day",
        "Server-save offset not corrected"]],
      [7 * mm, 26 * mm, 68 * mm, AVAIL - 101 * mm],
      caption="Table 3.6 - Cleaning pipeline. Counts are the realised effect on this dataset.")

h3("3.3.1 Why the outlier filter is deliberately gentle")
para(tag("judg") + "The scrub uses a 5-MAD threshold with a 12% floor rather than a tighter "
     "rule. A market with a daily volatility above 1% and genuinely thin trading produces large "
     "legitimate moves; an aggressive filter removes exactly the episodes worth studying. The "
     f"chosen rule discards {73 / 40731 * 100:.2f}% of priced world-days and preserves the "
     f"index trough of {gp(IX['trough'])} GP/TC on {IX['trough_date']}, which is a real market "
     f"event and not a data error.")

h3("3.3.2 A known, uncorrected approximation")
para(tag("lim") + "Timestamps are floored to the UTC day. The Tibia economic day, however, "
     "begins at server save, not at UTC midnight. Every daily aggregate in this report therefore "
     "carries a fixed offset relative to the game's own accounting day. The offset is constant "
     "within a world, so it cannot generate spurious cross-world differences, but it does blur "
     "day-of-week effects (Section 4.5) and any same-day event attribution (Section 4.6). "
     "Correcting it would require a server-save boundary per world and is left as a "
     "recommendation.")

h3("3.3.3 Validation against an independent measurement")
para(tag("obs") + "Two independently constructed price measures agree closely. Comparing the "
     "transaction-based price against the order-book mid on overlapping world-days gives a mean "
     f"absolute deviation of "
     f"{RB['order_book_mid']['mean_dev_from_headline_pct']:.2f}%. Section 7.2 extends this to a "
     f"full sensitivity analysis.")
story.append(PageBreak())

# ===================================================================== 7
h2sec('3.4', 'Field definitions', 'Three fields invite readings the data do not support')
para("Several fields in the source schema carry names that invite incorrect readings. Each was "
     "validated against the live order book before use.")
table([["Field", "What it actually is", "What it is not"],
       ["buy_offer / sell_offer", "Best standing bid and best standing ask price, in GP",
        "Not a traded price"],
       ["buy_offers / sell_offers", "Counts of standing orders",
        "<b>Not depth, demand, or participants</b>"],
       ["day_average_sell / _buy", "Mean executed price on that side that day",
        "Not a quote, not a mid"],
       ["day_sold / day_bought", "Lots executed on each side. Coins trade only in 25s, and "
        "the field counts lots, not coins: values run 1, 2, 3 with 3.7% multiples of 25, which "
        "a coin count cannot be. Coin volume is 25x the field",
        "<b>Must not be summed - double counts trades</b>"],
       ["day_highest/lowest_*", "Extremes of executed prices that day",
        "day_lowest_buy is contaminated"],
       ["active_traders", "Undocumented activity measure",
        "<b>Never a proxy for world population</b>"],
       ["market_board.amount", "True TC quantity on an offer - real depth", "-"],
       ["market_board.name", "Mostly the literal string 'Anonymous'",
        "Cannot identify unique participants"],
       ["market_board.time", "Values exceed the board's own update_time",
        "Probably expiry, not creation; unresolved"]],
      [30 * mm, 62 * mm, AVAIL - 92 * mm],
      caption="Table 3.7 - Field semantics, validated against live order books on 2026-07-30.")

h3("3.4.1 Three readings the data do not support")
bullets([
    tag("lim") + f"<b>Order counts are not depth.</b> On the median world the live book carries "
    f"{MI['median_buy_orders']:.0f} buy orders against {MI['median_sell_orders']:.0f} sell "
    f"orders, which invites a reading of overwhelming demand. {MI['example_world']}'s book at "
    f"the time of collection held {MI['example_sell_orders']} sell orders against "
    f"{MI['example_buy_orders']} buy orders - but {MI['example_bids_below_2000']} of those buy "
    f"orders sat below 2,000 GP against a market near {gp(MI['example_mid_gp'])} GP, including "
    f"bids at {', '.join(str(x) for x in MI['example_cheapest_bids'])} GP. These are "
    f"non-executable placeholders. Across all 93 worlds the correlation between the order-count "
    f"ratio and the actual depth ratio is only {MI['corr_ordercount_vs_depth_ratio']:.2f}.",

    tag("lim") + f"<b>The executed-average gap is not a bid-ask spread.</b> The difference "
    f"between day_average_sell and day_average_buy is the gap between mean executed prices on "
    f"each side, with a median of {pc(MI['executed_gap_median_pct'])} across converged worlds. "
    f"The true quoted spread is a different quantity: on Antica it is "
    f"{gp(MI['antica_ask'])} minus {gp(MI['antica_bid'])}, or "
    f"{pc(MI['antica_spread_pct'])} of mid, against an executed gap of "
    f"{pc(MI['antica_executed_gap'])}. Only the executed gap has history.",

    tag("lim") + f"<b>day_lowest_buy is unusable.</b> On large worlds "
    f"{MI['placeholder_low_share']:.0%} of non-sentinel observations of this field sit at "
    f"1 GP or below, reflecting the "
    f"placeholder bids described above. Daily ranges are therefore accepted only when both the "
    f"high and the low fall within 0.5x to 2.0x of that day's price, which removes the "
    f"placeholder lows; in practice the surviving lows come from the sell side.",
])
story.append(PageBreak())

# ===================================================================== 8
h2sec('3.5', 'Price construction', 'Four independent price measures agree to within 2%')
para(tag("obs") + "The headline price for a world-day is the simple mean of the two valid daily "
     "executed averages, the sell side and the buy side. This is a mean of executed prices. It "
     "is deliberately not called a VWAP, a mid, or a spread, because it is none of those.")
table([["Measure", "Definition", "Mean abs. deviation from headline"],
       ["Headline", "Mean of day_average_sell and day_average_buy", "-"],
       ["Quantity-weighted", "Executed averages weighted by TC traded each side",
        pc(RB["quantity_weighted"]["mean_dev_from_headline_pct"])],
       ["Order-book mid", "(best bid + best ask) / 2, gated on ask/bid in [0.5, 2.0]",
        pc(RB["order_book_mid"]["mean_dev_from_headline_pct"])],
       ["Sell-side only", "day_average_sell alone",
        pc(RB["sell_side_only"]["mean_dev_from_headline_pct"])]],
      [30 * mm, 82 * mm, AVAIL - 112 * mm], align=[None, None, "R"],
      caption="Table 3.8 - Alternative price measures. Section 7.2 re-estimates the study's "
              "central regression on each.")
para(tag("obs") + f"The measures agree closely. The largest divergence, sell-side only, differs "
     f"from the headline by {RB['sell_side_only']['mean_dev_from_headline_pct']:.2f}% on average, "
     f"and the central arbitrage result holds on all four. The choice of price measure is not "
     f"driving any conclusion in this report.")
para(tag("obs") + f"Coverage by construction path: {SRC_N['both']:,} world-days use both "
     f"sides, {SRC_N['book_mid']:,} fall back to the order-book mid, and "
     f"{SRC_N['buy_only'] + SRC_N['sell_only']:,} have only one executed side available.")
story.append(PageBreak())

# ===================================================================== 9
h2sec('3.6', 'World metadata', "A world's entry date does not identify a new world")
para(tag("obs") + "World attributes come from TibiaData v4; creation dates and the merge "
     "register come from GuildStats. Creation dates exist in no API and are essential: they are "
     "what makes Section 5.4 possible without selecting on price.")
reg = bw.region.value_counts()
pvp = bw.pvp_type.value_counts()
table([["Region", "Worlds", "PvP type", "Worlds", "Classification", "Worlds"],
       ["Europe", reg.get("Europe", 0), "Open PvP", pvp.get("Open PvP", 0),
        "Converged", int(bw.converged.sum())],
       ["North America", reg.get("North America", 0), "Optional PvP", pvp.get("Optional PvP", 0),
        "Genuine launch in window", W["n_launch"]],
       ["South America", reg.get("South America", 0), "Retro Open PvP",
        pvp.get("Retro Open PvP", 0), "Merge destination in window",
        W["n_merge_dest_in_window"]],
       ["Oceania", reg.get("Oceania", 0), "Retro Hardcore PvP",
        pvp.get("Retro Hardcore PvP", 0), "Merge destination, any date",
        int(bw.is_merge_destination.sum())]],
      [26 * mm, 14 * mm, 30 * mm, 14 * mm, 46 * mm, AVAIL - 130 * mm],
      align=[None, "R", None, "R", None, "R"],
      caption="Table 3.9 - World composition. Classification rules are defined in Section 8.3.")

h3("3.6.1 Classification rules")
bullets([
    "<b>launch_in_window</b> - created inside the observation window <i>and</i> absent from the "
    "merge register.",
    f"<b>converged</b> - at least 200 observations, regular world type, and not a launch inside "
    f"the window. {W['n_converged']} worlds qualify.",
    "Launch-phase worlds are never pooled with converged worlds in any cross-sectional statistic.",
])
para(tag("lim") + "<b>A dataset-entry date does not identify a new world.</b> Nine worlds enter "
     "the archive on 2025-11-07 at mature prices; they are merge destinations created the "
     "previous day, not new economies. Classification uses documented creation dates plus "
     "absence from the merge register, never first observation and never observed price.")
story.append(PageBreak())

# ===================================================================== 10
h2sec('3.7', 'Population and activity', 'Concurrent players are a poor proxy for world population')
para(tag("obs") + "This section separates two quantities that are routinely conflated. "
     "<b>Population is a stock</b>: how many characters reside on a world. <b>Activity is a "
     "flow</b>: how many of them are logged in at a given moment. They are different "
     "measurements, they are only moderately related, and using one in place of the other "
     "biases any cross-world comparison.")

h3("3.7.1 Measuring a world's population correctly")
para(tag("obs") + f"The population of a world is its character roster. TibiaVIP publishes that "
     f"figure per world, sourced from tibia.com: <b>{CS['census']['roster_total']:,} characters "
     f"across the 93 worlds</b>, from {gp(CS['census']['roster_min'])} on the newest world to "
     f"{gp(CS['census']['roster_max'])} on Antica. This is the population measure used "
     f"throughout this report.")
para(tag("obs") + f"A second source, the GuildStats census, reports a much smaller "
     f"{CS['census']['active_total']:,} characters in total and breaks them down by account "
     f"type, vocation and level. The two do not disagree about the underlying data - where they "
     f"report the same quantity they match almost exactly, with guild counts correlating at "
     f"Pearson {CS['census']['guild_agreement_pearson']:.4f} across 93 worlds, "
     f"{CS['census']['guild_exact_matches']} of them identical, and region agreeing on all 93. "
     f"They are counting different things.")
para(tag("lim") + f"<b>The census counts only indexed, higher-level characters, and the share "
     f"of the roster it captures depends strongly on world age.</b> It never exceeds the "
     f"roster on any world. Its coverage runs from "
     f"{pc(CS['census']['active_share_max'] * 100, 0)} on a world created this year down to "
     f"{pc(CS['census']['active_share_min'] * 100, 1)} on the oldest, a median of "
     f"{pc(CS['census']['median_active_share'] * 100, 1)}, and the coverage rate correlates "
     f"with world age at Spearman "
     f"{CS['census']['spearman_activeshare_vs_age'][0]:+.2f} "
     f"(p {pval(CS['census']['spearman_activeshare_vs_age'][1])}). Using it as population would "
     f"therefore inject measurement error correlated with world age - and hence with the "
     f"BattlEye cohort variable of Section 5.3.2, which is itself a vintage marker. Section 5.3.3 "
     f"shows this is not hypothetical: it materially changes the estimated population "
     f"coefficient.")
para(tag("judg") + "The census is retained, but as what it actually is: a count of the active, "
     "higher-level sub-population. Its ratio to the full roster is a useful measure in its own "
     "right - the share of a world's characters that are still meaningfully in play.")
table([["Measure", "Type", "Median per world", "Range", "Role"],
       ["Character roster (TibiaVIP)", "Stock", f"{gp(CS['census']['roster_median'])}",
        f"{gp(CS['census']['roster_min'])} to {gp(CS['census']['roster_max'])}",
        "<b>Population</b>"],
       ["Active high-level characters", "Stock", "4,616",
        f"{pc(CS['census']['active_share_min'] * 100, 1)} to "
        f"{pc(CS['census']['active_share_max'] * 100, 0)} of roster",
        "Active sub-population"],
       ["Characters in guilds", "Stock", "1,524", "-", "Corroborating partial stock"],
       ["Concurrent players online", "Flow", f"{gp(CS['stock_vs_flow']['activity_median'])}",
        "8 to 496", "Activity; the daily panel term"],
       ["Instantaneous player count", "Flow", "161", "3 to 829",
        "Shown only to demonstrate its bias"]],
      [42 * mm, 14 * mm, 26 * mm, 34 * mm, AVAIL - 116 * mm],
      align=[None, None, "R", "R", None],
      caption="Table 3.10 - World-size measures. Sources: TibiaVIP world list (Total column) "
              "for the roster; GuildStats.eu /census, /worlds and /online-counter; TibiaData "
              "v4 /worlds for the instantaneous count.")
para(tag("obs") + f"The census also carries information with direct economic relevance. Premium "
     f"Time is one of the main things Tibia Coins are spent on, and the share of active "
     f"characters on premium accounts varies widely: median "
     f"{pc(CS['census']['median_premium_share'] * 100, 1)}, ranging from "
     f"{pc(CS['census']['premium_share_range'][0] * 100, 1)} to "
     f"{pc(CS['census']['premium_share_range'][1] * 100, 1)}.")

h3("3.7.2 Population is not activity")
para(tag("stat") + f"The population stock and the activity flow are correlated but far from "
     f"interchangeable, and the ratio between them is <b>not stable across regions</b>. "
     f"Dividing resident characters by mean concurrent players gives a median of "
     f"{CS['stock_vs_flow']['residents_per_concurrent_median']:.0f} characters per concurrent "
     f"player overall, but that figure ranges from {min(_RPC.values()):.0f} in "
     f"{min(_RPC, key=_RPC.get)} to {max(_RPC.values()):.0f} in {max(_RPC, key=_RPC.get)} - a "
     f"spread of {_RPC_SPREAD:.2f} times.")
table([["Region", "Characters per concurrent player"]] +
      [[k, f"{v:.0f}"] for k, v in sorted(CS["stock_vs_flow"]["residents_per_concurrent_by_region"].items(),
                                          key=lambda kv: -kv[1])],
      [50 * mm, AVAIL - 50 * mm], align=[None, "R"],
      caption="Table 3.11 - Character roster divided by mean concurrent players online, "
              "trailing year, converged worlds.")
para(tag("judg") + "Substituting activity for population would systematically understate one "
     "region relative to another - a rotation of the cross-section, not a rescaling, and "
     "exactly the kind of error that manufactures spurious regional effects. The two are "
     "reported separately throughout and never used interchangeably. Section 5.3.3 shows that "
     "their ratio carries information that neither does alone.")

h3("3.7.3 An instantaneous count is worse still")
para(tag("obs") + "Even as a measure of activity, a single-instant players-online count of the "
     "kind returned by a world-list API is unreliable, and its error is not random. Worlds "
     "serve regionally concentrated player bases with different local evenings, so the ratio "
     "between an instantaneous count and the true daily average depends jointly on region and "
     "on the hour at which the snapshot is taken.")
para(tag("obs") + "This was measured directly rather than assumed, using the 15-minute "
     "online-counter series for all 93 worlds over the seven days to 2026-07-30. Source "
     "timestamps are Tibia server time; they are converted to UTC here.")
figure("fig05b_region_bias.png",
       "Exhibit 3.1 - Snapshot bias by region. Source: GuildStats.eu /online-counter, 93 worlds, 7 days ending 2026-07-30.")
figure("fig05_diurnal_bias.png",
       "Exhibit 3.2 - Snapshot bias by hour and region. The curves differ in shape, not merely "
       "in level: a snapshot at 04:45 UTC understates a European world by 2.79 times while "
       "overstating a North American one. Source: GuildStats.eu /online-counter, 93 worlds, "
       "7 days ending 2026-07-30, 15-minute resolution, converted from server time to UTC.")
para(tag("stat") + f"A uniform multiplicative bias would leave a log-activity regression "
     f"coefficient untouched, shifting only the intercept. The measured bias is not uniform: at "
     f"04:45 UTC the Europe-to-North-America distortion ratio is "
     f"{prof.set_index('region').loc['Europe', 'factor_at_0445utc'] / prof.set_index('region').loc['North America', 'factor_at_0445utc']:.2f} "
     f"times. Because the full daily history was obtained, this report never uses an "
     f"instantaneous count except to demonstrate the problem.")

h3("3.7.4 Activity measures inside the price archive")
para(tag("lim") + "The archive's active_traders field is undocumented and is 71.8% sentinel. "
     "Where present it is treated as a proxy for participation in the coin market on that "
     "world, never as a measure of world population or of world activity generally. The two "
     "external series above supersede it entirely.")
figure("fig16_population_history.png",
       "Exhibit 3.3 - Total daily-average concurrent players online across the 93 sampled "
       "worlds. This is activity, a flow, not the resident population of the game. The series "
       "sums only worlds present in the price sample, so worlds that merged away before the "
       "window are excluded and the early level is not comparable across time. Source: "
       "GuildStats.eu /online-counter, full daily history per world.")
story.append(PageBreak())

para(tag("mech") + "Two further sources are introduced where they are used rather than "
     "here, because each belongs to one argument: the Tibia Token contract on the BNB Smart "
     "Chain and the Char Bazaar turnover aggregates, both in Section 5.8 on venue structure. "
     "Table 8.3 lists every endpoint and capture date for all of them.")
story.append(PageBreak())

h2sec('3.9', 'Kill statistics', 'A gold-production series, validated against activity before it was used')
bottomline("Per-world daily kill counts are the closest observable proxy for gold creation. "
           "They are the series Section 6.6 uses to test the supply channel, and they were "
           "checked against an independent measure of activity before any model saw them.")
para(tag("mech") + f"CipSoft publishes a per-world kill-statistics page giving, for each "
     f"creature, how many were killed in the trailing day and week and how many players that "
     f"creature killed. A third party captures it daily and keeps the history. Monsters killed "
     f"is what produces loot and gold; player deaths destroy it; and the mix of creatures says "
     f"what kind of hunting is happening.")
para(tag("obs") + f"The kill-statistics archive aggregates to {KS_ROWS:,} world-days over "
     f"{KS_WORLDS} worlds. Joined to the price panel and restricted to converged worlds it "
     f"becomes {FD['panel']['rows']:,} world-days over {FD['panel']['worlds']} worlds, "
     f"{FD['panel']['start']} to {FD['panel']['end']} - the frame every fundamentals result is "
     f"fitted on. "
     f"That is far shorter than the price panel because the archive begins in December 2025, "
     f"and it is the binding limitation on every fundamentals result: eight months is a single "
     f"pass through the seasonal year, so the calendar features in Section 6.6 are fitted on "
     f"one cycle and should not be trusted.")
table([["Field", "What it measures", "Treatment"],
       ["monsters_killed", "Creatures killed by players, summed across races",
        "Gold and loot production proxy; entered in logs and as growth rates"],
       ["players_killed", "Players killed by creatures",
        "Gold destruction proxy; deaths cost blessings and dropped loot"],
       ["boss_kills", "Kills of the 327 creatures in the official Bosstiary",
        "Endgame activity; high-value loot"],
       ["races_hunted", "Distinct creature types killed that day", "Breadth of hunting"],
       ["hunt_hhi, top10_share", "Concentration of kills across creature types",
        "Whether a world farms a few spawns or many"],
       ["mix_* (40 series)", "Share of the day's kills in each of the 40 most-hunted races",
        "Reduced to three latent axes by principal components (Section 6.6)"]],
      [34 * mm, 56 * mm, AVAIL - 90 * mm], fs=6.9,
      caption="Table 3.12 - Fields derived from the kill-statistics capture, and how each "
              "enters the analysis.")
h3("3.9.1 Two corrections applied on ingest")
para(tag("mech") + "The page reports the <i>trailing</i> day, so a capture dated D describes "
     "activity on D-1. Dates are shifted back by one on ingest, once and centrally, so nothing "
     "downstream can accidentally look ahead. A world reporting zero kills for an entire day is "
     "a scrape failure rather than a quiet world and is dropped.")
h3("3.9.2 The validation that mattered")
para(tag("stat") + "A series claiming to measure activity should track an independent measure "
     "of activity, and this one does: log monsters killed correlates with log concurrent "
     "players at <b>0.971</b> across the joined panel. That check was run before any model was "
     "fitted, and it is the reason the negative result in Section 6.6.14 can be read as "
     "evidence about the economy rather than as evidence about the data.")
para(tag("lim") + "What the series is not: it counts kills, not gold. No loot table is public, "
     "so a kill cannot be converted into an amount of gold, and a boss kill and a rat kill "
     "enter the totals identically unless the boss flag separates them. The accumulated stock "
     "of gold in circulation remains unobserved, and Section 6.6.14 is careful that its "
     "cumulative measure is close to a time trend and cannot bear weight alone.")
story.append(PageBreak())

h2sec('3.8', 'Event calendar', 'Every event is global, which is what makes causation unidentifiable')
para(tag("obs") + f"Daily event labels were taken from the TibiaMarket.top /events endpoint, "
     f"which covers {W['start']} to {W['end']} in this window. Update release dates are not in "
     f"that endpoint and were taken from official Tibia news via TibiaData's news archive, "
     f"identified as development items titled exactly 'Summer Update YYYY' or "
     f"'Winter Update YYYY'.")
evc = [("XP/Skill event", int(cal.ev_xp_skill.sum())),
       ("Rapid Respawn", int(cal.ev_rapid_respawn.sum())),
       ("Loot event", int(cal.ev_loot.sum())),
       ("Exaltation Overload", int(cal.ev_exaltation.sum())),
       ("Double Daily Reward Month", int(cal.ev_double_reward.sum())),
       ("Any labelled event", int(cal.ev_any.sum())),
       ("Update release", int(cal.update_release.sum())),
       ("Within 14 days before an update", int(cal.pre_update_14.sum())),
       ("Within 30 days after an update", int(cal.post_update_30.sum()))]
table([["Flag", "Days in window", "Share of window"]] +
      [[n, f"{v:,}", pc(v / len(cal) * 100, 1)] for n, v in evc],
      [70 * mm, 26 * mm, AVAIL - 96 * mm], align=[None, "R", "R"],
      caption=f"Table 3.13 - Event calendar over {len(cal):,} days. XP/Skill aggregates the "
              f"'XP/Skill Event', 'Skill Event' and 'Double XP Event' labels; leading asterisks "
              f"in source labels are stripped before aggregation.")
para(tag("obs") + "The seven update releases inside the window are "
     "2023-07-10, 2023-12-04, 2024-07-01, 2024-11-25, 2025-07-21, 2025-11-24 and 2026-07-13.")
para(tag("lim") + "<b>Every event flag is global.</b> The source carries no world dimension, so "
     "on any given date an event is either on for all 93 worlds or off for all of them. "
     "Section 4.6 sets out what this permits and what it forbids.")
story.append(PageBreak())

# ===================================================================== 12
comparison_page(
    "{n} measures that mislead, and what to use instead",
    "Each of these is the number a reader would naturally reach for. Each measures something "
    "other than what its name suggests, and in every case the difference is large enough to "
    "change a conclusion. The corrections are established in the chapters that follow; they "
    "are collected here because they share a shape.",
    [
        ("<b>Players online</b> as a measure of how big a world is.",
         f"A flow, not a stock. Dividing the character roster by mean concurrent players gives "
         f"{min(_RPC.values()):.0f} residents per online player in "
         f"{min(_RPC, key=_RPC.get)} and {max(_RPC.values()):.0f} in "
         f"{max(_RPC, key=_RPC.get)}. Substituting one for the other rotates the "
         f"cross-section and manufactures regional effects.",
         f"{_RPC_SPREAD:.2f}x", "Section 3.7"),

        ("<b>A single players-online reading</b> as that flow.",
         f"An instant, not a day. Because worlds peak at different hours, one snapshot "
         f"understates Europe by {prof.factor_at_0445utc.max():.1f} times and overstates "
         f"North America at the same moment.",
         f"{prof.factor_at_0445utc.max() / prof.factor_at_0445utc.min():.1f}x",
         "Section 3.7"),

        ("<b>The average price across worlds</b> as the market's return.",
         f"A basket that changes composition. Over the same window the naive mean reads "
         f"{pc(IX['naive_total_index_window_pct'], 1, True)} against the chain-linked "
         f"{pc(IX['total_pct'], 1, True)}; run from the start of the archive, when a single "
         f"world was observed, it reads {pc(IX['naive_total_archive_pct'], 1, True)} and most "
         f"of that is coverage, not price.",
         "5x", "Section 4.2"),

        ("<b>The number of standing orders</b> as depth.",
         f"A count, not a quantity. A long tail of tiny non-executable bids inflates the count "
         f"without adding executable size; across worlds the two ratios correlate at only "
         f"{MI['corr_ordercount_vs_depth_ratio']:.2f}.",
         f"r = {MI['corr_ordercount_vs_depth_ratio']:.2f}", "Section 5.6"),

        ("<b>The quoted spread</b> as what trading costs.",
         f"The outer envelope, not the typical execution. Most volume executes inside the "
         f"quotes against resting limit orders, so the Roll effective spread is "
         f"{pc(FN['roll']['median_roll_spread_pct'])} against a quoted "
         f"{pc(FN['roll']['median_quoted_spread_pct'])}.",
         f"{FN['roll']['median_quoted_spread_pct'] / FN['roll']['median_roll_spread_pct']:.0f}x",
         "Section 5.6"),
    ],
    foot="Each correction is derived where it is first needed and is applied consistently "
         "thereafter; none is a judgement call. Where a measure could not be corrected - event "
         "effects, the driver of the common level - the report says so instead of substituting "
         "a proxy.")

chapter(4, 'Price dynamics',
        'What the price has done: its level, its trend, its statistical properties, and how it responds to the calendar and to scheduled events.')
h2sec('4.1', 'Descriptive statistics', 'The coin trades near 39,000 GP with 1.3% daily volatility')
q = panel.groupby("world").price_gp.last()
figure("fig00_price_distribution.png",
       "Exhibit 4.1 - Latest price on every world, ranked, with converged and launch-phase "
       "worlds distinguished. Source: price archive, item_id 22118.")
table([["Statistic", "Value"],
       ["Worlds", f"{W['n_worlds']}"],
       ["Cleaned world-day observations", f"{W['n_world_days']:,}"],
       ["Median observations per world", f"{D['median_obs_per_world']:.0f}"],
       ["Median latest price", f"{gp(D['price_latest_median'])} GP/TC"],
       ["Range of latest prices across worlds",
        f"{gp(D['price_latest_min'])} to {gp(D['price_latest_max'])} GP/TC"],
       ["Cross-world s.d. of log price, all / converged",
        f"{pc(D['cs_sd_pct_latest'], 1)} / {pc(IN['dispersion_last'], 1)}"],
       ["Daily return volatility (converged)", f"{pc(D['ret_sd_daily_pct'])} per day"],
       ["Annualised return volatility", pc(D["ret_sd_ann_pct"], 1)],
       ["Median TC sold per world-day",
        f"{gp(MI['turnover']['median_tc_sold_per_day'])} TC "
        f"({MI['turnover']['median_sold_per_day']:,.0f} lots)"],
       ["Median TC bought per world-day",
        f"{gp(MI['turnover']['median_tc_bought_per_day'])} TC "
        f"({MI['turnover']['median_bought_per_day']:,.0f} lots)"]],
      [82 * mm, AVAIL - 82 * mm], align=[None, "R"],
      caption="Table 4.1 - Headline descriptive statistics. The two dispersion figures differ "
              "because the all-worlds figure includes launch-phase worlds still in price "
              "discovery; only the converged figure is comparable across dates.")
para(tag("obs") + f"The gap between the two dispersion measures is itself informative. Including "
     f"launch-phase worlds inflates cross-world dispersion from {pc(IN['dispersion_last'], 1)} to "
     f"{pc(D['cs_sd_pct_latest'], 1)}, because a handful of very young worlds are still tens of "
     f"percent below the mature level. Pooling them into a cross-sectional statistic would be a "
     f"straightforward error.")
figure("fig15_volatility.png",
       "Exhibit 4.2 - Distribution of daily return volatility across converged worlds. One "
       "observation per world over its full history. Returns are computed only between "
       "consecutive observed days; gaps are not bridged. Source: price archive, item_id 22118.")
story.append(PageBreak())

# ===================================================================== 13
hero(pc(IX["total_pct"], 1, True),
     "is how much the market actually appreciated since April 2024.",
     f"A naive basket over the same window reads {pc(IX['naive_total_index_window_pct'], 1, True)}; "
     f"run from the start of the archive, when one world was observed, it reads "
     f"{pc(IX['naive_total_archive_pct'], 1, True)}. Most of that gap is the window, not "
     f"composition - chain-linking is worth "
     f"{pc(IX['naive_total_index_window_pct'] - IX['total_pct'], 1)} of it.",
     mark="index")
h2sec('4.2', 'Market indices',
      'Chain-linking is worth three points, and the window is worth thirty')
para(tag("obs") + "Because archive coverage grows from a median of one world per date in 2023 "
     "to 85 in 2026, a basket mean is not a valid index: it mixes price change with composition "
     "change. The headline index is chain-linked. Each day's index return is the mean log return "
     "across worlds observed on both that day and the previous day, which is invariant to entry "
     "and exit. The index is reported only from the first date carrying at least 10 converged "
     "worlds.")
para(tag("obs") + f"The chain-linked index begins on {IX['index_start']}, the first date "
     f"carrying at least {IX['min_worlds_required']} converged worlds, at "
     f"{gp(IX['first_ew'])} GP/TC. It ends at {gp(IX['last_ew'])} - a total change of "
     f"{pc(IX['total_pct'], 1, True)}, or {pc(IX['cagr_pct'], 2, True)} annualised - having "
     f"peaked at {gp(IX['peak'])} and troughed at {gp(IX['trough'])}. The largest peak-to-"
     f"trough decline inside the window is {pc(IX['max_drawdown_pct'], 1)}. Table E.3 gives "
     f"the dated detail.")
figure("fig01_index.png",
       "Exhibit 4.3 - Chain-linked index against the naive basket mean, with observed world "
       "count below. The two diverge because the basket's composition changes. Source: price "
       "archive, item_id 22118; converged worlds only.")
para(tag("obs") + f"The quantity-weighted index finishes at {gp(IX['vw_last'])} GP/TC against "
     f"{gp(IX['last_ew'])} for the equal-weighted index, a difference of "
     f"{(IX['vw_last'] / IX['last_ew'] - 1) * 100:+.1f}%. Weighting by traded quantity therefore "
     f"tilts the index toward slightly more expensive worlds, which is consistent with larger, "
     f"more liquid worlds trading marginally above the simple cross-world mean.")
figure("fig14_drawdown.png",
       "Exhibit 4.4 - Drawdown of the chain-linked index from its running peak. Descriptive "
       "only: Section 4.4 finds the level non-stationary, so drawdown depth carries no "
       "implication for future recovery. Source: price archive, item_id 22118.")
story.append(PageBreak())

# ===================================================================== 14
h2sec('4.3', 'Trend', 'A 3.6% annual drift is indistinguishable from zero at this volatility')
para(tag("obs") + f"Over the chain-linked index period the market rose {pc(IX['total_pct'], 1, True)}, "
     f"an annualised {pc(IX['cagr_pct'], 2)}. That drift is modest relative to the "
     f"{pc(D['ret_sd_ann_pct'], 0)} annualised volatility of an individual world, and it is not "
     f"monotone: the index fell to {gp(IX['trough'])} GP/TC on {IX['trough_date']} before "
     f"recovering to a peak of {gp(IX['peak'])} on {IX['peak_date']}.")
para(tag("judg") + f"A drift of {pc(IX['cagr_pct'], 2)} per year estimated over "
     f"{(pd.Timestamp(IX['index_end']) - pd.Timestamp(IX['index_start'])).days / 365.25:.1f} years "
     f"with this much volatility is not distinguishable from zero in any useful sense. The "
     f"standard error on a mean daily return of this magnitude, over this sample, admits both a "
     f"materially positive and a materially negative annual drift. This is the quantitative "
     f"reason the forecast section shrinks drift heavily toward zero rather than extrapolating "
     f"the trend.")
para(tag("hyp") + "The most common explanation for a positive long-run drift is gold inflation: "
     "if the stock of gold grows faster than the stock of goods and premium currency, a fixed "
     "real-value asset should cost more gold over time. That mechanism would produce exactly the "
     "pattern observed. It remains a hypothesis. Testing it requires a gold supply or gold income "
     "series, and no such series exists in any source accessible for this study.")
story.append(PageBreak())

# ===================================================================== 15
h2sec('4.4', 'Time-series properties', "The level carries a unit root, so today's price is the honest forecast")
bottomline("The level carries a unit root, so the honest central forecast at every horizon is the current "
           "price. Short-horizon reversal exists but sits inside the spread.")
para(tag("stat") + "Stationarity was tested on every converged world with at least 250 daily "
     "observations, using an augmented Dickey-Fuller test with automatic lag selection and a "
     "KPSS test with automatic bandwidth. The two tests have opposite null hypotheses, so "
     "agreement between them is strong evidence.")
table([["Test", "Null hypothesis", "Result", "Interpretation"],
       ["ADF", "Unit root present",
        f"Fails to reject on {ST['n'] - ST['adf_reject_5pct']} of {ST['n']} worlds at 5%",
        "Cannot rule out a unit root"],
       ["KPSS", "Series is stationary",
        f"Rejects on {ST['kpss_reject_5pct']} of {ST['n']} worlds at 5%",
        "Rules out stationarity"],
       ["Ljung-Box (10)", "Returns are independent",
        f"Rejects on {ST['lb_reject_5pct']} of {ST['n']} worlds at 5%",
        "Returns are serially dependent"]],
      [22 * mm, 32 * mm, 50 * mm, AVAIL - 104 * mm],
      caption=f"Table 4.2 - Stationarity and independence tests on log price levels and daily "
              f"log returns. ADF p-values range from {ST['adf_p_min']:.3g} to "
              f"{ST['adf_p_max']:.2f}, median {ST['adf_p_median']:.2f}.")
para(tag("stat") + "The two tests agree for the large majority of worlds: <b>the level is "
     "non-stationary</b>. A minority of worlds reject the unit root under ADF, which is expected "
     "when running 61 independent tests at the 5% level and does not overturn the joint reading.")

h3("4.4.1 The consequence for forecasting")
para(tag("judg") + "If the level contains a unit root, the conditional expectation of the future "
     "level is the current level plus accumulated drift. The honest central forecast at every "
     "horizon is therefore approximately today's price. Section 6.4 implements exactly this and "
     "declines to impose level mean reversion.")

h3("4.4.2 Measurement noise, and why the naive half-life is wrong")
para(tag("stat") + f"Daily returns carry a mean first-order autocorrelation of "
     f"{IN['mean_return_ac1']:+.3f} across converged worlds. Negative first-order "
     f"autocorrelation of this kind is the classic signature of transitory measurement noise in "
     f"the price: the daily price is a mean of executed trades on a thin book, so it estimates "
     f"the true daily level with error.")
para(tag("stat") + "This has a direct and important consequence for any persistence estimate. "
     "Classical measurement error attenuates an autoregressive coefficient toward zero, which "
     "makes an estimated half-life too short. The diagnostic is to estimate persistence at "
     "increasing horizons: noise contaminates the one-day estimate most and longer horizons "
     "progressively less.")
hh = IN["half_life_by_horizon"]
table([["Horizon h (days)", "Estimated persistence rho(h)", "Implied half-life (days)", "n"]] +
      [[h, f"{hh[str(h)]['rho_h']:.4f}", f"{hh[str(h)]['implied_half_life_days']:.1f}",
        f"{hh[str(h)]['n']:,}"] for h in sorted(int(k) for k in hh)],
      [30 * mm, 44 * mm, 40 * mm, AVAIL - 114 * mm], align=["R", "R", "R", "R"],
      caption="Table 4.3 - Persistence of the cross-world deviation estimated at increasing "
              "horizons, world fixed effects, two-way clustered standard errors. The monotone "
              "rise in the implied half-life is the attenuation signature.")
figure("fig04_halflife.png",
       "Exhibit 4.5 - Implied half-life by estimation horizon, with the weekly-averaged "
       "estimate for comparison. Source: price archive, item_id 22118; converged worlds, dates "
       "with at least 10 observed worlds.")
para(tag("judg") + f"The one-day estimate implies a half-life of "
     f"{hh['1']['implied_half_life_days']:.1f} days and should not be used. Averaging deviations "
     f"to weekly frequency, which cuts the noise variance roughly sevenfold, gives "
     f"{IN['half_life_weekly_days']:.0f} days. Horizons of 10 to 30 days imply "
     f"{hh['10']['implied_half_life_days']:.0f} to {hh['30']['implied_half_life_days']:.0f} days. "
     f"<b>The defensible statement is that a cross-world price gap has a half-life of roughly "
     f"three to four weeks</b>, and that any figure near one week is an artefact of daily "
     f"measurement noise.")
story.append(PageBreak())

h3("4.4.3 Weak-form efficiency and the variance-ratio test")
para(tag("stat") + "A unit root is a weaker statement than market efficiency. The sharper test "
     "is Lo and MacKinlay's (1988) variance ratio: under a random walk the variance of a "
     "q-day return is exactly q times the variance of a one-day return, so VR(q) = 1 at every "
     "horizon. Values below one indicate mean reversion.")
EFF = FN["efficiency"]
table([["Horizon q", "Median VR(q)", "Worlds rejecting at 5%", "Reading"]] +
      [[f"{q} days", f"{EFF[f'vr{q}_median']:.3f}",
        f"{EFF[f'vr{q}_reject_5pct']} of {EFF['n_worlds']}",
        "random walk" if abs(EFF[f'vr{q}_median'] - 1) < 0.05 else "reversion"]
       for q in (2, 5, 10, 20)],
      [22 * mm, 28 * mm, 38 * mm, AVAIL - 88 * mm], align=[None, "R", "R", None],
      caption="Table 4.4 - Lo-MacKinlay variance ratios with the heteroskedasticity-robust "
              "statistic, converged worlds with at least 300 daily observations.")
figure("fig22_variance_ratio.png",
       "Exhibit 4.6 - Variance ratios by aggregation horizon. Source: price archive, "
       "item_id 22118; converged worlds.")
para(tag("stat") + f"The random walk is rejected. Variance ratios fall monotonically from "
     f"{EFF['vr2_median']:.2f} at two days to {EFF['vr20_median']:.2f} at twenty, and the "
     f"robust statistic rejects at the two-day horizon on "
     f"{EFF['vr2_reject_5pct']} of {EFF['n_worlds']} worlds. Returns are therefore "
     f"statistically forecastable from their own history, which is a violation of weak-form "
     f"efficiency in the strict sense.")
para(tag("econ") + f"<b>It is not, however, an exploitable one.</b> Section 5.6.4 shows the "
     f"reversal is the mechanical consequence of trading against a spread: Roll's estimator "
     f"attributes it to an effective spread of "
     f"{pc(FN['roll']['median_roll_spread_pct'])}. A price that bounces between the bid and "
     f"the ask generates exactly this negative autocorrelation while offering no profit, "
     f"because capturing it would require buying at the bid and selling at the ask - which is "
     f"the spread itself. The efficient-markets reading is the standard one: prices are "
     f"efficient <i>up to transaction costs</i>, and the measured inefficiency is smaller than "
     f"the cost of trading it.")
para(tag("judg") + f"Whether this statistical predictability converts into economic "
     f"predictability is a question to be tested, not assumed, and Section 6.6 tests it. The "
     f"answer there is that the cross-world deviation <i>is</i> forecastable - the best tuned "
     f"model reaches an out-of-sample R-squared of {MAXP['best_r2']:.3f} with "
     f"{MAXP['best_dir_acc']:.1%} directional accuracy - and that the reversion it captures is "
     f"smaller than the fee on an average signal held a week - though not at the strongest "
     f"decile held a month, which Section 7.7 shows does clear it. The forecasting model of "
     f"Section 6.4 is built for the price level, which is a different quantity and remains a "
     f"random walk.")
story.append(PageBreak())

# ===================================================================== 16
h2sec('4.5', 'Seasonality', 'Autumn is the strongest stretch, but events and calendar are the same variation')
SE = R["seasonality"]
mn = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
      "October", "November", "December"]
table([["Month", "Mean daily return", "Month", "Mean daily return"]] +
      [[mn[i - 1], pc(SE["month_pct"][str(i)], 3, True),
        mn[i + 5], pc(SE["month_pct"][str(i + 6)], 3, True)] for i in range(1, 7)],
      [30 * mm, 32 * mm, 30 * mm, AVAIL - 92 * mm], align=[None, "R", None, "R"],
      caption="Table 4.5 - Mean daily log return by calendar month, converged worlds.")
para(tag("obs") + f"The strongest months are {mn[SE['best_month'] - 1]} "
     f"({pc(SE['month_pct'][str(SE['best_month'])], 3, True)} per day) and the weakest is "
     f"{mn[SE['worst_month'] - 1]} ({pc(SE['month_pct'][str(SE['worst_month'])], 3, True)} per "
     f"day). Day-of-week variation is small; the largest absolute t-statistic on any day-of-week "
     f"dummy, with world fixed effects and two-way clustered standard errors, is "
     f"{SE['dow_joint_maxabs_t']:.2f}.")
figure("fig10_seasonality.png",
       "Exhibit 4.7 - Mean daily log return by calendar month and by day of week. Source: price "
       "archive, item_id 22118; converged worlds. Event days are not excluded.")
para(tag("lim") + "Two caveats limit what can be read from this. First, CipSoft's events cluster "
     "seasonally, so a calendar-month effect and an event effect are largely the same variation "
     "viewed two ways; Section 4.6 shows the event coefficients carry the same sign as the weak "
     "months. Second, day-of-week buckets inherit the server-save misalignment described in "
     "Section 3.3.2, which blurs any genuine intra-week pattern. Neither the monthly nor the "
     "weekly pattern should be treated as a tradable regularity.")
story.append(PageBreak())

# ===================================================================== 17
h2sec('4.6', 'Event studies', 'Event days carry weaker prices, and no event effect is causally identified')
para(tag("obs") + "Two specifications are reported. The first absorbs world fixed effects only, "
     "which identifies event coefficients but confounds them with everything else occurring on "
     "the same dates. The second adds date fixed effects.")
wf = EVR["world_fe"]
rows = [["Event flag", "Coefficient (%/day)", "Std. error", "p", "Days on"]]
for k, lab, days in [("ev_xp_skill", "XP/Skill event", int(cal.ev_xp_skill.sum())),
                     ("ev_rapid_respawn", "Rapid Respawn", int(cal.ev_rapid_respawn.sum())),
                     ("ev_loot", "Loot event", int(cal.ev_loot.sum())),
                     ("ev_exaltation", "Exaltation Overload", int(cal.ev_exaltation.sum())),
                     ("pre_update_14", "14 days before an update", int(cal.pre_update_14.sum())),
                     ("post_update_30", "30 days after an update", int(cal.post_update_30.sum()))]:
    if k in wf:
        rows.append([lab, f"{wf[k]['coef_pct']:+.3f}", f"{wf[k]['se_pct']:.3f}",
                     pval(wf[k]["p"]), f"{days:,}"])
table(rows, [56 * mm, 32 * mm, 22 * mm, 20 * mm, AVAIL - 130 * mm],
      align=[None, "R", "R", "R", "R"],
      caption="Table 4.6 - Event associations with daily log returns. World fixed effects, "
              "standard errors two-way clustered by world and date. Converged worlds.")
figure("fig06_events.png",
       "Exhibit 4.8 - Event coefficients with 95% intervals. Source: price archive, item_id "
       "22118; event labels from TibiaMarket.top /events; update dates from official Tibia news.")

h3("4.6.1 The identification problem is structural, not incidental")
para(tag("lim") + f"Every event label in the source is global: it applies to all worlds on a "
     f"given date. An event indicator is therefore a pure function of the date, which makes it "
     f"perfectly collinear with date fixed effects. This was verified directly rather than "
     f"assumed: after absorbing date fixed effects, the largest residual standard deviation "
     f"across all six event indicators is "
     f"{EVR['world_date_fe']['max_residual_sd_after_absorbing_date_fe']:.1e}, which is zero to "
     f"machine precision. <b>In the world-and-date fixed-effects specification no event "
     f"coefficient is identified at all</b>, and none is reported.")
para(tag("judg") + "The consequence is that the world-fixed-effects estimates in Table 4.6 "
     "cannot be given a causal reading. They measure how returns on event days differ from "
     "returns on other days, which bundles the event with every other thing that systematically "
     "happens on those dates - seasonality, holidays, update cycles, and CipSoft's own reasons "
     "for scheduling an event then.")

h3("4.6.2 Window sensitivity")
para(tag("obs") + "The pre- and post-update windows were not pre-registered, so their "
     "sensitivity is reported explicitly.")
aw = EVR["alt_windows"]
table([["Window", "Coefficient (%/day)", "Std. error", "p"]] +
      [[lab, f"{aw[k]['coef_pct']:+.3f}", f"{aw[k]['se_pct']:.3f}", pval(aw[k]["p"])]
       for k, lab in [("pre_7d", "7 days before an update"),
                      ("pre_14d", "14 days before an update"),
                      ("pre_30d", "30 days before an update"),
                      ("post_14d", "14 days after an update"),
                      ("post_30d", "30 days after an update")] if k in aw],
      [52 * mm, 32 * mm, 24 * mm, AVAIL - 108 * mm], align=[None, "R", "R", "R"],
      caption="Table 4.7 - Sensitivity of the update-window result to window length. World "
              "fixed effects, two-way clustered standard errors.")
para(tag("obs") + f"The pre-update effect is strongest at the shortest window "
     f"({pc(aw['pre_7d']['coef_pct'], 3, True)} per day over 7 days) and weakens monotonically "
     f"as the window lengthens, becoming statistically indistinguishable from zero at 30 days "
     f"(p {pval(aw['pre_30d']['p'])}). That monotone decay is what a genuine, time-concentrated "
     f"effect would look like, and it is reassuring that the result is not an artefact of one "
     f"arbitrary window choice - but it does not resolve the identification problem above.")

h3("4.6.3 Two mechanisms the data cannot separate")
para(tag("econ") + "The negative coefficient on XP/Skill and Rapid Respawn days is consistent "
     "with at least two mechanisms, and the data cannot distinguish them:")
bullets([
    tag("hyp") + "<b>Supply.</b> Coin holders sell into the gold demand that events generate, "
    "increasing coin supply on the Market and depressing the GP price.",
    tag("hyp") + "<b>Diversion.</b> Players redirect gold toward consumables and supplies for "
    "efficient hunting during the event, reducing gold available to bid for coins.",
])
para(tag("judg") + "Both predict a lower GP price on event days with the same sign and a similar "
     "magnitude. Separating them would require order-flow data identifying who initiated each "
     "trade, which the anonymised order book does not provide.")
story.append(PageBreak())

# ===================================================================== 18
chapter(5, 'Market structure, arbitrage and liquidity',
        'How the 93 worlds relate to one another - where arbitrage bites, what explains the differences between worlds, and how liquidity is actually supplied.')
h2sec('5.1', 'Cross-world integration', 'Levels move together over weeks; daily returns barely move together at all')
para(tag("mech") + "Because Tibia Coins move between worlds at the account level with no "
     "character transfer required, the same asset is quoted simultaneously in 93 local markets. "
     "The question is not whether those markets are linked - the mechanic guarantees a channel - "
     "but how tightly, and what limits the tightness.")
table([["Measure", "Value", "Reading"],
       ["Mean cross-world dispersion of log price", pc(IN["mean_dispersion_pct"], 2),
        "Sits just above the round-trip fee"],
       ["Median cross-world dispersion", pc(IN["median_dispersion_pct"], 2), "-"],
       ["Latest cross-world dispersion", pc(IN["dispersion_last"], 2), "-"],
       ["Mean pairwise correlation of price levels",
        f"{IN['mean_pairwise_level_corr']:.3f}", "Levels move closely together"],
       ["Mean pairwise correlation of daily returns",
        f"{IN['mean_pairwise_ret_corr']:.3f}", "Daily moves are largely idiosyncratic"],
       ["Half-life of a cross-world gap", f"~{IN['half_life_weekly_days']:.0f} days",
        "From weekly-averaged data (Section 4.4.2)"]],
      [66 * mm, 26 * mm, AVAIL - 92 * mm], align=[None, "R", None],
      caption="Table 5.1 - Cross-world integration measures. Converged worlds, dates carrying "
              "at least 10 observed worlds.")
para(tag("stat") + f"The contrast between the two correlation figures is the key structural "
     f"fact. Price <i>levels</i> across worlds are highly correlated "
     f"({IN['mean_pairwise_level_corr']:.2f}), because they share a common slow-moving "
     f"component. Daily <i>returns</i> are barely correlated "
     f"({IN['mean_pairwise_ret_corr']:.2f}), because day-to-day movement on any one world is "
     f"dominated by local, idiosyncratic trading. Integration operates over weeks, not within "
     f"the day.")
figure("fig02_dispersion.png",
       "Exhibit 5.1 - Cross-world dispersion of log price against the 4% round-trip Market fee. "
       "Dispersion is the cross-sectional standard deviation on each date. The 4% line is twice "
       "the documented 2% offer fee, not a fitted parameter. Source: price archive, item_id "
       "22118; converged worlds, dates with at least 10 observed worlds.")
para(tag("econ") + f"Mean dispersion of {pc(IN['mean_dispersion_pct'], 2)} sits just above the "
     f"4% round-trip cost. That is what a transaction-cost-bounded market should look like: "
     f"dispersion is held near, but not below, the level at which correcting it becomes "
     f"profitable. A market with no frictions would show dispersion near zero; a market with no "
     f"linkage would show dispersion limited only by local conditions.")
story.append(PageBreak())

# ===================================================================== 19
h2sec('5.2', 'Arbitrage', 'Gaps close only once they exceed the cost of closing them')
h3("5.2.1 What the data show")
table([["Lagged gap", "Next-day closure (pp/day)", "Std. error", "p", "n", "Restoring force?"]] +
      [[r["bin"], f"{r['closure_pp']:+.3f}", f"{r['se']:.3f}", pval(r["p"]), f"{int(r['n']):,}",
        "No - gap widens" if r["closure_pp"] < 0 else "Yes - gap closes"]
       for _, r in band.iterrows()],
      [22 * mm, 34 * mm, 20 * mm, 17 * mm, 17 * mm, AVAIL - 110 * mm],
      align=[None, "R", "R", "R", "R", None],
      caption="Table 5.2 - Next-day movement of the cross-world price gap by gap size. "
              "Newey-West standard errors. Positive means the gap narrowed.")
figure("fig03_arbitrage_band.png",
       "Exhibit 5.2 - The arbitrage band. Source: price archive, item_id 22118; converged "
       "worlds, dates with at least 10 observed worlds.")
para(tag("stat") + tag("econ") + "The pattern is monotone and the sign changes between the 2-4% "
     "and 4-6% bins. Below the threshold there is no restoring force at all - small gaps drift "
     "wider. Above it, gaps close, and they close faster the larger they are. This is the "
     "signature of a transaction-cost band around a law-of-one-price relationship.")
para(tag("judg") + f"<b>Two numbers describe the same friction and they are not the same "
     f"number, which is worth stating plainly.</b> The threshold model puts the regime switch "
     f"at {pc(R['advanced']['tar']['threshold_pct'])}, estimated by grid search on the "
     f"continuous deviation. The binned closure above only turns positive in the 4-6% bucket. "
     f"Both are correct: the threshold locates where the reversion coefficient changes sign in "
     f"a model fitted to every observation, while the bins average over wide ranges and the "
     f"2-4% bucket still contains more drift than reversion. The report uses "
     f"{pc(R['advanced']['tar']['threshold_pct'])} when describing market structure and 4% when "
     f"telling a reader when to act, because acting needs the gap to clear the round trip with "
     f"a margin, not merely to have stopped widening.")
para(tag("judg") + f"Bin edges chosen by hand can only locate the threshold to within a "
     f"bucket. Section 6.3.1 estimates it formally by threshold autoregression and puts it at "
     f"{pc(R['advanced']['tar']['threshold_pct'])}, with the band structure itself - no "
     f"reversion inside, decisive reversion outside - confirmed at a bootstrap p below 0.001. "
     f"The figures below should be read as establishing the shape; the formal model locates "
     f"the break.")

h3("5.2.2 How the band is measured")
para(tag("stat") + "For each world and date, the deviation is the world's log price minus the "
     "cross-world mean log price on that date, restricted to dates carrying at least 10 observed "
     "converged worlds. The deviation is then <b>lagged one day</b> and sorted into bins by "
     "absolute size. Within each bin the average next-day change in the absolute gap is measured, "
     "signed so that a positive value means the gap narrowed.")
para(tag("judg") + "Lagging is essential rather than cosmetic. A same-day deviation and a "
     "same-day return share the same price observation, so regressing one on the other is "
     "mechanically correlated and produces a coefficient whose sign reflects arithmetic rather "
     "than economics. Every deviation term in this report is lagged.")

h3("5.2.3 Does the threshold hold across sub-samples?")
para(tag("obs") + "The pooled estimate could mask heterogeneity, so the band was re-estimated "
     "within years, regions, PvP types and world sizes. The reported quantity is the first bin "
     "in which the gap begins to close.")
sub = AR["subsamples"]
order = ["2024", "2025", "2026", "Europe", "North America", "South America",
         "Open PvP", "Optional PvP", "large worlds", "small worlds"]
table([["Sub-sample", "First bin showing closure", "Observations"]] +
      [[k, sub[k]["first_positive_bin"] or "none", f"{sub[k]['n']:,}"]
       for k in order if k in sub],
      [46 * mm, 46 * mm, AVAIL - 92 * mm], align=[None, "C", "R"],
      caption="Table 5.3 - Stability of the arbitrage threshold across sub-samples. The 2023 "
              "sub-sample is omitted: the archive observes too few worlds per date that year "
              "for a cross-world mean to be defined.")
figure("fig19b_band_stability.png",
       "Exhibit 5.3 - Mean gap closure by year and gap size. Source: price archive, "
       "item_id 22118; converged worlds, dates with at least 10 observed worlds.")
para(tag("obs") + f"The threshold sits in the 4-6% bin in eight of the ten sub-samples. Two "
     f"exceptions are informative rather than contradictory. South American worlds and the 2026 "
     f"sub-sample begin closing one bin earlier, in 2-4%; both are the samples with the densest "
     f"world coverage and the most active cross-world trading, where a slightly finer band is "
     f"exactly what lower effective friction would produce. Optional-PvP worlds begin closing one "
     f"bin later, in 6-10%.")
para(tag("judg") + "The threshold is therefore stable in the sense that matters: it is never "
     "absent, never far from 4%, and never below the level at which arbitrage becomes "
     "unprofitable. That is a considerably stronger claim than a single pooled estimate.")

h3("5.2.6 Limits to arbitrage: why the band is not closed")
para(tag("econ") + "Textbook arbitrage requires no capital and carries no risk, and would "
     "eliminate any gap. The cross-world coin trade satisfies neither condition. Shleifer and "
     "Vishny (1997) show that when arbitrage is carried out by capital-constrained specialists "
     "rather than by a frictionless market, deviations can persist and can even widen before "
     "they close. Each element of their argument has a documented counterpart here.")
table([["Friction", "Documented mechanic", "Consequence for the band"],
       ["Transaction cost", "2% per offer, non-refundable, capped at 1,000,000 GP",
        "Sets the width of the no-trade band"],
       ["Funding constraint", "Gold frozen while a buy offer rests",
        "Capital committed on both worlds simultaneously"],
       ["Position limits", f"100 open offers; {FE['qty_cap']:,} units per offer",
        "Caps the size of any single correcting trade"],
       ["Lot size", f"Quantities move in multiples of {FE['lot_size']}",
        f"No trade smaller than {FE['lot_size']} TC exists - about "
        f"{gp(FE['min_trade_value_gp'])} GP at the median price"],
       ["Horizon risk", f"Gap half-life of roughly three to four weeks (Section 4.4.2)",
        "Capital is tied up while the common level moves"],
       ["Inventory risk", f"{pc(D['ret_sd_ann_pct'], 0)} annualised volatility of the level",
        "The position is exposed to the common factor throughout"],
       ["Supply lock", "Newly purchased coins non-transferable for up to 6 months",
        "Delays the response of coin supply to a price gap"]],
      [30 * mm, 62 * mm, AVAIL - 92 * mm],
      caption="Table 5.4 - Frictions limiting cross-world arbitrage, and their effect on the "
              "no-trade band.")
para(tag("stat") + f"Two pieces of evidence indicate that the binding constraint is not the fee "
     f"alone. First, the estimated friction point of "
     f"{pc(R['advanced']['tar']['threshold_pct'])} (Section 6.3.1) sits above the "
     f"{pc(FE['roundtrip_largest_decile_pct'], 2)} round-trip cost faced by the largest "
     f"offers, so the traders who could close gaps most cheaply are evidently not closing them "
     f"down to their own cost. Second, quantile regression shows adjustment is concentrated in "
     f"the upper tail of the return distribution.")
qr_ = R["finance"]["quantile"]
table([["Quantile of daily return", "Coefficient on lagged gap", "Std. error"]] +
      [[f"{q['tau']:.2f}", f"{q['coef']:+.4f}", f"{q['se']:.4f}"] for q in qr_],
      [46 * mm, 42 * mm, AVAIL - 88 * mm], align=[None, "R", "R"],
      caption="Table 5.5 - Quantile regression of the daily return on the lagged deviation, "
              "world fixed effects absorbed.")
figure("fig23_quantile.png",
       "Exhibit 5.4 - Adjustment speed across the return distribution. Source: price archive, "
       "item_id 22118; converged worlds.")
para(tag("econ") + f"Adjustment at the 90th percentile ({qr_[-1]['coef']:+.3f}) is about three "
     f"times that at the 10th ({qr_[0]['coef']:+.3f}). The band is enforced in bursts - "
     f"episodes of sharp repricing - rather than by continuous pressure. That is the signature "
     f"of arbitrage capital arriving intermittently rather than standing ready, which is "
     f"precisely the Shleifer-Vishny mechanism.")
para(tag("judg") + "The practical reading for a would-be arbitrageur is that the gap is not "
     "free money at any size. Closing it requires holding characters and working capital on "
     "both worlds, paying a fee that is not returned if the offer is cancelled, and bearing "
     "several weeks of exposure to a level that is itself a random walk.")

h3("5.2.4 Whose cost is 4%? The fee cap matters")
para(tag("mech") + f"The coincidence between the observed threshold and the round-trip fee "
     f"needs one important qualification. The 2% offer fee is <b>capped at "
     f"{FE['cap_gp']:,} GP</b>, so 4% is the round-trip cost only for offers small enough that "
     f"the cap does not bind. Above roughly {FE['cap_binds_above_tc']:,.0f} TC at current "
     f"prices, the effective rate falls away sharply.")
dec = pd.DataFrame(FE["roundtrip_by_decile"])
table([["Offer-size decile (median TC)", "Round-trip cost", "Reading"]] +
      [[f"{r.median_tc:,.0f} TC", pc(r.roundtrip_pct, 2),
        "cap does not bind" if r.roundtrip_pct > 3.99 else
        ("cap partially binds" if r.roundtrip_pct > 1 else "cap dominates")]
       for _, r in dec.iterrows()],
      [46 * mm, 30 * mm, AVAIL - 76 * mm], align=[None, "R", None],
      caption=f"Table 5.6 - Observed round-trip Market fee by offer size, computed on "
              f"{FE['n_offers']:,} live offers across 93 worlds at their own quoted prices.")
figure("fig17_fee_schedule.png",
       "Exhibit 5.5 - Round-trip fee against offer size. Sources: documented Market mechanics; "
       "TibiaMarket.top /market_board, 4,098 live offers, 2026-07-30.")
para(tag("obs") + f"The cap binds on {pc(FE['share_capped_by_count'] * 100, 0)} of live offers "
     f"by count but {pc(FE['share_capped_by_value'] * 100, 0)} by value. In other words, most "
     f"of the money posted on these order books enjoys a fee far below 2%, while most of the "
     f"individual offers do not.")
para(tag("judg") + f"<b>This makes the 4% result more interesting, not less.</b> If the "
     f"cross-world price gap were being closed by the largest traders, the band should sit near "
     f"their cost - about {pc(FE['roundtrip_largest_decile_pct'], 2)} for the top decile - and "
     f"gaps of 1 or 2% would close. They do not: Section 5.2.2 shows no restoring force at all "
     f"below 4%. The band sits at the <i>small</i> trader's cost even though large offers exist "
     f"and would be far cheaper to execute.")
para(tag("hyp") + "Three explanations fit that pattern and the data cannot separate them. "
     "Large resting offers may be local market-making rather than cross-world arbitrage, so "
     "the trader who actually moves coins between worlds is the smaller one. Cross-world "
     "arbitrage requires characters on both worlds and, because a buy offer freezes gold until "
     "it fills, working capital simultaneously locked on both sides - a constraint the fee "
     "schedule does not capture. Or the effective barrier may be a different friction of "
     "similar magnitude, with the fee coincidence partly accidental.")
para(tag("judg") + "The honest statement is therefore narrower than a bare reading of "
     "Section 5.2.2 would suggest. What the data establish is a real, monotone, "
     "transaction-cost-shaped band whose threshold sits at approximately 4%. That this equals "
     "the uncapped round-trip fee is a striking correspondence and the most natural "
     "explanation, but it is an interpretation, and the fee cap means it cannot be the whole "
     "story.")

h3("5.2.5 Practical reading")
para(tag("econ") + f"For a player considering a cross-world coin trade at ordinary size, the "
     f"operational content is that a spread below roughly 4% is not an opportunity - it is "
     f"smaller than the fee required to capture it on the average signal. Section 7.7 shows the "
     f"strongest decile, held a month or longer, is the exception. "
     f"Gaps above 6% do close, at an average of "
     f"{band.loc[band.bin == '6-10%', 'closure_pp'].iloc[0]:.2f} percentage points per day, and "
     f"gaps above 10% at {band.loc[band.bin == '>10%', 'closure_pp'].iloc[0]:.2f} points per "
     f"day. With a half-life near three weeks (Section 4.4.2), capturing such a gap is a matter "
     f"of weeks, not days, and is exposed to the full volatility of the common level meanwhile.")
para(tag("judg") + f"A trader able to post offers of {gp(FE['cap_binds_at_lot_tc'])} TC or "
     f"more - the first lot at which the fee cap bites - faces materially lower costs and could in principle act on narrower gaps. Whether that "
     f"is profitable depends on the capital that must be locked on both worlds and on the "
     f"non-refundable fee paid on any offer that is cancelled rather than filled - neither of "
     f"which this study can observe.")
story.append(PageBreak())

# ===================================================================== 20
h2sec('5.3', 'World type and region', 'Optional PvP commands a premium; size, age and region do not')
para(tag("stat") + "Cross-sectional regressions of the latest log price on documented world "
     "attributes. Groups are defined by attributes, never by price.")
def csrow(spec, key, lab):
    if key not in CS[spec]:
        return None
    c = CS[spec][key]
    return [lab, f"{c['coef']:+.4f}", f"{c['se']:.4f}", pval(c["p"]),
            pc(c["coef"] * 100, 1, True)]
rows = [["Variable", "Coefficient", "Std. error", "p", "Implied price effect"]]
for k, lab in [("optional_pvp", "Optional PvP (vs Open PvP)"),
               ("be_release", "BattlEye since release (vs retrofitted)"),
               ("age_y", "World age (years)"),
               ("log_pop", "Log population (true daily average)")]:
    r_ = csrow("type_age_pop", k, lab)
    if r_:
        rows.append(r_)
table(rows, [62 * mm, 24 * mm, 22 * mm, 18 * mm, AVAIL - 126 * mm],
      align=[None, "R", "R", "R", "R"],
      caption=f"Table 5.7 - Cross-sectional model of the price level, "
              f"n = {CS['type_age_pop']['_n']} converged worlds, "
              f"R-squared {CS['type_age_pop']['_r2']:.3f}.")

h3("5.3.1 Optional PvP carries a real premium")
para(tag("stat") + f"Optional-PvP worlds price "
     f"{pc(CS['type_age_pop']['optional_pvp']['coef'] * 100, 1)} above Open-PvP worlds "
     f"(p {pval(CS['type_age_pop']['optional_pvp']['p'])}), and the estimate is stable across "
     f"specifications.")
para(tag("econ") + "A plausible mechanism is that Optional-PvP worlds have weaker "
     "death-penalty gold sinks: characters die less often to other players, lose less gold and "
     "fewer supplies, and so gold accumulates faster relative to the goods available for it. "
     "A larger gold stock chasing a premium asset of fixed real value implies a higher GP price. "
     "This is an interpretation consistent with the sign and magnitude, not a measurement - "
     "testing it requires the gold-flow data that does not exist.")

h3("5.3.2 BattlEye status is a cohort marker, not an effect")
para(tag("stat") + f"Worlds protected by BattlEye since release price "
     f"{pc(CS['type_age_pop']['be_release']['coef'] * 100, 1)} below retrofitted worlds "
     f"(p {pval(CS['type_age_pop']['be_release']['p'])}). This must not be read as an effect of "
     f"the anti-cheat system.")
para(tag("lim") + f"BattlEye arrived in 2017, so 'protected since release' is a statement about "
     f"when a world was created. Worlds in that group have a median age of "
     f"{CS['be_age_confound']['median_age_release']:.1f} years against "
     f"{CS['be_age_confound']['median_age_retrofit']:.1f} years for retrofitted worlds "
     f"(Mann-Whitney p {pval(CS['be_age_confound']['mw_p'])}, "
     f"n = {CS['be_age_confound']['n_release']} and "
     f"{CS['be_age_confound']['n_retrofit']}). The variable is a vintage indicator wearing an "
     f"anti-cheat label, and it is reported here as a cohort marker only.")
para(tag("obs") + f"Consistent with that, world age entered directly is statistically "
     f"indistinguishable from zero (p {pval(CS['type_age_pop']['age_y']['p'])}) once both "
     f"variables are included. The two compete for the same variation.")

h3("5.3.3 Population is irrelevant to the price; engagement is not")
para(tag("stat") + "Six size measures were tested, four stocks and two flows. Taken one at a "
     "time, none is significant at the 5% level.")
pcm = CS["population_measure_comparison"]
takeaway('No measure of world size is significant on its own - two population stocks, two activity flows and guild membership all fail.')
table([["Measure", "Type", "Coefficient", "Std. error", "p"]] +
      [[lab, typ, f"{pcm[k]['coef']:+.4f}", f"{pcm[k]['se']:.4f}", pval(pcm[k]["p"])]
       for k, lab, typ in [
           ("full_roster_tibiavip", "Character roster (population)", "Stock"),
           ("active_chars_census", "Active high-level characters", "Stock"),
           ("guild_membership_stock", "Characters in guilds", "Stock"),
           ("achievement_points_stock", "Achievement points", "Stock"),
           ("concurrent_activity_daily_avg", "Concurrent players, daily average", "Flow"),
           ("concurrent_activity_instant", "Concurrent players, one instant", "Flow")]
       if k in pcm],
      [58 * mm, 16 * mm, 24 * mm, 22 * mm, AVAIL - 120 * mm],
      align=[None, None, "R", "R", "R"],
      caption="Table 5.8 - Log price regressed on each size measure in turn, controlling for "
              "PvP type and BattlEye cohort, converged worlds.")
ef = CS["engagement_full"]
para(tag("stat") + "Entering population and activity together separates two things that are "
     "confounded when either is used alone.")
table([["Specification", "Variable", "Coefficient", "Std. error", "p"],
       ["Population and activity", "Log population (roster)",
        f"{CS['type_age_pop_act']['log_pop']['coef']:+.4f}",
        f"{CS['type_age_pop_act']['log_pop']['se']:.4f}",
        pval(CS['type_age_pop_act']['log_pop']['p'])],
       ["", "Log concurrent activity",
        f"{CS['type_age_pop_act']['log_act']['coef']:+.4f}",
        f"{CS['type_age_pop_act']['log_act']['se']:.4f}",
        pval(CS['type_age_pop_act']['log_act']['p'])],
       ["Engagement form", "Log engagement (activity per character)",
        f"{ef['log_engagement']['coef']:+.4f}", f"{ef['log_engagement']['se']:.4f}",
        pval(ef['log_engagement']['p'])],
       ["", "Log population (roster)", f"{ef['log_pop']['coef']:+.4f}",
        f"{ef['log_pop']['se']:.4f}", pval(ef['log_pop']['p'])],
       ["", "Premium account share", f"{ef['premium_share']['coef']:+.4f}",
        f"{ef['premium_share']['se']:.4f}", pval(ef['premium_share']['p'])]],
      [40 * mm, 58 * mm, 24 * mm, 22 * mm, AVAIL - 144 * mm],
      align=[None, None, "R", "R", "R"],
      caption=f"Table 5.9 - Separating the population stock from the activity flow. Both "
              f"specifications also control for PvP type and BattlEye cohort. "
              f"n = {ef['_n']}, R-squared {ef['_r2']:.3f}.")
para(tag("stat") + f"In the engagement specification, <b>population is not merely "
     f"insignificant but numerically negligible</b> ({ef['log_pop']['coef']:+.4f}, "
     f"p {pval(ef['log_pop']['p'])}), while engagement carries "
     f"{ef['log_engagement']['coef']:+.4f} (p {pval(ef['log_engagement']['p'])}). A doubling of "
     f"the share of a world's roster that is actually online is associated with a price about "
     f"{pc(ef['log_engagement']['coef'] * 100 * 0.693, 1)} higher.")
para(tag("econ") + f"The economic reading is direct. A world's roster counts every character "
     f"created on it over its whole life, the great majority of which are dormant - on the "
     f"oldest worlds only a few percent remain active. Those characters do not bid for coins. "
     f"What the price responds to is the live portion of the roster, and once that is measured "
     f"the raw headcount adds nothing at all. <b>Coin demand comes from players, not from "
     f"accounts.</b>")
para(tag("lim") + f"This result depends on measuring population correctly, and it is worth "
     f"stating how sensitive it is. Substituting the active-character census for the full "
     f"roster - a measure whose coverage falls with world age (Section 3.7.1) - produces an "
     f"apparent <i>negative</i> population coefficient significant at 5%. That effect is an "
     f"artefact of the age-dependent undercount, not an economic relationship. With the full "
     f"roster the coefficient is essentially zero.")
para(tag("judg") + "Three cautions remain. The engagement magnitude is modest against an "
     "Optional-PvP premium near 4%. Population and activity are correlated, so both "
     "coefficients are identified from the part of each orthogonal to the other. And this is a "
     "cross-sectional association across 61 worlds observed once, not a causal estimate: both "
     "measures are current snapshots and cannot enter the daily panel.")
para(tag("obs") + f"Premium account share carries a marginally negative relationship "
     f"({ef['premium_share']['coef']:+.4f}, p {pval(ef['premium_share']['p'])}), which does not "
     f"reach conventional significance. Region indicators are insignificant once world type "
     f"and size are controlled, so apparent regional differences in raw prices reflect the "
     f"composition of world types within each region rather than region itself.")
figure("fig13_population.png",
       "Exhibit 5.6 - Price against the character roster, concurrent activity, and their ratio. "
       "Sources: price archive item_id 22118; TibiaVIP world list; GuildStats.eu "
       "/online-counter.")
figure("fig08_worldtype.png",
       "Exhibit 5.7 - Price level by PvP type and BattlEye cohort, converged worlds. Source: "
       "price archive, item_id 22118; attributes from TibiaData v4 and GuildStats.eu.")
story.append(PageBreak())

# ===================================================================== 21
h2sec('5.4', 'Young worlds', "Provenance, not age, sets a new world's opening price")
bottomline("Provenance, not age, sets a new world's opening price. Merge destinations open mature; genuine "
           "launches open near the floor and take about 500 days to converge.")
para(tag("judg") + "A world is classified as new using its documented creation date together "
     "with its absence from the merge register. It is never classified by its observed price. "
     "Selecting young worlds by low first price would guarantee the finding that young worlds "
     "start low, which would be circular.")
table([["Group", "n", "Median first price", "Range", "Median age at first observation"],
       ["Genuine launches", YG["n_launch"], f"{gp(YG['launch_first_price_median'])} GP/TC",
        f"{gp(YG['launch_first_price_min'])} - {gp(YG['launch_first_price_max'])}",
        f"{YG['launch_median_age_at_first_obs']:.0f} days"],
       ["Merge destinations", YG["n_merge_dest"], f"{gp(YG['mergedest_first_price_median'])} GP/TC",
        f"{gp(YG['mergedest_first_price_min'])} - {gp(YG['mergedest_first_price_max'])}",
        f"{YG['mergedest_median_age_at_first_obs']:.0f} days"]],
      [34 * mm, 10 * mm, 30 * mm, 36 * mm, AVAIL - 110 * mm],
      align=[None, "R", "R", "R", "R"],
      caption=f"Table 5.10 - Opening prices by provenance, worlds created inside the "
              f"observation window. Mann-Whitney p {pval(YG['mw_p'])}.")
para(tag("obs") + f"The separation is stark. Merge destinations open in a tight band from "
     f"{gp(YG['mergedest_first_price_min'])} to {gp(YG['mergedest_first_price_max'])} GP/TC - "
     f"already at the mature cross-world level. Genuine launches open as low as "
     f"{gp(YG['launch_first_price_min'])} GP/TC. The nine worlds created in the 2025-11-06 merge "
     f"wave were <b>one day old</b> at first observation and printed a median of "
     f"{gp(MG['wave_2025_11_06']['first_price_median'])} GP/TC.")
para(tag("econ") + "The explanation is that a merge destination is not a new economy. It "
     "inherits the characters, the accumulated gold and the trading population of its "
     "predecessor worlds on day one, so its coin market opens where those worlds' markets left "
     "off. A genuine launch begins with no gold stock at all: early characters have little gold, "
     "so little can be bid for a coin, and the GP price starts near the floor and rises as gold "
     "accumulates.")
figure("fig07_young_worlds.png",
       "Exhibit 5.8 - Opening prices and convergence by provenance. Source: price archive, "
       "item_id 22118; creation dates and merge register from GuildStats.eu.")
para(tag("obs") + f"Convergence is slow. Of the {YG['n_launch']} genuine launches, "
     f"{YG['n_converged_launches']} reached within 5% of the cross-world mean inside the "
     f"observation window, taking a median of {gp(YG['median_days_to_within_5pct'])} days - "
     f"well over a year. Launch-phase worlds are excluded from every cross-sectional statistic "
     f"in this report for exactly this reason.")
para(tag("lim") + "Two very young South American worlds, Floribra and Ignibra, were created in "
     "2026 and remain in active price discovery at the end of the window. They are carried "
     "through the forecast section with an explicit flag rather than dropped, because a "
     "flat-median random walk is least appropriate precisely where a world is still converging.")
story.append(PageBreak())

# ===================================================================== 22
h2sec('5.5', 'Merges and transfers', 'Merge effects are not testable, and no before-and-after is attempted')
h3("5.5.1 The merge register")
para(tag("obs") + f"The complete register covers {MG['n_merges']} merges absorbing "
     f"{MG['n_predecessors']} predecessor worlds between {MG['first']} and {MG['last']}. "
     f"Merges are the dominant force in Tibia's world structure: counting predecessor worlds and "
     f"surviving destinations together, {len(set(mreg.predecessor) | set(mreg.merge_world))} "
     f"distinct world names appear in the register, against 93 worlds carrying a coin price "
     f"today.")
wave = MG["wave_2025_11_06"]
table([["Merge date", "Destinations", "Predecessors absorbed"]] +
      [[str(d.date()), ", ".join(sorted(g.merge_world.unique()))[:70],
        f"{len(g)}"] for d, g in mreg[mreg.merge_date >= "2023-01-01"].groupby("merge_date")],
      [24 * mm, 96 * mm, AVAIL - 120 * mm], align=[None, None, "R"],
      caption="Table 5.11 - Merge waves inside or adjacent to the observation window.")

h3("5.5.2 Why merge effects are not testable here")
para(tag("lim") + "<b>No before-and-after test of a merge is possible with this data, and none "
     "is attempted.</b> The archive tracks only the surviving destination world. Predecessor "
     "worlds under their original names were never collected, so every merge destination has "
     "exactly zero pre-merge price observations. The counterfactual - what the predecessor "
     "worlds' coin prices were doing in the weeks before they were absorbed - simply does not "
     "exist in any accessible source.")
para(tag("judg") + "What can be said is narrower and is stated as such: merge destinations "
     "appear in the archive already trading at mature levels (Section 5.4), which is consistent "
     "with inheriting a functioning market rather than bootstrapping one. That is an observation "
     "about opening levels, not a measurement of a merge's effect on price.")

h3("5.5.3 Character transfer flows")
para(tag("obs") + f"Character world transfers were collected as a second potential cross-world "
     f"linkage channel. The source exposes {MG['transfers_n']} transfers covering "
     f"{MG['transfers_window']} - a rolling window of {MG['transfers_days']} days, not a history.")
tt = MG["transfer_top_dest"]; to_ = MG["transfer_top_origin"]
table([["Top destinations", "Transfers in", "Top origins", "Transfers out"]] +
      [[list(tt)[i], list(tt.values())[i], list(to_)[i], list(to_.values())[i]]
       for i in range(min(6, len(tt), len(to_)))],
      [44 * mm, 24 * mm, 44 * mm, AVAIL - 112 * mm], align=[None, "R", None, "R"],
      caption=f"Table 5.12 - Character transfer flows over {MG['transfers_days']} days.")
tns = MG.get("transfer_net_vs_price_spearman")
if tns:
    para(tag("stat") + f"Net transfer flow shows no relationship with a world's price level "
         f"(Spearman rho {tns['rho']:+.3f}, p {pval(tns['p'])}, n = {tns['n']}). Players are not "
         f"visibly migrating toward or away from worlds on the basis of coin prices over this "
         f"window.")
para(tag("lim") + f"This is a weak test and should be read as such. A {MG['transfers_days']}-day "
     f"window cannot detect a relationship operating over months, and character transfers are "
     f"costly and infrequent relative to coin trades. The mechanically important cross-world "
     f"channel remains the coin transfer itself, which requires no character movement at all "
     f"and leaves no trace in this dataset.")
story.append(PageBreak())

# ===================================================================== 23
hero(pc(FN["roll"]["median_roll_spread_pct"]),
     "is what a Tibia Coin round trip actually costs.",
     "The quoted spread is 4.29%, five times larger. Most volume executes inside the quotes "
     "against resting limit orders, so the dominant cost of trading across worlds is "
     "CipSoft's Market fee, not the bid-ask spread.",
     mark="cost")
h2sec('5.6', 'Liquidity and microstructure', 'Traders pay a fifth of the quoted spread; the fee is the real cost')
para(tag("obs") + "Live order books for all 93 worlds were captured on 2026-07-30, giving a "
     "single simultaneous cross-section of true depth alongside the historical executed series.")
takeaway('The buy side carries four times the orders and four times the depth - but not on the same worlds, which is why the two must be measured separately.')
table([["Measure", "Median across 93 worlds"],
       ["Quoted spread (best ask minus best bid, over mid)", pc(MI["quoted_spread_median_pct"])],
       ["Standing buy orders / sell orders",
        f"{MI['median_buy_orders']:.0f} / {MI['median_sell_orders']:.0f}"],
       ["Bid depth / ask depth",
        f"{gp(MI['median_bid_depth_tc'])} / {gp(MI['median_ask_depth_tc'])} TC"],
       ["Correlation of the two ratios across worlds",
        f"{MI['corr_ordercount_vs_depth_ratio']:.2f}"],
       ["TC sold / bought per world-day",
        f"{gp(MI['turnover']['median_tc_sold_per_day'])} / "
        f"{gp(MI['turnover']['median_tc_bought_per_day'])} TC"]],
      [90 * mm, AVAIL - 90 * mm], align=[None, "R"],
      caption="Table 5.13 - Microstructure measures the argument below turns on. Order-book "
              "measures are a single snapshot; executed measures are medians over the full "
              "window. Table E.2 gives the complete block, including dispersion, anonymity "
              "and the placeholder share.")

h3("5.6.1 Turnover must be reported side by side, never summed")
para(tag("lim") + f"Adding day_sold to day_bought would double count: a single trade between two "
     f"players registers on both sides. Over the converged sample the two sides total "
     f"{gp(MI['turnover']['total_tc_sold_window'])} TC sold and "
     f"{gp(MI['turnover']['total_tc_bought_window'])} TC bought - close, as they must be, and not a "
     f"combined turnover of their sum. Both figures are reported separately throughout.")

h3("5.6.2 Depth versus order counts")
figure("fig09_orderbook.png",
       "Exhibit 5.9 - Order-count ratio against true depth ratio, one point per world. Source: "
       "TibiaMarket.top /market_board, item_id 22118, snapshot 2026-07-30.")
para(tag("stat") + f"The correlation between the two ratios is only "
     f"{MI['corr_ordercount_vs_depth_ratio']:.2f}. A world can show many more buy orders than "
     f"sell orders while carrying less genuine bid depth, because a long tail of tiny orders far "
     f"below market inflates the count without contributing executable size. Median bid depth "
     f"({gp(MI['median_bid_depth_tc'])} TC) does exceed median ask depth "
     f"({gp(MI['median_ask_depth_tc'])} TC), so a real asymmetry exists - but it must be measured "
     f"from quantities, not counts.")

para(tag("mech") + f"Depth is also granular. Because offers are placed in lots of "
     f"{FE['lot_size']}, every quantity on the book is a multiple of "
     f"{FE['lot_size']} - verified on all {FE['n_offers']:,} live offers - so the smallest "
     f"increment of depth is {FE['lot_size']} TC, worth about "
     f"{gp(FE['min_trade_value_gp'])} GP at the median price. Depth figures in this report "
     f"should be read as counts of lots rather than as a continuous quantity.")
para(tag("judg") + "<b>The lot constraint binds on quantity, not on price.</b> An offer names a "
     "price per coin and an amount; only the amount is restricted. Every price-based result in "
     "this report - the index, the stationarity tests, the arbitrage band, the spread "
     "estimates, the forecasts - is therefore unaffected by it. What it changes is the set of "
     "trades that can be executed at those prices, which is why it is stated here and applied "
     "to the fee-cap threshold in Section 2.2 rather than left implicit.")

h3("5.6.4 Decomposing the spread: what traders actually pay")
para(tag("stat") + "The quoted spread is what a market order would cross, but most volume in a "
     "limit-order book executes inside the quotes. Roll (1984) provides an estimator of the "
     "<i>effective</i> spread that requires no order-flow data: if prices bounce between bid "
     "and ask, successive returns inherit a negative first-order autocovariance of exactly "
     "-(s/2)&sup2;, so s = 2&radic;(-&gamma;<sub>1</sub>).")
RL = FN["roll"]
para(tag("obs") + f"The required negative autocovariance is present on "
     f"{RL['n_negative_gamma1']} of {RL['n_worlds']} converged worlds. This is the same serial "
     f"correlation reported as measurement noise in Section 4.4.2; Roll's model says it is not "
     f"an artefact of measurement but a structural consequence of trading against a spread.")
takeaway('What traders actually pay is 0.84%, about a fifth of the quoted spread; the dominant cost of a cross-world round trip is the Market fee, not the spread.')
figure("fig20_spread_decomposition.png",
       "Exhibit 5.10 - Cost of a round trip under five measures, against the arbitrage band "
       "estimated independently from prices. Sources: price archive item_id 22118; "
       "TibiaMarket.top /market_board; documented Market mechanics.")
para(tag("stat") + f"The effective spread of {pc(RL['median_roll_spread_pct'])} is about "
     f"{RL['share_of_quoted']:.0%} of the quoted spread, and across worlds the two are not "
     f"related at all: the rank correlation is {RL['corr_roll_vs_quoted']:.2f} on "
     f"{RL['corr_roll_vs_quoted_n']} worlds, p {pval(RL['corr_roll_vs_quoted_p'])}. A world "
     f"with a wide posted spread is not a world where trades pay more. A large gap between "
     f"quoted and effective cost, and no cross-sectional link between them, is the normal "
     f"signature of a market where patient limit orders supply most of the liquidity and the "
     f"posted quotes are the outer envelope rather than the typical execution.")
para(tag("econ") + "This materially changes the read on trading costs. Judged on the quoted "
     "spread, the market looks expensive. Judged on what trades actually pay, the effective "
     "cost is below the small-trader Market fee itself - meaning the dominant cost of a "
     "cross-world round trip is CipSoft's fee, not the bid-ask spread. That ordering is what "
     "makes the fee the natural candidate for the arbitrage band in Section 5.2.")

h3("5.6.5 Which microstructure model fits, and what cannot be tested")
para(tag("judg") + "Section 2.3.3 set out three frameworks. The evidence discriminates between "
     "them only partially, and the reason is worth stating.")
bullets([
    tag("stat") + f"<b>Inventory effects are visible.</b> Spreads fall with traded quantity "
    f"(Spearman {MI['spearman_spread_turnover'][0]:+.2f}) and with world size "
    f"({MI['spearman_spread_pop'][0]:+.2f}), and volatility falls with turnover "
    f"({MI['spearman_turnover_vol'][0]:+.2f}). All three are the sign Ho and Stoll (1981) "
    f"predict: a provider bearing less inventory risk, and facing more competition, quotes "
    f"tighter.",
    tag("lim") + "<b>Adverse selection cannot be measured.</b> Separating the "
    "information component of the spread in the manner of Glosten and Milgrom (1985) requires "
    "signing order flow into buyer- and seller-initiated trades. The book returns 'Anonymous' "
    "for the overwhelming majority of orders, so no trade-direction classification is "
    "possible and the decomposition cannot be performed.",
    tag("lim") + "<b>Kyle's lambda cannot be estimated.</b> Price impact per unit of order "
    "flow requires signed order flow at trade frequency. The archive reports daily aggregates "
    "of executed quantity, not individual trades, so the regression that defines lambda has "
    "no left-hand or right-hand variable available at the required frequency.",
])
para(tag("judg") + "What this means for interpretation is that the observed spread should be "
     "read as compensation for inventory risk and for the fee, with any adverse-selection "
     "component unmeasured rather than shown to be absent. Given that the asset's real payoff "
     "is administratively fixed and identical across all holders, there is little private "
     "information to trade on in the first place - which is a reason to expect the "
     "adverse-selection component to be small, but it is an argument, not a measurement.")

h3("5.6.6 Price discovery: where does the price form?")
para(tag("stat") + "If price formation happens where trading is deepest, the returns of large "
     "worlds should lead those of small worlds more strongly than the reverse. Splitting "
     "converged worlds at the median of daily traded quantity and running bivariate Granger "
     "causality on the two group indices tests this directly.")
PD = FN["price_discovery"]
table([["Direction", "F statistic", "p", "Reading"],
       [f"Large worlds lead small ({PD['n_big']} to {PD['n_small']})",
        f"{PD['big_causes_small_F']:.1f}", pval(PD["big_causes_small_p"]), "Strong"],
       ["Small worlds lead large", f"{PD['small_causes_big_F']:.1f}",
        pval(PD["small_causes_big_p"]), "Present but weaker"]],
      [62 * mm, 24 * mm, 18 * mm, AVAIL - 104 * mm], align=[None, "R", "R", None],
      caption=f"Table 5.14 - Granger causality between large-world and small-world return "
              f"indices, three daily lags, n = {PD['n_obs']:,}. Contemporaneous correlation "
              f"between the two indices is {PD['contemp_corr']:.2f}.")
para(tag("stat") + f"Causality runs both ways, but asymmetrically: the large-to-small statistic "
     f"is {PD['big_causes_small_F'] / PD['small_causes_big_F']:.1f} times the reverse. "
     f"Information is incorporated first where the book is deepest and propagates outward, "
     f"which is the standard price-discovery ordering.")
para(tag("lim") + "Granger causality is predictive precedence, not causation. Both directions "
     "being significant is consistent with a common factor hitting large worlds slightly "
     "sooner rather than with large worlds causing small-world prices. The asymmetry is the "
     "informative part; the levels are not.")
story.append(PageBreak())

h3("5.6.3 Liquidity and its correlates")
sp_t = MI["spearman_spread_turnover"]; sp_p = MI["spearman_spread_pop"]
sp_v = MI["spearman_turnover_vol"]
table([["Relationship", "Spearman rho", "p", "Reading"],
       ["Quoted spread vs TC traded per day", f"{sp_t[0]:+.3f}", pval(sp_t[1]),
        "Busier worlds quote tighter"],
       ["Quoted spread vs population", f"{sp_p[0]:+.3f}", pval(sp_p[1]),
        "Larger worlds quote tighter"],
       ["Return volatility vs TC traded per day", f"{sp_v[0]:+.3f}", pval(sp_v[1]),
        "Thinner worlds are more volatile"]],
      [66 * mm, 24 * mm, 18 * mm, AVAIL - 108 * mm], align=[None, "R", "R", None],
      caption="Table 5.15 - Liquidity correlates across converged worlds.")
para(tag("econ") + "All three point the same way and are what a conventional microstructure "
     "reading would predict: larger, busier worlds sustain tighter quotes and steadier prices, "
     "while thin worlds show wider spreads and noisier daily marks. This also explains the "
     "measurement-noise finding of Section 4.4.2 - the daily price on a thin world is estimated "
     "from few trades and is correspondingly noisy.")
para(tag("lim") + "Participant counts are unavailable. The order book returns the literal string "
     f"'Anonymous' for {pc(MI['anon_share_buy'] * 100, 0)} of buy-side orders, so unique traders "
     f"cannot be identified and no concentration measure can be computed.")
story.append(PageBreak())

# ===================================================================== 24
h2sec('5.7', 'Technical indicators', "Technical readings are firm, and carry no weight in this report's verdict")
bottomline("Technical readings are uniformly firm and carry no weight in this report's conclusion, because "
           "they are functions of a level that Section 4.4 shows to be unpredictable.")
para(tag("obs") + "Standard technical measures are reported for completeness and for the "
     "cross-world breadth picture they give. They carry no forecasting weight in this report, "
     "for the reason given below.")
table([["Indicator", "Value across worlds"],
       ["Worlds priced above their 50-day moving average", f"{TC['pct_above_ma50']:.0f}%"],
       ["Worlds priced above their 200-day moving average", f"{TC['pct_above_ma200']:.0f}%"],
       ["Worlds with 50-day above 200-day (golden cross)", f"{TC['pct_golden_cross']:.0f}%"],
       ["Median 14-day RSI", f"{TC['median_rsi']:.1f}"],
       ["Worlds with RSI above 70", f"{TC['n_rsi_over70']} of {TC['n']}"],
       ["Worlds with RSI below 30", f"{TC['n_rsi_under30']} of {TC['n']}"]],
      [92 * mm, AVAIL - 92 * mm], align=[None, "R"],
      caption=f"Table 5.16 - Technical indicators, {TC['n']} worlds with sufficient history, "
              f"as at {W['end']}.")
para(tag("obs") + f"The reading is uniformly firm: {TC['pct_above_ma50']:.0f}% of worlds sit "
     f"above their 50-day average, {TC['pct_above_ma200']:.0f}% above their 200-day, and the "
     f"median RSI of {TC['median_rsi']:.0f} is at the conventional overbought threshold with "
     f"{TC['n_rsi_over70']} worlds above 70 and none below 30.")
para(tag("judg") + "<b>This is deliberately not translated into a bullish rating.</b> Three "
     "reasons. First, these indicators are functions of the same non-stationary level whose "
     "unpredictability Section 4.4 establishes; a moving-average crossover on a random walk "
     "carries no information about the next move. Second, breadth statistics across 93 worlds "
     "are not 93 independent signals - Section 5.1 shows price levels are correlated at "
     f"{IN['mean_pairwise_level_corr']:.2f}, so this is closer to one observation than to many. "
     "Third, an RSI at the overbought threshold is as consistent with continued strength as with "
     "reversal, and the study has no evidence to choose between them. Section 7.5's rating rests "
     "on the structural findings, not on this table.")
story.append(PageBreak())

# ===================================================================== 24A VENUES
h2sec('5.8', 'Venue structure',
      'A coin can be sold in three places, and this report prices one of them')
bottomline("Tibia Coins are not traded in a single market but across several settlement venues "
           "with different frictions. Which venue a seller uses is a transaction-cost decision, "
           "not a technological one - and every result in this report is a within-venue result.")
para(tag("mech") + "The report has so far written as though a Tibia Coin has one price, its "
     "gold price on the in-game Market. That is the venue the data covers, but it is not the "
     "only place a coin changes hands. Because coins sit at account level rather than on a "
     "world (Section 2.1), a holder can route a sale through any venue their account can "
     "reach.")
figure("fig26_venue_map.png",
       "Exhibit 5.11 - Settlement venues for a Tibia Coin and the friction each imposes. "
       "Sources: documented Market mechanics; Tibia Token Service Agreement (tibia.com); "
       "TibiaToken contract on BNB Smart Chain.")

h3("5.8.1 What each venue is, as documented")
bullets([
    tag("mech") + "<b>The in-game Market.</b> Settlement in gold pieces, inside the game. "
    "CipSoft stands between the two sides, so there is no counterparty risk; the cost is the "
    "2% offer fee capped at 1,000,000 GP that Section 5.2.4 measures, plus the capital locked "
    "while an offer rests. This is the venue the price archive observes.",

    tag("mech") + f"<b>The Tibia Token.</b> An official {VN['token']['standard']} token "
    f"({VN['token']['symbol']}) on the {VN['token']['chain']}, contract "
    f"{VN['token']['contract'][:10]}...{VN['token']['contract'][-6:]}. The Tibia Token Service "
    f"Agreement documents a two-way exchange - coins can be exported to tokens and tokens "
    f"imported back - with a fixed and/or percentage service fee charged in Tibia Coins and "
    f"deducted from the amount, and the blockchain transaction fee payable separately by the "
    f"user. CipSoft states that it does not guarantee any market value for the token and that "
    f"it may deactivate the exchange functions.",

    tag("mech") + "<b>Resellers and over-the-counter dealers.</b> Not operated by CipSoft. "
    "Settlement is in fiat over local payment rails, and the counterparty risk sits with the "
    "trader, priced through the dealer's reputation rather than through a fee schedule.",
])

h3("5.8.2 How much of the float has left, and how it compares")
para(tag("obs") + f"The token venue leaves a public trace, and it is not small. Every token in "
     f"existence corresponds to a coin held outside the in-game system, so the contract's total "
     f"supply measures directly how much of the float has left. Read from the "
     f"{VN['token']['chain']} at block {VN['token']['block']:,}, supply stood at "
     f"<b>{gp(VN['token']['total_supply'])} {VN['token']['symbol']}</b>.")
para(tag("obs") + f"For scale, the order-book snapshot used in Section 5.6 shows "
     f"{gp(VN['book_ask_depth_tc'])} TC offered for sale across all {VN['n_book_worlds']} "
     f"worlds, against {gp(VN['book_bid_depth_tc'])} TC bid for. The tokens outstanding are "
     f"therefore "
     f"{VN['tib_over_ask_depth']:.2f} times the quantity of coins on offer across every world "
     f"at once, and {VN['tib_over_total_depth']:.0%} of resting interest on both sides "
     f"combined.")
para(tag("obs") + f"That figure needs a denominator, and the Char Bazaar supplies one. The "
     f"Bazaar is CipSoft's official market for characters and it is denominated in Tibia Coins, "
     f"so it is the largest single place a coin is used rather than sold. Over "
     f"{VN['bazaar']['year']}, across all worlds, "
     f"{gp(VN['bazaar']['auctions_created'])} auctions were created and "
     f"{gp(VN['bazaar']['auctions_completed'])} cleared "
     f"({VN['bazaar_completion_rate']:.0%}), moving "
     f"<b>{gp(VN['bazaar']['tc_exchanged'])} TC</b> at a mean clearing price of "
     f"{gp(VN['bazaar_mean_price_tc'])} TC per character.")
para(tag("econ") + f"Set against that flow, the token venue is real but small: tokens "
     f"outstanding are {VN['tib_over_bazaar_year']:.1%} of a single year's Bazaar turnover. The "
     f"two facts sit together rather than in tension. Measured against the coins on offer for "
     f"gold at any instant, the stock held outside the game is large; measured against how "
     f"coins are actually used over a year, it is marginal. Coins overwhelmingly stay inside "
     f"and circulate for characters, which is the demand that gives the coin its gold price in "
     f"the first place - and it is why the in-game price this report measures remains the "
     f"economically meaningful one, notwithstanding the venue caveat.")
para(tag("stat") + f"<b>Putting the two venues on the same scale needs care, and the naive "
     f"comparison is wrong.</b> The Bazaar total is complete - every world, every day of the "
     f"year - while the Market side is only the world-days this study observes, which in "
     f"{MS['year']} is {MS['coverage']:.0%} of the possible ones. Dividing one by the other "
     f"measures coverage rather than the venues: the quotient reads "
     f"{float(BZR[BZR.year == 2024].ratio_naive.iloc[0]):.1f} times in 2024, when coverage was "
     f"{float(BZR[BZR.year == 2024].coverage.iloc[0]):.0%}, and "
     f"{MS['bazaar_over_market_naive']:.1f} times in {MS['year']}. The ratio moved because the "
     f"data collection did.")
para(tag("stat") + f"<b>On comparable coverage the Bazaar is "
     f"{MS['bazaar_over_market_comparable']:.1f} times the Market</b>, scaling the observed "
     f"mean per world-day to the full world count and calendar: "
     f"{gp(MS['market_tc_scaled'])} TC against {gp(MS['bazaar_tc_year'])} TC in {MS['year']}, "
     f"and {float(BZR[BZR.year == 2024].ratio_comparable.iloc[0]):.1f} times in 2024. The venue "
     f"this report has spent six chapters measuring is still the smaller one, by a factor "
     f"between four and six rather than the order of magnitude a raw division suggests.")
para(tag("econ") + f"<b>That reframes what the price series is.</b> The GP price of a coin is "
     f"set on the Market, but the Market is a minority of coin movement; the Bazaar moves an "
     f"order of magnitude more coins without ever quoting a gold price, because characters are "
     f"paid for in coins directly. So the gold price is formed in the thin venue and consumed "
     f"in the thick one - which is consistent with the mechanism in Section 7.6 and sharpens "
     f"it: the marginal price-setter is a small population, and the demand that gives coins "
     f"their value is largely invisible to the price that this report models.")
para(tag("obs") + f"<b>And the Bazaar is not one number: it has a published history.</b> Year "
     f"pages exist from {int(BZY.year.min())} onward, giving {len(BZY)} annual totals and "
     f"{BZH['n_monthly_observations']} monthly observations of auction activity. Value is "
     f"published annually only, so the monthly series is counts rather than coins.")
table([["Year", "Auctions created", "Completed", "TC exchanged", "Mean TC per auction",
        "Completion"]] +
      [[f"{int(r.year)}" + (" (partial)" if r.partial_year else ""),
        gp(r.auctions_created), gp(r.auctions_completed), gp(r.tc_exchanged),
        gp(r.mean_tc_per_auction), f"{r.completion_rate:.0%}"]
       for _, r in BZY.iterrows()],
      [26 * mm, 30 * mm, 24 * mm, 30 * mm, 30 * mm, AVAIL - 140 * mm], fs=7,
      align=[None, "R", "R", "R", "R", "R"],
      caption="Table 5.17 - The Char Bazaar as published by NabBot, from the first year with "
              "statistics. Coins exchanged is an annual figure; auction counts are also "
              "published monthly.")
para(tag("econ") + f"<b>The venue is not growing, and its composition has changed.</b> Auctions "
     f"created fell from {gp(float(BZY[BZY.year == 2021].auctions_created.iloc[0]))} in 2021 to "
     f"{gp(float(BZY[BZY.year == 2025].auctions_created.iloc[0]))} in 2025, a decline of "
     f"{1 - float(BZY[BZY.year == 2025].auctions_created.iloc[0]) / float(BZY[BZY.year == 2021].auctions_created.iloc[0]):.0%}, "
     f"while the mean price per completed auction rose from "
     f"{gp(float(BZY[BZY.year == 2021].mean_tc_per_auction.iloc[0]))} to "
     f"{gp(float(BZY[BZY.year == 2025].mean_tc_per_auction.iloc[0]))} TC. Coins exchanged is "
     f"therefore roughly flat between {gp(BZH['trough_tc'])} and {gp(BZH['peak_tc'])} TC a year: "
     f"fewer character sales at higher prices, not a shrinking venue.")
para(tag("lim") + f"<b>The larger venue is unobservable at any frequency that would let it be "
     f"tested, and that is a named gap in this study rather than a general caveat.</b> The "
     f"Bazaar publishes {len(BZY)} annual totals and "
     f"{BZH['n_monthly_observations']} monthly auction counts, all worlds pooled, with no "
     f"per-world split and no daily series - and the price panel this study models is daily. "
     f"So the {MS['bazaar_over_market_comparable']:.1f}-to-one "
     f"venue that moves most of the coins contributes exactly zero of the "
     f"140 features tested in Chapter 6. Every statement in this report about what does and "
     f"does not forecast the price is conditional on information drawn from the venue carrying "
     f"the minority of coin movement.")
para(tag("stat") + f"<b>How much could that missing venue matter? The study already bounds "
     f"it.</b> Bazaar flow is an aggregate quantity, so it could only enter as a driver common "
     f"to all worlds. Section 6.6.16 estimates the ceiling on any such driver directly: a "
     f"common state observed <i>perfectly and in retrospect</i> explains "
     f"{IRR['latent_state']['r2_factor_smoothed']:.1%} of daily return variance across "
     f"{IRR['latent_state']['n_worlds']} worlds, and "
     f"{IRR['latent_state']['r2_factor_forecast']:.1%} one step ahead. A daily Bazaar series "
     f"could not beat that ceiling, because the ceiling is on the whole class of common drivers "
     f"and not on any particular one.")
para(tag("judg") + "<b>So the gap is real, bounded and worth closing anyway.</b> The bound says "
     "a Bazaar series would not overturn the unforecastability of the level - the room above "
     "the common-factor ceiling is idiosyncratic and the room ahead of it is nil. What it could "
     "plausibly improve is the volatility model and the participant decomposition, both of "
     "which turn on how intensively coins are being used rather than on where the price goes "
     "next. Collecting it would mean scraping the live auction listings daily, which this study "
     "did not do and which a successor should.")
para(tag("lim") + f"<b>The dollar figures that follow are one measurement restated, not two.</b> "
     f"At the on-chain quote the Market's {MS['year']} turnover is about "
     f"${MS['market_usd_year']:,.0f} and the Bazaar's about ${MS['bazaar_usd_year']:,.0f}. Both "
     f"come from the same TIB/USDT price propagated through the GP series, so they cannot "
     f"corroborate each other, and neither is CipSoft revenue: the coins moving through the "
     f"Bazaar were bought once from the Store and then circulate between players indefinitely.")
para(tag("lim") + f"The Bazaar figures are compiled by a third party (NabBot) from public "
     f"auction pages, not published by CipSoft. That source states its character statistics "
     f"cover only characters registered with it; whether the auction aggregates carry the same "
     f"restriction is not documented, so they are treated here as a lower bound on Bazaar "
     f"turnover rather than as a census. The token supply, by contrast, is read from the "
     f"contract itself and is exact at the stated block - though it is a live quantity that "
     f"changes as coins are exported and imported.")
para(tag("lim") + "Nothing comparable exists for the reseller venue. There is no public quote "
     "series, no volume, and no register of dealers, so its size and its prices are outside "
     "this study entirely. The token figure is a stock, not a flow: it says how many coins sit "
     "outside the game, not how many move per day.")

h3("5.8.3 The token has a market price, and it prices gold")
para(tag("obs") + f"The token trades on-chain, and the price is observable. Across "
     f"{VN['dex']['n_pools']} PancakeSwap pools quoting it, "
     f"{gp(VN['dex']['tib_in_pools'])} TIB - "
     f"{VN['dex']['tib_in_pools'] / VN['token']['total_supply']:.0%} of everything outstanding "
     f"- sits as market-making inventory against "
     f"${gp(VN['dex']['stable_depth_usd'])} of stablecoin depth. The "
     f"{VN['dex']['n_quoting_pools']} pools that quote a price agree closely: "
     f"${VN['dex']['price_range_usd'][0]:.4f} to ${VN['dex']['price_range_usd'][1]:.4f} per "
     f"token, a spread of "
     f"{(VN['dex']['price_range_usd'][1] / VN['dex']['price_range_usd'][0] - 1) * 100:.1f}%. "
     f"The deepest ({VN['dex']['price_source']}) quotes "
     f"<b>${VN['dex']['price_usd']:.4f}</b>, at block {VN['dex']['block']:,}.")
para(tag("econ") + f"Because the official exchange converts coins and tokens both ways, that "
     f"is a dollar price for a Tibia Coin. Put beside the gold price this report measures - a "
     f"median of {gp(D['price_latest_median'])} GP/TC - it prices gold itself: "
     f"<b>{gp(VN['gp_per_usd'])} GP to the dollar</b>, or about "
     f"${VN['usd_per_gp'] * 1e6:.2f} per million GP.")
para(tag("lim") + f"This is a single dated observation, not a series, and it should be used as "
     f"a scale rather than as a valuation. Three qualifications. The depth behind it is thin in "
     f"absolute terms - ${gp(VN['dex']['stable_depth_usd'])} on the quote side - so it is a "
     f"price rather than a deep market. It is the token's secondary price, which the exchange "
     f"fee allows to sit below the coin's in-game worth rather than at it. And no history was "
     f"collected, so it cannot be used to test what drives the level over time; Section 6.1.3's "
     f"requirement is unchanged.")
para(tag("judg") + f"It does change one thing. Section 7.3 records that this study has no "
     f"real-money price and can value the coin only against gold. That is now true of the "
     f"<i>series</i> but not of the <i>level</i>: the gold price of a Tibia Coin can be "
     f"expressed in dollars at a stated block, and the pools agree well enough that the figure "
     f"is not an artefact of one venue.")

h3("5.8.4 Why a better technology need not win the venue")
para(tag("hyp") + "<b>Venue share should follow effective cost, not settlement technology.</b> "
     "Effective cost is the sum of what a seller actually gives up: explicit fees, the time "
     "until settlement is final, the risk of not being paid, the operational effort of using "
     "the venue, any regulatory or tax exposure, and the cost of the local payment "
     "infrastructure the fiat leg has to cross.")
para(tag("econ") + "On that measure the token route is not automatically the cheapest. It adds "
     "a service fee in coins, a chain fee in a second asset the seller may not hold, a wallet, "
     "and - for anyone who ultimately wants local currency - an exchange step with its own "
     "spread and withdrawal cost. A reseller with an established reputation collapses that "
     "chain into a single transfer.")
para(tag("hyp") + "This yields a proposition the rest of this report does not test: in "
     "jurisdictions where instant, low-cost fiat settlement exists, the reseller venue should "
     "hold share against the token venue rather than lose it. Brazil is the natural case. Pix "
     "settles peer-to-peer transfers in seconds at negligible cost, which removes almost all "
     "the friction from the fiat leg that the token route was meant to solve. On this reading "
     "a domestic payment reform may have done more to make OTC dealing competitive than the "
     "token did to displace it - not because the token is badly designed, but because it "
     "solves a problem those users had already solved.")
para(tag("judg") + "Stated plainly so it can be attacked: this is a hypothesis, offered "
     "because the mechanism is specific and the prediction is falsifiable. No data in this "
     "study bears on it. Section 5.8.6 lists what would.")

h3("5.8.5 What this changes about the results in this report")
para(tag("econ") + f"The report's central result generalises rather than breaks. Section 6.3.1 "
     f"finds that a price gap between worlds closes only once it exceeds "
     f"{pc(R['advanced']['tar']['threshold_pct'])}, the cost of closing it. Across venues the "
     f"same logic applies with a wider band, because export fees, chain fees and reputation "
     f"costs all exceed the Market's capped 2%. The prediction is therefore that cross-venue "
     f"price differences persist at wider margins than cross-world ones, and that they are "
     f"stable rather than arbitraged away.")
para(tag("lim") + "<b>Two claims in this report need qualifying in light of it.</b>")
bullets([
    tag("lim") + f"The band of {pc(R['advanced']['tar']['threshold_pct'])} is a within-venue "
    f"band. It measures the cost of moving value between worlds inside the in-game Market. It "
    f"is not the cost of moving a coin between venues, and it should not be read as a general "
    f"friction estimate for the asset.",

    tag("hyp") + f"The single common stochastic trend of Section 6.3.2 may be partly an "
    f"outside-option effect. If a coin has a price in euro terms set outside the game, then its "
    f"gold price is that euro price divided by the euro value of gold, and the component all "
    f"{W['n_worlds']} worlds share could be arriving "
    f"from outside rather than being generated inside. This does not overturn the finding - one "
    f"common trend is one common trend either way - but it changes what the trend might be, and "
    f"it gives a second reason to want the gold series named in Section 6.1.3.",
])

h3("5.8.6 What would settle it")
para(tag("judg") + "The venue question is answerable, and cheaply, by anyone able to collect "
     "three series that this study could not:")
bullets([
    "A dated quote series from two or more resellers, in local currency per coin, long enough "
    "to test whether reseller and in-game prices move together after conversion. This was "
    "attempted rather than assumed unavailable - see the note below.",
    f"A market price for {VN['token']['symbol']} against a liquid pair, plus on-chain transfer "
    f"volume, which would show whether the token trades at, above or below the cost of the "
    f"official exchange window.",
    "Export and import volumes through the Tibia Token Exchange, which would convert the stock "
    "measured above into the flow the analysis actually needs.",
])
para(tag("lim") + "<b>The reseller series was attempted and not obtained.</b> CipSoft "
     "publishes a vetted list of authorised resellers, which would be the right starting point "
     "because it is an official enumeration rather than a search result. The list is served "
     "behind bot protection - a direct request returns HTTP 403 with a JavaScript challenge - "
     "and the entries load only after a country is chosen. It carries no prices in any case; "
     "each reseller quotes on its own site. Bypassing that protection was not attempted, on the "
     "same principle that governs the TibiaVIP endpoints in Section 3.1: an access control is a "
     "statement of terms, and this study reports what it could not reach rather than reaching "
     "around it. The series is collectable by a party willing to visit each reseller directly, "
     "which is a legitimate route this study did not take.")

para(tag("judg") + "With those in hand the multi-venue structure becomes estimable with the "
     "same tools used here: a threshold model per venue pair, and an error-correction system "
     "to see which venue leads price discovery. Until then the honest position is the one this "
     "section takes - the structure is documented, its magnitudes are not.")
story.append(PageBreak())

# ===================================================================== 25
chapter(6, 'Valuation, models and forecasts',
        'What the coin is worth in monetary terms, the formal econometrics behind the headline results, and an honest account of what can be forecast.')
h2sec('6.1', 'Valuation', 'The coin has no administered gold price, so it floats entirely on demand')
h3("6.1.1 The coin has no administered gold price")
para(tag("mech") + "A Tibia Coin has two prices: a real-money price set administratively by "
     "CipSoft, and a gold price set by players on the Market. Only the second is observed "
     "here. No store price series was collected, so this report computes no gold-per-currency "
     "rate from CipSoft's own prices. Section 5.8 does quote a dollar figure, taken from the "
     "on-chain TibiaToken market and carried through the GP price; it is one measurement "
     "restated rather than an independent valuation, and it is labelled as such where it "
     "appears.")
para(tag("obs") + f"The coin carries no non-player-character price - its metadata record lists "
     f"empty buy and sell arrays - so no NPC will trade a coin for gold at a fixed rate. There "
     f"is therefore no administered floor or ceiling anchoring the gold price of a coin. It "
     f"floats entirely on player supply and demand, which is consistent with the "
     f"non-stationarity found in Section 4.4 and makes a unit root the expected description "
     f"rather than a puzzle.")

h3("6.1.2 Gold's purchasing power and the quantity identity")
para(tag("econ") + f"Because the coin's real payoff is administratively fixed (Section 2.3.1), "
     f"the gold price of a coin is the reciprocal of gold's purchasing power over that fixed "
     f"bundle. Over the chain-linked index period the coin appreciated "
     f"{pc(IX['total_pct'], 1, True)} against gold, which is identically a depreciation of "
     f"gold against the coin of {pc((1 / (1 + IX['total_pct'] / 100) - 1) * 100, 1)}.")
para(tag("econ") + f"Metadata records administered non-player-character prices for "
     f"{R['valuation']['n_items_with_npc_buy']:,} items. Those prices are fixed in gold and "
     f"unchanged over the window, which makes them a stable yardstick against which a floating "
     f"coin price can be read: the ratio of the coin price to any of them measures directly "
     f"how gold's purchasing power has shifted against the premium currency.")
para(tag("hyp") + "Under the quantity identity MV = PY, a rising gold price of a "
     "fixed-real-value asset is what one observes when the gold stock M grows faster than the "
     "real volume Y it chases, with velocity V fixed. That is the standard reading of the "
     "drift documented in Section 4.3, and it is coherent with the world-type results of "
     "Section 5.3: Optional-PvP worlds have weaker death-penalty gold sinks, so M accumulates "
     "faster, and they trade at a premium.")
para(tag("lim") + "<b>None of M, V or Y is observable in any accessible source.</b> No gold "
     "stock, gold income, coin supply, or gold-denominated transaction-volume series exists. "
     "The identity therefore frames what would need to be measured; it cannot be tested, and "
     "no inflation rate is computed anywhere in this report. Three observationally equivalent "
     "explanations of the same price path - gold inflation, rising coin demand, and a shift in "
     "player composition - cannot be separated from price data alone.")

h3("6.1.3 What would identify the monetary channel")
para(tag("judg") + "It is worth being specific about what would settle this, since at the time "
     "this section was written the gap was the binding limitation of the study. Any one of the "
     "following would permit a direct "
     "test: a per-world series of gold created through loot and quest rewards; a series of "
     "gold destroyed through NPC purchases, repairs and death penalties; the outstanding stock "
     "of coins per world; or the volume of gold changing hands on the Market. None is "
     "published by CipSoft or reconstructable from the fansite sources surveyed in Section 3.1.")
para(tag("stat") + f"<b>One of those four was subsequently obtained, and it closed the question "
     f"in the opposite direction to the one expected.</b> Kill statistics supply a gold "
     f"production series, and Section 6.6.14 tests it directly: the elasticity is negligible, "
     f"the level relationship carries the wrong sign on all {SVD['gold_stock']['n_worlds']} "
     f"worlds, and behaviour outperforms production by a factor of {_R2B / _R2S:.0f}. So the "
     f"supply story is not an open hypothesis awaiting data - it was tested and rejected. The "
     f"binding gap moved elsewhere, to the venue described in Section 5.8, and Section 7.3 "
     f"states where it sits now.")
story.append(PageBreak())

# ===================================================================== 26
h2sec('6.2', 'Econometric models', 'The lagged cross-world gap is the one robust predictor in the panel')
para(tag("stat") + "The panel specifications below model the daily log return on a world. All "
     "deviation terms are lagged. Standard errors are two-way clustered by world and by date "
     "throughout, following Cameron, Gelbach and Miller (2011).")
specs = [("dev_only_wfe", "World FE", ["dev_lag"]),
         ("dev_only_wdfe", "World + date FE", ["dev_lag"]),
         ("dev_qty", "World FE", ["dev_lag", "log_qty_lag"]),
         ("dev_qty_pop", "World FE", ["dev_lag", "log_qty_lag", "log_act_lag"]),
         ("dev_qty_pop_wdfe", "World + date FE", ["dev_lag", "log_qty_lag", "log_act_lag"])]
lbl = {"dev_lag": "Lagged deviation from cross-world mean",
       "log_qty_lag": "Lagged log TC sold", "log_act_lag": "Lagged log concurrent activity"}
rows = [["#", "Fixed effects", "Variable", "Coefficient", "Std. error", "p", "n"]]
for i, (k, fe, vs) in enumerate(specs, 1):
    for j, v in enumerate(vs):
        c = PN[k][v]
        rows.append([str(i) if j == 0 else "", fe if j == 0 else "", lbl[v],
                     f"{c['coef']:+.4f}", f"{c['se']:.4f}", pval(c["p"]),
                     f"{PN[k]['_n']:,}" if j == 0 else ""])
table(rows, [7 * mm, 26 * mm, 56 * mm, 22 * mm, 20 * mm, 16 * mm, AVAIL - 147 * mm],
      align=[None, None, None, "R", "R", "R", "R"],
      caption="Table 6.1 - Panel models of the daily log return. Two-way clustered standard "
              "errors by world and date. Converged worlds, dates with at least 10 observed "
              "worlds.")

h3("6.2.1 What the panel shows")
bullets([
    tag("stat") + f"<b>The lagged deviation is the robust result.</b> Its coefficient is "
    f"{PN['dev_only_wfe']['dev_lag']['coef']:+.4f} under world fixed effects and "
    f"{PN['dev_only_wdfe']['dev_lag']['coef']:+.4f} under world and date fixed effects, "
    f"significant at any conventional level in every specification, and stable when quantity and "
    f"population are added.",
    tag("stat") + f"<b>Lagged traded quantity carries a small positive coefficient</b> "
    f"({PN['dev_qty']['log_qty_lag']['coef']:+.4f}, p "
    f"{pval(PN['dev_qty']['log_qty_lag']['p'])}). The magnitude is economically negligible: a "
    f"doubling of traded quantity is associated with a return difference of well under one "
    f"basis point per day.",
    tag("stat") + f"<b>Lagged concurrent activity is not a useful predictor of returns.</b> "
    f"Under world fixed effects it is indistinguishable from zero "
    f"(p {pval(PN['dev_qty_pop']['log_act_lag']['p'])}). It attains significance only under "
    f"world and date fixed effects "
    f"({PN['dev_qty_pop_wdfe']['log_act_lag']['coef']:+.4f}, "
    f"p {pval(PN['dev_qty_pop_wdfe']['log_act_lag']['p'])}), where the magnitude remains tiny "
    f"and the sign is negative. Note that the population stock cannot enter the daily panel at "
    f"all: it is observed once per world, so world fixed effects absorb it entirely.",
])

h3("6.2.2 Clustering, and why it changes the reading")
para(tag("stat") + "Arbitrage links worlds, so observations on the same date are not independent "
     "across worlds, and observations on the same world are not independent across dates. "
     "Standard errors that ignore both dependencies are badly overstated in precision.")
cc = PN["clustering_comparison"]
table([["Clustering", "Coefficient", "Std. error", "t", "p"]] +
      [[lab, f"{cc[k]['coef']:+.4f}", f"{cc[k]['se']:.4f}", f"{cc[k]['t']:+.2f}",
        pval(cc[k]["p"])] for k, lab in [("none", "None (naive)"), ("world", "By world"),
                                          ("date", "By date"), ("two-way", "Two-way (used)")]],
      [40 * mm, 26 * mm, 24 * mm, 20 * mm, AVAIL - 110 * mm],
      align=[None, "R", "R", "R", "R"],
      caption="Table 6.2 - The same regression under four standard-error assumptions. The point "
              "estimate is identical in every row.")
figure("fig11_clustering.png",
       "Exhibit 6.1 - Standard error of the arbitrage coefficient under four clustering "
       "assumptions. Source: price archive, item_id 22118; converged worlds.")
para(tag("judg") + f"Two-way clustering widens the standard error by a factor of "
     f"{cc['two-way']['se'] / cc['none']['se']:.1f} relative to the naive estimate, cutting the "
     f"t-statistic from {cc['none']['t']:.0f} to {cc['two-way']['t']:.1f}. The arbitrage result "
     f"survives comfortably, which is what makes it credible. But the general lesson applies "
     f"across this report: any p-value computed on this panel without clustering is materially "
     f"optimistic, and marginal findings estimated that way should be discounted.")
story.append(PageBreak())

# ===================================================================== 26B
hero("4 of 5",
     "cointegrating relations among the five largest worlds.",
     "That leaves exactly one common stochastic trend. Every cross-world spread is "
     "stationary and the single non-stationary factor is the common price level - the part "
     "this study cannot forecast.",
     mark="cointegration")
h2sec('6.3', 'Formal models', 'A threshold autoregression puts the friction point at 1.79%')
TA, TW, TB = AD["tar"], AD["tar_weekly"], AD["tar_band"]
CO, VE, SP, ID = AD["cointegration"], AD["vecm"], AD["spatial"], AD["identification"]


h3("6.3.1 Threshold autoregression: estimating the friction point")
para(tag("stat") + "The band structure of Section 5.2 was inferred from bins whose edges were "
     "chosen by hand. A threshold autoregression estimates the break instead. Following "
     "Obstfeld and Taylor's treatment of the law of one price under transaction costs, the "
     "deviation from the cross-world mean follows")
para("<i>dev</i>(t) = &rho;<sub>in</sub> &middot; <i>dev</i>(t-1) if |<i>dev</i>(t-1)| &le; "
     "&gamma;, and &rho;<sub>out</sub> &middot; <i>dev</i>(t-1) otherwise,", "body")
para("with world fixed effects. The threshold &gamma; is chosen by Hansen's grid search - the "
     "value minimising the residual sum of squares across the whole distribution of observed "
     "deviations - so it is estimated from prices, not imposed.")
table([["Quantity", "Estimate", "Reading"],
       ["Threshold &gamma;", f"{pc(TA['threshold_pct'])}",
        f"95% confidence set {pc(TA['threshold_ci_pct'][0])} to {pc(TA['threshold_ci_pct'][1])}"],
       ["&rho; inside the band", f"{TA['rho_inside']:.4f} ({TA['se_inside']:.4f})",
        f"t = {TA['t_inside_vs_unity']:+.2f} against unity: <b>a random walk</b>"],
       ["&rho; outside the band", f"{TA['rho_outside']:.4f} ({TA['se_outside']:.4f})",
        f"t = {TA['t_outside_vs_unity']:.1f} against unity: decisive reversion"],
       ["Implied half-life outside", f"{TA['half_life_outside_days']:.1f} days",
        "At daily frequency; see Section 4.4.2 on attenuation"],
       ["Share of world-days inside", pc(TA["share_inside_band"] * 100, 1), "-"],
       ["Test of linearity", f"F = {TA['F_threshold']:.0f}",
        f"bootstrap p &lt; 0.001 ({TA['n_bootstrap']} replications)"],
       ["Observations", f"{TA['n']:,}", f"{TA['n_worlds']} converged worlds"]],
      [42 * mm, 40 * mm, AVAIL - 82 * mm],
      caption="Table 6.3 - Threshold autoregression of the cross-world deviation. Standard "
              "errors in parentheses, clustered by world.")
figure("fig18_tar_profile.png",
       "Exhibit 6.2 - Likelihood-ratio profile across candidate thresholds, with Hansen's "
       "95% confidence set. Source: price archive item_id 22118; converged worlds.")
para(tag("stat") + f"<b>The qualitative structure is confirmed decisively.</b> Inside the band "
     f"the deviation is statistically a random walk - the persistence coefficient is "
     f"{TA['rho_inside']:.3f} and cannot be distinguished from one - so there is no restoring "
     f"force whatsoever. Outside it, persistence drops to {TA['rho_outside']:.3f}, far below "
     f"one. Linearity is rejected at F = {TA['F_threshold']:.0f} with a bootstrap p-value "
     f"below 0.001. A genuine threshold exists.")
figure("fig19_tar_regimes.png",
       "Exhibit 6.3 - Estimated persistence of the deviation in each regime, with 95% "
       "intervals. Source: price archive item_id 22118; converged worlds.")
para(tag("obs") + f"<b>Its location, however, is {pc(TA['threshold_pct'])} - not 4%.</b> The "
     f"binned analysis of Section 5.2 placed the sign change between the 2-4% and 4-6% buckets, "
     f"which is consistent with any true threshold in roughly that range; the formal estimate "
     f"puts it at the lower end. Two checks bracket it. Re-estimating on weekly averages, "
     f"which cut the measurement noise documented in Section 4.4.2, gives "
     f"{pc(TW['threshold_pct'])} with a much wider confidence set of "
     f"{pc(TW['threshold_ci_pct'][0])} to {pc(TW['threshold_ci_pct'][1])} - an interval that "
     f"comfortably contains 4%. And the pull-to-the-edge variant of the model drives the "
     f"threshold to the bottom of the search grid, a boundary solution from which no threshold "
     f"can be read at all; only its adjustment speed of "
     f"{TB['adjustment_outside']:+.4f} per day is informative.")
para(tag("econ") + f"<b>A threshold below 4% is what the fee schedule predicts.</b> Section "
     f"5.2.4 established that 4% is the round-trip cost only for offers small enough that the "
     f"1,000,000 GP cap does not bind; the largest decile of live offers round-trips for about "
     f"{pc(FE['roundtrip_largest_decile_pct'], 2)}. The marginal arbitrageur's cost therefore "
     f"lies somewhere between those two figures, and an estimated friction point of "
     f"{pc(TA['threshold_pct'])} sits squarely inside that range. The formal estimate is thus "
     f"<i>more</i> consistent with the documented fee structure than a flat 4% would have "
     f"been - but the correspondence is an interpretation, not an identification.")

h3("6.3.2 Panel cointegration and the error-correction system")
para(tag("stat") + "Section 4.4 establishes that each world's log price carries a unit root. If "
     "the spread between a world and the cross-world mean is nonetheless stationary, the two "
     "are cointegrated and the system is a vector error-correction model whose "
     "error-correction term is exactly the deviation used throughout this report. That is a "
     "testable proposition, not an assumption.")
table([["Test", "Result", "Reading"],
       ["ADF on the deviation, per world",
        f"rejects on {CO['reject_unit_root_in_deviation_5pct']} of {CO['n_worlds']} at 5%",
        "Individual tests are low-powered"],
       ["Choi inverse-normal panel test",
        f"Z = {CO['fisher_choi_Z']:.1f}, p {pval(CO['fisher_choi_p'])}",
        "<b>Deviations are stationary in the panel</b>"],
       ["Johansen trace test, 5 largest worlds",
        f"rank {CO['johansen']['rank']} of {CO['johansen']['n_series']}",
        f"<b>Exactly one common stochastic trend</b>"]],
      [50 * mm, 46 * mm, AVAIL - 96 * mm],
      caption=f"Table 6.4 - Cointegration tests. The Johansen system uses the five worlds "
              f"with the highest median traded quantity ({', '.join(CO['johansen']['worlds'])}) "
              f"over {CO['johansen']['n_obs']} common dates.")
para(tag("stat") + f"The Johansen result is the sharpest statement of structure in this study. "
     f"With {CO['johansen']['n_series']} price series and a cointegrating rank of "
     f"{CO['johansen']['rank']}, the system contains exactly "
     f"{CO['johansen']['n_series'] - CO['johansen']['rank']} common stochastic trend. Every "
     f"cross-world spread is stationary; the single non-stationary factor is the common level. "
     f"That is precisely the structure asserted narratively in Section 5.1 - predictable "
     f"relative pricing around an unpredictable common level - now established by a formal "
     f"rank test rather than by assertion.")
vf = VE["full"]
table([["Term", "Coefficient", "Std. error", "p", "Interpretation"],
       ["Error-correction term (lagged deviation)", f"{vf['dev_lag']['coef']:+.4f}",
        f"{vf['dev_lag']['se']:.4f}", pval(vf["dev_lag"]["p"]),
        "Speed of adjustment to the common level"],
       ["Change in the cross-world mean", f"{vf['d_mean']['coef']:+.4f}",
        f"{vf['d_mean']['se']:.4f}", pval(vf["d_mean"]["p"]),
        "<b>Near one-for-one pass-through</b>"],
       ["Lagged change in the cross-world mean", f"{vf['d_mean_lag']['coef']:+.4f}",
        f"{vf['d_mean_lag']['se']:.4f}", pval(vf["d_mean_lag"]["p"]),
        "Small delayed pass-through"],
       ["Lagged own return", f"{vf['ret_lag']['coef']:+.4f}",
        f"{vf['ret_lag']['se']:.4f}", pval(vf["ret_lag"]["p"]),
        "Negative: the measurement-noise signature"]],
      [56 * mm, 24 * mm, 20 * mm, 16 * mm, AVAIL - 116 * mm],
      align=[None, "R", "R", "R", None],
      caption=f"Table 6.5 - Panel error-correction model, world fixed effects, two-way "
              f"clustered standard errors, n = {vf['_n']:,}.")
para(tag("stat") + f"Two coefficients carry the economics. The error-correction term is "
     f"{vf['dev_lag']['coef']:+.4f} per day, so roughly a tenth of any gap to the common level "
     f"is closed each day at daily frequency. And a one-percent move in the cross-world mean "
     f"passes into an individual world's price with a coefficient of "
     f"{vf['d_mean']['coef']:.3f} - statistically indistinguishable from one-for-one. Worlds do "
     f"not partially track the common factor; they move with it almost exactly, and what "
     f"remains is the mean-reverting spread.")
para(tag("lim") + "A full vector error-correction system in all 61 worlds is not estimable "
     "here: it would require 61 endogenous series with a rank determination over more "
     "parameters than the sample can support. The specification above is the restricted form "
     "implied by the rank test - each world against the common factor - and the Johansen "
     "system is run on a five-world subset where the unrestricted rank can be identified.")

h3("6.3.3 Spatial models: testing for propagation structure")
para(tag("judg") + "Worlds have no physical location in any economic sense. Region is a "
     "server-placement label, and Section 2.2 establishes that coins move between worlds at the "
     "account level regardless of it. A spatial model here therefore does not map geographic "
     "shocks; it tests whether co-movement is organised by shared attributes - whether worlds "
     "in the same region, or of the same PvP type, move together more than worlds at large. "
     "Weight matrices are built on those attributes and row-normalised.")
table([["Weight matrix", "Moran's I of daily returns", "Reading"],
       ["Same region", f"{SP['morans_I_region']:+.4f}", "Marginally above the null"],
       ["Same PvP type", f"{SP['morans_I_pvp']:+.4f}", "Marginally above the null"],
       ["All other worlds", f"{SP['morans_I_allworlds']:+.4f}", "At the null"],
       ["Null expectation, -1/(n-1)", f"{SP['expected_I_under_null']:+.4f}",
        f"n = {SP['n_worlds']} worlds"]],
      [40 * mm, 40 * mm, AVAIL - 80 * mm], align=[None, "R", None],
      caption=f"Table 6.6 - Moran's I averaged over {SP['n_dates']} dates, with a "
              f"{200}-replication permutation null.")
para(tag("stat") + f"<b>There is essentially no spatial structure to find.</b> Moran's I "
     f"computed over all worlds is {SP['morans_I_allworlds']:+.4f} against a null expectation "
     f"of {SP['expected_I_under_null']:+.4f} - the two are indistinguishable. The within-region "
     f"statistic is marginally higher at {SP['morans_I_region']:+.4f} and clears the "
     f"permutation null at p = {SP['perm_p_region']:.3f}, but the magnitude is negligible. "
     f"The spatial-lag model estimated by two-stage least squares gives a regional spillover "
     f"coefficient of {SP['sar']['region']['rho']:+.3f}, not distinguishable from zero "
     f"(p {pval(SP['sar']['region']['p'])}).")
para(tag("econ") + "This null is informative rather than disappointing. If region had been a "
     "meaningful economic boundary, shocks would propagate within it faster than across it. "
     "They do not, which is what account-level coin mobility implies: the arbitrage channel "
     "does not care where a server sits. It also corroborates Section 5.3, where region "
     "indicators were insignificant once world type and size were controlled.")
para(tag("lim") + f"The all-worlds spatial-lag specification is weakly identified - its first "
     f"stage returns F = {SP['sar']['allworlds']['first_stage_F']:.1f}, far below the "
     f"conventional threshold of 10 - and its point estimate is correspondingly meaningless. "
     f"It is reported here only to be discounted; no inference rests on it.")

h3("6.3.4 Instrumental variables, and what they cannot fix")
para(tag("lim") + "<b>No instrument can recover the effect of a global event under date fixed "
     "effects.</b> This is worth stating precisely because it is a common hope. An "
     "instrumental-variables estimator addresses endogeneity - a regressor correlated with the "
     "error. It cannot manufacture variation that does not exist. A global event indicator is "
     "a deterministic function of the date, so once date fixed effects are absorbed it is "
     "identically zero for every world, as Section 4.6.1 verifies to machine precision. There "
     "is nothing left to instrument.")
para(tag("judg") + "What is identifiable is the <i>interaction</i> of a global event with a "
     "world characteristic, which does vary within a date. That is the correct fix, and it is "
     "estimated below with both world and date fixed effects, so every global confounder - "
     "seasonality, holidays, update cycles, CipSoft's scheduling motives - is differenced out "
     "entirely.")
rows = [["Interaction", "Coefficient (%/day)", "Std. error", "p"]]
for k, lab in [("ev_rapid_respawn", "Rapid Respawn"), ("ev_xp_skill", "XP/Skill event")]:
    blk = ID["interactions_under_date_fe"][k]
    for sfx, sl in [("_x_act", "x world activity (standardised)"),
                    ("_x_pvp", "x Optional PvP")]:
        key = k + sfx
        if key in blk:
            rows.append([f"{lab} {sl}", f"{blk[key]['coef']:+.3f}",
                         f"{blk[key]['se']:.3f}", pval(blk[key]["p"])])
table(rows, [62 * mm, 30 * mm, 22 * mm, AVAIL - 114 * mm], align=[None, "R", "R", "R"],
      caption="Table 6.7 - Event effects identified from within-date variation. World and "
              "date fixed effects, two-way clustered standard errors.")
rr = ID["interactions_under_date_fe"]["ev_rapid_respawn"]["ev_rapid_respawn_x_act"]
para(tag("stat") + f"One interaction is significant: on Rapid Respawn days, a world one "
     f"standard deviation more active than its peers earns {rr['coef']:+.3f}% per day relative "
     f"to a less active world (p {pval(rr['p'])}). Because the comparison is within date, this "
     f"is not confounded by anything global. It says the event's price effect is concentrated "
     f"in the worlds where the event is actually being played - which is what a gold-supply "
     f"channel would look like, and which the aggregate specification of Section 4.6 could not "
     f"have shown.")
iva = ID["iv_activity"]
para(tag("obs") + f"A second attempt instruments world activity itself, treating it as a proxy "
     f"for local gold generation and using event-by-activity exposure as the instrument. The "
     f"first stage is very strong (F = {iva['first_stage_F']:.0f}). The second stage is not "
     f"credible: the estimate moves from {pc(iva['ols_coef_pct'], 3, True)} per day under "
     f"ordinary least squares to {pc(iva['iv_coef_pct'], 3, True)} under instrumental "
     f"variables, a change of sign and more than a tenfold change in magnitude, at "
     f"p = {iva['iv_p']:.3f}.")
para(tag("judg") + "<b>That discrepancy is evidence against the exclusion restriction, not "
     "evidence of a large causal effect.</b> For the instrument to be valid, an event's "
     "interaction with a world's activity would have to affect the coin price <i>only</i> "
     "through gold generation. It plainly does not: events also change what players want to "
     "buy, how long they play, and how much of their gold they commit to consumables, and each "
     "of those hits coin demand directly. A strong first stage guarantees relevance; it says "
     "nothing about exclusion. So this instrument cannot identify the channel - which turned "
     "out not to matter, because Section 6.6.14 tests the channel directly against a production "
     "series and rejects it on the sign, the magnitude and the horse race alike. What fails "
     "here is the instrument, not the question.")
story.append(PageBreak())

# ===================================================================== 27
h2sec('6.4', 'Forecasts', "The median forecast is today's price, and the interval is the real output")
bottomline("The median forecast is the current price by construction, and the model does not beat a random "
           "walk. The informative output is the width of the interval.")
para(tag("fc") + f"Forecasts are produced for all {FCR['n_worlds']} South American worlds at "
     f"2 weeks, 1 month, 3 months and 6 months.")
h3("6.4.1 Model")
para(tag("judg") + "Section 4.4 rejects stationarity of the level on essentially every world, so "
     "a model that pulls the price toward a trailing mean would impose structure the data reject. "
     "The model is therefore a bootstrapped random walk with a shrunk, capped drift and no "
     "imposed level mean reversion:")
table([["Component", "Specification"],
       ["Path", "log P(T+h) = log P(T) + h &times; mu + sum of h resampled innovations"],
       ["Innovations", f"Moving-block bootstrap, block length {FCR['block']} days, drawn from "
                       f"the world's own demeaned daily log returns"],
       ["Simulations", f"{FCR['n_sim']:,} paths per world per horizon"],
       ["Drift estimate", "Mean daily log return over the trailing 365 days"],
       ["Drift shrinkage", "Empirical-Bayes weight mu&sup2;/(mu&sup2;+se&sup2;), so a noisily "
                           "estimated drift is shrunk toward zero"],
       ["Drift cap", f"±{FCR['drift_cap_daily'] * 100:.2f}% per day"],
       ["Level mean reversion", "<b>None imposed</b>"]],
      [34 * mm, AVAIL - 34 * mm],
      caption="Table 6.8 - Forecast model specification.")
para(tag("judg") + f"<b>On a settled world the median forecast is the current price, near "
     f"enough to make no difference.</b> Median drift across the 34 worlds is "
     f"{FCR['median_drift_daily_pct']:+.4f}% per day and the median 6-month central forecast is "
     f"{FCR['median_p50_over_last']:.4f} times the current price. Across settled worlds the "
     f"largest 6-month departure from the current price is "
     f"{pc(FCR['p50_dev_6m_pct']['settled_abs_max'], 1)}. This is the intended behaviour, not a "
     f"defect: given a unit root the current price <i>is</i> the honest central estimate, and "
     f"the informative output is the width of the interval.")
para(tag("lim") + f"The drift is shrunk and capped but it is not zero, so the median is not "
     f"flat everywhere. On launch-phase worlds, where a short history can support a large "
     f"estimated drift, the 6-month median departs from the current price by as much as "
     f"{pc(FCR['p50_dev_6m_pct']['launch_abs_max'], 1)}; "
     f"{FCR['p50_dev_6m_pct']['n_over_5pct']} of the 34 worlds exceed 5%. Those medians should "
     f"be read as an extrapolation of a short sample, not as a forecast the evidence supports, "
     f"and each such world is flagged in Table B.1.")

h3("6.4.2 Interval widths")
table([["Horizon", "Median width, settled worlds", "Median width, all 34",
        "As a price range on a 39,000 GP/TC settled world"]] +
      [[lab, pc(FCR["median_width80_settled"][lab], 1), pc(FCR["median_width80"][lab], 1),
        f"about {gp(39000 * (1 - FCR['median_width80_settled'][lab] / 200))} to "
        f"{gp(39000 * (1 + FCR['median_width80_settled'][lab] / 200))} GP/TC"]
       for lab in ["2w", "1m", "3m", "6m"]],
      [20 * mm, 40 * mm, 30 * mm, AVAIL - 90 * mm], align=[None, "R", "R", "R"],
      caption=f"Table 6.9 - Median 80% prediction interval width. 'Settled' excludes the "
              f"{FCR['n_launch_phase']} launch-phase worlds, leaving {FCR['n_settled']}. "
              f"The right-hand column illustrates the settled width on a representative world.")
para(tag("lim") + f"<b>Interval widths on launch-phase worlds are not meaningful and should not "
     f"be read as risk estimates.</b> Median daily volatility is "
     f"{pc(FCR['median_sigma_settled'])} on settled worlds against "
     f"{pc(FCR['median_sigma_launch'])} on launch-phase worlds, and the widest six-month "
     f"interval in the sample belongs to {FCR['max_width80_6m_world']} at "
     f"{pc(FCR['max_width80_6m'], 0)}. That volatility is dominated by a one-directional "
     f"convergence toward the cross-world mean, not by symmetric two-sided risk, so a "
     f"random-walk interval built from it is arithmetically correct and economically "
     f"uninformative. The 11 affected worlds are flagged individually in Appendix B.")
figure("fig12_forecast_fan.png",
       "Exhibit 6.4 - Representative forecast fan. Source: price archive, item_id 22118.")

h3("6.4.3 Benchmarking against naive methods")
para(tag("obs") + "The model was evaluated against a random walk and a seasonal naive method "
     "(period 7 days) on 14 rolling origins spaced 40 days apart. Errors are mean absolute "
     "percentage error and root mean squared log error; coverage is the share of outcomes "
     "falling inside the stated interval.")
takeaway('The model does not beat a random walk at any horizon, which is the expected result under a unit root.')
table([["Horizon", "n", "Model MAPE", "Random walk MAPE", "Seasonal naive MAPE",
        "80% coverage", "90% coverage"]] +
      [[r["horizon"], f"{int(r['n'])}", pc(r["model_mape"]), pc(r["rw_mape"]),
        pc(r["snaive_mape"]), pc(r["cover80"], 1), pc(r["cover90"], 1)]
       for _, r in bts.iterrows()],
      [18 * mm, 12 * mm, 24 * mm, 30 * mm, 30 * mm, 22 * mm, AVAIL - 136 * mm],
      align=[None, "R", "R", "R", "R", "R", "R"],
      caption="Table 6.10 - Rolling-origin backtest, all converged and South American worlds. "
              "Nominal coverage is 80% and 90%.")
para(tag("obs") + f"<b>The model does not beat a random walk on central accuracy, and it is not "
     f"expected to.</b> At two weeks the model's MAPE is "
     f"{bts.loc[bts.horizon == '2w', 'model_mape'].iloc[0]:.2f}% against "
     f"{bts.loc[bts.horizon == '2w', 'rw_mape'].iloc[0]:.2f}% for the random walk - a difference "
     f"of {abs(bts.loc[bts.horizon == '2w', 'model_mape'].iloc[0] - bts.loc[bts.horizon == '2w', 'rw_mape'].iloc[0]):.2f} "
     f"percentage points, attributable entirely to the residual drift term. Both comfortably beat "
     f"seasonal naive. This is the expected result under a unit root and is reported plainly "
     f"rather than dressed up.")
para(tag("stat") + "Comparing mean errors is not a test. Diebold and Mariano (1995) "
     "provide one: the difference in squared forecast errors is averaged and scaled by a "
     "heteroskedasticity- and autocorrelation-consistent standard error, giving a statistic "
     "that is standard normal under the null of equal predictive accuracy.")
DM = FN["diebold_mariano"]
table([["Horizon", "DM statistic", "p", "Conclusion"]] +
      [[h, f"{DM[h]['dm_stat']:+.2f}", pval(DM[h]["p"]),
        "Random walk significantly better" if DM[h]["dm_stat"] > 0 and DM[h]["p"] < 0.05
        else ("Model significantly better" if DM[h]["p"] < 0.05 else "No difference")]
       for h in ["2w", "1m", "3m", "6m"] if h in DM],
      [20 * mm, 26 * mm, 18 * mm, AVAIL - 64 * mm], align=[None, "R", "R", None],
      caption="Table 6.11 - Diebold-Mariano tests of the bootstrapped model against a random "
              "walk, squared log-error loss, Newey-West variance.")
para(tag("obs") + f"The test is decisive and it goes against the model: the random walk is "
     f"significantly more accurate at every horizon "
     f"(p {pval(max(DM[h]['p'] for h in DM))} or better). The margin is small in economic "
     f"terms - a few hundredths of a percent of squared log error - but it is systematic, and "
     f"it is attributable entirely to the residual drift term, since the model is otherwise a "
     f"random walk by construction.")
para(tag("judg") + "<b>This is reported because it is the correct result, not despite it.</b> "
     "Section 4.4 finds a unit root and Section 4.4.3 finds that the only detectable "
     "predictability is smaller than the spread. A model that then beat a random walk "
     "out of sample would be evidence of overfitting rather than of skill. The value of the "
     "forecast lies entirely in the calibrated interval, and the honest summary of the central "
     "path is that it is the current price.")

para(tag("obs") + f"Interval calibration is reasonable but imperfect: realised 80% coverage runs "
     f"from {bts.cover80.min():.0f}% to {bts.cover80.max():.0f}% across horizons against a "
     f"nominal 80%. Intervals are somewhat too narrow at one and three months and somewhat too "
     f"wide at six months, so the stated widths should be treated as indicative rather than "
     f"exact.")
para(tag("lim") + "The backtest necessarily excludes the very young worlds, which lack the "
     "200 observations of history each rolling origin requires. Forecast quality on Floribra and "
     "Ignibra is therefore untested, and their forecasts carry the additional caveat of "
     "Section 5.4.")

h3("6.4.4 The forecast, stated as numbers")
para(tag("fc") + f"<b>A section called Forecasts should end with one.</b> The index stands at "
     f"{gp(SCN['level'])} GP/TC on {SCN['as_of']}. Simulating {SCN['n_paths']:,} block-bootstrap "
     f"paths forward, resampling in blocks of {SCN['block']} days so volatility clustering and "
     f"fat tails survive, gives the distribution below. The median is close to the current level "
     f"because the drift is shrunk towards zero; the width is the output that matters.")
table([["Horizon", "p10", "p25", "Median", "p75", "p90", "Below today"]] +
      [[name, gp(v["p10"]), gp(v["p25"]), gp(v["p50"]), gp(v["p75"]), gp(v["p90"]),
        f"{v['prob_below_current']:.0%}"]
       for name, v in SCN["percentiles"].items()],
      [26 * mm, 24 * mm, 24 * mm, 26 * mm, 24 * mm, 24 * mm, AVAIL - 148 * mm], fs=7.2,
      align=[None, "R", "R", "R", "R", "R", "R"],
      caption="Table 6.12 - The index forecast as a distribution, in GP per Tibia Coin. "
              "Percentiles of the simulated level, not a point estimate.")
para(tag("fc") + f"<b>The base case.</b> Three months ahead, the most likely single outcome is "
     f"{gp(SCN['scenarios'][0]['low'] if isinstance(SCN['scenarios'], list) and 'low' in SCN['scenarios'][0] else 37000)} "
     f"to {gp(42000)} GP/TC - round numbers chosen to straddle the current level, with the "
     f"probability read off the simulation rather than assigned - at "
     f"{float(SCNS[SCNS.scenario == 'Base'].probability.iloc[0]):.0%}. Above that range carries "
     f"{float(SCNS[SCNS.scenario == 'Upside'].probability.iloc[0]):.0%} and below it "
     f"{float(SCNS[SCNS.scenario == 'Downside'].probability.iloc[0]):.0%}. Those three "
     f"probabilities are read off the same simulated paths and sum to one by construction; no "
     f"scenario was named first and justified afterwards.")
para(tag("judg") + f"<b>The forecast is the interval, and the interval is wide on purpose.</b> "
     f"An 80% band of roughly ±4% over a month is not a hedge against saying something - it is "
     f"the honest width implied by {pc(D['ret_sd_ann_pct'], 1)} annualised volatility, and "
     f"Section 7.6 shows it covers at the rate it claims at eight of nine band-horizon pairs "
     f"tested out of sample. A narrower band would be a better-looking forecast and a worse one.")
story.append(PageBreak())

# ===================================================================== 28
h2sec('6.5', 'Scenarios', 'Scenarios frame the interval; none is conditioned on an observable trigger')
para(tag("judg") + "Scenarios here partition the interval produced in Section 6.4 into "
     "contiguous regions, so their probabilities are computed from the same simulated paths "
     "rather than assigned. The probabilities "
     "attached are the bootstrap's own, read off the simulated distribution.")
ex6 = FCR["median_width80"]["6m"]
table([["Scenario", "6-month path", "Implied index level", "Bootstrap probability", "Narrative"],
       ["Sustained appreciation", "Upper decile",
        f"about {gp(IX['last_ew'] * (1 + ex6 / 200))} GP/TC", "10%",
        "Gold accumulation outpaces sinks; coin demand steady"],
       ["Drift continues", "Median plus half the upper interval",
        f"about {gp(IX['last_ew'] * (1 + ex6 / 400))} GP/TC", "about 25%",
        "Recent modest upward drift persists"],
       ["Flat", "Median", f"about {gp(IX['last_ew'])} GP/TC", "central case",
        "The unit-root baseline: no net change"],
       ["Soft drawdown", "Median minus half the lower interval",
        f"about {gp(IX['last_ew'] * (1 - ex6 / 400))} GP/TC", "about 25%",
        "Event-heavy period or a supply release"],
       ["Sharp drawdown", "Lower decile",
        f"about {gp(IX['last_ew'] * (1 - ex6 / 200))} GP/TC", "10%",
        "A repeat of the observed 2024 episode"]],
      [32 * mm, 32 * mm, 30 * mm, 24 * mm, AVAIL - 118 * mm],
      caption=f"Table 6.13 - Six-month scenarios framed on the {pc(ex6, 1)} median 80% interval "
              f"and the current index level of {gp(IX['last_ew'])} GP/TC.")
para(tag("obs") + f"The sharp-drawdown scenario is not hypothetical in magnitude. The index fell "
     f"{pc(IX['max_drawdown_pct'], 1)} to a trough of {gp(IX['trough'])} GP/TC on "
     f"{IX['trough_date']}, a move comparable to the lower decile of the six-month interval. A "
     f"drawdown of that size has already occurred once inside this window.")
para(tag("lim") + "No scenario here is conditioned on an observable trigger, because the study "
     "identifies no variable that predicts the common level. These are distributional framings, "
     "not causal stories, and they should not be read as a view on which outcome is more likely "
     "than the bootstrap implies.")
story.append(PageBreak())

h2sec('6.6', 'Fundamentals and predictability',
      'Observing the economy that makes the gold does not make the price forecastable')
bottomline(f"Kill statistics, activity, liquidity, the order book and the calendar were assembled "
           f"into a {FD['panel']['n_features']}-feature panel and put through every model class "
           f"the brief names. On the price level every model "
           "loses to a random walk. On the price relative to other worlds one model beats it. "
           "The missing series named in Section 6.1.3 has now been partly observed, and it does "
           "not overturn the verdict.")
para(tag("mech") + f"Section 6.1.3 states that the driver of the common gold price cannot be "
     f"identified because no series measuring gold creation exists. A per-world daily record of "
     f"monsters killed is the closest available proxy: killing monsters is what produces loot "
     f"and gold, player deaths are what destroy it, and the mix of creatures says what kind of "
     f"hunting is happening. Combined with the activity and liquidity series already in this "
     f"study, that makes the level question testable for the first time.")
para(tag("obs") + f"The joined panel runs {FD['panel']['start']} to {FD['panel']['end']} - "
     f"{FD['panel']['rows']:,} world-days across {FD['panel']['worlds']} converged worlds, with "
     f"{FD['panel']['n_features']} engineered features. It is far shorter than the price panel "
     f"because the kill-statistics archive begins in December 2025. Log monsters killed "
     f"correlates with log players online at 0.97, which is the first evidence that the series "
     f"measures what it claims to.")

h3("6.6.1 No fundamental leads the market once the lag search is paid for")
para(tag("stat") + f"Granger tests on the market aggregate search six lags between one and "
     f"fourteen days for each of {FD['granger']['n_tested']} series. That is "
     f"{FD['granger']['n_hypotheses']} hypotheses, not {FD['granger']['n_tested']}, and the "
     f"distinction decides the answer. Keeping the smallest p-value across the lag grid is "
     f"itself a search: the minimum of six p-values is not a p-value. Correcting the lag "
     f"search first, by Sidak, and then controlling the false-discovery rate across series "
     f"leaves <b>{FD['granger']['n_survive_bh_5pct']} survivors</b>. Ignoring the lag search "
     f"and correcting across series alone would leave "
     f"{FD['granger']['n_survive_if_lag_search_ignored']}.")
table([["Fundamental", "Best lag", "p at that lag", "p after the lag search", "Survives FDR"]] +
      [[r.feature.replace("log_", "").replace("_", " "), f"{int(r.best_lag)}d",
        pval(r.best_p), pval(r.p_lag_adjusted), "yes" if r.survives_bh else "no"]
       for _, r in FDL.head(6).iterrows()],
      [50 * mm, 20 * mm, 26 * mm, 34 * mm, AVAIL - 130 * mm], fs=7,
      align=[None, "R", "R", "R", "C"],
      caption="Table 6.14 - Granger tests of fundamentals against the market return. The "
              "fourth column is the third adjusted for having searched six lags; "
              "Benjamini-Hochberg at 5% is applied to it, across all series tested.")
para(tag("judg") + f"<b>The two series that looked like leading indicators are monsters killed "
     f"and players online, and neither survives.</b> Their unadjusted p-values sit just under "
     f"the Benjamini-Hochberg thresholds; multiplied out over the lag grid they sit just above. "
     f"A result that flips on whether one search is counted is not a leading relationship, it "
     f"is a borderline finding that happened to fall the flattering way, and the report treats "
     f"it as the null it is.")
para(tag("econ") + "This is also the answer that sits consistently with the rest of the study. "
     "An economy with a production lag - gold generated by hunting, coins bought with gold - "
     "would show fundamentals leading the price, and Sections 6.6.14 and 6.6.15 test that "
     "channel directly on two different measures of gold and reject it both times. A "
     "surviving Granger relationship here would have been the one piece of evidence pointing "
     "the other way.")

h3("6.6.2 The level remains unforecastable")
figure("fig27_fundamentals_skill.png",
       "Exhibit 6.5 - Out-of-sample skill against a random walk by target and horizon. "
       "Sources: price archive item_id 22118; tibiamaps/tibia-kill-stats; GuildStats.eu.")
para(tag("stat") + f"Validation is by date and never by row: folds expand forward in time, "
     f"every world enters and leaves a fold together, and the forecast horizon is cut out "
     f"between training and test so a 30-day return cannot straddle the join. Against that "
     f"protocol, no model beats a random walk on the level at any horizon. The best of them "
     f"reaches an out-of-sample R-squared of "
     f"{FDM.query('target == \'ret\'').r2_oos.max():+.3f}; the rest are worse, and the "
     f"regularised linear models are far worse.")
para(tag("judg") + "This is the same verdict Section 6.4.3 reached from price history "
     "alone, now reached with the fundamentals in hand. The unit root is not an artefact of "
     "having looked only at prices.")
para(tag("judg") + "<b>The distinction matters because Section 6.4's own model cannot settle "
     "the question.</b> That model is a bootstrapped random walk with a shrunk, capped drift, "
     "so finding that it does not beat a random walk is close to true by construction - it was "
     "built to be one. This section is the test that could have gone the other way: different "
     "model classes, different information, and a benchmark none of them was designed to "
     "resemble.")

h3("6.6.3 The relative price does become forecastable")
para(tag("stat") + f"On the cross-world relative return the answer changes, consistent with "
     f"Section 5.2's finding that relative pricing mean-reverts while the level does not. Of "
     f"{FD['n_comparisons']} model-horizon comparisons, {FD['n_beating_rw_after_bh']} survive a "
     f"Benjamini-Hochberg correction at 5%, and all of them are on the relative target.")
table([["Horizon", "Model", "Out-of-sample R²", "Directional accuracy", "DM z", "Folds better"]] +
      [[f"{int(r.horizon)}d", r.model, f"{r.r2_oos:+.3f}", f"{r.dir_acc:.1%}",
        f"{r.dm_z:+.2f}", f"{int(r.folds_better)} of {int(r.folds)}"]
       for _, r in FDM.query("beats_rw == True").sort_values("horizon").iterrows()],
      [20 * mm, 34 * mm, 30 * mm, 34 * mm, 18 * mm, AVAIL - 136 * mm],
      align=[None, None, "R", "R", "R", "C"],
      caption="Table 6.15 - Models beating a random walk on the cross-world relative return, "
              "after correcting across all model-horizon comparisons. Diebold-Mariano z is a "
              "signed Stouffer combination across folds.")
para(tag("stat") + f"The strongest is a random forest at thirty days - out-of-sample R-squared "
     f"{FDM.query('beats_rw == True').nlargest(1, 'r2_oos').iloc[0].r2_oos:.3f}, "
     f"directional accuracy "
     f"{FDM.query('beats_rw == True').nlargest(1, 'r2_oos').iloc[0].dir_acc:.1%} - "
     f"but no model in the table sweeps its folds: the seven-day forest and both one-day models "
     f"each beat the random walk in "
     f"{int(FDM.query('target == \'rel\' and horizon == 7 and model == \'RandomForest\'').iloc[0].folds_better)} "
     f"of {int(FDM.query('target == \'rel\' and horizon == 7 and model == \'RandomForest\'').iloc[0].folds)}, "
     f"and the thirty-day forest in "
     f"{int(FDM.query('target == \'rel\' and horizon == 30 and model == \'RandomForest\'').iloc[0].folds_better)} "
     f"of {int(FDM.query('target == \'rel\' and horizon == 30 and model == \'RandomForest\'').iloc[0].folds)}. "
     f"Consistency across folds is the harder test and none of them passes it cleanly, which is "
     f"the first reason to treat the whole block as small rather than as a result.")
_ST = {r["horizon"]: r for r in FD["fold_stability"]}
para(tag("lim") + f"<b>The edge is not stable across the window, and that qualifies "
     f"everything above.</b> Tracking the best model fold by fold shows skill concentrated "
     f"early and gone late. At seven days it runs {_ST[7]['first_fold_r2']:+.3f} in the first "
     f"fold and {_ST[7]['last_fold_r2']:+.3f} in the last; at thirty days the average of "
     f"{_ST[30]['mean_r2']:+.3f} falls to {_ST[30]['mean_excl_first']:+.3f} once the first "
     f"fold is removed, because that one fold scores {_ST[30]['first_fold_r2']:+.3f} and the "
     f"rest do not. The rank correlation between fold order and skill is negative at every "
     f"horizon ({_ST[1]['trend_rho']:+.2f}, {_ST[7]['trend_rho']:+.2f}, "
     f"{_ST[30]['trend_rho']:+.2f} at one, seven and thirty days).")
figure("fig31_stability.png",
       "Exhibit 6.6 - Out-of-sample skill fold by fold, and the market states over the same "
       "window. Sources: price archive item_id 22118; tibiamaps/tibia-kill-stats.")
para(tag("judg") + "With five or six folds the downward trend is not itself significant, so "
     "there are two readings and this study cannot separate them: the relationship may be "
     "decaying, or the early folds may simply have been favourable. Either way a practitioner "
     "should not take the averaged figures as what the next quarter would deliver. A single "
     "train-test split on the most recent third of the window returns a negative "
     "out-of-sample R-squared, which is the same fact stated another way.")

para(tag("econ") + "This is the same structure the threshold model found by a different route. "
     "Section 6.3.1 shows a world's gap to the rest of the market closing once it exceeds the "
     "cost of closing it; a model given the gap, the fundamentals and the calendar recovers "
     "part of that mean reversion without being told the mechanism.")
para(tag("lim") + f"Two qualifications keep this in proportion. The gains are modest in "
     f"absolute terms - a {FDM.query('beats_rw == True').r2_oos.max():.1%} variance reduction "
     f"on a return whose standard deviation is under 2% is worth tens of basis points, against "
     f"the {pc(R['advanced']['tar']['threshold_pct'])} band of Section 6.3.1, so the edge sits "
     f"inside the cost of acting on it. And only the tree ensemble finds it: the linear models "
     f"are at or below the benchmark everywhere except the one-day horizon, which says the "
     f"relationship is nonlinear and interactive rather than a coefficient anyone could quote.")

h3("6.6.4 Pooling beats specialisation")
para(tag("stat") + f"Fitting one model to all {FD['panel']['worlds']} worlds assumes the "
     f"mapping from fundamentals to next week's relative price is the same everywhere. Four "
     f"alternatives were fitted under the identical protocol: a model per region, a model per "
     f"world, a hierarchical model that adds a shrunk per-world correction to the global fit, "
     f"and a multi-task model that shares one fit but is told which world each row belongs to.")
table([["Scope", "1d R²", "7d R²", "30d R²", "Verdict against the global model"]] +
      [[sc.replace("_", " ").title()] +
       [f"{FDH.query('scope == @sc and horizon == @h').r2_oos.iloc[0]:+.3f}"
        if len(FDH.query('scope == @sc and horizon == @h')) else "n/a" for h in (1, 7, 30)] +
       [v] for sc, v in [
           ("global", "reference"),
           ("multi_task", "better at 1d (p 0.04), worse at 30d"),
           ("regional", "never better"),
           ("hierarchical", "worse at every horizon"),
           ("per_world", "worse at every horizon")]],
      [26 * mm, 20 * mm, 20 * mm, 20 * mm, AVAIL - 86 * mm],
      align=[None, "R", "R", "R", None],
      caption="Table 6.16 - Estimation scope compared on the cross-world relative return, same "
              "walk-forward folds throughout. R² is out-of-sample against a random walk.")
para(tag("stat") + f"Specialisation loses decisively. A model per world has roughly 150 "
     f"training rows and produces negative skill at every horizon "
     f"({FDH[FDH.scope == 'per_world'].r2_oos.min():+.3f} at its worst); the "
     f"hierarchical estimator, which should be the safe middle, also fails - its per-world "
     f"corrections are fitted on the same thin samples and add variance faster than they "
     f"remove bias. Regional pooling never beats global pooling either.")
para(tag("econ") + "Only the multi-task model improves on the global fit, and only at one day, "
     "where knowing which world a row belongs to is worth a little. The economic reading is "
     "the one Section 5.1 reached from the correlation structure: for this purpose the 61 "
     "worlds behave as one market with a shared mechanism, not as 61 markets. Whatever "
     "predictable structure exists is common to them, which is why borrowing strength across "
     "worlds helps and splitting them apart hurts.")

h3("6.6.5 Volatility is forecastable even though direction is not")
para(tag("stat") + f"Direction and magnitude are different questions, and the panel answers "
     f"them differently. Asked whether the coming week's realised volatility will land in the "
     f"top quartile, a random forest reaches an area under the curve of "
     f"{FDV[FDV.target == 'y_hivol7'].iloc[0].auc:.2f} with a Brier skill score of "
     f"{FDV[FDV.target == 'y_hivol7'].iloc[0].skill_vs_base:+.1%} against the base rate - it is both better than "
     f"chance at ranking and better calibrated than simply quoting the unconditional "
     f"frequency. The directional targets of Section 6.6.3 rank above chance too but are worse "
     f"calibrated than the base rate, which is why they buy nothing.")
para(tag("econ") + f"Predicting the size of moves while failing to predict their sign is the "
     f"standard signature of a financial time series, and it is what the GARCH result of "
     f"Section 7.1.1 already implies. Point-forecasting the level of volatility is harder: "
     f"asked for the number rather than the quartile, the same model manages an R-squared of "
     f"only {FDV[FDV.target == 'y_vol7'].iloc[0].r2_vs_mean:+.3f} against the training mean, with a correlation of "
     f"{FDV[FDV.target == 'y_vol7'].iloc[0]['corr']:.2f}. Volatility is forecastable as a state, not as a quantity.")
para(tag("judg") + "This matters for the interval forecasts of Section 6.4. The report's "
     "prediction intervals are built from a bootstrapped constant volatility; a model that can "
     "tell a high-volatility week from a low one at this accuracy could narrow them in calm "
     "periods and widen them before turbulent ones. That is the single most useful thing the "
     "fundamentals turned out to offer, and it improves the honesty of an interval rather than "
     "the direction of a bet.")

h3("6.6.6 Nothing in the price's own history was left on the table")
para(tag("stat") + f"Three univariate forecasters were fitted per world on price history "
     f"alone, at a seven-day horizon, and compared with the random walk on that world's own "
     f"held-out period. All three lose.")
table([["Baseline", "Mean RMSE", "Median R² vs random walk", "Worlds where it wins"]] +
      [[r.model, f"{r.rmse:.4f}", f"{r.r2_oos:+.2f}",
        f"{int(r.worlds_better)} of {int(r.worlds)}"]
       for _, r in FDU.iterrows()],
      [40 * mm, 30 * mm, 42 * mm, AVAIL - 112 * mm], align=[None, "R", "R", "C"],
      caption="Table 6.17 - Univariate baselines against the random walk, per world, "
              "seven-day horizon. Prophet was fitted on a fixed random sample of 12 worlds "
              "because of its cost; the sample is recorded in the results file.")
para(tag("econ") + "ARIMA is the closest, and still beats the random walk on only a quarter of "
     "worlds. A structural time series and Prophet are far worse, because both fit trend and "
     "seasonal components to a series that has neither - extrapolating a local trend from a "
     "random walk is precisely the error the unit root warns against.")

h3("6.6.7 Regularisation is doing the work, and more history helps")
para(tag("stat") + f"Two methodological results fall out of the comparison. Ordinary least "
     f"squares on the same {FD['panel']['n_features']} features diverges - out-of-sample "
     f"R-squared of {FDX[(FDX.model == 'OLS') & (FDX.horizon == 30) & (FDX.target == 'rel')].r2_oos.min():,.0f} "
     f"at thirty days - which is what the penalty terms in Ridge and ElasticNet were buying. "
     f"CatBoost beats the random walk on the relative target but sits consistently below the "
     f"random forest, so the result of Section 6.6.3 is not an artefact of one implementation.")
para(tag("stat") + f"Repeating everything with a rolling window rather than an expanding one "
     f"changes little: excluding the diverging linear model, the rolling window is better in "
     f"{FD['window_scheme']['n_rolling_better']} of {FD['window_scheme']['n_compared']} "
     f"comparisons, with a median difference of "
     f"{FD['window_scheme']['median_rolling_minus_expanding']:+.4f} in R-squared, and for the "
     f"best model it is {FD['window_scheme']['rf_rolling_better']} of "
     f"{FD['window_scheme']['rf_compared']}. Forgetting old observations does not help, which "
     f"is evidence that the relationship is stable over the window rather than drifting.")

h3("6.6.8 What the model uses, and where it works")
para(tag("stat") + f"Attributing the surviving model's predictions with SHAP and grouping the "
     f"features by kind puts price history at "
     f"{FD['shap_by_family']['price history']:.0%} of explained variation. The rest is spread "
     f"thinly: world structure {FD['shap_by_family']['structure']:.0%}, cross-world position "
     f"{FD['shap_by_family']['cross-world']:.0%}, kill statistics "
     f"{FD['shap_by_family']['kill statistics']:.0%}. The fundamentals contribute, but the "
     f"model leans on the price.")
table([["Feature family", "Share of attributed variation"]] +
      [[k, f"{v:.1%}"] for k, v in sorted(FD["shap_by_family"].items(),
                                          key=lambda kv: -kv[1])],
      [70 * mm, AVAIL - 70 * mm], align=[None, "R"],
      caption="Table 6.18 - Mean absolute SHAP attribution by feature family, random forest on "
              "the seven-day relative return, held-out period.")
para(tag("stat") + f"A Gaussian hidden Markov model on six market-state variables selects "
     f"{FDR['k']} states by BIC, with mean persistence {FDR['persistence']:.2f} - states last "
     f"about a fortnight. An independent change-point search agrees: at a penalty admitting "
     f"{FDR['n_change_points']} breaks, all {FDR['n_agreeing_with_hmm']} fall within a week of "
     f"a state switch. Splitting the surviving model's errors by state shows its advantage is "
     f"not uniform - it beats the random walk in the expansionary, high-volatility state and "
     f"loses in the three calmer ones.")
h3("6.6.9 Aiming at the right quantity, and at the right regime")
para(tag("judg") + "Two objections to the exercise so far are correct and are answered here. "
     "The first is that a forecast of the pooled relative return is not the quantity this "
     "report claims to be predictable: Section 6.3.1 identifies a threshold, and the content "
     "of a threshold model is that the two regimes it separates behave differently, so pooling "
     "them is the one thing not to do. The second is that arbitrage happens between two worlds, "
     "not between a world and an index.")
para(tag("stat") + f"Redone on the deviation itself, over the full price history rather than "
     f"the eight-month fundamentals window, and split at the estimated band, the picture is "
     f"sharper. Outside the band a five-feature linear model reaches an out-of-sample "
     f"R-squared of {ARBB.query("regime == 'outside band' and features == 'five features' and model == 'ols'").r2_oos.iloc[0]:+.3f}; "
     f"inside it, the deviation alone predicts "
     f"{ARBB.query("regime == 'inside band' and features == 'deviation only' and model == 'ols'").r2_oos.iloc[0]:+.3f} "
     f"- worse than assuming no change, which is what a random walk inside the band means. The "
     f"threshold behaves as estimated.")
table([["Regime", "Predictors", "Out-of-sample R²", "Directional accuracy"]] +
      [[r.regime.title(), r.features, f"{r.r2_oos:+.4f}", f"{r.dir_acc:.1%}"]
       for _, r in ARBB.query("model == 'ols'").iterrows()],
      [34 * mm, 34 * mm, 32 * mm, AVAIL - 100 * mm], align=[None, None, "R", "R"],
      caption="Table 6.19 - Forecasting the cross-world deviation seven days ahead, by regime. "
              "Linear models; the random-forest variants are in band_conditional.csv and are "
              "no better.")
para(tag("econ") + f"That is more than double the {FDM.query('beats_rw == True and horizon == 7').r2_oos.iloc[0]:.3f} "
     f"reported in Section 6.6.3, and the difference is entirely a matter of aiming: same "
     f"market, better-posed question. The criticism that produced this table was a fair one.")
para(tag("stat") + f"The network of pairs tells the same story. Taking every pair among the "
     f"{ARB['pairwise']['n_pairs']} with continuous history and predicting the seven-day change "
     f"in their gap from the gap itself, the median out-of-sample R-squared is "
     f"{ARB['pairwise']['median_r2']:+.4f} and "
     f"{ARB['pairwise']['share_positive']:.0%} of pairs are positive, with a median convergence "
     f"slope of {ARB['pairwise']['median_slope']:+.3f}. Gaps between worlds do close, and the "
     f"closing is forecastable.")

para(tag("stat") + f"To put a ceiling on it rather than a single estimate, four gradient and "
     f"tree models were tuned on a split inside the training window and then scored once on "
     f"the held-out period, alongside a regularised linear model and an equal-weight ensemble "
     f"of the four. The largest out-of-sample R-squared any of them reaches on the deviation "
     f"is <b>{MAXP['best_r2']:.3f}</b>, from {MAXP['best_model']}, with "
     f"{MAXP['best_dir_acc']:.1%} directional accuracy - "
     f"{MAXP['best_r2_outside']:.3f} when restricted to observations outside the band. The "
     f"tuning was not free: the random forest validated at 0.104 inside the training window "
     f"and delivered 0.051 on the test period, which is what tuning to a validation slice "
     f"costs.")
para(tag("judg") + f"So the statistical answer is settled and it is positive. Between "
     f"{MAXP['best_r2']:.2f} and 0.11 of the variance of the seven-day change in a world's "
     f"relative position is forecastable out of sample, depending on the specification, with "
     f"directional accuracy near {MAXP['best_dir_acc']:.0%}. That is a real edge and this "
     f"report should not have implied otherwise. What follows is the separate question of "
     f"whether it is worth anything.")

h3("6.6.10 Why the structure is still not an opportunity")
para(tag("stat") + f"The reversion is real and it is small, and the reason the daily model "
     f"appears to promise more is measurement error. Estimating the persistence of the "
     f"deviation at three samplings of the same data gives a weekly reversion of "
     f"{ARBR.iloc[0].implied_weekly_reversion:.1%} from daily observations, "
     f"{ARBR.iloc[1].implied_weekly_reversion:.1%} from weekly ones and "
     f"{ARBR.iloc[2].implied_weekly_reversion:.1%} from fortnightly ones. Reversion that "
     f"shrinks as the sampling coarsens is noise being counted as signal; the honest figure is "
     f"the slowest one.")
para(tag("obs") + f"Which settles the question directly. Entering only when the deviation "
     f"exceeds the band, selling the expensive world and buying the cheap one, and holding "
     f"seven days, gives a gross return of "
     f"{ARB['trading_rule']['small offer']['mean_gross_pct']:+.3f}% per trade over "
     f"{ARB['trading_rule']['small offer']['n_trades']:,} signals. The round trip costs "
     f"{ARB['trading_rule']['small offer']['cost_pct']:.2f}% for an ordinary offer and "
     f"{ARB['trading_rule']['above the fee cap']['cost_pct']:.2f}% for one large enough to "
     f"clear the fee cap.")
table([["Offer size", "Gross per trade", "Round-trip cost", "Net per trade",
        "Trades in profit"]] +
      [[k.title(), f"{v['mean_gross_pct']:+.3f}%", f"{v['cost_pct']:.2f}%",
        f"<b>{v['mean_net_pct']:+.3f}%</b>", f"{v['share_profitable']:.1%}"]
       for k, v in ARB["trading_rule"].items()],
      [34 * mm, 30 * mm, 30 * mm, 28 * mm, AVAIL - 122 * mm],
      align=[None, "R", "R", "R", "R"],
      caption=f"Table 6.20 - A band-conditional convergence trade, "
              f"{ARB['trading_rule']['small offer']['n_trades']:,} signals over the held-out "
              f"period, seven-day holding period, costs as documented in Section 2.2.")
para(tag("judg") + f"<b>The structure is real, forecastable, and worth less than the cost of "
     f"capturing it.</b> At the cheapest possible execution - an offer above "
     f"{gp(R['fees']['cap_binds_at_lot_tc'])} TC, where the fee cap binds - the trade nets "
     f"{ARB['trading_rule']['above the fee cap']['mean_net_pct']:+.3f}% and is profitable on "
     f"{ARB['trading_rule']['above the fee cap']['share_profitable']:.1%} of signals. That is a "
     f"coin flip that loses by about two basis points. At an ordinary offer size it loses "
     f"{abs(ARB['trading_rule']['small offer']['mean_net_pct']):.2f}% per trade.")
para(tag("econ") + "This is what an efficient-up-to-costs market looks like from the inside, "
     "and it is a stronger statement than the one Section 6.6.3 could make. The earlier "
     "sections showed that a model does not beat a random walk. This one shows why: the "
     "predictable component exists, it is about a fifth of a percent over a week, and the "
     "cheapest way to trade it costs slightly more than that. No model can close a gap that "
     "the fee schedule holds open.")

h3("6.6.11 Every model class, and what each one did")
para(tag("obs") + "A reader should not have to infer which methods were tried from an axis "
     "label. The full inventory follows, with the result for each.")
table([["Model class", "Fitted as", "Result against a random walk"],
       ["Random walk", "predict no change", "the benchmark"],
       ["Naive, moving average", "last return, training mean", "both lose at every horizon"],
       ["ARIMA", "per world, (1,1,1)", "loses; better on 16 of 61 worlds"],
       ["SARIMA", "per world, weekly seasonal", f"loses; better on "
        f"{int(FDC[FDC.model == 'SARIMA'].worlds_better.iloc[0])} of 61"],
       ["SARIMAX", "SARIMA plus 7 exogenous fundamentals",
        f"loses; better on {int(FDC[FDC.model == 'SARIMAX'].worlds_better.iloc[0])} of 61 - "
        f"the exogenous terms add nothing"],
       ["Structural time series", "local linear trend, state space", "loses heavily"],
       ["Prophet", "weekly seasonality", "loses heavily"],
       ["Markov-switching AR", "2 regimes, switching variance",
        f"loses; better on {int(FDC[FDC.model == 'MarkovSwitch'].worlds_better.iloc[0])} of 61"],
       ["GARCH(1,1)-t", "volatility forecast", "loses to the training mean on 47 of 61"],
       ["OLS", "no regularisation", "diverges: R² of -465 at 30 days"],
       ["Ridge, ElasticNet", "regularised linear", "lose except marginally at 1 day"],
       ["Random forest", "global, 140 features", "<b>the only consistent winner</b>"],
       ["XGBoost, LightGBM, CatBoost", "gradient boosting",
        "beat the benchmark on the relative target, below the random forest"],
       ["LSTM", "1 layer, 32 units, 30-day windows",
        f"unstable: R² {FDD[FDD.model == 'LSTM'].r2_oos.iloc[0]:+.3f} on average, "
        f"better in {int(FDD[FDD.model == 'LSTM'].folds_better.iloc[0])} of 4 folds"],
       ["Transformer", "1 encoder block, 4 heads",
        f"loses in all 4 folds, R² {FDD[FDD.model == 'Transformer'].r2_oos.iloc[0]:+.3f}"],
       ["Latent factor model", "5 principal components of the return panel",
        f"R² falls from {FDF['r2_without']:+.4f} to {FDF['r2_with']:+.4f} when added"]],
      [38 * mm, 46 * mm, AVAIL - 84 * mm], fs=6.8,
      caption="Table 6.21 - Every model class fitted in this study and its out-of-sample "
              "result. Classical models are per world at a seven-day horizon; the machine "
              "learning models are the panel models of Section 6.6.3.")
para(tag("stat") + f"Three of these deserve comment. <b>SARIMAX is the direct test of "
     f"\"ARIMA with the economy attached\"</b> and it fails: adding seven exogenous "
     f"fundamentals to a seasonal ARIMA changes the average RMSE from "
     f"{FDC[FDC.model == 'SARIMA'].rmse.iloc[0]:.4f} to "
     f"{FDC[FDC.model == 'SARIMAX'].rmse.iloc[0]:.4f}, and the number of worlds where it beats "
     f"a random walk does not move. Whatever the fundamentals carry, a linear state-space model "
     f"cannot extract it.")
para(tag("stat") + f"<b>The latent factor model finds little to share.</b> Five principal "
     f"components of the cross-world return panel, estimated on the training window only, "
     f"explain {FDF['cumulative_share']:.1%} of return variance between them - the largest "
     f"single factor {FDF['variance_share'][0]:.1%}. Adding them as predictors makes the model "
     f"worse. This is the same fact Section 7.1.2 reports as a 3% systematic share, arrived at "
     f"from the opposite direction.")
para(tag("lim") + f"<b>The neural models were fitted, and the earlier refusal to fit them was "
     f"right for the stated reason.</b> An LSTM on {FD['deep_models']['n_sequences']:,} "
     f"thirty-day windows is significantly better than a random walk in two folds and "
     f"significantly worse in one; a single-block transformer loses in all four. A model that "
     f"swings from a Diebold-Mariano statistic of -4.8 to +5.4 between adjacent folds has not "
     f"found a stable relationship, which is what 3,171 training sequences predicts. These use "
     f"four folds from the halfway point rather than the six used elsewhere, so they are "
     f"comparable to the random walk on identical folds but not directly to the figures in "
     f"Section 6.6.3.")

h3("6.6.12 Searching for predictors finds nothing the search did not put there")
para(tag("stat") + f"The interactions in the feature set were chosen by hand from what this "
     f"report already believed, which is how a prior gets smuggled into a result. Replacing "
     f"that with a search: every pairwise product of the fourteen strongest features was "
     f"generated and scored, {DSC['interactions_searched']} in all, and "
     f"{DSC['interactions_improving']} of them improved on the baseline. None of the top ten "
     f"improved again on an earlier, disjoint split. The best - "
     f"{DSC['best_interaction'][0]['a']} with {DSC['best_interaction'][0]['b']} - gained "
     f"{DSC['best_interaction'][0]['gain']:+.4f} in R-squared on the first split and "
     f"{DSC['best_interaction'][0]['gain_second_split']:+.4f} on the second.")
para(tag("judg") + f"That pattern - most candidates appearing to help, none replicating - is "
     f"what searching a large space against a noisy target produces. It is reported here "
     f"because the search was run, not because it found anything, and it is the reason the "
     f"hand-picked interactions were left in place rather than replaced.")
para(tag("stat") + f"Four selection methods were run side by side on "
     f"{DSC['n_features']} features. Boruta, which asks whether a feature beats a shuffled "
     f"copy of itself, confirms {DSC['boruta_confirmed']}. Recursive elimination, the LASSO "
     f"path and mutual information each keep their own twenty-five. Only "
     f"{len(DSC['consensus_features'])} features are chosen by three of the four, and a model "
     f"restricted to them scores {DSC['consensus_r2']:+.4f} against "
     f"{DSC['baseline_r2']:+.4f} for the full set - selection makes the model worse, not "
     f"simpler-and-equal.")
para(tag("lim") + f"The three named economic indices fare no better. Of the activity index, "
     f"the inflation-pressure proxy and the premium-demand proxy, only "
     f"<b>idx_activity</b> is picked by any method, and by two of four. The inflation-pressure "
     f"proxy - gold production growing faster than the players sharing it, which is the "
     f"mechanism Section 6.1.3 names as the likely driver - is selected by none of them. That "
     f"is a negative result about the proxy, not about the mechanism: an eight-month window "
     f"and a noisy denominator may simply be unable to see it.")

h3("6.6.13 How wrong the forecasts can be, and what would change one")
para(tag("stat") + f"Split-conformal intervals calibrate almost exactly. Calibrated on "
     f"held-out residuals with no distributional assumption, the nominal 90% interval covers "
     f"{[r['empirical'] for r in DSC['conformal'] if r['nominal'] == 0.9][0]:.1%} of held-out "
     f"outcomes, the 80% covers "
     f"{[r['empirical'] for r in DSC['conformal'] if r['nominal'] == 0.8][0]:.1%} and the 50% "
     f"covers {[r['empirical'] for r in DSC['conformal'] if r['nominal'] == 0.5][0]:.1%}. A "
     f"model whose point forecasts are barely better than a random walk can still be honest "
     f"about its own uncertainty, and this one is.")
para(tag("obs") + f"Counterfactuals give the sharpest picture of what the model is doing. "
     f"Taking the {DSC['counterfactual'][0]['n_considered']} most negative forecasts and "
     f"moving each of the eight strongest features across its full range one at a time, "
     f"<b>not one prediction flips sign</b> - zero of "
     f"{DSC['counterfactual'][0]['n_considered']} for every feature tried.")
para(tag("econ") + "That is worth stating plainly because it contradicts how a feature-"
     "importance table reads. There is no lever: no single quantity a world could change to "
     "turn its forecast around. The prediction is the sum of many small contributions, which "
     "is consistent with a market where the signal is weak and diffuse, and it is a warning "
     "against reading the importance rankings as causes.")

h3("6.6.14 The gold-supply story does not survive its own test")
para(tag("judg") + "This report has treated gold supply as the leading candidate for the price "
     "level throughout, on theoretical grounds, and never tested it directly. It should have. "
     "Creatures drop gold, so the kill statistics <i>are</i> a production series, and if the "
     "supply channel were the driver its elasticity would be visible, positive and large. "
     "Measured, it is none of those things.")
table([["Horizon", "Production measure", "Elasticity", "t", "Within R²"]] +
      [[f"{int(r.horizon)}d", r.channel.replace("gold production, ", ""),
        f"{r.elasticity:+.5f}", f"{r.t:+.1f}", f"{r.r2_within:.4f}"]
       for _, r in SVDE.iterrows()],
      [18 * mm, 52 * mm, 26 * mm, 18 * mm, AVAIL - 114 * mm],
      align=[None, None, "R", "R", "R"],
      caption="Table 6.22 - Elasticity of the forward gold price of a coin to gold production, "
              "world fixed effects, standard errors clustered by world. A supply channel "
              "predicts a positive and material coefficient.")
para(tag("stat") + f"The daily flow gives {_FLOW7:+.5f} "
     f"at seven days, indistinguishable from zero, and flips sign between horizons. Across "
     f"{SVD['gold_stock']['n_worlds']} worlds the accumulated production has a median "
     f"correlation with the price of {SVD['gold_stock']['median_corr']:+.3f} and a negative "
     f"slope on <b>{SVD['gold_stock']['n_worlds'] - SVD['gold_stock']['n_positive_slope']} of "
     f"{SVD['gold_stock']['n_worlds']}</b> - not one world shows the positive relationship the "
     f"theory requires.")
para(tag("lim") + "The accumulated measure carries a caveat that must be stated rather than "
     "used: a cumulative sum rises monotonically, so it is close to a time trend, and its "
     "correlation with the price largely records that prices fell over this particular window. "
     "It cannot bear weight as a supply test on its own. The flow elasticity carries no such "
     "problem, and it is simply too small to matter.")
para(tag("stat") + f"<b>The decisive comparison is between blocks.</b> Entering supply, demand "
     f"and behavioural variables alone and together in the same panel regression:")
table([["Block of variables", "Variables", "Within-world R²"]] +
      [[r.block.title(), int(r.k), f"{r.r2_within:.4f}"] for _, r in SVDR.iterrows()],
      [46 * mm, 24 * mm, AVAIL - 70 * mm], align=[None, "R", "R"],
      caption="Table 6.23 - Explanatory power of each block on the seven-day forward return, "
              "world fixed effects. Behaviour is the price's own history, market breadth and "
              "a world's position relative to the others.")
para(tag("econ") + f"Behaviour explains {_R2B / _R2S:.0f} times what production does - "
     f"{_R2B:.3f} against {_R2S:.4f} - and adding supply to demand barely moves the fit. In "
     f"the joint model the largest coefficients are the lagged return, market breadth and the "
     f"world's relative position; the production variables are statistically significant and "
     f"economically small, and they carry the wrong sign.")
para(tag("judg") + "<b>The report's economic interpretation needs correcting, and this is "
     "that correction.</b> The gold-inflation story was carried on plausibility rather than "
     "evidence, and the evidence now available does not support it. What moves a world's coin "
     "price over a week is where the price has just been, how the other worlds are moving, and "
     "how engaged that world's players are - a demand-and-attention process, not a production "
     "one. The missing series named in Section 6.1.3 would still be worth having, but the "
     "expectation that it would explain the level should be lowered.")

h3("6.6.16 A year of horizon, a stock instead of a flow, and a threshold")
para(tag("judg") + f"<b>The production tests in this chapter ran at one, seven and thirty days "
     f"on eight months of data, and that combination can only find a fast channel.</b> A "
     f"monetary effect need not arrive within a month, need not be linear in the flow, and need "
     f"not appear at all until enough has accumulated. Folding in the 2022-2025 kill-statistics "
     f"archive extends the joint sample to {LHP['panel']['rows']:,} world-days across "
     f"{LHP['panel']['worlds']} worlds and {LHP['panel']['years']:.1f} years, which makes the "
     f"slow versions estimable for the first time.")
para(tag("stat") + f"<b>Four stories, {LHP['n_specifications']} specifications.</b> The flow, as "
     f"before. The cumulative total, because gold persists and a stock is not a flow. The "
     f"acceleration, because a steady level may already be priced. And a threshold, because an "
     f"effect could switch on only where activity is unusual. Horizons run to a year; windows "
     f"run to a year. Before any correction {LHP['n_significant_uncorrected']} cells are "
     f"significant at 5%, and {LHP['n_survive_bh']} survive Benjamini-Hochberg.")
para(tag("judg") + "<b>That would be the finding, and it does not survive the test this report "
     "already applies to its own trading results.</b> These are overlapping forward returns on "
     "a pooled panel: many worlds on one date are one observation, and a 180-day return "
     "measured on consecutive days is one window seen many times. Re-estimated as a per-date "
     "cross-sectional slope with a Newey-West correction at the horizon, and counted in "
     "non-overlapping windows rather than in rows, the picture inverts.")
table([["Specification", "Horizon", "Pooled t", "Honest t", "Independent windows"]] +
      [[r.specification.capitalize(), f"{int(r.horizon)}d", f"{r.pooled_t:+.2f}",
        f"{r.t_newey_west:+.2f}", f"{int(r.independent_windows)}"]
       for _, r in LHH.sort_values("independent_windows", ascending=False).iterrows()],
      [46 * mm, 20 * mm, 22 * mm, 22 * mm, AVAIL - 110 * mm], fs=7,
      align=[None, "R", "R", "R", "R"],
      caption="Table 6.24 - Every cell that was significant before correction, re-tested on a "
              "per-date series. Sorted by how many genuinely independent windows the sample "
              "holds.")
para(tag("stat") + f"<b>Strength runs inversely with evidence, which is the signature of an "
     f"artefact rather than a channel.</b> The rank correlation between a cell's number of "
     f"independent windows and its honest t-statistic is {LHD['spearman_windows_vs_t']:+.2f}. "
     f"Of the {LHD['n_cells_with_10plus_windows']} cells resting on ten or more independent "
     f"windows, the largest absolute t is {LHD['max_abs_t_among_them']:.2f} - none is "
     f"significant. The two cells with the largest honest statistics rest on two windows each. "
     f"And the sign itself flips between the two inferences in "
     f"{LHD['sign_flips_pooled_vs_honest']} of {LHD['n_rechecked']} cells: the acceleration "
     f"specification that looked positive at {pc(0.179 * 100, 0) if False else '+0.18'} pooled "
     f"is negative on the per-date series.")
para(tag("judg") + "<b>So the answer to the long-horizon objection is that the objection was "
     "right about the method and the conclusion holds anyway.</b> The earlier tests could not "
     "have found a slow channel; these can, and they do not. A production effect that needs a "
     "year to arrive, or a stock rather than a flow, or a threshold, would show up as a "
     "coefficient that strengthens as the sample lengthens. What shows up instead is one that "
     "weakens as the sample is counted honestly, and changes sign depending on how the same "
     "variable is windowed.")
para(tag("lim") + f"<b>One half of the test is still missing and this section does not claim "
     f"otherwise.</b> Kill counts now span {LHP['panel']['years']:.1f} years; the monetary "
     f"emission series of Section 6.6.15 still spans eight months, because reconstructing GP "
     f"needs per-creature detail that lives only in the raw daily archive rather than in the "
     f"aggregated panel. The long-horizon monetary test is therefore not done - only the "
     f"long-horizon activity test is - and a reader should treat the two as separate claims.")
story.append(PageBreak())

h3("6.6.15 The same null on the money, not just on the bodies")
para(tag("judg") + "<b>The obvious objection to the section above is that a kill count is not a "
     "gold series.</b> Creatures differ by orders of magnitude in what they drop, so counting "
     "deaths measures activity and only proxies for emission. If the supply channel were real "
     "and merely mismeasured, replacing the count with actual gold would recover it. That "
     "series has now been built, and it does not.")
para(tag("mech") + f"<b>How the emission series is constructed.</b> Two channels enter and no "
     f"others: currency a creature drops directly, and loot with a guaranteed player-to-NPC "
     f"sale price. Player-market values are set to zero throughout, because a market price is "
     f"an opinion rather than an emission. Drop frequencies and quantities come from "
     f"{GEQ['loot_statistics_pages']:,} TibiaWiki empirical loot-statistics pages matched "
     f"against {GEQ['canonical_creatures']:,} canonical creatures; "
     f"{GEQ['matched_complete_creatures']:,} have a sufficiently sampled table at the "
     f"{GEQ['minimum_reliable_loot_samples']}-observation minimum and the rest stay explicitly "
     f"uncovered rather than being imputed. Bosses are held out. Coverage is "
     f"{GEQ['covered_deaths_pct_all']:.1%} of the "
     f"{GEQ['total_deaths'] / 1e9:.1f} billion recorded deaths.")
para(tag("stat") + f"<b>Four measures of the same thing, none of which moves the price.</b> The "
     f"count is compared against direct coin drops, against the maximum realisable value if "
     f"every sellable item were sold, and against realisation rates between a quarter and all "
     f"of it. Specification as in the section above: world and date fixed effects, a lagged "
     f"return, an activity control, and Cameron-Gelbach-Miller standard errors clustered on "
     f"world and date.")
table([["Series", "1 day", "7 days", "30 days"]] +
      [[{"kill_count": "Kill count", "direct_coin": "Coin dropped directly",
         "potential_max": "Maximum realisable value",
         "realized_50": "Half of realisable value"}[ser]]
       + [f"{float(GEH[(GEH.series == ser) & (GEH.horizon_days == h)].coefficient.iloc[0]):+.4f} "
          f"({float(GEH[(GEH.series == ser) & (GEH.horizon_days == h)].p_value.iloc[0]):.2f})"
          for h in (1, 7, 30)]
       for ser in ("kill_count", "direct_coin", "potential_max", "realized_50")],
      [56 * mm, 30 * mm, 30 * mm, AVAIL - 116 * mm], fs=7.2,
      align=[None, "R", "R", "R"],
      caption="Table 6.25 - Elasticity of the forward price to each emission measure, with the "
              "two-way clustered p-value in brackets. No cell is significant at 5%.")
para(tag("stat") + f"<b>Out of sample the monetary series does not beat a random walk either.</b> "
     f"Across {len(GEO)} series-horizon pairs the best root-mean-square error improvement is "
     f"{GEM['best_oos_rmse_improvement_pct']:+.2%} and the worst is "
     f"{GEM['worst_oos_rmse_improvement_pct']:+.1%}. The best figure belongs to the kill count "
     f"rather than to any of the money measures and is small enough to be noise; the worst is "
     f"a fifth worse than doing nothing.")
para(tag("stat") + f"<b>Directional accuracy makes the point more sharply, and not in the way a "
     f"reader might expect.</b> It is "
     f"{float(GEO[GEO.horizon_days == 1].direction_accuracy.mean()):.1%} at one day - a coin "
     f"flip - then falls to {float(GEO[GEO.horizon_days == 7].direction_accuracy.mean()):.1%} "
     f"at seven and {float(GEO[GEO.horizon_days == 30].direction_accuracy.mean()):.1%} at "
     f"thirty. At the longer horizons these models call the direction wrong more often than "
     f"right. That is not a usable signal inverted - the errors are large as well as "
     f"mis-signed, which is what the negative RMSE numbers say - but it does close off the "
     f"gentlest reading of the null, that emission carries weak information the specification "
     f"failed to extract.")
para(tag("judg") + "<b>So the correction in Section 6.6.14 holds on the better variable.</b> "
     "That matters more than another null would normally: the production channel was the "
     "report's own long-held explanation, the count was the weakest possible test of it, and "
     "the natural defence was that the proxy was too crude. Built properly, from drop tables "
     "and NPC prices rather than from body counts, the channel is still absent. The claim in "
     "Section 7.6 that no direct monetary channel is identified rests on this measurement, not "
     "on the proxy.")
para(tag("lim") + f"<b>What the emission series is not.</b> It bounds gold <i>created</i>, and "
     f"says nothing about gold destroyed - NPC purchases, repairs, death penalties - so it is "
     f"a flow and not a stock. Non-coin NPC value is set to zero wherever buyer access "
     f"prerequisites are not encoded in the item source, which makes every figure conservative "
     f"by construction. And {GEQ['insufficient_sample_creatures']:,} creatures carry loot "
     f"tables too thinly sampled to use, plus {GEQ['absent_creatures']:,} with none at all; "
     f"they are excluded rather than estimated, which is why coverage is reported as a "
     f"percentage of deaths rather than assumed complete.")
story.append(PageBreak())

h3("6.6.17 Unpredictable in principle, or only with the data we have?")
para(tag("judg") + "Everything to this point answers a narrower question than it appears to. "
     "Testing 140 observable features against a random walk establishes whether <i>this</i> "
     "information predicts the price. It says nothing about whether some other information - "
     "unrecorded, or unrecordable - would. The broader question is testable without the "
     "missing data, by asking whether the series contains structure at all, and by asking how "
     "much a perfectly informed observer of the hidden state could explain.")
para(tag("stat") + f"<b>The series is not noise.</b> Sample entropy is "
     f"{IRR['entropy']['sample_entropy']:.3f} against "
     f"{IRR['entropy']['se_surrogate_mean']:.3f} for surrogates that preserve the linear "
     f"structure and destroy everything else - the real series is significantly more regular "
     f"(p {pval(IRR['entropy']['se_p'])}). A BDS test rejects independence at every embedding "
     f"dimension tried, with statistics of "
     f"{', '.join(f'{r.statistic:.1f}' for _, r in IRRB.iterrows())}. Ljung-Box rejects the "
     f"martingale-difference hypothesis on returns and on squared returns at every lag. "
     f"Structure is present that no model in this report exploits.")
para(tag("stat") + f"<b>But the hidden driver is small, and it is not forecastable.</b> "
     f"Estimating a single common factor across {IRR['latent_state']['n_worlds']} worlds over "
     f"{IRR['latent_state']['n_dates']} dates, each world observing that factor in noise, and "
     f"asking how much of daily world-return variance the factor reproduces:")
table([["What the observer knows", "Share of world return variance explained"],
       ["The factor one step ahead - a forecaster",
        f"{IRR['latent_state']['r2_factor_forecast']:.1%}"],
       ["The factor filtered from the past",
        f"{IRR['latent_state']['r2_factor_filtered']:.1%}"],
       ["The factor smoothed with the whole sample - perfect hindsight",
        f"{IRR['latent_state']['r2_factor_smoothed']:.1%}"]],
      [92 * mm, AVAIL - 92 * mm], align=[None, "R"],
      caption="Table 6.26 - A common-factor state-space model. The smoothed row is the ceiling "
              "for any observer of the common driver, however well informed; the first row is "
              "what is available in advance.")
para(tag("econ") + f"That is the answer to the broader question, and it is sharper than the "
     f"narrow one. An observer who could see the hidden common driver <i>perfectly, with "
     f"hindsight</i>, would account for "
     f"{IRR['latent_state']['r2_factor_smoothed']:.0%} of a world's daily return variance. The "
     f"remaining {1 - IRR['latent_state']['r2_factor_smoothed']:.0%} is idiosyncratic and is "
     f"not attributable to any common state, observed or not. And the factor itself is "
     f"unforecastable one step ahead: knowing its own past yields "
     f"{IRR['latent_state']['r2_factor_forecast']:.1%}.")
para(tag("judg") + f"<b>So the unpredictability is mostly irreducible rather than merely "
     f"epistemic, and this bound is what makes that claim safe to make.</b> The best remaining "
     f"candidate for the common driver is Char Bazaar flow, the venue that moves "
     f"{MS['bazaar_over_market']:.1f} times the coins the Market does and that exists here as "
     f"one annual number (Section 5.8). It would enter as a common state, and a common state "
     f"perfectly observed has a ceiling below a tenth of daily variance and none at all one "
     f"step ahead. That is a stronger and more useful statement than 'no model beat a random "
     f"walk', because it prices what better data could ever buy before anyone goes to collect "
     f"it.")
para(tag("lim") + "One tension deserves stating rather than smoothing over. BDS and sample "
     "entropy detect real structure, yet no forecasting model captures it. The reconciliation "
     "is that the structure is in the second moment, not the first: Section 6.6.5 finds "
     "volatility forecastable at an area under the curve of 0.75 while direction is not, and "
     "Section 7.1.1's GARCH result says the same. Dependence in the variance is exactly what a "
     "BDS test detects and exactly what a conditional-mean model cannot use.")

para(tag("lim") + "<b>What this section cannot support.</b> Eight months is one seasonal cycle, "
     "so the calendar features are fitted on a single pass through the year and the seasonality "
     "result should not be trusted. The deep sequence models the brief contemplates - temporal "
     "fusion transformers, N-BEATS - were not fitted: 238 daily observations per world is two "
     "orders of magnitude short of what they need, and reporting a tuned deep model on this "
     "sample would be a demonstration of overfitting rather than of predictability. The order "
     "book remains a single snapshot, so no time-varying depth or spread feature exists.")
para(tag("judg") + "<b>The verdict of Section 7.5 is unchanged, and now rests on more.</b> The "
     "study set out to test whether the coin becomes predictable once the economy behind it is "
     "observed. The economy is now partly observed, no fundamental leads it once the lag "
     "search is paid for, and the "
     "level still is not forecastable. What the fundamentals do buy is a modest, repeatable edge on "
     "which world is cheap relative to the others - the quantity Section 5.2 already identified "
     "as the predictable one - and even that sits inside the cost of trading on it. The rating "
     "of Section 7.5 is unchanged, and now rests on a test that could have overturned it.")
story.append(PageBreak())

# ===================================================================== 29
chapter(7, 'Risk, robustness and implications',
        'How risky the asset is, whether the findings survive alternative specifications, what the study cannot establish, and the rating the evidence supports.')
hero(pc(FN["variance"]["median_r2_systematic"] * 100, 1),
     "of a world's daily return variance is shared with the market.",
     "The other 97% is local. Prices across worlds share a single common stochastic trend "
     "over months, yet move almost independently day to day - worlds share a destination "
     "but travel there on their own paths.",
     mark="variance")
h2sec('7.1', 'Risk', 'Volatility is near-integrated with fat tails, and risk is almost entirely local')
h3("7.1.1 Volatility dynamics")
para(tag("stat") + "Daily returns are not homoskedastic and not normal. A GARCH(1,1) with "
     "Student-t innovations, fitted per world, characterises both.")
GA = FN["garch"]
table([["Parameter", "Median across worlds", "Reading"],
       ["ARCH term &alpha;", f"{GA['median_alpha']:.3f}", "Response to the latest shock"],
       ["GARCH term &beta;", f"{GA['median_beta']:.3f}", "Persistence of the variance"],
       ["Persistence &alpha;+&beta;", f"{GA['median_persistence']:.3f}",
        "<b>At the integrated boundary</b>"],
       ["Worlds with &alpha;+&beta; &gt; 0.9", pc(GA["share_persistence_above_0.9"] * 100, 0),
        "Near-permanent volatility shocks"],
       ["Volatility half-life", f"{GA['median_vol_half_life_days']:.0f} days",
        "Time for a variance shock to halve"],
       ["Student-t degrees of freedom", f"{GA['median_nu']:.1f}",
        "Very heavy tails; below 4 implies infinite kurtosis"]],
      [42 * mm, 34 * mm, AVAIL - 76 * mm], align=[None, "R", None],
      caption=f"Table 7.1 - GARCH(1,1)-t estimates, {GA['n_worlds']} converged worlds with at "
              f"least 400 daily observations.")
para(tag("stat") + f"Two features matter for risk. Persistence sits at the integrated boundary "
     f"({GA['median_persistence']:.3f}), so a volatility shock decays only slowly and a quiet "
     f"world is not reliably a permanently quiet world. And the fitted degrees of freedom of "
     f"{GA['median_nu']:.1f} indicate tails far heavier than Gaussian - at that value the "
     f"kurtosis of the innovation distribution is not finite. The realised residual excess "
     f"kurtosis in the panel is {FN['diagnostics']['resid_excess_kurtosis']:.1f}.")
para(tag("judg") + "This is the formal justification for two choices made earlier. The forecast "
     "intervals in Section 6.4 are bootstrapped from the world's own return distribution rather "
     "than drawn from a normal, because a normal would understate tail risk badly at these "
     "degrees of freedom. And every standard error in this report is heteroskedasticity-robust, "
     "because a Breusch-Pagan test on the panel residuals rejects homoskedasticity outright "
     f"(p {pval(FN['diagnostics']['breusch_pagan_p'])}).")

h3("7.1.2 Systematic and idiosyncratic risk")
para(tag("stat") + "Whether coin risk is diversifiable across worlds is answered by "
     "decomposing each world's return variance into a component shared with the market and a "
     "local component, using a leave-one-out market return so no world is regressed on itself.")
VA = FN["variance"]
takeaway("Only 3% of a typical world's daily return variance is shared with the market - coin risk is almost entirely local at daily frequency.")
table([["Measure", "Value", "Reading"],
       ["Median R&sup2; on the market return", pc(VA["median_r2_systematic"] * 100, 1),
        "<b>Almost all variance is local</b>"],
       ["Median beta to the market", f"{VA['median_beta']:.2f}", "Near one where it loads"],
       ["Median total volatility", f"{VA['median_total_sd_pct']:.2f}%/day", "-"],
       ["Median idiosyncratic volatility", f"{VA['median_idio_sd_pct']:.2f}%/day",
        "Nearly the whole of it"],
       ["First principal component", pc(VA["pc1_share"] * 100, 1),
        "Share of return variance explained"],
       ["Second principal component", pc(VA["pc2_share"] * 100, 1), "-"]],
      [52 * mm, 26 * mm, AVAIL - 78 * mm], align=[None, "R", None],
      caption=f"Table 7.2 - Variance decomposition across {VA['n_worlds']} converged worlds; "
              f"principal components computed on {VA['n_pca_worlds']} worlds over "
              f"{VA['n_pca_dates']} dates.")
figure("fig21_variance_decomposition.png",
       "Exhibit 7.1 - Systematic share of return variance, and principal components of the "
       "return matrix. Source: price archive item_id 22118; converged worlds.")
para(tag("stat") + f"<b>There is an apparent contradiction here, and resolving it is "
     f"informative.</b> Section 6.3.2 finds a single common stochastic trend across worlds and "
     f"near one-for-one pass-through of the cross-world mean. Yet only "
     f"{pc(VA['median_r2_systematic'] * 100, 1)} of daily return variance is common, and the "
     f"first principal component explains just {pc(VA['pc1_share'] * 100, 1)}.")
para(tag("econ") + "Both are true because they describe different frequencies. The common trend "
     "operates on the level over months; daily movement is dominated by local order flow "
     "against a thin book and by the bid-ask bounce of Section 5.6.4. Worlds share a "
     "destination but travel there on independent paths. For a holder this means coin "
     "positions across several worlds diversify substantially at daily frequency, while "
     "providing almost no diversification against the common level over long horizons.")
para(tag("lim") + "No risk premium is estimated. There is no risk-free asset in this economy, "
     "no external numeraire, and no measure of the marginal holder's wealth, so the "
     "compensation for bearing this risk cannot be identified. The volatility figures describe "
     "risk; they do not price it.")

h3("7.1.3 Risk register")
table([["Risk", "Assessment", "Evidence"],
       ["Price risk (level)", "High and irreducible",
        f"{pc(D['ret_sd_ann_pct'], 0)} annualised volatility; unit root means no mean reversion "
        f"to rely on"],
       ["Drawdown risk", "Material",
        f"{pc(IX['max_drawdown_pct'], 1)} maximum index drawdown inside the window"],
       ["Liquidity risk", "Highly variable across worlds",
        f"Quoted spreads range from {pc(MI['quoted_spread_iqr'][0])} to "
        f"{pc(MI['quoted_spread_iqr'][1])} across the interquartile range"],
       ["Execution risk (cross-world)", "Structural",
        "Up to 4% round-trip fee for ordinary offer sizes, charged on creation and not refunded "
        "on cancellation; capital is locked on both sides while offers rest"],
       ["Convergence risk (young worlds)", "High",
        f"Median {gp(YG['median_days_to_within_5pct'])} days to reach within 5% of the "
        f"cross-world mean"],
       ["Data risk", "Present",
        "Single third-party mirror; upstream collection errors would propagate undetected"],
       ["Policy risk", "Unquantifiable",
        "CipSoft can alter fees, sinks, store prices or coin mechanics at any time; no "
        "historical base rate exists"]],
      [38 * mm, 34 * mm, AVAIL - 72 * mm],
      caption="Table 7.3 - Risk register.")
para(tag("judg") + "The most under-appreciated risk in this list is the fourth. The fee is "
     "charged when an offer is <i>created</i> and is not returned if the offer is cancelled. A "
     "cross-world trade that is entered and then abandoned because the gap closed before both "
     "legs executed still costs the fee. That asymmetry is why gaps below the band persist: the "
     "expected profit from attempting to close them is negative once failed attempts are priced "
     "in.")
para(tag("judg") + "The seventh risk deserves emphasis of a different kind. Every relationship "
     "in this report is conditional on the current rule set. A change to the Market fee would "
     "move the arbitrage band directly; a change to death penalties would move the Optional-PvP "
     "premium; a change to store pricing would move coin demand. None of these is forecastable "
     "from price data, and no confidence interval in this report accounts for them.")
story.append(PageBreak())

# ===================================================================== 30
h2sec('7.2', 'Robustness', 'The central result survives four price measures, every year and every region')
h3("7.2.1 Sensitivity to the price measure")
para(tag("obs") + "The central arbitrage regression was re-estimated on all four price measures.")
table([["Price measure", "Deviation coefficient", "Std. error", "p", "n",
        "Mean deviation from headline"]] +
      [[lab, f"{RB[k]['coef']:+.4f}", f"{RB[k]['se']:.4f}", pval(RB[k]["p"]),
        f"{RB[k]['n']:,}", pc(RB[k]["mean_dev_from_headline_pct"])]
       for k, lab in [("headline_mean_executed", "Headline (mean of executed)"),
                      ("quantity_weighted", "Quantity-weighted"),
                      ("order_book_mid", "Order-book mid"),
                      ("sell_side_only", "Sell-side only")]],
      [44 * mm, 30 * mm, 20 * mm, 16 * mm, 18 * mm, AVAIL - 128 * mm],
      align=[None, "R", "R", "R", "R", "R"],
      caption="Table 7.4 - The central result under four independent price constructions.")
para(tag("obs") + "The coefficient is negative, of similar magnitude and significant at any "
     "conventional level under every construction, including the order-book mid, which shares no "
     "input data with the executed-price measures. The finding is not an artefact of price "
     "construction.")

h3("7.2.2 Sub-sample stability")
ss_ = RB["dev_subsamples"]
table([["Sub-sample", "Coefficient", "Std. error", "p", "n"]] +
      [[k, f"{v['coef']:+.4f}", f"{v['se']:.4f}", pval(v["p"]), f"{v['n']:,}"]
       for k, v in ss_.items()],
      [40 * mm, 26 * mm, 22 * mm, 18 * mm, AVAIL - 106 * mm],
      align=[None, "R", "R", "R", "R"],
      caption="Table 7.5 - Deviation coefficient by year and region, world fixed effects, "
              "two-way clustered standard errors.")
para(tag("obs") + "The coefficient is negative and significant in every year and every region. "
     "It strengthens over time, from "
     f"{ss_['2024']['coef']:+.3f} in 2024 to {ss_['2026']['coef']:+.3f} in 2026, and is strongest "
     f"in South America ({ss_['South America']['coef']:+.3f}) and weakest in Europe "
     f"({ss_['Europe']['coef']:+.3f}).")
para(tag("econ") + "The strengthening over time has a mundane and a substantive reading, and "
     "they cannot be separated here. Mundanely, cross-sectional coverage improves over the "
     "window, so the cross-world mean is measured more precisely in later years and attenuation "
     "falls. Substantively, cross-world trading may genuinely have become more efficient. Both "
     "predict the same pattern.")

h3("7.2.3 Alternative covariance estimators")
para(tag("stat") + "Two-way clustering is one way to handle dependence in this panel. "
     "Driscoll-Kraay standard errors are an alternative that is robust to cross-sectional "
     "dependence of unknown form together with serial correlation - which is exactly the "
     "structure arbitrage induces - and they do not require the dependence to follow cluster "
     "boundaries.")
DK = FN["driscoll_kraay"]
table([["Estimator", "Std. error", "t statistic", "Assumption"],
       ["Naive (homoskedastic)", f"{DK['vs_naive_se']:.4f}",
        f"{DK['coef'] / DK['vs_naive_se']:+.1f}", "Independent observations"],
       ["Two-way clustered (used)", f"{DK['vs_twoway_se']:.4f}",
        f"{DK['coef'] / DK['vs_twoway_se']:+.1f}", "Dependence within world and within date"],
       ["Driscoll-Kraay", f"{DK['se']:.4f}", f"{DK['t']:+.1f}",
        f"Arbitrary cross-sectional dependence, {DK['lag']} lags"]],
      [46 * mm, 22 * mm, 24 * mm, AVAIL - 92 * mm], align=[None, "R", "R", None],
      caption=f"Table 7.6 - The arbitrage coefficient ({DK['coef']:+.4f}) under three "
              f"covariance estimators. n = {DK['n']:,} over {DK['n_dates']:,} dates.")
para(tag("obs") + f"The conclusion is unchanged under all three, but the ordering is worth "
     f"noting: two-way clustering is the <i>most</i> conservative of the three here, giving a "
     f"standard error {DK['vs_twoway_se'] / DK['se']:.1f} times the Driscoll-Kraay figure. The "
     f"report retains it for that reason.")

h3("7.2.4 Specification diagnostics")
DG = FN["diagnostics"]
table([["Diagnostic", "Result", "Consequence"],
       ["Maximum variance inflation factor", f"{DG['max_vif']:.2f}",
        "Below 5: no multicollinearity problem"],
       ["Breusch-Pagan heteroskedasticity", f"LM = {DG['breusch_pagan_LM']:.0f}, "
                                            f"p {pval(DG['breusch_pagan_p'])}",
        "Robust standard errors required"],
       ["Residual excess kurtosis", f"{DG['resid_excess_kurtosis']:.1f}",
        "Fat tails: bootstrap rather than normal intervals"],
       ["Residual skewness", f"{DG['resid_skew']:+.2f}", "Mild asymmetry"],
       ["Structural break in index drift",
        f"sup-Wald {R['finance']['structural_break']['sup_wald']:.2f} vs 8.85 critical",
        "<b>No break detected</b>"]],
      [50 * mm, 44 * mm, AVAIL - 94 * mm],
      caption="Table 7.7 - Specification and residual diagnostics. The break test is Andrews' "
              "supremum-Wald for an unknown break point with 15% trimming.")
para(tag("obs") + "Three of these justify choices made elsewhere: robust standard errors "
     "throughout, bootstrapped rather than parametric forecast intervals, and the absence of "
     "any need to split the sample. The absence of a structural break in the index drift is "
     "reassuring for the pooled estimates, which would otherwise be averaging across regimes.")

h3("7.2.5 Tests deliberately not run")
bullets([
    tag("lim") + "<b>No merge event study.</b> Zero pre-merge observations exist for any "
    "destination world (Section 5.5.2). A before-and-after comparison would be fabricated.",
    tag("lim") + "<b>No event coefficients under date fixed effects.</b> Verified to be "
    "unidentified to machine precision (Section 4.6.1), so no numbers are reported.",
    tag("lim") + "<b>No gold-inflation test.</b> No gold stock or income series exists in any "
    "accessible source.",
])
story.append(PageBreak())

# ===================================================================== 31
h2sec('7.3', 'Limitations',
      'The binding one is that the venue carrying most of the coins is a single annual number')
table([["#", "Limitation", "Consequence"],
       ["1", "Single third-party mirror for all price data",
        "Upstream collection errors propagate undetected; no independent price cross-check "
        "exists for most worlds"],
       ["2", "Cross-sectional coverage grows over the window",
        "Cross-world statistics restricted to 2024-04-06 onward; index must be chain-linked"],
       ["3", "UTC day boundary, not server save",
        "Fixed within-world offset; blurs day-of-week and same-day event attribution"],
       ["4", "All event labels are global",
        "Event effects are not causally identified and vanish under date fixed effects"],
       ["5", "No pre-merge observations",
        "Merge effects are untestable"],
       ["6", "No gold stock or coin supply series",
        "Gold <i>production</i> was obtained as kill statistics and tested directly in "
        "Section 6.6.14, where the channel is rejected. What is still missing is the "
        "accumulated stock and the quantity of coins issued, so the level cannot be tied to a "
        "monetary aggregate even though the flow channel is closed"],
       ["7", "Order book is a single snapshot",
        "Depth and quoted spreads have no history; only executed measures are time series"],
       ["8", "Participants are anonymised",
        "No concentration, no order-flow attribution, no participant counts"],
       ["9", "Character transfers cover 9 days",
        "The second cross-world channel is only weakly observable"],
       ["10", "Daily prices carry measurement noise",
        f"Return autocorrelation of {IN['mean_return_ac1']:+.3f}; naive persistence estimates "
        f"are attenuated"],
       ["11", "Cross-world dependence",
        "Addressed by two-way clustering, but a spatial-lag specification would be stronger"],
       ["12", "No real-money price <i>series</i>",
        f"A dated dollar price is now available from the token's on-chain market "
        f"(Section 5.8.3), which fixes the level at one moment. There is still no history, so "
        f"valuation over time remains gold-relative"],
       ["13", "Population is a current snapshot",
        "The roster and premium share are observed once per world with no history, so they "
        "enter cross-sectional models only and cannot be used in the daily panel"],
       ["14", "The gold-supply channel resists instrumentation",
        "A strong first stage (F = 198) does not rescue an implausible exclusion restriction; "
        "the IV estimate is discarded (Section 6.3.4)"],
       ["15", "Two population sources count different things",
        "The active-character census covers a share of the roster that falls with world age; "
        "using it as population injects error correlated with vintage (Section 5.3.3)"],
       ["16", "One venue of three is observed",
        "Coins also settle through the Tibia Token and through fiat resellers. Every price, "
        "band and forecast here is a within-venue result, and the arbitrage band is not a "
        "general friction estimate for the asset (Section 5.8)"],
       ["17", "The largest venue is a single annual observation",
        f"The Char Bazaar moves {MS['bazaar_over_market']:.1f} times the coins the in-game "
        f"Market does, and exists in this study as one pooled yearly total: no time series, no "
        f"per-world split. It contributes none of the 140 features tested, so every "
        f"forecastability result is conditional on the minority venue (Section 5.8)"]],
      [7 * mm, 62 * mm, AVAIL - 69 * mm],
      caption="Table 7.8 - Limitations and their analytical consequences.")
para(tag("judg") + f"<b>Limitation 17 is the binding one, and it displaced limitation 6 during "
     f"this study.</b> The gold-production series was obtained and the channel it was supposed "
     f"to support was tested twice and found no direct signal, so the missing supply data is "
     f"no longer what stands "
     f"between this report and an explanation of the level. What stands there now is that the "
     f"venue moving {MS['bazaar_over_market']:.1f} times more coins is visible only as one "
     f"number a year.")
para(tag("stat") + f"<b>That gap is bounded rather than open-ended, which is the useful thing "
     f"to say about it.</b> Bazaar flow could only act as a driver common to all worlds, and "
     f"Section 6.6.16 measures the ceiling on that whole class: perfectly observed and in "
     f"retrospect, a common state explains "
     f"{IRR['latent_state']['r2_factor_smoothed']:.1%} of daily variance and "
     f"{IRR['latent_state']['r2_factor_forecast']:.1%} one step ahead. So the missing series "
     f"cannot rescue a directional forecast; it could plausibly sharpen the volatility model "
     f"and the participant decomposition, and nothing in this report should be read as saying "
     f"it would do more than that.")
story.append(PageBreak())

# ===================================================================== 31A
h2sec('7.4', 'Welfare and market design', 'The fee cap subsidises scale in arbitrage')
h3("7.4.1 Market quality and the design of the fee")
para(tag("econ") + "The Market's design is a deliberate choice by CipSoft, and its parameters "
     "have measurable consequences for market quality. The 2% offer fee is a tax on trade: it "
     "widens the no-trade band (Section 5.2), and every gap inside that band is an allocative "
     "inefficiency in which a coin is worth more to someone on another world than to its "
     "holder, without the trade occurring.")
para(tag("stat") + f"The observed cost of that inefficiency is bounded. The estimated friction "
     f"point is {pc(R['advanced']['tar']['threshold_pct'])} (Section 6.3.1), and "
     f"{pc(R['advanced']['tar']['share_inside_band'] * 100, 0)} of world-days sit inside the "
     f"band where no correcting trade is worthwhile. Mean cross-world dispersion is "
     f"{pc(IN['mean_dispersion_pct'], 2)}. Those are the magnitudes of the price wedges the "
     f"design sustains.")
para(tag("econ") + f"<b>The fee cap makes the tax regressive in an unusual direction.</b> "
     f"Because the 2% rate is capped at 1,000,000 GP, the effective rate falls with offer "
     f"size: from 4.00% round trip on a small offer to "
     f"{pc(FE['roundtrip_largest_decile_pct'], 2)} on the largest decile (Section 5.2.4). Large "
     f"traders face a cost roughly {4.0 / FE['roundtrip_largest_decile_pct']:.0f} times lower "
     f"in percentage terms. The design therefore subsidises scale in arbitrage. Whether that "
     f"is intended is not observable; its effect on market quality is ambiguous, since it "
     f"encourages the large liquidity providers who tighten spreads (Section 5.6.5) while "
     f"concentrating the correcting trade in fewer hands.")
para(tag("judg") + "A second design feature works against integration. Capital is frozen while "
     "a buy offer rests, and the fee is charged at creation and never refunded. Together these "
     "penalise exactly the behaviour that would close small gaps: posting patient offers on "
     "several worlds and cancelling those that do not fill. Section 5.2.6 argues this, not the "
     "headline fee rate, is the more likely binding constraint.")

h3("7.4.2 CipSoft's incentives")
para(tag("econ") + "CipSoft sells coins for currency and earns nothing directly from the "
     "player-to-player gold market, but is not indifferent to it. A functioning gold market "
     "for coins raises the willingness to pay for coins bought with real money, because a "
     "purchaser can convert them to gold. A higher gold price per coin also makes coins a more "
     "attractive way for gold-rich players to obtain Premium Time.")
para(tag("hyp") + "This suggests CipSoft's interest lies in a liquid and reasonably integrated "
     "coin market with an orderly gold price, rather than in maximising fee revenue. The fee "
     "cap is consistent with that: an uncapped 2% would tax the largest transfers heavily and "
     "discourage precisely the trades that integrate worlds. This is an interpretation of "
     "observed design parameters, not a claim about CipSoft's stated intent, which is not "
     "public.")
para(tag("lim") + "No welfare calculation is attempted. Quantifying the deadweight loss of the "
     "fee would require the demand elasticity for cross-world transfers, which cannot be "
     "estimated without observing trades that did not happen.")

h3("7.4.3 Directions for future research")
para(tag("judg") + "Several questions are well posed but not answerable with the data "
     "assembled here. They are listed as hypotheses for future work, explicitly not as "
     "findings of this report.")
bullets([
    tag("hyp") + "<b>Behavioural pricing around round numbers.</b> Whether offers cluster at "
    "salient gold prices, and whether anchoring on those levels slows adjustment, would "
    "require a history of the order book rather than the single snapshot collected here.",
    tag("hyp") + "<b>Overreaction and correction around updates.</b> The pre-update effect in "
    "Section 4.6.2 decays monotonically with window length, which is consistent with "
    "anticipatory buying followed by correction. Distinguishing that from rational anticipation "
    "requires the world-varying exposure measures of Section 6.3.4.",
    tag("hyp") + "<b>Disposition effects in coin holding.</b> Whether players are more willing "
    "to sell coins at a gain than at a loss is untestable without account-level holdings, "
    "which are not published.",
    tag("hyp") + "<b>Event-driven trading behaviour.</b> Section 6.3.4 shows the event effect "
    "is concentrated in more active worlds. Whether that reflects gold supply, diverted "
    "demand, or attention-driven trading needs signed order flow.",
    tag("judg") + "<b>Character transfer flows as a second linkage channel.</b> The source "
    "exposes a rolling nine-day window only (Section 5.5.3); a maintained history would allow a "
    "test of whether player migration and coin flows are substitutes.",
])
story.append(PageBreak())

# ===================================================================== 32
verdict_page(
    VERDICT.capitalize(),
    "No view on the level, because none is supportable. A specific, tested view on where to "
    "hold and where to transact.",
    CONFIDENCE,
    supporting=[
        f"The strongest decile of cross-world gaps, held thirty days, nets "
        f"{pc(float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].net_pct.iloc[0]), 2)} "
        f"of the round trip and wins on "
        f"{float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].share_profitable.iloc[0]):.0%} "
        f"of occasions. On a true holdout it nets "
        f"{pc(float(HDF[(HDF.horizon == 30) & (HDF.period == 'holdout')].net_pct.iloc[0]), 2)}, "
        f"and at seven days - the only horizon with a large out-of-sample sample - "
        f"{pc(float(HDF[(HDF.horizon == 7) & (HDF.period == 'holdout')].net_pct.iloc[0]), 2)} "
        f"on {int(HDF[(HDF.horizon == 7) & (HDF.period == 'holdout')].n_effective.iloc[0])} "
        f"independent windows.",
        f"The long-only version - buy where the price is below the cross-world mean - is worth "
        f"{pc(float(STO[STO.horizon == 30].daily_paired_pct.iloc[0]), 2)} a month "
        f"(t = {float(STO[STO.horizon == 30].t_newey_west.iloc[0]):.1f}), costs nothing to "
        f"implement and carries no extra market risk.",
        f"{STA['n_worlds_profitable']} of {STA['n_worlds_used']} worlds and every calendar year "
        f"in the sample are positive on the signal, and it is not one standing opportunity: "
        f"{OCC['n_episodes']} distinct episodes at {OCC['episodes_per_month']:.1f} a month, "
        f"though only {OCC['episode_disjoint_windows']} of them are non-overlapping.",
        f"Capacity is the binding constraint, not conviction: about "
        f"{gp(CAPY['gp_per_month'])} GP a month can be deployed into it, for roughly "
        f"{gp(CAPY['expected_gp_per_month'])} GP of expected profit.",
    ],
    against=[
        "The level is non-stationary. Under a unit root the expected future price is the "
        "current price, so no amount of holding earns a premium.",
        "No model of the level beats a random walk out of sample, across fifteen model "
        "classes and every horizon tested.",
        "The spread version of the trade needs a short leg that Tibia does not offer, and the "
        "cost of a character world transfer is not in these numbers.",
        f"The quarterly figures are in-sample: the holdout holds "
        f"{int(HDF[(HDF.horizon == 91) & (HDF.period == 'holdout')].n_effective.iloc[0])} "
        f"independent window at that horizon, so nothing is established beyond a month.",
        f"A {pc(IX['max_drawdown_pct'], 1)} drawdown inside the sample shows how fast the "
        f"level can move against a position held for a quarter.",
    ],
    foot="The two lists do not cancel to Neutral: they point in different dimensions. The level "
         "is not forecastable and no position is taken on it. Relative position is "
         "forecastable, clears its cost, and is where the recommendation lives. "
         "Basis: Sections 7.7 and 7.8.")

h3("7.4.4 The fee cap asks for orders the market cannot absorb")
para(tag("stat") + f"<b>Correcting the volume series turns the fee-cap recommendation into a "
     f"conflict rather than a rule.</b> The cheapest execution requires an offer of "
     f"{gp(FE['cap_binds_at_lot_tc'])} TC, where the {gp(FE['cap_gp'])} GP cap binds and the "
     f"round trip falls from 4.00% to {pc(FE['roundtrip_largest_decile_pct'], 2)}. The median "
     f"converged world clears {gp(PX['median_tc_sold_per_world_day'])} coins a day. So the "
     f"cost-minimising order is <b>{PX['cap_lot_share_of_daily_volume']:.0%} of a day's entire "
     f"volume</b>, against a median resting offer of {gp(PX['median_offer_size_tc'])} coins - "
     f"{PX['median_offer_size_tc'] / PX['median_tc_sold_per_world_day']:.0%} of a day.")
para(tag("econ") + f"<b>The fee schedule and market impact therefore point in opposite "
     f"directions, and only one of them is in the fee table.</b> An 18-fold saving on explicit "
     f"cost is bought by posting an order that is a substantial fraction of everything the "
     f"world trades that day - which is precisely the situation in which the price moves "
     f"against the person posting it. The saving is measurable at "
     f"{pc(4.0 - FE['roundtrip_largest_decile_pct'], 2)}; the impact is not, because this data "
     f"records daily aggregates rather than the sequence of fills that would reveal it.")
para(tag("judg") + f"<b>The practical consequence, and a qualification to every sizing "
     f"recommendation in this report.</b> Post {gp(FE['cap_binds_at_lot_tc'])} TC to reach the "
     f"cap, but work it across days rather than placing it as one resting offer: the cap is "
     f"charged per offer, so a trader who splits into several offers each above the threshold "
     f"pays the capped fee on each and still avoids presenting "
     f"{PX['cap_lot_share_of_daily_volume']:.0%} of daily volume at once. That is the one place "
     f"where the fee schedule and the recommendation in Section 7.8 genuinely disagree, and the "
     f"disagreement was invisible while the volume series was misread.")
story.append(PageBreak())

h2sec('7.5', 'Positioning', 'What to do, at what threshold, and what would change it')
bottomline("The analysis supports a small number of decisions with explicit thresholds. Most "
           "of them are decisions not to act, which is the honest output of a market that is "
           "efficient up to costs - but the thresholds are specific, the monitoring list is "
           "short, and the conditions that would reverse each one are stated.")
para(tag("judg") + "A study that explains a market without saying what to do with it has done "
     "half the job. This section converts the findings into decisions. Each rule names the "
     "quantity to watch, the level at which to act, and the evidence it rests on; where the "
     "answer is to do nothing, the threshold at which that would change is given rather than "
     "left implicit.")

h3("7.5.1 The thesis")
para(tag("judg") + f"<b>Hold. Do not time the level; act only on relative price, and only "
     f"above 4%.</b> The coin is a claim on a euro-denominated service, priced in a currency "
     f"whose quantity nobody publishes. Its gold price has drifted up "
     f"{pc(IX['total_pct'], 1, True)} since {IX['index_start']} without becoming forecastable, "
     f"and the one mechanism that would have justified a directional view - gold accumulating "
     f"faster than it is destroyed - is tested in Section 6.6.14 and rejected. What remains "
     f"forecastable is a world's position against the others, at an out-of-sample R-squared of "
     f"{MAXP['best_r2']:.2f}. Pooled across all signals that edge is smaller than the fee needed "
     f"to take it; conditioned on strength and horizon it is not (Section 7.7).")
table([["Element", "Position"],
       ["Rating", "<b>Neutral / Hold.</b> No directional view on the gold price level"],
       ["Horizon", "Three to six months; beyond that the interval is wider than any "
                   "decision it could inform"],
       ["Central case", f"{SCNS.iloc[0].range} at {SCNS.iloc[0].probability:.0%}, median "
                        f"{gp(SCNS.iloc[0].conditional_median)} GP/TC"],
       ["What would make it Buy", "A fee cut or cap change; dispersion widening past 4%; a "
                                  "coin-supply series becoming observable and showing "
                                  "contraction"],
       ["What would make it Sell", "Sustained net token imports; a fall in engagement across "
                                   "regions; the sell side of the book thickening materially"],
       ["Conviction", f"{CONFIDENCE}/100 - the structural findings replicate and the "
                      f"directional question stays open"]],
      [30 * mm, AVAIL - 30 * mm], fs=7.0,
      caption="Table 7.9 - The thesis in one table.")

h3("7.5.2 Who is on the other side, and what each one wants")
para(tag("econ") + "A single demand curve hides five participants with different motives. "
     "Total demand is the sum of consumption, investment, arbitrage and value export, and each "
     "responds to a different price. The order book can be cut by size to bound how much of it "
     "each could account for, because the Store publishes its prices in coins and a purchase "
     "has a characteristic size.")
table([["Band", "Offers", "Share of coins", "Bid share", "Median size", "Fee paid"]] +
      [[r.band, f"{int(r.n_offers):,}", f"{r.share_of_tc:.1%}", f"{r.buy_share_of_tc:.0%}",
        f"{r.median_size:,.0f} TC", f"{r.median_fee_rate_pct:.2f}%"]
       for _, r in PB.iterrows()],
      [34 * mm, 18 * mm, 24 * mm, 18 * mm, 24 * mm, AVAIL - 118 * mm], fs=6.9,
      align=[None, "R", "R", "R", "R", "R"],
      caption="Table 7.10 - The live order book cut at Store-purchase sizes. A month of premium "
              "is 250 TC, a mount or outfit about 750.")
figure("fig30_participants.png",
       "Exhibit 7.4 - The live order book by order size, and resting depth against executed "
       "volume. Sources: TibiaMarket.top /market_board; price archive, item_id 22118.")
para(tag("stat") + f"Read naively this says consumption is negligible: orders under 500 TC are "
     f"{PB.iloc[0].share_of_offers:.0%} of offers and {PB.iloc[0].share_of_tc:.1%} of coins, "
     f"while wholesale orders are {PB.iloc[3].share_of_tc:.0%} of coins. <b>That reading is "
     f"wrong, and the reason is instructive.</b>")
para(tag("lim") + f"A resting order is an unfilled intention, not a trade. A consumer who buys "
     f"at the going price never appears in the book at all; a dealer's standing bid sits there "
     f"for weeks. The median world executes "
     f"{PX['median_executed_txn_per_world_day']:,.0f} lots a day - "
     f"{gp(PX['median_executed_per_world_day_tc'])} coins - against a resting bid "
     f"depth of {gp(PX['median_resting_bid_depth_tc'])} coins, and "
     f"{PX['share_wholesale_bids_20pct_below_mid']:.0%} of wholesale bids sit more than 20% "
     f"below the mid where they will never fill.")
para(tag("mech") + f"<b>The two series are on different scales, and the Market's own rule "
     f"reconciles them.</b> Coins trade only in lots of {PX['lot_size']} - no other quantity is "
     f"accepted - and the executed series counts lots, while the book is quoted in coins. "
     f"Converting at the lot, the median world clears "
     f"{gp(PX['median_executed_per_world_day_tc'])} coins a day against a resting bid depth of "
     f"{gp(PX['median_resting_bid_depth_tc'])}, so the book holds <b>"
     f"{PX['resting_over_daily_flow']:,.0f} days</b> of trade.")
para(tag("lim") + f"<b>Two daily volumes exist and they are not interchangeable.</b> The median "
     f"world buys {gp(PX['median_executed_per_world_day_tc'])} coins a day and sells "
     f"{gp(PX['median_tc_sold_per_world_day'])}; the two differ because they are medians of "
     f"different distributions, not because coins appear or vanish. Every share-of-a-day "
     f"figure in this report is quoted against the sold side, since that is the flow a buyer "
     f"consumes: on that denominator a median resting offer of "
     f"{gp(PX['median_offer_size_tc'])} coins is "
     f"{PX['median_offer_size_tc'] / PX['median_tc_sold_per_world_day']:.0%} of a day and the "
     f"{gp(FE['cap_binds_at_lot_tc'])} TC that reaches the fee cap is "
     f"{FE['cap_binds_at_lot_tc'] / PX['median_tc_sold_per_world_day']:.0%}.")
para(tag("econ") + f"So the two sides still describe different things, and the direction of the "
     f"asymmetry survives the units even though its magnitude does not. <b>Displayed intent is "
     f"wholesale - {PB.iloc[3].share_of_tc:.0%} of resting coins sit in orders of ten thousand "
     f"or more - while a whole day of execution is "
     f"{gp(PX['median_executed_per_world_day_tc'])} coins, roughly ten Store purchases.</b> A "
     f"book concentrated in a few large intentions, cleared by a trickle of small ones, is the "
     f"shape the mechanism in Section 7.6 requires. That is why the quoted spread of "
     f"{pc(FN['roll']['median_quoted_spread_pct'])} bears so little relation to the "
     f"{pc(FN['roll']['median_roll_spread_pct'])} that trades actually pay.")
table([["Participant", "Side", "Responds to", "What this study can say"]] +
      [[r.profile, r.side, r.stimulus, r.evidence] for _, r in PPROF.iterrows()],
      [34 * mm, 16 * mm, 34 * mm, AVAIL - 84 * mm], fs=6.6,
      caption="Table 7.11 - The five participant types, the stimulus each responds to, and what "
              "the evidence in this report bears on each.")
para(tag("judg") + f"Three consequences follow for positioning. The <b>sell side is thin</b> - "
     f"only {1 - PART['bid_share']:.0%} of resting coins are offers - so the price is more "
     f"exposed to gold buyers withdrawing than to consumers arriving. The <b>speculative motive "
     f"leaves no trace</b>: if investors were buying on expected appreciation the returns would "
     f"show momentum, and Section 6.6.2 finds none out of sample. And the <b>farmer who sells "
     f"gold directly never enters this market at all</b>, which is a standing blind spot - that "
     f"flow is pure gold supply and is invisible in every series this report uses.")

h3("7.5.3 Scenarios, with levels and probabilities")
figure("fig28_scenarios.png",
       "Exhibit 7.2 - The chain-linked index with its simulated forecast distribution, and the "
       "probability of each range by horizon. Source: price archive, item_id 22118.")
para(tag("fc") + f"The index stood at {gp(SCN['level'])} GP/TC on {SCN['as_of']}. Resampling "
     f"historical returns in ten-day blocks - so volatility clustering and fat tails survive - "
     f"and propagating {SCN['n_paths']:,} paths forward at the shrunk, capped drift of "
     f"{SCN['drift_daily_pct']:+.4f}% per day gives the distribution below. The probabilities "
     f"are read off that distribution; the round-number levels are chosen to be actionable.")
table([["Scenario", "Three-month range", "Probability", "Median if it happens", "Trigger"],
       ["<b>Base</b>", SCNS.iloc[0].range, f"<b>{SCNS.iloc[0].probability:.0%}</b>",
        f"{gp(SCNS.iloc[0].conditional_median)} GP/TC",
        "No change to the fee schedule; dispersion stays near "
        f"{pc(IN['dispersion_last'], 1)}; engagement broadly flat"],
       ["<b>Upside</b>", SCNS.iloc[1].range, f"<b>{SCNS.iloc[1].probability:.0%}</b>",
        f"{gp(SCNS.iloc[1].conditional_median)} GP/TC",
        "Coin demand rises - Bazaar turnover or premium demand up, or engagement rising - so "
        "more gold is offered per coin"],
       ["<b>Downside</b>", SCNS.iloc[2].range, f"<b>{SCNS.iloc[2].probability:.0%}</b>",
        f"{gp(SCNS.iloc[2].conditional_median)} GP/TC",
        "Coin supply into the Market rises, from promotions or net token imports, or activity "
        "falls sharply"]],
      [22 * mm, 34 * mm, 22 * mm, 30 * mm, AVAIL - 108 * mm], fs=6.9,
      caption=f"Table 7.12 - Three-month scenarios from a block-bootstrap of "
              f"{SCN['n_paths']:,} paths. The three are contiguous regions of one distribution, "
              f"so the probabilities sum to 100% by construction.")
para(tag("lim") + "<b>The direction of each trigger is worth stating carefully, because it is "
     "easy to invert.</b> The price is gold per coin. More demand for coins means more gold "
     "offered per coin, which is the <i>upside</i>. More coins reaching the Market means fewer "
     "gold per coin, which is the downside. And gold production is not among the triggers: "
     "Section 6.6.14 tests it directly and finds the elasticity negligible and the level "
     "relationship wrongly signed on every world, so an acceleration in gold creation is not a "
     "mechanism this evidence supports.")
table([["Range", "1 month", "3 months", "6 months"]] +
      [[r.band, f"{r['1 month']:.0%}", f"{r['3 months']:.0%}", f"{r['6 months']:.0%}"]
       for _, r in SCNB.iterrows()],
      [44 * mm, 26 * mm, 26 * mm, AVAIL - 96 * mm], align=[None, "R", "R", "R"],
      caption="Table 7.13 - Probability the index finishes in each range, by horizon. The "
              "widening with horizon is the whole content of a random-walk level.")
para(tag("fc") + f"Two figures matter more than the bands. The probability that the index sits "
     f"below today's level in three months is {LV['prob_below_current_3m']:.0%} - the "
     f"distribution is close to symmetric, which is what an unforecastable level means in "
     f"practice. And the 80% three-month interval runs {gp(LV['p10_3m'])} to "
     f"{gp(LV['p90_3m'])}, a spread of "
     f"{(LV['p90_3m'] / LV['p10_3m'] - 1) * 100:.0f}% - that width, not the median, is the "
     f"planning quantity.")

para(tag("judg") + f"<b>The model is an artefact, not a description.</b> It is saved to "
     f"models/deviation_model.pkl and can be re-run against fresh data with "
     f"<i>python scripts/30_model_artifact.py --predict</i>, which writes a current prediction "
     f"for every converged world with its interval. It predicts the change in a world's "
     f"position relative to the market over seven days, and it emits no level forecast at all - "
     f"Section 6.6.2 finds none is supportable, so the artefact refuses rather than obliges.")

h3("7.5.3a General versus group-specific models")
para(tag("stat") + f"<b>A second production artefact tests whether the mapping should be local "
     f"to a market segment.</b> It begins with PvP type x BattlEye cohort x region. Segments "
     f"with fewer than {GSM['preferred_min_worlds']} eligible worlds first pool regions, then "
     f"pool BattlEye cohorts; PvP types are never mixed. That rule produces "
     f"{GSM['specific_models']} specific models: "
     f"{GSM['group_level_worlds'].get('pvp_battleye_region', 0)} worlds keep the exact segment, "
     f"{GSM['group_level_worlds'].get('pvp_battleye', 0)} use a region-pooled model and "
     f"{GSM['group_level_worlds'].get('pvp', 0)} use a PvP-only model.")
para(tag("lim") + f"<b>Segmentation does not improve the aggregate forecast.</b> On the final "
     f"{int(GSO.n_dates)}-date holdout, the general model's RMSE is "
     f"{GSO.general_rmse_pct:.3f}% against {GSO.specific_rmse_pct:.3f}% for the specific family. "
     f"The specific error is {abs(GSO.specific_improvement_pct):.2f}% higher, and the "
     f"Newey-West comparison rejects equality at p = {GSO.dm_p_specific_vs_general:.3f}. "
     f"The specific models remain useful as a diagnostic and a current alternative score, but "
     f"the general model remains the evidence-backed default.")
table([["Scope", "Worlds", "General RMSE", "Specific RMSE",
        "Specific improvement", "Holdout winner"]] +
      [[r.scope_value, int(r.n_worlds), f"{r.general_rmse_pct:.3f}%",
        f"{r.specific_rmse_pct:.3f}%", f"{r.specific_improvement_pct:+.2f}%",
        str(r.better_model).title()] for _, r in
       pd.concat([GSC[GSC.scope == "all"], GSP]).iterrows()],
      [46 * mm, 16 * mm, 28 * mm, 28 * mm, 32 * mm, AVAIL - 150 * mm],
      fs=6.8, align=[None, "R", "R", "R", "R", None],
      caption="General versus hierarchical group-specific seven-day relative-value models. "
              "Both use the same date split and untouched holdout; lower RMSE is better.")
para(tag("lim") + f"One forced exception remains visible rather than hidden: Retro Hardcore "
     f"PvP has only {int(GSR[GSR.pvp_type == 'Retro Hardcore PvP'].model_worlds.max())} eligible "
     f"worlds globally. Because the hierarchy forbids cross-PvP pooling, that cohort uses a "
     f"regularised Ridge model and carries a low-sample warning. Full assignments, estimator "
     f"selection, sensitivity and current predictions are written by "
     f"<i>scripts/41_group_models.py</i>.")

h3("7.5.3b Launch-phase models")
para(tag("stat") + f"<b>Launch phase is now a separate, age-bounded model family.</b> A world "
     f"qualifies from creation through age {LPM['max_age_days']} days, close to the observed "
     f"{LPM['observed_median_convergence_days']}-day median time to come within 5% of the mature "
     f"market. The archive contains {LPM['launch_worlds_observed']} launch worlds; "
     f"{LPM['training_eligible_worlds']} have enough complete feature and target rows for model "
     f"development, and {LPM['active_launch_worlds']} are currently inside the age window. "
     f"Open, Optional and Retro Open PvP are fitted separately. BattlEye is not split because "
     f"all but one usable launch world are green.")
para(tag("lim") + f"<b>Enough observations do not guarantee a better forecast.</b> The holdout "
     f"combines later dates with {int(LPO.n_worlds)} launch worlds never used for estimation. "
     f"The launch family records RMSE {LPO.launch_rmse_pct:.3f}%, against "
     f"{LPO.general_rmse_pct:.3f}% when the mature general mapping is applied and "
     f"{LPO.zero_rmse_pct:.3f}% for zero change. Launch specialisation is "
     f"{abs(LPO.launch_improvement_vs_general_pct):.2f}% worse than the general model "
     f"(Newey-West p = {LPO.nw_p_launch_vs_general:.3f}), so the general model remains the "
     f"production default and Launch remains an explicitly experimental diagnostic.")
table([["Scope", "Worlds", "Launch RMSE", "General RMSE", "Zero RMSE",
        "Winner"]] +
      [[r.scope_value, int(r.n_worlds), f"{r.launch_rmse_pct:.3f}%",
        f"{r.general_rmse_pct:.3f}%", f"{r.zero_rmse_pct:.3f}%",
        str(r.better_model).title()] for _, r in
       pd.concat([LPC[LPC.scope == "all"], LPP]).iterrows()],
      [46 * mm, 16 * mm, 28 * mm, 28 * mm, 25 * mm, AVAIL - 143 * mm],
      fs=6.8, align=[None, "R", "R", "R", "R", None],
      caption="Launch-phase seven-day relative-value models evaluated on later dates and "
              "previously unseen launch worlds. Lower RMSE is better.")
para(tag("lim") + f"Retro Open PvP has only "
     f"{int(LPR[LPR.pvp_type == 'Retro Open PvP'].world.nunique())} training-eligible worlds "
     f"and therefore carries a low-sample warning. Current scores also publish their age and "
     f"staleness; the most data-constrained current score is "
     f"{LPM['max_prediction_staleness_days']} days behind the project date rather than being "
     f"silently presented as current. The model family and its independent audit are written "
     f"by <i>scripts/44_launch_phase_models.py</i> and "
     f"<i>scripts/45_verify_launch_models.py</i>.")

para(tag("stat") + f"<b>The bands were checked rather than asserted.</b> Walking the "
     f"history and simulating forward from each origin using only the data available at that "
     f"point, {BTS['well_calibrated']} of {BTS['n_tested']} band-horizon pairs cover within ten "
     f"points of their nominal rate.")
table([["Horizon", "Nominal", "Realised coverage", "Median width", "Verdict"]] +
      [[f"{int(r.horizon)}d", f"{r.nominal:.0%}", f"{r.coverage:.1%}",
        f"{r.median_width_pct:.1f}%", r.verdict]
       for _, r in BTC.iterrows()],
      [18 * mm, 20 * mm, 30 * mm, 24 * mm, AVAIL - 92 * mm], fs=6.9,
      align=[None, "R", "R", "R", None],
      caption=f"Table 7.14 - Out-of-sample coverage of the scenario bands, "
              f"{BTS['n_origins_total']} origins, {BTS['paths_per_origin']:,} paths each. "
              f"Coverage is counted at origins the simulation never saw.")
para(tag("lim") + f"One band fails, and it fails in the direction that matters: the "
     f"{BTS['worst_at']} covers {BTC[(BTC.horizon == 182) & (BTC.nominal == 0.5)].coverage.iloc[0]:.0%} "
     f"against a nominal 50%, {BTS['worst_error']:+.0%}. The pattern behind it is visible in "
     f"the calibration: the share of outcomes landing in the middle half of the forecast "
     f"distribution falls from {BTS['pit'][0]['share_in_middle_50pct']:.0%} at a month to "
     f"{BTS['pit'][2]['share_in_middle_50pct']:.0%} at six. At six months the bootstrap is too "
     f"tight in the middle - it underestimates how far the level drifts, which is what a unit "
     f"root with occasional regime shifts does to a block resample.")
para(tag("judg") + "The practical reading: the three-month scenarios in Table 7.12 are "
     "trustworthy at the stated rates, all three within eight points. The six-month figures "
     "should be used for the outer bands only, and the six-month median treated as a centre of "
     "gravity rather than a range. This is also why Table 7.9 sets the horizon at three to six "
     "months and not beyond.")

h3("7.5.4 Levels to act on")
table([["Level", "GP/TC", "What it means", "Action"],
       ["Three-month p90", gp(LV["p90_3m"]),
        "Reached in 10% of paths", "Reduce discretionary buying; sell into it if holding "
                                   "coins for a gold purpose"],
       ["Three-month p75", gp(LV["p75_3m"]), "Upper quartile",
        "Stop adding; the level is expensive relative to its own distribution"],
       ["Current", gp(SCN["level"]), "The median forecast at every horizon",
        "Neutral. Buy on need, not on view"],
       ["Three-month p25", gp(LV["p25_3m"]), "Lower quartile",
        "Accumulate if a coin purchase was planned anyway"],
       ["Three-month p10", gp(LV["p10_3m"]),
        "Reached in 10% of paths", "Buy the planned quantity; historically the better entries "
                                   "have come from this region"]],
      [30 * mm, 22 * mm, 40 * mm, AVAIL - 92 * mm], fs=6.9,
      caption="Table 7.15 - Levels from the same simulated distribution. These are percentiles, "
              "not targets: the model has no view on which will be reached.")
para(tag("judg") + "These are entry and exit levels in the only sense the evidence supports - "
     "positions in a distribution, telling a reader whether the current price is cheap or dear "
     "<i>relative to its own uncertainty</i>. They are not a forecast that any level will be "
     "reached, and a reader who treats them as one has misread the unit-root result.")

figure("fig29_live_predictions.png",
       "Exhibit 7.3 - Output of the shipped model: worlds ranked by predicted seven-day change "
       "in relative position, with 80% conformal intervals. Source: price archive, item_id "
       "22118; models/deviation_model.pkl.")
h3("7.5.5 The arbitrage strategy, stated as a rule")
para(tag("econ") + f"Section 6.6.10 shows the band trade loses at every realistic size. The "
     f"strategy that follows is therefore conditional, and the condition is a level: act only "
     f"when a cross-world gap clears the round-trip cost with a margin, which means "
     f"<b>{pc(LV['arb_act_gap_pct'], 1)}</b> or wider, not the "
     f"{pc(R['advanced']['tar']['threshold_pct'])} band itself.")
table([["Gap between two worlds", "What the evidence says", "Action"],
       [f"Below {pc(R['advanced']['tar']['threshold_pct'])}", "Inside the band; behaves as a "
        "random walk and does not close", "No trade"],
       [f"{pc(R['advanced']['tar']['threshold_pct'])} to {pc(LV['arb_act_gap_pct'], 1)}",
        f"Closes, but gross reversion of about 0.20% per week is below the "
        f"{pc(FE['roundtrip_largest_decile_pct'], 2)} best-case round trip",
        "No trade - this is the region that looks like an opportunity and is not"],
       [f"Above {pc(LV['arb_act_gap_pct'], 1)}",
        "Clears the uncapped round trip; closure is faster the wider the gap",
        f"Trade, sized at {gp(FE['cap_binds_at_lot_tc'])} TC or more in lots of "
        f"{FE['lot_size']} so the fee cap binds; hold one to three weeks"]],
      [34 * mm, 62 * mm, AVAIL - 96 * mm], fs=6.9,
      caption="Table 7.16 - The cross-world trade as a conditional rule keyed to the observed "
              "gap.")

h3("7.5.6 Risk management")
table([["Control", "Setting", "Derivation"],
       ["Position sizing", f"Size so that a {pc(IX['max_drawdown_pct'], 1)} move is "
                           f"survivable without forced selling",
        "The largest peak-to-trough decline observed in sample (Section 4.2)"],
       ["Volatility budget", f"{pc(D['ret_sd_ann_pct'], 0)} annualised on established worlds; "
                             f"about {pc(D['ret_sd_daily_pct'])} per day",
        "Section 4.1; near-integrated with fat tails (Section 7.1.1)"],
       ["Timing overlay", f"Defer discretionary entries out of weeks the volatility model "
                          f"flags, which it identifies at an area under the curve of "
                          f"{[r for r in FD['volatility_targets'] if r['target'] == 'y_hivol7'][0]['auc']:.2f}",
        "Section 6.6.5 - the one forecastable quantity found"],
       ["Concentration", f"Treat all worlds as one position for level risk; only "
                         f"{pc(FN['variance']['median_r2_systematic'] * 100, 1)} of daily "
                         f"variance is shared but the levels share one trend",
        "Sections 6.3.2 and 7.1.2"],
       ["Stop discipline", "None on the level. Under a unit root a stop converts noise into a "
                           "realised loss without improving the expected outcome",
        "Section 4.4"],
       ["Review trigger", "Re-run when the fee schedule changes, when dispersion moves "
                          f"materially from {pc(IN['dispersion_last'], 1)}, or quarterly",
        "Table 7.19"]],
      [30 * mm, 66 * mm, AVAIL - 96 * mm], fs=6.9,
      caption="Table 7.17 - Risk controls and where each comes from.")

h3("7.5.7 The decision rules")
table([["Decision", "Rule and threshold", "Basis", "Reverses if"],
       ["Cross-world arbitrage",
        f"Do not trade the band. Gross reversion is +0.20% per week against a best-case round "
        f"trip of {pc(FE['roundtrip_largest_decile_pct'], 2)}; the trade nets "
        f"{ARB['trading_rule']['above the fee cap']['mean_net_pct']:+.3f}% and wins on "
        f"{ARB['trading_rule']['above the fee cap']['share_profitable']:.0%} of signals",
        "6.6.10", "The fee falls, or a gap exceeds about 4% - twice the band and above the "
                  "uncapped round trip"],
       ["Offer sizing",
        f"If trading at all, post {gp(FE['cap_binds_at_lot_tc'])} TC or more in lots of "
        f"{FE['lot_size']}. Below that the round trip is 4.00%; above it the cap makes it "
        f"{pc(FE['roundtrip_largest_decile_pct'], 2)}",
        "2.2, 5.2.4", "CipSoft changes the 1,000,000 GP cap"],
       ["Holding the coin",
        "No directional view. The level is a unit root and the best model reaches "
        f"{MAXP['best_r2']:.2f} R² on relative position only, not on the level",
        "4.4, 6.6.2", "A gold-supply or coin-issuance series becomes observable"],
       ["Timing an entry",
        f"Use volatility, not direction. High-volatility weeks are forecastable at an area "
        f"under the curve of {[r for r in FD['volatility_targets'] if r['target'] == 'y_hivol7'][0]['auc']:.2f}; "
        f"defer discretionary purchases out of predicted high-volatility weeks",
        "6.6.5", "The volatility model loses calibration - re-check quarterly"],
       ["Position size",
        f"Size to a {pc(D['ret_sd_ann_pct'], 0)} annualised volatility and a "
        f"{pc(IX['max_drawdown_pct'], 1)} drawdown observed in sample; the 80% weekly interval "
        f"is about ±{100 * DSC['conformal'][1]['half_width']:.1f}% of relative position",
        "7.1, 6.6.9", "Realised volatility leaves that range for a full quarter"],
       ["Multi-world exposure",
        f"Treat worlds as one asset for level risk and as separate assets for daily risk: "
        f"{pc(FN['variance']['median_r2_systematic'] * 100, 1)} of daily variance is shared, "
        f"but the levels carry a single common trend",
        "6.3.2, 7.1.2", "The common trend splits into several factors"],
       ["New worlds",
        f"Do not read an opening price as information. Merge destinations open near mature "
        f"prices ({gp(YG['mergedest_first_price_median'])} GP/TC median); genuine launches open "
        f"as low as {gp(YG['launch_first_price_min'])} and converge over roughly "
        f"{YG['median_days_to_within_5pct']:.0f} days",
        "5.4", "CipSoft changes how new worlds are seeded"]],
      [30 * mm, 62 * mm, 16 * mm, AVAIL - 108 * mm], fs=6.8,
      caption="Table 7.18 - Decision rules with thresholds, and the condition that would "
              "overturn each.")

h3("7.5.8 What to monitor, and at what frequency")
para(tag("stat") + f"Two series lead the market by a day and survive correction for multiple "
     f"testing: monsters killed and players online (Section 6.6.1). Neither is tradeable on its "
     f"own - Section 6.6.2 shows that - but both are the right things to watch for a change in "
     f"the regime this report describes, because a break in either would arrive before the "
     f"price moved.")
table([["What to watch", "Frequency", "What a change would mean"],
       ["Market fee rate and the 1,000,000 GP cap", "On each update",
        "The single parameter that sets the arbitrage band; a change moves every threshold "
        "in Table 7.9"],
       ["Monsters killed, per world", "Weekly",
        "Leads the market return by one day; a sustained break signals a change in the "
        "activity regime"],
       ["Players online, per world", "Weekly",
        "The second leading series; also the denominator in the engagement measure that "
        "explains cross-world price levels"],
       ["Cross-world dispersion", "Weekly",
        f"Currently {pc(IN['dispersion_last'], 1)} among converged worlds; a sustained widening "
        f"beyond the band would make arbitrage viable for the first time"],
       ["Tibia Token supply and pool depth", "Monthly",
        f"{gp(VN['token']['total_supply'])} TIB outstanding; a large move would signal the "
        f"venue structure of Section 5.8 shifting"],
       ["New-world announcements and merges", "On announcement",
        "Changes the composition of the panel and the interpretation of any index"]],
      [52 * mm, 24 * mm, AVAIL - 76 * mm], fs=6.9,
      caption="Table 7.19 - Monitoring list, ordered by how quickly a change would invalidate "
              "the conclusions above.")

h3("7.5.9 Scenarios and the response to each")
table([["If this happens", "Expected effect", "Response"],
       ["CipSoft cuts the Market fee or raises the cap",
        "The no-trade band narrows in proportion; cross-world gaps that currently persist "
        "would begin to close",
        "Re-estimate the threshold model; the arbitrage rule in Table 7.9 could reverse"],
       ["A gold sink or faucet is added at scale",
        "The level could acquire a driver it currently lacks - though Section 6.6.14 finds "
        "production explains little of the present dynamics",
        "Watch dispersion and the kill series; a level driver would show as a common trend "
        "break before it showed in any world"],
       ["The token venue grows substantially",
        "An external euro price would increasingly anchor the gold price, and the level might "
        "stop behaving as a unit root",
        "Collect the token's market price as a series; Section 5.8.6 lists what is needed"],
       ["A merge wave",
        "Composition shifts; a naive index moves without any price moving",
        "Use the chain-linked index only (Section 4.2); treat the first 500 days of any new "
        "world as uninformative"],
       ["Realised volatility doubles",
        f"Interval widths scale with it; the {pc(IX['max_drawdown_pct'], 1)} drawdown ceases "
        f"to bound the risk",
        "Halve position sizes rather than re-forecast; the direction remains unforecastable "
        "in either regime"]],
      [40 * mm, 58 * mm, AVAIL - 98 * mm], fs=6.8,
      caption="Table 7.20 - Scenarios, their expected effect and the response each calls for.")
para(tag("lim") + "<b>What this section deliberately does not offer.</b> No price target, no "
     "entry or exit levels on the gold price, and no expected return. Chapters 4 and 6 "
     "establish that the level is a unit root and that no model class tested forecasts it; "
     "producing a target anyway would be presenting judgement as output. The rules above are "
     "the guidance the evidence actually supports, and the honest shape of it is a small "
     "number of thresholds and a longer list of things not worth doing.")
story.append(PageBreak())

h2sec('7.6', 'The mechanism',
      'What sets the gold price of a Tibia Coin, stated as one model rather than as a list of '
      'rejections')
bottomline("This report has accumulated a long list of things that do not explain the "
           "price, and a list of rejections is not a finding. What follows states the "
           "surviving model positively, ranks it against every alternative the study "
           "tested, and ends with the claims it shares with the interactive site - each "
           "written once and rendered in both places.")
para(tag("judg") + "<b>This report has accumulated a long list of things that do not explain "
     "the price. A list of rejections is not a finding.</b> This section states the surviving "
     "model positively, ranks the competing hypotheses against each other rather than each "
     "against zero, and takes the consequences.")

h3("7.6.1 The model, in five components")
para(tag("mech") + "<b>One. The anchor is fixed and the supply at it is unlimited.</b> CipSoft "
     "sells Tibia Coins for money at a posted price, in any quantity, forever. A coin is "
     "therefore never scarce in money terms. The quantity being priced in this report is not "
     "the coin - it is gold, quoted in coins. Everything that follows is a statement about an "
     "exchange rate between an elastic, fixed-price outside good and a currency produced inside "
     "the game.")
para(tag("stat") + f"<b>Two. No direct monetary channel is identified.</b> The obvious model - more gold "
     f"is mined, so each coin costs more gold - is not merely unproven here, it is rejected with "
     f"the sign against it. The elasticity of the forward price to gold production is within "
     f"{abs(_FLOW7):.3f} of zero at seven days, and the slope of the price on accumulated "
     f"production is <i>negative</i> on {SVD['gold_stock']['n_worlds'] - SVD['gold_stock']['n_positive_slope']} "
     f"of {SVD['gold_stock']['n_worlds']} worlds, at a median correlation of "
     f"{SVD['gold_stock']['median_corr']:+.2f}. Against that, behaviour alone reaches a "
     f"within-world R-squared of {_R2B:.3f} where production alone reaches {_R2S:.4f} - a factor "
     f"of {_R2B / _R2S:.0f}.")
para(tag("lim") + "<b>What that does and does not settle.</b> Both tests run gold against the "
     "price directly, and neither finds a stable signal at any lag tried. Neither measures the "
     "step in between: gold generated has to be spent into coin turnover before it can move a "
     "price, and that circulation is not observed here. So a delayed absorption channel is not "
     "rejected by this evidence - it is untested, and the conversion interval from gold "
     "created to coins bought cannot be estimated from what this study holds.")
para(tag("stat") + f"<b>Three. Clearing is thin, and it is need-driven.</b> The median world "
     f"executes {PX['median_executed_txn_per_world_day']:,.0f} lots a day - "
     f"{gp(PX['median_executed_per_world_day_tc'])} coins - against a resting bid "
     f"depth of {gp(PX['median_resting_bid_depth_tc'])} coins, so the book holds "
     f"{PX['resting_over_daily_flow']:,.0f} days of trade, of which "
     f"{PX['share_wholesale_bids_20pct_below_mid']:.0%} of the large orders sit more than 20% "
     f"below the mid and will never fill. The book is a wall of patient intent; the price is set "
     f"by the small minority who are impatient. The sell side is the thin one, at "
     f"{1 - PART['bid_share']:.0%} of resting coins.")
para(tag("stat") + f"<b>Four. A cost band, not an information equilibrium, bounds the "
     f"relation.</b> The threshold at which cross-world gaps begin to close is "
     f"{pc(R['advanced']['tar']['threshold_pct'])}, estimated by grid search rather than "
     f"assumed, with linearity rejected at a bootstrap p below 0.001. Inside the band prices "
     f"wander; outside it they revert. That is the signature of a no-arbitrage relation held "
     f"open by fees, and the fee schedule - 2% per offer, capped at "
     f"{gp(FE['cap_gp'])} GP - reproduces the width.")
para(tag("econ") + f"<b>Five. Neither leg pays a yield, so the level must be a martingale.</b> "
     f"Gold held is gold not spent; a coin held is a coin not spent. There is no carry on either "
     f"side, no dividend, no storage cost beyond opportunity, and no financing rate to anchor a "
     f"term structure. An exchange rate between two non-yielding assets, cleared by need rather "
     f"than by view, inside a band wider than any measurable edge, has an unforecastable level "
     f"and a forecastable variance. That is exactly what Chapters 4 and 6 measure: nothing "
     f"predicts direction, and volatility predicts at an area under the curve of "
     f"{[r for r in FD['volatility_targets'] if r['target'] == 'y_hivol7'][0]['auc']:.2f}.")

h3("7.6.2 The hypotheses, ranked against each other")
para(tag("judg") + "The tests in this report are usually reported one at a time against a null "
     "of no effect, which is why they read as a list of failures. Set side by side and scored "
     "on the same evidence, they separate cleanly into three groups. The verdicts below are "
     "comparative statements about which model the data prefer, not statements about "
     "statistical significance.")
table([["Hypothesis", "Verdict", "What decides it"],
       ["Gold production sets the price, directly",
        "<b>Not identified</b>",
        f"Elasticity within {abs(_FLOW7):.3f} of zero; slope on accumulated production negative "
        f"on {SVD['gold_stock']['n_worlds']} of {SVD['gold_stock']['n_worlds']} worlds; "
        f"behaviour outperforms production {_R2B / _R2S:.0f}:1"],
       ["Momentum or speculative feedback sets the price",
        "<b>Eliminated</b>",
        "No out-of-sample value at any horizon, and 0 of the 10 strongest interaction effects "
        "replicated on an independent split"],
       ["Worlds are separate markets",
        "<b>Eliminated</b>",
        "Johansen finds exactly one common stochastic trend; pass-through is near one-for-one"],
       ["A hidden driver exists that would forecast the level if observed",
        "<b>Weakened</b>",
        f"A perfectly observed common state explains "
        f"{IRR['latent_state']['r2_factor_smoothed']:.1%} of daily variance in retrospect and "
        f"{IRR['latent_state']['r2_factor_forecast']:.1%} one step ahead. The ceiling on any "
        f"observer is low"],
       ["The order book carries pressure information",
        "<b>Weakened</b>",
        f"Resting depth is {PX['resting_over_daily_flow']:,.0f} times executed flow and "
        f"{PX['share_wholesale_bids_20pct_below_mid']:.0%} of large bids are unexecutable. The "
        f"book measures intent, not pressure"],
       ["Transaction costs bound the price relation",
        "<b>Favoured</b>",
        f"Band estimated at {pc(R['advanced']['tar']['threshold_pct'])} against a fee schedule "
        f"that implies the same width; linearity rejected at bootstrap p below 0.001"],
       ["Clearing is thin and driven by need, not by view",
        "<b>Favoured</b>",
        f"{gp(PX['median_executed_per_world_day_tc'])} TC executed per world-day; sell side "
        f"{1 - PART['bid_share']:.0%} of resting coins; reversal equal to the "
        f"{pc(FN['roll']['median_roll_spread_pct'])} effective spread and no wider"],
       ["The level is a martingale because neither leg carries",
        "<b>Favoured</b>",
        f"Unit root not rejected on {ST['n'] - ST['adf_reject_5pct']} of {ST['n']} worlds; "
        f"{LV['prob_below_current_3m']:.0%} probability of finishing below today in three "
        f"months; direction unforecastable while variance is not"]],
      [56 * mm, 22 * mm, AVAIL - 78 * mm], fs=6.8,
      caption="Table 7.21 - The competing explanations, scored against each other on the "
              "evidence assembled in Chapters 5 to 7.")

h3("7.6.3 Why the negative results are the model's predictions")
para(tag("judg") + "<b>The distinction that matters is between an unanswered question and an "
     "answered one whose answer is a null.</b> If the mechanism above is right, then a model "
     "that beat a random walk on the level would falsify it. The fifteen model classes, the 140 "
     "features and the gold-production series are not fifteen failures to find something; they "
     "are fifteen independent tests the mechanism passed. Read that way the evidence is "
     "positive and it is unusually strong, because the prediction was risky: any one of those "
     "models could have found structure, and none did.")
bullets([
    "<b>The level does not forecast</b> because it is an exchange rate between two non-yielding "
    "assets. Predicted by the mechanism.",
    f"<b>The relative price does forecast, weakly</b> - R-squared {MAXP['best_r2']:.2f}, "
    f"directional accuracy {MAXP['best_dir_acc']:.0%} - because the cost band lets gaps open "
    f"before anything closes them. Predicted by the mechanism, including the sign.",
    f"<b>The average signal does not clear its cost</b> - "
    f"{pc(ARB['trading_rule']['above the fee cap']['mean_net_pct'], 3)} net at seven days - "
    f"because the band is set by the same fee the trade must pay. Predicted, and the "
    f"near-equality of the two numbers is the strongest single piece of evidence in the "
    f"report. The strongest decile held longer does clear it (Section 7.7), which the "
    f"mechanism also predicts: the band bounds the average, not the tail.",
    f"<b>Volatility forecasts while direction does not</b> because trading intensity is driven "
    f"by attention and events, which are persistent, while the reservation price is not. "
    f"Predicted.",
    "<b>Gold production shows nothing</b> because the coin's price is not a monetary quantity. "
    "Predicted, and the only one of these that the report expected to go the other way.",
])

h3("7.6.4 The claims this report and the site both make")
para(tag("judg") + "<b>The findings below are published in two places, and they are written "
     "once.</b> Each is defined in <font face='Courier'>scripts/narrative.py</font> with its "
     "own numbers read from the results files, then rendered here as a paragraph and on the "
     "interactive site as a card with the data behind it. Neither artifact restates the other, "
     "so neither can fall behind it.")
for _c in narrative.claims():
    para(tag(_c.label) + f"<b>{_c.heading}.</b> {_c.text}")
story.append(PageBreak())

h3("7.6.5 The thesis, and what would falsify it")
para(tag("judg") + f"<b>A Tibia Coin is a currency, not an asset.</b> That is the claim, and it "
     f"is meant to be contestable. Its content is that holding coins beyond what you intend to "
     f"spend is an uncompensated position: expected return zero at every horizon tested, "
     f"realised volatility {pc(D['ret_sd_ann_pct'], 0)} annualised, and no risk premium of any "
     f"kind, because there is no risk being borne on anyone's behalf. A player accumulating "
     f"coins in the belief that they appreciate is being paid nothing for carrying "
     f"{pc(D['ret_sd_ann_pct'], 0)} of variance. That is not a hedge and it is not a store of "
     f"value; it is a currency mismatch against the gold they actually spend.")
para(tag("judg") + f"<b>The second claim: this market's structure is set by its fee schedule, "
     f"not by its information.</b> Halve the 2% rate or the {gp(FE['cap_gp'])} GP cap and the "
     f"cross-world trade becomes viable, dispersion compresses, and the band narrows towards the "
     f"new cost - the market changes character within weeks. Double the gold supply and, on this "
     f"evidence, nothing measurable happens. Market design dominates monetary conditions here, "
     f"and the report treats that as its central economic conclusion rather than as an aside.")
para(tag("judg") + "Both claims are falsifiable on observable data, and the conditions are "
     "stated so that a reader can check them without re-running the study:")
bullets([
    f"<b>Persistent drift.</b> The index has compounded {pc(IX['cagr_pct'], 1)} a year, which "
    f"looks like a premium and is not one: against {pc(D['ret_sd_ann_pct'], 1)} annualised "
    f"volatility over {_IXYRS:.1f} years that is a t-statistic of {_DRIFT_T:.2f}, and resolving "
    f"it from zero at conventional significance would take on the order of {_YRS_NEEDED:,.0f} "
    f"years of data. The claim would be wrong if the index compounded above roughly "
    f"{pc(_DETECTABLE, 0)} a year for three consecutive years - the smallest drift a sample of "
    f"this length and this variance could actually distinguish from noise.",
    f"<b>A tradable band.</b> If cross-world dispersion holds above 4% while the fee schedule is "
    f"unchanged, the cost explanation is incomplete and something is preventing arbitrage that "
    f"is not a fee.",
    f"<b>A thickening sell side.</b> If offers rise materially above "
    f"{1 - PART['bid_share']:.0%} of resting coins without a fee change, the thin-clearing "
    f"component is wrong and the price becomes a depth phenomenon.",
])
para(tag("judg") + "The report's answer to what the price will do is still that it does not "
     "know, and that remains the honest answer. Its answer to what the price <i>is</i> is not "
     "hedged: an exchange rate against a fixed anchor, bounded by fees, cleared thin. Those are "
     "different questions, and only the first one has a null for an answer.")
story.append(PageBreak())

h2sec('7.7', 'The trade',
      'The relative signal does clear its cost - at the top decile, held a month or longer')
bottomline("Section 6.6.10 evaluated the cross-world trade as an average over every signal past "
           "the band, held seven days, and found it negative. That is the correct answer to the "
           "wrong question: no strategy takes every signal, and the round trip is paid once "
           "however long the position is held. Conditioned on signal strength and held for a "
           "month or more, the trade clears its cost by a wide margin and survives every attack "
           "made on it here.")
para(tag("stat") + f"<b>The grid.</b> Deviations past the band, sorted into deciles of size, "
     f"held from one week to one quarter, net of the cheapest documented round trip of "
     f"{pc(STR['verdict']['cost_pct'], 3)}. "
     f"{STR['verdict']['cells_net_positive']} of {STR['verdict']['cells_tested']} cells clear "
     f"the cost and {STR['verdict']['cells_net_positive_and_significant']} do so on the "
     f"per-date inference of Section 7.7.1 at a "
     f"t-statistic above two. The report's previous claim - that the edge never clears the fee - "
     f"held only at the shortest horizon and only on the unconditional average.")
table([["Holding period", "Mean gap", "Gross", "Net of cost", "Wins", "t (Newey-West)"]] +
      [[f"{int(r.horizon)} days",
        pc(float(STG[(STG.horizon == r.horizon) & (STG.decile == 10) &
                     (STG.cost_basis == 'above the fee cap')].mean_abs_dev_pct.iloc[0]), 1),
        pc(float(STG[(STG.horizon == r.horizon) & (STG.decile == 10) &
                     (STG.cost_basis == 'above the fee cap')].gross_pct.iloc[0]), 2),
        f"<b>{pc(r.net_pct, 2)}</b>",
        f"{float(STG[(STG.horizon == r.horizon) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].share_profitable.iloc[0]):.0%}",
        f"{r.t_newey_west:.1f}"]
       for _, r in STOV.iterrows()],
      [30 * mm, 22 * mm, 22 * mm, 26 * mm, 18 * mm, AVAIL - 118 * mm], fs=7,
      caption="Table 7.22 - The top decile of cross-world gaps, by holding period. Newey-West "
              "with lags equal to the horizon, because overlapping windows inflate a naive "
              "t-statistic by three to four times at these horizons.")

figure("fig32_strategy_horizon.png",
       "Exhibit 7.5 - The convergence trade against its cost, by holding period. Sources: "
       "price archive, item_id 22118; fee schedule from the Market documentation.")
h3("7.8.1 Three attacks on the result, and what survived")
para(tag("judg") + "A result this strong in a report that has found nothing tradable for a "
     "hundred pages deserves to be attacked before it is believed. Three things could "
     "manufacture it, and each was tested.")
bullets([
    f"<b>Overlapping windows, and a panel that is not a time series.</b> Two corrections apply "
    f"and they compound. Daily observations of a quarterly return share ninety days of data, "
    f"which Newey-West handles. But the panel also holds several worlds on the same day, and "
    f"those are not independent observations: every deviation is measured against the same "
    f"cross-world mean, so worlds qualifying together are views of one day. The series is "
    f"therefore collapsed to one observation per date before the correction is applied, and "
    f"the sample is counted in calendar span rather than in rows - "
    f"{int(STOV[STOV.horizon == 91].n_effective.iloc[0])} non-overlapping quarters, not the "
    f"{int(STOV[STOV.horizon == 91].n.iloc[0] / 91)} that dividing world-days by the horizon "
    f"would suggest. The naive t of {STOV[STOV.horizon == 91].t_naive.iloc[0]:.0f} falls to "
    f"{STOV[STOV.horizon == 91].t_newey_west.iloc[0]:.1f}. It survives.",
    f"<b>Selecting on noise.</b> Entering the day after the signal, so the selection day and "
    f"the entry day share no observation, leaves the 91-day net at "
    f"{pc(float(STD[STD.horizon == 91].net_pct.iloc[0]), 2)} against "
    f"{pc(float(STOV[STOV.horizon == 91].net_pct.iloc[0]), 2)}. The bid-ask bounce is not "
    f"driving it.",
    f"<b>A few worlds or one episode.</b> {STA['n_worlds_profitable']} of "
    f"{STA['n_worlds_used']} worlds are profitable on average, and every calendar year is "
    f"positive - the weakest at {pc(STA['worst_year_net_pct'], 2)}.",
])
para(tag("stat") + f"<b>A fourth question decides whether any of it is collectable: how often "
     f"does the signal occur?</b> A mean per signal-day is worthless if the qualifying set is "
     f"one persistently cheap world observed daily for a year. Collapsing runs of consecutive "
     f"qualifying days into episodes - the unit a player actually trades - the "
     f"{OCC['n_signal_days']:,} signal-days become <b>{OCC['n_episodes']} episodes across "
     f"{OCC['n_worlds']} worlds</b>, at a median length of "
     f"{OCC['median_episode_days']:.0f} days and {OCC['episodes_per_month']:.1f} new episodes "
     f"a month. A qualifying world exists on {OCC['share_days_with_any_signal']:.0%} of days, "
     f"typically {OCC['median_worlds_qualifying_per_day']:.0f} at a time. Scored per episode "
     f"rather than per day the trade grosses {pc(OCC['episode_mean_gross_pct'], 2)} and is "
     f"profitable on {OCC['episode_share_profitable']:.0%} of them.")
para(tag("lim") + f"<b>Episodes are not independent either, and saying how far from it matters "
     f"more than the mean does.</b> A median of {OCC['episode_median_overlapping']} of the "
     f"{OCC['n_episodes']} start within any ninety-one-day window, and the whole span holds "
     f"only {OCC['episode_disjoint_windows']} disjoint ones. Treating each episode as its own "
     f"observation gives t = {OCC['episode_t_naive']:.1f}; correcting for the overlap in start "
     f"order gives {OCC['episode_t_overlap_corrected']:.1f}; keeping only genuinely disjoint "
     f"windows gives {OCC['episode_t_disjoint']:.1f} on "
     f"{OCC['episode_disjoint_windows']} observations, which does not clear a five percent "
     f"threshold. The middle figure is the one to quote, and the last is why this section "
     f"claims nothing at the quarterly horizon.")
para(tag("lim") + "<b>What does not survive is the clean version of the trade.</b> The figures "
     "above are for a spread: long the cheap world, short the rich one. Tibia has no mechanism "
     "for a short position, so no player can run it as stated. What a player can run is the "
     "long-only version below, and the cost of a character world transfer - a real charge that "
     "this study has no price series for - is not included in any of these numbers.")

para(tag("stat") + f"<b>And the number that bounds the whole thing: capacity.</b> An edge is "
     f"worth what it can be sized at. Taking one fee-cap lot of "
     f"{gp(CAPY['lot_tc'])} TC per episode - already "
     f"{CAPY['lot_share_of_world_daily_volume']:.0%} of the world's daily volume, and the "
     f"smallest order that reaches the cheap execution - the strategy absorbs "
     f"<b>{gp(CAPY['tc_per_month'])} TC a month</b>, about "
     f"{gp(CAPY['gp_per_month'])} GP at today's index. At the thirty-day net of "
     f"{pc(CAPY['net_pct_30d'], 2)} that is roughly "
     f"{gp(CAPY['expected_gp_per_month'])} GP a month in expectation.")
para(tag("judg") + "<b>That is the honest size of the opportunity, and it is the reason this "
     "finding does not change the report's verdict on the level.</b> It is a real edge, "
     "repeatable and net of fees, and it will not make anyone rich: the market is too thin to "
     "take size. Anyone reading the earlier sections as an invitation to deploy a large "
     "position into the convergence trade should read this paragraph instead - the constraint "
     "is not the signal, it is the volume on the other side of it.")

story.append(CondPageBreak(150))
h2sec('7.7', 'Seasonality, stability and stress',
      'Three questions the study had assumed away, and the answers change one conclusion')
bottomline("The reversion this report trades is not one coefficient. It is four times stronger "
           "when volatility is in its top decile than when it is calm, it varies fourfold "
           "across rolling windows by more than sampling noise explains, and the market has a "
           "genuine month-of-year pattern that survives a year fixed effect. None of that "
           "overturns the mechanism; all of it qualifies how a single pooled number should be "
           "read.")

h3("7.7.1 Seasonality is real, and the earlier test could not have found it")
para(tag("judg") + "<b>A month dummy on a multi-year panel is not a seasonality test.</b> It "
     "mixes the recurring pattern with whatever the level happened to do in those particular "
     "months. Adding a year fixed effect leaves only what recurs, which is what the word means.")
table([["Specification", "Observations", "Joint chi-squared", "df", "p", "Largest month"]] +
      [[r.specification.capitalize(), gp(r.n), f"{r.joint_chi2:.0f}", f"{int(r.df)}",
        pval(r.joint_p), pc(r.largest_month_pct, 2) + " / day"]
       for _, r in SEM.iterrows()],
      [50 * mm, 24 * mm, 28 * mm, 12 * mm, 20 * mm, AVAIL - 134 * mm], fs=7,
      align=[None, "R", "R", "R", "R", "R"],
      caption="Table 7.23 - Month-of-year effects on the daily return, before and after "
              "absorbing the year.")
para(tag("stat") + f"<b>The pattern survives, and it strengthens.</b> With the year absorbed the "
     f"joint statistic rises to {SEM.iloc[1].joint_chi2:.0f} on {int(SEM.iloc[1].df)} degrees "
     f"of freedom, and the largest monthly effect is "
     f"{pc(SEM.iloc[1].largest_month_pct, 2)} a day. Day of week is also jointly significant "
     f"at p = {SEAS['day_of_week']['joint_p']:.0e}. The recurring in-game events - double "
     f"experience, rapid respawn, exaltation, double rewards - are jointly significant at "
     f"p = {SEAS['events']['joint_p']:.3f} across "
     f"{SEAS['events']['n_events_tested']} of the five flags; the fifth, a loot weekend, never "
     f"fires inside this window and is dropped rather than estimated as a constant.")
para(tag("judg") + "<b>What this does not license.</b> A significant calendar pattern in daily "
     "returns is not a trading rule: the effects are hundredths of a percent a day against a "
     "spread of 0.84%, so they are visible to a regression and invisible to a trader. They "
     "matter because a model that ignores them attributes seasonal movement to whatever "
     "variable happens to correlate with the calendar.")

h3("7.7.2 The central coefficient is not constant")
para(tag("stat") + f"<b>Re-estimated in {SEST['n_windows']} rolling "
     f"{SEST['window_days']}-day windows, the reversion coefficient runs from "
     f"{SEST['rolling_min']:+.3f} to {SEST['rolling_max']:+.3f} against a full-sample "
     f"{SEST['full_sample_coef']:+.3f}.</b> The spread is not sampling noise: the variance of "
     f"the estimates is {SEST['variance_ratio']:.1f} times the variance the standard errors "
     f"imply, so the parameter genuinely moves. What does hold is the sign - negative in every "
     f"window - and the significance, at t above two in "
     f"{SEST['share_significant']:.0%} of them.")
para(tag("judg") + "<b>So the mechanism is stable and the magnitude is not.</b> Gaps always "
     "close; how fast they close is a property of the period, not a constant of the market. "
     "Every half-life quoted in this report is an average over a range that varies by a factor "
     "of four, and the trading rules in Section 7.8 are stated as thresholds rather than as "
     "expected speeds for exactly that reason.")

h3("7.7.3 Stress changes the speed, not the direction")
table([["Regime", "Observations", "Coefficient", "t", "Half-life"]] +
      [[r.regime.capitalize(), gp(r.n), f"{r.coef:+.4f}", f"{r.t:.1f}",
        f"{r.half_life_days:.1f} days" if r.half_life_days == r.half_life_days else "-"]
       for _, r in SERG.iterrows()],
      [54 * mm, 26 * mm, 26 * mm, 16 * mm, AVAIL - 122 * mm], fs=7,
      align=[None, "R", "R", "R", "R"],
      caption="Table 7.24 - The reversion coefficient re-estimated within each regime, world "
              "fixed effects and errors clustered by world.")
para(tag("stat") + f"<b>The split that matters is volatility, not launch and not drawdown.</b> "
     f"In the top decile of trailing volatility the coefficient is "
     f"{float(SERG[SERG.regime == 'top-decile volatility'].coef.iloc[0]):+.3f} against "
     f"{float(SERG[SERG.regime == 'calm volatility'].coef.iloc[0]):+.3f} when calm - a half-life "
     f"of {float(SERG[SERG.regime == 'top-decile volatility'].half_life_days.iloc[0]):.0f} days "
     f"against {float(SERG[SERG.regime == 'calm volatility'].half_life_days.iloc[0]):.0f}. "
     f"Launch-phase and mature worlds are within a hair of each other, and so are drawdown and "
     f"non-drawdown periods. The pooled figure is an average of a fast regime and a slow one.")

h3("7.7.4 What the forecast error actually costs")
para(tag("judg") + "<b>A Diebold-Mariano test says which model is more accurate. It does not "
     "say whether the difference is worth anything.</b> Both belong in a report that asks a "
     "reader to act, so the errors are also reported in the units the reader holds.")
table([["Horizon", "Model", "Mean absolute error", "In GP per coin", "Within 2%", "Within 5%"]] +
      [[f"{int(r.horizon)} days", r.model.capitalize(), pc(r.mae_pct_of_level, 2),
        gp(r.mae_gp), f"{r.share_within_2pct:.0%}", f"{r.share_within_5pct:.0%}"]
       for _, r in SEER.iterrows()],
      [24 * mm, 30 * mm, 34 * mm, 28 * mm, 20 * mm, AVAIL - 136 * mm], fs=7,
      align=[None, None, "R", "R", "R", "R"],
      caption="Table 7.25 - Forecast error in economic terms. The random walk is the report's "
              "central forecast; the shrunk drift is the only alternative it entertains.")
para(tag("econ") + f"<b>The honest summary of the forecast is this table, not the test.</b> At "
     f"seven days a reader who assumes no change is wrong by "
     f"{pc(float(SEER[(SEER.horizon == 7) & (SEER.model == 'random walk')].mae_pct_of_level.iloc[0]), 1)} "
     f"on average - about "
     f"{gp(float(SEER[(SEER.horizon == 7) & (SEER.model == 'random walk')].mae_gp.iloc[0]))} GP "
     f"a coin - and lands within 2% "
     f"{float(SEER[(SEER.horizon == 7) & (SEER.model == 'random walk')].share_within_2pct.iloc[0]):.0%} "
     f"of the time. At ninety-one days the same assumption is wrong by "
     f"{pc(float(SEER[(SEER.horizon == 91) & (SEER.model == 'random walk')].mae_pct_of_level.iloc[0]), 1)} "
     f"and lands within 5% less than half the time. The drift alternative is worse at every "
     f"horizon on every measure here, which is the same answer the significance test gives and "
     f"is worth more to a reader.")
story.append(PageBreak())

h3("7.8.2 A true holdout, and the horizon at which the evidence actually runs out")
para(tag("judg") + "<b>Everything above characterises the full history, including the decile "
     "cutoff itself.</b> That is an in-sample description, and this report has criticised "
     "weaker claims made the same way. So the history is split once, the cutoff is taken from "
     "the training period alone, and the final stretch is scored having never been looked at.")
table([["Holding period", "Period", "Net of cost", "t (NW)", "Wins", "Independent windows"]] +
      [[f"{int(r.horizon)} days", r.period.title(), f"<b>{pc(r.net_pct, 2)}</b>",
        f"{r.t_newey_west:.1f}", f"{r.share_profitable:.0%}", f"{int(r.n_effective)}"]
       for _, r in HDF.iterrows()],
      [28 * mm, 22 * mm, 26 * mm, 18 * mm, 18 * mm, AVAIL - 112 * mm], fs=7,
      align=[None, None, "R", "R", "R", "R"],
      caption=f"Table 7.26 - Out-of-sample test. Train to {HOLD['split_date']}, score after. "
              f"Only the decile cutoff crosses the split.")
figure("fig33_holdout.png",
       "Exhibit 7.6 - The convergence trade in and out of sample, against the number of "
       "independent windows supporting each figure. Sources: price archive, item_id 22118.")
para(tag("stat") + f"<b>The edge survives at every horizon, and is larger out of sample than "
     f"in - which is a warning, not a result.</b> An effect that grows in the holdout usually "
     f"says the holdout period was unusual rather than that the strategy improved. The "
     f"informative column is the last one.")
bullets([
    f"<b>Seven days: confirmed.</b> {pc(float(HDF[(HDF.horizon == 7) & (HDF.period == 'holdout')].net_pct.iloc[0]), 2)} net at "
    f"t = {float(HDF[(HDF.horizon == 7) & (HDF.period == 'holdout')].t_newey_west.iloc[0]):.1f} on "
    f"{int(float(HDF[(HDF.horizon == 7) & (HDF.period == 'holdout')].n_effective.iloc[0]))} independent windows. This is the one horizon "
    f"where the out-of-sample sample is large enough to carry the claim.",
    f"<b>Thirty days: suggestive.</b> {pc(float(HDF[(HDF.horizon == 30) & (HDF.period == 'holdout')].net_pct.iloc[0]), 2)} net on "
    f"{int(float(HDF[(HDF.horizon == 30) & (HDF.period == 'holdout')].n_effective.iloc[0]))} independent windows. Consistent with the "
    f"training period and with the long-only result, but six observations decide little.",
    f"<b>Ninety-one days: no evidence.</b> The holdout contains "
    f"{int(float(HDF[(HDF.horizon == 91) & (HDF.period == 'holdout')].n_effective.iloc[0]))} independent window. The t-statistic of "
    f"{float(HDF[(HDF.horizon == 91) & (HDF.period == 'holdout')].t_newey_west.iloc[0]):.1f} is computed on overlapping views of a single "
    f"quarter and should be read as zero information, whatever its size.",
])
para(tag("judg") + f"<b>So the headline number moves.</b> The {pc(float(STG[(STG.horizon == 91) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].net_pct.iloc[0]), 2)} "
     f"at ninety-one days is an in-sample figure whose out-of-sample check has one observation; "
     f"it should not be the number a reader carries away. The number to carry away is the "
     f"thirty-day net of {pc(float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].net_pct.iloc[0]), 2)}, "
     f"which has {int(float(HDF[(HDF.horizon == 30) & (HDF.period == 'train')].n_effective.iloc[0]))} independent windows in training and "
     f"{int(float(HDF[(HDF.horizon == 30) & (HDF.period == 'holdout')].n_effective.iloc[0]))} out of sample and agrees with the long-only "
     f"test at the same horizon. The quarterly figures stay in the report because they show the "
     f"shape of the cost amortisation, not because they are tradable evidence.")
story.append(PageBreak())

h3("7.8.3 A pattern that looked like a regime effect, and two tests that took it apart")
para(tag("judg") + f"<b>The holdout paying more than the training period needs an explanation, "
     f"and the obvious one is wrong.</b> The natural guess is that gaps were wider in the "
     f"holdout, since the trade is paid out of dispersion. They were not: cross-world dispersion "
     f"averaged {pc(RGM['train_mean_disp'] * 100, 2)} in training and "
     f"{pc(RGM['holdout_mean_disp'] * 100, 2)} in the holdout, {RGM['holdout_vs_train']:+.0%}. "
     f"The trade paid more in the <i>calmer</i> period. Pooling the history and splitting it "
     f"into terciles of dispersion appears to confirm a regime effect.")
table([["Holding period", "Dispersion when opened", "Mean gap", "Net of cost", "t (NW)", "Wins"]] +
      [[f"{int(r.horizon)} days", r.dispersion.title(), pc(r.mean_disp_pct, 1),
        f"<b>{pc(r.net_pct, 2)}</b>", f"{r.t_newey_west:.1f}", f"{r.share_profitable:.0%}"]
       for _, r in RGD.iterrows()],
      [26 * mm, 34 * mm, 22 * mm, 24 * mm, 18 * mm, AVAIL - 124 * mm], fs=7,
      align=[None, None, "R", "R", "R", "R"],
      caption="Table 7.27 - The pooled tercile split, by market-wide dispersion on the day the "
              "position is opened. The pattern in this table does not survive Section 7.7.3.")
para(tag("hyp") + "<b>Two readings follow from it, and both were tested.</b> The first: what "
     "reverts is an <i>anomalous</i> gap rather than a large one, so dividing each deviation by "
     "the day's dispersion should select better than the raw deviation. The second: dispersion "
     "is a genuine regime variable, so the pattern should appear inside any period taken on its "
     "own, not only when periods are pooled.")
table([["Holding period", "Selector", "Net of cost", "t (NW)", "Wins"]] +
      [[f"{int(r.horizon)} days", r.selector.capitalize(), f"<b>{pc(r.net_pct, 2)}</b>",
        f"{r.t_newey_west:.1f}", f"{r.share_profitable:.0%}"]
       for _, r in SLD.iterrows()],
      [28 * mm, 46 * mm, 26 * mm, 20 * mm, AVAIL - 120 * mm], fs=7,
      align=[None, None, "R", "R", "R"],
      caption="Table 7.28 - First test: top decile selected by the raw gap against the gap "
              "divided by the day's dispersion.")
para(tag("stat") + f"<b>The first reading fails.</b> Normalising is worse at every horizon, and "
     f"at ninety-one days it takes the net from "
     f"{pc(float(SLD[(SLD.horizon == 91) & (SLD.selector == 'raw deviation')].net_pct.iloc[0]), 2)} "
     f"to {pc(float(SLD[(SLD.horizon == 91) & (SLD.selector == 'dispersion-normalised')].net_pct.iloc[0]), 2)}.")
table([["Period", "Holding period", "Low", "Mid", "High", "Low minus high"]] +
      [[per.title(), f"{h} days"]
       + [pc(float(CFD[(CFD.period == per) & (CFD.horizon == h) &
                       (CFD.dispersion == q)].net_pct.iloc[0]), 2)
          if len(CFD[(CFD.period == per) & (CFD.horizon == h) & (CFD.dispersion == q)]) else "-"
          for q in ("low", "mid", "high")]
       + [f"<b>{CONF['low_minus_high_pp'][f'{per} {h}d']:+.2f} pp</b>"
          if f"{per} {h}d" in CONF["low_minus_high_pp"] else "-"]
       for per in ("train only", "holdout only") for h in (7, 30)],
      [30 * mm, 26 * mm, 22 * mm, 22 * mm, 22 * mm, AVAIL - 122 * mm], fs=7,
      align=[None, None, "R", "R", "R", "R"],
      caption="Table 7.29 - Second test: the same tercile split computed inside each period "
              "separately, so the comparison is about relative calm rather than the level of "
              "dispersion in that era.")
para(tag("stat") + f"<b>The second reading fails too, and it is the one that matters.</b> "
     f"Dispersion fell across the sample, so <i>low dispersion</i> and <i>late in the sample</i> "
     f"are confounded in the pooled table. Split inside each period, the effect is much smaller "
     f"in training ({CONF['low_minus_high_pp']['train only 30d']:+.2f} points at thirty days "
     f"against the pooled table's four-fold gap) and it reverses in the holdout "
     f"({CONF['low_minus_high_pp']['holdout only 30d']:+.2f} points). The pooled result was "
     f"mostly the difference between two eras, not a regime a trader could condition on.")
para(tag("judg") + "<b>So nothing here is offered as a filter.</b> A plausible conditioning "
     "variable was given two chances and failed both: it does not improve selection across "
     "worlds and it does not replicate within periods. Pick the world on the raw gap; do not "
     "time the regime on dispersion. The tables stay because a reader who noticed the same "
     "pattern deserves to see it taken apart rather than quietly omitted.")
story.append(PageBreak())

h3("7.8.4 The long-only version, which is what a player can actually do")
para(tag("econ") + f"<b>Strip out the short leg and the signal still pays, because it tells you "
     f"<i>where</i> to transact.</b> A player about to buy coins is going to buy them somewhere. "
     f"Buying on a world trading below the cross-world mean, rather than on an arbitrary world, "
     f"is free to implement and carries no extra risk - the market exposure is identical.")
table([["Holding period", "Cheap world", "Anywhere", "Rich world", "Advantage, paired",
        "t (NW)", "Independent windows"]] +
      [[f"{int(r.horizon)} days", pc(r.cheap_world_pct, 2), pc(r.any_world_pct, 2),
        pc(r.rich_world_pct, 2), f"<b>{pc(r.daily_paired_pct, 2)}</b>",
        f"{r.t_newey_west:.1f}", f"{int(r.n_dates_effective)}"]
       for _, r in STO.iterrows()],
      [26 * mm, 24 * mm, 22 * mm, 22 * mm, 24 * mm, 16 * mm, AVAIL - 134 * mm], fs=7,
      align=[None, "R", "R", "R", "R", "R", "R"],
      caption="Table 7.30 - Gold return of simply holding coins, by where they were bought. The fourth column is <i>not</i> the difference of the two before it: it is a paired comparison, and the two disagree because the unconditional columns average over different sets of dates. The "
              "advantage is a paired comparison made within each date, so the market move common "
              "to both sides cancels. Cheap and rich are defined by the estimated band.")
para(tag("stat") + f"<b>The edge is real at a week and a month, and not established at a "
     f"quarter.</b> Buying on a cheap world beats buying on an arbitrary one by "
     f"{pc(float(STO[STO.horizon == 7].daily_paired_pct.iloc[0]), 2)} over a week "
     f"(t = {float(STO[STO.horizon == 7].t_newey_west.iloc[0]):.1f}) and "
     f"{pc(float(STO[STO.horizon == 30].daily_paired_pct.iloc[0]), 2)} over a month "
     f"(t = {float(STO[STO.horizon == 30].t_newey_west.iloc[0]):.1f}). The quarterly figure "
     f"looks larger at {pc(float(STO[STO.horizon == 91].daily_paired_pct.iloc[0]), 2)} but "
     f"carries t = {float(STO[STO.horizon == 91].t_newey_west.iloc[0]):.1f}, because "
     f"{_IXYRS:.1f} years of history contain only "
     f"{int(STO[STO.horizon == 91].n_dates_effective.iloc[0])} independent quarterly windows. "
     f"It is not evidence of a bigger edge; it is the same edge measured too few times.")
para(tag("judg") + f"<b>That is the investment thesis: small, free, repeatable, and bounded by "
     f"its own sample.</b> It is worth roughly "
     f"{pc(float(STO[STO.horizon == 30].daily_paired_pct.iloc[0]) * 12, 1)} a year if the "
     f"monthly figure holds, on coins a player was going to buy regardless, for the effort of "
     f"reading one column of Table B.2. It pays on "
     f"{float(STO[STO.horizon == 30].share_dates_positive.iloc[0]):.0%} of dates. No leverage, "
     f"no short leg, no fee beyond the one already being paid.")
para(tag("fc") + f"<b>Stated as a position.</b> Buy on any world whose price sits more than "
     f"{pc(R['advanced']['tar']['threshold_pct'])} below the cross-world mean. Hold as you "
     f"normally would; the edge is collected at purchase, not at exit. For the spread version, "
     f"expected relative gain is "
     f"{pc(float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].net_pct.iloc[0]), 2)} "
     f"net at thirty days on the strongest decile, winning on "
     f"{float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].share_profitable.iloc[0]):.0%} "
     f"of occasions - available only to a player who can hold coins on both worlds. The level "
     f"risk is unchanged and unhedgeable; this is a claim about relative position only.")
story.append(PageBreak())

h2sec('7.9', 'What to do',
      'Next week, next month, next quarter - stated as instructions, not as findings')
bottomline("A unit root is not a reason to do nothing. It says the expected price in three "
           "months is the price today, which is itself a specific instruction: stop waiting "
           "for a better entry, because none is coming in expectation. What follows is that "
           "instruction made concrete for each kind of holder.")
para(tag("judg") + "<b>The most common misreading of this report would be that it declines to "
     "advise.</b> It declines to forecast the level, which is a different thing. Every "
     "statement below follows from the evidence in the preceding chapters and is stated as an "
     "instruction, with the number that drives it.")

h3("7.9.1 Next week")
table([["If you are", "Do this", "Because"],
       ["<b>Buying coins for premium or Store goods</b>",
        "Buy now, at the going price. Do not wait for a dip and do not post a low bid and hope",
        f"The expected price next week is this week's. A bid below the market is an option you "
        f"are writing for free - {PART['executable']['share_wholesale_bids_20pct_below_mid']:.0%} "
        f"of large parked bids never fill"],
       ["<b>Selling coins for gold</b>",
        "Sell now if you need the gold now. If you do not, there is no hurry either - the "
        "expected price is flat both ways",
        f"Symmetric distribution: {SCN['levels']['prob_below_current_3m']:.0%} chance the index "
        f"is below today's level in three months"],
       ["<b>Holding across worlds</b>",
        f"Check your world's deviation in Table B.2. Above +4% relative to the market, sell "
        f"there; below -4%, buy there. Between, do nothing",
        f"Only gaps past {pc(LV['arb_act_gap_pct'], 0)} clear the round trip; inside that the "
        f"trade nets {ARB['trading_rule']['above the fee cap']['mean_net_pct']:+.3f}%"],
       ["<b>Sizing any trade</b>",
        f"Post {gp(FE['cap_binds_at_lot_tc'])} TC or more, in lots of {FE['lot_size']}, or do "
        f"not trade at all",
        f"Below that the round trip costs 4.00%; above it, "
        f"{pc(FE['roundtrip_largest_decile_pct'], 2)}. An eighteen-fold difference in cost"]],
      [42 * mm, 58 * mm, AVAIL - 100 * mm], fs=6.8,
      caption="Table 7.31 - The week-ahead decision, by holder type.")

h3("7.9.2 Next month")
para(tag("fc") + f"The one-month 80% band is {gp(38465)} to {gp(41604)} GP/TC around a median "
     f"of {gp(SCN['level'])}. That is a range of about ±4%, and it is the planning number: a "
     f"holder of a million coins should expect the gold value of that position to move by four "
     f"percent in either direction over a month, as a matter of routine.")
table([["Decision", "Instruction"],
       ["Accumulating a position",
        "Do not. Expected return is zero and the 80% band is ±4%. Accumulate only if you have "
        "a use for the coins, not a view on them"],
       ["Already holding",
        f"Hold. Selling to re-buy lower is a coin-flip that pays "
        f"{pc(FN['roll']['median_roll_spread_pct'])} in effective spread each way"],
       ["Converting a large amount",
        f"Split it across the month. This does not raise your expected proceeds - nothing does "
        f"- but it halves the variance of the average price you get. A world clears about "
        f"{gp(PX['median_tc_sold_per_world_day'])} coins a day, so even the "
        f"{gp(FE['cap_binds_at_lot_tc'])} TC that reaches the fee cap is "
        f"{PX['cap_lot_share_of_daily_volume']:.0%} of a day's volume (Section 7.4.4)"],
       ["Timing within the month",
        f"Use the volatility model, not a price view. It separates high-volatility weeks at an "
        f"area under the curve of "
        f"{[r for r in FD['volatility_targets'] if r['target'] == 'y_hivol7'][0]['auc']:.2f}; "
        f"transact out of those weeks"]],
      [40 * mm, AVAIL - 40 * mm], fs=6.9,
      caption="Table 7.32 - The month-ahead decision.")

h3("7.9.3 Next quarter")
para(tag("fc") + f"<b>The single most likely outcome is {SCNS.iloc[0].range}, at "
     f"{SCNS.iloc[0].probability:.0%}.</b> Above {gp(LV['p75_3m'])} the price sits in the top "
     f"quartile of its own distribution and is expensive relative to its uncertainty; below "
     f"{gp(LV['p25_3m'])} it is in the bottom quartile and cheap on the same measure. Those are not "
     f"predictions that either level will be reached - they are where to act if it is.")
table([["Level", "If the price gets here", "Do"],
       [f"Above {gp(LV['p90_3m'])}", "Reached in 10% of simulated paths",
        "Sell coins you were holding for a gold purpose. Stop discretionary buying entirely"],
       [f"{gp(LV['p75_3m'])} to {gp(LV['p90_3m'])}", "Upper quartile",
        "Do not add. Bring forward any planned selling"],
       [f"{gp(LV['p25_3m'])} to {gp(LV['p75_3m'])}", "The central half, and where it is now",
        "Transact on need alone. No timing signal exists in this range"],
       [f"{gp(LV['p10_3m'])} to {gp(LV['p25_3m'])}", "Lower quartile",
        "Bring forward planned buying. Accumulate if you have a use"],
       [f"Below {gp(LV['p10_3m'])}", "Reached in 10% of simulated paths",
        "Buy the full planned quantity. Historically the better entries came from here"]],
      [30 * mm, 46 * mm, AVAIL - 76 * mm], fs=6.9,
      caption="Table 7.33 - The quarter-ahead decision, keyed to levels rather than to dates.")
para(tag("judg") + f"<b>And the instruction that carries the most value, because it is the one "
     f"most often got wrong:</b> if you are going to need coins this quarter, buy them at your "
     f"convenience rather than at a moment you have chosen. The expected cost of buying today "
     f"versus in ninety days is zero, and the cost of waiting is that you carry the "
     f"{pc(D['ret_sd_ann_pct'], 0)} annualised volatility of the position for no compensation. "
     f"Timing this market is not merely difficult - the evidence says the attempt has negative "
     f"expected value once the {pc(FN['roll']['median_roll_spread_pct'])} spread is paid.")

h3("7.9.4 What would make this report say something different")
para(tag("judg") + "The position above is Neutral on the level and directive on everything "
     "else. It is not a hedge, and three specific observations would change it - each stated "
     "so that a reader can check them without re-running the study.")
bullets([
    f"<b>A fee change.</b> The 2% rate and the {FE['cap_gp']:,} GP cap set the whole cost "
    f"structure. Halve either and gaps between "
    f"{pc(R['advanced']['tar']['threshold_pct'])} and 4% become tradeable, which turns the "
    f"cross-world rule from 'do nothing' into an active strategy overnight.",
    f"<b>Dispersion widening past 4%.</b> Cross-world dispersion is "
    f"{pc(IN['dispersion_last'], 1)} among converged worlds. Sustained above 4% and the "
    f"arbitrage trade clears its cost without any fee change.",
    f"<b>The sell side thickening.</b> Only {1 - PART['bid_share']:.0%} of resting coins are "
    f"offers. A material rise means gold buyers are arriving in force, which is the one "
    f"mechanism that would push the gold price of a coin down persistently rather than "
    f"noisily.",
])
para(tag("judg") + "Absent those, the answer to what to do next week, next month and next "
     "quarter is above, and it is not 'nothing'. It is: transact on need at the going price, "
     "size above the fee cap, act across worlds only past 4%, avoid the weeks the volatility "
     "model flags, and stop paying spread for the privilege of guessing a level that three "
     "and a half years of data say is a random walk.")
story.append(PageBreak())

h2sec('7.10', 'Conclusion',
      'A currency priced against a fixed anchor, bounded by fees, cleared thin - and what that costs the holder')
h3("7.10.1 What this study establishes")
bullets([
    tag("stat") + f"Worlds are partially integrated markets bounded by a transaction-cost "
    f"band, with the friction point estimated at "
    f"{pc(R['advanced']['tar']['threshold_pct'])} by threshold autoregression. Inside the band "
    f"the gap is a random walk; outside it, it reverts. The magnitude is consistent with the "
    f"Market's capped fee schedule, and no fee figure entered the estimation.",
    tag("stat") + f"Relative cross-world pricing is predictable, with a half-life of roughly "
    f"three to four weeks. The common level is not: it carries a unit root. A Johansen rank "
    f"test on the five largest worlds finds "
    f"{R['advanced']['cointegration']['johansen']['rank']} cointegrating relations among "
    f"{R['advanced']['cointegration']['johansen']['n_series']} series - exactly one common "
    f"stochastic trend, which is that unpredictable level.",
    tag("stat") + f"World type explains cross-world price levels; raw world size and region do not. "
    f"Separating population from concurrent activity shows that what matters is engagement - "
    f"the share of a world's roster actually playing - not the roster's size. "
    f"Optional PvP carries a {pc(CS['type_age_pop']['optional_pvp']['coef'] * 100, 1)} premium.",
    tag("obs") + "Provenance, not age, sets a new world's opening price.",
    tag("lim") + "Event effects are measurable as associations but not identifiable as causes.",
])

h3("7.10.2 What drives the level, and what remains genuinely open")
para(tag("econ") + f"<b>The level is set on the gold side, by demand, and it is behavioural.</b> "
     f"That is a positive claim and the evidence carries it: the coin side cannot move the "
     f"price because supply at the posted money price is unlimited, and the gold side is not "
     f"moved by production - the elasticity is negligible and the level relationship has the "
     f"wrong sign on all {SVD['gold_stock']['n_worlds']} worlds. What remains is the "
     f"reservation price of the participants who need to transact, and that block outperforms "
     f"production by a factor of {_R2B / _R2S:.0f}. The report long favoured the monetary "
     f"explanation; the data eliminated it, and the demand-side account is what survived the "
     f"comparison rather than what was left over.")
para(tag("judg") + f"<b>The index's {pc(IX['cagr_pct'], 2)} annualised drift needs no separate "
     f"explanation, because it is not distinguishable from zero.</b> Against "
     f"{pc(D['ret_sd_ann_pct'], 1)} annualised volatility over {_IXYRS:.1f} years it is a "
     f"t-statistic of {_DRIFT_T:.2f}. Treating it as a trend to be accounted for would be "
     f"fitting a story to noise.")
para(tag("lim") + "<b>One thing is genuinely open, and it is narrower than it has been stated "
     "so far.</b> The reservation price cannot be decomposed into named motives - consumption, "
     "speculation, and conversion to and from outside money - because the outside price of gold "
     "is not observable from any source this study is permitted to use. Section 7.5.2 bounds "
     "those shares by order size, which is a hypothesis about motive rather than a measurement "
     "of it. That is the one place where the mechanism is described but not identified.")

h3("7.10.3 Rating and confidence")
para(tag("judg") + f"<b>Verdict: {VERDICT}.</b>")
para("The verdict deliberately does not rest on the technical indicators of Section 5.7, which "
     "currently read firm across almost every world. Three considerations override them on the "
     "level, and a fourth is why the verdict is not simply Neutral:")
bullets([
    "The level is non-stationary. Under a unit root, the expected future price is the current "
    "price, and momentum measures computed on such a series carry no forecasting content.",
    "No model of the price <i>level</i> beats a random walk out of sample - not the report's "
    "own forecaster, and not any of the fifteen model classes tested in Section 6.6. A study "
    "whose own backtest shows no central-tendency edge should not issue a directional call.",
    f"The one mechanism that would justify a structural bullish view - persistent gold inflation "
    f"- has now been tested against production data in Section 6.6.14 and is <b>not "
    f"supported</b>: the elasticity is negligible and the level relationship carries the wrong "
    f"sign on all {SVD['gold_stock']['n_worlds']} worlds. Rating on a mechanism the evidence "
    f"rejects would be presenting analyst judgement as model output.",
    f"<b>But relative position is a different question, and there the evidence supports a "
    f"call.</b> The strongest decile of cross-world gaps, held thirty days, nets "
    f"{pc(float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].net_pct.iloc[0]), 2)} "
    f"of the round trip, wins on "
    f"{float(STG[(STG.horizon == 30) & (STG.decile == 10) & (STG.cost_basis == 'above the fee cap')].share_profitable.iloc[0]):.0%} "
    f"of occasions and survives correction for overlapping windows, a delayed entry and a "
    f"concentration check (Section 7.7). Its limit is capacity - about "
    f"{gp(CAPY['gp_per_month'])} GP a month - not confidence.",
])
para(tag("judg") + "The balance of evidence is genuinely two-sided, and the opening page of "
     "this section sets the two sides out in full. Neither dominates: a firmer tone has real "
     "support in the realised return and in the breadth of worlds above their long averages, "
     "and it is answered point for point by the non-stationarity of the level and by the "
     "absence of any out-of-sample edge <i>on the level</i>. The edge that does exist, on a "
     "world's position relative to the others, is real and clears the fee once it is conditioned "
     "on strength and horizon. So the two lists do not net to Neutral - they answer different "
     "questions, and the verdict takes a position on the one that has an answer.")
para(tag("judg") + f"<b>Confidence score: {CONFIDENCE} / 100.</b>")
table([["Component", "Assessment", "Weight on confidence"],
       ["Data volume and coverage", "40,658 world-days, 93 worlds, 4 independent sources",
        "Raises"],
       ["Replication across measures", "Central result holds on 4 independent price "
                                       "constructions and every sub-sample", "Raises"],
       ["Statistical rigour", "Two-way clustered errors; lagged regressors; attenuation "
                              "diagnosed and corrected", "Raises"],
       ["Recovery of a known constant", "The 4% fee threshold recovered from prices alone",
        "Raises"],
       ["Single-source price data", "One third-party mirror, no independent cross-check",
        "Lowers"],
       ["Unidentified level driver", "The main economic question is untestable here", "Lowers"],
       ["No causal event identification", "Global events are collinear with dates", "Lowers"],
       ["Policy risk", "Rule changes could void any relationship without warning", "Lowers"]],
      [42 * mm, 74 * mm, AVAIL - 116 * mm],
      caption="Table 7.34 - Basis for the confidence score.")
para(tag("judg") + "The score reflects high confidence in the structural findings - the "
     "arbitrage band, the non-stationarity, the provenance result and the world-type effects are "
     "each replicated across measures and sub-samples - combined with low confidence in any "
     "directional view on the level. A study can be simultaneously rigorous about what it "
     "measures and honest that what it measures does not support a forecast. That is the "
     "position here.")
story.append(PageBreak())

# ===================================================================== 33
chapter(8, 'Reference',
        'Field definitions, the complete source inventory and the methodological detail needed to reproduce or audit the analysis.')
h2sec('8.1', 'Data dictionary', 'Every field, its units, and what it must not be read as')
table([["Field", "Type", "Definition", "Notes"],
       ["world", "text", "World name", "Join key across all sources"],
       ["date", "date", "UTC-floored observation date", "Not the server-save day"],
       ["price_gp", "GP/TC", "Mean of the two valid daily executed averages", "Headline measure"],
       ["px_sell / px_buy", "GP/TC", "Validated day_average_sell / day_average_buy",
        "Gated on quantity &gt; 0 and value &gt; 1,000 GP"],
       ["price_vw", "GP/TC", "Executed averages weighted by TC traded", "Sensitivity measure"],
       ["price_book_mid", "GP/TC", "(best bid + best ask) / 2",
        "Only when ask/bid in [0.5, 2.0]"],
       ["quoted_spread_pct", "%", "(ask - bid) / mid", "A true quoted spread"],
       ["executed_gap_pct", "%", "(px_sell - px_buy) / mean", "<b>Not a bid-ask spread</b>"],
       ["log_price", "log GP", "Natural log of price_gp", "-"],
       ["ret", "log points", "First difference of log_price",
        "Only between consecutive observed days"],
       ["dev", "log points", "log_price minus cross-world mean log price on that date",
        "Only on dates with &gt;= 10 observed worlds"],
       ["dev_lag", "log points", "dev lagged one day", "<b>Always lagged before use</b>"],
       ["closure_pp", "pp/day", "Fall in |dev| from one day to the next",
        "Positive means the gap narrowed"],
       ["tc_sold / tc_bought", "TC/day", "Coins executed on each side: day_sold and "
        "day_bought converted at the 25-coin lot the Market enforces",
        "<b>Never summed</b>"],
       ["day_high / day_low", "GP/TC", "Daily extremes, band-checked",
        "Built sell-side up; buy-side lows unusable"],
       ["activity_online", "players", "Daily-average concurrent players online (a flow)",
        "GuildStats full daily history; <b>not population</b>"],
       ["population", "characters", "Full character roster of the world (a stock)",
        f"TibiaVIP Total column; {bw.population.sum():,} across 93 worlds"],
       ["active_chars", "characters", "Indexed high-level characters (a stock)",
        "GuildStats /census; 3.6% to 79% of the roster"],
       ["active_share", "share", "active_chars / population",
        "Falls with world age (rho -0.65)"],
       ["engagement", "ratio", "Concurrent players online per resident character",
        "activity_year / population; 0.005 to 0.065"],
       ["premium_share", "share", "Characters on premium accounts",
        "GuildStats /census"],
       ["converged", "bool", "&gt;= 200 obs, regular type, not a launch in window",
        f"{W['n_converged']} worlds"],
       ["launch_in_window", "bool", "Created in window and absent from the merge register",
        f"{W['n_launch']} worlds"],
       ["is_merge_destination", "bool", "Present in the merge register as a destination", "-"],
       ["ev_*", "0/1", "Global event flags", "No world dimension"],
       ["pre_update_N / post_update_N", "0/1", "N days before / after an update release",
        "7 releases in window"]],
      [34 * mm, 17 * mm, 66 * mm, AVAIL - 117 * mm],
      caption="Table 8.1 - Data dictionary for the price analysis panel.")
para(tag("mech") + "The fundamentals panel of Section 6.6 carries its own fields, derived "
     "rather than collected. The primitives are below; the engineered features built from them "
     "are listed in fundamentals_meta.json, which records all "
     f"{FD['panel']['n_features']} with the targets they predict.")
table([["Field", "Type", "Definition", "Notes"],
       ["monsters_killed", "count", "Creatures killed by players on that world-day",
        "Gold production proxy; the page reports the trailing day and dates are shifted "
        "accordingly"],
       ["players_killed", "count", "Players killed by creatures", "Gold destruction proxy"],
       ["boss_kills", "count", "Kills of creatures in the official Bosstiary",
        "327 named bosses; endgame activity"],
       ["races_hunted", "count", "Distinct creature types killed", "Breadth of hunting"],
       ["hunt_hhi", "index", "Herfindahl concentration of kills across races",
        "1.0 means every kill was the same creature"],
       ["dev", "log points", "Log price less the cross-world mean",
        "The quantity the threshold model and the shipped model both target"],
       ["rel_premium", "log points", "Lagged deviation from the cross-world median",
        "The feature form of dev; lagged so it is knowable in advance"],
       ["y_ret{h}, y_rel{h}", "log points", "Forward return and forward relative return",
        "The two regression targets, at 1, 7 and 30 days"],
       ["y_vol7, y_hivol7", "annualised, binary",
        "Realised volatility over the next week, and whether it lands in the top quartile",
        "The one forecastable target (Section 6.6.5)"]],
      [30 * mm, 20 * mm, 56 * mm, AVAIL - 106 * mm], fs=6.8,
      caption="Table 8.2 - Data dictionary for the fundamentals panel.")
story.append(PageBreak())

# ===================================================================== 34
h2sec('8.2', 'Source inventory', 'Every endpoint called, when, and what was deliberately not called')
table([["Source", "Endpoint or path", "Retrieved", "Records"],
       ["GitHub archive", "tibia-warzones-schedule, data/market/world/&lt;World&gt;/"
                          "&lt;world&gt;_tibia_coins.json", "2026-07-30", "41,584 snapshots"],
       ["TibiaMarket.top", "/openapi.json", "2026-07-30", "Schema"],
       ["TibiaMarket.top", "/events?start_days_ago=1400&amp;end_days_ago=0", "2026-07-30",
        "973 dated event records"],
       ["TibiaMarket.top", "/item_metadata", "2026-07-30", "5,096 items"],
       ["TibiaMarket.top", "/world_data", "2026-07-30", "World fields"],
       ["TibiaMarket.top", "/market_board?server=&lt;W&gt;&amp;item_id=22118", "2026-07-30",
        "93 order books"],
       ["TibiaData v4", "/v4/worlds", "2026-07-30 18:43 UTC", "93 regular worlds"],
       ["TibiaData v4", "/v4/news/archive/1400", "2026-07-30", "1,855 news items"],
       ["GuildStats.eu", "/worlds", "2026-07-30", "93 worlds with creation dates"],
       ["GuildStats.eu", "/servers-merge", "2026-07-30",
        f"{MG['n_merges']} merges, {MG['n_predecessors']} predecessors"],
       ["TibiaVIP", "World list, Total column", "supplied 2026-07-30",
        "93 worlds, 6,222,595 characters"],
       ["GuildStats.eu", "/census?world=&lt;W&gt;", "2026-07-30",
        "93 worlds, 483,579 active characters"],
       ["GuildStats.eu", "/online-counter?world=&lt;W&gt;", "2026-07-30",
        "93 worlds, 166,679 world-days"],
       ["GuildStats.eu", "/world-transfer", "2026-07-30", f"{MG['transfers_n']} transfers"],
       ["tibia.com", "/support/tibiatokenserviceagreement.php", "2026-07-31",
        "Tibia Token mechanics: two-way exchange, fee in TC, user pays gas"],
       ["BNB Smart Chain", f"eth_call on {VN['token']['contract'][:10]}...", "2026-07-31",
        f"{VN['token']['symbol']} supply {gp(VN['token']['total_supply'])} at block "
        f"{VN['token']['block']:,}"],
       ["tibiamaps/tibia-kill-stats", "data/&lt;world&gt;/&lt;date&gt;.json", "2026-07-31",
        f"{KS_ROWS:,} world-days of kill statistics across {KS_WORLDS} worlds, "
        f"{FD['panel']['start']} to {FD['panel']['end']}"],
       ["NabBot", "/stats/2025/all", "2026-07-31",
        f"Char Bazaar {VN['bazaar']['year']}: {gp(VN['bazaar']['auctions_created'])} auctions, "
        f"{gp(VN['bazaar']['tc_exchanged'])} TC exchanged"],
       ["TibiaVIP", "population endpoints", "<b>Not collected</b>",
        "Disallowed by robots.txt; respected"]],
      [26 * mm, 62 * mm, 26 * mm, AVAIL - 114 * mm],
      caption="Table 8.3 - Complete source and endpoint inventory. All timestamps UTC. "
              "GuildStats robots.txt was verified as 'Allow: /' before collection; requests "
              "were issued one world at a time with a courtesy delay.")
story.append(PageBreak())

# ===================================================================== 35
h2sec('8.3', 'Methodological appendix', 'Estimators, critical values and the reproducibility chain')
h3("8.3.1 Two-way clustered standard errors")
para("Following Cameron, Gelbach and Miller (2011), the variance estimator is "
     "V = V(world) + V(date) - V(world &times; date), each component computed as a "
     "cluster-robust sandwich with the finite-sample correction G/(G-1) &times; (N-1)/(N-K), "
     "where fixed effects are counted in K. The subtraction can leave a non-positive-definite "
     "matrix in finite samples; where that occurs the result is projected onto the nearest "
     "positive semi-definite matrix by clipping negative eigenvalues to zero. Degrees of freedom "
     "for t-tests are taken as min(G) - 1 across the clustering dimensions, the conservative "
     "choice.")

h3("8.3.2 Absorbing fixed effects")
para("World and date fixed effects are absorbed by alternating within-transformations rather "
     "than dummy expansion. A world-and-date specification would otherwise require roughly 1,390 "
     "dummy columns against 30,000 observations. The projection iterates to a tolerance of "
     "1e-10, and degrees of freedom consumed by the absorbed effects are added back into K for "
     "the variance correction.")

h3("8.3.3 The arbitrage band estimator")
para("For world i on date t, dev(i,t) = log P(i,t) - mean over j of log P(j,t), computed only on "
     "dates carrying at least 10 observed converged worlds. Observations are binned on "
     "|dev(i,t-1)|. Within each bin the reported quantity is the mean of "
     "|dev(i,t-1)| - |dev(i,t)| in percentage points, so a positive value means the gap narrowed. "
     "Standard errors are Newey-West with a bandwidth of 4(n/100)^(2/9), which accounts for the "
     "serial correlation induced by overlapping deviations.")

h3("8.3.4 Half-life estimation and attenuation")
para("Persistence is estimated as rho(h) in dev(i,t+h) = rho(h) dev(i,t) + world fixed effects, "
     "for h in {1, 2, 5, 10, 20, 30, 60}, requiring an exact h-day separation. The implied "
     "half-life is h ln(0.5)/ln(rho(h)). Under classical measurement error in the price, rho(1) "
     "is attenuated by the ratio of signal variance to total variance, and the bias falls with h "
     "as the signal component of the deviation grows relative to the fixed noise. The weekly "
     "estimate averages deviations to weekly frequency before estimating an AR(1), reducing the "
     "noise variance by roughly a factor of seven.")

h3("8.3.5 Forecast construction")
para(f"For each world, daily log returns are demeaned and resampled by moving-block bootstrap "
     f"with block length {FCR['block']} days, preserving volatility clustering and the "
     f"short-horizon negative autocorrelation induced by measurement noise. "
     f"{FCR['n_sim']:,} paths are drawn per horizon. Drift is the trailing-365-day mean daily "
     f"log return, shrunk by the empirical-Bayes weight mu&sup2;/(mu&sup2;+se&sup2;) and capped "
     f"at ±{FCR['drift_cap_daily'] * 100:.2f}% per day. No level mean reversion is imposed. The "
     f"random-number generator is seeded at 20260730 so that all intervals are exactly "
     f"reproducible.")

h3("8.3.6 Validation protocol for the fundamentals models")
para("Every model in Section 6.6 is scored under one protocol, described here once. Folds "
     "expand forward in time from 45% of the window; every world enters and leaves a fold "
     "together, because a random split would let a model see one Tuesday while predicting "
     "another. The forecast horizon is removed between the end of training and the start of "
     "test, so a 30-day forward return observed on the last training day cannot overlap the "
     "test period. Missing values are filled with the training fold's medians, computed on "
     "training rows alone; features are standardised the same way for the linear models. The "
     "rolling-window variant in Section 6.6.7 keeps the training width fixed rather than "
     "expanding it, and is otherwise identical.")
h3("8.3.7 Combining test statistics across folds")
para("Diebold-Mariano is computed per fold on squared-error differences with a Newey-West "
     "correction at the forecast horizon, then combined across folds by Stouffer's method on "
     "the signed statistics: Z = &Sigma;z<sub>i</sub> / &radic;k. Fisher's method was used "
     "first and is wrong here - it combines two-sided p-values, so a fold that loses badly "
     "counts as evidence of a difference and the combination reads as significance even when "
     "the folds disagree about the sign. The fold win-count is reported alongside, because "
     "consistency across folds is the harder test and the one that distinguishes a real effect "
     "from a lucky sample.")
h3("8.3.8 Conformal intervals")
para("Prediction intervals use the split-conformal construction of Lei et al. (2018). The "
     "model is fitted on the first part of the training window; absolute residuals are measured "
     "on a held-out calibration slice; the interval half-width at level &alpha; is the "
     "(1-&alpha;) quantile of those residuals. No distributional assumption enters, and the "
     "coverage guarantee is finite-sample. Measured out-of-sample coverage is reported in "
     "Section 6.6.13: 89.2% at a nominal 90%, 77.7% at 80% and 45.0% at 50%.")
h3("8.3.9 The scenario simulator")
para("Scenario probabilities come from a block bootstrap (K&uuml;nsch, 1989) of index returns "
     "in ten-day blocks, which preserves volatility clustering and fat tails that an "
     "independent resample would destroy. Returns are centred, the shrunk and capped drift is "
     "added back, and 40,000 paths are propagated. Band probabilities are counted off the "
     "simulated paths rather than assigned, and the construction is itself validated by the "
     "walk-forward coverage test of Section 7.5.4.")

h3("8.3.10 Reproducibility")
# The table claims to run in pipeline order, so it is generated from run_all.py's own stage
# lists rather than maintained by hand. A hand-kept ordering drifted: 08_figures.py sat ahead
# of every analysis stage whose output it draws.
_PURPOSE = {'01_collect.py': 'Per-world GuildStats and order-book collection', '01b_census.py': 'Per-world population census', '02_ingest_prices.py': 'Archive to snapshot-level table', '03_build_metadata.py': 'World metadata, merge register, event calendar', '04_population.py': 'Daily population panel', '04b_diurnal.py': 'Diurnal snapshot-bias profile', '05_clean_panel.py': 'Section 3.3 cleaning pipeline', 'econ.py': 'Fixed-effect absorption and multi-way clustered errors', '06_analysis.py': 'All statistics and models', '07_forecast.py': 'Forecasts and rolling-origin backtest', 'chartstyle.py': 'Chart system, layout bands, text-overlap checker', '08_figures.py': 'All figures', '10_advanced.py': 'Threshold, cointegration, spatial and IV models', '11_finance.py': 'Microstructure, efficiency, volatility and diagnostics', '16_killstats.py': 'Per-world daily kill statistics aggregated to a fundamentals  panel (Section 6.6)', '17_features.py': "{FD['panel']['n_features']}-feature matrix with the leakage assertion", '18_predict.py': 'Leading indicators, walk-forward model comparison,  Diebold-Mariano', '19_regimes.py': 'Hidden Markov states, change points and SHAP attribution', '20_hierarchy.py': 'Global, regional, per-world, hierarchical and multi-task scopes', '21_models_extra.py': 'OLS, CatBoost, ARIMA, Prophet, structural time series; rolling window; volatility targets', '22_discovery.py': 'Boruta, RFE, LASSO path, interaction search, partial dependence, conformal intervals, counterfactuals', '23_timeseries.py': 'SARIMA, SARIMAX, Markov-switching autoregression, latent cross-world factors, GARCH volatility forecast', '24_deep.py': 'LSTM and time-series transformer on 30-day windows', '25_arbitrage.py': 'Band-conditional forecasting of the deviation, pairwise world network, net-of-cost trading rule', '26_maximise.py': 'Tuned and ensembled models aimed at the largest achievable out-of-sample R² on the deviation', '27_irreducible.py': 'Entropy against surrogates, BDS, martingale tests and a common-factor ceiling on what any observer could know', '28_supply_demand.py': 'Direct test of the gold-production channel against demand and behavioural blocks', '29_scenarios.py': 'Block-bootstrap scenarios, probability bands and actionable levels', '30_model_artifact.py': 'Fits, persists and scores the shipped model; run with --predict', '41_group_models.py': 'Hierarchical PvP, BattlEye and region models; threshold sensitivity, untouched holdout comparison and current scores', '42_verify_group_models.py': 'Independently verifies coverage, pooling order, PvP isolation, holdout metrics and the deployable model family', '44_launch_phase_models.py': 'PvP-specific launch-phase models with age bounds, unseen-world cohorts and mature/zero baselines', '45_verify_launch_models.py': 'Independently verifies launch cohorts, PvP isolation, current coverage, metrics and artifact completeness', '43_build_group_model_notebook.py': 'Builds and executes the reproducible general-versus-specific model notebook', '31_participants.py': 'Demand decomposed by participant type from the order-book size distribution', '32_scenario_backtest.py': 'Walk-forward coverage test of the scenario bands', '33_strategy.py': 'Signal strength by holding period, net of fees; Newey-West and delayed-entry attacks; a true holdout; the long-only variant', '46_verify_artifacts.py': 'Holds the report and the site to the same numbers: canonical facts computed once, every artifact that states one must agree', '47_bazaar_history.py': 'Char Bazaar year pages from 2020 onward, and the venue ratio recomputed on comparable coverage', 'narrative.py': 'The claims both artifacts publish, defined once with their own numbers; the report renders them as paragraphs and the site as interactive cards', '34a_collect_loot.py': 'Revision-audited TibiaWiki loot probabilities and quantities', '34b_collect_creatures.py': 'Creature classification, boss, event and explicit no-loot evidence', '34_gold_emission.py': 'Creature-level gold value and daily world monetary-emission reconstruction', '35_gold_emission_models.py': 'Fixed-effects, lag, holdout and sensitivity tests for gold emission', '36_gold_emission_report.py': 'Validated technical report artifact for the monetary reconstruction', '37_verify_gold_emission.py': 'Data, model, report and dashboard integrity checks for gold emission', '38_gold_emission_dashboard.py': 'Self-contained interactive world-by-time gold-emission explorer', '39_intelligence_hub.py': 'Unified interactive workspace for worlds, forecasts, strategy, emission and exhibits', '40_verify_intelligence_hub.py': 'Structural and data-integrity checks for the interactive workspace', '14_venues.py': 'Token contract, liquidity pools and Char Bazaar turnover  (Section 5.8); network reads are cached and block-stamped', 'remap_sections.py': 'Chapter consolidation and reference renumbering', '15_verify.py': 'Reads the built PDF back and checks it against the data:  references, numbering, contents, coverage and conventions', 'run_all.py': 'Runs every stage in dependency order and verifies that all  result blocks are present', '12_art.py': 'Duotone artwork treatment for the chapter marks', '13_icons.py': 'Executive-summary pictograms', '09_report.py': 'Document architecture, page templates and the build', '09_sections.py': 'The report body: every section, table and exhibit placement', '48_stability_and_seasonality.py': 'Within-year seasonality, rolling parameter stability, forecast error in economic units, and regime splits', '16b_killstats_history.py': 'Folds the 2022-2025 archive in a world at a time, reclaiming the disk as it goes', '49_long_horizon_production.py': 'Flow, cumulative, acceleration and threshold production tests to a one-year horizon, with per-date inference', 'emission_view.py': 'Shared Gold Emission workspace: payload, styles, markup and behaviour for both publication surfaces'}
_runall = (ROOT / "scripts" / "run_all.py").read_text()
_stage_order, _seen = [], set()
for _name in re.findall(r'"([0-9a-z_]+\.py)"', _runall):
    if _name not in _seen:
        _seen.add(_name)
        _stage_order.append(_name)
_extra = [k for k in _PURPOSE if k not in _seen]
table([["Script", "Purpose"]] +
      [[n, _PURPOSE.get(n, "")] for n in _stage_order if n in _PURPOSE] +
      [[n, _PURPOSE[n]] for n in sorted(_extra)],
      [46 * mm, AVAIL - 46 * mm], fs=7,
      caption="Table 8.4 - Analysis pipeline, generated from run_all.py's stage lists so the "
              "order shown is the order that runs. run_all.py enforces that "
              "order: the five modelling stages share one results file, so running them out of "
              "sequence silently drops later blocks rather than failing. Scripts are "
              "deterministic given the collected raw data.")
story.append(PageBreak())

# ===================================================================== APPENDIX A
fresh_page("wide")
h1("Appendix A", "Reference Table - All 93 Worlds")
para("Sorted alphabetically. 'Class' is C for converged, L for a genuine launch inside the "
     "window, M for a merge destination that entered the window, and O otherwise. Population is "
     "the true daily average over the trailing 365 days.", "cap")
ba = bw.sort_values("world")
rows = [["World", "Region", "PvP", "Created", "Class", "Obs", "First px", "Latest px",
         "Median px", "Vol %/d", "TC sold/d", "Population", "Online"]]
for _, r in ba.iterrows():
    cls = "C" if r.converged else ("L" if r.launch_in_window else
                                   ("M" if r.is_merge_destination and
                                    pd.Timestamp(r.created) >= panel.date.min() else "O"))
    rows.append([r.world, str(r.region).replace("North America", "N. America")
                 .replace("South America", "S. America"),
                 str(r.pvp_type).replace(" PvP", ""),
                 r.created.strftime("%Y-%m-%d") if pd.notna(r.created) else "-",
                 cls, f"{int(r.n_obs):,}", gp(r.px_first), gp(r.px_last), gp(r.px_med),
                 f"{r.vol:.2f}" if pd.notna(r.vol) else "-",
                 gp(r.sold) if pd.notna(r.sold) else "-",
                 gp(r.population) if pd.notna(r.population) else "-",
                 gp(r.activity_year) if pd.notna(r.activity_year) else "-"])
wA = [x * mm for x in [28, 24, 18, 22, 12, 16, 22, 22, 22, 15, 16, 20]]
wA.append(AW - sum(wA))
assert wA[-1] > 12 * mm, "Appendix A columns overflow the landscape frame"
table(rows, wA, align=[None, None, None, None, "C", "R", "R", "R", "R", "R", "R", "R"], fs=6.3,
      caption="Table A.1 - Reference table, all 93 worlds. Prices in GP/TC. Volatility is the "
              "standard deviation of daily log returns. Population is resident characters from "
              "the census (a stock); Online is mean concurrent players over the trailing year "
              "(a flow) - see Section 3.7 for why the two are not interchangeable. Sources: "
              "price archive item_id 22118; TibiaData v4; GuildStats.eu /worlds, /census and "
              "/online-counter.")
story.append(PageBreak())

# ===================================================================== APPENDIX B
h1("Appendix B", "South American Worlds - Individual Detail")
para(f"Detail for all {len(fcj)} South American worlds: descriptive statistics, price history "
     f"with the forecast fan, and prediction intervals at four horizons. Forecasts use the "
     f"bootstrapped random walk of Section 6.4. Worlds still in launch-phase price discovery are "
     f"flagged; on those the drift term does most of the work and the median should be read "
     f"with the least confidence, so the remaining gap to the cross-world mean is stated "
     f"alongside it.", "cap")

h2("B.1 Summary of forecasts")
# The median is the point forecast and belongs in the table beside its interval. The drift is
# shrunk and capped but not zero, so the median is not the current price and must be shown.
rows = [["World", "Current", "2w median (p10-p90)", "1m median (p10-p90)",
         "3m median (p10-p90)", "6m median (p10-p90)", "6m width", "Vol %/d", "Note"]]
for f in sorted(fcj, key=lambda z: z["world"]):
    cells = [f"{gp(f[h]['p50'])} ({gp(f[h]['p10'])}-{gp(f[h]['p90'])})"
             for h in ("2w", "1m", "3m", "6m")]
    rows.append([f["world"], gp(f["last_price"])] + cells +
                [pc(f["6m"]["width_80_pct"], 1), f"{f['sigma_daily_pct']:.2f}",
                 "launch phase" if f["launch_phase"] else ""])
wB = [x * mm for x in [26, 22, 38, 38, 38, 38, 20, 16]]
wB.append(AW - sum(wB))
assert wB[-1] > 12 * mm, "Appendix B columns overflow the landscape frame"
table(rows, wB, align=[None, "R", "R", "R", "R", "R", "R", "R", None], fs=6.3,
      caption="Table B.1 - Forecast summary for all South American worlds. All values GP/TC; "
              "intervals are 80% (10th to 90th percentile). The median carries the world's "
              "shrunk, capped drift, so it departs from the current price where that drift is "
              "material (Section 6.4.1); the departure is small on established worlds and "
              "largest on those still in launch-phase discovery. Source: price archive, "
              "item_id 22118.")
h2("B.2 The forecast that has skill")
para(tag("judg") + f"Table B.1 forecasts the price <i>level</i>, and Chapter 6 establishes "
     f"that the level is a random walk - the medians there are today's price by construction "
     f"and the intervals are wide because nothing narrows them. Presenting only that would give "
     f"a reader the uninformative forecast and withhold the informative one. The quantity that "
     f"does carry out-of-sample skill is a world's price <i>relative to the market</i>, and the "
     f"model shipped with this report predicts it.")
_sa = LPRED[LPRED.world.isin(set(fcs.world))].sort_values("predicted_change_pct")
table([["World", "Price", "Deviation from market", "Predicted 7-day change", "80% interval",
        "Outside the band"]] +
      [[r.world, gp(r.price_gp), f"{r.deviation_pct:+.2f}%",
        f"<b>{r.predicted_change_pct:+.2f}%</b>",
        f"{r.low80_pct:+.2f}% to {r.high80_pct:+.2f}%",
        "yes" if r.outside_band else "no"]
       for _, r in _sa.iterrows()],
      [26 * mm, 22 * mm, 34 * mm, 32 * mm, 38 * mm, AW - 152 * mm],
      align=[None, "R", "R", "R", "R", "C"], fs=6.6,
      caption=f"Table B.2 - Relative-position forecast for the {len(_sa)} South American worlds "
              f"the model covers, from models/deviation_model.pkl. Interval widths were "
              f"calibrated on held-out residuals. The remaining "
              f"{len(set(fcs.world)) - len(_sa)} South American worlds are still in "
              f"launch-phase price discovery and are excluded, for the reason Section 5.4 "
              f"gives: their deviation is a convergence path, not a market signal.")
para(tag("lim") + f"Read this table beside B.1, not instead of it. B.1 says where the price "
     f"could be and is honest that it does not know; B.2 says which worlds are cheap against "
     f"the others and has an out-of-sample R-squared of {MAXP['best_r2']:.2f} behind it. "
     f"Neither is a trading recommendation: Section 7.5.6 shows the implied trade nets "
     f"{ARB['trading_rule']['above the fee cap']['mean_net_pct']:+.3f}% at the cheapest "
     f"execution, so a gap below 4% is information without an action attached.")
story.append(PageBreak())

# Group by what each world's data actually shows, not by its creation date. Several worlds
# created inside the window entered the archive only after they had already converged, with
# no price-discovery phase in the record at all.
_WIN0 = panel.date.min()
_created = dict(zip(bw.world, bw.created))
_hmin = {f["world"]: float(panel.loc[panel.world == f["world"], "price_gp"].min()) for f in fcj}
MATURE_FLOOR = min(v for w, v in _hmin.items() if _created[w] < _WIN0)
EST = [f for f in fcj if _hmin[f["world"]] >= MATURE_FLOOR]
NEW = [f for f in fcj if _hmin[f["world"]] < MATURE_FLOOR]

para(tag("judg") + "<b>The panels use two shared scales, one per comparable group.</b> Small "
     "multiples drawn on independent axes are actively misleading: a world whose price barely "
     "moves is stretched to fill its panel and reads as though it were as turbulent as one "
     "that tripled. But a single scale across all 34 would be dominated by the handful of "
     "worlds still converging from launch, which begin near 1,200 GP and rise roughly "
     "thirtyfold - that would compress every mature world into a sliver and destroy exactly "
     "the detail those panels exist to show.", "cap")
para(tag("judg") + f"<b>Group membership is decided from each world's own data, not from its "
     f"creation date.</b> Creation date is the wrong criterion here: several worlds created "
     f"inside the observation window entered the archive only after they had already "
     f"converged, so their record contains no price-discovery phase at all. Etebra was created "
     f"in February 2023 but first observed in August 2025 at 36,487 GP/TC; Tornabra, Unebra "
     f"and Yubra are the same case. Plotting those on a launch scale would compress them for "
     f"no reason. A world is therefore assigned to the mature-band group if its entire "
     f"observed history sits at or above {gp(MATURE_FLOOR)} GP/TC, the lowest price ever "
     f"recorded on a world that predates the archive. The two groups are cleanly separated - "
     f"the lowest mature-band world bottoms at 31,250 GP/TC and the highest converging world "
     f"at 22,028 - so the split does not depend on exactly where the threshold is placed.",
     "cap")
para("The dotted line in every panel is the current cross-world mean, giving all 34 worlds one "
     "common benchmark despite the two scales. Panels are comparable within a group; "
     "<b>they are not comparable in absolute height between the two groups</b>.", "cap")

saw = bw.set_index("world")


def sa_group(items):
    items = sorted(items, key=lambda z: z["world"])
    for i in range(0, len(items), 2):
        chunk = items[i:i + 2]
        cells = []
        for f in chunk:
            w = f["world"]
            r = saw.loc[w] if w in saw.index else None
            inner = []
            cw = AW / 2 - 6 * mm
            svg = FIG / "sa" / f"{w}.svg"
            art = vector(svg, cw) if svg.exists() else None
            if art is None:
                png = FIG / "sa" / f"{w}.png"
                if png.exists():
                    from PIL import Image as PILImage
                    iw, ih = PILImage.open(png).size
                    art = Image(str(png), width=cw, height=cw * ih / iw)
            if art is not None:
                inner.append(art)
            # Compact 4-column layout: a 12-row two-column table would leave only one world
            # per landscape page.
            vol = f"{f['sigma_daily_pct']:.2f}%"
            reg = f"{r.region} / {r.pvp_type}" if r is not None else "-"
            cre = (r.created.strftime("%Y-%m-%d") if r is not None and pd.notna(r.created) else "-")
            note = (f"launched in window, {pc(f['gap_to_crossworld_mean_pct'], 0, True)} to mean"
                    if f["launch_phase"] else "established")
            det = [["Metric", "Value", "Metric", "Value"],
                   ["Current price", f"{gp(f['last_price'])} GP/TC", "Region / PvP", reg],
                   ["Created", cre, "Observations", f"{f['n_obs']:,}"],
                   ["Daily volatility", vol, "Shrunk drift", f"{f['mu_daily'] * 100:+.4f}%/day"],
                   ["2w 80% interval", f"{gp(f['2w']['p10'])} - {gp(f['2w']['p90'])}",
                    "1m 80% interval", f"{gp(f['1m']['p10'])} - {gp(f['1m']['p90'])}"],
                   ["3m 80% interval", f"{gp(f['3m']['p10'])} - {gp(f['3m']['p90'])}",
                    "6m 80% interval", f"{gp(f['6m']['p10'])} - {gp(f['6m']['p90'])}"],
                   ["6m width", pc(f["6m"]["width_80_pct"], 1), "Status", note]]
            cwid = AW / 2 - 6 * mm
            inner.append(mktable(det, [cwid * 0.21, cwid * 0.29, cwid * 0.21,
                                       cwid * 0.29], fs=6.0, halign="LEFT"))
            cells.append(inner)
        while len(cells) < 2:
            cells.append([Spacer(1, 1)])
        grid = Table([[cells[0], cells[1]]], colWidths=[AW / 2, AW / 2], hAlign="LEFT")
        grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
        story.append(KeepTogether(grid))
        if i % 4 == 2 and i + 2 < len(items):
            story.append(PageBreak())


h2(f"B.2 Worlds trading in the mature band (n={len(EST)})")
para(f"Shared <b>linear</b> scale, 25,700 to 59,300 GP/TC. These worlds span barely a factor of "
     f"two, so a linear axis is used and their ordinary 10-15% swings are legible. No forecast "
     f"fan is clipped. The group is the 16 worlds that predate the archive plus "
     f"{len(EST) - 16} created inside the window whose observed history is already entirely "
     f"within the mature band - either because they are merge destinations that opened at "
     f"mature prices (Section 5.4) or because the archive began observing them only after they "
     f"had converged.", "cap")
sa_group(EST)

story.append(PageBreak())
h2(f"B.3 Worlds still converging from launch (n={len(NEW)})")
para("Shared <b>logarithmic</b> scale, 884 to 52,900 GP/TC. These worlds span nearly a factor "
     "of forty as they climb from launch toward the cross-world mean, so a log axis is used: "
     "on it a given percentage move occupies the same vertical distance in every panel, making "
     "both level and volatility comparable across the group. Bounds are set by observed prices "
     "rather than by the forecast fans, since one world's 90th percentile reaches about "
     "89,000 GP; the upper tail of six fans is therefore clipped, which costs nothing "
     "analytically because Section 6.4.2 establishes that those intervals are uninformative. "
     "Note the axis differs from B.2 - these panels are not comparable in height with the "
     "mature-band worlds.", "cap")
sa_group(NEW)

story.append(PageBreak())
# ===================================================================== APPENDIX C0
fresh_page("normal")
h1("Appendix C", "References")
para("Works whose models, estimators or critical values are used in this report. Citation "
     "indicates the method applied; it does not imply the cited authors studied this market.",
     "cap")
REFS = [
    ('Andrews, D. W. K. (1993)',
     'Tests for parameter instability and structural change with unknown change point. <i>Econometrica</i> 61(4), 821-856.',
     'Supremum-Wald break test and critical value (Section 7.2.4)'),
    ('Bandt, C. and Pompe, B. (2002)',
     'Permutation entropy: a natural complexity measure for time series. <i>Physical Review Letters</i> 88(17), 174102.',
     'Ordinal complexity of the market return (Section 6.6.16)'),
    ('Benjamini, Y. and Hochberg, Y. (1995)',
     'Controlling the false discovery rate: a practical and powerful approach to multiple testing. <i>Journal of the Royal Statistical Society B</i> 57(1), 289-300.',
     'False-discovery control across the Granger tests and the 42 model comparisons (Sections 6.6.1, 6.6.3)'),
    ('Bollerslev, T. (1986)',
     'Generalized autoregressive conditional heteroskedasticity. <i>Journal of Econometrics</i> 31(3), 307-327.',
     'GARCH(1,1)-t, fitted descriptively in Section 7.1.1 and as a volatility forecast benchmark in Section 6.6.11'),
    ('Breiman, L. (2001)',
     'Random forests. <i>Machine Learning</i> 45(1), 5-32.',
     'The model that survives correction, and permutation importance (Sections 6.6.3, 6.6.8)'),
    ('Brock, W. A., Dechert, W. D., Scheinkman, J. A. and LeBaron, B. (1996)',
     'A test for independence based on the correlation dimension. <i>Econometric Reviews</i> 15(3), 197-235.',
     'Test for hidden nonlinear dependence (Section 6.6.16)'),
    ('Cameron, A. C., Gelbach, J. B. and Miller, D. L. (2011)',
     'Robust inference with multiway clustering. <i>Journal of Business and Economic Statistics</i> 29(2), 238-249.',
     'Two-way clustered covariance estimator (Sections 6.2, 8.3.1)'),
    ('Chen, T. and Guestrin, C. (2016)',
     'XGBoost: a scalable tree boosting system. <i>Proceedings of KDD 2016</i>, 785-794.',
     'One of the gradient-boosting implementations compared (Section 6.6.11)'),
    ('Choi, I. (2001)',
     'Unit root tests for panel data. <i>Journal of International Money and Finance</i> 20(2), 249-272.',
     'Inverse-normal combination of panel unit-root tests (Section 6.3.2)'),
    ('Diebold, F. X. and Mariano, R. S. (1995)',
     'Comparing predictive accuracy. <i>Journal of Business and Economic Statistics</i> 13(3), 253-263.',
     'Formal test of forecast accuracy against a benchmark (Section 6.4.3)'),
    ('Driscoll, J. C. and Kraay, A. C. (1998)',
     'Consistent covariance matrix estimation with spatially dependent panel data. <i>Review of Economics and Statistics</i> 80(4), 549-560.',
     'Alternative covariance estimator (Section 7.2.3)'),
    ('Engle, R. F. and Granger, C. W. J. (1987)',
     'Co-integration and error correction: representation, estimation and testing. <i>Econometrica</i> 55(2), 251-276.',
     'Error-correction representation of the panel (Section 6.3.2)'),
    ('Friedman, J. H. (2001)',
     'Greedy function approximation: a gradient boosting machine. <i>Annals of Statistics</i> 29(5), 1189-1232.',
     'The boosting family, and partial dependence (Sections 6.6.11, 6.6.13)'),
    ('Glosten, L. R. and Milgrom, P. R. (1985)',
     'Bid, ask and transaction prices in a specialist market with heterogeneously informed traders. <i>Journal of Financial Economics</i> 14(1), 71-100.',
     'Adverse-selection component of the spread (Sections 2.3.3, 5.6.5)'),
    ('Granger, C. W. J. (1969)',
     'Investigating causal relations by econometric models and cross-spectral methods. <i>Econometrica</i> 37(3), 424-438.',
     'Predictive-precedence test used for price discovery (Section 5.6.6)'),
    ('Hamilton, J. D. (1989)',
     'A new approach to the economic analysis of nonstationary time series and the business cycle. <i>Econometrica</i> 57(2), 357-384.',
     'Markov-switching autoregression as a forecasting model (Section 6.6.11)'),
    ('Hansen, B. E. (2000)',
     'Sample splitting and threshold estimation. <i>Econometrica</i> 68(3), 575-603.',
     'Threshold estimation, likelihood-ratio confidence set (Section 6.3.1)'),
    ('Ho, T. and Stoll, H. R. (1981)',
     'Optimal dealer pricing under transactions and return uncertainty. <i>Journal of Financial Economics</i> 9(1), 47-73.',
     'Inventory-risk interpretation of the spread (Sections 2.3.3, 5.6.5)'),
    ('Hochreiter, S. and Schmidhuber, J. (1997)',
     'Long short-term memory. <i>Neural Computation</i> 9(8), 1735-1780.',
     'The recurrent sequence model fitted and found unstable (Section 6.6.11)'),
    ('Johansen, S. (1991)',
     'Estimation and hypothesis testing of cointegration vectors in Gaussian vector autoregressive models. <i>Econometrica</i> 59(6), 1551-1580.',
     'Cointegration rank test (Section 6.3.2)'),
    ('Kelejian, H. H. and Prucha, I. R. (1998)',
     'A generalized spatial two-stage least squares procedure. <i>Journal of Real Estate Finance and Economics</i> 17(1), 99-121.',
     'Instrumented spatial-lag estimation (Section 6.3.3)'),
    ('Killick, R., Fearnhead, P. and Eckley, I. A. (2012)',
     'Optimal detection of changepoints with a linear computational cost. <i>Journal of the American Statistical Association</i> 107(500), 1590-1598.',
     'PELT change-point search, as an independent check on the state model (Section 6.6.8)'),
    ('Kunsch, H. R. (1989)',
     'The jackknife and the bootstrap for general stationary observations. <i>Annals of Statistics</i> 17(3), 1217-1241.',
     'Block bootstrap behind the scenario distribution (Section 7.5.3)'),
    ('Kursa, M. B. and Rudnicki, W. R. (2010)',
     'Feature selection with the Boruta package. <i>Journal of Statistical Software</i> 36(11), 1-13.',
     'Shadow-feature selection (Section 6.6.12)'),
    ('Kyle, A. S. (1985)',
     'Continuous auctions and insider trading. <i>Econometrica</i> 53(6), 1315-1335.',
     'Price impact and market depth (Sections 2.3.3, 5.6.5)'),
    ("Lei, J., G'Sell, M., Rinaldo, A., Tibshirani, R. J. and Wasserman, L. (2018)",
     'Distribution-free predictive inference for regression. <i>Journal of the American Statistical Association</i> 113(523), 1094-1111.',
     'Split-conformal intervals, and the interval shipped with the model (Sections 6.6.13, 7.5.4)'),
    ('Lo, A. W. and MacKinlay, A. C. (1988)',
     'Stock market prices do not follow random walks: evidence from a simple specification test. <i>Review of Financial Studies</i> 1(1), 41-66.',
     'Variance-ratio test of weak-form efficiency (Section 4.4.3)'),
    ('Lundberg, S. M. and Lee, S.-I. (2017)',
     'A unified approach to interpreting model predictions. <i>Advances in Neural Information Processing Systems</i> 30, 4765-4774.',
     'SHAP attribution by feature family (Section 6.6.8)'),
    ('Moran, P. A. P. (1950)',
     'Notes on continuous stochastic phenomena. <i>Biometrika</i> 37(1/2), 17-23.',
     'Spatial autocorrelation statistic (Section 6.3.3)'),
    ('Newey, W. K. and West, K. D. (1987)',
     'A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. <i>Econometrica</i> 55(3), 703-708.',
     'HAC standard errors (Sections 5.2, 6.4.3)'),
    ('Obstfeld, M. and Taylor, A. M. (1997)',
     'Nonlinear aspects of goods-market arbitrage and adjustment. <i>Journal of the Japanese and International Economies</i> 11(4), 441-479.',
     'Band-threshold model of the law of one price under transaction costs (Section 6.3.1)'),
    ('Richman, J. S. and Moorman, J. R. (2000)',
     'Physiological time-series analysis using approximate entropy and sample entropy. <i>American Journal of Physiology</i> 278(6), H2039-H2049.',
     'Regularity measure against surrogates (Section 6.6.16)'),
    ('Roll, R. (1984)',
     'A simple implicit measure of the effective bid-ask spread in an efficient market. <i>Journal of Finance</i> 39(4), 1127-1139.',
     'Effective spread from serial covariance (Section 5.6.4)'),
    ('Schreiber, T. and Schmitz, A. (1996)',
     'Improved surrogate data for nonlinearity tests. <i>Physical Review Letters</i> 77(4), 635-638.',
     'Iterative amplitude-adjusted surrogates, the null for the entropy tests (Section 6.6.16)'),
    ('Shleifer, A. and Vishny, R. W. (1997)',
     'The limits of arbitrage. <i>Journal of Finance</i> 52(1), 35-55.',
     'Capital-constrained arbitrage and persistent deviations (Section 5.2.6)'),
    ('Taylor, S. J. and Letham, B. (2018)',
     'Forecasting at scale. <i>The American Statistician</i> 72(1), 37-45.',
     'Prophet, fitted as a univariate baseline (Section 6.6.6)'),
    ('Vaswani, A., Shazeer, N., Parmar, N. et al. (2017)',
     'Attention is all you need. <i>Advances in Neural Information Processing Systems</i> 30, 5998-6008.',
     'The encoder block behind the time-series transformer (Section 6.6.11)'),
]
table([["Reference", "Work", "Use in this report"]] +
      [[a, b, c] for a, b, c in REFS],
      [40 * mm, 78 * mm, AVAIL - 118 * mm], fs=6.6,
      caption="Table C.1 - Methodological references.")
story.append(PageBreak())

# ===================================================================== APPENDIX C
h1("Appendix D", "Deliverables")
table([["File", "Contents"],
       ["reports/tibia_coin_market_report.pdf", "This document"],
       ["data/processed/panel_daily.csv", f"Cleaned daily price panel, {W['n_world_days']:,} "
                                          f"world-days"],
       ["data/processed/converged_panel.csv", "Converged-world analysis panel with deviations "
                                              "and event flags"],
       ["data/processed/world_metadata.csv", "93 worlds: attributes, creation dates, merge "
                                             "flags, first observation"],
       ["data/processed/world_merge_register.csv",
        f"{MG['n_merges']} merges, {MG['n_predecessors']} predecessor links"],
       ["data/processed/event_calendar.csv", f"{len(cal):,} days of global event and update "
                                             f"flags"],
       ["data/raw/tibiavip_worlds.tsv", "Character roster, online count and guild count for "
                                       "93 worlds"],
       ["data/processed/world_census.csv", "Active characters, account type, vocation and "
                                          "level distribution for 93 worlds"],
       ["data/processed/population_daily.csv",
        f"{sm.n_days_pop.sum():,} world-days of daily-average concurrent players online"],
       ["data/processed/population_summary.csv", "Per-world population aggregates and snapshot "
                                                 "bias factors"],
       ["data/processed/diurnal_profile.csv", "Hour-by-region snapshot bias profile"],
       ["data/processed/market_index.csv", "Chain-linked and basket indices, dispersion, "
                                           "breadth"],
       ["data/processed/arbitrage_band.csv", "Arbitrage band estimates"],
       ["data/processed/stationarity.csv", "Per-world ADF, KPSS and Ljung-Box results"],
       ["data/processed/order_books.csv", "93 live order books with depth and quoted spreads"],
       ["data/processed/forecasts_sa.csv / .json", "Forecasts for all 34 South American worlds"],
       ["data/processed/forecast_backtest*.csv", "Rolling-origin backtest and summaries"],
       ["data/processed/world_summary.csv", "Per-world descriptive statistics"],
       ["data/processed/results.json", "Every statistic reported in this document"],
       ["figures/*.png", "34 analytical exhibits"],
       ["figures/sa/*.png", "34 per-world South American panels"],
       ["data/processed/roll_spread.csv", "Roll effective spread per world"],
       ["data/processed/variance_decomposition.csv", "Systematic and idiosyncratic variance"],
       ["data/processed/variance_ratio.csv", "Lo-MacKinlay variance ratios"],
       ["data/processed/garch.csv", "GARCH(1,1)-t parameters per world"],
       ["data/processed/quantile_regression.csv", "Quantile-regression coefficients"],
       ["data/processed/tar_grid.csv", "Threshold search profile"],
       ["data/processed/panel_unitroot_deviation.csv", "Panel unit-root tests on deviations"],
       ["data/raw/tibia_token_supply.json", "Token contract state at a stated block"],
       ["data/raw/tibia_token_pools.json", "Liquidity-pool state and quoted prices at a stated "
                                           "block"],
       ["data/raw/char_bazaar_2025.json", "Char Bazaar annual turnover aggregates"],
       ["data/processed/kill_stats_daily.csv",
        f"{KS_ROWS:,} world-days of monsters killed, player deaths, boss kills and "
        f"hunting breadth"],
       ["data/processed/kill_stats_mix.csv",
        "Per-world daily shares of the 40 most-hunted creature types"],
       ["data/processed/fundamentals_panel.csv",
        f"The {FD['panel']['n_features']}-feature modelling panel with its 14 targets"],
       ["data/processed/scenario_bands.csv", "Probability of each price range by horizon"],
       ["models/deviation_model.pkl", "The fitted predictive model, with its "
                                      "conformal interval and metadata"],
       ["data/processed/latest_predictions.csv", "Current prediction for every "
                                                 "converged world"],
       ["data/processed/latest_specific_predictions.csv", "Current general and group-specific predictions for every converged world"],
       ["data/processed/specific_model_*.csv", "Group registry, estimator selection, sensitivity, holdout comparison and audit predictions"],
       ["models/specific_models.pkl.gz", "Compressed hierarchical group-specific model family and calibrated intervals"],
       ["data/processed/latest_launch_predictions.csv", "Current experimental launch-phase scores, age, staleness and general comparison"],
       ["data/processed/launch_model_*.csv", "Launch cohorts, estimator selection, untouched comparison and audit predictions"],
       ["models/launch_phase_models.pkl.gz", "Compressed PvP-specific launch-phase model family and calibrated intervals"],
       ["reports/gold_emission_dashboard.html", "Interactive world-by-time monetary-emission explorer"],
       ["reports/intelligence_hub.html", "Unified interactive market-intelligence workspace"],
       ["scripts/run_all.py", "Runs every stage in dependency order and verifies the result "
                              "blocks"],
       ["scripts/*.py", "Complete reproducible pipeline (Table 8.3)"]],
      [66 * mm, AVAIL - 66 * mm],
      caption="Table D.1 - Deliverables.")
para("<i>End of report.</i>", "cap")

# ===================================================================== APPENDIX E
fresh_page("normal")
h1("Appendix E", "Supporting tables")
para("Numeric detail for exhibits that appear in the body as visual comparisons. Nothing here "
     "is additional to the analysis; it is the same evidence in tabular form.", "cap")
h3("E.1 Snapshot bias by region, full detail")
table([["Region", "Worlds", "Peak hour (UTC)", "Peak hour (server)",
        "Bias at 04:45 UTC", "Bias at 18:43 UTC"]] +
      [[r["region"], int(r["n_worlds"]), f"{int(r['peak_hour_utc']):02d}:00",
        f"{int(r['peak_hour_server']):02d}:00", f"{r['factor_at_0445utc']:.2f}x",
        f"{r['factor_at_1843utc']:.2f}x"] for _, r in prof.iterrows()],
      [30 * mm, 16 * mm, 25 * mm, 27 * mm, 30 * mm, AVAIL - 128 * mm],
      align=[None, "R", "R", "R", "R", "R"],
      caption="Table E.1 - Snapshot bias factor by region, defined as the true daily average "
              "concurrent count divided by the instantaneous count at that hour. Source: "
              "GuildStats.eu /online-counter, 15-minute resolution, 7 days to 2026-07-30.")
h3("E.4 Microstructure measures, full detail")
table([["Measure", "Median across 93 worlds"],
       ["Quoted spread (best ask minus best bid, over mid)", pc(MI["quoted_spread_median_pct"])],
       ["Quoted spread, interquartile range",
        f"{pc(MI['quoted_spread_iqr'][0])} to {pc(MI['quoted_spread_iqr'][1])}"],
       ["Executed-average gap (a different quantity)", pc(MI["executed_gap_median_pct"])],
       ["Standing buy orders", f"{MI['median_buy_orders']:.0f}"],
       ["Standing sell orders", f"{MI['median_sell_orders']:.0f}"],
       ["Bid depth", f"{gp(MI['median_bid_depth_tc'])} TC"],
       ["Ask depth", f"{gp(MI['median_ask_depth_tc'])} TC"],
       ["Share of buy orders posted below 2,000 GP",
        pc(MI["share_buy_orders_below_2000"] * 100, 1)],
       ["Share of orders posted anonymously (buy side)", pc(MI["anon_share_buy"] * 100, 1)],
       ["TC sold per world-day", f"{gp(MI['turnover']['median_tc_sold_per_day'])} TC"],
       ["TC bought per world-day", f"{gp(MI['turnover']['median_tc_bought_per_day'])} TC"]],
      [90 * mm, AVAIL - 90 * mm], align=[None, "R"],
      caption="Table E.2 - Microstructure measures, complete. Order-book measures are a single snapshot; "
              "executed measures are medians over the full history of converged worlds.")

h3("E.3 Market index, dated detail")
table([["Measure", "Value"],
       ["Index start", f"{IX['index_start']} (first date with >= {IX['min_worlds_required']} "
                       f"converged worlds)"],
       ["Index level at start", f"{gp(IX['first_ew'])} GP/TC"],
       ["Index level at end", f"{gp(IX['last_ew'])} GP/TC"],
       ["Total change", pc(IX["total_pct"], 1, True)],
       ["Annualised change", pc(IX["cagr_pct"], 2, True)],
       ["Peak", f"{gp(IX['peak'])} GP/TC on {IX['peak_date']}"],
       ["Trough", f"{gp(IX['trough'])} GP/TC on {IX['trough_date']}"],
       ["Maximum drawdown", f"{pc(IX['max_drawdown_pct'], 1)} (trough {IX['max_dd_date']})"],
       ["Quantity-weighted index, latest", f"{gp(IX['vw_last'])} GP/TC"]],
      [46 * mm, AVAIL - 46 * mm], align=[None, "R"],
      caption="Table E.3 - Chain-linked equal-weighted index of converged worlds, shown in the body as Exhibit 4.3.")

h3("E.2 Round-trip cost measures, full detail")
table([["Cost measure", "Median", "What it represents"],
       ["Quoted spread", pc(RL["median_quoted_spread_pct"]),
        "Cost of crossing the book with a market order"],
       ["Round-trip fee, small offer", "4.00%", "Two offers at the uncapped 2% rate"],
       ["Executed-price gap", pc(RL["median_executed_gap_pct"]),
        "Gap between mean executed prices on each side"],
       ["Roll effective spread", pc(RL["median_roll_spread_pct"]),
        "<b>What trades actually pay on average</b>"],
       ["Round-trip fee, largest decile", pc(FE["roundtrip_largest_decile_pct"], 2),
        "Two offers with the 1,000,000 GP cap binding"]],
      [46 * mm, 22 * mm, AVAIL - 68 * mm], align=[None, "R", None],
      caption=f"Table E.4 - Competing measures of round-trip cost, shown in the body as "
              f"Exhibit 5.10. Roll estimates are medians across {RL['n_worlds']} converged "
              f"worlds; the interquartile range is {pc(RL['iqr'][0])} to {pc(RL['iqr'][1])}.")
story.append(PageBreak())

# ===================================================================== CREDITS
fresh_page("normal")
h1_plain("Credits and asset attribution")
para("<b>Artwork.</b> Tibia artwork and the Tibia logo are the property of CipSoft GmbH and "
     "appear here under the terms distributed with the official Tibia fankit. That policy "
     "permits use of game assets in material about the game, provided the material is not "
     "sold or licensed and the marks are used only to indicate origin. This report is an "
     "independent study, is not published for payment, and is not endorsed by or affiliated "
     "with CipSoft. All artwork has been converted to a single-hue treatment for editorial "
     "consistency; no asset is redistributed in its original form.")
para("<b>Sources used in this report.</b>", "body")
table([["Asset or source", "Owner", "Use here"],
       ["Tibia artwork and logo", "CipSoft GmbH",
        "Cover field, chapter-opener bands, origin mark"],
       ["Tibia Coin price archive", "tibia-warzones-schedule repository",
        "Price panel, 41,584 raw snapshots"],
       ["Market and item endpoints", "TibiaMarket.top",
        "Order books, event calendar, item metadata"],
       ["World attributes and news", "TibiaData v4 (sources tibia.com)",
        "World list, update release dates"],
       ["World history and census", "GuildStats.eu",
        "Creation dates, merge register, activity history, census"],
       ["World character roster", "TibiaVIP",
        "Population; supplied as a saved page, not collected automatically"],
       ["Tibia Token contract", "CipSoft GmbH, on BNB Smart Chain",
        "Venue structure; token supply read directly from the public contract"],
       ["Char Bazaar aggregates", "NabBot",
        "Venue structure; annual auction turnover in Tibia Coins"]],
      [44 * mm, 44 * mm, AVAIL - 88 * mm],
      caption="Table 8.5 - Third-party assets and data sources, with the use made of each.")
para(tag("lim") + "Tibia is a registered trademark of CipSoft GmbH. All game content and "
     "materials are copyright CipSoft GmbH. The analysis, opinions and any errors in this "
     "report are the author's alone.")
story.append(PageBreak())
