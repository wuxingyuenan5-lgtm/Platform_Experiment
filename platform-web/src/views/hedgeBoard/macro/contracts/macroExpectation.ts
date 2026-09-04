export interface MacroExpectationContract {
  status: 'ready' | 'no_data' | 'not_configured' | 'stale' | 'error';
  source: string;
  updatedAt: string;
  events: MacroExpectationContractEvent[];
}

export interface MacroExpectationContractEvent {
  id: string;
  label: string;
  category: 'monetary_policy' | 'macro' | 'geopolitics' | 'election';
  probability: number;
  history: Array<{
    observedAt: string;
    probability: number;
  }>;
}
