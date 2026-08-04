"""Section F cleaning pipeline: raw snapshots -> analysis-ready daily world panel.

Steps (in order):
  1. -1 sentinels -> missing, before any arithmetic.
  2. Collapse intraday scans to one row per world-day (last scan of the day: its
     trailing day_* aggregates are the most complete).
  3. Validity gates: accept day_average_sell only if day_sold > 0 and value > 1,000 gp
     (zero-trade days write 0, not null); same for the buy side.
  4. price_gp = mean of the two valid daily executed averages.
  5. Fallback to order-book mid only when 0.5 <= ask/bid <= 2.0.
  6. Outlier scrub: drop days > 5 MAD (floor 12%) from a centred 15-day rolling median.
  7. Daily range from the four high/low fields, restricted to 0.5x-2.0x of day price.
  8. Single-day gaps interpolated for indicators only; statistics use observed days.
  9. Timestamps: Unix epoch -> UTC -> floor to day. The Tibia economic day starts at
     server save, not UTC midnight; that offset is NOT corrected (documented limitation).

Output: data/processed/panel_daily.csv
"""
import pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed"

SENTINEL = -1
MIN_PRICE = 1_000.0
MAD_K, MAD_FLOOR, MAD_WIN = 5.0, 0.12, 15
BOOK_LO, BOOK_HI = 0.5, 2.0

df = pd.read_parquet(OUT / "snapshots_raw.parquet")
audit = {"snapshots_raw": len(df)}

# --- 1. sentinels -----------------------------------------------------------
numcols = [c for c in df.columns if df[c].dtype.kind in "if" and c not in ("time", "id")]
for c in numcols:
    df.loc[df[c] == SENTINEL, c] = np.nan

# --- 2. one row per world-day ----------------------------------------------
df = df.sort_values(["world", "ts"])
day = df.groupby(["world", "date"], as_index=False).last()
audit["world_days"] = len(day)
audit["intraday_collapsed"] = len(df) - len(day)

# --- 3. validity gates ------------------------------------------------------
sell_ok = (day["day_sold"] > 0) & (day["day_average_sell"] > MIN_PRICE)
buy_ok = (day["day_bought"] > 0) & (day["day_average_buy"] > MIN_PRICE)
day["day_average_sell_valid"] = day["day_average_sell"].where(sell_ok)
day["day_average_buy_valid"] = day["day_average_buy"].where(buy_ok)
audit["sell_valid"] = int(sell_ok.sum())
audit["buy_valid"] = int(buy_ok.sum())

# --- 4. price = mean of valid executed averages -----------------------------
day["price_gp"] = day[["day_average_sell_valid", "day_average_buy_valid"]].mean(axis=1, skipna=True)
day["price_source"] = np.where(sell_ok & buy_ok, "both",
                        np.where(sell_ok, "sell_only",
                          np.where(buy_ok, "buy_only", "none")))

# alternative measures for the sensitivity check (Section 30)
qty = day["day_sold"].fillna(0) + day["day_bought"].fillna(0)
day["price_vw"] = ((day["day_average_sell_valid"].fillna(0) * day["day_sold"].fillna(0) +
                    day["day_average_buy_valid"].fillna(0) * day["day_bought"].fillna(0)) /
                   qty.replace(0, np.nan))
day.loc[day["price_source"] == "none", "price_vw"] = np.nan

# --- 5. order-book mid fallback --------------------------------------------
ratio = day["sell_offer"] / day["buy_offer"]
book_ok = ratio.between(BOOK_LO, BOOK_HI) & (day["buy_offer"] > MIN_PRICE)
day["offer_mid"] = ((day["buy_offer"] + day["sell_offer"]) / 2).where(book_ok)
day["spread_pct"] = ((day["sell_offer"] - day["buy_offer"]) /
                            day["offer_mid"] * 100).where(book_ok)
filled = day["price_gp"].isna() & day["offer_mid"].notna()
day.loc[filled, "price_gp"] = day.loc[filled, "offer_mid"]
day.loc[filled, "price_source"] = "book_mid"
audit["book_mid_fills"] = int(filled.sum())

# executed-average gap (NOT a bid-ask spread: gap between mean executed prices per side)
day["executed_gap_pct"] = ((day["day_average_sell_valid"] - day["day_average_buy_valid"]) /
                           day[["day_average_sell_valid", "day_average_buy_valid"]].mean(axis=1) * 100)

