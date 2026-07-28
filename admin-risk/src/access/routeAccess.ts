import type { RouteMeta } from 'vue-router';
import { hasPermission } from './userAccess';

export interface RouteMetaCarrier {
  meta?: Partial<RouteMeta>;
}

export interface RoutePathCarrier extends RouteMetaCarrier {
  path?: string;
  children?: RoutePathCarrier[];
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

function normalizeStaticPath(value: string): string {
  const withoutQuery = value.split(/[?#]/, 1)[0] || '/';
  const withLeadingSlash = withoutQuery.startsWith('/') ? withoutQuery : `/${withoutQuery}`;
  const compact = withLeadingSlash.replace(/\/{2,}/g, '/');
  return compact.length > 1 ? compact.replace(/\/+$/, '') : compact;
}

function resolveRoutePath(parentPath: string, routePath: string): string {
  return routePath.startsWith('/')
    ? normalizeStaticPath(routePath)
    : normalizeStaticPath(`${parentPath}/${routePath}`);
}

export function findRouteChainByPath(
  items: readonly RoutePathCarrier[],
  targetPath: string,
  parentPath = '',
  parentChain: readonly RouteMetaCarrier[] = [],
): RouteMetaCarrier[] | undefined {
  const normalizedTarget = normalizeStaticPath(targetPath);
  for (const item of items) {
    if (!item.path) continue;

    const currentPath = resolveRoutePath(parentPath, item.path);
    const currentChain = [...parentChain, item];
    if (!/[:*]/.test(currentPath) && currentPath === normalizedTarget) return currentChain;

    const childMatch = findRouteChainByPath(
      item.children || [],
      normalizedTarget,
      currentPath,
      currentChain,
    );
    if (childMatch) return childMatch;
  }
  return undefined;
}

export function isKnownRouteDenied(
  items: readonly RoutePathCarrier[],
  targetPath: string,
  permissions: readonly string[],
): boolean {
  const chain = findRouteChainByPath(items, targetPath);
  return chain !== undefined && !canAccessMatchedRoute(chain, permissions);
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
