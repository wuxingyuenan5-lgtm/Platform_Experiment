<template>
  <PageWrapper title="交易执行记录">
    <div class="execution-records-page">
      <Card :bordered="false" class="vg-panel">
        <div class="toolbar">
          <div class="toolbar__filters">
            <Select
              v-model:value="filters.strategyKey"
              class="filter"
              :options="strategyOptions"
              placeholder="全部策略"
              allow-clear
              @change="applyFilters"
            />
            <Select
              v-model:value="filters.action"
              class="filter filter--narrow"
              :options="actionOptions"
              placeholder="全部动作"
              allow-clear
              @change="applyFilters"
            />
            <Select
              v-model:value="filters.status"
              class="filter filter--narrow"
              :options="statusOptions"
              placeholder="全部状态"
              allow-clear
              @change="applyFilters"
            />
            <Input
              v-model:value="filters.symbol"
              class="filter filter--narrow"
              placeholder="标的，例如 BTC"
              allow-clear
              @press-enter="applyFilters"
              @blur="applyFilters"
            />
            <RangePicker
              v-model:value="range"
              class="filter filter--wide"
              show-time
              format="YYYY-MM-DD HH:mm"
              @change="applyFilters"
            />
          </div>
          <Space>
            <Button :loading="loading" @click="reload">
              <template #icon><ReloadOutlined /></template>
              刷新
            </Button>
          </Space>
        </div>

        <Alert
          v-if="error"
          type="error"
          show-icon
          class="mb-3"
          :message="error"
          description="执行记录由批次终态投影生成；若刚完成下单，请稍后刷新。"
        />

        <Table
          row-key="id"
          size="middle"
          :columns="columns"
          :data-source="items"
          :loading="loading"
          :pagination="pagination"
          :scroll="{ x: 1180 }"
          :custom-row="customRow"
          @change="handleTableChange"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'startedAt'">
              <div class="cell-time">
                <strong>{{ formatDateTime(record.startedAt) }}</strong>
                <small>{{
                  record.durationMs != null ? `耗时 ${formatDuration(record.durationMs)}` : '进行中'
                }}</small>
              </div>
            </template>
            <template v-else-if="column.key === 'strategyKey'">
              <Tag :color="strategyColor(record.strategyKey)">{{
                strategyLabel(record.strategyKey)
              }}</Tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <span class="action">{{ actionLabel(record.action) }}</span>
              <small v-if="record.direction" class="action__direction">{{
                directionLabel(record.direction)
              }}</small>
            </template>
            <template v-else-if="column.key === 'quantity'">
              <div class="cell-number">{{ record.primaryQuantity ?? '--' }}</div>
              <small class="cell-sub">{{ record.primarySymbol ?? '--' }}</small>
            </template>
            <template v-else-if="column.key === 'notional'">
              <div class="cell-number">{{ formatAmount(record.notional) }}</div>
              <small class="cell-sub">均价 {{ formatAmount(record.primaryAveragePrice) }}</small>
            </template>
            <template v-else-if="column.key === 'fees'">
              <div class="cell-number">{{ formatAmount(record.totalFees) }}</div>
              <small class="cell-sub">{{ record.feeCurrency ?? '--' }}</small>
            </template>
            <template v-else-if="column.key === 'legs'">
              <span>{{ record.filledLegCount }} / {{ record.legCount }}</span>
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</Tag>
              <Tooltip v-if="record.failureReason" :title="record.failureReason">
                <span class="failure-mark">!</span>
              </Tooltip>
            </template>
            <template v-else-if="column.key === 'action-links'">
              <Button type="link" size="small" @click.stop="openDetail(record.id)"
                >查看全链路</Button
              >
            </template>
          </template>
        </Table>
      </Card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, watch } from 'vue';
  import { useRouter } from 'vue-router';
  import { useQuery } from '@tanstack/vue-query';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import {
    Alert,
    Button,
    Card,
    Input,
    RangePicker,
    Select,
    Space,
    Table,
    Tag,
    Tooltip,
  } from 'ant-design-vue';
  import { PageWrapper } from '@/components/Page';
  import {
    strategyQueryClient,
    strategyQueryKey,
    strategySession,
  } from '@/api/platform/strategyQueries';
  import { listExecutionRecords, type ExecutionRecord } from '@/api/platform/executionRecords';

  defineOptions({ name: 'StrategyExecutionRecords' });

  const router = useRouter();
  const pageSize = 20;
  const page = ref(1);
  const range = ref<[unknown, unknown] | null>(null);
  const filters = reactive<{
    strategyKey?: string;
    action?: string;
    status?: string;
    symbol?: string;
    startedFrom?: string;
    startedTo?: string;
  }>({});

  const strategyOptions = [
    { value: 'funding_arbitrage', label: '资金套利' },
    { value: 'cross_venue_spread', label: '跨所价差' },
  ];
  const actionOptions = [
    { value: 'open', label: '开仓' },
    { value: 'close', label: '平仓' },
    { value: 'risk_disposition', label: '风险处置' },
  ];
  const statusOptions = [
    { value: 'completed', label: '已完成' },
    { value: 'hedged', label: '已对冲' },
    { value: 'manual_intervention', label: '需人工处理' },
    { value: 'failed', label: '失败' },
    { value: 'executing', label: '执行中' },
  ];

  const columns = [
    { title: '提交时间', key: 'startedAt', width: 170 },
    { title: '策略', key: 'strategyKey', width: 110 },
    { title: '动作', key: 'action', width: 100 },
    { title: '成交数量', key: 'quantity', width: 140 },
    { title: '名义金额', key: 'notional', width: 150 },
    { title: '手续费', key: 'fees', width: 120 },
    { title: '腿', key: 'legs', width: 70 },
    { title: '状态', key: 'status', width: 120 },
    { title: '操作', key: 'action-links', width: 110, fixed: 'right' as const },
  ];

  const queryKey = computed(() =>
    strategyQueryKey(
      'execution-records',
      filters.strategyKey,
      filters.action,
      filters.status,
      filters.symbol,
      filters.startedFrom,
      filters.startedTo,
      page.value,
    ),
  );

  const query = useQuery(
    {
      queryKey,
      queryFn: ({ signal }) =>
        listExecutionRecords(
          {
            strategyKey: filters.strategyKey,
            action: filters.action,
            status: filters.status,
            symbol: filters.symbol,
            startedFrom: filters.startedFrom,
            startedTo: filters.startedTo,
            limit: pageSize,
            offset: (page.value - 1) * pageSize,
          },
          signal,
        ),
      // The list is a projection of live batches: never serve a cached page on
      // entry, and refetch when this tab becomes active again.
      refetchOnMount: 'always',
      staleTime: 0,
      refetchInterval: 15_000,
    },
    strategyQueryClient,
  );

  // `setStrategyQuerySession` clears the shared client whenever the identity
  // changes (login, role refresh, CSRF rotation). A clear during the first load
  // used to leave this page blank until a manual browser refresh.
  watch(
    () => strategySession.value.generation,
    () => {
      void query.refetch();
    },
  );

  const items = computed<ExecutionRecord[]>(() => query.data.value?.items ?? []);
  const total = computed(() => query.data.value?.total ?? 0);
  const loading = computed(() => query.isFetching.value);
  const error = computed(() =>
    query.error.value
      ? query.error.value instanceof Error
        ? query.error.value.message
        : '执行记录加载失败'
      : '',
  );

  const pagination = computed(() => ({
    current: page.value,
    pageSize,
    total: total.value,
    showSizeChanger: false,
    showTotal: (value: number) => `共 ${value} 条`,
  }));

  function applyFilters() {
    filters.startedFrom = range.value?.[0]
      ? new Date(range.value[0] as string).toISOString()
      : undefined;
    filters.startedTo = range.value?.[1]
      ? new Date(range.value[1] as string).toISOString()
      : undefined;
    page.value = 1;
  }

  function reload() {
    void query.refetch();
  }

  function handleTableChange(paginator: { current?: number }) {
    page.value = paginator.current ?? 1;
  }

  function customRow(record: ExecutionRecord) {
    return {
      style: 'cursor: pointer;',
      onClick: () => openDetail(record.id),
    };
  }

  function openDetail(recordId: string) {
    void router.push({ name: 'StrategyExecutionRecordDetail', params: { recordId } });
  }

  function formatDateTime(value: unknown) {
    if (!value) return '--';
    const parsed = new Date(String(value));
    return Number.isNaN(parsed.getTime())
      ? String(value)
      : parsed.toLocaleString('zh-CN', { hour12: false });
  }

  function formatAmount(value: unknown) {
    if (value == null || value === '') return '--';
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return String(value);
    return numeric.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  }

  function formatDuration(ms: number) {
    if (ms < 1000) return `${ms} ms`;
    if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
    return `${Math.floor(ms / 60_000)} min ${Math.round((ms % 60_000) / 1000)} s`;
  }

  const STRATEGY_LABELS: Record<string, string> = {
    funding_arbitrage: '资金套利',
    cross_venue_spread: '跨所价差',
  };
  const ACTION_LABELS: Record<string, string> = {
    open: '开仓',
    close: '平仓',
    risk_disposition: '风险处置',
  };
  const STATUS_LABELS: Record<string, string> = {
    pending: '待执行',
    accepted: '已受理',
    executing: '执行中',
    partially_executed: '部分执行',
    hedged: '已对冲',
    completed: '已完成',
    failed: '失败',
    rejected: '已拒绝',
    manual_intervention: '需人工处理',
    canceled: '已取消',
  };
  const DIRECTION_LABELS: Record<string, string> = {
    long: '多头',
    short: '空头',
    buy: '买入',
    sell: '卖出',
    open_long: '多',
    open_short: '空',
  };

  function strategyLabel(key?: string | null) {
    return key ? STRATEGY_LABELS[key] ?? key : '--';
  }
  function strategyColor(key?: string | null) {
    return key === 'funding_arbitrage'
      ? 'blue'
      : key === 'cross_venue_spread'
      ? 'purple'
      : 'default';
  }
  function actionLabel(action?: string | null) {
    return action ? ACTION_LABELS[action] ?? action : '--';
  }
  function statusLabel(status?: string | null) {
    return status ? STATUS_LABELS[status] ?? status : '--';
  }
  function statusColor(status?: string | null) {
    if (status === 'completed' || status === 'hedged') return 'green';
    if (status === 'failed' || status === 'rejected') return 'red';
    if (status === 'manual_intervention') return 'orange';
    if (status === 'executing' || status === 'accepted') return 'blue';
    return 'default';
  }
  function directionLabel(direction?: string | null) {
    if (!direction) return '';
    return DIRECTION_LABELS[direction] ?? direction;
  }
</script>

<style scoped lang="less">
  .execution-records-page {
    display: grid;
    gap: 12px;
  }

  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }

  .toolbar__filters {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }

  .filter {
    width: 150px;
  }

  .filter--narrow {
    width: 120px;
  }

  .filter--wide {
    width: 340px;
  }

  .cell-time {
    display: grid;
    gap: 2px;
  }

  .cell-time small,
  .cell-sub {
    color: rgba(0, 0, 0, 0.45);
    font-size: 12px;
  }

  .cell-number {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
  }

  .action {
    font-weight: 600;
    margin-right: 6px;
  }

  .action__direction {
    color: rgba(0, 0, 0, 0.45);
  }

  .failure-mark {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    margin-left: 6px;
    border-radius: 50%;
    background: #fff1f0;
    color: #cf1322;
    font-size: 11px;
    font-weight: 700;
    cursor: help;
  }
</style>
