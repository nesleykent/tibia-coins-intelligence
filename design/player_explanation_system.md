# Player-First Explanation System

**Status:** canonical editorial specification

**Plan ID:** SITE-05

**Last reviewed:** 2026-08-02

## Goal

A Tibia player who has never studied statistics, economics, or finance should
understand the principal conclusion and its practical consequence without
opening a methodology section.

This is not “dumbing down” the analysis. It is progressive disclosure:

1. what it means in Tibia;
2. why it matters for a decision;
3. how the evidence was produced.

## Required structure for every important result

### 1. Player answer — visible by default

- What happened?
- Is it good, bad, or inconclusive for the player?
- What action, if any, does the evidence support?
- What is the largest caveat?

Use short sentences and Tibia examples. Do not begin with a model name.

### 2. Intuitive explanation — visible or one click away

Explain the mechanism with game language. For example:

> If one world sells Tibia Coins much cheaper than the others, buyers gradually
> use that opportunity. The difference usually shrinks only when it is large
> enough to pay the Market fees.

### 3. Technical evidence — expandable

Keep the full method, sample, uncertainty, diagnostics, robustness,
reproducibility, and limitations. Experts must not lose information merely
because the default layer is simpler.

## Canonical terminology

| Technical or financial term | Player-first label | Plain explanation |
|---|---|---|
| GP | Gold pieces | Tibia’s regular in-game currency |
| TC | Tibia Coins | The premium currency sold by CipSoft |
| GP/TC | Price of one TC in GP | How many gold pieces are needed to buy 1 TC |
| Market index | Typical price across worlds | A combined line showing the general TC price across the tracked worlds |
| Cross-world dispersion | Difference between world prices | Whether worlds are selling TC at similar or very different prices |
| Relative deviation | Price versus other worlds | How expensive or cheap this world is compared with the market |
| Convergence | Price difference shrinking | A cheap or expensive world moving back toward the others |
| Friction/no-trade band | Difference too small to cover costs | A price gap that is not worth trading after Market fees and execution risk |
| Random walk | Today’s price is the best central estimate | The models could not reliably improve on simply carrying today’s price forward |
| Forecast interval | Likely range, not a target | A range of plausible outcomes; values outside it can still happen |
| Volatility | How sharply the price moves | Larger volatility means faster and less predictable price swings |
| Holdout | Later dates the model never saw | Data reserved to test whether the model still works outside its training period |
| RMSE | Typical prediction error | Roughly how far the model’s predictions miss; lower is better |
| AUC | Ability to separate calm and volatile periods | How well the model ranks risky weeks above calm weeks |
| Confidence level | Strength of the evidence | How much trust the available sample and tests justify—not the chance of profit |
| Statistical significance | Signal distinguishable from noise | Whether the observed pattern is strong enough that ordinary variation is an unlikely explanation |
| t-statistic / Newey-West | Robustness check for the result | A technical check that accounts for repeated and overlapping observations |
| Fixed effects | Fair comparison within the same world and date environment | Controls for permanent differences between worlds and market-wide daily shocks |
| Top decile | Strongest 10% of signals | Only the largest price gaps in every ten signals |
| Liquidity | Ease of buying or selling | How much TC can trade without waiting too long or moving the price |
| Capacity | How much GP the strategy can realistically use | A good percentage return may still accept only a limited amount of GP |
| Gold emission | GP generated through hunting | Direct GP drops plus modeled NPC-sale value from loot |
| Realization scenario | Assumed share of loot actually turned into GP | Not every dropped item is collected and sold to an NPC |
| Coverage | Share of deaths represented reliably | Low coverage means more of the generated GP is unknown |
| General model | Model shared across many worlds | Uses the larger sample and is the default when it performs better |
| Specific model | Model for similar world groups | Groups worlds by PvP, BattlEye, and region when enough data exists |
| Launch model | Experimental model for new worlds | New worlds have little accumulated GP and behave differently from mature ones |

## Words that require immediate explanation

Never leave these unexpanded in the default player layer:

- alpha;
- arbitrage;
- AUC;
- confidence interval;
- convergence;
- correlation;
- decile;
- deviation;
- dispersion;
- fixed effects;
- holdout;
- liquidity;
- Newey-West;
- random walk;
- realization;
- regime;
- RMSE;
- unit root;
- volatility.

The technical term may appear in parentheses after the plain label.

## Per-view reading path

### Overview

1. What is the typical TC price now?
2. Are worlds close together or far apart?
3. Is there a current actionable signal?
4. What should the player avoid concluding?

### Worlds

1. Which world is cheaper?
2. By how much in GP and percentage?
3. Is the gap large enough to matter after costs?
4. Is history missing for either world?

### Forecasts

1. What is the likely range?
2. How uncertain is it?
3. Does the model beat using today’s price?
4. Is the forecast about the common price or only the world’s relative position?

### Models

1. Which model is being used for this world?
2. Did it predict later unseen dates better?
3. What does its typical error mean in GP or percentage?
4. Why might a specific or launch model not be available?

### Strategy

1. What exact signal starts a trade?
2. What happens after fees?
3. How often did it work on later unseen dates?
4. How much GP can realistically be used?
5. When should the player do nothing?

### Gold Emission

1. How much GP was generated?
2. Which amount is observed and which is a scenario?
3. How much of the loot table is covered?
4. Is there evidence that this affects TC turnover or price?
5. Is the effect immediate, delayed, or not identifiable?

### Research Library

Every exhibit needs:

- one-sentence player takeaway;
- “why this matters”;
- units and period;
- a visible limitation;
- expandable technical method.

## Comprehension checklist

Before marking a view complete, verify:

- The first visible paragraph contains no unexplained technical term.
- A player can describe the chart without reading its tooltip.
- Every percentage states what changed and against what.
- Every prediction distinguishes range from certainty.
- Every recommendation includes a “do nothing” condition.
- GP, TC, and GP/TC are never ambiguous.
- “No evidence” is not written as “proof of no effect.”
- Scenario assumptions are visually different from observations.
- Model quality is translated into an intuitive error or comparison.
- The main limitation is visible before the technical appendix.
- The full statistical evidence remains accessible to expert readers.

## QA method

For each view:

1. Read only the default visible layer and summarize it as a player.
2. Record every term requiring outside statistical or financial knowledge.
3. Replace or explain those terms contextually.
4. Open the technical layer and confirm no evidence was lost.
5. Test desktop and mobile reading order.
6. Verify keyboard access to every expandable explanation.
