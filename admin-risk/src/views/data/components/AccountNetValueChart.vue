<template>
  <Card :bordered="false" class="vg-panel net-value-panel">
    <template #title>
      <div class="panel-title">
        <LineChartOutlined />
        <span>{{ title }}</span>
      </div>
    </template>
    <template #extra>
      <Space class="chart-controls">
        <RadioGroup v-model:value="rangeKey" size="small" button-style="solid">
          <RadioButton value="1d">1天</RadioButton>
          <RadioButton value="1w">1周</RadioButton>
          <RadioButton value="1m">1月</RadioButton>
        </RadioGroup>
        <Select
          v-if="showControls"
          v-model:value="selectedAccountId"
          class="account-select"
          :options="accountOptions"
          :disabled="loading || accountOptions.length === 0"
          placeholder="选择账户"
        />
        <Button size="small" :loading="loading" @click="reload">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </Space>
    </template>

    <Alert v-if="errorText" class="mb-3" type="warning" show-icon :message="errorText" />

    <Spin :spinning="loading">
      <div class="chart-shell" :style="{ height }">
        <div ref="chartRef" class="chart-view"></div>
        <div v-if="!loading && !hasData" class="empty-layer">
          <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" description="暂无净值数据" />
        </div>
      </div>
    </Spin>

    <div class="chart-foot">
      <span>{{ currentAccount?.name || '未选择账户' }}</span>
      <span v-if="latestPoint">最近净值 {{ formatNumber(latestPoint.unit_net_worth, 4) }}</span>
      <span v-if="latestPoint">更新时间 {{ latestPoint.created_at }}</span>
    </div>
  </Card>
</template>

