"""Map validated evidence to Buy / Sell / Hold / Avoid / Investigate, or abstain.

The report establishes findings; nothing turned them into an action under stated rules, so the
site risked reading a forecast as a recommendation. This is that missing layer, and most of its
work is refusing to act.

What the evidence supports, and what it does not:

* Relative deviation mean-reverts once a gap clears the cost of closing it. `arbitrage_band.csv`
  shows gaps above 4% closing significantly while gaps under 2% keep widening, and
  `strategy_holdout.csv` earns 1.73% net at 7 days out of sample, t = 4.6. Deviation is the only
  signal here that survives a holdout, so it is the only one allowed to produce a trade.
* The absolute price forecast has no skill. `forecast_backtest_summary.csv` loses to a random
  walk at every horizon - MAPE 2.23 against 2.19 at two weeks, 7.24 against 6.72 at six months.
  It therefore never sets a direction; it is carried only as an uncertainty range.
* Gold emission does not predict returns at any tested lag. It is not an input.

Abstention is a supported outcome, not a failure to decide. A world with no current price, an
unconverged series, a gap inside the cost band, or an interval spanning zero gets no call.

    python scripts/53_decision_policy.py
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "data" / "processed"

POLICY_VERSION = "1.0.0"

# Every threshold is a published figure from this repository, not a preference. Changing one is a
# policy change and must move POLICY_VERSION.
RULES = {
    "band_threshold_pct": None,   # filled from results.json: where mean reversion starts
    "action_threshold_pct": None, # published "act above this gap" level, reported for context
    "fee_rate_pct": None,         # Market fee, charged per side
    "min_holdout_t": 2.0,         # a horizon must clear this in its own holdout to be tradable
    "min_holdout_n_effective": 10,  # ... on more than a handful of independent episodes
    "min_depth_tc": 25,           # one lot; below this the quoted side cannot absorb a trade
    "max_staleness_days": 7,      # a price older than this is not a current price
}


def load() -> dict:
    results = json.loads((P / "results.json").read_text())
    return {
        "results": results,
        "predictions": pd.read_csv(P / "latest_predictions.csv", parse_dates=["as_of"]),
        "holdout": pd.read_csv(P / "strategy_holdout.csv"),
        "band": pd.read_csv(P / "arbitrage_band.csv"),
        "backtest": pd.read_csv(P / "forecast_backtest_summary.csv"),
        "books": pd.read_csv(P / "order_books.csv"),
    }


def tradable_horizons(holdout: pd.DataFrame) -> dict[int, dict]:
    """Horizons whose own holdout supports trading, with the evidence attached.

    The 91-day holdout reports one effective episode. A single episode is an anecdote whatever
    its t-statistic, so the rule requires independent episodes as well as significance and the
    horizon is refused rather than shown with a caveat.
    """
    out: dict[int, dict] = {}
    for _, row in holdout[holdout.period == "holdout"].iterrows():
        eligible = (
            row.t_newey_west >= RULES["min_holdout_t"]
            and row.n_effective >= RULES["min_holdout_n_effective"]
        )
        out[int(row.horizon)] = {
            "eligible": bool(eligible),
            "net_pct": float(row.net_pct),
            "t_newey_west": float(row.t_newey_west),
            "n_effective": int(row.n_effective),
            "share_profitable": float(row.share_profitable),
            "cutoff_pct": float(row.cutoff_pct),
            "reason": "" if eligible else (
                f"holdout rests on {int(row.n_effective)} effective episode(s), "
                f"below the {RULES['min_holdout_n_effective']} required"
            ),
        }
    return out


def decide(row: pd.Series, rules: dict, horizon: dict, book: pd.Series | None,
           as_of_max: pd.Timestamp) -> dict:
    """One world, one call, with the reason it was reached."""
    reasons: list[str] = []
    deviation = float(row.deviation_pct)
    staleness = int((as_of_max - row.as_of).days)

    # --- eligibility, before any signal is read ------------------------------------------
    if staleness > rules["max_staleness_days"]:
        return {"action": "Abstain", "confidence": "none",
                "reason": f"price is {staleness} days old; no current price to act on"}
    if not horizon["eligible"]:
        return {"action": "Abstain", "confidence": "none",
                "reason": f"no tradable horizon: {horizon['reason']}"}

    depth = float(book.buyers_amount) if book is not None and pd.notna(book.buyers_amount) else np.nan
    if np.isnan(depth):
        reasons.append("no order-book snapshot; capacity unknown")
    elif depth < rules["min_depth_tc"]:
        return {"action": "Avoid", "confidence": "low",
                "reason": f"resting demand is {depth:.0f} TC, under one {rules['min_depth_tc']} TC lot"}

    # --- the signal ------------------------------------------------------------------------
    # Round trip pays the Market fee on both sides, so a gap must exceed that before it is
    # worth closing, not merely exceed zero.
    round_trip = 2 * rules["fee_rate_pct"]
    if abs(deviation) < rules["band_threshold_pct"]:
        return {"action": "Hold", "confidence": "high",
                "reason": (f"deviation {deviation:+.2f}% sits inside the {rules['band_threshold_pct']:.2f}% "
                           "band, where gaps widen rather than close")}
    # Trade at the cutoff the holdout was actually earned at, not at the lower level where
    # closure is merely significant. The 4% figure comes from arbitrage_band, where the 4-6% bin
    # closes by 0.05pp - real, but a twelfth of the >10% bin - while the holdout that produces
    # the +1.73% net return selected on a 9.89% cutoff. Quoting that return to justify a 4% trade
    # would attach evidence to a rule that never generated it.
    cutoff = horizon["cutoff_pct"]
    if abs(deviation) < cutoff:
        return {"action": "Hold", "confidence": "medium",
                "reason": (f"deviation {deviation:+.2f}% clears the {rules['band_threshold_pct']:.2f}% "
                           f"band but not the {cutoff:.2f}% cutoff the holdout was validated at")}
    if abs(deviation) <= round_trip:
        return {"action": "Hold", "confidence": "medium",
                "reason": (f"deviation {deviation:+.2f}% does not cover the {round_trip:.1f}% "
                           "round-trip fee")}

    # --- conflicting evidence ---------------------------------------------------------------
    # The forecast cannot set direction - it loses to a random walk - but an interval that
    # contradicts the deviation signal is a reason to look rather than to act.
    interval_spans_zero = row.low80_pct < 0 < row.high80_pct
    predicted = float(row.predicted_change_pct)
    conflict = (deviation > 0 and predicted > 0) or (deviation < 0 and predicted < 0)

    action = "Sell TC" if deviation > 0 else "Buy TC"
    confidence = "medium"
    if conflict:
        return {"action": "Investigate", "confidence": "low",
                "reason": (f"deviation {deviation:+.2f}% implies {action.lower()}, but the fitted "
                           f"change {predicted:+.2f}% points the same way; signals disagree")}
    if interval_spans_zero:
        confidence = "low"
        reasons.append("80% range spans zero, so the size of the move is not established")
    if horizon["share_profitable"] < 0.6:
        confidence = "low"
        reasons.append(f"only {horizon['share_profitable']:.0%} of holdout episodes were profitable")

    reasons.insert(0, (
        f"deviation {deviation:+.2f}% clears the {cutoff:.2f}% cutoff the holdout was validated "
        f"at ({horizon['net_pct']:+.2f}% net over {horizon['n_effective']} effective episodes, "
        f"t={horizon['t_newey_west']:.1f})"
    ))
    return {"action": action, "confidence": confidence, "reason": "; ".join(reasons)}


def main() -> None:
    data = load()
    results = data["results"]
    rules = dict(RULES)
    rules["band_threshold_pct"] = float(results["advanced"]["tar"]["threshold_pct"])
    rules["action_threshold_pct"] = float(
        json.loads((P / "fundamentals_results.json").read_text())
        .get("scenarios", {}).get("levels", {}).get("arb_act_gap_pct", 4.0)
    ) if (P / "fundamentals_results.json").exists() else 4.0
    rules["fee_rate_pct"] = float(results["fees"]["rate_pct"])

    horizons = tradable_horizons(data["holdout"])
    # The shortest horizon that survives its own holdout; a longer one is not preferred merely
    # for reporting a larger number.
    chosen = min((h for h, spec in horizons.items() if spec["eligible"]), default=None)
    horizon_spec = horizons.get(chosen) if chosen else {
        "eligible": False,
        "reason": "no horizon clears the holdout requirement",
        "net_pct": float("nan"), "t_newey_west": float("nan"),
        "n_effective": 0, "share_profitable": float("nan"), "cutoff_pct": float("nan"),
    }

    predictions = data["predictions"]
    books = data["books"].set_index("world")
    as_of_max = predictions.as_of.max()

    rows = []
    for _, row in predictions.iterrows():
        book = books.loc[row.world] if row.world in books.index else None
        call = decide(row, rules, horizon_spec, book, as_of_max)
        rows.append({
            "world": row.world,
            "as_of": row.as_of.date(),
            "price_gp": row.price_gp,
            "deviation_pct": round(float(row.deviation_pct), 3),
            "predicted_change_pct": round(float(row.predicted_change_pct), 3),
            "low80_pct": round(float(row.low80_pct), 3),
            "high80_pct": round(float(row.high80_pct), 3),
            "horizon_days": chosen or "",
            "action": call["action"],
            "confidence": call["confidence"],
            "reason": call["reason"],
            "policy_version": POLICY_VERSION,
        })

    frame = pd.DataFrame(rows).sort_values(
        ["action", "deviation_pct"], ascending=[True, False]
    )
    frame.to_csv(P / "decision_policy.csv", index=False)

    backtest = data["backtest"]
    beats_rw = bool((backtest.model_mape < backtest.rw_mape).any())
    policy = {
        "version": POLICY_VERSION,
        "generated_utc": dt.datetime.now(dt.UTC).isoformat(),
        "rules": rules,
        "horizons": horizons,
        "horizon_used_days": chosen,
        "actions": ["Buy TC", "Sell TC", "Hold", "Avoid", "Investigate", "Abstain"],
        "signal_admitted": "cross-world relative deviation",
        "signals_refused": {
            "absolute price forecast": (
                "loses to a random walk at every tested horizon; carried as an uncertainty "
                "range only, never as a direction"
            ),
            "gold emission": (
                "no reliable association with forward returns at any tested lag, in or out of "
                "sample, on the 3.5-year panel"
            ),
        },
        "forecast_beats_random_walk": beats_rw,
        "counts": frame.action.value_counts().to_dict(),
        "limitations": [
            "Deviation is measured against a cross-world index, so a call is relative: every "
            "world can be fairly priced against the others while all of them move together.",
            "Holdout episodes overlap in calendar time; n_effective already discounts this, and "
            "horizons resting on too few episodes are refused rather than reported.",
            "Order-book depth is a single snapshot, so capacity is indicative and a large order "
            "will reach worse prices than the quoted side implies.",
            "Costs cover the Market fee only. Transfer restrictions, cancellation loss and "
            "partial fills are not deducted.",
        ],
    }
    (P / "decision_policy.json").write_text(json.dumps(policy, indent=1, default=str))

    print(f"[DECISION POLICY] v{POLICY_VERSION}, horizon {chosen or 'none'} days")
    print(f"  admitted: relative deviation | refused: price forecast, gold emission")
    for action, count in frame.action.value_counts().items():
        print(f"  {action:<12} {count:>3}")
    if not chosen:
        print("  no horizon survived its holdout; every world abstains")


if __name__ == "__main__":
    main()
