import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const news: AppRouteModule = {
  path: '/news-calendar',
  name: 'NewsCalendar',
  component: LAYOUT,
  redirect: '/news-calendar/macro',
  meta: {
    title: '新闻日历与理财',
    icon: 'ant-design:calendar-outlined',
    orderNo: 40,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
  },
  children: [
    {
      path: 'macro',
      name: 'NewsCalendarMacro',
      component: () => import('@/views/newsCalendar/index.vue'),
      meta: {
        title: '宏观日历',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        newsSection: 'macro',
      },
    },
    {
      path: 'news',
      name: 'NewsCalendarNews',
      component: () => import('@/views/newsCalendar/index.vue'),
      meta: {
        title: '新闻整理',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        newsSection: 'news',
      },
    },
    {
      path: 'wealth',
      name: 'NewsCalendarWealth',
      component: () => import('@/views/newsCalendar/index.vue'),
      meta: {
        title: '理财信息',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        newsSection: 'wealth',
        embeddedUrl: 'https://app.barker.money/campaigns',
      },
    },
    {
      path: 'calendar',
      name: 'NewsCalendarLegacy',
      redirect: '/news-calendar/macro',
      meta: {
        title: '新闻日历',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
  ],
};

export default news;
