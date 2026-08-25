<template>
  <section v-if="visible" class="live-test-panel" data-testid="strategy-live-test-session-panel">
    <div class="live-test-panel__header">
      <div>
        <h3>CEO 实盘测试会话</h3>
        <p>复用现有 LiveTradingSession。可同时覆盖 Funding 与 Cross，共享 bybit-live-main。</p>
      </div>
      <button type="button" class="state-refresh-btn" @click="refresh">刷新状态</button>
    </div>

    <div class="live-test-panel__grid">
      <label class="field-check">
        <input v-model="selectedFunding" type="checkbox" />
        <span>Funding</span>
      </label>
      <label class="field-check">
        <input v-model="selectedCross" type="checkbox" />
        <span>Cross</span>
      </label>
      <label class="field">
        <span>会话有效期（分钟）</span>
        <input v-model="expiryMinutes" type="number" min="1" step="1" />
      </label>
      <label class="field">
        <span>单笔上限</span>
        <input v-model="maxOrderNotional" type="text" />
      </label>
      <label class="field">
        <span>累计上限</span>
        <input v-model="maxDailyNotional" type="text" />
      </label>
      <label class="field">
        <span>Symbol allowlist</span>
        <input v-model="symbolsCsv" type="text" placeholder="BTCUSDT,ETHUSDT" />
      </label>
    </div>

    <div class="live-test-panel__meta">
      <div
        ><span>共享 Bybit 账户</span
        ><strong>{{ fundingContext?.accountId || '未就绪' }}</strong></div
      >
      <div
        ><span>Cross MT5 腿</span
        ><strong>{{ crossOverview?.primaryAccountCode || '--' }}</strong></div
      >
      <div
        ><span>Runtime Live Write</span><strong>{{ runtimeWriteLabel }}</strong></div
      >
      <div><span>默认武装状态</span><strong>未武装</strong></div>
    </div>

    <div class="live-test-panel__cards">
      <article class="status-card">
        <strong>Funding readiness</strong>
        <p>{{ readinessLabel(fundingOverview?.executionReadiness?.runnable) }}</p>
        <small>{{ blockerLabel(fundingOverview?.executionReadiness?.blockers) }}</small>
      </article>
      <article class="status-card">
        <strong>Cross readiness</strong>
        <p>{{ readinessLabel(crossOverview?.executionReadiness?.runnable) }}</p>
        <small>{{ blockerLabel(crossOverview?.executionReadiness?.blockers) }}</small>
      </article>
      <article class="status-card">
        <strong>未解决 result_unknown</strong>
        <p>{{ unresolvedUnknownCount }}</p>
        <small>来自两策略 executionReadiness 的 resultUnknownOrderCount</small>
      </article>
      <article class="status-card">
        <strong>Kill Switch / 账户门控</strong>
        <p>{{ blockerLabel(killSwitchSignals) }}</p>
        <small>状态来自现有 readiness blockers；本面板不绕过任何门控</small>
      </article>
    </div>

    <div class="live-test-panel__actions">
      <button type="button" :disabled="busy || !canCreate" @click="createSessions">创建会话</button>
      <button
        type="button"
        :disabled="busy || actionablePending.length === 0"
        @click="approveSessions"
      >
        审批并准备武装
      </button>
      <button
        type="button"
        :disabled="busy || actionableSessions.length === 0"
        @click="revokeSessions"
      >
        撤销会话
      </button>
    </div>

    <p v-if="error" class="state-text state-text--error">{{ error }}</p>

    <ul class="session-list">
      <li v-for="item in actionableSessions" :key="item.sessionId">
        <strong>{{ strategyLabel(item.strategyInstanceId) }}</strong>
        <span>{{ item.status }}</span>
        <span>{{ item.accountId }}</span>
        <span>{{ item.symbols.join(', ') }}</span>
        <span>{{ item.startsAt }} → {{ item.endsAt }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { message } from 'ant-design-vue';
  import { useUserStoreWithOut } from '@/store/modules/user';
  import { getFundingExecutionContext } from '@/api/platform/fundingWorkspace';
  import {
    approveLiveTradingSession,
    createLiveTradingSession,
    getLiveTradingSessions,
    revokeLiveTradingSession,
  } from '@/api/platform/trading';
  import type {
    LiveTradingSessionResult,
    StrategyManagementOverviewResult,
  } from '@/api/platform/trading.types';

  const props = defineProps<{
    fundingOverview: StrategyManagementOverviewResult | null;
    crossOverview: StrategyManagementOverviewResult | null;
  }>();

  const userStore = useUserStoreWithOut();
  const busy = ref(false);
  const error = ref<string | null>(null);
  const fundingContext = ref<Record<string, any> | null>(null);
  const sessions = ref<LiveTradingSessionResult[]>([]);
  const selectedFunding = ref(true);
  const selectedCross = ref(true);
  const expiryMinutes = ref('15');
  const maxOrderNotional = ref('100');
  const maxDailyNotional = ref('200');
  const symbolsCsv = ref('BTCUSDT');

  const visible = computed(() => {
    const roles = userStore.getRoleList;
    return roles.includes('ceo') || roles.includes('admin');
  });
  const selectedStrategies = computed(() =>
    [
      selectedFunding.value ? props.fundingOverview?.strategyInstanceId : null,
      selectedCross.value ? props.crossOverview?.strategyInstanceId : null,
    ].filter((value): value is string => Boolean(value)),
  );
  const actionableSessions = computed(() =>
    sessions.value.filter((item) =>
      [props.fundingOverview?.strategyInstanceId, props.crossOverview?.strategyInstanceId].includes(
        item.strategyInstanceId,
      ),
    ),
  );
  const actionablePending = computed(() =>
    actionableSessions.value.filter((item) => item.status === 'pending'),
  );
  const unresolvedUnknownCount = computed(
    () =>
      (props.fundingOverview?.executionReadiness?.resultUnknownOrderCount || 0) +
      (props.crossOverview?.executionReadiness?.resultUnknownOrderCount || 0),
  );
  const killSwitchSignals = computed(() => [
    ...(props.fundingOverview?.executionReadiness?.blockers || []),
    ...(props.crossOverview?.executionReadiness?.blockers || []),
  ]);
  const runtimeWriteLabel = computed(() =>
    fundingContext.value?.runtime?.liveWriteEnabled === true ? '已开启' : '关闭',
  );
  const canCreate = computed(
    () => selectedStrategies.value.length > 0 && Boolean(fundingContext.value?.accountId),
  );

  function strategyLabel(strategyInstanceId: string): string {
    if (strategyInstanceId === props.fundingOverview?.strategyInstanceId) return 'Funding';
    if (strategyInstanceId === props.crossOverview?.strategyInstanceId) return 'Cross';
    return strategyInstanceId;
  }

  function blockerLabel(values: string[] | undefined): string {
    return values && values.length ? values.join('；') : '无阻断';
  }

  function readinessLabel(value: boolean | undefined): string {
    return value ? 'ready' : 'blocked';
  }

  function sessionPayload(strategyInstanceId: string) {
    const now = new Date();
    const startsAt = new Date(now.getTime() + 60_000);
    const endsAt = new Date(startsAt.getTime() + Number(expiryMinutes.value || '15') * 60_000);
    const readOnlyVerifiedAt = new Date(now.getTime() - 5 * 60_000);
    const symbols = symbolsCsv.value
      .split(',')
      .map((item) => item.trim().toUpperCase())
      .filter(Boolean);
    const keySuffix =
      strategyInstanceId === props.fundingOverview?.strategyInstanceId ? 'funding' : 'cross';
    return {
      idempotencyKey: `live-session:${keySuffix}:${startsAt.toISOString()}`,
      sessionType: 'minimum_size_acceptance' as const,
      strategyInstanceId,
      accountId: String(fundingContext.value?.accountId || ''),
      symbols,
      sides: ['buy', 'sell'] as Array<'buy' | 'sell'>,
      orderTypes: ['market', 'limit'] as Array<'market' | 'limit'>,
      startsAt: startsAt.toISOString(),
      endsAt: endsAt.toISOString(),
      maxOrderNotional: maxOrderNotional.value,
      maxDailyNotional: maxDailyNotional.value,
      readOnlyVerifiedAt: readOnlyVerifiedAt.toISOString(),
      evidenceReference: 'ui://strategy-management/live-test-session',
      reason: 'CEO controlled-live test session',
    };
  }

  async function refresh() {
    if (!visible.value) return;
    error.value = null;
    try {
      const [context, liveSessions] = await Promise.all([
        getFundingExecutionContext(),
        getLiveTradingSessions(),
      ]);
      fundingContext.value = context;
      sessions.value = liveSessions;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '实盘测试会话状态加载失败';
    }
  }

  async function createSessions() {
    if (!canCreate.value) return;
    busy.value = true;
    error.value = null;
    try {
      await Promise.all(
        selectedStrategies.value.map((strategyInstanceId) =>
          createLiveTradingSession(sessionPayload(strategyInstanceId)),
        ),
      );
      await refresh();
      message.success('测试会话已创建');
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '测试会话创建失败';
    } finally {
      busy.value = false;
    }
  }

  async function approveSessions() {
    busy.value = true;
    error.value = null;
    try {
      await Promise.all(
        actionablePending.value.map((item) =>
          approveLiveTradingSession(
            item.sessionId,
            'CEO test window approved from strategy management',
          ),
        ),
      );
      await refresh();
      message.success('测试会话已审批');
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '测试会话审批失败';
    } finally {
      busy.value = false;
    }
  }

  async function revokeSessions() {
    busy.value = true;
    error.value = null;
    try {
      await Promise.all(
        actionableSessions.value
          .filter((item) => item.status === 'approved' || item.status === 'pending')
          .map((item) =>
            revokeLiveTradingSession(item.sessionId, 'CEO revoked strategy-management test window'),
          ),
      );
      await refresh();
      message.success('测试会话已撤销');
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '测试会话撤销失败';
    } finally {
      busy.value = false;
    }
  }

  onMounted(() => {
    void refresh();
  });
</script>

<style scoped lang="less">
  .live-test-panel {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .live-test-panel__header,
  .live-test-panel__actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .live-test-panel__header h3,
  .live-test-panel__header p {
    margin: 0;
  }

  .live-test-panel__header p,
  .state-text,
  .session-list {
    color: var(--strategy-text-2);
  }

  .live-test-panel__grid,
  .live-test-panel__meta,
  .live-test-panel__cards {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .field,
  .field-check,
  .live-test-panel__meta > div,
  .status-card {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    border-radius: 12px;
    background: rgb(12 18 35 / 72%);
  }

  .field input {
    min-height: 34px;
    padding: 0 10px;
    border: 1px solid rgb(126 150 255 / 20%);
    border-radius: 8px;
    background: rgb(12 18 35 / 82%);
    color: var(--strategy-text-1);
  }

  .field-check {
    justify-content: center;
  }

  .field-check input {
    margin-right: 8px;
  }

  .session-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 0;
    padding-left: 18px;
  }

  .state-text--error {
    color: #ff7875;
  }
</style>
