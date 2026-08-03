<template>
  <PageWrapper title="风控详情">
    <div class="risk-detail-page">
      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="health.status === 'ok' ? 'green' : 'orange'">
            {{ health.service || 'data-service' }} {{ health.status || 'unknown' }}
          </Tag>
          <Tag>最新事件 {{ latestEventTime || '-' }}</Tag>
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
            <Statistic title="总资产 USD" :value="totalAsset" :precision="2" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :xl="4">
          <Card :bordered="false" class="metric-card">
            <Statistic title="可用资金 USD" :value="availableFund" :precision="2" />
          </Card>
        </Col>
      </Row>

      <Card :bordered="false" title="风控总览" class="vg-panel">
        <Table
          row-key="id"
          size="middle"
          :columns="riskColumns"
          :data-source="riskRecords"
          :loading="loading"
          :pagination="{ pageSize: 8 }"
        >
          <template #bodyCell="{ column, record, index }">
            <template v-if="column.key === 'id'">{{ record.id || index + 1 }}</template>
            <template v-else-if="column.key === 'severity'">
              <Tag :color="severityColor(record.severity)">{{ record.severity || 'low' }}</Tag>
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="record.status === 'pending' ? 'orange' : 'green'">{{ record.status || 'resolved' }}</Tag>
            </template>
          </template>
        </Table>
      </Card>

      <section class="account-reports-grid">
        <Card :bordered="false" title="账户管理" class="vg-panel account-panel">
          <LegacyStrategyCoverage />
        </Card>

        <div class="reports-stack">
          <Card :bordered="false" title="报表中心 - 风控记录" class="vg-panel">
            <Table
              row-key="id"
              size="small"
              :columns="reportRiskColumns"
              :data-source="riskRecords"
              :loading="loading"
              :pagination="{ pageSize: 5 }"
            >
              <template #bodyCell="{ column, record, index }">
                <template v-if="column.key === 'id'">{{ record.id || index + 1 }}</template>
                <template v-else-if="column.key === 'severity'">
                  <Tag :color="severityColor(record.severity)">{{ record.severity || 'low' }}</Tag>
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="record.status === 'pending' ? 'orange' : 'green'">{{ record.status || 'resolved' }}</Tag>
                </template>
              </template>
            </Table>
          </Card>

          <Card :bordered="false" title="报表中心 - 通知消息" class="vg-panel">
            <Table
              :row-key="notificationRowKey"
              size="small"
              :columns="notificationColumns"
              :data-source="notifications"
              :loading="loading"
              :pagination="{ pageSize: 5 }"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'title'">
                  <div class="strong-cell">{{ record.title || record.subject || '-' }}</div>
                  <div class="muted-cell">{{ record.content || record.message || record.description || '-' }}</div>
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="notificationStatusColor(record)">{{ record.status || (record.read ? 'read' : 'unread') }}</Tag>
                </template>
              </template>
            </Table>
          </Card>
        </div>
      </section>

      <section class="audit-monitor-grid">
        <Card :bordered="false" title="审计日志" class="vg-panel">
          <Table
            row-key="key"
            size="middle"
            :columns="auditColumns"
            :data-source="auditRows"
            :loading="loading"
            :pagination="false"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <Tag :color="record.color">{{ record.status }}</Tag>
              </template>
            </template>
          </Table>
        </Card>

        <div class="monitor-stack">
          <Card :bordered="false" title="系统监控 - data-service" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="状态">
                <Tag :color="health.status === 'ok' ? 'green' : 'orange'">{{ health.status }}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="服务">{{ health.service || 'data-service' }}</Descriptions.Item>
              <Descriptions.Item label="同步频率">{{ health.update_frequency || '-' }}</Descriptions.Item>
              <Descriptions.Item label="端口">8082</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card :bordered="false" title="系统监控 - auth-service" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="状态">
                <Tag color="green">已连接</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="登录用户">{{ userInfo.username || userInfo.name || '-' }}</Descriptions.Item>
              <Descriptions.Item label="角色">{{ roleLabel }}</Descriptions.Item>
              <Descriptions.Item label="端口">8080</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card :bordered="false" title="资产结构快照" class="vg-panel">
            <Table
              row-key="name"
              size="small"
              :columns="ratioColumns"
              :data-source="ratioItems"
              :loading="loading"
              :pagination="false"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'value'">
                  {{ formatMoney(record.valueUSD ?? record.value) }}
                </template>
                <template v-else-if="column.key === 'percent'">
                  <Progress :percent="percentNumber(record.percent)" size="small" />
                </template>
              </template>
            </Table>
          </Card>
        </div>
      </section>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import {
    Button,
    Card,
    Col,
    Descriptions,
    Progress,
    Row,
    Space,
    Statistic,
    Table,
    Tag,
  } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import LegacyStrategyCoverage from '@/views/strategy/components/LegacyStrategyCoverage.vue';
  import {
    DataAccount,
    DataServiceHealth,
    ExchangeInfo,
    getAccounts,
    getDataHealth,
    getExchangeInfo,
    getNotificationList,
    getProductRatio,
    getRiskRecordList,
    getTotalAssetSummary,
    NotificationMessage,
    ProductRatioItem,
    RiskRecord,
    TotalAssetSummary,
  } from '@/api/riskControl';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { useUserStore } from '@/store/modules/user';
  import { formateNumStr } from '@/utils/formate';

  const loading = ref(false);
  const riskRecords = ref<RiskRecord[]>([]);
  const notifications = ref<NotificationMessage[]>([]);
  const accounts = ref<DataAccount[]>([]);
  const ratioItems = ref<ProductRatioItem[]>([]);
  const totalSummary = ref<TotalAssetSummary>({});
  const exchangeInfo = ref<ExchangeInfo>({});
  const health = ref<DataServiceHealth>({ status: 'unknown', service: 'data-service', update_frequency: '-' });

  const { roleLabel, roleColor } = useRoleAccess();
  const userStore = useUserStore();
  const userInfo = computed(() => userStore.getUserInfo as any);

  const pendingCount = computed(() => riskRecords.value.filter((item) => item.status === 'pending').length);
  const highCount = computed(() =>
    riskRecords.value.filter((item) => ['high', 'critical'].includes(item.severity || '')).length,
  );
  const unreadCount = computed(() => notifications.value.filter(isUnread).length);
  const latestEventTime = computed(() => {
    const riskTimes = riskRecords.value.map((item) => item.created_at).filter(Boolean);
    const notificationTimes = notifications.value.map((item) => item.created_at || item.createdAt).filter(Boolean);
    const times = [...riskTimes, ...notificationTimes].sort();
    return times[times.length - 1] || '';
  });
  const totalAsset = computed(() => {
    const fromApi = totalSummary.value.total_asset ?? totalSummary.value.total;
    if (typeof fromApi === 'number') return fromApi;
    return accounts.value.reduce((sum, item) => sum + Number(item.total_asset || 0), 0);
  });
  const availableFund = computed(() =>
    accounts.value.reduce((sum, item) => sum + Number(item.available_fund || 0), 0),
  );

  const riskColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '内容', dataIndex: 'content', key: 'content' },
    { title: '等级', dataIndex: 'severity', key: 'severity', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  ];

  const reportRiskColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 70 },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '等级', dataIndex: 'severity', key: 'severity', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  ];

  const notificationColumns = [
    { title: '消息', key: 'title' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 170 },
  ];

  const auditColumns = [
    { title: '模块', dataIndex: 'module', key: 'module' },
    { title: '来源', dataIndex: 'source', key: 'source' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 110 },
    { title: '最近记录', dataIndex: 'latest', key: 'latest', width: 180 },
  ];

  const ratioColumns = [
    { title: '资产项', dataIndex: 'name', key: 'name' },
    { title: '金额 USD', key: 'value', align: 'right', width: 180 },
    { title: '占比', key: 'percent', width: 180 },
  ];

  const auditRows = computed(() => [
    {
      key: 'auth',
      module: '认证登录',
      source: 'auth-service /login /me',
      status: '已接入',
      color: 'green',
      latest: '-',
    },
    {
      key: 'data',
      module: '数据同步',
      source: 'data-service /api/v1/data/sync',
      status: health.value.status === 'ok' ? '已连接' : '异常',
      color: health.value.status === 'ok' ? 'green' : 'orange',
      latest: health.value.update_frequency || '-',
    },
    {
      key: 'risk',
      module: '风控记录',
      source: '/risk/api/v1/risk-records/',
      status: '已接入',
      color: 'green',
      latest: riskRecords.value[0]?.created_at || '-',
    },
    {
      key: 'notification',
      module: '消息通知',
      source: '/notifications/api/v1/messages/',
      status: '已接入',
      color: 'green',
      latest: latestEventTime.value || '-',
    },
    {
      key: 'exchange',
      module: '汇率接口',
      source: '/exchange/',
      status: exchangeInfo.value.rate ? '已接入' : '待检查',
      color: exchangeInfo.value.rate ? 'green' : 'orange',
      latest: exchangeInfo.value.updated_at || '-',
    },
  ]);

  function severityColor(severity?: string) {
    if (severity === 'critical') return 'red';
    if (severity === 'high') return 'orange';
    if (severity === 'medium') return 'gold';
    return 'blue';
  }

  function notificationStatusColor(record: any) {
    if (record.status === 'unread' || record.read === false || record.isRead === false) return 'orange';
    if (record.status === 'failed') return 'red';
    return 'green';
  }

  function notificationRowKey(record: any, index?: number) {
    return record.id || record.message_id || `${record.created_at || 'notification'}-${index ?? 0}`;
  }

  function isUnread(record: NotificationMessage) {
    return record.status === 'unread' || record.read === false || record.isRead === false;
  }

  function formatMoney(value: any) {
    return formateNumStr(value || 0, { decimals: 2, keepZero: true });
  }

  function percentNumber(value: any) {
    return Number((Number(value || 0) * 100).toFixed(2));
  }

  async function loadAll() {
    loading.value = true;
    try {
      const [riskRes, notifyRes, accountRes, ratioRes, totalRes, exchangeRes, healthRes] = await Promise.all([
        getRiskRecordList(),
        getNotificationList(),
        getAccounts(),
        getProductRatio(),
        getTotalAssetSummary(),
        getExchangeInfo(),
        getDataHealth(),
      ]);
      riskRecords.value = riskRes;
      notifications.value = notifyRes;
      accounts.value = accountRes;
      ratioItems.value = ratioRes;
      totalSummary.value = totalRes;
      exchangeInfo.value = exchangeRes;
      health.value = healthRes;
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

  .account-reports-grid,
  .audit-monitor-grid {
    display: grid;
    grid-template-columns: 1.35fr 1fr;
    gap: 16px;
    margin-top: 16px;
  }

  .account-panel :deep(.page-wrapper),
  .account-panel :deep(.ant-page-header) {
    display: none;
  }

  .reports-stack,
  .monitor-stack {
    display: grid;
    gap: 16px;
  }

  .strong-cell {
    font-weight: 600;
  }

  .muted-cell {
    margin-top: 4px;
    color: #59636e;
    font-size: 12px;
  }

  @media (max-width: 1280px) {
    .account-reports-grid,
    .audit-monitor-grid {
      grid-template-columns: 1fr;
    }
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
