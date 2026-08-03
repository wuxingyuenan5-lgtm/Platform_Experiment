<template>
  <div>
    <Tabs size="small" :tabBarGutter="16" v-model:active-key="activeKey">
      <TabPane key="1">
        <template #tab>
          <div class="text-base">信息概览</div>
        </template>
        <overviewPane
          :account="account"
          :loading="loading"
          :productChildrenRisk="productChildrenRisk"
          :showProductHeader="!isSinglePlatform"
        />
      </TabPane>
      <TabPane key="2">
        <template #tab>
          <div class="text-base">风险处理</div>
        </template>
        <riskPane
          :loading="loading"
          :isFirst="isFirst"
          :productChildrenRisk="productChildrenRisk"
          :showProductHeader="!isSinglePlatform"
        />
      </TabPane>
      <TabPane key="3"
        ><template #tab>
          <div class="text-base">分级配置</div>
        </template>
        <configPane :account="account" :showStrategy="!isSinglePlatform" />
      </TabPane>
      <template #rightExtra>
        <Button v-if="activeKey == '2'" size="small" @click="handleRefresh">刷新</Button>
      </template>
    </Tabs>
  </div>
</template>
<script lang="tsx" setup>
  // import riskElm from '../compo /nents/risk.vue';
  import { Tabs, TabPane, Button } from 'ant-design-vue';
  import { onMounted, ref, computed, watch } from 'vue';
  import overviewPane from '../overview/index.vue';
  import riskPane from '../risk/index.vue';
  import configPane from '../config/index.vue';
  import { useRoute } from 'vue-router';
  import { useAccountRisk } from '@/views/risk/product/risk/hooks';
  import { watchOnce } from '@vueuse/shared';

  const activeKey = ref('1');
  const route = useRoute();
  const isSinglePlatform = ref(true);
  const params = ref();
  watchOnce(
    () => route,
    () => {
      // console.log('route------', route);
      params.value = route.meta?.curParams;
    },
    { immediate: true },
  );
  const {
    loading,
    dataSource: productChildrenRisk,
    account,
    isFirst,
    refresh,
    artificialStop,
  } = useAccountRisk(params as any, { showLoading: false });
  // console.log('productChildrenRisk-------', productChildrenRisk);

  onMounted(() => {
    // activeKey.value = route.query.active as string;
    artificialStop.value = false;
  });
  function handleRefresh() {
    refresh();
  }
</script>
