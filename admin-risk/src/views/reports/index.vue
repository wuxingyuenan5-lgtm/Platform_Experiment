<template>
  <PageWrapper title="报表">
    <div class="reports-page">
      <div class="toolbar">
        <Space>
          <Tag color="orange">风控报表</Tag>
          <Tag color="blue">通知报表</Tag>
          <Tag>最近更新 {{ latestUpdate || '-' }}</Tag>
        </Space>
        <Button :loading="loading" @click="loadReport">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <Row :gutter="[16, 16]">
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="风控记录" :value="riskRecords.length" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="待处理" :value="pendingCount" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="高风险" :value="highCount" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="未读消息" :value="unreadCount" />
          </Card>
        </Col>
      </Row>

      <Row :gutter="[16, 16]" class="mt-4">
        <Col :xs="24" :xl="12">
          <Card :bordered="false" title="风控记录报表" class="vg-panel">
            <Table
              row-key="id"
              size="small"
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
        </Col>
        <Col :xs="24" :xl="12">
          <Card :bordered="false" title="通知消息报表" class="vg-panel">
            <Table
              :row-key="notificationRowKey"
              size="small"
              :columns="notificationColumns"
              :data-source="notifications"
              :loading="loading"
              :pagination="{ pageSize: 8 }"
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
        </Col>
      </Row>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Row, Space, Statistic, Table, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import { getNotificationList, getRiskRecordList, RiskRecord } from '@/api/riskControl';

  const loading = ref(false);
  const riskRecords = ref<RiskRecord[]>([]);
  const notifications = ref<any[]>([]);

  const pendingCount = computed(() => riskRecords.value.filter((item) => item.status === 'pending').length);
  const highCount = computed(() =>
    riskRecords.value.filter((item) => ['high', 'critical'].includes(item.severity || '')).length,
  );
  const unreadCount = computed(() =>
    notifications.value.filter((item) => item.status === 'unread' || item.read === false || item.isRead === false).length,
  );
  const latestUpdate = computed(() => {
    const riskTimes = riskRecords.value.map((item) => item.created_at).filter(Boolean);
    const notifyTimes = notifications.value.map((item) => item.created_at || item.createdAt).filter(Boolean);
    const times = [...riskTimes, ...notifyTimes].sort();
    return times[times.length - 1] || '';
  });

  const riskColumns = [
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

  async function loadReport() {
    loading.value = true;
    try {
      const [riskRes, notifyRes] = await Promise.all([getRiskRecordList(), getNotificationList()]);
      riskRecords.value = riskRes;
      notifications.value = notifyRes;
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadReport);
</script>

<style scoped>
  .reports-page {
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

  .strong-cell {
    font-weight: 600;
  }

  .muted-cell {
    margin-top: 4px;
    color: #59636e;
    font-size: 12px;
  }

  @media (max-width: 768px) {
    .reports-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
