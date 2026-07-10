<template>
  <div class="flex h-full">
    <BasicTable
      class="no-header-bg component-background"
      :scroll="scroll"
      @register="registerTable"
      body-padding=""
    />
    <div v-if="showDoubleSide" class="w-80 flex-shrink-0 px-4 ml-1 pt-2 component-background">
      <div class="pb-3">双边平仓</div>
      <div v-if="symbolOptions?.length > 0">
        <div
          v-for="item in symbolOptions"
          :key="item.value"
          class="flex justify-between leading-10 hover:bg-#fafafa"
        >
          <div>{{ item.label }}</div>
          <div>
            <GhostButton @click="handleClickDoubleSide(item)" size="small" color="error" noBorder>
              平仓
            </GhostButton>
          </div>
        </div>
      </div>
      <div v-else>
        <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" class="!pt-10" />
      </div>
    </div>
    <!-- 单边/双平仓-弹框 -->
    <ClosePositionSingleModal
      ref="closePositionSingleModal"
      @submit="onSubmit"
      :record="curCreate"
      :type="closePositionSingleType"
      :isSingle="isSingle"
    />
  </div>
</template>
<script lang="tsx" setup>
  import { BasicTable, useTable } from '@/components/Table';
  import { getPositionColumns } from '../data';
  import { computed, nextTick, reactive, ref, watch } from 'vue';
  import { useProjectConfigStore } from '@/store/modules/projectConfig';
  import { getExecutionPositions, postExecutionPositionsClose } from '@/api/risk/execution';
  import { useApiBasic } from '@/hooks/web/useApi';
  import { AccountType } from '@/views/account/detail/type';
  import { useSymbolRisk } from '@/utils/options/useBasicOptions';
  import ClosePositionSingleModal from './ClosePositionSingle.vue';
  import GhostButton from '@/components/Button/src/GhostButton.vue';
  import { Empty } from 'ant-design-vue';

  const emits = defineEmits(['success']);
  const props = defineProps({
    account: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    product: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    showDoubleSide: {
      type: Boolean,
      default: true,
    },
  });
  const scroll = {
    x: 'max-content-width',
    y: 600,
  };

  const visibleGoogle = ref(false); // google验证码
  const refGoogle = ref();
  let curParams = {};
  // 单边平仓参数
  const curCreate = ref<any>();
  const closePositionSingleType = ref<any>();
  const closePositionSingleModal = ref<any>();

  // 双边平仓基础配置
  const imputProps = computed(() => {
    const _config: any = {
      placeholder: '请输入平仓数量',
      precision: undefined,
    };
    // if (curSymbol.value && Object.prototype.hasOwnProperty.call(curSymbol.value, 'total')) {
    //   _config.precision = (curSymbol.value?.total?.toString().split('.')[1] || '').length;
    // }
    console.log('双边平仓基础配置', _config, curSymbol);
    if (curSymbolConfig.value) {
      _config.precision = (curSymbolConfig.value?.lotSize?.toString().split('.')[1] || '').length;
      _config.step = curSymbolConfig.value?.lotSize * 1;
    }
    return _config;
  });
  const { options: symbolOptionsBasic } = useSymbolRisk();

  const dataSource = ref([]);
  const [registerTable, { setLoading, setTableData }] = useTable({
    useSearchForm: false,
    immediate: false,
    bordered: true,
    dataSource: dataSource,
    beforeFetch: (params) => {
      params.checkCode = props.account?.checkCode;
      // params.mode = 'realtime';
    },
    columns: getPositionColumns((data: any) => {
      console.log('getPositionColumns====', data);

      if (data?.type == 'symbol') {
        onSubmit(data);
      } else if (data?.type == 'single') {
        isSingle.value = true;
        openClosePositionSingleModal({
          type: data?.record?.platform,
          data: data?.record,
        });
      }
    }),
    showIndexColumn: false,
  });
  // const expandedRowKeys = ref(['沪金合计']);
  // const [registerTableSh, { setLoading: setLoadingSh, setTableData: setTableDataSh }] = useTable({
  //   api: getFutureStrategyPosition,
  //   columns: getPositionColumnsSh((data: any) =>
  //     openClosePositionSingleModal({ type: AccountType.SHFE, data }),
  //   ),
  //   showIndexColumn: false,
  //   useSearchForm: false,
  //   immediate: false,
  //   rowKey: 'exchange',
  //   expandedRowKeys: expandedRowKeys,
  // });
  const isSingle = ref(false); // 是否是单边平仓
  // 双边平仓输入框
  const sliderInputRef = ref();
  const symbolOptions = computed(() => {
    return filterOnlyMixed(dataSource.value);
  });
  const searchInfo = reactive({
    symbol: undefined,
  });
  // 双边平仓-持仓表格-标的数据
  const curSymbol = computed(() => {
    return symbolOptions.value.find((item) => item.value == searchInfo.symbol);
  });
  // 双边平仓-标的基本配置信息
  const curSymbolConfig = computed(() => {
    return symbolOptionsBasic.value?.find((item) => item.symbol == searchInfo.symbol);
  });

  const useProjectConfig = useProjectConfigStore();

  function onSubmit(params: any) {
    console.log('平仓操作', params, props.account);
    switch (params.type) {
      case 'single':
        // 单边参数处理
        onSubmitSingle(params);
        // visibleGoogle.value = true;
        // console.log('curParams=====', curParams);
        handleClickConfirm(curParams);
        break;
      case 'double':
        // 双边参数处理
        onSubmitSlider(params);
        handleClickConfirm(curParams);
        break;
      case 'symbol':
        dealHandicap(dataSource.value[params.value]);
        break;
    }
  }
  watch(
    () => props.account,
    () => {
      if (props.account?.checkCode) {
        sliderInputRef.value?.reset();
        searchInfo.symbol = undefined;
        nextTick(() => {
          initData();
        });
      }
    },
    { immediate: true },
  );

  async function initData() {
    console.log('beforeFetch-------', props);
    setLoading(true);

    let _apiFn: any = getExecutionPositions;
    let _params: any = {
      checkCode: props.account?.checkCode,
      platform: props.account?.platform,
      productId: props.product?.id,
    };
    // if (props.account?.platform == AccountType.BALANCE) {
    //   _apiFn = getExecutionPositions;
    //   setLoading(true);
    // } else if (props.account?.platform == AccountType.SHFE) {
    //   _params.strategyCode = props.account?.strategy_code;
    //   _apiFn = getFutureStrategyPosition;
    //   setLoadingSh(true);
    // } else if (props.account?.platform == AccountType.MT5) {
    //   _apiFn = getMt5positions;
    // }
    try {
      dataSource.value = [];
      const res = await _apiFn(_params);
      if (res?.retCode == 0) {
        dataSource.value = res?.data || [];
        setTableDataAll(res?.data || []);
        if (dataSource.value.length) {
          dealHandicap(dataSource.value[0]);
        }
        // console.log('dataSourc-------', dataSource.value);
      }
    } finally {
      setLoading(false);
      // if (props.account?.platform == AccountType.BALANCE) {
      //   setLoading(false);
      // } else if (props.account?.platform == AccountType.SHFE) {
      //   setLoadingSh(false);
      // } else if (props.account?.platform == AccountType.MT5) {
      //   console.log('MT5 不需要 loading');
      // }
    }
  }
  // 表格数据单独赋值处理
  function setTableDataAll(data: any[]) {
    setTableData(data);
    // if (props.account?.platform == AccountType.BALANCE) {
    //   setTableData(data);
    // } else if (props.account?.platform == AccountType.SHFE) {
    //   setTableDataSh(data);
    // } else if (props.account?.platform == AccountType.MT5) {
    //   console.log('MT5 不需要 loading222');
    // }
  }
  // 盘口参数
  function dealHandicap(params: any) {
    let _symbol;
    if (
      props.account?.platform == AccountType.BALANCE ||
      props.account?.platform == AccountType.MT5
    ) {
      _symbol = [params?.exchange, params?.category, params?.symbol];
      useProjectConfig.setCurrentSymbolInfo(_symbol);
    } else if (props.account?.platform == AccountType.SHFE) {
      // 国内盘口暂时不需要传入参数
      console.log('dealHandicap====', params);
      useProjectConfig.setCurrentSymbolFutureInfo(params.symbol);
      // _symbol = [];
    } else {
      // useProjectConfig.setCurrentSymbolFutureInfo('');
    }
  }
  // 统一调用接口
  function handleClickConfirm(params: any) {
    const _params = { ...curParams, ...params };
    console.log('handleClickConfirm---', _params);

    // 不同平台调用不同的平仓接口
    // postExecutionPositionsCloseFn(_params);
    const _apiFn = postExecutionPositionsClose;
    // let _apiFn: any;
    // if (isSingle.value) {
    //   // if (props.account?.platform == AccountType.BALANCE) {
    //   _apiFn = postExecutionPositionsClose;
    //   // } else if (props.account?.platform == AccountType.SHFE) {
    //   //   _apiFn = postFutureTqClosePosition;
    //   // } else if (props.account?.platform == AccountType.MT5) {
    //   //   // _apiFn = useApiBasic(getMt5positions).apiFn;
    //   // }
    // } else {
    //   if (props.account?.platform == AccountType.BALANCE) {
    //     _apiFn = postExecutionPositionsClose;
    //   } else if (props.account?.platform == AccountType.SHFE) {
    //     _apiFn = postFutureStrategyRisk;
    //   } else if (props.account?.platform == AccountType.MT5) {
    //     // _apiFn = useApiBasic(getMt5positions).apiFn;
    //   }
    // }

    useApiBasic({
      apiFn: _apiFn(_params),
      successFn() {
        initData();
        emits('success');
      },
      finallyFn() {
        // visibleGoogle.value = false;
        closePositionSingleModal.value?.openModal(false);
      },
    });
  }
  function filterOnlyMixed(positions) {
    // console.log('positions======', positions, props.account);

    let result: any = [];
    if (props.account?.platform == AccountType.SHFE) {
      result = filterOnlyMixedSh(positions);
    } else if (props.account?.platform == AccountType.BALANCE) {
      result = filterOnlyMixedLinear(positions);
    }
    return result;
  }
  // 筛选仅包含 spot 和 linear 的组合
  function filterOnlyMixedLinear(positions) {
    // 按 symbol 分组
    const grouped = positions.reduce((map, pos) => {
      if (!map[pos.symbol]) {
        map[pos.symbol] = [];
      }
      map[pos.symbol].push(pos);
      return map;
    }, {});

    const result: any = [];

    // 遍历每组 symbol
    for (const [symbol, group] of Object.entries(grouped)) {
      const hasSpot = group.some((item) => item.category === 'spot');
      const hasLinear = group.some((item) => item.category === 'linear');

      // 仅当同时存在 spot 和 linear 时，才保留 linear 的那条
      if (hasSpot && hasLinear) {
        const linearPos = group.find((item) => item.category === 'linear');
        if (linearPos) {
          result.push({ ...linearPos, value: symbol, label: symbol, total: linearPos.size });
        }
      }
      // 如果只有 spot 或只有 linear → 不保留（跳过）
    }

    return result;
  }
  // 筛选沪金内标的组合
  function filterOnlyMixedSh(positions) {
    return (
      positions?.map((item) => {
        return {
          value: item?.symbol,
          label: item?.symbol,
          total: item?.size,
          precision: 0,
          record: item,
        };
      }) || []
    );
  }
  // 单边平仓参数处理
  function onSubmitSingle(params: any) {
    isSingle.value = true;
    if (props.account?.platform == AccountType.BALANCE) {
      curParams = {
        ...params,
        platform: props.account?.platform,
        productId: props.product?.id,
        accountId: props.account?.accountId,
        symbol: params.record?.symbol,
        side: params.record?.side == 'Buy' ? 'Sell' : 'Buy',
        orderType: 'Market',
        category: params.record?.category,
        quantity: params.quantity,
        isLeverage: 0,
        reduceOnly: true,
        timeInForce: params.timeInForce,
        percentage: params.percentage,
        closeType: 'single_side', // 单边平仓,double_side 双边平仓
      };
    } else if (props.account?.platform == AccountType.SHFE) {
      curParams = {
        ...params,
        accountId: props.account?.accountId,
        productId: props.product?.id,
        symbol: params.record?.symbol,
        side: params.record?.side == 'Buy' ? 'Sell' : 'Buy',
        category: params.record?.category,
        closeType: 'single_side', // 单边平仓,double_side 双边平仓
        offset: 'CLOSETODAY',
        platform: props.account?.platform,
      };
    } else if (props.account?.platform == AccountType.MT5) {
      curParams = {
        ...params,
        accountId: props.account?.accountId,
        productId: props.product?.id,
        symbol: params.record?.symbol,
        side: params.record?.side == 'Buy' ? 'Sell' : 'Buy',
        category: params.record?.category,
        closeType: 'single_side', // 单边平仓,double_side 双边平仓
        platform: props.account?.platform,
        position: params.record?.ticket,
      };
    }

    console.log('单边平仓', curParams, params);
  }
  // 双边平仓点击
  function handleClickDoubleSide(params: any) {
    isSingle.value = false;
    searchInfo.symbol = params.value;
    // console.log('handleClickDoubleSide----', params, curSymbol);
    // 双边平仓参数向单边平仓参数转换
    openClosePositionSingleModal({
      type: props.account?.platform,
      data: {
        volume: curSymbol.value?.total || 100,
        size: curSymbol.value?.total || 100,
        symbol: curSymbol.value?.symbol || curSymbol.value?.label,
      },
    });
  }
  // 双边平仓参数处理
  function onSubmitSlider(params: any) {
    isSingle.value = false;
    if (props.account?.platform == AccountType.BALANCE) {
      curParams = {
        ...params,
        platform: props.account?.platform,
        productId: props.product?.id,
        accountId: props.account?.accountId,
        symbol: curSymbol.value?.symbol,
        side: curSymbol.value?.side == 'Buy' ? 'Sell' : 'Buy',
        orderType: 'Market',
        category: curSymbol.value?.category,
        // quantity: params,
        isLeverage: 0,
        reduceOnly: true,
        // timeInForce: 'IOC',
        closeType: 'double_side', // 双边平仓
      };
    } else if (props.account?.platform == AccountType.SHFE) {
      curParams = {
        ...params,
        accountId: props.account?.accountId,
        productId: props.product?.id,
        symbol: searchInfo.symbol,
        side: 'Sell',
        category: props.account?.platform,
        closeType: 'double_side', // 双边平仓
        offset: 'CLOSETODAY',
        platform: props.account?.platform,
        // checkCode: props.account?.checkCode,
        // strategyCode: props.account?.strategy_code,
        // quantity: params.quantity,
      };
    } else if (props.account?.platform == AccountType.MT5) {
      curParams = {
        ...params,
        accountId: props.account?.accountId,
        productId: props.product?.id,
        symbol: params.record?.symbol,
        side: 'Sell',
        category: params.record?.category,
        closeType: 'double_side', // 单边平仓,double_side 双边平仓
        platform: props.account?.platform,
        position: params.record?.ticket,
      };
    }
    console.log('双边平仓', params, curParams);
    // visibleGoogle.value = true; // google 验证
  }
  function openClosePositionSingleModal(params: any) {
    closePositionSingleType.value = params.type;
    curCreate.value = params.data;
    closePositionSingleModal.value?.openModal(params);
  }
</script>
