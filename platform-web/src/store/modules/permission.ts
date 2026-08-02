// @ts-nocheck
import type { AppRouteRecordRaw, Menu } from '@/router/types';

import { defineStore } from 'pinia';
import { store } from '@/store';
import { useI18n } from '@/hooks/web/useI18n';
import { useUserStore } from './user';
import { useAppStoreWithOut } from './app';
import { toRaw } from 'vue';
import { transformObjToRoute, flatMultiLevelRoutes } from '@/router/helper/routeHelper';
import { transformRouteToMenu } from '@/router/helper/menuHelper';
import { maskCompanyDisplay } from '@/utils/maskCompany';

import projectSetting from '@/settings/projectSetting';

import { PermissionModeEnum } from '@/enums/appEnum';

import { asyncRoutes } from '@/router/routes';
import { ERROR_LOG_ROUTE, PAGE_NOT_FOUND_ROUTE } from '@/router/routes/basic';

import { filter } from '@/utils/helper/treeHelper';

import { getPermCode, getUserInfo } from '@/api/sys/user';

import { useMessage } from '@/hooks/web/useMessage';
import { PageEnum } from '@/enums/pageEnum';

interface PermissionState {
  // Permission code list
  // 权限代码列表
  permCodeList: string[] | number[];
  // Whether the route has been dynamically added
  // 路由是否动态添加
  isDynamicAddedRoute: boolean;
  // To trigger a menu update
  // 触发菜单更新
  lastBuildMenuTime: number;
  // Backstage menu list
  // 后台菜单列表
  backMenuList: Menu[];
  // 菜单列表
  frontMenuList: Menu[];
}

