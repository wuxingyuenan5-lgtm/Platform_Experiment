import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const financialAi: AppRouteModule = {
  path: '/financial-ai',
  name: 'FinancialAi',
  component: LAYOUT,
  redirect: '/financial-ai/daily-review',
  meta: {
    title: '金融AI分析',
    icon: 'ant-design:robot-outlined',
    orderNo: 61,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
  },
  children: [
    {
      path: 'index',
      name: 'FinancialAiIndex',
      redirect: '/financial-ai/daily-review',
      meta: {
        title: '金融AI分析',
        hideMenu: true,
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
    {
      path: 'daily-review',
      name: 'FinancialAiDailyReview',
      component: () => import('@/views/financialAi/dailyReview.vue'),
      meta: {
        title: 'AI当日复盘',
        icon: 'ant-design:fund-view-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
    {
      path: 'stock-analysis',
      name: 'FinancialAiStockAnalysis',
      component: () => import('@/views/financialAi/stockAnalysis.vue'),
      meta: {
        title: '个股分析',
        icon: 'ant-design:stock-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
    {
      path: 'news-radar',
      name: 'FinancialAiNewsRadar',
      component: () => import('@/views/financialAi/newsRadar.vue'),
      meta: {
        title: '资讯雷达',
        icon: 'ant-design:radar-chart-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
    {
      path: 'ai-connection',
      name: 'FinancialAiConnection',
      component: () => import('@/views/financialAi/aiConnection.vue'),
      meta: {
        title: '接入AI',
        icon: 'ant-design:api-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
  ],
};

export default financialAi;
