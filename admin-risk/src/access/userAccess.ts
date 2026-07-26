export type PermissionRequirement = string | string[];

export function hasPermission(granted: readonly string[], permission: string): boolean {
  return granted.includes('*') || granted.includes(permission);
}

export function hasEveryPermission(
  granted: readonly string[],
  required?: PermissionRequirement,
): boolean {
  if (!required) return true;
  const values = Array.isArray(required) ? required : [required];
  return values.every((permission) => hasPermission(granted, permission));
}

export function hasAnyPermission(
  granted: readonly string[],
  required?: PermissionRequirement,
): boolean {
  if (!required) return true;
  const values = Array.isArray(required) ? required : [required];
  return values.some((permission) => hasPermission(granted, permission));
}

export function canAccessRoute(
  granted: readonly string[],
  meta?: Record<string, unknown>,
): boolean {
  const all = meta?.permissions as PermissionRequirement | undefined;
  const any = meta?.anyPermissions as PermissionRequirement | undefined;
  return hasEveryPermission(granted, all) && hasAnyPermission(granted, any);
}
