<template>
  <Dropdown placement="bottomRight">
    <span :class="[prefixCls, `${prefixCls}--${theme}`]" class="flex">
      <img :class="`${prefixCls}__header`" :src="profileAvatar" />
      <span :class="`${prefixCls}__info hidden md:block`">
        <span :class="`${prefixCls}__name`" class="truncate pr-1">
          {{ profileName }}
        </span>
      </span>
      <span :class="`${prefixCls}__caret`">⌄</span>
    </span>

    <template #overlay>
      <div class="min-w-40">
        <Menu @click="handleMenuClick">
          <MenuItem key="profile" text="账号设置" icon="mdi:account-cog-outline" />
          <MenuItem
            key="doc"
            :text="t('layout.header.dropdownItemDoc')"
            icon="ion:document-text-outline"
            v-if="getShowDoc"
          />
          <Menu.Divider v-if="getShowDoc" />
          <MenuItem
            v-if="getShowApi"
            key="api"
            :text="t('layout.header.dropdownChangeApi')"
            icon="ant-design:swap-outlined"
          />
          <MenuItem
            v-if="getUseLockPage"
            key="lock"
            :text="t('layout.header.tooltipLock')"
            icon="ion:lock-closed-outline"
          />
          <MenuItem key="code" :text="t('layout.header.code')" icon="icon-park-outline:pay-code-two" />
          <MenuItem
            key="changePwd"
            :text="t('layout.header.changePwd')"
            icon="icon-park-outline:personal-privacy"
          />
          <MenuItem
            key="logout"
            :text="t('layout.header.dropdownItemLoginOut')"
            icon="ant-design:poweroff-outlined"
          />
        </Menu>
      </div>
    </template>
  </Dropdown>

  <LockAction @register="register" />
  <ChangeApi @register="registerApi" />
  <CodeElm :code="code" @register="registerCode" />
  <Password ref="passwordRef" />

  <Modal
    v-model:open="profileVisible"
    title="账号设置"
    :footer="null"
    width="520px"
    destroy-on-close
  >
    <div class="profile-settings">
      <div class="profile-settings__avatar">
        <img :src="draftAvatar || profileAvatar" alt="avatar" />
        <Input v-model:value="draftAvatar" placeholder="输入头像地址，留空则保留当前头像" />
      </div>

      <div class="profile-settings__field">
        <span>账号名称</span>
        <Input v-model:value="draftName" placeholder="请输入展示名称" />
      </div>

      <div class="profile-settings__field">
        <span>新密码</span>
        <Input.Password v-model:value="draftPassword" placeholder="输入后仅本地保存展示" />
      </div>

      <div class="profile-settings__actions">
        <Button @click="profileVisible = false">取消</Button>
        <Button type="primary" @click="saveProfile">保存</Button>
      </div>
    </div>
  </Modal>
</template>

