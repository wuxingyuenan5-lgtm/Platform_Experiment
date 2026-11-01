<template>
  <PageWrapper title="执行记录详情">
    <div class="execution-record-detail">
      <Card :bordered="false" class="vg-panel">
        <div class="header">
          <div class="header__left">
            <Button size="small" @click="goBack">
              <template #icon><ArrowLeftOutlined /></template>
              返回
            </Button>
            <div class="header__title">
              <h3>{{ headline }}</h3>
              <p v-if="record">
                批次 {{ record.batchId }} · 追踪号 {{ record.traceId ?? '未记录' }}
              </p>
            </div>
          </div>
          <Space v-if="record">
            <Tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</Tag>
            <Button :loading="query.isFetching.value" @click="reload">
              <template #icon><ReloadOutlined /></template>
              刷新
            </Button>
          </Space>
        </div>

        <Alert
          v-if="errorMessage"
          type="error"
          show-icon
          :message="errorMessage"
          description="详情由批次、两腿订单、成交与执行步骤实时聚合，可稍后重试。"
        />

        <Spin v-if="query.isLoading.value && !record" class="detail-spin" />

        <template v-else-if="record">
          <p v-if="record.failureReason" class="failure-reason">
            失败原因：{{ record.failureReason }}
          </p>

          <section class="grid">
            <div class="cell">
              <span>策略</span><strong>{{ strategyLabel(record.strategyKey) }}</strong>
            </div>
            <div class="cell">
              <span>动作</span
              ><strong
                >{{ actionLabel(record.action) }} {{ directionLabel(record.direction) }}</strong
              >
            </div>
            <div class="cell">
              <span>标的</span><strong>{{ record.primarySymbol ?? '--' }}</strong>
            </div>
            <div class="cell">
              <span>成交数量</span><strong>{{ record.primaryQuantity ?? '--' }}</strong>
            </div>
            <div class="cell">
              <span>成交均价</span><strong>{{ formatAmount(record.primaryAveragePrice) }}</strong>
            </div>
            <div class="cell">
              <span>名义金额</span><strong>{{ formatAmount(record.notional) }}</strong>
            </div>
            <div class="cell">
              <span>手续费合计</span
              ><strong>{{ formatAmount(record.totalFees) }} {{ record.feeCurrency ?? '' }}</strong>
            </div>
            <div class="cell">
              <span>两腿完成度</span
              ><strong>{{ record.filledLegCount }} / {{ record.legCount }}</strong>
            </div>
            <div class="cell">
              <span>开始时间</span><strong>{{ formatDateTime(record.startedAt) }}</strong>
            </div>
            <div class="cell">
              <span>结束时间</span><strong>{{ formatDateTime(record.finishedAt) }}</strong>
            </div>
            <div class="cell">
              <span>总耗时</span
              ><strong>{{
                record.durationMs != null ? formatDuration(record.durationMs) : '进行中'
              }}</strong>
            </div>
            <div class="cell">
              <span>操作人</span><strong>{{ instruction?.requestedBy ?? '--' }}</strong>
            </div>
          </section>

          <section v-if="relatedRecord" class="related">
            <span>关联记录</span>
            <Button type="link" size="small" @click="openRelated(relatedRecord.id)">
              {{ actionLabel(relatedRecord.action) }} · {{ statusLabel(relatedRecord.status) }} ·
              {{ formatDateTime(relatedRecord.startedAt) }}
            </Button>
          </section>

          <div class="panel-title"><h4>账户状态快照</h4></div>
          <div v-if="!accountSnapshots.length" class="empty-hint">该批次未记录账户快照。</div>
          <div v-else class="snapshot-grid">
            <article v-for="snapshot in accountSnapshots" :key="snapshot.id" class="snapshot-card">
              <header>
                <strong>{{ phaseLabel(snapshot.phase) }}</strong>
                <small>{{ formatDateTime(snapshot.capturedAt) }}</small>
              </header>
              <div class="snapshot-row"
                ><span>账户</span><em>{{ snapshot.accountId }}</em></div
              >
              <div class="snapshot-row">
                <span>可用</span
                ><em>{{ formatAmount(snapshot.available) }} {{ snapshot.currency ?? '' }}</em>
              </div>
              <div class="snapshot-row">
                <span>权益</span><em>{{ formatAmount(snapshot.equity) }}</em>
              </div>
              <div class="snapshot-row"
                ><span>持仓数</span><em>{{ snapshot.positionCount ?? '未记录' }}</em></div
              >
              <div class="snapshot-row">
                <span>数据质量</span><em>{{ snapshot.qualityState ?? '--' }}</em>
              </div>
              <small v-if="snapshot.payload?.venueSnapshotAsOf" class="snapshot-note">
                交易所快照时间 {{ formatDateTime(snapshot.payload.venueSnapshotAsOf) }}
              </small>
              <small v-if="snapshot.derivedFrom === 'balance_snapshots'" class="snapshot-note">
                该批次未写入过程快照，此处取交易所账户余额序列中最接近的时间点（约 30 秒一条）。
              </small>
            </article>
          </div>

          <div class="panel-title"><h4>两腿执行明细</h4></div>
          <Table
            row-key="id"
            size="small"
            :columns="legColumns"
            :data-source="legRows"
            :pagination="false"
          >
            <template #bodyCell="{ column, record: leg }">
              <template v-if="column.key === 'role'">{{ legRoleLabel(leg.role) }}</template>
              <template v-else-if="column.key === 'side'">{{ directionLabel(leg.side) }}</template>
              <template v-else-if="column.key === 'status'">
                <Tag :color="statusColor(leg.status)">{{ statusLabel(leg.status) }}</Tag>
              </template>
              <template v-else-if="column.key === 'fees'">
                {{ formatAmount(leg.fees) }} {{ leg.feeCurrency ?? '' }}
                <Tooltip v-if="leg.feeBreakdown?.length > 1" :title="feeBreakdownText(leg)">
                  <span class="fee-multi">多币种</span>
                </Tooltip>
              </template>
            </template>
          </Table>

          <div class="panel-title"><h4>成交明细</h4></div>
          <div v-if="!fills.length" class="empty-hint">暂无成交记录。</div>
          <Table
            v-else
            row-key="id"
            size="small"
            :columns="fillColumns"
            :data-source="fills"
            :pagination="false"
            :scroll="{ x: 820 }"
          >
            <template #bodyCell="{ column, record: fill }">
              <template v-if="column.key === 'occurredAt'">{{
                formatDateTime(fill.occurred_at)
              }}</template>
              <template v-else-if="column.key === 'side'">{{ directionLabel(fill.side) }}</template>
              <template v-else-if="column.key === 'fee'">
                {{ formatAmount(fill.fee) }} {{ fill.fee_currency ?? '' }}
              </template>
            </template>
          </Table>

          <div class="panel-title"><h4>交易所订单</h4></div>
          <div v-if="!orders.length" class="empty-hint">暂无订单记录。</div>
          <Table
            v-else
            row-key="id"
            size="small"
            :columns="orderColumns"
            :data-source="orders"
            :pagination="false"
            :scroll="{ x: 900 }"
          >
            <template #bodyCell="{ column, record: order }">
              <template v-if="column.key === 'status'">
                <Tag :color="statusColor(order.status)">{{ statusLabel(order.status) }}</Tag>
              </template>
              <template v-else-if="column.key === 'side'">{{
                directionLabel(order.side)
              }}</template>
            </template>
          </Table>

          <ExecutionStepTimeline
            :timeline="timeline"
            :loading="query.isFetching.value"
            :trace-id="record.traceId"
            @refresh="reload"
          />
        </template>
      </Card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { useQuery } from '@tanstack/vue-query';
  import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons-vue';
  import { Alert, Button, Card, Space, Spin, Table, Tag, Tooltip } from 'ant-design-vue';
  import { PageWrapper } from '@/components/Page';
  import { strategyQueryClient, strategyQueryKey } from '@/api/platform/strategyQueries';
  import { getExecutionRecord } from '@/api/platform/executionRecords';
  import ExecutionStepTimeline from '@/views/strategy/funding-carry/components/ExecutionStepTimeline.vue';

  defineOptions({ name: 'StrategyExecutionRecordDetail' });

  const route = useRoute();
  const router = useRouter();
  const recordId = computed(() => String(route.params.recordId ?? ''));

  const query = useQuery(
    {
      queryKey: computed(() => strategyQueryKey('execution-record', recordId.value)),
      queryFn: ({ signal }) => getExecutionRecord(recordId.value, signal),
      enabled: computed(() => !!recordId.value),
      refetchOnMount: 'always',
      staleTime: 0,
    },
    strategyQueryClient,
  );

  const detail = computed(() => query.data.value ?? null);
  const record = computed(() => detail.value?.record ?? null);
  const instruction = computed(() => detail.value?.instruction ?? null);
  const timeline = computed(() => detail.value?.timeline ?? null);
  const asList = <T>(value: T[] | null | undefined): T[] => (Array.isArray(value) ? value : []);
  const accountSnapshots = computed(() => asList(detail.value?.accountSnapshots));
  const fills = computed(() => asList(detail.value?.fills));
  const orders = computed(() => asList(detail.value?.orders));
  const relatedRecord = computed(() => detail.value?.relatedRecord ?? null);

  const errorMessage = computed(() =>
    query.error.value
      ? query.error.value instanceof Error
        ? query.error.value.message
        : '执行记录加载失败'
      : '',
  );

  const headline = computed(() => {
    if (!record.value) return '执行记录';
    return `${actionLabel(record.value.action)} · ${record.value.primarySymbol ?? '--'}`;
  });

  const legRows = computed(() => {
    const details = record.value?.legDetails;
    if (!Array.isArray(details)) return [];
    return details.map((leg, index) => ({
      ...leg,
      id: leg.orderId ?? `${leg.role}-${index}`,
      requestedQuantity: leg.requestedQuantity,
    }));
  });

  const legColumns = [
    { title: '腿', key: 'role', width: 120 },
    { title: '标的', key: 'symbol', width: 110 },
    { title: '方向', key: 'side', width: 80 },
    { title: '请求数量', key: 'requestedQuantity', width: 120 },
    { title: '成交数量', key: 'filledQuantity', width: 120 },
    { title: '成交均价', key: 'averagePrice', width: 110 },
    { title: '手续费', key: 'fees', width: 100 },
    { title: '成交笔数', key: 'fillCount', width: 90 },
    { title: '状态', key: 'status', width: 110 },
    { title: '订单号', key: 'orderId', ellipsis: true },
  ];

  const fillColumns = [
    { title: '成交时间', key: 'occurredAt', width: 170 },
    { title: '标的', key: 'order_symbol', width: 110 },
    { title: '方向', key: 'side', width: 80 },
    { title: '数量', key: 'quantity', width: 120 },
    { title: '价格', key: 'price', width: 110 },
    { title: '手续费', key: 'fee', width: 120 },
    { title: '来源', key: 'source', width: 110 },
    { title: '交易所成交号', key: 'external_fill_id', ellipsis: true },
  ];

  const orderColumns = [
    { title: '标的', key: 'symbol', width: 110 },
    { title: '方向', key: 'side', width: 80 },
    { title: '类型', key: 'order_type', width: 100 },
    { title: '数量', key: 'quantity', width: 110 },
    { title: '状态', key: 'status', width: 110 },
    { title: '交易所订单号', key: 'external_order_id', width: 190, ellipsis: true },
    { title: '本地订单号', key: 'id', ellipsis: true },
  ];

  function reload() {
    void query.refetch();
  }

  function goBack() {
    void router.push({ name: 'StrategyExecutionRecords' });
  }

  function openRelated(id: string) {
    void router.push({ name: 'StrategyExecutionRecordDetail', params: { recordId: id } });
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
    partially_filled: '部分成交',
    filled: '已成交',
    hedged: '已对冲',
    completed: '已完成',
    failed: '失败',
    rejected: '已拒绝',
    manual_intervention: '需人工处理',
    canceled: '已取消',
  };
  const LEG_ROLE_LABELS: Record<string, string> = {
    spot_leg: '现货腿',
    perpetual_leg: '永续腿',
    bybit_leg: 'Bybit 腿',
    mt5_leg: 'MT5 腿',
  };
  const PHASE_LABELS: Record<string, string> = {
    pre_submit: '提交前',
    post_submit: '提交后',
    post_fill: '成交后',
    final: '终态',
  };
  const DIRECTION_LABELS: Record<string, string> = {
    long: '多头',
    short: '空头',
    buy: '买入',
    sell: '卖出',
  };

  function strategyLabel(key?: string | null) {
    return key ? STRATEGY_LABELS[key] ?? key : '--';
  }
  function actionLabel(action?: string | null) {
    return action ? ACTION_LABELS[action] ?? action : '--';
  }
  function statusLabel(status?: string | null) {
    return status ? STATUS_LABELS[status] ?? status : '--';
  }
  function statusColor(status?: string | null) {
    if (status === 'completed' || status === 'hedged' || status === 'filled') return 'green';
    if (status === 'failed' || status === 'rejected') return 'red';
    if (status === 'manual_intervention') return 'orange';
    if (status === 'executing' || status === 'accepted') return 'blue';
    return 'default';
  }
  function directionLabel(direction?: string | null) {
    if (!direction) return '--';
    return DIRECTION_LABELS[direction] ?? direction;
  }
  function legRoleLabel(role?: string | null) {
    if (!role) return '--';
    return LEG_ROLE_LABELS[role] ?? role;
  }
  function phaseLabel(phase?: string | null) {
    if (!phase) return '--';
    return PHASE_LABELS[phase] ?? phase;
  }

  function feeBreakdownText(leg: { feeBreakdown?: Array<{ currency: string; amount: string }> }) {
    const items = leg.feeBreakdown ?? [];
    return items.map((item) => `${formatAmount(item.amount)} ${item.currency}`).join(' + ');
  }
