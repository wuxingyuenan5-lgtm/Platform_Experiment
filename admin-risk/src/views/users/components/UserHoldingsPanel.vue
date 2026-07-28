<template>
  <div class="admin-holdings">
    <Alert
      type="info"
      show-icon
      message="会员客户报告持仓"
      description="持仓与基金单位净值由 CEO 人工维护；本区域不是申赎、清算或正式财务账本。"
    />

    <div class="toolbar">
      <div>
        <h4>基金持仓</h4>
        <p>全部数值以后端 Decimal 字符串为准，页面不进行浮点数重算。</p>
      </div>
      <Space>
        <Button :loading="loading" @click="loadAll">刷新</Button>
        <Button v-if="canUpdate" @click="openNavModal">更新基金净值</Button>
        <Button v-if="canUpdate" type="primary" @click="openHoldingModal()">新增持仓</Button>
      </Space>
    </div>

    <Spin :spinning="loading">
      <Table
        v-if="holdings.length"
        row-key="holdingId"
        size="small"
        :columns="columns"
        :data-source="holdings"
        :pagination="false"
        :scroll="{ x: 1040 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'fund'">
            <strong>{{ record.fundName }}</strong>
            <div class="subline">{{ record.fundCode || record.fundId }}</div>
          </template>
          <template v-else-if="column.key === 'shares'">
            {{ formatDecimal(record.shareQuantity) }}
          </template>
          <template v-else-if="column.key === 'nav'">
            <div>{{ formatNullableDecimal(record.latestUnitNav) }}</div>
            <Tag :color="navMeta(record.navStatus).color">{{
              navMeta(record.navStatus).label
            }}</Tag>
          </template>
          <template v-else-if="column.key === 'marketValue'">
            {{ formatMoney(record.marketValue, record.currency) }}
          </template>
          <template v-else-if="column.key === 'invested'">
            {{ formatMoney(record.cumulativeInvested, record.currency) }}
          </template>
          <template v-else-if="column.key === 'return'">
            <span :class="returnClass(record.cumulativeReturn)">
              {{ formatSignedMoney(record.cumulativeReturn, record.currency) }}
            </span>
          </template>
          <template v-else-if="column.key === 'asOf'">
            {{ formatTime(record.asOf) }}
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="record.status === 'active' ? 'green' : 'default'">
              {{ record.status === 'active' ? '持有中' : '已结束' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <Button v-if="canUpdate" type="link" size="small" @click="openHoldingModal(record)">
              编辑
            </Button>
          </template>
        </template>
      </Table>
      <Empty v-else-if="!loading" description="该会员暂无基金持仓" />
    </Spin>

    <Modal
      v-model:open="holdingModalOpen"
      :title="editingHolding ? '编辑持仓' : '新增持仓'"
      :confirm-loading="savingHolding"
      @ok="saveHolding"
      @cancel="resetHoldingDraft"
    >
      <Form layout="vertical">
        <Form.Item label="基金" required>
          <Select
            v-model:value="holdingDraft.fundId"
            :options="fundOptions"
            :disabled="!!editingHolding"
            show-search
            option-filter-prop="label"
          />
        </Form.Item>
        <Form.Item label="持有份额" required>
          <Input v-model:value="holdingDraft.shareQuantity" placeholder="例如：1250.50" />
        </Form.Item>
        <Form.Item label="累计投入" required>
          <Input v-model:value="holdingDraft.cumulativeInvested" placeholder="例如：100000" />
        </Form.Item>
        <Form.Item label="份额确认时间">
          <Input v-model:value="holdingDraft.confirmedAt" type="datetime-local" />
        </Form.Item>
        <Form.Item label="数据时点" required>
          <Input v-model:value="holdingDraft.asOf" type="datetime-local" />
        </Form.Item>
        <Form.Item label="状态" required>
          <Select
            v-model:value="holdingDraft.status"
            :options="[
              { value: 'active', label: '持有中' },
              { value: 'closed', label: '已结束' },
            ]"
          />
        </Form.Item>
        <Alert
          type="warning"
          show-icon
          message="保存后会写入审计记录"
          description="若该基金没有可用净值，市值和收益将保持不可用，不会显示为 0。"
        />
      </Form>
    </Modal>

    <Modal
      v-model:open="navModalOpen"
      title="更新基金单位净值"
      :confirm-loading="savingNav"
      @ok="saveNav"
      @cancel="resetNavDraft"
    >
      <Form layout="vertical">
        <Form.Item label="基金" required>
          <Select
            v-model:value="navDraft.fundId"
            :options="fundOptions"
            show-search
            option-filter-prop="label"
            @change="syncNavFund"
          />
        </Form.Item>
        <Form.Item label="基金代码">
          <Input v-model:value="navDraft.fundCode" maxlength="64" />
        </Form.Item>
        <Form.Item label="单位净值" required>
          <Input v-model:value="navDraft.unitNav" placeholder="例如：1.0235" />
        </Form.Item>
        <Form.Item label="币种" required>
          <Input v-model:value="navDraft.currency" disabled />
        </Form.Item>
        <Form.Item label="估值时间" required>
          <Input v-model:value="navDraft.valuationTime" type="datetime-local" />
        </Form.Item>
        <Alert
          type="info"
          show-icon
          message="新净值会替代上一条可用净值"
          description="历史记录保留为 superseded；不会修改策略净值或正式财务事实。"
        />
      </Form>
    </Modal>

    <Modal
      v-model:open="reauthOpen"
      title="重新验证当前密码"
      :confirm-loading="reauthLoading"
      @ok="submitReauthentication"
      @cancel="cancelReauthentication"
    >
      <Input.Password
        v-model:value="reauthPassword"
        autocomplete="current-password"
        placeholder="请输入当前登录账号密码"
        @press-enter="submitReauthentication"
      />
    </Modal>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref, watch } from 'vue';
  import {
    Alert,
    Button,
    Empty,
    Form,
    Input,
    message,
    Modal,
    Select,
    Space,
    Spin,
    Table,
    Tag,
  } from 'ant-design-vue';
  import { hasPermission } from '@/access/userAccess';
  import { UserSystemApiError, reauthenticateUser } from '@/api/platform/userSystem';
  import {
    getAdminMemberHoldings,
    listHoldingFunds,
    putAdminMemberHolding,
    putHoldingFundNav,
    type FundSummary,
    type HoldingStatus,
    type MemberHolding,
    type NavStatus,
  } from '@/api/platform/memberHoldings';

  interface Props {
    userId: string;
    permissions?: string[];
    active?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    permissions: () => [],
    active: false,
  });
  const emit = defineEmits<{ changed: [] }>();

  const holdings = ref<MemberHolding[]>([]);
  const funds = ref<FundSummary[]>([]);
  const loading = ref(false);
  const loaded = ref(false);
  const holdingModalOpen = ref(false);
  const editingHolding = ref<MemberHolding | null>(null);
  const savingHolding = ref(false);
  const navModalOpen = ref(false);
  const savingNav = ref(false);
  const reauthOpen = ref(false);
  const reauthPassword = ref('');
  const reauthLoading = ref(false);
  const pendingSensitiveAction = ref<(() => Promise<void>) | null>(null);

  const holdingDraft = reactive({
    fundId: '',
    shareQuantity: '',
    cumulativeInvested: '',
    confirmedAt: '',
    asOf: localDateTime(),
    status: 'active' as HoldingStatus,
  });
  const navDraft = reactive({
    fundId: '',
    fundCode: '',
    unitNav: '',
    currency: '',
    valuationTime: localDateTime(),
  });

  const canUpdate = computed(() => hasPermission(props.permissions, 'member.holding.update'));
  const fundOptions = computed(() =>
    funds.value.map((fund) => ({
      value: fund.fundId,
      label: `${fund.fundName}${fund.fundCode ? ` · ${fund.fundCode}` : ''} · ${fund.baseCurrency}`,
    })),
  );
  const columns = [
    { title: '基金', key: 'fund', width: 180, fixed: 'left' },
    { title: '份额', key: 'shares', width: 120 },
    { title: '单位净值', key: 'nav', width: 130 },
    { title: '市值', key: 'marketValue', width: 150 },
    { title: '累计投入', key: 'invested', width: 150 },
    { title: '累计收益', key: 'return', width: 150 },
    { title: '数据时点', key: 'asOf', width: 170 },
    { title: '状态', key: 'status', width: 90 },
    { title: '操作', key: 'action', width: 80, fixed: 'right' },
  ];

  watch(
    () => [props.active, props.userId],
    ([active]) => {
      if (active) {
        loaded.value = false;
        loadAll();
      }
    },
  );

  onMounted(() => {
    if (props.active) loadAll();
  });

  async function loadAll() {
    if (!props.userId || loading.value) return;
    loading.value = true;
    try {
      const [holdingItems, fundItems] = await Promise.all([
        getAdminMemberHoldings(props.userId),
        canUpdate.value ? listHoldingFunds() : Promise.resolve([] as FundSummary[]),
      ]);
      holdings.value = holdingItems;
      funds.value = fundItems;
      loaded.value = true;
    } catch (error) {
      message.error(error instanceof Error ? error.message : '会员持仓加载失败');
    } finally {
      loading.value = false;
    }
  }

  function openHoldingModal(holding?: MemberHolding) {
    editingHolding.value = holding || null;
    holdingDraft.fundId = holding?.fundId || funds.value[0]?.fundId || '';
    holdingDraft.shareQuantity = holding?.shareQuantity || '';
    holdingDraft.cumulativeInvested = holding?.cumulativeInvested || '';
    holdingDraft.confirmedAt = holding?.confirmedAt ? localDateTime(holding.confirmedAt) : '';
    holdingDraft.asOf = holding?.asOf ? localDateTime(holding.asOf) : localDateTime();
    holdingDraft.status = holding?.status || 'active';
    holdingModalOpen.value = true;
  }

  function resetHoldingDraft() {
    holdingModalOpen.value = false;
    editingHolding.value = null;
    holdingDraft.fundId = '';
    holdingDraft.shareQuantity = '';
    holdingDraft.cumulativeInvested = '';
    holdingDraft.confirmedAt = '';
    holdingDraft.asOf = localDateTime();
    holdingDraft.status = 'active';
  }

  async function saveHolding() {
    if (!holdingDraft.fundId || !plainDecimal(holdingDraft.shareQuantity)) {
      message.warning('请输入合法的非负持有份额');
      return;
    }
    if (!plainDecimal(holdingDraft.cumulativeInvested)) {
      message.warning('请输入合法的非负累计投入');
      return;
    }
    if (!holdingDraft.asOf) {
      message.warning('请选择数据时点');
      return;
    }
    savingHolding.value = true;
    try {
      await runSensitive(async () => {
        await putAdminMemberHolding(props.userId, holdingDraft.fundId, {
          shareQuantity: holdingDraft.shareQuantity,
          cumulativeInvested: holdingDraft.cumulativeInvested,
          confirmedAt: holdingDraft.confirmedAt ? toIso(holdingDraft.confirmedAt) : undefined,
          asOf: toIso(holdingDraft.asOf),
          source: 'manual_admin',
          status: holdingDraft.status,
          expectedVersion: editingHolding.value?.rowVersion,
        });
        message.success('会员持仓已保存');
        resetHoldingDraft();
        await loadAll();
        emit('changed');
      });
    } catch (error) {
      message.error(error instanceof Error ? error.message : '会员持仓保存失败');
    } finally {
      savingHolding.value = false;
    }
  }

  function openNavModal() {
    navDraft.fundId = funds.value[0]?.fundId || '';
    syncNavFund(navDraft.fundId);
    navDraft.unitNav = '';
    navDraft.valuationTime = localDateTime();
    navModalOpen.value = true;
  }

  function resetNavDraft() {
    navModalOpen.value = false;
    navDraft.fundId = '';
    navDraft.fundCode = '';
    navDraft.unitNav = '';
    navDraft.currency = '';
    navDraft.valuationTime = localDateTime();
  }

  function syncNavFund(fundId: string) {
    const fund = funds.value.find((item) => item.fundId === fundId);
    navDraft.fundCode = fund?.fundCode || '';
    navDraft.currency = fund?.baseCurrency || '';
  }

  async function saveNav() {
    if (!navDraft.fundId || !plainDecimal(navDraft.unitNav)) {
      message.warning('请选择基金并输入合法的非负单位净值');
      return;
    }
    if (!navDraft.valuationTime) {
      message.warning('请选择净值估值时间');
      return;
    }
    savingNav.value = true;
    try {
      await runSensitive(async () => {
        await putHoldingFundNav(navDraft.fundId, {
          unitNav: navDraft.unitNav,
          valuationTime: toIso(navDraft.valuationTime),
          currency: navDraft.currency,
          source: 'manual_admin',
          fundCode: navDraft.fundCode.trim() || undefined,
        });
        message.success('基金净值已更新');
        resetNavDraft();
        await loadAll();
        emit('changed');
      });
    } catch (error) {
      message.error(error instanceof Error ? error.message : '基金净值更新失败');
    } finally {
      savingNav.value = false;
    }
  }

  async function runSensitive(action: () => Promise<void>) {
    try {
      await action();
    } catch (error) {
      if (
        error instanceof UserSystemApiError &&
        error.code === 'recent_reauthentication_required'
      ) {
        pendingSensitiveAction.value = action;
        reauthPassword.value = '';
        reauthOpen.value = true;
        return;
      }
      throw error;
    }
  }

  async function submitReauthentication() {
    if (!reauthPassword.value) {
      message.warning('请输入当前密码');
      return;
    }
    reauthLoading.value = true;
    try {
      await reauthenticateUser(reauthPassword.value);
      const action = pendingSensitiveAction.value;
      cancelReauthentication();
      if (action) await action();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '密码验证失败');
    } finally {
      reauthLoading.value = false;
    }
  }

  function cancelReauthentication() {
    reauthOpen.value = false;
    reauthPassword.value = '';
    pendingSensitiveAction.value = null;
  }

  function plainDecimal(value: string) {
    return /^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(value);
  }

  function localDateTime(value?: string) {
    const date = value ? new Date(value) : new Date();
    if (Number.isNaN(date.getTime())) return '';
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
    return local.toISOString().slice(0, 16);
  }

  function toIso(value: string) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) throw new Error('时间格式无效');
    return date.toISOString();
  }

  function splitDecimal(value: string) {
    const negative = value.startsWith('-');
    const unsigned = negative ? value.slice(1) : value;
    const [integer = '0', fraction = ''] = unsigned.split('.');
    return { negative, integer, fraction };
  }

  function formatDecimal(value: string) {
    const { negative, integer, fraction } = splitDecimal(value);
    const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${negative ? '-' : ''}${grouped}${fraction ? `.${fraction}` : ''}`;
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

  function returnClass(value?: string) {
    if (!value || value === '0') return '';
    return value.startsWith('-') ? 'negative' : 'positive';
  }

  function navMeta(status: NavStatus) {
    return {
      available: { label: '可用', color: 'green' },
      stale: { label: '过期', color: 'orange' },
      unavailable: { label: '缺失', color: 'default' },
    }[status];
  }

  function formatTime(value?: string) {
    if (!value) return '-';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
  }
</script>

<style scoped>
  .admin-holdings {
    display: grid;
    gap: 16px;
  }

  .toolbar {
    display: flex;
    gap: 12px;
    align-items: center;
    justify-content: space-between;
  }

  .toolbar h4 {
    margin: 0;
    color: #0f172a;
  }

  .toolbar p,
  .subline {
    margin: 4px 0 0;
    color: #64748b;
    font-size: 12px;
  }

  .positive {
    color: #15803d;
  }

  .negative {
    color: #b91c1c;
  }

  @media (max-width: 760px) {
    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
