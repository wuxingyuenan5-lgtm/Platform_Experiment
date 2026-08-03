<template>
  <PageWrapper title="财务概览">
    <div class="finance-page">
      <ProductDataStatusAlert :meta="dataMeta" class="mb-4" />

      <div class="toolbar">
        <Space>
          <Tag :color="roleColor">{{ roleLabel }}</Tag>
          <Tag :color="dataMeta.status === 'ready' ? 'green' : 'orange'">
            {{ dataMeta.source }}
          </Tag>
          <Tag>{{ exchangeInfo.symbol || 'USD' }}</Tag>
        </Space>
        <Button :loading="loading" @click="loadData">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
      </div>

      <Row :gutter="[16, 16]">
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <span class="metric-label">总资产</span>
            <strong class="metric-value">{{ formatMoney(totalAsset) }}</strong>
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <span class="metric-label">可用资金</span>
            <strong class="metric-value">{{ formatMoney(availableFund) }}</strong>
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <span class="metric-label">资金占用</span>
            <strong class="metric-value">{{ formatMoney(usedFund) }}</strong>
          </Card>
        </Col>
        <Col :xs="24" :sm="12" :lg="6">
          <Card :bordered="false" class="metric-card">
            <span class="metric-label">资产项</span>
            <strong class="metric-value">{{ ratioItems.length }}</strong>
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
              <template #emptyText>
                <span>{{ dataMeta.status === 'ready' ? '暂无资产占比数据' : '数据源不可用' }}</span>
              </template>
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
          <Card :bordered="false" title="财务数据状态" class="vg-panel">
            <Descriptions :column="1" size="small">
              <Descriptions.Item label="状态">{{ dataMeta.status }}</Descriptions.Item>
              <Descriptions.Item label="来源">{{ dataMeta.source }}</Descriptions.Item>
              <Descriptions.Item label="汇率标的">{{ exchangeInfo.symbol || '不可用' }}</Descriptions.Item>
              <Descriptions.Item label="汇率">
                {{ formatDecimal(exchangeInfo.rate) }}
              </Descriptions.Item>
              <Descriptions.Item label="截至时间">{{ latestUpdateText }}</Descriptions.Item>
              <Descriptions.Item label="时区">{{ dataMeta.timezone || '来源定义' }}</Descriptions.Item>
              <Descriptions.Item label="精度">Decimal字符串</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import Decimal from 'decimal.js';
  import { computed, onMounted, ref } from 'vue';
  import { Button, Card, Col, Descriptions, Progress, Row, Space, Table, Tag } from 'ant-design-vue';
  import { ReloadOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import {
    type DataAccount,
    type ExchangeInfo,
    getAccounts,
    getExchangeInfo,
    getProductRatio,
    getTotalAssetSummary,
    type ProductRatioItem,
    type TotalAssetSummary,
  } from '@/api/riskControl';
  import {
    unavailableMeta,
    type DecimalString,
    type ProductDataMeta,
  } from '@/api/platform/productDataState';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { formatDecimalString, formatMoneyString } from '@/utils/decimalDisplay';
  import { formatToDateTime } from '@/utils/dateUtil';

  const loading = ref(false);
  const accounts = ref<DataAccount[]>([]);
  const ratioItems = ref<ProductRatioItem[]>([]);
  const totalSummary = ref<TotalAssetSummary>({});
  const exchangeInfo = ref<ExchangeInfo>({});
  const dataMeta = ref<ProductDataMeta>({
    status: 'no_data',
    source: 'data-service',
    timezone: 'source-defined',
    currency: 'USD',
    unit: 'money and ratio',
    precision: 'decimal-string',
    message: '尚未加载财务数据',
  });
  const { roleLabel, roleColor } = useRoleAccess();

  function sumAccountField(field: 'total_asset' | 'available_fund'): DecimalString | undefined {
    const values = accounts.value.map((item) => item[field]).filter((value): value is string => value !== undefined);
    if (!values.length) return undefined;
    return values.reduce((sum, value) => sum.plus(value), new Decimal(0)).toFixed();
  }

  const totalAsset = computed<DecimalString | undefined>(
    () => totalSummary.value.total_asset ?? totalSummary.value.total ?? sumAccountField('total_asset'),
  );
  const availableFund = computed<DecimalString | undefined>(() => sumAccountField('available_fund'));
  const usedFund = computed<DecimalString | undefined>(() => {
    if (totalAsset.value === undefined || availableFund.value === undefined) return undefined;
    return Decimal.max(new Decimal(totalAsset.value).minus(availableFund.value), 0).toFixed();
  });
  const latestUpdate = computed(() => {
    const times = accounts.value.map((item) => item.asset_updated_at).filter((value): value is string => Boolean(value)).sort();
    return times[times.length - 1] || totalSummary.value.updated_at || exchangeInfo.value.updated_at;
  });
  const latestUpdateText = computed(() =>
    latestUpdate.value ? formatToDateTime(latestUpdate.value) : '不可用',
  );

  const ratioColumns = [
    { title: '资产项', dataIndex: 'name', key: 'name' },
    { title: '金额 USD', key: 'value', align: 'right', width: 180 },
    { title: '占比', key: 'percent', width: 180 },
  ];

  function formatMoney(value?: DecimalString) {
    return formatMoneyString(value, 'USD');
  }

  function formatDecimal(value?: DecimalString) {
    return value === undefined ? '不可用' : formatDecimalString(value);
  }

  function percentNumber(value: DecimalString) {
    return new Decimal(value).mul(100).toDecimalPlaces(2).toNumber();
  }

  async function loadData() {
    loading.value = true;
    const results = await Promise.allSettled([
      getAccounts(),
      getProductRatio(),
      getTotalAssetSummary(),
      getExchangeInfo(),
    ]);
    try {
      const failures = results.filter((item) => item.status === 'rejected');
      const [accountResult, ratioResult, totalResult, exchangeResult] = results;
      if (accountResult.status === 'fulfilled') accounts.value = accountResult.value;
      if (ratioResult.status === 'fulfilled') ratioItems.value = ratioResult.value;
      if (totalResult.status === 'fulfilled') totalSummary.value = totalResult.value;
      if (exchangeResult.status === 'fulfilled') exchangeInfo.value = exchangeResult.value;

      if (failures.length === results.length) {
        const first = failures[0] as PromiseRejectedResult;
        dataMeta.value = unavailableMeta('data-service', first.reason, {
          timezone: 'source-defined',
          currency: 'USD',
          unit: 'money and ratio',
          precision: 'decimal-string',
        });
      } else if (failures.length) {
        dataMeta.value = {
          status: 'unavailable',
          source: 'data-service (partial)',
          asOf: latestUpdate.value,
          timezone: 'source-defined',
          currency: 'USD',
          unit: 'money and ratio',
          precision: 'decimal-string',
          errorCode: 'partial_provider_failure',
          message: `${failures.length}个财务数据端点不可用；已成功数据未被替换为0`,
          degraded: true,
        };
      } else {
        dataMeta.value = {
          status: accounts.value.length || ratioItems.value.length || totalAsset.value !== undefined ? 'ready' : 'no_data',
          source: 'data-service',
          asOf: latestUpdate.value,
          timezone: 'source-defined',
          currency: 'USD',
          unit: 'money and ratio',
          precision: 'decimal-string',
          message: accounts.value.length || ratioItems.value.length ? undefined : 'Provider成功返回，但没有财务记录',
        };
      }
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

  .metric-label {
    display: block;
    color: #59636e;
    font-size: 13px;
  }

  .metric-value {
    display: block;
    margin-top: 8px;
    font-size: 22px;
    line-height: 1.35;
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
