# Tibia Coins Intelligence — Living Product and Research Plan

**Last reviewed:** 2026-08-03

**Shared branch:** `main`

**Purpose:** show what exists, what is missing, why it matters, and what should
be built next across the site and the complete analysis.

This is a living execution document, not a wish list. Update it whenever a gap
is verified, claimed, completed, invalidated, or blocked.

## Status language

| Status | Meaning |
|---|---|
| `VERIFIED` | Present, tested, and supported by a named artifact or verifier |
| `IN PROGRESS` | Claimed by an agent; owner and start date must be recorded |
| `NEXT` | Highest-priority unblocked work |
| `PLANNED` | Valuable, defined, but sequenced after `NEXT` items |
| `BLOCKED — DATA` | Cannot be answered credibly with current observations |
| `RESEARCH QUESTION` | A hypothesis, not an established finding |
| `NOT PLANNED` | Deliberately excluded, with the reason recorded |

Priority means:

- **P0:** misleading, inconsistent, broken, or unsafe for decisions.
- **P1:** required for the promised investment-research product.
- **P2:** important depth, usability, or analytical improvement.
- **P3:** optional enhancement.

## Verified foundation

These are not backlog items unless a new check demonstrates a regression.

| Area | Current evidence | Status |
|---|---|---|
| Unified interactive workspace | Overview, Worlds, Forecasts, Models, Strategy, Gold Emission, Creature GP, and Research Library, all rendered natively by the hub | `VERIFIED` |
| Market coverage | 93 worlds and 40,658 cleaned price observations through 2026-07-30 | `VERIFIED` |
| General model | Relative-position model and current predictions for 61 eligible worlds | `VERIFIED` |
| Specific models | 11 hierarchical PvP/BattlEye/region models with disclosed pooling | `VERIFIED` |
| Launch phase | 3 PvP-specific experimental models and 18 current launch scores | `VERIFIED` |
| Gold emission | World-by-time workspace with direct GP and NPC potential, an all-worlds day drill-down that reconciles with `gold_emission_daily.csv`, and a Creature GP per-kill reference page | `VERIFIED` |
| Research library | 34 interactive analytical exhibits | `VERIFIED` |
| Cross-artifact consistency | 9 headline checks agree; 0 numerical disagreements | `VERIFIED` |
| Comparison behavior | Actual GP prices by default; fixed cross-world date domain; missing history remains blank | `VERIFIED` |

Verification commands:

```bash
.venv/bin/python scripts/40_verify_intelligence_hub.py
.venv/bin/python scripts/46_verify_artifacts.py
```

Latest known verifier result: one communication coverage gap remains—the main
PDF and hub state the reconstructed GP-emission null, while the standalone Gold
Emission report does not state that verdict explicitly.

## Now: ordered execution queue

Agents should normally work top to bottom. A lower item may proceed first only
when it is independent, the higher item is blocked, or the user changes the
priority.

