import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const browserRoles = [RoleEnum.CEO, RoleEnum.TECH_LEAD, RoleEnum.EMPLOYEE, RoleEnum.MEMBER];

const account: AppRouteModule = {
  path: '/account',
  name: 'Account',
  component: LAYOUT,
  redirect: '/account/index',
  meta: {
    title: '个人账号',
    icon: 'ant-design:user-outlined',
    orderNo: 80,
    roles: browserRoles,
    permissions: 'profile.read_self',
  },
  children: [
    {
      path: 'index',
      name: 'AccountIndex',
      component: () => import('@/views/account/index.vue'),
      meta: {
        title: '个人账号',
        icon: 'ant-design:user-outlined',
        single: true,
        roles: browserRoles,
        permissions: 'profile.read_self',
      },
    },
  ],
};

export default account;
