# Research Data Platform

Status: active on the Platform 0.9.1 research-upgrade branch.

## Purpose

The research-data capability supports the hedge-fund dashboard with read-only public-market information. It is a Platform Backend domain and is not part of trade execution, formal accounting or Venue reconciliation.

## Runtime flow

```text
Vue research pages
  -> /api/v1/research/**
  -> research_routes.py
  -> research_service.py
  -> research_providers.py
  -> free public market-data sources
```

The frontend never calls external market-data sources directly. `execution-runtime` is not imported or invoked by this flow.

## Authoritative modules

| Responsibility | Owner |
|---|---|
| Public response models and data-quality metadata | `platform-backend/app/research_data_schemas.py` |
| Deterministic A-share formulas and Shenwan aggregation | `platform-backend/app/a_share_research_policy.py` |
| TTL and last-known-good behavior | `platform-backend/app/research_cache.py` |
| Free-source adapters and field normalization | `platform-backend/app/research_providers.py` |
| Concurrent orchestration and partial-failure semantics | `platform-backend/app/research_service.py` |
| Authenticated HTTP routes | `platform-backend/app/research_routes.py` |
| Frontend API contract | `admin-risk/src/api/hedgeResearch.ts` |
| A-share page orchestration | `admin-risk/src/views/hedgeBoard/aShare/index.vue` |
| Macro event-probability presentation | `admin-risk/src/views/hedgeBoard/macro/MacroExpectationPanel.vue` |

## Data-quality contract

Every module returns:

- actual upstream source;
- source timestamp when supplied upstream;
- Platform fetch timestamp;
- `loading`, `ready`, `partial`, `no_data`, `stale` or `error` status;
- stale marker and bounded error metadata.

An empty or invalid pull cannot overwrite the last meaningful value. If a refresh fails and a prior meaningful value exists, the API returns the prior value as `stale` and labels it explicitly.

## A-share definitions

### 20-session volatility

Use the newest 21 strictly positive closing prices, calculate 20 log returns, take the sample standard deviation and annualize by `sqrt(252)`. The result is a percentage. Missing observations return unavailable; suspended sessions are not inserted as zero returns.

### Market breadth

- fewer than 600 advancing stocks: `冰点`;
- advance/decline ratio below 0.7: `偏弱`;
- below 1.2: `中性`;
- below 2.5: `偏强`;
- otherwise: `普涨`.

Speculation state uses the upstream `真实涨停` count: 100+ `亢奋`, 60+ `活跃`, 30+ `普通`, otherwise `冰点`.

### Short-term sentiment

- attempts = limit-up pool count + broken-board pool count;
- seal rate = limit-up count / attempts;
- break rate = broken-board count / attempts;
- promotion rate = today two-board-and-above count / yesterday limit-up count;
- zero denominators are unavailable rather than fabricated as zero.

### Shenwan classification

Industry ownership always uses a versioned Shenwan membership mapping. Market values can come from free quote sources, but external vendor board names cannot replace Shenwan L1/L2 classification.

The default L2 table shows only rank, L2, parent L1, return, turnover, total-market turnover share and net inflow when available. Constituent count and threshold counts are not columns in this default table.

The high-turnover work statistic is separate. It uses strict `stock turnover > threshold`, with 50/100/200亿元 and custom thresholds. A value exactly equal to the threshold is excluded.

## One-click stock data

A stock query is fixed code orchestration, not an AI workflow. The Platform Backend reads quote/valuation, consensus, financials, valuation percentiles, reports, announcements, raw stock news, margin, holders, fund flow, dividends, block trades, dragon-tiger data, lockups, investor Q&A and Shenwan classification in parallel.

Each module fails independently. A report-source failure cannot remove the quote or financial modules. The platform does not build a full historical stock warehouse for this feature; it uses bounded cache and last-known-good snapshots.

## Macro probabilities

The macro panel displays selected monetary-policy, macroeconomic, geopolitical and election event probabilities from a public prediction-market source. The backend stores a bounded 90-day probability history for curve display and calculates one-day and seven-day probability-point changes when enough observations exist.

These probabilities are research observations, not forecasts owned by the platform and not trade signals.

## Safety boundary

Research market data must never be used as the authoritative quote, position, order, fill, risk or accounting input for live execution. Any future reuse in execution requires a separate contract, Issue, review and acceptance process.