| ID | Priority | Work item | Why now | Definition of done | Status |
|---|---:|---|---|---|---|
| SITE-00 | P0 | Publish the complete analysis on the site | The site is the primary interactive publication, not a shortened companion to the PDF | Every PDF section, finding, limitation, table, and exhibit has a discoverable site destination generated from canonical content; quantitative views are interactive where useful; an automated coverage manifest reports zero unexplained omissions and zero disagreements | `NEXT` |
| SITE-01 | P0 | Complete a responsive visual and spacing audit of Overview | The Overview is the first impression and has already shown CSS/spacing regressions while new report content is being integrated | Desktop and narrow layouts inspected; hierarchy and spacing tokens consistent; no overlaps, clipped text, or misplaced controls; screenshots or browser checks recorded; hub verifier passes | `NEXT` |
| SITE-02 | P1 | Build an Executive Investment Summary decision surface | The current navigation exposes analytical tools but not one place answering buy/sell/hold/avoid, fair-value context, confidence, horizon, and risks | World selection produces an as-of-dated decision card; separates observation, forecast, and action; includes price/unit, horizon, range, confidence, costs, risks, invalidation, model used, freshness, and “insufficient evidence” state | `NEXT` |
| AN-01 | P1 | Define the decision and recommendation policy | A polished site must not turn raw forecasts into unsupported investment calls | Versioned rules map validated signals to Buy/Sell/Hold/Avoid/Investigate; transaction costs, liquidity, world eligibility, uncertainty, horizon, and conflicting signals are explicit; backtest and holdout evidence attached; policy can abstain | `NEXT` |
| SITE-03 | P1 | Add Investment Thesis and Market Overview journeys | Players need intuition; analysts and finance professionals need the Tibia market mechanics translated before methodology | Each major conclusion has headline, intuitive explanation, technical evidence, investor implication, and supported action; glossary translates Tibia and finance terms; content is linked to canonical narrative data | `PLANNED` |
| SITE-04 | P1 | Add dedicated Valuation and Risk views | These are promised decision questions but are currently dispersed through forecasts, strategy, and the report library | Valuation distinguishes relative value from non-forecastable absolute level; Risk covers liquidity, execution, model, data, game/platform, and venue risks; each risk is connected to affected decisions | `PLANNED` |
| SITE-05 | P0 | Make all analytical views player-first and audience-layered | The current site repeatedly exposes RMSE, holdout, dispersion, random walk, deviation, confidence, fixed effects, and related terms before explaining what they mean in Tibia | Every material card/chart starts with a player-readable conclusion and practical meaning; technical and financial layers remain expandable; terminology follows `design/player_explanation_system.md`; each view passes the player-comprehension checklist and browser QA | `IN PROGRESS` — Claude, 2026-08-02; Worlds regression repaired: the product's own Market vocabulary — `Buy TC`, `Sell TC`, `Mid`, `Spread`, `Demand depth`, `Supply depth`, `Reference mid`, `Quoted spread`, `Book snapshot`, `Latest executed midpoint`, `Latest executed buy / sell`, `Total return`, `7-day prediction` and the `Mid`/`Return (%)` chart modes — had been deleted and replaced by paraphrases, and is restored with a visible plain explanation on each label; bid/ask vocabulary stays in the data dictionary and is now blocked from Worlds labels by the verifier; Overview and Forecast tables use one compact terminology key instead of repeating definitions in every row; a visible “New to Tibia?” panel now translates worlds, world transfer, GP, TC, the Market, gold emission and the world attributes for analysts and finance professionals; Trading test and world-level Gold Emission first layers converted; Models and Research Library still require the same pass, and the reverse game-context layer still needs to reach Forecasts, Models, Strategy and Research Library |
| AN-02 | P1 | Create a world-level decision dataset | Site recommendations need one audited source rather than JavaScript combining unrelated outputs | One generated table contains as-of date, actual price, relative valuation, general/specific/launch outputs, selected production model, uncertainty, volatility flag, liquidity/capacity, strategy eligibility, action, confidence, risks, and provenance; schema and invariants verified | `PLANNED` |
| SITE-06 | P1 | Make provenance and freshness visible everywhere | A decision surface is unsafe when the reader cannot tell how current or complete it is | Each view shows data date, refresh state, source/model identity, eligibility/fallback, and stale/partial/error states; URL and filters remain shareable | `PLANNED` |
| AN-03 | P1 | Resolve and qualify the Gold Emission communication gap | The standalone report omits the direct-test result, while the existing PDF wording can be read as rejecting a delayed circulation channel that was not measured | Site, PDF and standalone Gold Emission report state that direct GP-to-price tests found no reliable signal at separately tested 1–90 day delays, but did not model GP circulation into TC turnover and therefore cannot reject the full channel or estimate a conversion interval; artifact verifier reports no coverage gap or semantic disagreement | `NEXT` |
| QA-01 | P1 | Expand browser-level interaction and accessibility QA | Static string checks cannot catch spacing, filter synchronization, keyboard, tooltip, or responsive failures | Automated or recorded browser tests cover all views, world/date switching, fixed windows, URLs, empty states, keyboard focus, responsive breakpoints, console errors, and the Gold Emission and Creature GP views | `PLANNED` |
| SITE-07 | P2 | Connect Research Library exhibits to decisions | The library is deep but readers must currently infer which exhibit supports which action | Each thesis, valuation, forecast, strategy, and risk claim links to the exact exhibit/method; exhibits link back to the decision they support or limit | `PLANNED` |
| AN-04 | P2 | Test Gold Emission as an explicit challenger feature in model families | Gold emission is tested as an economic channel but is not a central feature of the general/specific/launch scoring families | Leakage-safe feature experiment across eligible families; identical time holdouts and baselines; incremental performance and stability reported; feature is adopted only if it improves out-of-sample decisions | `PLANNED` |
| SITE-08 | P0 | Add shared selectable time windows and unambiguous GP/TC units | Overview metrics appeared unchanged after date selection, Worlds lacked a range control, and “Direct coins” could be read as Tibia Coins | Overview and Worlds share a URL-backed fixed date range; switching worlds never resets it; returns and range metrics use the selected window; Gold Emission uses Direct GP drops/Potential GP maximum/Realized GP estimate and carries the GP-versus-TC disclaimer; browser interaction and repository verifiers pass | `VERIFIED` — Codex, 2026-08-02 |
| AN-08 | P1 | Estimate the GP-to-TC absorption lag | Existing models test whether emission predicts price at selected lags, but do not measure the intermediate capital-turnover path from newly generated GP into TC trading | A preregistered distributed-lag analysis tests GP emission → TC turnover and then TC turnover → price; reports cumulative response and uncertainty over 0–90 days; provides a median/half-absorption time only if identified and stable in a time holdout; separates direct GP drops and realization scenarios; never interprets aggregate association as traced individual conversion | `NEXT` — design specified in `design/gold_to_tc_absorption.md` |
| SITE-12 | P0 | Make Gold Emission a native view with an honest all-worlds day drill-down and a dedicated Creature GP page | The view was an iframe rather than a hub page, the day drill-down refused to answer for “All worlds”, and it read the wrong day's kill-statistics file | Gold Emission and Creature GP render from one shared component (`scripts/emission_view.py`) used by the hub and the standalone pages; the day drill-down sums every reporting world and reconciles exactly with `gold_emission_daily.csv` (2026-07-30: 85,750,669 deaths, 72,135,275,683 potential GP, bosses reported separately); partial, stopped and failed-world states are explicit; table sorting runs on the full dataset and survives re-render; `scripts/37_verify_gold_emission.py`, `scripts/40_verify_intelligence_hub.py` and `scripts/46_verify_artifacts.py` pass | `VERIFIED` — Claude, 2026-08-03; remaining: the series label is now “Direct GP” everywhere the repository generates, but `reports/gold_emission_report.html` is an external export and keeps “Direct GP drops” until it is re-exported from the updated `gold_emission_report_artifact.json` |
| SITE-09 | P1 | Publish GP circulation and absorption interactively | Players need an intuitive answer to “how long could generated GP take to reach the TC market?” without being shown false precision | Gold Emission gains an “Absorption into TC market” section with emission, TC turnover, lag-response, cumulative absorption, world/range/scenario controls, sample and confidence; plain-language cash-cycle explanation; explicit “not identifiable” state when evidence is insufficient; full method and limitations available on site | `PLANNED` — depends on AN-08 |
| SITE-10 | P0 | Replace ambiguous single-price presentation with buy, sell, mid, spread, demand and supply | A midpoint alone is not an executable price and hides the cost and capacity a player faces | Shared definitions govern every artifact; Worlds exposes historical buy/sell/mid series and the current best bid, best ask, quoted spread and both depth sides; remaining forecasts, valuation, strategy, PDF and exhibits migrate without relabeling an executed-side gap as a quoted spread | `IN PROGRESS` — Codex, 2026-08-02; shared contract and Worlds first layer implemented, remaining publication surfaces require migration |
| AN-09 | P1 | Measure variable strength in price composition and price movement | Existing SHAP, permutation importance, feature-selection, partial-dependence and variance-decomposition outputs are fragmented and can be mistaken for causal explanations | Separate price-level composition from future price movement; report variable and feature-family strength, direction, uncertainty, horizon, model family, out-of-sample contribution and time/world stability; compare at least two compatible importance methods; quantify common-market versus world-specific variation; explicitly identify unstable, redundant and non-incremental variables; never translate predictive importance into causality | `NEXT` |
| SITE-11 | P1 | Publish an interactive price-driver view | Players and specialists need to understand what appears to matter, in which direction, and how reliable that conclusion is | Site presents player-first driver families, level-versus-movement toggle, world/group/horizon/model filters, signed effect shape, normalized importance, uncertainty, stability and incremental holdout value; technical layer exposes SHAP, permutation, partial dependence, feature-selection agreement, correlations among predictors and limitations; “not reliably identified” is a supported result | `PLANNED` — depends on AN-09 |