export const usePermissionStore = defineStore({
  id: 'app-permission',
  state: (): PermissionState => ({
    // 权限代码列表
    permCodeList: [],
    // Whether the route has been dynamically added
    // 路由是否动态添加
    isDynamicAddedRoute: false,
    // To trigger a menu update
    // 触发菜单更新
    lastBuildMenuTime: 0,
    // Backstage menu list
    // 后台菜单列表
    backMenuList: [],
    // menu List
    // 菜单列表
    frontMenuList: [],
  }),
  getters: {
    getPermCodeList(state): string[] | number[] {
      return state.permCodeList;
    },
    getBackMenuList(state): Menu[] {
      return state.backMenuList;
    },
    getFrontMenuList(state): Menu[] {
      return state.frontMenuList;
    },
    getLastBuildMenuTime(state): number {
      return state.lastBuildMenuTime;
    },
    getIsDynamicAddedRoute(state): boolean {
      return state.isDynamicAddedRoute;
    },
  },
  actions: {
    setPermCodeList(codeList: string[]) {
      this.permCodeList = codeList;
    },

    setBackMenuList(list: Menu[]) {
      this.backMenuList = list;
      list?.length > 0 && this.setLastBuildMenuTime();
    },

    setFrontMenuList(list: Menu[]) {
      this.frontMenuList = list;
    },

    setLastBuildMenuTime() {
      this.lastBuildMenuTime = new Date().getTime();
    },

    setDynamicAddedRoute(added: boolean) {
      this.isDynamicAddedRoute = added;
    },
    resetState(): void {
      this.isDynamicAddedRoute = false;
      this.permCodeList = [];
      this.backMenuList = [];
      this.lastBuildMenuTime = 0;
    },
    async changePermissionCode() {
      const codeList = await getPermCode();
      this.setPermCodeList(codeList);
    },

    // 构建路由
    async buildRoutesAction(): Promise<AppRouteRecordRaw[]> {
      const { t } = useI18n();
      const userStore = useUserStore();
      const appStore = useAppStoreWithOut();

      let routes: AppRouteRecordRaw[] = [];
      const roleList = toRaw(userStore.getRoleList) || [];
      const { permissionMode = projectSetting.permissionMode } = appStore.getProjectConfig;

      // 路由过滤器 在 函数filter 作为回调传入遍历使用
      const routeFilter = (route: AppRouteRecordRaw) => {
        const { meta } = route;
        // 抽出角色
        const { roles } = meta || {};
        if (!roles) return true;
        // 进行角色权限判断
        return roleList.some((role) => roles.includes(role));
      };

      const routeRemoveIgnoreFilter = (route: AppRouteRecordRaw) => {
        const { meta } = route;
        // ignoreRoute 为true 则路由仅用于菜单生成，不会在实际的路由表中出现
        const { ignoreRoute } = meta || {};
        // arr.filter 返回 true 表示该元素通过测试
        return !ignoreRoute;
      };

      /**
       * @description 根据设置的首页path，修正routes中的affix标记（固定首页）
       * */
      const patchHomeAffix = (routes: AppRouteRecordRaw[]) => {
        if (!routes || routes.length === 0) return;
        let homePath: string = userStore.getUserInfo.homePath || PageEnum.BASE_HOME;

        function patcher(routes: AppRouteRecordRaw[], parentPath = '') {
          if (parentPath) parentPath = parentPath + '/';
          routes.forEach((route: AppRouteRecordRaw) => {
            const { path, children, redirect } = route;
            const currentPath = path.startsWith('/') ? path : parentPath + path;
            if (currentPath === homePath) {
              if (redirect) {
                homePath = route.redirect! as string;
              } else {
                route.meta = Object.assign({}, route.meta, { affix: true });
                throw new Error('end');
              }
            }
            children && children.length > 0 && patcher(children, currentPath);
          });
        }

        try {
          patcher(routes);
        } catch (e) {
          // 已处理完毕跳出循环
        }
        return;
      };
      // console.log('permissionMode=====', permissionMode);

      switch (permissionMode) {
        // 角色权限
        case PermissionModeEnum.ROLE:
          // 对非一级路由进行过滤
          routes = filter(asyncRoutes, routeFilter);
          // 对一级路由根据角色权限过滤
          routes = routes.filter(routeFilter);
          // Convert multi-level routing to level 2 routing
          // 将多级路由转换为 2 级路由
          routes = flatMultiLevelRoutes(routes);
          break;

        // 路由映射， 默认进入该case
        case PermissionModeEnum.ROUTE_MAPPING:
          // 对非一级路由进行过滤
          routes = filter(asyncRoutes, routeFilter);
          // 对一级路由再次根据角色权限过滤
          routes = routes.filter(routeFilter);

          // 将路由转换成菜单
          const menuList = transformRouteToMenu(routes, true);
          console.log('menuList=====', menuList);

          // 移除掉 ignoreRoute: true 的路由 非一级路由
          routes = filter(routes, routeRemoveIgnoreFilter);
          // 移除掉 ignoreRoute: true 的路由 一级路由；
          routes = routes.filter(routeRemoveIgnoreFilter);
          // 对菜单进行排序
          menuList.sort((a, b) => {
            return (a.meta?.orderNo || 0) - (b.meta?.orderNo || 0);
          });

          // 设置菜单列表
          this.setFrontMenuList(menuList);

          // Convert multi-level routing to level 2 routing
          // 将多级路由转换为 2 级路由
          routes = flatMultiLevelRoutes(routes);
          break;

        //  If you are sure that you do not need to do background dynamic permissions, please comment the entire judgment below
        //  如果确定不需要做后台动态权限，请在下方注释整个判断
        case PermissionModeEnum.BACK:
          const { createMessage } = useMessage();
          createMessage.loading({
            content: t('sys.app.menuLoading'),
            duration: 1,
          });

          // !Simulate to obtain permission codes from the background,
          // 模拟从后台获取权限码，
          // this function may only need to be executed once, and the actual project can be put at the right time by itself
          // 这个功能可能只需要执行一次，实际项目可以自己放在合适的时间
          let routeList: AppRouteRecordRaw[] = [];
          try {
            // await this.changePermissionCode();
            const _userInfo: any = toRaw(userStore.getUserInfo);
            const routeData = _userInfo?.data?.path;

            const _productRoute = dealProductRoute(_userInfo?.data?.product, routeData);
            // console.log('_productRoute------', _productRoute);
            routeList = transformRoute(_productRoute);
          } catch (error) {
            console.error(error);
          }
          // console.log('routeList=====', routeList);

          // Dynamically introduce components
          // 动态引入组件
          routeList = transformObjToRoute(routeList);

          //  Background routing to menu structure
          //  后台路由到菜单结构
          const backMenuList = transformRouteToMenu(routeList);
          // console.log('backMenuList=====', backMenuList);

          this.setBackMenuList(backMenuList);

          // remove meta.ignoreRoute item
          // 删除 meta.ignoreRoute 项
          routeList = filter(routeList, routeRemoveIgnoreFilter);
          routeList = routeList.filter(routeRemoveIgnoreFilter);

          routeList = flatMultiLevelRoutes(routeList);
          console.log('routeList=====', routeList);

          routes = [PAGE_NOT_FOUND_ROUTE, ...routeList];
          break;
      }

      routes.push(ERROR_LOG_ROUTE);
      patchHomeAffix(routes);
      return routes;
    },
  },
});

// Need to be used outside the setup
// 需要在设置之外使用
export function usePermissionStoreWithOut() {
  return usePermissionStore(store);
}

