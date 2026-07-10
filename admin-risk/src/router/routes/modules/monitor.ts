import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const monitor: AppRouteModule = {
  path: '/monitor',
  name: 'Monitor',
  component: LAYOUT,
  redirect: '/monitor/index',
  meta: {
    title: '监控',
    icon: 'ant-design:monitor-outlined',
    orderNo: 70,
    hideMenu: true,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
  },
  children: [
    {
      path: 'index',
      name: 'MonitorIndex',
      component: () => import('@/views/monitor/index.vue'),
      meta: {
        title: '系统监控',
        icon: 'ant-design:monitor-outlined',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
  ],
};

export default monitor;
