export type FundingExchange = 'Binance' | 'OKX' | 'Bybit';

export type FundingSymbol = 'BTC' | 'ETH' | 'SOL' | 'DOGE' | 'XRP' | 'XAUT';

export type FundingViewMode = 'basis' | 'funding' | 'borrow';

export type FundingMarketRange = 'current' | '1d' | '7d' | '30d' | '1y';

export interface FundingSummaryMetric {
  label: string;
  unit?: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface FundingSymbolSnapshot {
  symbol: FundingSymbol;
  fundingRate: number;
  netCarry: number;
  basisDrag: number;
  borrowCost: number;
  stability: number;
  capacity: number;
}

export interface FundingBreakdownRow {
  label: string;
  value: string;
  note: string;
}

export interface FundingInsightBlock {
  title: string;
  badge: string;
  tone: 'bull' | 'flat' | 'bear';
  description: string;
  meta: string[];
}

export interface FundingAssetResearch {
  symbol: FundingSymbol;
  headline: string;
  note: string;
  executionMemo: string;
  decision: {
    label: string;
    tone: 'bull' | 'flat' | 'bear';
  };
  chips: string[];
  breakdownRows: FundingBreakdownRow[];
  insightBlocks: FundingInsightBlock[];
}

export interface FundingExchangeProfile {
  exchange: FundingExchange;
  updatedAt: string;
  overviewTitle: string;
  overviewDescription: string;
  metrics: FundingSummaryMetric[];
  snapshots: FundingSymbolSnapshot[];
  research: Record<FundingSymbol, FundingAssetResearch>;
}

export interface FundingMarketSummaryCard {
  title: string;
  value: string;
  subtitle: string;
  tone: 'positive' | 'negative';
}

export interface FundingMarketExtremaItem {
  market: string;
  value: number;
}

export interface FundingMarketHeatRow {
  symbol: string;
  usdtPerps: Record<string, number | null>;
  inversePerps: Record<string, number | null>;
}

export interface FundingMarketBoardData {
  updatedAt: string;
  symbolOptions: string[];
  resolutionOptions: string[];
  summaryCards: FundingMarketSummaryCard[];
  highest: FundingMarketExtremaItem[];
  lowest: FundingMarketExtremaItem[];
  usdtExchanges: string[];
  inverseExchanges: string[];
  rows: FundingMarketHeatRow[];
}

export interface FundingChartPoint {
  date: string;
  price: number;
  funding: number;
}

export interface FundingChartPanelData {
  title: string;
  legendPrice: string;
  legendFunding: string;
  points: FundingChartPoint[];
}

export interface FundingOrderMetric {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface FundingOrderPanelData {
  strategyLabel: string;
  nextWindow: string;
  accountMetrics: FundingOrderMetric[];
  executionMetrics: FundingOrderMetric[];
  leftLegTitle: string;
  rightLegTitle: string;
  leftLegMetrics: FundingOrderMetric[];
  rightLegMetrics: FundingOrderMetric[];
  actionButtons: string[];
  impactMetrics: FundingOrderMetric[];
  logs: string[];
}
