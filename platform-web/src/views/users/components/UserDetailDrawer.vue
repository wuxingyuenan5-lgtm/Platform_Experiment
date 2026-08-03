<template>
  <Drawer :open="open" :width="920" title="用户详情" destroy-on-close @close="emit('close')">
    <Spin :spinning="loading">
      <template v-if="detail">
        <div class="drawer-heading">
          <div>
            <h3>{{ detail.displayName || detail.realName || detail.username }}</h3>
            <p>{{ detail.username }} · {{ detail.userId }}</p>
          </div>
          <Space>
            <Tag :color="roleColor(detail.role || detail.requestedRole)">
              {{ roleLabel(detail.role || detail.requestedRole) }}
            </Tag>
            <Tag :color="statusColor(detail.status)">{{ statusLabel(detail.status) }}</Tag>
          </Space>
        </div>

        <Alert
          v-if="detail.contactMasked"
          class="mb-4"
          type="info"
          show-icon
          message="联系方式已脱敏"
          description="当前角色只能查看后端返回的脱敏信息。"
        />

        <Tabs v-model:active-key="activeTab">
          <TabPane key="profile" tab="基本资料">
            <Form layout="vertical" :model="profileDraft">
              <div class="form-grid">
                <Form.Item label="用户名">
                  <Input :value="detail.username" disabled />
                </Form.Item>
                <Form.Item label="展示名称">
                  <Input v-model:value="profileDraft.displayName" :disabled="!canEdit" />
                </Form.Item>
                <Form.Item label="真实姓名">
                  <Input v-model:value="profileDraft.realName" :disabled="!canEdit" />
                </Form.Item>
                <Form.Item label="邮箱">
                  <Input v-model:value="profileDraft.email" :disabled="!canEdit" />
                </Form.Item>
                <Form.Item label="手机号">
                  <Input v-model:value="profileDraft.phone" :disabled="!canEdit" />
                </Form.Item>
                <Form.Item label="部门">
                  <Input v-model:value="profileDraft.department" :disabled="!canEdit" />
                </Form.Item>
                <Form.Item label="会员类型">
                  <Input v-model:value="profileDraft.memberType" :disabled="!canEdit" />
                </Form.Item>
                <Form.Item label="注册时间">
                  <Input :value="formatTime(detail.registeredAt)" disabled />
                </Form.Item>
              </div>
              <Space v-if="canEdit">
                <Button @click="syncProfileDraft">恢复</Button>
                <Button type="primary" :loading="savingProfile" @click="saveProfile">
                  保存资料
                </Button>
              </Space>
            </Form>

            <div v-if="canEditNote" class="note-section">
              <div class="section-heading">
                <div>
                  <h4>运营备注</h4>
                  <p>仅管理人员可见，用于记录客户来源、沟通情况和跟进重点。</p>
                </div>
                <Tag>不进入会员端</Tag>
              </div>
              <Spin :spinning="noteLoading">
                <Input.TextArea
                  v-model:value="noteDraft"
                  :rows="4"
                  :maxlength="2000"
                  show-count
                  placeholder="例如：朋友介绍，已完成产品说明，下周回访。"
                />
                <Space class="mt-3">
                  <Button @click="syncNoteDraft">恢复</Button>
                  <Button type="primary" :loading="savingNote" @click="saveNote">保存备注</Button>
                </Space>
                <p class="note-meta">最近更新：{{ formatTime(adminNote?.updatedAt) }}</p>
              </Spin>
            </div>

            <Divider />
            <Descriptions :column="1" size="small" bordered>
              <Descriptions.Item label="申请身份">
                {{ roleLabel(detail.requestedRole) }}
              </Descriptions.Item>
              <Descriptions.Item label="申请说明">
                {{ detail.applicationNote || '-' }}
              </Descriptions.Item>
              <Descriptions.Item label="拒绝原因">
                {{ detail.rejectionReason || '-' }}
              </Descriptions.Item>
              <Descriptions.Item label="最近登录">
                {{ formatTime(detail.lastLoginAt) }}
              </Descriptions.Item>
              <Descriptions.Item label="活跃 Session">
                {{ detail.activeSessionCount }}
              </Descriptions.Item>
            </Descriptions>
          </TabPane>

          <TabPane key="authority" tab="角色与状态">
            <Descriptions :column="1" size="small" bordered>
              <Descriptions.Item label="当前角色">
                {{ roleLabel(detail.role) }}
              </Descriptions.Item>
              <Descriptions.Item label="账号状态">
                {{ statusLabel(detail.status) }}
              </Descriptions.Item>
              <Descriptions.Item label="权限点">
                <Space wrap>
                  <Tag v-for="permission in detail.permissions" :key="permission">
                    {{ permission }}
                  </Tag>
                  <span v-if="detail.permissions.length === 0">-</span>
                </Space>
              </Descriptions.Item>
            </Descriptions>

            <div v-if="canManage" class="action-section">
              <h4>管理操作</h4>
              <Space wrap>
                <Button
                  v-if="detail.status === 'pending'"
                  type="primary"
                  @click="openAction('approve')"
                >
                  通过申请
                </Button>
                <Button v-if="detail.status === 'pending'" danger @click="openAction('reject')">
                  拒绝申请
                </Button>
                <Button
                  v-if="detail.status === 'active' || detail.status === 'disabled'"
                  @click="openAction('role')"
                >
                  修改角色
                </Button>
                <Button v-if="detail.status === 'active'" danger @click="openAction('disable')">
                  停用账号
                </Button>
                <Button v-if="detail.status === 'disabled'" @click="openAction('enable')">
                  启用账号
                </Button>
              </Space>
            </div>
          </TabPane>

          <TabPane key="security" tab="账号与 Session">
            <div class="security-summary">
              <div>
                <span>活跃设备</span>
                <strong>{{ detail.activeSessionCount }}</strong>
              </div>
              <div>
                <span>最近登录</span>
                <strong>{{ formatTime(detail.lastLoginAt) }}</strong>
              </div>
            </div>
            <Space v-if="canManage" wrap class="mt-4">
              <Button
                v-if="canResetPassword"
                danger
                :loading="issuingTicket"
                @click="confirmResetTicket"
              >
                签发一次性重置凭证
              </Button>
              <Button
                v-if="canRevokeSessions"
                danger
                :loading="revokingSessions"
                @click="confirmRevokeSessions"
              >
                强制退出全部设备
              </Button>
            </Space>
            <Alert
              class="mt-4"
              type="warning"
              show-icon
              message="密码和 Session 操作要求近期再认证"
              description="平台不会显示或保存用户密码；一次性重置凭证只展示一次。"
            />
          </TabPane>

          <TabPane v-if="canReadHoldings" key="holdings" tab="基金持仓">
            <UserHoldingsPanel
              :user-id="detail.userId"
              :permissions="permissions"
              :active="activeTab === 'holdings'"
              @changed="handleHoldingsChanged"
            />
          </TabPane>

          <TabPane v-if="canReadAudit" key="audit" tab="审计记录">
            <Spin :spinning="auditLoading">
              <List :data-source="auditEvents" item-layout="vertical">
                <template #renderItem="{ item }">
                  <ListItem>
                    <ListItemMeta
                      :title="item.eventType"
                      :description="`${formatTime(item.createdAt)} · ${item.result || '-'} · ${
                        item.authMethod || '-'
                      }`"
                    />
                    <pre class="audit-details">{{ formatAudit(item.details) }}</pre>
                  </ListItem>
                </template>
              </List>
              <Empty v-if="!auditLoading && auditEvents.length === 0" description="暂无审计记录" />
            </Spin>
          </TabPane>
        </Tabs>
      </template>
      <Empty v-else-if="!loading" description="用户不存在或无权查看" />
    </Spin>

    <Modal
      v-model:open="actionModalOpen"
      :title="actionModalTitle"
      :confirm-loading="actionSubmitting"
      @ok="submitAction"
      @cancel="resetAction"
    >
      <Form layout="vertical">
        <Form.Item v-if="actionType === 'approve' || actionType === 'role'" label="目标角色">
          <Select v-model:value="actionDraft.role" :options="roleOptions" />
        </Form.Item>
        <Form.Item
          v-if="actionType === 'reject' || actionType === 'disable' || actionType === 'enable'"
          label="原因"
          required
        >
          <Input.TextArea v-model:value="actionDraft.reason" :rows="4" :maxlength="1000" />
        </Form.Item>
        <Alert
          v-if="actionType === 'role' || actionType === 'disable'"
          type="warning"
          show-icon
          message="操作成功后将撤销该用户全部 Session"
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

    <Modal
      v-model:open="ticketOpen"
      title="一次性密码重置凭证"
      :footer="null"
      @cancel="clearTicket"
    >
      <Alert
        type="warning"
        show-icon
        message="该凭证只展示一次"
        description="请通过安全渠道交给用户。关闭窗口后平台不会再次显示原始凭证。"
      />
      <Input.TextArea class="mt-4" :value="issuedTicket" :rows="5" readonly />
      <p class="ticket-expiry">有效期至：{{ formatTime(ticketExpiresAt) }}</p>
      <Button type="primary" block @click="copyTicket">复制凭证</Button>
    </Modal>
  </Drawer>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, watch } from 'vue';
  import {
    Alert,
    Button,
    Descriptions,
    Divider,
    Drawer,
    Empty,
    Form,
    Input,
    List,
    ListItem,
    ListItemMeta,
    message,
    Modal,
    Select,
    Space,
    Spin,
    TabPane,
    Tabs,
    Tag,
  } from 'ant-design-vue';
  import {
    UserSystemApiError,
    approveAdminUser,
    changeAdminUserRole,
    changeAdminUserStatus,
    getAdminUser,
    getAdminUserAudit,
    issueAdminPasswordResetTicket,
    reauthenticateUser,
    rejectAdminUser,
    revokeAdminUserSessions,
    updateAdminUser,
    type AdminUserDetail,
    type HumanRole,
    type UserAuditEvent,
  } from '@/api/platform/userSystem';
  import {
    getUserAdminNote,
    updateUserAdminNote,
    type UserAdminNote,
  } from '@/api/platform/userAdminNotes';
  import { hasPermission } from '@/access/userAccess';
  import { ROLE_COLOR_MAP, ROLE_LABEL_MAP } from '@/hooks/web/useRoleAccess';
  import UserHoldingsPanel from './UserHoldingsPanel.vue';

  type ActionType = 'approve' | 'reject' | 'role' | 'disable' | 'enable' | null;

  interface Props {
    open: boolean;
    userId?: string;
    currentUserId?: string;
    currentRole?: HumanRole;
    permissions?: string[];
  }

  const props = withDefaults(defineProps<Props>(), {
    userId: '',
    currentUserId: '',
    currentRole: 'employee',
    permissions: () => [],
  });
  const emit = defineEmits<{ close: []; changed: [] }>();

  const loading = ref(false);
  const detail = ref<AdminUserDetail | null>(null);
  const activeTab = ref('profile');
  const savingProfile = ref(false);
  const adminNote = ref<UserAdminNote | null>(null);
  const noteDraft = ref('');
  const noteLoading = ref(false);
  const savingNote = ref(false);
  const auditLoading = ref(false);
  const auditEvents = ref<UserAuditEvent[]>([]);
  const actionModalOpen = ref(false);
  const actionType = ref<ActionType>(null);
  const actionSubmitting = ref(false);
  const issuingTicket = ref(false);
  const revokingSessions = ref(false);
  const reauthOpen = ref(false);
  const reauthPassword = ref('');
  const reauthLoading = ref(false);
  const pendingSensitiveAction = ref<(() => Promise<void>) | null>(null);
  const ticketOpen = ref(false);
  const issuedTicket = ref('');
  const ticketExpiresAt = ref('');

  const profileDraft = reactive({
    displayName: '',
    realName: '',
    email: '',
    phone: '',
    department: '',
    memberType: '',
  });
  const actionDraft = reactive({ role: 'member' as HumanRole, reason: '' });

  const targetRole = computed(() => detail.value?.role || detail.value?.requestedRole);
  const canManage = computed(() => {
    if (!detail.value || props.currentUserId === detail.value.userId) return false;
    if (props.currentRole === 'ceo') return true;
    return (
      props.currentRole === 'tech_lead' && ['employee', 'member'].includes(String(targetRole.value))
    );
  });
  const canEdit = computed(
    () => !!detail.value && hasPermission(props.permissions, 'user.update') && canManage.value,
  );
  const canEditNote = computed(
    () =>
      canManage.value &&
      hasPermission(props.permissions, 'user.update') &&
      hasPermission(props.permissions, 'user.sensitive.read'),
  );
  const canResetPassword = computed(() => hasPermission(props.permissions, 'user.reset_password'));
  const canRevokeSessions = computed(() => hasPermission(props.permissions, 'user.session.revoke'));
  const canReadAudit = computed(() => hasPermission(props.permissions, 'user.audit.read'));
  const canReadHoldings = computed(
    () =>
      targetRole.value === 'member' && hasPermission(props.permissions, 'member.holding.read_all'),
  );
  const roleOptions = computed(() => {
    const values: HumanRole[] =
      props.currentRole === 'ceo'
        ? ['ceo', 'tech_lead', 'employee', 'member']
        : ['employee', 'member'];
    return values.map((value) => ({ value, label: roleLabel(value) }));
  });
  const actionModalTitle = computed(() => {
    const titles: Record<Exclude<ActionType, null>, string> = {
      approve: '通过注册申请',
      reject: '拒绝注册申请',
      role: '修改用户角色',
      disable: '停用用户',
      enable: '启用用户',
    };
    return actionType.value ? titles[actionType.value] : '用户操作';
  });

  watch(
    () => [props.open, props.userId],
    async ([open, userId]) => {
      if (open && userId) {
        activeTab.value = 'profile';
        await loadDetail();
      }
    },
    { immediate: true },
  );

  watch(activeTab, async (value) => {
    if (value === 'audit' && canReadAudit.value) await loadAudit();
  });

  async function loadDetail() {
    if (!props.userId) return;
    loading.value = true;
    try {
      detail.value = await getAdminUser(props.userId);
      syncProfileDraft();
      if (canEditNote.value) await loadNote();
      else {
        adminNote.value = null;
        noteDraft.value = '';
      }
      if (activeTab.value === 'audit' && canReadAudit.value) await loadAudit();
    } catch (error) {
      detail.value = null;
      message.error(errorMessage(error, '用户详情加载失败'));
    } finally {
      loading.value = false;
    }
  }

  async function loadNote() {
    if (!props.userId || !canEditNote.value) return;
    noteLoading.value = true;
    try {
      adminNote.value = await getUserAdminNote(props.userId);
      syncNoteDraft();
    } catch (error) {
      adminNote.value = null;
      noteDraft.value = '';
      message.error(errorMessage(error, '运营备注加载失败'));
    } finally {
      noteLoading.value = false;
    }
  }

  async function loadAudit() {
    if (!props.userId || !canReadAudit.value) return;
    auditLoading.value = true;
    try {
      auditEvents.value = await getAdminUserAudit(props.userId);
    } catch (error) {
      message.error(errorMessage(error, '审计记录加载失败'));
    } finally {
      auditLoading.value = false;
    }
  }

  async function handleHoldingsChanged() {
    emit('changed');
    if (canReadAudit.value) await loadAudit();
  }

  function syncProfileDraft() {
    if (!detail.value) return;
    profileDraft.displayName = detail.value.displayName || '';
    profileDraft.realName = detail.value.realName || '';
    profileDraft.email = detail.value.email || '';
    profileDraft.phone = detail.value.phone || '';
    profileDraft.department = detail.value.department || '';
    profileDraft.memberType = detail.value.memberType || '';
  }

  function syncNoteDraft() {
    noteDraft.value = adminNote.value?.adminNote || '';
  }

  async function saveProfile() {
    if (!detail.value || !canEdit.value) return;
    savingProfile.value = true;
    try {
      await runSensitive(async () => {
        detail.value = await updateAdminUser(detail.value!.userId, {
          displayName: profileDraft.displayName || undefined,
          realName: profileDraft.realName || undefined,
          email: profileDraft.email || undefined,
          phone: profileDraft.phone || undefined,
          department: profileDraft.department || undefined,
          memberType: profileDraft.memberType || undefined,
          expectedVersion: detail.value!.rowVersion,
        });
        syncProfileDraft();
        if (canEditNote.value) await loadNote();
        message.success('用户资料已更新');
        emit('changed');
      });
    } catch (error) {
      message.error(errorMessage(error, '用户资料更新失败'));
    } finally {
      savingProfile.value = false;
    }
  }

  async function saveNote() {
    if (!detail.value || !adminNote.value || !canEditNote.value) return;
    savingNote.value = true;
    try {
      adminNote.value = await updateUserAdminNote(
        detail.value.userId,
        noteDraft.value.trim() || null,
        adminNote.value.rowVersion,
      );
      syncNoteDraft();
      detail.value = await getAdminUser(detail.value.userId);
      message.success('运营备注已保存');
      emit('changed');
    } catch (error) {
      message.error(errorMessage(error, '运营备注保存失败'));
    } finally {
      savingNote.value = false;
    }
  }

  function openAction(type: Exclude<ActionType, null>) {
    if (!detail.value || !canManage.value) return;
    actionType.value = type;
    actionDraft.reason = '';
    actionDraft.role = (detail.value.role || detail.value.requestedRole || 'member') as HumanRole;
    actionModalOpen.value = true;
  }

  function resetAction() {
    actionModalOpen.value = false;
    actionType.value = null;
    actionDraft.reason = '';
  }

  async function submitAction() {
    if (!detail.value || !actionType.value) return;
    if (['reject', 'disable', 'enable'].includes(actionType.value) && !actionDraft.reason.trim()) {
      message.warning('请输入操作原因');
      return;
    }
    actionSubmitting.value = true;
    try {
      await runSensitive(async () => {
        const current = detail.value!;
        if (actionType.value === 'approve') {
          if (!['employee', 'member'].includes(actionDraft.role)) {
            throw new Error('公开注册申请只能批准为员工或会员');
          }
          detail.value = await approveAdminUser(
            current.userId,
            actionDraft.role as 'employee' | 'member',
            current.rowVersion,
          );
        } else if (actionType.value === 'reject') {
          detail.value = await rejectAdminUser(
            current.userId,
            actionDraft.reason.trim(),
            current.rowVersion,
          );
        } else if (actionType.value === 'role') {
          detail.value = await changeAdminUserRole(
            current.userId,
            actionDraft.role,
            current.rowVersion,
          );
        } else {
          detail.value = await changeAdminUserStatus(
            current.userId,
            actionType.value === 'disable' ? 'disabled' : 'active',
            actionDraft.reason.trim(),
            current.rowVersion,
          );
        }
        resetAction();
        syncProfileDraft();
        if (canEditNote.value) await loadNote();
        message.success('用户状态已更新');
        emit('changed');
      });
    } catch (error) {
      message.error(errorMessage(error, '用户操作失败'));
    } finally {
      actionSubmitting.value = false;
    }
  }

  function confirmResetTicket() {
    Modal.confirm({
      title: '签发一次性重置凭证？',
      content: '该操作将撤销目标用户全部 Session，原始凭证只展示一次。',
      okText: '确认签发',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        if (!detail.value) return;
        issuingTicket.value = true;
        try {
          await runSensitive(async () => {
            const result = await issueAdminPasswordResetTicket(detail.value!.userId);
            issuedTicket.value = result.resetTicket;
            ticketExpiresAt.value = result.expiresAt;
            ticketOpen.value = true;
            detail.value = await getAdminUser(detail.value!.userId);
            emit('changed');
          });
        } catch (error) {
          message.error(errorMessage(error, '重置凭证签发失败'));
        } finally {
          issuingTicket.value = false;
        }
      },
    });
  }

  function confirmRevokeSessions() {
    Modal.confirm({
      title: '强制退出全部设备？',
      content: '目标用户的全部活跃 Session 将立即失效。',
      okText: '确认强退',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        if (!detail.value) return;
        revokingSessions.value = true;
        try {
          await runSensitive(async () => {
            const count = await revokeAdminUserSessions(detail.value!.userId);
            message.success(`已撤销 ${count} 个 Session`);
            detail.value = await getAdminUser(detail.value!.userId);
            emit('changed');
          });
        } catch (error) {
          message.error(errorMessage(error, '强制退出失败'));
        } finally {
          revokingSessions.value = false;
        }
      },
    });
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

  function formatAudit(details: Record<string, unknown>) {
    return JSON.stringify(details, null, 2);
  }

  function errorMessage(error: unknown, fallback: string) {
    return error instanceof Error ? error.message : fallback;
  }
</script>

<style scoped>
  .drawer-heading,
  .section-heading {
    display: flex;
    gap: 16px;
    align-items: flex-start;
    justify-content: space-between;
  }

  .drawer-heading {
    margin-bottom: 18px;
  }

  .drawer-heading h3,
  .section-heading h4 {
    margin: 0 0 4px;
    color: #0f172a;
  }

  .drawer-heading h3 {
    font-size: 20px;
  }

  .drawer-heading p,
  .section-heading p,
  .note-meta {
    margin: 0;
    color: #64748b;
    font-size: 12px;
  }

  .form-grid {
    display: grid;
    gap: 0 16px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .note-section,
  .action-section {
    margin-top: 20px;
    padding: 16px;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #f8fafc;
  }

  .note-section :deep(textarea) {
    margin-top: 12px;
    background: #fff;
  }

  .note-meta {
    margin-top: 8px;
  }

  .action-section h4 {
    margin: 0 0 12px;
  }

  .security-summary {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .security-summary > div {
    padding: 16px;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
  }

  .security-summary span,
  .security-summary strong {
    display: block;
  }

  .security-summary span {
    margin-bottom: 6px;
    color: #64748b;
    font-size: 12px;
  }

  .security-summary strong {
    color: #0f172a;
    font-size: 16px;
  }

  .audit-details {
    max-height: 180px;
    overflow: auto;
    margin: 0;
    padding: 10px 12px;
    border-radius: 8px;
    background: #f8fafc;
    color: #475569;
    font-size: 12px;
    white-space: pre-wrap;
  }

  .ticket-expiry {
    margin: 12px 0;
    color: #64748b;
  }

  @media (max-width: 760px) {
    .form-grid,
    .security-summary {
      grid-template-columns: 1fr;
    }
  }
</style>
