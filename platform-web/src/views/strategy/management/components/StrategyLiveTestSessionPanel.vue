<template>
  <section v-if="visible" class="live-test-panel" data-testid="strategy-live-test-session-panel">
    <div class="live-test-panel__header">
      <div>
        <h3>CEO 实盘测试会话</h3>
        <p>复用现有 LiveTradingSession。Cross 会覆盖 Bybit + MT5 两个账户，会话审批不等于武装。</p>
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
      <div class="field">
        <span>Funding Spot / Perp</span>
        <strong>{{ fundingSymbolLabel }}</strong>
      </div>
      <div class="field">
        <span>Cross Bybit Symbol</span>
        <strong>{{ crossBybitSymbolLabel }}</strong>
      </div>
      <div class="field">
        <span>Cross MT5 Broker Symbol</span>
        <strong>{{ crossMt5SymbolLabel }}</strong>
      </div>
    </div>

    <div class="live-test-panel__meta">
      <div
        ><span>Platform Live Write</span><strong>{{ platformWriteLabel }}</strong></div
      >
      <div
        ><span>Runtime Live Write</span><strong>{{ runtimeWriteLabel }}</strong></div
      >
      <div
        ><span>Founder 本地自审批</span><strong>{{ founderDemoApprovalLabel }}</strong></div
      >
      <div><span>当前武装状态</span><strong>未武装</strong></div>
    </div>

    <div class="live-test-panel__cards">
      <article class="status-card">
        <strong>Funding 会话 / readiness</strong>
        <p
          >{{ coverageLabel(fundingState.coverageStatus) }} /
          {{ readyLabel(fundingState.ready) }}</p
        >
        <small>
          缺少会话：{{ missingLabel(fundingState.missingAccounts) }} ｜ 阻断：{{
            blockerLabel(fundingState.blockers)
          }}
        </small>
      </article>
      <article class="status-card">
        <strong>Cross 会话 / readiness</strong>
        <p>{{ coverageLabel(crossState.coverageStatus) }} / {{ readyLabel(crossState.ready) }}</p>
        <small>
          缺少会话：{{ missingLabel(crossState.missingAccounts) }} ｜ 阻断：{{
            blockerLabel(crossState.blockers)
          }}
        </small>
      </article>
      <article class="status-card">
        <strong>未解决 result_unknown</strong>
        <p>{{ unresolvedUnknownCount }}</p>
        <small>来自两策略 executionReadiness 的 resultUnknownOrderCount</small>
      </article>
      <article class="status-card">
        <strong>会话覆盖</strong>
        <p>{{ targetLabels.join(' ｜ ') || '未选择策略' }}</p>
        <small>Funding 单选创建 1 个会话；Cross 单选创建 2 个；同时选择共 3 个</small>
      </article>
    </div>

    <div class="live-test-panel__actions">
      <button type="button" :disabled="busy || !canCreate" @click="createSessions">创建会话</button>
      <button
        type="button"
        :disabled="busy || actionablePending.length === 0 || !canApproveLocally"
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
    <p v-else-if="approvalHint" class="state-text">{{ approvalHint }}</p>

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
  import { getCrossSpreadObservability } from '@/api/platform/crossSpreadObservability';
  import {
    approveLiveTradingSession,
    createLiveTradingSession,
    getLiveTradingSessions,
    getStrategyAccountBindings,
    getTradingSafety,
    revokeLiveTradingSession,
  } from '@/api/platform/trading';
  import type { CrossSpreadObservabilityResult } from '@/api/platform/crossSpreadObservability';
  import type { FundingExecutionContext } from '@/api/platform/fundingWorkspace';
  import type {
    LiveTradingSessionResult,
    StrategyAccountBindingResult,
    StrategyManagementOverviewResult,
    TradingSafetyResult,
  } from '@/api/platform/trading.types';
  import {
    buildLiveTradingSessionPayload,
    deriveLiveTestSessionTargets,
    deriveStrategySessionView,
    findReusableLiveSession,
  } from '../composables/liveTestSessionPanelState';

  const props = defineProps<{
    fundingOverview: StrategyManagementOverviewResult | null;
    crossOverview: StrategyManagementOverviewResult | null;
  }>();

  const userStore = useUserStoreWithOut();
  const busy = ref(false);
  const error = ref<string | null>(null);
  const fundingContext = ref<FundingExecutionContext | null>(null);
  const crossObservability = ref<CrossSpreadObservabilityResult | null>(null);
  const sessions = ref<LiveTradingSessionResult[]>([]);
  const tradingSafety = ref<TradingSafetyResult | null>(null);
  const fundingBindings = ref<StrategyAccountBindingResult[]>([]);
  const crossBindings = ref<StrategyAccountBindingResult[]>([]);
  const selectedFunding = ref(true);
  const selectedCross = ref(true);
  const expiryMinutes = ref('15');
  const maxOrderNotional = ref('100');
  const maxDailyNotional = ref('200');

  const visible = computed(() => {
    const roles = userStore.getRoleList;
    return roles.includes('ceo') || roles.includes('admin');
  });
  const currentUserId = computed(() => String(userStore.getUserInfo?.userId || ''));
  const selectedTargets = computed(() =>
    deriveLiveTestSessionTargets({
      selectedFunding: selectedFunding.value,
      selectedCross: selectedCross.value,
      fundingOverview: props.fundingOverview,
      crossOverview: props.crossOverview,
      fundingBindings: fundingBindings.value,
      crossBindings: crossBindings.value,
      fundingContext: fundingContext.value,
      crossObservability: crossObservability.value,
    }),
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
  const fundingState = computed(() =>
    deriveStrategySessionView({
      strategyLabel: 'Funding',
      overview: props.fundingOverview,
      targets: selectedTargets.value,
      sessions: sessions.value,
      tradingSafety: tradingSafety.value,
      runtimeLiveWriteEnabled: fundingContext.value?.runtime?.liveWriteEnabled === true,
      unresolvedUnknownCount:
        props.fundingOverview?.executionReadiness?.resultUnknownOrderCount || 0,
    }),
  );
  const crossState = computed(() =>
    deriveStrategySessionView({
      strategyLabel: 'Cross',
      overview: props.crossOverview,
      targets: selectedTargets.value,
      sessions: sessions.value,
      tradingSafety: tradingSafety.value,
      runtimeLiveWriteEnabled: fundingContext.value?.runtime?.liveWriteEnabled === true,
      unresolvedUnknownCount: props.crossOverview?.executionReadiness?.resultUnknownOrderCount || 0,
    }),
  );
  const fundingSymbolLabel = computed(() => {
    const target = selectedTargets.value.find((item) => item.targetKey === 'funding:primary');
    return target?.symbolText || target?.missingReason || '未就绪';
  });
  const crossBybitSymbolLabel = computed(() => {
    const target = selectedTargets.value.find((item) => item.targetKey === 'cross:venue_a');
    return target?.symbolText || target?.missingReason || '未就绪';
  });
  const crossMt5SymbolLabel = computed(() => {
    const target = selectedTargets.value.find((item) => item.targetKey === 'cross:mt5_leg');
    return target?.symbolText || target?.missingReason || '未就绪';
  });
  const targetLabels = computed(() =>
    selectedTargets.value.map((item) => {
      const account = item.accountCode || item.accountId || item.role;
      return `${item.strategyLabel}/${item.role}/${account}/${item.symbolText || '未就绪'}`;
    }),
  );
  const platformWriteLabel = computed(() =>
    tradingSafety.value?.liveTradingEnabled === true ? '开启' : '关闭',
  );
  const runtimeWriteLabel = computed(() =>
    fundingContext.value?.runtime?.liveWriteEnabled === true ? '已开启' : '关闭',
  );
  const founderDemoApprovalLabel = computed(() =>
    tradingSafety.value?.founderDemoLocalSelfApprovalEnabled === true ? '允许' : '关闭',
  );
  const canCreate = computed(
    () =>
      selectedTargets.value.length > 0 &&
      selectedTargets.value.every((item) => item.accountId && !item.missingReason),
  );
  const canApproveLocally = computed(() => {
    if (!actionablePending.value.length) return false;
    if (tradingSafety.value?.founderDemoLocalSelfApprovalEnabled === true) return true;
    return actionablePending.value.some((item) => item.applicantUserId !== currentUserId.value);
  });
  const approvalHint = computed(() => {
    if (error.value) return '';
    if (tradingSafety.value?.founderDemoLocalSelfApprovalEnabled === true) {
      return '当前环境允许 founder demo minimum_size_acceptance 本地 CEO 自审批；审批后仍不等于武装。';
    }
    if (actionablePending.value.some((item) => item.applicantUserId === currentUserId.value)) {
      return 'Founder demo 本地自审批默认关闭；当前申请需要独立 approver，页面不会伪造审批成功。';
    }
    return '';
  });

  function strategyLabel(strategyInstanceId: string): string {
    if (strategyInstanceId === props.fundingOverview?.strategyInstanceId) return 'Funding';
    if (strategyInstanceId === props.crossOverview?.strategyInstanceId) return 'Cross';
    return strategyInstanceId;
  }

  function blockerLabel(values: string[] | undefined): string {
    return values && values.length ? values.join('；') : '无阻断';
  }

  function readyLabel(value: boolean): string {
    return value ? 'ready' : 'blocked';
  }

  function coverageLabel(
    value: 'not_created' | 'pending' | 'approved' | 'revoked_or_expired' | 'blocked',
  ): string {
    const labels = {
      not_created: '会话未创建',
      pending: 'pending',
      approved: 'approved',
      revoked_or_expired: 'revoked/expired',
      blocked: 'blocked',
    };
    return labels[value];
  }

  function missingLabel(values: string[]): string {
    return values.length ? values.join('、') : '无';
  }

  async function refresh() {
    if (!visible.value) return;
    error.value = null;
    try {
      const [
        context,
        liveSessions,
        nextTradingSafety,
        nextCrossObservability,
        nextFundingBindings,
        nextCrossBindings,
      ] = await Promise.all([
        getFundingExecutionContext(),
        getLiveTradingSessions(),
        getTradingSafety(),
        getCrossSpreadObservability(1, 1, 'fast'),
        props.fundingOverview?.strategyInstanceId
          ? getStrategyAccountBindings(props.fundingOverview.strategyInstanceId)
          : Promise.resolve([]),
        props.crossOverview?.strategyInstanceId
          ? getStrategyAccountBindings(props.crossOverview.strategyInstanceId)
          : Promise.resolve([]),
      ]);
      fundingContext.value = context;
      sessions.value = liveSessions;
      tradingSafety.value = nextTradingSafety;
      crossObservability.value = nextCrossObservability;
      fundingBindings.value = nextFundingBindings;
      crossBindings.value = nextCrossBindings;
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : '实盘测试会话状态加载失败';
    }
  }

  async function createSessions() {
    if (!canCreate.value) return;
    busy.value = true;
    error.value = null;
    try {
      await refresh();
      const form = {
        expiryMinutes: expiryMinutes.value,
        maxOrderNotional: maxOrderNotional.value,
        maxDailyNotional: maxDailyNotional.value,
      };
      await Promise.all(
        selectedTargets.value.map(async (target) => {
          const existing = findReusableLiveSession(sessions.value, target, form);
          if (existing) return existing;
          return createLiveTradingSession(buildLiveTradingSessionPayload(target, form));
        }),
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
      if (!canApproveLocally.value) {
        throw new Error('当前会话需要独立 approver，或 founder demo 本地自审批未开启');
      }
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
