<script lang="tsx">
  import type { PropType, CSSProperties } from 'vue';

  import { computed, defineComponent, unref, toRef, ref } from 'vue';

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
  // import { useDesign } from '@/hooks/web/useDesign';
  import logoSvg from '@/assets/svg/logo.png';
  import { useI18n } from '@/hooks/web/useI18n';
  import Icon from '@/components/Icon/Icon.vue';
  import { listenerRouteChange } from '@/logics/mitt/routeChange';
  import { REDIRECT_NAME } from '@/router/constant';
  import { getCurrentParentPath } from '@/router/menus';
  import { Popover } from 'ant-design-vue';

  export default defineComponent({
    name: 'LayoutMenu',
    props: {
      theme: propTypes.oneOf(['light', 'dark']),

      splitType: {
        type: Number as PropType<MenuSplitTyeEnum>,
        default: MenuSplitTyeEnum.NONE,
      },

      isHorizontal: propTypes.bool,
      // menu Mode
      menuMode: {
        type: [String] as PropType<MenuModeEnum | null>,
        default: '',
      },
    },
    setup(props) {
      const go = useGo();
      const { t } = useI18n();
      const currentActivePath = ref('');

      const {
        // getMenuMode,
        // getMenuType,
        getMenuTheme,
        getCollapsed,
        getCollapsedShowTitle,
        getAccordion,
        getIsHorizontal,
        getIsSidebarType,
        // getSplit,
      } = useMenuSetting();
      const { getShowLogo } = useRootSetting();

      const { menusRef } = useSplitMenu(toRef(props, 'splitType'));

      const { getIsMobile } = useAppInject();

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
          height: `calc(100% - ${unref(getIsShowLogo) ? '120px' : '0px'})`,
        };
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
      listenerRouteChange((route) => {
        if (route.name === REDIRECT_NAME) return;
        getCurrentParentPath(route.path, true).then((res) => (currentActivePath.value = res));
      });
      /**
       * click menu
       * @param menu
       */

      function handleMenuClick(path: string) {
        go(path);
      }

      /**
       * before click menu
       * @param menu
       */
      async function beforeMenuClickFn(path: string) {
        if (!isHttpUrl(path)) {
          return true;
        }
        openWindow(path);
        return false;
      }

      function renderHeader() {
        if (!unref(getIsShowLogo) && !unref(getIsMobile)) return null;
        const { menus, ...menuProps } = unref(getCommonProps);
        const { collapse } = menuProps;
        let _style = {};
        if (collapse) {
          _style = {
            display: 'inline-block',
            width: '25px',
            height: '25px',
          };
        }
        return !collapse ? (
          <img class="pb-10 pt-9 ml-[25px]" src={logoSvg} />
        ) : (
          <img style={_style} class="mb-10 mt-9  ml-[8px]" src={'/logo.png'} />
        );
      }

      function renderMenu() {
        const { menus, ...menuProps } = unref(getCommonProps);
        // console.log('menus', menus);
        // console.log('currentActivePath.value==',currentActivePath.value);

        if (!menus || !menus.length) return null;
        const { collapse } = menuProps;
        return (
          <div class={['layout-menu', collapse && 'is-collapse']}>
            {menus.map((item: any) => (
              <div
                key={item.path}
                onClick={() => handleMenuClick(item.path)}
                class={[
                  (item.path == currentActivePath.value ||
                    item.redirect == currentActivePath.value) &&
                    'is-active',
                  ' layout-menu-item leading-12 pl-10',
                ]}
              >
                {!collapse ? (
                  <div class="truncate">
                    {t(item.name)}
                  </div>
                ) : (
                  <Popover placement="right">
                    {{
                      default: () => (
                        <span class="inline-flex h-[20px] w-[20px] items-center justify-center text-[12px] font-700">
                          {String(t(item.name)).slice(0, 1)}
                        </span>
                      ),
                      content: () => t(item.name),
                    }}
                  </Popover>
                )}
              </div>
            ))}
          </div>
        );
      }

      return () => {
        return (
          <>
            {renderHeader()}
            {unref(getUseScroll) ? (
              <ScrollContainer style={unref(getWrapperStyle)}>{() => renderMenu()}</ScrollContainer>
            ) : (
              renderMenu()
            )}
          </>
        );
      };
    },
  });
</script>
<style lang="less">
  .layout-menu {
    &-item {
      // color: #d1d4dc;
      cursor: pointer;

      &.is-active,
      &:hover {
        background: @sider-item-bg-color-hover;
        color: @primary-color;
      }
    }

    &.is-collapse {
      .layout-menu-item {
        padding-left: 12px;
      }
    }
  }
  @prefix-cls: ~'@{namespace}-layout-menu';
  @logo-prefix-cls: ~'@{namespace}-app-logo';

  .@{prefix-cls} {
    &-logo {
      height: @header-height;
      padding: 10px 4px 10px 10px;

      img {
        width: @logo-width;
        height: @logo-width;
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
</style>
