<template>
  <div>
    <!-- <Tabs size="small" :tabBarGutter="16" v-model:active-key="activeKey">
      <TabPane key="1">
        <template #tab>
          <div class="text-base">产品端</div>
        </template>
        <ProductPane />
      </TabPane>
      <TabPane key="2">
        <template #tab>
          <div class="text-base">服务器端</div>
        </template>
        <ServerPane />
      </TabPane>
    </Tabs> -->
    <ProductPane />
  </div>
</template>
<script lang="tsx" setup>
  import { ref } from 'vue';
  import ProductPane from './components/Product.vue';
  import ServerPane from './components/Server.vue';
  import { Tabs, TabPane } from 'ant-design-vue';

  const activeKey = ref('2');
</script>
