import { computed } from 'vue';
import { useUserStore } from '@/store/modules/user';

export const ROLE_LABEL_MAP: Record<string, string> = {
  admin: '管理员',
  employee: '员工',
  guest: '访客',
  super: '超级管理员',
  test: '测试',
};

export const ROLE_COLOR_MAP: Record<string, string> = {
  admin: 'red',
  employee: 'blue',
  guest: 'default',
  super: 'purple',
  test: 'green',
};

export function useRoleAccess() {
  const userStore = useUserStore();

  const roles = computed(() => {
    const list = userStore.getRoleList || [];
    const fallback = (userStore.getUserInfo as any)?.role;
    return list.length ? list.map(String) : fallback ? [String(fallback)] : ['guest'];
  });

  const currentRole = computed(() => {
    if (roles.value.includes('admin') || roles.value.includes('super')) return 'admin';
    if (roles.value.includes('employee')) return 'employee';
    return roles.value[0] || 'guest';
  });

  const roleLabel = computed(() => ROLE_LABEL_MAP[currentRole.value] || currentRole.value);
  const roleColor = computed(() => ROLE_COLOR_MAP[currentRole.value] || 'default');
  const isAdmin = computed(() => currentRole.value === 'admin');
  const isEmployee = computed(() => currentRole.value === 'employee');
  const isGuest = computed(() => currentRole.value === 'guest');
  const canOperateData = computed(() => isAdmin.value || isEmployee.value);
  const canManageAccounts = computed(() => isAdmin.value || isEmployee.value);
  const canDeleteAccounts = computed(() => isAdmin.value);
  const canViewRisk = computed(() => isAdmin.value || isEmployee.value);

  return {
    roles,
    currentRole,
    roleLabel,
    roleColor,
    isAdmin,
    isEmployee,
    isGuest,
    canOperateData,
    canManageAccounts,
    canDeleteAccounts,
    canViewRisk,
  };
}
