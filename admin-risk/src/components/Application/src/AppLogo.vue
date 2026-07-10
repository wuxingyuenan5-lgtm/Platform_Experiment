<template>
  <div class="anticon" :class="getAppLogoClass" @click="goHome">
    <img
      v-if="showTitle"
      class="app-logo__banner"
      src="../../../assets/svg/logo.png"
      alt="Variable Global"
    />
    <img v-else class="app-logo__icon" src="/logo.png" alt="Variable Global" />
  </div>
</template>
<script lang="ts" setup>
  import { computed, unref } from 'vue';
  import { useGo } from '@/hooks/web/usePage';
  import { useMenuSetting } from '@/hooks/setting/useMenuSetting';
  import { useDesign } from '@/hooks/web/useDesign';
  import { PageEnum } from '@/enums/pageEnum';
  import { useUserStore } from '@/store/modules/user';

  const props = defineProps({
    theme: { type: String, validator: (v: string) => ['light', 'dark'].includes(v) },
    showTitle: { type: Boolean, default: true },
    alwaysShowTitle: { type: Boolean },
  });

  const { prefixCls } = useDesign('app-logo');
  const { getCollapsedShowTitle } = useMenuSetting();
  const userStore = useUserStore();
  const go = useGo();

  const getAppLogoClass = computed(() => [
    prefixCls,
    props.theme,
    { 'collapsed-show-title': unref(getCollapsedShowTitle) },
  ]);

  function goHome() {
    go(userStore.getUserInfo.homePath || PageEnum.BASE_HOME);
  }
</script>
<style lang="less" scoped>
  @prefix-cls: ~'@{namespace}-app-logo';

  .@{prefix-cls} {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    min-height: 56px;
    transition: all 0.2s ease;

    &.collapsed-show-title {
      justify-content: center;
    }
  }

  .app-logo__banner {
    width: 234px;
    max-width: 100%;
    height: 69px;
    object-fit: contain;
    object-position: center;
  }

  .app-logo__icon {
    width: 46px;
    height: 46px;
    object-fit: contain;
  }
</style>
