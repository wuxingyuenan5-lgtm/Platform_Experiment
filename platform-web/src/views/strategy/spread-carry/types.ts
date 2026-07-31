export type SpreadWorkspaceVariant = 'crossVenue' | 'domesticOverseas';

export interface SpreadLegMetric {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface SpreadActionSummary {
  label: string;
  value: string;
  tone?: 'positive' | 'negative' | 'neutral';
}

export interface SpreadActionPreset {
  key: 'open' | 'rollover';
  label: string;
}

export interface SpreadExecutionTab {
  key: string;
  label: string;
}

export interface SpreadExecutionRow {
  [key: string]: string;
}

export interface SpreadExecutionTable {
  columns: Array<{ key: string; label: string }>;
  rows: SpreadExecutionRow[];
}

export interface SpreadExecutionConfig {
  variant: SpreadWorkspaceVariant;
  deskLabel: string;
  eyebrow: string;
  title: string;
  pairLabel: string;
  sceneLabel: string;
  sceneValue: string;
  defaultVenue: string;
  strategyOptions: Array<{ label: string; value: string }>;
  actionPresets: SpreadActionPreset[];
  actionButtons: Array<{ key: string; label: string; tone: 'primary' | 'default' }>;
  metricCards: SpreadActionSummary[];
  leftLegTitle: string;
  rightLegTitle: string;
  leftLegMetrics: SpreadLegMetric[];
  rightLegMetrics: SpreadLegMetric[];
  exposureMetrics: SpreadActionSummary[];
  logs: Array<{ time: string; text: string; tone?: 'positive' | 'negative' | 'neutral' }>;
  tabs: SpreadExecutionTab[];
  tables: Record<string, SpreadExecutionTable>;
}
