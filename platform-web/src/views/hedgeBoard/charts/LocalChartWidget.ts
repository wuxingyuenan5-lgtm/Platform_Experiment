import { defineComponent, h, type PropType } from 'vue';

import TerminalDetailPanel from '../components/TerminalDetailPanel.vue';
import MacroMarketDetailPanel from '../components/MacroMarketDetailPanel.vue';
import { type LocalWidgetKey, type WidgetConfig } from '../nativeData/dashboardClean';
import { marketTerminalConfigs } from '../nativeData/marketTerminal';
import { BTC_ETF_FLOW_ROWS, mergeGoldWithGvz, mergeGoldWithSeries } from './chartCore';
import DualAxisChart from './DualAxisChart';
import TreasuryFlowChart from './TreasuryFlowChart';
import MacroSeriesChart from './MacroSeriesChart';

const externalGoldResearch = {
  'etf-weekly-flows': {
    provider: 'World Gold Council',
    description: '全球及区域黄金 ETF 持仓与资金流',
    href: 'https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows',
  },
  'etf-ytd-summary': {
    provider: 'World Gold Council',
    description: '全球黄金 ETF 年内持仓与资金流汇总',
    href: 'https://www.gold.org/goldhub/data/gold-etfs-holdings-and-flows',
  },
  'spdr-daily-flow': {
    provider: 'SPDR Gold Shares',
    description: 'GLD 官方每日持仓及历史资料',
    href: 'https://www.spdrgoldshares.com/usa/historical-data/',
  },
  'spdr-holdings-vs-price': {
    provider: 'SPDR Gold Shares',
    description: 'GLD 官方每日持仓及历史资料',
    href: 'https://www.spdrgoldshares.com/usa/historical-data/',
  },
  'central-bank-holders': {
    provider: 'World Gold Council',
    description: '各国官方黄金储备数据',
    href: 'https://www.gold.org/goldhub/data/gold-reserves-by-country',
  },
  'central-bank-buyers': {
    provider: 'World Gold Council',
    description: '各国官方黄金储备数据',
    href: 'https://www.gold.org/goldhub/data/gold-reserves-by-country',
  },
} as const;

type ExternalGoldResearchKey = keyof typeof externalGoldResearch;

function renderExternalGoldResearch(key: ExternalGoldResearchKey) {
  const item = externalGoldResearch[key];
  return h(
    'div',
    {
      style: {
        minHeight: '260px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '14px',
        padding: '32px',
        textAlign: 'center',
        color: 'var(--color-text-2)',
      },
    },
    [
      h(
        'span',
        {
          style: {
            padding: '4px 10px',
            border: '1px solid var(--color-border-2)',
            borderRadius: '999px',
            fontSize: '12px',
            letterSpacing: '0.04em',
          },
        },
        'External Link · permission_required',
      ),
      h('strong', { style: { color: 'var(--color-text-1)', fontSize: '16px' } }, item.provider),
      h('span', item.description),
      h(
        'a',
        {
          href: item.href,
          target: '_blank',
          rel: 'noopener noreferrer',
          style: {
            padding: '9px 16px',
            borderRadius: '8px',
            background: 'rgb(var(--primary-6))',
            color: '#fff',
            fontWeight: '600',
            textDecoration: 'none',
          },
        },
        '打开官方数据页 ↗',
      ),
      h('small', '未取得生产再利用许可前，不在本地复制或展示第三方静态快照。'),
    ],
  );
}

