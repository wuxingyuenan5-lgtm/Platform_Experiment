<template>
  <div class="desk-tabs">
    <button
      v-for="item in exchanges"
      :key="item"
      type="button"
      :class="{ 'is-active': item === modelValue }"
      @click="$emit('update:modelValue', item)"
    >
      {{ item }}
    </button>
  </div>
</template>

<script setup lang="ts">
  import type { FundingExchange } from '../types';

  defineProps<{
    modelValue: FundingExchange;
    exchanges: FundingExchange[];
  }>();

  defineEmits<{
    (e: 'update:modelValue', value: FundingExchange): void;
  }>();
</script>

<style scoped lang="less">
  .desk-tabs {
    display: inline-flex;
    align-items: center;
    padding: 4px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    gap: 6px;

    button {
      min-width: 88px;
      height: var(--strategy-tab-height);
      padding: 0 18px;
      border: 0;
      border-radius: 12px;
      background: transparent;
      color: var(--strategy-text-2);
      font-size: var(--strategy-font-base);
      font-weight: 700;
      white-space: nowrap;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .is-active {
      background: var(--strategy-accent-soft);
      color: var(--strategy-accent-strong);
      box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    }
  }
</style>
