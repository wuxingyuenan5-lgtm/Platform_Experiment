import type { RouteMeta } from 'vue-router';
import { hasPermission } from './userAccess';

export interface RouteMetaCarrier {
  meta?: Partial<RouteMeta>;
}

export function normalizeRoutePermissions(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value
      .map(String)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (typeof value === 'string' && value.trim()) {
    return [value.trim()];
  }
  return [];
}

export function matchedRoutePermissions(matched: readonly RouteMetaCarrier[]): string[] {
  return Array.from(
    new Set(matched.flatMap((record) => normalizeRoutePermissions(record.meta?.permissions))),
  );
}

export function canAccessMatchedRoute(
  matched: readonly RouteMetaCarrier[],
  permissions: readonly string[],
): boolean {
  return matchedRoutePermissions(matched).every((permission) =>
    hasPermission(permissions, permission),
  );
}

export function canAccessRouteMeta(
  meta: Partial<RouteMeta> | undefined,
  permissions: readonly string[],
): boolean {
  return normalizeRoutePermissions(meta?.permissions).every((permission) =>
    hasPermission(permissions, permission),
  );
}

export function filterPermissionTree<T extends RouteMetaCarrier & { children?: T[] }>(
  items: readonly T[],
  permissions: readonly string[],
): T[] {
  return items.flatMap((item) => {
    if (!canAccessRouteMeta(item.meta, permissions)) return [];

    const originalChildren = item.children || [];
    const children = filterPermissionTree(originalChildren, permissions);
    if (originalChildren.length > 0 && children.length === 0) return [];

    return [{ ...item, children } as T];
  });
}
