<template>
  <PageWrapper title="审计日志">
    <div class="audit-page">
      <ProductDataStatusAlert :meta="dataMeta" class="mb-4" />

      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag>聚合读取</Tag>
        </Space>
        <Button :loading="loading" @click="loadAudit">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <Row :gutter="[16, 16]" class="mb-4">
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="风控记录" :value="riskRecords.length" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="通知消息" :value="notifications.length" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="未读消息" :value="unreadCount" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="最近事件" :value="latestEventTime || '不可用'" />
          </Card>
        </Col>
      </Row>

      <Card :bordered="false" title="审计来源" class="vg-panel">
        <Table
          row-key="key"
          size="middle"
          :columns="columns"
          :data-source="auditRows"
          :loading="loading"
          :pagination="false"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <Tag :color="statusColor(record.status)">{{ record.status }}</Tag>
            </template>
          </template>
        </Table>
      </Card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { Button, Card, Col, Row, Space, Statistic, Table, Tag } from 'ant-design-vue';
  import { computed, onMounted, ref } from 'vue';
  import type { ProductDataMeta } from '@/api/platform/productDataState';
  import {
    type DataServiceHealth,
    getDataHealth,
    getNotificationList,
    getRiskRecordList,
    type NotificationMessage,
    type RiskRecord,
  } from '@/api/riskControl';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';

  type SourceStatus = 'ready' | 'no_data' | 'unavailable';

  const loading = ref(false);
  const riskRecords = ref<RiskRecord[]>([]);
  const notifications = ref<NotificationMessage[]>([]);
  const health = ref<DataServiceHealth>({
    status: 'unknown',
    service: 'data-service',
    update_frequency: 'unknown',
  });
  const sourceStatus = ref<Record<string, SourceStatus>>({
    risk: 'no_data',
    notification: 'no_data',
    data: 'no_data',
  });
  const sourceErrors = ref<Record<string, string>>({});
  const dataMeta = ref<ProductDataMeta>({
    status: 'no_data',
    source: 'audit aggregation',
    timezone: 'source-defined',
    unit: 'audit event',
    message: '尚未加载审计来源',
  });
  const { roleLabel, roleColor } = useRoleAccess();

  const unreadCount = computed(() => notifications.value.filter(isUnread).length);
  const latestEventTime = computed(() =>
    [
      ...riskRecords.value.map((item) => item.created_at),
      ...notifications.value.map((item) => item.created_at || item.createdAt),
    ]
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1),
  );
  const auditRows = computed(() => [
    {
      key: 'data',
      module: '数据服务状态',
      source: 'data-service /health',
      status: sourceStatus.value.data,
      latest: health.value.as_of || health.value.update_frequency || '不可用',
      error: sourceErrors.value.data,
    },
    {
      key: 'risk',
      module: '风控记录',
      source: 'risk-service /risk/api/v1/risk-records/',
      status: sourceStatus.value.risk,
      latest:
        riskRecords.value
          .map((item) => item.created_at)
          .filter(Boolean)
          .sort()
          .at(-1) || '不可用',
      error: sourceErrors.value.risk,
    },
    {
      key: 'notification',
      module: '消息通知',
      source: 'notification-service /notifications/api/v1/messages/',
      status: sourceStatus.value.notification,
      latest: latestEventTime.value || '不可用',
      error: sourceErrors.value.notification,
    },
  ]);

  const columns = [
    { title: '模块', dataIndex: 'module', key: 'module' },
    { title: '来源', dataIndex: 'source', key: 'source' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
    { title: '最近记录', dataIndex: 'latest', key: 'latest', width: 190 },
    { title: '错误', dataIndex: 'error', key: 'error' },
  ];

  function isUnread(record: NotificationMessage) {
    return record.status === 'unread' || record.read === false || record.isRead === false;
  }

  function statusColor(status: SourceStatus) {
    if (status === 'ready') return 'green';
    if (status === 'unavailable') return 'red';
    return 'blue';
  }

  async function loadAudit() {
    loading.value = true;
    sourceErrors.value = {};
    const results = await Promise.allSettled([
      getRiskRecordList(),
      getNotificationList(),
      getDataHealth(),
    ]);
    try {
      const [riskResult, notificationResult, healthResult] = results;
      if (riskResult.status === 'fulfilled') {
        riskRecords.value = riskResult.value;
        sourceStatus.value.risk = riskResult.value.length ? 'ready' : 'no_data';
      } else {
        riskRecords.value = [];
        sourceStatus.value.risk = 'unavailable';
        sourceErrors.value.risk = String(
          riskResult.reason?.message || riskResult.reason || 'request failed',
        );
      }
      if (notificationResult.status === 'fulfilled') {
        notifications.value = notificationResult.value;
        sourceStatus.value.notification = notificationResult.value.length ? 'ready' : 'no_data';
      } else {
        notifications.value = [];
        sourceStatus.value.notification = 'unavailable';
        sourceErrors.value.notification = String(
          notificationResult.reason?.message || notificationResult.reason || 'request failed',
        );
      }
      if (healthResult.status === 'fulfilled') {
        health.value = healthResult.value;
        sourceStatus.value.data = healthResult.value.status === 'ok' ? 'ready' : 'unavailable';
        if (healthResult.value.status !== 'ok') {
          sourceErrors.value.data = `provider status=${healthResult.value.status}`;
        }
      } else {
        sourceStatus.value.data = 'unavailable';
        sourceErrors.value.data = String(
          healthResult.reason?.message || healthResult.reason || 'request failed',
        );
      }

      const unavailable = Object.values(sourceStatus.value).filter(
        (status) => status === 'unavailable',
      ).length;
      const ready = Object.values(sourceStatus.value).filter(
        (status) => status === 'ready',
      ).length;
      dataMeta.value = {
        status: unavailable ? 'unavailable' : ready ? 'ready' : 'no_data',
        source: unavailable ? 'audit aggregation (partial)' : 'audit aggregation',
        asOf: latestEventTime.value || health.value.as_of,
        timezone: 'source-defined',
        unit: 'audit event',
        errorCode: unavailable ? 'partial_source_failure' : undefined,
        message: unavailable
          ? `${unavailable}个审计来源不可用；成功来源的数据未被伪装为完整结果`
          : ready
            ? undefined
            : '所有来源均成功，但没有审计记录',
        degraded: unavailable > 0,
      };
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadAudit);
</script>

<style scoped>
  .audit-page {
    padding: 16px;
  }

  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

  .metric-card,
  .vg-panel {
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  @media (max-width: 768px) {
    .audit-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
