import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const finance: AppRouteModule = {
  path: '/finance',
  name: 'Finance',
  component: LAYOUT,
  redirect: '/finance/index',
  meta: {
    title: '财务',
    icon: 'ant-design:wallet-outlined',
    orderNo: 50,
    hideMenu: true,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
  },
  children: [
    {
      path: 'index',
      name: 'FinanceIndex',
      component: () => import('@/views/finance/index.vue'),
      meta: {
        title: '财务概览',
        icon: 'ant-design:wallet-outlined',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
  ],
};

export default finance;
