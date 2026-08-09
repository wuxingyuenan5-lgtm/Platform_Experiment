<template>
  <div
    v-if="visible"
    class="restored-product-banner"
    :class="`is-${state}`"
    role="status"
    :data-product-state="state"
    :data-actionable="String(actionable)"
  >
    <strong>{{ stateLabel }}</strong>
    <span>{{ messageText }}</span>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { ProductDataState } from '@/data/productDataEnvelope';

  const props = withDefaults(
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

  const visible = computed(() => ['unavailable', 'error'].includes(props.state));

  const stateLabel = computed(() => '数据暂不可用');

  const messageText = computed(() =>
    props.state === 'error' ? '当前数据暂时无法获取，请稍后重试。' : '暂无数据。',
  );
</script>

<style scoped>
  .restored-product-banner {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 10px;
    margin: 0 0 12px;
    padding: 8px 10px;
    border: 1px solid #d8e2ec;
    border-radius: 6px;
    background: #f8fafc;
    color: #334155;
    font-size: 13px;
  }

  .restored-product-banner strong {
    color: #b42318;
  }

  @media (max-width: 768px) {
    .restored-product-banner {
      grid-template-columns: 1fr;
    }
  }
</style>
