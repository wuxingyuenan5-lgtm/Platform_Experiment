export interface MacroExpectationContract {
  status: 'ready' | 'partial' | 'stale' | 'error';
  source: string;
  updatedAt: string;
  events: MacroExpectationContractEvent[];
}

export interface MacroExpectationContractEvent {
  id: string;
  category: 'monetary_policy' | 'macro' | 'geopolitics' | 'election';
  title: string;
  outcome: string;
  probabilityPct: number;
  history: Array<{
    observedAt: string;
    probabilityPct: number;
  }>;
}
