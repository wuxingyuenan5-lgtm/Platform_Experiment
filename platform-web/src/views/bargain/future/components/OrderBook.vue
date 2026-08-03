<template>
  <div class="h-full">
    <div class="component-background mb-1">
      <BasicTabs class="pl-1.5" v-model:value="tabVal" :options="tabsOptions" />
    </div>
    <KeepAlive>
      <component
        v-if="tabVal === 'Order'"
        type="Order"
        :dataSource="dataSource"
        :dataSourceOther="dataSourceDeal"
        :is="tabsComponentMap.Order"
        :scaleOptions="scaleOptions"
      />
      <component v-else :dataSource="dataSourceDeal" type="Deal" :is="tabsComponentMap.Order" />
    </KeepAlive>
  </div>
</template>
<script lang="ts" setup>
  import { ref, reactive, watch } from 'vue';
  import { BasicTabs } from '@/components/Tabs/index';
  import Order from './Order.vue';
  import { useWebSocket } from '@vueuse/core';
  import { useProjectConfigStore } from '@/store/modules/projectConfig';
  // import { findNode, useSymbolFutureSelect, useSymbolRisk } from '@/utils/options/useBasicOptions';

  const props = defineProps({
    checkCode: {
      type: String,
      default: '',
    },
  });
  const _future_ws_url = import.meta.env.VITE_GLOB_API_URL_FUTURE_WS;
  const dataSource = ref();
  const dataSourceDeal = ref();
  const webSocketUrlMap = reactive({
    Order: _future_ws_url + '/ws/quote',
    Deal: _future_ws_url + '/ws/newDeal',
  });
  const tabVal = ref('Order');
  const tabsComponentMap = {
    Order,
  };

  const searchInfo = {
    // checkCode: props.checkCode,
  };
  const searchInfoDeal = {
    // checkCode: props.checkCode,
  };
  const { send, open, close } = useWebSocket(webSocketUrlMap.Order, {
    immediate: false,
    onMessage: (ws, event) => {
      dataSource.value = JSON.parse(event.data);
      // console.log('dataSource.value---', dataSource.value, dealData(JSON.parse(event.data)));
    },
    onConnected: (ws) => {
      console.log('WebSocket onConnected', ws);
    },
    onError: (ws, event) => {
      console.log('WebSocket onError', ws, event);
    },
  });

  const {
    send: sendDeal,
    open: openDeal,
    close: closeDeal,
  } = useWebSocket(webSocketUrlMap.Deal, {
    immediate: false,
    onMessage: (ws, event) => {
      dataSourceDeal.value = JSON.parse(event.data);
      // console.log('dataSource.value---sendDeal', dataSourceDeal.value);
    },
    onConnected: (ws) => {
      console.log('WebSocket onConnected-sendDeal', ws);
    },
    onError: (ws, event) => {
      console.log('WebSocket onError-sendDeal', ws, event);
    },
  });

  const tabsOptions = [
    {
      value: 'Order',
      label: '订单薄',
    },
    {
      value: 'Deal',
      label: '最新成交',
    },
  ];
  const useProjectConfig = useProjectConfigStore();
  // const { options: cascaderOptions } = useSymbolRisk({ repeat: 3 });
  const scaleOptions: any = ref([]);
  watch(
    () => useProjectConfig.getCurrentSymbolFutureInfo,
    (newV) => {
      if (newV?.length > 0) {
        searchInfo.symbol = newV;
        searchInfoDeal.symbol = newV;
        changeSymbol();
      }
    },
    { immediate: true },
  );
  // watch(
  //   () => [useProjectConfig?.currentSymbolFutureInfo, cascaderOptions.value],
  //   (newV) => {
  //     console.log('newV===8888', newV);

  //     if (
  //       useProjectConfig?.currentSymbolFutureInfo?.length > 0 &&
  //       cascaderOptions.value?.length > 0
  //     ) {
  //       // const _symbol = findItem(useProjectConfig?.currentSymbolFutureInfo);
  //       // const _symbol = cascaderOptions.value.find((item: any) => item.value == useProjectConfig?.currentSymbolFutureInfo);
  //       searchInfo.symbol = _symbol?.symbol;
  //       searchInfoDeal.symbol = _symbol?.symbol;
  //       // console.log('newV===9999', searchInfo);

  //       changeSymbol();
  //     }
  //   },
  //   { immediate: true },
  // );
  // function changeScale(params: any) {
  //   searchInfo.scale = params;
  //   changeSymbol();
  // }
  function changeSymbol() {
    send(JSON.stringify(searchInfo));
    console.log('changeSymbol------', searchInfo);

    sendDeal(JSON.stringify(searchInfoDeal));
  }
  function initData() {
    open();
    openDeal();
  }
  initData();
  window.addEventListener('beforeunload', function () {
    close();
    closeDeal();
  });
  function findItem(arr: any[]) {
    if (arr?.length == 0) return null;
    const _item: any = cascaderOptions.value.find((item: any) => item.value == arr[0]);
    // cascaderValExchange.value = _item?.label;
    const _item1 = _item?.children?.find((item: any) => item.value == arr[1]);
    // console.log('_item1', _item1, cascaderOptions.value);

    return _item1;
  }
</script>
