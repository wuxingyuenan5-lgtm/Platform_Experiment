<template>
  <div
    v-if="getMenuFixed && !getIsMobile"
    v-show="showClassSideBarRef"
    :style="getHiddenDomStyle"
  ></div>
  <Layout.Sider
    v-show="showClassSideBarRef"
    ref="sideRef"
    breakpoint="lg"
    collapsible
    :class="getSiderClass"
    :width="getMenuWidth"
    :collapsed="getCollapsed"
    :collapsedWidth="getCollapsedWidth"
    :theme="getMenuTheme"
    :trigger="null"
    @breakpoint="onBreakpointChange"
  >
    <button v-if="!getIsMobile" type="button" class="sidebar-toggle" @click="toggleCollapsed">
      <span class="sidebar-toggle__glyph">
        <Icon icon="ion:reorder-three-outline" :size="18" />
      </span>
    </button>

    <LayoutMenu :theme="getMenuTheme" :menuMode="getMode" :splitType="getSplitType" />
    <DragBar ref="dragBarRef" />
  </Layout.Sider>
</template>

<script lang="ts" setup>
  import { Layout } from 'ant-design-vue';
  import { computed, CSSProperties, ref, unref } from 'vue';

  import { MenuModeEnum, MenuSplitTyeEnum } from '@/enums/menuEnum';
  import { useMenuSetting } from '@/hooks/setting/useMenuSetting';
  import { useAppInject } from '@/hooks/web/useAppInject';
  import { useDesign } from '@/hooks/web/useDesign';
  import Icon from '@/components/Icon/Icon.vue';

  import LayoutMenu from '../menu/index.vue';
  import DragBar from './DragBar.vue';
  import { useDragLine, useSiderEvent } from './useLayoutSider';

  defineOptions({ name: 'LayoutSideBar' });

  const dragBarRef = ref(null);
  const sideRef = ref(null);

  const {
    getCollapsed,
    getMenuWidth,
    getSplit,
    getMenuTheme,
    getRealWidth,
    getMenuHidden,
    getMenuFixed,
    getIsMixMode,
    toggleCollapsed,
  } = useMenuSetting();

  const { prefixCls } = useDesign('layout-sideBar');
  const { getIsMobile } = useAppInject();

  useDragLine(sideRef, dragBarRef);

  const { getCollapsedWidth, onBreakpointChange } = useSiderEvent();

  const getMode = computed(() => {
    return unref(getSplit) ? MenuModeEnum.INLINE : null;
  });

  const getSplitType = computed(() => {
    return unref(getSplit) ? MenuSplitTyeEnum.LEFT : MenuSplitTyeEnum.NONE;
  });

  const showClassSideBarRef = computed(() => {
    return unref(getSplit) ? !unref(getMenuHidden) : true;
  });

  const getSiderClass = computed(() => {
    return [
      prefixCls,
      {
        [`${prefixCls}--fixed`]: unref(getMenuFixed) && !unref(getIsMobile),
        [`${prefixCls}--mix`]: unref(getIsMixMode) && !unref(getIsMobile),
      },
    ];
  });

  const getHiddenDomStyle = computed((): CSSProperties => {
    const width = `${unref(getRealWidth)}px`;
    return {
      width,
      overflow: 'hidden',
      flex: `0 0 ${width}`,
      maxWidth: width,
      minWidth: width,
      transition: 'all 0.2s',
    };
  });
</script>

<style lang="less">
  @prefix-cls: ~'@{namespace}-layout-sideBar';

  .@{prefix-cls} {
    z-index: @layout-sider-fixed-z-index;

    &--fixed {
      position: fixed !important;
      top: 0;
      left: 0;
      height: 100%;
    }

    &--mix {
      top: @header-height;
      height: calc(100% - @header-height);
    }

    &.ant-layout-sider-dark {
      background-color: @sider-dark-bg-color;
    }

    .ant-layout-sider-trigger {
      display: none !important;
    }

    .ant-layout-sider-children {
      display: flex;
      position: relative;
      flex-direction: column;
      height: 100%;
    }

    .sidebar-toggle {
      display: grid;
      position: absolute;
      z-index: 12;
      top: 8px;
      right: 8px;
      width: 38px;
      height: 38px;
      padding: 0;
      transition: 0.2s ease;
      border: 0;
      border-radius: 12px;
      background: transparent;
      box-shadow: none;
      color: #4b5563;
      place-items: center;

      &:hover {
        transform: translateY(-1px);
        background: rgb(255 255 255 / 55%);
        color: #111827;
      }
    }

    .sidebar-toggle__glyph {
      display: grid;
      place-items: center;
      width: 100%;
      height: 100%;
      border-radius: 12px;
      background: transparent;
    }
  }
</style>
