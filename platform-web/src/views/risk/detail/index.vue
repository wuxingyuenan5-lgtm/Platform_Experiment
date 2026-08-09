<template>
  <PageWrapper title="风控详情">
    <main class="risk-detail-page" data-testid="risk-detail-restored">
      <section class="risk-toolbar">
        <div>
          <h2>风险总览</h2>
          <p>按账户、策略、持仓和品种维度跟踪敞口、杠杆、保证金、集中度与处理进度。</p>
        </div>
        <div class="toolbar-actions">
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag color="green">运行正常</Tag>
          <Tag>最近更新 {{ latestRefresh }}</Tag>
          <Button :loading="loading" @click="refreshRisk">刷新</Button>
        </div>
      </section>

      <Row :gutter="[12, 12]" class="summary-grid">
        <Col v-for="item in summaryCards" :key="item.label" :xs="24" :sm="12" :xl="6">
          <Card :bordered="false" class="metric-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <em :class="`tone-${item.tone}`">{{ item.note }}</em>
          </Card>
        </Col>
      </Row>

      <Row :gutter="[12, 12]">
        <Col :xs="24" :xl="14">
          <Card :bordered="false" class="vg-panel" title="风险维度">
            <div class="dimension-tabs">
              <button
                v-for="item in dimensionTabs"
                :key="item.key"
                type="button"
                :class="{ active: activeDimension === item.key }"
                @click="activeDimension = item.key"
              >
                {{ item.label }}
              </button>
            </div>
            <Table
              row-key="name"
              size="middle"
              :columns="dimensionColumns"
              :data-source="filteredDimensions"
              :pagination="false"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'usage'">
                  <Progress
                    :percent="record.usage"
                    size="small"
                    :status="record.usage > 82 ? 'exception' : 'normal'"
                  />
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="record.tone">{{ record.status }}</Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>

        <Col :xs="24" :xl="10">
          <Card :bordered="false" class="vg-panel" title="风险限额">
            <Table
              row-key="name"
              size="small"
              :columns="limitColumns"
              :data-source="riskLimits"
              :pagination="false"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'usage'">
                  <Progress
                    :percent="record.usage"
                    size="small"
                    :status="record.usage > 80 ? 'exception' : 'normal'"
                  />
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="record.tone">{{ record.status }}</Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>
      </Row>

      <Row :gutter="[12, 12]" class="mt-3">
        <Col :xs="24" :xl="10">
          <Card :bordered="false" class="vg-panel" title="资产结构快照">
            <div class="asset-list">
              <div v-for="item in assetStructure" :key="item.name" class="asset-row">
                <div>
                  <b>{{ item.name }}</b>
                  <span>{{ item.detail }}</span>
                </div>
                <strong>{{ item.value }}</strong>
                <Progress :percent="item.percent" size="small" />
              </div>
            </div>
          </Card>
        </Col>
        <Col :xs="24" :xl="14">
          <Card :bordered="false" class="vg-panel" title="异常事件与处理">
            <div class="record-toolbar">
              <Input v-model:value="keyword" allow-clear placeholder="查询事件、策略或品种" />
              <Select v-model:value="severityFilter" class="filter-select">
                <Select.Option value="all">全部等级</Select.Option>
                <Select.Option value="high">高风险</Select.Option>
                <Select.Option value="medium">中风险</Select.Option>
                <Select.Option value="low">低风险</Select.Option>
              </Select>
              <Select v-model:value="statusFilter" class="filter-select">
                <Select.Option value="all">全部状态</Select.Option>
                <Select.Option value="pending">待处理</Select.Option>
                <Select.Option value="processing">处理中</Select.Option>
                <Select.Option value="done">处理完成</Select.Option>
              </Select>
            </div>
            <Table
              row-key="id"
              size="middle"
              :columns="recordColumns"
              :data-source="filteredRecords"
              :pagination="{ pageSize: 6 }"
            >
              <template #emptyText>暂无风险记录</template>
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'severity'">
                  <Tag :color="severityColor(record.severity)">{{
                    severityLabel(record.severity)
                  }}</Tag>
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>
      </Row>

      <Row :gutter="[12, 12]" class="mt-3">
        <Col :xs="24" :xl="12">
          <Card :bordered="false" class="vg-panel" title="告警消息">
            <Table
              row-key="id"
              size="small"
              :columns="messageColumns"
              :data-source="messages"
              :pagination="{ pageSize: 5 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <Tag :color="record.status === '未读' ? 'orange' : 'green'">{{
                    record.status
                  }}</Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>
        <Col :xs="24" :xl="12">
          <Card :bordered="false" class="vg-panel" title="审计日志">
            <Table
              row-key="id"
              size="small"
              :columns="auditColumns"
              :data-source="auditLogs"
              :pagination="{ pageSize: 5 }"
            />
          </Card>
        </Col>
      </Row>
    </main>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { Button, Card, Col, Input, Progress, Row, Select, Table, Tag } from 'ant-design-vue';
  import type { ColumnsType } from 'ant-design-vue/es/table/interface';
  import { computed, ref } from 'vue';
  import { PageWrapper } from '@/components/Page';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';

  type DimensionKey = 'all' | 'account' | 'strategy' | 'position' | 'product';
  type Severity = 'high' | 'medium' | 'low';
  type RecordStatus = 'pending' | 'processing' | 'done';

  interface RiskDimension {
    category: Exclude<DimensionKey, 'all'>;
    name: string;
    exposure: string;
    leverage: string;
    margin: string;
    concentration: string;
    liquidity: string;
    usage: number;
    status: string;
    tone: string;
  }

  interface RiskRecord {
    id: string;
    time: string;
    target: string;
    event: string;
    severity: Severity;
    status: RecordStatus;
    owner: string;
  }

  const { roleLabel, roleColor } = useRoleAccess();
  const loading = ref(false);
  const latestRefresh = ref('2026-07-12 15:30:00');
  const activeDimension = ref<DimensionKey>('all');
  const keyword = ref('');
  const severityFilter = ref<'all' | Severity>('all');
  const statusFilter = ref<'all' | RecordStatus>('all');

  const summaryCards = [
    { label: '风控记录', value: '28', note: '近 24 小时 6 条', tone: 'neutral' },
    { label: '待处理', value: '4', note: '2 条需要当日处理', tone: 'warning' },
    { label: '高风险', value: '3', note: '保证金与集中度为主', tone: 'danger' },
    { label: '总资产', value: '32,846,520 USD', note: '可用资金 61.4%', tone: 'positive' },
    { label: '组合 VaR', value: '2.84%', note: '低于 3.50% 限额', tone: 'positive' },
    { label: '最大回撤', value: '-4.72%', note: '距预警线 1.28pct', tone: 'warning' },
    { label: '保证金使用率', value: '68.5%', note: '海外腿偏高', tone: 'warning' },
    { label: '集中度', value: '31.8%', note: '黄金主腿占比', tone: 'neutral' },
  ];

  const dimensionTabs: Array<{ key: DimensionKey; label: string }> = [
    { key: 'all', label: '全部' },
    { key: 'account', label: '账户' },
    { key: 'strategy', label: '策略' },
    { key: 'position', label: '持仓' },
    { key: 'product', label: '品种' },
  ];

  const riskDimensions: RiskDimension[] = [
    {
      category: 'account',
      name: '海外黄金账户',
      exposure: '9,765,941 CNY',
      leverage: '1.42X',
      margin: '72.8%',
      concentration: '28.4%',
      liquidity: '正常',
      usage: 76,
      status: '关注',
      tone: 'orange',
    },
    {
      category: 'strategy',
      name: '海内外价差',
      exposure: '21,773,757 CNY',
      leverage: '1.14X',
      margin: '68.5%',
      concentration: '31.8%',
      liquidity: '正常',
      usage: 69,
      status: '正常',
      tone: 'green',
    },
    {
      category: 'position',
      name: 'XAUUSD 空头腿',
      exposure: '4,305,580 CNY',
      leverage: '1.62X',
      margin: '83.6%',
      concentration: '18.7%',
      liquidity: '偏紧',
      usage: 84,
      status: '预警',
      tone: 'red',
    },
    {
      category: 'product',
      name: 'BTC 资费套利',
      exposure: '5,108,420 USD',
      leverage: '1.27X',
      margin: '54.2%',
      concentration: '16.5%',
      liquidity: '正常',
      usage: 58,
      status: '正常',
      tone: 'green',
    },
  ];

  const riskLimits = [
    {
      name: '组合 VaR',
      limit: '3.50%',
      current: '2.84%',
      usage: 81,
      status: '接近',
      tone: 'orange',
    },
    {
      name: '单策略回撤',
      limit: '6.00%',
      current: '4.72%',
      usage: 79,
      status: '关注',
      tone: 'orange',
    },
    {
      name: '保证金使用率',
      limit: '85.00%',
      current: '68.50%',
      usage: 81,
      status: '接近',
      tone: 'orange',
    },
    {
      name: '单品种集中度',
      limit: '40.00%',
      current: '31.80%',
      usage: 80,
      status: '正常',
      tone: 'green',
    },
    {
      name: '流动性缺口',
      limit: '8.00%',
      current: '3.20%',
      usage: 40,
      status: '正常',
      tone: 'green',
    },
  ];

  const assetStructure = [
    { name: '国内期货账户', detail: '沪金、沪银、股指', value: '12,007,816 CNY', percent: 37 },
    { name: '海外黄金账户', detail: 'XAUUSD 与保证金', value: '9,765,941 CNY', percent: 30 },
    { name: '数字资产账户', detail: 'BTC / ETH 资费腿', value: '6,842,190 USD', percent: 21 },
    { name: '现金与备用资金', detail: '多币种现金缓冲', value: '4,230,573 USD', percent: 12 },
  ];

  const riskRecords: RiskRecord[] = [
    {
      id: 'R-260712-01',
      time: '2026-07-12 14:42:10',
      target: '海外黄金账户',
      event: '预付款比例升至 83.6%，接近账户阈值',
      severity: 'high',
      status: 'processing',
      owner: '交易台',
    },
    {
      id: 'R-260712-02',
      time: '2026-07-12 13:28:44',
      target: '海内外价差',
      event: '汇率腿偏移扩大，需复核配平比例',
      severity: 'medium',
      status: 'pending',
      owner: '风控',
    },
    {
      id: 'R-260712-03',
      time: '2026-07-12 11:06:18',
      target: 'BTC 资费套利',
      event: '合约腿保证金占用回落',
      severity: 'low',
      status: 'done',
      owner: '策略',
    },
    {
      id: 'R-260711-08',
      time: '2026-07-11 22:18:39',
      target: '短线交易员A',
      event: '单品种集中度短时超过 30%',
      severity: 'medium',
      status: 'done',
      owner: '交易台',
    },
  ];

  const messages = [
    { id: 'M-01', time: '2026-07-12 14:45:00', title: '海外黄金账户保证金提醒', status: '未读' },
    { id: 'M-02', time: '2026-07-12 13:35:00', title: '海内外价差汇率腿复核', status: '未读' },
    { id: 'M-03', time: '2026-07-12 10:16:00', title: 'BTC 资费腿风险解除', status: '已读' },
  ];

  const auditLogs = [
    { id: 'A-01', time: '2026-07-12 14:48:18', operator: '风控', action: '调整海外账户预警等级' },
    { id: 'A-02', time: '2026-07-12 13:40:09', operator: '交易台', action: '提交海内外价差复核' },
    { id: 'A-03', time: '2026-07-12 10:20:31', operator: '系统', action: '完成资金占用重算' },
  ];

  const dimensionColumns: ColumnsType<RiskDimension> = [
    { title: '对象', dataIndex: 'name', key: 'name', width: 150 },
    { title: '敞口', dataIndex: 'exposure', key: 'exposure' },
    { title: '杠杆', dataIndex: 'leverage', key: 'leverage', width: 90 },
    { title: '保证金', dataIndex: 'margin', key: 'margin', width: 100 },
    { title: '集中度', dataIndex: 'concentration', key: 'concentration', width: 100 },
    { title: '流动性', dataIndex: 'liquidity', key: 'liquidity', width: 90 },
    { title: '使用率', key: 'usage', width: 160 },
    { title: '状态', key: 'status', width: 90 },
  ];

  const limitColumns: ColumnsType<(typeof riskLimits)[number]> = [
    { title: '指标', dataIndex: 'name', key: 'name' },
    { title: '阈值', dataIndex: 'limit', key: 'limit', width: 90 },
    { title: '当前', dataIndex: 'current', key: 'current', width: 90 },
    { title: '使用率', key: 'usage', width: 150 },
    { title: '状态', key: 'status', width: 90 },
  ];

  const recordColumns: ColumnsType<RiskRecord> = [
    { title: '时间', dataIndex: 'time', key: 'time', width: 170 },
    { title: '对象', dataIndex: 'target', key: 'target', width: 140 },
    { title: '事件', dataIndex: 'event', key: 'event' },
    { title: '等级', key: 'severity', width: 90 },
    { title: '处理', key: 'status', width: 100 },
    { title: '负责', dataIndex: 'owner', key: 'owner', width: 90 },
  ];

  const messageColumns: ColumnsType<(typeof messages)[number]> = [
    { title: '时间', dataIndex: 'time', key: 'time', width: 170 },
    { title: '消息', dataIndex: 'title', key: 'title' },
    { title: '状态', key: 'status', width: 90 },
  ];

  const auditColumns: ColumnsType<(typeof auditLogs)[number]> = [
    { title: '时间', dataIndex: 'time', key: 'time', width: 170 },
    { title: '操作人', dataIndex: 'operator', key: 'operator', width: 100 },
    { title: '动作', dataIndex: 'action', key: 'action' },
  ];

  const filteredDimensions = computed(() =>
    activeDimension.value === 'all'
      ? riskDimensions
      : riskDimensions.filter((item) => item.category === activeDimension.value),
  );

  const filteredRecords = computed(() => {
    const text = keyword.value.trim();
    return riskRecords.filter((item) => {
      const matchKeyword =
        !text ||
        `${item.target}${item.event}${item.owner}`.toLowerCase().includes(text.toLowerCase());
      const matchSeverity =
        severityFilter.value === 'all' || item.severity === severityFilter.value;
      const matchStatus = statusFilter.value === 'all' || item.status === statusFilter.value;
      return matchKeyword && matchSeverity && matchStatus;
    });
  });

  function refreshRisk() {
    loading.value = true;
    window.setTimeout(() => {
      latestRefresh.value = new Date()
        .toLocaleString('zh-CN', { hour12: false })
        .replace(/\//g, '-');
      loading.value = false;
    }, 300);
  }

  function severityColor(value: Severity) {
    return value === 'high' ? 'red' : value === 'medium' ? 'orange' : 'green';
  }

  function severityLabel(value: Severity) {
    return value === 'high' ? '高风险' : value === 'medium' ? '中风险' : '低风险';
  }

  function statusColor(value: RecordStatus) {
    return value === 'pending' ? 'orange' : value === 'processing' ? 'blue' : 'green';
  }

  function statusLabel(value: RecordStatus) {
    return value === 'pending' ? '待处理' : value === 'processing' ? '处理中' : '处理完成';
  }
</script>

<style scoped lang="less">
  .risk-detail-page {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px 4px 18px;
  }

  .risk-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 16px 18px;
    border: 1px solid #dbe4ed;
    border-radius: 8px;
    background: #fff;
  }

  .risk-toolbar h2 {
    margin: 0;
    color: #17212f;
    font-size: 22px;
    font-weight: 800;
  }

  .risk-toolbar p {
    margin: 6px 0 0;
    color: #5b6572;
  }

  .toolbar-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
  }

  .summary-grid {
    margin: 0;
  }

  .metric-card,
  .vg-panel {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .metric-card span {
    display: block;
    color: #59636e;
    font-size: 13px;
    font-weight: 700;
  }

  .metric-card strong {
    display: block;
    margin-top: 8px;
    color: #17212f;
    font-size: 22px;
    line-height: 1.25;
  }

  .metric-card em {
    display: block;
    margin-top: 6px;
    font-style: normal;
    font-size: 12px;
  }

  .tone-positive {
    color: #14804a;
  }

  .tone-warning {
    color: #a15c00;
  }

  .tone-danger {
    color: #b42318;
  }

  .tone-neutral {
    color: #59636e;
  }

  .dimension-tabs,
  .record-toolbar {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
  }

  .dimension-tabs button {
    height: 32px;
    padding: 0 12px;
    border: 1px solid #d8e1ea;
    border-radius: 6px;
    background: #f7f9fb;
    color: #344054;
    font-weight: 700;
  }

  .dimension-tabs button.active {
    border-color: #2f6fed;
    background: #eef5ff;
    color: #1f5cc4;
  }

  .filter-select {
    width: 132px;
  }

  .asset-list {
    display: grid;
    gap: 14px;
  }

  .asset-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px 12px;
  }

  .asset-row b,
  .asset-row strong {
    color: #17212f;
  }

  .asset-row span {
    display: block;
    margin-top: 2px;
    color: #667085;
    font-size: 12px;
  }

  .asset-row :deep(.ant-progress) {
    grid-column: 1 / -1;
  }

  .mt-3 {
    margin-top: 12px;
  }

  @media (max-width: 900px) {
    .risk-toolbar {
      align-items: flex-start;
      flex-direction: column;
    }

    .toolbar-actions {
      justify-content: flex-start;
    }
  }
</style>
