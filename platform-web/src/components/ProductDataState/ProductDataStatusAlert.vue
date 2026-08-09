<template>
  <Alert v-if="visible" show-icon :type="alertType" :message="title" :description="description" />
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

  const visible = computed(() => ['unavailable', 'stale'].includes(props.meta.status));

  const alertType = computed(() => (props.meta.status === 'unavailable' ? 'error' : 'warning'));

  const title = computed(() => (props.meta.status === 'stale' ? '数据更新延迟' : '数据暂不可用'));

  const description = computed(() =>
    props.meta.status === 'stale'
      ? '当前数据可能存在延迟，请结合页面更新时间判断。'
      : '当前数据暂时无法获取，请稍后重试。',
  );
</script>
