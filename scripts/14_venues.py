"""Measure what can be measured about the venues outside the in-game Market.

A Tibia Coin is an account-level asset and can leave the in-game economy in more than one way.
Only one of those routes leaves a public, verifiable trace: the Tibia Token, an official BEP-20
contract on the BNB Smart Chain whose supply is readable by anyone. Every token in existence
corresponds to a coin held outside the in-game system, so the supply is a direct measure of how
much of the float has left - the one number this study can put on a second venue.

The reseller/OTC venue leaves no such trace and is not measured here.

The chain read is cached. A rebuild of the report must not depend on the network, and the
cached value carries the block height it was read at so the figure can be reproduced exactly.
"""
import json, pathlib, re, urllib.request
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P, RAW = ROOT / "data" / "processed", ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
CACHE = RAW / "tibia_token_supply.json"
BAZ_CACHE = RAW / "char_bazaar_2025.json"
DEX_CACHE = RAW / "tibia_token_pools.json"
BAZ_URL = "https://nabbot.xyz/stats/2025/all"

# Published by CipSoft on the Tibia Token support page.
CONTRACT = "0x111B95C2b65CbA53aB4E0AaDA12f55985045E446"
RPC = "https://bsc-dataseed.binance.org/"


def _rpc(method, params):
    req = urllib.request.Request(
        RPC, data=json.dumps({"jsonrpc": "2.0", "id": 1,
                              "method": method, "params": params}).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=25))["result"]


def _call(sig):
    return _rpc("eth_call", [{"to": CONTRACT, "data": sig}, "latest"])


def _str(hexs):
    b = bytes.fromhex(hexs[2:])
    return b[64:64 + int.from_bytes(b[32:64], "big")].decode()


def read_chain():
    dec = int(_call("0x313ce567"), 16)
    return {"contract": CONTRACT, "chain": "BNB Smart Chain", "standard": "BEP-20",
            "name": _str(_call("0x06fdde03")), "symbol": _str(_call("0x95d89b41")),
            "decimals": dec,
            "total_supply": int(_call("0x18160ddd"), 16) / 10 ** dec,
            "block": int(_rpc("eth_blockNumber", []), 16)}


try:
    tok = read_chain()
    CACHE.write_text(json.dumps(tok, indent=1))
    print(f"[CHAIN] read at block {tok['block']:,}")
except Exception as e:                                  # offline rebuild
    if not CACHE.exists():
        raise SystemExit(f"no cached token supply and the chain is unreachable: {e}")
    tok = json.loads(CACHE.read_text())
    print(f"[CHAIN] unreachable ({type(e).__name__}); using cached block {tok['block']:,}")

