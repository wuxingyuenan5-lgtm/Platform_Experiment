import type { AppRouteModule } from '@/router/types';
import { LAYOUT, getParentLayout } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const hedge: AppRouteModule = {
  path: '/hedge-board',
  name: 'HedgeBoard',
  component: LAYOUT,
  redirect: '/hedge-board/macro',
  meta: {
    title: '\u5bf9\u51b2\u57fa\u91d1\u770b\u677f',
    icon: 'ant-design:fund-projection-screen-outlined',
    orderNo: 30,
    roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
  },
  children: [
    {
      path: 'macro',
      name: 'HedgeMacroBoard',
      component: () => import('@/views/hedgeBoard/index.vue'),
      meta: {
        title: '\u5b8f\u89c2',
        icon: 'ant-design:global-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        hedgeCategory: 'macro',
      },
    },
    {
      path: 'gold',
      name: 'HedgeGoldBoard',
      component: () => import('@/views/hedgeBoard/index.vue'),
      meta: {
        title: '\u5546\u54c1',
        icon: 'ant-design:gold-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        hedgeCategory: 'gold',
      },
    },
    {
      path: 'crypto',
      name: 'HedgeCryptoBoard',
      component: () => import('@/views/hedgeBoard/index.vue'),
      meta: {
        title: '\u52a0\u5bc6',
        icon: 'ant-design:cloud-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        hedgeCategory: 'crypto',
      },
    },
    {
      path: 'us',
      name: 'HedgeUsBoard',
      component: () => import('@/views/hedgeBoard/index.vue'),
      meta: {
        title: '\u7f8e\u80a1',
        icon: 'ant-design:stock-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        hedgeCategory: 'us',
      },
    },
    {
      path: 'a-share',
      name: 'HedgeAShareBoard',
      component: () => import('@/views/hedgeBoard/index.vue'),
      meta: {
        title: 'A\u80a1',
        icon: 'ant-design:bar-chart-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        hedgeCategory: 'aShare',
      },
    },
    {
      path: 'global',
      name: 'HedgeGlobalBoard',
      component: () => import('@/views/hedgeBoard/index.vue'),
      meta: {
        title: '\u5168\u7403',
        icon: 'ant-design:global-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
        hedgeCategory: 'global',
      },
    },
    {
      path: 'trading-tools',
      name: 'HedgeTradingTools',
      component: getParentLayout('HedgeTradingTools'),
      redirect: '/hedge-board/trading-tools/macro',
      meta: {
        title: '\u4ea4\u6613\u5de5\u5177',
        icon: 'ant-design:link-outlined',
        roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
      },
      children: [
        {
          path: 'macro',
          name: 'HedgeTradingToolsMacro',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u5b8f\u89c2\u5de5\u5177',
            roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
            toolCategory: 'macro',
          },
        },
        {
          path: 'equity',
          name: 'HedgeTradingToolsEquity',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u80a1\u5e02\u5de5\u5177',
            roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
            toolCategory: 'equity',
          },
        },
        {
          path: 'crypto',
          name: 'HedgeTradingToolsCrypto',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u52a0\u5bc6\u5de5\u5177',
            roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
            toolCategory: 'crypto',
          },
        },
        {
          path: 'metal',
          name: 'HedgeTradingToolsMetal',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u91d1\u5c5e\u5de5\u5177',
            roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
            toolCategory: 'metal',
          },
        },
        {
          path: 'quant',
          name: 'HedgeTradingToolsQuant',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u91cf\u5316\u5de5\u5177',
            roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
            toolCategory: 'quant',
          },
        },
        {
          path: 'general',
          name: 'HedgeTradingToolsGeneral',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u7efc\u5408\u5de5\u5177',
            roles: [RoleEnum.ADMIN, RoleEnum.EMPLOYEE],
            toolCategory: 'general',
          },
        },
      ],
    },
  ],
};

export default hedge;
