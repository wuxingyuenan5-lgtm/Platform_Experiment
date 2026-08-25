<template>
  <section class="panel funding-order-panel" data-testid="funding-order-panel">
    <div class="panel-title panel-title--between">
      <h3>Funding 真实执行</h3>
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
        <span>后端 Decimal 数量</span>
        <input
          :value="quantityInput"
          type="text"
          @input="$emit('update:quantity-input', ($event.target as HTMLInputElement).value)"
        />
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

    <div class="action-row">
      <button type="button" :disabled="!canSubmit" @click="$emit('submit-open')"
        >创建开仓指令</button
      >
      <button
        type="button"
        :disabled="!canSubmit || !positionGroups.length"
        @click="$emit('submit-close')"
      >
        创建平仓指令
      </button>
    </div>

    <div class="status-stack">
      <p v-if="error" class="state-text state-text--error">{{ error }}</p>
      <p v-if="pendingDraft" class="state-text">
        draft {{ pendingDraft.idempotencyKey }} · {{ pendingDraft.state }}
      </p>
      <p class="state-text">workspaceState: {{ workspaceState }}</p>
      <p class="state-text">submitting: {{ submitting ? 'true' : 'false' }}</p>
      <p class="state-text">
        readiness: {{ context?.controlledLiveReadiness?.ready === true ? 'ready' : 'blocked' }}
      </p>
    </div>

    <div class="positions-block">
      <strong>真实 Funding 组合</strong>
      <ul v-if="positionGroups.length">
        <li v-for="item in positionGroups" :key="item.instructionId">
          {{ item.perpetualSymbol }} / {{ item.spotSymbol }} · {{ item.status }} · hedge
          {{ item.hedgedQuantity }}
        </li>
      </ul>
      <p v-else class="state-text">暂无真实 Funding 组合。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
  const props = defineProps<{
    context: Record<string, any> | null;
    positionGroups: Array<Record<string, any>>;
    pendingDraft: Record<string, any> | null;
    workspaceState: string;
    submitting: boolean;
    error: string | null;
    quantityInput: string;
    notionalInput: string;
    canSubmit: boolean;
  }>();

  const emit = defineEmits<{
    (event: 'update:notional-input', value: string): void;
    (event: 'update:quantity-input', value: string): void;
    (event: 'submit-open'): void;
    (event: 'submit-close'): void;
    (event: 'refresh'): void;
    (event: 'select-symbol', perpetualSymbol: string, spotSymbol: string): void;
  }>();

  function handleSymbolChange(perpetualSymbol: string) {
    const option = props.context?.symbolOptions?.find(
      (item: Record<string, any>) => item.perpetualSymbol === perpetualSymbol,
    );
    if (option) {
      emit('select-symbol', option.perpetualSymbol, option.spotSymbol);
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
