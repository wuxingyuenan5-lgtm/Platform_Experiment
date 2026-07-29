# Hedge Research Dashboard UI Standard

Status: active for Platform 0.9.1 research pages.

## Scope

This standard applies to the hedge-fund dashboard research surfaces. It preserves the existing platform visual language and does not define trading, execution or account-operation controls.

## Page orchestration

- The page component owns section order and page-level navigation only.
- A natural research boundary is implemented as a child component.
- API state and request sequencing belong in a composable.
- Third-party fields are normalized by Platform Backend before they reach Vue.
- A single provider failure must not blank the whole page.

## Information hierarchy

Each research section uses:

1. an English eyebrow for scanning;
2. one Chinese business title;
3. a compact source/status line;
4. the primary table, chart or metric content;
5. details behind an explicit expand interaction.

Engineering explanations, adapter names and validation notes must not become primary product copy. The source line shows the actual upstream source and current data state.

## Tables

- Name and code columns are left aligned.
- Numeric values are right aligned where comparison benefits from alignment.
- Percentages use fixed decimal precision and red-up/green-down semantics.
- Missing data is `—`; missing values are never coerced to zero.
- Amounts use `万`, `亿` and `万亿` display units while the API keeps yuan values.
- Wide research tables scroll within their own bounded container.
- The A-share market-detail table has no 4H column.

## A-share section order

1. 大盘表现
2. 大盘广度
3. 市场明细
4. 申万板块
5. 短线情绪
6. 自选股
7. 一键个股数据

The default Shenwan L2 view shows turnover Top 10. High-turnover stock counts are a separate work-statistics panel and are not extra columns in the default ranking.

## One-click stock data

- The query header remains visible.
- All objective-data modules start collapsed after every new stock query.
- Each module shows its own source and status.
- Expand-all and collapse-all are secondary controls.
- A failed module remains visible as unavailable while successful modules continue to render.
- No AI action is part of this workspace.

## Macro probabilities

- Probability history curves are primary.
- Current probability, one-day change, seven-day change, liquidity and expiry are supporting metadata.
- Event-source links remain secondary.
- The panel does not produce platform forecasts, trading signals or recommendations.

## Responsive behavior

- Desktop research density is preserved above 1150px.
- Metric and event grids reduce columns before content becomes compressed.
- Tables keep their semantic columns and use contained horizontal scrolling.
- Headers stack vertically on compact screens.
- Sticky section navigation remains horizontally scrollable and must not create page-level overflow.
