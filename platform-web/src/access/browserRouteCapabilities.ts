import type { AppRouteRecordRaw } from '@/router/types';

export const BROWSER_ROUTE_CAPABILITIES: Readonly<Record<string, string>> = Object.freeze({
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
  '/users': 'user.read',
  '/audit': 'audit:read',
  '/account': 'profile.read_self',
});

function applyCapability(
  route: AppRouteRecordRaw,
  inheritedCapability?: string,
): AppRouteRecordRaw {
  const capability = BROWSER_ROUTE_CAPABILITIES[route.path] || inheritedCapability;
  const meta = { ...(route.meta || {}) } as Record<string, unknown>;

  // Historical route-role arrays are identity metadata only. Browser access is
  // resolved from the server-issued capability set and must not fork here.
  delete meta.roles;
  if (capability) meta.permissions = capability;

  return {
    ...route,
    meta,
    children: route.children?.map((child) => applyCapability(child, capability)),
  } as AppRouteRecordRaw;
}

export function applyBrowserRouteCapabilities(
  routes: readonly AppRouteRecordRaw[],
): AppRouteRecordRaw[] {
  return routes.map((route) => applyCapability(route));
}
