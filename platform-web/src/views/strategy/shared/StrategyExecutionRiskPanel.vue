<template>
  <section class="execution-risk-panel" data-testid="execution-risk-panel">
    <header
      ><h3>策略执行风控</h3
      ><button type="button" :disabled="busy" @click="load">刷新</button></header
    >
    <p v-if="!policy">{{ message || '正在读取风控设置…' }}</p>
    <template v-else>
      <p
        >当前{{ policy.source === 'default' ? '使用系统默认值' : '使用专属配置' }}：腿间最长
        {{ policy.maxLegDelaySeconds }} 秒；余差名义上限 {{ policy.maxResidualNotional }}；{{
          policy.failureAction === 'auto_flatten'
            ? '失败后尝试平掉已确认敞口'
            : '失败后暂停并人工处理'
        }}。</p
      >
      <p
        >策略执行开关：{{
          kill?.enabled ? '已阻断' : '未阻断'
        }}。全局及账户开关仍独立生效。阻断不会自动平仓。</p
      >
      <form v-if="canManage" @submit.prevent="preparePolicy">
        <fieldset :disabled="busy || !!pending">
          <label
            >腿间最长时间（秒）<input
              v-model.number="delay"
              type="number"
              min="1"
              max="3600"
              required
          /></label>
          <label
            >余差名义上限（结算币）<input v-model="limit" inputmode="decimal" required
          /></label>
          <label
            >失败处置<select v-model="action"
              ><option value="hold_and_escalate">暂停并人工处理</option
              ><option value="auto_flatten">尝试自动平掉已确认敞口</option></select
            ></label
          >
          <button type="submit">检查并保存</button>
          <button type="button" @click="prepareKill">{{
            kill?.enabled ? '解除策略阻断' : '阻断策略执行'
          }}</button>
        </fieldset>
      </form>
      <div v-if="pending" role="group" aria-label="确认风控变更">
        <p>{{
          pending.kind === 'policy'
            ? `确认后新批次采用 ${pending.body.maxLegDelaySeconds} 秒、余差上限 ${
                pending.body.maxResidualNotional
              }，失败处置为 ${
                pending.body.failureAction === 'auto_flatten' ? '尝试自动平仓' : '暂停并人工处理'
              }；已有批次保留原参数。`
            : pending.body.enabled
            ? '确认阻断该策略的后续执行？'
            : '确认解除该策略阻断？其余交易准入仍需满足。'
        }}</p>
        <p>未知成交结果保持待核对；资费失败平仓继续原平仓方向，需人工确认补腿。</p>
        <button type="button" :disabled="busy" @click="confirm">{{
          attempted ? '核对并重试原请求' : '确认变更'
        }}</button>
        <button v-if="!attempted" type="button" :disabled="busy" @click="pending = null"
          >取消</button
        >
      </div>
      <p role="status">{{ message }}</p>
    </template>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue';
  import Decimal from 'decimal.js';
  import { useUserStore } from '@/store/modules/user';
  import {
    readExecutionRisk,
    updateExecutionRisk,
    updateStrategyKillSwitch,
    type RiskPolicy,
    type RiskPolicyUpdate,
    type KillSwitch,
    type KillSwitchUpdate,
  } from '@/api/platform/executionRisk';

  const props = defineProps<{ strategyInstanceId: string }>();
  const user = useUserStore();
  const canManage = computed(
    () => user.authentication?.permissions.includes('risk:manage') ?? false,
  );
  const policy = ref<RiskPolicy | null>(null);
  const kill = ref<KillSwitch | null>(null);
  const delay = ref(10);
  const limit = ref('');
  const action = ref<RiskPolicy['failureAction']>('hold_and_escalate');
  const busy = ref(false);
  const message = ref('');
  const attempted = ref(false);
  const pending = ref<
    { kind: 'policy'; body: RiskPolicyUpdate } | { kind: 'kill'; body: KillSwitchUpdate } | null
  >(null);
  watch(
    () => user.authentication?.user.userId,
    () => {
      pending.value = null;
      attempted.value = false;
      policy.value = null;
      kill.value = null;
      message.value = '登录身份已变化，请重新读取风控设置。';
    },
  );
  async function load() {
    if (busy.value) return;
    busy.value = true;
    try {
      const result = await readExecutionRisk(props.strategyInstanceId);
      policy.value = result.policy;
      kill.value = result.kill;
      if (!pending.value) {
        delay.value = result.policy.maxLegDelaySeconds;
        limit.value = String(result.policy.maxResidualNotional);
        action.value = result.policy.failureAction;
      }
      message.value = pending.value ? '待确认请求已保留；重试使用同一请求。' : '';
    } catch {
      message.value = '风控设置读取失败，请刷新核对。';
    } finally {
      busy.value = false;
    }
  }
  function preparePolicy() {
    if (!canManage.value || !policy.value || pending.value) return;
    try {
      if (
        !new Decimal(limit.value).isFinite() ||
        !new Decimal(limit.value).gt(0) ||
        !Number.isInteger(delay.value) ||
        delay.value < 1 ||
        delay.value > 3600
      )
        throw new Error();
    } catch {
      message.value = '请填写正数余差上限，以及 1–3600 的整数秒。';
      return;
    }
    attempted.value = false;
    pending.value = {
      kind: 'policy',
      body: {
        idempotencyKey: crypto.randomUUID(),
        maxLegDelaySeconds: delay.value,
        maxResidualNotional: limit.value,
        failureAction: action.value,
        actor: user.authentication!.user.userId,
      },
    };
  }
  function prepareKill() {
    if (!canManage.value || !kill.value || pending.value) return;
    attempted.value = false;
    pending.value = {
      kind: 'kill',
      body: {
        idempotencyKey: crypto.randomUUID(),
        enabled: !kill.value.enabled,
        actor: user.authentication!.user.userId,
        reason: '策略管理页面确认变更',
      },
    };
  }
  async function confirm() {
    if (!pending.value || busy.value || !canManage.value) return;
    const current = pending.value;
    busy.value = true;
    attempted.value = true;
    try {
      if (current.kind === 'policy')
        policy.value = await updateExecutionRisk(props.strategyInstanceId, current.body);
      else kill.value = await updateStrategyKillSwitch(props.strategyInstanceId, current.body);
      pending.value = null;
      message.value = '已保存，服务端回执已确认。';
    } catch {
      message.value = '回执未确认。请核对当前设置，重试仍使用同一请求。';
    } finally {
      busy.value = false;
    }
  }
  onMounted(load);
</script>

<style scoped>
  .execution-risk-panel {
    padding: 20px;
    border: 1px solid #e2e7ef;
    border-radius: 10px;
    background: #fff;
    color: #26364d;
  }

  header,
  fieldset {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 16px;
  }

  header {
    justify-content: space-between;
  }

  fieldset {
    padding: 0;
    border: 0;
  }

  label {
    display: grid;
    gap: 6px;
  }

  input,
  select,
  button {
    padding: 8px 12px;
    border: 1px solid #bdc9d8;
    border-radius: 6px;
  }

  button {
    margin-right: 8px;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.5;
    cursor: default;
  }

  p {
    margin: 12px 0;
  }
</style>
