<template>
  <PageWrapper title="用户管理">
    <div class="users-page">
      <Card :bordered="false" class="vg-panel filter-card">
        <div class="filter-row">
          <Input.Search
            v-model:value="filters.search"
            allow-clear
            class="search-input"
            placeholder="搜索用户名、姓名、邮箱或手机号"
            @search="applyFilters"
          />
          <Select
            v-model:value="filters.role"
            allow-clear
            class="filter-select"
            placeholder="全部角色"
            :options="allRoleOptions"
          />
          <Select
            v-model:value="filters.status"
            allow-clear
            class="filter-select"
            placeholder="全部状态"
            :options="statusOptions"
          />
          <Space>
            <Button type="primary" :loading="loading" @click="applyFilters">查询</Button>
            <Button @click="resetFilters">重置</Button>
          </Space>
          <Button
            v-if="canCreateUser"
            type="primary"
            class="create-button"
            @click="openCreateModal"
          >
            新增用户
          </Button>
        </div>
      </Card>

      <div class="summary-grid">
        <Card :bordered="false" class="vg-panel summary-card">
          <span>筛选结果</span>
          <strong>{{ pageState.total }}</strong>
        </Card>
        <Card :bordered="false" class="vg-panel summary-card">
          <span>当前页正常账号</span>
          <strong>{{ activeCount }}</strong>
        </Card>
        <Card :bordered="false" class="vg-panel summary-card">
          <span>当前页待审核</span>
          <strong>{{ pendingCount }}</strong>
        </Card>
        <Card :bordered="false" class="vg-panel summary-card">
          <span>数据范围</span>
          <strong>{{ contactScopeLabel }}</strong>
        </Card>
      </div>

      <Card :bordered="false" class="vg-panel table-card">
        <Table
          row-key="userId"
          size="middle"
          :columns="columns"
          :data-source="users"
          :loading="loading"
          :pagination="false"
          :scroll="{ x: 1160 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'identity'">
              <div class="identity-cell">
                <div class="identity-avatar">
                  {{ initial(record.displayName || record.realName || record.username) }}
                </div>
                <div>
                  <button type="button" class="identity-name" @click="openDetail(record.userId)">
                    {{ record.displayName || record.realName || record.username }}
                  </button>
                  <div class="identity-sub">{{ record.username }}</div>
                </div>
              </div>
            </template>
            <template v-else-if="column.key === 'role'">
              <Tag :color="roleColor(record.role || record.requestedRole)">
                {{ roleLabel(record.role || record.requestedRole) }}
              </Tag>
            </template>
            <template v-else-if="column.key === 'contact'">
              <div>{{ record.email || '-' }}</div>
              <div class="muted-line">{{ record.phone || '-' }}</div>
              <Tag v-if="record.contactMasked" class="mt-1">后端脱敏</Tag>
            </template>
            <template v-else-if="column.key === 'status'">
              <Tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</Tag>
            </template>
            <template v-else-if="column.key === 'sessions'">
              {{ record.activeSessionCount }}
            </template>
            <template v-else-if="column.key === 'registeredAt'">
              {{ formatTime(record.registeredAt) }}
            </template>
            <template v-else-if="column.key === 'lastLoginAt'">
              {{ formatTime(record.lastLoginAt) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <Button type="link" size="small" @click="openDetail(record.userId)">查看详情</Button>
            </template>
          </template>
          <template #emptyText>
            <Empty description="没有符合条件的用户" />
          </template>
        </Table>

        <div class="pagination-row">
          <Pagination
            :current="pageState.page"
            :page-size="pageState.pageSize"
            :total="pageState.total"
            :show-size-changer="true"
            :page-size-options="['10', '20', '50', '100']"
            show-less-items
            @change="changePage"
            @show-size-change="changePageSize"
          />
        </div>
      </Card>
    </div>

    <Modal
      v-model:open="createOpen"
      title="新增用户"
      :width="680"
      :confirm-loading="creating"
      @ok="submitCreate"
      @cancel="resetCreate"
    >
      <Alert
        class="mb-4"
        type="info"
        show-icon
        message="平台不会生成或展示临时密码"
        description="创建成功后只返回一次性重置凭证，由用户自行设置新密码。"
      />
      <Form layout="vertical" :model="createDraft">
        <div class="form-grid">
          <Form.Item label="用户名" required>
            <Input v-model:value="createDraft.username" :maxlength="64" />
          </Form.Item>
          <Form.Item label="真实姓名" required>
            <Input v-model:value="createDraft.realName" :maxlength="128" />
          </Form.Item>
          <Form.Item label="展示名称">
            <Input v-model:value="createDraft.displayName" :maxlength="128" />
          </Form.Item>
          <Form.Item label="角色" required>
            <Select v-model:value="createDraft.role" :options="createRoleOptions" />
          </Form.Item>
          <Form.Item label="邮箱">
            <Input v-model:value="createDraft.email" :maxlength="254" />
          </Form.Item>
          <Form.Item label="手机号">
            <Input v-model:value="createDraft.phone" :maxlength="32" />
          </Form.Item>
          <Form.Item v-if="createDraft.role === 'employee'" label="部门" required>
            <Input v-model:value="createDraft.department" :maxlength="128" />
          </Form.Item>
          <Form.Item v-if="createDraft.role === 'member'" label="会员类型" required>
            <Input v-model:value="createDraft.memberType" :maxlength="128" />
          </Form.Item>
        </div>
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

    <Modal v-model:open="ticketOpen" title="用户创建成功" :footer="null" @cancel="clearTicket">
      <Alert
        type="warning"
        show-icon
        message="一次性重置凭证只展示一次"
        description="请立即通过安全渠道交给用户，关闭后平台不会再次显示原始凭证。"
      />
      <Input.TextArea class="mt-4" :value="issuedTicket" :rows="5" readonly />
      <p class="ticket-expiry">有效期至：{{ formatTime(ticketExpiresAt) }}</p>
      <Button type="primary" block @click="copyTicket">复制凭证</Button>
    </Modal>

    <UserDetailDrawer
      :open="detailOpen"
      :user-id="selectedUserId"
      :current-user-id="currentUserId"
      :current-role="currentRole"
      :permissions="permissions"
      @close="closeDetail"
      @changed="handleDetailChanged"
    />
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue';
  import {
    Alert,
    Button,
    Card,
    Empty,
    Form,
    Input,
    message,
    Modal,
    Pagination,
    Select,
    Space,
    Table,
    Tag,
  } from 'ant-design-vue';
  import { PageWrapper } from '@/components/Page';
  import { useUserStore } from '@/store/modules/user';
  import { hasPermission } from '@/access/userAccess';
  import { ROLE_COLOR_MAP, ROLE_LABEL_MAP } from '@/hooks/web/useRoleAccess';
  import UserDetailDrawer from './components/UserDetailDrawer.vue';
  import {
    UserSystemApiError,
    createAdminUser,
    listAdminUsers,
    reauthenticateUser,
    type AdminUserSummary,
    type HumanRole,
    type UserLifecycleStatus,
  } from '@/api/platform/userSystem';

  const userStore = useUserStore();
  const loading = ref(false);
  const users = ref<AdminUserSummary[]>([]);
  const detailOpen = ref(false);
  const selectedUserId = ref('');
  const createOpen = ref(false);
  const creating = ref(false);
  const reauthOpen = ref(false);
  const reauthPassword = ref('');
  const reauthLoading = ref(false);
  const pendingSensitiveAction = ref<(() => Promise<void>) | null>(null);
  const ticketOpen = ref(false);
  const issuedTicket = ref('');
  const ticketExpiresAt = ref('');

  const filters = reactive<{
    search: string;
    role?: HumanRole;
    status?: UserLifecycleStatus;
  }>({ search: '' });
  const pageState = reactive({ page: 1, pageSize: 20, total: 0 });
  const createDraft = reactive({
    username: '',
    displayName: '',
    realName: '',
    email: '',
    phone: '',
    role: 'member' as HumanRole,
    department: '',
    memberType: '',
  });

  const authentication = computed(() => userStore.getAuthentication);
  const permissions = computed(() => authentication.value?.permissions || []);
  const currentRole = computed<HumanRole>(() => authentication.value?.user.role || 'employee');
  const currentUserId = computed(() => authentication.value?.user.userId || '');
  const canCreateUser = computed(() => hasPermission(permissions.value, 'user.create'));
  const activeCount = computed(() => users.value.filter((item) => item.status === 'active').length);
  const pendingCount = computed(
    () => users.value.filter((item) => item.status === 'pending').length,
  );
  const contactScopeLabel = computed(() =>
    hasPermission(permissions.value, 'user.sensitive.read') ? '完整' : '脱敏',
  );
  const createRoleOptions = computed(() => {
    const roles: HumanRole[] =
      currentRole.value === 'ceo'
        ? ['ceo', 'tech_lead', 'employee', 'member']
        : ['employee', 'member'];
    return roles.map((value) => ({ value, label: roleLabel(value) }));
  });

  const allRoleOptions = ['ceo', 'tech_lead', 'employee', 'member'].map((value) => ({
    value,
    label: roleLabel(value),
  }));
  const statusOptions = [
    { value: 'pending', label: '待审核' },
    { value: 'active', label: '正常' },
    { value: 'disabled', label: '已停用' },
    { value: 'rejected', label: '已拒绝' },
  ];
  const columns: Array<{
    title: string;
    key: string;
    width: number;
    fixed?: 'left' | 'right';
    align?: 'center';
  }> = [
    { title: '用户', key: 'identity', width: 230, fixed: 'left' },
    { title: '角色', key: 'role', width: 110 },
    { title: '联系方式', key: 'contact', width: 230 },
    { title: '状态', key: 'status', width: 100 },
    { title: '活跃设备', key: 'sessions', width: 100, align: 'center' },
    { title: '注册时间', key: 'registeredAt', width: 170 },
    { title: '最近登录', key: 'lastLoginAt', width: 170 },
    { title: '操作', key: 'action', width: 100, fixed: 'right' },
  ];

  onMounted(loadUsers);

  async function loadUsers() {
    loading.value = true;
    try {
      const result = await listAdminUsers({
        search: filters.search.trim() || undefined,
        role: filters.role,
        status: filters.status,
        page: pageState.page,
        pageSize: pageState.pageSize,
        sortBy: 'registered_at',
        sortDirection: 'desc',
      });
      users.value = result.items;
      pageState.total = result.total;
      pageState.page = result.page;
      pageState.pageSize = result.pageSize;
    } catch (error) {
      message.error(errorMessage(error, '用户列表加载失败'));
    } finally {
      loading.value = false;
    }
  }

  function applyFilters() {
    pageState.page = 1;
    loadUsers();
  }

  function resetFilters() {
    filters.search = '';
    filters.role = undefined;
    filters.status = undefined;
    pageState.page = 1;
    loadUsers();
  }

  function changePage(page: number, pageSize: number) {
    pageState.page = page;
    pageState.pageSize = pageSize;
    loadUsers();
  }

  function changePageSize(_current: number, pageSize: number) {
    pageState.page = 1;
    pageState.pageSize = pageSize;
    loadUsers();
  }

  function openDetail(userId: string) {
    selectedUserId.value = userId;
    detailOpen.value = true;
  }

  function closeDetail() {
    detailOpen.value = false;
    selectedUserId.value = '';
  }

  async function handleDetailChanged() {
    await loadUsers();
  }

  function openCreateModal() {
    resetCreateDraft();
    createOpen.value = true;
  }

  function resetCreate() {
    createOpen.value = false;
    resetCreateDraft();
  }

  function resetCreateDraft() {
    createDraft.username = '';
    createDraft.displayName = '';
    createDraft.realName = '';
    createDraft.email = '';
    createDraft.phone = '';
    createDraft.role = 'member';
    createDraft.department = '';
    createDraft.memberType = '';
  }

  async function submitCreate() {
    if (!createDraft.username.trim() || !createDraft.realName.trim()) {
      message.warning('请输入用户名和真实姓名');
      return;
    }
    if (!createDraft.email.trim() && !createDraft.phone.trim()) {
      message.warning('邮箱或手机号至少填写一项');
      return;
    }
    if (createDraft.role === 'employee' && !createDraft.department.trim()) {
      message.warning('员工账号必须填写部门');
      return;
    }
    if (createDraft.role === 'member' && !createDraft.memberType.trim()) {
      message.warning('会员账号必须填写会员类型');
      return;
    }

    creating.value = true;
    try {
      await runSensitive(async () => {
        const result = await createAdminUser({
          username: createDraft.username.trim(),
          displayName: createDraft.displayName.trim() || undefined,
          realName: createDraft.realName.trim(),
          email: createDraft.email.trim() || undefined,
          phone: createDraft.phone.trim() || undefined,
          role: createDraft.role,
          department: createDraft.department.trim() || undefined,
          memberType: createDraft.memberType.trim() || undefined,
        });
        issuedTicket.value = result.resetTicket;
        ticketExpiresAt.value = result.resetTicketExpiresAt;
        createOpen.value = false;
        ticketOpen.value = true;
        resetCreateDraft();
        await loadUsers();
      });
    } catch (error) {
      message.error(errorMessage(error, '用户创建失败'));
    } finally {
      creating.value = false;
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
      message.error(errorMessage(error, '密码验证失败'));
    } finally {
      reauthLoading.value = false;
    }
  }

  function cancelReauthentication() {
    reauthOpen.value = false;
    reauthPassword.value = '';
    pendingSensitiveAction.value = null;
  }

  function clearTicket() {
    ticketOpen.value = false;
    issuedTicket.value = '';
    ticketExpiresAt.value = '';
  }

  async function copyTicket() {
    try {
      await navigator.clipboard.writeText(issuedTicket.value);
      message.success('凭证已复制，请立即通过安全渠道传递');
    } catch {
      message.error('复制失败，请手动复制');
    }
  }

  function initial(value: string) {
    return value.trim().slice(0, 1).toUpperCase() || '?';
  }

  function roleLabel(role?: string) {
    return role ? ROLE_LABEL_MAP[role] || role : '-';
  }

  function roleColor(role?: string) {
    return role ? ROLE_COLOR_MAP[role] || 'default' : 'default';
  }

  function statusLabel(status: string) {
    return (
      {
        pending: '待审核',
        active: '正常',
        disabled: '已停用',
        rejected: '已拒绝',
      }[status] || status
    );
  }

  function statusColor(status: string) {
    return (
      {
        pending: 'orange',
        active: 'green',
        disabled: 'red',
        rejected: 'default',
      }[status] || 'default'
    );
  }

  function formatTime(value?: string) {
    if (!value) return '-';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false });
  }

  function errorMessage(error: unknown, fallback: string) {
    return error instanceof Error ? error.message : fallback;
  }
