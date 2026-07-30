import type { AppRouteModule } from '@/router/types';
import { LAYOUT, getParentLayout } from '@/router/constant';
import { RoleEnum } from '@/enums/roleEnum';

const HEDGE_RESEARCH_ROLES = [RoleEnum.CEO, RoleEnum.TECH_LEAD, RoleEnum.EMPLOYEE, RoleEnum.ADMIN];

const hedge: AppRouteModule = {
  path: '/hedge-board',
  name: 'HedgeBoard',
  component: LAYOUT,
  redirect: '/hedge-board/macro',
  meta: {
    title: '\u5bf9\u51b2\u57fa\u91d1\u770b\u677f',
    icon: 'ant-design:fund-projection-screen-outlined',
    orderNo: 30,
    roles: HEDGE_RESEARCH_ROLES,
  },
  children: [
    {
      path: 'macro',
      name: 'HedgeMacroBoard',
      component: () => import('@/views/hedgeBoard/macro/index.vue'),
      meta: {
        title: '\u5b8f\u89c2',
        icon: 'ant-design:global-outlined',
        roles: HEDGE_RESEARCH_ROLES,
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
        roles: HEDGE_RESEARCH_ROLES,
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
        roles: HEDGE_RESEARCH_ROLES,
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
        roles: HEDGE_RESEARCH_ROLES,
        hedgeCategory: 'us',
      },
    },
    {
      path: 'a-share',
      name: 'HedgeAShareBoard',
      component: () => import('@/views/hedgeBoard/aShare/index.vue'),
      meta: {
        title: 'A\u80a1',
        icon: 'ant-design:bar-chart-outlined',
        roles: HEDGE_RESEARCH_ROLES,
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
        roles: HEDGE_RESEARCH_ROLES,
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
        roles: HEDGE_RESEARCH_ROLES,
      },
      children: [
        {
          path: 'macro',
          name: 'HedgeTradingToolsMacro',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u5b8f\u89c2\u5de5\u5177',
            roles: HEDGE_RESEARCH_ROLES,
            toolCategory: 'macro',
          },
        },
        {
          path: 'equity',
          name: 'HedgeTradingToolsEquity',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u80a1\u5e02\u5de5\u5177',
            roles: HEDGE_RESEARCH_ROLES,
            toolCategory: 'equity',
          },
        },
        {
          path: 'crypto',
          name: 'HedgeTradingToolsCrypto',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u52a0\u5bc6\u5de5\u5177',
            roles: HEDGE_RESEARCH_ROLES,
            toolCategory: 'crypto',
          },
        },
        {
          path: 'metal',
          name: 'HedgeTradingToolsMetal',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u91d1\u5c5e\u5de5\u5177',
            roles: HEDGE_RESEARCH_ROLES,
            toolCategory: 'metal',
          },
        },
        {
          path: 'quant',
          name: 'HedgeTradingToolsQuant',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u91cf\u5316\u5de5\u5177',
            roles: HEDGE_RESEARCH_ROLES,
            toolCategory: 'quant',
          },
        },
        {
          path: 'general',
          name: 'HedgeTradingToolsGeneral',
          component: () => import('@/views/hedgeBoard/tradingTools/index.vue'),
          meta: {
            title: '\u7efc\u5408\u5de5\u5177',
            roles: HEDGE_RESEARCH_ROLES,
            toolCategory: 'general',
          },
        },
      ],
    },
  ],
};

export default hedge;
