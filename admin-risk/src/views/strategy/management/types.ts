export type StrategyDeskKey = 'funding' | 'spread' | 'crossSpread' | 'domesticOverseas' | 'dip';
export type StrategyPeriodKey = 'day' | 'week' | 'month' | 'custom';

export interface StrategyKpiCard {
  label: string;
  value: string;
  unit?: string;
  note: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyAccountBreakdown {
  label: string;
  value: string;
  note: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyGaugeMetric {
  label: string;
  value: string;
  subValue: string;
  progress: number;
  leftLabel: string;
  rightLabel: string;
  leftColor: string;
  rightColor: string;
}

export interface StrategyExecutionMetric {
  label: string;
  before: string;
  after: string;
  alert?: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyLogItem {
  time: string;
  text: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyCurvePoint {
  date: string;
  value: number;
}

export interface StrategyCurveCard {
  title: string;
  amount: string;
  unit: string;
  points: StrategyCurvePoint[];
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyTableTab {
  key: string;
  label: string;
}

export interface StrategyTableColumn {
  key: string;
  label: string;
}

export interface StrategyTableRow {
  [key: string]: string;
}

export interface StrategyTableSection {
  columns: StrategyTableColumn[];
  rows: StrategyTableRow[];
}

export interface StrategyOverviewStatCard {
  label: string;
  value: string;
  subValue?: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyOverviewCountCard {
  label: string;
  count: string;
  subLabel: string;
}

export interface StrategyAttributionRow {
  type: string;
  strategyCount: string;
  pnl: string;
  ratio: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategySyncRow {
  category: string;
  status: string;
  message: string;
  time: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyOverviewPeriodData {
  periodLabel: string;
  dateLabel: string;
  totalFund: string;
  xLabels: string[];
  barValues: number[];
  lineValues: number[];
  statCards: StrategyOverviewStatCard[];
  stateCounts: StrategyOverviewCountCard[];
  profitRows: StrategyAttributionRow[];
  lossRows: StrategyAttributionRow[];
  syncRows: StrategySyncRow[];
}

export interface StrategyOverviewConfig {
  periods: readonly { key: StrategyPeriodKey; label: string }[];
  datasets: Record<StrategyPeriodKey, StrategyOverviewPeriodData>;
}

export interface StrategyDetailMetric {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyDetailLegRow {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyDetailLeg {
  title: string;
  market: string;
  symbol: string;
  actions: string[];
  rows: StrategyDetailLegRow[];
}

export interface StrategyDetailSnapshot {
  title: string;
  status: string;
  actions: string[];
  metrics: StrategyDetailMetric[];
  legs: StrategyDetailLeg[];
  exposureRows: StrategyDetailLegRow[];
  tabs: { key: string; label: string }[];
  tabTables: Record<string, StrategyTableSection>;
}

export interface StrategyDeskProfile {
  key: StrategyDeskKey;
  label: string;
  title: string;
  subtitle: string;
  strategyName: string;
  filters: string[];
  overview: StrategyOverviewConfig;
  detail: StrategyDetailSnapshot;
  kpis: StrategyKpiCard[];
  gauges: StrategyGaugeMetric[];
  accountBreakdown: StrategyAccountBreakdown[];
  executionHeader: string;
  executionStatus: string[];
  executionMetrics: StrategyExecutionMetric[];
  logs: StrategyLogItem[];
  curves: StrategyCurveCard[];
  tabs: StrategyTableTab[];
  tables: Record<string, StrategyTableSection>;
}
