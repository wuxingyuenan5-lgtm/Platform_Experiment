import { researchRequest } from '@/api/hedgeResearch';

export interface GoldMeta {
  status: string;
  retrievedAt?: string;
}
export interface PositionGroup {
  label: string;
  long: number;
  short: number;
  net: number;
  spreading: number | null;
  weeklyChange?: number | null;
  longChange?: number | null;
  shortChange?: number | null;
  change4w?: number | null;
  change13w?: number | null;
  netShare?: number;
  percentile52?: number | null;
  percentile156?: number | null;
}
export interface PositionRow {
  date: string;
  openInterest: number;
  traders: number | null;
  categories: Record<string, PositionGroup>;
}
export interface GoldPositions extends GoldMeta {
  scopes: Record<string, { latest: PositionRow; history: PositionRow[]; sourceUrl: string }>;
  optionsEquivalent: number | null;
}
export interface GoldReport extends GoldMeta {
  reportDate: string;
  generatedAt: string | null;
  cftcDate: string | null;
  conclusion: {
    directional_bias: string;
    one_sentence: string;
    reason: string;
    market_regime: string;
  };
  keyPoints: string[];
  quality: string;
  keyLevels: { core_low: number; core_high: number; side: string; reason: string }[];
  events: { date: string; event: string; expected_impact: string; source_url: string | null }[];
  sourceUrl: string;
  source: string;
}
export interface AnalystView {
  id: string;
  assetName: string;
  horizonText: string;
  stance: string;
  thesis: string;
  drivers: { text: string; effect: string }[];
  scenarios: {
    id: string;
    label: string;
    conditionText: string | null;
    outcome: string;
    stance: string;
  }[];
  levels: { id: string; expressionRaw: string; confirmationText: string | null }[];
}
export interface AnalystArticle {
  id: number;
  analystId: string;
  title: string;
  headlineChinese: string;
  date: string;
  publishedText: string;
  extractionStatus: string;
  summary: string;
  warnings: string[];
  urlOriginal: string | null;
  views: AnalystView[];
}
export interface AnalystPage extends GoldMeta {
  analysts: { id: string; name: string; nameZh: string; platform: string; styleTags: string[] }[];
  articles: AnalystArticle[];
  total: number;
  page: number;
  pageSize: number;
}
export const goldRequest = <T>(name: string, params?: Record<string, string | number>) =>
  researchRequest<T>({ method: 'GET', url: `/research/commodity/${name}`, params });
export const formatCount = (n: number | null | undefined) =>
  n == null ? '—' : n.toLocaleString('en-US', { maximumFractionDigits: 1 });
export const directionLabel = (value: string) =>
  ({
    bull: '看多',
    bullish: '看多',
    bear: '看空',
    bearish: '看空',
    neutral: '中性',
    conditional: '条件',
    mixed: '分歧',
    unspecified: '未明确',
  }[value] || '其他');
