<template>
  <div class="funding-exit" data-testid="funding-exit-settings">
    <span v-if="plan?.triggeredAt"
      >已触发{{ plan.triggerReason === 'take_profit' ? '止盈' : '止损' }}</span
    >
    <span v-else>{{ plan?.enabled ? '已启用' : '未启用' }}</span>
    <small v-if="plan?.enabled"
      >止盈 ≥ {{ plan.takeProfitSpread ?? '--' }} · 止损 ≤ {{ plan.stopLossSpread ?? '--' }}</small
    >
    <small v-if="plan?.closeInstructionId">平仓指令：{{ plan.closeInstructionId }}</small>
    <small v-if="plan?.lastError" role="status">{{ plan.lastError }}</small>
    <button v-if="canTrade && !plan?.triggeredAt" type="button" @click="openEditor">设置</button>
    <div v-if="editing" class="funding-exit__editor" role="group" aria-label="Funding 自动平仓设置">
      <p
        >平仓价差 = 现货买一 − 永续卖一，单位
        USDT/币。触发后按市价平掉该组全部剩余仓位，最终成交价可能变化。</p
      >
      <label><input v-model="enabled" type="checkbox" />启用价差自动平仓</label>
      <label>止盈价差（≥）<input v-model="takeProfit" type="text" inputmode="decimal" /></label>
      <label>止损价差（≤）<input v-model="stopLoss" type="text" inputmode="decimal" /></label>
      <small
        >至少填写一个阈值；同时填写时，止损须小于止盈。实盘权限关闭或行情不可用时不派单。</small
      >
      <p v-if="confirming">确认保存以上设置？已满足阈值且交易权限开启时可能立即触发平仓。</p>
      <button type="button" :disabled="saving" @click="editing = false">取消</button>
      <button type="button" :disabled="saving" @click="save">{{
        confirming ? '确认保存' : '检查设置'
      }}</button>
    </div>
    <small v-if="message" role="status">{{ message }}</small>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import Decimal from 'decimal.js';
  import { saveFundingExitPlan } from '@/api/platform/fundingWorkspace';
  import type { components } from '@/api/platform/generated/strategy';

  const props = defineProps<{
    openInstructionId: string;
    plan?: components['schemas']['FundingExitPlanResponse'] | null;
    canTrade: boolean;
  }>();
  const emit = defineEmits<{ (event: 'saved'): void }>();
  const editing = ref(false);
  const confirming = ref(false);
  const saving = ref(false);
  const enabled = ref(false);
  const takeProfit = ref('');
  const stopLoss = ref('');
  const revision = ref(0);
  const message = ref('');
  const values = computed(() => [enabled.value, takeProfit.value, stopLoss.value]);
  watch(values, () => {
    confirming.value = false;
  });

  function openEditor() {
    enabled.value = props.plan?.enabled ?? false;
    takeProfit.value = props.plan?.takeProfitSpread ?? '';
    stopLoss.value = props.plan?.stopLossSpread ?? '';
    revision.value = props.plan?.revision ?? 0;
    confirming.value = false;
    message.value = '';
    editing.value = true;
  }

  async function save() {
    if (!props.canTrade || props.plan?.triggeredAt || saving.value) return;
    try {
      const tp = takeProfit.value.trim() ? new Decimal(takeProfit.value.trim()) : null;
      const sl = stopLoss.value.trim() ? new Decimal(stopLoss.value.trim()) : null;
      if ((tp && !tp.isFinite()) || (sl && !sl.isFinite())) throw new Error('请输入有效数值');
      if (enabled.value && !tp && !sl) throw new Error('启用时至少填写一个阈值');
      if (tp && sl && sl.gte(tp)) throw new Error('止损价差须小于止盈价差');
      if (!confirming.value) {
        confirming.value = true;
        message.value = '';
        return;
      }
      saving.value = true;
      await saveFundingExitPlan(props.openInstructionId, {
        expectedRevision: revision.value,
        enabled: enabled.value,
        takeProfitSpread: tp?.toString() ?? null,
        stopLossSpread: sl?.toString() ?? null,
      });
      editing.value = false;
      message.value = '设置已保存';
      emit('saved');
    } catch (error) {
      message.value = error instanceof Error ? error.message : '保存未确认，请刷新核对设置';
      confirming.value = false;
    } finally {
      saving.value = false;
    }
  }
</script>

<style scoped>
  .funding-exit {
    min-width: 160px;
    white-space: normal;
  }

  .funding-exit small {
    display: block;
    margin-top: 4px;
  }

  .funding-exit button {
    margin: 6px 8px 0 0;
    color: #2563eb;
    cursor: pointer;
  }

  .funding-exit__editor {
    min-width: 240px;
    padding: 10px;
    background: #f8fafc;
  }

  .funding-exit__editor label {
    display: block;
    margin: 8px 0;
  }

  .funding-exit__editor input[type='text'] {
    width: 130px;
    margin-left: 6px;
    padding: 3px;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
  }
</style>
