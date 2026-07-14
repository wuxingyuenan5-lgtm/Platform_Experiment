<template>
  <div class="desk-tabs">
    <button
      v-for="item in tabs"
      :key="item.key"
      type="button"
      :class="{ 'is-active': item.key === activeKey }"
      @click="$emit('update:activeKey', item.key)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
  import type { StrategyDeskKey } from '../types';

  defineProps<{
    tabs: { key: StrategyDeskKey; label: string }[];
    activeKey: StrategyDeskKey;
  }>();

  defineEmits<{
    (e: 'update:activeKey', value: StrategyDeskKey): void;
  }>();
</script>

<style scoped lang="less">
  .desk-tabs {
    display: inline-flex;
    gap: 6px;
    padding: 5px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow: var(--strategy-shadow);
  }
  .desk-tabs button {
    min-width: 94px;
    height: 38px;
    padding: 0 18px;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: var(--strategy-text-3);
    font-size: 13px;
    font-weight: 800;
    cursor: pointer;
  }
  .desk-tabs .is-active {
    color: var(--strategy-accent-strong);
    background: var(--strategy-accent-soft);
    box-shadow: inset 0 0 0 1px rgba(201, 72, 72, 0.12);
  }
</style>
