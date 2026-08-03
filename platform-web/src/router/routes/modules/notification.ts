import type { AppRouteModule } from '@/router/types';

import { LAYOUT } from '@/router/constant';

const notification: AppRouteModule = {
  path: '/notification',
  name: 'Notification',
  component: LAYOUT,
  redirect: '/notification/index',
  meta: {
    hideMenu: true,
    hideChildrenInMenu: true,
    orderNo: 1,
    icon: 'menu-notification|svg',
    title: '消息通知',
  },
  children: [
    {
      path: 'index',
      name: 'notificationPage',
      component: () => import('@/views/notification/index.vue'),
      meta: {
        title: '消息通知',
        icon: 'menu-notification|svg',
        hideMenu: true,
        single: true,
        currentActiveMenu: '/notification/index',
      },
    },
  ],
};

export default notification;
