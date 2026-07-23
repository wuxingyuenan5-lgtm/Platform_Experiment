<template>
  <article class="symbol-card">
    <div class="section-head">
      <div>
        <span>Funding Snapshot</span>
        <h3>当前币种快照</h3>
      </div>
    </div>

    <div class="symbol-list">
      <button
        v-for="item in items"
        :key="item.symbol"
        type="button"
        :class="{ 'is-active': item.symbol === modelValue }"
        @click="$emit('update:modelValue', item.symbol)"
      >
        <div>
          <strong>{{ item.symbol }}</strong>
          <small>净 Carry {{ signed(item.netCarry) }}</small>
        </div>
        <em :class="item.fundingRate >= 0 ? 'is-positive' : 'is-negative'">{{
          signed(item.fundingRate, 4)
        }}</em>
      </button>
    </div>
  </article>
</template>

<script setup lang="ts">
  import type { FundingSymbol, FundingSymbolSnapshot } from '../types';

  defineProps<{
    modelValue: FundingSymbol;
    items: FundingSymbolSnapshot[];
  }>();

  defineEmits<{
    (e: 'update:modelValue', value: FundingSymbol): void;
  }>();

  function signed(value: number, digits = 2) {
    const prefix = value > 0 ? '+' : '';
    return `${prefix}${value.toFixed(digits)}%`;
  }
</script>

<style scoped lang="less">
  .symbol-card {
    height: 100%;
    padding: 22px;
    border: 1px solid rgba(134, 115, 87, 0.12);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: 0 16px 36px rgba(94, 76, 52, 0.06);
  }

  .section-head span {
    color: rgba(36, 29, 21, 0.48);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .section-head h3 {
    margin: 10px 0 0;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-sans);
    font-size: 23px;
    font-weight: 900;
  }

  .symbol-list {
    display: grid;
    gap: 10px;
    margin-top: 18px;
  }

  .symbol-list button {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 12px;
    min-height: 58px;
    padding: 0 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 14px;
    background: #fff;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .symbol-list button:hover,
  .symbol-list button.is-active {
    border-color: rgba(201, 72, 72, 0.14);
    background: var(--strategy-surface-selected);
  }

  .symbol-list strong,
  .symbol-list small,
  .symbol-list em {
    display: block;
  }

  .symbol-list strong {
    color: var(--strategy-text-1);
    font-size: 18px;
    font-weight: 800;
  }

  .symbol-list small {
    margin-top: 4px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .symbol-list em {
    font-style: normal;
    font-size: 18px;
    font-weight: 600;
  }

  .is-positive {
    color: #1ea15e;
  }

  .is-negative {
    color: #db3a34;
  }
</style>