export default defineComponent({
  name: 'LocalChartWidget',
  props: {
    widget: { type: Object as PropType<WidgetConfig>, required: true },
  },
  setup(props) {
    return () => {
      try {
        const key = props.widget.localKey as LocalWidgetKey;
        switch (key) {
          case 'spdr-daily-flow':
            return renderExternalGoldResearch(key);
          case 'spdr-holdings-vs-price':
            return renderExternalGoldResearch(key);
          case 'etf-weekly-flows':
            return renderExternalGoldResearch(key);
          case 'etf-ytd-summary':
            return renderExternalGoldResearch(key);
          case 'central-bank-holders':
            return renderExternalGoldResearch(key);
          case 'central-bank-buyers':
            return renderExternalGoldResearch(key);
          case 'gold-vs-nominal':
            return h(DualAxisChart, {
              rows: mergeGoldWithSeries('nominal10Y'),
              leftLabel: '黄金价格代理',
              rightLabel: '美国 10Y 名义利率',
              leftUnit: '美元/盎司',
              rightUnit: '%',
              leftColor: '#c7931a',
              rightColor: '#165dff',
            });
          case 'gold-vs-breakeven':
            return h(DualAxisChart, {
              rows: mergeGoldWithSeries('breakeven10Y'),
              leftLabel: '黄金价格代理',
              rightLabel: '10Y Breakeven',
              leftUnit: '美元/盎司',
              rightUnit: '%',
              leftColor: '#c7931a',
              rightColor: '#0f8b6d',
            });
          case 'gold-vs-real':
            return h(DualAxisChart, {
              rows: mergeGoldWithSeries('real10Y'),
              leftLabel: '黄金价格代理',
              rightLabel: '美国 10Y 实际利率',
              leftUnit: '美元/盎司',
              rightUnit: '%',
              leftColor: '#c7931a',
              rightColor: '#7c3aed',
            });
          case 'gold-vs-gvz':
            return h(DualAxisChart, {
              rows: mergeGoldWithGvz(),
              leftLabel: '黄金价格代理',
              rightLabel: 'GVZ',
              leftUnit: '美元/盎司',
              rightUnit: '指数点',
              leftColor: '#c7931a',
              rightColor: '#dc2626',
            });
          case 'gold-market-detail-table':
            return h(TerminalDetailPanel, {
              class: 'terminal-detail-panel--embedded',
              title: '市场明细',
              marketId: 'gold',
              columns: marketTerminalConfigs.gold.detailColumns,
              groups: marketTerminalConfigs.gold.detailGroups,
              rotationButtonLabel: marketTerminalConfigs.gold.rotationButtonLabel,
              rotationHeatmap: marketTerminalConfigs.gold.rotationHeatmap,
            });
          case 'macro-market-detail-table':
            return h(MacroMarketDetailPanel);
          case 'macro-global-m2':
            return h(MacroSeriesChart, {
              groupId: 'globalM2Level',
              years: 10,
              unitLabel: 'USD tn',
            });
          case 'macro-global-m2-yoy':
            return h(MacroSeriesChart, { groupId: 'globalM2YoY', years: 10, unitLabel: '%' });
          case 'macro-growth-production':
            return h(MacroSeriesChart, { groupId: 'growthProduction', years: 10, unitLabel: '%' });
          case 'macro-growth-labor':
            return h(MacroSeriesChart, { groupId: 'growthLabor', years: 2, unitLabel: 'persons' });
          case 'macro-growth-activity':
            return h(MacroSeriesChart, { groupId: 'growthActivity', years: 5, unitLabel: 'index' });
          case 'macro-actual-inflation':
            return h(MacroSeriesChart, { groupId: 'actualInflation', years: 5, unitLabel: '%' });
          case 'macro-upstream-inflation':
            return h(MacroSeriesChart, { groupId: 'upstreamInflation', years: 5, unitLabel: '%' });
          case 'macro-market-inflation':
            return h(MacroSeriesChart, { groupId: 'marketInflation', years: 5, unitLabel: '%' });
          case 'macro-rate-corridor':
            return h(MacroSeriesChart, { groupId: 'rateCorridor', years: 1, unitLabel: '%' });
          case 'macro-risk-hy-oas':
            return h(MacroSeriesChart, { groupId: 'riskHighYieldOas', years: 5, unitLabel: '%' });
          case 'macro-risk-credit-ratio':
            return h(MacroSeriesChart, {
              groupId: 'riskCreditRatio',
              years: 2,
              unitLabel: 'ratio',
            });
          case 'cftc-gold-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcGoldNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-gold-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcGoldPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'cftc-silver-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcSilverNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-silver-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcSilverPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'cftc-copper-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcCopperNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-copper-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcCopperPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'cftc-wti-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcWtiNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-wti-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcWtiPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'cftc-natural-gas-net':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcNaturalGasNet',
              years: 5,
              unitLabel: 'contracts',
            });
          case 'cftc-natural-gas-percentile':
            return h(MacroSeriesChart, {
              dataDomain: 'commodity',
              groupId: 'cftcNaturalGasPercentile',
              years: 5,
              unitLabel: 'percentile',
            });
          case 'crypto-market-detail-table':
            return h(TerminalDetailPanel, {
              class: 'terminal-detail-panel--embedded',
              title: '市场明细',
              marketId: 'crypto',
              columns: marketTerminalConfigs.crypto.detailColumns,
              groups: marketTerminalConfigs.crypto.detailGroups,
              rotationButtonLabel: marketTerminalConfigs.crypto.rotationButtonLabel,
              rotationHeatmap: marketTerminalConfigs.crypto.rotationHeatmap,
            });
          case 'btc-etf-flow':
            return h(DualAxisChart, {
              rows: BTC_ETF_FLOW_ROWS,
              leftLabel: 'BTC ETF 日净流量',
              rightLabel: 'BTC 价格',
              leftUnit: '百万美元',
              rightUnit: '美元',
              leftColor: '#1b9a7a',
              rightColor: '#2f63f2',
              barPositiveColor: '#1b9a7a',
              barNegativeColor: '#df5a55',
              barWidthRatio: 0.68,
              leftAsBars: true,
              divergingBars: true,
              showRangeSlider: true,
              windowSize: 8,
            });
          case 'btc-treasury-flow':
            return h(TreasuryFlowChart);
          default:
            return h('div', { class: 'local-empty' }, '该图表配置尚未接入。');
        }
      } catch (error) {
        console.error('[hedgeBoard] Local widget render failed:', props.widget.title, error);
        return h(
          'div',
          { class: 'local-empty' },
          '该研究卡片的数据格式暂未兼容，已自动跳过，不影响其他模块浏览。',
        );
      }
    };
  },
});
