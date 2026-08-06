<template>
  <section class="funding-market-board" data-testid="funding-market-board">
    <header>
      <div><span>市场板</span><h2>交易所资金费率比较</h2></div>
      <div class="filters">
        <select :value="selectedSymbol" @change="emitValue('update:selectedSymbol', $event)">
          <option v-for="symbol in ['BTC', 'ETH', 'SOL']" :key="symbol" :value="symbol">{{
            symbol
          }}</option>
        </select>
        <select :value="selectedRange" @change="emitValue('update:selectedRange', $event)">
          <option v-for="item in rangeOptions" :key="item.value" :value="item.value">{{
            item.label
          }}</option>
        </select>
        <select
          :value="selectedResolution"
          @change="emitValue('update:selectedResolution', $event)"
        >
          <option v-for="item in ['5分钟', '30分钟', '4小时']" :key="item">{{ item }}</option>
        </select>
      </div>
    </header>

    <div class="table-wrap">
      <table>
        <thead
          ><tr><th>交易所</th><th>币种</th><th>资金费率</th><th>基差</th><th>流动性</th></tr></thead
        >
        <tbody>
          <tr v-for="row in filteredRows" :key="`${row.exchange}-${row.symbol}`">
            <td>{{ row.exchange }}</td
            ><td>{{ row.symbol }}</td
            ><td>{{ row.rate }}</td
            ><td>{{ row.basis }}</td
            ><td>{{ row.liquidity }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { FundingRange } from '@/data/sample/funding';

  const props = defineProps<{
    rows: Array<{
      exchange: string;
      symbol: string;
      rate: string;
      basis: string;
      liquidity: string;
    }>;
    selectedRange: FundingRange;
    selectedSymbol: string;
    selectedResolution: string;
    rangeOptions: Array<{ value: FundingRange; label: string }>;
  }>();

  const emit = defineEmits<{
    (event: 'update:selectedRange', value: FundingRange): void;
    (event: 'update:selectedSymbol', value: string): void;
    (event: 'update:selectedResolution', value: string): void;
  }>();

  const filteredRows = computed(() =>
    props.rows.filter((row) => row.symbol === props.selectedSymbol),
  );

  function emitValue(event: string, domEvent: Event) {
    const value = (domEvent.target as HTMLSelectElement).value;
    if (event === 'update:selectedRange') emit(event, value as FundingRange);
    else if (event === 'update:selectedSymbol') emit(event, value);
    else emit('update:selectedResolution', value);
  }
</script>

<style scoped lang="less">
  .funding-market-board {
    display: grid;
    gap: 14px;
    padding: 18px;
    border: 1px solid #e1e7ef;
    border-radius: 14px;
    background: #fff;
  }
  header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
    align-items: flex-end;
  }
  header span {
    color: #718095;
    font-size: 11px;
  }
  h2 {
    margin: 4px 0 0;
    font-size: 18px;
  }
  .filters {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  select {
    height: 34px;
    padding: 0 9px;
    border: 1px solid #dce3eb;
    border-radius: 8px;
    background: #fff;
  }
  .table-wrap {
    overflow: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  th,
  td {
    padding: 11px;
    border-bottom: 1px solid #edf1f5;
    text-align: left;
    white-space: nowrap;
  }
  th {
    color: #788396;
    font-size: 12px;
  }
  @media (max-width: 720px) {
    header {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
