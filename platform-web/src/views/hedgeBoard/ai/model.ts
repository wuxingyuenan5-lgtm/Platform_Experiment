export type Amount = string | number | null;
export interface AccountingRow {
  start: string;
  end: string;
  values: Record<string, Amount>;
  balance?: Record<string, Amount>;
  provenance?: Record<
    string,
    { tag: string; filed: string; accn: string; basis: string; baseEnd?: string }
  >;
  ttm?: AccountingRow | null;
  yoy?: Record<string, Amount>;
}
export interface OperatingKpi {
  name: string;
  kind: string;
  unit: string;
  basis: string;
  source: string;
  sourceUrl: string;
  history: { date: string; value: Amount }[];
  latest: { date: string; value: Amount };
}
export interface Disclosure {
  name: string;
  kind: string;
  unit: string;
  value: Amount;
  upper?: Amount;
  date: string;
  qualifier?: string;
  sourceUrl: string;
  source: string;
  basis: string;
  excerpt: string;
}
export interface Company {
  ticker: string;
  name: string;
  sector: string;
  status: string;
  periodEnd?: string;
  sourceUrl?: string;
  filingsUrl?: string;
  generatedAt?: string;
  latest?: AccountingRow;
  quarters?: AccountingRow[];
  annual?: AccountingRow[];
  operatingKpis?: OperatingKpi[];
  disclosures?: Disclosure[];
  crossChecks?: {
    metric: string;
    date: string;
    primary: Amount;
    secondary: Amount;
    differencePct: Amount;
    status: string;
    sourceUrl: string;
  }[];
  sources?: Record<string, { status: string; retrievedAt?: string; sourceUrl: string }>;
}
export interface AiDashboard {
  status: string;
  generatedAt?: string;
  companies: Company[];
  capexHistory: { date: string; [key: string]: Amount }[];
  cds: {
    ticker: string;
    method: string;
    sourceUrl: string;
    upstreamUrl: string;
    latest: { date: string; value: Amount; trades: number };
    history: { date: string; value: Amount; trades: number }[];
    health: { status: string; retrievedAt?: string };
  }[];
  metricDefinitions?: Record<string, string>;
}
export const numeric = (v: unknown): number | null =>
  v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
export const format = (v: unknown, unit = 'USD') => {
  const n = numeric(v);
  if (n == null) return '—';
  if (unit === 'percent') return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) + '%';
  if (unit === 'times') return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) + '×';
  if (unit === 'count') return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  if (unit === 'bp') return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) + ' bp';
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 0 }) + ' USD';
};
export const compact = (v: unknown) => {
  const n = numeric(v);
  return n == null ? '—' : (n / 1e9).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
};
export const label: Record<string, string> = {
  revenue: '营业收入',
  grossProfit: '毛利润',
  operatingIncome: '经营利润',
  netIncome: '净利润',
  cfo: '经营现金流',
  capex: '现金资本开支',
  fcf: '自由现金流',
  rd: '研发费用',
  sbc: '股份薪酬',
  da: '折旧与摊销',
  interest: '利息费用',
  leasePrincipal: '融资租赁本金偿付',
  leaseAdditions: '非现金租赁资产新增',
  debtIssued: '长期债务发行所得',
  grossMargin: '毛利率',
  operatingMargin: '经营利润率',
  fcfMargin: '自由现金流率',
  capexRevenue: 'Capex / 收入',
  capexCfo: 'Capex / 经营现金流',
  sbcRevenue: 'SBC / 收入',
  rdRevenue: '研发 / 收入',
  daRevenue: '折旧摊销 / 收入',
  interestCoverage: '利息覆盖',
  cash: '现金及现金等价物',
  shortInvestments: '短期投资',
  debtCurrent: '一年内到期长期债务',
  debtNoncurrent: '非流动长期债务',
  leaseLiability: '融资租赁负债',
  ppe: '固定资产净额',
  rpo: '剩余履约义务 RPO',
  receivables: '应收账款',
  inventory: '存货',
};
export const percentage = (key: string) =>
  key.includes('Margin') || key.endsWith('Revenue') || key === 'capexCfo';
