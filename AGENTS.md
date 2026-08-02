# Tibia Coins Intelligence — Collaboration Guide

This file is the shared operating contract for every coding or research agent
working in this repository. Product quality is measured by analytical rigor,
decision usefulness, clarity for different audiences, and reproducibility.

## Planning source of truth

Read [PROJECT_PLAN.md](PROJECT_PLAN.md) before starting material work. It is the
shared source of truth for current product status, analytical gaps, priorities,
dependencies, and completion criteria.

- Work from the highest-priority unblocked item unless the user asks otherwise.
- Give each material change a plan ID and keep its scope narrow.
- Before implementation, verify that the stated gap still exists in the current
  code, data, and rendered artifact.
- When finishing work, update the item status, evidence, tests, remaining risk,
  and `Last reviewed` date in the same commit.
- Add newly discovered gaps to the plan. Do not hide them in chat, commit
  messages, or code comments only.
- A feature is not complete merely because code exists; it must satisfy the
  item’s definition of done and the repository verifiers.
- If two agents work concurrently, claim an item by marking it `IN PROGRESS`
  with the agent and date before editing. Do not start an already claimed item
  without coordinating.
- Do not rewrite verified findings as backlog. Separate missing product
  communication, missing analysis, missing data, and optional enhancement.

## Product mission

Build the definitive evidence-based investment research product for the Tibia
Coin market across game worlds. The product must help users decide when to buy,
sell, hold, avoid, or investigate an arbitrage opportunity, while making the
uncertainty and practical constraints explicit.

The product is research and decision support, not a promise of profit. Never
turn a statistical association or a point forecast into certainty.

## Audiences

Every important result must work for three audiences at the same time:

1. **Tibia players**
   - Know the game but may not know statistics, economics, or finance.
   - Need plain language, intuitive examples, readable charts, and direct
     implications for buying, selling, holding, or arbitrage.
   - Introduce technical terms only after explaining what they mean in play.

2. **Data analysts and quantitative researchers**
   - Know statistics and machine learning but may not know Tibia.
   - Need the game mechanics explained, as well as data lineage, assumptions,
     sample size, diagnostics, uncertainty, robustness, validation, limitations,
     and reproducible outputs.

3. **Financial-market professionals**
   - Know investment research but may not know Tibia.
   - Translate game concepts into financial concepts without erasing the
     original Tibia term:
     - world = local market;
     - gold = domestic virtual currency;
     - Tibia Coin = premium currency with developer-controlled primary supply;
     - world transfer = constrained cross-market capital mobility.
   - Emphasize valuation, liquidity, microstructure, catalysts, alpha, risk,
     transaction costs, and executable constraints.

Do not write three disconnected reports. Use progressive disclosure so a player
can act on the first layer and a specialist can audit the deeper layers.

## Communication layers

Present every material finding in this order:

1. **Decision headline** — one plain-language sentence.
2. **Intuitive explanation** — what happened, why it may happen, and a concrete
   Tibia example.
3. **Technical evidence** — method, sample, effect size, uncertainty,
   validation, diagnostics, limitations, and source.

The player layer is the default visible layer. Never require the reader to
understand a statistical or financial term in order to understand the finding.
When a technical term is useful, show a plain-language label first and place
the technical name in supporting text or an expandable layer.

Examples:

- “How different world prices are” before “cross-world dispersion”;
- “error on later dates the model never saw” before “holdout RMSE”;
- “using today’s price as the future estimate” before “random walk”;
- “strongest 10% of price gaps” before “top decile”;
- “likely range, not a guaranteed target” before “80% forecast interval”;
- “price compared with the other worlds” before “relative deviation.”

Use [design/player_explanation_system.md](design/player_explanation_system.md)
as the canonical translation and page-review checklist.

For each result, answer:

1. What was observed?
2. Why might it happen?
3. What does it mean for the user or investor?
4. What action is supported now?

If the evidence does not support an action, say so directly. Distinguish
observation, interpretation, forecast, and recommendation visually and in text.

## Investment-research standard

Any rating, fair value, expected return, forecast, or strategy must state:

- world or world group;
- as-of date and forecast horizon;
- price unit and direction of the trade;
- baseline or comparison;
- uncertainty or scenario range;
- confidence level and reason for it;
- fees, transfer restrictions, liquidity, and other execution assumptions;
- principal risks, invalidation conditions, and data freshness.

Use calibrated language. Prefer “the evidence supports,” “is consistent with,”
or “did not show a reliable effect” over causal or certain claims that the
design cannot establish. A statistically insignificant result is not proof that
an effect is exactly zero.

Never invent a current opportunity. A “Buy,” “Sell,” or arbitrage call must be
computed from current, validated data and pass the applicable cost and risk
thresholds.

## Analytical requirements

- Preserve source data and document transformations.
- Keep world, date, unit, sample coverage, and data-quality flags traceable.
- Prevent look-ahead leakage in forecasting and backtesting.
- Use time-aware holdouts and compare against simple baselines.
- Report effect sizes and uncertainty, not only p-values or model scores.
- Separate exploratory findings from validated findings.
- Verify that report prose, tables, charts, and generated artifacts agree.
- Treat missingness, short histories, world launches, mergers, and structural
  breaks explicitly.
