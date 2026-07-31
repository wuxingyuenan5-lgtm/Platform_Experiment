<!-- TODO 目前仅支持另类 -->
<template>
  <SimpleContainer title="仓位分布">
    <template #action>
      <Select v-model:value="currency" class="w-20" size="small" :options="unitOptions" />
    </template>
    <div :class="['component-background p-3', dataSoure?.length == 0 && 'overflow-hidden']">
      <Spin :spinning="loading">
        <div ref="chartRef" :style="{ width, height }">
          <div v-if="dataSoure?.length == 0" class="flex items-center justify-center h-full">
            <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          </div>
        </div>
      </Spin>
    </div>
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import { nextTick, ref, Ref, watch } from 'vue';
  // import { getExecutionAllPositions } from '@/api/risk/execution';
  import { useECharts } from '@/hooks/web/useECharts';
  import { formateNumStr, formatNumberWithUnit } from '@/utils/formate';
  import { Empty, Spin, Select } from 'ant-design-vue';
  import { AccountType } from '@/views/account/detail/type';
  import { platformOptions, unitOptions } from '@/utils/options/basicOptions';

  const props = defineProps({
    width: {
      type: String as PropType<string>,
      default: '100%',
    },
    height: {
      type: String as PropType<string>,
      default: '376px',
    },
    record: {
      type: Array as PropType<any>,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
  });
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, getInstance } = useECharts(chartRef as Ref<HTMLDivElement>);
  const dataSoure = ref<any>([]);
  // 当前币种
  const currency = ref('CNY');
  let currencyList = new Set();
  // const loading = ref(false);
  const colorList = ['#F55458', '#5BB86F', '#2C97EB', '#FFD54F', '#F57C00'];
  watch(
    () => props.record,
    (cur) => {
      if (cur?.length > 0) {
        dealData(cur);
        initChart();
      }
    },
    { immediate: true },
  );
  watch(currency, () => {
    if (props.record.length > 0) {
      dealData(props.record);
      initChart();
    }
  });

  function initChart() {
    const _dimensions = ['product', ...Array.from(currencyList)];
    const prefixColorMap = {};
    // 按前缀（-前面的部分）排序，使相同前缀的排在一起
    const _currencyList = Array.from(currencyList).sort((a, b) => {
      const prefixA = a.split('-')[0];
      const prefixB = b.split('-')[0];
      return prefixA.localeCompare(prefixB);
    });
    // console.log('currencyList----', _dimensions);
    const _series: any = _currencyList.map((item, i) => {
      const prefix = item?.split('&')[0]; // 提取前缀，如 BTC

      // 如果这个前缀还没有分配颜色，就从 colorList 中取一个
      if (!prefixColorMap[prefix]) {
        // 取一个颜色，可以用 Object.keys 的长度来模拟“第几个新前缀”
        const prefixIndex = Object.keys(prefixColorMap).length;
        prefixColorMap[prefix] = colorList[prefixIndex % colorList.length]; // 循环使用颜色
      }

      return {
        type: 'bar',
        stack: 'stack1', // 所有设置相同 stack 名称的系列会堆叠在一起
        encode: { x: item, y: 'product' }, // 映射：x轴用 product，y轴用 2023 列
        itemStyle: { color: prefixColorMap[prefix] },
        barMaxWidth: '30%',
        barMinHeight: 1,
      };
    });
    setOptions({
      dataset: {
        dimensions: _dimensions,
        source: dataSoure.value,
      },
      tooltip: {
        show: true,
        trigger: 'axis',
        axisPointer: {
          // Use axis to trigger tooltip
          type: 'shadow', // 'shadow' as default; can also be 'line' or 'shadow'
        },
        formatter: function (params: any, ticket) {
          const _data = params?.[0]?.data;
          const _items: any = [];
          let _total = 0;
          Object.entries(_data).forEach(([key, value]) => {
            if (key != 'product') {
              const _keyArr = key.split('&');
              _total += parseFloat(value || 0);
              _items.push({
                category: _keyArr?.[1],
                name: _keyArr?.[0],
                side: _keyArr?.[2] || '',
                value: value,
              });
            }
          });
          const _itemsSort = _items.sort((a, b) => {
            const prefixA = a?.name;
            const prefixB = b?.name;
            return prefixA.localeCompare(prefixB);
          });
          const _arr = _data?.product.split('&');
          const _platform =
            platformOptions.find((itemp) => itemp.value == _arr?.[0])?.label || _arr?.[0];
          return `<div class='min-w-[200px]'>
          <div>${_platform}-${_arr?.[1]}</div>
            ${_itemsSort
              ?.map((item: any, i) => {
                const _isSpot = item.category == 'spot';
                return `<div style="display: flex; justify-content: space-between; align-items: center;">
                <div class='mr-4'>
                  ${params?.[i]?.marker}${item.name}-<span class="${
                    _isSpot ? 'text-[#2c97ebff]' : 'text-[#eb6e2cff]'
                  }">${_isSpot ? '现货' : '期货'}</span><span class="${
                    item.side == 'Buy' ? 'text-[#22B573]' : 'text-[#C1272D]'
                  }">${item.side == 'Buy' ? '-买入' : item.side == 'Sell' ? '-卖出' : ''}</span> 
                </div>
                <div>
                  <span>${formateNumStr(item.value, { decimals: 2, keepZero: true })}</span>
                  <span>${((item.value / _total) * 100).toFixed(2)}%</span>
                </div>
              </div>`;
              })
              .join('')}
          </div>`;
        },
      },
      grid: {
        containLabel: true,
        left: 0,
        bottom: 0,
        top: 0,
      },
      xAxis: {
        type: 'value',
        axisLabel: {
          formatter: function (value: any) {
            return formatNumberWithUnit(value);
          },
        },
      },
      yAxis: {
        type: 'category',
        axisTick: {
          show: false,
        },
        axisLabel: {
          formatter: function (value: any) {
            const _arr = value.split('&');
            const _platform =
              platformOptions.find((item) => item.value == _arr?.[0])?.label || _arr?.[0];
            return `${_platform}\n${_arr?.[1]}`;
          },
        },
      },
      series: _series,
    });
  }
  function dealData(data: any) {
    // 产品归类
    const _obj = new Map();
    const _keyUnit = currency.value == 'CNY' ? 'positionValueCNY' : 'positionValueUSD';

    data?.forEach((item: any) => {
      let _key = (item.currency || item.symbol) + '&' + item.category;
      if (item.platform == AccountType.MT5) {
        _key += '&' + item.side;
      }
      // console.log('_key----', _key);
      const __objKey = item.platform + '&' + item.checkCode;
      currencyList.add(_key);
      if (!_obj.has(__objKey)) {
        _obj.set(__objKey, {
          product: __objKey,
          [_key]: item[_keyUnit],
        });
      } else {
        //
        // console.log('_obj.get(__objKey)[_key]===', _obj.get(__objKey)[_key], _key);
        if (item.platform == AccountType.MT5) {
          _obj.get(__objKey)[_key] = (_obj.get(__objKey)[_key] || 0) + item[_keyUnit];
        } else {
          _obj.get(__objKey)[_key] = item[_keyUnit];
        }
      }
    });
    // console.log('_obj----', _obj);

    dataSoure.value = Array.from(_obj.values());
  }
</script>
