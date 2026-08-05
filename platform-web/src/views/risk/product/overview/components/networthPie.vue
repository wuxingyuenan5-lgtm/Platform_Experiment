<template>
  <SimpleContainer title="账户净值">
    <div class="component-background p-3 overflow-hidden">
      <Spin :spinning="loading">
        <div ref="chartRef" :style="{ width, height }">
          <div v-if="dataSoure.length === 0" class="flex items-center justify-center h-full">
            <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" />
          </div>
        </div>
      </Spin>
    </div>
  </SimpleContainer>
</template>

<script lang="tsx" setup>
  import type { PropType, Ref } from 'vue';
  import { nextTick, ref, watch } from 'vue';
  import { Empty, Spin } from 'ant-design-vue';
  import { SimpleContainer } from '@/components/Container';
  import { useECharts } from '@/hooks/web/useECharts';
  import { formateNumStr } from '@/utils/formate';

  interface AccountNetWorthRow {
    name: string;
    value: number | string;
    percent: number;
  }

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
      type: Array as PropType<AccountNetWorthRow[]>,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
  });

  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions } = useECharts(chartRef as Ref<HTMLDivElement>);

  function chartRow(params: any): AccountNetWorthRow | undefined {
    return Array.isArray(params) ? params[0]?.data : params?.data;
  }

  function initChart() {
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
            name: { width: 90, fontSize: '14px' },
            value: { width: 100, align: 'right', fontSize: '14px' },
            percent: { width: 80, align: 'right', fontSize: '14px' },
          },
        },
        formatter(name: string) {
          const item = props.dataSoure.find((row) => row.name === name);
          return item
            ? [
                `{name|${name}}`,
                `{value|${formateNumStr(Number(item.value), { decimals: 2, keepZero: true })}}`,
                `{percent|${(item.percent * 100).toFixed(2)}%}`,
              ].join('')
            : '';
        },
        icon: 'circle',
      },
      tooltip: {
        formatter: (params: any) => {
          const data = chartRow(params);
          return `<div class='text-xs'>
                <div class='color-secondary'>${data?.name || ''}</div>
                <div class='border-bottom my-2'></div>
                <div>净值：${formateNumStr(data?.value, { decimals: 2, keepZero: true })}</div>
                <div>占比：${((data?.percent || 0) * 100).toFixed(2)}%</div>
                </div>`;
        },
      },
      series: [
        {
          type: 'pie',
          radius: ['33%', '48%'],
          center: ['20%', '50%'],
          color: ['#F55458', '#5BB86F', '#2C97EB', '#FFD54F', '#F57C00'],
          label: { show: false },
          animationType: 'scale',
          animationEasing: 'exponentialInOut',
          animationDelay: (index: number) => index * 40,
        },
      ],
    });
  }

  watch(
    () => props.dataSoure,
    () => nextTick(initChart),
    { deep: true, immediate: true },
  );
</script>