/**
 * 风险管理相关的自定义Hook
 * 用于处理和计算与风险相关的逻辑和数据
 */
import { getProductRisk, getAccountData } from '@/api/risk/monitoring';
// import { getStrategyRiskOverview } from '@/api/future';
import { getTotalLeverageRatio, getPositionsBalance } from '@/api/risk/execution';
import { useUserStore } from '@/store/modules/user';
import { ref, computed, reactive, nextTick, watch, onMounted, type Ref } from 'vue';
import { AccountType } from '@/views/account/detail/type';
import { useIntervalCustom } from '@/hooks/event/useIntervalCustom';
import { usdDataExchange } from '@/hooks/core/useUsd2Cny';
import { getProductNavDrawdown, getProductNavShfeDrawdown } from '@/api/data/product';
import { getProductConfig, getAccountConfig } from '@/api/risk/settings';
import { watchDebounced } from '@vueuse/shared';

interface useRiskConfig {
  // 是否定时刷新
  isTiming?: boolean;
  // 每次刷新是否显示loading动画
  showLoading?: boolean;
}
const defaultConfig: useRiskConfig = {
  isTiming: false,
  showLoading: true,
};
export function useProductRisk(productId: any, config: useRiskConfig = defaultConfig) {
  const { start, stop, artificialStop } = useIntervalCustom(initData, {
    immediate: false,
    delay: 60000,
  });
  const isFirst = ref(true); // 是否是第一次
  const userStore = useUserStore();
  const userProducts = computed(() => userStore.getUserInfoAccount);
  // 产品-产品基本信息
  const product = computed(() => {
    return userProducts.value.find((item) => item.id == productId.value);
  });
  // 产品-展示数据
  const productSource = reactive<any>({
    hasRetracement: true, // 是否有回撤
    retracement: 0, // 资产净值回撤
    hasNavDrawdown: false, // 是否有原始净值回撤
    navDrawdown: 0, // 原始净值回撤
    navShfeDrawdown: 0, // 产品净值回撤
    drawdownProgressList: [],
    levelRatio: 0, // 总杠杆率
    levelRatioProgressList: [], // 总杠杆率进度条等级配置
    deltaBalance: 0, // Delta中性平衡-多头
    deltaBalanceShort: 0, // Delta中性平衡-空头
    hasTotalNetworthRatio: false, // 是否有净值/权益总资产净值比例
    cryptoTotalNetworthRatio: 0, // 净值总资产净值比例
    futuresTotalNetworthRatio: 0, // 期货总资产净值比例
    cryptoLeverageRatio: 0, // 海外杠杆率
    futuresLeverageRatio: 0, // 期货杠杆率
    mt5LeverageRatio: 0, // MT5杠杆率
  });
  // 汇率数据
  const { exchange } = usdDataExchange();
  // const exchange = ref();
  // 产品-帐号风险数据
  const dataSource = ref<any>([]);
  const loading = ref(false);

  async function getProductRiskFn() {
    loading.value = true;
    getProductRisk({ productCode: product.value?.value })
      .then((res) => {
        if (res.retCode == 0) {
          dataSource.value = res.data?.data || [];
          dataSource.value.forEach((item: any) => {
            getAccountConfigFn({ accountId: item.accountId }, item);
          });
          // console.log('getProductRisk=====', dataSource);
        }
      })
      .finally(() => {
        nextTick(() => {
          loading.value = false;
          isFirst.value = false;
        });
      });
  }
  function initData() {
    if (isFirst.value) {
      loading.value = true;
    } else {
      if (config?.showLoading) {
        !config?.isTiming && (loading.value = true);
      }
    }
    getProductRiskFn();
    getTotalLeverageRatioFn();
    getPositionsBalanceFn();
    // getProductNavDrawdownFn();
    getProductNavShfeDrawdownFn();
    // 总杠杆率-分级配置获取
    getProductConfigFn();
    // if (hasNavDrawdown()) {
    //   productSource.hasNavDrawdown = true;
    //   getProductNavShfeDrawdownFn();
    // }
    // console.log('product====', product);
  }
  function getTotalLeverageRatioFn() {
    getTotalLeverageRatio({ productCode: product.value?.value }).then((res) => {
      if (res.retCode == 0) {
        productSource.levelRatio = (res.data?.totalLeverageRatio * 100).toFixed(2);
        productSource.cryptoLeverageRatio = (res.data?.cryptoLeverageRatio * 100).toFixed(2);
        productSource.futuresLeverageRatio = (res.data?.futuresLeverageRatio * 100).toFixed(2);
        productSource.mt5LeverageRatio = (res.data?.mt5LeverageRatio * 100).toFixed(2);
        // console.log('getTotalLeverageRatioFn----', res.data);
      }
    });
  }
  // 中性平衡
  function getPositionsBalanceFn() {
    getPositionsBalance({ productId: productId.value }).then((res) => {
      if (res.retCode == 0) {
        if (res.data?.long || res.data?.short) {
          const _total = res.data?.long + res.data?.short;
          if (_total) {
            productSource.deltaBalance = ((res.data?.long / _total) * 100).toFixed(2);
            productSource.deltaBalanceShort = ((res.data?.short / _total) * 100).toFixed(2);
          }
        }
      }
    });
  }
  // 净值/权益总资产净值比例计算
  function getNetworthRatioFn() {
    let _futuresTotalNetworth = 0;
    let _cryptoTotalNetworth = 0;
    const _hasTotalNetworthRatio = {
      [AccountType.SHFE]: false,
      [AccountType.MT5]: false,
    };
    const _totalNetworth = dataSource.value?.reduce((sum: number, item: any) => {
      // console.log('item---', item);
      let _equity = 0;
      if (item?.platform == AccountType.SHFE) {
        _hasTotalNetworthRatio[AccountType.SHFE] = true;
        _equity = item?.balance * 1 || 0;
        _futuresTotalNetworth += _equity;
      } else if (item?.platform == AccountType.MT5 && exchange.value?.rate) {
        _hasTotalNetworthRatio[AccountType.MT5] = true;
        _equity = item?.equity * exchange.value?.rate || 0;
        _cryptoTotalNetworth += _equity;
      }
      return sum + _equity;
    }, 0);
    if (_hasTotalNetworthRatio[AccountType.SHFE] && _hasTotalNetworthRatio[AccountType.MT5]) {
      productSource.hasTotalNetworthRatio = true;
    }
    if (_totalNetworth > 0) {
      productSource.futuresTotalNetworthRatio = (
        (_futuresTotalNetworth / _totalNetworth) *
        100
      ).toFixed(2);
      productSource.cryptoTotalNetworthRatio = (
        (_cryptoTotalNetworth / _totalNetworth) *
        100
      ).toFixed(2);
    }
    // console.log('_hasTotalNetworthRatio======', _hasTotalNetworthRatio, productSource, exchange);
  }

  // 获取账户当前实时沪金交易时间段回测率
  function getProductNavShfeDrawdownFn() {
    const _params = {
      product_code: product.value?.value,
    };
    getProductNavShfeDrawdown(_params).then((res) => {
      // console.log('getProductNavShfeDrawdown----', res);
      if (res?.retCode == 0) {
        productSource.navShfeDrawdown = res?.data?.drawdown_rate_percent || 0;
      }
    });
  }

  // 产品策略因子配置
  function getProductConfigFn() {
    getProductConfig({
      productId: productId.value,
    }).then((res) => {
      if (res.retCode == 0) {
        const _arr = res?.data || [];
        // 分级配置-代码 prodTotalLeverageRatio
        const _item = _arr?.find((item: any) => item.factorCode == 'prodTotalLeverageRatio');
        if (_item) {
          productSource.levelRatioProgressList = [
            {
              value: _item?.level1threshold,
              grade: 'level1',
            },
            {
              value: _item?.level2threshold,
              grade: 'level2',
            },
            {
              value: _item?.level3threshold,
              grade: 'level3',
            },
            {
              value: _item?.level4threshold,
              grade: 'level4',
            },
            {
              value: _item?.level5threshold,
              grade: 'level5',
            },
          ];
        }
        // 分级配置-代码 drawdown
        const _drawdown = _arr.find((item) => item.factorCode == 'SHFEdrawdown');
        if (_drawdown) {
          productSource.drawdownProgressList = [
            {
              value: _drawdown?.level1threshold * 100,
              grade: 'level1',
            },
            {
              value: _drawdown?.level2threshold * 100,
              grade: 'level2',
            },
            {
              value: _drawdown?.level3threshold * 100,
              grade: 'level3',
            },
            {
              value: _drawdown?.level4threshold * 100,
              grade: 'level4',
            },
            {
              value: _drawdown?.level5threshold * 100,
              grade: 'level5',
            },
          ];
        }
      }
    });
  }

  onMounted(() => {
    initData();
    if (config?.isTiming) {
      start();
    }
  });

  watchDebounced(
    () => [dataSource.value, exchange.value],
    () => {
      getNetworthRatioFn();
    },
    { deep: true, debounce: 1000 },
  );
  watch(
    () => [
      dataSource.value,
      productSource.mt5LeverageRatio,
      productSource.futuresLeverageRatio,
      productSource.cryptoLeverageRatio,
    ],
    () => {
      if (
        dataSource.value?.length > 0 &&
        productSource.mt5LeverageRatio &&
        productSource.futuresLeverageRatio &&
        productSource.cryptoLeverageRatio
      ) {
        setCardLevelRatio();
      }
    },
  );

  // 卡片杠杆率
  function setCardLevelRatio() {
    dataSource.value?.forEach((item: any) => {
      if (item.platform == AccountType.MT5) {
        item['leverRatio'] = productSource.mt5LeverageRatio;
      } else if (item.platform == AccountType.SHFE) {
        item['leverRatio'] = productSource.futuresLeverageRatio;
      } else if (item.platform == AccountType.BALANCE) {
        item['leverRatio'] = productSource.cryptoLeverageRatio;
      }
    });
    console.log('setCardLevelRatio------', dataSource.value);
  }
  function refresh() {
    initData();
  }
  return {
    product,
    dataSource,
    loading,
    productSource,
    refresh,
    artificialStop,
    isFirst,
  };
}
interface AccountConfig {
  checkCode: string;
  platform: AccountType;
}
export function useAccountRisk(params: Ref<AccountConfig>, config: useRiskConfig = defaultConfig) {
  const { start, stop, artificialStop } = useIntervalCustom(initData, {
    immediate: false,
    delay: 6000,
  });
  const loading = ref(false);
  const isFirst = ref(true); // 是否是第一次
  // 产品-帐号风险数据
  const dataSource = ref<any>([]);
  const userStore = useUserStore();
  const userProducts = computed(() => userStore.getUserInfoAccount);
  const account = ref();

  watch(
    () => [userProducts, params.value],
    () => {
      userProducts.value?.forEach((product: any) => {
        const _item = product.children?.find((account: any) => {
          return (
            account.checkCode == params.value.checkCode && account.platform == params.value.platform
          );
        });
        if (_item) {
          account.value = _item;
        }
      });
    },
    { deep: true, immediate: true },
  );
  async function getAccountDataFn() {
    loading.value = true;
    getAccountData({ checkCode: params.value?.checkCode, platform: params.value?.platform })
      .then((res) => {
        if (res.retCode == 0) {
          dataSource.value = res.data || [];
          dataSource.value.forEach((item: any) => {
            getAccountConfigFn({ accountId: item.accountId }, item);
          });
          // console.log('getProductRisk=====', dataSource);
        }
      })
      .finally(() => {
        nextTick(() => {
          loading.value = false;
          isFirst.value = false;
        });
      });
  }
  function initData() {
    if (isFirst.value) {
      loading.value = true;
    } else {
      if (config?.showLoading) {
        !config?.isTiming && (loading.value = true);
      }
    }
    getAccountDataFn();
  }
  onMounted(() => {
    initData();
    if (config?.isTiming) {
      start();
    }
  });
  function refresh() {
    initData();
  }
  return {
    loading,
    dataSource,
    account,
    isFirst,
    refresh,
    artificialStop,
  };
}

// 产品-账号-分级配置-卡片
function getAccountConfigFn(params: any, data: any) {
  getAccountConfig({ accountId: params.accountId }).then((res) => {
    if (res.retCode == 0) {
      let _item;
      if (!res?.data || res?.data?.length == 0) return;
      if (data?.platform == AccountType.SHFE) {
        // 分级配置-代码 futures-riskRatio
        _item = res?.data?.find((item: any) => item.factorCode == 'riskRatio');
      } else if (data?.platform == AccountType.MT5) {
        // 分级配置-代码 MT5-marginLevel
        _item = res?.data?.find((item: any) => item.factorCode == 'marginLevel');
      }
      data['levelList'] = [
        {
          value: _item?.level1threshold,
          grade: 'level1',
        },
        {
          value: _item?.level2threshold,
          grade: 'level2',
        },
        {
          value: _item?.level3threshold,
          grade: 'level3',
        },
        {
          value: _item?.level4threshold,
          grade: 'level4',
        },
        {
          value: _item?.level5threshold,
          grade: 'level5',
        },
      ];
    }
  });
}
