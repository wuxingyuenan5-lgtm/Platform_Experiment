import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const risk: AppRouteModule = {
  path: '/risk',
  name: 'Risk',
  component: LAYOUT,
  redirect: '/risk/detail',
  meta: {
    title: '风控管理',
    orderNo: 60,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
  },
  children: [
    {
      path: 'detail',
      name: 'RiskDetail',
      component: () => import('@/views/risk/detail/index.vue'),
      meta: {
        title: '风控详情',
        icon: 'ant-design:warning-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
    {
      path: 'users',
      name: 'RiskUserManagement',
      component: () => import('@/views/users/index.vue'),
      meta: {
        title: '用户管理',
        icon: 'ant-design:user-outlined',
        roles: [RoleEnum.ADMIN],
      },
    },
    {
      path: 'profile',
      name: 'RiskPersonalProfile',
      component: () => import('@/views/risk/profile/index.vue'),
      meta: {
        title: '个人账号',
        icon: 'ant-design:user-switch-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
  ],
};

export default risk;