// 后端接口数据处理成前端路由数据
export function transformRoute(routeModule: any[]) {
  if (!routeModule || routeModule.length == 0) return [] as any;
  return routeModule
    ?.map((item) => {
      return dealRoute(item);
    })
    .sort((a, b) => (a.meta?.orderNo || 0) - (b.meta?.orderNo || 0));
}
function dealRoute(routeModule: any) {
  const _name = routeModule?.route
    ?.split('/')
    ?.map((item) => item?.charAt(0).toUpperCase() + item?.slice(1))
    .join('');
  // console.log("_name===",_name,routeModule?.route);

  const _itemRoute = {
    path: routeModule?.route,
    component: routeModule?.component,
    name: _name,
    meta: {
      title: maskCompanyDisplay(routeModule?.menuName),
      icon: routeModule?.icon,
      orderNo: routeModule?.sortOrder,
      hideMenu: !routeModule.isVisible,
      hideChildrenInMenu: true,
      curParams: routeModule?.curParams,
    },
    children: [],
  };

  if (routeModule?.children?.length > 0) {
    _itemRoute.children = routeModule?.children
      .map((item: any) => {
        return dealRoute(item);
      })
      .sort((a, b) => (a.meta?.orderNo || 0) - (b.meta?.orderNo || 0));

    _itemRoute.redirect = routeModule?.children?.[0]?.route;
    // console.log(
    //   'routeModule?.children----',
    //   routeModule?.route,
    //   !(routeModule?.children?.length > 1),
    // );

    // 只有一个菜单时，隐藏子菜单，
    if (!(routeModule?.children?.length > 1)) {
      // console.log(2, routeModule?.route);

      // 页面刷新时，默认选中父级菜单
      _itemRoute.meta.currentActiveMenu = routeModule?.route;
      let _hideChildrenInMenu = true;

      // 子菜单只有一个，并且component == 'LAYOUT'时，那就不隐藏子菜单
      if (routeModule?.children?.[0]?.component == 'LAYOUT') {
        _hideChildrenInMenu = false;
        // console.log('566=======', routeModule, _itemRoute);
      }
      _itemRoute.meta.hideChildrenInMenu = _hideChildrenInMenu;
    } else {
      _itemRoute.meta.hideChildrenInMenu = false;
    }
    // console.log('routeModule-----', routeModule, _itemRoute);
  }

  return _itemRoute;
}

// 根据用户拥有的产品权限，将对应产品信息加入路由信息
function dealProductRoute(products: any[], routeModule: any[]) {
  // console.log('products------', products, routeModule);
  if (!routeModule || routeModule.length == 0) return [] as any;
  if (!products || products.length == 0) return routeModule as any;

  return routeModule?.map((item) => {
    if (item?.route == '/product') {
      return dealRouteByProducts(products, item);
    } else {
      return item;
    }
  });
}

// 路由数据根据产品权限进行处理
function dealRouteByProducts(products: any[], route: any) {
  // 目录节点（LAYOUT）
  if (route.component === 'LAYOUT') {
    const { children } = route;
    // 若无子节点，直接返回原路由
    if (!children || children.length === 0) {
      return route;
    }

    // 递归处理子节点，并过滤掉 null 结果
    const processedChildren = children
      .map((child) => dealRouteByProducts(products, child))
      .filter(Boolean);

    // 如果所有子节点都被过滤掉了，也可选择不返回该目录（按需调整）
    // 此处保留目录即使无子节点（与原逻辑一致）
    return {
      ...route,
      children: processedChildren,
    };
  }

  // 叶子节点：匹配产品权限
  let _route, _matchedProduct, _isProduct;
  products.forEach((p) => {
    // console.log('menuIds----', route.id, route);
    if (p.menuIds?.includes(route.id)) {
      _route = route;
      _matchedProduct = p.children.find((item: any) => item.accountName == _route.name);
      _isProduct = false;
      // 没有找到说明该路由信息是混合菜单
      if (!_matchedProduct) {
        _matchedProduct = p;
        _isProduct = true;
      }
    }
  });
  // console.log('matchedProduct===', _matchedProduct);

  if (!_matchedProduct) {
    return null; // 无权限，过滤掉
  }
  // 有权限，拼接 route 路径
  return {
    ...route,
    route: `${route.route ?? ''}/${_isProduct ? _matchedProduct.id : _matchedProduct.checkCode}`,
    curParams: !_isProduct
      ? {
        checkCode: _matchedProduct.checkCode,
        platform: _matchedProduct.platform,
      }
      : null,
  };
}
// function dealRouteByProducts(products: any[], route: any) {
//   // 目录节点（LAYOUT）
//   if (route.component === 'LAYOUT') {
//     const { children } = route;

//     // 若无子节点，直接返回原路由
//     if (!children || children.length === 0) {
//       return route;
//     }

//     // 递归处理子节点，并过滤掉 null 结果
//     const processedChildren = children
//       .map((child) => dealRouteByProducts(products, child))
//       .filter(Boolean);

//     // 如果所有子节点都被过滤掉了，也可选择不返回该目录（按需调整）
//     // 此处保留目录即使无子节点（与原逻辑一致）
//     return {
//       ...route,
//       children: processedChildren,
//     };
//   }

//   // 叶子节点：匹配产品权限
//   const matchedProduct = products.find((p) => p.label === route.menuName);

//   if (!matchedProduct) {
//     return null; // 无权限，过滤掉
//   }

//   // 有权限，拼接 route 路径
//   return {
//     ...route,
//     route: `${route.route ?? ''}/${matchedProduct.id}`,
//   };
// }
