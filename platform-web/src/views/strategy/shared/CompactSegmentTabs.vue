<template>
  <div class="segment-tabs compact-segment-tabs">
    <button
      v-for="item in items"
      :key="item.key"
      type="button"
      :class="{ 'is-active': item.key === modelValue }"
      @click="$emit('update:modelValue', item.key)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
  defineProps<{
    items: Array<{ key: string; label: string }>;
    modelValue: string;
  }>();

  defineEmits<{
    (e: 'update:modelValue', value: string): void;
  }>();
</script>

<style scoped lang="less">
  .segment-tabs {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow);
  }

  .segment-tabs button {
    min-width: 88px;
    height: var(--strategy-tab-height);
    padding: 0 16px;
    border: none;
    border-radius: var(--strategy-radius-control);
    background: transparent;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
  }

  .segment-tabs button.is-active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
  }
</style>
