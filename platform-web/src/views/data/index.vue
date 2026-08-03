<template>
  <PageWrapper title="数据管理">
    <div class="data-page">
      <ProductDataStatusAlert :meta="dataMeta" class="mb-4" />

      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="health.status === 'ok' ? 'green' : 'orange'">
            {{ health.service || 'data-service' }}
          </Tag>
          <Tag>同步频率 {{ health.update_frequency || '不可用' }}</Tag>
        </Space>
        <Space>
          <Button :loading="loading" @click="loadData">
            <template #icon><ReloadOutlined /></template>
            刷新
          </Button>
          <Button
            type="primary"
            :disabled="!canOperateData || dataMeta.status === 'unavailable'"
            :loading="syncing"
            @click="syncAccounts"
          >
            <template #icon><SyncOutlined /></template>
            同步账户
          </Button>
        </Space>
      </div>

      <AccountNetValueChart
        ref="chartRef"
        :accounts="accounts"
        :account-id="selectedAccountId"
        title="账户净值统计"
        height="420px"
      />

      <Card :bordered="false" title="账户数据快照" class="vg-panel mt-4">
        <Table
          row-key="id"
          size="small"
          :columns="columns"
          :data-source="accounts"
          :loading="loading"
          :pagination="{ pageSize: 8 }"
        >
          <template #emptyText>
            <span>{{ dataMeta.status === 'ready' ? '暂无账户数据' : '账户数据不可用' }}</span>
          </template>
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <div class="strong-cell">{{ record.name }}</div>
              <div class="muted-cell">{{ record.account_address || '未配置地址' }}</div>
            </template>
            <template v-else-if="column.key === 'asset'">
              <div>{{ formatMoney(record.total_asset) }}</div>
              <div class="muted-cell">可用 {{ formatMoney(record.available_fund) }}</div>
            </template>
            <template v-else-if="column.key === 'initial_capital'">
              {{ formatMoney(record.initial_capital) }}
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="record.status === 'active' ? 'green' : 'default'">{{ record.status }}</Tag>
            </template>
            <template v-else-if="column.key === 'asset_updated_at'">
              {{ formatDateTime(record.asset_updated_at) }}
            </template>
          </template>
        </Table>
      </Card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { ReloadOutlined, SyncOutlined } from '@ant-design/icons-vue';
  import { Button, Card, message, Space, Table, Tag } from 'ant-design-vue';
  import { computed, onMounted, ref } from 'vue';
  import { useRoute } from 'vue-router';
  import {
    type DecimalString,
    type ProductDataMeta,
    unavailableMeta,
  } from '@/api/platform/productDataState';
  import {
    type DataAccount,
    type DataServiceHealth,
    getAccounts,
    getDataHealth,
    triggerAccountSync,
  } from '@/api/riskControl';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { formatToDateTime } from '@/utils/dateUtil';
  import { formatMoneyString } from '@/utils/decimalDisplay';
  import AccountNetValueChart from './components/AccountNetValueChart.vue';

  const loading = ref(false);
  const syncing = ref(false);
  const accounts = ref<DataAccount[]>([]);
  const health = ref<DataServiceHealth>({
    status: 'unknown',
    service: 'data-service',
    update_frequency: 'unknown',
  });
  const dataMeta = ref<ProductDataMeta>({
    status: 'no_data',
    source: 'data-service',
    timezone: 'source-defined',
    currency: 'USD',
    unit: 'account facts',
    precision: 'decimal-string',
    message: '尚未加载账户数据',
  });
  const chartRef = ref<InstanceType<typeof AccountNetValueChart> | null>(null);
  const route = useRoute();
  const { roleLabel, roleColor, canOperateData } = useRoleAccess();
  const selectedAccountId = computed(() => {
    const value = route.query.account_id;
    const raw = Array.isArray(value) ? value[0] : value;
    const id = Number(raw);
    return Number.isFinite(id) && id > 0 ? id : undefined;
  });

  const columns = [
    { title: '账户', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'account_type', key: 'account_type', width: 110 },
    { title: '资产', key: 'asset', align: 'right' },
    { title: '初始资金', dataIndex: 'initial_capital', key: 'initial_capital', align: 'right' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
    { title: '更新时间', dataIndex: 'asset_updated_at', key: 'asset_updated_at', width: 190 },
  ];

  function formatMoney(value?: DecimalString) {
    return formatMoneyString(value, 'USD');
  }

  function formatDateTime(value?: string) {
    return value ? formatToDateTime(value) : '不可用';
  }

  async function loadData() {
    loading.value = true;
    try {
      const [accountRes, healthRes] = await Promise.all([getAccounts(), getDataHealth()]);
      accounts.value = accountRes;
      health.value = healthRes;
      dataMeta.value = {
        status: accountRes.length ? 'ready' : 'no_data',
        source: healthRes.service || 'data-service',
        asOf:
          healthRes.as_of ||
          accountRes
            .map((item) => item.asset_updated_at)
            .filter(Boolean)
            .sort()
            .at(-1),
        timezone: 'source-defined',
        currency: 'USD',
        unit: 'account facts',
        precision: 'decimal-string',
        message: accountRes.length ? undefined : 'Provider成功返回，但没有账户记录',
      };
    } catch (error) {
      accounts.value = [];
      dataMeta.value = unavailableMeta('data-service', error, {
        timezone: 'source-defined',
        currency: 'USD',
        unit: 'account facts',
        precision: 'decimal-string',
      });
    } finally {
      loading.value = false;
    }
  }

  async function syncAccounts() {
    if (!canOperateData.value || syncing.value) return;
    syncing.value = true;
    try {
      const result = await triggerAccountSync();
      message.success(
        `账户同步完成：成功 ${result.synced}，失败 ${result.failed}，跳过 ${result.skipped}`,
      );
      await loadData();
      await chartRef.value?.reload();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '同步失败');
    } finally {
      syncing.value = false;
    }
  }

  onMounted(loadData);
</script>

<style scoped>
  .data-page {
    padding: 16px;
  }

  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
  }

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
    word-break: break-all;
  }

  @media (max-width: 768px) {
    .data-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
