<template>
  <PageWrapper title="个人账号">
    <div class="personal-account">
      <Card :bordered="false" class="profile-summary">
        <div class="profile-summary__main">
          <img class="profile-summary__avatar" :src="avatarUrl" alt="avatar" />
          <div class="profile-summary__identity">
            <div class="profile-summary__name-row">
              <h2>{{ displayName }}</h2>
              <Tag :color="roleMeta.color">{{ roleMeta.label }}</Tag>
              <Tag :color="statusMeta.color">{{ statusMeta.label }}</Tag>
            </div>
            <p>{{ profile?.username || '-' }}</p>
            <div class="profile-summary__details">
              <span>{{ profile?.department || profile?.memberType || '未设置组织信息' }}</span>
              <span>最近登录：{{ formatTime(profile?.lastLoginAt) }}</span>
            </div>
          </div>
        </div>
      </Card>

      <Card :bordered="false" class="account-card">
        <Tabs v-model:activeKey="activeTab" @change="handleTabChange">
          <TabPane key="profile" tab="资料与安全">
            <Spin :spinning="loadingProfile">
              <div class="profile-grid">
                <section class="account-section">
                  <div class="section-title">基本资料</div>
                  <Form layout="vertical" :model="profileDraft">
                    <FormItem label="用户名">
                      <Input :value="profile?.username" disabled />
                    </FormItem>
                    <FormItem label="展示名称">
                      <Input v-model:value="profileDraft.displayName" :maxlength="128" />
                    </FormItem>
                    <FormItem label="手机号">
                      <Input v-model:value="profileDraft.phone" autocomplete="tel" />
                    </FormItem>
                    <FormItem label="邮箱">
                      <Input v-model:value="profileDraft.email" autocomplete="email" />
                    </FormItem>
                    <div class="readonly-grid">
                      <div>
                        <span>真实姓名</span>
                        <strong>{{ profile?.realName || '-' }}</strong>
                      </div>
                      <div>
                        <span>角色</span>
                        <strong>{{ roleMeta.label }}</strong>
                      </div>
                      <div>
                        <span>注册时间</span>
                        <strong>{{ formatTime(profile?.registeredAt) }}</strong>
                      </div>
                      <div>
                        <span>资料版本</span>
                        <strong>{{ profile?.rowVersion || '-' }}</strong>
                      </div>
                    </div>
                    <Space>
                      <Button @click="resetProfileDraft">恢复</Button>
                      <Button type="primary" :loading="savingProfile" @click="saveProfile">
                        保存资料
                      </Button>
                    </Space>
                  </Form>
                </section>

                <section class="account-section">
                  <div class="section-title">头像</div>
                  <div class="avatar-editor">
                    <img :src="avatarUrl" alt="avatar preview" />
                    <div class="avatar-editor__actions">
                      <Upload
                        :show-upload-list="false"
                        accept="image/jpeg,image/png,image/webp"
                        :custom-request="uploadAvatar"
                      >
                        <Button type="primary" :loading="uploadingAvatar">上传新头像</Button>
                      </Upload>
                      <Button
                        danger
                        :disabled="!profile?.avatarKey"
                        :loading="deletingAvatar"
                        @click="removeAvatar"
                      >
                        删除头像
                      </Button>
                      <p>支持 JPEG、PNG、WebP，最大 2 MB。图片会由服务器重新裁剪和编码。</p>
                    </div>
                  </div>

                  <Divider />
                  <div class="section-title">账号安全</div>
                  <div class="security-actions">
                    <div>
                      <strong>重新验证身份</strong>
                      <p>修改联系方式等敏感操作前，需要近期重新输入当前密码。</p>
                      <Button @click="openReauth">重新验证</Button>
                    </div>
                    <div>
                      <strong>修改密码</strong>
                      <p>修改成功后所有设备立即退出，需要使用新密码重新登录。</p>
                      <Button @click="passwordVisible = true">修改密码</Button>
                    </div>
                    <div>
                      <strong>退出当前账号</strong>
                      <p>撤销当前服务器 Session，并清除浏览器登录状态。</p>
                      <Button danger @click="userStore.confirmLoginOut()">退出登录</Button>
                    </div>
                  </div>
                </section>
              </div>
            </Spin>
          </TabPane>

          <TabPane key="holdings" tab="基金持仓">
            <HoldingsPanel :role="profile?.role" :active="activeTab === 'holdings'" />
          </TabPane>

          <TabPane key="sessions" tab="登录设备">
            <div class="sessions-header">
              <div>
                <div class="section-title">活动 Session</div>
                <p>设备信息仅展示摘要。撤销后该设备下一次请求会立即失效。</p>
              </div>
              <Space>
                <Button :loading="loadingSessions" @click="loadSessions">刷新</Button>
                <Button
                  danger
                  :loading="revokingOthers"
                  :disabled="sessions.filter((item) => !item.current).length === 0"
                  @click="revokeOthers"
                >
                  退出其他设备
                </Button>
              </Space>
            </div>
            <List :loading="loadingSessions" :data-source="sessions" class="session-list">
              <template #renderItem="{ item }">
                <ListItem>
                  <ListItemMeta>
                    <template #title>
                      <Space>
                        <strong>{{ item.userAgentSummary || '未知设备' }}</strong>
                        <Tag v-if="item.current" color="blue">当前设备</Tag>
                      </Space>
                    </template>
                    <template #description>
                      <div class="session-description">
                        <span>IP：{{ item.ipSummary || '-' }}</span>
                        <span>创建：{{ formatTime(item.createdAt) }}</span>
                        <span>最近活动：{{ formatTime(item.lastSeenAt) }}</span>
                        <span>空闲到期：{{ formatTime(item.idleExpiresAt) }}</span>
                      </div>
                    </template>
                  </ListItemMeta>
                  <template #actions>
                    <Button
                      v-if="!item.current"
                      danger
                      type="link"
                      @click="revokeSession(item.sessionId)"
                    >
                      退出该设备
                    </Button>
                  </template>
                </ListItem>
              </template>
            </List>
          </TabPane>
        </Tabs>
      </Card>
    </div>

    <Modal
      v-model:visible="reauthVisible"
      title="重新验证身份"
      :confirm-loading="reauthenticating"
      @ok="submitReauth"
    >
      <p class="modal-note">请输入当前密码。验证结果只更新当前 Session 的近期认证时间。</p>
      <Input.Password
        v-model:value="reauthPassword"
        placeholder="当前密码"
        autocomplete="current-password"
        @keypress.enter="submitReauth"
      />
    </Modal>

    <Modal
      v-model:visible="passwordVisible"
      title="修改密码"
      :confirm-loading="changingPassword"
      @ok="submitPasswordChange"
    >
      <Form layout="vertical">
        <FormItem label="当前密码">
          <Input.Password v-model:value="passwordDraft.current" autocomplete="current-password" />
        </FormItem>
        <FormItem label="新密码">
          <Input.Password v-model:value="passwordDraft.next" autocomplete="new-password" />
        </FormItem>
        <FormItem label="确认新密码">
          <Input.Password v-model:value="passwordDraft.confirm" autocomplete="new-password" />
        </FormItem>
      </Form>
      <p class="modal-note">新密码长度为 12—128 个字符，不能使用常见弱密码或包含完整联系方式。</p>
    </Modal>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, onMounted, reactive, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import {
    Button,
    Card,
    Divider,
    Form,
    Input,
    List,
    ListItem,
    ListItemMeta,
    message,
    Modal,
    Space,
    Spin,
    TabPane,
    Tabs,
    Tag,
    Upload,
  } from 'ant-design-vue';
  import type { UploadRequestOption } from 'ant-design-vue/es/vc-upload/interface';
  import { PageWrapper } from '@/components/Page';
  import { useUserStore } from '@/store/modules/user';
  import HoldingsPanel from './components/HoldingsPanel.vue';
  import {
    UserSystemApiError,
    changeSelfPassword,
    deleteSelfAvatar,
    getSelfProfile,
    listSelfSessions,
    reauthenticateUser,
    revokeOtherSelfSessions,
    revokeSelfSession,
    selfAvatarUrl,
    updateSelfProfile,
    uploadSelfAvatar,
    type SessionSummary,
    type UserSelf,
  } from '@/api/platform/userSystem';

  const FormItem = Form.Item;
  const router = useRouter();
  const userStore = useUserStore();
  const activeTab = ref('profile');
  const profile = ref<UserSelf>();
  const sessions = ref<SessionSummary[]>([]);
  const loadingProfile = ref(false);
  const savingProfile = ref(false);
  const loadingSessions = ref(false);
  const revokingOthers = ref(false);
  const uploadingAvatar = ref(false);
  const deletingAvatar = ref(false);
  const reauthVisible = ref(false);
  const reauthenticating = ref(false);
  const reauthPassword = ref('');
  const passwordVisible = ref(false);
  const changingPassword = ref(false);
  const pendingProfileRetry = ref(false);

  const profileDraft = reactive({
    displayName: '',
    email: '',
    phone: '',
  });
  const passwordDraft = reactive({ current: '', next: '', confirm: '' });

  const displayName = computed(
    () => profile.value?.displayName || profile.value?.realName || profile.value?.username || '-',
  );
  const avatarUrl = computed(
    () => `${selfAvatarUrl(profile.value?.avatarKey)}?v=${profile.value?.rowVersion || 0}`,
  );
  const roleMeta = computed(() => {
    const values = {
      ceo: { label: 'CEO', color: 'purple' },
      tech_lead: { label: '技术负责人', color: 'blue' },
      employee: { label: '员工', color: 'cyan' },
      member: { label: '会员', color: 'green' },
    };
    return values[profile.value?.role || 'member'];
  });
  const statusMeta = computed(() => {
    const values = {
      pending: { label: '待审核', color: 'orange' },
      active: { label: '正常', color: 'green' },
      disabled: { label: '已停用', color: 'red' },
      rejected: { label: '已拒绝', color: 'default' },
    };
    return values[profile.value?.status || 'active'];
  });

  function formatTime(value?: string) {
    if (!value) return '-';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? '-' : date.toLocaleString('zh-CN', { hour12: false });
  }

  function resetProfileDraft() {
    profileDraft.displayName = profile.value?.displayName || '';
    profileDraft.email = profile.value?.email || '';
    profileDraft.phone = profile.value?.phone || '';
  }

  async function loadProfile() {
    loadingProfile.value = true;
    try {
      profile.value = await getSelfProfile();
      resetProfileDraft();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '个人资料加载失败');
    } finally {
      loadingProfile.value = false;
    }
  }

  async function refreshAuthentication() {
    await userStore.getUserInfoAction();
    await loadProfile();
  }

  async function saveProfile() {
    if (!profile.value || savingProfile.value) return;
    savingProfile.value = true;
    try {
      profile.value = await updateSelfProfile({
        displayName: profileDraft.displayName.trim() || undefined,
        email: profileDraft.email.trim() || undefined,
        phone: profileDraft.phone.trim() || undefined,
        expectedVersion: profile.value.rowVersion,
      });
      resetProfileDraft();
      await userStore.getUserInfoAction();
      message.success('个人资料已更新');
    } catch (error) {
      if (
        error instanceof UserSystemApiError &&
        error.code === 'recent_reauthentication_required'
      ) {
        pendingProfileRetry.value = true;
        openReauth();
      } else {
        message.error(error instanceof Error ? error.message : '资料保存失败');
      }
    } finally {
      savingProfile.value = false;
    }
  }

  function openReauth() {
    reauthPassword.value = '';
    reauthVisible.value = true;
  }

  async function submitReauth() {
    if (!reauthPassword.value || reauthenticating.value) return;
    reauthenticating.value = true;
    try {
      await reauthenticateUser(reauthPassword.value);
      reauthVisible.value = false;
      reauthPassword.value = '';
      message.success('身份验证成功');
      if (pendingProfileRetry.value) {
        pendingProfileRetry.value = false;
        await saveProfile();
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '身份验证失败');
    } finally {
      reauthenticating.value = false;
    }
  }

  async function submitPasswordChange() {
    if (changingPassword.value) return;
    if (passwordDraft.next.length < 12) {
      message.warning('新密码至少 12 个字符');
      return;
    }
    if (passwordDraft.next !== passwordDraft.confirm) {
      message.warning('两次输入的新密码不一致');
      return;
    }
    changingPassword.value = true;
    try {
      await changeSelfPassword(passwordDraft.current, passwordDraft.next, passwordDraft.confirm);
      passwordVisible.value = false;
      await userStore.logout(false);
      message.success('密码已修改，请使用新密码重新登录');
      await router.replace('/login');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '密码修改失败');
    } finally {
      changingPassword.value = false;
      passwordDraft.current = '';
      passwordDraft.next = '';
      passwordDraft.confirm = '';
    }
  }

  async function uploadAvatar(options: UploadRequestOption) {
    if (!profile.value || uploadingAvatar.value) return;
    const file = options.file as File;
    uploadingAvatar.value = true;
    try {
      const result = await uploadSelfAvatar(file, profile.value.rowVersion);
      profile.value.avatarKey = result.avatarKey;
      profile.value.rowVersion = result.rowVersion;
      await refreshAuthentication();
      options.onSuccess?.(result);
      message.success('头像已更新');
    } catch (error) {
      options.onError?.(error as Error);
      message.error(error instanceof Error ? error.message : '头像上传失败');
    } finally {
      uploadingAvatar.value = false;
    }
  }

  async function removeAvatar() {
    if (!profile.value || deletingAvatar.value) return;
    deletingAvatar.value = true;
    try {
      const result = await deleteSelfAvatar(profile.value.rowVersion);
      profile.value.avatarKey = result.avatarKey;
      profile.value.rowVersion = result.rowVersion;
      await refreshAuthentication();
      message.success('头像已删除');
    } catch (error) {
      message.error(error instanceof Error ? error.message : '头像删除失败');
    } finally {
      deletingAvatar.value = false;
    }
  }

  async function loadSessions() {
    loadingSessions.value = true;
    try {
      sessions.value = await listSelfSessions();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '登录设备加载失败');
    } finally {
      loadingSessions.value = false;
    }
  }

  async function revokeSession(sessionId: string) {
    try {
      await revokeSelfSession(sessionId);
      message.success('该设备已退出');
      await loadSessions();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '设备退出失败');
    }
  }

  async function revokeOthers() {
    revokingOthers.value = true;
    try {
      const count = await revokeOtherSelfSessions();
      message.success(`已退出 ${count} 个其他设备`);
      await loadSessions();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '退出其他设备失败');
    } finally {
      revokingOthers.value = false;
    }
  }

  function handleTabChange(key: string | number) {
    if (key === 'sessions' && sessions.value.length === 0) loadSessions();
  }

  onMounted(async () => {
    await loadProfile();
    if (profile.value?.role === 'member') activeTab.value = 'holdings';
  });
