<template>
  <Card :bordered="false" class="product-state-panel">
    <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE">
      <template #description>
        <div class="state-copy">
          <strong>{{ title }}</strong>
          <span>{{ description }}</span>
          <span>来源：{{ source }}</span>
          <span>状态：not_configured</span>
        </div>
      </template>
    </Empty>
  </Card>
</template>

<script setup lang="ts">
  import { Card, Empty } from 'ant-design-vue';

  withDefaults(
    defineProps<{
      title: string;
      description?: string;
      source?: string;
    }>(),
    {
      description: '该正式产品页面尚未配置生产数据源，不展示演示值或随机值。',
      source: 'not-configured',
    },
  );
</script>

<style scoped>
  .product-state-panel {
    min-height: 220px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .state-copy {
    display: grid;
    gap: 6px;
    color: #59636e;
  }

  .state-copy strong {
    color: #1f2937;
    font-size: 16px;
  }
</style>
