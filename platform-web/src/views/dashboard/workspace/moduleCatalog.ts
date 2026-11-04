import { researchModules, type WidgetConfig } from '@/views/hedgeBoard/nativeData/dashboardClean';
import type { SeriesInfo } from '@/api/workspace';

export interface ModuleOption {
  path: string;
  title: string;
  widget?: WidgetConfig;
  series?: SeriesInfo;
  broadView?: 'flow' | 'details' | 'ratio';
  broadIndex?: string;
  permissions: string[];
}
// Each entry renders one chart (possibly with linked panes), never a route page.
const singleChartKeys = new Set<string>([
  'macro-fed-balance-structure',
  'macro-fed-assets',
  'macro-cn-rates',
  'macro-cn-policy-rates',
  'macro-cn-money-stock',
  'macro-cn-reserves',
  'macro-cn-rrr',
  'macro-cn-investment',
  'macro-cn-property',
  'macro-cn-trade',
  'macro-cn-fiscal',
  'macro-cn-profits',
  'macro-cn-labor',
  'macro-cn-youth-labor',
  'macro-cn-price-details',
  'macro-cn-ppi-details',
  'macro-cn-confidence',
  'macro-cn-fx',
  'macro-cn-treasury',
  'macro-cn-growth',
  'macro-cn-pmi',
  'macro-cn-credit',
  'macro-cn-inflation',
  'macro-cn-risk-leverage',
  'macro-cn-risk-volatility',
  'macro-corporate-yields',
  'macro-inflation-nowcast',
  'macro-inflation-expectations',
  'macro-gdp-now',
  'macro-lending-standards',
  'spdr-daily-flow',
  'china-gold-etf-flow',
  'spdr-holdings-vs-price',
  'central-bank-holders',
  'gold-vs-real',
  'macro-treasury-issuance',
  'macro-nfci',
  'macro-vix',
  'macro-nyfed-repo',
  'macro-discount-window',
  'macro-funding-spreads',
  'macro-treasury-spreads',
  'macro-dxy',
  'macro-major-fx',
  'macro-yen-fx',
  'macro-rmb-fx',
  'macro-other-fx',
  'macro-europe-yields',
  'macro-europe-spreads',
  'macro-jp10y',
  'macro-risk-ig-oas',
  'macro-move',
  'macro-vxeem',
  'macro-us-consumption',
  'macro-cn-retail',
  'macro-us-real-retail',
  'macro-us-consumption-momentum',
  'macro-us-employment',
  'macro-us-unemployment',
  'macro-us-profit-expectations',
  'gold-gvz',
  'crypto-strc',
  'crypto-deribit-metrics',
  'crypto-dvol',
  'crypto-eth-reserves',
  'gold-shfe-curve',
  'gold-shfe-iv',
  'gold-borrow-fee',
  'crypto-coinbase-premium',
  'crypto-margin-rate',
  'crypto-address-distribution',
  'crypto-treasuries',
  'crypto-strategy-holdings',
  'gold-comex-inventory',
  'crypto-fear-greed',
  'crypto-funding',
  'macro-treasury-yields',
  'macro-global-m2',
  'macro-global-m2-yoy',
  'macro-us-pmi',
  'macro-growth-production',
  'macro-growth-labor',
  'macro-growth-activity',
  'macro-actual-inflation',
  'macro-upstream-inflation',
  'macro-market-inflation',
  'macro-rate-corridor',
  'macro-risk-hy-oas',
  'macro-real-yield',
  'macro-risk-credit-ratio',
  'cftc-gold-net',
  'cftc-gold-percentile',
  'cftc-silver-net',
  'cftc-silver-percentile',
  'cftc-copper-net',
  'cftc-copper-percentile',
  'cftc-wti-net',
  'cftc-wti-percentile',
  'cftc-natural-gas-net',
  'cftc-natural-gas-percentile',
  'crypto-binance-eth-combined',
  'crypto-binance-open-interest',
  'macro-net-liquidity',
  'btc-etf-flow',
  'crypto-eth-etf-flow',
  'btc-treasury-flow',
  'crypto-coinbase-premium',
]);
export function moduleCatalog(permissions: readonly string[], series: SeriesInfo[] = []) {
  const out: ModuleOption[] = [];
  if (!permissions.includes('research.read') && !permissions.includes('*')) return out;
  for (const module of researchModules) {
    const base = module.id === 'aShare' ? 'a-share' : module.id;
    for (const section of module.sections)
      for (const widget of section.widgets)
        if (
          widget.kind === 'local-chart' &&
          widget.localKey &&
          singleChartKeys.has(widget.localKey)
        )
          out.push({
            path: `/hedge-board/${base}?view=${section.id}&workbenchWidget=${widget.localKey}`,
            title: `${module.label} · ${widget.title}`,
            widget,
            permissions: ['research.read'],
          });
  }
  for (const [key, label] of [
    ['hs300', '沪深300'],
    ['sse50', '上证50'],
    ['csi500', '中证500'],
    ['csi1000', '中证1000'],
    ['chinext', '创业板'],
    ['star50', '科创50'],
  ])
    for (const [view, name] of [
      ['flow', 'ETF净申赎图'],
      ['details', 'ETF资金统计表'],
      ['ratio', '头部ETF市值占比图'],
    ] as const)
      out.push({
        path: `/hedge-board/a-share?view=etf&workbenchWidget=broad-${view}&workbenchIndex=${key}`,
        title: `A股 · ${label} · ${name}`,
        broadView: view,
        broadIndex: key,
        permissions: ['research.read'],
      });
  for (const item of series)
    out.push({
      path: 'series:' + item.id,
      title: `${item.group} · ${item.name}`,
      series: item,
      permissions: ['research.read'],
    });
  return [...new Map(out.map((m) => [m.path, m])).values()];
}
