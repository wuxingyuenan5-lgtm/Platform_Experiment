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
    hideMenu: true,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
  },
  children: [
    {
      path: 'macro',
      name: 'NewsCalendarMacro',
      redirect: '/hedge-board/macro',
      meta: {
        title: '宏观日历',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        newsSection: 'macro',
        ignoreKeepAlive: true,
      },
    },
    {
      path: 'news',
      name: 'NewsCalendarNews',
      redirect: '/financial-ai/index#news-digest',
      meta: {
        title: '新闻整理',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        newsSection: 'news',
        ignoreKeepAlive: true,
      },
    },
    {
      path: 'wealth',
      name: 'NewsCalendarWealth',
      redirect: '/hedge-board/crypto',
      meta: {
        title: '理财信息',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        newsSection: 'wealth',
        ignoreKeepAlive: true,
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
