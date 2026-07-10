<template>
  <SimpleContainer title="净值曲线" :paragraph="{ rows: 13 }">
    <!-- <template #action>
      <div class="flex gap-2">
        <Select
          :disabled="loadingContent"
          v-model:value="searchInfo.tradingTimeFilter"
          class="w-25"
          size="small"
          :options="tradingTimeFilterOptions"
        />
        <Select
          :disabled="loadingContent"
          v-model:value="searchInfo.period"
          class="w-20"
          size="small"
          :options="timeOptions3"
        />
        <Segmented
          :disabled="loadingContent"
          class="component-background"
          v-model:value="searchInfo.is_dynamic"
          size="small"
          :options="netValueTypeOptions"
        />
      </div>
    </template> -->
    <div class="component-background overflow-hidden">
      <Spin :spinning="loadingContent">
        <div :style="{ height }">
          <div
            v-if="!chartData || chartData?.length == 0"
            class="h-full flex justify-center items-center"
          >
            <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          </div>
          <div
            ref="chartRef"
            :style="{ width, height: !chartData || chartData?.length == 0 ? '1px' : height }"
          >
          </div>
        </div>
      </Spin>
    </div>
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { ref, reactive, onMounted, watch, type Ref } from 'vue';
  import { SimpleContainer } from '@/components/Container';
  import { useECharts } from '@/hooks/web/useECharts';
  import { Spin, Empty, Select, Segmented } from 'ant-design-vue';
  import { getProductNavplatformNetValueList } from '@/api/data/product';
  import {
    timeOptions3,
    tradingTimeFilterOptions,
    netValueTypeOptions,
  } from '@/utils/options/basicOptions';
  import { watchDebounced } from '@vueuse/shared';

  const loadingContent = ref(false);
  const props = defineProps({
    width: {
      type: String as PropType<string>,
      default: '100%',
    },
    height: {
      type: String as PropType<string>,
      default: '400px',
    },
    account: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
  });
  const searchInfo = reactive({
    // period: 'D',
    // tradingTimeFilter: 1,
    // is_dynamic: 1,
  });
  const chartData = ref([]);
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);

  function initChart() {
    setOptions({
      dataset: {
        source: chartData.value,
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'line',
        },
      },
      dataZoom: [
        {
          type: 'inside',
        },
        {
          type: 'slider',
        },
      ],
      legend: {
        top: 20,
        show: true,
        icon: 'rect',
        itemWidth: 12,
        itemHeight: 2,
        itemGap: 36,
        // textStyle: {
        // color: '#D1D4DCFF',
        // },
      },
      grid: {
        left: '1%',
        right: '1%',
        bottom: '60px',
        containLabel: true,
      },
      xAxis: [
        {
          type: 'category',
          // data: _dataX,
          axisLine: {
            lineStyle: {
              color: '#0000001A', // #fff 0.2
              type: [5, 2],
              dashOffset: 3,
            },
          },
          axisLabel: {
            overflow: 'break',
            showMinLabel: chartData.value?.length < 4 ? true : false,
            color: '#000000A6', // x轴文本颜色
            // fontSize: 12,      // 文字大小
          },
          axisTick: {
            show: false,
          },
        },
      ],
      yAxis: [
        {
          type: 'value',
          name: '净值',
          scale: true,
          splitLine: {
            showMinLine: false,
            show: true,
            lineStyle: {
              color: '#000000', // #fff 0.2
              type: [2, 5],
              dashOffset: 5,
              opacity: 0.1,
            },
          },
          // min: 0,
        },
        // {
        //   type: 'value',
        //   name: '回撤（%）',
        //   max: 0,
        //   scale: true,
        //   splitLine: {
        //     show: false,
        //     lineStyle: {
        //       // color: '#5c5d65', // #fff 0.2
        //       type: [2, 5],
        //       dashOffset: 5,
        //     },
        //   },
        // },
      ],
      series: [
        {
          name: '净值',
          type: 'line',
          animation: false,
          smooth: true,
          symbol: chartData.value?.length > 1 ? 'none' : 'circle',
          lineStyle: {
            width: 1.5,
          },
          itemStyle: {
            color: '#C1272D',
          },
          markPoint: {
            label: {
              show: true,
              position: 'top',
              color: '#000',
            },
            emphasis: {
              disabled: true,
            },
            data: [
              {
                type: 'max',
                name: 'Max',
                symbolSize: 0, // 👈 关键兼容性补丁！
                label: {
                  color: '#C1272D',
                  formatter: 'max:{c}',
                },
              },
              {
                type: 'min',
                name: 'Min',
                label: {
                  color: '#22B573',
                  formatter: 'min:{c}',
                },
                symbolSize: 0, // 👈 关键兼容性补丁！
              },
            ],
          },
          encode: { x: 'created_at', y: 'unit_net_worth' },
        },
        // {
        //   name: '回撤',
        //   type: 'line',
        //   animation: false,
        //   smooth: true,
        //   symbol: chartData.value?.length > 1 ? 'none' : 'circle',
        //   yAxisIndex: 1,
        //   areaStyle: {},
        //   lineStyle: {
        //     width: 1.5,
        //   },
        //   itemStyle: {
        //     color: '#EDBD88',
        //   },
        //   encode: { x: 'created_at', y: 'current_drawdown' },
        // },
      ],
    });
    resize();
  }
  function getProductNavplatformNetValueListFn(params?: any) {
    loadingContent.value = true;

    const _params = {
      ...params,
    };
    getProductNavplatformNetValueList(_params)
      .then((res) => {
        if (res?.retCode == 0) {
          chartData.value =
            res?.data?.map((item) => {
              return {
                ...item,
                unit_net_worth: item.unit_net_worth.toFixed(4),
              };
            }) || [];
          initChart();
        }
      })
      .finally(() => {
        loadingContent.value = false;
      });
  }
  watch(
    () => props.account,
    (curV) => {
      if (curV && curV.value) {
        console.log('account------', props.account);

        getProductNavplatformNetValueListFn({
          checkCode: props.account?.checkCode,
          platform: props.account?.platform,
        });
      }
    },
    { immediate: true },
  );
  // watchDebounced(
  //   () => searchInfo,
  //   () => {
  //     getProductNavplatformNetValueListFn({ product_code: props.product.value, ...searchInfo });
  //   },
  //   { deep: true, debounce: 300 },
  // );
  // watch(
  //   () => searchInfo.is_dynamic,
  //   (cur) => {
  //     if (cur) {
  //       searchInfo.period = 'D';
  //     }
  //     timeOptions3.forEach((item) => {
  //       if (item.value == 'M') {
  //         item.disabled = cur;
  //       }
  //     });
  //   },
  // );
</script>
