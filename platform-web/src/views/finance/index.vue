<template>
  <PageWrapper title="财务概览">
    <div class="finance-page">
      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="exchangeInfo.rate ? 'green' : 'orange'">exchange {{ exchangeInfo.symbol || '-' }}</Tag>
        </Space>
        <Button :loading="loading" @click="loadData">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <Row :gutter="[16, 16]">
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="总资产 USD" :value="totalAsset" :precision="2" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="可用资金 USD" :value="availableFund" :precision="2" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="资金占用 USD" :value="usedFund" :precision="2" />
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <Statistic title="资产项" :value="ratioItems.length" />
          </Card>
        </Col>
      </Row>

      <Row :gutter="[16, 16]" class="mt-4">
        <Col :xs="24" :xl="15">
          <Card :bordered="false" title="资产占比" class="vg-panel">
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
        </Col>
        <Col :xs="24" :xl="9">
          <Card :bordered="false" title="财务接口状态" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="汇率标的">{{ exchangeInfo.symbol || 'USD' }}</Descriptions.Item>
              <Descriptions.Item label="汇率">{{ exchangeInfo.rate ?? '-' }}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{{ latestUpdateText }}</Descriptions.Item>
              <Descriptions.Item label="数据来源">data-service</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Descriptions, Progress, Row, Space, Statistic, Table, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import {
    DataAccount,
    ExchangeInfo,
    getAccounts,
    getExchangeInfo,
    getProductRatio,
    getTotalAssetSummary,
    ProductRatioItem,
    TotalAssetSummary,
  } from '@/api/riskControl';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { formateNumStr } from '@/utils/formate';
  import { formatToDateTime } from '@/utils/dateUtil';

  const loading = ref(false);
  const accounts = ref<DataAccount[]>([]);
  const ratioItems = ref<ProductRatioItem[]>([]);
  const totalSummary = ref<TotalAssetSummary>({});
  const exchangeInfo = ref<ExchangeInfo>({});
  const { roleLabel, roleColor } = useRoleAccess();

  const totalAsset = computed(() => {
    const fromApi = totalSummary.value.total_asset ?? totalSummary.value.total;
    if (typeof fromApi === 'number') return fromApi;
    return accounts.value.reduce((sum, item) => sum + Number(item.total_asset || 0), 0);
  });
  const availableFund = computed(() =>
    accounts.value.reduce((sum, item) => sum + Number(item.available_fund || 0), 0),
  );
  const usedFund = computed(() => Math.max(totalAsset.value - availableFund.value, 0));
  const latestUpdate = computed(() => {
    const times = accounts.value.map((item) => item.asset_updated_at).filter(Boolean).sort();
    return times[times.length - 1] || totalSummary.value.updated_at || '';
  });
  const latestUpdateText = computed(() => {
    const value = latestUpdate.value || exchangeInfo.value.updated_at;
    return value ? formatToDateTime(value) : '-';
  });

  const ratioColumns = [
    { title: '资产项', dataIndex: 'name', key: 'name' },
    { title: '金额 USD', key: 'value', align: 'right', width: 180 },
    { title: '占比', key: 'percent', width: 180 },
  ];

  function formatMoney(value: any) {
    return formateNumStr(value || 0, { decimals: 2, keepZero: true });
  }

  function percentNumber(value: any) {
    return Number((Number(value || 0) * 100).toFixed(2));
  }

  async function loadData() {
    loading.value = true;
    try {
      const [accountRes, ratioRes, totalRes, exchangeRes] = await Promise.all([
        getAccounts(),
        getProductRatio(),
        getTotalAssetSummary(),
        getExchangeInfo(),
      ]);
      accounts.value = accountRes;
      ratioItems.value = ratioRes;
      totalSummary.value = totalRes;
      exchangeInfo.value = exchangeRes;
    } finally {
      loading.value = false;
    }
  }

  onMounted(loadData);
</script>

<style scoped>
  .finance-page {
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
    .finance-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
