<template>
  <SimpleContainer title="海内外净值占比">
    <div class="h-100 component-background">
      <div class="flex justify-end pt-3 pr-3">
        <Segmented v-model:value="curUnit" size="small" :options="unitOptions" />
      </div>
      <div class="h-388px">
        <Spin :spinning="loading">
          <div ref="chartRef" :style="{ width, height }">
            <div
              v-if="!record || record.length === 0"
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
  import type { PropType, Ref } from 'vue';
  import { ref } from 'vue';
  import { Empty, Segmented, Spin } from 'ant-design-vue';
  import { watchDebounced } from '@vueuse/shared';
  import { getProductNavProductRatio } from '@/api/data/product';
  import { SimpleContainer } from '@/components/Container';
  import { useECharts } from '@/hooks/web/useECharts';
  import { formateNumStr } from '@/utils/formate';
  import { unitOptions } from '@/utils/options/basicOptions';

  interface NetWorthChartRow {
    name: string;
    value: string;
    percent: string | number;
  }

  defineProps({
    width: {
      type: String as PropType<string>,
      default: '100%',
    },
    height: {
      type: String as PropType<string>,
      default: '364px',
    },
  });

  const record = ref<NetWorthChartRow[]>([]);
  const curUnit = ref('USD');
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions } = useECharts(chartRef as Ref<HTMLDivElement>);
  const loading = ref(false);

  function chartRow(params: any): NetWorthChartRow | undefined {
    return Array.isArray(params) ? params[0]?.data : params?.data;
  }

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
        formatter: (params: any) => {
          const data = chartRow(params);
          return `<div class='text-xs'>
                <div class='color-secondary'>${data?.name || ''}</div>
                <div class='border-bottom my-2'></div>
                <div>净值：${formateNumStr(data?.value, { decimals: 2, keepZero: true })}</div>
                <div>占比：${(Number(data?.percent || 0) * 100).toFixed(2)}%</div>
                </div>`;
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
            formatter: (params: any) => {
              const data = chartRow(params);
              return `${data?.name || ''}\n${formateNumStr(data?.value, {
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

  async function loadProductRatio() {
    loading.value = true;
    try {
      const response: any = await getProductNavProductRatio();
      if (response.retCode !== 0) return;
      const total = response.data.reduce((sum: number, item: any) => {
        const value = curUnit.value === 'USD' ? item.valueUSD : item.value;
        return sum + Number(value || 0);
      }, 0);
      record.value = response.data.map((item: any) => {
        const value = Number(curUnit.value === 'USD' ? item.valueUSD : item.value);
        return {
          name: item.name,
          value: value.toFixed(2),
          percent: total ? (value / total).toFixed(4) : 0,
        };
      });
      initData();
    } finally {
      loading.value = false;
    }
  }

  watchDebounced(curUnit, () => void loadProductRatio(), { immediate: true });
</script>