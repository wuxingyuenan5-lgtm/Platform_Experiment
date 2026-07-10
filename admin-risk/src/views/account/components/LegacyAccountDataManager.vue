<template>
  <div class="account-page">
    <div class="toolbar">
      <Space>
        <Tag :color="roleColor">{{ roleLabel }}</Tag>
        <Tag v-if="!canOperateData">只读</Tag>
      </Space>
      <Space>
        <Button :loading="loading" @click="loadAccounts">
          <template #icon><ReloadOutlined /></template>
          刷新
        </Button>
        <Button type="primary" :disabled="!canOperateData" :loading="syncing" @click="syncAccounts">
          <template #icon><SyncOutlined /></template>
          同步账户
        </Button>
        <Button v-if="canManageAccounts" type="primary" @click="openCreateModal">
          <template #icon><PlusOutlined /></template>
          新增账户
        </Button>
      </Space>
    </div>

    <Row :gutter="[16, 16]" class="mb-4">
      <Col :xs="24" :md="8">
        <Card :bordered="false" class="metric-card">
          <Statistic title="账户数量" :value="accounts.length" />
        </Card>
      </Col>
      <Col :xs="24" :md="8">
        <Card :bordered="false" class="metric-card">
          <Statistic title="总资产 USD" :value="totalAsset" :precision="2" />
        </Card>
      </Col>
      <Col :xs="24" :md="8">
        <Card :bordered="false" class="metric-card">
          <Statistic title="可用资金 USD" :value="availableFund" :precision="2" />
        </Card>
      </Col>
    </Row>

    <Card :bordered="false" class="vg-panel">
      <Table
        row-key="id"
        :columns="columns"
        :data-source="accounts"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        size="middle"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <div class="account-name">
              <span>{{ record.name }}</span>
              <Tag v-if="record.account_type === 'bybit'" color="blue">Bybit</Tag>
            </div>
            <div class="account-address">{{ record.account_address }}</div>
          </template>
          <template v-else-if="column.key === 'initial_capital'">
            {{ formatMoney(record.initial_capital) }}
          </template>
          <template v-else-if="column.key === 'total_asset'">
            {{ formatMoney(record.total_asset) }}
          </template>
          <template v-else-if="column.key === 'available_fund'">
            {{ formatMoney(record.available_fund) }}
          </template>
          <template v-else-if="column.key === 'status'">
            <Tag :color="record.status === 'active' ? 'green' : 'default'">{{ record.status }}</Tag>
          </template>
          <template v-else-if="column.key === 'credentials'">
            <Tag :color="record.has_api_key && record.has_api_secret ? 'green' : 'orange'">
              {{ record.has_api_key && record.has_api_secret ? '已保存' : '未完整' }}
            </Tag>
          </template>
          <template v-else-if="column.key === 'asset_updated_at'">
            {{ formatDateTime(record.asset_updated_at) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <Popconfirm title="确认删除该账户？" @confirm="removeAccount(record.id)">
              <Button danger size="small">删除</Button>
            </Popconfirm>
          </template>
        </template>
      </Table>
    </Card>

    <Modal
      v-model:open="createModalOpen"
      title="新增账户"
      :confirm-loading="creating"
      @ok="submitAccount"
    >
      <div class="form-grid">
        <label>
          <span>账户名称</span>
          <Input v-model:value="accountForm.name" placeholder="Bybit Unified Account" />
        </label>
        <label>
          <span>账户类型</span>
          <Select v-model:value="accountForm.account_type" :options="accountTypeOptions" />
        </label>
        <label>
          <span>账户地址</span>
          <Input v-model:value="accountForm.account_address" placeholder="bybit-unified" />
        </label>
        <label>
          <span>初始资金</span>
          <InputNumber
            v-model:value="accountForm.initial_capital"
            class="w-full"
            :min="1"
            :precision="2"
          />
        </label>
        <label>
          <span>API Key</span>
          <Input v-model:value="accountForm.api_key" placeholder="保存后不会明文显示" />
        </label>
        <label>
          <span>API Secret</span>
          <Input.Password
            v-model:value="accountForm.api_secret"
            visibilityToggle
            placeholder="后端加密保存"
          />
        </label>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import {
    Button,
    Card,
    Col,
    Input,
    InputNumber,
    message,
    Modal,
    Popconfirm,
    Row,
    Select,
    Space,
    Statistic,
    Table,
    Tag,
  } from 'ant-design-vue';
  import { PlusOutlined, ReloadOutlined, SyncOutlined } from '@ant-design/icons-vue';
  import {
    createAccount,
    DataAccount,
    deleteAccount,
    getAccounts,
    triggerAccountSync,
  } from '@/api/riskControl';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { formateNumStr } from '@/utils/formate';
  import { formatToDateTime } from '@/utils/dateUtil';

  const loading = ref(false);
  const syncing = ref(false);
  const creating = ref(false);
  const createModalOpen = ref(false);
  const accounts = ref<DataAccount[]>([]);
  const router = useRouter();
  const { roleLabel, roleColor, canOperateData, canManageAccounts, canDeleteAccounts } = useRoleAccess();

  const accountForm = reactive({
    name: '',
    account_type: 'bybit',
    account_address: '',
    initial_capital: 1,
    api_key: '',
    api_secret: '',
  });

  const accountTypeOptions = [
    { label: 'Bybit', value: 'bybit' },
    { label: 'Puridia', value: 'puridia' },
    { label: 'MT5 Exam', value: 'mt5_exam' },
    { label: 'Trader A', value: 'trader_a' },
    { label: 'Trader B', value: 'trader_b' },
  ];

  const baseColumns = [
    { title: '账户', dataIndex: 'name', key: 'name', width: 260 },
    { title: '类型', dataIndex: 'account_type', key: 'account_type', width: 120 },
    { title: '初始资金', dataIndex: 'initial_capital', key: 'initial_capital', align: 'right' },
    { title: '总资产', dataIndex: 'total_asset', key: 'total_asset', align: 'right' },
    { title: '可用资金', dataIndex: 'available_fund', key: 'available_fund', align: 'right' },
    { title: 'API 密钥', key: 'credentials', width: 110 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
    { title: '资产更新时间', dataIndex: 'asset_updated_at', key: 'asset_updated_at', width: 190 },
  ];

  const columns = computed(() => {
    if (!canDeleteAccounts.value) return baseColumns;
    return [...baseColumns, { title: '操作', key: 'action', width: 90 }];
  });

  const totalAsset = computed(() =>
    accounts.value.reduce((sum, item) => sum + Number(item.total_asset || 0), 0),
  );
  const availableFund = computed(() =>
    accounts.value.reduce((sum, item) => sum + Number(item.available_fund || 0), 0),
  );

  function formatMoney(value: any) {
    return formateNumStr(value || 0, { decimals: 2, keepZero: true });
  }

  function formatDateTime(value?: string) {
    return value ? formatToDateTime(value) : '-';
  }

  async function loadAccounts() {
    loading.value = true;
    try {
      accounts.value = await getAccounts();
    } finally {
      loading.value = false;
    }
  }

  async function syncAccounts() {
    if (!canOperateData.value) return;
    syncing.value = true;
    try {
      const res = await triggerAccountSync();
      message.success(`账户同步完成：成功 ${res.synced || 0}，失败 ${res.failed || 0}，跳过 ${res.skipped || 0}`);
      await loadAccounts();
    } catch (error: any) {
      message.error(error?.response?.data?.message || error?.message || '账户同步失败');
    } finally {
      syncing.value = false;
    }
  }

  function openCreateModal() {
    accountForm.name = '';
    accountForm.account_type = 'bybit';
    accountForm.account_address = '';
    accountForm.initial_capital = 1;
    accountForm.api_key = '';
    accountForm.api_secret = '';
    createModalOpen.value = true;
  }

  async function submitAccount() {
    if (!accountForm.name || !accountForm.account_address) {
      message.warning('请填写账户名称和账户地址');
      return;
    }
    if (accountForm.account_type === 'bybit' && (!accountForm.api_key || !accountForm.api_secret)) {
      message.warning('新增 Bybit 账户需要填写 API Key 和 API Secret');
      return;
    }
    creating.value = true;
    try {
      const created = await createAccount(accountForm);
      message.success('账户已创建，正在打开资产走势页');
      createModalOpen.value = false;
      await loadAccounts();
      if (created?.id) {
        router.push({
          path: '/data/index',
          query: { account_id: String(created.id) },
        });
      }
    } finally {
      creating.value = false;
    }
  }

  async function removeAccount(id: number) {
    if (!canDeleteAccounts.value) return;
    try {
      await deleteAccount(id);
      message.success('账户已删除');
      await loadAccounts();
    } catch (error: any) {
      message.error(error?.response?.data?.message || error?.message || '账户删除失败');
    }
  }

  onMounted(loadAccounts);
</script>

<style scoped>
  .account-page {
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

  .account-name {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
  }

  .account-address {
    margin-top: 4px;
    color: #59636e;
    font-size: 12px;
    word-break: break-all;
  }

  .form-grid {
    display: grid;
    gap: 14px;
  }

  .form-grid label {
    display: grid;
    gap: 6px;
  }

  .form-grid span {
    color: #364152;
    font-size: 13px;
  }

  @media (max-width: 768px) {
    .account-page {
      padding: 12px;
    }

    .toolbar {
      align-items: flex-start;
      flex-direction: column;
    }
  }
</style>
