# Tibia Coins Intelligence — Living Product and Research Plan

**Last reviewed:** 2026-08-03 (GP-emission rebuild: AN-10 through AN-14 verified; all four verifiers clean)

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
| Market coverage | 93 worlds and 40,658 cleaned price observations through 2026-07-30; GP emission reconstructed over 90,701 world-days from 2022-08-22 | `VERIFIED` |
| General model | Relative-position model and current predictions for 61 eligible worlds | `VERIFIED` |
| Specific models | 11 hierarchical PvP/BattlEye/region models with disclosed pooling | `VERIFIED` |
| Launch phase | 3 PvP-specific experimental models and 18 current launch scores | `VERIFIED` |
| Gold emission | World-by-time workspace with direct GP and NPC potential, an all-worlds day drill-down that reconciles with `gold_emission_daily.csv.gz`, and a Creature GP per-kill reference page | `VERIFIED` |
| Research library | 34 interactive analytical exhibits | `VERIFIED` |
| Cross-artifact consistency | 10 headline checks agree; 0 coverage gaps; 0 numerical disagreements | `VERIFIED` |
| Comparison behavior | Actual GP prices by default; fixed cross-world date domain; missing history remains blank | `VERIFIED` |

Verification commands:

```bash
.venv/bin/python scripts/40_verify_intelligence_hub.py
.venv/bin/python scripts/46_verify_artifacts.py
```

Latest known verifier result: all four verifiers clean — 10 headline checks
agree, 0 coverage gaps, 0 disagreements. The standalone Gold Emission report is
now generated in-repo by `scripts/51_render_gold_emission_report.py`, so it
carries the GP-emission verdict and cannot freeze behind the data again.

## Now: ordered execution queue

Agents should normally work top to bottom. A lower item may proceed first only
when it is independent, the higher item is blocked, or the user changes the
priority.

