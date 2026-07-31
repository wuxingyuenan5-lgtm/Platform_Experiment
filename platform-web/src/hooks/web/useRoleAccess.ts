import { computed } from 'vue';
import { useUserStore } from '@/store/modules/user';

export const ROLE_LABEL_MAP: Record<string, string> = {
  ceo: 'CEO',
  tech_lead: '技术负责人',
  employee: '员工',
  member: '会员',
  admin: '旧管理员',
  guest: '旧访客',
  super: '超级管理员',
  test: '测试',
};

export const ROLE_COLOR_MAP: Record<string, string> = {
  ceo: 'red',
  tech_lead: 'purple',
  employee: 'blue',
  member: 'green',
  admin: 'red',
  guest: 'default',
  super: 'purple',
  test: 'cyan',
};

export function useRoleAccess() {
  const userStore = useUserStore();

  const roles = computed(() => {
    const list = userStore.getRoleList || [];
    const fallback = (userStore.getUserInfo as any)?.role;
    return list.length ? list.map(String) : fallback ? [String(fallback)] : [];
  });

  const currentRole = computed(() => {
    const priority = ['ceo', 'tech_lead', 'employee', 'member', 'admin', 'super', 'test', 'guest'];
    return priority.find((role) => roles.value.includes(role)) || roles.value[0] || 'guest';
  });

  const roleLabel = computed(() => ROLE_LABEL_MAP[currentRole.value] || currentRole.value);
  const roleColor = computed(() => ROLE_COLOR_MAP[currentRole.value] || 'default');
  const isAdmin = computed(() => ['ceo', 'admin', 'super'].includes(currentRole.value));
  const isTechnicalLead = computed(() => currentRole.value === 'tech_lead');
  const isEmployee = computed(() => currentRole.value === 'employee');
  const isMember = computed(() => currentRole.value === 'member');
  const isGuest = computed(() => currentRole.value === 'guest');
  const canOperateData = computed(() => isAdmin.value || isTechnicalLead.value || isEmployee.value);
  const canManageAccounts = computed(
    () => isAdmin.value || isTechnicalLead.value || isEmployee.value,
  );
  const canDeleteAccounts = computed(() => isAdmin.value);
  const canViewRisk = computed(() => isAdmin.value || isTechnicalLead.value || isEmployee.value);

  return {
    roles,
    currentRole,
    roleLabel,
    roleColor,
    isAdmin,
    isTechnicalLead,
    isEmployee,
    isMember,
    isGuest,
    canOperateData,
    canManageAccounts,
    canDeleteAccounts,
    canViewRisk,
  };
}