# The token has a secondary market, and it is worth measuring properly. An earlier read of the
# PancakeSwap V2 pair alone showed a few hundred dollars of depth and would have supported the
# conclusion that no real market exists; almost all of the liquidity is in fact in V3 pools, and
# the V2-only picture was wrong. Every pool the factories know about is enumerated here, and the
# price is taken from the deepest one with the others reported as a cross-check.
PANCAKE_V2 = "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"
PANCAKE_V3 = "0x0BFbCF9fa4f9C56B0F40a671Ad40E0805A091865"
QUOTES = {"USDT": "0x55d398326f99059fF775485246999027B3197955",
          "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
          "BUSD": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
          "WBNB": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"}
STABLE = ("USDT", "USDC", "BUSD")


def _pad(a):
    return a.lower().replace("0x", "").rjust(64, "0")


def _erc20_balance(token, holder):
    return int(_rpc("eth_call", [{"to": token, "data": "0x70a08231" + _pad(holder)},
                                 "latest"]), 16) / 1e18


def read_pools():
    """Enumerate every PancakeSwap pool quoting the token, with its depth and its price."""
    out = []
    for sym, quote in QUOTES.items():
        v2 = _rpc("eth_call", [{"to": PANCAKE_V2,
                                "data": "0xe6a43905" + _pad(CONTRACT) + _pad(quote)}, "latest"])
        cands = [("V2", None, "0x" + v2[-40:])] if v2 and int(v2, 16) else []
        for fee in (100, 500, 2500, 10000):
            r = _rpc("eth_call", [{"to": PANCAKE_V3,
                                   "data": "0x1698ee82" + _pad(CONTRACT) + _pad(quote)
                                           + hex(fee)[2:].rjust(64, "0")}, "latest"])
            if r and int(r, 16):
                cands.append(("V3", fee, "0x" + r[-40:]))
        for kind, fee, pool in cands:
            tib = _erc20_balance(CONTRACT, pool)
            qty = _erc20_balance(quote, pool)
            if kind == "V2":
                price = qty / tib if tib else None
            else:
                sqrt_p = int(_rpc("eth_call", [{"to": pool, "data": "0x3850c7bd"},
                                               "latest"])[2:66], 16)
                # Both sides carry 18 decimals and the token sorts below every quote asset
                # used here, so slot0 gives quote-per-token directly.
                price = (sqrt_p / 2 ** 96) ** 2
            out.append({"venue": kind, "fee_bps": fee, "quote": sym, "pool": pool,
                        "tib": tib, "quote_qty": qty, "price": price})
    return out


try:
    pools = read_pools()
    dex_block = int(_rpc("eth_blockNumber", []), 16)
    DEX_CACHE.write_text(json.dumps({"block": dex_block, "pools": pools}, indent=1))
except Exception as e:                                  # offline rebuild, as for the supply
    if not DEX_CACHE.exists():
        raise SystemExit(f"no cached pool state and the chain is unreachable: {e}")
    _c = json.loads(DEX_CACHE.read_text())
    pools, dex_block = _c["pools"], _c["block"]
    print(f"[DEX] unreachable ({type(e).__name__}); using cached block {dex_block:,}")

stable_pools = [x for x in pools if x["quote"] in STABLE and x["quote_qty"] > 1]
deepest = max(stable_pools, key=lambda x: x["quote_qty"]) if stable_pools else None
dex = {
    "block": dex_block,
    "n_pools": len(pools),
    "tib_in_pools": sum(x["tib"] for x in pools),
    "stable_depth_usd": sum(x["quote_qty"] for x in pools if x["quote"] in STABLE),
    "price_usd": deepest["price"] if deepest else None,
    "price_source": f"{deepest['venue']} {deepest['quote']}"
                    + (f" {deepest['fee_bps'] / 10000:g}%" if deepest["fee_bps"] else "")
                    if deepest else None,
    "price_range_usd": [min(x["price"] for x in stable_pools),
                        max(x["price"] for x in stable_pools)] if stable_pools else None,
    "n_quoting_pools": len(stable_pools),
    "pools": pools,
}
print(f"[DEX] block {dex_block:,}; {dex['n_pools']} pools; {dex['tib_in_pools']:,.0f} TIB and "
      f"${dex['stable_depth_usd']:,.0f} stablecoin depth; price "
      f"${dex['price_usd']:.6f} from {dex['price_source']}")

# The Char Bazaar is the other place a coin goes, and the largest one: coins are spent there on
# characters rather than sold for gold, which makes it a demand sink rather than a competing
# venue. Its turnover is the right yardstick for judging how large the token venue actually is.
# The page renders its figures client-side, so the numbers are read from the streamed payload
# the server sends rather than from the rendered DOM.
def read_bazaar():
    req = urllib.request.Request(BAZ_URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    pl = "".join(re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S))
    pl = pl.encode().decode("unicode_escape", errors="ignore")
    i = pl.index('"auctions":{') + 11
    depth = 0
    for j in range(i, len(pl)):
        if pl[j] == "{":
            depth += 1
        elif pl[j] == "}":
            depth -= 1
            if depth == 0:
                break
    a = json.loads(pl[i:j + 1])
    months = a["perMonth"]
    assert sum(m["created"] for m in months) == a["total"], "monthly counts do not reconcile"
    assert len(months) == 12, "not a full year"
    return {"year": 2025, "scope": "all worlds",
            "auctions_created": a["total"], "auctions_completed": a["totalCompleted"],
            "tc_exchanged": a["totalExchanged"], "tc_commission": a["totalComission"],
            "tc_fees": a["totalFees"], "tc_cancel_fees": a["totalCancelFees"],
            "highest_tc": a["mostExpensive"][0]["value"],
            "highest_name": a["mostExpensive"][0]["name"]}


try:
    baz = read_bazaar()
    BAZ_CACHE.write_text(json.dumps(baz, indent=1))
    print(f"[BAZAAR] {baz['tc_exchanged']:,} TC exchanged over "
          f"{baz['auctions_completed']:,} completed auctions in {baz['year']}")
except Exception as e:
    if not BAZ_CACHE.exists():
        raise SystemExit(f"no cached bazaar figures and the source is unreachable: {e}")
    baz = json.loads(BAZ_CACHE.read_text())
    print(f"[BAZAAR] unreachable ({type(e).__name__}); using cached {baz['year']} figures")

# Scale the token venue against the in-game one. Ask depth is the right comparison: it is the
# quantity of coins actually offered for sale, which is what the token venue competes with.
bd = pd.read_csv(P / "order_books.csv")
ask = float(bd.sellers_amount.sum())
bid = float(bd.buyers_amount.sum())

res = json.load(open(P / "results.json"))
res["venues"] = {
    "token": tok,
    "sellers_amount_total": ask,
    "buyers_amount_total": bid,
    "book_total_depth_tc": ask + bid,
    "n_book_worlds": int(len(bd)),
    "tib_over_sellers_amount": tok["total_supply"] / ask,
    "tib_over_total_depth": tok["total_supply"] / (ask + bid),
    "dex": dex,
    "bazaar": baz,
    # With a dollar price for the coin and a gold price for the coin, gold itself acquires a
    # dollar value - the first real-money anchor available anywhere in this study.
    "usd_per_gp": (dex["price_usd"] / res["desc"]["price_latest_median"]
                   if dex["price_usd"] else None),
    "gp_per_usd": (res["desc"]["price_latest_median"] / dex["price_usd"]
                   if dex["price_usd"] else None),
    "tib_over_bazaar_year": tok["total_supply"] / baz["tc_exchanged"],
    "bazaar_completion_rate": baz["auctions_completed"] / baz["auctions_created"],
    "bazaar_mean_price_tc": baz["tc_exchanged"] / baz["auctions_completed"],
}

# How large is the in-game Market next to the Bazaar? The comparison was not available while
# the executed series was misread as coins - it would have implied a ratio near 300, which is
# its own kind of warning. On corrected units the two venues are on the same scale and the
# Market is decisively the smaller one.
_pan = pd.read_csv(P / "panel_daily.csv", parse_dates=["date"])
_y = _pan[_pan.date.dt.year == baz["year"]]
_mkt_tc = float(_y.day_sold_tc.sum())
_mkt_gp = float((_y.day_sold_tc * _y.price_gp).sum())
_usd_tc = (res["desc"]["price_latest_median"] * res["venues"]["usd_per_gp"]
           if res["venues"]["usd_per_gp"] else None)
# Comparable coverage, not raw sums. The Bazaar total is complete - all worlds, all year -
# while the Market side is only the world-days this study observes, which in 2025 is 35 of 93
# worlds on a typical day. Dividing one by the other measures our coverage, not the venues:
# the naive ratio reads 33.5x in 2024 at 14% coverage and 11.5x in 2025 at 52%. Scaling the
# observed mean per world-day to the full world count and calendar makes the two comparable.
_n_worlds = int(_pan.world.nunique())
_days = int(_y.date.nunique())
_mkt_scaled = float(_y.day_sold_tc.mean()) * _n_worlds * _days
_baz_span = float(baz["tc_exchanged"]) * _days / 365
res["venues"]["market_size"] = {
    "year": baz["year"],
    "coverage": len(_y) / (_n_worlds * _days),
    "market_tc_scaled": _mkt_scaled,
    "bazaar_over_market_naive": float(baz["tc_exchanged"]) / _mkt_tc,
    "bazaar_over_market_comparable": _baz_span / _mkt_scaled,
    "n_worlds": int(_y.world.nunique()),
    "market_tc_year": _mkt_tc,
    "market_gp_year": _mkt_gp,
    "bazaar_tc_year": float(baz["tc_exchanged"]),
    "bazaar_over_market": _baz_span / _mkt_scaled,
    "market_usd_year": _mkt_gp * res["venues"]["usd_per_gp"] if res["venues"]["usd_per_gp"] else None,
    "bazaar_usd_year": baz["tc_exchanged"] * _usd_tc if _usd_tc else None,
    # NOT an independent cross-check: usd_per_gp is itself the DEX price divided by the median
    # GP price, so multiplying it back by that price returns the DEX quote by construction.
    # The dollar figures below are the on-chain quote restated, not a second measurement.
    "usd_basis": "on-chain TIB/USDT quote, propagated through the GP price; not independent",
    "tc_usd": _usd_tc,
}
_ms = res["venues"]["market_size"]
print(f"[SIZE] {baz['year']}: Market {_mkt_tc:,.0f} TC observed at {_ms['coverage']:.0%} "
      f"coverage, {_ms['market_tc_scaled']:,.0f} TC scaled to all worlds; Bazaar "
      f"{baz['tc_exchanged']:,.0f} TC")
print(f"[SIZE] Bazaar is {_ms['bazaar_over_market_comparable']:.1f}x the Market on comparable "
      f"coverage ({_ms['bazaar_over_market_naive']:.1f}x if the raw sums are divided)")
if _usd_tc:
    print(f"[SIZE] at the on-chain quote of ${_usd_tc:.4f}/coin: Market "
          f"${_mkt_gp * res['venues']['usd_per_gp']:,.0f}, Bazaar "
          f"${baz['tc_exchanged'] * _usd_tc:,.0f} for the year")

json.dump(res, open(P / "results.json", "w"), indent=1, default=str)

print(f"[VENUES] {tok['symbol']} supply {tok['total_supply']:,.0f} vs ask depth "
      f"{ask:,.0f} TC across {len(bd)} worlds "
      f"({res['venues']['tib_over_sellers_amount']:.2f}x); vs both sides "
      f"({res['venues']['tib_over_total_depth']:.0%})")
print(f"[VENUES] token supply is {res['venues']['tib_over_bazaar_year']:.1%} of one year of "
      f"Char Bazaar turnover; mean clearing price "
      f"{res['venues']['bazaar_mean_price_tc']:,.0f} TC")
