<template>
  <div class="holdings-panel">
    <Alert
      type="info"
      show-icon
      message="客户报告持仓"
      description="本区域展示会员基金份额与基金单位净值读模型，不代表交易账户余额、申赎清算或正式财务账本。"
    />

    <template v-if="role !== 'member'">
      <Empty class="empty-state" description="当前角色没有个人会员基金持仓">
        <template #image>
          <Icon icon="ant-design:fund-outlined" :size="68" color="#94a3b8" />
        </template>
      </Empty>
    </template>

    <template v-else>
      <div class="summary-grid">
        <div class="summary-item">
          <span>基金数量</span>
          <strong>{{ holdings.length }}</strong>
        </div>
        <div class="summary-item">
          <span>净值可用</span>
          <strong>{{ availableCount }}</strong>
        </div>
        <div class="summary-item summary-item--warning">
          <span>净值过期</span>
          <strong>{{ staleCount }}</strong>
        </div>
        <div class="summary-item summary-item--muted">
          <span>净值缺失</span>
          <strong>{{ unavailableCount }}</strong>
        </div>
      </div>

      <div class="panel-toolbar">
        <div>
          <h3>个人基金持仓</h3>
          <p>金额和份额均由后端 Decimal 字符串返回，页面不使用浮点数重新计算。</p>
        </div>
        <Button :loading="loading" @click="loadHoldings">刷新</Button>
      </div>

      <Spin :spinning="loading">
        <div v-if="holdings.length" class="holding-list">
          <Card
            v-for="holding in holdings"
            :key="holding.holdingId"
            :bordered="false"
            class="holding-card"
          >
            <div class="holding-card__header">
              <div>
                <div class="fund-name">{{ holding.fundName }}</div>
                <div class="fund-code">
                  {{ holding.fundCode || holding.fundId }} · {{ holding.currency }}
                </div>
              </div>
              <Space>
                <Tag :color="navStatusMeta(holding.navStatus).color">
                  {{ navStatusMeta(holding.navStatus).label }}
                </Tag>
                <Tag :color="holding.status === 'active' ? 'green' : 'default'">
                  {{ holding.status === 'active' ? '持有中' : '已结束' }}
                </Tag>
              </Space>
            </div>

            <div class="holding-metrics">
              <div>
                <span>持有份额</span>
                <strong>{{ formatDecimal(holding.shareQuantity) }}</strong>
              </div>
              <div>
                <span>最新单位净值</span>
                <strong>{{ formatNullableDecimal(holding.latestUnitNav) }}</strong>
              </div>
              <div>
                <span>当前市值</span>
                <strong>{{ formatMoney(holding.marketValue, holding.currency) }}</strong>
              </div>
              <div>
                <span>累计投入</span>
                <strong>{{ formatMoney(holding.cumulativeInvested, holding.currency) }}</strong>
              </div>
              <div>
                <span>累计收益</span>
                <strong :class="returnClass(holding.cumulativeReturn)">
                  {{ formatSignedMoney(holding.cumulativeReturn, holding.currency) }}
                </strong>
              </div>
              <div>
                <span>收益率</span>
                <strong :class="returnClass(holding.returnRate)">
                  {{ formatRatioAsPercent(holding.returnRate) }}
                </strong>
              </div>
            </div>

            <div class="holding-card__footer">
              <span>数据时点：{{ formatTime(holding.asOf) }}</span>
              <span>净值时点：{{ formatTime(holding.navValuationTime) }}</span>
              <span>份额确认：{{ formatTime(holding.confirmedAt) }}</span>
            </div>
            <Alert
              v-if="holding.navStatus !== 'available'"
              class="holding-warning"
              :type="holding.navStatus === 'stale' ? 'warning' : 'info'"
              show-icon
              :message="
                holding.navStatus === 'stale'
                  ? '基金净值已超过新鲜度阈值，市值仅按最近可用净值展示'
                  : '当前没有可用基金净值，市值与收益保持不可用而不是显示为 0'
              "
            />
          </Card>
        </div>
        <Empty v-else-if="!loading" class="empty-state" description="暂无个人基金持仓" />
      </Spin>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue';
  import { Alert, Button, Card, Empty, message, Space, Spin, Tag } from 'ant-design-vue';
  import { Icon } from '@/components/Icon';
  import {
    getSelfMemberHoldings,
    type MemberHolding,
    type NavStatus,
  } from '@/api/platform/memberHoldings';
  import type { HumanRole } from '@/api/platform/userSystem';

  interface Props {
    role?: HumanRole;
    active?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    role: 'employee',
    active: false,
  });

  const holdings = ref<MemberHolding[]>([]);
  const loading = ref(false);
  const loaded = ref(false);
  const availableCount = computed(
    () => holdings.value.filter((item) => item.navStatus === 'available').length,
  );
  const staleCount = computed(
    () => holdings.value.filter((item) => item.navStatus === 'stale').length,
  );
  const unavailableCount = computed(
    () => holdings.value.filter((item) => item.navStatus === 'unavailable').length,
  );

  watch(
    () => props.active,
    (active) => {
      if (active && props.role === 'member' && !loaded.value) loadHoldings();
    },
  );

  watch(
    () => props.role,
    (role) => {
      if (role !== 'member') {
        holdings.value = [];
        loaded.value = true;
      } else if (props.active) {
        loaded.value = false;
        loadHoldings();
      }
    },
  );

  onMounted(() => {
    if (props.active && props.role === 'member') loadHoldings();
  });

  async function loadHoldings() {
    if (props.role !== 'member' || loading.value) return;
    loading.value = true;
    try {
      holdings.value = await getSelfMemberHoldings();
      loaded.value = true;
    } catch (error) {
      message.error(error instanceof Error ? error.message : '个人基金持仓加载失败');
    } finally {
      loading.value = false;
    }
  }

  function navStatusMeta(status: NavStatus) {
    const values = {
      available: { label: '净值可用', color: 'green' },
      stale: { label: '净值过期', color: 'orange' },
      unavailable: { label: '净值缺失', color: 'default' },
    };
    return values[status];
  }

  function splitDecimal(value: string) {
    const negative = value.startsWith('-');
    const unsigned = negative ? value.slice(1) : value;
    const [integer = '0', fraction = ''] = unsigned.split('.');
    return { negative, integer, fraction };
  }

  function groupInteger(value: string) {
    return value.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }

  function formatDecimal(value: string) {
    const { negative, integer, fraction } = splitDecimal(value);
    return `${negative ? '-' : ''}${groupInteger(integer)}${fraction ? `.${fraction}` : ''}`;
  }

  function formatNullableDecimal(value?: string) {
    return value === undefined || value === null ? '不可用' : formatDecimal(value);
  }

  function formatMoney(value: string | undefined, currency: string) {
    return value === undefined || value === null ? '不可用' : `${formatDecimal(value)} ${currency}`;
  }

  function formatSignedMoney(value: string | undefined, currency: string) {
    if (value === undefined || value === null) return '不可用';
    const prefix = value.startsWith('-') || value === '0' ? '' : '+';
    return `${prefix}${formatDecimal(value)} ${currency}`;
  }

  function multiplyDecimalByHundred(value: string) {
    const { negative, integer, fraction } = splitDecimal(value);
    const targetPosition = integer.length + 2;
    let expanded = `${integer}${fraction}`;
    if (targetPosition > expanded.length) expanded = expanded.padEnd(targetPosition, '0');
    const whole = expanded.slice(0, targetPosition) || '0';
    const decimal = expanded.slice(targetPosition).replace(/0+$/, '');
    const normalizedWhole = whole.replace(/^0+(?=\d)/, '') || '0';
    return `${negative ? '-' : ''}${normalizedWhole}${decimal ? `.${decimal}` : ''}`;
  }

  function formatRatioAsPercent(value?: string) {
    if (value === undefined || value === null) return '不可用';
    const percent = multiplyDecimalByHundred(value);
    const prefix = percent.startsWith('-') || percent === '0' ? '' : '+';
    return `${prefix}${formatDecimal(percent)}%`;
  }

  function returnClass(value?: string) {
    if (!value || value === '0') return '';
    return value.startsWith('-') ? 'return-negative' : 'return-positive';
  }

  function formatTime(value?: string) {
    if (!value) return '-';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
  }
