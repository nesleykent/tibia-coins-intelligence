"""One statement of every claim the report and the site both make.

Until now the two artifacts were written separately and reconciled afterwards: a finding was
worded in `09_sections.py` for the PDF, then worded again in `39_intelligence_hub.py` for the
site, and `46_verify_artifacts.py` checked that the numbers had not drifted apart. That check
is worth keeping as a backstop, but reconciliation is the wrong shape for the problem - every
new finding costs the work twice and can disagree in between.

So the shared claims live here, once. A claim carries its own text, its own numbers read from
`data/processed`, and the evidence label the report's conventions require. Both renderers
consume the same objects: the PDF turns a claim into a labelled paragraph, the site turns it
into a card with fact tiles and, where the claim names one, an interactive view of the data
behind it.

What belongs here is the material both artifacts publish - the mechanism, the verdict, the
strategy, the venue structure. What does not belong here is the report's long-form derivation
of any of it; the PDF still owns that, because a 179-page argument is not something the site
is trying to reproduce.

    from narrative import claims, facts, fact_tiles
"""
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"


def _load() -> dict:
    res = json.loads((P / "results.json").read_text())
    fund = json.loads((P / "fundamentals_results.json").read_text())
    grid = pd.DataFrame(fund["strategy"]["grid"])
    hold = pd.DataFrame(fund["strategy"]["holdout"]["rows"])

    def cell(h: int, col: str) -> float:
        row = grid[(grid.horizon == h) & (grid.decile == grid.decile.max())
                   & (grid.cost_basis == "above the fee cap")]
        return float(row[col].iloc[0])

    def ho(h: int, col: str) -> float:
        return float(hold[(hold.horizon == h) & (hold.period == "holdout")][col].iloc[0])

    pages = 0
    pdf = ROOT / "reports" / "tibia_coin_market_report.pdf"
    if pdf.exists():
        try:
            from pypdf import PdfReader
            pages = len(PdfReader(str(pdf)).pages)
        except Exception:
            pages = 0

    ex = fund["participants"]["executable"]
    ms = res["venues"]["market_size"]
    irr = fund["irreducibility"]["latent_state"]
    return {
        "verdict": "buy relative, not directional",
        "confidence": 78,
        "reportPages": pages,
        "bandThresholdPct": res["advanced"]["tar"]["threshold_pct"],
        "actionGapPct": fund["scenarios"]["levels"]["arb_act_gap_pct"],
        "lotSize": res["fees"]["lot_size"],
        "feeCapLotTc": res["fees"]["cap_binds_at_lot_tc"],
        "feeRatePct": res["fees"]["rate_pct"],
        "feeCapGp": res["fees"]["cap_gp"],
        "roundTripPct": res["fees"]["roundtrip_largest_decile_pct"],
        "strategyNet7": cell(7, "net_pct"),
        "strategyNet30": cell(30, "net_pct"),
        "strategyNet91": cell(91, "net_pct"),
        "strategyWin30": cell(30, "share_profitable"),
        "holdoutNet7": ho(7, "net_pct"),
        "holdoutT7": ho(7, "t_newey_west"),
        "holdoutWindows7": int(ho(7, "n_effective")),
        "holdoutWindows30": int(ho(30, "n_effective")),
        "holdoutWindows91": int(ho(91, "n_effective")),
        "episodesPerMonth": fund["strategy"]["occurrence"]["episodes_per_month"],
        "episodes": fund["strategy"]["occurrence"]["n_episodes"],
        "capacityGpPerMonth": fund["strategy"]["capacity"]["gp_per_month"],
        "bazaarOverMarket": ms["bazaar_over_market_comparable"],
        "bazaarOverMarketNaive": ms["bazaar_over_market_naive"],
        "marketCoverage": ms["coverage"],
        "marketTcScaled": ms["market_tc_scaled"],
        "marketTcYear": ms["market_tc_year"],
        "bazaarTcYear": ms["bazaar_tc_year"],
        "venueYear": ms["year"],
        "tcPerWorldDay": ex["median_executed_per_world_day_tc"],
        "restingBidTc": ex["median_resting_bid_depth_tc"],
        "bookDaysOfTrade": ex["resting_over_daily_flow"],
        "sellSideShare": 1 - fund["participants"]["bid_share"],
        "annualVolPct": res["desc"]["ret_sd_ann_pct"],
        "factorR2": irr["r2_factor_smoothed"],
        "factorR2Ahead": irr["r2_factor_forecast"],
        "emissionVerdict": "rejected",
        "emissionCoverage": json.loads(
            (P / "gold_emission_quality.json").read_text())["covered_deaths_pct_all"],
        "behaviourOverProduction": (
            fund["supply_vs_demand"]["horse_race"][2]["r2_within"]
            / fund["supply_vs_demand"]["horse_race"][0]["r2_within"]),
    }


F = _load()


def facts() -> dict:
    """The canonical numbers, for embedding in a page payload or formatting into prose."""
    return dict(F)


def pc(x: float, d: int = 2) -> str:
    return f"{x:.{d}f}%"


