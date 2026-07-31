import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const audit: AppRouteModule = {
  path: '/audit',
  name: 'Audit',
  component: LAYOUT,
  redirect: '/audit/index',
  meta: {
    title: '审计',
    icon: 'ant-design:file-search-outlined',
    orderNo: 40,
    hideMenu: true,
    roles: [RoleEnum.ADMIN],
  },
  children: [
    {
      path: 'index',
      name: 'AuditIndex',
      component: () => import('@/views/audit/index.vue'),
      meta: {
        title: '审计日志',
        icon: 'ant-design:file-search-outlined',
        hideMenu: true,
        roles: [RoleEnum.ADMIN],
      },
    },
  ],
};

export default audit;
