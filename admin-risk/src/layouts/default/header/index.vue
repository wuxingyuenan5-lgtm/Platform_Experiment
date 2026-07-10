<template>
  <Layout.Header style="padding: 0 28px" :class="getHeaderClass">
    <div :class="`${prefixCls}-left`">
      <AppLogo :showTitle="true" theme="light" />
    </div>

    <div v-if="getShowTopMenu && !getIsMobile" :class="`${prefixCls}-menu`">
      <LayoutMenu
        :isHorizontal="true"
        :theme="getHeaderTheme"
        :splitType="getSplitType"
        :menuMode="getMenuMode"
      />
    </div>

    <div :class="`${prefixCls}-action justify-end`">
      <AppSearch v-if="getShowSearch" :class="`${prefixCls}-action__item `" />

      <ErrorAction v-if="getUseErrorHandle" :class="`${prefixCls}-action__item error-action`" />

      <Notify
        v-if="getShowNotice && route.path != '/notification/index'"
        :class="`${prefixCls}-action__item notify-item`"
      />

      <FullScreen v-if="getShowFullScreen" :class="`${prefixCls}-action__item fullscreen-item`" />

      <AppLocalePicker
        v-if="getShowLocalePicker"
        :reload="true"
        :showText="false"
        :class="`${prefixCls}-action__item`"
      />

      <SettingDrawer v-if="getShowSetting" :class="`${prefixCls}-action__item`" />

      <UserDropDown :theme="getHeaderTheme" :class="`${prefixCls}-action__item user-action`" />
    </div>
  </Layout.Header>
</template>
<script lang="ts" setup>
  import { Layout } from 'ant-design-vue';
  import { computed, unref } from 'vue';

  import { AppLocalePicker, AppLogo, AppSearch } from '@/components/Application';
  import { SettingButtonPositionEnum } from '@/enums/appEnum';
  import { MenuModeEnum, MenuSplitTyeEnum } from '@/enums/menuEnum';
  import { useHeaderSetting } from '@/hooks/setting/useHeaderSetting';
  import { useMenuSetting } from '@/hooks/setting/useMenuSetting';
  import { useRootSetting } from '@/hooks/setting/useRootSetting';
  import { useAppInject } from '@/hooks/web/useAppInject';
  import { useDesign } from '@/hooks/web/useDesign';
  import { useLocale } from '@/locales/useLocale';
  import { createAsyncComponent } from '@/utils/factory/createAsyncComponent';
  import { propTypes } from '@/utils/propTypes';
  import { useRoute } from 'vue-router';
  import LayoutMenu from '../menu/index.vue';
  import { ErrorAction, FullScreen, Notify } from './components';
  import UserDropDown from './components/user-dropdown/index.vue';

  const route = useRoute();
  const SettingDrawer = createAsyncComponent(() => import('@/layouts/default/setting/index.vue'), {
    loading: true,
  });
  defineOptions({ name: 'LayoutHeader' });

  const props = defineProps({
    fixed: propTypes.bool,
  });
  const { prefixCls } = useDesign('layout-header');
  const { getShowTopMenu, getSplit } = useMenuSetting();
  const { getUseErrorHandle, getShowSettingButton, getSettingButtonPosition } = useRootSetting();

  const {
    getHeaderTheme,
    getShowFullScreen,
    getShowNotice,
    getShowHeader,
    getShowSearch,
  } = useHeaderSetting();

  const { getShowLocalePicker } = useLocale();
  const { getIsMobile } = useAppInject();

  const getHeaderClass = computed(() => {
    const theme = unref(getHeaderTheme);
    return [
      prefixCls,
      {
        [`${prefixCls}--fixed`]: props.fixed,
        [`${prefixCls}--mobile`]: unref(getIsMobile),
        [`${prefixCls}--${theme}`]: theme,
      },
    ];
  });

  const getShowSetting = computed(() => {
    if (!unref(getShowSettingButton)) {
      return false;
    }
    const settingButtonPosition = unref(getSettingButtonPosition);

    if (settingButtonPosition === SettingButtonPositionEnum.AUTO) {
      return unref(getShowHeader);
    }
    return settingButtonPosition === SettingButtonPositionEnum.HEADER;
  });

  const getSplitType = computed(() => {
    return unref(getSplit) ? MenuSplitTyeEnum.TOP : MenuSplitTyeEnum.NONE;
  });

  const getMenuMode = computed(() => {
    return unref(getSplit) ? MenuModeEnum.HORIZONTAL : null;
  });
</script>
<style lang="less">
  @import url('./index.less');
</style>
