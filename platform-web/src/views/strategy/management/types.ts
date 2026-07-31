export type StrategyDeskKey =
  | 'funding'
  | 'spread'
  | 'crossSpread'
  | 'domesticOverseas'
  | 'dip'
  | 'shortLineTraderL'
  | 'shortLineTraderW';
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

export interface StrategyCapitalRiskCard {
  label: string;
  value: string;
  note: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyCapitalComparisonCard {
  title: string;
  centerValue: string;
  centerLabel: string;
  leftLabel: string;
  leftValue: string;
  rightLabel: string;
  rightValue: string;
  leftNote?: string;
  rightNote?: string;
  progress: number;
  startColor?: string;
  endColor?: string;
}

export interface StrategyCapitalCurveOption {
  key: string;
  label: string;
}

export interface StrategyCapitalCurveSummary {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyCapitalCurveConfig {
  title: string;
  subtitle: string;
  metricOptions: StrategyCapitalCurveOption[];
  periodOptions: StrategyCapitalCurveOption[];
  modeOptions?: StrategyCapitalCurveOption[];
  defaultMetric: string;
  defaultPeriod: string;
  defaultMode?: string;
  xLabels: string[];
  netValueData: number[];
  drawdownData: number[];
  summaries: StrategyCapitalCurveSummary[];
}

export interface StrategyCapitalRuleMetric {
  label: string;
  value: string;
  note: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyCapitalRuleAlert {
  time: string;
  text: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface StrategyCapitalRulePanel {
  title: string;
  status: string;
  statusNote: string;
  tone?: 'positive' | 'negative' | 'neutral';
  metrics: StrategyCapitalRuleMetric[];
  alerts: StrategyCapitalRuleAlert[];
}

export interface StrategyCapitalRiskOverview {
  title: string;
  rows: Array<{
    product: string;
    type: string;
    level: string;
    factor: string;
    firstValue: string;
    latestValue: string;
    latestTime: string;
    count: string;
    status: string;
    tone?: 'positive' | 'negative' | 'neutral';
  }>;
}

export interface StrategyCapitalProfile {
  overview: StrategyKpiCard[];
  riskCards: StrategyCapitalRiskCard[];
  structureCards: StrategyAccountBreakdown[];
  comparisonCards?: StrategyCapitalComparisonCard[];
  curve: StrategyCapitalCurveConfig;
  metricCurves?: StrategyCurveCard[];
  specialRulePanel?: StrategyCapitalRulePanel;
  riskOverview?: StrategyCapitalRiskOverview;
}
