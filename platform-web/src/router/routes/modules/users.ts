import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const users: AppRouteModule = {
  path: '/user',
  name: 'User',
  component: LAYOUT,
  redirect: '/user/list',
  meta: {
    title: '用户管理',
    orderNo: 50,
    hideMenu: true,
    roles: [RoleEnum.ADMIN],
  },
  children: [
    {
      path: 'list',
      name: 'UserList',
      component: () => import('@/views/users/index.vue'),
      meta: {
        title: '用户管理',
        icon: 'ant-design:user-outlined',
        hideMenu: true,
        roles: [RoleEnum.ADMIN],
      },
    },
  ],
};

export default users;
