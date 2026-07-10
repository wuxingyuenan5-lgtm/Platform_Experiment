import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const risk: AppRouteModule = {
  path: '/risk',
  name: 'Risk',
  component: LAYOUT,
  redirect: '/risk/records',
  meta: {
    title: '风控管理',
    orderNo: 60,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
  },
  children: [
    {
      path: 'records',
      name: 'RiskRecords',
      component: () => import('@/views/risk/index.vue'),
      meta: {
        title: '风控总览',
        icon: 'ant-design:warning-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
    {
      path: 'reports',
      name: 'RiskReports',
      component: () => import('@/views/reports/index.vue'),
      meta: {
        title: '报表中心',
        icon: 'ant-design:bar-chart-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
    {
      path: 'finance',
      name: 'RiskFinanceOverview',
      component: () => import('@/views/finance/index.vue'),
      meta: {
        title: '财务总览',
        icon: 'ant-design:wallet-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
    {
      path: 'audit',
      name: 'RiskAuditLog',
      component: () => import('@/views/audit/index.vue'),
      meta: {
        title: '审计日志',
        icon: 'ant-design:file-search-outlined',
        roles: [RoleEnum.ADMIN],
      },
    },
    {
      path: 'data',
      name: 'RiskDataManagement',
      component: () => import('@/views/data/index.vue'),
      meta: {
        title: '数据管理',
        icon: 'ant-design:database-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
    {
      path: 'monitor',
      name: 'RiskSystemMonitor',
      component: () => import('@/views/monitor/index.vue'),
      meta: {
        title: '系统监控',
        icon: 'ant-design:monitor-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
    },
    {
      path: 'accounts',
      name: 'RiskAccountManagement',
      component: () => import('@/views/account/index.vue'),
      meta: {
        title: '账户管理',
        icon: 'ant-design:credit-card-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
    {
      path: 'users',
      name: 'RiskUserManagement',
      component: () => import('@/views/users/index.vue'),
      meta: {
        title: '用户管理',
        icon: 'ant-design:user-outlined',
        roles: [RoleEnum.ADMIN],
      },
    },
  ],
};

export default risk;
