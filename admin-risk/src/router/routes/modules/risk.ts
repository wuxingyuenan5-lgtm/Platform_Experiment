import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const internalRoles = [RoleEnum.CEO, RoleEnum.TECH_LEAD, RoleEnum.EMPLOYEE];

const risk: AppRouteModule = {
  path: '/risk',
  name: 'Risk',
  component: LAYOUT,
  redirect: '/risk/detail',
  meta: {
    title: '风控管理',
    icon: 'ant-design:safety-certificate-outlined',
    orderNo: 60,
    roles: internalRoles,
    permissions: 'risk.read',
  },
  children: [
    {
      path: 'detail',
      name: 'RiskDetail',
      component: () => import('@/views/risk/detail/index.vue'),
      meta: {
        title: '风控详情',
        icon: 'ant-design:warning-outlined',
        roles: internalRoles,
        permissions: 'risk.read',
      },
    },
    {
      path: 'users',
      name: 'RiskUserManagement',
      component: () => import('@/views/users/index.vue'),
      meta: {
        title: '用户管理',
        icon: 'ant-design:user-outlined',
        roles: internalRoles,
        permissions: 'user.read',
      },
    },
    {
      path: 'profile',
      name: 'RiskPersonalProfile',
      redirect: '/account/index',
      meta: {
        title: '个人账号',
        icon: 'ant-design:user-switch-outlined',
        roles: internalRoles,
        permissions: 'profile.read_self',
        hideMenu: true,
      },
    },
  ],
};

export default risk;
