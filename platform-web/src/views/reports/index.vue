<template>
  <PageWrapper title="报表">
    <div class="reports-page">
      <ProductDataStatusAlert :meta="dataMeta" class="mb-4" />

      <div class="toolbar">
        <Space>
          <Tag color="orange">风控报表</Tag>
          <Tag color="blue">通知报表</Tag>
          <Tag>最近更新 {{ latestUpdate || '不可用' }}</Tag>
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
              <template #emptyText>
                <span>
                  {{ riskStatus === 'unavailable' ? '风控来源不可用' : '暂无风控记录' }}
                </span>
              </template>
              <template #bodyCell="{ column, record, index }">
                <template v-if="column.key === 'id'">{{ record.id || index + 1 }}</template>
                <template v-else-if="column.key === 'severity'">
                  <Tag :color="severityColor(record.severity)">
                    {{ record.severity || 'unknown' }}
                  </Tag>
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
              <template #emptyText>
                <span>
                  {{ notificationStatus === 'unavailable' ? '通知来源不可用' : '暂无通知消息' }}
                </span>
              </template>
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'title'">
                  <div class="strong-cell">
                    {{ record.title || record.subject || '未命名消息' }}
                  </div>
                  <div class="muted-cell">
                    {{ record.content || record.message || record.description || '无正文' }}
                  </div>
                </template>
                <template v-else-if="column.key === 'status'">
                  <Tag :color="notificationStatusColor(record)">
                    {{ record.status || (record.read ? 'read' : 'unread') }}
                  </Tag>
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
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { Button, Card, Col, Row, Space, Statistic, Table, Tag } from 'ant-design-vue';
  import { computed, onMounted, ref } from 'vue';
  import type { ProductDataMeta } from '@/api/platform/productDataState';
  import {
    getNotificationList,
    getRiskRecordList,
    type NotificationMessage,
    type RiskRecord,
  } from '@/api/riskControl';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';

  type SourceStatus = 'ready' | 'no_data' | 'unavailable';

  const loading = ref(false);
  const riskRecords = ref<RiskRecord[]>([]);
  const notifications = ref<NotificationMessage[]>([]);
  const riskStatus = ref<SourceStatus>('no_data');
  const notificationStatus = ref<SourceStatus>('no_data');
  const dataMeta = ref<ProductDataMeta>({
    status: 'no_data',
    source: 'report aggregation',
    timezone: 'source-defined',
    unit: 'report row',
    message: '尚未加载报表数据',
  });

  const pendingCount = computed(
    () => riskRecords.value.filter((item) => item.status === 'pending').length,
  );
  const highCount = computed(
    () => riskRecords.value.filter((item) => ['high', 'critical'].includes(item.severity || '')).length,
  );
  const unreadCount = computed(
    () =>
      notifications.value.filter(
        (item) => item.status === 'unread' || item.read === false || item.isRead === false,
      ).length,
  );
  const latestUpdate = computed(() =>
    [
      ...riskRecords.value.map((item) => item.created_at),
      ...notifications.value.map((item) => item.created_at || item.createdAt),
    ]
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1),
  );

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

  function notificationStatusColor(record: NotificationMessage) {
    if (record.status === 'unread' || record.read === false || record.isRead === false) {
      return 'orange';
    }
    if (record.status === 'failed') return 'red';
    return 'green';
  }

  function notificationRowKey(record: NotificationMessage, index?: number) {
    return record.id || record.message_id || `${record.created_at || 'notification'}-${index ?? 0}`;
  }

  async function loadReport() {
    loading.value = true;
    const [riskResult, notificationResult] = await Promise.allSettled([
      getRiskRecordList(),
      getNotificationList(),
    ]);
    try {
      if (riskResult.status === 'fulfilled') {
        riskRecords.value = riskResult.value;
        riskStatus.value = riskResult.value.length ? 'ready' : 'no_data';
      } else {
        riskRecords.value = [];
        riskStatus.value = 'unavailable';
      }
      if (notificationResult.status === 'fulfilled') {
        notifications.value = notificationResult.value;
        notificationStatus.value = notificationResult.value.length ? 'ready' : 'no_data';
      } else {
        notifications.value = [];
        notificationStatus.value = 'unavailable';
      }

      const unavailable = [riskStatus.value, notificationStatus.value].filter(
        (status) => status === 'unavailable',
      ).length;
      const ready = [riskStatus.value, notificationStatus.value].filter(
        (status) => status === 'ready',
      ).length;
      dataMeta.value = {
        status: unavailable ? 'unavailable' : ready ? 'ready' : 'no_data',
        source: unavailable ? 'report aggregation (partial)' : 'report aggregation',
        asOf: latestUpdate.value,
        timezone: 'source-defined',
        unit: 'report row',
        errorCode: unavailable ? 'partial_source_failure' : undefined,
        message: unavailable
          ? `${unavailable}个报表来源不可用；未用空数组冒充完整结果`
          : ready
            ? undefined
            : '所有来源成功，但没有报表记录',
        degraded: unavailable > 0,
      };
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