## Site gap inventory

This inventory distinguishes “available somewhere” from “usable as a product
journey.”

| Product question | Current state | Missing product behavior | Related queue |
|---|---|---|---|
| Where is the complete research? | PDF contains the full narrative and the site exposes eight views plus 34 exhibits | Full section-by-section site publication with no unexplained omissions from the PDF | SITE-00, QA-01 |
| What is happening now? | Overview and world charts exist | Stronger responsive hierarchy and a concise market regime explanation | SITE-01, SITE-03 |
| Should I buy, sell, hold, or avoid? | Strategy evidence and forecasts exist separately | Audited recommendation policy and unified decision card | AN-01, AN-02, SITE-02 |
| Is the coin cheap or expensive? | Relative deviations and scenarios exist | Dedicated valuation framing; do not imply a forecastable absolute fair value | SITE-04 |
| What return might I expect? | Scenario fans and strategy horizons exist | Net expected outcome tied to eligibility, capacity, uncertainty, and execution assumptions | SITE-02, AN-02 |
| Can I arbitrage? | Threshold and holdout research exist | Executable opportunity state, abstention rules, transfer feasibility, and capacity warning | AN-01, SITE-02 |
| What model am I seeing? | Model comparison view exists | Model identity and fallback displayed on every downstream decision | SITE-06, AN-02 |
| What can go wrong? | Risks and limitations exist in the PDF | Dedicated decision-linked risk view | SITE-04 |
| Why should I trust this? | Technical report, library, and verifiers exist | Progressive evidence links and visible freshness/provenance | SITE-05, SITE-06, SITE-07 |
| What is actually moving the price? | Several technical importance and decomposition outputs exist separately | One coherent view separating price-level composition, future movement, direction, strength, stability and non-causal interpretation | AN-09, SITE-11 |
| Can each audience understand it? | Mixed explanatory content exists | Consistent three-layer treatment across the site | SITE-05 |
| Does interaction behave predictably? | Core filters and URLs exist | Full browser, accessibility, responsive, loading, and error-state coverage | QA-01 |

