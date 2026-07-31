<template>
  <div class="holdings-panel">
    <template v-if="role !== 'member'">
      <Empty class="empty-state" description="当前角色没有个人会员基金持仓">
        <template #image>
          <Icon icon="ant-design:fund-outlined" :size="68" color="#94a3b8" />
        </template>
      </Empty>
    </template>

    <template v-else>
      <div class="account-heading">
        <div>
          <span class="eyebrow">MEMBER ACCOUNT</span>
          <h2>我的资产</h2>
          <p>展示已确认基金份额、最新净值和收益情况。</p>
        </div>
        <Button :loading="loading" @click="loadHoldings">刷新数据</Button>
      </div>

      <Spin :spinning="loading">
        <div v-if="holdings.length" class="overview-card">
          <div class="overview-main">
            <span>账户估值</span>
            <strong>{{ formatMoney(totalMarketValue, summaryCurrency) }}</strong>
            <small>数据时点：{{ formatTime(latestAsOf) }}</small>
          </div>
          <div class="overview-metrics">
            <div>
              <span>累计投入</span>
              <strong>{{ formatMoney(totalInvested, summaryCurrency) }}</strong>
            </div>
            <div>
              <span>累计收益</span>
              <strong :class="returnClass(totalReturn)">
                {{ formatSignedMoney(totalReturn, summaryCurrency) }}
              </strong>
            </div>
            <div>
              <span>持有基金</span>
              <strong>{{ activeHoldingCount }}</strong>
            </div>
          </div>
        </div>

        <div v-if="holdings.length" class="data-status">
          <Tag color="green">净值可用 {{ availableCount }}</Tag>
          <Tag v-if="staleCount" color="orange">净值过期 {{ staleCount }}</Tag>
          <Tag v-if="unavailableCount">净值缺失 {{ unavailableCount }}</Tag>
          <span>本页为客户报告视图，不代表申赎清算或正式财务账本。</span>
        </div>

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
                <span>当前市值</span>
                <strong>{{ formatDetailedMoney(holding.marketValue, holding.currency) }}</strong>
              </div>
              <div>
                <span>累计收益</span>
                <strong :class="returnClass(holding.cumulativeReturn)">
                  {{ formatDetailedSignedMoney(holding.cumulativeReturn, holding.currency) }}
                </strong>
              </div>
              <div>
                <span>收益率</span>
                <strong :class="returnClass(holding.returnRate)">
                  {{ formatRatioAsPercent(holding.returnRate) }}
                </strong>
              </div>
              <div>
                <span>持有份额</span>
                <strong>{{ formatDecimal(holding.shareQuantity) }}</strong>
              </div>
              <div>
                <span>最新单位净值</span>
                <strong>{{ formatNullableDecimal(holding.latestUnitNav) }}</strong>
              </div>
              <div>
                <span>累计投入</span>
                <strong>
                  {{ formatDetailedMoney(holding.cumulativeInvested, holding.currency) }}
                </strong>
              </div>
            </div>

            <div class="holding-card__footer">
              <span>持仓更新：{{ formatTime(holding.asOf) }}</span>
              <span>净值更新：{{ formatTime(holding.navValuationTime) }}</span>
              <span>份额确认：{{ formatTime(holding.confirmedAt) }}</span>
            </div>
            <Alert
              v-if="holding.navStatus !== 'available'"
              class="holding-warning"
              :type="holding.navStatus === 'stale' ? 'warning' : 'info'"
              show-icon
              :message="
                holding.navStatus === 'stale'
                  ? '基金净值已超过更新阈值，当前估值使用最近一次可用净值'
                  : '当前没有可用基金净值，市值和收益暂不展示'
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
  import Icon from '@/components/Icon/Icon.vue';
  import {
    getSelfMemberHoldings,
    type MemberHolding,
    type NavStatus,
  } from '@/api/platform/memberHoldings';
  import type { HumanRole } from '@/api/platform/userSystem';
  import {
    decimalDirection,
    formatDecimalString,
    formatMoneyString,
    formatNullableDecimalString,
    formatRatioPercentString,
    formatSignedMoneyString,
  } from '@/utils/decimalDisplay';

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
  const activeHoldingCount = computed(
    () => holdings.value.filter((item) => item.status === 'active').length,
  );
  const summaryCurrency = computed(() => {
    const currencies = Array.from(new Set(holdings.value.map((item) => item.currency)));
    return currencies.length === 1 ? currencies[0] || '' : '多币种';
  });
  const canAggregate = computed(() => summaryCurrency.value !== '多币种');
  const hasCompleteValuation = computed(() =>
    holdings.value.every(
      (item) => isDecimal(item.marketValue) && isDecimal(item.cumulativeReturn),
    ),
  );
  const totalMarketValue = computed(() =>
    canAggregate.value && hasCompleteValuation.value
      ? sumDecimalStrings(holdings.value.map((item) => item.marketValue as string))
      : undefined,
  );
  const totalInvested = computed(() =>
    canAggregate.value
      ? sumDecimalStrings(holdings.value.map((item) => item.cumulativeInvested))
      : undefined,
  );
  const totalReturn = computed(() =>
    canAggregate.value && hasCompleteValuation.value
      ? sumDecimalStrings(holdings.value.map((item) => item.cumulativeReturn as string))
      : undefined,
  );
  const latestAsOf = computed(() =>
    holdings.value.reduce<string | undefined>((latest, item) => {
      if (!latest) return item.asOf;
      return item.asOf > latest ? item.asOf : latest;
    }, undefined),
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

  function isDecimal(value?: string): value is string {
    return value !== undefined && value !== null;
  }

  function stripLeadingZeros(value: string): string {
    return value.replace(/^0+(?=\d)/, '') || '0';
  }

  function compareUnsigned(left: string, right: string): number {
    const normalizedLeft = stripLeadingZeros(left);
    const normalizedRight = stripLeadingZeros(right);
    if (normalizedLeft.length !== normalizedRight.length) {
      return normalizedLeft.length > normalizedRight.length ? 1 : -1;
    }
    if (normalizedLeft === normalizedRight) return 0;
    return normalizedLeft > normalizedRight ? 1 : -1;
  }

  function addUnsigned(left: string, right: string): string {
    let leftIndex = left.length - 1;
    let rightIndex = right.length - 1;
    let carry = 0;
    let result = '';
    while (leftIndex >= 0 || rightIndex >= 0 || carry) {
      const leftDigit = leftIndex >= 0 ? left.charCodeAt(leftIndex) - 48 : 0;
      const rightDigit = rightIndex >= 0 ? right.charCodeAt(rightIndex) - 48 : 0;
      const sum = leftDigit + rightDigit + carry;
      result = String.fromCharCode(48 + (sum % 10)) + result;
      carry = Math.floor(sum / 10);
      leftIndex -= 1;
      rightIndex -= 1;
    }
    return stripLeadingZeros(result);
  }

  function subtractUnsigned(left: string, right: string): string {
    let leftIndex = left.length - 1;
    let rightIndex = right.length - 1;
    let borrow = 0;
    let result = '';
    while (leftIndex >= 0) {
      let digit = left.charCodeAt(leftIndex) - 48 - borrow;
      const rightDigit = rightIndex >= 0 ? right.charCodeAt(rightIndex) - 48 : 0;
      if (digit < rightDigit) {
        digit += 10;
        borrow = 1;
      } else {
        borrow = 0;
      }
      result = String.fromCharCode(48 + digit - rightDigit) + result;
      leftIndex -= 1;
      rightIndex -= 1;
    }
    return stripLeadingZeros(result);
  }

  function sumDecimalStrings(values: string[]): string | undefined {
    if (values.length === 0) return undefined;
    let scale = 0;
    for (const value of values) {
      const fractionLength = value.split('.')[1]?.length || 0;
      if (fractionLength > scale) scale = fractionLength;
    }

    let totalDigits = '0';
    let totalNegative = false;
    for (const value of values) {
      const negative = value.startsWith('-');
      const unsigned = negative ? value.slice(1) : value;
      const [integer = '0', fraction = ''] = unsigned.split('.');
      const digits = stripLeadingZeros(`${integer}${fraction.padEnd(scale, '0')}`);
      if (digits === '0') continue;

      if (totalDigits === '0') {
        totalDigits = digits;
        totalNegative = negative;
      } else if (totalNegative === negative) {
        totalDigits = addUnsigned(totalDigits, digits);
      } else {
        const comparison = compareUnsigned(totalDigits, digits);
        if (comparison === 0) {
          totalDigits = '0';
          totalNegative = false;
        } else if (comparison > 0) {
          totalDigits = subtractUnsigned(totalDigits, digits);
        } else {
          totalDigits = subtractUnsigned(digits, totalDigits);
          totalNegative = negative;
        }
      }
    }

    const padded = totalDigits.padStart(scale + 1, '0');
    const whole = scale ? padded.slice(0, -scale) || '0' : padded;
    const fraction = scale ? padded.slice(-scale).replace(/0+$/, '') : '';
    return `${totalNegative && totalDigits !== '0' ? '-' : ''}${whole}${
      fraction ? `.${fraction}` : ''
    }`;
  }

  function withMinimumFraction(value: string, minimum = 2): string {
    const negative = value.startsWith('-');
    const unsigned = negative ? value.slice(1) : value;
    const [integer = '0', fraction = ''] = unsigned.split('.');
    const paddedFraction = fraction.padEnd(minimum, '0');
    return `${negative ? '-' : ''}${integer}.${paddedFraction}`;
  }

  function navStatusMeta(status: NavStatus) {
    return {
      available: { label: '净值可用', color: 'green' },
      stale: { label: '净值过期', color: 'orange' },
      unavailable: { label: '净值缺失', color: 'default' },
    }[status];
  }

  function formatDecimal(value: string) {
    return formatDecimalString(value);
  }

  function formatNullableDecimal(value?: string) {
    return formatNullableDecimalString(value);
  }

  function formatMoney(value: string | undefined, currency: string) {
    if (currency === '多币种') return '多币种资产';
    return formatMoneyString(value, currency);
  }

  function formatSignedMoney(value: string | undefined, currency: string) {
    if (currency === '多币种') return '多币种资产';
    return formatSignedMoneyString(value, currency);
  }

  function formatDetailedMoney(value: string | undefined, currency: string) {
    return formatMoneyString(
      value === undefined ? undefined : withMinimumFraction(value),
      currency,
    );
  }

  function formatDetailedSignedMoney(value: string | undefined, currency: string) {
    return formatSignedMoneyString(
      value === undefined ? undefined : withMinimumFraction(value),
      currency,
    );
  }

  function formatRatioAsPercent(value?: string) {
    return formatRatioPercentString(value);
  }

  function returnClass(value?: string) {
    const direction = decimalDirection(value);
    return direction === 'negative'
      ? 'return-negative'
      : direction === 'positive'
      ? 'return-positive'
      : '';
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

  .account-heading,
  .holding-card__header,
  .holding-card__footer,
  .data-status {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
  }

  .account-heading h2 {
    margin: 3px 0;
    color: #0f172a;
    font-size: 24px;
  }

  .account-heading p,
  .data-status span {
    margin: 0;
    color: #64748b;
    font-size: 12px;
  }

  .eyebrow {
    color: #2563eb;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
  }

  .overview-card {
    display: grid;
    grid-template-columns: minmax(240px, 1.2fr) 2fr;
    overflow: hidden;
    border: 1px solid #dbeafe;
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  }

  .overview-main {
    padding: 24px;
    background: linear-gradient(135deg, #eff6ff, #f8fafc);
  }

  .overview-main span,
  .overview-main strong,
  .overview-main small,
  .overview-metrics span,
  .overview-metrics strong {
    display: block;
  }

  .overview-main span,
  .overview-metrics span {
    color: #64748b;
    font-size: 12px;
  }

  .overview-main strong {
    margin: 8px 0;
    color: #0f172a;
    font-size: 30px;
  }

  .overview-main small {
    color: #64748b;
  }

  .overview-metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .overview-metrics > div {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 20px;
    border-left: 1px solid #e2e8f0;
  }

  .overview-metrics strong {
    margin-top: 8px;
    color: #0f172a;
    font-size: 18px;
  }

  .data-status {
    justify-content: flex-start;
    padding: 10px 14px;
    border-radius: 10px;
    background: #f8fafc;
  }

  .data-status span {
    margin-left: auto;
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
    margin-bottom: 5px;
    color: #64748b;
    font-size: 12px;
  }

  .holding-metrics strong {
    color: #0f172a;
    font-size: 15px;
  }

  .holding-card__footer {
    justify-content: flex-start;
    margin-top: 16px;
    color: #64748b;
    font-size: 12px;
  }

  .holding-warning {
    margin-top: 14px;
  }

  .return-positive {
    color: #15803d !important;
  }

  .return-negative {
    color: #b91c1c !important;
  }

  .empty-state {
    padding: 48px 0;
  }

  @media (max-width: 900px) {
    .overview-card,
    .overview-metrics {
      grid-template-columns: 1fr;
    }

    .overview-metrics > div {
      border-top: 1px solid #e2e8f0;
      border-left: 0;
    }

    .holding-metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .data-status {
      align-items: flex-start;
      flex-wrap: wrap;
    }

    .data-status span {
      width: 100%;
      margin-left: 0;
    }
  }

  @media (max-width: 620px) {
    .account-heading,
    .holding-card__header,
    .holding-card__footer {
      align-items: flex-start;
      flex-direction: column;
    }

    .holding-metrics {
      grid-template-columns: 1fr;
    }
  }
</style>
