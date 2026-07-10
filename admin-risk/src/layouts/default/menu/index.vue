<script lang="tsx">
  import type { CSSProperties, PropType } from 'vue';

  import { computed, defineComponent, toRef, unref } from 'vue';
  import { BasicMenu } from '@/components/Menu';
  import { SimpleMenu } from '@/components/SimpleMenu';
  import { AppLogo } from '@/components/Application';

  import { MenuModeEnum, MenuSplitTyeEnum } from '@/enums/menuEnum';
  import { useMenuSetting } from '@/hooks/setting/useMenuSetting';
  import { ScrollContainer } from '@/components/Container';
  import { useGo } from '@/hooks/web/usePage';
  import { useSplitMenu } from './useLayoutMenu';
  import { openWindow } from '@/utils';
  import { propTypes } from '@/utils/propTypes';
  import { isHttpUrl } from '@/utils/is';
  import { useRootSetting } from '@/hooks/setting/useRootSetting';
  import { useAppInject } from '@/hooks/web/useAppInject';
  import { useDesign } from '@/hooks/web/useDesign';
  import UserDropDown from '../header/components/user-dropdown/index.vue';

  export default defineComponent({
    name: 'LayoutMenu',
    props: {
      theme: propTypes.oneOf(['light', 'dark']),
      splitType: {
        type: Number as PropType<MenuSplitTyeEnum>,
        default: MenuSplitTyeEnum.NONE,
      },
      isHorizontal: propTypes.bool,
      menuMode: {
        type: [String] as PropType<MenuModeEnum | null>,
        default: '',
      },
    },
    setup(props) {
      const go = useGo();
      const {
        getMenuMode,
        getMenuType,
        getMenuTheme,
        getCollapsed,
        getCollapsedShowTitle,
        getAccordion,
        getIsHorizontal,
        getIsSidebarType,
        getSplit,
      } = useMenuSetting();
      const { getShowLogo } = useRootSetting();
      const { prefixCls } = useDesign('layout-menu');
      const { menusRef } = useSplitMenu(toRef(props, 'splitType'));
      const { getIsMobile } = useAppInject();

      const getComputedMenuMode = computed(() =>
        unref(getIsMobile) ? MenuModeEnum.INLINE : props.menuMode || unref(getMenuMode),
      );

      const getComputedMenuTheme = computed(() => props.theme || unref(getMenuTheme));
      const getIsShowLogo = computed(() => unref(getShowLogo) && unref(getIsSidebarType));

      const getUseScroll = computed(() => {
        return (
          !unref(getIsHorizontal) &&
          (unref(getIsSidebarType) ||
            props.splitType === MenuSplitTyeEnum.LEFT ||
            props.splitType === MenuSplitTyeEnum.NONE)
        );
      });

      const getWrapperStyle = computed((): CSSProperties => {
        return {
          flex: '1 1 auto',
          minHeight: 0,
        };
      });

      const getLogoClass = computed(() => {
        return [
          `${prefixCls}-logo`,
          unref(getComputedMenuTheme),
          {
            [`${prefixCls}--mobile`]: unref(getIsMobile),
          },
        ];
      });

      const getCommonProps = computed(() => {
        const menus = unref(menusRef);
        return {
          menus,
          beforeClickFn: beforeMenuClickFn,
          items: menus,
          theme: unref(getComputedMenuTheme),
          accordion: unref(getAccordion),
          collapse: unref(getCollapsed),
          collapsedShowTitle: unref(getCollapsedShowTitle),
          onMenuClick: handleMenuClick,
        };
      });

      function handleMenuClick(path: string) {
        go(path);
      }

      async function beforeMenuClickFn(path: string) {
        if (!isHttpUrl(path)) {
          return true;
        }
        openWindow(path);
        return false;
      }

      function renderHeader() {
        if (!unref(getIsShowLogo) && !unref(getIsMobile)) return null;

        return (
          <AppLogo
            showTitle={!unref(getCollapsed)}
            class={unref(getLogoClass)}
            theme={unref(getComputedMenuTheme)}
          />
        );
      }

      function renderMenu() {
        const { menus, ...menuProps } = unref(getCommonProps);
        if (!menus || !menus.length) return null;
        return !props.isHorizontal ? (
          <SimpleMenu {...menuProps} isSplitMenu={unref(getSplit)} items={menus} />
        ) : (
          <BasicMenu
            {...(menuProps as any)}
            isHorizontal={props.isHorizontal}
            type={unref(getMenuType)}
            showLogo={unref(getIsShowLogo)}
            mode={unref(getComputedMenuMode as any)}
            items={menus}
          />
        );
      }

      function renderAccount() {
        if (props.isHorizontal) return null;
        return (
          <div class="layout-account">
            <UserDropDown theme={unref(getComputedMenuTheme)} />
          </div>
        );
      }

      return () => (
        <div class={prefixCls}>
          {renderHeader()}
          {unref(getUseScroll) ? (
            <>
              <ScrollContainer style={unref(getWrapperStyle)}>{() => renderMenu()}</ScrollContainer>
              {renderAccount()}
            </>
          ) : (
            renderMenu()
          )}
        </div>
      );
    },
  });
</script>

<style lang="less">
  @prefix-cls: ~'@{namespace}-layout-menu';
  @logo-prefix-cls: ~'@{namespace}-app-logo';

  .@{prefix-cls} {
    display: flex;
    flex-direction: column;
    height: 100%;

    &-logo {
      display: flex;
      align-items: center;
      justify-content: center;
      flex: 0 0 auto;
      min-height: 82px;
      padding: 4px 12px 2px;
      margin: 2px 8px 0;

      img {
        width: 100%;
        max-width: 234px;
        height: 69px;
        object-fit: contain;
        object-position: center;
      }
    }

    &--mobile {
      .@{logo-prefix-cls} {
        &__title {
          opacity: 1;
        }
      }
    }
  }

  .layout-account {
    flex: 0 0 auto;
    padding: 8px 12px 14px;

    .vg-header-user-dropdown {
      display: flex;
      align-items: center;
      width: 100%;
      height: 54px;
      padding: 0 14px;
      border: 1px solid rgba(201, 164, 95, 0.14);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.82);
      overflow: hidden;

      img {
        width: 28px;
        height: 28px;
      }

      .vg-header-user-dropdown__info {
        display: block !important;
      }
    }
  }
</style>
