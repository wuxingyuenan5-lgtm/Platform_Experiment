import { defineComponent, h, type PropType } from 'vue';

import ReserveRanking from '../components/ReserveRanking';
import TerminalDetailPanel from '../components/TerminalDetailPanel.vue';
import MacroMarketDetailPanel from '../components/MacroMarketDetailPanel.vue';
import { type LocalWidgetKey, type WidgetConfig } from '../nativeData/dashboardClean';
import { marketData } from '../nativeData/generated/marketData';
import { marketTerminalConfigs } from '../nativeData/marketTerminal';
import { BTC_ETF_FLOW_ROWS, mergeGoldWithGvz, mergeGoldWithSeries } from './chartCore';
import DualAxisChart from './DualAxisChart';
import { EtfWeeklyFlowsPanel, YtdSummaryPanel } from './EtfResearchPanels';
import TreasuryFlowChart from './TreasuryFlowChart';
import MacroSeriesChart from './MacroSeriesChart';

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
            return h(DualAxisChart, {
              rows: marketData.spdr.history.slice(-60).map((point) => ({
                date: point.date,
                left: point.flowTonnes ?? 0,
                right: point.goldPrice,
              })),
              leftLabel: 'SPDR 日流量',
              rightLabel: '黄金价格',
              leftUnit: '吨',
              rightUnit: '美元/盎司',
              leftColor: '#159a76',
              rightColor: '#2f63f2',
              barPositiveColor: '#18a17d',
              barNegativeColor: '#de5d56',
              barWidthRatio: 0.7,
              leftAsBars: true,
              divergingBars: true,
            });
          case 'spdr-holdings-vs-price':
            return h(DualAxisChart, {
              rows: marketData.spdr.history.slice(-60).map((point) => ({
                date: point.date,
                left: point.tonnes,
                right: point.goldPrice,
              })),
              leftLabel: 'SPDR 持仓量',
              rightLabel: '黄金价格',
              leftUnit: '吨',
              rightUnit: '美元/盎司',
              leftColor: '#d6ae4a',
              rightColor: '#2f63f2',
              barWidthRatio: 0.6,
              leftAsBars: true,
            });
          case 'etf-weekly-flows':
            return h(EtfWeeklyFlowsPanel);
          case 'etf-ytd-summary':
            return h(YtdSummaryPanel);
          case 'central-bank-holders':
            return h(ReserveRanking, {
              rows: marketData.centralBank.topHolders.map((item) => ({
                label: item.name,
                value: item.tonnes,
                sublabel: item.region,
                detail: item.region,
              })),
              color: '#c7931a',
            });
          case 'central-bank-buyers':
            return h(ReserveRanking, {
              rows: marketData.centralBank.strategicBuyers.map((item) => ({
                label: item.name,
                value: item.deltaTonnes,
                sublabel: `${item.startTonnes.toFixed(2)} → ${item.endTonnes.toFixed(2)} 吨`,
                detail: `${item.startTonnes.toFixed(2)} → ${item.endTonnes.toFixed(2)} 吨`,
              })),
              color: '#165dff',
              diverging: true,
            });
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
