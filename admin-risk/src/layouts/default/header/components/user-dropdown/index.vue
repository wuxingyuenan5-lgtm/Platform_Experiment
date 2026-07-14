<template>
  <button type="button" :class="[prefixCls, `${prefixCls}--${theme}`]" class="flex" @click="go('/risk/profile')">
    <img :class="`${prefixCls}__header`" :src="profileAvatar" />
    <span :class="`${prefixCls}__info hidden md:block`">
      <span :class="`${prefixCls}__name`" class="truncate pr-1">
        {{ profileName }}
      </span>
    </span>
  </button>
</template>

<script lang="ts" setup>
  import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
  import { useDesign } from '@/hooks/web/useDesign';
  import { propTypes } from '@/utils/propTypes';
  import { useUserStore } from '@/store/modules/user';
  import { useGo } from '@/hooks/web/usePage';

  type LocalProfile = {
    name?: string;
    avatar?: string;
    signature?: string;
  };

  defineOptions({ name: 'UserDropdown' });
  defineProps({
    theme: propTypes.oneOf(['dark', 'light']),
  });

  const PROFILE_KEY = 'vg_user_profile';
  const defaultUserLogo = '/logo.png';
  const { prefixCls } = useDesign('header-user-dropdown');
  const userStore = useUserStore();
  const go = useGo();
  const localProfile = ref<LocalProfile>(JSON.parse(window.localStorage.getItem(PROFILE_KEY) || '{}'));

  const getUserInfo = computed(() => {
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
    return { userName, avatar: avatar || defaultUserLogo };
  });

  const profileName = computed(() => localProfile.value.name || getUserInfo.value.userName);
  const profileAvatar = computed(() => localProfile.value.avatar || getUserInfo.value.avatar);

  function syncProfile() {
    localProfile.value = JSON.parse(window.localStorage.getItem(PROFILE_KEY) || '{}');
  }

  onMounted(() => {
    window.addEventListener('vg-profile-updated', syncProfile as EventListener);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('vg-profile-updated', syncProfile as EventListener);
  });
</script>

<style lang="less">
  @prefix-cls: ~'@{namespace}-header-user-dropdown';

  .@{prefix-cls} {
    align-items: center;
    height: 40px;
    padding: 0 4px 0 2px;
    overflow: hidden;
    cursor: pointer;
    border: none;
    border-radius: 999px;
    background: transparent;
    box-shadow: none;
    outline: none;

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

  }
</style>
