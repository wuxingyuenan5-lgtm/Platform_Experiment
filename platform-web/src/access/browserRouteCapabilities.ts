import type { PermissionRequirement } from '@/access/userAccess';
import type { AppRouteRecordRaw } from '@/router/types';

export const BROWSER_ROUTE_CAPABILITIES: Readonly<
  Record<string, PermissionRequirement>
> = Object.freeze({
  '/home': 'dashboard.read',
  '/hedge-board': 'research.read',
  '/strategy': 'strategy.read',
  '/finance': 'finance.read',
  '/data': 'data.read',
  '/monitor': 'monitor.read',
  '/reports': 'reports.read',
  '/news-calendar': 'news.read',
  '/financial-ai': 'financial_ai.read',
  '/settings': 'settings.read',
  '/risk': 'risk.read',
  '/risk/detail': 'risk.read',
  '/risk/users': 'user.read',
  '/risk/profile': 'profile.read_self',
  '/users': 'user.read',
  '/audit': 'audit:read',
  '/account': 'profile.read_self',
});

function normalizeRoutePath(parentPath: string, routePath: string): string {
  if (routePath.startsWith('/')) return routePath.replace(/\/+$/, '') || '/';
  const parent = parentPath.replace(/\/+$/, '');
  const child = routePath.replace(/^\/+|\/+$/g, '');
  return `${parent}/${child}`.replace(/\/{2,}/g, '/') || '/';
}

function applyCapability(
  route: AppRouteRecordRaw,
  parentPath = '',
  inheritedCapability?: PermissionRequirement,
): AppRouteRecordRaw {
  const fullPath = normalizeRoutePath(parentPath, route.path);
  const meta = { ...(route.meta || {}) } as Record<string, unknown>;
  const explicitCapability = meta.permissions as PermissionRequirement | undefined;
  const mappedCapability = BROWSER_ROUTE_CAPABILITIES[fullPath];
  const capability = explicitCapability ?? mappedCapability ?? inheritedCapability;

  // Historical route-role arrays are identity metadata only. Browser access is
  // resolved from the server-issued capability set and must not fork here.
  delete meta.roles;
  if (capability) meta.permissions = capability;

  return {
    ...route,
    meta,
    children: route.children?.map((child) =>
      applyCapability(child, fullPath, capability),
    ),
  } as AppRouteRecordRaw;
}

export function applyBrowserRouteCapabilities(
  routes: readonly AppRouteRecordRaw[],
): AppRouteRecordRaw[] {
  return routes.map((route) => applyCapability(route));
}