- Do not silently change a time window when the selected world changes. Keep
  the requested comparison window fixed and show unavailable periods honestly.
- Do not rebase price series to 100 by default. Show real prices and units;
  normalization may be an optional, clearly labeled comparison mode.

### Gold emission and Kill Statistics

Use Kill Statistics and reconstructed gold-emission data in analyses that make
claims about gold production. Distinguish:

- raw kill counts;
- direct coin drops;
- NPC-sale potential;
- assumed realization scenarios;
- gross gold production;
- net money-supply change, which is not observed without gold sinks and actual
  realization.

A claim that gold emission does or does not predict Tibia Coin prices must be
based on the reconstructed GP series, appropriate controls, lags, sensitivity
tests, and out-of-sample evidence—not raw kill counts alone.

Do not equate gold production with immediate Tibia Coin demand. Treat the
possible transmission chain explicitly:

`GP emission → GP circulation/market turnover → TC turnover → GP/TC price`

When studying this chain:

- use “GP-to-TC absorption lag” or “detectable circulation lag,” not “the time
  each GP takes to become a TC”;
- test whether GP-emission shocks precede TC turnover before testing price;
- estimate a distributed response across lags rather than selecting the largest
  isolated correlation;
- report the cumulative response and its confidence band;
- report a median/half-absorption time only when the cumulative response is
  positive, statistically distinguishable from zero, and stable out of sample;
- otherwise state that no conversion time is identifiable from the available
  data;
- disclose that anonymized aggregate data cannot trace individual GP from a
  creature drop into a Tibia Coin purchase.

### Model families

Keep model identity visible:

- **General model:** broad cross-world benchmark.
- **Specific model:** grouped by PvP type, BattlEye status, and location.
  PvP types must remain separate. When a group is too small, pool from the
  bottom up: relax location first, then BattlEye status; disclose the fallback.
- **Launch-phase model:** for newly launched worlds and their distinct market
  regime.

Show which model produced each result, its eligible population, fallback group,
training window, validation window, and confidence. “No model” must be explained
rather than displayed as an unexplained blank.

## Interface and editorial design

- The website is a complete publication of the research, not a summary or a
  companion dashboard. Every analysis, finding, limitation, table, and exhibit
  published in the PDF must also be discoverable on the site.
- Keep one canonical source for shared analytical content. Do not manually copy
  conclusions into separate PDF and site implementations that can drift.
- Site coverage must preserve the meaning and evidential depth of the analysis.
  Progressive disclosure may hide technical detail initially, but it must
  remain accessible on the same site.
- Quantitative content should be interactive when interaction materially helps
  comparison or exploration. A static representation is acceptable when
  interaction adds no analytical value, but the underlying method, source,
  sample, units, uncertainty, and limitations must still be available.
- New analysis is incomplete until it appears in every applicable publication
  surface and cross-artifact coverage checks pass.
- Optimize first for comprehension and decisions, then density.
- Maintain a clear hierarchy: conclusion, implication, evidence, details.
- Keep spacing, typography, controls, and chart behavior consistent across the
  Overview and all report sections.
- Define technical and Tibia-specific terms at first use.
- Use units as part of the meaning, not as decoration:
  - **GP** always means Tibia gold pieces;
  - **TC** always means Tibia Coins;
  - **GP/TC** is the price of one Tibia Coin measured in gold pieces.
  Never expand GP as “gold price.” GP names the in-game currency; price is a
  relationship between units.
  Never shorten gold-piece output to “coins,” because readers may interpret it
  as Tibia Coins. Use labels such as “Direct GP drops,” “Potential GP maximum,”
  and “Realized GP estimate.”
- Unit definitions, scope warnings, and interpretive disclaimers established in
  the canonical report must accompany the same analysis on the site. Moving an
  exhibit to the site without its governing caveat is a coverage defect.
- Every chart needs a descriptive title, units, time period, source, and a
  reader-facing takeaway. Legends and tooltips must expose meaningful values.
- Interactive filters must update all dependent text, metrics, charts, tables,
  dates, and provenance consistently.
- Preserve context when switching worlds; avoid surprising resets.
- Empty, partial, loading, stale, and error states must be explicit.
- Make methodology and limitations accessible without overwhelming the primary
  decision view.

Recommended report flow:

1. Executive Investment Summary
2. Investment Thesis
3. Market Overview
4. Market Intelligence
5. Valuation
6. Forecasts and Scenarios
7. Investment Strategy
8. Risk Analysis
9. Quantitative Research
10. Data and Methodology
11. Technical Appendix

## Collaboration and change safety

- Inspect the current worktree before editing.
- Treat existing changes as another collaborator’s work. Do not overwrite,
  revert, or reformat unrelated changes.
- Prefer small, auditable changes and reuse established components and data
  contracts.
- When changing a metric, model, or conclusion, update every dependent artifact
  and verification check.
- Run proportionate tests and artifact verifiers before declaring completion.
- Record important assumptions and unresolved limitations in the product, not
  only in chat.

## Git workflow

- Keep active work on the repository’s current shared branch unless the user
  explicitly requests another branch.
- Commit completed work with a descriptive message.
- Synchronize the completed commit with GitHub.
- Before pushing, confirm that the commit contains only intended files and does
  not overwrite a collaborator’s newer work.
