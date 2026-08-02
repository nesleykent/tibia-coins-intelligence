# GP-to-TC Absorption Lag

**Status:** analytical design; implementation pending

**Plan IDs:** AN-08 and SITE-09

**Last reviewed:** 2026-08-02

## Decision question

After a world generates an unusually large amount of GP, is there a detectable
delay before activity increases in the Tibia Coin market? If so, how is that
response distributed through time?

This is analogous to a cash-conversion or working-capital cycle, but the
available data observes aggregate markets rather than individual wallets.

## What can and cannot be measured

The project can observe, by world and day:

- reconstructed direct GP drops;
- potential NPC-sale GP;
- realization scenarios for NPC-sale value;
- TC bought and sold through the observed in-game Market;
- GP/TC prices;
- player activity and world characteristics.

It cannot observe:

- which player received each unit of GP;
- whether that GP was saved, spent on supplies, consumed by a sink, transferred,
  or used to purchase TC;
- account-level GP balances;
- signed participant-level order flow;
- all TC venues at world-day frequency.

Therefore the estimand is a **detectable aggregate absorption lag**, not the
literal time taken by an identifiable GP unit to become a TC purchase.

## Economic transmission chain

1. Creatures die and generate direct GP plus loot with potential NPC value.
2. Players collect, sell, save, spend, or lose that GP to sinks.
3. Some available GP may fund TC demand in the in-game Market.
4. Additional demand may change TC turnover.
5. Only an imbalance between demand and supply can affect the GP/TC price.

The analysis must test each observable link. It must not skip directly from
deaths to a claimed conversion time.

## Primary variables

### Exposure

Run the analysis separately for:

- direct GP drops;
- realized GP estimate at 25%, 50%, 75%, and 100%;
- potential GP maximum as an upper-bound scenario.

Use logarithmic innovations or deviations from a world-specific expected level,
not raw totals alone. Activity-normalized versions are required as sensitivity
checks.

### Intermediate outcome

Primary TC-turnover measure:

`TC turnover = tc_bought + tc_sold`

The archive fields are already converted from 25-TC lots into TC. Never apply
the lot multiplier a second time.

Secondary measures:

- TC bought;
- TC sold;
- TC-turnover value in GP;
- buy/sell imbalance, only with a documented interpretation of the source
  fields;
- turnover per average online player.

### Final outcome

- future log change in GP/TC price;
- future change in relative world price versus the cross-world mean.

The relative outcome is important because the common price level has not beaten
a random walk in existing holdouts.

## Estimation plan

### Stage 1 — GP emission to TC turnover

Estimate a panel distributed-lag response for lags 0 through 90 days:

`TC_turnover(w,t) = world FE + date FE + Σ β(k) GP_shock(w,t-k) + controls + error`

Use a regularized or smooth lag basis to avoid selecting a noisy coefficient
from 91 separate tests. Controls should include lagged TC turnover, online-player
activity, calendar effects not absorbed by date fixed effects where applicable,
data-quality flags, and a consistent sample gate.

Report:

- the daily lag-response curve;
- simultaneous confidence bands;
- cumulative response through 7, 14, 30, 60, and 90 days;
- share of any positive cumulative response absorbed through each horizon;
- world and period stability;
- time-holdout performance against a no-emission baseline.

### Stage 2 — TC turnover to price

Test whether the emission-associated turnover component precedes:

- GP/TC price returns;
- relative-price convergence;
- volatility.

This stage remains descriptive unless a defensible instrument or natural
experiment is established. More TC turnover alone does not imply upward price
pressure because turnover is unsigned and every completed trade has two sides.

### Identification rule

Publish a median or half-absorption time only when all conditions hold:

1. The cumulative Stage-1 response is positive.
2. Its joint confidence interval excludes zero over a declared horizon.
3. The cumulative response is not driven by one world or short period.
4. The response keeps the same broad shape in an untouched later-date holdout.
5. Results are not reversed across reasonable GP-realization scenarios.

If these conditions fail, the site must display:

> No reliable GP-to-TC absorption time is identifiable from the available
> aggregate data.

Zero, one day, or the largest isolated coefficient must never be substituted for
an unidentified absorption time.

## Required robustness

- direct GP versus all realization scenarios;
- levels, innovations, and activity-normalized exposure;
- 0–30, 0–60, and 0–90-day lag windows;
- established worlds versus launch-phase worlds;
- PvP/BattlEye/region groups where sample size permits;
- exclusion of partial and low-coverage kill-stat dates;
- world and date fixed effects;
- two-way clustered or block-bootstrap uncertainty;
- placebo leads: future GP emission must not predict past TC turnover;
- leave-one-world-out and leave-one-month-out influence checks;
- time-aware holdout;
- raw kill count as a non-monetary benchmark.

Because the current kill-statistics history is short, the effective number of
independent 60- and 90-day windows must be shown prominently.

## Site presentation

The Gold Emission view should add an **Absorption into TC market** section with:

1. A one-sentence result: identified time range or “not identifiable.”
2. An intuitive cash-cycle explanation for players.
3. A two-line time chart of GP emission and TC turnover with an optional,
   clearly labeled lag alignment.
4. A lag-response chart with zero line and confidence band.
5. A cumulative-response chart with 7/14/30/60/90-day markers.
6. World, date, GP scenario, normalization, and world-group controls.
7. Sample size, independent-window count, holdout result, and data freshness.
8. An expandable technical layer containing the specification, robustness, and
   limitations.

The charts must use GP for gold pieces, TC for Tibia Coins, and GP/TC for price.
The phrase “gold converts into Tibia Coins” may be used only as an intuitive
question; the measured result must be labeled aggregate absorption.

## Deliverables

- `data/processed/gold_to_tc_lag_response.csv`
- `data/processed/gold_to_tc_cumulative_response.csv`
- `data/processed/gold_to_tc_holdout.csv`
- `data/processed/gold_to_tc_absorption_summary.json`
- reproducible analysis script and verifier
- canonical report finding and limitations
- PDF section
- interactive site section
- cross-artifact coverage check
