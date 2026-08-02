import type { AppRouteModule, AppRouteRecordRaw, Component } from '@/router/types';
import type { Router, RouteRecordNormalized } from 'vue-router';

import { getParentLayout, LAYOUT, EXCEPTION_COMPONENT } from '@/router/constant';
import { resolveViewComponent } from '@/router/viewRegistry.generated';
import { cloneDeep, omit } from 'lodash-es';
import { warn } from '@/utils/log';
import { createRouter, createWebHashHistory } from 'vue-router';

export type LayoutMapKey = 'IFRAME' | 'LAYOUT';
const IFRAME: Component = () => import('@/views/sys/iframe/FrameBlank.vue');

const layoutMap = new Map<LayoutMapKey, Component>([
  ['LAYOUT', LAYOUT],
  ['IFRAME', IFRAME],
]);

function resolveRouteComponent(component: string): Component {
  const layout = layoutMap.get(component.toUpperCase() as LayoutMapKey);
  if (layout) return layout;

  const view = resolveViewComponent(component);
  if (view) return view;

  warn(`在正式View Registry中找不到组件：${component}`);
  return EXCEPTION_COMPONENT;
}

// Convert backend menu records into runtime route records.
function asyncImportRoute(routes: AppRouteRecordRaw[] | undefined): void {
  if (!routes) return;

  routes.forEach((item) => {
    if (!item.component && item.meta?.frameSrc) {
      item.component = 'IFRAME';
    }

    const { component, name } = item;
    if (typeof component === 'string') {
      item.component = resolveRouteComponent(component);
    } else if (!component && name) {
      item.component = getParentLayout();
    }

    if (item.children?.length) asyncImportRoute(item.children);
  });
}

// Turn background objects into routing objects.
export function transformObjToRoute<T = AppRouteModule>(routeList: AppRouteModule[]): T[] {
  routeList.forEach((route) => {
    const { component } = route;
    if (typeof component === 'string') {
      if (component.toUpperCase() === 'LAYOUT') {
        route.component = layoutMap.get('LAYOUT');
      } else {
        route.children = [cloneDeep(route)];
        route.component = LAYOUT;

        if (!route.name) {
          warn(`找不到菜单对应的name, 请检查数据!${JSON.stringify(route)}`);
        }
        route.name = `${route.name}Parent`;
        route.path = '';
        route.meta = {
          ...(route.meta || {}),
          single: true,
          affix: false,
        };
      }
    } else if (!component) {
      warn(`请正确配置路由：${String(route.name)}的component属性`);
    }

    if (route.children?.length) asyncImportRoute(route.children);
  });
  return routeList as unknown as T[];
}

/** Convert multi-level routing to level 2 routing. */
export function flatMultiLevelRoutes(routeModules: AppRouteModule[]): AppRouteModule[] {
  const modules: AppRouteModule[] = cloneDeep(routeModules);

  for (const routeModule of modules) {
    if (isMultipleRoute(routeModule)) promoteRouteLevel(routeModule);
  }
  return modules;
}

function promoteRouteLevel(routeModule: AppRouteModule): void {
  let router: Router | null = createRouter({
    routes: [routeModule as unknown as RouteRecordNormalized],
    history: createWebHashHistory(),
  });
  const routes = router.getRoutes();
  addToChildren(routes, routeModule.children || [], routeModule);
  router = null;

  routeModule.children = routeModule.children?.map(
    (item) => omit(item, 'children') as AppRouteRecordRaw,
  );
}

function addToChildren(
  routes: RouteRecordNormalized[],
  children: AppRouteRecordRaw[],
  routeModule: AppRouteModule,
): void {
  for (const child of children) {
    const route = routes.find((item) => item.name === child.name);
    if (!route) continue;

    routeModule.children = routeModule.children || [];
    if (!routeModule.children.some((item) => item.name === route.name)) {
      routeModule.children.push(route as unknown as AppRouteModule);
    }
    if (child.children?.length) addToChildren(routes, child.children, routeModule);
  }
}

function isMultipleRoute(routeModule: AppRouteModule): boolean {
  return Boolean(routeModule?.children?.some((child) => child.children?.length));
}
