import { createStrategyApi, strategyData } from './strategyApi';
import type { components } from './generated/strategy';

const api = createStrategyApi();
export type RiskPolicy = components['schemas']['ExecutionRiskPolicyResponse'];
export type RiskPolicyUpdate = components['schemas']['ExecutionRiskPolicyUpdateRequest'];
export type KillSwitch = components['schemas']['KillSwitchResponse'];
export type KillSwitchUpdate = components['schemas']['KillSwitchUpdateRequest'];

export async function readExecutionRisk(id: string) {
  const [policy, kill] = await Promise.all([
    api
      .GET('/api/v1/strategies/instances/{strategy_instance_id}/execution-risk-policy', {
        params: { path: { strategy_instance_id: id } },
      })
      .then(strategyData),
    api
      .GET('/api/v1/risk/kill-switches/{scope_type}/{scope_id}', {
        params: { path: { scope_type: 'strategy', scope_id: id } },
      })
      .then(strategyData),
  ]);
  return { policy, kill };
}

export async function updateExecutionRisk(id: string, body: RiskPolicyUpdate) {
  return strategyData(
    await api.PUT('/api/v1/strategies/instances/{strategy_instance_id}/execution-risk-policy', {
      params: { path: { strategy_instance_id: id } },
      body,
    }),
  );
}

export async function updateStrategyKillSwitch(id: string, body: KillSwitchUpdate) {
  return strategyData(
    await api.PUT('/api/v1/risk/kill-switches/{scope_type}/{scope_id}', {
      params: { path: { scope_type: 'strategy', scope_id: id } },
      body,
    }),
  );
}
