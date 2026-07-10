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
    padding: 6px;
    border: 1px solid var(--strategy-border);
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: var(--strategy-shadow);
    gap: 4px;

    button {
      min-width: 92px;
      height: 40px;
      padding: 0 16px;
      border: 0;
      border-radius: 12px;
      background: transparent;
      color: var(--strategy-text-3);
      font-size: 14px;
      font-weight: 800;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .is-active {
      background: var(--strategy-accent-soft);
      color: var(--strategy-accent-strong);
      box-shadow: inset 0 0 0 1px rgba(201, 72, 72, 0.1);
    }
  }
</style>
