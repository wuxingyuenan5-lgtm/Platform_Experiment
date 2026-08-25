<template>
  <section class="panel funding-market-board" data-testid="funding-market-board">
    <div class="panel-title panel-title--between">
      <h3>Funding 实时上下文</h3>
      <button type="button" class="ghost-button" @click="$emit('refresh')">刷新</button>
    </div>

    <p v-if="loading" class="state-text">正在同步 Bybit 实时行情与账户状态。</p>
    <p v-else-if="error" class="state-text state-text--error">{{ error }}</p>
    <p v-else-if="!context" class="state-text">尚无数据</p>

    <template v-else>
      <div class="symbol-grid">
        <button
          v-for="item in context.symbolOptions"
          :key="`${item.perpetualSymbol}:${item.spotSymbol}`"
          type="button"
          class="symbol-chip"
          :class="{ active: item.perpetualSymbol === context.perpetualSymbol }"
          @click="$emit('select-symbol', item.perpetualSymbol, item.spotSymbol)"
        >
          {{ item.baseAsset }}
        </button>
      </div>

      <div class="stats-grid">
        <div
          ><span>Venue</span><strong>{{ context.venue }}</strong></div
        >
        <div
          ><span>共享 UTA</span><strong>{{ context.accountId }}</strong></div
        >
        <div
          ><span>现货</span><strong>{{ context.spotSymbol }}</strong></div
        >
        <div
          ><span>永续</span><strong>{{ context.perpetualSymbol }}</strong></div
        >
        <div
          ><span>现货中间价</span><strong>{{ context.spotQuote?.mid ?? '尚无数据' }}</strong></div
        >
        <div
          ><span>永续中间价</span
          ><strong>{{ context.perpetualQuote?.mid ?? '尚无数据' }}</strong></div
        >
        <div
          ><span>资金费率</span><strong>{{ context.fundingRate ?? '尚无数据' }}</strong></div
        >
        <div
          ><span>下次结算</span><strong>{{ context.nextFundingTime ?? '尚无数据' }}</strong></div
        >
        <div
          ><span>Basis</span><strong>{{ context.basis ?? '尚无数据' }}</strong></div
        >
        <div
          ><span>Funding 可用余额</span
          ><strong>{{ context.activeReservation?.fundingAvailable ?? '尚无数据' }}</strong></div
        >
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    context: Record<string, any> | null;
    loading: boolean;
    error: string | null;
  }>();

  defineEmits<{
    (event: 'refresh'): void;
    (event: 'select-symbol', perpetualSymbol: string, spotSymbol: string): void;
  }>();
</script>

<style scoped lang="less">
  .funding-market-board {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .panel-title--between {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .ghost-button,
  .symbol-chip {
    padding: 8px 12px;
    border: 1px solid rgb(126 150 255 / 20%);
    border-radius: 10px;
    background: rgb(12 18 35 / 82%);
    color: var(--strategy-text-1);
    cursor: pointer;
  }

  .symbol-grid {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }

  .symbol-chip.active {
    border-color: #7e96ff;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 12px;
  }

  .stats-grid div {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    border-radius: 12px;
    background: rgb(12 18 35 / 72%);
  }

  .stats-grid span,
  .state-text {
    color: var(--strategy-text-2);
  }

  .state-text--error {
    color: #ff7875;
  }
</style>