| ID | Priority | Work item | Why now | Definition of done | Status |
|---|---:|---|---|---|---|
| SITE-00 | P0 | Publish the complete analysis on the site | The site is the primary interactive publication, not a shortened companion to the PDF | Every PDF section, finding, limitation, table, and exhibit has a discoverable site destination generated from canonical content; quantitative views are interactive where useful; an automated coverage manifest reports zero unexplained omissions and zero disagreements | `VERIFIED` — Claude, 2026-08-03; `scripts/52_coverage_manifest.py` pairs every published unit with a site destination and exits non-zero on an unexplained omission: 194 units — 8 chapters, 45 sections, 34 exhibits, 107 tables — with 0 unexplained and 1 declared (Table 0.1, the report's own question index, which is navigational apparatus rather than a series). Exhibits pair exactly rather than by guess: the PDF numbers them in the order `figure()` is called and the library is built from that same list, and the script asserts the three counts agree. Structure was previously unchecked — `46_verify_artifacts.py` compares shared numbers, so a whole chapter could have vanished from the site with every check still passing. Verified to have teeth by removing the Gold Emission view from the hub inventory, which fails chapter 3. Two silent-omission traps were found while building it: reading sections from extracted PDF text cannot separate a heading from a table row (`1.04 Ignibra` parses as a section), so sections come from the canonical source; and chapters 2-8 call `chapter()` while chapter 1 is front matter, so trusting those calls alone reported a seven-chapter document |
| SITE-01 | P0 | Complete a responsive visual and spacing audit of Overview | The Overview is the first impression and has already shown CSS/spacing regressions while new report content is being integrated | Desktop and narrow layouts inspected; hierarchy and spacing tokens consistent; no overlaps, clipped text, or misplaced controls; browser checks recorded; hub verifier passes | `VERIFIED` — Claude, 2026-08-03; measured in-browser at 1280x800 and 375x812 rather than judged from screenshots, which produced two false alarms before the DOM was read. All eight views clean at both widths: no page-level horizontal scroll, no element unreachable outside a scroll ancestor, no clipped text, no console errors. Wide tables sit in `overflow-x:auto` wrappers and scroll correctly; the sidebar collapses to a horizontal nav below the breakpoint. The audit caught a regression this session had introduced: the all-worlds TC price line was empty on the hub because `indexRows` was gated behind `include_prices`, which the hub sets to `False` — the standalone dashboard looked correct throughout, so only the hub exposed it |
| SITE-02 | P1 | Build an Executive Investment Summary decision surface | The current navigation exposes analytical tools but not one place answering buy/sell/hold/avoid, fair-value context, confidence, horizon, and risks | World selection produces an as-of-dated decision card; separates observation, forecast, and action; includes price/unit, horizon, range, confidence, costs, risks, invalidation, model used, freshness, and “insufficient evidence” state | `NEXT` |
| AN-01 | P1 | Define the decision and recommendation policy | A polished site must not turn raw forecasts into unsupported investment calls | Versioned rules map validated signals to Buy/Sell/Hold/Avoid/Investigate; transaction costs, liquidity, world eligibility, uncertainty, horizon, and conflicting signals are explicit; backtest and holdout evidence attached; policy can abstain | `NEXT` |
| SITE-03 | P1 | Add Investment Thesis and Market Overview journeys | Players need intuition; analysts and finance professionals need the Tibia market mechanics translated before methodology | Each major conclusion has headline, intuitive explanation, technical evidence, investor implication, and supported action; glossary translates Tibia and finance terms; content is linked to canonical narrative data | `PLANNED` |
| SITE-04 | P1 | Add dedicated Valuation and Risk views | These are promised decision questions but are currently dispersed through forecasts, strategy, and the report library | Valuation distinguishes relative value from non-forecastable absolute level; Risk covers liquidity, execution, model, data, game/platform, and venue risks; each risk is connected to affected decisions | `PLANNED` |
| SITE-05 | P0 | Make all analytical views player-first and audience-layered | The current site repeatedly exposes RMSE, holdout, dispersion, random walk, deviation, confidence, fixed effects, and related terms before explaining what they mean in Tibia | Every material card/chart starts with a player-readable conclusion and practical meaning; technical and financial layers remain expandable; terminology follows `design/player_explanation_system.md`; each view passes the player-comprehension checklist and browser QA | `IN PROGRESS` — Claude, 2026-08-02; Worlds regression repaired: the product's own Market vocabulary — `Buy TC`, `Sell TC`, `Mid`, `Spread`, `Demand depth`, `Supply depth`, `Reference mid`, `Quoted spread`, `Book snapshot`, `Latest executed midpoint`, `Latest executed buy / sell`, `Total return`, `7-day prediction` and the `Mid`/`Return (%)` chart modes — had been deleted and replaced by paraphrases, and is restored with a visible plain explanation on each label; bid/ask vocabulary stays in the data dictionary and is now blocked from Worlds labels by the verifier; Overview and Forecast tables use one compact terminology key instead of repeating definitions in every row; a visible “New to Tibia?” panel now translates worlds, world transfer, GP, TC, the Market, gold emission and the world attributes for analysts and finance professionals; Trading test and world-level Gold Emission first layers converted; Models and Research Library still require the same pass, and the reverse game-context layer still needs to reach Forecasts, Models, Strategy and Research Library |
| AN-02 | P1 | Create a world-level decision dataset | Site recommendations need one audited source rather than JavaScript combining unrelated outputs | One generated table contains as-of date, actual price, relative valuation, general/specific/launch outputs, selected production model, uncertainty, volatility flag, liquidity/capacity, strategy eligibility, action, confidence, risks, and provenance; schema and invariants verified | `PLANNED` |
| SITE-06 | P1 | Make provenance and freshness visible everywhere | A decision surface is unsafe when the reader cannot tell how current or complete it is | Each view shows data date, refresh state, source/model identity, eligibility/fallback, and stale/partial/error states; URL and filters remain shareable | `PLANNED` |
| AN-10 | P0 | Rebuild GP emission after the loot-quantity defect | Every published GP figure was computed from a loot table in which every stack counted as one unit | Quantity read from the source's empirical `total`; series, models, sensitivity and all artifacts rebuilt; a build-time assertion fails if the empirical quantity stops parsing | `VERIFIED` — Claude, 2026-08-03; `parse_loot_line` reads Loot2 fields by name after the greedy `times:([\d,]+)` pattern was found to swallow the separator, leaving `amount:` and `total:` unmatched on all 35,257 item rows. Direct emission x2.58 (3.12e12 -> 8.06e12 GP), potential emission x1.42, NPC share of potential 78.2% -> 60.2%. Loot-block selection now prefers the newest table clearing 100 kills instead of the newest table outright, recovering 67 creatures (Abyssador 2 kills -> 117; Energuardian of Tales 46 -> 8,558); non-boss death coverage 96.2% -> 98.3%. The emission-to-price null is unchanged under every specification, so the earlier null was not an artefact of the mismeasured regressor |
| AN-11 | P1 | Price the NPC buyer-access assumption instead of assuming it | `npc_sell_value_conservative_gp` was hardcoded to 0, so the "conservative NPC price" scenario was indistinguishable from direct coins and measured nothing | A conservative series priced at buyers reachable without a quest or store purchase, carried through the models and the sensitivity grid | `VERIFIED` — Claude, 2026-08-03; Rashid (Travelling Trader Quest) and Hirelings (bought with Tibia Coins) are excluded, premium travel treated as ordinary. 1,898 of 12,903 sellable rows lose value and 1,740 have a gated-only buyer. Kill-weighted, open-access pricing retains 71.2% of NPC-sale potential and 82.6% of total potential, so best-buyer access is worth ~17% of potential emission — previously reported as if it were worth everything |
| AN-12 | P2 | Re-export the standalone Gold Emission report | `reports/gold_emission_report.html` was an external portable-artifact export with no generator in the repo, so its numbers froze on export day and the verifier could name the gap but never close it | The HTML is regenerated from `gold_emission_report_artifact.json` and `46_verify_artifacts.py` reports no coverage gap | `VERIFIED` — Claude, 2026-08-03; `scripts/51_render_gold_emission_report.py` renders the manifest and snapshot the external reader consumed into a self-contained page (18 blocks, 3 SVG charts, 2 tables, 7 metric tiles, 28 kB against the old 676 kB, which bundled a whole JS reader), and runs in the `run_all.py --report` chain. Closing it surfaced two defects the opaque export had hidden: `46_verify_artifacts.py` compared every artifact against every fact regardless of the `scope` already declared on each fact, so the report was failed for contradicting a transaction-cost band it does not discuss — a coverage tile reading `80.00%` satisfies that fact's pattern as `0.00` — and the tile label `Threshold` was ambiguous where the project uses that word for the cost band, now `Coverage gate` |
| AN-14 | P2 | Publish the conservative-NPC and category-realisation scenarios on the site | Both series reached the data, the models and the sensitivity grid but not the site, so a reader could see the potential-emission number without seeing what it assumes | Gold Emission exposes both as selectable series with their governing caveats; hub and artifact verifiers pass | `VERIFIED` — Claude, 2026-08-03; both are selectable series in `scripts/emission_view.py`, off by default so four lines of unequal standing are not offered as alternatives of the same kind, and Reset restores the default pair. Over the panel the open-access series is 82.1% of potential and the category scenario 76.5%. The category series is labelled `Scenario: NPC sales by item category`, not `Realized GP estimate`: `37_verify_gold_emission.py` enforces `AGENTS.md`'s rule that realisation percentages are sensitivity scenarios and must not appear as a primary site metric, and it rejected the first label |
| AN-13 | P1 | Extend the monetary panel to the 3.5-year archive | The GP series covered 2025-12-03 onward while the activity panel reached 2022-08-23, so long-horizon tests stood on kill counts alone | `34b_emission_history.py` streams `tibia-kill-stats-from-2022-08-23-to-2025-12-04` world by world, the union passes the 50% per-world coverage floor, and models plus artifacts are rebuilt on the long panel | `VERIFIED` — Claude, 2026-08-03; 87 of 93 worlds read, 6 unavailable, 69,010 rows added. The series is now 90,701 world-days over 2022-08-22..2026-08-02 with 98.09% non-boss coverage on the pre-2025 half and zero blank rows, against 0% coverage in the withdrawn attempt. Models reach n=31,146 over 1,233 dates from 2023-01-11, where `panel_daily.csv` prices begin; emission exists earlier but has no price to join. The null is unchanged and better powered: p 0.54–0.80 across all 10 series, out-of-sample never better than +0.14% against the random walk. Three defects were fixed to get here — `git sparse-checkout add` rejects `--no-cone` and killed the fetch of the name normaliser; `partial_date_flag` measured every past date against today's 93 worlds and discarded 67.5% of the panel, which would have made the extension change nothing; and `34b` left the quality metrics behind, so the verifier demanded a re-run of `34_gold_emission.py`, which knows only the recent archive and would have deleted the history. `34b --rebuild-only` now re-derives the table without re-downloading |
| AN-03 | P1 | Resolve and qualify the Gold Emission communication gap | The standalone report omitted the direct-test result, while older wording elsewhere could read as rejecting a delayed circulation channel that was never measured | Site, PDF and standalone Gold Emission report state that direct GP-to-price tests found no reliable signal at separately tested 1–90 day delays, but did not model GP circulation into TC turnover and therefore cannot reject the full channel or estimate a conversion interval; artifact verifier reports no coverage gap or semantic disagreement | `VERIFIED` — Claude, 2026-08-03; closed by AN-12. The report is now generated in-repo, states the verdict and its scope limit in the same paragraph — “This is a result about the direct test only” — and `46_verify_artifacts.py` reports the `emission_channel` fact present in pdf, hub and gold_report with 0 coverage gaps |
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
| DATA-05 | Actual loot pickup and NPC-sale realization | Current 25/50/75/100% gold scenarios are assumptions, as is the per-item-category scenario added alongside them | Observed pickup/sale telemetry or a defensible external estimate | `BLOCKED — DATA` |
| DATA-11 | Item weight | Step 5 asks for a realization scenario weighted by carry cost, and Step 13 for a "coins plus light items" scenario; `tm_item_metadata.json` carries category but no weight, so value density stands in for carry cost | A per-item weight field, or a source that supplies one | `BLOCKED — DATA` |
| DATA-12 | Summon identification in kill statistics | Step 8 asks that summons be excluded to prevent double counting; TibiaWiki has "Summonable Creatures" and "Creatures that Use Summon" but no category marking a kill-statistics entry as itself summoned, so the zero summon count is unidentifiable rather than measured | A source that flags summoned kills in the statistics | `BLOCKED — DATA` |
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
