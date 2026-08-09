<template>
  <section
    class="restored-product-surface"
    :data-product-state="state"
    :data-actionable="String(actionable)"
  >
    <slot></slot>
  </section>
</template>

<script setup lang="ts">
  import type { ProductDataState } from '@/data/productDataEnvelope';

  withDefaults(
    defineProps<{
      state: ProductDataState;
      source?: string;
      asOf?: string | null;
      actionable?: boolean;
      message?: string;
    }>(),
    {
      source: '',
      asOf: null,
      actionable: false,
      message: '',
    },
  );
</script>

<style scoped>
  .restored-product-surface {
    min-width: 0;
  }

  .restored-product-surface[data-product-state='sample'][data-actionable='false']
    :deep(.ant-btn-primary),
  .restored-product-surface[data-product-state='sample'][data-actionable='false']
    :deep(.ant-btn-dangerous),
  .restored-product-surface[data-product-state='sample'][data-actionable='false']
    :deep(button[type='submit']),
  .restored-product-surface[data-product-state='sample'][data-actionable='false']
    :deep([data-write-action='true']),
  .restored-product-surface[data-product-state='sample'][data-actionable='false']
    :deep([class*='execution'] button),
  .restored-product-surface[data-product-state='sample'][data-actionable='false']
    :deep([class*='order'] button) {
    pointer-events: none !important;
    opacity: 0.52 !important;
    cursor: not-allowed !important;
  }
</style>
