import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const dataModule: AppRouteModule = {
  path: '/data',
  name: 'Data',
  component: LAYOUT,
  redirect: '/data/index',
  meta: {
    title: '数据',
    icon: 'ant-design:database-outlined',
    orderNo: 60,
    hideMenu: true,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
  },
  children: [
    {
      path: 'index',
      name: 'DataIndex',
      component: () => import('@/views/data/index.vue'),
      meta: {
        title: '数据管理',
        icon: 'ant-design:database-outlined',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
  ],
};

export default dataModule;
