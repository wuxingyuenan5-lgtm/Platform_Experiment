import { researchRequest } from './hedgeResearch';

export type EtfValue = string | number | null;
export interface EtfRow {
  date: string;
  [key: string]: EtfValue;
}
export interface EtfSource {
  status: string | null;
  fetchedAt: string | null;
  url: string | null;
}
export interface EtfMeta {
  code: string;
  name: string;
  display_group: string;
  dashboard_eligible: boolean;
  latest_report_date: string;
  latest_combined_ratio_pct: EtfValue;
  latest_combined_value_yi: EtfValue;
  signal_source?: string;
}
export interface EtfItem extends EtfMeta {
  latest: EtfRow | null;
  source: EtfSource;
}
export interface EtfCatalog {
  items: EtfItem[];
  source: EtfSource;
}
export interface EtfDetail {
  groupLabel: string;
  members: Array<{ meta: EtfMeta; series: EtfRow[]; margin: EtfRow[] }>;
  meta: EtfMeta;
  series: EtfRow[];
  disclosures: Array<EtfRow & { report_date: string }>;
  margin: EtfRow[];
  groupMargin: EtfRow[];
  group: EtfRow[];
  sources: Record<string, EtfSource>;
}
export const getEtfCatalog = (signal?: AbortSignal) =>
  researchRequest<EtfCatalog>({
    method: 'GET',
    url: '/research/a-share/etf-tracking',
    signal,
  });
export const getEtfDetail = (code: string, signal?: AbortSignal) =>
  researchRequest<EtfDetail>({
    method: 'GET',
    url: `/research/a-share/etf-tracking/${code}`,
    signal,
  });
