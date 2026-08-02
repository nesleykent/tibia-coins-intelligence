"""Decompose demand for Tibia Coins by participant type.

The report has treated demand as one variable. Economically it is a sum of demands with
different motives, and the participants on each side face different prices:

    total demand = consumption + investment + arbitrage + RMT

A player converting money into gold is on the *supply* side of the Market - they sell coins for
gold. A player buying premium features is on the demand side, and so is a speculator, and so is
a farmer converting gold into coins into money. These have different stimuli, so they should
leave different traces.

Identification comes from size. The Store prices its goods in coins, and those prices are known:
premium time, mounts, outfits and boosts fall in a narrow band. An order sized for a month of
premium is almost certainly consumption; an order sized in the tens of thousands is not, because
nobody consumes at that rate. That gives an economically motivated cut rather than a statistical
one, and the shares that follow are bounded by it rather than asserted.

The mapping is a hypothesis, not a measurement, and the section that reports it says so. What is
measured is the size distribution, the imbalance within each band, and how each band responds to
the stimulus its supposed occupant should react to.

    python scripts/31_participants.py
"""
import json, pathlib, warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

lo = pd.read_csv(P / "live_offers.csv")
R = json.load(open(P / "results.json"))
FE = R["fees"]
lo["is_buy"] = lo.side.eq("buyers")
print(f"live order book: {len(lo):,} offers across {lo.world.nunique()} worlds")

# Store prices in Tibia Coins, from the documented catalogue. These set the bands: an order that
# buys roughly one purchase is consumption-shaped, and one that buys hundreds is not.
STORE = {"30 days of premium": 250, "a mount or outfit": 750,
         "a large boost bundle": 1500}
CAP_LOT = FE["cap_binds_at_lot_tc"]

BANDS = [
    ("Consumption-shaped", 0, 500,
     "One or two Store purchases; the size a player buying premium would post"),
    ("Heavy consumption", 500, 1500,
     "Several purchases at once, or a season of premium bought ahead"),
    ("Above the fee cap", 1500, 10000,
     f"Large enough that the {FE['cap_gp']:,} GP fee cap binds ({CAP_LOT:,.0f} TC), which is "
     f"where arbitrage and speculation become cost-efficient"),
    ("Wholesale", 10000, np.inf,
     "Tens of thousands of coins; consistent with converting money to gold at scale, or with "
     "an inventory position"),
]


def band_of(a):
    for i, (name, lo_, hi_, _) in enumerate(BANDS):
        if lo_ <= a < hi_:
            return name
    return BANDS[-1][0]


lo["band"] = lo.amount.map(band_of)
rows = []
for name, lo_, hi_, note in BANDS:
    b = lo[lo.band == name]
    if not len(b):
        continue
    buy, sell = b[b.is_buy], b[~b.is_buy]
    rows.append({
        "band": name, "range_tc": f"{lo_:,.0f}-{'' if np.isinf(hi_) else f'{hi_:,.0f}'}",
        "n_offers": len(b), "share_of_offers": len(b) / len(lo),
        "tc_in_band": b.amount.sum(), "share_of_tc": b.amount.sum() / lo.amount.sum(),
        "n_buy": len(buy), "n_sell": len(sell),
        "buy_share_of_offers": len(buy) / len(b),
        "tc_buy": buy.amount.sum(), "tc_sell": sell.amount.sum(),
        "buy_share_of_tc": buy.amount.sum() / max(1, b.amount.sum()),
        "median_size": float(b.amount.median()),
        "median_fee_rate_pct": float(b.eff_rate_pct.median()),
        "note": note})
bands = pd.DataFrame(rows)
bands.to_csv(P / "participant_bands.csv", index=False)
print("\n[BANDS] the order book by size, and the balance within each")
print(bands[["band", "n_offers", "share_of_tc", "buy_share_of_tc",
             "median_size", "median_fee_rate_pct"]].round(3).to_string(index=False))

# The asymmetry that matters: who is buying and who is selling, weighted by coins rather than by
# order count, because a thousand tiny bids are not a thousand coins.
tot_buy, tot_sell = lo[lo.is_buy].amount.sum(), lo[~lo.is_buy].amount.sum()
print(f"\n[SIDES] {tot_buy:,} TC bid against {tot_sell:,} TC offered "
      f"({tot_buy / (tot_buy + tot_sell):.0%} of resting coins are bids)")

# Consumption is bounded from above: it cannot exceed what the smallest bands could absorb.
cons_tc = bands[bands.band.isin(["Consumption-shaped", "Heavy consumption"])].tc_buy.sum()
spec_tc = bands[bands.band.isin(["Above the fee cap", "Wholesale"])].tc_buy.sum()
print(f"[SPLIT] of coins bid, {cons_tc / max(1, tot_buy):.0%} sits in consumption-shaped "
      f"orders and {spec_tc / max(1, tot_buy):.0%} in sizes only an arbitrageur, a speculator "
      f"or a dealer would post")

