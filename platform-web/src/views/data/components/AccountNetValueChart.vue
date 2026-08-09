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

    <Alert v-if="errorText" class="mb-3" type="error" show-icon :message="errorText" />

    <Spin :spinning="loading">
      <div class="chart-shell" :style="{ height }">
        <div ref="chartRef" class="chart-view"></div>
        <div v-if="!loading && !hasData" class="empty-layer">
          <Empty
            :image="Empty.PRESENTED_IMAGE_SIMPLE"
            :description="errorText ? '净值数据暂不可用' : '暂无净值数据'"
          />
        </div>
      </div>
    </Spin>

    <div class="chart-foot">
      <span>{{ currentAccount?.name || '未选择账户' }}</span>
      <span v-if="latestPoint">最近净值 {{ formatDecimal(latestPoint.unit_net_worth) }}</span>
      <span v-if="latestPoint">更新时间 {{ latestPoint.created_at }}</span>
      <span>数据服务</span>
      <span>精度：Decimal字符串</span>
    </div>
  </Card>
</template>

<script setup lang="ts">
  import { LineChartOutlined, ReloadOutlined } from '@ant-design/icons-vue';
  import { Alert, Button, Card, Empty, Radio, Select, Space, Spin } from 'ant-design-vue';
  import Decimal from 'decimal.js';
  import { computed, onMounted, ref, watch } from 'vue';
  import type { PropType, Ref } from 'vue';
  import {
    type DataAccount,
    getAccounts,
    getNetValueHistory,
    type NetValuePoint,
  } from '@/api/riskControl';
  import { useECharts } from '@/hooks/web/useECharts';
  import { formatDecimalString } from '@/utils/decimalDisplay';

  const props = defineProps({
    title: { type: String, default: '账户净值曲线' },
    height: { type: String, default: '360px' },
    accounts: { type: Array as PropType<DataAccount[]>, default: () => [] },
    accountId: { type: Number as PropType<number | undefined>, default: undefined },
    showControls: { type: Boolean, default: true },
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
    '1d': { hours: 24, sampleMinutes: 5, limit: 1000 },
    '1w': { hours: 24 * 7, sampleMinutes: 30, limit: 10000 },
    '1m': { hours: 24 * 30, sampleMinutes: 120, limit: 20000 },
  };

  const accountSource = computed(() =>
    props.accounts.length ? props.accounts : localAccounts.value,
  );
  const accountOptions = computed(() =>
    accountSource.value.map((item) => ({
      label: `${item.name} · ${item.account_type}`,
      value: item.id,
    })),
  );
  const currentAccount = computed(() =>
    accountSource.value.find((item) => item.id === selectedAccountId.value),
  );
  const latestPoint = computed(() => points.value.at(-1));
  const hasData = computed(() => points.value.length > 0);
  const currentRange = computed(() => rangeOptions[rangeKey.value]);

  function formatDecimal(value: string) {
    return formatDecimalString(value);
  }

  function chartNumber(value: string) {
    return new Decimal(value).toNumber();
  }

  function percentText(value: string) {
    return `${new Decimal(value).mul(100).toFixed(2)}%`;
  }

  function pickDefaultAccount(accounts: DataAccount[]) {
    if (!accounts.length || selectedAccountId.value) return;
    selectedAccountId.value = (
      accounts.find((item) => item.account_type === 'bybit') || accounts[0]
    )?.id;
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
    setOptions({
      tooltip: {
        trigger: 'axis',
        formatter: (params: any[]) => {
          const row = params?.[0]?.data?.raw as NetValuePoint | undefined;
          if (!row) return '';
          return `
            <div>
              <div>${row.created_at}</div>
              <div>单位净值：${formatDecimal(row.unit_net_worth)}</div>
              <div>总资产：${formatDecimal(row.total_asset)} USD</div>
              <div>可用资金：${formatDecimal(row.available_fund)} USD</div>
              <div>当前回撤：${percentText(row.current_drawdown)}</div>
            </div>
          `;
        },
      },
      legend: { top: 0, itemWidth: 12, itemHeight: 2 },
      grid: { left: 16, right: 20, top: 46, bottom: 42, containLabel: true },
      xAxis: {
        type: 'category',
        data: points.value.map((item) => item.created_at),
        axisTick: { show: false },
        axisLabel: { color: '#59636e', hideOverlap: true },
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
          axisLabel: { formatter: (value: number) => `${value}%` },
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
            value: chartNumber(item.unit_net_worth),
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
            value: chartNumber(item.total_asset),
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
            value: new Decimal(item.current_drawdown).mul(100).toNumber(),
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
      if (!selectedAccountId.value) {
        points.value = [];
        drawChart();
        return;
      }
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
    } catch (error) {
      errorText.value = error instanceof Error ? error.message : '净值数据加载失败';
      points.value = [];
      drawChart();
    } finally {
      loading.value = false;
    }
  }

  watch(
    () => props.accounts,
    (accounts) => accounts?.length && pickDefaultAccount(accounts),
    { immediate: true },
  );
  watch(
    () => props.accountId,
    (accountId) => {
      if (accountId) selectedAccountId.value = accountId;
    },
  );
  watch(selectedAccountId, reload);
  watch(rangeKey, reload);
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
