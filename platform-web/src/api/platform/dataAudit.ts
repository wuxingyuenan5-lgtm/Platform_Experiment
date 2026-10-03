import { createStrategyClient } from './strategyClient';

export interface DataCheck {
  key: string;
  name: string;
  group: string;
  status: 'healthy' | 'warning' | 'error' | 'info';
  message: string;
  checkedAt: string;
  evidence: Record<string, unknown>;
}
export interface DataAuditReport {
  checkedAt: string | null;
  monitorStale: boolean;
  summary: Record<string, number>;
  checks: DataCheck[];
  alerts: {
    id: string;
    message: string;
    status: string;
    severity: string;
    first_seen_at: string;
    last_seen_at: string;
    occurrence_count: number;
  }[];
}
const client = createStrategyClient();
export async function getDataAudit(): Promise<DataAuditReport> {
  return (await client.get('/risk/data-audit')).data;
}
