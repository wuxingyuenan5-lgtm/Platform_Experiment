<template>
  <div
    class="restored-product-banner"
    :class="`is-${state}`"
    role="status"
    :data-product-state="state"
    :data-actionable="String(actionable)"
  >
    <strong>{{ stateLabel }}</strong>
    <span>{{ messageText }}</span>
    <small>
      {{ source }}
      <template v-if="asOf"> · {{ asOf }}</template>
    </small>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import type { ProductDataState } from '@/data/productDataEnvelope';

  const props = withDefaults(
    defineProps<{
      state: ProductDataState;
      source: string;
      asOf?: string | null;
      actionable?: boolean;
      message?: string;
    }>(),
    {
      asOf: null,
      actionable: false,
      message: '',
    },
  );

  const stateLabel = computed(
    () =>
      ({
        live: '实时数据',
        sample: '示例数据 · 非实时 · 不可执行',
        unavailable: '数据源尚未配置',
        error: '实时数据获取失败',
      }[props.state]),
  );

  const messageText = computed(() => {
    if (props.message) return props.message;
    if (props.state === 'sample') return '当前恢复原产品结构，数值仅用于界面展示。';
    if (props.state === 'error') return '当前展示明确标记的示例内容，不冒充实时结果。';
    return '数据来源和可操作性以本状态为准。';
  });
</script>

<style scoped>
  .restored-product-banner {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) auto;
    align-items: center;
    gap: 10px;
    margin: 0 0 12px;
    padding: 10px 12px;
    border: 1px solid #d8e2ec;
    border-radius: 8px;
    background: #f8fafc;
    color: #334155;
    font-size: 13px;
  }

  .restored-product-banner strong {
    color: #9a6700;
  }

  .restored-product-banner.is-live strong {
    color: #087a55;
  }

  .restored-product-banner.is-error strong {
    color: #b42318;
  }

  .restored-product-banner small {
    color: #64748b;
    text-align: right;
  }

  @media (max-width: 768px) {
    .restored-product-banner {
      grid-template-columns: 1fr;
    }

    .restored-product-banner small {
      text-align: left;
    }
  }
</style>
