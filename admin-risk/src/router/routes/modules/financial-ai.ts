import type { AppRouteModule } from '@/router/types';
import { LAYOUT } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const financialAi: AppRouteModule = {
  path: '/financial-ai',
  name: 'FinancialAi',
  component: LAYOUT,
  redirect: '/financial-ai/index',
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
      component: () => import('@/views/financialAi/index.vue'),
      meta: {
        title: '金融AI分析',
        icon: 'ant-design:robot-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE, RoleEnum.GUEST],
      },
    },
  ],
};

export default financialAi;
