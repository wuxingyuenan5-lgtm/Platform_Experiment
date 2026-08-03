<template>
  <section class="funding-carry-page">
    <ProductNotConfiguredPanel
      title="资费与资金费率套利数据链尚未配置"
      description="当前仓库没有为资金费率行情、APR、仓位、PnL或执行回报注册正式Provider与Runtime事实Owner，因此不展示静态行情、模拟收益或未经ACK/Fill证明的成功状态。"
      source="not-configured: funding-carry-provider-and-runtime-owner"
    />
  </section>
</template>

<script setup lang="ts">
  import ProductNotConfiguredPanel from '@/components/ProductDataState/ProductNotConfiguredPanel.vue';

  withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedExchange?: string;
      selectedSymbol?: string;
      selectedResolution?: string;
    }>(),
    {
      activeSection: 'analysis',
      selectedExchange: '',
      selectedSymbol: '',
      selectedResolution: '',
    },
  );
</script>

<style scoped>
  .funding-carry-page {
    padding: 18px;
  }
</style>
