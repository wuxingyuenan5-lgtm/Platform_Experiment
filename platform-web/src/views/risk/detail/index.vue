<template>
  <PageWrapper title="风控详情">
    <div class="risk-detail-page">
      <ProductDataStatusAlert :meta="dataMeta" class="mb-4" />

      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="health.status === 'ok' ? 'green' : 'orange'">
            {{ health.service || 'data-service' }} {{ health.status || 'unavailable' }}
          </Tag>
          <Tag>最近事实 {{ latestEventTime || '不可用' }}</Tag>
        </Space>
        <Button :loading="loading" @click="loadAll">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <Row :gutter="[16, 16]" class="summary-grid">
        <Col :xs="24" :sm="12" :xl="4">
          <Card :bordered="false" class="metric-card">
            <Statistic title="风控记录" :value="riskRecords.length" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :xl="4">
          <Card :bordered="false" class="metric-card">
            <Statistic title="待处理" :value="pendingCount" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :xl="4">
          <Card :bordered="false" class="metric-card">
            <Statistic title="高风险" :value="highCount" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :xl="4">
          <Card :bordered="false" class="metric-card">
            <Statistic title="未读消息" :value="unreadCount" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :xl="4">
          <Card :bordered="false" class="metric-card">
            <span class="metric-label">总资产</span>
            <strong class="metric-value">{{ formatMoney(totalAsset) }}</strong>
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :xl="4">
          <Card :bordered="false" class="metric-card">
            <span class="metric-label">可用资金</span>
            <strong class="metric-value">{{ formatMoney(availableFund) }}</strong>
          </Card>
        </Col>
      </Row>

      <Row :gutter="[16, 16]">
        <Col :xs="24" :xl="14">
          <Card :bordered="false" title="风控记录" class="vg-panel">
            <Table
              row-key="id"
              size="middle"
              :columns="riskColumns"
              :data-source="riskRecords"
              :loading="loading"
              :pagination="{ pageSize: 8 }"
            >
              <template #emptyText>
                <span>{{ sourceStatus.risk === 'unavailable' ? '风控来源不可用' : '暂无风控记录' }}</span>
              </template>
              <template #bodyCell="{ column, record, index }">
                <template v-if="column.key === 'id'">{{ record.id || index + 1 }}</template>
                <template v-else-if="column.key === 'severity'">
                  <Tag :color="severityColor(record.severity)">{{ record.severity || 'unknown' }}</Tag>
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="record.status === 'pending' ? 'orange' : 'green'">
                    {{ record.status || 'unknown' }}
                  </Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>
        <Col :xs="24" :xl="10">
          <Card :bordered="false" title="数据源状态" class="vg-panel">
            <Table
              row-key="key"
              size="small"
              :columns="sourceColumns"
              :data-source="sourceRows"
              :pagination="false"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <Tag :color="sourceStatusColor(record.status)">{{ record.status }}</Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>
      </Row>

      <Row :gutter="[16, 16]" class="mt-4">
        <Col :xs="24" :xl="12">
          <Card :bordered="false" title="通知事实" class="vg-panel">
            <Table
              :row-key="notificationRowKey"
              size="small"
              :columns="notificationColumns"
              :data-source="notifications"
              :loading="loading"
              :pagination="{ pageSize: 6 }"
            >
              <template #emptyText>
                <span>{{ sourceStatus.notification === 'unavailable' ? '通知来源不可用' : '暂无通知' }}</span>
              </template>
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'title'">
                  <div class="strong-cell">{{ record.title || record.subject || '未命名消息' }}</div>
                  <div class="muted-cell">
                    {{ record.content || record.message || record.description || '无正文' }}
                  </div>
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="isUnread(record) ? 'orange' : 'green'">
                    {{ isUnread(record) ? 'unread' : 'read' }}
                  </Tag>
                </template>
              </template>
            </Table>
          </Card>
        </Col>
        <Col :xs="24" :xl="12">
          <Card :bordered="false" title="资产结构" class="vg-panel">
            <Table
              row-key="name"
              size="small"
              :columns="ratioColumns"
              :data-source="ratioItems"
              :loading="loading"
              :pagination="false"
            >
              <template #emptyText>
                <span>{{ sourceStatus.finance === 'unavailable' ? '财务来源不可用' : '暂无资产结构' }}</span>
              </template>
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'value'">
                  {{ formatMoney(record.valueUSD ?? record.value) }}
                </template>
                <template v-else-if="column.key === 'percent'">
                  {{ formatPercent(record.percent) }}
                </template>
              </template>
            </Table>
          </Card>
        </Col>
      </Row>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import Decimal from 'decimal.js';
  import { computed, onMounted, reactive, ref } from 'vue';
  import { Button, Card, Col, Row, Space, Statistic, Table, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import {
    type DataAccount,
    type DataServiceHealth,
    getAccounts,
    getDataHealth,
    getExchangeInfo,
    getNotificationList,
    getProductRatio,
    getRiskRecordList,
    getTotalAssetSummary,
    type ExchangeInfo,
    type NotificationMessage,
    type ProductRatioItem,
    type RiskRecord,
    type TotalAssetSummary,
  } from '@/api/riskControl';
  import {
    type DecimalString,
    type ProductDataMeta,
  } from '@/api/platform/productDataState';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { formatMoneyString, formatRatioPercentString } from '@/utils/decimalDisplay';

  type SourceStatus = 'ready' | 'no_data' | 'unavailable';

  const loading = ref(false);
  const riskRecords = ref<RiskRecord[]>([]);
  const notifications = ref<NotificationMessage[]>([]);
  const accounts = ref<DataAccount[]>([]);
  const ratioItems = ref<ProductRatioItem[]>([]);
  const totalSummary = ref<TotalAssetSummary>({});
  const exchangeInfo = ref<ExchangeInfo>({});
  const health = ref<DataServiceHealth>({
    status: 'unknown',
    service: 'data-service',
    update_frequency: 'unknown',
  });
  const sourceStatus = reactive<Record<string, SourceStatus>>({
    risk: 'no_data',
    notification: 'no_data',
    finance: 'no_data',
    health: 'no_data',
  });
  const sourceErrors = reactive<Record<string, string>>({});
  const dataMeta = ref<ProductDataMeta>({
    status: 'no_data',
    source: 'risk detail aggregation',
    timezone: 'source-defined',
    currency: 'USD',
    unit: 'risk and account facts',
    precision: 'decimal-string',
    message: '尚未加载风控事实',
  });

  const { roleLabel, roleColor } = useRoleAccess();
  const pendingCount = computed(() => riskRecords.value.filter((item) => item.status === 'pending').length);
  const highCount = computed(() =>
    riskRecords.value.filter((item) => ['high', 'critical'].includes(item.severity || '')).length,
  );
  const unreadCount = computed(() => notifications.value.filter(isUnread).length);
  const latestEventTime = computed(() =>
    [
      ...riskRecords.value.map((item) => item.created_at),
      ...notifications.value.map((item) => item.created_at || item.createdAt),
      ...accounts.value.map((item) => item.asset_updated_at),
      totalSummary.value.updated_at,
      exchangeInfo.value.updated_at,
      health.value.as_of,
    ]
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1),
  );

  function sumAccountField(field: 'total_asset' | 'available_fund'): DecimalString | undefined {
    const values = accounts.value.map((item) => item[field]).filter((value): value is string => value !== undefined);
    if (!values.length) return undefined;
    return values.reduce((sum, value) => sum.plus(value), new Decimal(0)).toFixed();
  }

  const totalAsset = computed<DecimalString | undefined>(
    () => totalSummary.value.total_asset ?? totalSummary.value.total ?? sumAccountField('total_asset'),
  );
  const availableFund = computed<DecimalString | undefined>(() => sumAccountField('available_fund'));

  const riskColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '内容', dataIndex: 'content', key: 'content' },
    { title: '等级', dataIndex: 'severity', key: 'severity', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  ];
  const sourceColumns = [
    { title: '来源', dataIndex: 'label', key: 'label' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 110 },
    { title: '截至/错误', dataIndex: 'detail', key: 'detail' },
  ];
  const notificationColumns = [
    { title: '消息', key: 'title' },
    { title: '状态', key: 'status', width: 100 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  ];
  const ratioColumns = [
    { title: '资产项', dataIndex: 'name', key: 'name' },
    { title: '金额 USD', key: 'value', align: 'right', width: 180 },
    { title: '占比', key: 'percent', width: 130 },
  ];

  const sourceRows = computed(() => [
    {
      key: 'risk',
      label: 'risk-service',
      status: sourceStatus.risk,
      detail: sourceErrors.risk || riskRecords.value.map((item) => item.created_at).filter(Boolean).sort().at(-1) || '不可用',
    },
    {
      key: 'notification',
      label: 'notification-service',
      status: sourceStatus.notification,
      detail: sourceErrors.notification || notifications.value.map((item) => item.created_at || item.createdAt).filter(Boolean).sort().at(-1) || '不可用',
    },
    {
      key: 'finance',
      label: 'data-service finance',
      status: sourceStatus.finance,
      detail: sourceErrors.finance || totalSummary.value.updated_at || exchangeInfo.value.updated_at || '不可用',
    },
    {
      key: 'health',
      label: 'data-service health',
      status: sourceStatus.health,
      detail: sourceErrors.health || health.value.as_of || health.value.update_frequency || '不可用',
    },
  ]);

  function severityColor(severity?: string) {
    if (severity === 'critical') return 'red';
    if (severity === 'high') return 'orange';
    if (severity === 'medium') return 'gold';
    return 'blue';
  }

  function isUnread(record: NotificationMessage) {
    return record.status === 'unread' || record.read === false || record.isRead === false;
  }

  function notificationRowKey(record: NotificationMessage, index?: number) {
    return record.id || record.message_id || `${record.created_at || 'notification'}-${index ?? 0}`;
  }

  function sourceStatusColor(status: SourceStatus) {
    if (status === 'ready') return 'green';
    if (status === 'unavailable') return 'red';
    return 'blue';
  }

  function formatMoney(value?: DecimalString) {
    return formatMoneyString(value, 'USD');
  }

  function formatPercent(value: DecimalString) {
    return formatRatioPercentString(value);
  }

  function setRejected(source: string, reason: unknown) {
    sourceStatus[source] = 'unavailable';
    sourceErrors[source] = reason instanceof Error ? reason.message : String(reason || 'request failed');
  }

  async function loadAll() {
    loading.value = true;
    Object.keys(sourceErrors).forEach((key) => delete sourceErrors[key]);
    const results = await Promise.allSettled([
      getRiskRecordList(),
      getNotificationList(),
      getAccounts(),
      getProductRatio(),
      getTotalAssetSummary(),
      getExchangeInfo(),
      getDataHealth(),
    ]);
    try {
      const [riskResult, notificationResult, accountResult, ratioResult, totalResult, exchangeResult, healthResult] = results;

      if (riskResult.status === 'fulfilled') {
        riskRecords.value = riskResult.value;
        sourceStatus.risk = riskResult.value.length ? 'ready' : 'no_data';
      } else {
        riskRecords.value = [];
        setRejected('risk', riskResult.reason);
      }

      if (notificationResult.status === 'fulfilled') {
        notifications.value = notificationResult.value;
        sourceStatus.notification = notificationResult.value.length ? 'ready' : 'no_data';
      } else {
        notifications.value = [];
        setRejected('notification', notificationResult.reason);
      }

      let financeFailures = 0;
      if (accountResult.status === 'fulfilled') accounts.value = accountResult.value;
      else {
        accounts.value = [];
        financeFailures += 1;
        sourceErrors.finance = String(accountResult.reason?.message || accountResult.reason || 'accounts failed');
      }
      if (ratioResult.status === 'fulfilled') ratioItems.value = ratioResult.value;
      else {
        ratioItems.value = [];
        financeFailures += 1;
        sourceErrors.finance = `${sourceErrors.finance || ''} ratio failed`.trim();
      }
      if (totalResult.status === 'fulfilled') totalSummary.value = totalResult.value;
      else {
        totalSummary.value = {};
        financeFailures += 1;
        sourceErrors.finance = `${sourceErrors.finance || ''} total failed`.trim();
      }
      if (exchangeResult.status === 'fulfilled') exchangeInfo.value = exchangeResult.value;
      else {
        exchangeInfo.value = {};
        financeFailures += 1;
        sourceErrors.finance = `${sourceErrors.finance || ''} exchange failed`.trim();
      }
      sourceStatus.finance = financeFailures
        ? 'unavailable'
        : accounts.value.length || ratioItems.value.length || totalAsset.value !== undefined
          ? 'ready'
          : 'no_data';

      if (healthResult.status === 'fulfilled') {
        health.value = healthResult.value;
        sourceStatus.health = healthResult.value.status === 'ok' ? 'ready' : 'unavailable';
        if (healthResult.value.status !== 'ok') {
          sourceErrors.health = `provider status=${healthResult.value.status}`;
        }
      } else {
        setRejected('health', healthResult.reason);
      }

      const statuses = Object.values(sourceStatus);
      const unavailable = statuses.filter((status) => status === 'unavailable').length;
      const ready = statuses.filter((status) => status === 'ready').length;
      dataMeta.value = {
        status: unavailable ? 'unavailable' : ready ? 'ready' : 'no_data',
        source: unavailable ? 'risk detail aggregation (partial)' : 'risk detail aggregation',
        asOf: latestEventTime.value,
        timezone: 'source-defined',
        currency: 'USD',
        unit: 'risk and account facts',
        precision: 'decimal-string',
        errorCode: unavailable ? 'partial_source_failure' : undefined,
        message: unavailable
          ? `${unavailable}个来源不可用；成功来源的事实仍单独保留`
          : ready
            ? undefined
            : '所有来源成功，但没有风控或账户事实',
        degraded: unavailable > 0,
      };
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadAll);
</script>

<style scoped>
  .risk-detail-page {
    padding: 16px;
  }

  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  .summary-grid {
    margin-bottom: 16px;
  }

  .metric-card,
  .vg-panel {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .metric-label {
    display: block;
    color: #59636e;
    font-size: 13px;
  }

  .metric-value {
    display: block;
    margin-top: 8px;
    font-size: 20px;
    line-height: 1.35;
  }

  .strong-cell {
    font-weight: 600;
  }

  .muted-cell {
    margin-top: 4px;
    color: #59636e;
    font-size: 12px;
  }

  @media (max-width: 768px) {
    .risk-detail-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