# The book is a stock of unfilled intentions, not a record of trade, and the two say different
# things. A consumer who buys at the market price never rests in the book at all, while a dealer's
# standing bid sits there for weeks. Separating executable orders from parked ones is what makes
# the size distribution interpretable.
bd = pd.read_csv(P / "order_books.csv")
lo["mid"] = lo.world.map(bd.set_index("world").mid.to_dict())
ex = lo.dropna(subset=["mid"]).copy()
ex["rel"] = ex.price / ex["mid"] - 1
buy = ex[ex.is_buy]
near = buy[buy.rel > -0.05]
pan = pd.read_csv(P / "panel_daily.csv")
# day_bought is a count of 25-coin lots; bid_depth_tc is already coins. Comparing them
# without converting was a units error of exactly 25x.
LOT = FE["lot_size"]
txn = float(pan.day_bought.median())
flow = txn * LOT
depth = float(bd.bid_depth_tc.median())
deep_far = float((buy[buy.amount > 10000].rel < -0.20).mean())
EXEC = {
    "median_executed_txn_per_world_day": txn,
    "lot_size": LOT,
    "median_executed_per_world_day_tc": flow,
    "median_resting_bid_depth_tc": depth,
    "resting_over_daily_flow": depth / max(1.0, flow),
    "share_wholesale_bids_20pct_below_mid": deep_far,
    "median_offer_size_tc": float(lo.amount.median()),
    # The fee schedule and market impact pull in opposite directions, and the ratio is the
    # size of the conflict: the cheapest order to place is a large share of a day's volume.
    "median_tc_sold_per_world_day": float(pan[pan.world.isin(
        set(pd.read_csv(P / "world_summary.csv").query("converged").world))].tc_sold.median()),
    "cap_lot_share_of_daily_volume": float(CAP_LOT / max(1.0, pan[pan.world.isin(
        set(pd.read_csv(P / "world_summary.csv").query("converged").world))].tc_sold.median())),
    "median_gp_turnover_per_world_day": float(
        (pan.tc_sold * pan.price_gp).median()),
    "near_mid_bid_tc": float(near.amount.sum()),
    "near_mid_share_of_bids": float(near.amount.sum() / max(1, buy.amount.sum())),
    "consumption_share_of_near_mid": float(
        near[near.amount < 500].amount.sum() / max(1, near.amount.sum())),
}
print(f"\n[EXECUTABLE] median executed {txn:,.0f} lots per world-day = {flow:,.0f} TC, "
      f"against a resting bid depth of {depth:,.0f} TC - the book is "
      f"{depth / max(1, flow):,.0f} times a day's flow")
print(f"[EXECUTABLE] {deep_far:.0%} of wholesale bids sit more than 20% below the mid and will "
      f"not fill; among bids within 5% of the mid, consumption-shaped orders are "
      f"{EXEC['consumption_share_of_near_mid']:.0%} of coins")

# Each profile should respond to its own stimulus. These are the testable predictions of the
# taxonomy, matched to what the study has already measured.
STIM = [
    {"profile": "Gold buyer (money to gold)", "side": "Supply",
     "stimulus": "GP received per unit of money", "prediction":
     "Sells more coins when the GP price is high, which caps rallies",
     "evidence": "Sell-side depth is only "
                 f"{tot_sell / (tot_buy + tot_sell):.0%} of resting coins, so this side is "
                 f"thin and its withdrawal would move the price"},
    {"profile": "Consumer (gold to services)", "side": "Demand",
     "stimulus": "Need for premium, boosts, mounts", "prediction":
     "Buys in Store-sized lots, insensitive to price, on a monthly cycle",
     "evidence": f"{bands.iloc[0].share_of_offers:.0%} of offers are under 500 TC but only "
                 f"{bands.iloc[0].share_of_tc:.1%} of coins"},
    {"profile": "Investor or speculator", "side": "Demand",
     "stimulus": "Expected appreciation", "prediction":
     "Buys on momentum; would show as return autocorrelation",
     "evidence": "Momentum carries no out-of-sample value (Section 6.6.2), so this motive "
                 "leaves no detectable footprint in prices"},
    {"profile": "Arbitrageur", "side": "Both",
     "stimulus": "Price gap between worlds", "prediction":
     "Trades only when the gap clears the fee",
     "evidence": f"The band sits at {R['advanced']['tar']['threshold_pct']:.2f}%; the average "
                 f"trade nets below zero while the strongest decile held a month does not "
                 f"(Sections 6.6.10, 7.7)"},
    {"profile": "Farmer, gold to coin to money", "side": "Demand",
     "stimulus": "Farm hours against the coin price and the outside money price",
     "prediction": "Buys coins to export value; would show as coins leaving the game",
     "evidence": f"{json.load(open(P / 'fundamentals_results.json'))['venues']['token']['total_supply']:,.0f} "
                 f"TIB outstanding is coins held outside the in-game system (Section 5.8)"
                 if "venues" in json.load(open(P / "fundamentals_results.json"))
                 else "token supply unavailable"},
    {"profile": "Farmer selling gold directly", "side": "Absent",
     "stimulus": "Outside price of gold", "prediction":
     "Never touches the coin market; is pure gold supply",
     "evidence": "Invisible in this data by construction, and a standing limitation"},
]
stim = pd.DataFrame(STIM)
stim.to_csv(P / "participant_profiles.csv", index=False)

RES = {"executable": EXEC, "bands": bands.drop(columns=["note"]).to_dict("records"),
       "band_notes": {r["band"]: r["note"] for _, r in bands.iterrows()},
       "total_bid_tc": int(tot_buy), "total_ask_tc": int(tot_sell),
       "bid_share": float(tot_buy / (tot_buy + tot_sell)),
       "consumption_share_of_bids": float(cons_tc / max(1, tot_buy)),
       "large_share_of_bids": float(spec_tc / max(1, tot_buy)),
       "store_prices_tc": STORE,
       "profiles": STIM,
       "caveat": ("the mapping from order size to motive is a hypothesis; what is measured is "
                  "the size distribution and the imbalance within each band")}
out = json.load(open(P / "fundamentals_results.json"))
out["participants"] = RES
json.dump(out, open(P / "fundamentals_results.json", "w"), indent=1, default=str)
print("\n[PARTICIPANTS] written: participant_bands, participant_profiles")
