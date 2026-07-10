<template>
  <PageWrapper title="消息通知">
    <div class="notification-page">
      <div class="toolbar">
        <Space>
          <Tag :color="unreadCount ? 'orange' : 'green'">未读 {{ unreadCount }}</Tag>
          <Tag>消息 {{ messages.length }}</Tag>
        </Space>
        <Space>
          <Button :disabled="!messages.length" @click="readAll">全部已读</Button>
          <Button :loading="loading" @click="loadMessages">
            <template #icon><ReloadOutlined /></template>
            刷新
          </Button>
        </Space>
      </div>

      <Row :gutter="[16, 16]" class="mb-4">
        <Col :xs="24" :md="8">
          <Card :bordered="false" class="metric-card">
            <Statistic title="全部消息" :value="messages.length" />
          </Card>
        </Col>
        <Col :xs="24" :md="8">
          <Card :bordered="false" class="metric-card">
            <Statistic title="未读消息" :value="unreadCount" />
          </Card>
        </Col>
        <Col :xs="24" :md="8">
          <Card :bordered="false" class="metric-card">
            <Statistic title="最近时间" :value="latestTime || '-'" />
          </Card>
        </Col>
      </Row>

      <Card :bordered="false" title="消息列表" class="vg-panel">
        <Table
          :row-key="rowKey"
          size="middle"
          :columns="columns"
          :data-source="messages"
          :loading="loading"
          :pagination="{ pageSize: 10 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'title'">
              <div class="strong-cell">{{ record.title || record.subject || '-' }}</div>
              <div class="muted-cell">{{ record.content || record.message || record.description || '-' }}</div>
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="isUnread(record) ? 'orange' : 'green'">{{ isUnread(record) ? '未读' : '已读' }}</Tag>
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
  import { getNotificationList, NotificationMessage } from '@/api/riskControl';

  const loading = ref(false);
  const messages = ref<NotificationMessage[]>([]);

  const unreadCount = computed(() => messages.value.filter(isUnread).length);
  const latestTime = computed(() => {
    const times = messages.value.map((item) => item.created_at || item.createdAt).filter(Boolean).sort();
    return times[times.length - 1] || '';
  });

  const columns = [
    { title: '消息', key: 'title' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  ];

  function isUnread(record: NotificationMessage) {
    return record.status === 'unread' || record.read === false || record.isRead === false;
  }

  function rowKey(record: NotificationMessage, index?: number) {
    return record.id || record.message_id || `${record.created_at || 'notification'}-${index ?? 0}`;
  }

  function readAll() {
    messages.value = messages.value.map((item) => ({
      ...item,
      status: item.status === 'unread' ? 'read' : item.status,
      read: item.read === false ? true : item.read,
      isRead: item.isRead === false ? true : item.isRead,
    }));
  }

  async function loadMessages() {
    loading.value = true;
    try {
      messages.value = await getNotificationList();
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadMessages);
</script>

<style scoped>
  .notification-page {
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
    .notification-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
