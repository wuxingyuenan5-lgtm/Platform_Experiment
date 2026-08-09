<template>
  <div class="strategy-page">
    <div class="toolbar">
      <Space>
        <Tag :color="roleColor">{{ roleLabel }}</Tag>
        <Tag :color="canOperateData ? 'blue' : 'default'">
          {{ canOperateData ? '可同步' : '待同步' }}
        </Tag>
      </Space>
      <Button :loading="loading" @click="loadStrategyState">
        <template #icon><ReloadOutlined /></template>
        刷新
      </Button>
    </div>

    <Row :gutter="[16, 16]" class="mb-4">
      <Col :xs="24" :sm="12" :lg="6">
        <Card :bordered="false" class="metric-card">
          <Statistic title="活跃账户" :value="activeAccounts.length" />
        </Card>
      </Col>
      <Col :xs="24" :sm="12" :lg="6">
        <Card :bordered="false" class="metric-card">
          <Statistic title="Bybit 账户" :value="bybitAccounts.length" />
        </Card>
      </Col>
      <Col :xs="24" :sm="12" :lg="6">
        <Card :bordered="false" class="metric-card">
          <Statistic title="已有资产快照" :value="syncedAccounts.length" />
        </Card>
      </Col>
      <Col :xs="24" :sm="12" :lg="6">
        <Card :bordered="false" class="metric-card">
          <Statistic title="数据频率" :value="health.update_frequency || '-'" />
        </Card>
      </Col>
    </Row>

    <Row :gutter="[16, 16]">
      <Col :xs="24" :xl="14">
        <Card :bordered="false" title="策略账户覆盖" class="vg-panel">
          <Table
            row-key="id"
            size="small"
            :columns="columns"
            :data-source="accounts"
            :loading="loading"
            :pagination="{ pageSize: 8 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <Tag :color="record.status === 'active' ? 'green' : 'default'">{{
                  record.status
                }}</Tag>
              </template>
              <template v-else-if="column.key === 'ready'">
                <Tag :color="record.asset_updated_at ? 'green' : 'orange'">
                  {{ record.asset_updated_at ? '已同步' : '待同步' }}
                </Tag>
              </template>
              <template v-else-if="column.key === 'asset_updated_at'">
                {{ formatDateTime(record.asset_updated_at) }}
              </template>
            </template>
          </Table>
        </Card>
      </Col>
      <Col :xs="24" :xl="10">
        <Card :bordered="false" title="数据状态" class="vg-panel">
          <Descriptions :column="1" size="small">
            <Descriptions.Item label="策略状态">
              <Tag color="default">待同步</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="数据状态">
              <Tag :color="health.status === 'ok' ? 'green' : 'orange'">{{ health.status }}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="当前角色">
              <Tag :color="canOperateData ? 'blue' : 'default'">
                {{ canOperateData ? 'employee/admin' : roleLabel }}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="最近快照">{{ latestUpdateText }}</Descriptions.Item>
          </Descriptions>
        </Card>
      </Col>
    </Row>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import {
    Button,
    Card,
    Col,
    Descriptions,
    Row,
    Space,
    Statistic,
    Table,
    Tag,
  } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { DataAccount, DataServiceHealth, getAccounts, getDataHealth } from '@/api/riskControl';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { formatToDateTime } from '@/utils/dateUtil';

  const loading = ref(false);
  const accounts = ref<DataAccount[]>([]);
  const health = ref<DataServiceHealth>({
    status: 'unknown',
    service: '数据状态',
    update_frequency: '-',
  });
  const { roleLabel, roleColor, canOperateData } = useRoleAccess();

  const activeAccounts = computed(() => accounts.value.filter((item) => item.status === 'active'));
  const bybitAccounts = computed(() =>
    accounts.value.filter((item) => item.account_type === 'bybit'),
  );
  const syncedAccounts = computed(() => accounts.value.filter((item) => !!item.asset_updated_at));
  const latestUpdate = computed(() => {
    const times = accounts.value
      .map((item) => item.asset_updated_at)
      .filter(Boolean)
      .sort();
    return times[times.length - 1] || '';
  });
  const latestUpdateText = computed(() => formatDateTime(latestUpdate.value));

  const columns = [
    { title: '账户', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'account_type', key: 'account_type', width: 120 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
    { title: '同步状态', key: 'ready', width: 110 },
    { title: '更新时间', dataIndex: 'asset_updated_at', key: 'asset_updated_at', width: 180 },
  ];

  function formatDateTime(value?: string) {
    return value ? formatToDateTime(value) : '-';
  }

  async function loadStrategyState() {
    loading.value = true;
    try {
      const [accountRes, healthRes] = await Promise.all([getAccounts(), getDataHealth()]);
      accounts.value = accountRes;
      health.value = healthRes;
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadStrategyState);
</script>

<style scoped>
  .strategy-page {
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
    .strategy-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
