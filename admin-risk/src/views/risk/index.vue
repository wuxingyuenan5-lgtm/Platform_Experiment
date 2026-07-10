<template>
  <PageWrapper title="风控记录">
    <div class="risk-page">
      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="canViewRisk ? 'green' : 'default'">{{ canViewRisk ? '可见' : '隐藏' }}</Tag>
        </Space>
        <Button :loading="loading" @click="loadRecords">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <Row :gutter="[16, 16]" class="mb-4">
        <Col :xs="24" :md="8">
          <Card :bordered="false" class="metric-card">
            <Statistic title="风控记录" :value="records.length" />
          </Card>
        </Col>
        <Col :xs="24" :md="8">
          <Card :bordered="false" class="metric-card">
            <Statistic title="待处理" :value="pendingCount" />
          </Card>
        </Col>
        <Col :xs="24" :md="8">
          <Card :bordered="false" class="metric-card">
            <Statistic title="高风险" :value="highCount" />
          </Card>
        </Col>
      </Row>

      <Card :bordered="false" class="vg-panel">
        <Table
          row-key="id"
          size="middle"
          :columns="columns"
          :data-source="records"
          :loading="loading"
          :pagination="{ pageSize: 10 }"
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
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Row, Space, Statistic, Table, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import { getRiskRecordList, RiskRecord } from '@/api/riskControl';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';

  const loading = ref(false);
  const records = ref<RiskRecord[]>([]);
  const { roleLabel, roleColor, canViewRisk } = useRoleAccess();

  const pendingCount = computed(() => records.value.filter((item) => item.status === 'pending').length);
  const highCount = computed(() =>
    records.value.filter((item) => ['high', 'critical'].includes(item.severity || '')).length,
  );

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '内容', dataIndex: 'content', key: 'content' },
    { title: '等级', dataIndex: 'severity', key: 'severity', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 180 },
  ];

  function severityColor(severity?: string) {
    if (severity === 'critical') return 'red';
    if (severity === 'high') return 'orange';
    if (severity === 'medium') return 'gold';
    return 'blue';
  }

  async function loadRecords() {
    loading.value = true;
    try {
      records.value = await getRiskRecordList();
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadRecords);
</script>

<style scoped>
  .risk-page {
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
</style>