## Analysis gap inventory

### Answerable with current data or engineering

| ID | Gap | Current boundary | Next analytical action | Status |
|---|---|---|---|---|
| AN-01 | Recommendation policy | Findings exist, but no single governed mapping from evidence to action | Specify and validate an abstaining decision policy | `NEXT` |
| AN-02 | Unified decision record | Outputs are spread across multiple processed tables | Generate and verify one world/as-of decision dataset | `PLANNED` |
| AN-03 | Gold report conclusion coverage and qualification | Direct-test null is omitted from the standalone report; old wording elsewhere overreaches beyond the tested circulation path | Publish one canonical, qualified conclusion across site, PDF and standalone report, then extend verifier coverage to detect semantic disagreement | `NEXT` |
| AN-04 | Incremental predictive value of emission in deployed model families | Emission channel was tested separately | Run leakage-safe challenger experiment; do not assume benefit | `PLANNED` |
| AN-05 | Decision calibration | Model metrics do not by themselves show whether confidence labels are calibrated for actions | Define confidence buckets and test realized outcomes/coverage by bucket | `PLANNED` |
| AN-06 | Strategy sensitivity to realistic execution | One-day delay and known costs are tested; fill uncertainty remains only partly observed | Stress delay, slippage, partial fills, capacity, and cancellation loss using bounded scenarios | `PLANNED` |
| AN-07 | Monitoring and drift | Current artifacts are refreshed, but decision drift thresholds are not a product contract | Define freshness, coverage, feature drift, forecast degradation, and model fallback alerts | `PLANNED` |
| AN-08 | GP-to-TC absorption lag | Current lag models go directly from GP emission to future GP/TC returns and therefore do not estimate the intermediate turnover mechanism | Estimate a distributed lag from excess GP emission to TC turnover, followed by the conditional price response; publish an absorption time only if the cumulative response is identified and holdout-stable | `NEXT` |
| AN-09 | Variable strength and price drivers | SHAP, permutation importance, feature-selection votes, partial dependence and common/idiosyncratic variance are available but answer different questions and are not yet reconciled | Build a horizon- and model-aware driver analysis that separates level from movement, measures incremental out-of-sample value, compares compatible attribution methods and reports stability across time and world groups | `NEXT` |