day = day[day["price_gp"].notna()].copy()
audit["priced_world_days"] = len(day)

# --- 6. outlier scrub -------------------------------------------------------
def roll_med(s):
    return s.rolling(MAD_WIN, center=True, min_periods=5).median()


day = day.sort_values(["world", "date"]).reset_index(drop=True)
med = day.groupby("world")["price_gp"].transform(roll_med)
dev = (day["price_gp"] - med).abs()
mad = dev.groupby(day["world"]).transform(roll_med)
tol = np.maximum(MAD_K * mad, MAD_FLOOR * med)
day["is_outlier"] = (dev > tol) & med.notna()
audit["outliers_dropped"] = int(day["is_outlier"].sum())
day = day[~day["is_outlier"]].drop(columns=["is_outlier"]).copy()

# --- 7. daily range ---------------------------------------------------------
hi = day[["day_highest_sell", "day_highest_buy"]].max(axis=1)
lo = day[["day_lowest_sell", "day_lowest_buy"]].min(axis=1)
band_ok = (hi.between(BOOK_LO * day["price_gp"], BOOK_HI * day["price_gp"]) &
           lo.between(BOOK_LO * day["price_gp"], BOOK_HI * day["price_gp"]) & (hi >= lo))
day["day_high"] = hi.where(band_ok)
day["day_low"] = lo.where(band_ok)
day["day_range_pct"] = ((day["day_high"] - day["day_low"]) / day["price_gp"] * 100)

# --- 8. derived series ------------------------------------------------------
day["log_price"] = np.log(day["price_gp"])
day = day.sort_values(["world", "date"])
g = day.groupby("world")
day["ret"] = g["log_price"].diff()
day["gap_days"] = g["date"].diff().dt.days
day.loc[day["gap_days"] != 1, "ret"] = np.nan          # returns only over consecutive days
# Coins trade only in lots of 25 - the Market will not accept any other quantity - and
# day_sold / day_bought are expressed in those lots, not in coins. The values run 1, 2, 3 with
# only ~4% multiples of 25, which is what a lot count looks like and what a coin count cannot
# be. Coin volume is therefore 25 x the field. The order-book amounts are the opposite case:
# minimum 25 and 100% multiples of 25, so those are already coins and are left alone.
LOT = 25
day["day_sold_tc"] = day["day_sold"] * LOT
day["day_bought_tc"] = day["day_bought"] * LOT
day["day_sold_txn"] = day["day_sold"]
day["day_bought_txn"] = day["day_bought"]

# --- classification ---------------------------------------------------------
meta = pd.read_csv(OUT / "world_metadata.csv", parse_dates=["created", "first_obs"])
day = day.merge(meta[["world", "region", "pvp_type", "battleye_protected", "battleye_date",
                      "transfer_type", "premium_only", "game_world_type", "created",
                      "is_merge_destination", "launch_in_window"]], on="world", how="left")
day["world_age_years"] = (day["date"] - day["created"]).dt.days / 365.25

n_obs = day.groupby("world")["date"].size()
conv = ((n_obs >= 200) &
        day.groupby("world")["game_world_type"].first().eq("regular") &
        ~day.groupby("world")["launch_in_window"].first().fillna(False))
day["converged"] = day["world"].map(conv).fillna(False)

day.to_csv(OUT / "panel_daily.csv", index=False)

print("CLEANING AUDIT")
for k, v in audit.items():
    print(f"  {k:<22} {v:,}")
print(f"  {'converged worlds':<22} {conv.sum():,}")
print(f"  {'launch worlds':<22} {int(meta.launch_in_window.sum()):,}")
print("\nprice_source:", day["price_source"].value_counts().to_dict())
print("date range :", day.date.min().date(), "->", day.date.max().date())
print("worlds     :", day.world.nunique())

print("\nPrice-measure sensitivity (mean |%| deviation from the headline mean-of-executed):")
for c, lab in [("price_vw", "quantity-weighted"), ("offer_mid", "order-book mid"),
               ("day_average_sell_valid", "sell-side only")]:
    d = ((day[c] - day["price_gp"]).abs() / day["price_gp"] * 100).dropna()
    print(f"  {lab:<20} {d.mean():5.2f}%   (n={len(d):,})")
