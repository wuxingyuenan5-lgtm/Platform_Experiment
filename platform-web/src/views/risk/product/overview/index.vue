<template>
  <div>
    <productElm
      v-if="product && Object.keys(product)?.length > 0"
      :showProductHeader="showProductHeader"
      :title="product?.label || '账户概览'"
      :product="product"
      :isTiming="false"
    />
    <accountElm
      v-else
      :dataSource="productChildrenRisk"
      :title="account?.accountName || '账户概览'"
    />
    <div class="flex gap-4 pt-6 w-full">
      <div class="flex-1">
        <networthLine v-if="product && Object.keys(product)?.length > 0" :product="product" />
        <networthAccountLine v-else :account="account" />
      </div>
      <div class="w-568px">
        <PositionChartElm :record="dataSoure" :loading="loadingPosition" />
      </div>
    </div>
    <PositionElm class="pt-6" :record="dataSoure" :loading="loadingPosition" />
  </div>
</template>
<script lang="tsx" setup>
  import productElm from '@/views/risk/home/components/product.vue';
  import accountElm from '@/views/risk/home/components/account.vue';
  import networthLine from './components/networthLine.vue';
  import networthAccountLine from './components/networthAccountLine.vue';
  import PositionElm from './components/position.vue';

  import PositionChartElm from './components/positionChart.vue';
  import { ref, watch } from 'vue';
  import { getExecutionAllPositions, getExecutionPositions } from '@/api/risk/execution';

  const props = defineProps({
    product: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    account: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    loading: {
      type: Boolean,
      default: false,
    },
    showProductHeader: {
      type: Boolean,
      default: true,
    },
    productChildrenRisk: {
      type: Array as PropType<any>,
      default: () => [],
    },
  });
  // 仓位规模
  const dataSoure = ref<any>([]);
  const loadingPosition = ref(false);
  watch(
    () => props.product,
    (cur) => {
      if (cur && JSON.stringify(cur) !== '{}') {
        getExecutionAllPositionsFn();
      }
    },
    { immediate: true },
  );
  watch(
    () => props.account,
    (cur) => {
      if (cur && JSON.stringify(cur) !== '{}') {
        getExecutionPositionsFn();
      }
    },
    { immediate: true },
  );
  function getExecutionAllPositionsFn() {
    loadingPosition.value = true;
    getExecutionAllPositions({
      productId: props.product?.id,
    })
      .then((res) => {
        if (res.retCode == 0) {
          dataSoure.value = res.data;
        }
      })
      .finally(() => {
        loadingPosition.value = false;
      });
  }
  function getExecutionPositionsFn() {
    loadingPosition.value = true;
    getExecutionPositions({
      checkCode: props.account?.checkCode,
      platform: props.account?.platform,
    })
      .then((res) => {
        if (res.retCode == 0) {
          dataSoure.value = res.data;
        }
      })
      .finally(() => {
        loadingPosition.value = false;
      });
  }
</script>