### Blocked by missing observations

These items must not be “solved” by inventing proxies without labeling the
identification change.

| ID | Missing evidence | Why it matters | What would unblock it | Status |
|---|---|---|---|---|
| DATA-01 | Historical Char Bazaar flow by date and preferably world | Bazaar volume is much larger than the observed in-game Market and may improve volatility/participant analysis | Reproducible time series with definitions and world/date grain | `IN PROGRESS` — Claude, 2026-08-02; newly detected collection and analysis files still require review and validation |
| DATA-02 | Historical order-book snapshots | Needed for quoted spread, depth, fill probability, round-number behavior, and realistic execution | Scheduled bid/ask/amount snapshots with stable timestamps | `BLOCKED — DATA` |
| DATA-03 | Longer character-transfer history | Needed to test migration as a cross-world linkage channel | Maintained daily archive beyond the rolling source window | `BLOCKED — DATA` |
| DATA-04 | Gold stock and major gold-sink flows | Gross production is not net money-supply change | Sink series plus stock or credible stock reconstruction | `BLOCKED — DATA` |
| DATA-05 | Actual loot pickup and NPC-sale realization | Current 25/50/75/100% gold scenarios are assumptions | Observed pickup/sale telemetry or a defensible external estimate | `BLOCKED — DATA` |
| DATA-06 | Historical real-money Tibia Coin/token/reseller prices | Needed for time-varying real-money valuation across venues | Audited dated price series with fees and venue definitions | `BLOCKED — DATA` |
| DATA-07 | Historical world population/premium composition | Current population snapshot cannot enter daily causal/predictive panels safely | Repeated consistent census by world and date | `BLOCKED — DATA` |
| DATA-08 | Participant/account-level holdings and signed order flow | Needed for concentration, disposition effects, and buyer/seller attribution | Privacy-safe participant identifiers and transaction direction | `BLOCKED — DATA` |
| DATA-09 | Independent cross-check for historical world prices | A single upstream mirror can propagate collection errors | Second source with overlapping world/date coverage | `BLOCKED — DATA` |
| DATA-10 | Pre-merge destination-world histories | Required for credible merger event studies | Genuine observations before each merger—not reconstructed values | `BLOCKED — DATA` |

## Research questions, not findings

- Do offers cluster at psychologically salient GP levels, and does this slow
  adjustment?
- Do updates cause overreaction followed by correction, rather than rational
  anticipation?
- Are character transfers and Tibia Coin flows substitute integration channels?
- Does signed attention or demand explain event effects in more active worlds?
- Can Bazaar flow improve volatility forecasts without improving directional
  price forecasts?

Keep these labeled as hypotheses until the necessary data and design exist.

## Definition of done for the full product

The product is decision-ready only when all of the following are true:

- The site answers buy, sell, hold, avoid, and arbitrage questions with an
  explicit option to say “insufficient evidence.”
- Every analysis, finding, limitation, table, and exhibit in the PDF is
  discoverable on the site, with equivalent meaning and evidential depth.
- An automated coverage manifest maps canonical analysis IDs to their PDF and
  site destinations and reports zero unexplained omissions or disagreements.
- Quantitative analysis is interactive where filtering, comparison, tooltips,
  drill-down, or scenario selection improves understanding.
- Every action states world, date, unit, horizon, expected range, confidence,
  costs, capacity, risks, freshness, and model identity.
- Players can understand the decision without reading formulas.
- analysts can reproduce the data and validate the method.
- financial professionals can evaluate valuation, liquidity, execution, alpha,
  and risk without knowing Tibia beforehand.
- Site, PDF, standalone reports, and decision datasets agree on every shared
  quantitative claim.
- All interactive views pass functional, responsive, accessibility, empty-state,
  stale-state, and error-state checks.
- All adopted models beat their stated baselines on untouched time-aware
  holdouts for the decision they are used to support.
- Known missing data remains visible, and no blocked question is presented as a
  solved finding.

## Work-item update template

Copy this block when adding or completing a material item:

```text
ID:
Title:
Priority:
Status:
Owner:
Started:
Last reviewed:
User decision supported:
Verified gap:
Scope:
Dependencies:
Definition of done:
Evidence/tests:
Remaining limitations:
Files/artifacts changed:
Commit:
```
