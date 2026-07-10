<template>
  <PageWrapper title="审计日志">
    <div class="audit-page">
      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="health.status === 'ok' ? 'green' : 'orange'">data-service {{ health.status || 'unknown' }}</Tag>
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
            <Statistic title="最近事件" :value="latestEventTime || '-'" />
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
              <Tag :color="record.color">{{ record.status }}</Tag>
            </template>
          </template>
        </Table>
      </Card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Row, Space, Statistic, Table, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import {
    DataServiceHealth,
    getDataHealth,
    getNotificationList,
    getRiskRecordList,
    NotificationMessage,
    RiskRecord,
  } from '@/api/riskControl';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';

  const loading = ref(false);
  const riskRecords = ref<RiskRecord[]>([]);
  const notifications = ref<NotificationMessage[]>([]);
  const health = ref<DataServiceHealth>({ status: 'unknown', service: 'data-service', update_frequency: '-' });
  const { roleLabel, roleColor } = useRoleAccess();

  const unreadCount = computed(() => notifications.value.filter(isUnread).length);
  const latestEventTime = computed(() => {
    const riskTimes = riskRecords.value.map((item) => item.created_at).filter(Boolean);
    const notificationTimes = notifications.value.map((item) => item.created_at || item.createdAt).filter(Boolean);
    const times = [...riskTimes, ...notificationTimes].sort();
    return times[times.length - 1] || '';
  });
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
  ]);

  const columns = [
    { title: '模块', dataIndex: 'module', key: 'module' },
    { title: '来源', dataIndex: 'source', key: 'source' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 110 },
    { title: '最近记录', dataIndex: 'latest', key: 'latest', width: 180 },
  ];

  function isUnread(record: NotificationMessage) {
    return record.status === 'unread' || record.read === false || record.isRead === false;
  }

  async function loadAudit() {
    loading.value = true;
    try {
      const [riskRes, notificationRes, healthRes] = await Promise.all([
        getRiskRecordList(),
        getNotificationList(),
        getDataHealth(),
      ]);
      riskRecords.value = riskRes;
      notifications.value = notificationRes;
      health.value = healthRes;
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
