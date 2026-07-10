<template>
  <div>
    <KeepAlive>
      <component
        type="Order"
        :dataSource="dataSource"
        :dataSourceOther="dataSourceDeal"
        :is="tabsComponentMap.Order"
        :scaleOptions="scaleOptions"
        @change="changeScale"
      />
    </KeepAlive>
  </div>
</template>
<script lang="ts" setup>
  import { ref, reactive, watch } from 'vue';
  import { BasicTabs } from '@/components/Tabs/index';
  import Order from './Order.vue';
  import { useWebSocket } from '@vueuse/core';
  import { useProjectConfigStore } from '@/store/modules/projectConfig';
  import { findNode, useSymbolSelect } from '@/utils/options/useBasicOptions';

  const dataSource = ref();
  const dataSourceDeal = ref();
  const _ws_url = import.meta.env.VITE_GLOB_API_URL_MONITOR_WS;

  const webSocketUrlMap = reactive({
    Order: _ws_url + '/websocket/orderBook/',
    Deal: _ws_url + '/websocket/publicTrade/',
  });
  const tabsComponentMap = {
    Order,
  };

  const searchInfo = {
    category: 'spot',
    symbol: 'BTCUSDT',
    limit: 50,
    scale: 0.01,
  };
  const searchInfoDeal = {
    category: 'spot',
    symbol: 'BTCUSDT',
    limit: 20,
  };
  const { send, open, close, status } = useWebSocket(webSocketUrlMap.Order, {
    immediate: false,
    onMessage: (ws, event) => {
      dataSource.value = JSON.parse(event.data);
      // console.log('dataSource.value---', dataSource.value);
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
      // console.log('dataSource.value---1111', dataSourceDeal.value);
    },
    onConnected: (ws) => {
      console.log('WebSocket onConnected', ws);
    },
    onError: (ws, event) => {
      console.log('WebSocket onError', ws, event);
    },
  });

  const useProjectConfig = useProjectConfigStore();
  const { options } = useSymbolSelect();
  const scaleOptions: any = ref([]);
  watch(
    () => [useProjectConfig?.currentSymbolInfo, options.value],
    (newV) => {
      console.log('newV===', newV);

      if (useProjectConfig?.currentSymbolInfo?.length > 0 && options.value?.length > 0) {
        const _symbol = findNode(options.value, useProjectConfig?.currentSymbolInfo, {
          value: 'symbol',
        });
        // console.log('_symbol===', _symbol);

        if (_symbol?.scale) {
          scaleOptions.value = JSON.parse(_symbol?.scale).map((item) => {
            return {
              label: item,
              value: item,
            };
          });
          searchInfo.scale = scaleOptions.value?.[0].value;
        }
        searchInfo.category = useProjectConfig?.currentSymbolInfo[1];
        searchInfoDeal.category = useProjectConfig?.currentSymbolInfo[1];
        searchInfo.symbol = _symbol?.symbol;
        searchInfoDeal.symbol = _symbol?.symbol;
        changeSymbol();
      }
    },
    { immediate: true },
  );
  function changeScale(params: any) {
    searchInfo.scale = params;
    changeSymbol();
  }
  function changeSymbol() {
    if (status.value === 'CLOSED') {
      initData();
    }
    send(JSON.stringify(searchInfo));
    sendDeal(JSON.stringify(searchInfoDeal));
  }
  function initData() {
    open();
    openDeal();
  }
  window.addEventListener('beforeunload', function () {
    close();
    closeDeal();
  });
</script>
