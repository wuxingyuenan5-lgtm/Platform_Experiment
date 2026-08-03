<template>
  <SimpleContainer title="海内外净值占比">
    <div class="h-100 component-background">
      <div class="flex justify-end pt-3 pr-3">
        <Segmented v-model:value="curUnit" size="small" :options="unitOptions" />
      </div>
      <div class="h-388px">
        <Spin :spinning="loading">
          <div ref="chartRef" :style="{ width, height: height }">
            <div
              v-if="!record || record?.length == 0"
              class="flex items-center justify-center h-full"
            >
              <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </div>
          </div>
        </Spin>
      </div>
    </div>
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import type { PropType, Ref } from 'vue';
  import { watch, ref, reactive, toRaw, onMounted } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import { Empty, Spin, Segmented } from 'ant-design-vue';
  import { formateNumStr } from '@/utils/formate';
  import { unitOptions } from '@/utils/options/basicOptions';
  import { getProductNavProductRatio } from '@/api/data/product';
  import { watchDebounced } from '@vueuse/shared';

  const props = defineProps({
    // record: {
    //   type: Object,
    //   default: () => {},
    // },
    // loading: {
    //   type: Boolean,
    //   default: false,
    // },
    width: {
      type: String as PropType<string>,
      default: '100%',
    },
    height: {
      type: String as PropType<string>,
      default: '364px',
    },
  });
  const record = ref();
  // 当前单位
  const curUnit = ref('USD');
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, getInstance } = useECharts(chartRef as Ref<HTMLDivElement>);
  const loading = ref(false);
  function initData() {
    setOptions({
      dataset: { source: record.value },
      legend: {
        show: true,
        top: 16,
        icon: 'rect',
        itemWidth: 12,
        itemHeight: 2,
        itemGap: 36,
      },
      tooltip: {
        formatter: function (params) {
          // console.log(params);

          const _data = params?.data;
          return `<div class='text-xs'>
                <div class='color-secondary'>${_data?.name}</div>
                <div class='border-bottom my-2'></div>
                <div>净值：${formateNumStr(_data?.value, { decimals: 2, keepZero: true })}</div>
                <div>占比：${((_data?.percent || 0) * 100).toFixed(2)}%</div>
                </div>
                `;
        },
      },
      series: [
        {
          type: 'pie',
          radius: '50%',
          center: ['50%', '55%'],
          color: ['#F55458', '#5BB86F'],
          label: {
            show: true,
            formatter: function (params) {
              // console.log(params);
              return `${params?.data?.name}\n${formateNumStr(params?.data?.value, {
                decimals: 2,
                keepZero: true,
              })}`;
            },
          },
          animationType: 'scale',
          animationEasing: 'exponentialInOut',
          animationDelay: (index: number) => index * 40,
        },
      ],
    });
  }
  function getProductNavProductRatioFn() {
    loading.value = true;
    getProductNavProductRatio()
      .then((res: any) => {
        if (res.retCode == 0) {
          const _total = res.data.reduce((pre: any, cur: any) => {
            const _val = curUnit.value == 'USD' ? cur.valueUSD : cur.value;
            return pre + _val;
          }, 0);
          record.value = res.data?.map((item: any) => {
            let _val = curUnit.value == 'USD' ? item.valueUSD : item.value;
            return {
              name: item.name,
              value: _val.toFixed(2),
              percent: _total ? (_val / _total).toFixed(4) : 0,
            };
          });
          initData();
        }
      })
      .finally(() => {
        loading.value = false;
      });
  }
  watchDebounced(
    () => curUnit.value,
    () => {
      getProductNavProductRatioFn();
    },
    { immediate: true },
  );
</script>