</script>

<style scoped>
  .personal-account {
    display: grid;
    gap: 16px;
    padding: 16px;
  }

  .profile-summary,
  .account-card {
    border-radius: 14px;
    box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
  }

  .profile-summary__main {
    display: flex;
    gap: 20px;
    align-items: center;
  }

  .profile-summary__avatar,
  .avatar-editor img {
    width: 88px;
    height: 88px;
    border: 1px solid #e2e8f0;
    border-radius: 50%;
    background: #f8fafc;
    object-fit: cover;
  }

  .profile-summary__identity h2 {
    margin: 0;
    color: #0f172a;
    font-size: 24px;
  }

  .profile-summary__name-row,
  .profile-summary__details,
  .sessions-header {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .profile-summary__identity p,
  .profile-summary__details,
  .sessions-header p,
  .security-actions p,
  .avatar-editor p,
  .modal-note {
    color: #64748b;
    font-size: 13px;
  }

  .profile-summary__details {
    flex-wrap: wrap;
  }

  .profile-grid {
    display: grid;
    gap: 20px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .account-section {
    min-width: 0;
    padding: 20px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
  }

  .section-title {
    margin-bottom: 16px;
    color: #0f172a;
    font-size: 16px;
    font-weight: 700;
  }

  .readonly-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-bottom: 20px;
  }

  .readonly-grid div {
    padding: 12px;
    border-radius: 9px;
    background: #f8fafc;
  }

  .readonly-grid span,
  .readonly-grid strong {
    display: block;
  }

  .readonly-grid span {
    margin-bottom: 5px;
    color: #64748b;
    font-size: 12px;
  }

  .avatar-editor {
    display: flex;
    gap: 18px;
    align-items: center;
  }

  .avatar-editor__actions {
    display: flex;
    flex: 1;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
  }

  .avatar-editor__actions p {
    flex-basis: 100%;
    margin: 0;
  }

  .security-actions {
    display: grid;
    gap: 12px;
  }

  .security-actions > div {
    padding: 14px;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
  }

  .security-actions p {
    margin: 5px 0 10px;
  }

  .sessions-header {
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .sessions-header p {
    margin: -8px 0 0;
  }

  .session-description {
    display: grid;
    gap: 4px 14px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  @media (max-width: 900px) {
    .profile-grid {
      grid-template-columns: 1fr;
    }

    .sessions-header {
      align-items: flex-start;
      flex-direction: column;
    }
  }

  @media (max-width: 640px) {
    .profile-summary__main,
    .avatar-editor {
      align-items: flex-start;
      flex-direction: column;
    }

    .readonly-grid,
    .session-description {
      grid-template-columns: 1fr;
    }
  }
</style>