def gp(x: float) -> str:
    return f"{x:,.0f}"


@dataclass
class Tile:
    """One fact as the site renders it: a label, a value and the reason it is here."""
    label: str
    value: str
    note: str


@dataclass
class Claim:
    """A statement both artifacts make, with the numbers already in it."""
    key: str
    label: str                       # the report's evidence-label key: mech/stat/econ/judg/lim
    heading: str
    text: str
    summary: str = ""                # the shorter form, for an executive summary
    player_heading: str = ""         # simple site-first heading
    player_text: str = ""            # simple site-first explanation
    tiles: list[Tile] = field(default_factory=list)
    interactive: str | None = None   # a view the site can offer for this claim
    section: str = ""                # where the PDF states it, for cross-reference


def claim(key: str) -> Claim:
    """One claim by key, for a renderer that wants to place a single statement."""
    return next(c for c in claims() if c.key == key)


def claims() -> list[Claim]:
    """Every claim published in both places, in the order the argument runs."""
    return [
        Claim(
            key="mechanism",
            label="econ",
            heading="What sets the price",
            section="7.6",
            text=(
                f"The price of a Tibia Coin measured in GP is an exchange rate, not an asset price. Coin "
                f"supply is perfectly elastic at a money price CipSoft fixes, so nothing on the "
                f"coin side can move it; neither leg pays a yield; and a {pc(F['feeRatePct'], 0)} "
                f"fee capped at {gp(F['feeCapGp'])} GP holds a {pc(F['bandThresholdPct'])} band "
                f"open around every relation in the market. That model, not a preference for "
                f"efficient markets, is why the level does not forecast."),
            summary=(
                f"The price of a Tibia Coin measured in GP is an exchange rate, not an asset price: supply "
                f"is elastic at a fixed money price, neither leg pays a yield, and a "
                f"{pc(F['feeRatePct'], 0)} fee holds a {pc(F['bandThresholdPct'])} band open."),
            player_heading="Why TC prices differ between worlds",
            player_text=(
                "Players buy and sell TC with GP on each world. Small price differences are "
                "usually not worth chasing because Market fees consume the profit. Large "
                "differences can shrink over time. That is why this report compares worlds "
                "instead of guessing that every TC price will rise or fall together."),
            tiles=[
                Tile("Friction band", pc(F["bandThresholdPct"]),
                     "estimated from prices alone, with no fee figure supplied"),
                Tile("Minimum viable order", f"{gp(F['feeCapLotTc'])} TC",
                     "where the fee cap binds"),
                Tile("Round trip at that size", pc(F["roundTripPct"]),
                     "against 4.00% below it"),
            ],
        ),
        Claim(
            key="currency",
            label="judg",
            heading="Coins are a currency, not an asset",
            section="7.6.4",
            text=(
                f"Holding more than you intend to spend is an uncompensated position: zero "
                f"expected return at every horizon tested, {pc(F['annualVolPct'], 0)} annualised "
                f"volatility, and no risk premium of any kind, because no risk is being borne "
                f"on anyone's behalf."),
            summary=(
                f"Coins are a currency, not an asset. Held beyond what you intend to spend they "
                f"pay nothing for {pc(F['annualVolPct'], 0)} of annualised volatility."),
            player_heading="Do not keep extra TC expecting easy profit",
            player_text=(
                "TC are useful for Premium Time, Store products and the Char Bazaar. The data "
                "does not show a reliable reward for simply holding extra TC and waiting. Keep "
                "what you plan to use; treat the rest as a risky bet."),
            tiles=[
                Tile("Annualised volatility", pc(F["annualVolPct"], 0),
                     "carried for no compensation"),
                Tile("Common-factor ceiling", f"{F['factorR2']:.1%}",
                     "of daily variance, observed perfectly and in retrospect"),
                Tile("One step ahead", f"{F['factorR2Ahead']:.1%}",
                     "which is what makes the level unforecastable"),
            ],
        ),
        Claim(
            key="strategy",
            label="stat",
            heading="The one edge that clears its cost",
            section="7.7",
            text=(
                f"Averaged over every signal past the band and held a week, the cross-world "
                f"convergence trade loses. Conditioned on the strongest decile and held longer "
                f"it does not: {pc(F['strategyNet30'])} net at thirty days, winning on "
                f"{F['strategyWin30']:.0%} of occasions, across {F['episodes']} distinct "
                f"episodes rather than one standing gap."),
            player_heading="Only very large price gaps may be worth trading",
            player_text=(
                "Most differences between worlds are too small after Market costs. The biggest "
                "10% of gaps performed better, but the amount of GP that can be used is limited "
                "by available offers. This is a signal to investigate, not an automatic trade."),
            tiles=[
                Tile("Net at 30 days", f"+{pc(F['strategyNet30'])}", "strongest decile, after cost"),
                Tile("Wins", f"{F['strategyWin30']:.0%}", "of 30-day occasions"),
                Tile("Opportunities", f"{F['episodesPerMonth']:.1f} / month",
                     f"{F['episodes']} distinct episodes"),
                Tile("Capacity", f"{F['capacityGpPerMonth'] / 1e6:.0f}M GP / month",
                     "the binding constraint, not conviction"),
            ],
            interactive="strategyGrid",
        ),
        Claim(
            key="evidence_limit",
            label="lim",
            heading="Where the evidence runs out",
            section="7.7.2",
            text=(
                f"The payoff rises with the holding period and so does the apparent "
                f"significance, while the out-of-sample evidence collapses. A true holdout "
                f"leaves {F['holdoutWindows7']} independent windows at seven days, "
                f"{F['holdoutWindows30']} at thirty and {F['holdoutWindows91']} at ninety-one. "
                f"Only the seven-day claim is carried by its sample."),
            player_heading="Trust the 7-day test more than the longer ones",
            player_text=(
                f"The later test period contains {F['holdoutWindows7']} separate 7-day windows, "
                f"but only {F['holdoutWindows30']} 30-day windows and "
                f"{F['holdoutWindows91']} 91-day window. The longer results may look better, "
                f"but there are too few separate tests to rely on them."),
            tiles=[
                Tile("Holdout net, 7 days", f"+{pc(F['holdoutNet7'])}",
                     f"t = {F['holdoutT7']:.1f}, Newey-West"),
                Tile("Independent windows", f"{F['holdoutWindows7']} · {F['holdoutWindows30']} "
                                            f"· {F['holdoutWindows91']}",
                     "at 7 · 30 · 91 days"),
            ],
            interactive="holdout",
        ),
        Claim(
            key="venues",
            label="stat",
            heading="The priced venue is the smaller one",
            section="5.8",
            text=(
                f"In {F['venueYear']} the Char Bazaar moved {gp(F['bazaarTcYear'])} TC against a "
                f"Market that clears {gp(F['marketTcScaled'])} TC once observed volume is scaled "
                f"to every world and day - {F['bazaarOverMarket']:.1f} times more. Dividing the "
                f"raw sums instead would say {F['bazaarOverMarketNaive']:.1f} times, but that "
                f"measures this study's {F['marketCoverage']:.0%} coverage rather than the two "
                f"venues. The GP/TC price is formed in the thin venue and consumed in the thick "
                f"one, so the marginal price-setter is a small population."),
            player_heading="Most TC move through the Char Bazaar, not this Market",
            player_text=(
                f"In {F['venueYear']}, the Char Bazaar moved about "
                f"{F['bazaarOverMarket']:.1f} times more TC than the in-game Market after making "
                f"the periods comparable. The price history used here comes from the smaller "
                f"in-game Market, so it does not show every place where players use TC."),
            tiles=[
                Tile("Char Bazaar vs Market", f"{F['bazaarOverMarket']:.1f}×",
                     "coins in a year, on comparable coverage"),
                Tile("Cleared per world-day", f"{gp(F['tcPerWorldDay'])} TC",
                     f"converted at the {F['lotSize']}-coin lot"),
                Tile("Book depth", f"{F['bookDaysOfTrade']:.0f} days",
                     "of trade resting in bids"),
            ],
        ),
        Claim(
            key="gold",
            label="stat",
            heading="Gold production does not set the price",
            section="6.6.15",
            text=(
                f"Tested first on kill counts and then on a monetary emission series covering "
                f"{F['emissionCoverage']:.1%} of recorded deaths, the channel is absent both "
                f"times. No elasticity is significant at any horizon, and behaviour outperforms "
                f"production by a factor of {F['behaviourOverProduction']:.0f}. This market is "
                f"not a monetary phenomenon."),
            player_heading="More hunting did not reliably move the TC price",
            player_text=(
                "Days with more creature deaths and more generated GP were not followed by a "
                "reliable change in the TC price. This does not prove that GP can never matter. "
                "It means the available history does not support using hunting activity alone "
                "to decide when to buy or sell TC."),
            tiles=[
                Tile("Gold production channel", "Rejected",
                     "same null on the GP-emission series"),
                Tile("Behaviour vs production", f"{F['behaviourOverProduction']:.0f}×",
                     "within-world explanatory power"),
                Tile("Emission coverage", f"{F['emissionCoverage']:.1%}",
                     "of recorded deaths, rest excluded not imputed"),
            ],
        ),
    ]


def fact_tiles() -> list[dict]:
    """Every tile, flattened, for a page that wants them without the prose."""
    return [{"claim": c.key, "label": t.label, "value": t.value, "note": t.note}
            for c in claims() for t in c.tiles]


if __name__ == "__main__":
    cs = claims()
    print(f"{len(cs)} shared claims, {sum(len(c.tiles) for c in cs)} fact tiles\n")
    for c in cs:
        print(f"[{c.label}] {c.heading}  (report {c.section}"
              + (f", site view {c.interactive}" if c.interactive else "") + ")")
        print(f"  {c.text[:150]}...")
        for t in c.tiles:
            print(f"    - {t.label}: {t.value}")
        print()