</script>

<style scoped>
  .users-page {
    padding: 16px;
  }

  .vg-panel {
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .filter-card,
  .table-card {
    margin-bottom: 16px;
  }

  .filter-row {
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
  }

  .search-input {
    width: min(360px, 100%);
  }

  .filter-select {
    width: 150px;
  }

  .create-button {
    margin-left: auto;
  }

  .summary-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-bottom: 16px;
  }

  .summary-card span,
  .summary-card strong {
    display: block;
  }

  .summary-card span {
    margin-bottom: 8px;
    color: #64748b;
    font-size: 12px;
  }

  .summary-card strong {
    color: #0f172a;
    font-size: 22px;
  }

  .identity-cell {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .identity-avatar {
    display: flex;
    width: 38px;
    height: 38px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #e2e8f0;
    color: #334155;
    font-weight: 700;
  }

  .identity-name {
    padding: 0;
    border: 0;
    background: transparent;
    color: #0f172a;
    cursor: pointer;
    font-weight: 600;
    text-align: left;
  }

  .identity-name:hover {
    color: #1677ff;
  }

  .identity-sub,
  .muted-line {
    margin-top: 3px;
    color: #64748b;
    font-size: 12px;
  }

  .pagination-row {
    display: flex;
    justify-content: flex-end;
    padding-top: 18px;
  }

  .form-grid {
    display: grid;
    gap: 0 16px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ticket-expiry {
    margin: 12px 0;
    color: #64748b;
  }

  @media (max-width: 960px) {
    .summary-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .create-button {
      margin-left: 0;
    }
  }

  @media (max-width: 640px) {
    .summary-grid,
    .form-grid {
      grid-template-columns: 1fr;
    }

    .filter-select,
    .search-input {
      width: 100%;
    }
  }
</style>