</script>

<style scoped>
  .holdings-panel {
    display: grid;
    gap: 18px;
  }

  .summary-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .summary-item {
    padding: 16px 18px;
    border: 1px solid #dcfce7;
    border-radius: 12px;
    background: #f0fdf4;
  }

  .summary-item--warning {
    border-color: #fde68a;
    background: #fffbeb;
  }

  .summary-item--muted {
    border-color: #e2e8f0;
    background: #f8fafc;
  }

  .summary-item span,
  .summary-item strong {
    display: block;
  }

  .summary-item span {
    margin-bottom: 6px;
    color: #64748b;
    font-size: 12px;
  }

  .summary-item strong {
    color: #0f172a;
    font-size: 22px;
  }

  .panel-toolbar,
  .holding-card__header,
  .holding-card__footer {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
  }

  .panel-toolbar h3 {
    margin: 0;
    color: #0f172a;
    font-size: 17px;
  }

  .panel-toolbar p {
    margin: 5px 0 0;
    color: #64748b;
    font-size: 12px;
  }

  .holding-list {
    display: grid;
    gap: 14px;
  }

  .holding-card {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
  }

  .fund-name {
    color: #0f172a;
    font-size: 16px;
    font-weight: 700;
  }

  .fund-code {
    margin-top: 4px;
    color: #64748b;
    font-size: 12px;
  }

  .holding-metrics {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: 18px;
  }

  .holding-metrics > div {
    padding: 13px 14px;
    border-radius: 10px;
    background: #f8fafc;
  }

  .holding-metrics span,
  .holding-metrics strong {
    display: block;
  }

  .holding-metrics span {
    margin-bottom: 6px;
    color: #64748b;
    font-size: 12px;
  }

  .holding-metrics strong {
    color: #0f172a;
    font-size: 15px;
    overflow-wrap: anywhere;
  }

  .return-positive {
    color: #15803d !important;
  }

  .return-negative {
    color: #b91c1c !important;
  }

  .holding-card__footer {
    justify-content: flex-start;
    flex-wrap: wrap;
    margin-top: 16px;
    color: #64748b;
    font-size: 12px;
  }

  .holding-warning {
    margin-top: 14px;
  }

  .empty-state {
    padding: 56px 0;
  }

  @media (max-width: 900px) {
    .summary-grid,
    .holding-metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 600px) {
    .summary-grid,
    .holding-metrics {
      grid-template-columns: 1fr;
    }

    .panel-toolbar,
    .holding-card__header {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