<script setup lang="ts">
  import type { Ref, PropType } from 'vue';
  import { computed, onMounted, ref, watch } from 'vue';
  import { Alert, Button, Card, Empty, Radio, Select, Space, Spin } from 'ant-design-vue';
  import { LineChartOutlined, ReloadOutlined } from '@ant-design/icons-vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import { formateNumStr } from '@/utils/formate';
  import {
    DataAccount,
    getAccounts,
    getNetValueHistory,
    NetValuePoint,
  } from '@/api/riskControl';

  const props = defineProps({
    title: {
      type: String,
      default: '账户净值曲线',
    },
    height: {
      type: String,
      default: '360px',
    },
    accounts: {
      type: Array as PropType<DataAccount[]>,
      default: () => [],
    },
    accountId: {
      type: Number as PropType<number | undefined>,
      default: undefined,
    },
    showControls: {
      type: Boolean,
      default: true,
    },
  });

  const loading = ref(false);
  const errorText = ref('');
  const localAccounts = ref<DataAccount[]>([]);
  const selectedAccountId = ref<number | undefined>(props.accountId);
  const rangeKey = ref<'1d' | '1w' | '1m'>('1d');
  const points = ref<NetValuePoint[]>([]);
  const chartRef = ref<HTMLDivElement | null>(null);
  const { setOptions, resize } = useECharts(chartRef as Ref<HTMLDivElement>);
  const RadioGroup = Radio.Group;
  const RadioButton = Radio.Button;

  const rangeOptions = {
    '1d': { label: '过去一天', hours: 24, sampleMinutes: 5, limit: 1000 },
    '1w': { label: '过去一周', hours: 24 * 7, sampleMinutes: 30, limit: 10000 },
    '1m': { label: '过去一月', hours: 24 * 30, sampleMinutes: 120, limit: 20000 },
  };

  const accountSource = computed(() => (props.accounts.length ? props.accounts : localAccounts.value));
  const accountOptions = computed(() =>
    accountSource.value.map((item) => ({
      label: `${item.name} · ${item.account_type}`,
      value: item.id,
    })),
  );
  const currentAccount = computed(() =>
    accountSource.value.find((item) => item.id === selectedAccountId.value),
  );
  const latestPoint = computed(() => points.value[points.value.length - 1]);
  const hasData = computed(() => points.value.length > 0);
  const currentRange = computed(() => rangeOptions[rangeKey.value]);

  function formatNumber(value: any, decimals = 2) {
    return formateNumStr(value || 0, { decimals, keepZero: true });
  }

  function pickDefaultAccount(accounts: DataAccount[]) {
    if (!accounts.length || selectedAccountId.value) return;
    const bybit = accounts.find((item) => item.account_type === 'bybit');
    selectedAccountId.value = (bybit || accounts[0])?.id;
  }

  async function ensureAccounts() {
    if (props.accounts.length) {
      pickDefaultAccount(props.accounts);
      return;
    }
    localAccounts.value = await getAccounts();
    pickDefaultAccount(localAccounts.value);
  }

  function drawChart() {
    const xAxis = points.value.map((item) => item.created_at);
    setOptions({
      color: ['#1677ff', '#22a06b', '#d4380d'],
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
          const row = params?.[0]?.data?.raw as NetValuePoint | undefined;
          if (!row) return '';
          return `
            <div>
              <div>${row.created_at}</div>
              <div>单位净值：${formatNumber(row.unit_net_worth, 4)}</div>
              <div>总资产：${formatNumber(row.total_asset, 2)} USD</div>
              <div>可用资金：${formatNumber(row.available_fund, 2)} USD</div>
              <div>当前回撤：${formatNumber(row.current_drawdown * 100, 2)}%</div>
            </div>
          `;
        },
      },
      legend: {
        top: 0,
        itemWidth: 12,
        itemHeight: 2,
      },
      grid: {
        left: 16,
        right: 20,
        top: 46,
        bottom: 42,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: xAxis,
        axisTick: { show: false },
        axisLabel: {
          color: '#59636e',
          hideOverlap: true,
        },
      },
      yAxis: [
        {
          type: 'value',
          name: '净值',
          scale: true,
          splitLine: { lineStyle: { color: 'rgba(5, 5, 5, 0.08)' } },
        },
        {
          type: 'value',
          name: '回撤',
          scale: true,
          axisLabel: {
            formatter: (value: number) => `${value}%`,
          },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '单位净值',
          type: 'line',
          smooth: true,
          symbol: points.value.length > 1 ? 'none' : 'circle',
          lineStyle: { width: 2 },
          areaStyle: { opacity: 0.08 },
          data: points.value.map((item) => ({
            value: Number(item.unit_net_worth || 0).toFixed(6),
            raw: item,
          })),
        },
        {
          name: '总资产',
          type: 'line',
          smooth: true,
          symbol: 'none',
          lineStyle: { width: 2 },
          data: points.value.map((item) => ({
            value: Number(item.total_asset || 0).toFixed(2),
            raw: item,
          })),
        },
        {
          name: '当前回撤',
          type: 'line',
          smooth: true,
          symbol: 'none',
          yAxisIndex: 1,
          lineStyle: { width: 2 },
          data: points.value.map((item) => ({
            value: Number((item.current_drawdown || 0) * 100).toFixed(2),
            raw: item,
          })),
        },
      ],
    });
  }

  async function reload() {
    loading.value = true;
    errorText.value = '';
    try {
      await ensureAccounts();
      const range = currentRange.value;
      const from = new Date(Date.now() - range.hours * 60 * 60 * 1000).toISOString();
      points.value = await getNetValueHistory({
        account_id: selectedAccountId.value,
        from,
        limit: range.limit,
        sample_minutes: range.sampleMinutes,
      });
      drawChart();
      resize();
    } catch (error: any) {
      errorText.value = error?.message || '净值数据加载失败';
      points.value = [];
      drawChart();
    } finally {
      loading.value = false;
    }
  }

  watch(
    () => props.accounts,
    (accounts) => {
      if (accounts?.length) {
        pickDefaultAccount(accounts);
      }
    },
    { immediate: true },
  );

  watch(
    () => props.accountId,
    (accountId) => {
      if (accountId) selectedAccountId.value = accountId;
    },
  );

  watch(selectedAccountId, () => {
    reload();
  });

  watch(rangeKey, () => {
    reload();
  });

  onMounted(reload);

  defineExpose({ reload });
</script>

<style scoped>
  .net-value-panel {
    min-width: 0;
  }

  .panel-title {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 600;
  }

  .account-select {
    width: 220px;
  }

  .chart-controls {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .chart-shell {
    position: relative;
    min-height: 280px;
  }

  .chart-view {
    width: 100%;
    height: 100%;
  }

  .empty-layer {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
  }

  .chart-foot {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-top: 10px;
    color: #59636e;
    font-size: 12px;
  }

  @media (max-width: 768px) {
    .account-select {
      width: 160px;
    }
  }
</style>
