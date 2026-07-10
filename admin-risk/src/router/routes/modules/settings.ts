import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const settings: AppRouteModule = {
  path: '/settings',
  name: 'Settings',
  component: LAYOUT,
  redirect: '/settings/profile',
  meta: {
    title: '系统设置',
    icon: 'ant-design:setting-outlined',
    orderNo: 90,
    hideMenu: true,
    roles: [RoleEnum.ADMIN],
  },
  children: [
    {
      path: 'profile',
      name: 'SettingsProfile',
      component: () => import('@/views/settings/index.vue'),
      meta: {
        title: '基本设置',
        icon: 'ant-design:setting-outlined',
        hideMenu: true,
        roles: [RoleEnum.ADMIN],
      },
    },
  ],
};

export default settings;