</script>

<style scoped lang="less">
  .execution-record-detail {
    display: grid;
    gap: 12px;
  }

  .header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 16px;
  }

  .header__left {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }

  .header__title h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 800;
  }

  .header__title p {
    margin: 4px 0 0;
    color: rgba(0, 0, 0, 0.45);
    font-size: 12px;
  }

  .failure-reason {
    margin: 0 0 12px;
    padding: 10px 12px;
    border: 1px solid #ffccc7;
    border-radius: 8px;
    background: #fff2f0;
    color: #cf1322;
    font-size: 13px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px;
  }

  .cell {
    display: grid;
    gap: 4px;
    padding: 10px 12px;
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 10px;
  }

  .cell span {
    color: rgba(0, 0, 0, 0.45);
    font-size: 12px;
  }

  .cell strong {
    font-size: 14px;
    font-variant-numeric: tabular-nums;
  }

  .related {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 12px;
    font-size: 13px;
  }

  .related span {
    color: rgba(0, 0, 0, 0.45);
  }

  .panel-title {
    margin: 20px 0 10px;
  }

  .panel-title h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 800;
  }

  .snapshot-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 12px;
  }

  .snapshot-card {
    display: grid;
    gap: 6px;
    padding: 12px 14px;
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-radius: 12px;
    background: #fafafa;
  }

  .snapshot-card header {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 13px;
  }

  .snapshot-card header small {
    color: rgba(0, 0, 0, 0.45);
  }

  .snapshot-row {
    display: flex;
    justify-content: space-between;
    gap: 8px;
    font-size: 12px;
  }

  .snapshot-row span {
    color: rgba(0, 0, 0, 0.45);
  }

  .snapshot-row em {
    font-style: normal;
    font-variant-numeric: tabular-nums;
  }

  .snapshot-note {
    color: rgba(0, 0, 0, 0.35);
    font-size: 11px;
  }

  .fee-multi {
    margin-left: 4px;
    padding: 0 5px;
    border-radius: 8px;
    background: #f0f5ff;
    color: #2f54eb;
    font-size: 11px;
    cursor: help;
  }

  .empty-hint {
    padding: 12px 0;
    color: rgba(0, 0, 0, 0.45);
    font-size: 12px;
  }

  .detail-spin {
    display: block;
    margin: 40px auto;
  }
</style>
