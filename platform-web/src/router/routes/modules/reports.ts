import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const reports: AppRouteModule = {
  path: '/reports',
  name: 'Reports',
  component: LAYOUT,
  redirect: '/reports/index',
  meta: {
    title: '报表',
    icon: 'ant-design:bar-chart-outlined',
    orderNo: 30,
    hideMenu: true,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
  },
  children: [
    {
      path: 'index',
      name: 'ReportsIndex',
      component: () => import('@/views/reports/index.vue'),
      meta: {
        title: '报表',
        icon: 'ant-design:bar-chart-outlined',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
  ],
};

export default reports;
