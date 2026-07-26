import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const internalRoles = [RoleEnum.CEO, RoleEnum.TECH_LEAD, RoleEnum.EMPLOYEE];

const dashboard: AppRouteModule = {
  path: '/home',
  name: 'Home',
  component: LAYOUT,
  redirect: '/home/index',
  meta: {
    title: '首页',
    icon: 'ant-design:home-outlined',
    orderNo: 0,
    roles: internalRoles,
  },
  children: [
    {
      path: 'index',
      name: 'Dashboard',
      component: () => import('@/views/dashboard/index.vue'),
      meta: {
        title: '首页',
        single: true,
        affix: true,
        roles: internalRoles,
      },
    },
  ],
};

export default dashboard;
