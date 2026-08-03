<template>
  <SimpleContainer title="产品净值占比 ">
    <div class="component-background p-3">
      <div class="flex justify-between items-center w-full">
        <div class="flex gap-3 color-secondary text-xs">
          <div>汇率：{{ exchange?.rate }}</div>
          <div>更新时间：{{ exchange?.created_at }}</div>
        </div>
        <div>
          <Segmented
            :disabled="loading"
            v-model:value="curUnit"
            size="small"
            :options="unitOptions"
          />
        </div>
      </div>
      <Spin :spinning="loading">
        <div :style="{ height, paddingTop: '1px' }">
          <div v-if="list.length == 0 ? height : 0" class="flex items-center justify-center h-full">
            <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          </div>
          <div ref="chartRef" :style="{ width, height: list.length != 0 ? height : '1px' }"> </div>
        </div>
      </Spin>
    </div>
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import { ref, Ref, onMounted, computed, watch } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import { formateNumStr } from '@/utils/formate';
  import { Empty, Spin, Segmented } from 'ant-design-vue';
  // import { getCryptoProductProportion } from '@/api/risk/monitoring';
  import { useUserStore } from '@/store/modules/user';
  import { unitOptions } from '@/utils/options/basicOptions';
  import { usdDataExchange } from '@/hooks/core/useUsd2Cny';
  import { getProductNavFundingRatio } from '@/api/data/product';
  import { watchDebounced } from '@vueuse/shared';

  const userStore = useUserStore();
  const userProducts = computed(() => userStore.getUserInfoAccount);

  const props = defineProps({
    width: {
      type: String as PropType<string>,
      default: '100%',
    },
    height: {
      type: String as PropType<string>,
      default: '352px',
    },
  });
  const loading = ref(false);
  const chartRef = ref<HTMLDivElement | null>(null);
  // 汇率数据
  // const exchange = ref();
  const { exchange } = usdDataExchange();
  // 当前单位
  const curUnit = ref('USD');
  const { setOptions, getInstance } = useECharts(chartRef as Ref<HTMLDivElement>);
  let list = [];
  function initChart() {
    setOptions({
      dataset: { source: list },
      legend: {
        type: 'scroll',
        orient: 'vertical',
        right: '20',
        top: 'center',
        padding: [16, 0],
        itemGap: 16,
        itemWidth: 8,
        itemHeight: 8,
        pageIconColor: '#edbd88',
        pageIconInactiveColor: '#ffffff66',
        textStyle: {
          rich: {
            name: {
              width: 90,
              // color: '#fff',
              fontSize: '14px',
            },
            value: {
              width: 100,
              align: 'right',
              // color: '#fff',
              fontSize: '14px',
            },
            percent: {
              width: 80,
              align: 'right',
              // color: '#fff',
              fontSize: '14px',
            },
          },
        },
        formatter(name) {
          const _item: any = list?.find((item: any) => item.name === name);
          let _val: any = Number(_item.value);
          return _item
            ? [
                `{name|${name}}`,
                `{value|${formateNumStr(_val, { decimals: 2, keepZero: true })}}`,
                `{percent|${_item.percent?.toFixed(2)}%}`,
              ].join('')
            : '';
        },
        icon: 'circle',
      },
      tooltip: {
        formatter: function (params) {
          const _data = params?.data;
          return `<div class='text-xs'>
                <div class='color-secondary'>${_data?.name}</div>
                <div class='border-bottom my-2'></div>
                <div>净值：${formateNumStr(_data?.value, { decimals: 2, keepZero: true })}</div>
                <div>占比：${_data?.percent?.toFixed(2)}%</div>
                </div>
                `;
        },
      },
      series: [
        {
          type: 'pie',
          radius: ['33%', '48%'],
          center: ['20%', '50%'],
          color: ['#F55458', '#5BB86F', '#2C97EB', '#FFD54F', '#F57C00'],
          label: {
            show: false,
          },
          animationType: 'scale',
          animationEasing: 'exponentialInOut',
          animationDelay: function () {
            return Math.random() * 400;
          },
        },
      ],
    });
  }
  function getProductNavFundingRatioFn() {
    // const _params = {
    //   productCodes: userProducts.value?.map((item: any) => item.value)?.join(','),
    // };
    loading.value = true;
    getProductNavFundingRatio()
      .then((res: any) => {
        if (res.retCode == 0) {
          // const _total = res.data.reduce((pre: any, cur: any) => {
          //   const _val = curUnit.value == 'USD' ? cur.equitySumUSD : cur.equitySumCNY;
          //   return pre + Number(_val);
          // }, 0);
          console.log('res.data====', res.data);

          list = res.data?.map((item: any) => {
            const _val =
              curUnit.value == 'CNY'
                ? item?.net_worth
                : item?.net_worth / (exchange.value?.rate || 1);
            return {
              name: item?.product_code,
              value: _val?.toFixed(2),
              percent: item?.net_worth_percentage || 0,
            };
          });
        }
        initChart();
      })
      .finally(() => {
        loading.value = false;
      });
  }
  watch(
    () => userProducts.value,
    (cur) => {
      if (cur?.length) {
        getProductNavFundingRatioFn();
      }
    },
    { immediate: true },
  );
  watchDebounced(
    () => curUnit.value,
    () => {
      getProductNavFundingRatioFn();
    },
  );
</script>
