<template>
  <section class="panel funding-order-panel" data-testid="funding-order-panel">
    <div class="panel-title panel-title--between">
      <h3>Funding 执行工作台</h3>
      <button type="button" class="ghost-button" @click="$emit('refresh')">刷新</button>
    </div>

    <div v-if="context" class="form-grid">
      <label class="field">
        <span>标的</span>
        <select
          :value="context.perpetualSymbol"
          @change="handleSymbolChange(($event.target as HTMLSelectElement).value)"
        >
          <option
            v-for="item in context.symbolOptions"
            :key="item.perpetualSymbol"
            :value="item.perpetualSymbol"
          >
            {{ item.baseAsset }} · {{ item.perpetualSymbol }}
          </option>
        </select>
      </label>

      <label class="field">
        <span>名义金额</span>
        <input
          :value="notionalInput"
          type="text"
          @input="$emit('update:notional-input', ($event.target as HTMLInputElement).value)"
        />
      </label>

      <label class="field">
        <span>后端数量</span>
        <input :value="quantityInput" type="text" readonly />
      </label>
    </div>

    <div v-if="context" class="preview-grid">
      <div
        ><span>现货腿</span><strong>buy {{ context.spotSymbol }}</strong></div
      >
      <div
        ><span>永续腿</span><strong>sell {{ context.perpetualSymbol }}</strong></div
      >
      <div
        ><span>建议数量</span><strong>{{ context.suggestedQuantity ?? '尚无数据' }}</strong></div
      >
      <div
        ><span>预计资金占用</span
        ><strong>{{ context.requestedNotional ?? notionalInput }}</strong></div
      >
    </div>

    <div class="positions-block">
      <strong>真实 Funding 活动组合</strong>
      <ul v-if="activeGroups.length" class="group-selector">
        <li v-for="item in activeGroups" :key="item.instructionId">
          <label class="group-option">
            <input
              type="radio"
              name="funding-close-group"
              :disabled="item.lifecycleState !== 'active'"
              :checked="selectedCloseInstructionId === item.instructionId"
              @change="$emit('select-close-instruction', item.instructionId)"
            />
            <div class="group-metrics">
              <span>
                {{ item.perpetualSymbol }} / {{ item.spotSymbol }} ·
                {{ formatState(item.status) }} ·
                {{ item.lifecycleState === 'history' ? '历史' : '活动' }}
              </span>
              <small>
                已对冲 {{ item.hedgedQuantity ?? '0' }} / 权威已平
                {{ item.authoritativeClosedQuantity ?? item.alreadyClosedQuantity ?? '0' }} /
                待平预约 {{ item.pendingCloseQuantity ?? '0' }} / 结果未知预约
                {{ item.resultUnknownReservedQuantity ?? '0' }} / 剩余可平
                {{ item.remainingClosableQuantity ?? '0' }}
              </small>
            </div>
          </label>
        </li>
      </ul>
      <p v-else class="state-text">暂无活动 Funding 组合。</p>
      <div v-if="historyGroups.length" class="history-block">
        <strong>已完成历史组合</strong>
        <ul class="group-selector">
          <li v-for="item in historyGroups" :key="item.instructionId">
            <div class="group-option group-option--history">
              <div class="group-metrics">
                <span>{{ item.perpetualSymbol }} / {{ item.spotSymbol }} · 已完全平仓</span>
                <small>
                  已对冲 {{ item.hedgedQuantity ?? '0' }} / 权威已平
                  {{ item.authoritativeClosedQuantity ?? item.alreadyClosedQuantity ?? '0' }}
                </small>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <div class="action-row">
      <button type="button" :disabled="!canSubmit" @click="$emit('submit-open')"
        >创建开仓指令</button
      >
      <button
        type="button"
        :disabled="!canSubmit || !selectedCloseInstructionId"
        @click="$emit('submit-close')"
      >
        创建平仓指令
      </button>
    </div>

    <div class="status-stack">
      <p v-if="error" class="state-text state-text--error">{{ error }}</p>
      <p v-if="pendingDraft" class="state-text">
        待恢复指令：{{ pendingDraft.idempotencyKey }} · {{ formatState(pendingDraft.state) }}
      </p>
      <p class="state-text">当前状态：{{ formatState(workspaceState) }}</p>
      <p class="state-text">
        controlled-live：{{
          context?.controlledLiveReadiness?.ready === true ? '已就绪' : '未就绪'
        }}
      </p>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  const props = defineProps<{
    context: Record<string, any> | null;
    positionGroups: Array<Record<string, any>>;
    pendingDraft: Record<string, any> | null;
    workspaceState: string;
    submitting: boolean;
    error: string | null;
    quantityInput: string;
    notionalInput: string;
    selectedCloseInstructionId: string;
    selectedCloseGroup: Record<string, any> | null;
    canSubmit: boolean;
  }>();

  const activeGroups = computed(() =>
    props.positionGroups.filter((item: Record<string, any>) => item.lifecycleState !== 'history'),
  );
  const historyGroups = computed(() =>
    props.positionGroups.filter((item: Record<string, any>) => item.lifecycleState === 'history'),
  );

  const emit = defineEmits<{
    (event: 'update:notional-input', value: string): void;
    (event: 'update:quantity-input', value: string): void;
    (event: 'submit-open'): void;
    (event: 'submit-close'): void;
    (event: 'refresh'): void;
    (event: 'select-symbol', perpetualSymbol: string, spotSymbol: string): void;
    (event: 'select-close-instruction', instructionId: string): void;
  }>();

  function handleSymbolChange(perpetualSymbol: string) {
    const option = props.context?.symbolOptions?.find(
      (item: Record<string, any>) => item.perpetualSymbol === perpetualSymbol,
    );
    if (option) {
      emit('select-symbol', option.perpetualSymbol, option.spotSymbol);
    }
  }

  function formatState(state: string | null | undefined) {
    switch (state) {
      case 'submitting':
        return '提交中';
      case 'accepted':
        return '已受理';
      case 'executing':
        return '执行中';
      case 'partially_hedged':
        return '部分对冲';
      case 'reconciling':
        return '对账中';
      case 'completed':
        return '已完成';
      case 'failed':
        return '已失败';
      case 'result_unknown':
        return '结果未知';
      case 'manual_intervention':
        return '人工处理';
      default:
        return state || '尚未开始';
    }
  }
</script>

<style scoped lang="less">
  .funding-order-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .panel-title--between,
  .action-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .form-grid,
  .preview-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .field,
  .preview-grid div,
  .positions-block {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    border-radius: 12px;
    background: rgb(12 18 35 / 72%);
  }

  .group-selector {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
  }

  .group-option {
    display: flex;
    gap: 8px;
    align-items: flex-start;
  }

  .group-option--history {
    cursor: default;
  }

  .group-metrics {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .group-metrics small {
    color: var(--strategy-text-2);
  }

  .history-block {
    margin-top: 12px;
  }

  .ghost-button,
  .action-row button {
    padding: 8px 12px;
    border: 1px solid rgb(126 150 255 / 20%);
    border-radius: 10px;
    background: rgb(12 18 35 / 82%);
    color: var(--strategy-text-1);
    cursor: pointer;
  }

  .action-row button[disabled] {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .status-stack {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .state-text {
    color: var(--strategy-text-2);
  }

  .state-text--error {
    color: #ff7875;
  }
</style>
