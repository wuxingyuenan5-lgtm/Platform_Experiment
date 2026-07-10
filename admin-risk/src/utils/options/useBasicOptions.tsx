import { isRef, onMounted, ref, Ref, watch, toRaw, unref } from 'vue';
import { getMonitorSymbolSelect } from '@/api/monitor';
// import { getFmonitorSymbol } from '@/api/fmonitor';
import { getUserInfo } from '@/api/sys/user';
import { toLabelValueOptions } from './basicOptions';
import { useProjectConfigStore } from '@/store/modules/projectConfig';
import { getFutureTqSymbolInfo } from '@/api/future';
import { getUserRelAccounts } from '@/api/quantSystem';
// import { getMt5Symbol } from '@/api/mt5';
import { getExecutionTasksSymbols } from '@/api/risk/execution';

interface Options {
  label?: string;
  value: string;
  children?: Options[];
}
// 基础参数配置
interface Config {
  api: Function;
  params?: any;
}
// 数据处理配置
interface ConfigData {
  option: Options;
  fn?: Function;
}

// 接口参数调用配置
interface ParamsConfig {
  immediate?: boolean;
}

function baseFetch(
  { api, params }: Config,
  { option: { label = 'label', value = 'value' }, fn }: ConfigData,
  paramsConfig: ParamsConfig = { immediate: true },
) {
  const options: Ref<any> = ref([]);
  const useProjectConfig = useProjectConfigStore();
  const regex = /"\/(.+?)\/"/;
  async function fetch() {
    let _key = api.toString().match(regex)?.[1];
    const _params = isRef(params) ? unref(params) : params;
    // console.log('_key----', _key, api.toString());

    // 如果有参数
    if (params && JSON.stringify(_params) != '{}') {
      // console.log('_key-----baseFetch---2');
      _key = _key + JSON.stringify(_params);
    }
    const _map = useProjectConfig.getOptionsMap;
    if (_key && _map[_key]) {
      options.value = JSON.parse(JSON.stringify(_map[_key]));
      return Promise.resolve(JSON.parse(JSON.stringify(options.value)));
    }

    api(_params).then((res) => {
      let _data = res.data;
      if (!Array.isArray(_data) && Object.hasOwnProperty.call(_data, 'list')) {
        _data = res.data?.list;
      }
      if (_data?.length > 0 || fn) {
        options.value = fn ? fn(_data) : toLabelValueOptions(_data, { label: label, value: value });
        if (_key) {
          useProjectConfig.setOptionsMap({
            ..._map,
            [_key]: JSON.parse(JSON.stringify(options.value)),
          });
          // console.log('_key-----then--2', _key, _map);
          // console.log(
          //   '_key-----thenuseProjectConfig.getOptionsMap',
          //   useProjectConfig.getOptionsMap,
          // );
        }
        return Promise.resolve(JSON.parse(JSON.stringify(options.value)));
      }
    });
  }
  // console.log("paramsConfig----",paramsConfig,params);

  if (paramsConfig?.immediate) {
    fetch();
  }
  // onMounted(() => {
  //   fetch();
  // });
  // 参数变化重新获取
  if (params && isRef(params)) {
    watch(
      () => params,
      () => {
        // console.log('baseFetch', 'params', params);
        fetch();
      },
      { deep: true },
    );
  }
  // 添加对 getOptionsMap 的监听
  watch(
    () => useProjectConfig.getOptionsMap,
    (newMap) => {
      let _key = api.toString().match(regex)?.[1];
      const _params = isRef(params) ? unref(params) : params;
      // 如果有参数
      if (params && JSON.stringify(_params) != '{}') {
        _key = _key + JSON.stringify(_params);
      }

      if (_key && newMap[_key] && options.value.length === 0) {
        options.value = JSON.parse(JSON.stringify(newMap[_key]));
      }
    },
    { deep: true },
  );
  return {
    options,
    fetch,
  };
}

// currency
// export function useCurrency() {
//   return baseFetch({ api: getCurrency }, { option: { label: 'currency', value: 'currency' } });
// }
// checkCode
// export function useCheckCode() {
//   return baseFetch({ api: getCheckCode }, { option: { label: 'checkCode', value: 'checkCode' } });
// }

// userInfo
export function useUserInfo() {
  return baseFetch(
    { api: getUserInfo },
    {
      option: { label: 'label', value: 'value' },
      fn: (data: any) => {
        return toLabelValueOptions(data?.product, { label: 'label', value: 'value' });
      },
    },
  );
}

// account
export function useAccount() {
  return baseFetch({ api: getUserRelAccounts }, { option: { label: 'label', value: 'value' } });
}

// symbolSelect TODO 树结构数据需优化
export function useSymbolSelect(params?: any) {
  return baseFetch(
    { api: getMonitorSymbolSelect, params },
    { option: { label: 'label', value: 'value' } },
  );
}
// symbolSelect-期货 TODO 树结构数据需优化
export function useSymbolFutureSelect(params?: any) {
  return baseFetch(
    { api: getFutureTqSymbolInfo, params },
    { option: { label: 'label', value: 'value' } },
  );
}

// Symbol TODO 只支持历史订单-资金流水使用
// export function useSymbol(params?: any) {
//   return baseFetch(
//     { api: getMonitorSymbol, params },
//     { option: { label: 'symbol', value: 'symbol' } },
//   );
// }
// 风控- symbol c初次使用在产品-风险处理-单边平仓功能
export function useSymbolRisk(params?: any) {
  return baseFetch(
    { api: getExecutionTasksSymbols, params },
    { option: { label: 'symbol', value: 'symbol' } },
  );
}
// export function useFmonitorSymbol(params?: any) {
//   return baseFetch(
//     { api: getFmonitorSymbol, params },
//     { option: { label: 'symbol', value: 'symbol' } },
//   );
// }

// mt5-symbol
// export function useMt5Symbol(params?: any, paramsConfig?: ParamsConfig) {
//   return baseFetch(
//     { api: getMt5Symbol, params },
//     { option: { label: 'name', value: 'name' } },
//     paramsConfig,
//   );
// }

/** 找到指定节点
 * arr 数据源
 * url 指定节点地址信息
 * options 节点基本信息
 * 返回指定节点
 * */
export function findNode(arr: any[], url: string | number[], options?: Options) {
  let _item,
    _arr = arr;
  for (let i = 0; i < url.length; i++) {
    _item = _arr.find((item) => (item[options?.value || 'value'] || item.value) == url[i]);
    if (_item?.children) {
      _arr = _item.children;
    }
  }
  return _item;
}
