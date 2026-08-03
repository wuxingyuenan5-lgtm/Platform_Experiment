<template>
  <div>
    <!-- 风险 -->
    <riskElm />
    <!-- 产品概览 -->
    <productElm
      v-for="(item, i) in userProducts"
      :key="i"
      :product="item"
      :title="item?.label"
      class="pt-6"
    />
    <!-- 资金占比  海内外净值占比偏移率 距离沪金交割日剩余时间-->
    <div class="flex gap-3 pt-6">
      <fundElm class="w-33%" />
      <networthElm class="w-33%" />
      <closeDateElm class="w-33%" />
    </div>
  </div>
</template>
<script lang="tsx" setup>
  import { ref, computed } from 'vue';
  import riskElm from './components/risk.vue';
  import productElm from './components/product.vue';
  import fundElm from './components/fund.vue';
  import networthElm from './components/networth.vue';
  import closeDateElm from './components/closeDate.vue';
  import { useUserStore } from '@/store/modules/user';

  const userStore = useUserStore();
  const userProducts = computed(() => userStore.getUserInfoAccount);
</script>
