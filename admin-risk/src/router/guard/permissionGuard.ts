import type { Router, RouteRecordRaw } from 'vue-router';

import { usePermissionStoreWithOut } from '@/store/modules/permission';

import { PageEnum } from '@/enums/pageEnum';
import { useUserStoreWithOut } from '@/store/modules/user';

import { PAGE_NOT_FOUND_ROUTE } from '@/router/routes/basic';
import { PAGE_NOT_FOUND_NAME } from '@/router/constant';

import { RootRoute } from '@/router/routes';

const LOGIN_PATH = PageEnum.BASE_LOGIN;
const REGISTER_APPLY_PATH = '/register-apply';

const ROOT_PATH = RootRoute.path;
const PAGE_NOT_FOUND_CHILD_NAME = PAGE_NOT_FOUND_NAME;
const PAGE_NOT_FOUND_PARENT_NAME = String(PAGE_NOT_FOUND_ROUTE.name || '');
const PAGE_NOT_FOUND_NAMES = [PAGE_NOT_FOUND_PARENT_NAME, PAGE_NOT_FOUND_CHILD_NAME].filter(Boolean);

const whitePathList = [LOGIN_PATH, REGISTER_APPLY_PATH];

export function createPermissionGuard(router: Router) {
  const userStore = useUserStoreWithOut();
  const permissionStore = usePermissionStoreWithOut();

  const ensureDynamicRoutes = async () => {
    const routes = await permissionStore.buildRoutesAction();

    routes.forEach((route) => {
      const routeName = String(route.name || '');
      if (routeName && router.hasRoute(routeName)) {
        return;
      }
      router.addRoute(route as unknown as RouteRecordRaw);
    });

    permissionStore.setDynamicAddedRoute(true);
  };

  router.beforeEach(async (to, from, next) => {
    if (
      to.path === PageEnum.BASE_HOME &&
      userStore.getUserInfo.homePath &&
      userStore.getUserInfo.homePath !== PageEnum.BASE_HOME
    ) {
      next(userStore.getUserInfo.homePath);
      return;
    }

    const token = userStore.getToken;
    // Whitelist can be directly entered
    if (whitePathList.includes(to.path as PageEnum)) {
      if (to.path === LOGIN_PATH && token) {
        const isSessionTimeout = userStore.getSessionTimeout;
        try {
          await userStore.afterLoginAction();
          if (!isSessionTimeout && userStore.getUserInfo?.data) {
            next((to.query?.redirect as string) || '/');
            return;
          }
        } catch {
          //
        }
      }
      next();
      return;
    }

    // token or user does not exist
    if (!token) {
      // You can access without permission. You need to set the routing meta.ignoreAuth to true
      if (to.meta.ignoreAuth) {
        next();
        return;
      }

      // redirect login page
      const redirectData: { path: string; replace: boolean; query?: Recordable<string> } = {
        path: LOGIN_PATH,
        replace: true,
      };
      if (to.path) {
        redirectData.query = {
          ...redirectData.query,
          redirect: to.path,
        };
      }
      next(redirectData);
      return;
    }

    // Jump to the 404 page after processing the login
    if (
      from.path === LOGIN_PATH &&
      PAGE_NOT_FOUND_NAMES.includes(String(to.name || '')) &&
      to.fullPath !== (userStore.getUserInfo.homePath || PageEnum.BASE_HOME)
    ) {
      next(userStore.getUserInfo.homePath || PageEnum.BASE_HOME);
      return;
    }

    // get userinfo while last fetch time is empty
    if (userStore.getLastUpdateTime === 0) {
      try {
        await userStore.getUserInfoAction();
      } catch (err) {
        next();
        return;
      }
    }

    if (permissionStore.getIsDynamicAddedRoute) {
      const isUnmatchedRoute =
        to.matched.length === 0 || PAGE_NOT_FOUND_NAMES.includes(String(to.name || ''));

      if (isUnmatchedRoute) {
        await ensureDynamicRoutes();
        next({ path: to.fullPath, replace: true, query: to.query });
        return;
      }

      next();
      return;
    }

    await ensureDynamicRoutes();
    if (PAGE_NOT_FOUND_NAMES.includes(String(to.name || ''))) {
      // 动态添加路由后，此处应当重定向到fullPath，否则会加载404页面内容
      next({ path: to.fullPath, replace: true, query: to.query });
    } else {
      const redirectPath = ((to.query?.redirect as string) || to.fullPath || to.path) as string;
      const redirect = decodeURIComponent(redirectPath);
      const nextData = to.path === redirect ? { ...to, replace: true } : { path: redirect };
      next(nextData);
    }
  });
}
