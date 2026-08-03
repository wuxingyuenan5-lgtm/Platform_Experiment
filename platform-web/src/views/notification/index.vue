<template>
  <PageWrapper title="消息通知">
    <div class="notification-page">
      <ProductDataStatusAlert :meta="dataMeta" class="mb-4" />

      <div class="toolbar">
        <Space>
          <Tag :color="unreadCount ? 'orange' : 'green'">未读 {{ unreadCount }}</Tag>
          <Tag>消息 {{ messages.length }}</Tag>
          <Tag>只读</Tag>
        </Space>
        <Button :loading="loading" @click="loadMessages">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
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
            <Statistic title="最近时间" :value="latestTime || '不可用'" />
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
          <template #emptyText>
            <span>{{ dataMeta.status === 'ready' ? '暂无消息' : '消息数据不可用' }}</span>
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
                {{ isUnread(record) ? '未读' : '已读' }}
              </Tag>
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
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import { getNotificationList, type NotificationMessage } from '@/api/riskControl';
  import {
    unavailableMeta,
    type ProductDataMeta,
  } from '@/api/platform/productDataState';

  const loading = ref(false);
  const messages = ref<NotificationMessage[]>([]);
  const dataMeta = ref<ProductDataMeta>({
    status: 'no_data',
    source: 'notification-service',
    timezone: 'source-defined',
    unit: 'message',
    message: '尚未加载消息',
  });

  const unreadCount = computed(() => messages.value.filter(isUnread).length);
  const latestTime = computed(() =>
    messages.value
      .map((item) => item.created_at || item.createdAt)
      .filter((value): value is string => Boolean(value))
      .sort()
      .at(-1),
  );

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

  async function loadMessages() {
    loading.value = true;
    try {
      messages.value = await getNotificationList();
      dataMeta.value = {
        status: messages.value.length ? 'ready' : 'no_data',
        source: 'notification-service',
        asOf: latestTime.value,
        timezone: 'source-defined',
        unit: 'message',
        message: messages.value.length ? undefined : 'Provider成功返回，但没有消息',
      };
    } catch (error) {
      messages.value = [];
      dataMeta.value = unavailableMeta('notification-service', error, {
        timezone: 'source-defined',
        unit: 'message',
      });
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
