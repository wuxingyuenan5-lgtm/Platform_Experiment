<template>
  <div>
    <!-- 待处理风险 -->
    <riskElm v-if="!isSinglePlatform" class="mb-5" />
    <Tabs size="small" :tabBarGutter="16" v-model:active-key="activeKey">
      <TabPane key="1">
        <template #tab>
          <div class="text-base">信息概览</div>
        </template>
        <overviewPane
          :product="product"
          :productChildren="productChildrenRisk"
          :loading="loading"
        />
      </TabPane>
      <TabPane key="2">
        <template #tab>
          <div class="text-base">风险处理</div>
        </template>
        <riskPane
          :product="product"
          :productSource="productSource"
          :loading="loading"
          :isFirst="isFirst"
          :productChildrenRisk="productChildrenRisk"
        />
      </TabPane>
      <TabPane key="3"
        ><template #tab>
          <div class="text-base">分级配置</div>
        </template>
        <configPane :showStrategy="!isSinglePlatform" />
      </TabPane>
      <template #rightExtra>
        <Button v-if="activeKey == '2'" size="small" @click="handleRefresh">刷新</Button>
      </template>
    </Tabs>
  </div>
</template>
<script lang="tsx" setup>
  import riskElm from './components/risk.vue';
  import { Tabs, TabPane, Button } from 'ant-design-vue';
  import { onMounted, ref, computed, watch } from 'vue';
  import overviewPane from './overview/index.vue';
  import riskPane from './risk/index.vue';
  import configPane from './config/index.vue';
  import { useRoute } from 'vue-router';
  import { useProductRisk } from '@/views/risk/product/risk/hooks';
  import { watchOnce, watchDebounced } from '@vueuse/shared';

  const activeKey = ref('0');
  const route = useRoute();
  // 当前产品
  const productId = ref();
  // 是否是单一平台产品
  const isSinglePlatform = ref(true);
  watchOnce(
    () => route,
    () => {
      productId.value = route.path.split('/').pop();
    },
    { immediate: true },
  );
  const {
    product,
    loading,
    isFirst,
    dataSource: productChildrenRisk,
    productSource,
    refresh,
    artificialStop,
  } = useProductRisk(productId, { showLoading: false });
  // console.log('product-------666', product);
  // console.log('productChildrenRisk-------666', productChildrenRisk);
  watchDebounced(
    () => productChildrenRisk,
    () => {
      let _platform = undefined;
      for (const item of productChildrenRisk.value) {
        if (!_platform) {
          _platform = item.platform;
        } else if (_platform !== item.platform) {
          isSinglePlatform.value = false;
          break;
        }
      }
      console.log('productChildrenRisk changed-------', productChildrenRisk);
      console.log('isSinglePlatform changed-------', isSinglePlatform);
    },
    { deep: true, debounce: 1000 },
  );
  onMounted(() => {
    activeKey.value = route.query.active as string;
    artificialStop.value = false;
  });
  function handleRefresh() {
    refresh();
  }
</script>
