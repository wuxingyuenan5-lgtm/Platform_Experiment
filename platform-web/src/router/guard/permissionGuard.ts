import type { Router, RouteRecordRaw } from 'vue-router';

import { usePermissionStoreWithOut } from '@/store/modules/permission';

import { PageEnum } from '@/enums/pageEnum';
import { useUserStoreWithOut } from '@/store/modules/user';

import { asyncRoutes } from '@/router/routes';
import { PAGE_NOT_FOUND_ROUTE } from '@/router/routes/basic';
import { PAGE_NOT_FOUND_NAME } from '@/router/constant';
import {
  canAccessMatchedRoute,
  filterPermissionTree,
  findRouteChainByPath,
  isKnownRouteDenied,
} from '@/access/routeAccess';

const LOGIN_PATH = PageEnum.BASE_LOGIN;
const REGISTER_APPLY_PATH = '/register-apply';
const RESET_PASSWORD_PATH = '/reset-password';
const FORBIDDEN_PATH = `${PageEnum.ERROR_PAGE}/403`;

const PAGE_NOT_FOUND_CHILD_NAME = PAGE_NOT_FOUND_NAME;
const PAGE_NOT_FOUND_PARENT_NAME = String(PAGE_NOT_FOUND_ROUTE.name || '');
const PAGE_NOT_FOUND_NAMES = [PAGE_NOT_FOUND_PARENT_NAME, PAGE_NOT_FOUND_CHILD_NAME].filter(
  Boolean,
);

const whitePathList = [LOGIN_PATH, REGISTER_APPLY_PATH, RESET_PASSWORD_PATH];

export function createPermissionGuard(router: Router) {
  const userStore = useUserStoreWithOut();
  const permissionStore = usePermissionStoreWithOut();

  const ensureDynamicRoutes = async () => {
    const permissions = userStore.getAuthentication?.permissions || [];
    const builtRoutes = await permissionStore.buildRoutesAction();
    const routes = filterPermissionTree(builtRoutes, permissions);
    permissionStore.setFrontMenuList(
      filterPermissionTree(permissionStore.getFrontMenuList, permissions),
    );

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

    if (whitePathList.includes(to.path as PageEnum)) {
      if (to.path === LOGIN_PATH) {
        const authenticated = await userStore.hydrateSession();
        if (authenticated) {
          next((to.query?.redirect as string) || userStore.getUserInfo.homePath || '/');
          return;
        }
      }
      next();
      return;
    }

    // Protected navigation must revalidate the server-side Session. Local Pinia
    // state is presentation state only and cannot survive password or admin revocation.
    const authenticated = await userStore.hydrateSession(true);
    if (!authenticated) {
      if (to.meta.ignoreAuth) {
        next();
        return;
      }
      const redirectData: { path: string; replace: boolean; query?: Recordable<string> } = {
        path: LOGIN_PATH,
        replace: true,
      };
      if (to.path) {
        redirectData.query = { redirect: to.path };
      }
      next(redirectData);
      return;
    }

    if (
      from.path === LOGIN_PATH &&
      PAGE_NOT_FOUND_NAMES.includes(String(to.name || '')) &&
      to.fullPath !== (userStore.getUserInfo.homePath || PageEnum.BASE_HOME)
    ) {
      next(userStore.getUserInfo.homePath || PageEnum.BASE_HOME);
      return;
    }

    if (userStore.getLastUpdateTime === 0) {
      try {
        await userStore.getUserInfoAction();
      } catch {
        await userStore.logout(false);
        next({ path: LOGIN_PATH, replace: true, query: { redirect: to.fullPath } });
        return;
      }
    }

    const permissions = userStore.getAuthentication?.permissions || [];
    if (!canAccessMatchedRoute(to.matched, permissions)) {
      next({ path: FORBIDDEN_PATH, replace: true });
      return;
    }

    if (permissionStore.getIsDynamicAddedRoute) {
      const isUnmatchedRoute =
        to.matched.length === 0 || PAGE_NOT_FOUND_NAMES.includes(String(to.name || ''));

      if (isUnmatchedRoute) {
        const knownRoute = findRouteChainByPath(asyncRoutes, to.path) !== undefined;
        if (knownRoute) {
          if (isKnownRouteDenied(asyncRoutes, to.path, permissions)) {
            next({ path: FORBIDDEN_PATH, replace: true });
            return;
          }
          // Pinia state can survive a full browser reload while Vue Router's
          // in-memory dynamic route table cannot. Rebuild known authorized routes
          // before retrying the original URL instead of falling through to 404/home.
          await ensureDynamicRoutes();
          next({ path: to.fullPath, replace: true, query: to.query });
          return;
        }
        next();
        return;
      }

      next();
      return;
    }

    await ensureDynamicRoutes();
    if (PAGE_NOT_FOUND_NAMES.includes(String(to.name || ''))) {
      if (isKnownRouteDenied(asyncRoutes, to.path, permissions)) {
        next({ path: FORBIDDEN_PATH, replace: true });
        return;
      }
      next({ path: to.fullPath, replace: true, query: to.query });
    } else {
      const redirectPath = ((to.query?.redirect as string) || to.fullPath || to.path) as string;
      const redirect = decodeURIComponent(redirectPath);
      const nextData = to.path === redirect ? { ...to, replace: true } : { path: redirect };
      next(nextData);
    }
  });
}
