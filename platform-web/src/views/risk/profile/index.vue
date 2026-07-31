<template>
  <PageWrapper title="个人账号">
    <div class="risk-profile-page">
      <Row :gutter="[16, 16]" class="overview-row">
        <Col :xs="24" :xl="8">
          <Card :bordered="false" class="vg-panel hero-card">
            <div class="hero-card__main">
              <img class="hero-card__avatar" :src="profileAvatar" alt="avatar" />
              <div class="hero-card__info">
                <div class="hero-card__name-row">
                  <h2>{{ profileName }}</h2>
                  <Tag :color="roleColor">{{ roleLabel }}</Tag>
                </div>
                <p>{{ accountSignature }}</p>
                <Space wrap>
                  <Tag color="green">状态正常</Tag>
                  <Tag>本地资料已同步</Tag>
                </Space>
              </div>
            </div>
            <div class="hero-card__metrics">
              <div class="hero-metric">
                <span>登录账号</span>
                <strong>{{ loginName }}</strong>
              </div>
              <div class="hero-metric">
                <span>展示名称</span>
                <strong>{{ profileName }}</strong>
              </div>
              <div class="hero-metric">
                <span>安全方式</span>
                <strong>密码 + 谷歌验证</strong>
              </div>
            </div>
          </Card>
        </Col>

        <Col :xs="24" :xl="16">
          <Row :gutter="[16, 16]">
            <Col :xs="24" :md="12">
              <Card :bordered="false" class="vg-panel profile-card" title="账号资料">
                <div class="profile-form">
                  <div class="profile-preview">
                    <img :src="draftAvatar || profileAvatar" alt="preview" />
                    <div>
                      <div class="profile-preview__title">头像预览</div>
                      <div class="profile-preview__desc">支持输入图片地址，保存后顶部账号和侧边账号同步更新。</div>
                    </div>
                  </div>

                  <div class="field-block">
                    <label>账号名称</label>
                    <Input v-model:value="draftName" placeholder="请输入展示名称" />
                  </div>

                  <div class="field-block">
                    <label>头像地址</label>
                    <Input v-model:value="draftAvatar" placeholder="请输入头像图片 URL" />
                  </div>

                  <div class="field-block">
                    <label>个人说明</label>
                    <Input v-model:value="draftSignature" placeholder="例如：黄金跨所与资费策略观察者" />
                  </div>

                  <div class="profile-actions">
                    <Button @click="resetDraft">恢复当前资料</Button>
                    <Button type="primary" @click="saveProfile">保存资料</Button>
                  </div>
                </div>
              </Card>
            </Col>

            <Col :xs="24" :md="12">
              <Card :bordered="false" class="vg-panel security-card" title="安全与功能">
                <div class="security-grid">
                  <button type="button" class="action-tile" @click="focusProfileForm">
                    <span class="action-tile__title">账号设置</span>
                    <span class="action-tile__desc">返回左侧资料表单，修改名称、头像与说明。</span>
                  </button>
                  <button type="button" class="action-tile" @click="handleGoogleBind">
                    <span class="action-tile__title">谷歌验证</span>
                    <span class="action-tile__desc">打开谷歌验证二维码与绑定流程。</span>
                  </button>
                  <button type="button" class="action-tile" @click="handleChangePassword">
                    <span class="action-tile__title">修改密码</span>
                    <span class="action-tile__desc">进入原有密码修改流程，保持现有接口逻辑。</span>
                  </button>
                  <button type="button" class="action-tile action-tile--danger" @click="handleLogout">
                    <span class="action-tile__title">退出系统</span>
                    <span class="action-tile__desc">立即退出当前平台账号。</span>
                  </button>
                </div>

                <div class="security-status">
                  <div class="security-status__item">
                    <span>当前账号</span>
                    <strong>{{ loginName }}</strong>
                  </div>
                  <div class="security-status__item">
                    <span>角色权限</span>
                    <strong>{{ roleLabel }}</strong>
                  </div>
                  <div class="security-status__item">
                    <span>密码状态</span>
                    <strong>可修改</strong>
                  </div>
                </div>
              </Card>
            </Col>
          </Row>
        </Col>
      </Row>

      <Card :bordered="false" class="vg-panel chart-card" title="个人购买基金净值曲线">
        <AccountNetValueChart title="个人购买基金净值曲线" height="420px" />
      </Card>
    </div>

    <CodeElm :code="code" @register="registerCode" />
    <Password ref="passwordRef" />
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { Button, Card, Col, Input, Row, Space, Tag } from 'ant-design-vue';
  import { PageWrapper } from '@/components/Page';
  import { useRoleAccess } from '@/hooks/web/useRoleAccess';
  import { useMessage } from '@/hooks/web/useMessage';
  import { useModal } from '@/components/Modal';
  import { createAsyncComponent } from '@/utils/factory/createAsyncComponent';
  import { useUserStore } from '@/store/modules/user';
  import { loginQrcode } from '@/api/sys/user';
  import { Password } from '@/views/demo/system/save/components/modules';
  import AccountNetValueChart from '@/views/data/components/AccountNetValueChart.vue';

  type LocalProfile = {
    name?: string;
    avatar?: string;
    signature?: string;
  };

  const PROFILE_KEY = 'vg_user_profile';
  const defaultUserLogo = '/logo.png';
  const CodeElm = createAsyncComponent(() => import('@/layouts/default/header/components/code/index.vue'));

  const { roleLabel, roleColor } = useRoleAccess();
  const { createMessage } = useMessage();
  const userStore = useUserStore();
  const passwordRef = ref();
  const code = ref('');
  const [registerCode, { openModal: openCodeModal }] = useModal();

  const localProfile = ref<LocalProfile>(JSON.parse(window.localStorage.getItem(PROFILE_KEY) || '{}'));
  const draftName = ref('');
  const draftAvatar = ref('');
  const draftSignature = ref('');

  const userInfo = computed(() => {
    const info: any = userStore.getUserInfo || {};
    const { avatar, data } = info;
    const userName =
      data?.userInfo?.name ||
      data?.userInfo?.username ||
      data?.name ||
      data?.username ||
      info.realName ||
      info.username ||
      info.name ||
      'admin';
    return {
      userName,
      avatar: avatar || defaultUserLogo,
    };
  });

  const loginName = computed(() => userInfo.value.userName);
  const profileName = computed(() => localProfile.value.name || userInfo.value.userName);
  const profileAvatar = computed(() => localProfile.value.avatar || userInfo.value.avatar);
  const accountSignature = computed(() => localProfile.value.signature || '用于维护个人资料、安全设置与个人基金净值观察。');

  function syncDraft() {
    draftName.value = profileName.value;
    draftAvatar.value = localProfile.value.avatar || '';
    draftSignature.value = localProfile.value.signature || '';
  }

  syncDraft();

  function emitProfileUpdate() {
    window.dispatchEvent(
      new CustomEvent('vg-profile-updated', {
        detail: { ...localProfile.value },
      }),
    );
  }

  function resetDraft() {
    syncDraft();
  }

  function focusProfileForm() {
    const top = document.querySelector('.profile-card');
    top?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function saveProfile() {
    localProfile.value = {
      name: draftName.value.trim() || loginName.value,
      avatar: draftAvatar.value.trim() || '',
      signature: draftSignature.value.trim() || '',
    };
    window.localStorage.setItem(PROFILE_KEY, JSON.stringify(localProfile.value));
    emitProfileUpdate();
    createMessage.success('个人账号资料已更新');
  }

  async function handleGoogleBind() {
    const res = await loginQrcode();
    if (res.retCode === 0) {
      code.value = res.data;
      openCodeModal(true, {});
      return;
    }
    createMessage.error(res.msg || res.retMsg || '谷歌验证加载失败');
  }

  function handleChangePassword() {
    passwordRef.value.visible = true;
  }

  function handleLogout() {
    userStore.confirmLoginOut();
  }
</script>

<style scoped>
  .risk-profile-page {
    padding: 16px;
  }

  .vg-panel {
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .overview-row,
  .chart-card {
    margin-bottom: 16px;
  }

  .hero-card {
    height: 100%;
  }

  .hero-card__main {
    display: flex;
    gap: 18px;
    align-items: center;
    margin-bottom: 20px;
  }

  .hero-card__avatar {
    width: 88px;
    height: 88px;
    border-radius: 50%;
    object-fit: cover;
    border: 1px solid rgba(214, 221, 229, 0.95);
    background: #fff;
  }

  .hero-card__info {
    min-width: 0;
    flex: 1;
  }

  .hero-card__name-row {
    display: flex;
    gap: 12px;
    align-items: center;
    margin-bottom: 8px;
  }

  .hero-card__name-row h2 {
    margin: 0;
    color: #0f172a;
    font-size: 24px;
    font-weight: 700;
    line-height: 1.2;
  }

  .hero-card__info p {
    margin: 0 0 10px;
    color: #64748b;
    font-size: 13px;
    line-height: 1.7;
  }

  .hero-card__metrics {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .hero-metric {
    padding: 14px 16px;
    border: 1px solid rgba(226, 232, 240, 0.95);
    border-radius: 10px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.92));
  }

  .hero-metric span {
    display: block;
    margin-bottom: 6px;
    color: #64748b;
    font-size: 12px;
  }

  .hero-metric strong {
    color: #0f172a;
    font-size: 15px;
    font-weight: 700;
  }

  .profile-form,
  .security-card {
    height: 100%;
  }

  .profile-form {
    display: grid;
    gap: 16px;
  }

  .profile-preview {
    display: flex;
    gap: 14px;
    align-items: center;
    padding: 12px 14px;
    border: 1px solid rgba(226, 232, 240, 0.95);
    border-radius: 10px;
    background: rgba(248, 250, 252, 0.65);
  }

  .profile-preview img {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    object-fit: cover;
    border: 1px solid rgba(214, 221, 229, 0.95);
  }

  .profile-preview__title {
    margin-bottom: 4px;
    color: #0f172a;
    font-size: 14px;
    font-weight: 700;
  }

  .profile-preview__desc {
    color: #64748b;
    font-size: 12px;
    line-height: 1.6;
  }

  .field-block {
    display: grid;
    gap: 8px;
  }

  .field-block label {
    color: #334155;
    font-size: 13px;
    font-weight: 700;
  }

  .profile-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 4px;
  }

  .security-grid {
    display: grid;
    gap: 12px;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin-bottom: 16px;
  }

  .action-tile {
    display: grid;
    gap: 8px;
    min-height: 108px;
    padding: 16px;
    text-align: left;
    border: 1px solid rgba(226, 232, 240, 0.95);
    border-radius: 10px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.9));
    transition: all 0.2s ease;
    cursor: pointer;
  }

  .action-tile:hover {
    border-color: rgba(59, 130, 246, 0.3);
    box-shadow: 0 8px 18px rgba(148, 163, 184, 0.12);
    transform: translateY(-1px);
  }

  .action-tile--danger:hover {
    border-color: rgba(239, 68, 68, 0.28);
  }

  .action-tile__title {
    color: #0f172a;
    font-size: 14px;
    font-weight: 700;
  }

  .action-tile__desc {
    color: #64748b;
    font-size: 12px;
    line-height: 1.7;
  }

  .security-status {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .security-status__item {
    padding: 14px 16px;
    border-radius: 10px;
    background: rgba(248, 250, 252, 0.8);
    border: 1px solid rgba(226, 232, 240, 0.95);
  }

  .security-status__item span {
    display: block;
    margin-bottom: 6px;
    color: #64748b;
    font-size: 12px;
  }

  .security-status__item strong {
    color: #0f172a;
    font-size: 14px;
    font-weight: 700;
  }

  @media (max-width: 1024px) {
    .hero-card__metrics,
    .security-status {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    .risk-profile-page {
      padding: 12px;
    }

    .hero-card__main,
    .profile-preview {
      align-items: flex-start;
      flex-direction: column;
    }

    .security-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
