<template>
  <PositionElm :product="product" :productChildren="productChildren" />
  <!-- <div>
    <template v-if="product?.value.includes(AccountType.SHFE)">
      <positionFutureElm :productChildrenRisk="productChildrenRisk" />
    </template>
    <template v-else>
      <PositionElm :product="product" :productChildren="productChildren" />
    </template>
  </div> -->
</template>
<script lang="tsx" setup>
  import ProductRisk from '@/views/risk/home/components/productRisk.vue';
  import PositionElm from './position.vue';
  import positionFutureElm from './positionFuture.vue';
  import { AccountType } from '@/views/account/detail/type';
  import PositionChartElm from './positionChart.vue';

  const props = defineProps({
    product: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    productChildren: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    // productChildrenRisk: {
    //   type: Array as PropType<any>,
    //   default: () => [],
    // },
    loading: {
      type: Boolean,
      default: false,
    },
  });
</script>
