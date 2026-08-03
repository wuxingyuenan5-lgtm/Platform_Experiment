<template>
  <Alert
    v-if="meta.status !== 'ready'"
    show-icon
    :type="alertType"
    :message="title"
    :description="description"
  />
</template>

<script setup lang="ts">
  import { computed, type PropType } from 'vue';
  import { Alert } from 'ant-design-vue';
  import type { ProductDataMeta } from '@/api/platform/productDataState';

  const props = defineProps({
    meta: {
      type: Object as PropType<ProductDataMeta>,
      required: true,
    },
  });

  const alertType = computed(() => {
    if (props.meta.status === 'unavailable') return 'error';
    if (props.meta.status === 'stale') return 'warning';
    return 'info';
  });

  const title = computed(() => {
    const labels: Record<ProductDataMeta['status'], string> = {
      ready: '数据可用',
      no_data: '暂无数据',
      unavailable: '数据源不可用',
      stale: '正在展示过期数据',
      not_configured: '数据源尚未配置',
      unsupported: '当前数据源不支持此功能',
    };
    return labels[props.meta.status];
  });

  const description = computed(() => {
    const parts = [props.meta.message, `来源：${props.meta.source}`];
    if (props.meta.asOf) parts.push(`截至：${props.meta.asOf}`);
    if (props.meta.timezone) parts.push(`时区：${props.meta.timezone}`);
    if (props.meta.errorCode) parts.push(`错误码：${props.meta.errorCode}`);
    if (props.meta.fallbackSource) parts.push(`回退来源：${props.meta.fallbackSource}`);
    return parts.filter(Boolean).join('；');
  });
</script>