<script lang="ts" setup>
  import { Button, Dropdown, Input, Menu, Modal } from 'ant-design-vue';
  import type { MenuInfo } from 'ant-design-vue/lib/menu/src/interface';
  import { computed, ref } from 'vue';
  import { DOC_URL } from '@/settings/siteSetting';
  import { useUserStore } from '@/store/modules/user';
  import { useHeaderSetting } from '@/hooks/setting/useHeaderSetting';
  import { useI18n } from '@/hooks/web/useI18n';
  import { useDesign } from '@/hooks/web/useDesign';
  import { useModal } from '@/components/Modal';
  import { propTypes } from '@/utils/propTypes';
  import { openWindow } from '@/utils';
  import { createAsyncComponent } from '@/utils/factory/createAsyncComponent';
  import { loginQrcode } from '@/api/sys/user';
  import { useMessage } from '@/hooks/web/useMessage';
  import { Password } from '@/views/demo/system/save/components/modules';

  type MenuEvent = 'profile' | 'logout' | 'doc' | 'lock' | 'api' | 'code' | 'changePwd';

  const MenuItem = createAsyncComponent(() => import('./DropMenuItem.vue'));
  const LockAction = createAsyncComponent(() => import('../lock/LockModal.vue'));
  const ChangeApi = createAsyncComponent(() => import('../ChangeApi/index.vue'));
  const CodeElm = createAsyncComponent(() => import('../code/index.vue'));
  const passwordRef = ref();

  defineOptions({ name: 'UserDropdown' });
  defineProps({
    theme: propTypes.oneOf(['dark', 'light']),
  });

  const PROFILE_KEY = 'vg_user_profile';
  const { createMessage } = useMessage();
  const { prefixCls } = useDesign('header-user-dropdown');
  const { t } = useI18n();
  const { getShowDoc, getUseLockPage, getShowApi } = useHeaderSetting();
  const userStore = useUserStore();
  const code = ref('');
  const defaultUserLogo = '/logo.png';
  const profileVisible = ref(false);
  const localProfile = ref<{ name?: string; avatar?: string; password?: string }>(
    JSON.parse(window.localStorage.getItem(PROFILE_KEY) || '{}'),
  );
  const draftName = ref('');
  const draftAvatar = ref('');
  const draftPassword = ref('');

  const getUserInfo = computed(() => {
    const info: any = userStore.getUserInfo || {};
    const { avatar, desc, data } = info;
    const userName =
      data?.userInfo?.name ||
      data?.userInfo?.username ||
      data?.name ||
      data?.username ||
      info.realName ||
      info.username ||
      info.name ||
      'admin';
    return { userName, avatar: avatar || defaultUserLogo, desc };
  });

  const profileName = computed(() => localProfile.value.name || getUserInfo.value.userName);
  const profileAvatar = computed(() => localProfile.value.avatar || getUserInfo.value.avatar);

  const [register, { openModal }] = useModal();
  const [registerApi, { openModal: openApiModal }] = useModal();
  const [registerCode, { openModal: openCodeModal }] = useModal();

  function handleLock() {
    openModal(true);
  }

  function handleApi() {
    openApiModal(true, {});
  }

  function handleLoginOut() {
    userStore.confirmLoginOut();
  }

  function openDoc() {
    openWindow(DOC_URL);
  }

  async function handleCode() {
    const res = await loginQrcode();
    if (res.retCode == 0) {
      code.value = res.data;
      openCodeModal(true, {});
    } else {
      createMessage.error(res.msg || res.retMsg);
    }
  }

  function handleChangePwd() {
    passwordRef.value.visible = true;
  }

  function openProfile() {
    draftName.value = profileName.value;
    draftAvatar.value = localProfile.value.avatar || '';
    draftPassword.value = localProfile.value.password || '';
    profileVisible.value = true;
  }

  function saveProfile() {
    localProfile.value = {
      name: draftName.value?.trim() || profileName.value,
      avatar: draftAvatar.value?.trim() || '',
      password: draftPassword.value?.trim() || '',
    };
    window.localStorage.setItem(PROFILE_KEY, JSON.stringify(localProfile.value));
    profileVisible.value = false;
    createMessage.success('账号资料已更新');
  }

  function handleMenuClick(e: MenuInfo) {
    switch (e.key as MenuEvent) {
      case 'profile':
        openProfile();
        break;
      case 'logout':
        handleLoginOut();
        break;
      case 'doc':
        openDoc();
        break;
      case 'lock':
        handleLock();
        break;
      case 'api':
        handleApi();
        break;
      case 'code':
        handleCode();
        break;
      case 'changePwd':
        handleChangePwd();
        break;
    }
  }
</script>

<style lang="less">
  @prefix-cls: ~'@{namespace}-header-user-dropdown';

  .@{prefix-cls} {
    align-items: center;
    height: 40px;
    padding: 0 12px 0 8px;
    overflow: hidden;
    font-size: 12px;
    cursor: pointer;
    border: 1px solid rgba(214, 221, 229, 0.95);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 8px 20px rgba(135, 155, 182, 0.1);

    img {
      width: 28px;
      height: 28px;
      margin-right: 8px;
      object-fit: cover;
    }

    &__header {
      border-radius: 50%;
    }

    &__name {
      display: inline-block;
      max-width: 120px;
      color: #0f172a;
      font-size: 14px;
      font-weight: 700;
      line-height: 1;
    }

    &__caret {
      margin-left: 4px;
      color: #64748b;
      font-size: 14px;
    }
  }

  .profile-settings {
    display: grid;
    gap: 18px;

    &__avatar {
      display: grid;
      gap: 10px;

      img {
        width: 68px;
        height: 68px;
        border-radius: 50%;
        object-fit: cover;
        border: 1px solid rgba(214, 221, 229, 0.96);
      }
    }

    &__field {
      display: grid;
      gap: 8px;

      span {
        color: #475569;
        font-size: 13px;
        font-weight: 600;
      }
    }

    &__actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-top: 8px;
    }
  }
</style>
