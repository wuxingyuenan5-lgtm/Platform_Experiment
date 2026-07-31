import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const strategy: AppRouteModule = {
  path: '/strategy',
  name: 'Strategy',
  component: LAYOUT,
  redirect: '/strategy/platform',
  meta: {
    title: '策略',
    icon: 'ant-design:line-chart-outlined',
    orderNo: 50,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
  },
  children: [
    {
      path: 'platform',
      name: 'StrategyPlatform',
      component: () => import('@/views/platform/index.vue'),
      meta: {
        title: '交易平台',
        icon: 'ant-design:dashboard-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
    {
      path: 'management',
      name: 'StrategyManagement',
      component: () => import('@/views/strategy/index.vue'),
      meta: {
        title: '策略管理',
        icon: 'ant-design:apartment-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
  ],
};

export default strategy;
