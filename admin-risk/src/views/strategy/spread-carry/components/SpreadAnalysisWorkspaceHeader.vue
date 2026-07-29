<template>
  <section class="spread-workspace-head">
    <div class="spread-workspace-head__main">
      <label v-if="variant === 'domesticOverseas'" class="workspace-control">
        <span>标的</span>
        <select :value="domesticMetal" @change="emitSelect('domesticMetal', $event)">
          <option value="gold">金</option>
          <option value="silver">银</option>
          <option value="copper">铜</option>
        </select>
      </label>

      <label v-else class="workspace-control">
        <span>主交易所</span>
        <select :value="selectedVenue" @change="emitSelect('selectedVenue', $event)">
          <option value="Bybit">Bybit</option>
          <option value="Binance">Binance</option>
          <option value="OKX">OKX</option>
        </select>
      </label>

      <label class="workspace-control">
        <span>主腿</span>
        <select :value="leftLegSymbol" @change="emitSelect('leftLegSymbol', $event)">
          <option value="XAUTUSDT.P">XAUTUSDT.P</option>
          <option value="SHFE.au2604">SHFE.au2604</option>
          <option value="SHFE.ag2510">SHFE.ag2510</option>
        </select>
      </label>

      <label class="workspace-control">
        <span>对冲腿</span>
        <select :value="rightLegSymbol" @change="emitSelect('rightLegSymbol', $event)">
          <option value="XAUUSD+">XAUUSD+</option>
          <option value="SHFE.au2606">SHFE.au2606</option>
          <option value="SHFE.ag2512">SHFE.ag2512</option>
        </select>
      </label>

      <label class="workspace-control">
        <span>时间精度</span>
        <select :value="selectedResolution" @change="emitSelect('selectedResolution', $event)">
          <option value="15分钟">15分钟</option>
          <option value="30分钟">30分钟</option>
          <option value="1小时">1小时</option>
          <option value="4小时">4小时</option>
        </select>
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
  import type { SpreadWorkspaceVariant } from '../types';

  type DomesticMetal = 'gold' | 'silver' | 'copper';

  defineProps<{
    variant: SpreadWorkspaceVariant;
    domesticMetal: DomesticMetal;
    selectedVenue: string;
    leftLegSymbol: string;
    rightLegSymbol: string;
    selectedResolution: string;
  }>();

  const emit = defineEmits<{
    (event: 'update:domesticMetal', value: DomesticMetal): void;
    (event: 'update:selectedVenue', value: string): void;
    (event: 'update:leftLegSymbol', value: string): void;
    (event: 'update:rightLegSymbol', value: string): void;
    (event: 'update:selectedResolution', value: string): void;
  }>();

  function emitSelect(
    field:
      | 'domesticMetal'
      | 'selectedVenue'
      | 'leftLegSymbol'
      | 'rightLegSymbol'
      | 'selectedResolution',
    event: Event,
  ) {
    const value = (event.target as HTMLSelectElement).value;
    if (field === 'domesticMetal') {
      emit('update:domesticMetal', value as DomesticMetal);
      return;
    }
    emit(`update:${field}` as never, value as never);
  }
</script>

<style scoped lang="less">
  .spread-workspace-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 2px 0;
  }

  .spread-workspace-head__main {
    display: flex;
    flex: 0 0 auto;
    flex-wrap: nowrap;
    gap: var(--strategy-space-2);
    align-items: center;
    width: auto;
    max-width: 100%;
    min-height: 46px;
    padding: 5px var(--strategy-space-2);
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .workspace-control {
    display: inline-flex;
    flex: 0 0 auto;
    align-items: center;
    gap: var(--strategy-space-1);
    min-width: 0;
  }

  .workspace-control span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
    letter-spacing: 0;
    white-space: nowrap;
  }

  .workspace-control select {
    width: auto;
    min-width: 88px;
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
  }

  @media (max-width: 1480px) {
    .spread-workspace-head,
    .spread-workspace-head__main {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
