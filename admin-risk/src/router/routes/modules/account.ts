import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const account: AppRouteModule = {
  path: '/account',
  name: 'Account',
  component: LAYOUT,
  redirect: '/account/index',
  meta: {
    title: '账户',
    icon: 'ant-design:credit-card-outlined',
    orderNo: 80,
    hideMenu: true,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
  },
  children: [
    {
      path: 'index',
      name: 'AccountIndex',
      component: () => import('@/views/account/index.vue'),
      meta: {
        title: '账户管理',
        icon: 'ant-design:credit-card-outlined',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
  ],
};

export default account;
