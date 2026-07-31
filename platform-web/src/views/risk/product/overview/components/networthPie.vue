<template>
  <SimpleContainer title="账户净值 ">
    <div class="component-background p-3 overflow-hidden">
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
  import { useECharts } from '@/hooks/web/useECharts';
  import { formateNumStr } from '@/utils/formate';
  import { Empty, Spin } from 'ant-design-vue';

  const props = defineProps({
    width: {
      type: String as PropType<string>,
      default: '100%',
    },
    height: {
      type: String as PropType<string>,
      default: '376px',
    },
    dataSoure: {
      type: Array as PropType<Array<any>>,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
  });
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, getInstance } = useECharts(chartRef as Ref<HTMLDivElement>);

  function initChart() {
    console.log('dataSoure----', props.dataSoure);

    setOptions({
      dataset: { source: props.dataSoure },
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
          const _item: any = props.dataSoure?.find((item: any) => item.name === name);
          return _item
            ? [
                `{name|${name}}`,
                `{value|${formateNumStr(Number(_item.value), { decimals: 2, keepZero: true })}}`,
                `{percent|${(_item.percent * 100).toFixed(2)}%}`,
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
                <div>占比：${(_data?.percent * 100).toFixed(2)}%</div>
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
  watch(
    () => props.dataSoure,
    () => {
      nextTick(() => {
        initChart();
      });
    },
    { deep: true, immediate: true },
  );
</script>
