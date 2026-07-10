<template>
  <div>
    <div class="flex justify-between items-center">
      <div class="text-base leading-6 font-500 pb-1">{{ title || product?.label }}</div>
      <LevelMarket />
    </div>
    <!-- 产品 -->
    <productRisk :showProductHeader="showProductHeader" :product="product" :isTiming="isTiming" />
  </div>
</template>
<script lang="tsx" setup>
  import LevelMarket from './LevelMarket.vue';
  import productRisk from './productRisk.vue';

  const props = defineProps({
    title: {
      type: String,
      default: '产品概览',
    },
    product: {
      type: Object,
      default: () => ({}),
    },
    isTiming: {
      type: Boolean,
      default: true,
    },
    showProductHeader: {
      type: Boolean,
      default: true,
    },
  });
</script>
<style lang="less" scoped></style>
