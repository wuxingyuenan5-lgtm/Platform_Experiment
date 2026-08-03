import { onMounted, ref, watch } from 'vue';
// import { getUsd2cny } from '@/api/monitor';
import { useProjectConfigStore } from '@/store/modules/projectConfig';
import { getDataExchange } from '@/api/data/exchange';

// export function useUsd2Cny() {
//   const usd2cny = ref<number>(1);
//   async function getUsd2CnyFn() {
//     const res = await getUsd2cny();
//     if (res.retCode == 0) {
//       usd2cny.value = res.data?.USDExchangeRate || 1;
//     }
//   }
//   onMounted(() => {
//     getUsd2CnyFn();
//   });
//   return {
//     usd2cny,
//   };
// }

export function usdDataExchange() {
  // 汇率数据
  const exchange = ref();
  const useProjectConfig = useProjectConfigStore();

  const _key = 'exchange';
  const _map = useProjectConfig.getOptionsMap;

  function getDataExchangeFn() {
    getDataExchange().then((res) => {
      if (res?.retCode == 0) {
        exchange.value = res?.data;
        useProjectConfig.setOptionsMap({
          ..._map,
          [_key]: JSON.parse(JSON.stringify(exchange.value)),
        });
      }
    });
  }
  watch(
    () => useProjectConfig.getOptionsMap,
    () => {
      if (_map[_key]) {
        exchange.value = JSON.parse(JSON.stringify(_map[_key]));
      }
    },
    { deep: true },
  );
  onMounted(() => {
    if (!_map[_key]) {
      getDataExchangeFn();
    } else {
      exchange.value = JSON.parse(JSON.stringify(_map[_key]));
    }
  });
  return {
    exchange,
  };
}
