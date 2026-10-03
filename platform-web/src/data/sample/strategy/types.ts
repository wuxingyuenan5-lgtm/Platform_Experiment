export type StrategyDeskKey =
  | 'funding'
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
  description?: string;
  emptyMessage?: string;
  details?: Record<
    string,
    {
      fields: Array<{ label: string; value: string }>;
      sections?: Array<{ title: string; columns: StrategyTableColumn[]; rows: StrategyTableRow[] }>;
    }
  >;
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
  metricSeries?: Record<
    string,
    {
      title: string;
      timestamps?: string[];
      xLabels: string[];
      netValueData: number[];
      drawdownData: (number | null)[];
      summaries: StrategyCapitalCurveSummary[];
    }
  >;
  title: string;
  subtitle: string;
  metricOptions: StrategyCapitalCurveOption[];
  periodOptions: StrategyCapitalCurveOption[];
  modeOptions?: StrategyCapitalCurveOption[];
  modeMetricKeys?: string[];
  defaultMetric: string;
  defaultPeriod: string;
  defaultMode?: string;
  timestamps?: string[];
  xLabels: string[];
  netValueData: number[];
  drawdownData: (number | null)[];
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

export interface StrategyPositionSlice {
  label: string;
  /** 多空方向，用于区分对冲双腿 */
  side: 'long' | 'short';
  /** 该标的净数量的绝对值，用于计算占比 */
  value: number;
  amount: string;
  notionalAmount?: string;
  share: string;
  currency: string;
  unit?: string;
  tone: 'positive' | 'negative' | 'neutral';
}

export interface StrategyPositionGroup {
  currency: string;
  gross: string;
  legs: StrategyPositionSlice[];
}

export interface StrategyPositionDistribution {
  title: string;
  /** 统一计价币种；多币种并存时为空，各币种按原币分组分别计算占比 */
  currency: string;
  mixedCurrency: boolean;
  grossLabel: string;
  gross: string;
  netLabel: string;
  net: string;
  /** 按原币分组的腿，用于逐币种绘制环形 */
  groups: StrategyPositionGroup[];
  slices: StrategyPositionSlice[];
  emptyMessage: string;
}

/**
 * 逐日盈亏读数，与后端 `dailyPnl` 一一对应。
 *
 * 后端已剔除出入金并给出当日口径的收益率，前端只做区间（月/年）聚合，
 * 不重建口径、不补零：`pnl` 为 null 表示该日不可估值，`quality` 说明原因。
 */
export interface StrategyPnlDayPoint {
  date: string;
  pnl: number | null;
  rate: number | null;
  quality: string;
}

/** 盈亏日历的取数周期：按日（可翻月）或按月（可翻年）。 */
export type StrategyPnlCalendarMode = 'daily' | 'monthly';
/** 日历格无法给出盈亏时的原因，用于悬浮说明而不是补零。 */
export type StrategyPnlCalendarTone = 'positive' | 'negative' | 'neutral' | 'unavailable';

export interface StrategyPnlCalendarCell {
  key: string;
  /** 日视图为日号，月视图为月份标签 */
  label: string;
  amount: string;
  rateText: string;
  tone: StrategyPnlCalendarTone;
  title: string;
}

export interface StrategyPnlCalendar {
  mode: StrategyPnlCalendarMode;
  title: string;
  currency: string;
  cursorLabel: string;
  summaryLabel: string;
  summaryAmount: string;
  summaryRateText: string;
  summaryTone: StrategyPnlCalendarTone;
  note: string;
  weekdayLabels: string[];
  /** 固定 7 列的网格；日视图补足前后空位，月视图为 12 个月 */
  cells: StrategyPnlCalendarCell[];
  isMonthly: boolean;
}
