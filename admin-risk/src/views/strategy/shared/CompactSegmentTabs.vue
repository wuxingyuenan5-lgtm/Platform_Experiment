<template>
  <div class="segment-tabs">
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
    padding: 4px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.97);
    box-shadow: var(--strategy-shadow);
  }

  .segment-tabs button {
    min-width: 82px;
    height: 34px;
    padding: 0 15px;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: var(--strategy-text-3);
    font-size: 12px;
    font-weight: 800;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .segment-tabs button.is-active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px rgba(201, 72, 72, 0.12);
  }
</style>
